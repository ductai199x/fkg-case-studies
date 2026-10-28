# Long-horizon evaluation (sim/waves.py). For each event k the KG is queried as it stood eval_after_h hours after the event
# started: within-wave detectors (windowed), cross-wave TTP edges to accounts a takedown report names or an earlier wave
# flagged, then attribution by one hop (direct) or by following edges back through earlier waves (chained), against
# account-overlap, co-repost, narrative and posting-time baselines. One JSON row per world x event x method.
import argparse, json, math, os, queue, shutil, subprocess, sys, tempfile, threading, time
from collections import Counter, defaultdict, deque
from concurrent.futures import ProcessPoolExecutor
from datetime import timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sim")); sys.path.insert(0, str(ROOT / "eval"))
from waves import WaveScenario, make_wave_cfg
from waves_grid import WEXPS
from generate import BASE
from run_eval import prf
QW = ROOT / "queries/waves"; PFX = (QW / "_prefix.rq").read_text()
SCRATCH = Path(os.environ.get("STRESS_SCRATCH", Path(tempfile.gettempdir()) / "fkg_wave_worlds"))
INFERRED = f"<{BASE}graph/inferred>"; FLAGGED = f"<{BASE}FlaggedAccount>"; RDF_TYPE = "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>"


class Server:  # one store per snapshot; a query that times out kills the server, which is restarted for the next query
    def __init__(self, path): self.path = path; self.p = None
    def start(self):
        self.p = subprocess.Popen([sys.executable, str(ROOT / "eval/_qserver.py"), str(self.path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.q = queue.Queue(); threading.Thread(target=lambda: [self.q.put(l) for l in self.p.stdout], daemon=True).start()
        self.info = json.loads(self.q.get(timeout=1800))
    def ask(self, q, var="account", timeout=900):
        if self.p is None or self.p.poll() is not None: self.start()
        self.p.stdin.write(json.dumps({"q": q, "var": var}) + "\n"); self.p.stdin.flush()
        try: return json.loads(self.q.get(timeout=timeout)), None
        except queue.Empty: self.close(); return None, "timeout"
    def close(self):
        if self.p: self.p.kill(); self.p.wait(); self.p = None


def tmpl(name, **kw):
    q = (QW / name).read_text()
    for k, v in kw.items(): q = q.replace(f"%{k}%", v)
    return PFX + q


def amp_hop(core):
    iris = [f"<{a}>" for a in sorted(core)]
    q = (ROOT / "queries/stress/amp_noage.rq.tmpl").read_text()
    return q.replace("NOT IN (%CORE%)", "NOT IN (" + ", ".join(iris) + ")").replace("%CORE%", " ".join(iris))


def cosine(x, y):
    d = sum(v * y.get(k, 0) for k, v in x.items()); nx = math.sqrt(sum(v * v for v in x.values())); ny = math.sqrt(sum(v * v for v in y.values()))
    return d / (nx * ny) if nx and ny else 0.0


def argmax(scores, min_score=1e-9):
    if not scores: return None
    best = max(scores.values())
    if best < min_score: return None
    top = [k for k, v in scores.items() if v == best]
    return top[0] if len(top) == 1 else None


def chained_label(a, adj, lab, max_hops):  # nearest takedown-labelled accounts by BFS over cross-wave edges; majority at that distance
    seen, frontier = {a}, [a]
    for _ in range(max_hops):
        nxt = []
        for u in frontier:
            for v in adj.get(u, ()):
                if v not in seen: seen.add(v); nxt.append(v)
        hit = Counter(lab[v] for v in nxt if v in lab)
        if hit: return argmax(dict(hit))
        frontier = nxt
        if not frontier: break
    return None


def run_world(exp, seed, eta, timeout, scaling, min_hits, max_hops, naive_timeout=900):
    cfg = make_wave_cfg(**WEXPS[exp]); tag = f"w_{exp}_e{eta}_s{seed}_{os.getpid()}"; wd = SCRATCH / tag
    shutil.rmtree(wd, ignore_errors=True); wd.mkdir(parents=True)
    t0 = time.time(); sc = WaveScenario(cfg, seed, eta); sc.build_world(); info = sc.build_lines(); t_gen = time.time() - t0
    tr = sc.truth(); roles, opof = tr["roles"], tr["op"]; iri2op = {v: k for k, v in sc.op_iri.items()}
    flagged_hist, adj, out = {}, defaultdict(set), []
    base0 = {"exp": exp, "seed": seed, "eta": eta, "gen_s": t_gen, **{f"world_{k}": v for k, v in info.items()}}
    for e, t_ev in enumerate(sc.events):
        T = t_ev + timedelta(hours=cfg["eval_after_h"]); W0 = t_ev - timedelta(days=1); w0 = W0.strftime("%Y-%m-%dT%H:%M:%SZ")
        waves_e = [w for w in sc.waves if w["event"] == e]
        pos = {BASE + "actor/" + a["id"]: w["op"] for w in waves_e for a in w["core"] + w["amps"]}
        extra = [f"<{a}> {RDF_TYPE} {FLAGGED} {INFERRED} .\n" for a in sorted(flagged_hist)]
        t0 = time.time(); nq = sc.write_snapshot(wd / "snap.nq", T, extra); t_write = time.time() - t0
        srv = Server(wd / "snap.nq"); srv.start(); base = {**base0, "event": e, "quads": srv.info["quads"], "load_s": srv.info["loaded"], "write_s": t_write}
        secs, sets = {}, {}
        def ask(name, q, var="account"):
            d, err = srv.ask(q, var, timeout); secs[name] = d["seconds"] if d else f"{err}"
            return d["rows"] if d else None
        for det in ("open_stance_w", "tie_open_w"):
            core = ask(det, tmpl(det + ".rq.tmpl", W0=w0)); core = set(core or [])
            amp = ask(det + "+amp", amp_hop(core)) if core else []
            sets[det] = core; sets[det + "+amp"] = core | set(amp or [])
        U = sets["open_stance_w+amp"] | sets["tie_open_w+amp"]
        edges = {}
        for v, hg in (("same_gen", "gen"), ("any_gen", "hgen")):
            rows = ask(f"sig_edges_{v}", tmpl("sig_edges.rq.tmpl", W0=w0, HGEN=hg), "*") if (flagged_hist or e) else []
            edges[v] = [(a, h, int(n)) for a, h, n in (rows or [])]
        lab = {a: iri2op[o] for a, o in (ask("rows_takedown", PFX + (QW / "rows_takedown.rq").read_text(), "*") or [])}
        ann = ask("rows_announce", PFX + (QW / "rows_announce.rq").read_text(), "*") or []
        notes = ask("rows_time", PFX + (QW / "rows_time.rq").read_text(), "*") or []
        topics = ask("rows_topic", PFX + (QW / "rows_topic.rq").read_text(), "*") or []
        srv.close()
        if scaling:  # naive full-history detector vs the same detector over a window-only store (incremental view)
            srv = Server(wd / "snap.nq"); d, err = srv.ask((ROOT / "queries/stress/open_stance.rq").read_text(), "account", naive_timeout); srv.close()
            secs["naive_open_stance_full"] = d["seconds"] if d else err
            sc.write_snapshot(wd / "win.nq", T, since=W0); srv = Server(wd / "win.nq"); srv.start(); base["window_quads"] = srv.info["quads"]
            for det, f in (("open_stance", "queries/stress/open_stance.rq"), ("tie_open", "queries/stress/tie_open.rq")):
                d, err = srv.ask((ROOT / f).read_text(), "account", timeout); secs[f"window_{det}"] = d["seconds"] if d else err
                if d: base[f"window_{det}_same_as_full"] = set(d["rows"]) == sets[det + "_w"]
            srv.close()
        # ---- cross-wave edges and attribution ----
        hits = defaultdict(lambda: defaultdict(int))
        for v in edges:
            for a, h, n in edges[v]: hits[v][(a, h)] += n
        res = {}
        for v in edges:
            direct, linked = {}, set()
            for (a, h), n in hits[v].items():
                if n < min_hits: continue
                linked.add(a)
                if h in lab: direct.setdefault(a, Counter())[lab[h]] += n
            direct = {a: argmax(dict(c)) for a, c in direct.items()}
            g = defaultdict(set, {k: set(s) for k, s in adj.items()})
            for (a, h), n in hits[v].items():
                if n >= min_hits: g[a].add(h); g[h].add(a)
            chained = {a: chained_label(a, g, lab, max_hops) for a in linked}
            res[v] = (direct, chained, linked, g)
        # within-wave propagation: an unlabelled flagged account takes the majority label of the flagged accounts it has repost ties with
        author = {n: a for n, a, t in notes}; ties = defaultdict(set)
        for a, n in ann:
            b = author.get(n)
            if b and b != a and a in U | set(pos) and b in U | set(pos): ties[a].add(b); ties[b].add(a)
        def propagate(pred, flagged):
            outp = dict(pred)
            for a in flagged:
                if outp.get(a) is None:
                    c = Counter(pred[b] for b in ties[a] & flagged if pred.get(b) is not None)
                    outp[a] = argmax(dict(c))
            return outp
        # baselines (attributing the within-wave flagged set U)
        hist_ann = defaultdict(set); [hist_ann[a].add(n) for a, n in ann]
        df = Counter(n for s in hist_ann.values() for n in s); N = max(1, len(hist_ann))
        tfidf = lambda s: {n: math.log(N / df[n]) + 1e-9 for n in s}
        op_ann = defaultdict(set); [op_ann[o].update(hist_ann[a]) for a, o in lab.items()]
        top = defaultdict(Counter); [top[a].update([t]) for a, t in topics]
        op_top = defaultdict(Counter); [op_top[o].update(top[a]) for a, o in lab.items()]
        hrs = defaultdict(Counter)
        for n, a, t in notes: hrs[a][int(t[11:13])] += 1
        op_hrs = defaultdict(Counter); [op_hrs[o].update(hrs[a]) for a, o in lab.items()]
        P = {"overlap": {a: lab.get(a) for a in U},
             "corepost": {a: argmax({o: cosine(tfidf(hist_ann[a]), tfidf(s)) for o, s in op_ann.items()}) for a in U},
             "narrative": {a: argmax({o: cosine(top[a], c) for o, c in op_top.items()}) for a in U},
             "timing": {a: argmax({o: cosine(hrs[a], c) for o, c in op_hrs.items()}) for a in U}}
        for v, (direct, chained, linked, g) in res.items():
            P[f"fkg_direct_{v}"] = propagate({a: direct.get(a) for a in U}, U)
            P[f"fkg_chained_{v}"] = propagate({a: chained.get(a) for a in U}, U)
        def attr_rows(method, pred, flagged):
            camp = [a for a in flagged if a in pos]; correct = sum(pred.get(a) == pos[a] for a in camp)
            labelled = [a for a in flagged if pred.get(a) is not None]; wrong_benign = sum(1 for a in labelled if a not in pos)
            links = Counter()
            for w in waves_e:
                ids = [BASE + "actor/" + a["id"] for a in w["core"] + w["amps"]]; ls = [pred[a] for a in ids if a in flagged and pred.get(a) is not None]
                if len(ls) < 2: links["none"] += 1; continue
                links["correct" if argmax(dict(Counter(ls))) == w["op"] else "wrong"] += 1
            return {"method": method, "n_flagged": len(flagged), "n_camp_flagged": len(camp), "attr_correct": correct, "attr_labelled": len(labelled),
                    "attr_acc": correct / max(1, len(camp)), "attr_prec": correct / max(1, len(labelled)), "benign_labelled": wrong_benign,
                    "waves": len(waves_e), "link_correct": links["correct"], "link_wrong": links["wrong"], "link_none": links["none"]}
        # fusion: TTP continuity with the context signals. vote: a label two of the three agree on, else the FKG label;
        # confirmed: the FKG label only when narrative or timing agrees (precision mode)
        fk, nar, tim = P["fkg_chained_any_gen"], P["narrative"], P["timing"]
        def vote(a):
            c = Counter(x for x in (fk.get(a), nar.get(a), tim.get(a)) if x is not None); top = c.most_common(1)
            return top[0][0] if top and top[0][1] >= 2 else fk.get(a)
        P["fused_vote"] = {a: vote(a) for a in U}
        P["fkg_confirmed"] = {a: fk.get(a) if fk.get(a) is not None and fk.get(a) in (nar.get(a), tim.get(a)) else None for a in U}
        # lineage: cross-wave edges between accounts of the same operator, of different operators, or touching a non-campaign account
        allop = opof; lin = Counter()
        for (a, h), n in hits["any_gen"].items():
            if n < min_hits: continue
            lin["same_op" if a in allop and h in allop and allop[a] == allop[h] else "cross_op" if a in allop and h in allop else "benign"] += 1
        common = {**base, "lineage": dict(lin), "seconds": secs, "n_pos": len(pos), "n_takedown_labelled": len(lab), "n_hist_flagged": len(flagged_hist)}
        for m, pred in P.items(): out.append({**common, "kind": "attribution", **attr_rows(m, pred, U)})
        sets["U"] = U
        for name, s in sets.items(): out.append({**common, "kind": "detection", "method": name, **prf(s, set(pos)), "fp_roles": sorted(Counter(roles.get(a, "?") for a in s - set(pos)).items())})
        for v, (direct, chained, linked, g) in res.items():
            for m, pred in ((f"fkg_direct_{v}", direct), (f"fkg_chained_{v}", chained)):
                D = {a for a, o in pred.items() if o is not None}
                out.append({**common, "kind": "detection", "method": m, **prf(D, set(pos)), "fp_roles": sorted(Counter(roles.get(a, "?") for a in D - set(pos)).items())})
                out.append({**common, "kind": "attribution_own", **attr_rows(m, pred, D)})
                out.append({**common, "kind": "detection", "method": f"U+{m}", **prf(U | D, set(pos)), "fp_roles": sorted(Counter(roles.get(a, "?") for a in (U | D) - set(pos)).items())})
            out.append({**common, "kind": "detection", "method": f"linked_{v}", **prf(linked, set(pos))})
        # chained memory for the next events: flagged accounts and the cross-wave edges seen so far (same-generator edges)
        for a in U | res["same_gen"][2]: flagged_hist.setdefault(a, e)
        for (a, h), n in hits["same_gen"].items():
            if n >= min_hits: adj[a].add(h); adj[h].add(a)
    shutil.rmtree(wd, ignore_errors=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exps", nargs="+", required=True); ap.add_argument("--etas", default="0,0.3"); ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--timeout", type=float, default=900); ap.add_argument("--workers", type=int, default=3); ap.add_argument("--scaling", action="store_true")
    ap.add_argument("--naive-timeout", type=float, default=900); ap.add_argument("--min-hits", type=int, default=2); ap.add_argument("--max-hops", type=int, default=6)
    ap.add_argument("--out", default=str(ROOT / "results/waves")); ap.add_argument("--fresh", action="store_true")
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    jobs = [(x, int(s), float(e)) for x in a.exps for e in a.etas.split(",") for s in a.seeds.split(",")]
    if a.fresh:
        for x in a.exps: (out / f"{x}.jsonl").unlink(missing_ok=True)
    with ProcessPoolExecutor(a.workers) as ex:
        futs = {ex.submit(run_world, x, s, e, a.timeout, a.scaling, a.min_hits, a.max_hops, a.naive_timeout): (x, s, e) for x, s, e in jobs}
        for f in futs:
            x, s, e = futs[f]; rows = f.result()
            with open(out / f"{x}.jsonl", "a") as fh:
                for r in rows: fh.write(json.dumps(r, default=str) + "\n")
            print(f"done {x} s{s} eta{e}: {len(rows)} rows", flush=True)


if __name__ == "__main__":
    main()
