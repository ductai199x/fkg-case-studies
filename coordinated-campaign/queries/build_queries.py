# Writes the hand-written SPARQL detection queries (full method + ablations) to queries/*.rq.
from pathlib import Path

PREFIXES = """PREFIX fkg:    <https://example.org/fkg#>
PREFIX as:     <https://www.w3.org/ns/activitystreams#>
PREFIX schema: <https://schema.org/>
PREFIX prov:   <http://www.w3.org/ns/prov#>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
PREFIX g:      <https://example.org/cc/graph/>
"""
POSTS_WITH_IMAGES = """  GRAPH g:platform {
    ?n1 as:attributedTo ?account ; as:published ?t1 ; as:attachment ?i1 .
    ?n2 as:attributedTo ?peer    ; as:published ?t2 ; as:attachment ?i2 .
  }
  FILTER(?account != ?peer)"""
POSTS_ANY = """  GRAPH g:platform {
    ?n1 as:attributedTo ?account ; as:published ?t1 .
    ?n2 as:attributedTo ?peer    ; as:published ?t2 .
  }
  FILTER(?account != ?peer)"""
# Forensic TTP match: synthetic regions with the same attributed generator and >= 2 processing operations of the same
# type whose estimated parameters agree within 15 %.
TTP = """  { SELECT ?i1 ?i2 WHERE {
      GRAPH g:forensics {
        ?r1 fkg:contained_in ?i1 ; fkg:produced_by ?s1 . ?s1 a fkg:AIGenerator ; fkg:hasGeneratorModel ?gen .
        ?r2 fkg:contained_in ?i2 ; fkg:produced_by ?s2 . ?s2 a fkg:AIGenerator ; fkg:hasGeneratorModel ?gen .
        FILTER(?i1 != ?i2)
        ?r1 fkg:modified_by ?o1 . ?o1 a ?op ; fkg:hasParameter ?p1 . ?p1 fkg:hasParameterName ?pn ; fkg:hasParameterValue ?v1 .
        ?r2 fkg:modified_by ?o2 . ?o2 a ?op ; fkg:hasParameter ?p2 . ?p2 fkg:hasParameterName ?pn ; fkg:hasParameterValue ?v2 .
        FILTER(ABS(?v1 - ?v2) <= 0.15 * ?v1)
      } } GROUP BY ?i1 ?i2 HAVING (COUNT(DISTINCT ?op) >= 2) }"""
# Exclude re-uploads: images that provenance analysis derives from another image are copies, not new productions.
PROVENANCE = """  FILTER NOT EXISTS { GRAPH g:provenance { ?i1 prov:wasDerivedFrom ?src1 } }
  FILTER NOT EXISTS { GRAPH g:provenance { ?i2 prov:wasDerivedFrom ?src2 } }"""
WINDOW = """  FILTER(?t2 - ?t1 <= "PT72H"^^xsd:dayTimeDuration && ?t1 - ?t2 <= "PT72H"^^xsd:dayTimeDuration)"""
# Shared narrative: both accounts posted appearances of the same claim that a fact-check rated false (<= 2 of 5).
NARRATIVE = """  GRAPH g:platform { ?m1 as:attributedTo ?account . ?m2 as:attributedTo ?peer . }
  GRAPH g:factcheck {
    ?claim schema:appearance ?m1 , ?m2 .
    ?review schema:itemReviewed ?claim ; schema:reviewRating ?rating . ?rating schema:ratingValue ?score .
    FILTER(?score <= 2)
  }"""
NARRATIVE_ON_POSTS = NARRATIVE.replace("?m1 as:attributedTo ?account . ?m2 as:attributedTo ?peer .", "").replace("?m1 , ?m2", "?n1 , ?n2")


def account_query(name, comment, blocks, min_peers=2):
    body = "\n".join(blocks)
    return f"""# {name}: {comment}
{PREFIXES}
SELECT ?account (COUNT(DISTINCT ?peer) AS ?peers) WHERE {{
  {{ SELECT DISTINCT ?account ?peer WHERE {{
{body}
  }} }}
}}
GROUP BY ?account
HAVING (COUNT(DISTINCT ?peer) >= {min_peers})
ORDER BY DESC(?peers)
"""


QUERIES = {
    "full": ("forensic TTP match + 72 h window + shared fact-checked false claim, excluding re-uploads", [POSTS_WITH_IMAGES, TTP, PROVENANCE, WINDOW, NARRATIVE]),
    "forensic_only": ("forensic TTP match only (with re-upload exclusion)", [POSTS_WITH_IMAGES, TTP, PROVENANCE]),
    "forensic_time": ("forensic TTP match + 72 h window, no claim records", [POSTS_WITH_IMAGES, TTP, PROVENANCE, WINDOW]),
    "context_only": ("shared fact-checked false claim posted within 72 h, no forensic records", [POSTS_ANY, WINDOW, NARRATIVE_ON_POSTS]),
    "full_no_provenance": ("full query without the provenance (re-upload) exclusion", [POSTS_WITH_IMAGES, TTP, WINDOW, NARRATIVE]),
}

# Second hop: unflagged accounts that repost content of >= 2 distinct flagged accounts, post fact-checked false claims,
# and were created within 7 days of a flagged account (account-creation burst).
AMPLIFIERS = f"""# amplifiers: second hop from the accounts flagged by the full query (bound through VALUES ?core)
{PREFIXES}
SELECT ?account (COUNT(DISTINCT ?core) AS ?amplified) WHERE {{
  VALUES ?core {{ %CORE% }}
  GRAPH g:platform {{
    ?ann a as:Announce ; as:actor ?account ; as:object ?note .
    ?note as:attributedTo ?core .
    ?own as:attributedTo ?account .
    ?account as:published ?created . ?burstPeer as:published ?peerCreated .
  }}
  VALUES ?burstPeer {{ %CORE% }}
  FILTER(?account NOT IN (%CORE%))
  FILTER(?created - ?peerCreated <= "P7D"^^xsd:dayTimeDuration && ?peerCreated - ?created <= "P7D"^^xsd:dayTimeDuration)
  GRAPH g:factcheck {{
    ?claim schema:appearance ?own .
    ?review schema:itemReviewed ?claim ; schema:reviewRating ?rating . ?rating schema:ratingValue ?score . FILTER(?score <= 2)
  }}
}}
GROUP BY ?account
HAVING (COUNT(DISTINCT ?core) >= 2)
"""

# Explanation: the shared evidence behind one flagged pair, for the paper's listing.
EXPLAIN = f"""# explain: forensic, temporal and narrative evidence shared by two accounts
{PREFIXES}
SELECT ?gen ?op ?pn ?v1 ?v2 ?t1 ?t2 ?claimText WHERE {{
  VALUES (?account ?peer) {{ (%A% %B%) }}
{POSTS_WITH_IMAGES}
  GRAPH g:forensics {{
    ?r1 fkg:contained_in ?i1 ; fkg:produced_by ?s1 . ?s1 a fkg:AIGenerator ; fkg:hasGeneratorModel ?gen .
    ?r2 fkg:contained_in ?i2 ; fkg:produced_by ?s2 . ?s2 a fkg:AIGenerator ; fkg:hasGeneratorModel ?gen .
    ?r1 fkg:modified_by ?o1 . ?o1 a ?op ; fkg:hasParameter ?p1 . ?p1 fkg:hasParameterName ?pn ; fkg:hasParameterValue ?v1 .
    ?r2 fkg:modified_by ?o2 . ?o2 a ?op ; fkg:hasParameter ?p2 . ?p2 fkg:hasParameterName ?pn ; fkg:hasParameterValue ?v2 .
    FILTER(ABS(?v1 - ?v2) <= 0.15 * ?v1)
  }}
{WINDOW}
  GRAPH g:factcheck {{ ?claim schema:appearance ?n1 ; schema:text ?claimText . }}
}} LIMIT 12
"""

if __name__ == "__main__":
    d = Path(__file__).resolve().parent
    for k, (c, b) in QUERIES.items():
        (d / f"{k}.rq").write_text(account_query(k, c, b))
    (d / "amplifiers.rq.tmpl").write_text(AMPLIFIERS); (d / "explain.rq.tmpl").write_text(EXPLAIN)
    print("wrote", sorted(p.name for p in d.glob("*.rq*")))
