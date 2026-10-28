Events 1+ pooled over seeds and noise levels. Link: an operator's wave is linked when >= 2 of its flagged accounts get a label and the majority names the right operator.

### Cross-wave link: correct / wrong / no link (operator waves)

| exp | overlap | corepost | narrative | timing | fkg_direct_same_gen | fkg_chained_same_gen | fkg_direct_any_gen | fkg_chained_any_gen | fused_vote | fkg_confirmed |
|---|---|---|---|---|---|---|---|---|---|---|
| w_long | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 | 0.73 / 0.18 / 0.09 | 0.77 / 0.14 / 0.09 | 0.82 / 0.00 / 0.18 | 0.82 / 0.00 / 0.18 | 0.82 / 0.00 / 0.18 | 0.82 / 0.00 / 0.18 | 0.86 / 0.05 / 0.09 | 0.82 / 0.00 / 0.18 |

### Account attribution of the within-wave flagged set: accuracy over campaign accounts / precision over labelled accounts

| exp | overlap | corepost | narrative | timing | fkg_direct_same_gen | fkg_chained_same_gen | fkg_direct_any_gen | fkg_chained_any_gen | fused_vote | fkg_confirmed |
|---|---|---|---|---|---|---|---|---|---|---|
| w_long | 0.00 / 0.00 | 0.00 / 0.00 | 0.74 / 0.65 | 0.63 / 0.55 | 0.84 / 0.85 | 0.84 / 0.81 | 0.84 / 0.84 | 0.84 / 0.80 | 0.81 / 0.72 | 0.80 / 0.80 |

### Detection of the current wave's accounts: F1 (precision, recall), mean over worlds x events

| exp | U | fkg_chained_same_gen | U+fkg_chained_same_gen | U+fkg_chained_any_gen |
|---|---|---|---|---|
| w_long | 0.78 (0.80, 0.78) | 0.50 (0.72, 0.41) | 0.79 (0.78, 0.82) | 0.77 (0.72, 0.83) |

### Graph size and query time by event (mean seconds; all events)


w_long

| event | quads | naive_open_stance_full | open_stance_w | open_stance_w+amp | rows_announce | rows_takedown | rows_time | rows_topic | sig_edges_any_gen | sig_edges_same_gen | tie_open_w | tie_open_w+amp | window_open_stance | window_tie_open |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 72,730 | 1.24 | 0.48 | 0.01 | 0.01 | 0.00 | 0.03 | 0.01 | - | - | 1.02 | 0.00 | 0.40 | 0.57 |
| 1 | 191,394 | 11.37 | 1.43 | 0.01 | 0.03 | 0.00 | 0.07 | 0.02 | 0.08 | 0.09 | 7.22 | 0.03 | 0.39 | 1.17 |
| 2 | 324,581 | 48.40 | 2.81 | 0.02 | 0.06 | 0.00 | 0.15 | 0.04 | 0.12 | 0.12 | 20.57 | 0.02 | 0.63 | 1.57 |
| 3 | 452,615 | 105.28 | 4.40 | 0.04 | 0.09 | 0.00 | 0.20 | 0.03 | 0.22 | 0.17 | 27.50 | 0.02 | 0.42 | 1.37 |
| 4 | 581,416 | 204.39 | 6.50 | 0.04 | 0.10 | 0.00 | 0.26 | 0.04 | 0.25 | 0.22 | 35.80 | 0.05 | 0.53 | 1.11 |
| 5 | 711,851 | 437.38 | 9.66 | 0.05 | 0.14 | 0.00 | 0.38 | 0.06 | 0.33 | 0.34 | 50.40 | 0.15 | 0.48 | 1.40 |
| 6 | 840,495 | 752.24 | 12.69 | 0.11 | 0.17 | 0.00 | 0.45 | 0.08 | 0.38 | 0.34 | 41.21 | 0.10 | 0.47 | 0.82 |
| 7 | 962,029 | 1256.54 | 14.37 | 0.09 | 0.17 | 0.00 | 0.43 | 0.11 | 0.47 | 0.41 | 48.96 | 0.09 | 0.42 | 1.10 |
| 8 | 1,087,272 | 1770.89 | 16.14 | 0.13 | 0.22 | 0.00 | 0.54 | 0.11 | 0.65 | 0.45 | 38.69 | 0.09 | 0.46 | 0.79 |
| 9 | 1,218,488 | - | 20.95 | 0.14 | 0.22 | 0.00 | 0.52 | 0.11 | 0.63 | 0.51 | 59.47 | 0.16 | 0.39 | 1.01 |
| 10 | 1,346,115 | - | 25.34 | 0.16 | 0.25 | 0.00 | 0.69 | 0.12 | 0.74 | 0.61 | 62.65 | 0.15 | 0.39 | 0.92 |
| 11 | 1,464,611 | - | 29.64 | 0.42 | 0.25 | 0.00 | 0.64 | 0.13 | 0.91 | 0.76 | 86.22 | 0.17 | 0.51 | 1.17 |
