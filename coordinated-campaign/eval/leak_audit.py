# Label-leak audit for the stress simulator (approach after _audit/leak_audit.py in the use-cases study).
# For every attribute an investigator can read, score it ALONE against the ground truth with a 5-fold CV lookup-table
# rule (balanced accuracy: 0.5 = no signal, 1.0 = perfect leak). Attributes are tagged "intended" when the scenario
# design meant them to carry signal (processing, claims, timing, creation burst, reposts) and "nuisance" otherwise;
# a nuisance attribute far above 0.5 is a leak by construction.
import argparse, json, random, sys, tempfile
from collections import Counter, defaultdict
from pathlib import Path
import pyoxigraph as ox
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sim")); sys.path.insert(0, str(ROOT / "eval"))
from stress import StressScenario, make_cfg
from stress_grid import EXPS

PFX = """PREFIX fkg: <https://example.org/fkg#> PREFIX as: <https://www.w3.org/ns/activitystreams#> PREFIX schema: <https://schema.org/> PREFIX prov: <http://www.w3.org/ns/prov#>"""
Q_REGION = PFX + """ SELECT ?img ?r ?obj ?desc ?srcType ?conf ?cmp ?q (COUNT(?m) AS ?nops) WHERE {
  ?r fkg:contained_in ?img ; fkg:produced_by ?s ; fkg:depict ?d ; fkg:compress_by ?c . ?s a ?srcType ; fkg:hasConfidence ?conf .
  ?d fkg:hasObjectedness ?obj ; fkg:hasObjectDescription ?desc . ?c a ?cmp . OPTIONAL { ?c fkg:hasCompressionFactor ?q } OPTIONAL { ?r fkg:modified_by ?m }
} GROUP BY ?img ?r ?obj ?desc ?srcType ?conf ?cmp ?q"""
Q_NREG = PFX + " SELECT ?img (COUNT(?r) AS ?n) WHERE { ?img fkg:hasRegion ?r } GROUP BY ?img"
Q_POSTER = PFX + " SELECT ?img ?acct ?t WHERE { ?n as:attachment ?img ; as:attributedTo ?acct ; as:published ?t }"
Q_ACCT = PFX + """ SELECT ?a ?created ?user (COUNT(DISTINCT ?n) AS ?posts) (COUNT(DISTINCT ?i) AS ?imgs) WHERE {
  ?a a as:Person ; as:published ?created ; as:preferredUsername ?user . OPTIONAL { ?n as:attributedTo ?a . OPTIONAL { ?n as:attachment ?i } } } GROUP BY ?a ?created ?user"""
Q_ANN = PFX + " SELECT ?ann ?a WHERE { ?ann a as:Announce ; as:actor ?a }"
Q_CONTENT = PFX + " SELECT ?a ?txt WHERE { ?n as:attributedTo ?a ; as:content ?txt }"


def cv_lookup(pairs, k=5, seed=0):
    xs = pairs[:]; random.Random(seed).shuffle(xs); ok, tot = Counter(), Counter()
    for f in range(k):
        tr = [x for i, x in enumerate(xs) if i % k != f]; te = [x for i, x in enumerate(xs) if i % k == f]
        by, n = defaultdict(Counter), Counter(l for _, l in tr)
        for v, l in tr: by[v][l] += 1
        pred = {v: max((0, 1), key=lambda l: c[l] / max(n[l], 1)) for v, c in by.items()}
        for v, l in te: tot[l] += 1; ok[l] += pred.get(v, 0) == l
    return round(0.5 * (ok[0] / max(tot[0], 1) + ok[1] / max(tot[1], 1)), 3)


def world_rows(exp, seed, eta, over=None):
    sc = StressScenario(make_cfg(**{**EXPS[exp], **(over or {})}), seed, eta); sc.build_world()
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "w.nq"; sc.write_nquads(p); st = ox.Store(); st.bulk_load(path=str(p), format=ox.RdfFormat.N_QUADS)
        q = lambda s: [{k: (v.value if v is not None else None) for k, v in zip([x.value for x in res.variables], row)} for res in [st.query(s, use_default_graph_as_union=True)] for row in res]
        regions, nreg, posters, accts, anns, texts = q(Q_REGION), q(Q_NREG), q(Q_POSTER), q(Q_ACCT), q(Q_ANN), q(Q_CONTENT)
    truth = sc.truth(); pos = set(truth["positives"]); core = set(truth["core"])
    img_core = defaultdict(int)
    for r in posters: img_core[r["img"]] |= r["acct"] in core
    nreg = {r["img"]: int(r["n"]) for r in nreg}
    # image level: label = posted by a campaign core account (the campaign's own images)
    img_rows = []
    by_img = defaultdict(list)
    for r in regions: by_img[r["img"]].append(r)
    for img, rs in by_img.items():
        synth = [r for r in rs if r["srcType"].endswith("AIGenerator")]; cam = [r for r in rs if r["srcType"].endswith("CameraModel")]
        img_rows.append(dict(label=img_core[img], n_regions=nreg.get(img, 0), any_obj_false=any(r["obj"] == "false" for r in rs),
                             descs="|".join(sorted({r["desc"] for r in rs})), compression="|".join(sorted({r["cmp"].split("#")[1] + str(r["q"]) for r in rs})),
                             synth_conf_bin=min((round(float(r["conf"]) * 20) / 20 for r in synth), default=None),
                             cam_conf_bin=min((round(float(r["conf"]) * 20) / 20 for r in cam), default=None),
                             n_ops=max(int(r["nops"]) for r in rs)))
    # account level: label = campaign core or amplifier
    n_ann = Counter(r["a"] for r in anns); ann_idx = defaultdict(list)
    for r in anns: ann_idx[r["a"]].append(int(r["ann"].rsplit("-", 1)[1]) if r["ann"].rsplit("-", 1)[1].isdigit() else -1)
    acct_imgs = defaultdict(set)
    for r in posters: acct_imgs[r["acct"]].add(r["img"])
    first_words = defaultdict(set)
    for r in texts: first_words[r["a"]].add(r["txt"].split()[0].lower() if r["txt"] else "")
    acct_rows = []
    for r in accts:
        a = r["a"]; ims = acct_imgs.get(a, set())
        acct_rows.append(dict(label=int(a in pos), posts=int(r["posts"]), imgs=int(r["imgs"]), announces=n_ann[a],
                              created_year=r["created"][:4], username_len=len(r["user"]),
                              any_2region_img=any(nreg.get(i, 0) >= 2 for i in ims),
                              any_obj_false_img=any(any(x["obj"] == "false" for x in by_img.get(i, [])) for i in ims),
                              ann_index_decile=(min(ann_idx[a]) * 10 // max(1, len(anns))) if ann_idx[a] else None,
                              first_word="|".join(sorted(first_words[a]))[:60]))
    return img_rows, acct_rows


INTENDED = {"n_ops", "posts", "imgs", "announces", "created_year", "first_word"}  # first_word: template pools are a known, documented shortcut


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--exps", nargs="+", default=["base", "r_all"]); ap.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3])
    ap.add_argument("--etas", nargs="+", type=float, default=[0.0, 0.3]); ap.add_argument("--out", default=str(ROOT / "results" / "leak_audit.json")); ap.add_argument("--set", default="{}")
    args = ap.parse_args(); res = {}
    for exp in args.exps:
        for eta in args.etas:
            I, A = [], []
            for s in args.seeds:
                i, a = world_rows(exp, s, eta, json.loads(args.set)); I += i; A += a
            key = f"{exp}@eta{eta}"
            res[key] = {"images": {f: cv_lookup([(str(r[f]), r["label"]) for r in I]) for f in I[0] if f != "label"},
                        "accounts": {f: cv_lookup([(str(r[f]), r["label"]) for r in A]) for f in A[0] if f != "label"},
                        "n": {"img_pos": sum(r["label"] for r in I), "img": len(I), "acct_pos": sum(r["label"] for r in A), "acct": len(A)}}
            print(key, json.dumps(res[key]), flush=True)
    Path(args.out).write_text(json.dumps(res, indent=1))
    print("intended:", sorted(INTENDED))


if __name__ == "__main__":
    main()
