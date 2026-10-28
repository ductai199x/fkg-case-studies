# Long-horizon world: months of organic activity, a news event every ~4 weeks, and operators that run one campaign wave
# per event with fresh personas, retire them afterwards and drift their editing presets between waves. Platforms publish
# takedown reports (operator attribution + removed accounts) with a lag. Every record carries the time it became
# visible, so a snapshot "as of T" is a prefix of one fixed set of observations (detector outputs never change between
# snapshots). Reuses the realism models of sim/stress.py. All data is synthetic.
import copy, hashlib, math, random, sys
from datetime import timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate import GENERATORS, CAMERAS, OPS, ORGANIC_TEXT, ORGANIC_CONTENT, BRAND_TEXT, ni_iri, dt, rand_time, BASE
from stress import StressScenario, DEFAULT as STRESS_DEFAULT, PREFIX, SUFFIX, NAME_DRIFT, FSD_TPR

# fictional events and claim templates per theme ({p} = place)
EVENTS = [("Brennerton", "flood"), ("Halvik", "wildfire"), ("Corran", "storm"), ("Mesdale", "power outage"), ("Tarrow", "chemical spill"),
          ("Edenfield", "heatwave"), ("Osterby", "bridge collapse"), ("Vellmar", "earthquake")]
THEMES = {
    "sabotage": ["Officials in {p} caused the {e} on purpose to clear the east side.", "The {p} {e} was engineered by council contractors who were paid in advance.",
                 "Emergency crews in {p} were ordered to let the {e} spread."],
    "relief": ["Relief centers in {p} are turning away {e} victims without ID.", "{p} relief cash cards are being seized at police checkpoints.",
               "Insurers told adjusters to deny every {e} claim from {p}."],
    "elite": ["{p}'s mayor fled by private plane before the {e}.", "{p} officials got warnings about the {e} days early and told only donors.",
              "A {p} councillor's company profits from the {e} rebuild contracts."],
    "health": ["{p} tap water is unsafe after the {e} even when boiled.", "Hospitals in {p} are hiding {e} deaths.", "The {e} in {p} released a toxin officials won't name."],
}
POST_STYLE = ["They don't want you to see this. {c}", "{c} Look at this.", "No accident. {c}", "{c} Share before it's deleted.", "Wake up: {c}"]
BELIEVER_STYLE = ["Is this true? {c}", "Can anyone confirm? People say {c}", "If this is real it's criminal: {c}"]
CONTENT = {"sabotage": ["flooded street", "burning hillside", "crew at barrier"], "relief": ["crowd at relief center", "police checkpoint"],
           "elite": ["private jet on runway", "official boarding plane"], "health": ["hospital entrance", "glass of water"]}
TOPICAL = ["flooded street", "burning hillside", "storm damage", "crowd at relief center", "city skyline", "rain clouds", "police checkpoint", "hospital entrance"]
FAN_CONTENT = ["anime character", "fantasy landscape", "band poster", "game screenshot"]

OPERATOR = dict(name="A", themes=["sabotage", "relief"], gen="FLUX.1 [dev]", kit=[[("Resampling", 0.80), ("GaussianBlur", 0.60), ("GaussianNoise", 1.20)],
                [("Resampling", 0.70), ("Sharpening", 0.90), ("GaussianNoise", 1.60)]], param_mode="kit", jitter=0.03, drift=0.05, p_swap=0.15,
                p_gen_switch=0.0, n_core=12, n_amp=4, aged=False, core_reposts=True, organic_reposts=False, hours=([(9.5, 12), (13.5, 17.5), (19, 22)], 8), offset_h=6, window_h=48,
                posts=(3, 5), edit_frac=0.3, claimless_frac=0.2, events=None, mimic=False, reuse_amp=0.0)
OP_B = dict(OPERATOR, name="B", themes=["sabotage", "elite"], gen="Midjourney v7", kit=[[("GaussianBlur", 1.40), ("Sharpening", 0.60), ("Resampling", 1.20)]],
            param_mode="kit", n_core=8, n_amp=3, aged=True, organic_reposts=True, offset_h=18, hours=([(9, 13), (14, 18)], 3))
WAVE_DEFAULT = dict(STRESS_DEFAULT, start=(2026, 5, 1), end=(2026, 10, 10), first_event=(2026, 5, 12, 0), event_every_d=28, n_events=6,
                    operators=[OPERATOR, OP_B], fan_groups=1, fan_size=8, debunkers=8, brand_agencies=1, fc_stream=True, leakfix=True, stance=True,
                    p_takedown=0.8, takedown_recall=0.75, takedown_lag_d=35.0, takedown_lag_sd=0.5, eval_after_h=96, block_d=15)


def make_wave_cfg(**kw):
    cfg = copy.deepcopy(WAVE_DEFAULT)
    ops = kw.pop("operators", None); op_kw = kw.pop("op", {})
    cfg.update(kw)
    cfg["operators"] = [dict(OPERATOR, **o) for o in ops] if ops is not None else [dict(o, **op_kw) for o in cfg["operators"]]
    return cfg


def clamp(t, v): lo, hi = OPS[t][1]; return min(max(v, lo), hi)


class WaveScenario(StressScenario):
    def __init__(self, cfg, seed, eta):
        super().__init__(cfg, seed, eta)
        self.claims, self.claim_text, self.claim_topic, self.claim_event = {}, {}, {}, {}
        self.true_claims = set()
        self.events = [dt(*cfg["first_event"]) + timedelta(days=cfg["event_every_d"] * k) for k in range(cfg["n_events"])]

    def add_account(self, role, created, campaign=None, wave=None):
        a = super().add_account(role, created, campaign); a["wave"] = wave; return a

    def event_claims(self, k):
        place, ev = EVENTS[k % len(EVENTS)]; out = {}
        for th, tmpl in THEMES.items():
            ids = []
            for j, t in enumerate(tmpl):
                cid = f"E{k}{th[:2]}{j}"; txt = t.format(p=place, e=ev)
                self.claims[cid] = (txt, 1, "False"); self.claim_topic[cid] = th; self.claim_event[cid] = k
                self.claim_text[cid] = [s.format(c=txt) for s in POST_STYLE]; ids.append(cid)
            out[th] = ids
        tc, rc = f"E{k}T", f"E{k}R"
        self.claims[tc] = (f"The {ev} hit parts of {place}.", 5, "True"); self.claim_topic[tc] = "news"; self.claim_event[tc] = k; self.true_claims.add(tc)
        self.claims[rc] = (f"A second {ev} is expected in {place} tonight.", 1, "False"); self.claim_topic[rc] = "rumor"; self.claim_event[rc] = k
        self.claim_text[tc] = [f"{place}: the {ev} is bad, stay safe.", f"Roads closed in {place} after the {ev}."]
        self.claim_text[rc] = [f"Heard another {ev} is coming to {place} tonight.", f"Second {ev} expected in {place}, get out now."]
        return out, tc, rc

    def drift_kit(self, st, op, r):
        kit = []
        for ch in st["kit"]:
            ch = [(t, round(clamp(t, v * math.exp(r.gauss(0, op["drift"]))), 3)) for t, v in ch]
            if r.random() < op["p_swap"]:  # tool change: one operation replaced by another
                i = r.randrange(len(ch)); new = r.choice([t for t in OPS if t not in {x for x, _ in ch}])
                ch[i] = (new, round(r.uniform(*OPS[new][1]), 3))
            kit.append(ch)
        st["kit"] = kit
        if r.random() < op["p_gen_switch"]: st["gen"] = r.choice([g for g in GENERATORS if g != st["gen"]])

    def wave_chain(self, op, st, persona_i, acct_chain):
        r = self.truth_rng
        if op["mimic"]: base = list(self.presets[0])
        elif op["param_mode"] == "per_account": base = acct_chain
        else: base = st["kit"][persona_i % len(st["kit"])]
        return [(t, round(clamp(t, v * (1 + r.gauss(0, op["jitter"]))), 3)) for t, v in base]

    def op_time(self, op, t0, t1):
        r = self.truth_rng
        if not op["hours"]: return rand_time(r, t0, t1)
        shifts, tz = op["hours"]
        while True:
            t = rand_time(r, t0, t1); h = (t.hour + t.minute / 60 + tz) % 24
            if any(lo <= h < hi for lo, hi in shifts): return t

    def build_world(self):
        r, c = self.truth_rng, self.cfg
        k = c["scale"]; n_org = int(150 * k)
        pr = random.Random(f"{self.seed}:presets")
        self.presets = [[(t, round(pr.uniform(*OPS[t][1]), 2)) for t in pr.sample(list(OPS), 2)] for _ in range(c["n_presets"])]
        o0, o1 = dt(*c["start"]), dt(*c["end"]); nb = max(1, round((o1 - o0).days / c["block_d"]))
        organic = [self.add_account("organic", rand_time(r, dt(2026, 1, 1), dt(2026, 9, 1)) if r.random() < 0.15 else rand_time(r, dt(2012, 1, 1), dt(2025, 12, 31))) for _ in range(n_org)]
        ev_claims = [self.event_claims(e) for e in range(c["n_events"])]
        # operators: one wave per event they join; fresh (or bought aged) personas each wave; presets drift between waves
        self.waves, camp_notes_by_ev = [], {e: [] for e in range(c["n_events"])}
        orng = random.Random(f"{self.seed}:operators")
        for oi, op in enumerate(c["operators"]):
            st = {"gen": op["gen"], "kit": [list(ch) for ch in op["kit"]]}; prev_amps = []
            for e, t_ev in enumerate(self.events):
                if op["events"] is not None and e not in op["events"]: continue
                if self.waves and any(w["op"] == oi for w in self.waves): self.drift_kit(st, op, orng)
                cw0 = t_ev + timedelta(hours=op["offset_h"]); cw1 = cw0 + timedelta(hours=op["window_h"])
                c0, c1 = (dt(2014, 1, 1), dt(2025, 12, 31)) if op["aged"] else (cw0 - timedelta(days=23), cw0 - timedelta(days=19))
                core = [self.add_account("campaign_core", rand_time(r, c0, c1), oi, e) for _ in range(op["n_core"])]
                keep = [a for a in prev_amps if r.random() < op["reuse_amp"]]
                amps = keep + [self.add_account("campaign_amplifier", rand_time(r, c0, c1), oi, e) for _ in range(op["n_amp"] - len(keep))]
                w = {"op": oi, "event": e, "core": core, "amps": amps, "gen": st["gen"], "kit": copy.deepcopy(st["kit"]), "t0": cw0, "t1": cw1}
                self.waves.append(w); prev_amps = amps
                claims = [cid for th in op["themes"] for cid in ev_claims[e][0][th]]
                for a in core + [a for a in amps if a not in keep]:  # persona filler before the wave
                    f0 = max(o0, cw0 - timedelta(days=21)) if op["aged"] else a["created"] + timedelta(days=1)
                    for t in self.times(a, r.randint(1, 3), f0, cw0 - timedelta(hours=12)):
                        self.post(a, t, r.choice(ORGANIC_TEXT), self.organic_image(r.choice(ORGANIC_CONTENT)) if r.random() < 0.6 else None)
                mine = []
                for pi, a in enumerate(core):
                    acct_chain = [(t, round(r.uniform(*OPS[t][1]), 3)) for t in r.sample(list(OPS), r.randint(2, 3))]
                    for _ in range(r.randint(*op["posts"])):
                        claim = r.choice(claims) if r.random() >= op["claimless_frac"] else None
                        content = r.choice(CONTENT[self.claim_topic[claim]] if claim else ["city skyline", "rain clouds"])
                        img = self.new_image("synthetic" if r.random() >= op["edit_frac"] else "edit", gen=st["gen"], chain=self.wave_chain(op, st, pi, acct_chain), camera=r.choice(CAMERAS), content=content)
                        text = self.text_for(claim, self.claim_text[claim] if claim else ["Praying for everyone tonight.", "Unreal scenes today."])
                        mine.append(self.post(a, self.op_time(op, cw0, cw1), text, img, claim))
                if op["core_reposts"]:
                    for a in core:
                        for n in r.sample([n for n in mine if n["acct"] != a["id"]], min(r.randint(2, 5), len(mine) - 1)):
                            self.announces.append({"acct": a["id"], "note": n["id"], "t": n["t"] + timedelta(minutes=r.uniform(5, 600))})
                for a in amps:
                    for _ in range(r.randint(2, 3)):
                        claim = r.choice(claims); self.post(a, self.op_time(op, cw0, cw1), self.text_for(claim, self.claim_text[claim]), None, claim)
                    for n in r.sample(mine, min(r.randint(6, 10), len(mine))):
                        self.announces.append({"acct": a["id"], "note": n["id"], "t": n["t"] + timedelta(minutes=r.uniform(5, 300))})
                w["notes"] = mine; camp_notes_by_ev[e] += mine
        # persistent benign actors: brand agencies (monthly pushes, fixed pipeline), fan groups (shared preset, mutual reposts), newsroom debunkers
        brand = []
        for b in range(max(0, int(round(c["brand_agencies"] * k)))):
            gen = "GPT-Image 1" if b == 0 else r.choices(list(GENERATORS), weights=list(GENERATORS.values()))[0]
            chain = [("Resampling", 0.50), ("Sharpening", 0.80)] if b == 0 else [(t, round(r.uniform(*OPS[t][1]), 2)) for t in r.sample(list(OPS), 2)]
            accts = [self.add_account("brand", rand_time(r, dt(2019, 1, 1), dt(2023, 12, 31))) for _ in range(6)]; brand += accts
            t = o0 + timedelta(days=r.uniform(0, 20))
            while t < o1:
                for a in accts:
                    for _ in range(4):
                        img = self.new_image("synthetic", gen=gen, chain=chain, pre=False, content=r.choice(["hiker in jacket", "mountain trail", "product shot"]))
                        self.post(a, t + timedelta(hours=r.uniform(0, 36)), r.choice(BRAND_TEXT), img)
                t += timedelta(days=r.uniform(25, 35))
        fans = []
        for g in range(c["fan_groups"]):
            gen = r.choices(list(GENERATORS), weights=list(GENERATORS.values()))[0]
            chain = list(self.presets[0]) if g == 0 else [(t, round(r.uniform(*OPS[t][1]), 2)) for t in r.sample(list(OPS), 2)]
            grp = [self.add_account("fan", rand_time(r, dt(2018, 1, 1), dt(2025, 6, 30))) for _ in range(c["fan_size"])]; fans.append((grp, gen, chain))
            for a in grp:
                for t in self.times(a, max(2, int((o1 - o0).days / 7 * r.uniform(0.5, 1.5))), o0, o1):
                    self.post(a, t, "Made this one tonight.", self.new_image("synthetic", gen=gen, chain=chain, pre=r.random() < 0.5, content=r.choice(FAN_CONTENT)))
        # organic background over the whole horizon (heavy-tailed totals, the stress world's per-block rate)
        for a in organic:
            a0 = max(o0, a["created"]); n = max(1, min(400, int(r.lognormvariate(1.0, 1.0) * nb * (o1 - a0).days / max(1, (o1 - o0).days))))
            for t in self.times(a, n, a0, o1):
                self.post(a, t, r.choice(ORGANIC_TEXT), self.organic_image(r.choice(ORGANIC_CONTENT), a) if r.random() < 0.85 else None)
        # each event: news posts, believers, re-uploaders, rumor spreaders, fans joining in, debunkers
        debunkers = [self.add_account("debunker", rand_time(r, dt(2012, 1, 1), dt(2020, 12, 31))) for _ in range(c["debunkers"])]
        for e, t_ev in enumerate(self.events):
            _, tc, rc = ev_claims[e]; cn = camp_notes_by_ev[e]; claim_notes = [n for n in cn if n["claim"]]
            for a in organic:
                if a["created"] < t_ev and r.random() < 0.15:
                    self.post(a, t_ev + timedelta(hours=r.uniform(0, 96)), r.choice(self.claim_text[tc]), self.organic_image(r.choice(TOPICAL), a) if r.random() < 0.7 else None, tc)
            pool = r.sample(organic, len(organic))
            nbl, nre, nru = (round(c[f] * n_org) for f in ("believer_frac", "reuploader_frac", "rumor_frac"))
            for a in pool[:nbl] if claim_notes else []:
                for _ in range(r.randint(1, 2)):
                    src = r.choice(claim_notes); cl = src["claim"]
                    img = self.organic_image(r.choice(TOPICAL), a) if r.random() < 0.7 else None
                    self.post(a, src["t"] + timedelta(hours=r.uniform(1, 30)), r.choice(BELIEVER_STYLE).format(c=self.claims[cl][0]), img, cl)
                for n in r.sample(cn, min(r.randint(1, 3), len(cn))):
                    self.announces.append({"acct": a["id"], "note": n["id"], "t": n["t"] + timedelta(minutes=r.uniform(30, 1440))})
            for a in pool[nbl:nbl + nre] if claim_notes else []:
                src = r.choice(claim_notes); s = self.images[src["img"]]
                img = self.new_image(s["kind"], gen=s["gen"], chain=s["chain"], camera=s["camera"], content=s["content"], derived_from=src["img"])
                self.post(a, src["t"] + timedelta(hours=r.uniform(2, 30)), r.choice(BELIEVER_STYLE).format(c=self.claims[src["claim"]][0]), img, src["claim"])
            for a in pool[nbl + nre:nbl + nre + nru]:
                self.post(a, t_ev + timedelta(hours=r.uniform(-24, 72)), r.choice(self.claim_text[rc]), self.organic_image(r.choice(TOPICAL)) if r.random() < 0.6 else None, rc)
            for grp, gen, chain in fans:  # a fan community passes a false claim around with its own house style
                fc = r.choice([cid for ids in ev_claims[e][0].values() for cid in ids])
                for a in grp:
                    if r.random() < 0.4:
                        img = self.new_image("synthetic", gen=gen, chain=chain, pre=r.random() < 0.5, content=r.choice(TOPICAL))
                        self.post(a, t_ev + timedelta(hours=r.uniform(6, 72)), r.choice(BELIEVER_STYLE).format(c=self.claims[fc][0]), img, fc)
            for a in debunkers if claim_notes else []:
                for _ in range(r.randint(0, 2)):
                    src = r.choice(claim_notes); s = self.images[src["img"]]
                    img = self.new_image(s["kind"], gen=s["gen"], chain=s["chain"], camera=s["camera"], content=s["content"], derived_from=src["img"], extra_ops=[("Resampling", 0.66)])
                    n = self.post(a, src["t"] + timedelta(hours=r.uniform(6, 48)), f"FALSE: this image claiming that {self.claims[src['claim']][0].lower()} is AI-generated.", img, src["claim"])
                    n["debunk"] = True
        # reposts: popularity-weighted over the whole horizon; fans repost each other; evasive personas repost organic posts
        if c["platform"] == "calibrated": pop = {a["id"]: min(1e4, r.paretovariate(1.276)) for a in organic + brand + [a for g in fans for a in g[0]]}
        else: pop = {a["id"]: r.lognormvariate(0, 1.0) for a in organic + brand}
        pool = [n for n in self.notes if n["acct"] in pop]; weights = [pop[n["acct"]] for n in pool]
        for a in organic:
            kk = sum(r.choice([0, 0, 1, 1, 2, 3, 4, 6]) for _ in range(nb))
            for n in r.choices(pool, weights=weights, k=kk):
                if n["acct"] != a["id"] and n["t"] < o1: self.announces.append({"acct": a["id"], "note": n["id"], "t": n["t"] + self.repost_delay(5, 2880)})
        by_acct = {}
        for n in self.notes: by_acct.setdefault(n["acct"], []).append(n)
        for grp, _, _ in fans:
            for a in grp:
                peers = [n for b in grp if b is not a for n in by_acct.get(b["id"], [])]
                for n in r.sample(peers, min(len(peers), int(len(peers) * 0.3))):
                    self.announces.append({"acct": a["id"], "note": n["id"], "t": n["t"] + timedelta(minutes=r.uniform(5, 1440))})
        for w in self.waves:
            op = c["operators"][w["op"]]
            if not op["organic_reposts"]: continue
            near = [i for i, n in enumerate(pool) if w["t0"] - timedelta(days=10) <= n["t"] <= w["t1"]]
            for a in w["core"] + w["amps"]:
                for i in r.choices(near, weights=[weights[i] for i in near], k=r.randint(4, 9)):
                    self.announces.append({"acct": a["id"], "note": pool[i]["id"], "t": max(pool[i]["t"], w["t0"] - timedelta(days=3)) + timedelta(minutes=r.uniform(5, 2880))})
        if c["leakfix"]: self.fix_leaks_waves()
        # fact-checks per claim (own streams), takedown reports per wave (own stream)
        first_seen = {}
        for n in self.notes:
            if n["claim"]: first_seen[n["claim"]] = min(first_seen.get(n["claim"], n["t"]), n["t"])
        self.review_t, lr = {}, random.Random(f"{self.seed}:fc-latency")
        for cid in self.claims:
            u = random.Random(f"{self.seed}:fc:{cid}").random()
            if cid in self.true_claims or cid.endswith("R") or u < c["fc_coverage"]:
                self.reviewed.add(cid)
                self.review_t[cid] = first_seen.get(cid, self.events[self.claim_event[cid]]) + timedelta(hours=c["fc_latency_h"] * math.exp(lr.gauss(0, 1.0)))
        tr = random.Random(f"{self.seed}:takedowns"); self.takedowns = []
        for wi, w in enumerate(self.waves):
            if tr.random() >= c["p_takedown"]: continue
            t = w["t1"] + timedelta(days=c["takedown_lag_d"] * math.exp(tr.gauss(0, c["takedown_lag_sd"])))
            removed = [a["id"] for a in w["core"] + w["amps"] if tr.random() < c["takedown_recall"]]
            if removed: self.takedowns.append({"wave": wi, "op": w["op"], "t": t, "accounts": removed})
        self.t_first = min(n["t"] for w in self.waves for n in w["notes"])

    def fix_leaks_waves(self):  # same leak fixes as StressScenario.fix_leaks, for event claims
        lr = random.Random(f"{self.seed}:leakfix"); role = {a["id"]: a["role"] for a in self.accounts}
        ev_windows = [(t, t + timedelta(days=5)) for t in self.events]
        for n in self.notes:
            im = self.images.get(n["img"]) if n["img"] else None
            if im is None or im["derived_from"] or not role[n["acct"]].startswith("organic"): continue
            if n["claim"]: im["content"] = lr.choice(TOPICAL)
            elif any(a <= n["t"] <= b for a, b in ev_windows) and lr.random() < 0.35: im["content"] = lr.choice(TOPICAL)
            if im["kind"] == "camera" and lr.random() < 0.12:
                im["kind"], im["gen"] = "edit", lr.choices(list(GENERATORS), weights=list(GENERATORS.values()))[0]

    # ---------- timestamped quads: every record is visible from the time it was created ----------
    def build_lines(self):
        r, e, c = self.rng, self.eta, self.cfg
        self.bias = {t: random.Random(f"{self.seed}:bias:{t}").gauss(0, c["bias_sd"]) for t in OPS}
        G = {g: f"<{BASE}graph/{g}>" for g in ("forensics", "platform", "factcheck", "provenance", "takedown")}
        RDF, XSD = "http://www.w3.org/1999/02/22-rdf-syntax-ns#", "http://www.w3.org/2001/XMLSchema#"
        FKG, AS, SDO, PROV = "https://example.org/fkg#", "https://www.w3.org/ns/activitystreams#", "https://schema.org/", "http://www.w3.org/ns/prov#"
        I = lambda x: f"<{x}>"; R = lambda kind, x: f"<{BASE}{kind}/{x}>"
        def lit(v, dtp=None, lang=None):
            s = str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            return f'"{s}"@{lang}' if lang else (f'"{s}"^^<{XSD}{dtp}>' if dtp else f'"{s}"')
        ts = lambda t: lit(t.replace(microsecond=0).isoformat().replace("+00:00", "Z"), "dateTime")
        a_ = I(RDF + "type"); out = []; cur = [None]
        w = lambda s, p, o, g: out.append((cur[0], f"{s} {p} {o} {G[g]} .\n"))
        img_iri = {iid: I(str(ni_iri(f"{self.seed}:{iid}"))) for iid in self.images}
        first_use = {}
        for n in self.notes:
            if n["img"]: first_use[n["img"]] = min(first_use.get(n["img"], n["t"]), n["t"])
        for iid, im in self.images.items():
            if iid not in first_use: continue
            if random.Random(f"{self.seed}:{iid}:cov").random() >= c["coverage"]: continue
            cur[0] = first_use[iid]
            Im = img_iri[iid]; key = hashlib.sha256(f"{self.seed}:{iid}".encode()).hexdigest()[:14]; z = self.img_latent(iid)
            w(Im, a_, I(FKG + "Image"), "forensics")
            regions = [(im["kind"] == "synthetic", im["content"], True)] if im["kind"] in ("synthetic", "camera") else [(False, "background", False), (True, im["content"], True)]
            pre_obs = None
            if c["leakfix"] and im["kind"] == "edit":
                o = self.observe_source(True, im["gen"], im["camera"] or r.choice(CAMERAS), z, len(im["chain"]))
                if o[0] == "camera": regions, pre_obs = [(True, im["content"], True)], {0: o}
                else: pre_obs = {1: o}
            any_synth = False
            for kx, (synth, content, obj) in enumerate(regions):
                Rg, S, D, C = (R(x, f"{key}-{kx}") for x in ("region", "source", "content", "compression"))
                w(Im, I(FKG + "hasRegion"), Rg, "forensics")
                for p, o in [(a_, I(FKG + "Region")), (I(FKG + "contained_in"), Im), (I(FKG + "produced_by"), S), (I(FKG + "depict"), D), (I(FKG + "compress_by"), C)]:
                    w(Rg, p, o, "forensics")
                if pre_obs and kx in pre_obs: kind, val, conf = pre_obs[kx]
                else: kind, val, conf = self.observe_source(synth, im["gen"], im["camera"] or r.choice(CAMERAS), z, len(im["chain"]))
                if c["leakfix"]: conf = self.nuisance_conf(iid, kx, synth, kind)
                any_synth |= kind == "synthetic"
                if kind == "synthetic":
                    lab = NAME_DRIFT[val] if random.Random(f"{self.seed}:{iid}:drift").random() < c["name_drift"] else val
                    w(S, a_, I(FKG + "AIGenerator"), "forensics"); w(S, I(FKG + "hasGeneratorModel"), lit(lab), "forensics")
                else:
                    w(S, a_, I(FKG + "CameraModel"), "forensics"); w(S, I(FKG + "hasCameraModel"), lit(val), "forensics")
                w(S, I(FKG + "hasConfidence"), lit(round(conf, 3), "float"), "forensics")
                prev = None; ops = self.observe_chain(im["chain"], z)
                for j, (t, v) in enumerate(ops):
                    M, P = R("op", f"{key}-{kx}-{j}"), R("param", f"{key}-{kx}-{j}")
                    w(Rg, I(FKG + "modified_by"), M, "forensics"); w(M, a_, I(FKG + t), "forensics"); w(M, I(FKG + "hasParameter"), P, "forensics")
                    w(P, a_, I(FKG + "Parameter"), "forensics"); w(P, I(FKG + "hasParameterName"), lit(OPS[t][0]), "forensics"); w(P, I(FKG + "hasParameterValue"), lit(round(v, 3), "float"), "forensics")
                    if prev: w(prev, I(FKG + "hasNext"), M, "forensics")
                    prev = M
                if not ops:
                    M = R("op", f"{key}-{kx}-none"); w(Rg, I(FKG + "modified_by"), M, "forensics"); w(M, a_, I(FKG + "NoPostProc"), "forensics")
                if im["pre"] or im["derived_from"]:
                    w(C, a_, I(FKG + "ReCompressed"), "forensics"); w(C, I(FKG + "hasReCompressed"), lit("true", "boolean"), "forensics")
                else:
                    qf = random.Random(f"{self.seed}:{iid}:q").choice([0.70, 0.75, 0.80, 0.85, 0.90, 0.95]) if c["leakfix"] else 0.85
                    w(C, a_, I(FKG + "LastCompressed"), "forensics"); w(C, I(FKG + "hasCompressionAlgorithm"), lit("JPEG"), "forensics"); w(C, I(FKG + "hasCompressionFactor"), lit(qf, "float"), "forensics")
                w(D, a_, I(FKG + "Content"), "forensics"); w(D, I(FKG + "hasObjectDescription"), lit(content), "forensics"); w(D, I(FKG + "hasObjectedness"), lit(str(obj).lower(), "boolean"), "forensics")
            rec, concl = R("record", key), R("conclusion", key)
            w(rec, a_, I(FKG + "ForensicRecord"), "forensics"); w(rec, I(FKG + "aboutImage"), Im, "forensics"); w(rec, I(FKG + "hasConclusion"), concl, "forensics")
            w(concl, a_, I(FKG + "ForensicConclusion"), "forensics"); w(concl, I(FKG + "aboutImage"), Im, "forensics")
            w(concl, I(FKG + "verdict"), I(FKG + ("Manipulated" if any_synth else "Authentic")), "forensics")
        for a in self.accounts:
            cur[0] = a["created"]; A = R("actor", a["id"])
            w(A, a_, I(AS + "Person"), "platform"); w(A, I(AS + "preferredUsername"), lit(a["username"]), "platform"); w(A, I(AS + "published"), ts(a["created"]), "platform")
        for n in self.notes:
            cur[0] = n["t"]; N, act, A = R("note", n["id"]), R("activity", "create-" + n["id"]), R("actor", n["acct"])
            for s, p, o in [(act, a_, I(AS + "Create")), (act, I(AS + "actor"), A), (act, I(AS + "object"), N), (act, I(AS + "published"), ts(n["t"])),
                            (N, a_, I(AS + "Note")), (N, I(AS + "attributedTo"), A), (N, I(AS + "published"), ts(n["t"])), (N, I(AS + "content"), lit(n["text"], lang="en"))]:
                w(s, p, o, "platform")
            if n["img"]: w(N, I(AS + "attachment"), img_iri[n["img"]], "platform"); w(img_iri[n["img"]], a_, I(AS + "Image"), "platform")
        for an in self.announces:
            cur[0] = an["t"]; act = R("activity", "announce-" + hashlib.sha256(f"{self.seed}:ann:{an['acct']}:{an['note']}:{an['t']}".encode()).hexdigest()[:12])
            for s, p, o in [(act, a_, I(AS + "Announce")), (act, I(AS + "actor"), R("actor", an["acct"])), (act, I(AS + "object"), R("note", an["note"])), (act, I(AS + "published"), ts(an["t"]))]:
                w(s, p, o, "platform")
        opaque = {cid: hashlib.sha256(f"{self.seed}:{cid}".encode()).hexdigest()[:10] for cid in self.claims}
        first_seen = {}
        for n in self.notes:
            if n["claim"]: first_seen[n["claim"]] = min(first_seen.get(n["claim"], n["t"]), n["t"])
        for cid, (text, rating, label) in self.claims.items():
            cur[0] = first_seen.get(cid, self.events[self.claim_event[cid]])
            Cl = R("claim", opaque[cid]); w(Cl, a_, I(SDO + "Claim"), "factcheck"); w(Cl, I(SDO + "text"), lit(text), "factcheck")
            w(Cl, I(SDO + "about"), R("topic", self.claim_topic[cid]), "factcheck")  # fact-checkers' topic tag
            if cid not in self.reviewed: continue
            cur[0] = self.review_t[cid]; Rv, Rt = R("review", opaque[cid]), R("rating", opaque[cid])
            for s, p, o in [(Rv, a_, I(SDO + "ClaimReview")), (Rv, I(SDO + "itemReviewed"), Cl), (Rv, I(SDO + "datePublished"), lit(self.review_t[cid].date().isoformat(), "date")),
                            (Rv, I(SDO + "reviewRating"), Rt), (Rt, a_, I(SDO + "Rating")), (Rt, I(SDO + "ratingValue"), lit(rating, "integer")), (Rt, I(SDO + "alternateName"), lit(label))]:
                w(s, p, o, "factcheck")
        cal = c["claim_match"] == "calibrated"
        base_miss = (0.12 if c["text_mode"] == "pool" else 0.30) if cal else (0.25 if c["text_mode"] == "paraphrase" else 0.0)
        topical = [n for n in self.notes if n["claim"]]
        for n in self.notes:
            cur[0] = n["t"]; miss = 1 - (1 - base_miss) * (1 - 0.5 * e)
            if n["claim"] and (n.get("debunk") and r.random() < c["debunk_link_p"] or not n.get("debunk") and r.random() >= miss):
                w(R("claim", opaque[n["claim"]]), I(SDO + "appearance"), R("note", n["id"]), "factcheck")
                if cal and r.random() < 0.12:
                    w(R("claim", opaque[n["claim"]]), I(SDO + "appearance"), R("note", r.choice(topical)["id"]), "factcheck")
            if c["stance"] and n["claim"]:
                sr = random.Random(f"{self.seed}:{n['id']}:stance").random()
                if sr < (c["stance_recall"] if n.get("debunk") else c["stance_fpr"]): w(R("note", n["id"]), f"<{BASE}stance>", f"<{BASE}Refutes>", "factcheck")
            if n["img"] and self.images[n["img"]]["derived_from"]:
                im = self.images[n["img"]]; rec = c["debunk_prov_recall"] if n.get("debunk") else c["prov_recall"]
                if r.random() < rec * (1 - 0.5 * e): w(img_iri[n["img"]], I(PROV + "wasDerivedFrom"), img_iri[im["derived_from"]], "provenance")
        # takedown reports: operator attribution and removed accounts, published with a lag (cf. Meta adversarial threat reports, X IO archive)
        opq = lambda oi: hashlib.sha256(f"{self.seed}:operator:{oi}".encode()).hexdigest()[:10]
        for k, td in enumerate(self.takedowns):
            cur[0] = td["t"]; T = R("takedown", hashlib.sha256(f"{self.seed}:td:{k}".encode()).hexdigest()[:10])
            w(T, a_, f"<{BASE}Takedown>", "takedown"); w(T, f"<{BASE}operator>", R("operator", opq(td["op"])), "takedown"); w(T, f"<{BASE}date>", ts(td["t"]), "takedown")
            for aid in td["accounts"]: w(T, f"<{BASE}removed>", R("actor", aid), "takedown")
        self.op_iri = {oi: f"{BASE}operator/{opq(oi)}" for oi in range(len(c["operators"]))}
        out.sort(key=lambda x: x[0]); self.lines = out
        return {"images": len(self.images), "notes": len(self.notes), "announces": len(self.announces), "accounts": len(self.accounts), "quads": len(out)}

    def write_snapshot(self, path, T, extra=(), since=None):  # all records visible at T (optionally only those created after `since`)
        n = 0
        with open(path, "w") as f:
            for t, line in self.lines:
                if t > T: break
                if since is None or t >= since: f.write(line); n += 1
            for line in extra: f.write(line); n += 1
        return n

    def truth(self):
        acc = {BASE + "actor/" + a["id"]: a for a in self.accounts}
        return {"roles": {k: a["role"] for k, a in acc.items()}, "op": {k: a["campaign"] for k, a in acc.items() if a["campaign"] is not None},
                "wave_event": {k: a["wave"] for k, a in acc.items() if a["wave"] is not None}}
