# Stress-test generator: the v2 scenario generalized with scale, several campaigns, adaptive adversaries, extra decoys
# and realism models (heavy-tailed activity, bursty timing, calibrated and correlated detector errors, partial records).
# Writes N-Quads (same 4 named graphs and record shapes as generate.py) + ground-truth JSON. All data is synthetic.
import copy, hashlib, json, math, random, sys
from datetime import timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate import (GENERATORS, SIBLING, CAMERAS, OPS, CAMPAIGN_CHAIN, CLAIMS, CAMPAIGN_TEXT, CAMPAIGN_CONTENT, ORGANIC_TEXT,
                      ORGANIC_CONTENT, FLOOD_TEXT, BELIEVER_TEXT, RUMOR_TEXT, BRAND_TEXT, ADJ, NOUN, ni_iri, dt, rand_time, BASE)

EXTRA_CLAIMS = {  # additional fictional false claims for concurrent campaigns
    "C4": ("Council contractors were paid to sabotage the Brennerton levee.", ["They PAID contractors to weaken the levee. Follow the money.", "The levee didn't fail, it was sabotaged by council contractors.", "Levee sabotage: council contractors got paid weeks before the flood."]),
    "C5": ("Insurers told adjusters to deny every flood claim from Brennerton's east side.", ["Insurers ordered adjusters to deny ALL east side flood claims.", "Leaked: insurance memo says deny every east side claim.", "East side families, your flood claims will be denied. It's policy now."]),
    "C6": ("Rescue crews were ordered to evacuate west-side residents first.", ["Rescue boats were told to go west side first. East side waited.", "They prioritized the rich west side for rescues. Look.", "Orders came down: west side gets rescued first."]),
    "C7": ("Brennerton's water plant was shut down on purpose to force evacuations.", ["The water plant was shut off deliberately to force people out.", "No water = forced evacuation. They planned this.", "Water plant shutdown was intentional, not flood damage."]),
    "C8": ("Relief cash cards are being confiscated at police checkpoints.", ["Police are confiscating relief cash cards at checkpoints!", "Checkpoints on Route 9 taking people's relief cards.", "Don't carry your relief card, they're seizing them at checkpoints."]),
}
PREFIX = ["", "", "BREAKING: ", "Wake up. ", "Share this. ", "Why is nobody talking about this? ", "Thread: "]
SUFFIX = ["", "", " #Brennerton", " #BrennertonFlood", " Spread the word.", " Retweet before they delete it.", " 🙏"]
# Calibrated detector profile: per-generator synthetic-detection rates measured by the FSD detector on the curated
# in-the-wild datasets (agentic-data-curation, internal); SDXL and FLUX.1 [schnell] have no measurement and use assumed values.
FSD_TPR = {"FLUX.1 [dev]": .815, "FLUX.1 [schnell]": .815, "Midjourney v7": .907, "SDXL": .85, "GPT-Image 1": .984, "Seedream 4": .213, "Nano Banana": .972}
NAME_DRIFT = {"FLUX.1 [dev]": "black-forest-labs/FLUX.1-dev", "FLUX.1 [schnell]": "black-forest-labs/FLUX.1-schnell", "Midjourney v7": "midjourney-v7",
              "SDXL": "stabilityai/stable-diffusion-xl-base-1.0", "GPT-Image 1": "openai/gpt-image-1", "Seedream 4": "bytedance/seedream-4.0", "Nano Banana": "google/gemini-2.5-flash-image"}

CAMPAIGN = dict(n_core=10, n_amp=2, claims=["C1", "C2", "C3"], gens=["FLUX.1 [dev]"], chain=CAMPAIGN_CHAIN, param_mode="fixed", jitter=0.0,
                op_shuffle=False, aged=False, organic_reposts=False, core_reposts=True, start=(2026, 10, 3, 6), window_h=48, posts=(3, 5), edit_frac=0.3,
                hours=None, claimless_frac=0.2, mimic=False)
DEFAULT = dict(scale=1, campaigns=[CAMPAIGN], brand_per_scale=1, believer_frac=20 / 150, reuploader_frac=6 / 150, rumor_frac=10 / 150,
               debunkers=0, debunk_link_p=0.5, debunk_prov_recall=0.7, text_mode="pool", activity="uniform", timing="uniform",
               detector="eta", rho=0.0, bias_sd=0.0, coverage=1.0, fc_coverage=1.0, name_drift=0.0, entity_vocab=False,
               ttp_index=False, platform="v2", p_preset=0.0, n_presets=5, p_habit=0.0, claim_match="eta", prov_recall=1.0, fc_latency_h=15.3, as_of=None, leakfix=False, fc_stream=False,
               stance=False, stance_recall=0.85, stance_fpr=0.05)


def make_cfg(**kw):
    cfg = copy.deepcopy(DEFAULT)
    camp_kw = kw.pop("campaign", {})
    cfg.update(kw)
    if "campaigns" not in kw: cfg["campaigns"] = [dict(CAMPAIGN, **camp_kw)]
    else: cfg["campaigns"] = [dict(CAMPAIGN, **c) for c in kw["campaigns"]]
    return cfg


def sigmoid(x): return 1 / (1 + math.exp(-x))
def logit(p): p = min(max(p, 1e-6), 1 - 1e-6); return math.log(p / (1 - p))


class StressScenario:
    def __init__(self, cfg, seed, eta):
        self.cfg, self.seed, self.eta = cfg, seed, eta
        self.truth_rng = random.Random(seed)
        self.rng = random.Random(seed * 1000 + int(round(eta * 100)))
        self.accounts, self.notes, self.announces, self.images, self.ids = [], [], [], {}, set()
        self.claims = {cid: (t, 1 if lab == "False" else 5, lab) for cid, (t, _, lab) in CLAIMS.items()}
        self.claim_text = {cid: list(v) for cid, v in CAMPAIGN_TEXT.items() if cid}
        for cid, (t, texts) in EXTRA_CLAIMS.items():
            self.claims[cid] = (t, 1, "False"); self.claim_text[cid] = texts
        self.reviewed = set()

    def uid(self, rng, prefix):
        while True:
            x = prefix + "".join(rng.choice("0123456789abcdef") for _ in range(10))
            if x not in self.ids: self.ids.add(x); return x

    def add_account(self, role, created, campaign=None):
        r = self.truth_rng
        a = {"id": self.uid(r, "u"), "username": f"{r.choice(ADJ)}_{r.choice(NOUN)}{r.randint(1, 9999)}", "created": created, "role": role, "campaign": campaign,
             "tz": r.choice([-8, -7, -6, -5, -5, -5, -4, 0, 1])}
        self.accounts.append(a); return a

    def new_image(self, kind, gen=None, chain=None, camera=None, pre=True, content="", derived_from=None, extra_ops=()):
        iid = self.uid(self.truth_rng, "img")
        self.images[iid] = {"kind": kind, "gen": gen, "chain": list(chain or []) + list(extra_ops), "camera": camera, "pre": pre, "content": content, "derived_from": derived_from}
        return iid

    @staticmethod
    def random_chain(r, p_none):
        if r.random() < p_none: return []
        n = r.choices([1, 2, 3], weights=[.6, .3, .1])[0]
        return [(t, round(r.uniform(*OPS[t][1]), 2)) for t in r.sample(list(OPS), n)]

    def organic_chain(self, acct, p_none):  # realism: popular app presets and personal habits, else a random chain (v2)
        r, c = self.truth_rng, self.cfg
        if c["p_preset"] and r.random() < c["p_preset"]: return list(r.choices(self.presets, weights=[1 / (i + 1) for i in range(len(self.presets))])[0])
        if acct is not None and c["p_habit"] and r.random() < c["p_habit"]:
            if "habit" not in acct: acct["habit"] = self.random_chain(r, 0.0)
            return list(acct["habit"])
        return self.random_chain(r, p_none)

    def organic_image(self, content, acct=None):
        r = self.truth_rng
        if r.random() < 0.6: return self.new_image("camera", camera=r.choice(CAMERAS), chain=self.organic_chain(acct, 0.7), content=content)
        gen = (acct.get("gen") if acct else None) or r.choices(list(GENERATORS), weights=list(GENERATORS.values()))[0]
        if acct is not None and self.cfg["p_habit"] and "gen" not in acct and r.random() < self.cfg["p_habit"]: acct["gen"] = gen  # habitual generator
        return self.new_image("synthetic", gen=gen, chain=self.organic_chain(acct, 0.5), pre=r.random() < 0.5, content=content)

    def post(self, acct, t, text, img=None, claim=None):
        n = {"id": self.uid(self.truth_rng, "n"), "acct": acct["id"], "t": t, "text": text, "img": img, "claim": claim}
        self.notes.append(n); return n

    # ---------- realism helpers ----------
    def n_posts(self, lo, hi):  # uniform (v2) or heavy-tailed lognormal activity
        r = self.truth_rng
        if self.cfg["activity"] == "heavy": return max(1, min(200, int(r.lognormvariate(1.0, 1.0))))
        return r.randint(lo, hi)

    def times(self, acct, n, t0, t1):  # uniform (v2) or bursty sessions with a diurnal cycle in the account's time zone
        r = self.truth_rng
        if self.cfg["timing"] == "loguniform":  # inter-event times P(tau) ~ 1/tau between 1 min and 7 days (alpha ~ 1, Barabasi 2005)
            out, t, span = [], rand_time(r, t0, t1), (t1 - t0)
            while len(out) < n:
                h = (t.hour + acct["tz"]) % 24
                if r.random() < 0.15 + 0.85 * (0.5 + 0.5 * math.cos((h - 20) / 24 * 2 * math.pi)): out.append(t)
                t += timedelta(minutes=math.exp(r.uniform(0, math.log(7 * 1440))))
                if t > t1: t = t0 + (t - t1) % span
            return out
        if self.cfg["timing"] != "bursty": return [rand_time(r, t0, t1) for _ in range(n)]
        out, span = [], (t1 - t0).total_seconds()
        while len(out) < n:
            while True:  # session start, accepted with diurnal weight (peak ~20:00 local, trough ~04:00)
                t = t0 + timedelta(seconds=r.uniform(0, span)); h = (t.hour + acct["tz"]) % 24
                if r.random() < 0.15 + 0.85 * (0.5 + 0.5 * math.cos((h - 20) / 24 * 2 * math.pi)): break
            for _ in range(min(n - len(out), 1 + int(r.expovariate(0.7)))):
                out.append(t); t += timedelta(minutes=r.expovariate(1 / 8))
        return [min(x, t1) for x in out]

    def repost_delay(self, lo_min, hi_min):  # v2: uniform; calibrated: median 1 h, 75 % within 1 day (Kwak et al. 2010)
        r = self.truth_rng
        if self.cfg["platform"] != "calibrated": return timedelta(minutes=r.uniform(lo_min, hi_min))
        return timedelta(hours=min(336.0, max(1 / 60, math.exp(r.gauss(0, 4.71)))))

    def campaign_time(self, camp, t0, t1):
        r = self.truth_rng
        if not camp["hours"]: return rand_time(r, t0, t1)
        shifts, tz = camp["hours"]  # operator shifts in local time, e.g. ([(9.5, 12), (13.5, 17.5), (19, 22)], +8)
        while True:
            t = rand_time(r, t0, t1); h = (t.hour + t.minute / 60 + tz) % 24
            if any(lo <= h < hi for lo, hi in shifts): return t

    def text_for(self, claim, base_pool):
        r = self.truth_rng
        base = r.choice(base_pool)
        if self.cfg["text_mode"] == "pool": return base
        return (r.choice(PREFIX) + base + r.choice(SUFFIX)).strip()

    def campaign_chain(self, camp, acct_chain):
        r = self.truth_rng; m = camp["param_mode"]
        if camp["mimic"]: ch = list(self.presets[0])  # hide in the crowd: the most popular app preset
        elif m == "fixed": ch = list(camp["chain"])
        elif m == "jitter": ch = [(t, round(min(max(v * (1 + r.gauss(0, camp["jitter"])), OPS[t][1][0]), OPS[t][1][1]), 3)) for t, v in camp["chain"]]
        elif m == "uniform": ch = [(t, round(r.uniform(*OPS[t][1]), 3)) for t, _ in camp["chain"]]
        elif m == "pool": ch = [(t, round(r.uniform(*OPS[t][1]), 3)) for t in r.sample(list(OPS), r.randint(2, 3))]
        elif m == "per_account": ch = list(acct_chain)
        else: raise ValueError(m)
        if camp["op_shuffle"]: r.shuffle(ch)
        return ch

    # ---------- ground-truth world ----------
    def build_world(self):
        r, c = self.truth_rng, self.cfg
        k = c["scale"]; n_org = int(150 * k)
        pr = random.Random(f"{self.seed}:presets")  # separate stream so worlds without presets are unchanged
        self.presets = [[(t, round(pr.uniform(*OPS[t][1]), 2)) for t in pr.sample(list(OPS), 2)] for _ in range(c["n_presets"])]
        o0, o1 = dt(2026, 9, 22), dt(2026, 10, 6, 23)
        organic = [self.add_account("organic", rand_time(r, dt(2026, 1, 1), dt(2026, 10, 1)) if r.random() < 0.15 else rand_time(r, dt(2012, 1, 1), dt(2025, 12, 31))) for _ in range(n_org)]
        r.shuffle(organic)
        nb, nr, nm = round(c["believer_frac"] * n_org), round(c["reuploader_frac"] * n_org), round(c["rumor_frac"] * n_org)
        believers, reuploaders, rumor = organic[:nb], organic[nb:nb + nr], organic[nb + nr:nb + nr + nm]
        for a in believers: a["role"] = "organic_believer"
        for a in reuploaders: a["role"] = "organic_reuploader"
        for a in rumor: a["role"] = "organic_rumor"
        # campaigns
        camp_notes, all_claims, members = [], [], []
        for ci, camp in enumerate(c["campaigns"]):
            cw0 = dt(*camp["start"]); cw1 = cw0 + timedelta(hours=camp["window_h"])
            c0, c1 = (dt(2014, 1, 1), dt(2025, 12, 31)) if camp["aged"] else (cw0 - timedelta(days=23), cw0 - timedelta(days=19))
            core = [self.add_account("campaign_core", rand_time(r, c0, c1), ci) for _ in range(camp["n_core"])]
            amps = [self.add_account("campaign_amplifier", rand_time(r, c0, c1), ci) for _ in range(camp["n_amp"])]
            members.append((camp, core, amps)); all_claims += camp["claims"]
            for a in core + amps:  # persona filler
                f0 = o0 if camp["aged"] else a["created"] + timedelta(days=1)
                for t in self.times(a, r.randint(1, 3), f0, cw0 - timedelta(hours=12)):
                    self.post(a, t, r.choice(ORGANIC_TEXT), self.organic_image(r.choice(ORGANIC_CONTENT)) if r.random() < 0.6 else None)
            mine = []
            for a in core:
                acct_chain = [(t, round(r.uniform(*OPS[t][1]), 3)) for t in r.sample(list(OPS), r.randint(2, 3))]
                for _ in range(r.randint(*camp["posts"])):
                    claim = r.choice(camp["claims"]) if r.random() >= camp["claimless_frac"] else None
                    content = r.choice(CAMPAIGN_CONTENT.get(claim, CAMPAIGN_CONTENT[None]) if claim in CAMPAIGN_CONTENT else ["flooded street", "crowd", "city skyline", "official at podium"])
                    gen, chain = r.choice(camp["gens"]), self.campaign_chain(camp, acct_chain)
                    img = self.new_image("synthetic" if r.random() >= camp["edit_frac"] else "edit", gen=gen, chain=chain, camera=r.choice(CAMERAS), content=content)
                    text = self.text_for(claim, self.claim_text[claim] if claim else CAMPAIGN_TEXT[None])
                    n = self.post(a, self.campaign_time(camp, cw0, cw1), text, img, claim); mine.append(n)
            for a in core:  # in-network amplification among core personas (core_reposts=False: an operator that avoids it)
                if not camp["core_reposts"]: continue
                for n in r.sample([n for n in mine if n["acct"] != a["id"]], min(r.randint(2, 5), len(mine) - 1)):
                    self.announces.append({"acct": a["id"], "note": n["id"], "t": n["t"] + timedelta(minutes=r.uniform(5, 600))})
            for a in amps:
                for _ in range(r.randint(2, 3)):
                    claim = r.choice(camp["claims"])
                    self.post(a, self.campaign_time(camp, cw0, cw1), self.text_for(claim, self.claim_text[claim]), None, claim)
                for n in r.sample(mine, min(r.randint(6, 10), len(mine))):
                    self.announces.append({"acct": a["id"], "note": n["id"], "t": n["t"] + timedelta(minutes=r.uniform(5, 300))})
            camp_notes += mine
        # brand campaigns: coordinated, shared pipeline, no fact-checked claims (one per scale unit)
        brand = []
        for b in range(max(1, int(round(c["brand_per_scale"] * k)))):
            gen = "GPT-Image 1" if b == 0 else r.choices(list(GENERATORS), weights=list(GENERATORS.values()))[0]
            chain = [("Resampling", 0.50), ("Sharpening", 0.80)] if b == 0 else [(t, round(r.uniform(*OPS[t][1]), 2)) for t in r.sample(list(OPS), 2)]
            bw0 = rand_time(r, dt(2026, 9, 23), dt(2026, 10, 5))
            for _ in range(6):
                a = self.add_account("brand", rand_time(r, dt(2019, 1, 1), dt(2023, 12, 31))); brand.append(a)
                for _ in range(4):
                    img = self.new_image("synthetic", gen=gen, chain=chain, pre=False, content=r.choice(["hiker in jacket", "mountain trail", "product shot"]))
                    self.post(a, rand_time(r, bw0, bw0 + timedelta(hours=36)), r.choice(BRAND_TEXT), img)
        # organic background
        for a in organic:
            for t in self.times(a, self.n_posts(2, 6), o0, o1):
                self.post(a, t, r.choice(ORGANIC_TEXT), self.organic_image(r.choice(ORGANIC_CONTENT), a) if r.random() < 0.85 else None)
            if r.random() < 0.15:
                self.post(a, rand_time(r, dt(2026, 10, 2), o1), r.choice(FLOOD_TEXT), self.organic_image("flooded street", a) if r.random() < 0.7 else None, "T1")
        sigma = 1.5 if c["activity"] == "heavy" else 1.0
        if c["platform"] == "calibrated": pop = {a["id"]: min(1e4, r.paretovariate(1.276)) for a in organic + brand}  # follower tail exponent 2.276 (Kwak et al. 2010)
        else: pop = {a["id"]: r.lognormvariate(0, sigma) for a in organic + brand}
        pop.update({a["id"]: 3 * pop[a["id"]] for a in brand})
        pool = [n for n in self.notes if n["acct"] in pop]; weights = [pop[n["acct"]] for n in pool]
        for a in organic:
            kk = self.n_posts(0, 0) - 1 if c["activity"] == "heavy" else r.choice([0, 0, 1, 1, 2, 3, 4, 6])
            for n in r.choices(pool, weights=weights, k=kk):
                if n["acct"] != a["id"]: self.announces.append({"acct": a["id"], "note": n["id"], "t": n["t"] + self.repost_delay(5, 2880)})
        for camp, core, amps in members:
            if camp["organic_reposts"]:
                for a in core + amps:
                    for n in r.choices(pool, weights=weights, k=r.randint(4, 9)):
                        self.announces.append({"acct": a["id"], "note": n["id"], "t": n["t"] + timedelta(minutes=r.uniform(5, 2880))})
        claim_notes = [n for n in camp_notes if n["claim"]]
        first = min(n["t"] for n in camp_notes); last = max(n["t"] for n in camp_notes)
        for a in believers:
            for _ in range(r.randint(1, 2)):
                src = r.choice(claim_notes); claim = src["claim"]
                img = self.organic_image(r.choice(["flooded street", "rain clouds", "city street"]), a) if r.random() < 0.7 else None
                pool_t = BELIEVER_TEXT.get(claim, [f"Is this real? {self.claims[claim][0]}", f"Can anyone confirm? Heard that {self.claims[claim][0].lower()}"])
                self.post(a, src["t"] + timedelta(hours=r.uniform(1, 30)), r.choice(pool_t), img, claim)
            for n in r.sample(camp_notes, min(r.randint(1, 3), len(camp_notes))):
                self.announces.append({"acct": a["id"], "note": n["id"], "t": n["t"] + timedelta(minutes=r.uniform(30, 1440))})
        for a in reuploaders:
            src = r.choice(claim_notes); s = self.images[src["img"]]
            img = self.new_image(s["kind"], gen=s["gen"], chain=s["chain"], camera=s["camera"], content=s["content"], derived_from=src["img"])
            pool_t = BELIEVER_TEXT.get(src["claim"], [f"Is this real? {self.claims[src['claim']][0]}"])
            self.post(a, src["t"] + timedelta(hours=r.uniform(2, 30)), r.choice(pool_t), img, src["claim"])
        for a in rumor:
            for _ in range(r.randint(1, 2)):
                self.post(a, rand_time(r, dt(2026, 9, 25), dt(2026, 10, 1)), r.choice(RUMOR_TEXT), self.organic_image(r.choice(["glass of water", "kitchen sink"])) if r.random() < 0.6 else None, "O1")
        # debunkers: newsroom accounts that post campaign images (cropped, with a house resize) to say they are fake
        for _ in range(c["debunkers"]):
            a = self.add_account("debunker", rand_time(r, dt(2012, 1, 1), dt(2020, 12, 31)))
            for _ in range(r.randint(1, 3)):
                src = r.choice(claim_notes); s = self.images[src["img"]]
                img = self.new_image(s["kind"], gen=s["gen"], chain=s["chain"], camera=s["camera"], content=s["content"], derived_from=src["img"], extra_ops=[("Resampling", 0.66)])
                n = self.post(a, src["t"] + timedelta(hours=r.uniform(6, 48)), f"FALSE: this image claiming that {self.claims[src['claim']][0].lower()} is AI-generated. Our analysis:", img, src["claim"])
                n["debunk"] = True
        self.t_first, self.t_last = first, last
        if c["leakfix"]: self.fix_leaks()
        # which claims get a published fact-check
        first_seen = {}
        for n in self.notes:
            if n["claim"]: first_seen[n["claim"]] = min(first_seen.get(n["claim"], n["t"]), n["t"])
        self.review_t, lr = {}, random.Random(f"{self.seed}:fc-latency")  # own stream keeps worlds comparable across versions
        for cid in self.claims:
            # fc_stream: per-claim draw, so which claims get a fact-check no longer shifts when other parts of the world change
            u = random.Random(f"{self.seed}:fc:{cid}").random() if c["fc_stream"] else r.random()
            if cid in ("T1", "O1") or u < c["fc_coverage"]:
                self.reviewed.add(cid)  # latency: lognormal, median fc_latency_h (Community Notes median 15.3 h; Hoaxy ~13 h lag)
                self.review_t[cid] = first_seen.get(cid, dt(2026, 9, 25)) + timedelta(hours=c["fc_latency_h"] * math.exp(lr.gauss(0, 1.0)))
        r.shuffle(self.notes)

    def fix_leaks(self):  # leak audit fixes (eval/leak_audit.py); own RNG stream so the accounts, posts and claims are unchanged
        lr = random.Random(f"{self.seed}:leakfix")
        topical = sorted({x for v in CAMPAIGN_CONTENT.values() for x in v} | {"flooded street", "crowd", "city skyline", "official at podium", "rain clouds"})
        role = {a["id"]: a["role"] for a in self.accounts}
        for n in self.notes:
            im = self.images.get(n["img"]) if n["img"] else None
            if im is None or im["derived_from"] or not role[n["acct"]].startswith("organic"): continue
            # flood-topic posts by organic accounts depict the same scenes the campaign fakes (content no longer marks the campaign)
            if n["claim"] in self.claim_text or n["claim"] == "T1": im["content"] = lr.choice(topical)
            elif n["t"] >= dt(2026, 10, 2) and lr.random() < 0.35: im["content"] = lr.choice(topical)  # residents photograph the flood too (assumed share)
            # organic AI edits (a real photo with one AI-edited object), so a two-region layout no longer marks the campaign
            if im["kind"] == "camera" and lr.random() < 0.12:
                im["kind"], im["gen"] = "edit", lr.choices(list(GENERATORS), weights=list(GENERATORS.values()))[0]

    def nuisance_conf(self, iid, kx, true_synth, kind):  # overlapping confidences (leakfix): correct and wrong calls differ on average only
        mu = {(True, "synthetic"): 0.80, (False, "synthetic"): 0.72, (False, "camera"): 0.82, (True, "camera"): 0.74}[(true_synth, kind)]
        return min(0.99, max(0.5, random.Random(f"{self.seed}:{iid}:{kx}:conf").gauss(mu, 0.10)))

    # ---------- noisy observation ----------
    def img_latent(self, iid):  # per-image difficulty shared by all of that image's detector outputs (correlated errors)
        return random.Random(f"{self.seed}:{iid}:z").gauss(0, 1)

    def p(self, base, z):
        rho = self.cfg["rho"]
        return base if rho == 0 or base <= 0 else sigmoid(logit(base) + rho * z)

    def observe_source(self, true_synth, gen, camera, z, n_ops):
        r, e, cal = self.rng, self.eta, self.cfg["detector"] == "calibrated"
        if true_synth:
            miss = 1 - FSD_TPR[gen] * (1 - 0.04 * n_ops) if cal else 0.0  # each processing op costs ~4 % sensitivity (assumed)
            if r.random() < self.p(1 - (1 - miss) * (1 - 0.3 * e), z): return ("camera", r.choice(CAMERAS), r.uniform(0.5, 0.8))
            g = gen
            if r.random() < self.p(1 - (1 - (0.08 if cal else 0)) * (1 - 0.5 * e), z):
                g = SIBLING[gen] if r.random() < 0.7 else r.choice([x for x in GENERATORS if x != gen])
            return ("synthetic", g, max(0.5, r.uniform(0.85, 0.99) - 0.5 * e * r.random()))
        if r.random() < self.p(1 - (1 - (0.03 if cal else 0)) * (1 - 0.1 * e), z):
            return ("synthetic", r.choices(list(GENERATORS), weights=list(GENERATORS.values()))[0], r.uniform(0.5, 0.75))
        return ("camera", camera, max(0.5, r.uniform(0.85, 0.99) - 0.5 * e * r.random()))

    def observe_chain(self, chain, z):
        r, e, cal = self.rng, self.eta, self.cfg["detector"] == "calibrated"
        out, n = [], len(chain)
        for pos, (t, v) in enumerate(chain):
            masked = n - 1 - pos  # ops applied earlier are partly masked by later ones (assumed linear growth)
            miss = 1 - (1 - ((0.05 + 0.08 * masked) if cal else 0)) * (1 - 0.5 * e)
            if r.random() < self.p(miss, z): continue
            sd = (0.03 + 0.03 * masked if cal else 0.02) + 0.15 * e
            out.append((t, max(0.05, v * (1 + self.bias[t]) * (1 + r.gauss(0, sd)))))
        if r.random() < self.p(1 - (1 - (0.05 if cal else 0)) * (1 - 0.2 * e), z):
            t = r.choice(list(OPS)); out.insert(r.randint(0, len(out)), (t, r.uniform(*OPS[t][1])))
        return out

    # ---------- N-Quads ----------
    def write_nquads(self, path):
        r, e, c = self.rng, self.eta, self.cfg
        self.bias = {t: random.Random(f"{self.seed}:bias:{t}").gauss(0, c["bias_sd"]) for t in OPS}  # detector calibration bias, shared by all images
        G = {g: f"<{BASE}graph/{g}>" for g in ("forensics", "platform", "factcheck", "provenance", "vocab", "index")}
        RDF, XSD = "http://www.w3.org/1999/02/22-rdf-syntax-ns#", "http://www.w3.org/2001/XMLSchema#"
        FKG, AS, SDO, PROV = "https://example.org/fkg#", "https://www.w3.org/ns/activitystreams#", "https://schema.org/", "http://www.w3.org/ns/prov#"
        I = lambda x: f"<{x}>"
        R = lambda kind, x: f"<{BASE}{kind}/{x}>"
        def lit(v, dtp=None, lang=None):
            s = str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            return f'"{s}"@{lang}' if lang else (f'"{s}"^^<{XSD}{dtp}>' if dtp else f'"{s}"')
        ts = lambda t: lit(t.replace(microsecond=0).isoformat().replace("+00:00", "Z"), "dateTime")
        a_ = I(RDF + "type")
        f = open(path, "w"); w = lambda s, p, o, g: f.write(f"{s} {p} {o} {G[g]} .\n")
        img_iri = {iid: I(str(ni_iri(f"{self.seed}:{iid}"))) for iid in self.images}
        gen_label = lambda g, iid: NAME_DRIFT[g] if random.Random(f"{self.seed}:{iid}:drift").random() < c["name_drift"] else g
        T = c["as_of"]
        notes = [n for n in self.notes if T is None or n["t"] <= T]
        visible_img = {n["img"] for n in notes if n["img"]}
        announces = [an for an in self.announces if T is None or an["t"] <= T]
        reviewed = {cid for cid in self.reviewed if T is None or self.review_t[cid] <= T}
        analyzed = 0
        for iid, im in self.images.items():
            if iid not in visible_img: continue
            if random.Random(f"{self.seed}:{iid}:cov").random() >= c["coverage"]: continue
            analyzed += 1
            Im = img_iri[iid]; key = hashlib.sha256(f"{self.seed}:{iid}".encode()).hexdigest()[:14]; z = self.img_latent(iid)
            w(Im, a_, I(FKG + "Image"), "forensics")
            regions = [(im["kind"] == "synthetic", im["content"], True)] if im["kind"] in ("synthetic", "camera") else [(False, "background", False), (True, im["content"], True)]
            pre_obs = None
            if c["leakfix"] and im["kind"] == "edit":  # report a second region only when the edited part is detected
                o = self.observe_source(True, im["gen"], im["camera"] or r.choice(CAMERAS), z, len(im["chain"]))
                if o[0] == "camera": regions, pre_obs = [(True, im["content"], True)], {0: o}
                else: pre_obs = {1: o}
            any_synth = False
            for kx, (synth, content, obj) in enumerate(regions):
                Rg, S, D, C = (R(x, f"{key}-{kx}") for x in ("region", "source", "content", "compression"))
                for p, o in [(FKG + "hasRegion", Rg)]: w(Im, I(p), o, "forensics")
                for p, o in [(a_, I(FKG + "Region")), (I(FKG + "contained_in"), Im), (I(FKG + "produced_by"), S), (I(FKG + "depict"), D), (I(FKG + "compress_by"), C),
                             (I(FKG + "localizationStatus"), I(FKG + "LocalizationNotProvided"))]:
                    w(Rg, p, o, "forensics")
                if pre_obs and kx in pre_obs: kind, val, conf = pre_obs[kx]
                else: kind, val, conf = self.observe_source(synth, im["gen"], im["camera"] or r.choice(CAMERAS), z, len(im["chain"]))
                if c["leakfix"]: conf = self.nuisance_conf(iid, kx, synth, kind)
                any_synth |= kind == "synthetic"
                if kind == "synthetic":
                    w(S, a_, I(FKG + "AIGenerator"), "forensics"); w(S, I(FKG + "hasGeneratorModel"), lit(gen_label(val, iid)), "forensics")
                else:
                    w(S, a_, I(FKG + "CameraModel"), "forensics"); w(S, I(FKG + "hasCameraModel"), lit(val), "forensics")
                w(S, I(FKG + "hasConfidence"), lit(round(conf, 3), "float"), "forensics")
                prev = None
                ops = self.observe_chain(im["chain"], z)
                for j, (t, v) in enumerate(ops):
                    M, P = R("op", f"{key}-{kx}-{j}"), R("param", f"{key}-{kx}-{j}")
                    w(Rg, I(FKG + "modified_by"), M, "forensics"); w(M, a_, I(FKG + t), "forensics"); w(M, I(FKG + "hasParameter"), P, "forensics")
                    w(P, a_, I(FKG + "Parameter"), "forensics"); w(P, I(FKG + "hasParameterName"), lit(OPS[t][0]), "forensics"); w(P, I(FKG + "hasParameterValue"), lit(round(v, 3), "float"), "forensics")
                    if prev: w(prev, I(FKG + "hasNext"), M, "forensics")
                    if c["ttp_index"] and kind == "synthetic":  # derived index: generator|op|log-bin keys (bin 0.17 > log(1/0.85)), own bin + neighbours
                        b = math.floor(math.log(max(v, 1e-3)) / 0.17); lab = gen_label(val, iid)
                        w(P, f"<{BASE}idx/ttpKey>", lit(f"{lab}|{t}|{b}"), "index")
                        for d in (-1, 0, 1): w(P, f"<{BASE}idx/ttpNear>", lit(f"{lab}|{t}|{b + d}"), "index")
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
        if c["entity_vocab"]:  # generator entity vocabulary: every known label (incl. drifted spellings) -> one entity IRI
            for g, alt in NAME_DRIFT.items():
                ent = R("generator", hashlib.sha256(g.encode()).hexdigest()[:8])
                for lab in (g, alt): w(ent, I("http://www.w3.org/2004/02/skos/core#altLabel"), lit(lab), "vocab")
        for a in self.accounts:
            A = R("actor", a["id"])
            w(A, a_, I(AS + "Person"), "platform"); w(A, I(AS + "preferredUsername"), lit(a["username"]), "platform"); w(A, I(AS + "published"), ts(a["created"]), "platform")
        for n in notes:
            N, act, A = R("note", n["id"]), R("activity", "create-" + n["id"]), R("actor", n["acct"])
            for s, p, o in [(act, a_, I(AS + "Create")), (act, I(AS + "actor"), A), (act, I(AS + "object"), N), (act, I(AS + "published"), ts(n["t"])),
                            (N, a_, I(AS + "Note")), (N, I(AS + "attributedTo"), A), (N, I(AS + "published"), ts(n["t"])), (N, I(AS + "content"), lit(n["text"], lang="en"))]:
                w(s, p, o, "platform")
            if n["img"]: w(N, I(AS + "attachment"), img_iri[n["img"]], "platform"); w(img_iri[n["img"]], a_, I(AS + "Image"), "platform")
        for k, an in enumerate(announces):
            act = R("activity", f"announce-{hashlib.sha256(f'{self.seed}:ann:{k}'.encode()).hexdigest()[:12]}" if c["leakfix"] else f"announce-{k}")
            for s, p, o in [(act, a_, I(AS + "Announce")), (act, I(AS + "actor"), R("actor", an["acct"])), (act, I(AS + "object"), R("note", an["note"])), (act, I(AS + "published"), ts(an["t"]))]:
                w(s, p, o, "platform")
        opaque = {cid: hashlib.sha256(f"{self.seed}:{cid}".encode()).hexdigest()[:10] for cid in self.claims}
        for cid, (text, rating, label) in self.claims.items():
            Cl = R("claim", opaque[cid]); w(Cl, a_, I(SDO + "Claim"), "factcheck"); w(Cl, I(SDO + "text"), lit(text), "factcheck")
            if cid not in reviewed: continue
            Rv, Rt = R("review", opaque[cid]), R("rating", opaque[cid])
            for s, p, o in [(Rv, a_, I(SDO + "ClaimReview")), (Rv, I(SDO + "itemReviewed"), Cl), (Rv, I(SDO + "claimReviewed"), lit(text)), (Rv, I(SDO + "datePublished"), lit(self.review_t[cid].date().isoformat(), "date")),
                            (Rv, I(SDO + "reviewRating"), Rt), (Rt, a_, I(SDO + "Rating")), (Rt, I(SDO + "ratingValue"), lit(rating, "integer")), (Rt, I(SDO + "bestRating"), lit(5, "integer")),
                            (Rt, I(SDO + "worstRating"), lit(1, "integer")), (Rt, I(SDO + "alternateName"), lit(label))]:
                w(s, p, o, "factcheck")
        cal = c["claim_match"] == "calibrated"
        # calibrated matcher: recall 0.88 for near-copies of the claim wording, 0.70 for paraphrases, and about 12 % of the
        # links it makes are wrong (claim-matching F1 ~0.885, Kazemi et al. 2021; HasPositive@1 0.54-0.69, Shaar et al. 2020)
        base_miss = (0.12 if c["text_mode"] == "pool" else 0.30) if cal else (0.25 if c["text_mode"] == "paraphrase" else 0.0)
        topical = [n for n in notes if n["claim"] or n["text"] in FLOOD_TEXT]
        false_claims = [cid for cid, (_, rt, _) in self.claims.items() if rt <= 2 and cid != "O1"]
        for n in notes:
            miss = 1 - (1 - base_miss) * (1 - 0.5 * e)
            if n["claim"] and (n.get("debunk") and r.random() < c["debunk_link_p"] or not n.get("debunk") and r.random() >= miss):
                w(R("claim", opaque[n["claim"]]), I(SDO + "appearance"), R("note", n["id"]), "factcheck")
                if cal and r.random() < 0.12:  # a wrong link: a topically similar post matched to this claim
                    w(R("claim", opaque[n["claim"]]), I(SDO + "appearance"), R("note", r.choice(topical)["id"]), "factcheck")
            if c["stance"] and n["claim"]:  # stance classifier on claim-bearing posts (assumed error rates): marks posts it reads as refuting
                sr = random.Random(f"{self.seed}:{n['id']}:stance").random()
                if sr < (c["stance_recall"] if n.get("debunk") else c["stance_fpr"]): w(R("note", n["id"]), f"<{BASE}stance>", f"<{BASE}Refutes>", "factcheck")
            if n["claim"] == "T1" and r.random() < 0.1 * e: w(R("claim", opaque["C1"]), I(SDO + "appearance"), R("note", n["id"]), "factcheck")
        for n in notes:
            if not n["img"]: continue
            im = self.images[n["img"]]
            if im["derived_from"]:
                rec = c["debunk_prov_recall"] if n.get("debunk") else c["prov_recall"]
                if r.random() < rec * (1 - 0.5 * e): w(img_iri[n["img"]], I(PROV + "wasDerivedFrom"), img_iri[im["derived_from"]], "provenance")
        f.close()
        return {"images": len(self.images), "analyzed": analyzed, "notes": len(self.notes), "announces": len(self.announces), "accounts": len(self.accounts)}

    def truth(self):
        return {"seed": self.seed, "eta": self.eta, "accounts": {BASE + "actor/" + a["id"]: a["role"] for a in self.accounts},
                "campaign_of": {BASE + "actor/" + a["id"]: a["campaign"] for a in self.accounts if a["campaign"] is not None},
                "positives": sorted(BASE + "actor/" + a["id"] for a in self.accounts if a["role"] in ("campaign_core", "campaign_amplifier")),
                "core": sorted(BASE + "actor/" + a["id"] for a in self.accounts if a["role"] == "campaign_core")}
