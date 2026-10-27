#!/usr/bin/env bash
# Iteration 6: repost-tie evidence and the age-free amplifier hop against per-persona settings on aged accounts,
# the operator who drops in-network reposts, early detection scored against accounts already active, and unions (seeds 1-6).
source "$(dirname "$0")/_common.sh"
O="$OUT_ROOT/stress6"; $PY queries/build_stress_queries.py
stress --exps i5f_per_persona_aged i6_pp_aged_noties i5f_base i5f_debunkers i5f_low_volume i5f_spamouflage i5f_ttd_12h i5f_ttd_24h i5f_ttd_36h i6_pp_aged_ttd_24h i6_pp_aged_ttd_36h \
  --etas 0,0.3 --seeds 1,2,3,4,5,6 --timeout 900 --out "$O" --queries open_stance tie_open sc_open_stance open_stance_one_op agent_eta0.2 corepost
W="i5f_base i5f_debunkers i5f_low_volume i5f_spamouflage i5f_per_persona_aged i6_pp_aged_noties"
Q="open_stance open_stance+amp tie_open tie_open+amp sc_open_stance open_stance_one_op agent_eta0.2 corepost"
for m in f1 precision recall; do summ --dir "$O" --metric $m --exps $W --queries $Q; echo; done > "$O/summary.md"
$PY eval/ttd_active.py --dir "$O" --exps i5f_ttd_12h i5f_ttd_24h i5f_ttd_36h i6_pp_aged_ttd_24h i6_pp_aged_ttd_36h \
  --queries open_stance open_stance+amp open_stance_one_op tie_open+amp corepost > "$O/ttd_active.md"
U="open_stance+amp open_stance+amp|agent_eta0.2 tie_open+amp|open_stance_one_op open_stance+amp|tie_open+amp open_stance+amp|tie_open+amp|agent_eta0.2 open_stance+amp|tie_open+amp|open_stance_one_op open_stance+amp|tie_open+amp|open_stance_one_op|agent_eta0.2"
for S in 1,2,3,4,5,6 2,3,4,5,6; do for m in f1 precision; do echo "$m, eta=0/0.3, seeds $S"; $PY eval/union_scores.py --dir "$O" --exps $W --unions $U --seeds $S --metric $m; done; done > "$O/unions.md"
