# Load a TriG world into Oxigraph and run SPARQL 1.1 over the union of selected named graphs.
# CLI: uv run python sparql_runner.py WORLD.trig QUERY.rq [--graphs reference,context,fkg] [--limit N]
import sys, csv, argparse, time
import pyoxigraph as ox

PREFIXES = """PREFIX fkg: <https://example.org/fkg#>
PREFIX ctx: <https://example.org/fkg/context#>
PREFIX as: <https://www.w3.org/ns/activitystreams#>
PREFIX schema: <https://schema.org/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX iptc: <http://cv.iptc.org/newscodes/digitalsourcetype/>
"""
ALL = ("reference", "context", "fkg")

def _layer(gname):
    g = gname.value if isinstance(gname, ox.NamedNode) else ""
    return "reference" if g == "urn:g:reference" else "context" if g == "urn:g:context" else "fkg" if g.startswith("urn:g:fkg/") else "derived"

def load(path, layers=ALL):
    full = ox.Store(); full.load(path=path, format=ox.RdfFormat.TRIG)
    if set(layers) >= set(ALL): return full
    st = ox.Store(); st.extend([q for q in full if _layer(q.graph_name) in layers]); return st

def _val(t): return None if t is None else t.value

def run(store, text):
    if "PREFIX fkg:" not in text: text = PREFIXES + text
    res = store.query(text, use_default_graph_as_union=True)
    if isinstance(res, ox.QueryBoolean): return [dict(ask=bool(res))]
    if isinstance(res, ox.QueryTriples): return [dict(s=_val(t.subject), p=_val(t.predicate), o=_val(t.object)) for t in res]
    vars_ = [v.value for v in res.variables]
    return [{v: _val(sol[v]) for v in vars_} for sol in res]

def add_triples(store, rows, graph="urn:g:derived"):
    g = ox.NamedNode(graph)
    def term(x): return ox.NamedNode(x) if x.startswith(("http", "urn:")) else ox.Literal(x)
    store.extend([ox.Quad(ox.NamedNode(r["s"]), ox.NamedNode(r["p"]), term(r["o"]), g) for r in rows])

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("world"); ap.add_argument("query")
    ap.add_argument("--graphs", default=",".join(ALL)); ap.add_argument("--limit", type=int, default=50)
    a = ap.parse_args(); t0 = time.time()
    st = load(a.world, tuple(a.graphs.split(","))); rows = run(st, open(a.query).read())
    print(f"# {len(rows)} rows ({time.time()-t0:.1f}s)")
    if rows:
        w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys())); w.writeheader()
        for r in rows[: a.limit]: w.writerow(r)
