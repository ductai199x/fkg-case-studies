#!/usr/bin/env bash
# Iteration 1: operator varies processing parameters, operation order, generator mix; evasive operator.
source "$(dirname "$0")/_common.sh"
O="$OUT_ROOT/stress"; $PY queries/build_stress_queries.py
stress --exps base jitter_10 jitter_20 jitter_40 uniform_params op_pool per_account op_shuffle gen_mix3 pool_genmix --etas 0,0.3,0.5 --seeds 1,2,3 --out "$O" \
  --queries context_only forensic_only forensic_time full full_no_provenance full_gen_only full_ops_any_gen full_self_consistent full_heavy_processing agent_eta0.0 agent_eta0.2 agent_eta0.4 corepost
stress --exps evasive per_account_evasive op_pool_evasive pool_genmix_evasive --etas 0,0.3,0.5 --seeds 1,2,3 --out "$O" \
  --queries context_only forensic_only forensic_time full full_no_provenance full_gen_only full_ops_any_gen full_self_consistent full_heavy_processing agent_eta0.0 agent_eta0.2 agent_eta0.4 corepost
summ --dir "$O" --exps base jitter_10 jitter_20 jitter_40 uniform_params op_pool per_account op_shuffle gen_mix3 pool_genmix evasive per_account_evasive op_pool_evasive pool_genmix_evasive \
  --queries full full+amplifiers full_self_consistent full_heavy_processing full_gen_only context_only agent_eta0.0 agent_eta0.2 agent_eta0.4 corepost > "$O/iter1_summary.md"
