#!/usr/bin/env python3
"""
moc_postprocess.py — Controlli sul MOC appena scritto (chiamato da orchestrator.post_process_job).

1. Titoli: un concetto = una nota. I wikilink quasi uguali (nello stesso MOC o rispetto alle note
   esistenti e ai titoli pianificati negli altri MOC della disciplina) vengono giudicati da un
   revisore agy; quelli che indicano lo stesso argomento vengono riscritti con un unico titolo,
   preferendo sempre quello già esistente o già pianificato altrove.
2. Accenti: parole italiane senza accento nei titoli dei wikilink (Unicita -> Unicità), salvo
   quando il titolo senza accento è già una nota esistente o un titolo di un altro MOC.
3. Esclusività (solo "Solo NotebookLM"): ogni argomento collegato nei moduli viene chiesto a
   NotebookLM; quelli che nessun notebook tratta perdono le doppie quadre (non diventano note)
   e vengono elencati in fondo al MOC.
"""

import json
import re
import sys
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orchestrator import (  # noqa: E402
    RUNTIME_DIR,
    extract_notebooks_list,
    query_nlm_parallel,
    run_agy_structured,
    update_status,
)
import vault_layout  # noqa: E402

WIKILINK = re.compile(r"(?<!!)\[\[([^\[\]|#]+)((?:#[^\[\]|]*)?)((?:\|[^\[\]]*)?)\]\]")
STOPWORDS = {"di", "del", "della", "dei", "degli", "delle", "dello", "e", "ed", "il", "lo", "la", "le", "i", "gli",
             "un", "una", "uno", "per", "in", "su", "sul", "sulla", "sui", "nei", "nelle", "nel", "nella", "a", "al",
             "alla", "ai", "con", "tra", "fra", "da", "dal", "dalla", "d", "l", "sull", "dell", "all", "nell"}
ACCENT_WORDS = {
    "perche": "perché", "piu": "più", "cioe": "cioè", "poiche": "poiché", "affinche": "affinché", "finche": "finché",
    "unicita": "unicità", "proprieta": "proprietà", "identita": "identità", "densita": "densità", "parita": "parità",
    "verita": "verità", "totalita": "totalità", "quantita": "quantità", "velocita": "velocità", "unita": "unità",
}
# Suffissi che in italiano sono sempre accentati: -bilità, -alità, -icità, -ività, -osità, -inuità, -essità, -ezzità
ACCENT_SUFFIX = re.compile(r"\b(\w+(?:bil|al|ic|iv|os|inu|ess|ar|ol|ur|ent|itt)ita)\b", re.IGNORECASE)

MERGE_SCHEMA = {
    "type": "object",
    "properties": {
        "same": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "keep": {"type": "string"}},
                "required": ["id", "keep"],
            },
        }
    },
    "required": ["same"],
}


def strip_accents(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")


def norm_tokens(title: str) -> List[str]:
    t = re.sub(r"[^\w\s]", " ", strip_accents(title).lower())
    return [w for w in t.split() if w not in STOPWORDS]


def moc_links(text: str) -> List[str]:
    return list(dict.fromkeys(m.group(1).strip() for m in WIKILINK.finditer(text)))


def replace_link_target(text: str, old: str, new: Optional[str]) -> str:
    """Riscrive i wikilink verso `old`: verso `new`, oppure (new=None) li trasforma in testo semplice."""
    def repl(m: re.Match) -> str:
        if m.group(1).strip() != old:
            return m.group(0)
        if new is None:
            alias = m.group(3)[1:] if m.group(3) else ""
            section = m.group(2)[1:] if m.group(2) else ""
            return alias or section or old
        return f"[[{new}{m.group(2)}{m.group(3)}]]"
    return WIKILINK.sub(repl, text)


# ------------------------------------------------------------------------------
# 1. Titoli duplicati o diversi dagli altri MOC
# ------------------------------------------------------------------------------

def reference_titles(vault_root: Path, discipline: str, moc_rel: str) -> Set[str]:
    titles: Set[str] = set()
    for c in vault_layout.load_courses(vault_root):
        if c.moc_rel != moc_rel and (not discipline or c.discipline == discipline):
            titles.update(c.note_titles)
    disc_dir = vault_root / discipline if discipline else None
    if disc_dir and disc_dir.is_dir():
        titles.update(p.stem for p in disc_dir.rglob("*.md") if not p.stem.endswith(" MOC"))
    return titles


def similar(a: str, b: str) -> bool:
    ta, tb = set(norm_tokens(a)), set(norm_tokens(b))
    if not ta or not tb:
        return False
    if ta == tb:
        return True
    jac = len(ta & tb) / len(ta | tb)
    small, big = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    subset = small <= big and len(small) >= 2 and len(big) - len(small) <= 2
    return (jac >= 0.6 and SequenceMatcher(None, " ".join(sorted(ta)), " ".join(sorted(tb))).ratio() >= 0.75) or subset


def reconcile_titles(text: str, refs: Set[str]) -> Tuple[str, List[Dict[str, str]]]:
    links = [l for l in moc_links(text) if not l.endswith(" MOC")]
    merges: List[Dict[str, str]] = []
    ref_by_norm = {" ".join(norm_tokens(r)): r for r in refs}
    # Stessi termini (cambiano solo accenti, maiuscole, articoli): unificazione diretta sul titolo di riferimento
    for l in links:
        key = " ".join(norm_tokens(l))
        if key in ref_by_norm and ref_by_norm[key] != l:
            merges.append({"from": l, "to": ref_by_norm[key], "why": "stesso titolo a meno di accenti o articoli"})
    for m in merges:
        text = replace_link_target(text, m["from"], m["to"])
    links = [l for l in moc_links(text) if not l.endswith(" MOC")]

    pairs: List[Tuple[str, str, bool]] = []  # (titolo del MOC, altro titolo, altro è di riferimento)
    for i, a in enumerate(links):
        for b in links[i + 1:]:
            if similar(a, b):
                pairs.append((a, b, False))
        for r in refs:
            if r not in links and similar(a, r):
                pairs.append((a, r, True))
    pairs = pairs[:120]
    if not pairs:
        return text, merges

    listing = "\n".join(f"P{i}: A = «{a}» | B = «{b}»" + (" (B è già una nota o un titolo di un altro MOC)" if ref else "")
                        for i, (a, b, ref) in enumerate(pairs, 1))
    prompt = (
        "Sei un revisore di un vault di appunti universitari. Per ciascuna coppia di titoli di note decidi se indicano "
        "lo STESSO argomento (e quindi devono essere una sola nota) oppure argomenti diversi.\n"
        "Sono DIVERSI i titoli che distinguono casi, oggetti o versioni differenti (es. 'Teorema di Unicità del Limite "
        "per Successioni' e '... per Funzioni', 'Resto di Taylor in Forma di Peano' e '... di Lagrange', "
        "'Primitive Elementari' e 'Primitive Non Elementari', 'Secondo' e 'Terzo Teorema di Isomorfismo').\n"
        "Sono lo STESSO argomento i titoli che differiscono solo per formulazione (es. 'Studio del Grafico di una "
        "Funzione' e 'Studio Completo del Grafico di una Funzione').\n"
        "Restituisci in `same` solo le coppie che sono lo stesso argomento, con `keep` = 'A' o 'B' (il titolo da tenere: "
        "se B è già una nota o un titolo di un altro MOC tieni sempre B; altrimenti il più chiaro e canonico, preferendo "
        "quello con il prefisso di tipo 'Teorema ...', 'Metodo ...', 'Criterio ...' quando l'argomento è un teorema o un metodo).\n\n"
        + listing
    )
    result = run_agy_structured(prompt, MERGE_SCHEMA, timeout_sec=420, effort="low") or {"same": []}
    for item in result.get("same") or []:
        m = re.match(r"P(\d+)$", str(item.get("id", "")).strip())
        if not m or not (1 <= int(m.group(1)) <= len(pairs)):
            continue
        a, b, ref = pairs[int(m.group(1)) - 1]
        keep_b = ref or str(item.get("keep", "")).strip().upper() == "B"
        old, new = (a, b) if keep_b else (b, a)
        if old == new or old not in moc_links(text):
            continue
        text = replace_link_target(text, old, new)
        merges.append({"from": old, "to": new, "why": "stesso argomento (revisore)"})
    return text, merges


# ------------------------------------------------------------------------------
# 2. Accenti
# ------------------------------------------------------------------------------

def accent_title(title: str) -> str:
    def fix_word(w: str) -> str:
        low = w.lower()
        if low in ACCENT_WORDS:
            fixed = ACCENT_WORDS[low]
        elif ACCENT_SUFFIX.fullmatch(w):
            fixed = low[:-1] + "à"
        else:
            return w
        return fixed[0].upper() + fixed[1:] if w[0].isupper() else fixed
    return re.sub(r"\b\w+\b", lambda m: fix_word(m.group(0)), title)


def fix_accents(text: str, refs: Set[str]) -> Tuple[str, List[Dict[str, str]]]:
    changes = []
    for l in moc_links(text):
        if l in refs:
            continue  # titolo già usato altrove così com'è: cambiarlo romperebbe il collegamento
        fixed = accent_title(l)
        if fixed != l:
            text = replace_link_target(text, l, fixed)
            changes.append({"from": l, "to": fixed})

    # Anche i nomi delle sezioni [[Nota#Sezione]]: la nota verrà scritta con questi titoli di paragrafo
    def fix_section(m: re.Match) -> str:
        if not m.group(2):
            return m.group(0)
        fixed = "#" + accent_title(m.group(2)[1:])
        if fixed == m.group(2):
            return m.group(0)
        changes.append({"from": m.group(1) + m.group(2), "to": m.group(1) + fixed})
        return f"[[{m.group(1)}{fixed}{m.group(3)}]]"
    text = WIKILINK.sub(fix_section, text)
    return text, changes


# ------------------------------------------------------------------------------
# 3. Esclusività degli argomenti (Solo NotebookLM)
# ------------------------------------------------------------------------------

def topics_supported(topics: List[str], notebooks: List[Dict[str, str]], vault_root: Path, target_rel: str,
                     chunk: int = 12) -> Dict[str, Optional[bool]]:
    """True se almeno un notebook tratta l'argomento, False se tutti lo negano, None se senza risposta."""
    verdict: Dict[str, Optional[bool]] = {t: None for t in topics}
    ids = {f"T{i}": t for i, t in enumerate(topics, 1)}
    pattern = re.compile(r"\b(T\d+)\b[\s*`]*[|:\-–]\s*[*`]*\s*(S[IÌÍ]|NO)\b", re.IGNORECASE)

    def ask(id_list: List[str], size: int) -> None:
        tasks = []
        for c_idx in range(0, len(id_list), size):
            group = id_list[c_idx:c_idx + size]
            listing = "\n".join(f"{i}: {ids[i]}" for i in group)
            prompt = (
                "Per ciascun argomento indica se le fonti di questo notebook lo trattano esplicitamente "
                "(definizione, enunciato, spiegazione o esercizi). Rispondi su una riga per argomento nel formato "
                "esatto `ID | SI` oppure `ID | NO`. Non aggiungere altro.\n\n" + listing
            )
            for nb_idx, nb in enumerate(notebooks):
                tasks.append(((c_idx, nb_idx), nb["id"], prompt))

        def progress(done: int, total: int) -> None:
            update_status(
                vault_root=vault_root, percent=97, step_number=6, total_steps=6,
                message=f"🛡️ Verifica del MOC: NotebookLM controlla {len(topics)} argomenti",
                detail=f"{done} di {total} gruppi verificati", status="running", target_file=target_rel,
                phase="verify", progress={"done": done, "total": total, "unit": "gruppi"},
            )
        for text in query_nlm_parallel(tasks, timeout_sec=300, on_progress=progress).values():
            for tid, ans in pattern.findall(text or ""):
                t = ids.get(tid.upper())
                if t is None:
                    continue
                if ans.upper().startswith("S"):
                    verdict[t] = True
                elif verdict[t] is None:
                    verdict[t] = False

    ask(list(ids), chunk)
    pending = [i for i, t in ids.items() if verdict[t] is None]
    if pending:
        ask(pending, max(4, chunk // 2))
    return verdict


def drop_unsupported(text: str, removed: List[str]) -> str:
    for t in removed:
        text = replace_link_target(text, t, None)
    if removed:
        block = ["", "> [!warning]- Argomenti tolti dal MOC perché assenti dalle fonti NotebookLM",
                 "> Questi argomenti erano collegati ma nessun notebook del corso li tratta: non verranno create note.",
                 ">"] + [f"> - {t}" for t in removed]
        text = text.rstrip() + "\n" + "\n".join(block) + "\n"
    return text


# ------------------------------------------------------------------------------

def postprocess_moc(vault_root: Path, job_data: Dict[str, Any], target_rel: str) -> Dict[str, Any]:
    path = vault_root / target_rel
    report: Dict[str, Any] = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "target": target_rel, "type": "moc"}
    if not path.exists():
        report["error"] = "MOC non trovato"
        return report
    text = path.read_text(encoding="utf-8", errors="replace")
    original = text
    discipline = job_data.get("discipline", "")

    update_status(
        vault_root=vault_root, percent=96, step_number=6, total_steps=6,
        message="🔁 Verifica del MOC: titoli doppi e titoli condivisi con gli altri MOC",
        detail="Un concetto, una sola nota", status="running", target_file=target_rel, phase="verify",
    )
    refs = reference_titles(vault_root, discipline, target_rel)
    text, report["merged"] = reconcile_titles(text, refs)
    text, report["accents"] = fix_accents(text, refs)

    strict = job_data.get("moc_mode") == "start_notebooklm" and not job_data.get("allow_base_knowledge")
    report["removed"] = []
    if strict:
        notebooks = extract_notebooks_list(job_data.get("source", {}), job_data)
        path.write_text(text, encoding="utf-8")
        course = vault_layout.Course(vault_root, target_rel)
        topics = [t for t in course.note_titles if course.module_index.get(t.lower())]
        if not topics:  # MOC piccolo senza moduli: si verificano tutti i link
            topics = [t for t in course.note_titles]
        disc_dir = vault_root / discipline if discipline else None
        existing = {p.stem for p in disc_dir.rglob("*.md")} if disc_dir and disc_dir.is_dir() else set()
        topics = [t for t in topics if t not in existing]  # le note già create hanno avuto la loro verifica
        report["checked"] = len(topics)
        if topics and notebooks:
            verdict = topics_supported(topics, notebooks, vault_root, target_rel)
            report["removed"] = [t for t, v in verdict.items() if v is False]
            report["unverified"] = [t for t, v in verdict.items() if v is None]
            text = drop_unsupported(text, report["removed"])

    if text != original:
        path.write_text(text, encoding="utf-8")
    try:
        with open(vault_root / ".antigravity" / "grounding-log.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(report, ensure_ascii=False) + "\n")
    except Exception:
        pass
    (RUNTIME_DIR / "moc-check-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    parts = []
    if report["merged"]:
        parts.append(f"{len(report['merged'])} titoli unificati")
    if report["accents"]:
        parts.append(f"{len(report['accents'])} accenti corretti")
    if strict:
        parts.append(f"{len(report['removed'])} argomenti tolti perché assenti dalle fonti")
    report["summary"] = "🛡️ MOC verificato: " + (", ".join(parts) if parts else "nessuna correzione necessaria")
    return report
