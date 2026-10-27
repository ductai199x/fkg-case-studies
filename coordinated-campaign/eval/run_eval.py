# Runs the hand-written queries on every (eta, seed) dataset with Oxigraph and scores account-level detection.
import argparse, json, statistics as st, time
from pathlib import Path
import pyoxigraph as ox

ROOT = Path(__file__).resolve().parent.parent
QDIR = ROOT / "queries"


def load(path):
    store = ox.Store(); store.load(path=str(path), format=ox.RdfFormat.TRIG); return store


def accounts(store, q):
    res = store.query(q)
    return {s["account"].value for s in res}


def prf(pred, pos):
    tp = len(pred & pos); p = tp / len(pred) if pred else 0.0; r = tp / len(pos) if pos else 0.0
    return {"precision": p, "recall": r, "f1": 2 * p * r / (p + r) if p + r else 0.0, "tp": tp, "fp": len(pred - pos), "fn": len(pos - pred)}


def amplifiers(store, core):
    if not core: return set()
    iris = [f"<{a}>" for a in sorted(core)]
    q = (QDIR / "amplifiers.rq.tmpl").read_text().replace("NOT IN (%CORE%)", "NOT IN (" + ", ".join(iris) + ")").replace("%CORE%", " ".join(iris))
    return accounts(store, q)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--data", default=str(ROOT / "data")); ap.add_argument("--truth", default=str(ROOT / "truth"))
    ap.add_argument("--extra", nargs="*", default=[], help="additional .rq files (e.g. agent-authored) to score")
    ap.add_argument("--out", default=str(ROOT / "results" / "handwritten.json"))
    args = ap.parse_args()
    qs = {p.stem: p.read_text() for p in sorted(QDIR.glob("*.rq"))}
    qs.update({Path(p).stem: Path(p).read_text() for p in args.extra})
    rows = []
    for ddir in sorted(Path(args.data).glob("eta_*/seed_*")):
        eta, seed = ddir.parent.name[4:], int(ddir.name[5:])
        truth = json.load(open(Path(args.truth) / f"eta_{eta}" / f"seed_{seed}.json"))
        pos, roles = set(truth["positives"]), truth["accounts"]
        store = load(ddir / "dataset.trig")
        for name, q in qs.items():
            t0 = time.time(); pred = accounts(store, q); dt = time.time() - t0
            row = {"eta": float(eta), "seed": seed, "query": name, "seconds": dt, **prf(pred, pos),
                   "fp_roles": sorted(roles[a] for a in pred - pos), "fn_roles": sorted(roles[a] for a in pos - pred)}
            rows.append(row)
            if name == "full":
                pred2 = pred | amplifiers(store, pred)
                rows.append({"eta": float(eta), "seed": seed, "query": "full+amplifiers", "seconds": dt, **prf(pred2, pos),
                             "fp_roles": sorted(roles[a] for a in pred2 - pos), "fn_roles": sorted(roles[a] for a in pos - pred2)})
        print(f"eta={eta} seed={seed} " + " ".join(f"{r['query']}:{r['f1']:.2f}" for r in rows if r["eta"] == float(eta) and r["seed"] == seed), flush=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True); json.dump(rows, open(args.out, "w"), indent=1)
    # summary table: mean +- sd over seeds
    names = list(dict.fromkeys(r["query"] for r in rows)); etas = sorted({r["eta"] for r in rows})
    lines = ["| query | " + " | ".join(f"eta={e:.1f}" for e in etas) + " |", "|---|" + "---|" * len(etas)]
    for metric in ("precision", "recall", "f1"):
        lines.append(f"| **{metric}** |" + " |" * len(etas))
        for n in names:
            cells = []
            for e in etas:
                v = [r[metric] for r in rows if r["query"] == n and r["eta"] == e]
                cells.append(f"{st.mean(v):.2f} ± {st.stdev(v) if len(v) > 1 else 0:.2f}")
            lines.append(f"| {n} | " + " | ".join(cells) + " |")
    Path(args.out).with_suffix(".md").write_text("\n".join(lines) + "\n"); print("\n".join(lines))


if __name__ == "__main__":
    main()
