# Tables for the long-horizon runs (results/waves/<exp>.jsonl): cross-wave link outcomes, account attribution, detection,
# and query time against graph size by event. Events >= --from-event are pooled (event 0 has no history to link to).
import argparse, json, statistics as st
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
ATTR = ["overlap", "corepost", "narrative", "timing", "fkg_direct_same_gen", "fkg_chained_same_gen", "fkg_direct_any_gen", "fkg_chained_any_gen", "fused_vote", "fkg_confirmed"]
DET = ["U", "fkg_chained_same_gen", "U+fkg_chained_same_gen", "U+fkg_chained_any_gen"]


def load(d, exp): return [json.loads(l) for l in open(Path(d) / f"{exp}.jsonl")]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dir", default=str(ROOT / "results/waves")); ap.add_argument("--exps", nargs="+", required=True)
    ap.add_argument("--from-event", type=int, default=1); ap.add_argument("--etas", default=None); a = ap.parse_args()
    etas = {float(x) for x in a.etas.split(",")} if a.etas else None
    out = []; P = out.append
    data = {e: [r for r in load(a.dir, e) if r["event"] >= a.from_event and (etas is None or r["eta"] in etas)] for e in a.exps}
    P(f"Events {a.from_event}+ pooled over seeds and noise levels. Link: an operator's wave is linked when >= 2 of its flagged accounts get a label and the majority names the right operator.\n")
    P("### Cross-wave link: correct / wrong / no link (operator waves)\n"); P("| exp | " + " | ".join(ATTR) + " |"); P("|---|" + "---|" * len(ATTR))
    for e, rows in data.items():
        cells = []
        for m in ATTR:
            R = [r for r in rows if r["kind"] == "attribution" and r["method"] == m]
            if not R: cells.append("-"); continue
            c, w, n = (sum(r[k] for r in R) for k in ("link_correct", "link_wrong", "link_none")); tot = max(1, c + w + n)
            cells.append(f"{c / tot:.2f} / {w / tot:.2f} / {n / tot:.2f}")
        P(f"| {e} | " + " | ".join(cells) + " |")
    P("\n### Account attribution of the within-wave flagged set: accuracy over campaign accounts / precision over labelled accounts\n")
    P("| exp | " + " | ".join(ATTR) + " |"); P("|---|" + "---|" * len(ATTR))
    for e, rows in data.items():
        cells = []
        for m in ATTR:
            R = [r for r in rows if r["kind"] == "attribution" and r["method"] == m]
            if not R: cells.append("-"); continue
            cor, camp, lab = (sum(r[k] for r in R) for k in ("attr_correct", "n_camp_flagged", "attr_labelled"))
            cells.append(f"{cor / max(1, camp):.2f} / {cor / max(1, lab):.2f}")
        P(f"| {e} | " + " | ".join(cells) + " |")
    P("\n### Detection of the current wave's accounts: F1 (precision, recall), mean over worlds x events\n")
    P("| exp | " + " | ".join(DET) + " |"); P("|---|" + "---|" * len(DET))
    for e, rows in data.items():
        cells = []
        for m in DET:
            if m == "U":
                R = [r for r in rows if r["kind"] == "attribution" and r["method"] == "overlap"]
                pr = [(r["n_camp_flagged"] / max(1, r["n_flagged"]), r["n_camp_flagged"] / max(1, r["n_pos"])) for r in R]
                f = [2 * p * q / (p + q) if p + q else 0 for p, q in pr]
                cells.append(f"{st.mean(f):.2f} ({st.mean(p for p, _ in pr):.2f}, {st.mean(q for _, q in pr):.2f})" if R else "-"); continue
            R = [r for r in rows if r["kind"] == "detection" and r["method"] == m]
            cells.append(f"{st.mean(r['f1'] for r in R):.2f} ({st.mean(r['precision'] for r in R):.2f}, {st.mean(r['recall'] for r in R):.2f})" if R else "-")
        P(f"| {e} | " + " | ".join(cells) + " |")
    P("\n### Graph size and query time by event (mean seconds; all events)\n")
    for e in a.exps:
        rows = [r for r in load(a.dir, e) if r["kind"] == "attribution" and r["method"] == "overlap" and (etas is None or r["eta"] in etas)]
        by = defaultdict(list)
        for r in rows: by[r["event"]].append(r)
        keys = sorted({k for r in rows for k, v in r["seconds"].items() if isinstance(v, (int, float))})
        P(f"\n{e}\n"); P("| event | quads | " + " | ".join(keys) + " |"); P("|---|---|" + "---|" * len(keys))
        for ev in sorted(by):
            R = by[ev]; t = lambda k: [r["seconds"][k] for r in R if isinstance(r["seconds"].get(k), (int, float))]
            P(f"| {ev} | {st.mean(r['quads'] for r in R):,.0f} | " + " | ".join(f"{st.mean(t(k)):.2f}" if t(k) else "-" for k in keys) + " |")
        break
    print("\n".join(out))


if __name__ == "__main__":
    main()
