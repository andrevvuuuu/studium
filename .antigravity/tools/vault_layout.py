#!/usr/bin/env python3
"""
vault_layout.py — Collocazione delle note nel file explorer secondo i MOC.

Ogni MOC di corso (es. `01 MOC's/Analisi 1 MOC.md`, Disciplina: Matematica) definisce:
    <Disciplina>/<Corso>/<NN Modulo>/<Nota>.md
dove <Corso> è il nome del MOC senza " MOC" e i moduli sono le sezioni H2 del MOC che
collegano note, numerate nell'ordine del MOC. L'ordine nel file explorer è scritto nel
data.json del plugin Manual Sorting (kh4f), che lo ricarica da solo quando cambia su disco.

Modalità:
  --resolve --title "<nota>" [--discipline D] [--moc <rel>]   stampa il percorso relativo
  --sync --moc <rel> [--no-move]                              sposta le note del MOC e aggiorna l'ordine
  --sync-all [--no-move]                                      come sopra per tutti i MOC di corso
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orchestrator import parse_simple_frontmatter, resolve_vault_root  # noqa: E402

MOC_DIR = "01 MOC's"
SORTING_DATA = Path(".obsidian") / "plugins" / "manual-sorting" / "data.json"
MOVES_LOG = Path(".antigravity") / "layout-moves.jsonl"

# Sezioni H2 del MOC che non sono moduli del corso
NON_MODULE_HEADINGS = re.compile(r"visione d.insieme|note e paragrafi collegati|diagnosi|fonti|bibliografia", re.IGNORECASE)
# Sezioni di raccordo: i loro link sono rimandi (Macro-MOC, altri corsi), non note del corso
RACCORDO_HEADINGS = re.compile(r"note e paragrafi collegati|fuori dall.indice|diagnosi|bibliografia", re.IGNORECASE)
ATTACHMENT_RE = re.compile(r"\.(png|jpe?g|gif|svg|webp|pdf|mp3|mp4|mov|wav|canvas|excalidraw|base)$", re.IGNORECASE)
ILLEGAL_CHARS = re.compile(r'[\\/:*?"<>|#^\[\]]')
MAX_FOLDER_NAME = 72
# Sotto questa soglia di note il corso resta una sola cartella, senza sottocartelle per modulo
MIN_NOTES_FOR_MODULES = 15
# Nota "di base" della materia (va in <Disciplina>/ fuori dai corsi): collegata da 2+ corsi della stessa
# disciplina e, in ognuno, nei primi moduli o in un modulo introduttivo
EARLY_MODULE_MAX = 3
BASE_MODULE_HEADINGS = re.compile(r"fondament|prelimin|nozioni|insiem|logica|basi|introduz|richiam|prerequisit", re.IGNORECASE)
# Frontmatter della nota che decide a mano: `corso: generale` (radice della materia) o `corso: <nome corso>`
OVERRIDE_KEYS = ("corso", "Corso")
BASE_OVERRIDE = re.compile(r"^(generale|base|basi|comune|fondamenti)$", re.IGNORECASE)
PLACEMENTS_FILE = Path(".antigravity") / "layout-placements.json"


def is_moc_rel(rel: str) -> bool:
    return bool(re.match(r"^\d+ MOC", rel)) or Path(rel).stem.endswith(" MOC")


def clean_folder_name(title: str) -> str:
    name = re.sub(r"^\s*(\d+|[IVXLC]+)[.)]\s+", "", title)  # la numerazione la aggiunge la cartella
    name = ILLEGAL_CHARS.sub("", name)
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) > MAX_FOLDER_NAME:
        cut = name[:MAX_FOLDER_NAME].rsplit(" ", 1)[0]
        name = re.sub(r"[\s,;.\-]+(e|ed|di|del|della|dei|degli|delle|con|per|tra|nei|nelle)?$", "", cut) if len(cut) > 20 else name[:MAX_FOLDER_NAME]
    return name.rstrip(" .")


def link_target(raw: str) -> str:
    target = raw.split("|", 1)[0].split("#", 1)[0].strip()
    if "/" in target:
        target = target.rsplit("/", 1)[-1]
    if target.lower().endswith(".md"):
        target = target[:-3]
    return target.strip()


class Course:
    """Struttura di un MOC di corso: moduli ordinati e note di ciascun modulo."""

    def __init__(self, vault_root: Path, moc_rel: str):
        self.moc_rel = moc_rel
        text = (vault_root / moc_rel).read_text(encoding="utf-8", errors="replace")
        fm, body_start = parse_simple_frontmatter(text)
        disc = fm.get("Disciplina") or fm.get("disciplina") or ""
        self.discipline = disc if isinstance(disc, str) else ""
        ids = fm.get("notebooklm_ids") or []
        self.notebooks = set(ids if isinstance(ids, list) else [ids])
        name = Path(moc_rel).stem
        self.name = name[:-4].strip() if name.endswith(" MOC") else name
        body = re.sub(r"```.*?```", "", text[body_start:], flags=re.DOTALL)

        # Quante volte il MOC collega ogni nota: misura di quanto la nota pesa in questo corso
        self.mentions: Dict[str, int] = {}
        for m in re.finditer(r"(?<!!)\[\[([^\[\]]+)\]\]", body):
            k = link_target(m.group(1)).lower()
            self.mentions[k] = self.mentions.get(k, 0) + 1
        self.module_index: Dict[str, int] = {}  # titolo minuscolo -> numero del modulo (0 = fuori dai moduli)
        # Sezioni richieste dal MOC con [[Nota#Sezione]]: diventano paragrafi della nota madre
        self.sections: Dict[str, List[str]] = {}
        for m in re.finditer(r"(?<!!)\[\[([^\[\]|#]+)#([^\[\]|]+)(?:\|[^\[\]]*)?\]\]", body):
            k, sec = link_target(m.group(1)).lower(), m.group(2).strip()
            if sec and sec not in self.sections.setdefault(k, []):
                self.sections[k].append(sec)

        self.modules: List[Tuple[str, List[str]]] = []  # (nome cartella, note in ordine)
        self.note_module: Dict[str, Optional[str]] = {}  # titolo minuscolo -> cartella modulo (None = radice corso)
        self.note_titles: List[str] = []
        sections = re.split(r"(?m)^##\s+(.+)$", body)
        for i in range(1, len(sections), 2):
            heading, content = sections[i].strip(), sections[i + 1]
            links = []
            for m in re.finditer(r"(!?)\[\[([^\[\]]+)\]\]", content):
                if m.group(1) == "!":
                    continue
                t = link_target(m.group(2))
                if not t or ATTACHMENT_RE.search(t) or t.endswith(" MOC") or ILLEGAL_CHARS.search(t):
                    continue
                links.append(t)
            if RACCORDO_HEADINGS.search(heading):
                continue
            if NON_MODULE_HEADINGS.search(heading) or not links:
                # Note collegate solo qui finiscono nella radice del corso
                for t in links:
                    if t.lower() not in self.note_module:
                        self.note_module[t.lower()] = None
                        self.note_titles.append(t)
                continue
            folder = f"{len(self.modules) + 1:02d} {clean_folder_name(heading)}"
            notes = []
            for t in links:
                key = t.lower()
                if key in self.note_module and self.note_module[key] is not None:
                    continue
                if key not in self.note_module:
                    self.note_titles.append(t)
                self.note_module[key] = folder
                self.module_index[key] = len(self.modules) + 1
                notes.append(t)
            self.modules.append((folder, notes))

        # Corso piccolo: tutte le note nella cartella del corso, nell'ordine del MOC
        if len(self.note_titles) < MIN_NOTES_FOR_MODULES:
            self.modules = []
            self.note_module = {t.lower(): None for t in self.note_titles}
    @property
    def valid(self) -> bool:
        return bool(self.discipline and self.note_titles)

    @property
    def folder(self) -> str:
        return f"{self.discipline}/{self.name}"

    def path_for(self, title: str) -> Optional[str]:
        key = title.lower()
        if key not in self.note_module:
            return None
        module = self.note_module[key]
        return f"{self.folder}/{module}/{title}.md" if module else f"{self.folder}/{title}.md"


def requested_sections(vault_root: Path, title: str) -> List[str]:
    """Sezioni che i MOC collegano come [[title#Sezione]]: la nota deve contenerle come paragrafi."""
    out: List[str] = []
    for c in load_courses(vault_root):
        for sec in c.sections.get(title.lower(), []):
            if sec not in out:
                out.append(sec)
    return out


def load_courses(vault_root: Path) -> List[Course]:
    courses = []
    moc_dir = vault_root / MOC_DIR
    if not moc_dir.is_dir():
        return courses
    for p in sorted(moc_dir.glob("*.md")):
        try:
            c = Course(vault_root, str(p.relative_to(vault_root)))
        except Exception:
            continue
        if c.valid and (vault_root / c.discipline).is_dir():
            courses.append(c)
    return courses


def find_existing_note(vault_root: Path, title: str) -> Optional[str]:
    target = f"{title}.md".lower()
    for root, dirs, files in os.walk(vault_root):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.lower() == target:
                return str((Path(root) / f).relative_to(vault_root))
    return None


def note_override(vault_root: Path, title: str) -> str:
    """Valore di `corso:` nel frontmatter della nota, se esiste: decide a mano dove va."""
    rel = find_existing_note(vault_root, title)
    if not rel:
        return ""
    try:
        fm, _ = parse_simple_frontmatter((vault_root / rel).read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return ""
    for k in OVERRIDE_KEYS:
        v = fm.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def is_early(course: Course, key: str) -> bool:
    idx = course.module_index.get(key, 0)
    if idx == 0:
        return True  # citata solo fuori dai moduli: per questo corso è un riferimento generale
    return idx <= EARLY_MODULE_MAX or bool(BASE_MODULE_HEADINGS.search(course.note_module.get(key) or ""))


def importance(course: Course, key: str, notebooks: Optional[List[str]] = None) -> int:
    score = (3 if course.note_module.get(key) else 0) + course.mentions.get(key, 0)
    if notebooks and course.notebooks & set(notebooks):
        score += 2
    return score


def placement(vault_root: Path, courses: List[Course], title: str, discipline: str = "", moc_hint: str = "",
              notebooks: Optional[List[str]] = None) -> Optional[Tuple[str, Any]]:
    """Dove va la nota: ("base", disciplina) nella radice della materia, ("course", Course) nel corso
    in cui pesa di più, None se nessun MOC di corso la collega."""
    key = title.lower()
    linking = [c for c in courses if key in c.note_module]
    if not linking:
        return None
    disc = discipline or linking[0].discipline
    same = [c for c in linking if c.discipline == disc] or linking
    override = note_override(vault_root, title)
    if override and BASE_OVERRIDE.match(override):
        return ("base", same[0].discipline)
    if override:
        for c in linking:
            if c.name.lower() == override.lower():
                return ("course", c)
    if len(same) >= 2 and all(is_early(c, key) for c in same):
        return ("base", same[0].discipline)
    best = max(importance(c, key, notebooks) for c in same)
    top = [c for c in same if importance(c, key, notebooks) == best]
    for c in top:
        if moc_hint and c.moc_rel == moc_hint:
            return ("course", c)
    return ("course", top[0])


def placement_path(pl: Tuple[str, Any], title: str) -> str:
    kind, where = pl
    return f"{where}/{title}.md" if kind == "base" else where.path_for(title)


def owner_course(courses: List[Course], title: str, discipline: str = "", moc_hint: str = "",
                 current_rel: str = "", notebooks: Optional[List[str]] = None,
                 vault_root: Optional[Path] = None) -> Optional[Course]:
    """Corso che gestisce la nota (per le note di base: il primo corso della disciplina che la collega)."""
    root = vault_root or resolve_vault_root()
    pl = placement(root, courses, title, discipline, moc_hint, notebooks)
    if not pl:
        return None
    if pl[0] == "course":
        return pl[1]
    return next(c for c in courses if title.lower() in c.note_module and c.discipline == pl[1])


def resolve_note_path(vault_root: Path, title: str, discipline: str = "", moc_hint: str = "",
                      notebooks: Optional[List[str]] = None) -> str:
    """Percorso relativo in cui creare la nota; ricade su <Disciplina>/<Titolo>.md se nessun MOC la collega."""
    existing = find_existing_note(vault_root, title)
    if existing:
        return existing
    pl = placement(vault_root, load_courses(vault_root), title, discipline, moc_hint, notebooks)
    if pl:
        return placement_path(pl, title)
    return f"{discipline}/{title}.md" if discipline else f"{title}.md"


def load_placements(vault_root: Path) -> Dict[str, str]:
    try:
        return json.loads((vault_root / PLACEMENTS_FILE).read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_placements(vault_root: Path, data: Dict[str, str]) -> None:
    (vault_root / PLACEMENTS_FILE).write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


def may_move(current: str, recorded: Optional[str], courses: List[Course], discipline: str) -> bool:
    """Le note spostate a mano (es. con Manual Sorting) non vengono più toccate: si sposta solo una nota
    che è ancora dove l'automazione l'aveva messa, o una nota mai sistemata che sta nella radice della
    disciplina o in una cartella di corso."""
    if recorded:
        return current == recorded
    if parent_of(current) == discipline:
        return True
    return any(current.startswith(c.folder + "/") for c in courses if c.discipline == discipline)


# ------------------------------------------------------------------------------
# Manual Sorting
# ------------------------------------------------------------------------------

def parent_of(rel: str) -> str:
    return rel.rsplit("/", 1)[0] if "/" in rel else "/"


def load_sorting(vault_root: Path) -> Optional[Dict[str, Any]]:
    p = vault_root / SORTING_DATA
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_sorting(vault_root: Path, data: Dict[str, Any]) -> None:
    p = vault_root / SORTING_DATA
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)


def ordered_children(order: Dict[str, Any], folder: str, wanted: List[str], vault_root: Path) -> None:
    """Imposta i figli di `folder`: prima `wanted` nell'ordine dato, poi gli altri elementi già presenti."""
    entry = order.setdefault(folder, {"children": [], "sortOrder": "custom"})
    folder_abs = vault_root if folder == "/" else vault_root / folder
    on_disk = []
    if folder_abs.is_dir():
        for child in sorted(folder_abs.iterdir()):
            if child.name.startswith(".") or child.name.endswith(".tmp"):
                continue
            on_disk.append(child.name if folder == "/" else f"{folder}/{child.name}")
    present = set(on_disk)
    wanted = [w for w in wanted if w in present]
    rest = [c for c in entry.get("children", []) if c in present and c not in wanted]
    rest += [c for c in on_disk if c not in wanted and c not in rest]
    entry["children"] = wanted + rest
    entry["sortOrder"] = "custom"


def apply_course_order(vault_root: Path, course: Course, data: Dict[str, Any]) -> None:
    order = data.setdefault("customOrder", {})
    # Cartella disciplina: i corsi vanno in cima, prima delle note sciolte
    disc_entry = order.get(course.discipline, {"children": []})
    courses_first = [c for c in disc_entry.get("children", []) if (vault_root / c).is_dir()]
    if course.folder not in courses_first:
        courses_first.insert(0, course.folder)
    # Poi le note di base della materia, nell'ordine in cui il corso le presenta
    base_notes = [f"{course.discipline}/{t}.md" for t in course.note_titles]
    known = [c for c in disc_entry.get("children", []) if c in base_notes]
    base_notes = known + [b for b in base_notes if b not in known]
    ordered_children(order, course.discipline, courses_first + base_notes, vault_root)
    ordered_children(order, course.folder, [f"{course.folder}/{m}" for m, _ in course.modules] +
                     [f"{course.folder}/{t}.md" for t in course.note_titles if course.note_module[t.lower()] is None],
                     vault_root)
    for module, notes in course.modules:
        mod_rel = f"{course.folder}/{module}"
        ordered_children(order, mod_rel, [f"{mod_rel}/{t}.md" for t in notes], vault_root)
    # Le chiavi di cartelle scomparse (moduli rinominati) vanno eliminate
    for key in list(order.keys()):
        if key.startswith(course.folder + "/") and not (vault_root / key).is_dir():
            del order[key]


# ------------------------------------------------------------------------------
# Sincronizzazione
# ------------------------------------------------------------------------------

def sync_course(vault_root: Path, moc_rel: str, move: bool = True, courses: Optional[List[Course]] = None,
                dry_run: bool = False) -> Dict[str, Any]:
    """Serializzato con un lock su file: più note del batch possono finire insieme."""
    import fcntl
    lock_path = vault_root / ".antigravity" / "layout.lock"
    with open(lock_path, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            return _sync_course(vault_root, moc_rel, move, courses, dry_run)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _sync_course(vault_root: Path, moc_rel: str, move: bool, courses: Optional[List[Course]],
                 dry_run: bool) -> Dict[str, Any]:
    courses = courses if courses is not None else load_courses(vault_root)
    course = next((c for c in courses if c.moc_rel == moc_rel), None)
    if not course:
        return {"moc": moc_rel, "skipped": "MOC senza Disciplina, senza moduli o cartella disciplina assente"}

    # Le cartelle dei moduli non si rinominano: se i moduli cambiano, si spostano le note e le cartelle
    # rimaste vuote vengono eliminate (rinominare per numero metterebbe note nel modulo sbagliato)
    moves: List[Tuple[str, str]] = []
    placements = load_placements(vault_root)
    if move:
        for title in course.note_titles:
            current = find_existing_note(vault_root, title)
            if not current or not current.startswith(course.discipline + "/"):
                continue
            pl = placement(vault_root, courses, title, course.discipline)
            # Ogni corso sistema le proprie note e quelle di base della sua materia
            if not pl or (pl[0] == "course" and pl[1] is not course):
                continue
            target = placement_path(pl, title)
            if current == target:
                placements[title.lower()] = target
                continue
            if not may_move(current, placements.get(title.lower()), courses, course.discipline):
                continue
            if (vault_root / target).exists():
                continue
            if dry_run:
                moves.append((current, target))
                continue
            (vault_root / target).parent.mkdir(parents=True, exist_ok=True)
            os.rename(vault_root / current, vault_root / target)
            placements[title.lower()] = target
            moves.append((current, target))
    if dry_run:
        return {"moc": moc_rel, "folder": course.folder, "modules": [m for m, _ in course.modules],
                "would_move": moves}
    # Le cartelle dei moduli nascono con la prima nota (vedi spostamenti e resolve_note_path)
    (vault_root / course.folder).mkdir(parents=True, exist_ok=True)
    save_placements(vault_root, placements)
    # Cartelle di modulo rimaste vuote dopo gli spostamenti
    for module, _ in course.modules:
        d = vault_root / course.folder / module
        if d.is_dir() and not any(x for x in d.iterdir() if x.name != ".DS_Store"):
            for x in d.iterdir():
                x.unlink()
            d.rmdir()

    if moves:
        with open(vault_root / MOVES_LOG, "a", encoding="utf-8") as fh:
            for src, dst in moves:
                fh.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "from": src, "to": dst},
                                    ensure_ascii=False) + "\n")
        # Lascia a Obsidian il tempo di registrare gli spostamenti prima di riscrivere l'ordine
        time.sleep(2)

    data = load_sorting(vault_root)
    if data is not None:
        apply_course_order(vault_root, course, data)
        save_sorting(vault_root, data)
    return {"moc": moc_rel, "folder": course.folder, "modules": len(course.modules),
            "moved": len(moves), "sorting_updated": data is not None}


def sync_for_note(vault_root: Path, title: str, discipline: str = "", moc_hint: str = "") -> Optional[Dict[str, Any]]:
    """Dopo la creazione/modifica di una nota: sincronizza il corso che la contiene."""
    courses = load_courses(vault_root)
    current = find_existing_note(vault_root, title) or ""
    course = owner_course(courses, title, discipline, moc_hint, current, vault_root=vault_root)
    if not course:
        return None
    return sync_course(vault_root, course.moc_rel, courses=courses)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault-root", default="")
    ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--sync", action="store_true")
    ap.add_argument("--sync-all", action="store_true")
    ap.add_argument("--title", default="")
    ap.add_argument("--discipline", default="")
    ap.add_argument("--moc", default="")
    ap.add_argument("--no-move", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    vault_root = Path(args.vault_root).resolve() if args.vault_root else resolve_vault_root()

    if args.resolve:
        print(resolve_note_path(vault_root, args.title, args.discipline, args.moc))
        return 0
    if args.sync:
        print(json.dumps(sync_course(vault_root, args.moc, move=not args.no_move, dry_run=args.dry_run), ensure_ascii=False))
        return 0
    if args.sync_all:
        courses = load_courses(vault_root)
        for c in courses:
            print(json.dumps(sync_course(vault_root, c.moc_rel, move=not args.no_move, courses=courses,
                                         dry_run=args.dry_run), ensure_ascii=False, indent=1))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
