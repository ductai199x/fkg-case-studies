# SHACL-validate each case world (union of named graphs), plus CS3's materialized intent assessments.
import sys, glob, json
from rdflib import Dataset, Graph
from pyshacl import validate
sys.path.insert(0, ".")
from sparql_runner import load, run
shapes = Graph().parse("fkg-shapes.ttl")
out = {}
for w in sorted(glob.glob("../cs*/data/world.trig")):
    ds = Dataset(); ds.parse(w, format="trig"); g = Graph()
    for q in ds.quads((None, None, None, None)): g.add(q[:3])
    if "cs3" in w:
        st = load(w)
        for t in run(st, open("../cs3_intent_materiality/queries/q3_intent_rule.rq").read()):
            from rdflib import URIRef, Literal
            o = URIRef(t["o"]) if t["o"].startswith(("http", "urn:")) else Literal(t["o"]); g.add((URIRef(t["s"]), URIRef(t["p"]), o))
    conforms, _, text = validate(g, shacl_graph=shapes, inference="none")
    out[w] = dict(triples=len(g), conforms=conforms, violations=text.count("Constraint Violation"))
    print(w, out[w])
json.dump(out, open("shacl_report.json", "w"), indent=1)
