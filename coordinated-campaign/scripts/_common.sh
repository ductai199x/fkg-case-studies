# Sourced by every script: run from the case-study root, write under $OUT_ROOT (default repro/) so the
# checked-in results/ stay untouched and can be diffed against a rerun.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
OUT_ROOT="${OUT_ROOT:-repro}"; WORKERS="${WORKERS:-3}"; PY="${PY:-uv run python}"
mkdir -p "$OUT_ROOT"
stress() { $PY eval/run_stress.py --fresh --workers "$WORKERS" "$@"; }
summ() { $PY eval/summarize_stress.py "$@"; }
