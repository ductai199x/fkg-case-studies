# Investigation log - coordinated manipulated-media campaign (Brennerton flood)

All findings come from SPARQL queries through `sparql.py`. The numbers refer to `queries/NN_*.rq`.

## Orientation
- **01-03**: There are four graphs: 648 images, each with an FKG record; 168 accounts; 766 posts; 437 reposts; and 5 ClaimReviews. Four claims are rated False (dam opened on purpose, relief centres refusing people without ID, tap water unsafe even boiled, mayor fled by private plane) and one is rated True (heavy rain caused the flood). The matcher links 81 posts to these claims.
- **04**: 42 accounts have posts matched to False claims, and many of them also have "Manipulated" images. That is too broad to call coordination, and it fits noisy predictions.
- **05**: I checked the FKG record structure: regions, source, op chain with hasNext, parameters, compression, conclusion.

## Hypothesis 1: a shared tools-and-tactics fingerprint
- **06-07**: Ordered op chains per region. Most images have NoPostProc or a single op. One three-step chain, Resampling>GaussianBlur>GaussianNoise, stands out: 15 AI regions (FLUX/Seedream) and 12 camera regions inside AI-edited images. A tally that ignores order was misleading at first, so I rebuilt it in order in 07.
- **08**: Images with that chain have tightly clustered parameters (scale ~0.8, sigma ~0.6, noise ~1.2), are all ReCompressed, and nearly all were posted Oct 3-5 by a handful of accounts on posts with false narratives. Two outliers (rusty_ranger777 and true_patriot7) have very different parameters and benign posts, so I treated them as coincidences. Some chain images carry an **Authentic** verdict with a camera source, which shows the verdict is noisy while the processing fingerprint still links them.
- **14-15**: The parameter histograms confirm a tight cluster. Allowing for missed ops (≥2 of the 3 signature ops), 10 accounts have 3-5 such images each, and every other account has at most 1.
- **16-17**: No image IRI is shared between accounts. The single-image cases split into two groups: benign posts with coincidental parameters (brave_patriot493, mellow_fox648) and organic re-sharers (wild_ranger624, sunny_willow249).

## Hypothesis 2: an account-creation burst and a repost network
- **09-10**: 13 accounts were created Sep 10-13 2026, after 11 days with no new accounts. 12 of them are the 10 fingerprint accounts plus real_river38 and lazy_river856. The 13th, mellow_comet121, posts only benign content.
- **11, 18-20**: The burst accounts repost one another densely. real_river38 and lazy_river856 have few or no images. All 16 of their reposts target core posts, and every one came within 6 h; across the whole dataset only 83 of 437 reposts come that fast. mellow_comet121 does not take part.
- **12, 22**: The burst accounts post generic filler before Oct 3. From Oct 3 to Oct 5 they post assertive false narratives in identical wording, and the claim matcher misses many of these posts. Some cover posts ("Praying for everyone...") carry AI-edited images.

## Hypothesis 3: copy-paste narratives
- **21**: Older accounts that post False-claim content use hedged, question-style templates with unrelated images. The tap-water rumour (Sep 25-30) is spread only by such accounts. I classed it as organic misinformation, not part of the campaign.
- **23**: Only the 12 accounts post text that is a verbatim copy of the core's false-claim posts. This brings in the two image-less amplifiers.

## Alternative explanations
- **13**: Provenance shows core images re-uploaded by older accounts (rusty_harbor678, local_patriot982, sunny_willow249, wild_ranger20). Each did this once, with a questioning caption and no network ties, so they look like people taken in by the campaign.
- **24-26**: A generic pairwise TTP-link query, with no hard-coded values, found a **second** coordinated cluster: six older accounts sharing a Resampling~0.5>Sharpening~0.8 fingerprint on Sep 28-29. It is an "Aurora Trail" product promotion with no claim matches, so it is coordinated but not disinformation. This is why the detector requires false-claim content on both sides of a TTP link.
- **27**: The posts matching the True claim come from older accounts and include no burst accounts. The matcher has errors; for example, one sandbag post is matched to both a True and a False claim.
- **28-29**: I tested the detector thresholds. Core needs ≥2 linked images. The cohort has 2-5 and re-sharers have 1, so the gap is clean. The amplifier rule (fast reposts of ≥2 core accounts plus verbatim text) separates real_river38 and lazy_river856 from older fast reposters (blue_maple418, sunny_patriot10, sunny_atlas704), who never copy network text.

## Dead ends and pitfalls
- In Oxigraph, a FILTER inside `GRAPH {}` or `OPTIONAL {}` that uses a variable bound outside that group silently drops every row. My first detector draft returned 0 rows for this reason. Cross-graph filters have to sit at the outer group level.
- `DAY()/HOURS()` on durations is not supported. I used duration comparisons (`?t2 - ?t1 <= "PT6H"`) instead.

## Conclusion
The coordinated effort has 12 accounts: 10 producers who share one manipulated-media processing fingerprint and push three False claims, and 2 text-only amplifiers. `detector.rq` returns exactly these 12 using generic criteria.
