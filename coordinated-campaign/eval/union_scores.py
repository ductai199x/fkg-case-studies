# F1 of unions of detectors (an account is flagged if any member flags it), from the per-world predictions in results/*.jsonl.
import argparse, json, statistics as st
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
POS = {"campaign_core", "campaign_amplifier"}
ap = argparse.ArgumentParser(); ap.add_argument("--dir", default=str(ROOT / "results/stress6")); ap.add_argument("--exps", nargs="+", required=True)
ap.add_argument("--unions", nargs="+", required=True, help="members joined with '|', e.g. open_stance+amp|tie_open+amp")
ap.add_argument("--seeds", default="1,2,3,4,5,6"); ap.add_argument("--metric", default="f1"); a = ap.parse_args(); seeds = {int(s) for s in a.seeds.split(",")}
print(f"{a.metric}, eta=0/0.3, seeds {a.seeds}"); print("| exp | " + " | ".join(a.unions) + " |"); print("|---|" + "---|" * len(a.unions))
for e in a.exps:
    by = defaultdict(dict)
    for l in open(Path(a.dir) / f"{e}.jsonl"):
        r = json.loads(l)
        if "pred" in r and r["seed"] in seeds: by[(r["eta"], r["seed"])][r["query"]] = r
    cells = []
    for u in a.unions:
        qs = u.split("|"); v = defaultdict(list)
        for (eta, s), d in by.items():
            if not all(q in d for q in qs): continue
            roles = {x: ro for q in qs for x, ro in d[q]["pred"]}; tp = sum(ro in POS for ro in roles.values())
            P = tp / len(roles) if roles else 0; R = tp / d[qs[0]]["n_pos"]
            v[eta].append({"f1": 2 * P * R / (P + R) if P + R else 0, "precision": P, "recall": R}[a.metric])
        cells.append("/".join("%.2f" % st.mean(v[x]) for x in sorted(v)) if v else "-")
    print(f"| {e} | " + " | ".join(cells) + " |")
