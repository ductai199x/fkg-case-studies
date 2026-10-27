# Runs CS2 queries (two-stage lineage rules included) and baselines; scores against the planted spread tree.
import json, sys, csv, time
sys.path.insert(0, "../_shared")
from sparql_runner import load, run, add_triples
from metrics import set_prf

def save(rows, path):
    with open(path, "w") as f:
        if rows: w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

def main(query_dir="queries", out="results"):
    import os; D = os.environ.get("FKG_DATA", "data"); ds = load(f"{D}/world.trig"); gt = json.load(open(f"{D}/ground_truth.json")); R = {}
    def q(path):
        t0 = time.time(); rows = run(ds, open(path).read()); save(rows, f"{out}/{path.split('/')[-1].replace('.rq', '.csv')}"); return rows, round(time.time() - t0, 2)
    gold_pz = {(f"https://example.org/fkg/cs2#cluster_{x['cluster']}", x["post"]) for x in gt["patient_zero"]}
    gold_pz_acct = {(f"https://example.org/fkg/cs2#cluster_{x['cluster']}", x["account"]) for x in gt["patient_zero"]}
    for name, path in [("CQ2.1 patient zero (integrated, corroborated)", f"{query_dir}/q1_patient_zero.rq"),
                       ("Ablation: no corroboration", "baselines/b1_patient_zero_no_corroboration.rq"),
                       ("Baseline: earliest post in cluster (context only)", "baselines/b1_patient_zero_context_only.rq")]:
        rows, dt = q(path)
        spread = {x["post"]: sum(gt["cluster_of"][k] == x["cluster"] and x["generator"] in v for k, v in gt["variant"].items()) - 1 for x in gt["patient_zero"]}
        spread_gold = {(c, p) for c, p in gold_pz if spread[p] >= 2}
        R[name] = dict(recall_on_edits_that_spread=f'{len({(r["cluster"], r["post"]) for r in rows} & spread_gold)}/{len(spread_gold)}', post=set_prf({(r["cluster"], r["post"]) for r in rows}, gold_pz),
                       account=set_prf({(r["cluster"], r["account"]) for r in rows}, gold_pz_acct), seconds=dt)
    # lineage: two-stage rule, materialized into a derived graph
    t0 = time.time(); cand = run(ds, open(f"{query_dir}/q2a_candidate_parents.rq").read())
    add_triples(ds, cand)
    der = run(ds, open(f"{query_dir}/q2b_derivation.rq").read()); dt = round(time.time() - t0, 2)
    save(der, f"{out}/q2_derivation_edges.csv")
    def lineage_score(edges):
        par = {e["s"]: e["o"] for e in edges if e["p"].endswith("wasDerivedFrom")}
        gold = gt["parent"]; var = gt["variant"]
        exact = sum(par.get(c) == p for c, p in gold.items())
        branch = sum(c in par and var[par[c]] == var[p] for c, p in gold.items())
        return dict(instances=len(gold), exact_parent=round(exact / len(gold), 3), same_variant_parent=round(branch / len(gold), 3),
                    no_parent_found=sum(c not in par for c in gold))
    R["CQ2.2 lineage (FKG-constrained rule)"] = dict(lineage_score(der), seconds=dt,
        edit_steps=set_prf({e["s"] for e in der if e["p"].endswith("introducesSyntheticRegionFrom")},
                           {x["post"].replace("post_p", "img") for x in gt["patient_zero"]}))
    rows, dt = q("baselines/b2_derivation_timestamp_only.rq"); R["Baseline: lineage by timestamp only"] = dict(lineage_score(rows), seconds=dt)
    gl = gt["laundering_posts"]
    rows, dt = q(f"{query_dir}/q3_laundering.rq"); R["CQ2.3 laundering (integrated)"] = dict(set_prf({r["post"] for r in rows}, gl), seconds=dt)
    rows, dt = q("baselines/b3_laundering_context_only.rq"); R["Baseline: all outlet-crediting posts"] = dict(set_prf({r["post"] for r in rows}, gl), seconds=dt)
    gh = gt["hop_source_platform"]
    def hop_score(rows):
        pred = {}
        for r in rows:
            pred[r["post"]] = "editor_export" if r["hiddenSource"] == "no_platform_match" else r["hiddenSource"].split("platform_")[-1]
        return dict(correct=sum(pred.get(k) == v for k, v in gh.items()), of=len(gh))
    rows, dt = q(f"{query_dir}/q4_hidden_hop.rq"); R["CQ2.4 hidden platform hop (integrated)"] = dict(hop_score(rows), seconds=dt)
    rows, dt = q("baselines/b4_hop_context_only.rq"); R["Baseline: previous post's platform"] = dict(hop_score(rows), seconds=dt)
    json.dump(R, open(f"{out}/summary.json", "w"), indent=1); return R

if __name__ == "__main__":
    for k, v in main(*sys.argv[1:]).items(): print(k, v)
