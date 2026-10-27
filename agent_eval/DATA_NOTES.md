# Data notes given to every query writer (human or agent)

Three RDF datasets (TriG), one per case: cs1 (claims about current events), cs2 (a viral image spreading across
platforms), cs3 (altered media and how it is presented). Vocabulary: fkg-core.ttl (Forensic Knowledge Graph, from
arXiv:2606.23917 Appendix A) and fkg-context.ttl (ctx: extension reusing Activity Streams 2.0, schema.org, PROV-O).
Queries run over the union of all named graphs (urn:g:reference, urn:g:context, urn:g:fkg/<image>). No RDFS/OWL
inference is applied, so subclass membership must be matched explicitly (e.g. ?s a fkg:AIGenerator).

What the data looks like:
- Every posted file is its own fkg:Image instance with its own forensic record: regions, each with exactly one source
  (fkg:CameraModel or fkg:AIGenerator, with fkg:hasConfidence), post-processing, compression (fkg:LastCompressed
  with fkg:hasCompressionFactor on a 0-1 scale; also typed fkg:ReCompressed when recompression was detected), and
  depicted content (fkg:hasObjectDescription; in cs3 also ctx:depictsEntity linking to an entity IRI).
- Posts are as:Note with as:attributedTo, as:published (xsd:dateTime), as:attachment (the image), ctx:onPlatform,
  ctx:shareCount; optional ctx:creditsSource and ctx:hasDisclosure. Accounts carry ctx:accountGenre.
- Claims are schema:Claim with schema:appearance (the post); in cs1 ctx:assertsDepictionOf an schema:Event
  (schema:startDate); in cs3 schema:about an entity. Fact-checks are schema:ClaimReview with schema:isBasedOn a
  forensic record.
- Near-duplicate clusters (ctx:inCluster) come from perceptual hashing; membership has no direction.
- Platforms (ctx:Platform) have a transcoding profile: ctx:transcodeQuality, ctx:maxLongEdge, ctx:passthrough.
  A pass-through platform stores uploaded files byte-for-byte; other platforms re-encode to their quality and
  downscale to their maximum size. ctx:pixelLongEdge is measured per image.
- Content credentials (ctx:ContentCredential) summarize signed C2PA manifests: ctx:digitalSourceType uses IPTC
  Digital Source Type IRIs (iptc:digitalCapture, iptc:trainedAlgorithmicMedia,
  iptc:compositeWithTrainedAlgorithmicMedia); ctx:claimedCaptureDevice; ctx:signatureValid.
- Detector provenance: each fkg:ForensicRecord prov:wasGeneratedBy a ctx:DetectorRun, prov:wasAssociatedWith a
  ctx:DetectorVersion. Known defects are ctx:KnownIssue (ctx:affectsVersion, ctx:affectsProperty as an IRI string).
  ctx:GeneratorModel entities (linked via ctx:generatorEntity) carry schema:datePublished (release date).

Known data caveats (as an analyst would know them):
- The organization treats AI attributions with confidence below 0.7 as unreliable; heavy recompression can push
  a genuine AI region's confidence down to roughly 0.5-0.7.
- The detector occasionally reports false AI regions at moderate confidence. They are triggered by image content, so a
  false region can recur on some (not necessarily all) copies of the same photograph.
- Perceptual near-duplicate clustering occasionally merges two different photographs of a similar scene.
- The crawl is incomplete (open world): absence of a triple is not evidence of absence.
