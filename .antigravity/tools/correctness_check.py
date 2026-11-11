#!/usr/bin/env python3
"""
correctness_check.py — Verifica di correttezza di una nota con un secondo modello, via agy (quota di Antigravity).

La verifica di esclusività (orchestrator.py) controlla che la nota dica solo ciò che c'è nelle fonti;
questa controlla che ciò che dice sia vero: definizioni, enunciati, dimostrazioni, calcoli, esempi.
Le note non vengono rilette a mano e Sinapsi le usa come base di studio, quindi un errore di Gemini
verrebbe imparato come vero.

Una sola chiamata sulla nota intera: il revisore segnala i problemi e, per gli errori certi, scrive già
le modifiche find/replace. Con --fix (sempre attivo nella pipeline) le modifiche vengono applicate e una
seconda chiamata, breve e con un modello più leggero, controlla solo i brani cambiati: le correzioni
bocciate vengono annullate e restano segnalate (backup in .antigravity/backups/). I dubbi non vengono
mai toccati. Prima erano fino a cinque chiamate sulla nota intera (verifica, correzione, riverifica, due giri). L'esito va nel frontmatter (Verifica: ok |
dubbi | errori, Verificata: data, Corretti: numero) e le segnalazioni rimaste in un callout subito
dopo il frontmatter, tra i commenti %% verifica-inizio %% e %% verifica-fine %%. Sinapsi legge entrambi.

Uso:
  python3 correctness_check.py "Matematica/Analisi 1/Numeri Reali.md"
  python3 correctness_check.py --folder Matematica --skip-verified --limit 10 --fix
  python3 correctness_check.py --moc "01 MOC's/Analisi 1 MOC.md" --skip-verified --recheck --fix
Modello: --model oppure la variabile ANTIGRAVITY_VERIFY_MODEL (default: gemini-3.8-flash-high, una chiamata per
verifica; `agy models` elenca gli altri). Prova del 2 novembre 2026 su Principio del Buon Ordinamento: Gemini
sulla nota intera trova l'errore vero; claude-opus-4-6-thinking lo manca sulla nota intera e lo trova solo
dividendola in parti (4 chiamate).
"""

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VAULT = Path(__file__).resolve().parents[2]
START, END = "%% verifica-inizio %%", "%% verifica-fine %%"
DEFAULT_MODEL = "gemini-3.8-flash-high"
RUNTIME_DIR = Path(os.environ.get("ANTIGRAVITY_RUNTIME_DIR") or "/tmp/antigravity_runtime")
BLOCK_RE = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\n*", re.S)
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)

EDIT = {"type": "object", "properties": {"find": {"type": "string"}, "replace": {"type": "string"}}, "required": ["find", "replace"]}
SCHEMA = {
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "quote": {"type": "string"},
                    "problem": {"type": "string"},
                    "correction": {"type": "string"},
                    "severity": {"type": "string", "enum": ["errore", "dubbio"]},
                    "edits": {"type": "array", "items": EDIT},
                },
                "required": ["quote", "problem", "correction", "severity", "edits"],
            },
        }
    },
    "required": ["issues"],
}

PROMPT = """Sei un revisore matematico e scientifico. La nota qui sotto è stata scritta da un altro modello AI. Uno studente universitario la userà come base di studio senza rileggerla: ogni errore che ti sfugge lo imparerà come vero.

Controlla la CORRETTEZZA:
- definizioni (condizioni mancanti, di troppo o sbagliate);
- enunciati (ipotesi mancanti o superflue, tesi sbagliate, quantificatori invertiti);
- dimostrazioni (passaggi non validi, ragionamenti circolari, casi dimenticati, uso di un risultato senza averne verificato le ipotesi);
- calcoli, esempi e controesempi (un controesempio deve davvero violare ciò che dice di violare);
- affermazioni fattuali (nomi, date, attribuzioni, dati).

NON segnalare stile, formattazione, completezza, scelte didattiche, livello di dettaglio, wikilink o frontmatter.
Segnala solo ciò che sapresti giustificare. Per ogni problema:
- "quote": il testo ESATTO della nota dove si trova (al massimo 300 caratteri);
- "problem": cosa non va e perché, in italiano, in modo verificabile e breve;
- "correction": la versione corretta, in breve;
- "severity": "errore" se sei certo che sia sbagliato, "dubbio" se è sospetto ma non ne sei certo;
- "edits": solo per gli errori (per i dubbi lascia []), le modifiche che lo correggono nella nota. Ogni modifica è "find" (brano copiato ESATTAMENTE dalla nota, carattere per carattere, abbastanza lungo da comparire una volta sola) e "replace" (il brano corretto). Correggi anche le altre occorrenze dello stesso errore (flashcard, quiz, tabelle, riepiloghi). Cambia il minimo indispensabile, mantieni lingua, tono e formattazione (LaTeX con $...$ e $$...$$, callout con "> " a inizio riga, wikilink [[...]]); se serve un passaggio nuovo in una dimostrazione, scrivilo nello stile dei passaggi vicini.
Se non trovi problemi restituisci "issues": [].

=== NOTA ===
{note}
=== FINE NOTA ==="""

CHECK_MODEL = "gemini-3.8-flash-medium"
CHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"n": {"type": "integer"}, "ok": {"type": "boolean"}, "reason": {"type": "string"}},
                "required": ["n", "ok", "reason"],
            },
        }
    },
    "required": ["results"],
}

CHECK_PROMPT = """Sei un revisore matematico. In una nota di studio sono state fatte le correzioni elencate sotto. Per ognuna controlla che il testo nuovo sia matematicamente corretto, risolva il problema indicato e non introduca errori nuovi. Rispondi con "results": per ogni correzione il suo numero "n", "ok" (true se va bene) e "reason" (breve, in italiano).

{fixes}"""

def strip_block(text: str) -> str:
    return BLOCK_RE.sub("", text)


def is_moc(text: str) -> bool:
    m = FRONTMATTER_RE.match(text)
    return bool(m and re.search(r"(?m)^Type:\s*\n\s*-\s*MOC\s*$", m.group(1)))


def is_verified(text: str) -> bool:
    m = FRONTMATTER_RE.match(text)
    return bool(m and re.search(r"(?m)^Verifica:", m.group(1)))


NO_TOOLS = "\n\nLavora solo sul testo di questo messaggio: non leggere file, non usare strumenti, non cercare sul web. Rispondi direttamente con il JSON."


QUOTA_RE = re.compile(r"quota reached|RESOURCE_EXHAUSTED", re.I)
RESET_RE = re.compile(r"Resets in\s*(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+)s)?")
MAX_QUOTA_WAIT = 6 * 3600


class QuotaExhausted(Exception):
    def __init__(self, wait: int):
        super().__init__(f"quota di Antigravity esaurita, riparte tra {wait // 60} min")
        self.wait = wait


def quota_wait(text: str) -> Optional[int]:
    """Secondi fino al reset della quota se agy dice che è esaurita, altrimenti None."""
    if not QUOTA_RE.search(text):
        return None
    m = RESET_RE.search(text)
    h, mi, se = (int(g or 0) for g in m.groups()) if m else (0, 30, 0)
    return h * 3600 + mi * 60 + se


def ask_agy(prompt: str, schema: Dict[str, Any], model: str = "", timeout_sec: int = 600, attempts: int = 2) -> Optional[Dict[str, Any]]:
    """Come ask_agy_once, ma riprova quando agy torna vuoto (strumento negato in headless, timeout a metà turno)
    e, a quota esaurita, aspetta il reset invece di far fallire le note che restano."""
    n, waited = 0, 0
    while n < attempts:
        try:
            out = ask_agy_once(prompt + NO_TOOLS, schema, model=model, timeout_sec=timeout_sec)
        except QuotaExhausted as e:
            if waited + e.wait > MAX_QUOTA_WAIT:
                sys.stderr.write(f"[Correttezza] {e}: troppo lontano, mi fermo\n")
                return None
            sys.stderr.write(f"[Correttezza] {e}: aspetto\n")
            time.sleep(e.wait + 30)
            waited += e.wait + 30
            continue
        if out is not None:
            return out
        n += 1
        if n < attempts:
            sys.stderr.write(f"[Correttezza] Nuovo tentativo ({n + 1}/{attempts})\n")
    return None


def ask_agy_once(prompt: str, schema: Dict[str, Any], model: str = "", timeout_sec: int = 600) -> Optional[Dict[str, Any]]:
    """agy in print mode con output vincolato allo schema (come orchestrator.run_agy_structured), quota di Antigravity."""
    agy = shutil.which("agy") or str(Path.home() / ".local/bin/agy")
    cmd = [
        agy, "-p", prompt,
        "--output-format", "json",
        "--json-schema", json.dumps(schema),
        "--print-timeout", f"{timeout_sec}s",
        "--model", model or DEFAULT_MODEL,
    ]
    try:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        # Cartella neutra: il revisore lavora solo sul testo del prompt, non sul vault
        # Gruppo di processi proprio: agy è un wrapper, e al timeout va fermato anche il figlio, che altrimenti
        # resta vivo per ore a consumare quota
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(RUNTIME_DIR), start_new_session=True)
    except OSError as e:
        sys.stderr.write(f"[Correttezza] agy non parte: {e}\n")
        return None
    try:
        stdout, stderr = proc.communicate(timeout=timeout_sec + 30)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        sys.stderr.write(f"[Correttezza] agy non ha risposto in {timeout_sec}s\n")
        return None
    out = (stdout or "").strip()
    for candidate in [out] + [l for l in reversed(out.splitlines()) if l.strip().startswith("{")]:
        try:
            data = json.loads(candidate)
        except Exception:
            continue
        if isinstance(data.get("structured_output"), dict):
            return data["structured_output"]
        if isinstance(data.get("response"), str):
            try:
                return json.loads(data["response"])
            except Exception:
                pass
    wait = quota_wait(out + (stderr or ""))
    if wait is not None:
        raise QuotaExhausted(wait)
    sys.stderr.write(f"[Correttezza] Output di agy non interpretabile: {out[:300]} {(stderr or '')[:300]}\n")
    return None


def find_issues(note: str, model: str = "") -> Optional[List[Dict[str, Any]]]:
    out = ask_agy(PROMPT.replace("{note}", note), SCHEMA, model=model)
    if out is None or not isinstance(out.get("issues"), list):
        return None
    return [i for i in out["issues"] if isinstance(i, dict) and str(i.get("problem", "")).strip()]


def clean_edit(edit: Any) -> Optional[Tuple[str, str]]:
    if not isinstance(edit, dict):
        return None
    find, replace = str(edit.get("find", "")), str(edit.get("replace", ""))
    # Nei callout il modello tende a ripetere il "> " iniziale che "find" non include: diventerebbe un callout annidato
    if replace.startswith("> ") and not find.startswith(">"):
        replace = replace[2:]
    return (find, replace) if find and find != replace else None


def locate(note: str, find: str) -> Optional[Tuple[int, int]]:
    """Dove sta "find" nella nota, se compare una sola volta. Se il modello lo ha copiato su più righe di un
    callout senza i "> " iniziali (o con spazi diversi), lo cerca anche ignorando spazi, a capo e "> "."""
    if note.count(find) == 1:
        i = note.index(find)
        return i, i + len(find)
    tokens = [re.escape(t) for t in re.split(r"(?:\s|(?<![^\s])>)+", find.strip()) if t]
    if not tokens:
        return None
    matches = list(re.finditer(r"(?:\s|>)+".join(tokens), note))
    return (matches[0].start(), matches[0].end()) if len(matches) == 1 else None


def apply_edits(note: str, issue: Dict[str, Any]) -> Optional[Tuple[str, List[Tuple[str, str]]]]:
    """Tutte le modifiche di un errore o nessuna: ogni "find" deve comparire una sola volta."""
    edits = [e for e in (clean_edit(x) for x in issue.get("edits") or []) if e]
    if not edits:
        return None
    applied = []
    for find, replace in edits:
        span = locate(note, find)
        if not span:
            return None
        old = note[span[0]:span[1]]
        # Dentro un callout ogni riga nuova deve ricominciare con "> "
        if "\n>" in old:
            replace = re.sub(r"\n(?!>)", "\n> ", replace)
        note = note[:span[0]] + replace + note[span[1]:]
        applied.append((old, replace))
    return note, applied


def check_fixes(fixed: List[Dict[str, Any]]) -> Optional[set]:
    """Numeri (da 1) delle correzioni che il controllo boccia; None se il controllo non risponde."""
    listed = "\n\n".join(
        f"{n}. Problema: {i.get('problem', '')}\n"
        + "\n".join(f"Prima: «{f}»\nDopo: «{r}»" for f, r in i["applied"])
        for n, i in enumerate(fixed, 1)
    )
    out = ask_agy(CHECK_PROMPT.replace("{fixes}", listed), CHECK_SCHEMA, model=CHECK_MODEL, timeout_sec=300)
    if out is None or not isinstance(out.get("results"), list):
        return None
    return {r.get("n") for r in out["results"] if isinstance(r, dict) and r.get("ok") is False}


def backup(path: Path, text: str) -> None:
    """Stessa convenzione di orchestrator.create_target_note_backup."""
    folder = VAULT / ".antigravity" / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r'[\\/*?:"<>| ]', "_", path.stem)
    (folder / f"{time.strftime('%Y%m%d_%H%M%S')}_{stem}{path.suffix}").write_text(text, encoding="utf-8")


ANKI_LOCK = threading.Lock()


def resync_anki(path: Path) -> None:
    """Le flashcard sono già state mandate ad Anki prima della verifica: aggiornale (se Anki è aperto).
    Una nota alla volta anche quando le verifiche girano in parallelo."""
    tool = Path(__file__).with_name("anki_sync.py")
    if tool.exists():
        with ANKI_LOCK:
            subprocess.run([sys.executable, str(tool), str(path), "--quiet"], capture_output=True, timeout=30, check=False)


def quote_lines(text: str) -> str:
    return "\n".join("> " + line if line.strip() else ">" for line in text.strip().splitlines())


def render_block(issues: List[Dict[str, Any]]) -> str:
    errors = sum(1 for i in issues if i.get("severity") == "errore")
    doubts = len(issues) - errors
    counts = ", ".join(p for p in [
        f"{errors} {'errore' if errors == 1 else 'errori'}" if errors else "",
        f"{doubts} {'dubbio' if doubts == 1 else 'dubbi'}" if doubts else "",
    ] if p)
    parts = [
        START,
        f"> [!warning] Verifica di correttezza: {counts}",
        "> Segnalazioni di un secondo modello da controllare: in questi punti il testo della nota non è stato corretto.",
    ]
    for n, i in enumerate(issues, 1):
        label = "Errore" if i.get("severity") == "errore" else "Dubbio"
        parts += [
            ">",
            f"> **{n}. {label}** in: «{' '.join(str(i.get('quote', '')).split())}»",
            quote_lines(str(i.get("problem", ""))),
            ">",
            quote_lines("*Correzione:* " + str(i.get("correction", "")).strip()),
        ]
    parts.append(END)
    return "\n".join(parts) + "\n\n"


def apply_result(text: str, issues: List[Dict[str, Any]], fixed: int = 0) -> str:
    """Scrive esito e segnalazioni nella nota (senza toccare il resto del testo)."""
    verdict = "errori" if any(i.get("severity") == "errore" for i in issues) else ("dubbi" if issues else "ok")
    body = strip_block(text)
    fields = f"Verifica: {verdict}\nVerificata: {time.strftime('%Y-%m-%d')}" + (f"\nCorretti: {fixed}" if fixed else "")
    m = FRONTMATTER_RE.match(body)
    if m:
        fm = re.sub(r"(?m)^(Verifica|Verificata|Corretti):.*\n?", "", m.group(1)).rstrip("\n")
        head, rest = f"---\n{fm}\n{fields}\n---\n", body[m.end():]
    else:
        head, rest = f"---\n{fields}\n---\n", body
    rest = rest.lstrip("\n")
    return head + "\n" + (render_block(issues) if issues else "") + rest


def check_note(path: Path, model: str = "", fix: bool = False) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if is_moc(text):
        return {"status": "skipped", "reason": "MOC"}
    original = strip_block(text)
    issues = find_issues(original, model=model)
    if issues is None:
        return {"status": "error"}
    note, fixed, remaining = original, [], []
    for issue in issues:
        done = apply_edits(note, issue) if fix and issue.get("severity") == "errore" else None
        if done:
            note, issue["applied"] = done
            fixed.append(issue)
        else:
            remaining.append(issue)
    if fixed:
        rejected = check_fixes(fixed)
        # Senza conferma non si tocca niente: meglio un errore segnalato che una correzione sbagliata
        if rejected is None:
            rejected = set(range(1, len(fixed) + 1))
        if rejected:
            note = original
            kept = [i for n, i in enumerate(fixed, 1) if n not in rejected]
            remaining += [i for n, i in enumerate(fixed, 1) if n in rejected]
            fixed = []
            for issue in kept:
                done = apply_edits(note, issue)
                if done:
                    note = done[0]
                    fixed.append(issue)
                else:
                    remaining.append(issue)
    # La nota potrebbe essere cambiata durante la verifica (minuti): riscrivi solo se è ancora quella
    if path.read_text(encoding="utf-8", errors="replace") != text:
        return {"status": "error", "reason": "nota modificata durante la verifica"}
    if fixed:
        backup(path, text)
    path.write_text(apply_result(note, remaining, len(fixed)), encoding="utf-8")
    if fixed:
        try:
            resync_anki(path)
        except Exception:
            pass
    errors = sum(1 for i in remaining if i.get("severity") == "errore")
    return {"status": "checked", "errors": errors, "doubts": len(remaining) - errors, "fixed": len(fixed)}


def summary(report: Dict[str, Any]) -> str:
    if report["status"] == "skipped":
        return ""
    if report["status"] == "error":
        return f"⚠️ Verifica di correttezza non completata{': ' + report['reason'] if report.get('reason') else ''}"
    fixed = f"{report['fixed']} correzioni applicate, " if report.get("fixed") else ""
    if not report["errors"] and not report["doubts"]:
        return f"🔎 Correttezza verificata: {fixed}nessun problema rimasto"
    return f"🔎 Correttezza: {fixed}{report['errors']} errori e {report['doubts']} dubbi rimasti, segnalati nella nota"


def notes_of_moc(moc: Path) -> List[Path]:
    """Note esistenti citate nel corpo del MOC, nell'ordine del MOC (senza le sezioni di raccordo verso altri MOC)."""
    import moc_batch
    by_name: Dict[str, Path] = {}
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.lower().endswith(".md"):
                by_name.setdefault(f[:-3].lower(), Path(root) / f)
    links = moc_batch.extract_ordered_links(moc.read_text(encoding="utf-8", errors="replace"))
    return [by_name[t.lower()] for t in links if t.lower() in by_name]


def main() -> int:
    ap = argparse.ArgumentParser(description="Verifica di correttezza delle note (agy).")
    ap.add_argument("notes", nargs="*", help="Note da verificare (percorsi assoluti o relativi al vault)")
    ap.add_argument("--folder", help="Verifica tutte le note .md della cartella (relativa al vault)")
    ap.add_argument("--moc", help="Verifica tutte le note collegate a questo MOC (percorso relativo al vault)")
    ap.add_argument("--skip-verified", action="store_true", help="Salta le note che hanno già il campo Verifica")
    ap.add_argument("--limit", type=int, default=0, help="Numero massimo di note da verificare")
    ap.add_argument("--fix", action="store_true", help="Correggi gli errori certi (con backup) e riverifica")
    ap.add_argument("--recheck", action="store_true", help="Con --skip-verified, riprendi anche le note con Verifica: errori")
    ap.add_argument("--parallel", type=int, default=3, help="Quante note verificare insieme (consuma la quota più in fretta)")
    ap.add_argument("--model", default=os.environ.get("ANTIGRAVITY_VERIFY_MODEL", ""))
    args = ap.parse_args()

    paths = [p if p.is_absolute() else VAULT / p for p in map(Path, args.notes)]
    if args.folder:
        paths += sorted((VAULT / args.folder).rglob("*.md"))
    if args.moc:
        moc = Path(args.moc) if Path(args.moc).is_absolute() else VAULT / args.moc
        paths += [p for p in notes_of_moc(moc) if p not in paths]
    if args.skip_verified:
        keep = lambda t: not is_verified(t) or (args.recheck and re.search(r"(?m)^Verifica: errori", t))
        paths = [p for p in paths if keep(p.read_text(encoding="utf-8", errors="replace"))]
    if args.limit:
        paths = paths[: args.limit]

    # Più note insieme: ogni nota ha la sua istanza di agy, indipendente dalle altre
    def run(path: Path) -> Dict[str, Any]:
        try:
            return check_note(path, model=args.model, fix=args.fix)
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    failed = done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.parallel)) as pool:
        futures = {pool.submit(run, p): p for p in paths}
        for fut in concurrent.futures.as_completed(futures):
            path, report = futures[fut], fut.result()
            done += 1
            failed += report["status"] == "error"
            print(f"[{done}/{len(paths)}] {path.relative_to(VAULT) if path.is_relative_to(VAULT) else path}: {summary(report) or 'saltata (MOC)'}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
