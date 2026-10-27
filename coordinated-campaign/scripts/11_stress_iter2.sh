#!/usr/bin/env bash
# Iteration 2: scale (3x, 10x, 30x organic population) and several concurrent campaigns.
source "$(dirname "$0")/_common.sh"
O="$OUT_ROOT/stress"; $PY queries/build_stress_queries.py
stress --exps scale_3 scale_10 camps_3_scale3 --etas 0,0.3 --seeds 1,2 --timeout 900 --out "$O" \
  --queries context_only forensic_only forensic_time full full_no_provenance full_gen_only full_heavy_processing full_ops_any_gen full_self_consistent agent_eta0.0 agent_eta0.2 agent_eta0.4 corepost
WORKERS=2 stress --exps scale_30 camps_5_scale10 big_campaign_scale10 --etas 0.3 --seeds 1,2 --timeout 1800 --out "$O" \
  --queries context_only forensic_only full full_self_consistent agent_eta0.2 corepost
summ --dir "$O" --exps scale_3 scale_10 camps_3_scale3 scale_30 camps_5_scale10 big_campaign_scale10 \
  --queries full full+amplifiers full_self_consistent forensic_only context_only agent_eta0.2 corepost > "$O/iter2_summary.md"
