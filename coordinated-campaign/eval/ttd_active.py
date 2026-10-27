# Early-detection recall measured against the campaign accounts that have acted in the campaign window by the cut
# (posted or reposted at or after the campaign start), alongside the usual recall against all campaign accounts.
import argparse, json, statistics as st, sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sim")); sys.path.insert(0, str(ROOT / "eval"))
from stress import StressScenario, make_cfg
from stress_grid import EXPS
from generate import BASE
from generate import dt

def active_set(exp, seed, eta):
    cfg = make_cfg(**EXPS[exp]); sc = StressScenario(cfg, seed, eta); sc.build_world()
    T = cfg["as_of"]; t0 = min(dt(*cp["start"]) for cp in cfg["campaigns"])
    pos = set(sc.truth()["positives"]); first = {}
    for x in sc.notes + sc.announces:
        if x["t"] >= t0: first[x["acct"]] = min(first.get(x["acct"], x["t"]), x["t"])
    return {a for a in pos if a.rsplit("/", 1)[1] in first and first[a.rsplit("/", 1)[1]] <= T}, len(pos)

ap = argparse.ArgumentParser(); ap.add_argument("--dir", default=str(ROOT / "results/stress6")); ap.add_argument("--exps", nargs="+", required=True)
ap.add_argument("--queries", nargs="+", required=True); a = ap.parse_args()
print("| exp | active / all campaign accounts | " + " | ".join(f"{q} F1 (active)" for q in a.queries) + " |"); print("|---|---|" + "---|" * len(a.queries))
for e in a.exps:
    rows = [json.loads(l) for l in open(Path(a.dir) / f"{e}.jsonl")]; cache = {}; f1 = defaultdict(lambda: defaultdict(list)); frac = []
    for r in rows:
        if r["query"] not in a.queries or "pred" not in r: continue
        k = (r["seed"], r["eta"])
        if k not in cache: cache[k] = active_set(e, r["seed"], r["eta"]); frac.append(len(cache[k][0]) / cache[k][1])
        act = cache[k][0]; pred = {x for x, _ in r["pred"]}; tp = len(pred & act)
        P = len({x for x, ro in r["pred"] if ro in ("campaign_core", "campaign_amplifier")}) / len(pred) if pred else 0; R = tp / max(1, len(act))
        f1[r["query"]][r["eta"]].append(2 * P * R / (P + R) if P + R else 0)
    print(f"| {e} | {st.mean(frac):.2f} | " + " | ".join("/".join("%.2f" % st.mean(f1[q][x]) for x in sorted(f1[q])) for q in a.queries) + " |")
