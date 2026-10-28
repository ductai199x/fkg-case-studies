| exp | look-alikes per campaign account | U precision | U recall | U+FKG precision | FP roles (U) | narrative link c/w/n | timing link c/w/n | fkg_chained_same_gen link c/w/n | fkg_chained_any_gen link c/w/n | fkg_confirmed link c/w/n | narrative attr. precision (benign labelled) | timing attr. precision (benign labelled) | fkg_chained_same_gen attr. precision (benign labelled) | fkg_chained_any_gen attr. precision (benign labelled) | fkg_confirmed attr. precision (benign labelled) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| w_br0 | 1.0 | 0.85 | 0.68 | 0.76 | organic 89, fan 5, debunker 2 | 0.82/0.15/0.03 | 0.83/0.13/0.03 | 0.87/0.00/0.13 | 0.87/0.00/0.13 | 0.87/0.00/0.13 | 0.70 (88) | 0.58 (95) | 0.88 (64) | 0.87 (72) | 0.90 (52) |
| w_br10 | 8.4 | 0.60 | 0.66 | 0.52 | fan 186, organic 112, brand 40, news 17 | 0.82/0.17/0.02 | 0.80/0.18/0.02 | 0.85/0.00/0.15 | 0.87/0.00/0.13 | 0.87/0.00/0.13 | 0.52 (299) | 0.41 (357) | 0.79 (122) | 0.70 (203) | 0.76 (143) |
| w_br30 | 23.2 | 0.38 | 0.63 | 0.32 | fan 675, organic 106, brand 37, news 18 | 0.82/0.13/0.05 | 0.85/0.10/0.05 | 0.85/0.00/0.15 | 0.85/0.02/0.13 | 0.85/0.02/0.13 | 0.34 (730) | 0.26 (837) | 0.65 (244) | 0.46 (516) | 0.51 (417) |
| w_br30_warm | 23.2 | 0.36 | 0.63 | 0.30 | fan 657, organic 209, news 28, brand 24 | 0.82/0.13/0.05 | 0.68/0.27/0.05 | 0.85/0.00/0.15 | 0.85/0.02/0.13 | 0.85/0.02/0.13 | 0.34 (772) | 0.23 (920) | 0.61 (298) | 0.44 (588) | 0.51 (428) |

### With the style-tenure filter

| exp | x | U precision | U recall | U+FKG same-gen precision | recall | campaign accounts dropped / all dropped | FKG same-gen attr. precision (benign labelled) |
|---|---|---|---|---|---|---|---|
| w_br0 | 1.0 | 0.86 | 0.68 | 0.83 | 0.73 | 0 / 30 | 0.89 (59) |
| w_br10 | 8.4 | 0.72 | 0.66 | 0.71 | 0.73 | 0 / 271 | 0.83 (94) |
| w_br30 | 23.2 | 0.55 | 0.63 | 0.55 | 0.70 | 0 / 739 | 0.76 (144) |
| w_br30_warm | 23.2 | 0.40 | 0.43 | 0.39 | 0.47 | 188 / 941 | 0.64 (180) |
