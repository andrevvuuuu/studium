#!/usr/bin/env python3
"""
paper_note.py - Studi scientifici di Bodybuilding nel vault (via agy, nessuna API a pagamento).

  python3 .antigravity/tools/paper_note.py paper <DOI | PMID | PMCID | file.pdf> [--overwrite]
      Nota Studio Standalone in Bodybuilding/Studi/: testo completo (Europe PMC / PDF open access / PDF locale),
      estrazione con agy vincolata allo schema, validazione Pydantic, ricalcolo dell'effect size corretto per il
      disegno (within-subject vs gruppi paralleli), conversione SEM->SD, audit dello spin, callout e linking.

  python3 .antigravity/tools/paper_note.py concept "<percorso nota.md>" --papers <citekey|alias|DOI> ... \
      [--kind exercise|principle|muscle_group]
      Integra criticamente gli studi in una nota di bodybuilding esistente: blocco "Evidenza scientifica"
      gerarchizzato (MRI > ecografia > DEXA/BIA; avanzati verificati > ricreativi; cedimento oggettivo > volizionale),
      affermazioni declassate se gli studi non bastano, backlink nei due versi. Il resto della nota non viene toccato.

L'ultima riga stampata inizia con "RISULTATO:" (successo) o "ERRORE:" (codice di uscita 1): il menu la mostra.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

for _p in ("/opt/homebrew/bin", str(Path.home() / ".local/bin"), "/usr/local/bin"):
    if _p not in os.environ.get("PATH", "").split(":"):
        os.environ["PATH"] = _p + ":" + os.environ.get("PATH", "")

def _reexec_with_deps() -> None:
    """Dal menu di Obsidian 'python3' puo' essere un interprete senza le librerie (es. Homebrew): in quel caso
    il processo si rilancia con il primo Python del Mac che ha pydantic, requests, yaml e PyMuPDF."""
    if os.environ.get("STUDI_REEXEC"):
        return
    for cand in ("/Library/Frameworks/Python.framework/Versions/3.14/bin/python3", "/usr/local/bin/python3",
                 "/opt/homebrew/bin/python3.14", "/usr/bin/python3"):
        if not Path(cand).exists() or os.path.realpath(cand) == os.path.realpath(sys.executable):
            continue
        probe = subprocess.run([cand, "-c", "import pydantic, requests, yaml, fitz"], capture_output=True)
        if probe.returncode == 0:
            os.environ["STUDI_REEXEC"] = "1"
            os.execv(cand, [cand, str(Path(__file__).resolve()), *sys.argv[1:]])


try:
    import requests
    import yaml  # noqa: F401
    from pydantic import ValidationError
except ImportError as _e:  # pragma: no cover
    _reexec_with_deps()
    print(f"ERRORE: libreria Python mancante ({_e.name}). Esegui: "
          "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 -m pip install --user pydantic requests pyyaml pymupdf")
    sys.exit(1)

from studi.evidence import Envelope, Synthesis, enforce_claims, load_card
from studi.jats import parse_jats
from studi.models import normalize_doi
from studi.notefs import atomic_write, make_citekey, read_frontmatter
from studi.prompts import EXTRACTION_SYSTEM, KIND_ADDENDA, SYNTHESIS_SYSTEM, synthesis_user
from studi.sections import segment
from studi.templates import join_note, render_evidence_block, render_paper_note, split_note, strip_block, upsert_block, wrap

UA = {"User-Agent": "StudiumObsidian/1.0 (personal literature notes)"}
MAX_SECTION_CHARS = 20000
SECTION_LIMITS = {"methods": 20000, "methods_supplement": 8000, "results": 20000, "discussion": 6000}
EXTRACT_TIMEOUT = int(os.environ.get("ANTIGRAVITY_STUDY_TIMEOUT", "600"))      # secondi per singola estrazione
EXTRACT_EFFORT = os.environ.get("ANTIGRAVITY_STUDY_EFFORT", "medium")


def resolve_vault_root() -> Path:
    env = os.environ.get("ANTIGRAVITY_VAULT_DIR")
    if env:
        return Path(env).expanduser().resolve()
    for parent in Path(__file__).resolve().parents:
        if (parent / ".obsidian").exists():
            return parent
    return Path(__file__).resolve().parents[2]


VAULT = resolve_vault_root()
STUDI_DIR = VAULT / "Bodybuilding" / "Studi"
DATA_DIR = VAULT / ".antigravity" / "studi-data"
BACKUP_DIR = VAULT / ".antigravity" / "backups"
RUNTIME = Path(os.environ.get("ANTIGRAVITY_RUNTIME_DIR") or "/tmp/antigravity_runtime") / "studi"


class StepError(Exception):
    pass


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(VAULT))
    except ValueError:
        return str(p)


def log(msg: str) -> None:
    print(f"> {msg}", flush=True)


# ====================================================================== agy

def resolve_agy() -> str:
    cand = Path.home() / ".local" / "bin" / "agy"
    if cand.exists() and os.access(cand, os.X_OK):
        return str(cand)
    found = shutil.which("agy")
    if not found:
        raise StepError("CLI agy non trovata (attesa in ~/.local/bin/agy)")
    return found


def inline_refs(schema: dict) -> dict:
    """Espande i $ref locali (#/$defs/...) in uno schema autonomo: agy non risolve i riferimenti di Pydantic."""
    defs = schema.get("$defs", {})

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                target = walk(defs[ref.split("/")[-1]])
                extra = {k: walk(v) for k, v in node.items() if k != "$ref"}
                return {**target, **extra}
            return {k: walk(v) for k, v in node.items() if k != "$defs"}
        if isinstance(node, list):
            return [walk(x) for x in node]
        return node

    return walk(schema)


def agy_json(prompt: str, schema: dict, timeout: int = 1500, effort: str = "") -> dict:
    """agy in print mode con output vincolato allo schema; ritorna structured_output."""
    schema = inline_refs(schema)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    schema_path = RUNTIME / f"schema-{hashlib.sha1(json.dumps(schema).encode()).hexdigest()[:10]}.json"
    if not schema_path.exists():
        tmp = schema_path.with_name(f".{schema_path.name}.{os.getpid()}.{threading.get_ident()}")
        tmp.write_text(json.dumps(schema), encoding="utf-8")
        os.replace(tmp, schema_path)
    cmd = [resolve_agy(), "-p", prompt, "--output-format", "json", "--json-schema", str(schema_path),
           "--print-timeout", f"{timeout}s"] + (["--effort", effort] if effort else [])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 90, check=False)
    except subprocess.TimeoutExpired as e:
        raise StepError(f"agy non ha risposto entro {timeout}s") from e
    out = (proc.stdout or "").strip()
    if re.search(r"quota_exhausted|resource_exhausted|rate.?limit|\b429\b", out + proc.stderr, re.I):
        raise StepError("agy ha finito la quota di Antigravity: riprova piu' tardi")
    for cand in [out] + [l for l in reversed(out.splitlines()) if l.strip().startswith("{")]:
        try:
            data = json.loads(cand)
        except Exception:
            continue
        if isinstance(data.get("structured_output"), dict):
            return data["structured_output"]
        if isinstance(data.get("response"), str):
            try:
                return json.loads(data["response"])
            except Exception:
                pass
    raise StepError(f"risposta di agy non interpretabile: {(out or proc.stderr)[:300]}")


def _errors(e: Exception) -> str:
    if isinstance(e, ValidationError):
        return "\n".join(f"- {'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()[:25])
    return f"- {e}"


# ====================================================================== metadati e testo completo

def _author_last_first(name: str) -> str:
    name = name.strip()
    if not name or "," in name:
        return name
    parts = name.split()
    return f"{parts[-1]}, {' '.join(parts[:-1])}" if len(parts) > 1 else name


def idconv(identifier: str) -> dict:
    """DOI / PMID / PMCID -> {pmid, pmcid, doi} tramite la ricerca di Europe PMC."""
    s = identifier.strip()
    if re.fullmatch(r"\d{1,9}", s):
        query = f"EXT_ID:{s} AND SRC:MED"
    elif re.fullmatch(r"PMC\d+", s, re.I):
        query = f"PMCID:{s.upper()}"
    else:
        query = f'DOI:"{s}"'
    try:
        r = requests.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                         params={"query": query, "format": "json", "resultType": "lite", "pageSize": 2},
                         headers=UA, timeout=25)
        res = r.json().get("resultList", {}).get("result", []) if r.ok else []
    except Exception:
        res = []
    rec = res[0] if len(res) == 1 else {}
    out = {k: str(rec[k]) for k in ("pmid", "pmcid", "doi") if rec.get(k)}
    if out.get("doi"):
        out["doi"] = out["doi"].lower()
    return out


def pmid_from_doi(doi: str) -> Optional[str]:
    try:
        r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                         params={"db": "pubmed", "term": f"{doi}[doi]", "retmode": "json"}, headers=UA, timeout=25)
        ids = r.json().get("esearchresult", {}).get("idlist", []) if r.ok else []
    except Exception:
        ids = []
    return ids[0] if len(ids) == 1 else None


def pubmed_meta(pmid: str) -> dict:
    r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                     params={"db": "pubmed", "id": pmid, "retmode": "xml"}, headers=UA, timeout=30)
    if not r.ok:
        return {}
    art = ET.fromstring(r.content).find(".//PubmedArticle")
    if art is None:
        return {}

    def txt(el):
        return re.sub(r"\s+", " ", "".join(el.itertext())).strip() if el is not None else ""

    authors = []
    for a in art.findall(".//AuthorList/Author"):
        last, fore = txt(a.find("LastName")), txt(a.find("ForeName"))
        if last:
            authors.append(f"{last}, {fore}".strip(", "))
        elif a.find("CollectiveName") is not None:
            authors.append(txt(a.find("CollectiveName")))
    year = txt(art.find(".//JournalIssue/PubDate/Year")) or txt(art.find(".//ArticleDate/Year"))
    if not year:
        m = re.search(r"(19|20)\d{2}", txt(art.find(".//JournalIssue/PubDate/MedlineDate")))
        year = m.group(0) if m else ""
    doi = txt(art.find(".//ArticleIdList/ArticleId[@IdType='doi']")) or txt(art.find(".//ELocationID[@EIdType='doi']"))
    pmc = txt(art.find(".//ArticleIdList/ArticleId[@IdType='pmc']"))
    abstract = " ".join(
        (f"{p.get('Label')}: " if p.get("Label") else "") + txt(p) for p in art.findall(".//Abstract/AbstractText"))
    return {"title": txt(art.find(".//ArticleTitle")).rstrip("."), "authors": authors,
            "year": int(year) if year.isdigit() else None, "journal": txt(art.find(".//Journal/Title")),
            "doi": doi.lower() or None, "pmid": pmid, "pmcid": pmc or None, "abstract": abstract}


def openalex_meta(doi: str) -> dict:
    try:
        r = requests.get(f"https://api.openalex.org/works/doi:{doi}", headers=UA, timeout=25)
        w = r.json() if r.ok else {}
    except Exception:
        w = {}
    if not w:
        return {}
    inv = w.get("abstract_inverted_index") or {}
    pos = {i: word for word, idx in inv.items() for i in idx}
    pdfs = [loc.get("pdf_url") for loc in ([w.get("best_oa_location")] + (w.get("locations") or [])) if loc and loc.get("pdf_url")]
    return {"title": w.get("title") or w.get("display_name"), "year": w.get("publication_year"),
            "authors": [_author_last_first(a.get("author", {}).get("display_name", "")) for a in w.get("authorships", [])],
            "journal": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
            "abstract": " ".join(pos[i] for i in sorted(pos)), "pdf_urls": list(dict.fromkeys(pdfs)),
            "pmid": str((w.get("ids") or {}).get("pmid", "")).rsplit("/", 1)[-1] or None}


def europepmc_jats(pmcid: str) -> Optional[str]:
    try:
        r = requests.get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML", headers=UA, timeout=40)
    except Exception:
        return None
    if not r.ok or b"<body" not in r.content:
        return None
    try:
        jd = parse_jats(r.content)
    except ET.ParseError:
        return None
    return jd.markdown if jd.has_fulltext else None


def pdf_text(path: Path) -> str:
    from pdf_extract import extract_pdf_data
    data = extract_pdf_data(path, RUNTIME / "pdf-img" / path.stem[:40])
    return "\n\n".join(p.get("text", "") for p in data.get("pages", []))


def download_pdf(url: str) -> Optional[Path]:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    try:
        r = requests.get(url, headers={**UA, "Accept": "application/pdf"}, timeout=60, allow_redirects=True)
    except Exception:
        return None
    if not r.ok or not r.content.startswith(b"%PDF") or len(r.content) < 50_000:
        return None
    p = RUNTIME / f"oa-{hashlib.sha1(url.encode()).hexdigest()[:10]}.pdf"
    p.write_bytes(r.content)
    return p


_DOI_RX = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>\]\)]+)", re.I)


def load_source(source: str) -> dict:
    """-> {doi, meta, markdown, flags}"""
    s = source.strip().strip("'\"")
    p = Path(s).expanduser()
    if not p.is_absolute():
        p = VAULT / s
    flags: list[str] = []
    if p.suffix.lower() == ".pdf" and p.is_file():
        log(f"Lettura del PDF {p.name}")
        md = pdf_text(p)
        m = _DOI_RX.search(md[:8000])
        doi = normalize_doi(m.group(1).rstrip(".,;")) if m else f"urn:sha256:{hashlib.sha256(p.read_bytes()).hexdigest()}"
        meta: dict = {}
        if doi.startswith("10."):
            pmid = idconv(doi).get("pmid") or pmid_from_doi(doi)
            meta = pubmed_meta(pmid) if pmid else openalex_meta(doi)
        else:
            flags.append("no_doi_found_using_sha256_urn")
        if not meta.get("title"):
            first = next((l.strip() for l in md.splitlines() if len(l.strip()) > 20), p.stem)
            meta["title"] = first[:200]
        return {"doi": doi, "meta": meta, "markdown": md, "flags": flags}

    ids: dict = {}
    if re.fullmatch(r"\d{1,9}", s):
        ids["pmid"] = s
    elif re.fullmatch(r"PMC\d+", s, re.I):
        ids["pmcid"] = s.upper()
    else:
        m = _DOI_RX.search(s)
        if not m:
            raise StepError(f"identificatore non riconosciuto: {source!r} (atteso DOI, PMID, PMCID o percorso PDF)")
        ids["doi"] = normalize_doi(m.group(1).rstrip(".,;"))
    log("Risoluzione identificatori (Europe PMC)")
    ids = {**idconv(next(iter(ids.values()))), **ids}
    if not ids.get("pmid") and ids.get("doi"):
        ids["pmid"] = pmid_from_doi(ids["doi"])
    meta = pubmed_meta(ids["pmid"]) if ids.get("pmid") else {}
    doi = ids.get("doi") or meta.get("doi")
    if not doi:
        raise StepError("DOI non trovato per questo identificatore")
    oa = openalex_meta(doi)
    meta = {**{k: v for k, v in oa.items() if v}, **{k: v for k, v in meta.items() if v}}
    pmcid = ids.get("pmcid") or meta.get("pmcid")
    md = None
    if pmcid:
        log(f"Testo completo da Europe PMC ({pmcid})")
        md = europepmc_jats(pmcid)
    if not md:
        for url in oa.get("pdf_urls", []):
            log(f"PDF open access: {url[:90]}")
            pdf = download_pdf(url)
            if pdf:
                md = pdf_text(pdf)
                break
    if not md:
        raise StepError("testo completo non disponibile in open access: scarica il PDF e usa 'Nota Studio da PDF'")
    return {"doi": doi, "meta": meta, "markdown": md, "flags": flags}


# ====================================================================== Modalita' 1

def extraction_schema() -> dict:
    schema = Envelope.model_json_schema()
    for d in schema.get("$defs", {}).values():
        for k in ("audit", "audit_statistical_discrepancy"):
            d.get("properties", {}).pop(k, None)
            if k in d.get("required", []):
                d["required"].remove(k)
    return schema


def build_user_prompt(doi: str, meta: dict, markdown: str, flags: list[str]) -> tuple[str, list[str]]:
    seg = segment(markdown)
    flags = flags + seg.flags
    parts = [f"DOI: {doi}", f"TITLE: {meta.get('title', '')}", f"YEAR: {meta.get('year', '')}",
             f"ABSTRACT:\n{meta.get('abstract') or '(not available)'}"]
    used = False
    for key, label in (("methods", "METHODS"), ("methods_supplement", "SUPPLEMENTARY METHODS"),
                       ("results", "RESULTS"), ("discussion", "DISCUSSION")):
        if key in seg.sections:
            parts.append(f"## {label}\n{seg.sections[key][:SECTION_LIMITS[key]]}")
            used = used or key in ("methods", "results")
    if not used:
        flags.append("segmentation_failed_full_text_fallback")
        parts.append(f"## FULL TEXT (unsegmented)\n{markdown[:MAX_SECTION_CHARS * 3]}")
    parts.append(f"PARSER FLAGS: {', '.join(flags) or 'none'}")
    return "\n\n".join(parts), flags


def _valid_spread(sp: Any) -> bool:
    if not isinstance(sp, dict):
        return False
    kind = sp.get("kind")
    if kind in ("sd", "sem"):
        return isinstance(sp.get("value"), (int, float)) and sp["value"] > 0
    if kind == "ci95":
        lo, hi = sp.get("lower"), sp.get("upper")
        return isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and hi > lo
    return False


def repair_payload(payload: dict) -> list[str]:
    """Ripara in modo deterministico i difetti tipici dell'estrazione invece di rifarla da capo:
    statistiche senza dispersione valida -> tolte; effetti senza valore -> tolti; blocchi vuoti -> tolti."""
    fixes: list[str] = []
    doc = payload.get("document") if isinstance(payload, dict) else None
    if not isinstance(doc, dict):
        return fixes
    for i, o in enumerate(doc.get("outcomes") or []):
        if not isinstance(o, dict):
            continue
        for cname in ("condition_a", "condition_b"):
            c = o.get(cname)
            if not isinstance(c, dict):
                continue
            for st in ("pre", "post", "change"):
                v = c.get(st)
                if v is None:
                    continue
                if not isinstance(v, dict) or not isinstance(v.get("mean"), (int, float)) or not _valid_spread(v.get("spread")):
                    c[st] = None
                    fixes.append(f"outcomes[{i}].{cname}.{st}")
        re_ = o.get("reported_effect")
        if re_ is not None and (not isinstance(re_, dict) or not isinstance(re_.get("value"), (int, float))):
            o["reported_effect"] = None
            fixes.append(f"outcomes[{i}].reported_effect")
        pr = o.get("paired")
        if isinstance(pr, dict):
            for k in ("sd_diff",):
                if isinstance(pr.get(k), (int, float)) and pr[k] <= 0:
                    pr[k] = None
            if isinstance(pr.get("p_exact"), (int, float)) and not 0 < pr["p_exact"] < 1:
                pr["p_exact"] = None
    return fixes


def extract(doi: str, user: str, retries: int = 2) -> Envelope:
    system = EXTRACTION_SYSTEM.replace("JSON Schema:\n<<SCHEMA>>", "The JSON Schema is enforced by the caller.")
    schema = extraction_schema()
    err = ""
    for attempt in range(retries + 1):
        log(f"Estrazione con agy (tentativo {attempt + 1}/{retries + 1})")
        payload = agy_json(f"{system}\n\nDo not use tools: answer only from the text below.\n\n{user}{err}", schema,
                           timeout=EXTRACT_TIMEOUT, effort=EXTRACT_EFFORT)
        fixes = repair_payload(payload)
        if fixes:
            log(f"Riparati {len(fixes)} campi incompleti senza rifare l'estrazione")
        try:
            doc = payload.get("document", {})
            doc["doi"] = doi
            doc.pop("audit_statistical_discrepancy", None)
            for o in doc.get("outcomes", []) or []:
                o.pop("audit", None)
            return Envelope.model_validate(payload)
        except (ValueError, AttributeError, TypeError) as e:
            err = "\n\nYOUR PREVIOUS OUTPUT WAS REJECTED BY THE VALIDATOR. Return the full corrected JSON. Errors:\n" + _errors(e)
            log("Estrazione respinta dal validatore: " + _errors(e).splitlines()[0])
    raise StepError("estrazione non valida dopo i tentativi: " + err.splitlines()[-1][:200])


def create_study_note(source: str, overwrite: bool = False, preloaded: Optional[dict] = None, retries: int = 2) -> Path:
    """Testo completo -> estrazione agy -> validazione/audit -> Nota Studio + sidecar. Ritorna il percorso della nota."""
    src = preloaded or load_source(source)
    meta = src["meta"]
    user, flags = build_user_prompt(src["doi"], meta, src["markdown"], src["flags"])
    env = extract(src["doi"], user, retries=retries)
    meta_note = {k: v for k, v in meta.items() if k not in ("abstract", "pdf_urls")}
    ck0 = make_citekey(meta_note.get("authors", []), meta_note.get("year"), meta_note.get("title", ""), env.document.doi)
    prev = STUDI_DIR / f"{ck0}.md"
    if prev.exists() and not overwrite:
        old = read_frontmatter(prev)
        if old.get("status") not in ("needs_review", None):
            raise StepError(f"la nota {prev.name} esiste gia' (status {old.get('status')}): usa 'sovrascrivi'")
    concepts = (read_frontmatter(prev).get("concepts") or []) if prev.exists() else []
    job = f"studio-{dt.datetime.now():%Y%m%d-%H%M%S}"
    ck, text, sidecar = render_paper_note(env.document, env.narrative, meta_note, job, flags, concepts)
    atomic_write(DATA_DIR / f"{ck}.json", json.dumps(sidecar, ensure_ascii=False, indent=1))
    path = STUDI_DIR / f"{ck}.md"
    atomic_write(path, text)
    return path


def cmd_paper(source: str, overwrite: bool) -> str:
    path = create_study_note(source, overwrite)
    fm = read_frontmatter(path)
    warn = []
    if fm.get("audit_statistical_discrepancy"):
        warn.append("discrepanza statistica")
    if not fm.get("usable_for_conclusions"):
        warn.append("non utilizzabile per conclusioni: " + ", ".join(fm.get("evidence_gates") or []))
    return f"{rel(path)} - evidenza {fm.get('evidence_level')} (peso {fm.get('evidence_weight')})" + (f" - {'; '.join(warn)}" if warn else "")


# ====================================================================== Modalita' 2

def resolve_study(ref: str) -> Optional[str]:
    ref = ref.strip().removeprefix("[[").removesuffix("]]").split("|")[0].strip()
    if (STUDI_DIR / f"{ref}.md").exists() and (DATA_DIR / f"{ref}.json").exists():
        return ref
    want = ref.lower().removeprefix("https://doi.org/").removeprefix("doi:")
    for p in STUDI_DIR.glob("*.md"):
        fm = read_frontmatter(p)
        names = [str(fm.get("doi", "")).lower(), str(fm.get("pmid", "")), str(fm.get("title", "")).lower()]
        if want in names or ref in (fm.get("aliases") or []):
            return fm.get("citekey") or p.stem
    return None


def backlink(concept: str, cks: list[str]) -> None:
    for ck in cks:
        p = STUDI_DIR / f"{ck}.md"
        if not p.exists():
            continue
        fm, body = split_note(p.read_text(encoding="utf-8"))
        cs = list(dict.fromkeys([*(fm.get("concepts") or []), concept]))
        fm["concepts"] = cs
        if "## Concetti collegati" not in body:
            body = body.rstrip("\n") + "\n\n## Concetti collegati\n"
        atomic_write(p, join_note(fm, upsert_block(body, "concepts", wrap("concepts", "\n".join(f"- [[{c}]]" for c in cs)))))


def cmd_concept(note: str, papers: list[str], kind: str) -> str:
    if kind not in KIND_ADDENDA:
        raise StepError(f"tipo di nota non valido: {kind}")
    path = Path(note).expanduser()
    path = path if path.is_absolute() else VAULT / note
    if not path.is_file():
        raise StepError(f"nota non trovata: {note}")
    concept = path.stem
    cards, missing = {}, []
    for ref in papers:
        ck = resolve_study(ref)
        card = load_card(DATA_DIR, ck) if ck else None
        if card:
            cards[ck] = card
        else:
            missing.append(ref)
    if not cards:
        raise StepError("nessuno degli studi indicati ha una Nota Studio generata da questo strumento")
    text = path.read_text(encoding="utf-8")
    fm_text, body = "", text
    if text.startswith("---\n") and text.find("\n---", 4) > 0:
        end = text.find("\n---", 4) + 4
        fm_text, body = text[:end], text[end:]
    ordered = sorted(cards.values(), key=lambda c: (-c.usable, -c.weight))
    user = synthesis_user(concept, kind, [c.for_prompt() for c in ordered], strip_block(body, "evidence"))
    schema = Synthesis.model_json_schema()
    err = ""
    for attempt in range(3):
        log(f"Sintesi critica con agy (tentativo {attempt + 1}/3)")
        raw = agy_json(f"{SYNTHESIS_SYSTEM}{KIND_ADDENDA[kind]}\n\nDo not use tools.\n\n{user}{err}", schema)
        try:
            syn = Synthesis.model_validate(raw)
            break
        except ValueError as e:
            err = "\n\nPREVIOUS OUTPUT REJECTED. Return the full corrected JSON.\n" + _errors(e)
    else:
        raise StepError("sintesi non valida dopo 3 tentativi")
    checked = enforce_claims(syn.claims, cards)
    block = render_evidence_block(concept, kind, syn, checked, cards)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, BACKUP_DIR / f"{path.stem}.{dt.datetime.now():%Y%m%d-%H%M%S}.md")
    atomic_write(path, fm_text + upsert_block(body, "evidence", block))
    backlink(concept, list(cards))
    downgraded = sum(1 for c in checked if c.final != c.claim.strength)
    out = (f"{rel(path)} - {len(cards)} studi ({sum(c.usable for c in cards.values())} utilizzabili), "
           f"{len(checked)} affermazioni ({downgraded} declassate)")
    return out + (f" - non trovati: {', '.join(missing)}" if missing else "")


def main() -> int:
    ap = argparse.ArgumentParser(description="Studi scientifici di Bodybuilding nel vault (via agy)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("paper")
    p.add_argument("source")
    p.add_argument("--overwrite", action="store_true")
    c = sub.add_parser("concept")
    c.add_argument("note")
    c.add_argument("--papers", nargs="+", required=True)
    c.add_argument("--kind", default="principle", choices=sorted(KIND_ADDENDA))
    a = ap.parse_args()
    try:
        res = cmd_paper(a.source, a.overwrite) if a.cmd == "paper" else cmd_concept(a.note, a.papers, a.kind)
    except StepError as e:
        print(f"ERRORE: {e}", flush=True)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"ERRORE: {type(e).__name__}: {e}", flush=True)
        return 1
    print(f"RISULTATO: {res}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
