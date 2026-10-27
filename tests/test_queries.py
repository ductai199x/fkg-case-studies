# Every query the study names exists, parses, uses declared terms that some world contains, and (hand-written) runs.
# The full run with agent queries is `uv run python scripts/check_queries.py`; here agent queries are checked statically.
import glob, json
import pytest
from conftest import ROOT
import check_queries as cq

CS4 = ROOT / "coordinated-campaign"

@pytest.fixture(scope="module")
def report():
    return cq.audit(run=True, run_agents=False)

def test_no_errors_in_any_query(report):
    bad = {r["query"]: r["errors"] for r in report["queries"] if r["errors"]}
    assert not bad, json.dumps(bad, indent=1)

def test_every_hand_written_query_ran(report):
    assert not [r["query"] for r in report["queries"] if r["kind"] == "hand" and "rows" not in r]

def test_worlds_use_only_declared_terms(report):
    assert report["data_terms_not_in_ontology"] == {"cs13": [], "cs4": []}

def test_catalog_sketches_exist(report):
    assert report["catalog_missing"] == []
    cat = json.load(open(ROOT / "_catalog/catalog.json"))
    assert [u["id"] for u in cat] == [f"UC{i}" for i in range(1, 19)]
    for u in cat:
        if u.get("sketch"): assert (ROOT / "_catalog" / u["sketch"]).resolve().is_file(), u["id"]

def test_agent_questions_have_reference_queries():
    ids = [q["id"] for q in json.load(open(ROOT / "agent_eval/questions.json"))]
    assert len(ids) == 12
    for d in ["agent_eval/hand"] + sorted(glob.glob(str(ROOT / "agent_eval/agents/*"))):
        for i in ids: assert (ROOT / d / f"{i}.rq").is_file(), f"{d}/{i}.rq"

def test_cs4_reported_query_names_resolve():
    stems = {p.split("/")[-1].removesuffix(".rq") for p in glob.glob(f"{CS4}/queries/**/*.rq", recursive=True)}
    stems |= {f"agent_eta{e}" for e in ("0.0", "0.2", "0.4")} | {"corepost"}   # agent queries; corepost is the behavioural baseline
    names = set()
    for f in glob.glob(f"{CS4}/results/*.json") + glob.glob(f"{CS4}/results/**/*.jsonl", recursive=True):
        rows = json.load(open(f)) if f.endswith(".json") else [json.loads(l) for l in open(f)]
        if isinstance(rows, list): names |= {r["query"] for r in rows if isinstance(r, dict) and "query" in r}
    assert names
    for n in names:   # seeded second hops are reported as <detector>+amp / +amplifiers
        base = n.split("+")[0]
        assert base in stems or (n.startswith("agent_") and "eta" in n), n
        if "+" in n: assert n.split("+")[1] in ("amp", "amplifiers"), n

def test_uc13_recipe_is_order_independent_of_aggregation():
    # GROUP_CONCAT order is undefined in SPARQL 1.1; UC13 must give one recipe string per pipeline
    from sparql_runner import load, run
    q = open(ROOT / "_catalog/uc13_toolkit_fingerprint.rq").read()
    inner = q[q.index("{ SELECT ?region") + 2:q.index("GROUP BY ?region }") + len("GROUP BY ?region")]
    recipes = {r["recipe"] for r in run(load(str(ROOT / "cs3_intent_materiality/data/world.trig")), inner)}
    assert recipes == {"Sharpening(percent=40) > Resampling(scaleFactor=0.5)"}
