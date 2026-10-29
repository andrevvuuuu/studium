#!/usr/bin/env python3
"""
moc_batch.py — Creazione automatica delle note mancanti di un MOC.

Modalità:
  --plan --moc "<percorso MOC relativo al vault>"
      Stampa in JSON il piano: note ancora da creare (nell'ordine del MOC) e, per ciascuna,
      l'unione dei NotebookLM di TUTTI i MOC che la collegano (frontmatter `notebooklm_ids`).
  --run --config <batch-config.json>
      Esegue il batch con 2 note alla volta (config "parallel"), mai due dello stesso modulo del MOC.
      Ogni posto ha il suo runtime in /tmp/antigravity_runtime/workers/wN (ANTIGRAVITY_RUNTIME_DIR);
      lo stato complessivo è in /tmp/antigravity_runtime/batch-status.json. Si ferma quando trova il
      file batch-stop, si mette in pausa dopo errori consecutivi, tiene sveglio il Mac (caffeinate),
      aggiorna il rapporto in "00 Meta/Report Batch/" e manda notifiche (notify.py).
      A fine batch la prima menzione di ogni nota creata più tardi diventa un wikilink.

Le note dello stesso modulo restano in sequenza perché si citano a vicenda più spesso; il writer
in batch non modifica il MOC (la nota è già collegata), quindi due scritture non si sovrappongono.
"""

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orchestrator import (  # noqa: E402
    RUNTIME_DIR,
    parse_simple_frontmatter,
    resolve_vault_root,
    write_moc_notebooks_frontmatter,
)
from vault_layout import RACCORDO_HEADINGS, load_courses, resolve_note_path, sync_course  # noqa: E402
from notify import notify  # noqa: E402

BATCH_STATUS_FILE = RUNTIME_DIR / "batch-status.json"
BATCH_STOP_FILE = RUNTIME_DIR / "batch-stop"
BATCH_LOG_FILE = RUNTIME_DIR / "batch-output.log"

UNIVERSITY_DISCIPLINES = {
    "Matematica", "Informatica", "Fisica", "Intelligenza Artificiale", "Neuroscienze", "Biologia",
}

# Quota NotebookLM (Google AI Pro): rete di sicurezza, interviene solo se la quota è davvero esaurita
NLM_MIN_REMAINING_PERCENT = 1.5
# Limite NotebookLM a breve termine (troppe query ravvicinate): la nota torna in coda e il batch
# aspetta, con attese crescenti; dopo RATE_LIMIT_MAX_WAITS attese di fila va in pausa.
RATE_LIMIT_MARKER = "limite di utilizzo temporaneo"
RATE_LIMIT_WAIT_MINUTES = (10, 15, 20, 30, 45, 60)
RATE_LIMIT_MAX_WAITS = 30  # circa un giorno: la finestra breve di NotebookLM può durare ore
# Dopo un'attesa si riparte con una nota sola (fa da prova con lavoro vero: il limite è sul calcolo
# consumato, non sul numero di domande) e si torna al parallelo pieno dopo qualche nota riuscita
RATE_LIMIT_RAMP_SUCCESSES = 3
MAX_CONSECUTIVE_FAILURES = 2
# Note scritte contemporaneamente (sempre di moduli diversi del MOC)
DEFAULT_PARALLEL_NOTES = 2
MAX_PARALLEL_NOTES = 3
MIN_NOTE_BYTES = 800
ATTACHMENT_RE = re.compile(r"\.(png|jpe?g|gif|svg|webp|pdf|mp3|mp4|mov|wav|canvas|excalidraw|base)$", re.IGNORECASE)


# ------------------------------------------------------------------------------
# Scansione del vault
# ------------------------------------------------------------------------------

def iter_vault_markdown(vault_root: Path):
    for root, dirs, files in os.walk(vault_root):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.endswith(".md"):
                yield Path(root) / f


def normalize_link_target(raw: str) -> str:
    target = raw.split("|", 1)[0].split("#", 1)[0].strip()
    if "/" in target:
        target = target.rsplit("/", 1)[-1]
    if target.lower().endswith(".md"):
        target = target[:-3]
    return target.strip()


def extract_ordered_links(text: str) -> List[str]:
    """Wikilink del corpo in ordine di apparizione, escludendo frontmatter, blocchi di codice, embed e le
    sezioni di raccordo finali (rimandi al Macro-MOC e ad altri corsi, che non sono note da creare)."""
    _, body_start = parse_simple_frontmatter(text)
    body = text[body_start:]
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    body = "".join(sec for sec in re.split(r"(?m)^(?=## )", body)
                   if not RACCORDO_HEADINGS.search(sec.split("\n", 1)[0]))
    links: List[str] = []
    seen: Set[str] = set()
    for m in re.finditer(r"(!?)\[\[([^\[\]]+)\]\]", body):
        if m.group(1) == "!":
            continue
        target = normalize_link_target(m.group(2))
        if not target or ATTACHMENT_RE.search(target):
            continue
        key = target.lower()
        if key not in seen:
            seen.add(key)
            links.append(target)
    return links


def as_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def is_moc_file(path: Path, fm: Dict[str, Any], vault_root: Path) -> bool:
    types = [t.lower() for t in as_list(fm.get("Type") or fm.get("type"))]
    rel = str(path.relative_to(vault_root))
    return "moc" in types or bool(re.match(r"^\d+ MOC", rel)) or path.stem.endswith(" MOC")


class VaultScan:
    def __init__(self, vault_root: Path):
        self.vault_root = vault_root
        self.names: Set[str] = set()
        self.mocs: Dict[str, Dict[str, Any]] = {}
        self.records: List[Dict[str, Any]] = []
        for path in iter_vault_markdown(vault_root):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            fm, _ = parse_simple_frontmatter(text)
            aliases = as_list(fm.get("aliases") or fm.get("alias"))
            self.names.add(path.stem.lower())
            self.names.update(a.lower() for a in aliases)
            rel = str(path.relative_to(vault_root))
            self.records.append({
                "title": path.stem,
                "path": rel,
                "aliases": aliases,
                "tags": [t.lstrip("#") for t in as_list(fm.get("tags") or fm.get("tag"))],
                "disciplina": fm.get("Disciplina") or fm.get("disciplina") or (rel.split("/")[0] if "/" in rel else ""),
                "type": as_list(fm.get("Type") or fm.get("type")),
                "headings": [
                    {"level": len(h.group(1)), "heading": h.group(2).strip()}
                    for h in re.finditer(r"(?m)^(#{1,6})\s+(.+)$", re.sub(r"```.*?```", "", text, flags=re.DOTALL))
                ],
            })
            if is_moc_file(path, fm, vault_root):
                ids = as_list(fm.get("notebooklm_ids"))
                titles = as_list(fm.get("NotebookLM"))
                notebooks = [
                    {"id": nb_id, "title": titles[i] if i < len(titles) else nb_id}
                    for i, nb_id in enumerate(ids)
                ]
                self.mocs[rel] = {
                    "path": rel,
                    "name": path.stem,
                    "discipline": fm.get("Disciplina") or fm.get("disciplina") or "",
                    "notebooks": notebooks,
                    "links": extract_ordered_links(text),
                }

    def exists(self, title: str) -> bool:
        return title.lower() in self.names

    def write_vault_index(self, runtime: Path = RUNTIME_DIR) -> None:
        """Rigenera vault-index.json nel runtime indicato (stesso formato del menu Obsidian)."""
        (runtime / "vault-index.json").write_text(
            json.dumps(self.records, indent=2, ensure_ascii=False), encoding="utf-8"
        )


# ------------------------------------------------------------------------------
# Piano
# ------------------------------------------------------------------------------

def known_notebooks(vault_root: Path) -> Dict[str, str]:
    """Titolo -> id dei NotebookLM, dalla cache che il menu aggiorna a ogni apertura."""
    for p in (RUNTIME_DIR / "notebooks-cache.json", vault_root / ".antigravity" / "notebooks-cache.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            items = data.get("notebooks", data) if isinstance(data, dict) else data
            return {str(n.get("title", "")).strip(): n["id"] for n in items if n.get("id")}
        except Exception:
            continue
    return {}


def auto_map_moc_notebooks(vault_root: Path, scan: "VaultScan") -> List[str]:
    """MOC senza `notebooklm_ids`: li ricava dalla riga "Fonti Ufficiali del Corso: *Titolo*" scritta
    nei MOC creati da NotebookLM e li salva nel frontmatter. Restituisce i MOC mappati."""
    titles = known_notebooks(vault_root)
    mapped = []
    for rel, moc in scan.mocs.items():
        if moc["notebooks"] or not titles:
            continue
        try:
            text = (vault_root / rel).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        m = re.search(r"(?im)^.*Fonti Ufficiali[^\n]*$", text)
        if not m:
            continue
        line = re.sub(r"\*\*[^*\n]*\*\*", "", m.group(0))  # toglie l'etichetta in grassetto
        found = [t.strip() for t in re.findall(r"\*([^*\n]+)\*", line) if t.strip() in titles]
        if not found:
            continue
        notebooks = [{"id": titles[t], "title": t} for t in dict.fromkeys(found)]
        if write_moc_notebooks_frontmatter(vault_root / rel, notebooks):
            moc["notebooks"] = notebooks
            mapped.append(moc["name"])
    return mapped


def build_plan(vault_root: Path, moc_rel: str) -> Dict[str, Any]:
    scan = VaultScan(vault_root)
    auto_mapped = auto_map_moc_notebooks(vault_root, scan)
    moc = scan.mocs.get(moc_rel)
    if not moc:
        return {"error": f"MOC non trovato o non riconosciuto come MOC: {moc_rel}"}

    linked_by: Dict[str, List[str]] = {}
    for rel, m in scan.mocs.items():
        for link in m["links"]:
            linked_by.setdefault(link.lower(), []).append(rel)

    notes = []
    warnings: Set[str] = set()
    unmapped_mocs: Dict[str, str] = {}  # altri MOC che collegano note del piano ma senza NotebookLM
    for title in moc["links"]:
        if scan.exists(title) or title.endswith(" MOC") or re.search(r'[*"\\<>:|?^]', title):
            continue
        # NotebookLM: prima quelli del MOC corrente, poi quelli degli altri MOC che collegano la nota
        moc_paths = [moc_rel] + [p for p in linked_by.get(title.lower(), []) if p != moc_rel]
        notebooks: List[Dict[str, str]] = []
        seen_ids: Set[str] = set()
        for p in moc_paths:
            m = scan.mocs[p]
            for nb in m["notebooks"]:
                if nb["id"] not in seen_ids:
                    seen_ids.add(nb["id"])
                    notebooks.append(nb)
        for p in moc_paths:
            if not scan.mocs[p]["notebooks"] and p != moc_rel:
                unmapped_mocs.setdefault(p, scan.mocs[p]["name"])
        notes.append({
            "title": title,
            "notebooks": notebooks,
            "mocs": [scan.mocs[p]["name"] for p in moc_paths],
        })

    return {
        "moc": moc_rel,
        "moc_name": moc["name"],
        "discipline": moc["discipline"],
        "moc_notebooks": moc["notebooks"],
        "notes": notes,
        "warnings": sorted(warnings),
        "auto_mapped": auto_mapped,
        "unmapped_mocs": [{"path": p, "name": n} for p, n in unmapped_mocs.items()],
    }


# ------------------------------------------------------------------------------
# Esecuzione
# ------------------------------------------------------------------------------

def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}\n"
    sys.stdout.write(line)
    sys.stdout.flush()
    with open(BATCH_LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(line)


def write_batch_status(state: Dict[str, Any], **changes: Any) -> None:
    state.update(changes)
    state["updated_at"] = int(time.time() * 1000)
    tmp = BATCH_STATUS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(BATCH_STATUS_FILE)


def stop_requested() -> bool:
    return BATCH_STOP_FILE.exists()


def nlm_remaining() -> Optional[Dict[str, Any]]:
    """Finestra di quota NotebookLM più vincolante, o None se non determinabile."""
    try:
        proc = subprocess.run(["nlm", "usage", "--json"], capture_output=True, text=True, timeout=30, check=False)
        windows = json.loads(proc.stdout).get("windows") or []
        return min(windows, key=lambda w: w.get("percent_remaining", 100)) if windows else None
    except Exception:
        return None


def wait_for_nlm_quota(state: Dict[str, Any]) -> bool:
    """Se la quota è quasi esaurita attende il reset. Restituisce False se l'utente ferma il batch."""
    window = nlm_remaining()
    if not window or window.get("percent_remaining", 100) >= NLM_MIN_REMAINING_PERCENT:
        return True
    try:
        resume_at = datetime.fromisoformat(window["resets_at"]).timestamp() + 60
    except Exception:
        resume_at = time.time() + 1800
    resume_label = datetime.fromtimestamp(resume_at).strftime("%H:%M")
    log(f"Quota NotebookLM quasi esaurita ({window.get('percent_remaining', 0):.1f}% residuo): attesa fino alle {resume_label}")
    write_batch_status(state, status="waiting", message=f"⏳ Quota NotebookLM quasi esaurita: ripresa automatica alle {resume_label}")
    while time.time() < resume_at:
        if stop_requested():
            return False
        time.sleep(30)
    write_batch_status(state, status="running", message="Ripresa dopo il reset della quota NotebookLM")
    return True


def build_job(cfg: Dict[str, Any], note: Dict[str, Any], vault_root: Path) -> Dict[str, Any]:
    discipline = cfg["discipline"]
    title = note["title"]
    notebooks = note["notebooks"]
    # Cartella del corso e del modulo del MOC in cui la nota compare
    target_rel = resolve_note_path(vault_root, title, discipline, cfg.get("moc", ""))
    label = (
        f"NotebookLM: {notebooks[0]['title']}" if len(notebooks) == 1
        else f"NotebookLM Multiplo ({len(notebooks)} fonti: {' + '.join(nb['title'] for nb in notebooks)})"
    )
    details = [{"id": nb["id"], "title": nb["title"], "sources": 0} for nb in notebooks]
    allow_base = bool(cfg.get("allow_base_knowledge"))
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": "normal",
        "operation_type": "normal",
        "operation_label": "Nota Normale (Nuova)",
        "moc_mode": None,
        "allow_base_knowledge": allow_base,
        "syllabus_text": "",
        "syllabus_files": [],
        "notebook_id": notebooks[0]["id"],
        "notebook_title": label,
        "notebooks": [nb["id"] for nb in notebooks],
        "notebook_details": details,
        "target_file_path": target_rel,
        "target_file_abs": str(vault_root / target_rel),
        "title": title,
        "edit_mode": None,
        "user_instructions": "",
        "discipline": discipline,
        "disciplina": discipline,
        "layout_moc": cfg.get("moc", ""),
        "pole": "università" if discipline in UNIVERSITY_DISCIPLINES else "personale",
        "topic": title,
        "source": {
            "type": "notebooklm",
            "label": label,
            "value": details,
            "notebooks": [nb["id"] for nb in notebooks],
            "notebook_details": details,
            "allow_base_knowledge": allow_base,
        },
        "status": "pending",
        "batch": {"moc": cfg["moc"]},
    }


def worker_dir(slot: int) -> Path:
    return RUNTIME_DIR / "workers" / f"w{slot}"


def reset_runtime_for_job(runtime: Path, target_rel: str) -> None:
    """Equivalente di preRunCleanup del menu, nel runtime del posto di lavoro: contesto pulito e stato iniziale."""
    ctx = runtime / "job-context"
    if ctx.exists():
        subprocess.run(["rm", "-rf", str(ctx)], check=False)
    ctx.mkdir(parents=True, exist_ok=True)
    for stale in ("grounding-report.json", "current-prompt.md"):
        (runtime / stale).unlink(missing_ok=True)
    (runtime / "job-status.json").write_text(json.dumps({
        "status": "running",
        "percent": 5,
        "step_number": 1,
        "total_steps": 6,
        "phase": "prep",
        "message": "Preparazione della nota",
        "detail": "",
        "target_file": target_rel,
        "error": None,
        "pid": os.getpid(),
        "updated_at": int(time.time() * 1000),
    }, indent=2, ensure_ascii=False), encoding="utf-8")


def run_single_note(cfg: Dict[str, Any], note: Dict[str, Any], vault_root: Path, slot: int) -> Dict[str, Any]:
    runtime = worker_dir(slot)
    runtime.mkdir(parents=True, exist_ok=True)
    job = build_job(cfg, note, vault_root)
    target_rel = job["target_file_path"]
    reset_runtime_for_job(runtime, target_rel)
    VaultScan(vault_root).write_vault_index(runtime)
    (runtime / "current-job.json").write_text(json.dumps(job, indent=2, ensure_ascii=False), encoding="utf-8")
    run_job = vault_root / ".antigravity" / "scripts" / "run_job.sh"
    env = {**os.environ, "ANTIGRAVITY_RUNTIME_DIR": str(runtime)}
    started = time.time()
    with open(runtime / "job-output.log", "w", encoding="utf-8") as out:
        proc = subprocess.run(["bash", str(run_job)], cwd=str(vault_root), stdout=out, stderr=subprocess.STDOUT,
                              env=env, check=False)

    def read_json(name: str) -> Dict[str, Any]:
        try:
            return json.loads((runtime / name).read_text(encoding="utf-8"))
        except Exception:
            return {}

    status, final_job, grounding = read_json("job-status.json"), read_json("current-job.json"), read_json("grounding-report.json")
    target_path = vault_root / (final_job.get("target_file_rel") or status.get("target_file") or target_rel)
    written = target_path.exists() and target_path.stat().st_size >= MIN_NOTE_BYTES
    ok = proc.returncode == 0 and status.get("status") == "completed" and written
    compact = lambda items: [{"claim": c.get("claim", ""), "quote": c.get("quote", "")} for c in (items or [])]
    return {
        "title": note["title"],
        "path": str(target_path.relative_to(vault_root)) if target_path.exists() else target_rel,
        "ok": ok,
        "started_at": int(started * 1000),
        "finished_at": int(time.time() * 1000),
        "seconds": int(time.time() - started),
        "error": None if ok else (status.get("error") or status.get("detail") or ("Nota non scritta" if not written else f"exit {proc.returncode}")),
        "grounding": final_job.get("grounding_summary", ""),
        "removed": compact(grounding.get("removed")),
        "unverified": compact(grounding.get("unverified")),
        "confirmed": len(grounding.get("confirmed") or []),
        "missing_sections": final_job.get("missing_sections") or [],
    }


def pid_alive(pid: Any) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def note_module(course: Any, title: str) -> str:
    if not course:
        return ""
    return course.note_module.get(title.lower()) or ""


def run_batch(cfg_path: Path) -> int:
    vault_root = resolve_vault_root()
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    if BATCH_STATUS_FILE.exists():
        try:
            prev = json.loads(BATCH_STATUS_FILE.read_text(encoding="utf-8"))
            if prev.get("status") in ("running", "waiting") and prev.get("pid") != os.getpid() and pid_alive(prev.get("pid")):
                sys.stderr.write("Un batch è già in esecuzione.\n")
                return 1
        except Exception:
            pass
    if BATCH_STOP_FILE.exists():
        BATCH_STOP_FILE.unlink()
    BATCH_LOG_FILE.write_text("", encoding="utf-8")

    # Il Mac non va in stop finché il batch è vivo (con il coperchio chiuso si addormenta comunque)
    try:
        subprocess.Popen(["caffeinate", "-i", "-m", "-w", str(os.getpid())],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    notes = cfg["notes"]
    workers = max(1, min(MAX_PARALLEL_NOTES, int(cfg.get("parallel", DEFAULT_PARALLEL_NOTES))))
    course = next((c for c in load_courses(vault_root) if c.moc_rel == cfg["moc"]), None)
    state: Dict[str, Any] = {
        "status": "running",
        "pid": os.getpid(),
        "moc": cfg["moc"],
        "moc_name": cfg.get("moc_name", ""),
        "total": len(notes),
        "parallel": workers,
        "index": 0,
        "current_title": "",
        "active": [],
        "done": [],
        "failed": [],
        "skipped": [],
        "links_added": 0,
        "report": "",
        "message": "Avvio del batch",
        "started_at": int(time.time() * 1000),
    }
    lock = threading.Lock()

    def publish(**changes: Any) -> None:
        with lock:
            state["current_title"] = " + ".join(a["title"] for a in state["active"])
            write_batch_status(state, **changes)
            try:
                state["report"] = write_batch_report(vault_root, state)
            except Exception as e:
                log(f"Rapporto non aggiornato: {e}")

    publish()
    log(f"Batch avviato su {cfg['moc']}: {len(notes)} note, {workers} alla volta")

    pending = list(enumerate(notes, 1))
    running: Dict[Any, Dict[str, Any]] = {}
    free_slots = list(range(1, workers + 1))
    consecutive_failures = 0
    paused_msg = ""
    queued: Dict[Any, Tuple[int, Dict[str, Any]]] = {}
    rate_waits = 0
    resume_after = 0.0
    slot_limit = workers
    ramp_successes = 0

    def wait_rate_limit(reason: str) -> None:
        nonlocal rate_waits, resume_after, paused_msg, slot_limit, ramp_successes
        rate_waits += 1
        slot_limit, ramp_successes = 1, 0
        if rate_waits > RATE_LIMIT_MAX_WAITS:
            paused_msg = ("⚠️ Batch in pausa: NotebookLM continua a rifiutare le query per il limite "
                          "di utilizzo. Riavvia il batch più tardi: riprenderà dalle note mancanti.")
            return
        minutes = RATE_LIMIT_WAIT_MINUTES[min(rate_waits, len(RATE_LIMIT_WAIT_MINUTES)) - 1]
        resume_after = time.time() + minutes * 60
        label = datetime.fromtimestamp(resume_after).strftime("%H:%M")
        log(f"   ⏳ {reason}: NotebookLM al limite di utilizzo. Nuovo tentativo alle {label}")
        publish(status="waiting",
                message=f"⏳ NotebookLM al limite di utilizzo (troppe query): nuovo tentativo alle {label}")

    def note_job(i: int, note: Dict[str, Any], slot: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for attempt in (1, 2):
            log(f"[{i}/{len(notes)}] Posto {slot}: {note['title']}" + (" (secondo tentativo)" if attempt == 2 else ""))
            result = run_single_note(cfg, note, vault_root, slot)
            if RATE_LIMIT_MARKER in str(result.get("error") or ""):
                result["rate_limited"] = True
                break
            if result["ok"] or stop_requested():
                break
            log(f"   ❌ {note['title']}: tentativo {attempt} fallito: {result['error']}")
            if attempt == 1:
                time.sleep(30)
        result["index"] = i
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        while pending or running:
            # Avvio: una nota per posto libero, mai due dello stesso modulo insieme
            if resume_after and time.time() >= resume_after and not running:
                resume_after = 0.0
                publish(status="running", message="Ripresa con una nota alla volta dopo il limite di NotebookLM")
            while (free_slots and pending and len(running) < slot_limit and not stop_requested()
                   and not paused_msg and not resume_after):
                busy_modules = {a["module"] for a in state["active"] if a["module"]}
                pick = next((k for k, (_, n) in enumerate(pending) if not note_module(course, n["title"])
                             or note_module(course, n["title"]) not in busy_modules), None)
                if pick is None:
                    break
                i, note = pending.pop(pick)
                if VaultScan(vault_root).exists(note["title"]) or not note["notebooks"]:
                    state["skipped"].append(note["title"])
                    log(f"[{i}/{len(notes)}] Saltata ({'già esistente' if note['notebooks'] else 'nessun NotebookLM'}): {note['title']}")
                    publish()
                    continue
                if not wait_for_nlm_quota(state):
                    break
                slot = free_slots.pop(0)
                fut = pool.submit(note_job, i, note, slot)
                queued[fut] = (i, note)
                running[fut] = {"title": note["title"], "slot": slot, "index": i,
                                "module": note_module(course, note["title"]),
                                "runtime": str(worker_dir(slot)), "started_at": int(time.time() * 1000)}
                state["active"] = list(running.values())
                publish(status="running", index=max(a["index"] for a in state["active"]),
                        message=f"{len(running)} note in corso")

            if not running:
                if resume_after and pending and not stop_requested():
                    time.sleep(5)
                    continue
                break
            done_futs, _ = concurrent.futures.wait(list(running), timeout=5, return_when=concurrent.futures.FIRST_COMPLETED)
            for fut in done_futs:
                info = running.pop(fut)
                free_slots.append(info["slot"])
                free_slots.sort()
                try:
                    result = fut.result()
                except Exception as e:
                    result = {"title": info["title"], "ok": False, "error": str(e), "seconds": 0, "index": info["index"]}
                state["active"] = list(running.values())
                if result.get("rate_limited"):
                    pending.insert(0, queued.pop(fut))
                    if resume_after:
                        log(f"   ⏳ {result['title']}: rimessa in coda (limite NotebookLM)")
                    else:
                        wait_rate_limit(f"{result['title']} rimessa in coda")
                    continue
                queued.pop(fut, None)
                if result["ok"]:
                    rate_waits = 0
                    consecutive_failures = 0
                    ramp_successes += 1
                    if slot_limit < workers and ramp_successes >= RATE_LIMIT_RAMP_SUCCESSES:
                        slot_limit = workers
                        log(f"   NotebookLM regge di nuovo: si torna a {workers} note alla volta")
                    state["done"].append(result)
                    log(f"   ✅ {result['title']} in {result['seconds']}s → {result['path']} {result.get('grounding', '')}")
                else:
                    consecutive_failures += 1
                    state["failed"].append(result)
                    notify(f"Nota non creata: {result['title']}",
                           f"Due tentativi falliti. Errore: {str(result.get('error'))[:160]}", "high")
                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES and not paused_msg:
                        paused_msg = (f"⚠️ Batch in pausa dopo {consecutive_failures} note fallite di fila "
                                      f"(ultimo errore: {result['error']}). Controlla 'nlm login' e riavvia il batch: "
                                      "riprenderà dalle note mancanti.")
                publish()
            if stop_requested() and not running:
                break

    created = [r for r in state["done"] if r.get("ok")]
    try:
        state["links_added"] = link_later_notes(vault_root, created)
        if state["links_added"]:
            log(f"Collegamenti verso le note create dopo: {state['links_added']}")
    except Exception as e:
        log(f"Passaggio collegamenti non riuscito: {e}")
    try:
        log(f"Layout: {json.dumps(sync_course(vault_root, cfg['moc']), ensure_ascii=False)}")
    except Exception as e:
        log(f"Layout non aggiornato: {e}")

    counts = f"{len(state['done'])} create, {len(state['failed'])} fallite, {len(state['skipped'])} saltate"
    if paused_msg:
        state["active"] = []
        publish(status="paused", message=paused_msg)
        notify(f"Batch in pausa: {state['moc_name']}", f"{counts}. {paused_msg[2:200]}", "high")
        log(paused_msg)
        return 1
    if stop_requested():
        state["active"] = []
        publish(status="stopped", message=f"⏸️ Batch fermato dall'utente ({counts})")
        log("Batch fermato dall'utente")
        return 0
    msg = f"✅ Batch completato: {counts}"
    state["active"] = []
    publish(status="completed", message=msg)
    notify(f"Batch completato: {state['moc_name']}", counts + (f", {state['links_added']} collegamenti aggiunti" if state["links_added"] else ""))
    log(msg)
    return 0


# ------------------------------------------------------------------------------
# Collegamenti verso le note create dopo
# ------------------------------------------------------------------------------

def protected_spans(text: str) -> List[Tuple[int, int]]:
    """Zone in cui non si inseriscono link: frontmatter, codice, formule, link esistenti, titoli, callout, dati di studio."""
    spans = []
    _, body_start = parse_simple_frontmatter(text)
    spans.append((0, body_start))
    multiline = (r"```.*?```", r"%%.*?%%", r"\$\$.*?\$\$")
    single_line = (r"(?<!\\)\$[^$\n]+?(?<!\\)\$", r"`[^`\n]+`", r"!?\[\[[^\]]*\]\]", r"\[[^\]\n]*\]\([^)\n]*\)",
                   r"(?m)^#{1,6} .*$", r"(?m)^>\s*\[![^\]]*\].*$", r"<[^>\n]+>")
    for pattern in multiline:
        spans += [(m.start(), m.end()) for m in re.finditer(pattern, text, flags=re.DOTALL)]
    for pattern in single_line:
        spans += [(m.start(), m.end()) for m in re.finditer(pattern, text)]
    return spans


def link_later_notes(vault_root: Path, created: List[Dict[str, Any]]) -> int:
    """Nelle note del batch, la prima menzione testuale di una nota creata più tardi (non ancora esistente
    quando la nota è stata scritta) diventa un wikilink. Nessuna riscrittura: si aggiungono solo [[ ]]."""
    added = 0
    names: Dict[str, List[str]] = {}
    for r in created:
        p = vault_root / r["path"]
        if not p.exists():
            continue
        fm, _ = parse_simple_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
        names[r["title"]] = [r["title"]] + [a for a in as_list(fm.get("aliases")) if len(a) >= 6]
    for r in created:
        path = vault_root / r["path"]
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        original = text
        later = [o for o in created if o["title"] != r["title"] and o.get("finished_at", 0) > r.get("started_at", 0)]
        for other in later:
            if re.search(r"\[\[" + re.escape(other["title"]) + r"(\]\]|[|#])", text, flags=re.IGNORECASE):
                continue
            spans = protected_spans(text)
            for name in sorted(names.get(other["title"], [other["title"]]), key=len, reverse=True):
                hit = None
                for m in re.finditer(r"(?<![\w\[])" + re.escape(name) + r"(?![\w\]])", text, flags=re.IGNORECASE):
                    if not any(a <= m.start() < b for a, b in spans):
                        hit = m
                        break
                if hit:
                    found = hit.group(0)
                    link = f"[[{other['title']}]]" if found == other["title"] else f"[[{other['title']}|{found}]]"
                    text = text[:hit.start()] + link + text[hit.end():]
                    added += 1
                    break
        if text != original:
            path.write_text(text, encoding="utf-8")
    return added


# ------------------------------------------------------------------------------
# Rapporto del batch (nota nel vault)
# ------------------------------------------------------------------------------

REPORT_DIR = "00 Meta/Report Batch"


def write_batch_report(vault_root: Path, state: Dict[str, Any]) -> str:
    started = datetime.fromtimestamp(state["started_at"] / 1000)
    rel = f"{REPORT_DIR}/Report batch {state.get('moc_name') or 'MOC'} {started.strftime('%Y-%m-%d %H.%M')}.md"
    done, failed, skipped = state["done"], state["failed"], state["skipped"]
    removed_total = sum(len(r.get("removed") or []) for r in done)
    unverified_total = sum(len(r.get("unverified") or []) for r in done)
    status_label = {"running": "in corso", "waiting": "in attesa", "completed": "completato", "paused": "in pausa",
                    "stopped": "fermato"}.get(state.get("status"), state.get("status", ""))
    moc_link = Path(state["moc"]).stem
    lines = [
        "---",
        "Type:",
        "  - Report",
        f"MOC: \"[[{moc_link}]]\"",
        f"created: {started.strftime('%Y-%m-%d')}",
        "---",
        "",
        f"# Report batch: {state.get('moc_name', '')}",
        "",
        f"Avviato il {started.strftime('%d/%m/%Y alle %H:%M')} da [[{moc_link}]], stato: **{status_label}**.",
        "",
        f"- Note create: **{len(done)}** di {state['total']}",
        f"- Note fallite: **{len(failed)}**",
        f"- Note saltate (già esistenti o senza NotebookLM): **{len(skipped)}**",
        f"- Contenuti esterni rimossi dalla verifica di esclusività: **{removed_total}**",
        f"- Affermazioni non verificabili da controllare: **{unverified_total}**",
    ]
    if state.get("links_added"):
        lines.append(f"- Collegamenti aggiunti verso note create dopo: **{state['links_added']}**")
    if state.get("active"):
        lines += ["", "In corso ora: " + ", ".join(f"[[{a['title']}]]" for a in state["active"])]

    to_check = [r for r in done if r.get("unverified")]
    if to_check:
        lines += ["", "## Da controllare a mano",
                  "NotebookLM non ha saputo dire se queste affermazioni sono nelle fonti: sono rimaste nella nota.", ""]
        for r in to_check:
            lines.append(f"### [[{r['title']}]]")
            for c in r["unverified"]:
                lines.append(f"- [ ] {c['claim']}")
                if c.get("quote"):
                    lines.append("  > " + " ".join(c["quote"].split())[:300])
            lines.append("")
    no_sections = [r for r in done if r.get("missing_sections")]
    if no_sections:
        lines += ["", "## Sezioni richieste dal MOC ma mancanti nella nota",
                  "Il MOC collega questi paragrafi con [[Nota#Sezione]], ma la nota non li contiene.", ""]
        for r in no_sections:
            lines.append(f"- [[{r['title']}]]: " + ", ".join(r["missing_sections"]))
    if failed:
        lines += ["", "## Note fallite", ""]
        for r in failed:
            lines.append(f"- **{r['title']}**: {str(r.get('error') or 'errore sconosciuto')[:300]}")
    if done:
        lines += ["", "## Note create", "", "| Nota | Durata | Rimossi | Confermati | Da controllare |", "|---|---|---|---|---|"]
        for r in sorted(done, key=lambda x: x.get("index", 0)):
            mins = f"{r['seconds'] // 60} min" if r.get("seconds") else ""
            lines.append(f"| [[{r['title']}]] | {mins} | {len(r.get('removed') or [])} | {r.get('confirmed', 0)} | "
                         f"{len(r.get('unverified') or [])} |")
        removed_notes = [r for r in done if r.get("removed")]
        if removed_notes:
            lines += ["", "## Contenuti rimossi perché assenti dalle fonti", ""]
            for r in removed_notes:
                lines.append(f"- [[{r['title']}]]")
                for c in r["removed"]:
                    lines.append(f"    - {c['claim']}")
    lines.append("")
    path = vault_root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return rel


def main() -> int:
    parser = argparse.ArgumentParser(description="Creazione automatica delle note mancanti di un MOC.")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--moc", type=str, default="")
    parser.add_argument("--config", type=str, default=str(RUNTIME_DIR / "batch-config.json"))
    args = parser.parse_args()

    if args.plan:
        print(json.dumps(build_plan(resolve_vault_root(), args.moc), ensure_ascii=False))
        return 0
    if args.run:
        try:
            return run_batch(Path(args.config))
        except Exception as e:
            state: Dict[str, Any] = {}
            try:
                state = json.loads(BATCH_STATUS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
            write_batch_status(state, status="error", message=f"❌ Errore del batch: {e}", current_title="")
            log(f"Errore del batch: {e}")
            return 1
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
