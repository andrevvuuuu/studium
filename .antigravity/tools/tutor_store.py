#!/usr/bin/env python3
"""
tutor_store.py — Configurazione dei corsi e archivio delle lezioni del tutor.

L'archivio è un JSONL a sola aggiunta: una riga {"key", "lesson"} per ogni lezione letta e una riga
{"analyzed": key} quando agy l'ha analizzata. La chiave contiene l'hash del testo: se il professore
corregge il diario di una lezione, è una lezione nuova da rianalizzare.
"""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set

from diary_sources import Lesson


@dataclass
class Course:
    id: str
    nome: str
    moc: str
    start_year: int
    fonte: Dict[str, Any]
    orario: List[Dict[str, str]] = field(default_factory=list)
    esami: List[Dict[str, str]] = field(default_factory=list)


def load_courses(path: Path) -> List[Course]:
    return [Course(**c) for c in json.loads(path.read_text(encoding="utf-8"))]


def load_secrets(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def lesson_key(l: Lesson) -> str:
    return f"{l.course}|{l.date}|{hashlib.sha256(l.text.encode('utf-8')).hexdigest()[:12]}"


def read_events(store: Path) -> List[Dict[str, Any]]:
    try:
        lines = store.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def append_events(store: Path, events: List[Dict[str, Any]]) -> None:
    if not events:
        return
    store.parent.mkdir(parents=True, exist_ok=True)
    with store.open("a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def append_new(store: Path, lessons: List[Lesson]) -> List[Lesson]:
    known: Set[str] = {e["key"] for e in read_events(store) if "key" in e}
    added = []
    for l in lessons:
        key = lesson_key(l)
        if key not in known:
            known.add(key)
            added.append(l)
    append_events(store, [{"key": lesson_key(l), "lesson": asdict(l)} for l in added])
    return added


def pending(store: Path, course: str, include_analyzed: bool = False) -> List[Lesson]:
    """Le lezioni ancora da analizzare; con include_analyzed tutte (per rifare l'analisi con un metodo nuovo), una per
    data con il testo più recente."""
    events = read_events(store)
    if include_analyzed:
        latest = {e["lesson"]["date"]: Lesson(**e["lesson"]) for e in events if "key" in e and e["lesson"]["course"] == course}
        return [latest[d] for d in sorted(latest)]
    analyzed = {e["analyzed"] for e in events if "analyzed" in e}
    out = []
    for e in events:
        if "key" in e and e["key"] not in analyzed and e["lesson"]["course"] == course:
            out.append(Lesson(**e["lesson"]))
    return out


def mark_analyzed(store: Path, keys: List[str]) -> None:
    append_events(store, [{"analyzed": k} for k in keys])
