# The numbers the report and exec summary quote. CS1-CS3 are rerun from the checked-in worlds into a temporary
# directory; CS4 reruns its eta=0 world and checks the stored 5-seed table; agent scores are read from the stored score files.
import json, subprocess, sys
from statistics import mean
import pytest
from conftest import ROOT
import check_queries as cq

def rerun(study, tmp_path):
    out = tmp_path / study; out.mkdir()
    subprocess.run([sys.executable, "run.py", "queries", str(out)], cwd=ROOT / study, check=True, capture_output=True)
    return json.load(open(out / "summary.json"))

def test_cs1_recycled_media(tmp_path):
    s = rerun("cs1_recycled_media", tmp_path)
    assert s["CQ1.3 classification (integrated)"]["accuracy"] == 0.952
    assert s["Baseline: forensic layer only"]["accuracy"] == 0.743
    assert s["Baseline: context layer only"]["accuracy"] == 0.657
    r = s["CQ1.1 recycled out-of-context (integrated)"]; assert (r["precision"], r["recall"]) == (1.0, 0.88)
    e = s["CQ1.2 earliest appearance"]; assert (e["correct"], e["of"]) == (22, 22)
    abl = sorted(v["accuracy"] for k, v in s.items() if k.startswith("Ablation"))
    assert abl == [0.924, 0.943]

def test_cs2_lineage_laundering(tmp_path):
    s = rerun("cs2_lineage_laundering", tmp_path)
    assert s["CQ2.1 patient zero (integrated, corroborated)"]["post"]["precision"] == 0.75
    lin, base = s["CQ2.2 lineage (FKG-constrained rule)"], s["Baseline: lineage by timestamp only"]
    assert (lin["same_variant_parent"], base["same_variant_parent"]) == (1.0, 0.893)
    assert (lin["exact_parent"], base["exact_parent"]) == (0.288, 0.176)
    assert (lin["edit_steps"]["tp"], lin["edit_steps"]["fp"]) == (6, 1)
    assert s["CQ2.3 laundering (integrated)"]["precision"] == 1.0
    assert s["Baseline: all outlet-crediting posts"]["precision"] == 0.137
    assert (s["CQ2.4 hidden platform hop (integrated)"]["correct"], s["Baseline: previous post's platform"]["correct"]) == (50, 15)

def test_cs3_intent_materiality(tmp_path):
    s = rerun("cs3_intent_materiality", tmp_path)
    q = s["CQ3.1 triage queue (integrated)"]; assert (q["precision"], q["recall"]) == (1.0, 0.912)
    assert s["Baseline queue: forensic only"]["precision"] == 0.284
    assert s["Baseline queue: context only"]["precision"] == 0.42
    assert s["Ablation queue: no materiality join"]["precision"] == 0.646
    c = s["CQ3.2 credential contradictions"]; assert (c["tp"], c["fp"]) == (8, 0)
    assert s["CQ3.3 intent rule (integrated)"]["accuracy"] == 0.971
    rows = lambda f: sum(1 for _ in open(tmp_path / "cs3_intent_materiality" / f)) - 1
    assert (rows("q4_anachronism.csv"), rows("q5_retraction_impact.csv")) == (3, 5)

def test_cs4_campaign_eta0_rerun(tmp_path):
    cq.ensure_cs4_worlds()   # generates the eta=0, seed 0 world (deterministic) if missing
    out = tmp_path / "hw.json"
    subprocess.run([sys.executable, "eval/run_eval.py", "--data", str(cq.WORLDS / "data"), "--truth", str(cq.WORLDS / "truth"), "--out", str(out)],
                   cwd=ROOT / "coordinated-campaign", check=True, capture_output=True)
    new = {r["query"]: r["f1"] for r in json.load(open(out))}
    old = {r["query"]: r["f1"] for r in json.load(open(ROOT / "coordinated-campaign/results/handwritten.json")) if r["eta"] == 0.0 and r["seed"] == 0}
    assert new == pytest.approx(old)

def test_cs4_reported_table():
    rows = json.load(open(ROOT / "coordinated-campaign/results/handwritten.json"))
    f1 = lambda q, eta: round(mean(r["f1"] for r in rows if r["query"] == q and r["eta"] == eta), 2)
    assert f1("full+amplifiers", 0.0) == 1.00 and f1("full+amplifiers", 0.7) == 0.97
    assert (f1("full", 0.0), f1("forensic_only", 0.0), f1("context_only", 0.0)) == (0.91, 0.70, 0.40)

def test_agent_scores():
    def means(prefix):
        sets = {}
        for f in sorted((ROOT / "agent_eval").glob(f"{prefix}*.json")): sets.update(json.load(open(f)))
        qs = sorted({q for v in sets.values() for q in v if q.startswith("Q")})
        return {k: round(mean(v.get(q, {}).get("primary", 0) or 0 for q in qs), 3) for k, v in sets.items()}, sets
    held, sets = means("heldout_scores_")
    assert held == {"hand": 0.911, "A1": 0.922, "A2": 0.925, "B1": 0.953, "B2": 0.942, "B1r": 0.964, "B2r": 0.964}
    ep = {k: v["Q2.2"]["detail"]["exact_parent"] for k, v in sets.items()}
    assert (ep["hand"], ep["B1"]) == (0.299, 0.456)
