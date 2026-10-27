#!/usr/bin/env bash
# Section 7.3 tables: hand-written queries and the agent-written queries on naive and evasive worlds.
# The agent queries in agent/v2_eta*/ are frozen outputs of the agent runs (their logs are next to them); this scores them.
source "$(dirname "$0")/_common.sh"
D="${DATA:-$OUT_ROOT/data}"; T="${TRUTH:-$OUT_ROOT/truth}"; DE="${DATA_EVASIVE:-$OUT_ROOT/data_evasive}"; TE="${TRUTH_EVASIVE:-$OUT_ROOT/truth_evasive}"
[ -d "$D" ] || { D=data; T=truth; DE=data_evasive; TE=truth_evasive; echo "using checked-in data/ (run 01_original_data.sh to regenerate)"; }
O="$OUT_ROOT/original"; mkdir -p "$O"
$PY eval/run_eval.py --data "$D" --truth "$T" --out "$O/handwritten.json"
$PY eval/run_eval.py --data "$D" --truth "$T" --extra agent/v2_eta*/agent_eta*.rq --out "$O/with_agents.json"
$PY eval/run_eval.py --data "$DE" --truth "$TE" --extra agent/v2_eta*/agent_eta*.rq --out "$O/with_agents_evasive.json"
$PY eval/run_eval.py --data "$D" --truth "$T" --extra agent/v2_eta0.2/agent_eta0.2.rq --out "$O/agent02_naive.json"
$PY eval/run_eval.py --data "$DE" --truth "$TE" --extra agent/v2_eta0.2/agent_eta0.2.rq --out "$O/agent02_evasive.json"
