# Score SELECT answers (hand-written or agent-written) for Q1.1..Q3.5 against the planted ground truth.
# Usage: uv run python score.py ANSWER_DIR [ANSWER_DIR ...]   (ANSWER_DIR holds Q*.rq; "hand" = the hand-written queries)
import json, sys, os, time, csv
sys.path.insert(0, "../_shared")
from sparql_runner import load, run, add_triples
from metrics import set_prf, classify_report
BASE = os.path.dirname(os.path.abspath(__file__)) + "/.."
DATA = os.environ.get("EVAL_DATA", "data")   # "heldout" = fresh-seed worlds no agent saw
W = {c: load(f"{BASE}/{d}/{DATA}/world.trig") for c, d in [("cs1", "cs1_recycled_media"), ("cs2", "cs2_lineage_laundering"), ("cs3", "cs3_intent_materiality")]}
GT = {c: json.load(open(f"{BASE}/{d}/{DATA}/ground_truth.json")) for c, d in [("cs1", "cs1_recycled_media"), ("cs2", "cs2_lineage_laundering"), ("cs3", "cs3_intent_materiality")]}
loc = lambda x: (x or "").split("#")[-1].split("/")[-1]

def s11(r):
    g = GT["cs1"]["claim_posts"]; return dict(primary=set_prf({x["post"] for x in r}, [k for k, v in g.items() if v == "recycled_ooc"])["f1"], detail=set_prf({x["post"] for x in r}, [k for k, v in g.items() if v == "recycled_ooc"]))
def s12(r):
    gold = {(k, v) for k, v in GT["cs1"]["earliest_appearance"].items() if v}; d = set_prf({(x["post"], x["earliestPost"]) for x in r}, gold); return dict(primary=d["f1"], detail=d)
def s13(r):
    g = {k: ("no_problem_found" if v in ("authentic_current", "archival_ok") else v) for k, v in GT["cs1"]["claim_posts"].items()}
    d = classify_report({x["post"]: x["label"] for x in r}, g, ["synthetic", "manipulated", "recycled_ooc", "no_problem_found"]); return dict(primary=d["macro_f1"], detail={k: d[k] for k in ("accuracy", "macro_f1")})
def s21(r):
    gold = {(f"https://example.org/fkg/cs2#cluster_{x['cluster']}", x["post"]) for x in GT["cs2"]["patient_zero"]}; d = set_prf({(x["cluster"], x["post"]) for x in r}, gold); return dict(primary=d["f1"], detail=d)
def s22(r):
    par = {x["child"]: x["parent"] for x in r}; g = GT["cs2"]; gold = g["parent"]
    exact = sum(par.get(c) == p for c, p in gold.items()) / len(gold)
    branch = sum(c in par and par[c] in g["variant"] and g["variant"][par[c]] == g["variant"][p] for c, p in gold.items()) / len(gold)
    return dict(primary=round(branch, 3), detail=dict(same_variant_parent=round(branch, 3), exact_parent=round(exact, 3), rows=len(r)))
def s23(r):
    d = set_prf({x["post"] for x in r}, GT["cs2"]["laundering_posts"]); return dict(primary=d["f1"], detail=d)
def s24(r):
    gh = GT["cs2"]["hop_source_platform"]; pred = {}
    for x in r:
        v = loc(x["hiddenSource"]).replace("platform_", ""); pred[x["post"]] = "editor_export" if "no_platform_match" in (x["hiddenSource"] or "") else v
    acc = sum(pred.get(k) == v for k, v in gh.items()) / len(gh); return dict(primary=round(acc, 3), detail=dict(correct=round(acc * len(gh)), of=len(gh)))
def s31(r):
    gold = [k for k, v in GT["cs3"]["intent"].items() if v == "UndisclosedMaterialAlteration"]; ranked = list(dict.fromkeys(x["post"] for x in r))
    d = set_prf(ranked, gold); d["p_at_10"] = sum(p in gold for p in ranked[:10]) / 10; return dict(primary=d["f1"], detail=d)
def s32(r):
    d = set_prf({x["post"] for x in r}, GT["cs3"]["credential_contradiction"]); return dict(primary=d["f1"], detail=d)
def s33(r):
    d = classify_report({x["post"]: loc(x["category"]) for x in r}, GT["cs3"]["intent"], ["NoAlteration", "UndisclosedMaterialAlteration", "UndisclosedPeripheralAlteration", "DisclosedSynthetic", "SatireOrArt"])
    return dict(primary=d["macro_f1"], detail={k: d[k] for k in ("accuracy", "macro_f1")})
def s34(r):
    d = set_prf({x["post"] for x in r}, GT["cs3"]["anachronism"]); return dict(primary=d["f1"], detail=d)
def s35(r):
    d = set_prf({x["review"] for x in r}, GT["cs3"]["affected_reviews"]); return dict(primary=d["f1"], detail=d)
Q = {"Q1.1": ("cs1", s11), "Q1.2": ("cs1", s12), "Q1.3": ("cs1", s13), "Q2.1": ("cs2", s21), "Q2.2": ("cs2", s22), "Q2.3": ("cs2", s23),
     "Q2.4": ("cs2", s24), "Q3.1": ("cs3", s31), "Q3.2": ("cs3", s32), "Q3.3": ("cs3", s33), "Q3.4": ("cs3", s34), "Q3.5": ("cs3", s35)}

TIMEOUT = int(os.environ.get("SCORE_TIMEOUT", 600))   # per query, seconds; a query that runs longer scores 0
def score_one(d, qid, case, f, q):
        p = f"{d}/{qid}.rq"
        try:
            t0 = time.time(); st = W[case]
            if os.path.exists(f"{d}/{qid}.stage1.rq"):          # two-stage rule: materialize stage 1 into a fresh store
                st = load(f"{BASE}/cs2_lineage_laundering/{DATA}/world.trig"); add_triples(st, run(st, open(f"{d}/{qid}.stage1.rq").read()))
            rows = run(st, open(p).read()); q.put(dict(f(rows), seconds=round(time.time() - t0, 2)))
        except Exception as e:
            q.put(dict(primary=0.0, error=f"{type(e).__name__}: {str(e)[:200]}"))
def score_dir(d):
    import multiprocessing as mp; out = {}
    for qid, (case, f) in Q.items():
        if not os.path.exists(f"{d}/{qid}.rq"): out[qid] = dict(primary=0.0, error="missing"); continue
        q = mp.Queue(); pr = mp.Process(target=score_one, args=(d, qid, case, f, q)); pr.start()
        try: out[qid] = q.get(timeout=TIMEOUT)
        except Exception: out[qid] = dict(primary=0.0, error=f"timeout after {TIMEOUT}s")
        pr.join(5); pr.kill() if pr.is_alive() else None
        print(d, qid, out[qid].get("primary"), out[qid].get("seconds", out[qid].get("error")), flush=True)
    return out

if __name__ == "__main__":
    res = {os.path.basename(os.path.normpath(d)): score_dir(d) for d in sys.argv[1:]}
    allres = json.load(open(os.environ.get("SCORES_OUT", "scores.json"))) if os.path.exists(os.environ.get("SCORES_OUT", "scores.json")) else {}
    allres.update(res); json.dump(allres, open(os.environ.get("SCORES_OUT", "scores.json"), "w"), indent=1)
    names = list(res); print("Q     " + "  ".join(f"{n:>8}" for n in names))
    for qid in Q: print(f"{qid:5} " + "  ".join(f"{res[n][qid]['primary']:>8.3f}" for n in names))
    for n in names:
        errs = {q: v["error"] for q, v in res[n].items() if "error" in v}
        if errs: print(n, "errors:", errs)
