# Audit every SPARQL query in the repository. For each .rq file (and each rendered .rq.tmpl) it checks that the query
#   1. parses as SPARQL 1.1 (Oxigraph, the engine every study runs on; rdflib as a second parser),
#   2. uses only fkg:/ctx: terms that its study's ontology declares,
#   3. matches only on terms that occur in a generated world or are written by one of the study's rules (CONSTRUCT),
#      and reads only named graphs that a world contains, so no triple pattern is dead on arrival,
#   4. runs on its study's world: hand-written queries must finish; agent queries get a short timeout and a timeout is
#      reported, not failed, since the report already notes that some agent queries are too slow to use.
# It also checks that every catalog entry points to an existing query and lists terms the worlds use but the ontology
# does not declare. Agent-written queries are records of the experiment and are audited, never edited.
# Usage: uv run python scripts/check_queries.py [--no-run] [--no-agents] [--json OUT] [--agent-timeout S]
import argparse, glob, json, multiprocessing as mp, re, sys, time, warnings
from pathlib import Path
import pyoxigraph as ox
import rdflib
from rdflib.plugins.sparql import prepareQuery

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "_shared"))
from sparql_runner import PREFIXES as CS13_PREFIXES  # noqa: E402

NS = dict(fkg="https://example.org/fkg#", ctx="https://example.org/fkg/context#", as_="https://www.w3.org/ns/activitystreams#",
          schema="https://schema.org/", prov="http://www.w3.org/ns/prov#", dcterms="http://purl.org/dc/terms/",
          iptc="http://cv.iptc.org/newscodes/digitalsourcetype/", rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#",
          rdfs="http://www.w3.org/2000/01/rdf-schema#", skos="http://www.w3.org/2004/02/skos/core#")
VOCABS = tuple(NS.values())
OWN = (NS["fkg"], NS["ctx"])   # terms in these namespaces must be declared in the study's ontology
CS4_BASE = "https://example.org/cc/"
CS4_GRAPH_NS = CS4_BASE + "graph/"
CS4_DIR = ROOT / "coordinated-campaign"
WORLDS = ROOT / ".query_check_worlds"   # regenerated CS4 worlds (gitignored)
CS13 = {"cs1": "cs1_recycled_media", "cs2": "cs2_lineage_laundering", "cs3": "cs3_intent_materiality"}

# --- query discovery ------------------------------------------------------------------------------------------
def discover():
    qs = []   # dicts: path, study, kind ("hand" | "agent"), world key
    for key, d in CS13.items():
        for p in sorted(glob.glob(f"{ROOT}/{d}/queries/*.rq") + glob.glob(f"{ROOT}/{d}/baselines/*.rq")):
            qs.append(dict(path=p, study="cs13", kind="hand", world=key))
    cat = json.load(open(ROOT / "_catalog/catalog.json"))
    world_of = {Path(u["sketch"]).name: k for u in cat if u.get("sketch") for k, v in CS13.items() if v == u.get("world")}
    for p in sorted(glob.glob(f"{ROOT}/_catalog/*.rq")):
        qs.append(dict(path=p, study="cs13", kind="hand", world=world_of[Path(p).name]))
    agents = sorted(p.name for p in (ROOT / "agent_eval/agents").iterdir() if p.is_dir())
    for d, kind in [("agent_eval/hand", "hand")] + [(f"agent_eval/agents/{a}", "agent") for a in agents]:
        for p in sorted(glob.glob(f"{ROOT}/{d}/*.rq")):
            qs.append(dict(path=p, study="cs13", kind=kind, world={"Q1": "cs1", "Q2": "cs2", "Q3": "cs3"}[Path(p).name[:2]]))
    for p in sorted(glob.glob(f"{CS4_DIR}/queries/**/*.rq", recursive=True) + glob.glob(f"{CS4_DIR}/queries/**/*.rq.tmpl", recursive=True)):
        qs.append(dict(path=p, study="cs4", kind="hand", world="cs4stress" if "/queries/stress" in p else "cs4"))
    for p in sorted(glob.glob(f"{CS4_DIR}/agent/**/*.rq", recursive=True)):
        qs.append(dict(path=p, study="cs4", kind="agent", world="cs4"))
    return qs

def query_text(q):
    t = open(q["path"]).read()
    if q["path"].endswith(".tmpl"):   # rendered as eval/run_eval.py does, seeded with the campaign core accounts of the world it runs on
        truth = WORLDS / ("stress/truth.json" if q["world"] == "cs4stress" else "truth/eta_0.0/seed_0.json")
        core = json.load(open(truth))["core"]
        iris = [f"<{a}>" for a in sorted(core)]
        t = t.replace("NOT IN (%CORE%)", "NOT IN (" + ", ".join(iris) + ")").replace("%CORE%", " ".join(iris))
        t = t.replace("%A%", iris[0]).replace("%B%", iris[1])
    if q["study"] == "cs13" and not re.search(r"(?im)^\s*PREFIX\s+fkg:", t):
        t = CS13_PREFIXES + t   # sparql_runner.run prepends the same block
    return t

# --- term extraction: which IRIs a query matches on, writes (CONSTRUCT template) or only compares against ----------
def _path_iris(p, out):
    if isinstance(p, rdflib.URIRef): out.add(str(p))
    for attr in ("args", "path"):
        v = getattr(p, attr, None)
        if v is None: continue
        for x in (v if isinstance(v, (list, tuple)) else [v]): _path_iris(x, out)

def _walk(node, pattern, graphs, allx):
    if isinstance(node, rdflib.URIRef): allx.add(str(node)); return
    if isinstance(node, dict):
        if getattr(node, "name", None) == "BGP":
            for tr in node["triples"]:
                for x in tr: _path_iris(x, pattern)
        if getattr(node, "name", None) == "Graph" and isinstance(node.get("term"), rdflib.URIRef): graphs.add(str(node["term"]))
        for v in node.values(): _walk(v, pattern, graphs, allx)
    elif isinstance(node, (list, tuple, set)):
        for v in node: _walk(v, pattern, graphs, allx)
    elif hasattr(node, "args") or hasattr(node, "path"):
        _path_iris(node, pattern)

def terms_of(text):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore"); alg = prepareQuery(text).algebra
    pattern, graphs, allx, template = set(), set(), set(), set()
    for tr in alg.get("template") or []:
        for x in tr:
            if isinstance(x, rdflib.URIRef): template.add(str(x))
    _walk({k: v for k, v in alg.items() if k != "template"}, pattern, graphs, allx)
    return pattern, allx - pattern - graphs, template, graphs

# regex fallback for queries rdflib cannot parse: every prefixed name or IRI counts as a pattern term
TOK = re.compile(r'(?P<iri><[^<>"{}|^`\\\s]*>)|(?P<str>"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\')|(?P<com>#[^\n]*)')
PNAME = re.compile(r"(?<![\w?$:<])([A-Za-z][\w-]*)?:([A-Za-z_][\w-]*(?:\.[\w-]+)*)")
def terms_by_regex(text):
    prefixes = {p or "": iri for p, iri in re.findall(r"(?i)PREFIX\s+([A-Za-z][\w-]*)?:\s*<([^>]*)>", text)}
    text = re.sub(r"(?i)\b(?:PREFIX\s+(?:[A-Za-z][\w-]*)?:|BASE)\s*<[^>]*>", " ", text)
    iris, code, pos = set(), [], 0
    for m in TOK.finditer(text):
        code.append(text[pos:m.start()]); pos = m.end()
        if m.group("iri"): iris.add(m.group("iri")[1:-1])
        code.append(" ")
    code.append(text[pos:])
    for pfx, local in PNAME.findall("".join(code)):
        iris.add(prefixes[pfx] + local if pfx in prefixes else f"UNDECLARED-PREFIX:{pfx}:{local}")
    graphs = {i for i in iris if i.startswith(CS4_GRAPH_NS)}
    return iris - graphs, set(), set(), graphs

# --- ontology and world vocabularies -----------------------------------------------------------------------------
SH = "http://www.w3.org/ns/shacl#"
def declared(paths):
    g = rdflib.Graph()
    for p in paths: g.parse(p, format="turtle")
    return {str(s) for s in g.subjects() if isinstance(s, rdflib.URIRef)}

def shaped(paths):
    g = rdflib.Graph()
    for p in paths: g.parse(p, format="turtle")
    return {str(o) for pr in ("path", "targetClass", "class", "in") for o in g.objects(None, rdflib.URIRef(SH + pr)) if isinstance(o, rdflib.URIRef)}

def load_store(path):
    st = ox.Store(); st.load(path=str(path), format=ox.RdfFormat.N_QUADS if str(path).endswith(".nq") else ox.RdfFormat.TRIG); return st

def world_vocab(paths):
    terms, graphs = set(), set()
    for p in paths:
        for q in load_store(p):
            terms.add(q.predicate.value)
            for t in (q.subject, q.object):
                if isinstance(t, ox.NamedNode): terms.add(t.value)
                elif isinstance(t, ox.Literal): terms.add(t.datatype.value)
            if isinstance(q.graph_name, ox.NamedNode): graphs.add(q.graph_name.value)
    return terms, graphs

def ensure_cs4_worlds():
    import subprocess
    base, ev, stress = WORLDS / "data/eta_0.0/seed_0/dataset.trig", WORLDS / "data_evasive/eta_0.0/seed_0/dataset.trig", WORLDS / "stress/w.nq"
    if not base.exists():
        subprocess.run([sys.executable, "sim/generate.py", "--etas", "0.0", "--seeds", "1", "--out", str(WORLDS / "data"), "--truth", str(WORLDS / "truth")], cwd=CS4_DIR, check=True, capture_output=True)
    if not ev.exists():
        subprocess.run([sys.executable, "sim/generate.py", "--etas", "0.0", "--seeds", "1", "--behavior", "evasive", "--out", str(WORLDS / "data_evasive"), "--truth", str(WORLDS / "truth_evasive")], cwd=CS4_DIR, check=True, capture_output=True)
    if not stress.exists():   # an iteration-5/6 stress world (i5f_base, seed 1) with the entity vocabulary and TTP index graphs on
        stress.parent.mkdir(parents=True, exist_ok=True)
        code = ("import sys, json; sys.path[:0] = ['sim', 'eval']; from stress import StressScenario, make_cfg; from stress_grid import EXPS; "
                "cfg = make_cfg(**{**EXPS['i5f_base'], 'entity_vocab': True, 'ttp_index': True}); "
                f"sc = StressScenario(cfg, 1, 0.0); sc.build_world(); sc.write_nquads('{stress}'); t = sc.truth(); "
                f"json.dump(dict(core=sorted(a for a, r in t['accounts'].items() if r == 'campaign_core')), open('{stress.parent / 'truth.json'}', 'w'))")
        subprocess.run([sys.executable, "-c", code], cwd=CS4_DIR, check=True, capture_output=True)
    return dict(cs4=[base, ev], cs4stress=[stress])

WORLD_FILES = {}
def world_files():
    w = {k: [ROOT / d / "data/world.trig"] for k, d in CS13.items()}
    w.update(ensure_cs4_worlds())
    return w

# --- execution with a timeout ----------------------------------------------------------------------------------
def _run(world, text, stage1, out):
    try:
        st = load_store(WORLD_FILES[world][0])
        if stage1:   # two-stage lineage rule: materialise stage 1 first, as agent_eval/score.py does
            st.extend([ox.Quad(t.subject, t.predicate, t.object, ox.NamedNode("urn:g:derived")) for t in st.query(stage1, use_default_graph_as_union=True)])
        t0 = time.time(); res = st.query(text, use_default_graph_as_union=True)
        n = 1 if isinstance(res, ox.QueryBoolean) else sum(1 for _ in res)
        out.put(dict(rows=n, seconds=round(time.time() - t0, 2)))
    except Exception as e:
        out.put(dict(error=f"{type(e).__name__}: {str(e)[:300]}"))

def run_with_timeout(world, text, timeout, stage1=None):
    ctx = mp.get_context("fork"); out = ctx.Queue(); p = ctx.Process(target=_run, args=(world, text, stage1, out)); p.start(); p.join(timeout)
    if p.is_alive(): p.kill(); p.join(); return dict(timeout=timeout)
    return out.get() if not out.empty() else dict(error="process exited without a result")

# --- the audit ---------------------------------------------------------------------------------------------------
def audit(run=True, hand_timeout=300, agent_timeout=30, run_agents=True):
    global WORLD_FILES
    WORLD_FILES = world_files()
    onto = {"cs13": declared([ROOT / "_shared/fkg-core.ttl", ROOT / "_shared/fkg-context.ttl"]), "cs4": declared([CS4_DIR / "ontology/fkg-core.ttl"])}
    shapes = {"cs13": shaped([ROOT / "_shared/fkg-shapes.ttl"]), "cs4": shaped([CS4_DIR / "ontology/fkg-shapes.ttl"])}
    wv = {k: world_vocab(v) for k, v in WORLD_FILES.items()}
    vocab = {"cs13": set().union(*(wv[k][0] for k in CS13)), "cs4": wv["cs4"][0] | wv["cs4stress"][0]}
    graphs = {"cs13": set().union(*(wv[k][1] for k in CS13)), "cs4": wv["cs4"][1] | wv["cs4stress"][1]}
    queries = discover(); parsed = {}
    for q in queries:
        text = query_text(q)
        try: parsed[q["path"]] = (terms_of(text), None)
        except Exception as e: parsed[q["path"]] = (terms_by_regex(text), f"{type(e).__name__}: {str(e)[:160]}")
    # terms a study's own hand-written rules write (CONSTRUCT templates) are valid inputs for later stages
    derived = {s: set().union(*(parsed[q["path"]][0][2] for q in queries if q["study"] == s and q["kind"] == "hand")) for s in onto}
    rows = []
    for q in queries:
        text = query_text(q); s = q["study"]; rel = str(Path(q["path"]).relative_to(ROOT))
        r = dict(query=rel, study=s, kind=q["kind"], world=q["world"], errors=[], warnings=[], not_in_shapes=[])
        try: ox.Store().query(text)
        except SyntaxError as e: r["errors"].append(f"Oxigraph parse error: {str(e)[:200]}")
        (pattern, constants, template, gs), rdflib_err = parsed[q["path"]]
        if rdflib_err: r["warnings"].append(f"rdflib cannot parse it (Oxigraph, the engine of record, can): {rdflib_err}")
        for g in sorted(gs):
            if g.startswith(CS4_GRAPH_NS) and g not in graphs[s]: r["errors"].append(f"named graph not in any generated world: {g}")
        for t in sorted(pattern | constants | template):
            if t.startswith("UNDECLARED-PREFIX"): r["errors"].append(f"prefix not declared: {t.split(':', 2)[1]}:"); continue
            if not t.startswith(VOCABS): continue
            role = "pattern" if t in pattern else "template" if t in template else "constant"
            if t.startswith(OWN) and t not in onto[s]: r["errors"].append(f"{role} term not declared in the {s} ontology: {t}"); continue
            if role == "pattern" and t not in vocab[s] and t not in derived[s]:
                (r["errors"] if t not in onto[s] else r["warnings"]).append(
                    f"matches on a term no generated world or rule contains (pattern cannot match): {t}")
            elif role == "constant" and t not in vocab[s] and t not in onto[s] and t not in derived[s]:
                r["warnings"].append(f"compares against a value no generated world contains: {t}")
            if t.startswith(OWN) and t not in shapes[s]: r["not_in_shapes"].append(t)
        if run and (run_agents or q["kind"] == "hand") and not any(e.startswith("Oxigraph parse") for e in r["errors"]):
            st1 = Path(q["path"].replace(".rq", ".stage1.rq"))
            stage1 = query_text(dict(q, path=str(st1))) if st1.exists() and not q["path"].endswith(".stage1.rq") else None
            res = run_with_timeout(q["world"], text, hand_timeout if q["kind"] == "hand" else agent_timeout, stage1)
            r.update(res)
            if "error" in res: r["errors"].append(f"execution error: {res['error']}")
            if "timeout" in res and q["kind"] == "hand": r["errors"].append(f"hand-written query exceeded {hand_timeout} s")
        rows.append(r)
    cat = json.load(open(ROOT / "_catalog/catalog.json"))
    catalog_missing = [u["id"] for u in cat if u.get("sketch") and not (ROOT / "_catalog" / u["sketch"]).resolve().exists()]
    data_not_in_onto = {s: sorted(t for t in vocab[s] if t.startswith(OWN) and t not in onto[s]) for s in onto}
    return dict(queries=rows, catalog_missing=catalog_missing, data_terms_not_in_ontology=data_not_in_onto)

def summarize(rep):
    qs = rep["queries"]; by = lambda k: sum(1 for r in qs if r["kind"] == k)
    err = [r for r in qs if r["errors"]]; warn = [r for r in qs if r["warnings"] and not r["errors"]]
    lines = [f"{len(qs)} queries ({by('hand')} hand-written, {by('agent')} agent-written): {len(err)} with errors "
             f"({sum(1 for r in err if r['kind'] == 'hand')} hand-written), {len(warn)} with warnings only",
             f"agent queries over the timeout: {sum(1 for r in qs if 'timeout' in r)}",
             f"catalog entries pointing to a missing query: {rep['catalog_missing'] or 'none'}"]
    for s, ts in rep["data_terms_not_in_ontology"].items(): lines.append(f"{s}: terms the worlds use but the ontology does not declare: {ts or 'none'}")
    for r in err + warn:
        lines.append(f"- {r['query']} ({r['kind']})")
        lines += [f"    ERROR {e}" for e in r["errors"]] + [f"    warn  {w}" for w in r["warnings"]]
    return "\n".join(lines)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--no-run", action="store_true"); ap.add_argument("--json", default=str(ROOT / "results/query_audit.json"))
    ap.add_argument("--agent-timeout", type=int, default=30); ap.add_argument("--no-agents", action="store_true", help="check agent queries statically, do not run them")
    a = ap.parse_args(); rep = audit(run=not a.no_run, agent_timeout=a.agent_timeout, run_agents=not a.no_agents)
    Path(a.json).parent.mkdir(exist_ok=True); json.dump(rep, open(a.json, "w"), indent=1)
    print(summarize(rep))
    sys.exit(1 if any(r["errors"] and r["kind"] == "hand" for r in rep["queries"]) or rep["catalog_missing"] else 0)
