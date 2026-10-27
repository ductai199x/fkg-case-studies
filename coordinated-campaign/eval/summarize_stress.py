# Summarizes results/stress/<exp>.jsonl: mean F1 (and P, R) per experiment x detector x eta, plus cost columns.
import argparse, json, statistics as st
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(); ap.add_argument("--exps", nargs="+", required=True); ap.add_argument("--queries", nargs="*", default=[])
ap.add_argument("--metric", default="f1"); ap.add_argument("--dir", default=str(ROOT / "results/stress"))
a = ap.parse_args()
rows = [json.loads(l) for e in a.exps for l in open(Path(a.dir) / f"{e}.jsonl")]
qs = a.queries or list(dict.fromkeys(r["query"] for r in rows)); etas = sorted({r["eta"] for r in rows})
cell = defaultdict(list); secs = defaultdict(list); err = defaultdict(int)
for r in rows:
    if "f1" in r: cell[(r["exp"], r["query"], r["eta"])].append(r[a.metric]); secs[(r["exp"], r["query"])].append(r["seconds"])
    else: err[(r["exp"], r["query"])] += 1
print(f"{a.metric} (mean over seeds), columns eta=" + "/".join(f"{e:g}" for e in etas))
print("| exp | quads | " + " | ".join(qs) + " |"); print("|---|---|" + "---|" * len(qs))
for e in a.exps:
    qd = st.mean(r["quads"] for r in rows if r["exp"] == e)
    cells = []
    for q in qs:
        v = ["%.2f" % st.mean(cell[(e, q, x)]) if cell[(e, q, x)] else "-" for x in etas]
        s = f"{'/'.join(v)}" + (f" ({err[(e, q)]}err)" if err[(e, q)] else "")
        cells.append(s)
    print(f"| {e} | {qd/1e3:.0f}k | " + " | ".join(cells) + " |")
print("\nmedian query seconds")
print("| exp | " + " | ".join(qs) + " |")
for e in a.exps:
    print(f"| {e} | " + " | ".join("%.1f" % st.median(secs[(e, q)]) if secs[(e, q)] else "-" for q in qs) + " |")
