# Base-rate curve (doc section 7.8): within-wave detection precision and cross-wave attribution as benign look-alike
# coordination (fans, brand agencies, news syndication) grows relative to the campaign. x = look-alike accounts per campaign
# account in an event. Events >= --from-event pooled over seeds and noise levels; prints markdown, writes a JSON for charts.
import argparse, json, statistics as st
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
LOOK = {"fan", "brand", "news"}
ATTR = ["narrative", "timing", "fkg_chained_same_gen", "fkg_chained_any_gen", "fkg_confirmed"]
DET = ["U", "U+fkg_chained_any_gen"]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--points", nargs="+", required=True, help="exp=path/to.jsonl")
    ap.add_argument("--from-event", type=int, default=1); ap.add_argument("--json", default=None); a = ap.parse_args()
    out, P = [], print
    P("| exp | look-alikes per campaign account | U precision | U recall | U+FKG precision | FP roles (U) | " + " | ".join(f"{m} link c/w/n" for m in ATTR) + " | " + " | ".join(f"{m} attr. precision (benign labelled)" for m in ATTR) + " |")
    P("|---|" + "---|" * (5 + 2 * len(ATTR)))
    for spec in a.points:
        exp, path = spec.split("="); rows = [json.loads(l) for l in open(path)]; rows = [r for r in rows if r["exp"] == exp and r["event"] >= a.from_event]
        det = {m: [r for r in rows if r["kind"] == "detection" and r["method"] == m] for m in DET}
        att = {m: [r for r in rows if r["kind"] == "attribution" and r["method"] == m] for m in ATTR}
        n_look = st.mean(r.get("n_lookalike", 26) for r in det["U"]); n_pos = st.mean(r["n_pos"] for r in det["U"]); x = n_look / n_pos
        prec = lambda R: sum(r["tp"] for r in R) / max(1, sum(r["tp"] + r["fp"] for r in R)) if R and "tp" in R[0] else st.mean(r["precision"] for r in R)
        rec = lambda R: sum(r["tp"] for r in R) / max(1, sum(r["tp"] + r["fn"] for r in R)) if R and "tp" in R[0] else st.mean(r["recall"] for r in R)
        fpr = Counter()
        for r in det["U"]: fpr.update(dict(r["fp_roles"]))
        links = {}
        for m, R in att.items():
            c, w, n = (sum(r[k] for r in R) for k in ("link_correct", "link_wrong", "link_none")); t = max(1, c + w + n); links[m] = (c / t, w / t, n / t)
        aprec = {m: (sum(r["attr_correct"] for r in R) / max(1, sum(r["attr_labelled"] for r in R)), sum(r["benign_labelled"] for r in R)) for m, R in att.items()}
        d = {"exp": exp, "x": x, "n_lookalike": n_look, "n_pos": n_pos, "U_prec": prec(det["U"]), "U_rec": rec(det["U"]), "UF_prec": prec(det["U+fkg_chained_any_gen"]),
             "UF_rec": rec(det["U+fkg_chained_any_gen"]), "fp_roles": dict(fpr), "links": links, "attr_prec": aprec, "n_rows": len(det["U"])}
        T = [r for r in rows if r["kind"] == "detection" and r["method"] == "U_tenure"]
        if T:  # style-tenure filter: within-wave flagged accounts minus those with an old house style matching their window images
            TF = [r for r in rows if r["kind"] == "detection" and r["method"] == "U_tenure+fkg_chained_same_gen"]
            AT = [r for r in rows if r["kind"] == "attribution_tenure" and r["method"] == "fkg_chained_same_gen"]
            d["tenure"] = {"U_prec": prec(T), "U_rec": rec(T), "UF_prec": prec(TF), "UF_rec": rec(TF), "camp_tenured": sum(r["n_tenured_camp"] for r in T),
                           "tenured": sum(r["n_tenured"] for r in T), "attr_prec": sum(r["attr_correct"] for r in AT) / max(1, sum(r["attr_labelled"] for r in AT)),
                           "benign_labelled": sum(r["benign_labelled"] for r in AT)}
        out.append(d); fr = ", ".join(f"{k} {v}" for k, v in fpr.most_common(4))
        P(f"| {exp} | {x:.1f} | {d['U_prec']:.2f} | {d['U_rec']:.2f} | {d['UF_prec']:.2f} | {fr} | " + " | ".join("{:.2f}/{:.2f}/{:.2f}".format(*links[m]) for m in ATTR) + " | " + " | ".join("{:.2f} ({})".format(*aprec[m]) for m in ATTR) + " |")
    if any("tenure" in d for d in out):
        P("\n### With the style-tenure filter\n"); P("| exp | x | U precision | U recall | U+FKG same-gen precision | recall | campaign accounts dropped / all dropped | FKG same-gen attr. precision (benign labelled) |"); P("|---|---|---|---|---|---|---|---|")
        for d in out:
            t = d.get("tenure")
            if t: P(f"| {d['exp']} | {d['x']:.1f} | {t['U_prec']:.2f} | {t['U_rec']:.2f} | {t['UF_prec']:.2f} | {t['UF_rec']:.2f} | {t['camp_tenured']} / {t['tenured']} | {t['attr_prec']:.2f} ({t['benign_labelled']}) |")
    if a.json: Path(a.json).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
