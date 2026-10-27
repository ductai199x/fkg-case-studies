# Runs CS3 queries/rule and baselines; scores against planted ground truth.
import json, sys, csv, time
sys.path.insert(0, "../_shared")
from sparql_runner import load, run
from metrics import set_prf, classify_report

CATS = ["NoAlteration", "UndisclosedMaterialAlteration", "UndisclosedPeripheralAlteration", "DisclosedSynthetic", "SatireOrArt"]
def save(rows, path):
    with open(path, "w") as f:
        if rows: w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

def main(query_dir="queries", out="results"):
    import os; D = os.environ.get("FKG_DATA", "data"); ds = load(f"{D}/world.trig"); gt = json.load(open(f"{D}/ground_truth.json")); R = {}
    def q(path):
        t0 = time.time(); rows = run(ds, open(path).read()); save(rows, f"{out}/{path.split('/')[-1].replace('.rq', '.csv')}"); return rows, round(time.time() - t0, 2)
    gold_mat = [k for k, v in gt["intent"].items() if v == "UndisclosedMaterialAlteration"]
    rows, dt = q(f"{query_dir}/q1_material_undisclosed.rq")
    ranked = list(dict.fromkeys(r["post"] for r in rows))
    R["CQ3.1 triage queue (integrated)"] = dict(set_prf(ranked, gold_mat), precision_at_10=sum(p in gold_mat for p in ranked[:10]) / 10, seconds=dt,
        note="3 material alterations have AI confidence < 0.7 (detector misses); recall ceiling 31/34")
    for name, path in [("Baseline queue: forensic only", "baselines/b1_forensic_only.rq"), ("Baseline queue: context only", "baselines/b1_context_only.rq"),
                       ("Ablation queue: no materiality join", "baselines/b1_no_materiality.rq")]:
        rows, dt = q(path); R[name] = dict(set_prf({r["post"] for r in rows}, gold_mat), seconds=dt)
    rows, dt = q(f"{query_dir}/q2_credential_contradiction.rq")
    R["CQ3.2 credential contradictions"] = dict(set_prf({r["post"] for r in rows}, gt["credential_contradiction"]), seconds=dt)
    trip, dt = q(f"{query_dir}/q3_intent_rule.rq")
    ia_post = {t["s"]: t["o"] for t in trip if t["p"].endswith("aboutPost")}
    pred = {ia_post[t["s"]]: t["o"].split("#")[-1] for t in trip if t["p"].endswith("intentCategory")}
    R["CQ3.3 intent rule (integrated)"] = dict(classify_report(pred, gt["intent"], CATS), triples=len(trip), seconds=dt)
    for name, path in [("Baseline labels: forensic only", "baselines/b3_forensic_only_labels.rq"), ("Baseline labels: context only", "baselines/b3_context_only_labels.rq")]:
        rows, dt = q(path); R[name] = dict(classify_report({r["post"]: r["cat"].split("#")[-1] for r in rows}, gt["intent"], CATS), seconds=dt)
    rows, dt = q(f"{query_dir}/q4_anachronism.rq"); R["CQ3.4 anachronistic attributions"] = dict(set_prf({r["post"] for r in rows}, gt["anachronism"]),
        versions=sorted({r["version"].split("#")[-1] for r in rows}), seconds=dt)
    rows, dt = q(f"{query_dir}/q5_retraction_impact.rq"); R["CQ3.5 retraction impact"] = dict(set_prf({r["review"] for r in rows}, gt["affected_reviews"]), seconds=dt)
    json.dump(R, open(f"{out}/summary.json", "w"), indent=1); return R

if __name__ == "__main__":
    for k, v in main(*sys.argv[1:]).items():
        print(k, {kk: vv for kk, vv in v.items() if kk not in ("per_class", "confusion")})
        if "per_class" in v: print("   per-class F1:", {L: x["f1"] for L, x in v["per_class"].items()})
