# Named long-horizon experiments (sim/waves.py): name -> make_wave_cfg keyword arguments. All use the realism blocks
# of the stress tests (R_ALL), the leak fixes, the stance classifier and the per-claim fact-check draw.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from stress_grid import R_ALL
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sim"))
from waves import OPERATOR, OP_B
W = {"scale": 3, **R_ALL}
ops = lambda a={}, b={}: [{**OPERATOR, **a}, {**OP_B, **b}]
WEXPS = {
    # two operators, six events four weeks apart, full persona turnover, 5 % parameter drift and a 15 % chance of a tool change per wave
    "w_base": dict(W),
    # attacks on the cross-wave link, and on the baselines
    "w_shared_narrative": {**W, "operators": ops({"themes": ["sabotage", "elite"]})},          # both push the same narratives
    "w_scheduler": {**W, "operators": ops({"hours": None}, {"hours": None})},                   # scheduling tools: no shift pattern
    "w_drift_high": {**W, "op": {"drift": 0.15, "p_swap": 0.3}},                               # faster preset drift and more tool changes
    "w_gen_switch": {**W, "op": {"p_gen_switch": 0.4}},                                        # a new generator in 40 % of waves
    "w_slow_takedown": {**W, "p_takedown": 0.5, "takedown_lag_d": 70.0},                       # fewer, later takedown reports
    "w_per_persona": {**W, "op": {"param_mode": "per_account"}},                               # a fresh random pipeline per persona and wave
    "w_mimic": {**W, "operators": ops({}, {"mimic": True})},                                   # operator B uses the most popular app preset
    "w_shared_kit": {**W, "operators": ops({}, {"gen": "FLUX.1 [dev]", "kit": OPERATOR["kit"]})},  # both buy the same generator and toolkit
}
# growth: a year of events, and a 10x population, to measure precision and query time as the graph grows
WEXPS["w_long"] = {**W, "n_events": 12, "end": (2027, 4, 1)}
WEXPS["w_long_scale10"] = {**W, "scale": 10, "n_events": 12, "end": (2027, 4, 1)}
