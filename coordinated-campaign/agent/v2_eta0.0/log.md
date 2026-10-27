# Investigation log: coordinated manipulated-media campaign (Brennerton flood)

**Question:** is there a coordinated effort that uses manipulated media to push false claims, and who is in it?

## Orientation (queries 01-06)
- There are 4 named graphs: about 22K forensic triples (648 images, 668 regions), a platform export (168 accounts, 766 notes, 437 reposts), 5 ClaimReviews (4 False, 1 True) and 6 provenance links.
- 05: many accounts have notes matched to False claims, and many of those notes carry Manipulated images. A naive "false claim + fake image" rule would flag about 30 accounts, so it is too noisy. Hypothesis: a real operation leaves a shared *toolchain* fingerprint.
- 06: 297 images are Manipulated, spread over 7 generators. On its own this does not set any group apart.

## Toolchain fingerprint (07-09, 19-21)
- 07/08: I looked at post-processing chains with 2 or more operations. Two tight parameter clusters stand out:
  - **A:** 3 ops on FLUX.1 [dev] regions: GaussianNoise ~1.2, GaussianBlur ~0.6, Resampling ~0.8. The op *order* varies between images, so I read the order as estimation noise and match chains order-insensitively.
  - **B:** Sharpening ~0.8 + Resampling ~0.5 on GPT-Image 1 regions.
- 09/14: Cluster A notes are the flood false-claim texts (dam, mayor, ID), posted 2026-10-03 to 10-05 by 10 accounts with 3-5 images each. Some images are AIEditing splices: a camera region with the same chain. A few Cluster A notes have benign text and no claim match ("Praying for everyone", "Stay safe"), which fits an incomplete matcher.
- 19/20: The parameters are tight on both the generator and the camera regions, and all regions are recompressed.
- 21: A fuzzy search (2 of 3 ops in tolerance, any source) found no further campaign images. There are no hidden misattributions.

## Alternatives (10-18, 24-25)
- **18, Cluster B:** an "Aurora Trail" jacket marketing push by 6 aged accounts (2020-2023), with no false-claim matches. It is benign coordination, so a false-claim requirement is needed.
- **15, provenance:** 6 derived copies of Cluster A images were re-posted by old accounts with hedged text ("Is it true...?"). I read these as organic re-sharers. I exclude them by requiring original images and >=3 of them.
- **13, copy text:** hedged rumour templates are used by many old accounts. The assertive templates are used only by the 10 accounts plus 2 others. Text alone does not separate the groups; the tap-water rumour has no campaign media at all.
- **10/24/25, account ages:** the 10 accounts plus u20363c2b and u653f610d were created within 3.5 days (09-10 to 09-13). u20efe1df was also created then but is uninvolved: lifestyle posts only, no false claims, no reposts of the network. So creation date is only a supporting signal.
- **11/16/17, reposts:** the 10 accounts repost each other densely. u20363c2b (9/9) and u653f610d (7/7) repost only the network and post assertive false texts without images, so I classed them as **amplifiers**. Old accounts with a few reposts into the network (e.g., udda74b6c, 3/3) fall outside the batch window and are organic.

## Detector (22, 23, 26 = detector.rq)
- 22: The nested NOT EXISTS version of the generic chain match timed out. The op-level join version runs in about 3 s. It returns exactly the two clusters, and only Cluster A has false-claim matches.
- 23: Loosening the tolerance to 25% leaves the membership unchanged.
- 26/detector.rq: the core criteria plus the amplifier branch return 10 core and 2 amplifier accounts, which match my manual conclusion.

## Dead ends
- An ordered-chain signature string (07): GROUP_CONCAT ordering is unreliable and the op order is noisy.
- The first account-profile query used FILTER EXISTS with a property path and timed out.
- Unbound OPTIONAL attachments multiplied rows (first version of 12); fixed by nesting the OPTIONAL.
