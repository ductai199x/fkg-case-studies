# Investigation log: coordinated manipulated-media effort (Brennerton flood)

All findings come from SPARQL queries run with `sparql.py` (see `queries/`).

## Orientation
- **01**: four named graphs: 648 images with FKG records, 168 accounts, 766 posts, 437 reposts, 5 ClaimReviews and 2 provenance links.
- **02**: of the 5 claims, 4 are rated False (dam opened on purpose, mayor fled by plane, relief centres demand ID, tap water unsafe) and 1 is True (heavy rain caused the flood).

## Hypothesis 1: accounts that post false claims with manipulated images
- **03**: my first version had an unbound-variable join bug. Text-only posts matched every manipulated image and gave counts of 293. I fixed it with a separate variable plus FILTER, and used the same fix in 11 and 16.
- **03 result**: 44 accounts touch false claims. Many have a single manipulated post, so this view alone is too noisy.
- **04**: manipulated images are common across ordinary users. A Manipulated verdict alone is therefore not evidence.
- **05**: there is a burst of 13 accounts created 2026-09-10..13, just before the first post (2026-09-12). Other months have 1-6 new accounts.

## Hypothesis 2: a shared forensic TTP (processing fingerprint)
- **06/07**: ordered op chains per AI region show two over-represented multi-step chains:
  - FLUX.1 [dev] Resampling > GaussianBlur > GaussianNoise (23 regions, plus variants with an op missing or the generator misattributed);
  - GPT-Image 1 Resampling > Sharpening (19 regions).
- **08**: both chains have tight parameter bands:
  - chain A: scale ~0.75-0.86, blur ~0.55-0.67, noise ~1.03-1.30;
  - chain B: scale ~0.45-0.55, sharpen ~0.74-0.86.
- **09**: the two chains have different owners.
  - Chain A sits on templated false-claim posts by the new accounts, burst 2026-10-03..05, mixed with camouflage posts.
  - Chain B is an "Aurora Trail" product-marketing push by 6 older accounts with no false claims. It is coordinated but commercial, so I treat it as a decoy.
- **10**: identical texts are widespread even for benign phrases, so text duplication is weak evidence on its own.
- **11**: per-post view of all recently created accounts.
  - Ten of them post chain-A images on false-claim posts.
  - real_river38 and lazy_river856 post campaign wording as text only. The claim matcher missed both of lazy_river856's posts and one of north_ember718's.
  - The other new accounts look ordinary.

## Hypothesis 3: coordinated amplification
- **12**: provenance shows campaign images (from lazy_pixel298 and quiet_atlas278) re-uploaded by ordinary users (urban_falcon521, wild_ranger624).
- **13**: no image IRI is shared directly between accounts.
- **14**: reposts of false-claim posts concentrate on the new accounts. They repost each other within 0.5-6 h, while ordinary users repost later.
- **15**: chain-A parameters per poster form one tight cluster across the campaign accounts. The only ordinary users with matching parameters are re-sharers.
- **17**: generic pairwise fingerprint matching (>=2 op types, 15% tolerance) links ~16 accounts. Six of them have just one such post and are organic re-sharers: hedged text, old accounts.
- **18/19**: the 12 new accounts direct 100% of their reposts to other new accounts. real_river38 makes 8 fast reposts of false posts and lazy_river856 makes 7.

## Alternatives checked
- **16/21**: the tap-water false claim has no reposts, mixed-age accounts and mostly authentic or text-only posts. It looks like an organic rumor and is not media-driven.
- **20**: the Resampling>Sharpening cluster is marketing with zero false-claim matches.
- **02/16**: the True rain claim also carries manipulated images. This confirms the Manipulated verdict must be combined with other signals.

## Detector and sensitivity
- `detector.rq` = criterion A (shared TTP fingerprint on false-claim manipulated media) OR criterion B (new-account in-group amplification plus false-claim content).
- **22-25**: criterion A returns the same 9 accounts at 10%, 15% and 25% tolerance. Criterion B returns 10 accounts. Their union is the 12 accounts in answer.json.

## Dead ends and caveats
- Account age alone flags benign newcomers.
- The claim matcher misses posts.
- FKG sometimes misattributes the generator (schnell or Midjourney instead of FLUX dev) or misses one op. That is why the detector matches on parameter similarity over >=2 op types rather than on the exact chain or generator.
