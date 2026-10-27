# Runs stress-test experiments: generate world (sim/stress.py) -> N-Quads -> each detector in a
# subprocess (in-memory store) with a timeout -> account-level P/R/F1, query time, graph size. Rows appended to results/stress/<exp>.jsonl.
import argparse, json, os, shutil, subprocess, sys, tempfile, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import pyoxigraph as ox
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sim")); sys.path.insert(0, str(ROOT / "eval"))
from stress import StressScenario, make_cfg
from generate import BASE as BASE_IRI
from stress_grid import EXPS
from behavioral import ANNOUNCES, corepost
from run_eval import prf

# seeded second hops: detector -> (template, reported name). amp_noage drops the account-creation burst (aged accounts)
SEEDED = {"full": ("amplifiers.rq.tmpl", "full+amplifiers"), "open_stance": ("stress/amp_noage.rq.tmpl", "open_stance+amp"),
          "mutual_open": ("stress/amp_noage.rq.tmpl", "mutual_open+amp"), "mutual_sc": ("stress/amp_noage.rq.tmpl", "mutual_sc+amp"),
          "tie_open": ("stress/amp_noage.rq.tmpl", "tie_open+amp"), "tie_sc": ("stress/amp_noage.rq.tmpl", "tie_sc+amp")}
AGENTS = {f"agent_eta{e}": ROOT / f"agent/v2_eta{e}/agent_eta{e}.rq" for e in ("0.0", "0.2", "0.4")}
SCRATCH = Path(os.environ.get("STRESS_SCRATCH", Path(tempfile.gettempdir()) / "fkg_stress_worlds"))  # worlds are written here and deleted after scoring


def run_q(store_dir, q, timeout, var="account"):
    try:
        p = subprocess.run([sys.executable, str(ROOT / "eval/_q.py"), str(store_dir), var], input=q, capture_output=True, text=True, timeout=timeout)
        if p.returncode: return None, f"error: {p.stderr[-300:]}"
        d = json.loads(p.stdout); return d, None
    except subprocess.TimeoutExpired:
        return None, "timeout"


def detectors(cfg, which):
    qs = {p.stem: p.read_text() for p in sorted((ROOT / "queries").glob("*.rq"))}
    qs.update({p.stem: p.read_text() for p in sorted((ROOT / "queries/stress").glob("*.rq"))})
    if not cfg["entity_vocab"]: qs.pop("full_entity", None)
    if cfg["ttp_index"]: qs.update({p.stem: p.read_text() for p in sorted((ROOT / "queries/stress_index").glob("*.rq"))})
    qs.update({k: p.read_text() for k, p in AGENTS.items()})
    return {k: v for k, v in qs.items() if not which or k in which}


def one_world(exp, eta, seed, timeout, which, overrides):
    cfg = make_cfg(**{**EXPS[exp], **overrides})
    tag = f"{exp}_e{eta}_s{seed}_{os.getpid()}"; wd = SCRATCH / tag; shutil.rmtree(wd, ignore_errors=True); wd.mkdir(parents=True)
    t0 = time.time(); sc = StressScenario(cfg, seed, eta); sc.build_world(); stats = sc.write_nquads(wd / "w.nq"); t_gen = time.time() - t0
    truth = sc.truth(); pos, roles = set(truth["positives"]), truth["accounts"]
    t0 = time.time(); st = ox.Store(); st.bulk_load(path=str(wd / "w.nq"), format=ox.RdfFormat.N_QUADS); nquads = len(st); del st; t_load = time.time() - t0
    T = cfg["as_of"]; first = {}
    for x in sc.notes + sc.announces: first[x["acct"]] = min(first.get(x["acct"], x["t"]), x["t"])
    act = {a for a in pos if T is None or (a.rsplit("/", 1)[1] in first and first[a.rsplit("/", 1)[1]] <= T)}
    base = {"exp": exp, "eta": eta, "seed": seed, "quads": nquads, "nq_mb": (wd / "w.nq").stat().st_size / 1e6, "gen_s": t_gen, "load_s": t_load, "n_pos": len(pos), **stats}
    rows = []
    def score(name, pred, secs, err=None):
        if pred is None: rows.append({**base, "query": name, "seconds": secs, "error": err}); return
        rows.append({**base, "query": name, "seconds": secs, **prf(pred, pos), "n_pos_active": len(act), "recall_active": len(pred & act) / max(1, len(act)), "pred": sorted([a, roles.get(a, "?")] for a in pred), "fp_roles": sorted(roles.get(a, "?") for a in pred - pos), "fn_roles": sorted(roles[a] for a in pos - pred)})
    for name, q in detectors(cfg, which).items():
        d, err = run_q(wd / "w.nq", q, timeout)
        score(name, set(d["rows"]) if d else None, d["seconds"] if d else timeout, err)
        if name in SEEDED and d:  # second hop seeded from this detector's accounts
            tmpl, label = SEEDED[name]; core = set(d["rows"])
            if core:
                iris = [f"<{a}>" for a in sorted(core)]
                qa = (ROOT / "queries" / tmpl).read_text().replace("NOT IN (%CORE%)", "NOT IN (" + ", ".join(iris) + ")").replace("%CORE%", " ".join(iris))
                da, erra = run_q(wd / "w.nq", qa, timeout)
                score(label, core | set(da["rows"]) if da else None, d["seconds"] + (da["seconds"] if da else timeout), erra)
            else: score(label, set(), d["seconds"])
    if not which or "corepost" in which:
        d, err = run_q(wd / "w.nq", ANNOUNCES, timeout, "*")
        if d:
            t0 = time.time(); pred = corepost(d["rows"]); score("corepost", pred, d["seconds"] + time.time() - t0)
        else: score("corepost", None, timeout, err)
    shutil.rmtree(wd, ignore_errors=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exps", nargs="+", required=True); ap.add_argument("--etas", default="0,0.3,0.5"); ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--timeout", type=float, default=600); ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--queries", nargs="*", default=[]); ap.add_argument("--set", default="{}", help="JSON cfg overrides applied to every exp")
    ap.add_argument("--out", default=str(ROOT / "results/stress")); ap.add_argument("--fresh", action="store_true", help="delete <out>/<exp>.jsonl first (rows are appended otherwise)")
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if a.fresh:
        for e in a.exps: (out / f"{e}.jsonl").unlink(missing_ok=True)
    jobs = [(e, float(eta), int(s)) for e in a.exps for eta in a.etas.split(",") for s in a.seeds.split(",")]
    with ProcessPoolExecutor(a.workers) as ex:
        futs = {ex.submit(one_world, e, eta, s, a.timeout, a.queries, json.loads(a.set)): (e, eta, s) for e, eta, s in jobs}
        for fu in futs:
            e, eta, s = futs[fu]
            try: rows = fu.result()
            except Exception as x: print("FAILED", e, eta, s, repr(x), flush=True); continue
            with open(out / f"{e}.jsonl", "a") as f:
                for r in rows: f.write(json.dumps(r) + "\n")
            print(f"{e} eta={eta} seed={s} quads={rows[0]['quads']} " + " ".join(f"{r['query']}:{r.get('f1', float('nan')):.2f}" for r in rows), flush=True)


if __name__ == "__main__":
    main()
