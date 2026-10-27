# Dataset schema card

`dataset.trig` is an RDF dataset (TriG) assembled for an investigation of social-media activity around a local flood event.
It integrates records from four independent producers, each in its own named graph. The default graph describes the named graphs.

| Named graph | Producer | Vocabulary |
|---|---|---|
| `<https://example.org/cc/graph/forensics>` | Forensic Knowledge Graph (FKG) system run on every uploaded image | `fkg:` (below), PROV-O |
| `<https://example.org/cc/graph/platform>` | Platform export of public accounts, posts and reposts | Activity Streams 2.0 (`as:`) |
| `<https://example.org/cc/graph/factcheck>` | Fact-checking desk: ClaimReview fact-checks, plus a claim-matching service linking claims to posts | schema.org (`schema:`) |
| `<https://example.org/cc/graph/provenance>` | Image provenance analysis (near-duplicate / derivation detection) | PROV-O (`prov:wasDerivedFrom`) |

Prefixes: `fkg: <https://example.org/fkg#>`, `as: <https://www.w3.org/ns/activitystreams#>`, `schema: <https://schema.org/>`,
`prov: <http://www.w3.org/ns/prov#>`, `xsd: <http://www.w3.org/2001/XMLSchema#>`. Images are identified by RFC 6920 `ni:///sha-256;...` IRIs,
which are the same IRIs in the platform graph (`as:attachment`) and the forensics graph (`fkg:Image`).

## Forensic Knowledge Graph (FKG) records
An FKG partitions an image into Regions; each region links to exactly one Source and to its processing and compression history.
- `?img a fkg:Image ; fkg:hasRegion ?r .` and `?r fkg:contained_in ?img .`
- `?r fkg:produced_by ?s .` with `?s a fkg:CameraModel ; fkg:hasCameraModel "..."` or `?s a fkg:AIGenerator ; fkg:hasGeneratorModel "..."`; `fkg:hasConfidence` (xsd:float) on the source.
- `?r fkg:modified_by ?op .` — one link per post-processing operation estimated for that region (types `fkg:Resampling`, `fkg:GaussianBlur`,
  `fkg:GaussianNoise`, `fkg:Sharpening`, or `fkg:NoPostProc`). Operations are ordered by `?op fkg:hasNext ?nextOp`. Each operation has
  `fkg:hasParameter ?p . ?p fkg:hasParameterName "scaleFactor"|"sigma"|"amount" ; fkg:hasParameterValue ?v (xsd:float)`. Parameter values are estimates.
- `?r fkg:compress_by ?c .` with `?c a fkg:LastCompressed` (`fkg:hasCompressionAlgorithm`, `fkg:hasCompressionFactor`) or `?c a fkg:ReCompressed` (`fkg:hasReCompressed true`).
- `?r fkg:depict ?d . ?d fkg:hasObjectDescription "..." ; fkg:hasObjectedness true|false .`
- Image-level record: `?rec a fkg:ForensicRecord ; fkg:aboutImage ?img ; fkg:hasConclusion ?concl ; prov:wasGeneratedBy ?analysis .`
  `?concl fkg:verdict fkg:Manipulated|fkg:Authentic ; fkg:manipulationType fkg:FullySynthetic|fkg:AIEditing .`
- Forensic outputs are predictions and can be wrong (misattributed sources, missed or spurious operations, parameter estimation error).

## Platform records (Activity Streams 2.0)
- Accounts: `?a a as:Person ; as:preferredUsername "..." ; as:published ?accountCreated .`
- Posts: `?act a as:Create ; as:actor ?a ; as:object ?note ; as:published ?t .` and `?note a as:Note ; as:attributedTo ?a ; as:published ?t ; as:content "..."@en ; as:attachment ?img .` (attachment optional)
- Reposts: `?act a as:Announce ; as:actor ?a ; as:object ?note ; as:published ?t .`
- Timestamps are xsd:dateTime. The SPARQL engine (Oxigraph) supports dateTime subtraction, e.g. `FILTER(?t2 - ?t1 <= "PT72H"^^xsd:dayTimeDuration)`.

## Fact-check records (schema.org)
- `?review a schema:ClaimReview ; schema:itemReviewed ?claim ; schema:claimReviewed "..." ; schema:author ?org ; schema:reviewRating ?rating .`
  `?rating schema:ratingValue ?v ; schema:bestRating 5 ; schema:worstRating 1 ; schema:alternateName "False"|"True"|... .`
- `?claim a schema:Claim ; schema:text "..." ; schema:appearance ?note .` — appearances come from an automatic claim matcher and can be incomplete or wrong.

## Provenance records
- `?img2 prov:wasDerivedFrom ?img1 .` — image 2 was detected as a derived copy (e.g. re-upload) of image 1. Detection can miss links.

## Querying
`python3 sparql.py my_query.rq` (or a query string) runs SPARQL 1.1 over `dataset.trig` and prints tab-separated results (`--limit N`).
Use `GRAPH <...> { ... }` to address a named graph.
