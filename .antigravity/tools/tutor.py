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


# ------------------------------------------------------------------------------
# Esecuzione giornaliera
# ------------------------------------------------------------------------------

TUTOR_DIR = VAULT / ".antigravity" / "tutor"
STORE = TUTOR_DIR / "lessons.jsonl"
STATE = TUTOR_DIR / "state.json"
LOCK = TUTOR_DIR / "tutor.lock"
WEEKDAYS = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]
RECUPERO_DAYS = 7


def should_run(state: Dict[str, Any], today: str, force: bool) -> bool:
    return force or state.get("last_run_day") != today


def acquire_lock(path: Path) -> bool:
    """Un'esecuzione alla volta (Obsidian aperto due volte); il lock di un processo morto non blocca."""
    try:
        pid = int(path.read_text().strip())
        os.kill(pid, 0)
        return False
    except (OSError, ValueError):
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(os.getpid()))
    return True


def release_lock(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


def next_lesson(orario: List[Dict[str, str]], today: str) -> Optional[Dict[str, str]]:
    from datetime import date, timedelta
    if not orario:
        return None
    d = date.fromisoformat(today)
    for offset in range(1, 8):
        day = d + timedelta(days=offset)
        slots = sorted(s["ora"] for s in orario if s.get("giorno") == WEEKDAYS[day.weekday()])
        if slots:
            return {"data": day.isoformat(), "ora": slots[0]}
    return None


def build_state(courses: List[Course], analyses: Dict[str, List[Dict[str, Any]]], forecasts: Dict[str, List[Lesson]],
                exams: Dict[str, List[Dict[str, str]]], errors: Dict[str, str], today: str, previous: Dict[str, Any]) -> Dict[str, Any]:
    from datetime import date, timedelta
    prev = {c.get("id"): c for c in previous.get("courses") or []}
    cutoff = (date.fromisoformat(today) - timedelta(days=RECUPERO_DAYS)).isoformat()
    out, recupero = [], False
    for c in courses:
        lessons = {l["date"]: l for l in (prev.get(c.id) or {}).get("lessons") or []}
        for l in analyses.get(c.id) or []:
            lessons[l["date"]] = l
        ordered = [lessons[d] for d in sorted(lessons)]
        if any(it.get("status") == "da_creare" for l in ordered if l["date"] < cutoff for it in l["items"]):
            recupero = True
        seen, all_exams = set(), []
        for e in c.esami + (exams.get(c.id) or []):
            key = (e["nome"], e["data"])
            if key not in seen and e["data"] >= today:
                seen.add(key)
                all_exams.append(e)
        entry = {
            "id": c.id, "nome": c.nome, "lessons": ordered,
            "previsione": [l.text for l in (forecasts.get(c.id) or [])[:5]],
            "esami": sorted(all_exams, key=lambda e: e["data"]),
            "prossima_lezione": next_lesson(c.orario, today),
        }
        if c.id in errors:
            entry["errore"] = errors[c.id]
        out.append(entry)
    return {"updated_at": today, "last_run_day": today, "courses": out, "recupero": recupero}


def write_state(path: Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def read_course(course: Course):
    """(lezioni fatte, previsione, esami) dalla fonte del corso; solleva DiaryFormatError o OSError."""
    from diary_sources import DiaryFormatError, read_malvenuto
    tipo = course.fonte.get("tipo")
    if tipo == "malvenuto_site":
        return read_malvenuto(course.fonte["url"], course.id, course.start_year)
    if tipo == "gmail_forum":
        from tutor_store import load_secrets
        secrets = load_secrets(TUTOR_DIR / "secrets.json")
        if not secrets.get("gmail_url"):
            raise DiaryFormatError("script Google non ancora configurato")
        from diary_sources import read_gmail_forum
        return read_gmail_forum(secrets, course.id, course.start_year), [], []
    raise DiaryFormatError(f"fonte sconosciuta: {tipo}")


def run(force: bool = False) -> int:
    from datetime import date
    from tutor_store import append_new, lesson_key, load_courses, mark_analyzed, pending
    today = date.today().isoformat()
    try:
        previous = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    if not should_run(previous, today, force) or not acquire_lock(LOCK):
        return 0
    try:
        courses = load_courses(TUTOR_DIR / "courses.json")
        analyses, forecasts, exams, errors = {}, {}, {}, {}
        for c in courses:
            try:
                done, forecasts[c.id], exams[c.id] = read_course(c)
                append_new(STORE, done)
            except Exception as e:  # una fonte giù non ferma le altre
                errors[c.id] = str(e)
            todo = pending(STORE, c.id)
            if not todo:
                continue
            result = analyze(c, todo, VAULT)
            if result is None:
                errors[c.id] = "agy non ha risposto: riprovo domani"
                continue
            analyses[c.id] = result
            mark_analyzed(STORE, [lesson_key(l) for l in todo])
        write_state(STATE, build_state(courses, analyses, forecasts, exams, errors, today, previous))
        return 0
    finally:
        release_lock(LOCK)


# ------------------------------------------------------------------------------
# Pulsanti della barra: config per la pipeline esistente (moc_batch, modalità modifica)
# ------------------------------------------------------------------------------

LIST_ITEM_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s")


def insert_after_in_moc(moc_text: str, title: str, after: Optional[str]) -> str:
    """Aggiunge [[title]] come voce di elenco subito dopo quella di [[after]] (stesso rientro e marcatore);
    senza ancora, dopo l'ultima voce di elenco del MOC. Se il link c'è già, il MOC non cambia."""
    if f"[[{title}]]" in moc_text or f"[[{title}|" in moc_text:
        return moc_text
    lines = moc_text.split("\n")
    target = None
    if after:
        for i, line in enumerate(lines):
            if (f"[[{after}]]" in line or f"[[{after}|" in line) and LIST_ITEM_RE.match(line):
                target = i
                break
    if target is None:
        items = [i for i, line in enumerate(lines) if LIST_ITEM_RE.match(line)]
        if not items:
            return moc_text.rstrip("\n") + f"\n- [[{title}]]\n"
        target = items[-1]
    m = LIST_ITEM_RE.match(lines[target])
    indent, marker = m.group(1), m.group(2)
    if marker[0].isdigit():
        marker = "-"
    lines.insert(target + 1, f"{indent}{marker} [[{title}]]")
    return "\n".join(lines)


def lesson_items(state: Dict[str, Any], course_id: str, date: str) -> List[Dict[str, Any]]:
    for c in state.get("courses") or []:
        if c.get("id") == course_id:
            for l in c.get("lessons") or []:
                if l.get("date") == date:
                    return l.get("items") or []
    return []


def lesson_batch_notes(state: Dict[str, Any], course_id: str, date: str, diary: str) -> List[Dict[str, Any]]:
    return [{"title": it["title"], "after": it.get("after"), "diary": diary, "lessons": [date]}
            for it in lesson_items(state, course_id, date) if it.get("status") == "da_creare" and it.get("title")]


def edit_job(state: Dict[str, Any], course_id: str, date: str, note_title: str, diary: str, target_rel: str,
             base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Job di modifica chirurgica; `base` porta i campi di NotebookLM e disciplina (moc_batch.build_job)."""
    item = next((it for it in lesson_items(state, course_id, date) if it.get("note") == note_title), {})
    return {
        **(base or {}),
        "operation": "edit", "operation_type": "edit", "operation_label": "Modifica / Migliora Nota Esistente",
        "edit_mode": "surgical_prompt", "title": note_title, "topic": note_title,
        "target_file_path": target_rel, "target_file_abs": str(VAULT / target_rel),
        "user_instructions": f"Integra quanto fatto a lezione il {date}: {item.get('missing') or item.get('concept', '')}. "
                             f"Testo del diario del professore: {diary}",
        "lessons": [date], "status": "pending",
    }


def lesson_text(course_id: str, date: str) -> str:
    from tutor_store import read_events
    texts = [e["lesson"]["text"] for e in read_events(STORE) if "lesson" in e and e["lesson"]["course"] == course_id and e["lesson"]["date"] == date]
    return texts[-1] if texts else ""


def write_batch_config(course_id: str, date: str) -> Path:
    """Inserisce nel MOC le note da creare della lezione e scrive la config di moc_batch (stesso formato del menu)."""
    import moc_batch
    from tutor_store import load_courses
    course = next(c for c in load_courses(TUTOR_DIR / "courses.json") if c.id == course_id)
    state = json.loads(STATE.read_text(encoding="utf-8"))
    notes = lesson_batch_notes(state, course_id, date, lesson_text(course_id, date))
    if not notes:
        raise SystemExit("Nessuna nota da creare per questa lezione")
    moc_path = VAULT / course.moc
    text = moc_path.read_text(encoding="utf-8")
    for n in notes:
        text = insert_after_in_moc(text, n["title"], n.get("after"))
    moc_path.write_text(text, encoding="utf-8")
    plan = moc_batch.build_plan(VAULT, course.moc)
    if plan.get("error"):
        raise SystemExit(plan["error"])
    wanted = {n["title"].lower(): n for n in notes}
    cfg_notes = [dict(p, diary=wanted[p["title"].lower()]["diary"], lessons=wanted[p["title"].lower()]["lessons"])
                 for p in plan["notes"] if p["title"].lower() in wanted]
    cfg = {"moc": plan["moc"], "moc_name": plan["moc_name"], "discipline": plan["discipline"],
           "allow_base_knowledge": False, "parallel": 2, "notes": cfg_notes}
    out = moc_batch.RUNTIME_DIR / "tutor-batch-config.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def write_edit_config(course_id: str, date: str, note_title: str) -> Path:
    import moc_batch
    state = json.loads(STATE.read_text(encoding="utf-8"))
    path = note_files(VAULT).get(note_title.lower())
    if not path:
        raise SystemExit(f"Nota non trovata: {note_title}")
    from tutor_store import load_courses
    course = next(c for c in load_courses(TUTOR_DIR / "courses.json") if c.id == course_id)
    plan = moc_batch.build_plan(VAULT, course.moc)
    base = moc_batch.build_job({"discipline": plan["discipline"], "moc": course.moc},
                               {"title": note_title, "notebooks": plan["moc_notebooks"]}, VAULT) if plan.get("moc_notebooks") else {}
    job = edit_job(state, course_id, date, note_title, lesson_text(course_id, date), str(path.relative_to(VAULT)), base)
    out = moc_batch.RUNTIME_DIR / "current-job.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Tutor delle lezioni: diari, analisi con agy, stato per la barra.")
    ap.add_argument("--force", action="store_true", help="Esegui anche se oggi è già stato fatto")
    ap.add_argument("--measure", metavar="COURSE", help="Costo reale di una chiamata sull'ultima lezione del corso")
    ap.add_argument("--batch-config", nargs=2, metavar=("COURSE", "DATE"), help="Prepara la creazione delle note di una lezione")
    ap.add_argument("--edit-config", nargs=3, metavar=("COURSE", "DATE", "NOTE"), help="Prepara il completamento di una nota")
    args = ap.parse_args()
    if args.batch_config:
        print(write_batch_config(*args.batch_config))
        return 0
    if args.edit_config:
        print(write_edit_config(*args.edit_config))
        return 0
    if args.measure:
        measure(args.measure)
        return 0
    return run(force=args.force)


if __name__ == "__main__":
    sys.exit(main())
