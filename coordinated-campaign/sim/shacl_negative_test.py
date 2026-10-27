# Negative test: records that break Axioms 2, 3 and 4 must fail validation.
from pathlib import Path
from rdflib import Graph
from pyshacl import validate
root = Path(__file__).resolve().parent.parent
bad = """@prefix fkg: <https://example.org/fkg#> . @prefix ex: <https://example.org/bad#> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:i a fkg:Image ; fkg:hasRegion ex:r . ex:r a fkg:Region ; fkg:contained_in ex:i ; fkg:produced_by ex:s1, ex:s2 ; fkg:depict ex:d ; fkg:modified_by ex:m1, ex:m2 .
ex:s1 a fkg:AIGenerator, fkg:CameraModel ; fkg:hasGeneratorModel "X" ; fkg:hasCameraModel "Y" . ex:s2 a fkg:AIGenerator ; fkg:hasGeneratorModel "Z" .
ex:m1 a fkg:Resampling ; fkg:hasNext ex:m2 . ex:m2 a fkg:GaussianNoise ; fkg:hasNext ex:m1 . ex:d a fkg:Content ."""
ok, _, text = validate(Graph().parse(data=bad, format="turtle"), shacl_graph=Graph().parse(root / "ontology/fkg-shapes.ttl"),
                       ont_graph=Graph().parse(root / "ontology/fkg-core.ttl"), inference="rdfs", advanced=True)
print("conforms", ok); print("\n".join(l for l in text.splitlines() if "Message" in l))
