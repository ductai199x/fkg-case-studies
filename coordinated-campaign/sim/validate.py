# SHACL-validate the forensics named graph of a dataset against the FKG shapes (+ ontology for class inference).
import sys
from pathlib import Path
from rdflib import Dataset, Graph, URIRef
from pyshacl import validate
root = Path(__file__).resolve().parent.parent
ds = Dataset(); ds.parse(sys.argv[1], format="trig")
data = Graph()
for t in ds.graph(URIRef("https://example.org/cc/graph/forensics")): data.add(t)
ont = Graph().parse(root / "ontology/fkg-core.ttl"); shapes = Graph().parse(root / "ontology/fkg-shapes.ttl")
conforms, _, text = validate(data, shacl_graph=shapes, ont_graph=ont, inference="rdfs", advanced=True)
print("triples", len(data), "conforms", conforms)
if not conforms: print(text[:3000])
