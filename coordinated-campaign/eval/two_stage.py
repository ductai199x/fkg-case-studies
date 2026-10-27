# Two-stage evaluation of the full query: stage 1 finds images posted by accounts that have any fact-checked false-claim
# post (cheap, selective); stage 2 runs the unchanged TTP join only on those images, bound through VALUES.
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
STAGE1 = """PREFIX as: <https://www.w3.org/ns/activitystreams#>
PREFIX schema: <https://schema.org/>
PREFIX g: <https://example.org/cc/graph/>
SELECT DISTINCT ?img WHERE {
  GRAPH g:factcheck { ?claim schema:appearance ?m . ?review schema:itemReviewed ?claim ; schema:reviewRating ?rating . ?rating schema:ratingValue ?score . FILTER(?score <= 2) }
  GRAPH g:platform { ?m as:attributedTo ?account . ?n as:attributedTo ?account ; as:attachment ?img . }
}"""


def stage2(images):
    full = (ROOT / "queries/full.rq").read_text()
    vals = " ".join(f"<{i}>" for i in sorted(images)) or "<urn:none>"
    anchor = "      GRAPH g:forensics {\n        ?r1 fkg:contained_in ?i1"
    assert full.count(anchor) == 1
    return full.replace(anchor, f"      VALUES ?i1 {{ {vals} }}\n      VALUES ?i2 {{ {vals} }}\n" + anchor)


# Investigation subgraph: the forensic records of the stage-1 images plus the platform, fact-check and provenance graphs;
# the unchanged full query then runs on this much smaller store.
SUBGRAPH = """PREFIX fkg: <https://example.org/fkg#>
PREFIX g: <https://example.org/cc/graph/>
CONSTRUCT { ?s ?p ?o } WHERE { VALUES ?img { %IMGS% } GRAPH g:forensics {
  { ?img fkg:hasRegion ?s . ?s ?p ?o } UNION { ?img fkg:hasRegion ?rg . ?rg ?q ?s . ?s ?p ?o FILTER(?q != fkg:contained_in) }
  UNION { ?img fkg:hasRegion ?rg . ?rg fkg:modified_by ?op . ?op fkg:hasParameter ?s . ?s ?p ?o }
  UNION { BIND(?img AS ?s) ?s ?p ?o } } }"""


def investigation_store(store, ox):
    import time
    t0 = time.time(); imgs = sorted({x["img"].value for x in store.query(STAGE1)})
    sub = ox.Store()
    for g in ("platform", "factcheck", "provenance"):
        G = ox.NamedNode(f"https://example.org/cc/graph/{g}")
        sub.extend(store.quads_for_pattern(None, None, None, G))
    G = ox.NamedNode("https://example.org/cc/graph/forensics")
    for k in range(0, len(imgs), 500):
        vals = " ".join(f"<{i}>" for i in imgs[k:k + 500])
        sub.extend(ox.Quad(t.subject, t.predicate, t.object, G) for t in store.query(SUBGRAPH.replace("%IMGS%", vals)))
    return sub, len(imgs), time.time() - t0
