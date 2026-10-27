#!/usr/bin/env bash
# Iteration 5 (Table 7.6): leak-fixed realistic worlds with per-claim fact-check draws (i5f_*), the stance-aware and
# one-operation detectors, early-detection cuts, then the chosen ensembles re-checked on held-out seeds 4-6.
source "$(dirname "$0")/_common.sh"
O="$OUT_ROOT/stress"; F="$OUT_ROOT/stress_fresh"; $PY queries/build_stress_queries.py
W="i5f_base i5f_debunkers i5f_debunkers_weak_stance i5f_low_volume i5f_per_persona_aged i5f_spamouflage"
TTD="i5f_ttd_12h i5f_ttd_18h i5f_ttd_24h i5f_ttd_36h i5f_ttd_48h"
stress --exps $W $TTD --etas 0,0.3 --seeds 1,2,3 --timeout 900 --out "$O" \
  --queries full full_unreviewed_ok open_stance open_stance_one_op open_one_op open_gen_only open_peers1 sc_open_one_op full_self_consistent agent_eta0.2 agent_eta0.4 context_only corepost
Q="full full+amplifiers full_unreviewed_ok open_stance open_stance_one_op open_one_op open_peers1 sc_open_one_op full_self_consistent agent_eta0.2 agent_eta0.4 context_only corepost"
for m in f1 precision recall; do summ --dir "$O" --metric $m --exps $W $TTD --queries $Q; echo; done > "$O/i5f_summary.md"
U="open_stance_one_op|agent_eta0.2 open_stance|agent_eta0.2 open_stance_one_op|open_stance"
$PY eval/union_scores.py --dir "$O" --exps $W $TTD --unions $U --seeds 1,2,3 > "$O/i5f_union.md"
stress --exps i5f_base i5f_debunkers i5f_low_volume i5f_per_persona_aged i5f_spamouflage --etas 0,0.3 --seeds 4,5,6 --timeout 900 --out "$F" \
  --queries full open_stance open_stance_one_op agent_eta0.2 corepost
FW="i5f_base i5f_debunkers i5f_low_volume i5f_per_persona_aged i5f_spamouflage"
summ --dir "$F" --exps $FW --queries full full+amplifiers open_stance open_stance_one_op agent_eta0.2 corepost > "$F/summary.md"
for m in f1 precision; do $PY eval/union_scores.py --dir "$F" --exps $FW --unions "open_stance|agent_eta0.2" "open_stance_one_op|agent_eta0.2" --seeds 4,5,6 --metric $m; echo; done > "$F/union.md"
