Events 1+ pooled over seeds and noise levels. Link: an operator's wave is linked when >= 2 of its flagged accounts get a label and the majority names the right operator.

### Cross-wave link: correct / wrong / no link (operator waves)

| exp | overlap | corepost | narrative | timing | fkg_direct_same_gen | fkg_chained_same_gen | fkg_direct_any_gen | fkg_chained_any_gen | fused_vote | fkg_confirmed |
|---|---|---|---|---|---|---|---|---|---|---|
| w_base | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 | 0.77 / 0.15 / 0.08 | 0.62 / 0.30 / 0.08 | 0.72 / 0.00 / 0.28 | 0.82 / 0.00 / 0.18 | 0.75 / 0.07 / 0.18 | 0.82 / 0.02 / 0.17 | 0.82 / 0.10 / 0.08 | 0.82 / 0.02 / 0.17 |
| w_gen_switch | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 | 0.77 / 0.15 / 0.08 | 0.63 / 0.28 / 0.08 | 0.40 / 0.00 / 0.60 | 0.40 / 0.00 / 0.60 | 0.80 / 0.00 / 0.20 | 0.82 / 0.02 / 0.17 | 0.82 / 0.10 / 0.08 | 0.82 / 0.02 / 0.17 |
| w_shared_kit | 0.00 / 0.00 / 1.00 | 0.00 / 0.00 / 1.00 | 0.72 / 0.17 / 0.12 | 0.62 / 0.27 / 0.12 | 0.38 / 0.42 / 0.20 | 0.42 / 0.42 / 0.17 | 0.43 / 0.40 / 0.17 | 0.45 / 0.40 / 0.15 | 0.63 / 0.23 / 0.13 | 0.48 / 0.33 / 0.18 |

### Account attribution of the within-wave flagged set: accuracy over campaign accounts / precision over labelled accounts

| exp | overlap | corepost | narrative | timing | fkg_direct_same_gen | fkg_chained_same_gen | fkg_direct_any_gen | fkg_chained_any_gen | fused_vote | fkg_confirmed |
|---|---|---|---|---|---|---|---|---|---|---|
| w_base | 0.00 / 0.00 | 0.00 / 0.00 | 0.74 / 0.70 | 0.59 / 0.55 | 0.71 / 0.92 | 0.84 / 0.91 | 0.78 / 0.88 | 0.83 / 0.89 | 0.81 / 0.78 | 0.79 / 0.91 |
| w_gen_switch | 0.00 / 0.00 | 0.00 / 0.00 | 0.67 / 0.62 | 0.55 / 0.51 | 0.40 / 0.86 | 0.42 / 0.86 | 0.79 / 0.88 | 0.81 / 0.85 | 0.76 / 0.71 | 0.75 / 0.87 |
| w_shared_kit | 0.00 / 0.00 | 0.00 / 0.00 | 0.68 / 0.64 | 0.55 / 0.51 | 0.42 / 0.45 | 0.45 / 0.44 | 0.45 / 0.46 | 0.47 / 0.46 | 0.62 / 0.58 | 0.45 / 0.53 |

### Detection of the current wave's accounts: F1 (precision, recall), mean over worlds x events

| exp | U | fkg_chained_same_gen | U+fkg_chained_same_gen | U+fkg_chained_any_gen |
|---|---|---|---|---|
| w_base | 0.73 (0.90, 0.65) | 0.44 (0.80, 0.32) | 0.76 (0.87, 0.70) | 0.74 (0.82, 0.71) |
| w_gen_switch | 0.72 (0.89, 0.64) | 0.24 (0.52, 0.17) | 0.74 (0.88, 0.67) | 0.74 (0.80, 0.71) |
| w_shared_kit | 0.71 (0.88, 0.63) | 0.45 (0.78, 0.33) | 0.74 (0.85, 0.69) | 0.72 (0.79, 0.70) |

### Graph size and query time by event (mean seconds; all events)


w_base

| event | quads | open_stance_w | open_stance_w+amp | rows_announce | rows_takedown | rows_time | rows_topic | sig_edges_any_gen | sig_edges_same_gen | tie_open_w | tie_open_w+amp |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 74,414 | 0.38 | 0.01 | 0.01 | 0.00 | 0.03 | 0.01 | - | - | 1.58 | 0.00 |
| 1 | 200,108 | 1.12 | 0.02 | 0.03 | 0.00 | 0.09 | 0.01 | 0.06 | 0.06 | 6.27 | 0.01 |
| 2 | 327,632 | 2.38 | 0.04 | 0.06 | 0.00 | 0.15 | 0.03 | 0.12 | 0.11 | 11.12 | 0.02 |
| 3 | 461,676 | 4.13 | 0.08 | 0.07 | 0.00 | 0.22 | 0.04 | 0.18 | 0.17 | 18.28 | 0.04 |
| 4 | 606,539 | 6.02 | 0.11 | 0.10 | 0.00 | 0.28 | 0.05 | 0.24 | 0.21 | 17.72 | 0.03 |
| 5 | 754,428 | 8.66 | 0.10 | 0.12 | 0.00 | 0.35 | 0.06 | 0.29 | 0.26 | 31.93 | 0.07 |
