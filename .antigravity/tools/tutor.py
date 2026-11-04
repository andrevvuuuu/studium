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
ANALYZE_CHUNK = 4
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

DOVE VA IL CONTENUTO (prima di ogni "da_completare"):
- se una sezione della nota, o di un'altra nota dell'elenco, tratta già quel contenuto (anche con un altro nome), la voce è "coperto";
- accanto ai titoli delle sezioni, "[con dimostrazione]" vuol dire che la sezione contiene una dimostrazione e "[senza dimostrazione]" che ha l'enunciato ma la dimostrazione manca. Se il diario dice che a lezione un risultato è stato dimostrato, è "coperto" solo se una sezione su quel risultato è segnata "[con dimostrazione]"; altrimenti è "da_completare" con "missing" = quella dimostrazione;
- "da_completare" solo se il contenuto mancante appartiene all'argomento centrale della nota: la sua definizione, il suo enunciato, la sua dimostrazione, una sua proprietà diretta;
- se invece è un risultato, un algoritmo o un procedimento con un nome proprio che ha già una nota sua nell'elenco, o tra quelle previste, la voce va su quella nota (coperto o da_completare se esiste, da_creare con quel titolo se è prevista). Una nota generale che lo cita in poche righe non è la sua nota.

=== LEZIONI ===
{lessons}
=== NOTE DEL CORSO (titolo · alias · sezioni) ===
{notes}
=== NOTE PREVISTE DAL PROGRAMMA, NON ANCORA SCRITTE (per "title" usa uno di questi titoli se è adatto) ===
{planned}
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


# Sezioni che ci sono in ogni nota o che non dicono quali concetti copre: nel prompt costano token e basta
BOILERPLATE_HEADING = re.compile(r"note e paragrafi collegati|teoremi e concetti derivati|riferimenti puntuali|note generali e moc|"
                                 r"esercizi|quiz|flashcard", re.I)


NO_PROOF = re.compile(r"dimostrazione non presente", re.I)
PROOF = re.compile(r"^>\s*\[![a-z]+\][-+]?\s*Dimostrazion", re.I)


def note_headings(text: str) -> List[str]:
    """Titoli ## e ### della nota. Il tutor vede solo questi, quindi accanto al titolo si segna se la sezione contiene
    una dimostrazione (il riquadro "> [!tip]- Dimostrazione" delle note) o il segno "Dimostrazione non presente"
    (lo scrive la pipeline quando le fonti non la danno): dal solo titolo non si capisce."""
    headings: List[str] = []
    flags: List[List[str]] = []
    last: Optional[int] = None
    for line in text.splitlines():
        m = re.match(r"^(#+)\s+(.*)", line)
        if m and len(m.group(1)) in (2, 3):
            if BOILERPLATE_HEADING.search(line):
                last = None
            else:
                headings.append(m.group(2).strip())
                flags.append([])
                last = len(headings) - 1
            continue
        if m or last is None:
            continue
        flag = "con dimostrazione" if PROOF.search(line) else "senza dimostrazione" if NO_PROOF.search(line) else None
        if flag and flag not in flags[last]:
            flags[last].append(flag)
    return [h + "".join(f" [{f}]" for f in fl) for h, fl in zip(headings, flags)]


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
        out.append({"title": title, "aliases": read_frontmatter_aliases(text), "headings": note_headings(text), "exists": True})
    return out


def build_prompt(course: Course, lessons: List[Lesson], notes: List[Dict[str, Any]]) -> str:
    lesson_lines = "\n".join(f"[{l.date}] {l.text}" for l in lessons)
    note_lines = "\n".join(" · ".join([n["title"]] + n["aliases"] + n["headings"]) for n in notes if n["exists"])
    planned = "\n".join(n["title"] for n in notes if not n["exists"])
    return (PROMPT.replace("{course}", course.nome).replace("{lessons}", lesson_lines).replace("{notes}", note_lines or "(nessuna)")
            .replace("{planned}", planned or "(nessuna)"))


TITLE_FILLERS = {"teorema", "teoremi", "formula", "principio", "il", "lo", "la", "i", "gli", "le", "l", "di", "d", "del", "dello",
                 "della", "dei", "degli", "delle", "e", "ed", "a", "al", "sul", "sulla", "sui", "sulle", "per", "in", "nel", "nella",
                 "con", "tra", "fra", "un", "una"}


def title_core(title: str) -> frozenset:
    """Le parole che contano di un titolo, in qualsiasi ordine: "Binomio di Newton" e "Teorema del Binomio di Newton"
    sono la stessa nota. Con meno di due parole il confronto non è affidabile e non si fa."""
    words = frozenset(w for w in re.split(r"[^0-9a-z]+", norm(title)) if w and w not in TITLE_FILLERS)
    return words if len(words) >= 2 else frozenset()


def validate(raw: Any, notes: List[Dict[str, Any]], dates: Optional[set] = None,
             vault_titles: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """Corregge ciò che agy non può sapere con certezza: esiste solo ciò che c'è davvero nel vault (anche fuori da
    questo MOC), i titoli previsti dal programma si usano con la grafia del MOC, e valgono solo le date chieste."""
    existing: Dict[str, str] = {norm(k): v for k, v in (vault_titles or {}).items()}
    planned: Dict[str, str] = {}
    for n in notes:
        if n["exists"]:
            for name in [n["title"]] + n["aliases"]:
                existing[norm(name)] = n["title"]
        else:
            planned.setdefault(norm(n["title"]), n["title"])
    existing_core = {title_core(k): v for k, v in existing.items() if title_core(k)}
    planned_core = {title_core(v): v for v in planned.values() if title_core(v)}
    if not isinstance(raw, dict):
        return []
    out = []
    for lesson in raw.get("lessons") or []:
        if not isinstance(lesson, dict) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(lesson.get("date", ""))):
            continue
        if dates is not None and lesson["date"] not in dates:
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
                real = (existing.get(norm(item.get("title", ""))) or existing.get(norm(item.get("concept", "")))
                        or existing_core.get(title_core(item.get("title", ""))))
                if real:
                    item["status"] = "coperto"
                    item["note"] = real
                    item.pop("title", None)
                else:
                    item["title"] = (planned.get(norm(item.get("title", ""))) or planned_core.get(title_core(item.get("title", "")))
                                     or item.get("title") or item.get("concept", ""))
            # Una voce per nota: agy a volte divide in più voci i pezzi della stessa nota da creare o completare
            target = (item["status"], norm(item.get("title") or item.get("note", ""))) if item["status"] != "coperto" else None
            twin = next((x for x in items if target and (x["status"], norm(x.get("title") or x.get("note", ""))) == target), None)
            if twin:
                for k in ("concept", "missing"):
                    if item.get(k) and item[k] not in twin.get(k, ""):
                        twin[k] = f"{twin[k]}; {item[k]}" if twin.get(k) else item[k]
                continue
            items.append(item)
        out.append({"date": lesson["date"], "items": items})
    return out


def analyze(course: Course, lessons: List[Lesson], vault: Path, ask: Callable[..., Optional[Dict[str, Any]]] = ask_agy) -> Optional[List[Dict[str, Any]]]:
    """Poche lezioni per chiamata: con risposte lunghe (15 lezioni insieme) agy si blocca fino al timeout. Il prompt
    ripete l'elenco delle note, ma quella parte agy la legge dalla cache. Una chiamata fallita perde solo le sue lezioni."""
    notes = moc_notes(vault, course.moc)
    vault_titles = {p.stem: p.stem for p in note_files(vault).values()}
    out: List[Dict[str, Any]] = []
    answered = False
    for i in range(0, len(lessons), ANALYZE_CHUNK):
        chunk = lessons[i:i + ANALYZE_CHUNK]
        raw = ask(build_prompt(course, chunk, notes), ANALYZE_SCHEMA, model=TUTOR_MODEL, timeout_sec=90)
        if raw is None:
            continue
        answered = True
        got = validate(raw, notes, dates={l.date for l in chunk}, vault_titles=vault_titles)
        out += got
        # I titoli nuovi diventano "previsti" per i gruppi dopo: un concetto ripreso in più lezioni ha un solo nome
        known = {n["title"].lower() for n in notes}
        for it in (it for l in got for it in l["items"] if it["status"] == "da_creare"):
            if it["title"].lower() not in known:
                known.add(it["title"].lower())
                notes = notes + [{"title": it["title"], "aliases": [], "headings": [], "exists": False}]
    return out if answered else None


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
    state = {"updated_at": today, "last_run_day": today, "courses": out}
    state["recupero"] = is_recupero(state, today)
    return state


def note_lessons(text: str) -> List[str]:
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    block = re.search(r"(?m)^Lezioni:[ \t]*\n((?:[ \t]+-.*\n?)*)", m.group(1) + "\n") if m else None
    return re.findall(r"-\s*['\"]?(\d{4}-\d{2}-\d{2})", block.group(1)) if block else []


def is_recupero(state: Dict[str, Any], today: str) -> bool:
    from datetime import date, timedelta
    cutoff = (date.fromisoformat(today) - timedelta(days=RECUPERO_DAYS)).isoformat()
    return any(it.get("status") == "da_creare" for c in state.get("courses") or [] for l in c.get("lessons") or []
               if l.get("date", "") < cutoff for it in l.get("items") or [])


def reconcile(state: Dict[str, Any], vault: Path, today: str) -> Dict[str, Any]:
    """Allinea lo stato ai file, senza AI: una nota creata è coperta, una nota completata (Lezioni con la data
    della lezione nel frontmatter) pure. Così la barra non ripropone ciò che è già fatto."""
    files = note_files(vault)
    for c in state.get("courses") or []:
        for l in c.get("lessons") or []:
            for it in l.get("items") or []:
                if it.get("status") == "da_creare":
                    path = files.get(norm(it.get("title", "")).lower()) or files.get((it.get("title") or "").lower())
                    if path:
                        it["status"], it["note"] = "coperto", path.stem
                elif it.get("status") == "da_completare":
                    path = files.get((it.get("note") or "").lower())
                    if path and l.get("date") in note_lessons(path.read_text(encoding="utf-8", errors="replace")):
                        it["status"] = "coperto"
    state["recupero"] = is_recupero(state, today)
    return state


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
        return read_gmail_forum(secrets, course.id, course.start_year, course.fonte.get("corso", "")), [], []
    raise DiaryFormatError(f"fonte sconosciuta: {tipo}")


def run(force: bool = False, only_reconcile: bool = False) -> int:
    """Una volta al giorno legge i diari e analizza le lezioni nuove; ogni volta allinea lo stato ai file (senza AI)."""
    from datetime import date
    from tutor_store import append_new, lesson_key, load_courses, mark_analyzed, pending
    today = date.today().isoformat()
    try:
        previous = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    if not acquire_lock(LOCK):
        return 0
    try:
        if only_reconcile or not should_run(previous, today, force):
            if previous.get("courses"):
                write_state(STATE, reconcile(previous, VAULT, today))
            return 0
        courses = load_courses(TUTOR_DIR / "courses.json")
        analyses, forecasts, exams, errors = {}, {}, {}, {}
        for c in courses:
            try:  # un corso che si rompe (fonte giù, MOC rinominato, risposta strana) non ferma gli altri
                try:
                    done, forecasts[c.id], exams[c.id] = read_course(c)
                    append_new(STORE, done)
                except Exception as e:
                    errors[c.id] = str(e)
                todo = pending(STORE, c.id)
                if not todo:
                    continue
                result = analyze(c, todo, VAULT)
                if result is None:
                    errors[c.id] = "agy non ha risposto: riprovo domani"
                    continue
                analyses[c.id] = result
                answered = {l["date"] for l in result}
                mark_analyzed(STORE, [lesson_key(l) for l in todo if l.date in answered])
            except Exception as e:
                errors[c.id] = f"analisi non riuscita: {e}"
        write_state(STATE, reconcile(build_state(courses, analyses, forecasts, exams, errors, today, previous), VAULT, today))
        return 0
    finally:
        release_lock(LOCK)


# ------------------------------------------------------------------------------
# Pulsanti della barra: config per la pipeline esistente (moc_batch, modalità modifica)
# ------------------------------------------------------------------------------

LIST_ITEM_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s")


def insert_after_in_moc(moc_text: str, title: str, after: Optional[str]) -> str:
    """Aggiunge [[title]] al MOC nel modulo della nota che la precede (le cartelle dei corsi seguono le sezioni
    "## " del MOC): subito dopo la voce di elenco di [[after]] e dei suoi sotto-punti, oppure, se il MOC lì è in
    prosa, come voce in fondo alla sua sezione. Senza ancora va in fondo all'ultima sezione che non sia di
    raccordo (quelle finali la pipeline le ignora). Se il link c'è già, anche con altre maiuscole, nulla cambia."""
    from vault_layout import RACCORDO_HEADINGS
    link_re = lambda name: re.compile(r"\[\[" + re.escape(name) + r"(?:[|#][^\]]*)?\]\]", re.I)
    if link_re(title).search(moc_text):
        return moc_text
    lines = moc_text.split("\n")
    in_code, code = False, []
    for line in lines:
        if line.lstrip().startswith("```"):
            in_code = not in_code
            code.append(True)
        else:
            code.append(in_code)
    headings = [i for i, l in enumerate(lines) if l.startswith("## ") and not code[i]]

    def section_end(i: int) -> int:
        nxt = [h for h in headings if h > i]
        return nxt[0] if nxt else len(lines)

    anchor = None
    if after:
        rx = link_re(after)
        anchor = next((i for i, l in enumerate(lines) if not code[i] and rx.search(l)), None)
    if anchor is not None and LIST_ITEM_RE.match(lines[anchor]):
        m = LIST_ITEM_RE.match(lines[anchor])
        indent, marker = m.group(1), m.group(2)
        if marker[0].isdigit():
            marker = "-"
        j = anchor + 1
        while j < len(lines) and lines[j].strip() and len(lines[j]) - len(lines[j].lstrip()) > len(indent):
            j += 1
        lines.insert(j, f"{indent}{marker} [[{title}]]")
        return "\n".join(lines)
    if anchor is not None:
        end = section_end(anchor)
    else:
        body = [h for h in headings if not RACCORDO_HEADINGS.search(lines[h])]
        first_raccordo = next((h for h in headings if RACCORDO_HEADINGS.search(lines[h])), None)
        if body:
            last = max(h for h in body if first_raccordo is None or h < first_raccordo) if any(first_raccordo is None or h < first_raccordo for h in body) else body[-1]
            end = section_end(last)
        else:
            end = first_raccordo if first_raccordo is not None else len(lines)
    k = end
    while k > 0 and not lines[k - 1].strip():
        k -= 1
    block = [f"- [[{title}]]"] if k > 0 and LIST_ITEM_RE.match(lines[k - 1]) else ["", f"- [[{title}]]"]
    lines[k:k] = block
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
    # target_file_path: se dalla barra si sceglie un'altra fonte, la nota diventa un job singolo nella stessa cartella
    cfg_notes = [dict(p, diary=wanted[p["title"].lower()]["diary"], lessons=wanted[p["title"].lower()]["lessons"],
                      target_file_path=moc_batch.resolve_note_path(VAULT, p["title"], plan["discipline"], course.moc))
                 for p in plan["notes"] if p["title"].lower() in wanted]
    cfg = {"moc": plan["moc"], "moc_name": plan["moc_name"], "discipline": plan["discipline"],
           "allow_base_knowledge": False, "parallel": 2, "notes": cfg_notes}
    out = moc_batch.RUNTIME_DIR / "tutor-batch-config.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def job_running(runtime: Path) -> bool:
    """C'è un job di Antigravity vivo? Allora current-job.json è suo e non va sovrascritto."""
    try:
        st = json.loads((runtime / "job-status.json").read_text(encoding="utf-8"))
        if st.get("status") != "running" or not st.get("pid"):
            return False
        os.kill(int(st["pid"]), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def write_edit_config(course_id: str, date: str, note_title: str) -> Path:
    import moc_batch
    if job_running(moc_batch.RUNTIME_DIR):
        raise SystemExit("Antigravity sta già lavorando a una nota: riprova quando ha finito")
    state = json.loads(STATE.read_text(encoding="utf-8"))
    path = note_files(VAULT).get(note_title.lower())
    if not path:
        raise SystemExit(f"Nota non trovata: {note_title}")
    from tutor_store import load_courses
    course = next(c for c in load_courses(TUTOR_DIR / "courses.json") if c.id == course_id)
    plan = moc_batch.build_plan(VAULT, course.moc)
    base = moc_batch.build_job({"discipline": plan["discipline"], "moc": course.moc},
                               {"title": note_title, "notebooks": plan["moc_notebooks"]}, VAULT) if plan.get("moc_notebooks") else {
        "discipline": plan["discipline"], "disciplina": plan["discipline"],
        "pole": "università" if plan["discipline"] in moc_batch.UNIVERSITY_DISCIPLINES else "personale"}
    job = edit_job(state, course_id, date, note_title, lesson_text(course_id, date), str(path.relative_to(VAULT)), base)
    out = moc_batch.RUNTIME_DIR / "current-job.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Tutor delle lezioni: diari, analisi con agy, stato per la barra.")
    ap.add_argument("--force", action="store_true", help="Esegui anche se oggi è già stato fatto")
    ap.add_argument("--reconcile", action="store_true", help="Solo allinea lo stato ai file (nessuna AI)")
    ap.add_argument("--measure", metavar="COURSE", help="Costo reale di una chiamata sull'ultima lezione del corso")
    ap.add_argument("--batch-config", nargs=2, metavar=("COURSE", "DATE"), help="Prepara la creazione delle note di una lezione")
    ap.add_argument("--edit-config", nargs=3, metavar=("COURSE", "DATE", "NOTE"), help="Prepara il completamento di una nota")
    ap.add_argument("--import-paste", nargs=2, metavar=("COURSE", "FILE"), help="Aggiungi all'archivio lo storico del forum copiato da Moodle")
    args = ap.parse_args()
    if args.import_paste:
        from diary_sources import parse_forum_paste
        from tutor_store import append_new, load_courses
        course = next(c for c in load_courses(TUTOR_DIR / "courses.json") if c.id == args.import_paste[0])
        lessons = parse_forum_paste(Path(args.import_paste[1]).read_text(encoding="utf-8"), course.id, course.start_year)
        added = append_new(STORE, lessons)
        print(f"{len(lessons)} lezioni lette, {len(added)} nuove")
        return 0
    if args.batch_config:
        print(write_batch_config(*args.batch_config))
        return 0
    if args.edit_config:
        print(write_edit_config(*args.edit_config))
        return 0
    if args.measure:
        measure(args.measure)
        return 0
    return run(force=args.force, only_reconcile=args.reconcile)


if __name__ == "__main__":
    sys.exit(main())
