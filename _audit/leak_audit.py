# Label-leak audit. Question: can a nuisance attribute of an AI-attributed region tell a detector false positive (FP)
# from a true AI region (TP), without any cross-layer reasoning? Worlds are pooled over seeds so FPs are numerous.
# Discrete features: 5-fold cross-validated balanced accuracy of a lookup-table rule (0.5 = no signal, 1.0 = perfect leak).
# Only AI regions inside images that also have a camera region are compared (fully synthetic images differ for real reasons).
# Confidence: AUC (an intended, overlapping signal) and the share of FP regions that repeat the most common FP value.
import json, sys, os, random, subprocess, tempfile, shutil
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../_shared"))
from sparql_runner import load, run
Q = """PREFIX fkg: <https://example.org/fkg#> PREFIX as: <https://www.w3.org/ns/activitystreams#> PREFIX ctx: <https://example.org/fkg/context#>
SELECT ?img ?post ?gen ?conf ?desc ?obj ?re ?q ?ent ?post_ops WHERE {
  ?r fkg:contained_in ?img ; fkg:produced_by ?s ; fkg:depict ?d . ?s a fkg:AIGenerator ; fkg:hasGeneratorModel ?gen ; fkg:hasConfidence ?conf .
  ?d fkg:hasObjectDescription ?desc ; fkg:hasObjectedness ?obj . ?post as:attachment ?img . OPTIONAL { ?d ctx:depictsEntity ?ent }
  FILTER EXISTS { ?r2 fkg:contained_in ?img ; fkg:produced_by ?s2 . ?s2 a fkg:CameraModel }   # partially AI images only: the real FP-vs-edit confusion
  OPTIONAL { ?r fkg:compress_by ?c . ?c fkg:hasCompressionFactor ?q . OPTIONAL { ?c fkg:hasReCompressed ?re } }
  { SELECT ?r (GROUP_CONCAT(DISTINCT STRAFTER(STR(?t), "#"); separator="+") AS ?post_ops) WHERE { ?r fkg:modified_by ?m . ?m a ?t } GROUP BY ?r } }"""
STUDIES = {"cs1": ("cs1_recycled_media", {"FKG_ETA": "0.3"}, range(5)), "cs2": ("cs2_lineage_laundering", {}, range(10)), "cs3": ("cs3_intent_materiality", {"FKG_ETA": "0.3"}, range(5))}
def label(study, r, gt):
    if study == "cs1": return "fp" if gt["claim_posts"].get(r["post"]) in ("authentic_current", "recycled_ooc", "archival_ok") else "tp"
    if study == "cs2": return "tp" if r["gen"] in gt["variant"].get(r["img"], []) else "fp"
    return "fp" if gt["intent"].get(r["post"]) == "NoAlteration" else "tp"
def cv_lookup(xs, k=5, seed=0):
    xs = xs[:]; random.Random(seed).shuffle(xs); correct = Counter(); total = Counter()
    for f in range(k):
        train = [x for i, x in enumerate(xs) if i % k != f]; test = [x for i, x in enumerate(xs) if i % k == f]
        by = defaultdict(Counter)
        for v, l in train: by[v][l] += 1
        n = Counter(l for _, l in train)
        pred = {v: max(("fp", "tp"), key=lambda l: c[l] / max(n[l], 1)) for v, c in by.items()}
        for v, l in test: total[l] += 1; correct[l] += pred.get(v, "tp") == l
    return round(0.5 * (correct["fp"] / max(total["fp"], 1) + correct["tp"] / max(total["tp"], 1)), 3)
def auc(pos, neg):
    return round(sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg)), 3)
def rows_for(gen_dir, study, seeds, env):
    out = []
    for s in seeds:
        tmp = tempfile.mkdtemp()
        subprocess.run([sys.executable, "generate.py"], cwd=gen_dir, env={**os.environ, **env, "FKG_SEED": str(1000 + s), "FKG_DATA": tmp}, check=True, capture_output=True)
        ds = load(f"{tmp}/world.trig"); gt = json.load(open(f"{tmp}/ground_truth.json"))
        for r in run(ds, Q):
            r["label"] = label(study, r, gt)
            if study == "cs3" and r.get("ent"): continue   # compare FPs with non-entity (peripheral-type) true regions only
            out.append(r)
        shutil.rmtree(tmp)
    return out
def audit(gen_root):
    res = {}
    for study, (d, env, seeds) in STUDIES.items():
        rows = rows_for(os.path.join(gen_root, d), study, seeds, env)
        fp = [r for r in rows if r["label"] == "fp"]; tp = [r for r in rows if r["label"] == "tp"]
        feats = {"objectness": "obj", "description": "desc", "recompressed": "re", "post_processing": "post_ops", "compression_factor": "q"}
        res[study] = dict(n=dict(fp=len(fp), tp=len(tp)),
                          lookup_balanced_acc={k: cv_lookup([(r.get(f) or "none", r["label"]) for r in rows]) for k, f in feats.items()},
                          conf_auc_tp_over_fp=auc([float(r["conf"]) for r in tp], [float(r["conf"]) for r in fp]),
                          fp_conf_modal_share=round(Counter(r["conf"] for r in fp).most_common(1)[0][1] / len(fp), 3))
    return res
if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, ".."); out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "leak_audit.json")
    res = audit(root); json.dump(res, open(out, "w"), indent=1)
    for k, v in res.items(): print(k, v)
