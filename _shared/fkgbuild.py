# Shared helpers: emit FKG records + context into an rdflib Dataset with named graphs.
import hashlib, random
from rdflib import Dataset, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS, PROV

FKG = Namespace("https://example.org/fkg#")
CTX = Namespace("https://example.org/fkg/context#")
AS = Namespace("https://www.w3.org/ns/activitystreams#")
SCHEMA = Namespace("https://schema.org/")
IPTC = Namespace("http://cv.iptc.org/newscodes/digitalsourcetype/")
G_REF, G_CTX = URIRef("urn:g:reference"), URIRef("urn:g:context")
AI_CONF_THRESHOLD = 0.7
AI_OBJECTNESS_P = 0.6   # objectness of any AI-attributed region, drawn the same way whether the attribution is right or wrong

def ai_region_look(rng, desc_pool):
    """description + objectness for an AI-attributed region; deliberately independent of ground truth (no label leak)"""
    return dict(desc=rng.choice(desc_pool), objectness=rng.random() < AI_OBJECTNESS_P)

def new_dataset(base):
    ds = Dataset(default_union=True)
    for p, ns in [("fkg", FKG), ("ctx", CTX), ("as", AS), ("schema", SCHEMA), ("prov", PROV), ("dcterms", DCTERMS), ("iptc", IPTC), ("ex", Namespace(base))]:
        ds.bind(p, ns)
    return ds, Namespace(base)

def lit_dt(s): return Literal(s, datatype=XSD.dateTime)

def add_detector(ds, EX, version, released):
    g = ds.graph(G_REF); v = EX[f"detector_{version.replace('.', '_')}"]
    g.add((v, RDF.type, CTX.DetectorVersion)); g.add((v, RDFS.label, Literal(f"FKG generation system {version}")))
    g.add((v, SCHEMA.softwareVersion, Literal(version))); g.add((v, SCHEMA.datePublished, Literal(released, datatype=XSD.date)))
    return v

def add_image(ds, EX, iid, regions, detector, run_time, long_edge, rng):
    """regions: list of dicts {kind:'camera'|'ai', model, conf, entity(optional), gen_entity(optional),
       desc, objectness, post:[(cls, {name:value})], comp:{'q':float,'re':bool} or None}"""
    gname = URIRef(f"urn:g:fkg/{iid}"); g = ds.graph(gname)
    img = EX[iid]
    g.add((img, RDF.type, FKG.Image)); g.add((img, CTX.pixelLongEdge, Literal(long_edge, datatype=XSD.positiveInteger)))
    g.add((img, CTX.sha256, Literal(hashlib.sha256(f"{iid}-{rng.random()}".encode()).hexdigest())))
    kinds = []
    for k, r in enumerate(regions, 1):
        reg, src, con = EX[f"{iid}_r{k}"], EX[f"{iid}_s{k}"], EX[f"{iid}_d{k}"]
        g.add((reg, RDF.type, FKG.Region)); g.add((reg, FKG.contained_in, img)); g.add((img, FKG.hasRegion, reg))
        g.add((reg, FKG.produced_by, src))
        if r["kind"] == "camera":
            g.add((src, RDF.type, FKG.CameraModel)); g.add((src, FKG.hasCameraModel, Literal(r["model"])))
        else:
            g.add((src, RDF.type, FKG.AIGenerator)); g.add((src, FKG.hasGeneratorModel, Literal(r["model"])))
            if r.get("gen_entity") is not None: g.add((src, CTX.generatorEntity, r["gen_entity"]))
        g.add((src, FKG.hasConfidence, Literal(round(r["conf"], 3), datatype=XSD.float)))
        kinds.append(r["kind"] if (r["kind"] == "camera" or r["conf"] >= 0.5) else "camera")
        posts = r.get("post") or [("NoPostProc", {})]
        prev = None
        for j, (cls, params) in enumerate(posts, 1):
            m = EX[f"{iid}_m{k}_{j}"]; g.add((m, RDF.type, FKG[cls])); g.add((reg, FKG.modified_by, m))
            for n, (pname, pval) in enumerate(params.items(), 1):
                p = EX[f"{iid}_p{k}_{j}_{n}"]; g.add((m, FKG.hasParameter, p)); g.add((p, RDF.type, FKG.Parameter))
                g.add((p, FKG.hasParameterName, Literal(pname))); g.add((p, FKG.hasParameterValue, Literal(float(pval), datatype=XSD.float)))
            if prev is not None: g.add((prev, FKG.hasNext, m))
            prev = m
        if r.get("comp"):
            c = EX[f"{iid}_c{k}"]; g.add((reg, FKG.compress_by, c))
            g.add((c, RDF.type, FKG.LastCompressed)); g.add((c, FKG.hasCompressionAlgorithm, Literal("JPEG")))
            g.add((c, FKG.hasCompressionFactor, Literal(round(r["comp"]["q"], 3), datatype=XSD.float)))
            if r["comp"].get("re"):
                g.add((c, RDF.type, FKG.ReCompressed)); g.add((c, FKG.hasReCompressed, Literal(True)))
        g.add((reg, FKG.depict, con)); g.add((con, RDF.type, FKG.Content))
        g.add((con, FKG.hasObjectDescription, Literal(r["desc"]))); g.add((con, FKG.hasObjectedness, Literal(bool(r.get("objectness", True)))))
        if r.get("entity") is not None: g.add((con, CTX.depictsEntity, r["entity"]))
    # record layer (Jane's pattern, minus per-triple observations for scale)
    rec, concl, run = EX[f"{iid}_record"], EX[f"{iid}_conclusion"], EX[f"{iid}_run"]
    g.add((rec, RDF.type, FKG.ForensicRecord)); g.add((rec, FKG.aboutImage, img)); g.add((rec, FKG.hasConclusion, concl))
    g.add((rec, PROV.wasGeneratedBy, run)); g.add((run, RDF.type, CTX.DetectorRun))
    g.add((run, PROV.wasAssociatedWith, detector)); g.add((run, PROV.endedAtTime, lit_dt(run_time)))
    verdict = FKG.Authentic if all(x == "camera" for x in kinds) else (CTX.SyntheticImage if all(x == "ai" for x in kinds) else FKG.Manipulated)
    g.add((concl, RDF.type, FKG.ForensicConclusion)); g.add((concl, FKG.aboutImage, img)); g.add((concl, FKG.verdict, verdict))
    g.add((concl, FKG.evidenceStatus, FKG.Inferred))
    return img

def add_platform(ds, EX, key, label, q, passthrough, max_edge):
    g = ds.graph(G_REF); p = EX[f"platform_{key}"]
    g.add((p, RDF.type, CTX.Platform)); g.add((p, RDFS.label, Literal(label)))
    g.add((p, CTX.transcodeQuality, Literal(q, datatype=XSD.float))); g.add((p, CTX.passthrough, Literal(passthrough)))
    g.add((p, CTX.maxLongEdge, Literal(max_edge, datatype=XSD.positiveInteger))); g.add((p, FKG.evidenceStatus, FKG.SourceReported))
    return p

def add_account(ds, EX, key, platform, genre):
    g = ds.graph(G_CTX); a = EX[f"acct_{key}"]
    g.add((a, RDF.type, AS.Person)); g.add((a, AS.preferredUsername, Literal(key))); g.add((a, CTX.onPlatform, platform))
    g.add((a, CTX.accountGenre, genre)); return a

def add_post(ds, EX, key, account, platform, published, image, shares=0, credits=None, disclosure=None, content=None):
    g = ds.graph(G_CTX); n = EX[f"post_{key}"]
    g.add((n, RDF.type, AS.Note)); g.add((n, AS.attributedTo, account)); g.add((n, CTX.onPlatform, platform))
    g.add((n, AS.published, lit_dt(published))); g.add((n, AS.attachment, image))
    g.add((n, CTX.shareCount, Literal(shares, datatype=XSD.nonNegativeInteger)))
    if credits is not None: g.add((n, CTX.creditsSource, credits))
    if disclosure is not None: g.add((n, CTX.hasDisclosure, disclosure))
    if content: g.add((n, AS.content, Literal(content)))
    return n

def add_cluster_member(ds, EX, cluster_key, image):
    g = ds.graph(G_CTX); c = EX[f"cluster_{cluster_key}"]
    g.add((c, RDF.type, CTX.NearDuplicateCluster)); g.add((image, CTX.inCluster, c)); g.add((c, FKG.evidenceStatus, FKG.Inferred))
    return c

def write(ds, path):
    ds.serialize(destination=path, format="trig")
