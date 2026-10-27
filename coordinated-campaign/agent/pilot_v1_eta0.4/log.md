# Investigation log

Question: is there a coordinated effort that uses manipulated media to push false claims, and who is involved?
All evidence comes from SPARQL over dataset.trig (queries/01-22). Text filtering was applied only to query output, never to the dataset.

## Orientation (q01-q03)
- 4 named graphs: 622 images (281 Manipulated: 264 FullySynthetic, 17 AIEditing), 742 posts, 102 reposts, 168 accounts, 5 fact-checked claims (4 False, 1 True), 5 provenance links.
- Pitfall found early: `OPTIONAL` blocks joined on an unbound `?img` match every image. q05 was rewritten with per-metric subqueries.

## H1: a cluster of fresh accounts pushes the false claims with manipulated images (q05-q07, q11)
- q05: the 12 accounts created in 2026 (2026-09-10 to 09-13) have the highest share of false-claim posts and manipulated images. All began posting 2026-10-03/04 after ~3 weeks of dormancy.
- q06: daily volume spikes on Oct 3-5, along with the false-claim matches.
- q07/q11: these accounts post assertive texts ("No ID, no help...", "Share before it's deleted") for the dam, relief-center ID and mayor claims. Ordinary users post hedging texts ("Heard..., can anyone confirm?"). The claim matcher misses some campaign posts. The 12 accounts also post some filler ("Praying for everyone...").

## H2: the cluster shares a forensic TTP (q04, q08, q12, q14, q16, q19)
- q04: the chains on AI regions are mostly single operations or NoPostProc. Resampling+Blur+Noise chains are rare.
- q08: almost every image from the young accounts has a FLUX-family source with downscale Resampling (0.70-0.89), GaussianBlur (~0.53-0.73) and GaussianNoise (~1.0-1.34), then recompression. Some images miss one or two of these operations, which fits detector noise. A few images are attributed to schnell or Nano Banana, which looks like misattribution.
- q12: a pairwise TTP graph (>=2 shared op types, parameter difference <=0.15) shows the 10 image-posting young accounts form a dense clique. It also shows a second clique of 6-7 aged accounts, and loose links among a few aged accounts.
- q14: adding "both images attached to posts matched to False claims" and "exclude provenance-derived copies" leaves exactly the 10 young image posters. q16: this result holds for tolerances 0.10 to 0.40. At 0.05, one or two members drop out.
- q19: dead end. The base photos of AI-edited images come from mixed cameras, so no shared device. But 15 of the 17 AI-edited images in the dataset belong to the cluster.

## Alternative explanations
- Re-sharers (q09, q17, q18): all 5 provenance links are aged accounts re-uploading cluster images 4-28 h later with hedging texts, and they have normal posting histories. Without the provenance filter they would join the seed set (q17), so they are excluded as deceived organic sharers.
- Second TTP clique (q13): a coordinated brand campaign ("Aurora Trail" jacket). It is coordinated but makes no false claims, so it is excluded by the fact-check requirement.
- Reposters (q10, q15, q20): all 102 reposts target the cluster's posts. Many aged accounts repost them and post one false-matched question, but nobody reposts them back and their accounts are years old. Without the creation-burst condition, the amplifier branch adds 14 such organic users (q20), so that condition is required.
- Tap-water rumor (q22): an earlier false claim (Sep 25-29) from 9 aged accounts. It has no young authors, no reposts and no shared TTP: an organic rumor with no evidence of coordination.
- Text duplication (q21): exact texts repeat among ordinary users too, so duplication alone is not evidence. But the assertive template set is used only by the 12 young accounts, and the two sets do not overlap.

## Amplifiers (q10, q15)
- real_river38 and lazy_river856 post no images. Each was created in the same 4-day burst, posts only campaign texts (2-3 claim-matched posts) and reposts 4-7 seed accounts, some within 5-15 minutes. They are included as text amplifiers.

## Conclusion
There is one coordinated effort: 12 accounts (10 media operators and 2 amplifiers). detector.rq returns exactly these 12, and answer.json lists the same 12.
