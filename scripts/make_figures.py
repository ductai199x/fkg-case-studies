# Draws the report's result figures from the JSON results in this repo (no data regeneration needed).
import json, statistics as st, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parent.parent; OUT = ROOT / "figures"; OUT.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
ACC, GREY, LIGHT = "#2f6fbf", "#8a8a8a", "#c8c8c8"

def sweep():
    S = json.load(open(ROOT / "robustness.json"))["summary"]; etas = [0.05, 0.1, 0.2, 0.3, 0.5]
    panels = [("cs1_recycled_media", "CS1 four-way post labels (macro-F1)", [("CQ1.3 classification (integrated)", "integrated", ACC, "-"), ("Baseline: forensic layer only", "forensic only", GREY, "-"), ("Baseline: context layer only", "context only", LIGHT, "--")]),
              ("cs3_intent_materiality", "CS3 fact-check triage queue (F1)", [("CQ3.1 triage queue (integrated)", "integrated", ACC, "-"), ("Baseline queue: forensic only", "forensic only", GREY, "-"), ("Baseline queue: context only", "context only", LIGHT, "--")])]
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    for ax, (case, title, series) in zip(axs, panels):
        for key, lab, col, ls in series:
            m = [S[f"{case} eta={e}"][key]["headline"]["mean"] for e in etas]; s = [S[f"{case} eta={e}"][key]["headline"]["std"] for e in etas]
            ax.errorbar(etas, m, yerr=s, label=lab, color=col, ls=ls, marker="o", ms=4, lw=2 if lab == "integrated" else 1.4, capsize=2)
        ax.set_title(title); ax.set_xlabel("noise rate per failure mode (η)"); ax.set_ylim(0, 1.02); ax.grid(axis="y", alpha=.3)
    axs[0].set_ylabel("score (mean ± sd, 5 seeds)"); axs[0].legend(frameon=False, loc="lower left")
    fig.tight_layout(); fig.savefig(OUT / "noise_sweep.png", dpi=200); plt.close(fig)

def campaign():
    rows = json.load(open(ROOT / "coordinated-campaign/results/handwritten.json"))
    qs = [("full+amplifiers", "integrated + amplifier hop", ACC, "-"), ("full", "integrated (images only)", ACC, ":"), ("forensic_only", "forensic only", GREY, "-"), ("context_only", "context only", LIGHT, "--")]
    etas = sorted({r["eta"] for r in rows}); fig, ax = plt.subplots(figsize=(6, 3.4))
    for q, lab, col, ls in qs:
        m = [st.mean(r["f1"] for r in rows if r["eta"] == e and r["query"] == q) for e in etas]
        ax.plot(etas, m, label=lab, color=col, ls=ls, marker="o", ms=4, lw=2 if "integrated" in lab else 1.4)
    ax.set_title("CS4 coordinated campaign: account-level F1"); ax.set_xlabel("observation noise η"); ax.set_ylabel("F1 (mean, 5 seeds)"); ax.set_ylim(0, 1.05); ax.grid(axis="y", alpha=.3); ax.legend(frameon=False, fontsize=8, loc="lower left")
    fig.tight_layout(); fig.savefig(OUT / "campaign_noise.png", dpi=200); plt.close(fig)

def agents():
    sets = ["hand", "A1", "A2", "B1", "B2", "B1r", "B2r"]; d = ROOT / "agent_eval"
    def mean(f):
        j = next(iter(json.load(open(f)).values())); v = [x.get("primary") for x in j.values() if isinstance(x, dict)]
        v = [x if isinstance(x, (int, float)) else 0.0 for x in v]; return sum(v) / len(v)
    m = [mean(d / f"heldout_scores_{s}.json") for s in sets]
    fig, ax = plt.subplots(figsize=(6, 3)); cols = [GREY] + [ACC] * 6  # dot plot: no truncated bars
    ax.axhline(m[0], color=GREY, lw=1, ls="--"); ax.scatter(sets, m, color=cols, s=50, zorder=3); [ax.text(i, v + .004, f"{v:.3f}", ha="center", fontsize=8) for i, v in enumerate(m)]
    ax.set_ylim(0.88, 0.98); ax.set_ylabel("mean score, 12 questions"); ax.set_title("Agent-written vs hand-written queries (held-out worlds)")
    fig.tight_layout(); fig.savefig(OUT / "agents_heldout.png", dpi=200); plt.close(fig)

for f in (sweep, campaign, agents):
    try: f(); print("ok", f.__name__)
    except Exception as e: print("skip", f.__name__, repr(e), file=sys.stderr)
