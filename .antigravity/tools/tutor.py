#!/usr/bin/env python3
"""
tutor.py — Tutor delle lezioni del vault.

Legge i diari (diary_sources.py), tiene l'archivio delle lezioni (tutor_store.py) e, per ogni corso con
lezioni nuove, fa UNA chiamata agy che confronta le voci delle lezioni con le note del MOC: coperto, da
completare, da creare. Il risultato va in .antigravity/tutor/state.json, che la barra di Obsidian mostra.
Nessuna fonte NotebookLM nel prompt: solo il testo delle lezioni e l'elenco compatto delle note.
"""

import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from correctness_check import ask_agy  # noqa: E402
from diary_sources import Lesson  # noqa: E402
from moc_batch import extract_ordered_links  # noqa: E402
from tutor_store import Course  # noqa: E402

VAULT = Path(__file__).resolve().parents[2]
TUTOR_MODEL = "gemini-3.8-flash-low"
STATUSES = ("coperto", "da_completare", "da_creare")
KINDS = ("concetto", "teorema", "definizione")

ITEM = {
    "type": "object",
    "properties": {
        "concept": {"type": "string"},
        "kind": {"type": "string", "enum": list(KINDS)},
        "status": {"type": "string", "enum": list(STATUSES)},
        "note": {"type": "string"},
        "missing": {"type": "string"},
        "title": {"type": "string"},
        "after": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["concept", "kind", "status", "reason"],
}
ANALYZE_SCHEMA = {
    "type": "object",
    "properties": {
        "lessons": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"date": {"type": "string"}, "items": {"type": "array", "items": ITEM}},
                "required": ["date", "items"],
            },
        }
    },
    "required": ["lessons"],
}

PROMPT = """Sei il tutor di uno studente universitario del corso di {course}. Sotto ci sono il diario di alcune lezioni scritto dal professore e l'elenco delle note che lo studente ha già nel suo vault per questo corso, nell'ordine del programma.

Per ogni lezione elenca i concetti, le definizioni e i teoremi introdotti o dimostrati a lezione. Ignora esercitazioni, esercizi svolti, prove in itinere, avvisi organizzativi e materiale bibliografico.
Per ogni voce indica:
- "status": "coperto" se una nota esistente (titolo, alias o sezione) la tratta; "da_completare" se la nota esiste ma manca qualcosa che il diario dice fatto a lezione (per esempio una dimostrazione), da scrivere in "missing"; "da_creare" se nessuna nota la tratta;
- "note": il titolo ESATTO della nota esistente, copiato dall'elenco (per coperto e da_completare);
- "title": per da_creare, il titolo della nuova nota, nello stile dei titoli dell'elenco (una nota per concetto o teorema, nome standard in italiano);
- "after": per da_creare, il titolo della nota dell'elenco dopo cui va inserita nel programma;
- "reason": una frase breve in italiano che spiega la scelta allo studente.
Raggruppa nella stessa voce i concetti che starebbero nella stessa nota. Non inventare titoli di note esistenti.

=== LEZIONI ===
{lessons}
=== NOTE DEL CORSO (titolo · alias · sezioni) ===
{notes}
=== FINE ==="""


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return re.sub(r"\s+", " ", "".join(c for c in s if not unicodedata.combining(c))).strip().lower()


def read_frontmatter_aliases(text: str) -> List[str]:
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not m:
        return []
    block = re.search(r"(?ms)^aliases:\s*\n((?:\s+-.*\n?)+)", m.group(1) + "\n")
    return [re.sub(r"^\s+-\s*", "", l).strip().strip("\"'") for l in block.group(1).splitlines() if l.strip()] if block else []


def note_files(vault: Path) -> Dict[str, Path]:
    by_name: Dict[str, Path] = {}
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.lower().endswith(".md"):
                by_name.setdefault(f[:-3].lower(), Path(root) / f)
    return by_name


def moc_notes(vault: Path, moc_rel: str) -> List[Dict[str, Any]]:
    """Note collegate dal MOC, nell'ordine del MOC, con alias e titoli delle sezioni."""
    files = note_files(vault)
    out = []
    for title in extract_ordered_links((vault / moc_rel).read_text(encoding="utf-8", errors="replace")):
        path = files.get(title.lower())
        if not path:
            out.append({"title": title, "aliases": [], "headings": [], "exists": False})
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        headings = [re.sub(r"^#+\s*", "", l).strip() for l in text.splitlines() if re.match(r"^#{2,4}\s", l)]
        out.append({"title": title, "aliases": read_frontmatter_aliases(text), "headings": headings, "exists": True})
    return out


def build_prompt(course: Course, lessons: List[Lesson], notes: List[Dict[str, Any]]) -> str:
    lesson_lines = "\n".join(f"[{l.date}] {l.text}" for l in lessons)
    note_lines = "\n".join(" · ".join([n["title"]] + n["aliases"] + n["headings"]) for n in notes if n["exists"])
    return PROMPT.replace("{course}", course.nome).replace("{lessons}", lesson_lines).replace("{notes}", note_lines or "(nessuna)")


def validate(raw: Dict[str, Any], notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Corregge ciò che agy non può sapere con certezza: le note esistenti sono solo quelle dell'elenco."""
    existing: Dict[str, str] = {}
    for n in notes:
        if n["exists"]:
            for name in [n["title"]] + n["aliases"]:
                existing.setdefault(norm(name), n["title"])
    out = []
    for lesson in raw.get("lessons") or []:
        if not isinstance(lesson, dict) or not lesson.get("date"):
            continue
        items = []
        for it in lesson.get("items") or []:
            if not isinstance(it, dict) or not str(it.get("reason", "")).strip() or it.get("status") not in STATUSES:
                continue
            item = {k: str(v).strip() for k, v in it.items() if isinstance(v, str) and str(v).strip()}
            if item["status"] in ("coperto", "da_completare"):
                real = existing.get(norm(item.get("note", "")))
                if not real:
                    item["status"] = "da_creare"
                    item["title"] = item.get("title") or item.get("note") or item.get("concept", "")
                    item.pop("note", None)
                else:
                    item["note"] = real
            if item["status"] == "da_creare":
                real = existing.get(norm(item.get("title", ""))) or existing.get(norm(item.get("concept", "")))
                if real:
                    item["status"] = "coperto"
                    item["note"] = real
                    item.pop("title", None)
                elif not item.get("title"):
                    item["title"] = item.get("concept", "")
            items.append(item)
        out.append({"date": lesson["date"], "items": items})
    return out


def analyze(course: Course, lessons: List[Lesson], vault: Path, ask: Callable[..., Optional[Dict[str, Any]]] = ask_agy) -> Optional[List[Dict[str, Any]]]:
    notes = moc_notes(vault, course.moc)
    raw = ask(build_prompt(course, lessons, notes), ANALYZE_SCHEMA, model=TUTOR_MODEL)
    if raw is None:
        return None
    return validate(raw, notes)


def measure(course_id: str) -> None:
    """Costo reale di una chiamata (ultima lezione del corso): token in ingresso, cache, durata."""
    import shutil
    import subprocess
    from diary_sources import read_malvenuto
    from tutor_store import load_courses
    course = next(c for c in load_courses(VAULT / ".antigravity" / "tutor" / "courses.json") if c.id == course_id)
    done, _, _ = read_malvenuto(course.fonte["url"], course.id, course.start_year)
    prompt = build_prompt(course, done[-1:], moc_notes(VAULT, course.moc))
    agy = shutil.which("agy") or str(Path.home() / ".local/bin/agy")
    proc = subprocess.run([agy, "-p", prompt + "\n\nLavora solo sul testo di questo messaggio: non leggere file e non usare strumenti.",
                           "--output-format", "json", "--json-schema", json.dumps(ANALYZE_SCHEMA), "--print-timeout", "300s",
                           "--model", TUTOR_MODEL], capture_output=True, text=True, timeout=360, start_new_session=True, cwd="/tmp")
    data = json.loads(proc.stdout)
    if data.get("status") != "SUCCESS" or not (data.get("structured_output") or data.get("response")):
        print(proc.stdout[-800:], proc.stderr[-400:])
    u = data.get("usage") or {}
    print(f"prompt {len(prompt)} caratteri · input {u.get('input_tokens')} · output {u.get('output_tokens')} · "
          f"thinking {u.get('thinking_tokens')} · cache {u.get('cache_read_tokens')} · {data.get('duration_seconds', 0):.0f} s")
    print(json.dumps(data.get("structured_output") or data.get("response"), ensure_ascii=False)[:1500])


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--measure":
    measure(sys.argv[2])
