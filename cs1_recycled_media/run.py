# Runs CS1 hand-written queries and baselines, scores against planted ground truth, records results.
import json, sys, csv, time
sys.path.insert(0, "../_shared")
from sparql_runner import load, run
from metrics import set_prf, classify_report

def main(query_dir="queries", out="results"):
    import os; D = os.environ.get("FKG_DATA", "data"); ds = load(f"{D}/world.trig"); gt = json.load(open(f"{D}/ground_truth.json"))
    gold = gt["claim_posts"]; gold4 = {k: ("no_problem_found" if v in ("authentic_current", "archival_ok") else v) for k, v in gold.items()}
    labels = ["synthetic", "manipulated", "recycled_ooc", "no_problem_found"]
    R = {}
    def q(name):
        t0 = time.time(); rows = run(ds, open(name).read()); dt = time.time() - t0
        with open(f"{out}/{name.split('/')[-1].replace('.rq', '.csv')}", "w") as f:
            if rows: w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
        return rows, round(dt, 2)
    rows, dt = q(f"{query_dir}/q1_recycled.rq")
    R["CQ1.1 recycled out-of-context (integrated)"] = dict(set_prf([r["post"] for r in rows], [k for k, v in gold.items() if v == "recycled_ooc"]), seconds=dt,
        note="3 of 25 recycled posts have no pre-event instance in the crawl; recall ceiling is 22/25 = 0.88")
    rows, dt = q(f"{query_dir}/q2_earliest_appearance.rq")
    pred = {r["post"]: r["earliestPost"] for r in rows}; known = {k: v for k, v in gt["earliest_appearance"].items() if v}
    R["CQ1.2 earliest appearance"] = dict(correct=sum(pred.get(k) == v for k, v in known.items()), of=len(known), spurious=len(set(pred) - set(known)), seconds=dt)
    for name, path in [("CQ1.3 classification (integrated)", f"{query_dir}/q3_classify.rq"),
                       ("Baseline: forensic layer only", "baselines/b_forensic_only.rq"),
                       ("Baseline: context layer only", "baselines/b_context_only.rq"),
                       ("Ablation: no camera-agreement guard", "baselines/ablation_no_camera_guard.rq"),
                       ("Ablation: no confidence threshold", "baselines/ablation_no_conf_threshold.rq")]:
        rows, dt = q(path); R[name] = dict(classify_report({r["post"]: r["label"] for r in rows}, gold4, labels), seconds=dt)
    # set view of the baselines on the recycled class, for the headline comparison
    json.dump(R, open(f"{out}/summary.json", "w"), indent=1)
    return R

if __name__ == "__main__":
    R = main(*sys.argv[1:])
    for k, v in R.items():
        print(k, {kk: vv for kk, vv in v.items() if kk not in ("per_class", "confusion")})
        if "per_class" in v: print("   per-class F1:", {L: x["f1"] for L, x in v["per_class"].items()})
