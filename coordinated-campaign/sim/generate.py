# Synthetic coordinated-campaign scenario -> TriG dataset (4 named graphs) + ground truth JSON.
# All accounts, posts, claims, images and forensic findings are synthetic.
import argparse, base64, hashlib, json, random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from rdflib import Dataset, Graph, Literal, Namespace, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS, PROV

FKG = Namespace("https://example.org/fkg#")
AS = Namespace("https://www.w3.org/ns/activitystreams#")
SDO = Namespace("https://schema.org/")
BASE = "https://example.org/cc/"
G_FOR, G_PLAT, G_FC, G_PROV = (URIRef(BASE + "graph/" + n) for n in ("forensics", "platform", "factcheck", "provenance"))
UTC = timezone.utc

GENERATORS = {"FLUX.1 [dev]": .25, "Midjourney v7": .20, "SDXL": .15, "GPT-Image 1": .15, "Seedream 4": .10, "Nano Banana": .10, "FLUX.1 [schnell]": .05}
SIBLING = {"FLUX.1 [dev]": "FLUX.1 [schnell]", "FLUX.1 [schnell]": "FLUX.1 [dev]", "SDXL": "FLUX.1 [schnell]", "Midjourney v7": "Seedream 4",
           "Seedream 4": "Midjourney v7", "GPT-Image 1": "Nano Banana", "Nano Banana": "GPT-Image 1"}
CAMERAS = ["Apple iPhone 15 Pro", "Apple iPhone 13", "Samsung Galaxy S24", "Google Pixel 8", "Samsung Galaxy A54", "Xiaomi Redmi Note 12", "Canon EOS R6", "Sony A7 IV"]
OPS = {"Resampling": ("scaleFactor", (0.4, 1.6)), "GaussianBlur": ("sigma", (0.3, 2.5)), "GaussianNoise": ("sigma", (0.5, 3.0)), "Sharpening": ("amount", (0.3, 1.5))}
CAMPAIGN_CHAIN = [("Resampling", 0.80), ("GaussianBlur", 0.60), ("GaussianNoise", 1.20)]
BRAND_CHAIN = [("Resampling", 0.50), ("Sharpening", 0.80)]
CAMPAIGN_GEN, BRAND_GEN = "FLUX.1 [dev]", "GPT-Image 1"

CLAIMS = {  # id: (text, rating 1..5, label)
    "C1": ("The Brennerton dam was opened on purpose to flood the east side of the city.", 1, "False"),
    "C2": ("Relief centers in Brennerton are turning away flood victims who cannot show ID.", 1, "False"),
    "C3": ("Brennerton's mayor left the city by private plane before the flood.", 1, "False"),
    "O1": ("Brennerton tap water is contaminated with sewage and unsafe even after boiling.", 1, "False"),
    "T1": ("Heavy rain caused the Brenner River to flood parts of Brennerton.", 5, "True"),
}
CAMPAIGN_TEXT = {
    "C1": ["They opened the dam ON PURPOSE. East side was sacrificed. Look at this.", "Brennerton dam was opened deliberately to flood the east side. Share before it's deleted.",
           "No accident: officials released the dam on the east side neighborhoods.", "East Brennerton was flooded on purpose. The dam gates were opened at night."],
    "C2": ["Relief centers are refusing flood victims without ID. This is happening right now in Brennerton.", "No ID, no help. Brennerton relief center turning families away.",
           "Flood victims turned away for not having papers. Disgusting."],
    "C3": ["Where is the mayor? Flew out on a private plane before the flood hit.", "Brennerton mayor escaped on a private jet while the city drowned.",
           "Mayor left by private plane the night before. They knew."],
    None: ["Praying for everyone in Brennerton tonight.", "Stay safe out there.", "Unreal scenes today.", "Morning walk before the storm."],
}
CAMPAIGN_CONTENT = {"C1": ["flooded street", "dam spillway", "submerged houses"], "C2": ["crowd at relief center", "family outside shelter"],
                    "C3": ["private jet on runway", "official boarding plane"], None: ["city skyline", "rain clouds"]}
ORGANIC_TEXT = ["Coffee and a good book.", "New trail run PR today!", "My cat refuses to leave the couch.", "Sunset from the roof.", "Trying a new pasta recipe.",
                "Concert last night was amazing.", "Made this with an AI tool, thoughts?", "Weekend market haul.", "Fall colors are here.", "Throwback to the beach trip."]
ORGANIC_CONTENT = ["coffee cup", "trail", "cat", "sunset", "pasta", "concert stage", "fantasy landscape", "market stall", "autumn trees", "beach", "portrait", "city street"]
FLOOD_TEXT = ["Brenner River is way up after the rain.", "Roads closed near the river, take care.", "Heavy rain caused flooding by the river today.", "Volunteers filling sandbags downtown."]
BELIEVER_TEXT = {"C1": ["Is it true they opened the dam on purpose?? My cousin lives on the east side.", "People are saying the dam was opened deliberately. If true this is criminal."],
                 "C2": ["Heard relief centers are turning people away without ID, can anyone confirm?", "If they're really refusing people without ID that's awful."],
                 "C3": ["So the mayor just left on a private plane? Unbelievable.", "Mayor flew out before the flood? Need answers."]}
RUMOR_TEXT = ["Don't drink the tap water, it's contaminated with sewage even if you boil it.", "Tap water in Brennerton is NOT safe even boiled. Buy bottled.", "Heard the water is sewage-contaminated, boiling won't help."]
BRAND_TEXT = ["The Aurora Trail jacket drops Friday. Built for the wild.", "Rain or shine, #AuroraTrail has you covered.", "Meet the new Aurora Trail collection.", "Adventure-ready. Aurora Trail, out now."]
ADJ = ["quiet", "blue", "lucky", "urban", "wild", "sunny", "rusty", "mellow", "brave", "lazy", "north", "true", "daily", "real", "local"]
NOUN = ["fox", "river", "maple", "pixel", "otter", "harbor", "falcon", "comet", "willow", "cedar", "ember", "atlas", "nomad", "ranger", "patriot"]


def ni_iri(token):  # RFC 6920 named-information URI from a SHA-256 digest
    return URIRef("ni:///sha-256;" + base64.urlsafe_b64encode(hashlib.sha256(token.encode()).digest()).decode().rstrip("="))


def dt(y, mo, d, h=0, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=UTC)


def rand_time(rng, t0, t1):
    return t0 + timedelta(seconds=rng.uniform(0, (t1 - t0).total_seconds()))


class Scenario:
    def __init__(self, seed, eta, behavior="naive"):
        self.rng, self.eta, self.seed = random.Random(seed * 1000 + int(eta * 100)), eta, seed
        self.behavior = behavior  # naive: fresh personas that repost only each other; evasive: aged accounts that also repost organic content
        self.truth_rng = random.Random(seed)  # world (ground truth) depends only on seed; detector noise depends on eta too
        self.accounts, self.notes, self.announces, self.images = [], [], [], {}
        self.ids = set()

    def uid(self, rng, prefix):
        while True:
            x = prefix + "".join(rng.choice("0123456789abcdef") for _ in range(8))
            if x not in self.ids:
                self.ids.add(x); return x

    # ---------- ground-truth world ----------
    def add_account(self, role, created):
        r = self.truth_rng
        a = {"id": self.uid(r, "u"), "username": f"{r.choice(ADJ)}_{r.choice(NOUN)}{r.randint(1, 999)}", "created": created, "role": role}
        self.accounts.append(a); return a

    def new_image(self, kind, gen=None, chain=None, camera=None, precompressed=True, content="", derived_from=None):
        r = self.truth_rng
        iid = self.uid(r, "img")
        self.images[iid] = {"kind": kind, "gen": gen, "chain": chain or [], "camera": camera, "pre": precompressed, "content": content, "derived_from": derived_from}
        return iid

    def organic_image(self, content):
        r = self.truth_rng
        if r.random() < 0.6:
            return self.new_image("camera", camera=r.choice(CAMERAS), chain=self.random_chain(r, 0.7), content=content)
        gen = r.choices(list(GENERATORS), weights=list(GENERATORS.values()))[0]
        return self.new_image("synthetic", gen=gen, chain=self.random_chain(r, 0.5), precompressed=r.random() < 0.5, content=content)

    @staticmethod
    def random_chain(r, p_none):
        if r.random() < p_none:
            return []
        n = r.choices([1, 2, 3], weights=[.6, .3, .1])[0]
        return [(t, round(r.uniform(*OPS[t][1]), 2)) for t in r.sample(list(OPS), n)]

    def post(self, acct, t, text, img=None, claim=None):
        n = {"id": self.uid(self.truth_rng, "n"), "acct": acct["id"], "t": t, "text": text, "img": img, "claim": claim}
        self.notes.append(n); return n

    def build_world(self):
        r = self.truth_rng
        cw0, cw1 = dt(2026, 10, 3, 6), dt(2026, 10, 5, 6)                       # campaign window (48 h)
        evasive = self.behavior == "evasive"
        c0, c1 = (dt(2014, 1, 1), dt(2025, 12, 31)) if evasive else (dt(2026, 9, 10), dt(2026, 9, 14))  # evasive: bought aged accounts
        core = [self.add_account("campaign_core", rand_time(r, c0, c1)) for _ in range(10)]
        amps = [self.add_account("campaign_amplifier", rand_time(r, c0, c1)) for _ in range(2)]
        brand = [self.add_account("brand", rand_time(r, dt(2019, 1, 1), dt(2023, 12, 31))) for _ in range(6)]
        # organic accounts: mostly years old, 15 % opened during 2026 (so new accounts alone are not a campaign signal)
        organic = [self.add_account("organic", rand_time(r, dt(2026, 1, 1), dt(2026, 10, 1)) if r.random() < 0.15 else rand_time(r, dt(2012, 1, 1), dt(2025, 12, 31))) for _ in range(150)]
        r.shuffle(organic)
        believers, reuploaders, rumor = organic[:20], organic[20:26], organic[26:36]
        for a in believers: a["role"] = "organic_believer"
        for a in reuploaders: a["role"] = "organic_reuploader"
        for a in rumor: a["role"] = "organic_rumor"
        # campaign core: distinct originals from one generation + processing script
        camp_notes = []
        for a in core + amps:  # persona building: a few innocuous posts between account creation and the operation
            for _ in range(r.randint(1, 3)):
                c = r.choice(ORGANIC_CONTENT)
                f0 = dt(2026, 9, 22) if evasive else a["created"] + timedelta(days=1)
                self.post(a, rand_time(r, f0, dt(2026, 10, 2)), r.choice(ORGANIC_TEXT), self.organic_image(c) if r.random() < 0.6 else None, None)
        for a in core:
            for _ in range(r.randint(3, 5)):
                claim = r.choices(["C1", "C2", "C3", None], weights=[.4, .25, .15, .2])[0]
                content = r.choice(CAMPAIGN_CONTENT[claim])
                if r.random() < 0.7:
                    img = self.new_image("synthetic", gen=CAMPAIGN_GEN, chain=CAMPAIGN_CHAIN, content=content)
                else:  # local AI edit: camera background + inserted synthetic region, same processing script on the whole image
                    img = self.new_image("edit", gen=CAMPAIGN_GEN, chain=CAMPAIGN_CHAIN, camera=r.choice(CAMERAS), content=content)
                camp_notes.append(self.post(a, rand_time(r, cw0, cw1), r.choice(CAMPAIGN_TEXT[claim]), img, claim))
        for a in core:  # mutual amplification
            for n in r.sample([n for n in camp_notes if n["acct"] != a["id"]], r.randint(2, 5)):
                self.announces.append({"acct": a["id"], "note": n["id"], "t": n["t"] + timedelta(minutes=r.uniform(5, 600))})
        for a in amps:  # amplifier personas: text-only claim posts + heavy announcing of core content
            for _ in range(r.randint(2, 3)):
                claim = r.choice(["C1", "C2", "C3"])
                self.post(a, rand_time(r, cw0, cw1), r.choice(CAMPAIGN_TEXT[claim]), None, claim)
            for n in r.sample(camp_notes, r.randint(6, 10)):
                self.announces.append({"acct": a["id"], "note": n["id"], "t": n["t"] + timedelta(minutes=r.uniform(5, 300))})
        # brand campaign: coordinated, shared pipeline, short window, no fact-checked claims
        bw0 = dt(2026, 9, 28, 12)
        for a in brand:
            for _ in range(4):
                img = self.new_image("synthetic", gen=BRAND_GEN, chain=BRAND_CHAIN, precompressed=False, content=r.choice(["hiker in jacket", "mountain trail", "product shot"]))
                self.post(a, rand_time(r, bw0, bw0 + timedelta(hours=36)), r.choice(BRAND_TEXT), img, None)
        # organic background activity
        o0, o1 = dt(2026, 9, 22), dt(2026, 10, 6, 23)
        for a in organic:
            for _ in range(r.randint(2, 6)):
                c = r.choice(ORGANIC_CONTENT)
                self.post(a, rand_time(r, o0, o1), r.choice(ORGANIC_TEXT), self.organic_image(c) if r.random() < 0.85 else None, None)
            if r.random() < 0.15:  # flood news, true claim
                self.post(a, rand_time(r, dt(2026, 10, 2), o1), r.choice(FLOOD_TEXT), self.organic_image("flooded street") if r.random() < 0.7 else None, "T1")
        # organic reposting: heavy-tailed account popularity; brand posts get extra reach
        pop = {a["id"]: r.lognormvariate(0, 1) for a in organic + brand}
        pop.update({a["id"]: 3 * pop[a["id"]] for a in brand})
        pool = [n for n in self.notes if n["acct"] in pop]
        weights = [pop[n["acct"]] for n in pool]
        for a in organic:
            for n in r.choices(pool, weights=weights, k=r.choice([0, 0, 1, 1, 2, 3, 4, 6])):
                if n["acct"] != a["id"]:
                    self.announces.append({"acct": a["id"], "note": n["id"], "t": n["t"] + timedelta(minutes=r.uniform(5, 2880))})
        if evasive:  # campaign accounts blend in by also resharing popular organic and brand content
            for a in core + amps:
                for n in r.choices(pool, weights=weights, k=r.randint(4, 9)):
                    self.announces.append({"acct": a["id"], "note": n["id"], "t": n["t"] + timedelta(minutes=r.uniform(5, 2880))})
        for a in believers:  # organic users who repeat the false narrative, with their own media, and reshare campaign posts
            for _ in range(r.randint(1, 2)):
                claim = r.choice(["C1", "C2", "C3"])
                img = self.organic_image(r.choice(["flooded street", "rain clouds", "city street"])) if r.random() < 0.7 else None
                self.post(a, rand_time(r, cw0 + timedelta(hours=6), cw1 + timedelta(hours=24)), r.choice(BELIEVER_TEXT[claim]), img, claim)
            for n in r.sample(camp_notes, r.randint(1, 3)):
                self.announces.append({"acct": a["id"], "note": n["id"], "t": n["t"] + timedelta(minutes=r.uniform(30, 1440))})
        for a in reuploaders:  # download and re-upload a campaign image with the claim
            src = r.choice([n for n in camp_notes if n["claim"]])
            s = self.images[src["img"]]
            img = self.new_image(s["kind"], gen=s["gen"], chain=s["chain"], camera=s["camera"], content=s["content"], derived_from=src["img"])
            self.post(a, src["t"] + timedelta(hours=r.uniform(2, 30)), r.choice(BELIEVER_TEXT[src["claim"]]), img, src["claim"])
        for a in rumor:  # organic, uncoordinated false rumor
            for _ in range(r.randint(1, 2)):
                self.post(a, rand_time(r, dt(2026, 9, 25), dt(2026, 10, 1)), r.choice(RUMOR_TEXT), self.organic_image(r.choice(["glass of water", "kitchen sink"])) if r.random() < 0.6 else None, "O1")

    # ---------- noisy observation (what the detectors and matchers report) ----------
    def observe_source(self, true_synth, gen, camera):
        r, e = self.rng, self.eta
        if true_synth:
            if r.random() < 0.3 * e:
                return ("camera", r.choice(CAMERAS), r.uniform(0.5, 0.8))
            g = gen
            if r.random() < 0.5 * e:
                g = SIBLING[gen] if r.random() < 0.7 else r.choice([x for x in GENERATORS if x != gen])
            return ("synthetic", g, max(0.5, r.uniform(0.85, 0.99) - 0.5 * e * r.random()))
        if r.random() < 0.1 * e:
            return ("synthetic", r.choices(list(GENERATORS), weights=list(GENERATORS.values()))[0], r.uniform(0.5, 0.75))
        return ("camera", camera, max(0.5, r.uniform(0.85, 0.99) - 0.5 * e * r.random()))

    def observe_chain(self, chain):
        r, e = self.rng, self.eta
        out = [(t, max(0.05, v * (1 + r.gauss(0, 0.02 + 0.15 * e)))) for t, v in chain if r.random() >= 0.5 * e]
        if r.random() < 0.2 * e:
            t = r.choice(list(OPS)); out.insert(r.randint(0, len(out)), (t, r.uniform(*OPS[t][1])))
        return out

    # ---------- RDF ----------
    def to_dataset(self):
        r, e = self.rng, self.eta
        ds = Dataset()
        for p, ns in [("fkg", FKG), ("as", AS), ("schema", SDO), ("prov", PROV), ("dcterms", DCTERMS), ("xsd", XSD), ("cc", Namespace(BASE)), ("g", Namespace(BASE + "graph/"))]:
            ds.bind(p, ns)
        gf, gp, gc, gv = (ds.graph(g) for g in (G_FOR, G_PLAT, G_FC, G_PROV))
        dflt = ds.default_graph
        R = lambda kind, x: URIRef(f"{BASE}{kind}/{x}")
        L = lambda v, dtp=None: Literal(v, datatype=dtp)
        # named-graph descriptions (default graph)
        fkg_agent, cm_agent, fc_org, pv_agent, platform = R("agent", "fkg-system"), R("agent", "claim-matcher"), R("agent", "factcheck-desk"), R("agent", "provenance-analyzer"), R("agent", "platform")
        for g, who, desc in [(G_FOR, fkg_agent, "FKG records produced by the forensic analysis system"), (G_PLAT, platform, "Activity Streams 2.0 export of public posts and reposts"),
                             (G_FC, fc_org, "ClaimReview fact-checks and claim-to-post matches"), (G_PROV, pv_agent, "Image derivation links from provenance analysis")]:
            dflt.add((g, RDF.type, PROV.Entity)); dflt.add((g, PROV.wasAttributedTo, who)); dflt.add((g, DCTERMS.description, L(desc)))
        dflt.add((fkg_agent, RDF.type, PROV.SoftwareAgent)); dflt.add((fkg_agent, RDFS.label, L("FKG generation system (simulated)"))); dflt.add((fkg_agent, DCTERMS.hasVersion, L("sim-1.0")))
        dflt.add((cm_agent, RDF.type, PROV.SoftwareAgent)); dflt.add((pv_agent, RDF.type, PROV.SoftwareAgent))
        dflt.add((fc_org, RDF.type, SDO.Organization)); dflt.add((fc_org, SDO.name, L("Example Fact Check Desk (fictional)")))
        img_iri = {iid: ni_iri(f"{self.seed}:{iid}") for iid in self.images}
        # forensics
        for iid, im in self.images.items():
            I = img_iri[iid]; key = hashlib.sha256(f"{self.seed}:{iid}".encode()).hexdigest()[:12]
            gf.add((I, RDF.type, FKG.Image))
            rec, ana, concl = R("record", key), R("analysis", key), R("conclusion", key)
            regions = []
            if im["kind"] in ("synthetic", "camera"):
                regions.append((im["kind"] == "synthetic", im["content"], True))
            else:  # edit: background camera region + inserted synthetic object region
                regions += [(False, "background", False), (True, im["content"], True)]
            any_synth = False
            for k, (synth, content, obj) in enumerate(regions):
                Rg, S, D, C = R("region", f"{key}-{k}"), R("source", f"{key}-{k}"), R("content", f"{key}-{k}"), R("compression", f"{key}-{k}")
                for t in [(I, FKG.hasRegion, Rg), (Rg, RDF.type, FKG.Region), (Rg, FKG.contained_in, I), (Rg, FKG.produced_by, S), (Rg, FKG.depict, D), (Rg, FKG.compress_by, C),
                          (Rg, FKG.localizationStatus, FKG.LocalizationNotProvided)]:
                    gf.add(t)
                kind, val, conf = self.observe_source(synth, im["gen"], im["camera"] or r.choice(CAMERAS))
                any_synth |= kind == "synthetic"
                gf.add((S, RDF.type, FKG.AIGenerator if kind == "synthetic" else FKG.CameraModel))
                gf.add((S, FKG.hasGeneratorModel if kind == "synthetic" else FKG.hasCameraModel, L(val)))
                gf.add((S, FKG.hasConfidence, L(round(conf, 3), XSD.float)))
                ops = self.observe_chain(im["chain"])
                prev = None
                for j, (t, v) in enumerate(ops):
                    M, P = R("op", f"{key}-{k}-{j}"), R("param", f"{key}-{k}-{j}")
                    for tr in [(Rg, FKG.modified_by, M), (M, RDF.type, FKG[t]), (M, FKG.hasParameter, P), (P, RDF.type, FKG.Parameter),
                               (P, FKG.hasParameterName, L(OPS[t][0])), (P, FKG.hasParameterValue, L(round(v, 3), XSD.float))]:
                        gf.add(tr)
                    if prev is not None: gf.add((prev, FKG.hasNext, M))
                    prev = M
                if not ops:
                    M = R("op", f"{key}-{k}-none"); gf.add((Rg, FKG.modified_by, M)); gf.add((M, RDF.type, FKG.NoPostProc))
                recompressed = im["pre"] or im["derived_from"] is not None
                if recompressed:
                    gf.add((C, RDF.type, FKG.ReCompressed)); gf.add((C, FKG.hasReCompressed, L(True)))
                else:
                    gf.add((C, RDF.type, FKG.LastCompressed)); gf.add((C, FKG.hasCompressionAlgorithm, L("JPEG"))); gf.add((C, FKG.hasCompressionFactor, L(0.85, XSD.float)))
                gf.add((D, RDF.type, FKG.Content)); gf.add((D, FKG.hasObjectDescription, L(content))); gf.add((D, FKG.hasObjectedness, L(obj)))
            for t in [(rec, RDF.type, FKG.ForensicRecord), (rec, FKG.aboutImage, I), (rec, FKG.hasConclusion, concl), (rec, PROV.wasGeneratedBy, ana),
                      (ana, RDF.type, PROV.Activity), (ana, PROV.used, I), (ana, PROV.wasAssociatedWith, fkg_agent),
                      (concl, RDF.type, FKG.ForensicConclusion), (concl, FKG.aboutImage, I), (concl, FKG.verdict, FKG.Manipulated if any_synth else FKG.Authentic)]:
                gf.add(t)
            if any_synth:
                gf.add((concl, FKG.manipulationType, FKG.AIEditing if len(regions) > 1 and not all(s for s, _, _ in regions) else FKG.FullySynthetic))
        # platform (Activity Streams 2.0)
        for a in self.accounts:
            A = R("actor", a["id"])
            gp.add((A, RDF.type, AS.Person)); gp.add((A, AS.preferredUsername, L(a["username"]))); gp.add((A, AS.published, L(a["created"].replace(microsecond=0), XSD.dateTime)))
        for n in self.notes:
            N, act, A = R("note", n["id"]), R("activity", "create-" + n["id"]), R("actor", n["acct"])
            t = L(n["t"].replace(microsecond=0), XSD.dateTime)
            for tr in [(act, RDF.type, AS.Create), (act, AS.actor, A), (act, AS.object, N), (act, AS.published, t),
                       (N, RDF.type, AS.Note), (N, AS.attributedTo, A), (N, AS.published, t), (N, AS.content, Literal(n["text"], lang="en"))]:
                gp.add(tr)
            if n["img"]:
                gp.add((N, AS.attachment, img_iri[n["img"]])); gp.add((img_iri[n["img"]], RDF.type, AS.Image))
        for k, an in enumerate(self.announces):
            act = R("activity", f"announce-{self.uid(self.truth_rng, 'a')}")
            for tr in [(act, RDF.type, AS.Announce), (act, AS.actor, R("actor", an["acct"])), (act, AS.object, R("note", an["note"])), (act, AS.published, L(an["t"].replace(microsecond=0), XSD.dateTime))]:
                gp.add(tr)
        # fact-checks (schema.org ClaimReview) and claim matching
        opaque = {cid: hashlib.sha256(f"{self.seed}:{cid}".encode()).hexdigest()[:10] for cid in CLAIMS}
        for cid, (text, rating, label) in CLAIMS.items():
            Cl, Rv, Rt = R("claim", opaque[cid]), R("review", opaque[cid]), R("rating", opaque[cid])
            for tr in [(Cl, RDF.type, SDO.Claim), (Cl, SDO.text, L(text)), (Rv, RDF.type, SDO.ClaimReview), (Rv, SDO.itemReviewed, Cl), (Rv, SDO.claimReviewed, L(text)),
                       (Rv, SDO.author, fc_org), (Rv, SDO.datePublished, L("2026-10-06", XSD.date)), (Rv, SDO.reviewRating, Rt), (Rt, RDF.type, SDO.Rating),
                       (Rt, SDO.ratingValue, L(rating)), (Rt, SDO.bestRating, L(5)), (Rt, SDO.worstRating, L(1)), (Rt, SDO.alternateName, L(label))]:
                gc.add(tr)
        claim_iri = {cid: R("claim", opaque[cid]) for cid in CLAIMS}
        for n in self.notes:
            if n["claim"] and r.random() >= 0.5 * e:
                gc.add((claim_iri[n["claim"]], SDO.appearance, R("note", n["id"])))
            if n["claim"] == "T1" and r.random() < 0.1 * e:  # matcher confuses flood news with the dam claim
                gc.add((claim_iri["C1"], SDO.appearance, R("note", n["id"])))
        # provenance analysis
        for iid, im in self.images.items():
            if im["derived_from"] and r.random() >= 0.5 * e:
                gv.add((img_iri[iid], PROV.wasDerivedFrom, img_iri[im["derived_from"]]))
        return ds

    def truth(self):
        pos = {"campaign_core", "campaign_amplifier"}
        return {"seed": self.seed, "eta": self.eta, "accounts": {BASE + "actor/" + a["id"]: a["role"] for a in self.accounts},
                "positives": sorted(BASE + "actor/" + a["id"] for a in self.accounts if a["role"] in pos),
                "core": sorted(BASE + "actor/" + a["id"] for a in self.accounts if a["role"] == "campaign_core")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--etas", default="0,0.1,0.2,0.3,0.4,0.5"); ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--behavior", choices=["naive", "evasive"], default="naive")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "data")); ap.add_argument("--truth", default=str(Path(__file__).resolve().parent.parent / "truth"))
    args = ap.parse_args()
    for eta in [float(x) for x in args.etas.split(",")]:
        for seed in range(args.seeds):
            sc = Scenario(seed, eta, args.behavior); sc.build_world(); ds = sc.to_dataset()
            d = Path(args.out) / f"eta_{eta:.1f}" / f"seed_{seed}"; d.mkdir(parents=True, exist_ok=True)
            ds.serialize(d / "dataset.trig", format="trig")
            t = Path(args.truth) / f"eta_{eta:.1f}"; t.mkdir(parents=True, exist_ok=True)
            json.dump(sc.truth(), open(t / f"seed_{seed}.json", "w"), indent=1)
            print(f"eta={eta:.1f} seed={seed} quads={len(ds)} images={len(sc.images)} notes={len(sc.notes)} announces={len(sc.announces)}")


if __name__ == "__main__":
    main()
