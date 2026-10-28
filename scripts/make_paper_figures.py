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

CC = ROOT / "coordinated-campaign/results"; WRONG = "#c8553d"
jl = lambda f: [json.loads(l) for l in open(f)] if Path(f).exists() else []

def waves_links():  # cross-wave link outcomes per attack world, events 1+ pooled over seeds and noise levels
    worlds = [("w_base", "base"), ("w_shared_narrative", "shared narrative"), ("w_scheduler", "scheduling tool"), ("w_drift_high", "fast preset drift"), ("w_gen_switch", "generator switch"),
              ("w_slow_takedown", "slow takedowns"), ("w_mimic", "mimics app preset"), ("w_shared_kit", "shared toolkit"), ("w_per_persona", "per-persona pipeline")]
    meth = [("fkg_chained_any_gen", "FKG"), ("narrative", "narrative"), ("timing", "timing")]
    fig, ax = plt.subplots(figsize=(W, 4.1)); y, ticks, labs = 0, [], []
    for exp, name in worlds:
        R = [r for r in jl(CC / f"waves/{exp}.jsonl") if r["kind"] == "attribution" and r["event"] >= 1]
        for k, (m, ml) in enumerate(meth):
            M = [r for r in R if r["method"] == m]; c, w, n = (sum(r[x] for r in M) for x in ("link_correct", "link_wrong", "link_none")); t = max(1, c + w + n)
            col = ACC if m.startswith("fkg") else GREY
            ax.barh(y, c / t, color=col, height=0.78); ax.barh(y, w / t, left=c / t, color=WRONG, height=0.78); ax.barh(y, n / t, left=(c + w) / t, color="#e6e6e6", height=0.78)
            ax.text(1.01, y, f"{c / t:.0%} / {w / t:.0%}", va="center", fontsize=7.5, color=col)
            ticks.append(y); labs.append(ml); y -= 1
        ax.text(-0.155, y + 2, name, transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=8, fontweight="bold")
        y -= 0.6
    ax.set_yticks(ticks); ax.set_yticklabels(labs, fontsize=7.5); ax.tick_params(axis="y", length=0); ax.spines["left"].set_visible(False)
    ax.set_xlim(0, 1.13); ax.set_xticks([0, .25, .5, .75, 1]); ax.set_xticklabels(["0", "25%", "50%", "75%", "100%"]); ax.set_xlabel("share of operator waves (correct / wrong shown at right)")
    h = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (ACC, GREY, WRONG, "#e6e6e6")]
    ax.legend(h, ["FKG chained: right operator", "baseline: right operator", "wrong operator", "no link"], frameon=False, ncol=4, loc="lower center", bbox_to_anchor=(0.36, 1.0), fontsize=7, handlelength=1, columnspacing=1)
    fig.subplots_adjust(left=0.33, right=0.92, top=0.93, bottom=0.11); fig.savefig(OUT / "waves_links.pdf"); plt.close(fig)

def waves_scale():  # (a) query time against graph size over a year of events; (b) precision against the benign look-alike base rate
    fig, (a, b) = plt.subplots(1, 2, figsize=(W, 3.6))
    for exp, mk in (("w_long", "o"), ("w_long_scale10", "s")):
        S = [r for r in jl(CC / f"waves_growth/{exp}.jsonl") if r["kind"] == "attribution" and r["method"] == "overlap"]
        q = [r["quads"] / 1e6 for r in S]; sec = lambda k: [r["seconds"].get(k) if isinstance(r["seconds"].get(k), (int, float)) else float("nan") for r in S]
        for k, lab, col, ls in (("tie_open_w", "repost tie, event-scoped", ACC, "--"), ("open_stance_w", "joined query, event-scoped", ACC, "-"),
                                ("naive_open_stance_full", "joined query, unscoped", "black", ":"), ("sig_edges_any_gen", "cross-wave edges", GREY, "-"), ("window_open_stance", "window-only store", LIGHT, "-")):
            a.plot(q, sec(k), color=col, ls=ls, marker=mk, ms=3, lw=1.4, label=lab if exp == "w_long" else None)
    a.set_xscale("log"); a.set_yscale("log"); a.set_xlabel("graph size (million quads)"); a.set_ylabel("query time (s)"); a.axhline(1800, color=LIGHT, lw=0.8)
    a.text(0.08, 1800 * 1.15, "30-min timeout", fontsize=7, color=GREY); a.set_title("(a) query time as the graph grows")
    h, l = a.get_legend_handles_labels(); h += [plt.Line2D([], [], color=GREY, marker=m, ls="none", ms=4) for m in "os"]; l += ["1x population", "10x population"]
    a.legend(h, l, frameon=False, fontsize=6.8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    C = json.load(open(CC / "waves_baserate/curve.json")); C = sorted(C, key=lambda d: d["x"]); x = [d["x"] for d in C if d["exp"] != "w_base_noise"]
    pick = lambda f: [f(d) for d in C if d["exp"] != "w_base_noise"]
    b.plot(x, pick(lambda d: d["U_prec"]), color=ACC, marker="o", ms=3.5, lw=2, label="within-wave detection")
    b.plot(x, pick(lambda d: d["attr_prec"]["fkg_chained_same_gen"][0]), color=GREY, marker="o", ms=3, lw=1.4, label="attribution, FKG same generator")
    b.plot(x, pick(lambda d: d["attr_prec"]["fkg_chained_any_gen"][0]), color=GREY, ls="--", marker="o", ms=3, lw=1.2, label="attribution, FKG any generator")
    b.plot(x, pick(lambda d: d["attr_prec"]["narrative"][0]), color=LIGHT, marker="o", ms=3, lw=1.2, label="attribution, narrative")
    T = json.load(open(CC / "waves_baserate_t/curve.json")) if (CC / "waves_baserate_t/curve.json").exists() else []
    T = sorted([d for d in T if "tenure" in d and "warm" not in d["exp"]], key=lambda d: d["x"])
    if T: b.plot([d["x"] for d in T], [d["tenure"]["U_prec"] for d in T], color=ACC, ls="-.", marker="^", ms=4.5, lw=1.4, label="detection with style tenure")
    Wm = [d for d in json.load(open(CC / "waves_baserate_t/curve.json")) if "warm" in d["exp"]] if T else []
    if Wm: b.scatter([Wm[0]["x"]], [Wm[0]["tenure"]["U_prec"]], marker="v", s=36, color=WRONG, zorder=5, label="with tenure, personas warmed up 60 days")
    nz = next(d for d in C if d["exp"] == "w_base_noise"); b0 = next(d for d in C if d["exp"] == "w_base")
    b.errorbar([1.0], [(b0["U_prec"] + nz["U_prec"]) / 2], yerr=[abs(b0["U_prec"] - nz["U_prec"]) / 2], fmt="none", ecolor=ACC, capsize=3, elinewidth=1)
    b.text(1.08, nz["U_prec"] - 0.07, "noise", fontsize=6.5, color=ACC)
    b.set_xscale("log"); b.set_xticks([1, 2, 5, 10, 20]); b.set_xticklabels(["1", "2", "5", "10", "20"]); b.set_ylim(0, 1); b.grid(axis="y", alpha=.3)
    b.set_xlabel("look-alikes per campaign account"); b.set_ylabel("precision"); b.set_title("(b) precision against benign look-alikes")
    b.legend(frameon=False, fontsize=6.8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=1)
    fig.tight_layout(); fig.subplots_adjust(bottom=0.36, right=0.97, wspace=0.32); fig.savefig(OUT / "waves_scale.pdf"); plt.close(fig)

for f in (headline, sweep, campaign, agents, waves_links, waves_scale): f(); print("ok", f.__name__)
