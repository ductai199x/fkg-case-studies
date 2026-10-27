# Defender variants for the stress tests: relaxations of the full query's forensic TTP block (queries/stress/*.rq).
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_queries import POSTS_WITH_IMAGES, PROVENANCE, WINDOW, NARRATIVE, account_query

# same generator on both synthetic regions, processing ignored
GEN_ONLY = """  { SELECT DISTINCT ?i1 ?i2 WHERE {
      GRAPH g:forensics {
        ?r1 fkg:contained_in ?i1 ; fkg:produced_by ?s1 . ?s1 a fkg:AIGenerator ; fkg:hasGeneratorModel ?gen .
        ?r2 fkg:contained_in ?i2 ; fkg:produced_by ?s2 . ?s2 a fkg:AIGenerator ; fkg:hasGeneratorModel ?gen .
        FILTER(?i1 != ?i2) } } }"""
# >= 2 matching processing operations on synthetic regions of any generator
OPS_ANY_GEN = """  { SELECT ?i1 ?i2 WHERE {
      GRAPH g:forensics {
        ?r1 fkg:contained_in ?i1 ; fkg:produced_by ?s1 . ?s1 a fkg:AIGenerator .
        ?r2 fkg:contained_in ?i2 ; fkg:produced_by ?s2 . ?s2 a fkg:AIGenerator .
        FILTER(?i1 != ?i2)
        ?r1 fkg:modified_by ?o1 . ?o1 a ?op ; fkg:hasParameter ?p1 . ?p1 fkg:hasParameterName ?pn ; fkg:hasParameterValue ?v1 .
        ?r2 fkg:modified_by ?o2 . ?o2 a ?op ; fkg:hasParameter ?p2 . ?p2 fkg:hasParameterName ?pn ; fkg:hasParameterValue ?v2 .
        FILTER(ABS(?v1 - ?v2) <= 0.15 * ?v1)
      } } GROUP BY ?i1 ?i2 HAVING (COUNT(DISTINCT ?op) >= 2) }"""
# full TTP match, with generator labels resolved to one entity through the vocabulary graph (handles naming drift)
TTP_ENTITY = """  { SELECT ?i1 ?i2 WHERE {
      GRAPH g:forensics {
        ?r1 fkg:contained_in ?i1 ; fkg:produced_by ?s1 . ?s1 a fkg:AIGenerator ; fkg:hasGeneratorModel ?l1 .
        ?r2 fkg:contained_in ?i2 ; fkg:produced_by ?s2 . ?s2 a fkg:AIGenerator ; fkg:hasGeneratorModel ?l2 .
        FILTER(?i1 != ?i2) }
      GRAPH g:vocab { ?gen skos:altLabel ?l1 , ?l2 . }
      GRAPH g:forensics {
        ?r1 fkg:modified_by ?o1 . ?o1 a ?op ; fkg:hasParameter ?p1 . ?p1 fkg:hasParameterName ?pn ; fkg:hasParameterValue ?v1 .
        ?r2 fkg:modified_by ?o2 . ?o2 a ?op ; fkg:hasParameter ?p2 . ?p2 fkg:hasParameterName ?pn ; fkg:hasParameterValue ?v2 .
        FILTER(ABS(?v1 - ?v2) <= 0.15 * ?v1)
      } } GROUP BY ?i1 ?i2 HAVING (COUNT(DISTINCT ?op) >= 2) }"""
from build_queries import TTP, PREFIXES
# Self-consistent pipeline: an account whose own images (>= 2, not re-uploads) share a generator and processing (TTP match);
# defends against attackers that give every persona its own preset, at the price of needing >= 2 images per account.
def self_consistent(var):
    return ("  { SELECT DISTINCT ?%s WHERE {\n    GRAPH g:platform { ?sa as:attributedTo ?%s ; as:attachment ?i1 . ?sb as:attributedTo ?%s ; as:attachment ?i2 . }\n" % (var, var, var)
            + TTP.replace("\n", "\n  ") + "\n" + PROVENANCE + "\n  } }")
SELF_CONSISTENT = f"""# full_self_consistent: accounts with an internally consistent generation+processing pipeline that share a fact-checked false claim within 72 h with >= 2 such accounts
{PREFIXES}
SELECT ?account (COUNT(DISTINCT ?peer) AS ?peers) WHERE {{
  {{ SELECT DISTINCT ?account ?peer WHERE {{
{self_consistent("account")}
{self_consistent("peer")}
  GRAPH g:platform {{ ?m1 as:attributedTo ?account ; as:published ?t1 . ?m2 as:attributedTo ?peer ; as:published ?t2 . }}
  FILTER(?account != ?peer)
{WINDOW}
  GRAPH g:factcheck {{
    ?claim schema:appearance ?m1 , ?m2 .
    ?review schema:itemReviewed ?claim ; schema:reviewRating ?rating . ?rating schema:ratingValue ?score . FILTER(?score <= 2)
  }}
  }} }}
}}
GROUP BY ?account
HAVING (COUNT(DISTINCT ?peer) >= 2)
"""
# both images synthetic (any generator) and each carries >= 2 estimated processing operations; no parameter match
HEAVY_PROC = """  { SELECT DISTINCT ?i1 ?i2 WHERE {
      { SELECT ?i1 WHERE { GRAPH g:forensics { ?r1 fkg:contained_in ?i1 ; fkg:produced_by ?s1 ; fkg:modified_by ?o1 . ?s1 a fkg:AIGenerator . ?o1 a ?t1 . FILTER(?t1 != fkg:NoPostProc) } }
        GROUP BY ?i1 HAVING (COUNT(DISTINCT ?o1) >= 2) }
      { SELECT ?i2 WHERE { GRAPH g:forensics { ?r2 fkg:contained_in ?i2 ; fkg:produced_by ?s2 ; fkg:modified_by ?o2 . ?s2 a fkg:AIGenerator . ?o2 a ?t2 . FILTER(?t2 != fkg:NoPostProc) } }
        GROUP BY ?i2 HAVING (COUNT(DISTINCT ?o2) >= 2) }
      FILTER(?i1 != ?i2) } }"""
# TTP match through the derived index graph: hash join on generator|op|bin keys, then the exact 15 % check
TTP_INDEXED = """  { SELECT ?i1 ?i2 WHERE {
      { SELECT DISTINCT ?p1 ?p2 WHERE { GRAPH g:index { ?p1 idx:ttpKey ?key . ?p2 idx:ttpNear ?key . } FILTER(?p1 != ?p2) } }
      GRAPH g:forensics {
        ?o1 fkg:hasParameter ?p1 ; a ?op . ?o2 fkg:hasParameter ?p2 ; a ?op .
        ?p1 fkg:hasParameterValue ?v1 . ?p2 fkg:hasParameterValue ?v2 .
        FILTER(ABS(?v1 - ?v2) <= 0.15 * ?v1)
        ?r1 fkg:modified_by ?o1 ; fkg:contained_in ?i1 . ?r2 fkg:modified_by ?o2 ; fkg:contained_in ?i2 .
        FILTER(?i1 != ?i2)
      } } GROUP BY ?i1 ?i2 HAVING (COUNT(DISTINCT ?op) >= 2) }"""
# Same semantics as full, evaluated from the most selective evidence: account pairs that share a fact-checked false
# claim first, then their image posts in the window, then the forensic TTP check on just those image pairs.
CLAIM_FIRST = f"""# full_claim_first: full query reordered to start from shared false claims (same result, lower cost)
{PREFIXES}
SELECT ?account (COUNT(DISTINCT ?peer) AS ?peers) WHERE {{
  {{ SELECT DISTINCT ?account ?peer WHERE {{
    {{ SELECT ?account ?peer ?i1 ?i2 WHERE {{
        {{ SELECT DISTINCT ?account ?peer WHERE {{
{NARRATIVE}
          FILTER(?account != ?peer) }} }}
        GRAPH g:platform {{ ?n1 as:attributedTo ?account ; as:published ?t1 ; as:attachment ?i1 . ?n2 as:attributedTo ?peer ; as:published ?t2 ; as:attachment ?i2 . }}
{WINDOW}
        GRAPH g:forensics {{
          ?r1 fkg:contained_in ?i1 ; fkg:produced_by ?s1 . ?s1 a fkg:AIGenerator ; fkg:hasGeneratorModel ?gen .
          ?r2 fkg:contained_in ?i2 ; fkg:produced_by ?s2 . ?s2 a fkg:AIGenerator ; fkg:hasGeneratorModel ?gen .
          FILTER(?i1 != ?i2)
          ?r1 fkg:modified_by ?o1 . ?o1 a ?op ; fkg:hasParameter ?p1 . ?p1 fkg:hasParameterName ?pn ; fkg:hasParameterValue ?v1 .
          ?r2 fkg:modified_by ?o2 . ?o2 a ?op ; fkg:hasParameter ?p2 . ?p2 fkg:hasParameterName ?pn ; fkg:hasParameterValue ?v2 .
          FILTER(ABS(?v1 - ?v2) <= 0.15 * ?v1)
        }}
    }} GROUP BY ?account ?peer ?i1 ?i2 HAVING (COUNT(DISTINCT ?op) >= 2) }}
{PROVENANCE}
  }} }}
}}
GROUP BY ?account
HAVING (COUNT(DISTINCT ?peer) >= 2)
"""
# Open-world narrative: the shared claim must not be rated true, but it need not have a published fact-check yet
NARRATIVE_OPEN = """  GRAPH g:platform { ?m1 as:attributedTo ?account . ?m2 as:attributedTo ?peer . }
  GRAPH g:factcheck {
    ?claim schema:appearance ?m1 , ?m2 .
    FILTER NOT EXISTS { ?review schema:itemReviewed ?claim ; schema:reviewRating ?rating . ?rating schema:ratingValue ?score . FILTER(?score >= 3) }
  }"""
NARRATIVE_OPEN_STANCE = NARRATIVE_OPEN.replace("  }", """    FILTER NOT EXISTS { ?m1 cc:stance cc:Refutes } FILTER NOT EXISTS { ?m2 cc:stance cc:Refutes }
  }""")
TTP1 = TTP.replace("COUNT(DISTINCT ?op) >= 2", "COUNT(DISTINCT ?op) >= 1")
def self_consistent_1(var):  # own images share a generator and >= 1 matching operation
    return self_consistent(var).replace("COUNT(DISTINCT ?op) >= 2", "COUNT(DISTINCT ?op) >= 1")
SC_OPEN_1 = f"""# sc_open_one_op: self-consistent pipeline (>= 1 matching op among an account's own images) + shared unrefuted claim within 72 h with >= 2 such accounts
{PREFIXES}
SELECT ?account (COUNT(DISTINCT ?peer) AS ?peers) WHERE {{
  {{ SELECT DISTINCT ?account ?peer WHERE {{
{self_consistent_1("account")}
{self_consistent_1("peer")}
  GRAPH g:platform {{ ?m1 as:attributedTo ?account ; as:published ?t1 . ?m2 as:attributedTo ?peer ; as:published ?t2 . }}
  FILTER(?account != ?peer)
{WINDOW}
{NARRATIVE_OPEN.replace("  GRAPH g:platform { ?m1 as:attributedTo ?account . ?m2 as:attributedTo ?peer . }", "")}
  }} }}
}}
GROUP BY ?account
HAVING (COUNT(DISTINCT ?peer) >= 2)
"""

# Iteration 6: evidence that survives per-persona processing and aged accounts. Mutual reposting between two accounts
# (each reposted the other) that both post synthetic images carrying the same unrefuted, not-rated-true claim within
# 72 h; no cross-account parameter match and no account-age condition.
MUTUAL_BLOCK = """  GRAPH g:platform {
    ?x a as:Announce ; as:actor ?account ; as:object ?pnote . ?pnote as:attributedTo ?peer .
    ?y a as:Announce ; as:actor ?peer ; as:object ?anote . ?anote as:attributedTo ?account .
    ?n1 as:attributedTo ?account ; as:published ?t1 ; as:attachment ?i1 .
    ?n2 as:attributedTo ?peer ; as:published ?t2 ; as:attachment ?i2 .
  }
  FILTER(?account != ?peer)
  GRAPH g:forensics { ?r1 fkg:contained_in ?i1 ; fkg:produced_by ?s1 . ?s1 a fkg:AIGenerator . ?r2 fkg:contained_in ?i2 ; fkg:produced_by ?s2 . ?s2 a fkg:AIGenerator . }"""
CLAIM_ON_POSTS_OPEN_STANCE = """  GRAPH g:factcheck {
    ?claim schema:appearance ?n1 , ?n2 .
    FILTER NOT EXISTS { ?review schema:itemReviewed ?claim ; schema:reviewRating ?rating . ?rating schema:ratingValue ?score . FILTER(?score >= 3) }
    FILTER NOT EXISTS { ?n1 cc:stance cc:Refutes } FILTER NOT EXISTS { ?n2 cc:stance cc:Refutes }
  }"""
# a repost tie in either direction (the mutual version is too sparse: core personas each repost only 2 to 5 campaign posts)
TIE_BLOCK = MUTUAL_BLOCK.replace("""    ?x a as:Announce ; as:actor ?account ; as:object ?pnote . ?pnote as:attributedTo ?peer .
    ?y a as:Announce ; as:actor ?peer ; as:object ?anote . ?anote as:attributedTo ?account .""", """    { ?x a as:Announce ; as:actor ?account ; as:object ?pnote . ?pnote as:attributedTo ?peer . }
    UNION { ?y a as:Announce ; as:actor ?peer ; as:object ?anote . ?anote as:attributedTo ?account . }""")
QUERIES_I6 = {
    "tie_open": ("repost tie (either direction) + synthetic images + shared unrefuted claim within 72 h (no TTP match, no account age)", [TIE_BLOCK, PROVENANCE, WINDOW, CLAIM_ON_POSTS_OPEN_STANCE]),
    "tie_sc": ("tie_open + both accounts have a self-consistent pipeline (>= 1 matching op among own images)", [TIE_BLOCK, self_consistent_1("account"), self_consistent_1("peer"), PROVENANCE, WINDOW, CLAIM_ON_POSTS_OPEN_STANCE]),
    "mutual_open": ("mutual reposts + synthetic images + shared unrefuted claim within 72 h (no TTP match, no account age)", [MUTUAL_BLOCK, PROVENANCE, WINDOW, CLAIM_ON_POSTS_OPEN_STANCE]),
    "mutual_sc": ("mutual_open + both accounts have a self-consistent pipeline (>= 1 matching op among own images)", [MUTUAL_BLOCK, self_consistent_1("account"), self_consistent_1("peer"), PROVENANCE, WINDOW, CLAIM_ON_POSTS_OPEN_STANCE]),
    "sc_open_stance": ("self-consistent accounts (>= 1 op) sharing a same-generator synthetic image post with an unrefuted claim within 72 h, >= 2 such peers", [POSTS_WITH_IMAGES, self_consistent_1("account"), self_consistent_1("peer"), GEN_ONLY, PROVENANCE, WINDOW, CLAIM_ON_POSTS_OPEN_STANCE]),
}
# second hop without the creation-burst condition: >= 4 reposts of >= 2 seeded accounts' posts, and an own unrefuted,
# not-true claim appearance (believers repost 1-3 campaign posts in the simulator; the threshold sits above that)
AMP_NOAGE = f"""# amp_noage: second hop seeded from a detector's accounts (VALUES ?core), no account-age condition
{PREFIXES.replace("PREFIX g:", "PREFIX cc:     <https://example.org/cc/>" + chr(10) + "PREFIX g:")}
SELECT ?account (COUNT(DISTINCT ?note) AS ?reposts) WHERE {{
  VALUES ?core {{ %CORE% }}
  GRAPH g:platform {{ ?ann a as:Announce ; as:actor ?account ; as:object ?note . ?note as:attributedTo ?core . ?own as:attributedTo ?account . }}
  FILTER(?account NOT IN (%CORE%))
  GRAPH g:factcheck {{
    ?claim schema:appearance ?own .
    FILTER NOT EXISTS {{ ?review schema:itemReviewed ?claim ; schema:reviewRating ?rating . ?rating schema:ratingValue ?score . FILTER(?score >= 3) }}
    FILTER NOT EXISTS {{ ?own cc:stance cc:Refutes }}
  }}
}}
GROUP BY ?account
HAVING (COUNT(DISTINCT ?note) >= 4 && COUNT(DISTINCT ?core) >= 2)
"""

QUERIES = {
    "open_stance": ("open-world query that ignores posts a stance classifier marks as refuting the claim", [POSTS_WITH_IMAGES, TTP, PROVENANCE, WINDOW, NARRATIVE_OPEN_STANCE]),
    "open_stance_one_op": ("open-world query with stance filter and the TTP match relaxed to one matching operation", [POSTS_WITH_IMAGES, TTP1, PROVENANCE, WINDOW, NARRATIVE_OPEN_STANCE]),
    "open_one_op": ("open-world query with the TTP match relaxed to one matching operation", [POSTS_WITH_IMAGES, TTP1, PROVENANCE, WINDOW, NARRATIVE_OPEN]),
    "open_gen_only": ("open-world query with the TTP match relaxed to 'same generator'", [POSTS_WITH_IMAGES, GEN_ONLY, PROVENANCE, WINDOW, NARRATIVE_OPEN]),
    "full_gen_only": ("full query with the TTP block relaxed to 'same generator'", [POSTS_WITH_IMAGES, GEN_ONLY, PROVENANCE, WINDOW, NARRATIVE]),
    "full_ops_any_gen": ("full query with the TTP block relaxed to 'matching processing, any generator'", [POSTS_WITH_IMAGES, OPS_ANY_GEN, PROVENANCE, WINDOW, NARRATIVE]),
    "full_heavy_processing": ("full query with the TTP block relaxed to 'both images synthetic and heavily processed'", [POSTS_WITH_IMAGES, HEAVY_PROC, PROVENANCE, WINDOW, NARRATIVE]),
    "full_indexed": ("full query with the TTP join through the derived fingerprint index", [POSTS_WITH_IMAGES, TTP_INDEXED, PROVENANCE, WINDOW, NARRATIVE]),
    "full_unreviewed_ok": ("full query that also accepts claims not yet fact-checked (but not ones rated true)", [POSTS_WITH_IMAGES, TTP, PROVENANCE, WINDOW, NARRATIVE_OPEN]),
    "open_peers1": ("open-world query that needs one matching peer instead of two", [POSTS_WITH_IMAGES, TTP, PROVENANCE, WINDOW, NARRATIVE_OPEN]),
    "full_entity": ("full query joining generators through the entity vocabulary", [POSTS_WITH_IMAGES, TTP_ENTITY, PROVENANCE, WINDOW, NARRATIVE]),
    **QUERIES_I6,
}
if __name__ == "__main__":
    d = Path(__file__).resolve().parent / "stress"; d.mkdir(exist_ok=True)
    for k, (c, b) in QUERIES.items():
        q = account_query(k, c, b, min_peers=1 if k.endswith("_peers1") else 2); out = d.parent / "stress_index" if k == "full_indexed" else d; out.mkdir(exist_ok=True)
        if "idx:" in q: q = q.replace("PREFIX g:", "PREFIX idx:    <https://example.org/cc/idx/>\nPREFIX g:")
        if "cc:" in q: q = q.replace("PREFIX g:", "PREFIX cc:     <https://example.org/cc/>\nPREFIX g:")
        if "skos:" in q: q = q.replace("PREFIX g:", "PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>\nPREFIX g:")
        (out / f"{k}.rq").write_text(q)
    (d / "amp_noage.rq.tmpl").write_text(AMP_NOAGE); (d / "sc_open_one_op.rq").write_text(SC_OPEN_1); (d / "full_self_consistent.rq").write_text(SELF_CONSISTENT); (d.parent / "stress_extra" / "full_claim_first.rq").write_text(CLAIM_FIRST)  # not run by default: slow plan
    print(sorted(p.name for p in d.glob("*.rq")))
