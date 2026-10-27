# Vector (PDF) figures for the LaTeX report and executive summary in docs/, drawn from the stored results.
# Sized for a 6.5 in single-column text width so 8-9 pt labels print at their nominal size.
import json, statistics as st
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parent.parent; OUT = ROOT / "docs/figures"; OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9, "legend.fontsize": 8.5, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
                     "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42, "font.family": "DejaVu Sans"})
ACC, GREY, LIGHT = "#2f6fbf", "#6e6e6e", "#a8a8a8"
W = 6.3   # inches; \textwidth is 6.5 in
summary = lambda cs: json.load(open(ROOT / cs / "results/summary.json"))

def headline():
    s1, s2, s3 = summary("cs1_recycled_media"), summary("cs2_lineage_laundering"), summary("cs3_intent_materiality")
    hw = json.load(open(ROOT / "coordinated-campaign/results/handwritten.json"))
    f1 = lambda q: st.mean(r["f1"] for r in hw if r["query"] == q and r["eta"] == 0.0)
    hop = s2["CQ2.4 hidden platform hop (integrated)"]; hopb = s2["Baseline: previous post's platform"]
    rows = [("CS1 recycled media", "four-way label accuracy", {"integrated": s1["CQ1.3 classification (integrated)"]["accuracy"], "forensic only": s1["Baseline: forensic layer only"]["accuracy"], "context only": s1["Baseline: context layer only"]["accuracy"]}),
            ("CS2 source laundering", "precision", {"integrated": s2["CQ2.3 laundering (integrated)"]["precision"], "context only": s2["Baseline: all outlet-crediting posts"]["precision"]}),
            ("CS2 hidden platform hop", "accuracy", {"integrated": hop["correct"] / hop["of"], "context only": hopb["correct"] / hopb["of"]}),
            ("CS3 materiality triage", "precision", {"integrated": s3["CQ3.1 triage queue (integrated)"]["precision"], "forensic only": s3["Baseline queue: forensic only"]["precision"], "context only": s3["Baseline queue: context only"]["precision"]}),
            ("CS4 coordinated campaign", "account-level F1", {"integrated": f1("full+amplifiers"), "forensic only": f1("forensic_only"), "context only": f1("context_only")})]
    fig, ax = plt.subplots(figsize=(W, 2.9)); n = len(rows)
    sty = {"integrated": dict(s=60, color=ACC, zorder=4), "forensic only": dict(s=40, color=GREY, zorder=3), "context only": dict(s=40, facecolors="white", edgecolors=GREY, linewidths=1.4, zorder=3)}
    for i, (task, metric, v) in enumerate(rows):
        y = n - 1 - i; ax.plot([min(v.values()), max(v.values())], [y, y], color="#d9d9d9", lw=3, zorder=1)
        for m, x in v.items(): ax.scatter([x], [y], **sty[m], label=m if i == 0 or (m == "forensic only" and i == 0) else None)
        ax.text(v["integrated"] + 0.025, y, f"{v['integrated']:.2f}", va="center", color=ACC, fontsize=8.5)
    ax.set_yticks(range(n)); ax.set_yticklabels([f"{t}\n{m}" for t, m, _ in reversed(rows)], fontsize=8.5)
    ax.set_xlim(0, 1.08); ax.set_xticks([0, .25, .5, .75, 1]); ax.grid(axis="x", alpha=.3); ax.set_ylim(-0.6, n - 0.4)
    ax.tick_params(axis="y", length=0); ax.spines["left"].set_visible(False)
    h = [plt.scatter([], [], **{k: v for k, v in sty[m].items() if k != "zorder"}) for m in sty]
    ax.legend(h, ["integrated FKG + context", "forensic only", "context only"], frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.45, 1.0), handletextpad=0.3)
    fig.tight_layout(); fig.savefig(OUT / "headline.pdf"); plt.close(fig)

def sweep():
    S = json.load(open(ROOT / "robustness.json"))["summary"]; etas = [0.05, 0.1, 0.2, 0.3, 0.5]
    panels = [("cs1_recycled_media", "CS1 four-way classification (macro-F1)", [("CQ1.3 classification (integrated)", "integrated", ACC, "-"), ("Baseline: forensic layer only", "forensic only", GREY, "-"), ("Baseline: context layer only", "context only", LIGHT, "--")]),
              ("cs3_intent_materiality", "CS3 fact-check triage queue (F1)", [("CQ3.1 triage queue (integrated)", "integrated", ACC, "-"), ("Baseline queue: forensic only", "forensic only", GREY, "-"), ("Baseline queue: context only", "context only", LIGHT, "--")])]
    fig, axs = plt.subplots(1, 2, figsize=(W, 2.8), sharey=True)
    for ax, (case, title, series) in zip(axs, panels):
        for key, lab, col, ls in series:
            m = [S[f"{case} eta={e}"][key]["headline"]["mean"] for e in etas]; s = [S[f"{case} eta={e}"][key]["headline"]["std"] for e in etas]
            ax.errorbar(etas, m, yerr=s, label=lab, color=col, ls=ls, marker="o", ms=3.5, lw=2 if lab == "integrated" else 1.3, capsize=2)
        ax.set_title(title); ax.set_xlabel("noise rate per failure mode $\\eta$"); ax.set_ylim(0, 1.02); ax.set_xlim(0, 0.53); ax.set_xticks([0, .1, .2, .3, .4, .5]); ax.grid(axis="y", alpha=.3)
    axs[0].set_ylabel("mean $\\pm$ sd over 5 seeds"); axs[0].legend(frameon=False, loc="lower left")
    fig.tight_layout(); fig.savefig(OUT / "noise_sweep.pdf"); plt.close(fig)

def campaign():
    rows = json.load(open(ROOT / "coordinated-campaign/results/handwritten.json"))
    qs = [("full+amplifiers", "joined + amplifier hop", ACC, "-"), ("full", "joined query", ACC, ":"), ("forensic_only", "forensic only", GREY, "-"), ("context_only", "context only", LIGHT, "--")]
    etas = sorted({r["eta"] for r in rows}); fig, ax = plt.subplots(figsize=(W, 2.8))
    for q, lab, col, ls in qs:
        v = [[r["f1"] for r in rows if r["eta"] == e and r["query"] == q] for e in etas]
        ax.errorbar(etas, [st.mean(x) for x in v], yerr=[st.pstdev(x) if len(x) > 1 else 0 for x in v], label=lab, color=col, ls=ls, marker="o", ms=3.5, lw=2 if "joined" in lab else 1.3, capsize=2)
    ax.set_xlabel("detector and claim-matcher error rate $\\eta$"); ax.set_ylabel("account-level F1, mean $\\pm$ sd (5 seeds)"); ax.set_ylim(0, 1.05); ax.set_xticks(etas)
    ax.grid(axis="y", alpha=.3); ax.legend(frameon=False, loc="lower left", ncol=2)
    fig.tight_layout(); fig.savefig(OUT / "campaign_noise.pdf"); plt.close(fig)

def agents():
    sets = ["hand", "A1", "A2", "B1", "B2", "B1r", "B2r"]; d = ROOT / "agent_eval"
    def mean(f):
        j = next(iter(json.load(open(f)).values())); v = [x.get("primary") for k, x in j.items() if k.startswith("Q")]
        return st.mean(x if isinstance(x, (int, float)) else 0.0 for x in v)
    m = [mean(d / f"heldout_scores_{s}.json") for s in sets]
    fig, ax = plt.subplots(figsize=(W, 2.4)); cols = [GREY] + [ACC] * 6
    ax.axhline(m[0], color=GREY, lw=1, ls="--"); ax.scatter(sets, m, color=cols, s=45, zorder=3)
    for i, v in enumerate(m): ax.text(i, v + .005, f"{v:.3f}", ha="center", fontsize=8.5)
    ax.set_ylim(0.88, 0.985); ax.set_ylabel("mean score, 12 questions"); ax.set_xlabel("query set (hand-written, then agents)"); ax.grid(axis="y", alpha=.3)
    fig.tight_layout(); fig.savefig(OUT / "agents_heldout.pdf"); plt.close(fig)

for f in (headline, sweep, campaign, agents): f(); print("ok", f.__name__)
