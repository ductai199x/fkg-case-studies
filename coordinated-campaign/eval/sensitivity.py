# Sensitivity of the full query to its three thresholds (parameter tolerance, matched operations, minimum peers).
import json, os, statistics as st, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); sys.path.insert(0, str(Path(__file__).parent.parent / "queries"))
from run_eval import load, accounts, prf, ROOT
import build_queries as bq
DATA, TRUTH = Path(os.environ.get("FKG_DATA", ROOT / "data")), Path(os.environ.get("FKG_TRUTH", ROOT / "truth"))
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results/sensitivity.json"
rows = []
for eta in ["0.0", "0.3", "0.5"]:
    stores = [(load(DATA / f"eta_{eta}/seed_{s}/dataset.trig"), set(json.load(open(TRUTH / f"eta_{eta}/seed_{s}.json"))["core"])) for s in range(5)]
    for tol in [0.05, 0.15, 0.30]:
        for nops in [1, 2, 3]:
            for k in [1, 2, 3]:
                ttp = bq.TTP.replace("0.15 * ?v1", f"{tol} * ?v1").replace(">= 2) }", f">= {nops}) }}")
                q = bq.account_query("full", "sens", [bq.POSTS_WITH_IMAGES, ttp, bq.PROVENANCE, bq.WINDOW, bq.NARRATIVE], min_peers=k)
                f = [prf(accounts(s, q), core)["f1"] for s, core in stores]
                rows.append({"eta": float(eta), "tol": tol, "matched_ops": nops, "min_peers": k, "f1_core_mean": st.mean(f), "f1_core_sd": st.stdev(f)})
                print(rows[-1], flush=True)
OUT.parent.mkdir(parents=True, exist_ok=True); json.dump(rows, open(OUT, "w"), indent=1)
