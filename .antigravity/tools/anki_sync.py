#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anki_sync.py
============
Sincronizzatore Automatico tra Obsidian Vault e Anki tramite AnkiConnect.

Funzionalità Principali:
1. Connessione non bloccante ad AnkiConnect (porta 8765):
   - Se Anki è chiuso, non interrompe l'automazione ma stampa un avviso informativo gentile.
2. Generazione Automatica del Mazzo Gerarchico:
   - Mazzo: Obsidian::<Polo>::<Disciplina>::<Titolo Nota>
   - Esempio: Obsidian::Università::Matematica::Numeri Interi Relativi
3. Conversione del LaTeX per il MathJax nativo di Anki:
   - Formule display: $$...$$ -> \\[...\\]
   - Formule inline:  $...$   -> \\(...\\)
4. Duplicazione Intelligente e Prevenzione Doppioni:
   - Flashcard create con modello "Basic" (Fronte e Retro).
   - Quiz a scelta multipla con Domanda + 4 Opzioni sul Fronte e Risposta Corretta + Spiegazione sul Retro.
   - Opzioni anti-duplicato per deck ("duplicateScope": "deck").
5. Supporto per Singola Nota o Vault Intero (--all).
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ANKI_CONNECT_URL = "http://127.0.0.1:8765"
DEFAULT_CONNECT_TIMEOUT = 2.0


def resolve_vault_root() -> Path:
    """Risolve la radice del vault Obsidian."""
    curr = Path(__file__).resolve().parent
    for parent in [curr] + list(curr.parents):
        if (parent / ".obsidian").is_dir() or (parent / ".antigravity").is_dir():
            return parent
    return Path.cwd()


# ==============================================================================
# 1. COMUNICAZIONE CON ANKICONNECT
# ==============================================================================

def invoke_anki(action: str, timeout: float = DEFAULT_CONNECT_TIMEOUT, **params: Any) -> Dict[str, Any]:
    """Invia una richiesta JSON-RPC ad AnkiConnect."""
    payload = json.dumps({"action": action, "version": 6, "params": params}).encode("utf-8")
    req = urllib.request.Request(
        ANKI_CONNECT_URL,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if len(data) != 2:
                raise ValueError("Risposta AnkiConnect non valida: mancano campi obbligatori.")
            if "error" not in data:
                raise ValueError("Risposta AnkiConnect non valida: campo 'error' assente.")
            if data["error"] is not None:
                raise RuntimeError(str(data["error"]))
            return data
    except urllib.error.URLError as e:
        raise ConnectionError(f"Impossibile connettersi ad AnkiConnect ({ANKI_CONNECT_URL}): {e.reason}")
    except Exception as e:
        raise ConnectionError(f"Errore di comunicazione con AnkiConnect: {e}")


def is_anki_running(timeout: float = 1.5) -> bool:
    """Verifica rapida se Anki è attivo e AnkiConnect risponde."""
    try:
        res = invoke_anki("version", timeout=timeout)
        return res.get("result") is not None
    except Exception:
        return False


# ==============================================================================
# 2. TRASFORMAZIONE TESTO E CONVERSIONE LATEX PER MATHJAX
# ==============================================================================

def convert_latex_for_anki(text: str) -> str:
    """
    Converte le formule LaTeX per il motore MathJax nativo di Anki.
    $$...$$ -> \\[...\\]
    $...$   -> \\(...\\)
    """
    if not text:
        return ""
    # 1. Display Math: $$...$$ -> \[...\]
    display_pattern = re.compile(r"\$\$([\s\S]*?)\$\$")
    text = display_pattern.sub(r"\\[\1\\]", text)

    # 2. Inline Math: $...$ -> \(...\) (evitando match su simboli dollaro isolati)
    inline_pattern = re.compile(r"(?<!\$)\$([^\$\n]+?)\$(?!\$)")
    text = inline_pattern.sub(r"\\(\1\\)", text)

    return text


def markdown_to_anki_html(text: str) -> str:
    """
    Converte costrutti Markdown standard e Wikilink in HTML pulito per Anki.
    Preserva i delimitatori MathJax \\[...\\] e \\(...\\).
    """
    if not text:
        return ""

    # Rimozione o risoluzione dei Wikilink: [[Nota#Paragrafo|Alias]] -> Alias
    text = re.sub(r"\[\[(?:[^\]|]+)\|([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)

    # Grassetto e corsivo
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)

    # Codice inline
    text = re.sub(r"`([^`]+)`", r"<code style='background:#f0f0f0;padding:2px 4px;border-radius:3px;'>\1</code>", text)

    # Liste puntate semplici
    text = re.sub(r"^\s*-\s+(.+)$", r"• \1<br>", text, flags=re.MULTILINE)

    # Newlines e paragrafi
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{2,}", r"<br><br>", text)
    text = text.replace("\n", "<br>")

    return text.strip()


def sanitize_tag(tag: str) -> str:
    """Pulisce una stringa per renderla un tag Anki valido."""
    tag = tag.strip().lower()
    tag = re.sub(r"[^\w\-]", "-", tag)
    tag = re.sub(r"-+", "-", tag).strip("-")
    return tag or "obsidian"


# ==============================================================================
# 3. PARSING METADATI FRONTMATTER E DATI DI STUDIO
# ==============================================================================

def parse_frontmatter(content: str) -> Dict[str, str]:
    """Estrae i metadati YAML di primo livello da una nota Obsidian."""
    fm: Dict[str, str] = {}
    m = re.match(r"^---\s*\n([\s\S]*?)\n---\s*(?:\n|$)", content)
    if not m:
        return fm

    yaml_block = m.group(1)
    for line in yaml_block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            key = k.strip().lower()
            val = v.strip().strip("\"'").strip()
            # Gestione tag con cancelletto
            if val.startswith("#"):
                val = val.lstrip("#")
            fm[key] = val
    return fm


def extract_study_block(content: str) -> Optional[str]:
    """Individua il blocco delimitato %%STUDY_DATA ... %% o <!-- STUDY_DATA ... -->."""
    m = re.search(r"(?:%%|<!--\s*)STUDY_DATA([\s\S]*?)(?:%%|\s*-->)", content, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def parse_study_data(raw_block: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Esegue il parsing dei dati di studio supportando due formati:
    1. Formato JSON (auto-sanitizzato per backslash LaTeX).
    2. Formato Markdown con sezioni native (### FLASHCARD e ### QUIZ).
    """
    flashcards: List[Dict[str, Any]] = []
    quizzes: List[Dict[str, Any]] = []

    if not raw_block:
        return flashcards, quizzes

    # Rimuove eventuali prefissi di callout '>' se il blocco è dentro un callout Obsidian
    clean_lines = [re.sub(r"^\s*>\s?", "", line) for line in raw_block.splitlines()]
    raw_block = "\n".join(clean_lines).strip()

    # Modalità 1: Formato JSON
    if raw_block.startswith("{"):
        try:
            # Sanitizza i backslash isolati che romperebbero JSON.parse con il LaTeX
            # Trasforma \ non seguiti da escape JSON validi in \\
            sanitized = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', raw_block)
            data = json.loads(sanitized)
            for idx, item in enumerate(data.get("flashcards", []), 1):
                q = (item.get("question") or "").strip()
                a = (item.get("answer") or "").strip()
                t = (item.get("title") or f"Carta {idx}").strip()
                if q and a:
                    flashcards.append({"id": idx, "title": t, "question": q, "answer": a})

            for idx, item in enumerate(data.get("quizzes", []), 1):
                q = (item.get("question") or "").strip()
                opts_raw = item.get("options", [])
                opts: List[Dict[str, str]] = []
                for o_idx, opt in enumerate(opts_raw):
                    if isinstance(opt, str):
                        m_opt = re.match(r"^([A-D])\)\s*(.*)$", opt.strip())
                        if m_opt:
                            opts.append({"key": m_opt.group(1).upper(), "text": m_opt.group(2).strip()})
                        else:
                            opts.append({"key": chr(65 + o_idx), "text": opt.strip()})
                    elif isinstance(opt, dict):
                        opts.append({
                            "key": str(opt.get("key", chr(65 + o_idx))).upper(),
                            "text": str(opt.get("text", "")).strip()
                        })
                correct = str(item.get("correct", "A")).strip().upper()
                exp = (item.get("explanation") or "").strip()
                t = (item.get("title") or f"Quiz {idx}").strip()
                if q and opts:
                    quizzes.append({
                        "id": idx,
                        "title": t,
                        "question": q,
                        "options": opts,
                        "correct": correct,
                        "explanation": exp
                    })
            return flashcards, quizzes
        except Exception:
            # Fallback al parser Markdown
            pass

    # Modalità 2: Formato Markdown nativo
    items = re.split(r"(?=###\s+(?:FLASHCARD|QUIZ))", raw_block, flags=re.IGNORECASE)
    for it in items:
        it = it.strip()
        if not it:
            continue

        if re.match(r"^###\s+FLASHCARD", it, re.IGNORECASE):
            h_m = re.match(r"^###\s+FLASHCARD\s*(?:\d*):?\s*(.*)$", it, re.IGNORECASE | re.MULTILINE)
            title = h_m.group(1).strip() if h_m else ""

            q_m = re.search(r"\*\*Q:\*\*\s*([\s\S]*?)(?=\*\*A:\*\*|$)", it, re.IGNORECASE)
            a_m = re.search(r"\*\*A:\*\*\s*([\s\S]*)$", it, re.IGNORECASE)

            question = q_m.group(1).strip() if q_m else ""
            answer = a_m.group(1).strip() if a_m else ""

            if question and answer:
                card_id = len(flashcards) + 1
                flashcards.append({
                    "id": card_id,
                    "title": title or f"Carta {card_id}",
                    "question": question,
                    "answer": answer
                })

        elif re.match(r"^###\s+QUIZ", it, re.IGNORECASE):
            h_m = re.match(r"^###\s+QUIZ\s*(?:\d*):?\s*(.*)$", it, re.IGNORECASE | re.MULTILINE)
            title = h_m.group(1).strip() if h_m else ""

            q_m = re.search(r"\*\*Q:\*\*\s*([\s\S]*?)(?=(?:^[-\s*]*[A-D]\)|\*\*CORRECT:))", it, re.IGNORECASE | re.MULTILINE)
            question = q_m.group(1).strip() if q_m else ""

            options: List[Dict[str, str]] = []
            for line in it.splitlines():
                line_str = line.strip()
                if line_str.startswith("**CORRECT:") or line_str.startswith("**EXPLANATION:") or line_str.startswith("**Q:"):
                    continue
                opt_m = re.match(r"^(?:-\s*\[\s*\]\s*|\*\*)?([A-D])[\).:\-]\s*\**\s*(.+)$", line_str, re.IGNORECASE)
                if opt_m:
                    options.append({
                        "key": opt_m.group(1).upper(),
                        "text": opt_m.group(2).strip()
                    })

            corr_m = re.search(r"\*\*CORRECT:\*\*\s*([A-D])", it, re.IGNORECASE)
            correct = corr_m.group(1).upper().strip() if corr_m else "A"

            exp_m = re.search(r"\*\*EXPLANATION:\*\*\s*([\s\S]*)$", it, re.IGNORECASE)
            explanation = exp_m.group(1).strip() if exp_m else ""

            if question and options:
                quiz_id = len(quizzes) + 1
                quizzes.append({
                    "id": quiz_id,
                    "title": title or f"Quiz {quiz_id}",
                    "question": question,
                    "options": options,
                    "correct": correct,
                    "explanation": explanation
                })

    return flashcards, quizzes


# ==============================================================================
# 4. SINCRONIZZAZIONE DIRETTA AD ANKI
# ==============================================================================

def sync_note_to_anki(
    file_path: Path,
    vault_root: Path,
    custom_deck: Optional[str] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Sincronizza una singola nota Obsidian con Anki.
    Restituisce un dizionario riassuntivo con esito e conteggi.
    """
    result_summary: Dict[str, Any] = {
        "file": str(file_path),
        "status": "skipped",
        "deck": "",
        "flashcards_count": 0,
        "quizzes_count": 0,
        "added_count": 0,
        "error": None
    }

    if not file_path.exists():
        result_summary["status"] = "error"
        result_summary["error"] = f"File non trovato: {file_path}"
        return result_summary

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        result_summary["status"] = "error"
        result_summary["error"] = f"Impossibile leggere il file: {e}"
        return result_summary

    raw_study_block = extract_study_block(content)
    if not raw_study_block:
        result_summary["status"] = "no_study_data"
        if verbose:
            print(f"ℹ️ Nessun blocco %%STUDY_DATA trovato in: {file_path.name}")
        return result_summary

    flashcards, quizzes = parse_study_data(raw_study_block)
    result_summary["flashcards_count"] = len(flashcards)
    result_summary["quizzes_count"] = len(quizzes)

    if not flashcards and not quizzes:
        result_summary["status"] = "empty_study_data"
        if verbose:
            print(f"ℹ️ Blocco STUDY_DATA presente ma vuoto o non interpretabile in: {file_path.name}")
        return result_summary

    # Risoluzione gerarchia del Mazzo Anki
    fm = parse_frontmatter(content)
    polo = fm.get("polo") or "Università"
    polo_clean = polo.strip().capitalize()
    disciplina = fm.get("disciplina") or "Generale"
    note_title = fm.get("title") or file_path.stem

    if custom_deck:
        deck_name = custom_deck
    else:
        deck_name = f"Obsidian::{polo_clean}::{disciplina}::{note_title}"
    result_summary["deck"] = deck_name

    # 1. Creazione / Assicurazione esistenza del Mazzo
    try:
        invoke_anki("createDeck", deck=deck_name)
    except Exception as e:
        result_summary["status"] = "error"
        result_summary["error"] = f"Impossibile creare o verificare il mazzo '{deck_name}': {e}"
        return result_summary

    # 2. Preparazione Note Anki
    tag_disc = sanitize_tag(disciplina)
    tag_polo = sanitize_tag(polo_clean)
    anki_notes: List[Dict[str, Any]] = []

    # A. Flashcard
    for f in flashcards:
        q_math = convert_latex_for_anki(f.get("question", ""))
        a_math = convert_latex_for_anki(f.get("answer", ""))
        title = f.get("title", f"Carta {f.get('id', '')}")

        front_html = f"<div style='font-size:1.15em;font-weight:600;margin-bottom:12px;color:#2c3e50;'>{title}</div>"
        front_html += f"<div>{markdown_to_anki_html(q_math)}</div>"

        back_html = f"<div style='font-size:1.05em;color:#27ae60;font-weight:600;margin-bottom:8px;'>Risposta Rigorosa:</div>"
        back_html += f"<div>{markdown_to_anki_html(a_math)}</div>"

        anki_notes.append({
            "deckName": deck_name,
            "modelName": "Basic",
            "fields": {
                "Front": front_html,
                "Back": back_html
            },
            "options": {
                "allowDuplicate": False,
                "duplicateScope": "deck",
                "duplicateScopeOptions": {
                    "deckName": deck_name,
                    "checkChildren": False
                }
            },
            "tags": ["obsidian-flashcard", tag_disc, tag_polo]
        })

    # B. Quiz a Scelta Multipla
    for q in quizzes:
        q_math = convert_latex_for_anki(q.get("question", ""))
        correct_key = q.get("correct", "A").strip().upper()
        title = q.get("title", f"Quiz {q.get('id', '')}")

        options_html = "<ol type='A' style='margin-top:14px;padding-left:20px;'>"
        for opt in q.get("options", []):
            opt_text_math = convert_latex_for_anki(opt.get("text", ""))
            opt_key = opt.get("key", "")
            options_html += f"<li style='margin-bottom:8px;'><b>{opt_key})</b> {markdown_to_anki_html(opt_text_math)}</li>"
        options_html += "</ol>"

        front_html = f"<div style='font-size:1.15em;font-weight:600;margin-bottom:12px;color:#2c3e50;'>[Quiz] {title}</div>"
        front_html += f"<div>{markdown_to_anki_html(q_math)}</div>"
        front_html += options_html

        exp_math = convert_latex_for_anki(q.get("explanation", ""))
        back_html = f"<div style='background:#e8f8f5;border-left:4px solid #2ecc71;padding:10px 14px;border-radius:4px;margin-bottom:12px;'>"
        back_html += f"<span style='font-size:1.1em;font-weight:bold;color:#27ae60;'>✅ Risposta Corretta: Opzione {correct_key}</span>"
        back_html += "</div>"
        if exp_math:
            back_html += f"<div style='margin-top:10px;'><b>💡 Spiegazione Rigorosa e Analisi Trappole:</b><br>{markdown_to_anki_html(exp_math)}</div>"

        anki_notes.append({
            "deckName": deck_name,
            "modelName": "Basic",
            "fields": {
                "Front": front_html,
                "Back": back_html
            },
            "options": {
                "allowDuplicate": False,
                "duplicateScope": "deck",
                "duplicateScopeOptions": {
                    "deckName": deck_name,
                    "checkChildren": False
                }
            },
            "tags": ["obsidian-quiz", tag_disc, tag_polo]
        })

    # 3. Invio cumulativo tramite AnkiConnect addNotes
    try:
        res = invoke_anki("addNotes", notes=anki_notes)
        created_ids = res.get("result", [])
        added_count = sum(1 for cid in created_ids if cid is not None)
        result_summary["status"] = "success"
        result_summary["added_count"] = added_count

        if verbose:
            print(f"✅ Sincronizzazione completata per '{note_title}':")
            print(f"   • Mazzo Anki:        {deck_name}")
            print(f"   • Flashcard trovate: {len(flashcards)}")
            print(f"   • Quiz trovati:      {len(quizzes)}")
            print(f"   • Note create/agg:   {added_count} (duplicati ignorati automaticamente)")
    except Exception as e:
        result_summary["status"] = "error"
        result_summary["error"] = f"Errore durante l'aggiunta delle note ad Anki: {e}"
        if verbose:
            sys.stderr.write(f"❌ Errore sincronizzazione Anki per '{note_title}': {e}\n")

    return result_summary


def sync_all_notes(vault_root: Path, verbose: bool = True) -> Dict[str, Any]:
    """Scansiona l'intero vault Obsidian e sincronizza ogni nota dotata di STUDY_DATA."""
    total_notes_scanned = 0
    total_notes_synced = 0
    total_cards = 0
    total_quizzes = 0
    total_added = 0

    ignored_dirs = {".obsidian", ".antigravity", ".git", "allegati", "templates", "Scripts"}

    for root, dirs, files in os.walk(vault_root):
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]
        for file in files:
            if not file.endswith(".md"):
                continue
            p = Path(root) / file
            total_notes_scanned += 1
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
                if "STUDY_DATA" in txt:
                    res = sync_note_to_anki(p, vault_root, verbose=False)
                    if res["status"] == "success":
                        total_notes_synced += 1
                        total_cards += res["flashcards_count"]
                        total_quizzes += res["quizzes_count"]
                        total_added += res["added_count"]
                        if verbose:
                            print(f"  + Sincronizzato: {p.relative_to(vault_root)} ({res['added_count']} create/agg)")
            except Exception:
                continue

    summary = {
        "scanned": total_notes_scanned,
        "synced": total_notes_synced,
        "flashcards": total_cards,
        "quizzes": total_quizzes,
        "added": total_added
    }
    if verbose:
        print("\n=======================================================")
        print(f"📊 RIEPILOGO SINCRONIZZAZIONE ANKI VAULT:")
        print(f"• Note esaminate:     {total_notes_scanned}")
        print(f"• Note con STUDY_DATA: {total_notes_synced}")
        print(f"• Flashcard totali:   {total_cards}")
        print(f"• Quiz totali:        {total_quizzes}")
        print(f"• Nuove note Anki:    {total_added}")
        print("=======================================================")
    return summary


# ==============================================================================
# 5. ENTRYPOINT CLI
# ==============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sincronizzatore automatico tra Obsidian Vault e Anki tramite AnkiConnect.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "note_path",
        nargs="?",
        default=None,
        help="Percorso relativo o assoluto della nota .md da sincronizzare."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scansiona l'intero vault e sincronizza tutte le note con blocco STUDY_DATA."
    )
    parser.add_argument(
        "--deck",
        type=str,
        default=None,
        help="Nome personalizzato del mazzo Anki di destinazione."
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Verifica unicamente se AnkiConnect è raggiungibile senza sincronizzare."
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Sopprime i messaggi informativi non critici."
    )

    args = parser.parse_args()
    vault_root = resolve_vault_root()

    # 1. Verifica disponibilità AnkiConnect
    anki_online = is_anki_running(timeout=DEFAULT_CONNECT_TIMEOUT)

    if args.check_only:
        if anki_online:
            print(f"✅ AnkiConnect è attivo e pronto ({ANKI_CONNECT_URL}).")
            return 0
        else:
            print(f"⚠️ AnkiConnect non è raggiungibile ({ANKI_CONNECT_URL}). Verifica che Anki sia aperto con il plugin AnkiConnect.")
            return 1

    if not anki_online:
        if not args.quiet:
            print("======================================================================")
            print("ℹ️  AVVISO ANKI: Anki non è attualmente in esecuzione sul Mac.")
            print(f"   (Porta 8765 su {ANKI_CONNECT_URL} non raggiungibile)")
            print("----------------------------------------------------------------------")
            print("• Nessun problema: la generazione e il salvataggio della nota proseguono regolarmente.")
            print("• Quando aprirai Anki, potrai sincronizzare con un solo clic premendo:")
            print("  [🔄 Sincronizza con Anki] direttamente dal pannello interattivo della nota.")
            print("======================================================================")
        return 0

    # 2. Esecuzione scansione totale vault
    if args.all:
        if not args.quiet:
            print(f"🚀 Avvio sincronizzazione massiva Anki per tutto il vault: {vault_root}")
        sync_all_notes(vault_root, verbose=not args.quiet)
        return 0

    # 3. Esecuzione singola nota
    if args.note_path:
        raw_p = Path(args.note_path)
        if raw_p.is_absolute():
            target_file = raw_p
        else:
            target_file = (vault_root / raw_p).resolve()

        if not target_file.exists():
            sys.stderr.write(f"❌ Errore: File specificato non trovato: {target_file}\n")
            return 1

        sync_note_to_anki(target_file, vault_root, custom_deck=args.deck, verbose=not args.quiet)
        return 0

    # Se nessun argomento specificato, mostra l'help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
