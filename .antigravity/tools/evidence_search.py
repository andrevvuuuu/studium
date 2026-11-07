#!/usr/bin/env python3
"""
evidence_search.py - Ricerca automatica e analisi critica degli studi su un argomento di Bodybuilding.

Dall'argomento (italiano) al dossier delle evidenze usato da orchestrator.py per scrivere la nota:
  1. query      agy traduce l'argomento (e, se c'e', il testo della fonte) in 3-5 query PubMed in inglese;
  2. ricerca    Europe PMC (comprende PubMed, segnala gli articoli open access e il PMCID);
  3. selezione  agy sceglie gli studi primari longitudinali pertinenti e le revisioni/meta-analisi;
  4. analisi    per ogni studio primario: Nota Studio gia' presente -> riuso; testo completo open access ->
                estrazione vincolata, ricalcolo dell'effect size per disegno, SEM->SD, spin, gate (paper_note.py);
                altrimenti resta "solo abstract" (non verificato, non utilizzabile per conclusioni);
  5. dossier    evidence_dossier.md (per la scrittura) + pubmed_evidence.json (compatibile con la verifica).

Uso da terminale:
  python3 .antigravity/tools/evidence_search.py "Stretch-Mediated Hypertrophy" --out-dir /tmp/x [--context-file f.md]
Variabili: ANTIGRAVITY_MAX_STUDIES (studi primari da analizzare, default 6), ANTIGRAVITY_STUDY_WORKERS (default 3).
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import paper_note as pn  # noqa: E402  (rilancia con il Python giusto se mancano le librerie)
from studi.evidence import load_card  # noqa: E402

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
Progress = Callable[[str, int, int], None]

QUERY_SCHEMA = {
    "type": "object",
    "properties": {"queries": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 5}},
    "required": ["queries"],
}
SCREEN_SCHEMA = {
    "type": "object",
    "properties": {
        "primary": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"}, "reason": {"type": "string"}}, "required": ["id", "reason"]}},
        "reviews": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string"}, "reason": {"type": "string"}}, "required": ["id", "reason"]}},
    },
    "required": ["primary", "reviews"],
}


def _log(msg: str) -> None:
    sys.stderr.write(f"[Evidenze] {msg}\n")
    sys.stderr.flush()


# ---------------------------------------------------------------------- 1. query

def plan_queries(topic: str, context_text: str = "") -> List[str]:
    prompt = (
        "You build PubMed/Europe PMC search queries for resistance-training science.\n"
        f"Topic of an Italian bodybuilding note: \"{topic}\".\n"
        + (f"Excerpt of the note's source material (for context):\n{context_text[:4000]}\n" if context_text.strip() else "")
        + "Return 3-5 English queries that retrieve LONGITUDINAL training studies (RCTs, within-subject unilateral trials) "
          "and meta-analyses measuring muscle hypertrophy (muscle thickness, CSA, MRI, ultrasound) or strength on this topic. "
          "Use specific terms (muscle names, exercise names, training variables), boolean AND/OR, quotes for phrases. "
          "Each query must be short (max ~12 words). Do not use tools."
    )
    try:
        out = pn.agy_json(prompt, QUERY_SCHEMA, timeout=240, effort="low")
        qs = [q.strip() for q in out.get("queries", []) if q and q.strip()]
    except Exception as e:  # noqa: BLE001
        _log(f"query via agy non riuscite ({e}): uso l'argomento")
        qs = []
    base = re.sub(r"[^\w\s-]", " ", topic).strip()
    return list(dict.fromkeys(qs or [f"{base} AND (hypertrophy OR \"muscle thickness\")", base]))[:5]


# ---------------------------------------------------------------------- 2. ricerca

def search_europepmc(query: str, n: int = 15) -> List[Dict[str, Any]]:
    q = f"({query}) AND SRC:MED"
    try:
        r = pn.requests.get(EPMC, params={"query": q, "format": "json", "resultType": "core", "pageSize": n},
                            headers=pn.UA, timeout=40)
        res = r.json().get("resultList", {}).get("result", []) if r.ok else []
    except Exception as e:  # noqa: BLE001
        _log(f"ricerca fallita per {query!r}: {e}")
        return []
    out = []
    for x in res:
        out.append({
            "pmid": x.get("pmid"), "pmcid": x.get("pmcid"), "doi": (x.get("doi") or "").lower() or None,
            "title": re.sub(r"<[^>]+>", "", x.get("title") or "").strip().rstrip("."),
            "authors": x.get("authorString") or "", "year": int(x["pubYear"]) if str(x.get("pubYear", "")).isdigit() else None,
            "journal": ((x.get("journalInfo") or {}).get("journal") or {}).get("title") or "",
            "open_access": x.get("isOpenAccess") == "Y" or bool(x.get("pmcid")),
            "pub_types": [t for t in ((x.get("pubTypeList") or {}).get("pubType") or [])],
            "cited_by": x.get("citedByCount") or 0,
            "abstract": re.sub(r"<[^>]+>", " ", x.get("abstractText") or "").strip(),
        })
    return out


# ---------------------------------------------------------------------- 3. selezione

def _is_review(c: Dict[str, Any]) -> bool:
    t = " ".join(c.get("pub_types", [])).lower() + " " + c.get("title", "").lower()
    return any(k in t for k in ("meta-analysis", "systematic review", "review", "meta analysis"))


def screen(topic: str, cands: List[Dict[str, Any]], n_primary: int, n_reviews: int) -> tuple[list, list]:
    listing = "\n\n".join(
        f"[C{i}] {c['title']} ({c.get('year')}; {c.get('journal')}) | types: {', '.join(c.get('pub_types', [])[:3])} | "
        f"open access: {'yes' if c.get('open_access') else 'no'}\n{c.get('abstract', '')[:1200]}"
        for i, c in enumerate(cands))
    prompt = (
        f"Topic of an Italian bodybuilding note: \"{topic}\".\nCandidate papers:\n\n{listing}\n\n"
        f"Select up to {n_primary} PRIMARY longitudinal training studies (RCT, within-subject unilateral, crossover) that directly "
        f"test the topic and measure hypertrophy (MRI/CT/panoramic US > single-point ultrasound > DEXA > BIA) or, secondarily, strength. "
        f"Prefer trained/advanced participants, objective effort (training to failure or measured velocity loss), larger samples, "
        f"open access, more recent. Exclude acute/EMG-only studies, animal studies, clinical populations unless the topic requires them. "
        f"Also select up to {n_reviews} systematic reviews/meta-analyses directly on the topic. "
        "Use the bracket ids (e.g. C3). If nothing is relevant return empty lists. Do not use tools."
    )
    try:
        out = pn.agy_json(prompt, SCREEN_SCHEMA, timeout=600, effort="medium")
    except Exception as e:  # noqa: BLE001
        _log(f"selezione via agy non riuscita ({e}): uso l'ordine di rilevanza")
        prim = [c for c in cands if not _is_review(c)][:n_primary]
        return prim, [c for c in cands if _is_review(c)][:n_reviews]

    def pick(items: list, limit: int) -> list:
        chosen = []
        for it in items[:limit]:
            m = re.fullmatch(r"\[?C(\d+)\]?", str(it.get("id", "")).strip(), re.I)
            if m and int(m.group(1)) < len(cands):
                c = dict(cands[int(m.group(1))])
                c["reason"] = it.get("reason", "")
                if c not in chosen:
                    chosen.append(c)
        return chosen

    return pick(out.get("primary", []), n_primary), pick(out.get("reviews", []), n_reviews)


# ---------------------------------------------------------------------- 4. analisi

_lock = threading.Lock()


def _label(c: Dict[str, Any]) -> str:
    first = (c.get("authors") or "Anon").split(",")[0].strip()
    surname = first.split()[0] if first else "Anon"
    more = " et al." if (c.get("authors") or "").count(",") >= 2 else ""
    return f"{surname}{more} {c.get('year') or 'n.d.'}"


def analyze_primary(c: Dict[str, Any]) -> Dict[str, Any]:
    """-> {status: analyzed|reused|abstract_only|failed, citekey?, card?, candidate}"""
    ident = c.get("doi") or c.get("pmcid") or c.get("pmid")
    out: Dict[str, Any] = {"candidate": c, "status": "abstract_only"}
    if not ident:
        return out
    with _lock:
        ck = pn.resolve_study(c["doi"]) if c.get("doi") else None
        ck = ck or (pn.resolve_study(str(c["pmid"])) if c.get("pmid") else None)
    if ck:
        card = load_card(pn.DATA_DIR, ck)
        if card:
            return {**out, "status": "reused", "citekey": ck, "card": card}
    try:
        src = pn.load_source(c.get("pmcid") or c.get("doi") or str(c.get("pmid")))
    except pn.StepError as e:
        _log(f"{_label(c)}: niente testo completo ({e})")
        return out
    except Exception as e:  # noqa: BLE001
        _log(f"{_label(c)}: acquisizione fallita ({e})")
        return out
    try:
        path = pn.create_study_note("", overwrite=False, preloaded=src)
    except pn.StepError as e:
        if "esiste gia'" in str(e):
            ck = pn.resolve_study(src["doi"])
            card = load_card(pn.DATA_DIR, ck) if ck else None
            if card:
                return {**out, "status": "reused", "citekey": ck, "card": card}
        _log(f"{_label(c)}: analisi non riuscita ({e})")
        return {**out, "status": "failed", "error": str(e)}
    except Exception as e:  # noqa: BLE001
        _log(f"{_label(c)}: analisi non riuscita ({type(e).__name__}: {e})")
        return {**out, "status": "failed", "error": str(e)}
    ck = path.stem
    return {**out, "status": "analyzed", "citekey": ck, "card": load_card(pn.DATA_DIR, ck)}


# ---------------------------------------------------------------------- 5. dossier

LEVEL_IT = {"high": "alto", "moderate": "medio", "low": "basso", "insufficient": "insufficiente"}


def _pm_link(c: Dict[str, Any]) -> str:
    return f"[PMID {c['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{c['pmid']}/)" if c.get("pmid") else (
        f"[DOI](https://doi.org/{c['doi']})" if c.get("doi") else "")


def render_dossier(topic: str, queries: List[str], results: List[Dict[str, Any]], reviews: List[Dict[str, Any]]) -> str:
    analyzed = sorted([r for r in results if r.get("card")], key=lambda r: (-r["card"].usable, -r["card"].weight))
    abstract_only = [r for r in results if not r.get("card")]
    L = [f"# Dossier delle evidenze — {topic}", "",
         f"Query eseguite su Europe PMC/PubMed: {'; '.join(f'`{q}`' for q in queries)}", "",
         "## Come usare questo dossier",
         "- Ogni affermazione empirica della nota deve provenire da questi studi. Non citare studi o PMID che non sono qui.",
         "- Ordine di peso gia' calcolato: misura (MRI/fCSA > ecografia > DEXA > BIA), popolazione (avanzati verificati > allenati > ricreativi > principianti), sforzo (cedimento oggettivo > RIR > prescrizione fissa > volizionale), qualita', spin e audit statistico.",
         "- Gli studi con **Utilizzabile = no** o letti **solo nell'abstract** non possono sostenere conclusioni o regole pratiche: citali come indizi o lacune.",
         "- Cita gli studi analizzati con il link alla loro Nota Studio (colonna Studio), es. `[[citekey|Autore et al. Anno]]`.",
         "- Dichiara la forza di ogni conclusione: solida (≥2 studi utilizzabili concordi, almeno uno di livello alto), moderata (≥1 utilizzabile di livello medio/alto), provvisoria, insufficiente.",
         "- Effetti: d_z non e' confrontabile con d tra gruppi; nei disegni unilaterali N = persone, non arti.", ""]
    L += ["## Studi primari analizzati sul testo completo (ordinati per peso)", ""]
    if analyzed:
        L += ["| Studio | Peso | Livello | Utilizzabile | Disegno | N (arti) | Popolazione | Misura | Sforzo | Spin | Audit | Fonte |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in analyzed:
            k, c = r["card"], r["candidate"]
            n = f"{k.n_participants} ({k.n_limbs})" if k.n_limbs else str(k.n_participants)
            pop = k.training_status + (" verificato" if k.advanced_verified else "")
            L.append(f"| [[{k.citekey}\\|{k.label}]] | {k.weight:.2f} | {LEVEL_IT[k.level]} | {'si' if k.usable else 'no'} | "
                     f"{k.design} | {n} | {pop} | {k.best_tool or '-'} | {k.effort} | {k.spin_severity} | {k.worst_tier or '-'} | {_pm_link(c)} |")
        L.append("")
        for r in analyzed:
            k = r["card"]
            L += [f"### [[{k.citekey}|{k.label}]] — {k.title}",
                  f"- **Sintesi:** {k.takeaway or '-'}"]
            L += [f"- **Risultato ricalcolato:** {f}" for f in k.findings]
            if k.gates:
                L.append(f"- **Limiti che lo escludono dalle conclusioni:** {', '.join(k.gates)}")
            L.append("")
    else:
        L += ["*(Nessuno studio primario con testo completo disponibile e analizzabile.)*", ""]
    if abstract_only:
        L += ["## Studi primari letti solo nell'abstract (non verificati, non utilizzabili per conclusioni)", ""]
        for r in abstract_only:
            c = r["candidate"]
            L += [f"- **{_label(c)}** — {c['title']} ({c.get('journal')}) {_pm_link(c)}",
                  f"  - Abstract: {c.get('abstract', '')[:900]}"]
        L.append("")
    if reviews:
        L += ["## Revisioni sistematiche e meta-analisi (contesto, dall'abstract)", ""]
        for c in reviews:
            L += [f"- **{_label(c)}** — {c['title']} ({c.get('journal')}) {_pm_link(c)}",
                  f"  - Abstract: {c.get('abstract', '')[:1200]}"]
        L.append("")
    return "\n".join(L).rstrip() + "\n"


def _article_json(c: Dict[str, Any], r: Optional[Dict[str, Any]], kind: str) -> Dict[str, Any]:
    a = {"pmid": c.get("pmid") or "N/D", "pmcid": c.get("pmcid"), "doi": c.get("doi") or "N/D", "title": c.get("title"),
         "first_author": _label(c).rsplit(" ", 1)[0], "authors": c.get("authors"), "year": c.get("year") or "N/D",
         "journal": c.get("journal"), "url": f"https://pubmed.ncbi.nlm.nih.gov/{c['pmid']}/" if c.get("pmid") else None,
         "publication_types": c.get("pub_types", []), "abstract": c.get("abstract", ""), "kind": kind,
         "selection_reason": c.get("reason", "")}
    if r and r.get("card"):
        k = r["card"]
        a.update(analysis="full_text", study_note=f"[[{k.citekey}|{k.label}]]", evidence_weight=k.weight,
                 evidence_level=k.level, usable_for_conclusions=k.usable, gates=k.gates, design=k.design,
                 n_participants=k.n_participants, n_limbs=k.n_limbs, training_status=k.training_status,
                 measurement_tool=k.best_tool, effort=k.effort, spin=k.spin_severity, audit=k.worst_tier,
                 takeaway=k.takeaway, recomputed_findings=k.findings)
    else:
        a.update(analysis="abstract_only" if kind == "primary" else "review_abstract", usable_for_conclusions=False)
    return a


def build_dossier(topic: str, out_dir: Path, context_text: str = "", progress: Optional[Progress] = None,
                  max_primary: Optional[int] = None, max_reviews: int = 3) -> Dict[str, Any]:
    max_primary = max_primary or int(os.environ.get("ANTIGRAVITY_MAX_STUDIES", "6"))
    workers = int(os.environ.get("ANTIGRAVITY_STUDY_WORKERS", "3"))
    say = progress or (lambda msg, done, total: _log(f"{msg} ({done}/{total})"))
    out_dir.mkdir(parents=True, exist_ok=True)

    say("Preparo le query per la ricerca degli studi", 0, 1)
    queries = plan_queries(topic, context_text)
    _log(f"query: {queries}")
    cands: List[Dict[str, Any]] = []
    seen: set = set()
    for i, q in enumerate(queries):
        say(f"Cerco studi su Europe PMC: {q}", i, len(queries))
        for c in search_europepmc(q):
            key = c.get("doi") or c.get("pmid") or c.get("title")
            if key and key not in seen:
                seen.add(key)
                cands.append(c)
    cands = cands[:45]
    if not cands:
        return {"queries": queries, "articles": [], "dossier_path": None, "analyzed": 0}

    say(f"Seleziono gli studi pertinenti tra {len(cands)} candidati", 0, 1)
    primary, reviews = screen(topic, cands, max_primary, max_reviews)
    _log(f"selezionati {len(primary)} primari e {len(reviews)} revisioni")

    results: List[Dict[str, Any]] = []
    done = 0
    say(f"Analisi critica degli studi sul testo completo", 0, len(primary))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = {ex.submit(analyze_primary, c): c for c in primary}
        for f in concurrent.futures.as_completed(futs):
            results.append(f.result())
            done += 1
            say(f"Analisi critica degli studi sul testo completo", done, len(primary))

    order = {id(c): i for i, c in enumerate(primary)}
    results.sort(key=lambda r: order.get(id(r["candidate"]), 0))
    dossier = render_dossier(topic, queries, results, reviews)
    dossier_path = out_dir / "evidence_dossier.md"
    dossier_path.write_text(dossier, encoding="utf-8")
    articles = [_article_json(r["candidate"], r, "primary") for r in results] + [_article_json(c, None, "review") for c in reviews]
    bundle = {"queries_executed": queries, "total_articles": len(articles), "articles": articles,
              "dossier_path": str(dossier_path),
              "analyzed": sum(1 for r in results if r.get("card")),
              "usable": sum(1 for r in results if r.get("card") and r["card"].usable)}
    (out_dir / "pubmed_evidence.json").write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    return bundle


def main() -> int:
    ap = argparse.ArgumentParser(description="Ricerca e analisi critica degli studi su un argomento di Bodybuilding")
    ap.add_argument("topic")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--context-file")
    ap.add_argument("--max", type=int, default=None, help="studi primari da analizzare")
    a = ap.parse_args()
    ctx = Path(a.context_file).read_text(encoding="utf-8", errors="replace") if a.context_file else ""
    b = build_dossier(a.topic, Path(a.out_dir), ctx, max_primary=a.max)
    print(json.dumps({k: b.get(k) for k in ("queries_executed", "total_articles", "analyzed", "usable", "dossier_path")},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
