#!/usr/bin/env python3
"""
orchestrator.py
===============
Orchestratore finale avanzato del flusso Antigravity per Obsidian Vault.
Ottimizzato per Token, Velocità ed Estrazione Fonti ad Altissima Fedeltà.

Caratteristiche Architetturali:
1. Pre-Assembly SOLO delle Regole Statiche:
   - Unisce .antigravity/core-guidelines.md + .antigravity/disciplines/<disciplina>.md +
     .antigravity/snippets/<disciplina>_blueprint.md in un unico file:
     .antigravity/job-context/compiled-instructions.md
   - L'agente legge tutte le regole e gli esempi in un'unica operazione di lettura (zero token sprecati).
2. Esecuzione Ibrida e Sinergica delle Fonti (fast_source_extract.py):
   - YouTube: trascrizione istantanea in 0.3s con youtube-transcript-api (fallback yt-dlp)
     concorrente con claude-watch / FFmpeg per catturare i fotogrammi salienti in allegati/.
   - Web: estrazione Markdown pulito tramite trafilatura (fallback r.jina.ai).
   - PDF: estrazione testo e figure pagina per pagina con pdf_extract.py.
   - NotebookLM: estrazione o aggancio concettuale tramite CLI nlm.
3. Esecuzione Sequenziale Intelligente di PubMed:
   - Vietato il parallelismo cieco: prima si estrae il testo della fonte, poi si estraggono
     i termini anatomici/biochimici/scientifici specifici in inglese, e solo a quel punto
     si interroga pubmed_search.py con query mirate.
"""

import argparse
import concurrent.futures
import html
import json
import os
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Iniezione del PATH completo di macOS per ambienti grafici e terminali
EXTRA_PATHS = [
    "/opt/homebrew/bin",
    "/opt/homebrew/sbin",
    str(Path.home() / ".local/bin"),
    str(Path.home() / "Library/Python/3.14/bin"),
    "/Library/Frameworks/Python.framework/Versions/3.14/bin",
    "/usr/local/bin",
    "/usr/bin",
    "/bin",
    "/usr/sbin",
    "/sbin",
]
current_path = os.environ.get("PATH", "")
path_elements = [p for p in EXTRA_PATHS if p not in current_path.split(":")]
if path_elements:
    os.environ["PATH"] = ":".join(path_elements) + (":" + current_path if current_path else "")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# Cartella runtime isolata FUORI dal vault per non innescare il file watcher di Obsidian / Dataview
# ANTIGRAVITY_RUNTIME_DIR permette a più note di girare in parallelo (batch), ognuna col proprio runtime
RUNTIME_DIR = Path(os.environ.get("ANTIGRAVITY_RUNTIME_DIR") or "/tmp/antigravity_runtime")
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def resolve_vault_index_path(vault_root: Path) -> Path:
    """Restituisce il percorso dell'indice del vault, preferendo quello isolato in /tmp."""
    runtime_idx = RUNTIME_DIR / "vault-index.json"
    if runtime_idx.exists():
        return runtime_idx
    vault_idx = vault_root / ".antigravity" / "vault-index.json"
    return vault_idx if vault_idx.exists() else runtime_idx

# Mappa delle 20 Macro-Discipline per normalizzazione degli Slug
DISCIPLINE_SLUG_MAP = {
    "Matematica": "matematica",
    "Informatica": "informatica",
    "Fisica": "fisica",
    "Intelligenza Artificiale": "intelligenza-artificiale",
    "Neuroscienze": "neuroscienze",
    "Biologia": "biologia",
    "Bodybuilding": "bodybuilding",
    "Nutrizione e Salute": "nutrizione-e-salute",
    "Chimica": "chimica",
    "Droghe": "droghe",
    "Tecnologia ed Elettronica": "tecnologia-ed-elettronica",
    "Musica e Industria Musicale": "musica-e-industria-musicale",
    "Arte e Storia dell'Arte": "arte-e-storia-dellarte",
    "Filosofia": "filosofia",
    "Letteratura": "letteratura",
    "Analisi Narrativa": "analisi-narrativa",
    "Storia": "storia",
    "Politica e Geopolitica": "politica-e-geopolitica",
    "Economia e Finanza": "economia-e-finanza",
    "Psicologia": "psicologia"
}

# Dizionario Termini Scientifici Bilingue (Italiano -> Termini Medici/Biologici Inglesi per PubMed)
SCIENTIFIC_TERM_DETECTORS = {
    "Bodybuilding": [
        (r"\b(?:bicipit[ei]|bicipite brachiale)\b", "biceps brachii"),
        (r"\b(?:brachial[ei])\b", "brachialis"),
        (r"\b(?:brachioradial[ei])\b", "brachioradialis"),
        (r"\b(?:tricipit[ei])\b", "triceps brachii"),
        (r"\b(?:quadricipit[ei])\b", "quadriceps"),
        (r"\b(?:femorali|ischiocrurali|hamstring)\b", "hamstrings"),
        (r"\b(?:pettoral[ei]|gran pettorale)\b", "pectoralis major"),
        (r"\b(?:dorsal[ei]|gran dorsale)\b", "latissimus dorsi"),
        (r"\b(?:deltoid[ei])\b", "deltoid"),
        (r"\b(?:ipertrofia|hypertrophy)\b", "muscle hypertrophy"),
        (r"\b(?:tensione meccanica|mechanical tension)\b", "mechanical tension"),
        (r"\b(?:stretch[- ]mediated|allungamento|lengthened)\b", "stretch-mediated hypertrophy"),
        (r"\b(?:parziali|lengthened partials)\b", "lengthened partials"),
        (r"\b(?:braccio di leva|moment arm)\b", "internal moment arm"),
        (r"\b(?:insufficienza attiva)\b", "active insufficiency"),
        (r"\b(?:sintesi proteica|mps)\b", "muscle protein synthesis"),
        (r"\b(?:semg|elettromiografia)\b", "surface electromyography sEMG"),
        (r"\b(?:rir|cedimento|failure)\b", "resistance training to failure")
    ],
    "Nutrizione e Salute": [
        (r"\b(?:sintesi proteica|mps)\b", "muscle protein synthesis"),
        (r"\b(?:leucina|leucine|soglia leucinica)\b", "leucine threshold"),
        (r"\b(?:mtorc?1?)\b", "mTORC1 activation"),
        (r"\b(?:sensibilità insulinica|insulina)\b", "insulin sensitivity"),
        (r"\b(?:indice glicemico|carico glicemico)\b", "glycemic response"),
        (r"\b(?:flessibilità metabolica)\b", "metabolic flexibility"),
        (r"\b(?:chetosi|chetoni)\b", "ketosis ketogenic"),
        (r"\b(?:deficit calorico|bilancio energetico)\b", "energy balance caloric deficit"),
        (r"\b(?:creatina|creatine)\b", "creatine monohydrate"),
        (r"\b(?:omega[- ]3|acidi grassi)\b", "omega-3 fatty acids")
    ],
    "Droghe": [
        (r"\b(?:mdma|ecstasy)\b", "MDMA 3,4-methylenedioxymethamphetamine"),
        (r"\b(?:psilocibina|psilocina|funghi)\b", "psilocybin psilocin"),
        (r"\b(?:cocaina)\b", "cocaine dopamine transporter"),
        (r"\b(?:serotonina|sert|5[- ]ht)\b", "serotonin transporter SERT"),
        (r"\b(?:dopamina|dat)\b", "dopamine transporter DAT"),
        (r"\b(?:5[- ]ht2a)\b", "5-HT2A receptor"),
        (r"\b(?:vmat[- ]?2)\b", "vesicular monoamine transporter VMAT2"),
        (r"\b(?:farmacocinetica|biodisponibilità)\b", "pharmacokinetics bioavailability"),
        (r"\b(?:neurotossicità|danno assonale)\b", "neurotoxicity axonal"),
        (r"\b(?:downregulation|tolleranza)\b", "receptor downregulation tolerance")
    ],
    "Neuroscienze": [
        (r"\b(?:potenziale d'azione|action potential)\b", "action potential"),
        (r"\b(?:potenziale di membrana|riposo)\b", "resting membrane potential"),
        (r"\b(?:sinapsi|trasmissione sinaptica)\b", "synaptic transmission"),
        (r"\b(?:plasticità|ltp|potenziamento)\b", "synaptic plasticity LTP"),
        (r"\b(?:gaba|inibizione)\b", "GABAergic neurotransmission"),
        (r"\b(?:glutammato|nmda|ampa)\b", "glutamate NMDA receptor"),
        (r"\b(?:canali voltaggio[- ]dipendenti)\b", "voltage-gated ion channels"),
        (r"\b(?:fmri|risonanza magnetica)\b", "functional MRI neuroimaging")
    ],
    "Biologia": [
        (r"\b(?:dna|replicazione)\b", "DNA replication polymerase"),
        (r"\b(?:trascrizione|mrna|rna)\b", "mRNA transcription RNA polymerase"),
        (r"\b(?:traduzione|ribosom[ei])\b", "ribosomal translation protein synthesis"),
        (r"\b(?:espressione genica)\b", "gene expression regulation"),
        (r"\b(?:glicolisi|ciclo di krebs)\b", "glycolysis Krebs cycle"),
        (r"\b(?:fosforilazione ossidativa|mitocondri)\b", "oxidative phosphorylation ATP synthase"),
        (r"\b(?:crispr|editing genomico)\b", "CRISPR-Cas9 gene editing")
    ],
    "Psicologia": [
        (r"\b(?:dissonanza cognitiva|festinger)\b", "cognitive dissonance"),
        (r"\b(?:bias cognitivi|euristiche)\b", "cognitive bias heuristics"),
        (r"\b(?:teoria del prospetto|kahneman)\b", "prospect theory Kahneman"),
        (r"\b(?:meccanismi di difesa|io)\b", "defense mechanisms ego"),
        (r"\b(?:condizionamento operante|skinner)\b", "operant conditioning reinforcement"),
        (r"\b(?:attaccamento|bowlby)\b", "attachment theory")
    ]
}


def resolve_vault_root() -> Path:
    """Risolve la directory radice dell'Obsidian Vault a partire dallo script."""
    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        if (parent / ".obsidian").exists() or (parent / ".antigravity").exists():
            return parent
    return script_path.parents[2]


PHASE_BY_STEP = {1: "prep", 2: "sources", 3: "context", 4: "context", 5: "writing", 6: "final"}


def progress_reporter(vault_root: Path, percent: int, step_number: int, message: str, phase: str,
                      target_file: str, unit: str = "risposte"):
    """Callback per query_nlm_parallel: aggiorna job-status.json a ogni risposta ricevuta."""
    def report(done: int, total: int) -> None:
        update_status(
            vault_root=vault_root, percent=percent, step_number=step_number, total_steps=6,
            message=message, detail=f"{done} di {total} {unit} ricevute da NotebookLM",
            status="running", target_file=target_file, phase=phase,
            progress={"done": done, "total": total, "unit": unit},
        )
    return report


def update_status(
    vault_root: Path,
    percent: int,
    step_number: int,
    total_steps: int = 6,
    message: str = "",
    detail: str = "",
    status: str = "running",
    target_file: str = "",
    error: Optional[str] = None,
    phase: str = "",
    progress: Optional[Dict[str, Any]] = None,
) -> None:
    """
    `phase` identifica la fase reale mostrata dall'HUD (prep, sources, context, writing, verify, final);
    se vuota si ricava dallo step. `progress` = {"done", "total", "unit"} quando la fase è misurabile.
    Aggiorna atomicamente /tmp/antigravity_runtime/job-status.json per il tracking in tempo reale
    della Loading Bar (HUD) dentro Obsidian (zero scritture nel Vault!).
    Preserva il target_file esistente per evitare cancellazioni involontarie a fine job.
    """
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    status_file = RUNTIME_DIR / "job-status.json"

    # Preserva target_file se vuoto o non specificato (salvo stato idle)
    if status == "idle":
        target_file = ""
    elif not target_file and status_file.exists():
        try:
            prev_status = json.loads(status_file.read_text(encoding="utf-8"))
            target_file = prev_status.get("target_file", "")
        except Exception:
            pass
    if not target_file and status != "idle":
        job_file = RUNTIME_DIR / "current-job.json"
        if job_file.exists():
            try:
                j_data = json.loads(job_file.read_text(encoding="utf-8"))
                target_file = j_data.get("target_file_rel") or j_data.get("target_file_path") or ""
            except Exception:
                pass

    status_data = {
        "status": status,
        "percent": max(0, min(100, int(percent))),
        "step_number": int(step_number),
        "total_steps": int(total_steps),
        "message": message,
        "detail": detail,
        "target_file": target_file,
        "error": error,
        "phase": phase or PHASE_BY_STEP.get(int(step_number), ""),
        "progress": progress,
        "pid": None if status in ["completed", "cancelled", "error", "idle"] else os.getpid(),
        "updated_at": int(time.time() * 1000),
    }
    tmp_path = status_file.with_suffix(".tmp")
    try:
        tmp_path.write_text(json.dumps(status_data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(status_file)
    except Exception as e:
        sys.stderr.write(f"[Orchestrator] Errore aggiornamento job-status.json: {e}\n")

    # Mantiene il symlink trasparente in .antigravity/job-status.json per compatibilità
    try:
        vault_status = vault_root / ".antigravity" / "job-status.json"
        if not vault_status.exists() and not vault_status.is_symlink():
            vault_status.parent.mkdir(parents=True, exist_ok=True)
            vault_status.symlink_to(status_file)
    except Exception:
        pass



def sanitize_markdown_text(text: str, is_moc: Optional[bool] = None) -> str:
    """
    Sanifica il testo Markdown applicando i 4 vincoli tassativi del vault:
    1. Sostituisce \vline con \vert in formule LaTeX (compatibilità MathJax Obsidian).
    2. Rimuove apici singoli, doppi e backtick attorno ai wikilink: ['"`]([[...]])['"`] -> \1.
    3. Rimuove riferimenti metadidattici a lezioni, capitoli o codici notebook (es. *(Lezioni 1–28...)*).
    4. Rimuove tutte le emoji Unicode dai testi generati (note e MOC) salvaguardando caratteri matematici e formattazione.
    5. Pulisce spazi doppi residui nei titoli, nei punti elenco e nei callout.
    6. Se e solo se il file è un MOC (is_moc=True o rilevato dal frontmatter Type: MOC), applica la Legge 4 (Zero Formule, Zero Alias).
    """
    if not text:
        return text

    # 1. Sostituzione \vline con \vert (compatibilità MathJax Obsidian)
    text = re.sub(r"\\vline\b", r"\\vert", text)

    # 2. Protezione blocchi di codice recintati (```dataviewjs ... ```, ```mermaid ... ```, etc.)
    code_blocks: List[str] = []
    def code_block_repl(match):
        idx = len(code_blocks)
        code_blocks.append(match.group(0))
        return f"__ANTIGRAVITY_CODE_BLOCK_{idx}__"

    text = re.sub(r"```[\s\S]*?```", code_block_repl, text)

    # 3. Riquadramento Wikilink: rimuove backtick, apici singoli e doppi attorno a [[...]]
    text = re.sub(r"[`'\"](\[\[.+?\]\])[`'\"]", r"\1", text)

    # 4. Divieto assoluto di riferimenti meta a lezioni, capitoli o codici notebook
    text = re.sub(r"(?m)^\s*\*\s*\((?:Lezioni?|Indice Libro|Dal Diario)[^)]*\)\s*\*\s*$\n?", "", text)
    text = re.sub(r"(?m)^\s*\((?:Lezioni?|Indice Libro|Dal Diario)[^)]*\)\s*$\n?", "", text)
    text = re.sub(r"\s*\(\s*(?:Lezioni?|Indice Libro|Dal Diario|Cap\.\s*\d+[^)]*|Capp\.\s*\d+[^)]*)[^)]*\)", "", text)

    # 5. Purga totale delle Emoji Unicode
    emoji_pattern = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B50\u2B55]\uFE0F?")
    text = emoji_pattern.sub("", text)
    text = text.replace("\uFE0F", "")

    # 6. Pulizia spazi doppi residui lasciati dalla rimozione delle emoji
    text = re.sub(r"(?m)^(#{1,6})\s{2,}", r"\1 ", text)
    text = re.sub(r"\*\*\s{2,}", "**", text)
    text = re.sub(r">\s*\[!([^\]]+)\]-\s{2,}", r"> [!\1]- ", text)
    text = re.sub(r">\s*\[!([^\]]+)\]\s{2,}", r"> [!\1] ", text)

    # 6.5. Vincoli specifici per i MOC (Legge 4: Zero Formule, Zero Alias nei Wikilink)
    if is_moc is None:
        # Rileva MOC tassativamente ed esclusivamente dal frontmatter YAML:
        # non usare mai match su heading generici (# ... MOC) per evitare collisioni con "### Note Generali e MOC"
        is_moc = bool(
            re.search(r"(?m)^Type:\s*\n(?:\s*-\s*[^\n]+\n)*\s*-\s*MOC\b", text)
            or re.search(r"(?m)^Type:\s*MOC\b", text)
        )

    if is_moc:
        # Vincolo 3 MOC: Divieto assoluto di alias nei wikilink (trasforma [[Target|alias]] in [[Target]])
        text = re.sub(r"\[\[([^|\]\n#]+)(#[^|\]\n]+)?\|[^\]\n]+\]\]", r"[[\1\2]]", text)
        # Vincolo 1 MOC: Divieto assoluto di formule LaTeX nei MOC
        text = re.sub(r"\$\$[\s\S]*?\$\$", "", text)
        text = re.sub(r"\$([^$\n]+)\$", r"\1", text)

    # 7. Ripristino dei blocchi di codice
    for idx, block in enumerate(code_blocks):
        if is_moc and block.startswith("```mermaid"):
            # Purga formule LaTeX e delimitatori $ da Mermaid
            block = re.sub(r"\$([^$\n]+)\$", r"\1", block)
            # Purga pipe/alias nei wikilink dentro nodi Mermaid
            block = re.sub(r"\[\[([^|\]\n#]+)(#[^|\]\n]+)?\|[^\]\n]+\]\]", r"[[\1\2]]", block)
        text = text.replace(f"__ANTIGRAVITY_CODE_BLOCK_{idx}__", block)

    return text


def sanitize_markdown_file(file_path: Union[str, Path], is_moc: Optional[bool] = None) -> bool:
    """
    Legge un file Markdown, applica sanitize_markdown_text e lo sovrascrive se modificato.
    Restituisce True se il file è stato sanificato e modificato, False altrimenti.
    """
    p = Path(file_path).resolve()
    if not p.exists() or not p.is_file():
        return False
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        if is_moc is None:
            # Controllo euristico sul percorso file se non specificato a monte
            if "01 MOC's" in p.parts or p.name.lower().endswith("moc.md"):
                is_moc = True
        sanitized = sanitize_markdown_text(content, is_moc=is_moc)
        if sanitized != content:
            p.write_text(sanitized, encoding="utf-8")
            sys.stdout.write(f"[Sanitizer] File sanificato con successo: {p}\n")
            return True
        return False
    except Exception as e:
        sys.stderr.write(f"[Sanitizer] Errore sanificazione file {p}: {e}\n")
        return False


def typical_note_lines(vault_root: Path, discipline: str, is_moc: bool) -> int:
    """Lunghezza tipica (mediana delle 15 note più recenti) delle note dello stesso tipo e disciplina.
    Serve all'HUD per misurare la scrittura in righe reali invece che in tempo trascorso."""
    base = vault_root / ("01 MOC's" if is_moc else discipline) if (is_moc or discipline) else None
    if not base or not base.is_dir():
        return 400 if not is_moc else 550
    files = [p for p in base.rglob("*.md") if is_moc == p.stem.endswith(" MOC")]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    counts = []
    for p in files[:15]:
        try:
            counts.append(len(p.read_text(encoding="utf-8", errors="replace").splitlines()))
        except Exception:
            pass
    counts = sorted(c for c in counts if c >= 50)
    return counts[len(counts) // 2] if counts else 400


def monitor_target_generation(
    vault_root: Path,
    target_rel: str,
    job_file: Optional[Path] = None,
    timeout_sec: int = 900
) -> int:
    """
    Monitora in tempo reale la scrittura del file target da parte dell'agente Antigravity:
    - Risolve dinamicamente ad ogni ciclo il percorso effettivo del file tra candidati multipli
      (es. 01 MOC's/ per i MOC, cartella disciplina, percorso relativo specificato).
    - MOC (Legge 4): incrementa dinamicamente la percentuale da 70% a 92% in base alle righe generate,
      NON attende %%STUDY_DATA né esegue anki_sync.py, verifica completezza strutturale e stabilità,
      applica la sanificazione vincolante al 95% e conclude al 100% (completed).
    - Note Normali (Legge 8): incrementa da 70% a 92%, quando rileva %%STUDY_DATA avanza al 95% ed
      esegue anki_sync.py, verifica stabilità (fallback 6s se assente) e conclude al 100%.
    - In caso di timeout, notifica lo stato 'error' in job-status.json prevenendo blocchi infiniti.
    - Rispetta 'cancelled' o 'error' impostati esternamente.
    """
    tools_dir = vault_root / ".antigravity" / "tools"
    start_time = time.time()
    last_line_count = 0
    stable_cycles = 0
    study_detected = False

    # Carica job data se disponibile per determinare tipo operazione e disciplina
    job_data: Dict[str, Any] = {}
    if job_file and job_file.exists():
        try:
            job_data = json.loads(job_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    if not job_data:
        default_job = RUNTIME_DIR / "current-job.json"
        if default_job.exists():
            try:
                job_data = json.loads(default_job.read_text(encoding="utf-8"))
            except Exception:
                pass

    op_type = job_data.get("operation_type") or job_data.get("operation", "")
    discipline = job_data.get("discipline", "")
    is_moc = bool(
        op_type == "moc"
        or "MOC" in target_rel
        or "01 MOC" in target_rel
        or job_data.get("is_moc")
        or job_data.get("moc_mode")
    )

    sys.stdout.write(f"[Monitor] Avviato monitoraggio in tempo reale per: {target_rel} (is_moc={is_moc}, timeout: {timeout_sec}s)...\n")
    sys.stdout.flush()

    expected_lines = typical_note_lines(vault_root, discipline, is_moc)
    active_target_path: Optional[Path] = None
    active_target_rel = target_rel
    initial_target_mtime: Optional[float] = None

    while (time.time() - start_time) < timeout_sec:
        # 1. Controlla stati terminali esterni (annullato o errore)
        status_file = RUNTIME_DIR / "job-status.json"
        if status_file.exists():
            try:
                curr_status = json.loads(status_file.read_text(encoding="utf-8"))
                if curr_status.get("status") in ["cancelled", "error"]:
                    sys.stdout.write(f"[Monitor] Job terminato esternamente con stato: {curr_status.get('status')}\n")
                    return 0
                if curr_status.get("status") == "completed":
                    st_time = curr_status.get("updated_at", 0)
                    st_target = curr_status.get("target_file", "")
                    if st_time > (start_time * 1000 - 2000) and (not st_target or st_target == active_target_rel or st_target == target_rel):
                        sys.stdout.write(f"[Monitor] Job già contrassegnato completed.\n")
                        return 0
            except Exception:
                pass

        # 2. Risoluzione dinamica dei percorsi candidati
        target_name = Path(active_target_rel).name
        target_stem = Path(active_target_rel).stem

        candidates: List[Path] = []
        # Candidato 1: percorso relativo dichiarato
        candidates.append(vault_root / active_target_rel)
        # Candidato 2: 01 MOC's se è un MOC o contiene MOC nel nome
        if is_moc or "MOC" in target_name:
            candidates.append(vault_root / "01 MOC's" / target_name)
            if not target_stem.lower().endswith("moc"):
                candidates.append(vault_root / "01 MOC's" / f"{target_stem} MOC.md")
        # Candidato 3: cartella della disciplina
        if discipline:
            candidates.append(vault_root / discipline / target_name)
        # Candidato 4: root del vault
        candidates.append(vault_root / target_name)

        # Rimuovi duplicati preservando l'ordine
        seen_cand = set()
        unique_candidates: List[Path] = []
        for c in candidates:
            try:
                resolved_c = c.resolve()
            except Exception:
                resolved_c = c
            if resolved_c not in seen_cand:
                seen_cand.add(resolved_c)
                unique_candidates.append(c)

        # Individua il candidato attivo: priorità al file che esiste ed è stato toccato dopo l'avvio del job
        best_cand: Optional[Path] = None
        best_mtime: float = -1.0
        for c in unique_candidates:
            if c.exists() and c.is_file():
                try:
                    c_mtime = c.stat().st_mtime
                    if c_mtime >= (start_time - 5.0) and c_mtime > best_mtime:
                        best_cand = c
                        best_mtime = c_mtime
                except Exception:
                    pass

        # Se nessun file è stato toccato di recente, controlla se ne esiste già uno
        if not best_cand:
            for c in unique_candidates:
                if c.exists() and c.is_file():
                    best_cand = c
                    break

        if best_cand:
            active_target_path = best_cand
            if initial_target_mtime is None:
                try:
                    cand_mtime = best_cand.stat().st_mtime
                    if cand_mtime < start_time:
                        initial_target_mtime = cand_mtime
                except Exception:
                    pass
            try:
                rel_cand = str(best_cand.relative_to(vault_root))
                if rel_cand != active_target_rel:
                    active_target_rel = rel_cand
                    # Sincronizza current-job.json con il percorso reale risolto
                    if job_file and job_file.exists():
                        try:
                            job_data["target_file_rel"] = active_target_rel
                            job_file.write_text(json.dumps(job_data, indent=2, ensure_ascii=False), encoding="utf-8")
                        except Exception:
                            pass
            except Exception:
                pass

        # 3. Se il file target non esiste ancora o non è ancora stato toccato dal runner/agente, attendi con stato dinamico
        file_ready_for_scan = False
        if active_target_path and active_target_path.exists():
            try:
                mtime = active_target_path.stat().st_mtime
                file_untouched = False
                if initial_target_mtime is not None and mtime <= initial_target_mtime:
                    file_untouched = True
                elif mtime < (start_time - 1.0):
                    file_untouched = True

                if not file_untouched:
                    file_ready_for_scan = True
            except Exception:
                file_ready_for_scan = False

        if not file_ready_for_scan:
            elapsed = int(time.time() - start_time)
            dyn_pct = min(88, max(70, int(70 + (elapsed / 180.0) * 18)))
            if op_type == "edit":
                wait_msg = "✍️ Antigravity sta analizzando ed elaborando le modifiche richieste..."
                wait_detail = f"In attesa di riscrittura su {active_target_rel} ({elapsed}s trascorse)..."
            elif is_moc:
                wait_msg = "✍️ Antigravity sta redigendo il MOC discorsivo e la mappa dei collegamenti..."
                wait_detail = f"In attesa di scrittura su {active_target_rel} ({elapsed}s trascorse)..."
            else:
                wait_msg = "✍️ Antigravity sta generando la nota e gli schemi..."
                wait_detail = f"In attesa di scrittura su {active_target_rel} ({elapsed}s trascorse)..."

            update_status(
                vault_root=vault_root,
                percent=dyn_pct,
                step_number=5,
                total_steps=6,
                message=wait_msg,
                detail=wait_detail,
                status="running",
                target_file=active_target_rel,
            )
            time.sleep(1.0)
            continue

        # 4. Analizza contenuto e crescita
        if active_target_path and active_target_path.exists():
            try:
                content = active_target_path.read_text(encoding="utf-8", errors="replace")
                lines = content.splitlines()
                line_count = len(lines)

                # Rileva se il contenuto dimostra che si tratta di un MOC (mai per note normali o edit non-MOC)
                if not is_moc and op_type != "normal":
                    is_moc = bool(
                        re.search(r"(?m)^Type:\s*\n(?:\s*-\s*[^\n]+\n)*\s*-\s*MOC\b", content)
                        or re.search(r"(?m)^Type:\s*MOC\b", content)
                        or "01 MOC's" in active_target_rel
                        or active_target_rel.lower().endswith("moc.md")
                    )

                # Trova l'ultimo heading per live activity
                last_heading = ""
                for line in lines:
                    trimmed = line.strip()
                    if trimmed.startswith("#"):
                        last_heading = re.sub(r"^#+\s*", "", trimmed)
                heading_info = f" ({last_heading[:30]}...)" if last_heading else ""

                if is_moc:
                    # ==========================================
                    # LOGICA SPECIFICA PER I MOC (Legge 4)
                    # ==========================================
                    calc_pct = 70 + int(22 * min(1.0, line_count / expected_lines))
                    update_status(
                        vault_root=vault_root,
                        percent=calc_pct,
                        step_number=5,
                        total_steps=6,
                        message="✍️ Antigravity sta scrivendo il MOC e la mappa dei collegamenti",
                        detail=f"{line_count} righe scritte{heading_info}",
                        status="running",
                        target_file=active_target_rel,
                        progress={"done": line_count, "total": expected_lines, "unit": "righe"},
                    )

                    # Verifica stabilità
                    if line_count == last_line_count and line_count > 15:
                        stable_cycles += 1
                    else:
                        stable_cycles = 0

                    # Verifica completezza strutturale del MOC
                    is_structurally_complete = False
                    if line_count >= 30:
                        code_fence_count = content.count("```")
                        balanced_fences = (code_fence_count % 2 == 0)
                        has_closing_section = (
                            ("## Note e Paragrafi Collegati" in content)
                            or ("### Riferimenti Generali" in content)
                            or ("### Ponti Interdisciplinari" in content)
                            or ("[!] Diagnosi di Completezza" in content)
                            or ("[!]todo" in content and "Diagnosi" in content)
                        )
                        if balanced_fences and (has_closing_section or line_count >= 80):
                            is_structurally_complete = True

                    # Soglia stabilità MOC: 4 cicli (4s) se strutturalmente completo, altrimenti 8 cicli (8s)
                    min_stable_moc = 4 if is_structurally_complete else 8

                    if stable_cycles >= min_stable_moc and line_count >= 30:
                        # Fase 6/6 (95%): Sanificazione vincolante MOC (Zero formule, zero alias wikilink, ecc.)
                        update_status(
                            vault_root=vault_root,
                            percent=95,
                            step_number=6,
                            total_steps=6,
                            message="🔍 Sanificazione e raccordo collegamenti del MOC...",
                            detail=f"MOC verificato ({line_count} righe). Applicazione regole di formattazione...",
                            status="running",
                            target_file=active_target_rel,
                        )
                        try:
                            sanitize_markdown_file(active_target_path, is_moc=True)
                        except Exception as e_san:
                            sys.stderr.write(f"[Monitor] Errore sanificazione MOC: {e_san}\n")

                        time.sleep(0.5)
                        final_lines = len(active_target_path.read_text(encoding="utf-8", errors="replace").splitlines())

                        # Il MOC passa poi dalla verifica (titoli, accenti, esclusività): il completamento lo dichiara run_job.sh
                        if job_data.get("moc_check_required"):
                            update_status(
                                vault_root=vault_root, percent=95, step_number=6, total_steps=6,
                                message="✍️ MOC scritto: in attesa della verifica",
                                detail=f"{final_lines} righe in {active_target_rel}", status="running",
                                target_file=active_target_rel, phase="verify",
                            )
                            return 0

                        # Completamento al 100%
                        update_status(
                            vault_root=vault_root,
                            percent=100,
                            step_number=6,
                            total_steps=6,
                            message="✅ MOC completato con successo!",
                            detail=f"Salvato in: {active_target_rel} ({final_lines} righe)",
                            status="completed",
                            target_file=active_target_rel,
                        )
                        sys.stdout.write(f"[Monitor] MOC completato con successo ({final_lines} righe in {active_target_rel})!\n")
                        return 0

                else:
                    # ==========================================
                    # LOGICA NOTE NORMALI (Legge 8)
                    # ==========================================
                    has_study = ("%%STUDY_DATA" in content) or ("Palestra d'Esame" in content) or ("study_panel.js" in content)

                    if has_study and not study_detected:
                        study_detected = True
                        update_status(
                            vault_root=vault_root,
                            percent=95,
                            step_number=6,
                            total_steps=6,
                            message="🃏 Configurazione Pannello Flashcard/Quiz, Sync Anki e aggiornamento MOC...",
                            detail=f"Studio data rilevato ({line_count} righe). Verifica flashcard e sincronizzazione...",
                            status="running",
                            target_file=active_target_rel,
                        )
                        anki_tool = tools_dir / "anki_sync.py"
                        if anki_tool.exists():
                            try:
                                subprocess.run([sys.executable, str(anki_tool), str(active_target_path), "--quiet"], capture_output=True, timeout=8, check=False)
                            except Exception:
                                pass

                    elif not study_detected:
                        if line_count > 5 and line_count != last_line_count:
                            calc_pct = 70 + int(22 * min(1.0, line_count / expected_lines))
                            update_status(
                                vault_root=vault_root,
                                percent=calc_pct,
                                step_number=5,
                                total_steps=6,
                                message="✍️ Antigravity sta scrivendo la nota",
                                detail=f"{line_count} righe scritte{heading_info}",
                                status="running",
                                target_file=active_target_rel,
                                progress={"done": line_count, "total": expected_lines, "unit": "righe"},
                            )

                    if line_count == last_line_count and line_count > 10:
                        stable_cycles += 1
                    else:
                        stable_cycles = 0

                    min_stable = 3 if study_detected else 6
                    if stable_cycles >= min_stable:
                        try:
                            sanitize_markdown_file(active_target_path, is_moc=is_moc)
                        except Exception as e_san:
                            sys.stderr.write(f"[Monitor] Errore sanificazione file target: {e_san}\n")

                        time.sleep(0.3)
                        final_lines = len(active_target_path.read_text(encoding="utf-8", errors="replace").splitlines())

                        # In modalità "Solo NotebookLM" il completamento lo dichiara run_job.sh dopo la verifica di esclusività
                        if job_data.get("grounding_verification_required"):
                            update_status(
                                vault_root=vault_root,
                                percent=95,
                                step_number=6,
                                total_steps=6,
                                message="✍️ Nota scritta: in attesa della verifica di esclusività NotebookLM...",
                                detail=f"{final_lines} righe in {active_target_rel}",
                                status="running",
                                target_file=active_target_rel,
                                phase="verify",
                            )
                            sys.stdout.write(f"[Monitor] Scrittura stabile ({final_lines} righe): completamento rinviato alla verifica di esclusività.\n")
                            return 0

                        comp_msg = "✅ Nota modificata con successo!" if op_type == "edit" else "✅ Nota completata con successo!"
                        update_status(
                            vault_root=vault_root,
                            percent=100,
                            step_number=6,
                            total_steps=6,
                            message=comp_msg,
                            detail=f"Salvata in: {active_target_rel} ({final_lines} righe)",
                            status="completed",
                            target_file=active_target_rel,
                        )
                        sys.stdout.write(f"[Monitor] {comp_msg} ({final_lines} righe in {active_target_rel})!\n")
                        return 0

                last_line_count = line_count

            except Exception as e:
                sys.stderr.write(f"[Monitor] Errore lettura file target: {e}\n")

        time.sleep(1.0)

    # Raggiunto il timeout massimo
    sys.stderr.write(f"[Monitor] Timeout raggiunto ({timeout_sec}s).\n")
    update_status(
        vault_root=vault_root,
        percent=0,
        step_number=0,
        total_steps=6,
        message="❌ Timeout: tempo massimo di generazione superato",
        detail=f"Nessun completamento rilevato per {active_target_rel} entro {timeout_sec}s",
        status="error",
        target_file=active_target_rel,
        error=f"Timeout superato ({timeout_sec}s)",
    )
    return 1


def run_tool_script(script_name: str, args: List[str], tools_dir: Path) -> subprocess.CompletedProcess:
    """Esegue un tool Python della cartella .antigravity/tools/ con PATH garantito."""
    script_path = tools_dir / script_name
    cmd = [sys.executable, str(script_path)] + args
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def create_target_note_backup(vault_root: Path, target_rel_path: str) -> Optional[Path]:
    """
    Crea un backup automatico immediato del file prima di qualsiasi modifica.
    Salva la copia esatta in .antigravity/backups/YYYYMMDD_HHMMSS_<nomefile>.md
    """
    if not target_rel_path:
        return None
    target_path = vault_root / target_rel_path
    if not target_path.exists():
        target_path = Path(target_rel_path)
        if not target_path.exists():
            sys.stderr.write(f"[Orchestrator] Warning: File target non trovato per backup: {target_rel_path}\n")
            return None

    backups_dir = vault_root / ".antigravity" / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
    sanitized_stem = re.sub(r'[\\/*?:"<>| ]', '_', target_path.stem)
    backup_filename = f"{timestamp_str}_{sanitized_stem}{target_path.suffix}"
    backup_file = backups_dir / backup_filename

    try:
        content = target_path.read_text(encoding="utf-8", errors="replace")
        backup_file.write_text(content, encoding="utf-8")
        sys.stderr.write(f"[Orchestrator] 🛡️ Backup di sicurezza creato con successo in: {backup_file}\n")
        return backup_file
    except Exception as e:
        sys.stderr.write(f"[Orchestrator] ❌ Errore durante la creazione del backup: {e}\n")
        return None


# ==============================================================================
# 1. PRE-ASSEMBLY DELLE REGOLE STATICHE (ZERO PERDITA DI QUALITÀ)
# ==============================================================================

def compile_static_instructions(
    vault_root: Path,
    antigravity_dir: Path,
    discipline_name: str,
    context_dir: Path
) -> Path:
    """
    Unisce in un unico file (.antigravity/job-context/compiled-instructions.md):
    - .antigravity/core-guidelines.md
    - .antigravity/disciplines/<slug>.md
    - .antigravity/snippets/<slug>_blueprint.md
    
    Permette all'agente di assimilare tutte le regole e i calibri stilistici con una sola
    chiamata di lettura, senza sovraccaricare il context window né disperdere l'attenzione.
    """
    slug = DISCIPLINE_SLUG_MAP.get(discipline_name, discipline_name.lower().replace(" ", "-"))
    core_path = antigravity_dir / "core-guidelines.md"
    disc_path = antigravity_dir / "disciplines" / f"{slug}.md"
    snippet_path = antigravity_dir / "snippets" / f"{slug}_blueprint.md"

    # Fallback per symlink di nomi alternativi
    if not disc_path.exists():
        for cand in (antigravity_dir / "disciplines").glob("*.md"):
            if cand.stem == slug or cand.stem.startswith(slug[:6]):
                disc_path = cand
                break

    if not snippet_path.exists():
        for cand in (antigravity_dir / "snippets").glob("*_blueprint.md"):
            if cand.stem.startswith(slug):
                snippet_path = cand
                break

    compiled_blocks: List[str] = []
    compiled_blocks.append(f"# 🏛️ REGOLE STATICHE COMPILATE PER ANTIGRAVITY — {discipline_name.upper()}")
    compiled_blocks.append(
        "> [!NOTE] File Pre-Assemblato per Esecuzione ad Alta Velocità\n"
        "> Questo file contiene la sintesi completa della Costituzione Universale, "
        "delle Regole della Materia e dello Snippet Blueprint Compresso. "
        "Leggilo una volta per avere l'intero quadro normativo e stilistico a sforzo zero.\n"
    )

    # 1. Costituzione Universale
    if core_path.exists():
        core_text = core_path.read_text(encoding="utf-8", errors="replace").strip()
        compiled_blocks.append("## 📜 SEZIONE 1 — COSTITUZIONE UNIVERSALE DEL VAULT\n")
        compiled_blocks.append(core_text)
        compiled_blocks.append("\n---\n")
    else:
        compiled_blocks.append("*(Costituzione non trovata in .antigravity/core-guidelines.md)*\n\n---\n")

    # 2. Profilo di Disciplina Specifico
    if disc_path.exists():
        disc_text = disc_path.read_text(encoding="utf-8", errors="replace").strip()
        compiled_blocks.append(f"## 🎯 SEZIONE 2 — PROFILO DISCIPLINARE: {discipline_name.upper()}\n")
        compiled_blocks.append(disc_text)
        compiled_blocks.append("\n---\n")
    else:
        compiled_blocks.append(f"*(Profilo per {discipline_name} non trovato in {disc_path})*\n\n---\n")

    # 3. Snippet Blueprint Compresso
    if snippet_path.exists():
        snip_text = snippet_path.read_text(encoding="utf-8", errors="replace").strip()
        compiled_blocks.append(f"## 📐 SEZIONE 3 — SNIPPET BLUEPRINT COMPRESSO (MODELLO E TONO)\n")
        compiled_blocks.append(snip_text)
        compiled_blocks.append("\n")
    else:
        compiled_blocks.append(f"*(Snippet Blueprint per {discipline_name} non trovato in {snippet_path})*\n")

    out_file = context_dir / "compiled-instructions.md"
    out_file.write_text("\n".join(compiled_blocks), encoding="utf-8")
    sys.stderr.write(f"[Orchestrator] Istruzioni statiche compilate in: {out_file}\n")
    return out_file


# ==============================================================================
# 2. SCANSIONE VAULT E DIAGNOSI LINK ROSSI PER MOC E NOTE
# ==============================================================================

def parse_markdown_frontmatter_and_sections(fpath: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str, List[str]]:
    """
    Estrae da un file markdown del vault:
    1. Metadata frontmatter (disciplina, type, tags, aliases, title)
    2. Struttura degli header H2 (##) e H3 (###)
    3. Paragrafo introduttivo (primo blocco testuale pulito, ignorando titoli e callout)
    4. Outgoing wikilinks ([[Target]] e [[Target|Alias]]) escludendo allegati/media.
    """
    meta: Dict[str, Any] = {
        "title": fpath.stem,
        "disciplina": "",
        "type": [],
        "tags": [],
        "aliases": []
    }
    headings: List[Dict[str, Any]] = []
    intro_paragraph: str = ""
    outgoing_links: List[str] = []

    try:
        content = fpath.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return meta, headings, f"Errore lettura file: {e}", outgoing_links

    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body = parts[2]
            current_list_key = None
            for raw_line in fm_text.splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("- ") and current_list_key:
                    val = line[2:].strip().strip("\"'")
                    if val:
                        meta[current_list_key].append(val)
                    continue
                if ":" in line:
                    key, val = [x.strip() for x in line.split(":", 1)]
                    k_lower = key.lower()
                    if k_lower == "disciplina":
                        meta["disciplina"] = val.strip("\"'")
                        current_list_key = None
                    elif k_lower == "title":
                        meta["title"] = val.strip("\"'")
                        current_list_key = None
                    elif k_lower in ["type", "tags", "aliases"]:
                        current_list_key = k_lower
                        if val:
                            if val.startswith("[") and val.endswith("]"):
                                items = [x.strip().strip("\"'") for x in val[1:-1].split(",") if x.strip()]
                                meta[k_lower].extend(items)
                            else:
                                meta[k_lower].append(val.strip("\"'"))
                    else:
                        current_list_key = None

    # Estrazione Headings H2 e H3
    for line in body.splitlines():
        if line.startswith("## "):
            headings.append({"level": 2, "title": line[3:].strip()})
        elif line.startswith("### "):
            headings.append({"level": 3, "title": line[4:].strip()})

    # Estrazione Paragrafo Introduttivo (primo paragrafo pulito)
    for para in body.split("\n\n"):
        p_clean = para.strip()
        if not p_clean:
            continue
        if p_clean.startswith("#") or p_clean.startswith("> [!") or p_clean.startswith("---"):
            continue
        if p_clean.startswith("|") or p_clean.startswith("[!["):
            continue
        intro_paragraph = " ".join(p_clean.split())
        if len(intro_paragraph) > 400:
            intro_paragraph = intro_paragraph[:400] + "..."
        break

    # Estrazione Wikilink uscenti escludendo allegati
    wikilink_re = re.compile(r"(?<!!)\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
    raw_links = wikilink_re.findall(body)
    media_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".pdf", ".mp3", ".mp4", ".wav"}
    for link_target in raw_links:
        target_clean = link_target.strip()
        if not target_clean:
            continue
        suffix = Path(target_clean).suffix.lower()
        if suffix in media_exts:
            continue
        if target_clean not in outgoing_links:
            outgoing_links.append(target_clean)

    return meta, headings, intro_paragraph, outgoing_links


def build_vault_notes_summary(
    vault_root: Path,
    discipline_name: str,
    topic: str,
    context_dir: Path
) -> Dict[str, Any]:
    """
    Scansiona il vault ed estrae tutte le note esistenti per una data disciplina o argomento.
    Calcola per ciascuna nota: metadata, struttura H2/H3, paragrafo introduttivo e wikilink uscenti.
    Confronta i wikilink con l'indice generale del vault per distinguere i link esistenti dai 'link rossi'.
    Genera .antigravity/job-context/vault_notes_summary.md e il file JSON corrispondente.
    """
    # 1. Indicizzazione globale del Vault (per validazione e disambiguazione dei wikilink)
    canonical_files: Dict[str, str] = {}   # lowercase_stem -> exact_stem
    canonical_paths: Dict[str, Path] = {}  # exact_stem -> relative_path
    aliases_map: Dict[str, str] = {}       # lowercase_alias -> exact_stem

    ignored_dirs = {"templates", "Templates", "00 Meta", "Prompts", "allegati", ".antigravity", ".obsidian", ".git", ".trash"}

    for p in vault_root.rglob("*.md"):
        try:
            rel = p.relative_to(vault_root)
        except ValueError:
            continue
        parts = rel.parts
        if any(part.startswith(".") for part in parts) or (parts and parts[0] in ignored_dirs):
            continue

        exact_stem = p.stem
        canonical_files[exact_stem.lower()] = exact_stem
        canonical_paths[exact_stem] = rel

        # Estrai alias dal frontmatter per risoluzione wikilink
        try:
            c = p.read_text(encoding="utf-8", errors="replace")
            if c.startswith("---"):
                fm_parts = c.split("---", 2)
                if len(fm_parts) >= 3:
                    for line in fm_parts[1].splitlines():
                        if "aliases:" in line:
                            rest = line.split("aliases:", 1)[1].strip()
                            if rest.startswith("[") and rest.endswith("]"):
                                for al in rest[1:-1].split(","):
                                    clean_al = al.strip().strip("\"'")
                                    if clean_al:
                                        aliases_map[clean_al.lower()] = exact_stem
                        elif line.strip().startswith("- "):
                            val = line.strip()[2:].strip().strip("\"'")
                            if val:
                                aliases_map[val.lower()] = exact_stem
        except Exception:
            pass

    # 2. Ricerca delle note pertinenti alla disciplina o argomento
    slug = DISCIPLINE_SLUG_MAP.get(discipline_name, discipline_name.lower().replace(" ", "-"))
    discipline_keywords = [
        discipline_name.lower(),
        slug.lower(),
        slug.replace("-", " ").lower(),
    ]

    DISCIPLINE_DIR_ALIASES = {
        "Arte e Storia dell'Arte": ["arte", "storia dell'arte"],
        "Biologia": ["biologia", "biologia e neuroscienze"],
        "Neuroscienze": ["neuroscienze", "biologia e neuroscienze"],
        "Letteratura": ["letteratura", "letteratura inglese"],
        "Storia": ["storia", "storiа"],
        "Politica e Geopolitica": ["politica", "geopolitica", "politica e geopolitica", "educazione civica"],
        "Economia e Finanza": ["economia", "finanza", "economia e finanza"],
        "Tecnologia ed Elettronica": ["tecnologia", "elettronica", "tecnologia ed elettronica"],
        "Musica e Industria Musicale": ["musica", "industria musicale", "musica e industria musicale"],
    }
    extra_aliases = DISCIPLINE_DIR_ALIASES.get(discipline_name, [])
    for ea in extra_aliases:
        discipline_keywords.append(ea.lower())

    matching_notes: List[Path] = []
    for exact_stem, rel_path in canonical_paths.items():
        fpath = vault_root / rel_path

        # Controllo A: percorsi cartella genitore
        parent_parts = [part.lower() for part in rel_path.parts[:-1]]
        matched_by_dir = False
        for part in parent_parts:
            for kw in discipline_keywords:
                if kw == part or (len(kw) > 4 and kw in part):
                    matched_by_dir = True
                    break
            if matched_by_dir:
                break

        if matched_by_dir:
            matching_notes.append(fpath)
            continue

        # Controllo B: frontmatter disciplina o tag
        meta, _, _, _ = parse_markdown_frontmatter_and_sections(fpath)
        meta_disc = meta.get("disciplina", "").lower()
        if meta_disc and any(kw in meta_disc for kw in discipline_keywords):
            matching_notes.append(fpath)
            continue

        meta_tags = [t.lower().lstrip("#") for t in meta.get("tags", [])]
        if any(kw in t for t in meta_tags for kw in discipline_keywords):
            matching_notes.append(fpath)
            continue

        # Controllo C: corrispondenza con il topic se specifico
        if topic and len(topic) > 3 and topic.lower() in exact_stem.lower():
            matching_notes.append(fpath)
            continue

    # Dedup conservando l'ordine
    unique_matching_notes: List[Path] = []
    seen_paths = set()
    for p in matching_notes:
        if p not in seen_paths:
            seen_paths.add(p)
            unique_matching_notes.append(p)

    # 3. Analisi approfondita di ciascuna nota pertinente
    notes_analysis: List[Dict[str, Any]] = []
    global_red_links: Dict[str, List[str]] = {}
    global_existing_links: Dict[str, List[str]] = {}

    for note_path in unique_matching_notes:
        meta, headings, intro, outgoing_links = parse_markdown_frontmatter_and_sections(note_path)

        note_existing: List[str] = []
        note_red: List[str] = []

        for target in outgoing_links:
            target_clean = target.strip()
            target_lower = target_clean.lower()

            resolved_stem = None
            if target_lower in canonical_files:
                resolved_stem = canonical_files[target_lower]
            elif target_lower in aliases_map:
                resolved_stem = aliases_map[target_lower]

            if resolved_stem:
                if resolved_stem not in note_existing:
                    note_existing.append(resolved_stem)
                global_existing_links.setdefault(resolved_stem, []).append(note_path.stem)
            else:
                if target_clean not in note_red:
                    note_red.append(target_clean)
                global_red_links.setdefault(target_clean, []).append(note_path.stem)

        note_entry = {
            "title": note_path.stem,
            "path": str(note_path.relative_to(vault_root)),
            "meta": meta,
            "headings": headings,
            "intro": intro,
            "existing_links": note_existing,
            "red_links": note_red
        }
        notes_analysis.append(note_entry)

    # 4. Generazione del Dossier Markdown: vault_notes_summary.md
    md_lines: List[str] = []
    md_lines.append(f"# 📚 DOSSIER NOTE ESISTENTI NEL VAULT — {discipline_name.upper()}")
    md_lines.append(f"> **Focus Operativo / MOC:** `{topic}` | **Data Generazione:** `{time.strftime('%Y-%m-%d %H:%M:%S')}`\n")
    md_lines.append("## 📊 Big Picture e Statistiche")
    md_lines.append(f"- **Disciplina:** `{discipline_name}`")
    md_lines.append(f"- **Note Analizzate nel Vault:** `{len(notes_analysis)}`")
    md_lines.append(f"- **Note Collegate Esistenti:** `{len(global_existing_links)}`")
    md_lines.append(f"- **Link Rossi Rilevati (Citati ma non ancora creati):** `{len(global_red_links)}`")
    md_lines.append("")

    md_lines.append("---")
    md_lines.append("## 📝 SEZIONE 1 — SCHEDE DETTAGLIATE DELLE NOTE PRESENTI")
    md_lines.append("")

    if not notes_analysis:
        md_lines.append("*(Nessuna nota trovata per questa disciplina nel vault)*\n")
    else:
        for idx, entry in enumerate(notes_analysis, 1):
            md_lines.append(f"### {idx}. [[{entry['title']}]]")
            md_lines.append(f"- **File:** `{entry['path']}`")
            types_str = ", ".join(entry['meta'].get('type', [])) or "Non specificato"
            tags_str = ", ".join([f"#{t}" for t in entry['meta'].get('tags', [])]) or "Nessun tag"
            aliases_str = ", ".join(entry['meta'].get('aliases', [])) or "Nessun alias"
            md_lines.append(f"- **Tipologia:** `{types_str}` | **Tag:** {tags_str} | **Alias:** `{aliases_str}`")
            if entry["intro"]:
                md_lines.append(f"- **Sintesi Introduttiva:** {entry['intro']}")

            if entry["headings"]:
                md_lines.append("- **Struttura Sezioni (H2/H3):**")
                for h in entry["headings"]:
                    indent = "    " if h["level"] == 3 else "  "
                    prefix = "###" if h["level"] == 3 else "##"
                    md_lines.append(f"{indent}- {prefix} {h['title']}")

            if entry["existing_links"]:
                ext_str = ", ".join([f"[[{link}]]" for link in entry["existing_links"]])
                md_lines.append(f"- **Note Esistenti Collegate:** {ext_str}")
            if entry["red_links"]:
                red_str = ", ".join([f"`[[{link}]]`" for link in entry["red_links"]])
                md_lines.append(f"- **Link Rossi Rilevati (non ancora create):** {red_str}")

            md_lines.append("")

    md_lines.append("---")
    md_lines.append("## 🔴 SEZIONE 2 — DIAGNOSI GLOBALE LINK ROSSI (DA INSERIRE NEL CALLOUT FINALE)")
    md_lines.append("")
    md_lines.append("Questi concetti sono stati citati tra le note del vault ma non dispongono ancora di una nota dedicata.")
    md_lines.append("Devi elencarli nel callout diagnostico `> [!todo] Diagnosi di Completezza (Fine Studio / Pre-Esame)` in fondo al MOC.\n")

    if not global_red_links:
        md_lines.append("*(Nessun link rosso rilevato: tutte le note citate esistono nel vault)*\n")
    else:
        md_lines.append("| Concetto Citato (\"Link Rosso\") | Citato Nelle Seguenti Note | Occorrenze |")
        md_lines.append("| :--- | :--- | :---: |")
        sorted_red = sorted(global_red_links.items(), key=lambda x: len(x[1]), reverse=True)
        for red_target, source_notes in sorted_red:
            sources_str = ", ".join([f"[[{sn}]]" for sn in source_notes])
            md_lines.append(f"| `[[{red_target}]]` | {sources_str} | {len(source_notes)} |")
        md_lines.append("")

    summary_content = "\n".join(md_lines)
    summary_file = context_dir / "vault_notes_summary.md"
    summary_file.write_text(summary_content, encoding="utf-8")

    # Salva anche in formato JSON strutturato
    summary_data = {
        "discipline": discipline_name,
        "topic": topic,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_notes": len(notes_analysis),
        "total_existing_links": len(global_existing_links),
        "total_red_links": len(global_red_links),
        "notes": notes_analysis,
        "global_red_links": global_red_links
    }
    (context_dir / "vault_notes_summary.json").write_text(
        json.dumps(summary_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    sys.stderr.write(f"[Orchestrator] Dossier note vault generato in: {summary_file} ({len(notes_analysis)} note, {len(global_red_links)} link rossi)\n")
    return summary_data


# ==============================================================================
# 3. PRE-PROCESSING DELLE FONTI (FAST SOURCE EXTRACT)
# ==============================================================================

def extract_notebooks_list(source_info: Dict[str, Any], job_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """
    Estrae e normalizza la lista di NotebookLM da job_data e source_info.
    Garantisce supporto completo sia al singolo notebook che a molteplici notebook contemporanei.
    Formato restituito: [{'id': str, 'title': str}, ...]
    """
    jdata = job_data or {}
    
    # 1. Dettagli completi strutturati
    raw_details = jdata.get("notebook_details") or source_info.get("notebook_details")
    if raw_details and isinstance(raw_details, list):
        res = []
        for item in raw_details:
            if isinstance(item, dict) and (item.get("id") or item.get("title")):
                nb_id = str(item.get("id") or item.get("title")).strip()
                nb_title = str(item.get("title") or item.get("id")).strip()
                res.append({"id": nb_id, "title": nb_title})
        if res:
            return res

    # 2. Array di ID/Nomi (job_data['notebooks'] = ["ID_1", "ID_2"])
    candidates = jdata.get("notebooks") or source_info.get("notebooks") or source_info.get("value")
    res = []
    if isinstance(candidates, list):
        for item in candidates:
            if isinstance(item, dict):
                nb_id = str(item.get("id") or item.get("title", "")).strip()
                nb_title = str(item.get("title") or item.get("id", "")).strip()
                if nb_id:
                    res.append({"id": nb_id, "title": nb_title})
            elif isinstance(item, str) and item.strip():
                clean_s = item.strip()
                res.append({"id": clean_s, "title": clean_s})
    elif isinstance(candidates, dict):
        nb_id = str(candidates.get("id") or candidates.get("title", "")).strip()
        nb_title = str(candidates.get("title") or candidates.get("id", "")).strip()
        if nb_id:
            res.append({"id": nb_id, "title": nb_title})
    elif isinstance(candidates, str) and candidates.strip():
        clean_s = candidates.strip()
        res.append({"id": clean_s, "title": clean_s})

    # 3. Fallback su notebook_id / notebook_title singoli
    if not res:
        single_id = jdata.get("notebook_id") or source_info.get("id")
        single_title = jdata.get("notebook_title") or source_info.get("title") or single_id
        if single_id:
            res.append({"id": str(single_id).strip(), "title": str(single_title).strip()})

    return res


def format_nlm_output(raw: str, include_quotes: bool = False, max_quote_chars: int = 12000) -> str:
    """
    Normalizza l'output JSON di `nlm query` in Markdown leggibile:
    - estrae il campo 'answer' e rimuove i suggerimenti di follow-up finali (righe 💡);
    - se include_quotes, accoda i passaggi VERBATIM citati dalle fonti (references.cited_text),
      deduplicati e limitati a max_quote_chars, come prova testuale primaria per l'agente.
    Se l'output non è JSON, viene restituito invariato.
    """
    text = (raw or "").strip()
    if not text.startswith("{"):
        return text
    try:
        data = json.loads(text)
    except Exception:
        return text
    answer = str(data.get("answer") or "").strip()
    answer = "\n".join(l for l in answer.splitlines() if not l.strip().startswith("💡")).strip()
    if not include_quotes:
        return answer
    quotes: List[str] = []
    seen = set()
    total = 0
    for ref in data.get("references") or []:
        cited = re.sub(r"\s+", " ", str(ref.get("cited_text") or "")).strip()
        if len(cited) < 40 or cited in seen:
            continue
        if total + len(cited) > max_quote_chars:
            break
        seen.add(cited)
        total += len(cited)
        quotes.append(f"> [{ref.get('citation_number', '?')}] {cited}")
    if quotes:
        answer += "\n\n**Passaggi verbatim citati dalle fonti del notebook:**\n" + "\n>\n".join(quotes)
    return answer


def query_nlm_parallel(
    tasks: List[Tuple[Any, str, str]],
    timeout_sec: int = 180,
    include_quotes: bool = False,
    max_workers: int = 6,
    on_progress=None,
) -> Dict[Any, str]:
    """Esegue più query nlm contemporaneamente. tasks = [(chiave, nb_id, prompt)] -> {chiave: testo}.
    `on_progress(fatte, totali)` viene chiamata all'avvio e a ogni risposta ricevuta."""
    results: Dict[Any, str] = {}
    if not tasks:
        return results
    if on_progress:
        on_progress(0, len(tasks))
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, len(tasks))) as pool:
        futures = {
            pool.submit(query_nlm_cli, nb_id, prompt, timeout_sec, include_quotes): key
            for key, nb_id, prompt in tasks
        }
        for fut in concurrent.futures.as_completed(futures):
            try:
                results[futures[fut]] = fut.result()
            except Exception as e:
                sys.stderr.write(f"[Orchestrator] Eccezione query parallela nlm: {e}\n")
                results[futures[fut]] = ""
            if on_progress:
                try:
                    on_progress(len(results), len(tasks))
                except Exception:
                    pass
    return results


# Limite a breve termine di NotebookLM: troppe query insieme vengono rifiutate per qualche minuto
# anche con la quota settimanale libera. Le query di tutti i processi (batch con più note in
# parallelo) passano da pochi posti condivisi e, se una viene rifiutata, tutte si fermano insieme.
NLM_SHARED_DIR = Path("/tmp/antigravity_nlm")
NLM_MAX_CONCURRENT = 3
NLM_RATE_LIMIT_WAITS = (45,)  # attese brevi: se il limite dura, la nota torna al batch, che aspetta in modo visibile
NLM_RATE_LIMIT_MARKERS = ("usage limit", "temporarily rejected", "rate limit", "too many requests", "resource_exhausted")
NLM_RATE_LIMITED = False  # vero se almeno una query è rimasta senza risposta per il limite
RATE_LIMIT_ERROR = "⏳ NotebookLM ha raggiunto il limite di utilizzo temporaneo (troppe query ravvicinate)."


NLM_LIMIT_MEMORY = 600  # per 10 minuti dopo un rifiuto definitivo non si richiede la chat


def _nlm_cooldown_file() -> Path:
    return NLM_SHARED_DIR / "cooldown-until"


def _nlm_limited_recently() -> bool:
    try:
        return time.time() - float((NLM_SHARED_DIR / "limited-at").read_text().strip()) < NLM_LIMIT_MEMORY
    except Exception:
        return False


def _mark_nlm_limited() -> None:
    try:
        NLM_SHARED_DIR.mkdir(parents=True, exist_ok=True)
        (NLM_SHARED_DIR / "limited-at").write_text(str(time.time()))
    except Exception:
        pass


def _wait_nlm_cooldown() -> None:
    try:
        until = float(_nlm_cooldown_file().read_text().strip() or 0)
    except Exception:
        return
    while time.time() < until:
        time.sleep(min(15, max(1, until - time.time())))


def _set_nlm_cooldown(seconds: int) -> None:
    try:
        NLM_SHARED_DIR.mkdir(parents=True, exist_ok=True)
        f = _nlm_cooldown_file()
        try:
            current = float(f.read_text().strip() or 0)
        except Exception:
            current = 0
        f.write_text(str(max(current, time.time() + seconds)))
    except Exception:
        pass


class _NlmSlot:
    """Uno dei NLM_MAX_CONCURRENT posti condivisi tra processi (lock fcntl su file)."""

    def __enter__(self):
        import fcntl
        NLM_SHARED_DIR.mkdir(parents=True, exist_ok=True)
        while True:
            for i in range(NLM_MAX_CONCURRENT):
                fh = open(NLM_SHARED_DIR / f"slot-{i}.lock", "w")
                try:
                    fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.fh = fh
                    return self
                except OSError:
                    fh.close()
            time.sleep(0.5)

    def __exit__(self, *exc):
        import fcntl
        try:
            fcntl.flock(self.fh, fcntl.LOCK_UN)
        finally:
            self.fh.close()


def query_nlm_cli(nb_id: str, prompt: str, timeout_sec: int = 180, include_quotes: bool = False) -> str:
    """
    Interroga NotebookLM tramite la CLI nlm gestendo fallback sintattici e timeout.
    Ogni query apre una conversazione nuova (--new-conversation): le query parallele non
    condividono la chat del notebook e non si contaminano a vicenda tra note diverse.
    Se NotebookLM rifiuta per il limite a breve termine, aspetta e riprova (NLM_RATE_LIMIT_WAITS).
    """
    global NLM_RATE_LIMITED
    if not nb_id or nb_id == "N/D":
        return ""
    if _nlm_limited_recently():
        NLM_RATE_LIMITED = True
        return ""

    commands = [
        ["nlm", "query", "notebook", nb_id, prompt, "--new-conversation", "--timeout", str(timeout_sec)],
        ["nlm", "query", "notebook", nb_id, prompt, "--timeout", str(timeout_sec)],
        ["nlm", "query", "notebook", nb_id, prompt],
    ]
    for wait in (*NLM_RATE_LIMIT_WAITS, None):
        rate_limited = False
        for cmd in commands:
            _wait_nlm_cooldown()
            try:
                with _NlmSlot():
                    proc = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout_sec + 15,
                        check=False
                    )
                out = proc.stdout.strip()
                err = proc.stderr.strip()
                combined_msg = f"{out} {err}".lower()
                if any(k in combined_msg for k in NLM_RATE_LIMIT_MARKERS):
                    rate_limited = True
                    break
                if any(k in combined_msg for k in ["authentication expired", "authentication failed", "run 'nlm login'", "query failed"]):
                    sys.stderr.write(f"[Orchestrator] Avviso: nlm errore/auth scaduta per {nb_id}: {out or err}\n")
                    return ""
                if proc.returncode == 0 and out:
                    return format_nlm_output(out, include_quotes=include_quotes)
            except subprocess.TimeoutExpired:
                sys.stderr.write(f"[Orchestrator] Timeout ({timeout_sec}s) interrogazione nlm per {nb_id}.\n")
            except Exception as e:
                sys.stderr.write(f"[Orchestrator] Eccezione comando nlm: {e}\n")
        if not rate_limited:
            return ""
        if wait is None:
            NLM_RATE_LIMITED = True
            _mark_nlm_limited()
            sys.stderr.write(f"[Orchestrator] NotebookLM ancora al limite di utilizzo per {nb_id}: rinuncio.\n")
            return ""
        sys.stderr.write(f"[Orchestrator] NotebookLM al limite di utilizzo: pausa di {wait}s e nuovo tentativo.\n")
        _set_nlm_cooldown(wait)
    return ""


def local_source_passages(nb_id: str, topic: str, extra: List[str], max_chars: int = 45000) -> str:
    """Ripiego quando la chat NotebookLM è al limite: passaggi pertinenti presi dal testo originale
    delle fonti del notebook (nlm_local, cache sul Mac). Stringa vuota se non c'è nulla."""
    try:
        import nlm_local
        return nlm_local.format_passages(nlm_local.search([nb_id], topic, extra, max_chars=max_chars))
    except Exception as e:
        sys.stderr.write(f"[Orchestrator] Testo locale delle fonti non disponibile per {nb_id}: {e}\n")
        return ""


def extract_syllabus_content(
    syllabus_files: List[str],
    syllabus_text: str,
    vault_root: Path,
    tools_dir: Path,
) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, str]]]:
    """
    Estrae e combina il testo da file allegati (.pdf, .txt, .md) e testo incollato (A ∪ B),
    dando a entrambi lo stesso identico peso.
    Se un singolo file fallisce, gli errori non vengono inghiottiti: vengono tracciati con
    traceback e si continua con i file successivi.
    """
    sections: List[str] = []
    file_metadata: List[Dict[str, Any]] = []
    failed_files: List[Dict[str, str]] = []

    # 1. Estrazione dai file allegati
    for fentry in syllabus_files:
        if not fentry:
            continue
        fpath = Path(fentry)
        if not fpath.is_absolute():
            fpath = vault_root / fpath

        if not fpath.exists():
            msg = f"File traccia non trovato su disco: {fentry}"
            sys.stderr.write(f"[Orchestrator] Avviso: {msg}\n")
            failed_files.append({"file": str(fentry), "error": msg})
            continue

        ext = fpath.suffix.lower()
        extracted_text = ""
        try:
            if ext == ".pdf":
                sys.stderr.write(f"[Orchestrator] Estrazione testo PDF da {fpath.name} con pdf_extract.py...\n")
                res = run_tool_script("pdf_extract.py", [str(fpath), "--json"], tools_dir)
                if res.returncode == 0 and res.stdout.strip():
                    try:
                        pdf_data = json.loads(res.stdout)
                        page_texts = [p.get("text", "").strip() for p in pdf_data.get("pages", []) if p.get("text", "").strip()]
                        extracted_text = "\n\n".join(page_texts)
                    except Exception as json_err:
                        sys.stderr.write(f"[Orchestrator] Fallback testo grezzo da pdf_extract per {fpath.name}: {json_err}\n")
                        extracted_text = res.stdout.strip()
                else:
                    err_msg = res.stderr.strip()[:300] or f"Exit code {res.returncode}"
                    sys.stderr.write(f"[Orchestrator] Errore estrazione pdf_extract per {fpath.name}: {err_msg}\n")
                    failed_files.append({"file": fpath.name, "error": err_msg})
            elif ext in [".txt", ".md", ".json", ".csv"]:
                extracted_text = fpath.read_text(encoding="utf-8", errors="replace").strip()
            else:
                extracted_text = fpath.read_text(encoding="utf-8", errors="replace").strip()
        except Exception as e:
            sys.stderr.write(f"[Orchestrator] Eccezione lettura file traccia {fpath.name}: {e}\n")
            traceback.print_exc(file=sys.stderr)
            failed_files.append({"file": fpath.name, "error": str(e)})

        if extracted_text:
            sections.append(f"### 📄 Traccia File: `{fpath.name}`\n{extracted_text}")
            file_metadata.append({"file": fpath.name, "path": str(fpath), "chars": len(extracted_text)})

    # 2. Testo incollato manualmente (Finestra Multi-Riga)
    if syllabus_text and syllabus_text.strip():
        sections.append(f"### 📋 Traccia Incollata (Indice Libro / Diario Lezioni)\n{syllabus_text.strip()}")

    combined = "\n\n".join(sections).strip()
    return combined, file_metadata, failed_files


CHAPTER_LINE = re.compile(
    r"^\s*(?:#{1,2}\s+)?(?:(?:capitolo|cap\.?|chapter|parte|unità|unita|modulo)\s+)?(\d{1,2}|[IVXLC]{1,6})(?:[.)]|\s+[-–—:]?)\s*(?=[A-ZÀ-Ýa-z])",
    re.IGNORECASE,
)
SUBSECTION_LINE = re.compile(r"^\s*(?:#{3,}\s+)?\d{1,2}\.\d")


def partition_index_into_chapters(text: str, max_blocks: int = 15) -> List[Dict[str, str]]:
    """Divide l'indice del libro ai confini reali dei capitoli (righe "3 Limiti", "Capitolo 3", "## 3. ...",
    non i paragrafi "3.2"). Capitoli consecutivi vengono uniti solo se sono più di `max_blocks`.
    Se l'indice non ha capitoli riconoscibili ricade su partition_syllabus_into_blocks."""
    lines = [l.rstrip() for l in text.splitlines()]
    starts = [i for i, l in enumerate(lines) if l.strip() and CHAPTER_LINE.match(l) and not SUBSECTION_LINE.match(l)]
    if not (3 <= len(starts) <= 60):
        return partition_syllabus_into_blocks(text, min_blocks=8, max_blocks=max_blocks)
    chapters = []
    for k, start in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(lines)
        body = "\n".join(lines[start:end]).strip()
        title = re.sub(r"^[#\s]*", "", lines[start]).strip()
        chapters.append({"title": title[:80], "content": body})
    preface = "\n".join(lines[:starts[0]]).strip()
    if preface and len(preface) > 200:
        chapters.insert(0, {"title": "Introduzione e prerequisiti", "content": preface})
    if len(chapters) <= max_blocks:
        return chapters
    # Troppi capitoli: si uniscono gruppi consecutivi di dimensione simile, mai più di max_blocks
    target = sum(len(c["content"]) for c in chapters) / max_blocks
    groups: List[List[Dict[str, str]]] = []
    current: List[Dict[str, str]] = []
    acc = 0
    for ch in chapters:
        current.append(ch)
        acc += len(ch["content"])
        if acc >= (len(groups) + 1) * target and len(groups) < max_blocks - 1:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return [{"title": (g[0]["title"] if len(g) == 1 else f"{g[0]['title']} – {g[-1]['title']}")[:120],
             "content": "\n\n".join(c["content"] for c in g)} for g in groups]


def partition_syllabus_into_blocks(text: str, min_blocks: int = 8, max_blocks: int = 15) -> List[Dict[str, str]]:
    """
    Partiziona l'indice o la traccia risultante in 8-15 blocchi logici o moduli tematici.
    Preserva il 100% del testo senza perdite o omissioni.
    """
    lines = [l.rstrip() for l in text.splitlines()]
    non_empty = [l for l in lines if l.strip()]
    if not non_empty:
        return [{"title": f"Modulo {i+1}", "content": f"Modulo didattico {i+1}"} for i in range(min_blocks)]

    # Cerca separatori naturali (Capitoli, Moduli, Lezioni, Settimane, numeri, intestazioni Markdown)
    pattern = re.compile(r"^(#+\s+|(?:\d+[\.\)]|capitolo|modulo|lezione|parte|unità|settimana|topic)\b)", re.IGNORECASE)
    section_indices = [i for i, line in enumerate(lines) if line.strip() and pattern.match(line.strip())]

    if len(section_indices) >= min_blocks and len(section_indices) <= max_blocks * 2:
        target_k = min(max_blocks, max(min_blocks, len(section_indices)))
        step = len(section_indices) / target_k
        chosen_indices = [section_indices[int(i * step)] for i in range(target_k)]
        chosen_indices = sorted(list(set(chosen_indices)))
    elif len(section_indices) > max_blocks * 2:
        target_k = max_blocks
        step = len(section_indices) / target_k
        chosen_indices = [section_indices[int(i * step)] for i in range(target_k)]
        chosen_indices = sorted(list(set(chosen_indices)))
    else:
        total_items = len(non_empty)
        target_k = min(max_blocks, max(min_blocks, min(total_items, 10)))
        step = total_items / target_k
        chosen_items = [int(i * step) for i in range(target_k)]
        chosen_indices = []
        cur_non_empty = 0
        for i, l in enumerate(lines):
            if l.strip():
                if cur_non_empty in chosen_items:
                    chosen_indices.append(i)
                cur_non_empty += 1

    if not chosen_indices or chosen_indices[0] != 0:
        chosen_indices.insert(0, 0)
    chosen_indices = sorted(list(set(chosen_indices)))

    blocks = []
    for b_idx in range(len(chosen_indices)):
        start = chosen_indices[b_idx]
        end = chosen_indices[b_idx + 1] if b_idx + 1 < len(chosen_indices) else len(lines)
        block_lines = lines[start:end]
        block_text = "\n".join(block_lines).strip()
        if not block_text:
            continue

        first_line = ""
        for bl in block_lines:
            if bl.strip():
                first_line = re.sub(r"^[#\*\-\s\d\.\)]+", "", bl.strip()).strip()
                break
        if not first_line:
            first_line = f"Parte {len(blocks) + 1}"
        if len(first_line) > 60:
            first_line = first_line[:57] + "..."

        blocks.append({
            "title": f"Modulo {len(blocks) + 1}: {first_line}",
            "content": block_text
        })

    # Se per brevità del testo i blocchi risultanti fossero inferiori a min_blocks, dividi per righe non vuote
    if len(blocks) < min_blocks and len(non_empty) >= min_blocks:
        blocks = []
        target_k = min(max_blocks, max(min_blocks, len(non_empty)))
        step = len(non_empty) / target_k
        for i in range(target_k):
            s_idx = int(i * step)
            e_idx = int((i + 1) * step) if i + 1 < target_k else len(non_empty)
            sub_lines = non_empty[s_idx:e_idx]
            first_l = re.sub(r"^[#\*\-\s\d\.\)]+", "", sub_lines[0].strip()).strip() if sub_lines else f"Modulo {i+1}"
            blocks.append({
                "title": f"Modulo {i+1}: {first_l[:55]}",
                "content": "\n".join(sub_lines)
            })

    # Garanzia assoluta range 8-15 blocchi tematici/moduli
    if len(blocks) < min_blocks:
        expanded = []
        base_content = text.strip() if text.strip() else "Argomenti e fondamenti del corso"
        sub_topics = [
            "Fondamenti Teorici e Definizioni di Base",
            "Assiomi, Proprietà e Strutture Preliminari",
            "Teoremi Principali e Proposizioni Cardine",
            "Dimostrazioni Chiave ed Enunciati Formali",
            "Metodi Risolutivi e Algoritmi Operativi",
            "Tipologie di Esercizi d'Esame e Casi Studio",
            "Corollari, Casi Particolari ed Eccezioni",
            "Connessioni Avanzate e Visione d'Insieme"
        ]
        for i in range(min_blocks):
            sub_label = sub_topics[i] if i < len(sub_topics) else f"Approfondimento {i+1}"
            expanded.append({
                "title": f"Modulo {i+1}: {sub_label}",
                "content": f"{base_content}\nFocus Didattico: {sub_label}"
            })
        return expanded

    return blocks


def process_source_fast(
    source_info: Dict[str, Any],
    vault_root: Path,
    allegati_dir: Path,
    context_dir: Path,
    tools_dir: Path,
    job_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Elabora la fonte selezionata usando `fast_source_extract.py` per massimizzare
    velocità e fedeltà (YouTube in 0.3s + FFmpeg parallelo; Web con trafilatura).
    Supporta inoltre le 3 modalità MOC:
    - start_notebooklm: estrazione architettura concettuale da NotebookLM + cross-reference con il vault
    - start_base_knowledge: estrazione note affini dal vault per roadmap da zero
    - end_vault_consolidation: scansione completa e diagnosi link rossi
    """
    stype = source_info.get("type", "none")
    sval = source_info.get("value")
    result: Dict[str, Any] = {
        "source_type": stype,
        "label": source_info.get("label", ""),
        "extracted_files": [],
        "content_markdown": "",
        "raw_source_text": "",
        "metadata": None,
        "target_content": "",
    }

    # Intercetta il tipo operazione e le modalità specifiche
    op_type = job_data.get("operation_type") or job_data.get("operation", "normal") if job_data else "normal"
    moc_mode = job_data.get("moc_mode") if job_data else None
    edit_mode = job_data.get("edit_mode") if job_data else None

    # Gestione specifica per Operazione di Modifica / Miglioramento Nota Esistente (op_type == "edit")
    if op_type == "edit":
        target_rel = job_data.get("target_file_path", "")
        target_path = (vault_root / target_rel) if target_rel else None
        target_content = ""
        if target_path and target_path.exists():
            try:
                target_content = target_path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                target_content = f"*(Errore lettura target note: {e})*"
        elif job_data.get("target_file_abs"):
            abs_p = Path(job_data.get("target_file_abs"))
            if abs_p.exists():
                try:
                    target_content = abs_p.read_text(encoding="utf-8", errors="replace")
                except Exception as e:
                    target_content = f"*(Errore lettura target note: {e})*"

        result["target_content"] = target_content

        # Salva copia nel context
        if target_content:
            (context_dir / "target_note_before_edit.md").write_text(target_content, encoding="utf-8")

        # Nelle modalità diverse da merge_source, la nota target stessa è la fonte primaria
        if edit_mode != "merge_source":
            result["content_markdown"] = target_content
            result["raw_source_text"] = target_content
            result["metadata"] = {
                "edit_mode": edit_mode,
                "target_file": target_rel,
                "user_instructions": job_data.get("user_instructions", "")
            }
            return result

    # MOC Modalità 3: Fine Studio / Consolidamento Note del Vault
    if stype == "vault_consolidation" or (op_type == "moc" and moc_mode == "end_vault_consolidation"):
        discipline_name = job_data.get("discipline", "") if job_data else ""
        topic = job_data.get("topic", "") if job_data else ""
        sys.stderr.write(f"[Orchestrator] Avvio scansione vault e diagnosi link rossi per {discipline_name} / {topic}...\n")
        summary_data = build_vault_notes_summary(
            vault_root=vault_root,
            discipline_name=discipline_name,
            topic=topic,
            context_dir=context_dir
        )
        summary_md_file = context_dir / "vault_notes_summary.md"
        if summary_md_file.exists():
            result["content_markdown"] = summary_md_file.read_text(encoding="utf-8")
        result["raw_source_text"] = f"{discipline_name} {topic} {len(summary_data.get('notes', []))} note"
        result["metadata"] = summary_data
        return result

    # MOC Modalità 2: Inizio Studio da Conoscenza Base di Antigravity
    if stype == "base_knowledge" or (op_type == "moc" and moc_mode == "start_base_knowledge"):
        discipline_name = job_data.get("discipline", "") if job_data else ""
        topic = job_data.get("topic", "") if job_data else ""
        sys.stderr.write(f"[Orchestrator] Estrazione note per MOC da Conoscenza Base ({discipline_name})...\n")

        vault_index_file = resolve_vault_index_path(vault_root)
        existing_discipline_notes = []
        if vault_index_file.exists():
            try:
                v_idx = json.loads(vault_index_file.read_text(encoding="utf-8"))
                for entry in v_idx:
                    d = entry.get("disciplina", "")
                    if d.lower() == discipline_name.lower() or discipline_name.lower() in d.lower():
                        existing_discipline_notes.append(entry.get("title", ""))
            except Exception:
                pass

        note_list_md = "\n".join([f"- `[[{t}]]`" for t in existing_discipline_notes]) if existing_discipline_notes else "*(Nessuna nota ancora creata nel vault per questa disciplina)*"

        result["content_markdown"] = (
            f"# 🧠 MOC di Inizio Studio — Da Conoscenza Base di Antigravity\n"
            f"- **Disciplina:** `{discipline_name}`\n"
            f"- **Argomento MOC:** `{topic}`\n\n"
            f"## 📋 Note già Presenti nel Vault per questa Disciplina\n"
            f"{note_list_md}\n\n"
            f"> [!IMPORTANT] Vincolo Operativo di Inizio Studio:\n"
            f"> Utilizza la tua conoscenza di base universitaria per progettare da zero una **roadmap accademica "
            f"completa, rigorosa e discorsiva** sull'argomento.\n"
            f"> - Usa i titoli esatti per le note già presenti nel vault indicate sopra.\n"
            f"> - Crea i `[[wikilink]]` pianificati per tutti i concetti, teoremi e metodi futuri necessari per padroneggiare la materia.\n"
            f"> - Il MOC deve essere pienamente discorsivo e ragionante, senza elenchi puntati sterili.\n"
        )
        result["raw_source_text"] = f"{discipline_name} {topic} roadmap da zero"
        return result

    # 1. Fonte YouTube (Sinergia: youtube-transcript-api in 0.3s + claude-watch / FFmpeg)
    if stype == "youtube" or (isinstance(sval, str) and ("youtube.com" in sval or "youtu.be" in sval)):
        url = sval if isinstance(sval, str) else str(sval)
        sys.stderr.write(f"[Orchestrator] Esecuzione rapida fast_source_extract.py su YouTube: {url}...\n")
        res = run_tool_script(
            "fast_source_extract.py",
            ["youtube", url, "--max-frames", "10", "--out-dir", str(allegati_dir), "--json"],
            tools_dir,
        )
        if res.returncode == 0 and res.stdout.strip():
            try:
                yt_data = json.loads(res.stdout)
                result["metadata"] = {
                    "video_id": yt_data.get("video_id"),
                    "title": yt_data.get("title"),
                    "author": yt_data.get("author"),
                    "duration": yt_data.get("duration"),
                    "transcript_source": yt_data.get("transcript_source")
                }
                result["extracted_files"] = [f["filename"] for f in yt_data.get("frames", [])]
                result["content_markdown"] = yt_data.get("synchronized_markdown", "")
                result["raw_source_text"] = yt_data.get("transcript_text", "")
                (context_dir / "youtube_data.json").write_text(res.stdout, encoding="utf-8")
            except Exception as e:
                result["content_markdown"] = res.stdout
                result["raw_source_text"] = res.stdout
        else:
            sys.stderr.write(f"[Orchestrator] Warning YouTube extract: {res.stderr[:250]}\n")
            result["content_markdown"] = f"Fonte YouTube: {url}\n\n{res.stdout}\n{res.stderr}"
            result["raw_source_text"] = res.stdout

    # 2. Fonte Sito Web (trafilatura pulito + fallback jina.ai)
    elif stype == "web":
        url = sval if isinstance(sval, str) else ""
        sys.stderr.write(f"[Orchestrator] Esecuzione trafilatura via fast_source_extract.py: {url}...\n")
        res = run_tool_script(
            "fast_source_extract.py",
            ["web", url, "--json"],
            tools_dir,
        )
        if res.returncode == 0 and res.stdout.strip():
            try:
                web_data = json.loads(res.stdout)
                result["metadata"] = {
                    "url": web_data.get("url"),
                    "title": web_data.get("title"),
                    "source": web_data.get("source"),
                    "char_count": web_data.get("char_count")
                }
                result["content_markdown"] = f"# {web_data.get('title')}\n\n**Fonte**: {url}\n\n---\n\n{web_data.get('markdown')}"
                result["raw_source_text"] = web_data.get("markdown", "")
                (context_dir / "web_data.json").write_text(res.stdout, encoding="utf-8")
            except Exception:
                result["content_markdown"] = res.stdout
                result["raw_source_text"] = res.stdout
        else:
            result["content_markdown"] = f"Fonte Web: {url}\n\n{res.stdout}\n{res.stderr}"
            result["raw_source_text"] = res.stdout

    # 3. Fonte File Locali / PDF / Appunti
    elif stype in ["local_files", "vault_files", "vault_file"]:
        file_list = sval if isinstance(sval, list) else [sval]
        text_blocks: List[str] = []
        raw_accum: List[str] = []
        for file_entry in file_list:
            if not file_entry:
                continue
            fpath = Path(file_entry)
            if not fpath.is_absolute():
                fpath = vault_root / fpath

            if not fpath.exists():
                text_blocks.append(f"*(File non trovato: {file_entry})*")
                continue

            if fpath.suffix.lower() == ".pdf":
                sys.stderr.write(f"[Orchestrator] Esecuzione pdf_extract.py su {fpath.name}...\n")
                res = run_tool_script(
                    "pdf_extract.py",
                    [str(fpath), "--out-dir", str(allegati_dir), "--json"],
                    tools_dir,
                )
                if res.returncode == 0 and res.stdout.strip():
                    try:
                        pdf_data = json.loads(res.stdout)
                        for im in pdf_data.get("images", []):
                            result["extracted_files"].append(im["filename"])

                        pdf_md = [f"## 📄 Contenuto Estratto dal PDF: {fpath.name}\n"]
                        for p in pdf_data.get("pages", []):
                            pdf_md.append(f"\n--- PAGINA {p['page']} ---")
                            for im in p.get("images", []):
                                pdf_md.append(f"![[{im['filename']}]]")
                            if p.get("text"):
                                pdf_md.append(p["text"])
                                raw_accum.append(p["text"])
                        text_blocks.append("\n".join(pdf_md))
                    except Exception:
                        text_blocks.append(res.stdout)
                else:
                    text_blocks.append(f"Errore estrazione PDF {fpath.name}: {res.stderr}")

            elif fpath.suffix.lower() in [".m4a", ".mp3", ".wav", ".aac", ".ogg", ".flac", ".m4b"]:
                sys.stderr.write(f"[Orchestrator] File audio rilevato: esecuzione audio_transcribe.py su {fpath.name}...\n")
                res = run_tool_script(
                    "audio_transcribe.py",
                    [str(fpath), "--out-dir", str(context_dir), "--json"],
                    tools_dir,
                )
                if res.returncode == 0 and res.stdout.strip():
                    try:
                        audio_data = json.loads(res.stdout)
                        transcript_md = audio_data.get("transcript_markdown", "") or audio_data.get("raw_text", "")
                        text_blocks.append(transcript_md)
                        raw_accum.append(audio_data.get("raw_text", ""))
                    except Exception:
                        text_blocks.append(res.stdout)
                        raw_accum.append(res.stdout)
                else:
                    text_blocks.append(f"Errore trascrizione audio {fpath.name}: {res.stderr}")

            elif fpath.suffix.lower() in [".md", ".txt", ".json", ".csv"]:
                try:
                    c = fpath.read_text(encoding="utf-8", errors="replace")
                    text_blocks.append(f"## 📄 File: {fpath.name}\n\n{c}")
                    raw_accum.append(c)
                except Exception as e:
                    text_blocks.append(f"Errore lettura {fpath.name}: {e}")

            elif fpath.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
                result["extracted_files"].append(fpath.name)
                text_blocks.append(f"## 🖼️ Allegato Immagine per Ispezione: `{fpath.name}`\n![[{fpath.name}]]")

        result["content_markdown"] = "\n\n".join(text_blocks)
        result["raw_source_text"] = "\n".join(raw_accum)

    # 3.5. Fonte Audio Dedicata (Lezione / Registrazione Vocale)
    elif stype in ["audio", "audio_file", "audio_recording", "sbobinatura", "voice"]:
        fpath = Path(sval) if isinstance(sval, str) else Path(str(sval))
        if not fpath.is_absolute():
            fpath = vault_root / fpath
        if fpath.exists():
            sys.stderr.write(f"[Orchestrator] Trascrizione audio MLX su {fpath.name}...\n")
            res = run_tool_script(
                "audio_transcribe.py",
                [str(fpath), "--out-dir", str(context_dir), "--json"],
                tools_dir,
            )
            if res.returncode == 0 and res.stdout.strip():
                try:
                    audio_data = json.loads(res.stdout)
                    result["content_markdown"] = audio_data.get("transcript_markdown", "")
                    result["raw_source_text"] = audio_data.get("raw_text", "")
                except Exception:
                    result["content_markdown"] = res.stdout
                    result["raw_source_text"] = res.stdout
            else:
                result["content_markdown"] = f"Errore trascrizione audio: {res.stderr}"
        else:
            result["content_markdown"] = f"*(File audio non trovato: {fpath})*"

    # 4. Fonte NotebookLM (Singolo o Multiplo: Fusione di Fonti Cross-Notebook)
    elif stype in ["notebooklm", "notebooklm_manual"]:
        notebooks_list = extract_notebooks_list(source_info, job_data)
        if not notebooks_list:
            notebooks_list = [{"id": "N/D", "title": "NotebookLM Non Specificato"}]

        is_multi = len(notebooks_list) > 1
        topic_clean = (job_data.get("topic") if job_data else "") or "l'argomento selezionato"
        op_type = (job_data.get("operation_type") or job_data.get("operation") if job_data else "normal")
        target_rel = job_data.get("target_file_path", "") if job_data else ""

        # =====================================================================
        # RAMO SPECIALE: MOC DI INIZIO STUDIO DA NOTEBOOKLM (SCANSIONE PROFONDA)
        # =====================================================================
        if op_type == "moc" and moc_mode == "start_notebooklm":
            jd = job_data or {}
            # Indice del libro = spina dorsale (moduli, ordine, perimetro); diario = integrazione facoltativa.
            # I job vecchi hanno solo syllabus_text/files: vengono trattati come indice.
            has_split = any(k in jd for k in ("syllabus_index_text", "syllabus_index_files", "syllabus_diary_text", "syllabus_diary_files"))
            index_files = jd.get("syllabus_index_files", []) if has_split else jd.get("syllabus_files", [])
            index_paste = jd.get("syllabus_index_text", "") if has_split else jd.get("syllabus_text", "")
            diary_files = jd.get("syllabus_diary_files", []) if has_split else []
            diary_paste = jd.get("syllabus_diary_text", "") if has_split else ""
            syllabus_text = "\n\n".join(t for t in (index_paste, diary_paste) if t)
            syllabus_files = list(index_files) + list(diary_files)

            # 1. Lettura dei file allegati e del testo incollato
            index_text, index_meta, failed_files = extract_syllabus_content(
                syllabus_files=index_files, syllabus_text=index_paste, vault_root=vault_root, tools_dir=tools_dir)
            diary_text, diary_meta, diary_failed = extract_syllabus_content(
                syllabus_files=diary_files, syllabus_text=diary_paste, vault_root=vault_root, tools_dir=tools_dir)
            failed_files += diary_failed
            syllabus_meta = index_meta + diary_meta

            if failed_files:
                for ff in failed_files:
                    sys.stderr.write(f"[Orchestrator] Avviso: Impossibile caricare il file traccia '{ff['file']}': {ff['error']}\n")

            if syllabus_files and not (index_text.strip() or diary_text.strip()):
                err_detail = "; ".join(f"{ff['file']}: {ff['error']}" for ff in failed_files) or "Nessun file valido"
                sys.stderr.write(f"[Orchestrator] ERRORE CRITICO: Tutti i file traccia sono falliti: {err_detail}\n")
                update_status(
                    vault_root=vault_root,
                    percent=0,
                    step_number=0,
                    total_steps=6,
                    status="error",
                    message="❌ Errore lettura file traccia (Indice/Diario)",
                    detail=f"File illeggibili: {err_detail[:150]}",
                    target_file=target_rel,
                    error=err_detail
                )
                raise RuntimeError(f"Tutti i file traccia sono falliti: {err_detail}")

            scope_label = "indice del libro" if index_text.strip() else ("diario delle lezioni" if diary_text.strip() else "intero notebook")
            prelim_docs = ""
            # 2. Nessuna traccia: indice generale chiesto a NotebookLM (l'elenco documenti resta solo nel dossier)
            if not index_text.strip() and not diary_text.strip():
                sys.stderr.write("[Orchestrator] Nessuna traccia manuale: indice e documenti chiesti a NotebookLM...\n")
                update_status(
                    vault_root=vault_root,
                    percent=26,
                    step_number=2,
                    total_steps=6,
                    message="🔍 Indice generale e documenti da NotebookLM",
                    detail=f"Nessun indice allegato: il MOC copre tutto il notebook ({topic_clean})",
                    status="running",
                    target_file=target_rel,
                )
                prelim_tasks = []
                for nb_idx, nb in enumerate(notebooks_list):
                    prelim_tasks.append(((nb_idx, "docs"), nb["id"], "Elenca tutti i documenti, capitoli e fonti presenti in questo notebook con i rispettivi titoli e descrizioni sintetiche."))
                    prelim_tasks.append(((nb_idx, "index"), nb["id"], f"Fornisci l'indice generale dettagliato degli argomenti trattati nelle fonti di questo notebook per la materia '{topic_clean}', diviso in capitoli numerati (una riga per capitolo nel formato '1. Titolo', seguita dai suoi paragrafi '1.1 ...')."))
                prelim_answers = query_nlm_parallel(prelim_tasks)
                index_parts, docs_parts = [], []
                for nb_idx, nb in enumerate(notebooks_list):
                    if prelim_answers.get((nb_idx, "docs")):
                        docs_parts.append(f"### Documenti del notebook `{nb['title']}`\n{prelim_answers[(nb_idx, 'docs')]}")
                    if prelim_answers.get((nb_idx, "index")):
                        index_parts.append(prelim_answers[(nb_idx, "index")])
                index_text = "\n\n".join(index_parts) or f"Argomenti e concetti fondamentali per lo studio di {topic_clean}."
                prelim_docs = "\n\n".join(docs_parts)

            # 3. Moduli: capitoli dell'indice (o del diario se manca l'indice); il diario diventa un blocco aggiuntivo
            if index_text.strip():
                blocks = partition_index_into_chapters(index_text, max_blocks=15)
                if diary_text.strip():
                    blocks.append({"title": "Argomenti del diario delle lezioni", "content": diary_text[:12000]})
            else:
                blocks = partition_index_into_chapters(diary_text, max_blocks=15)
            combined_syllabus = "\n\n".join(part for part in (
                f"### Indice del libro (spina dorsale del MOC)\n{index_text}" if index_text.strip() else "",
                f"### Diario delle lezioni (integrazione)\n{diary_text}" if diary_text.strip() else "",
                prelim_docs,
            ) if part)
            total_blocks = len(blocks)
            sys.stderr.write(f"[Orchestrator] Perimetro: {scope_label}; {total_blocks} moduli da interrogare.\n")

            # 4. Multi-Query su nlm per ciascun blocco, tutte in parallelo
            block_extractions: List[str] = []
            raw_text_parts: List[str] = []
            allow_base_moc = bool(
                (job_data or {}).get("allow_base_knowledge", False)
                or source_info.get("allow_base_knowledge", False)
            )

            def block_query_prompt(block_content: str) -> str:
                return (
                    f"Analizza a fondo tutte le fonti di questo notebook relative a questi punti dell'indice e del diario delle lezioni:\n"
                    f"{block_content}\n\n"
                    "Estrai senza omettere nulla:\n"
                    "1) Ogni singolo Concetto e Definizione;\n"
                    "2) Ogni singolo Teorema, Proposizione, Lemma e Corollario;\n"
                    "3) Ogni singolo Metodo risolutivo e tipologia di esercizio d'esame;\n"
                    "4) L'ordine logico e i collegamenti tra essi."
                )

            update_status(
                vault_root=vault_root,
                percent=30,
                step_number=2,
                total_steps=6,
                message=f"📥 Scansione NotebookLM in parallelo: {total_blocks} moduli × {len(notebooks_list)} notebook...",
                detail=f"{total_blocks * len(notebooks_list)} query nlm contemporanee",
                status="running",
                target_file=target_rel,
            )
            sys.stderr.write(f"[Orchestrator] Scansione parallela di {total_blocks} blocchi su {len(notebooks_list)} notebook...\n")
            block_tasks = [
                ((b_idx, nb_idx), nb["id"], block_query_prompt(block["content"]))
                for b_idx, block in enumerate(blocks)
                for nb_idx, nb in enumerate(notebooks_list)
            ]
            block_answers = query_nlm_parallel(block_tasks, on_progress=progress_reporter(
                vault_root, 30, 2, f"📥 Scansione NotebookLM: {total_blocks} moduli × {len(notebooks_list)} notebook",
                "sources", target_rel,
            ))

            # Secondo tentativo (domanda più semplice) per i blocchi rimasti senza alcuna risposta
            empty_blocks = [
                b_idx for b_idx in range(total_blocks)
                if not any(block_answers.get((b_idx, nb_idx), "").strip() for nb_idx in range(len(notebooks_list)))
            ]
            if empty_blocks:
                sys.stderr.write(f"[Orchestrator] Nuovo tentativo su {len(empty_blocks)} blocchi senza risposta...\n")
                retry_tasks = [
                    ((b_idx, nb_idx), nb["id"],
                     f"Quali concetti, definizioni, teoremi e metodi spiegano le fonti di questo notebook riguardo a: {blocks[b_idx]['title']}?")
                    for b_idx in empty_blocks
                    for nb_idx, nb in enumerate(notebooks_list)
                ]
                block_answers.update({k: v for k, v in query_nlm_parallel(retry_tasks).items() if v.strip()})

            for b_idx, block in enumerate(blocks):
                block_title = block["title"]
                block_nb_results = []
                for nb_idx, nb in enumerate(notebooks_list):
                    ext_text = block_answers.get((b_idx, nb_idx), "")
                    if ext_text:
                        block_nb_results.append(f"##### Fonte: `{nb['title']}`\n{ext_text}")
                        raw_text_parts.append(ext_text)

                sec_block = [
                    f"### 📦 {block_title}",
                    "**Voci Indice / Diario Analizzate:**",
                    block["content"],
                    "",
                    "#### 📝 Contenuto Estratto da NotebookLM:"
                ]
                if block_nb_results:
                    sec_block.extend(block_nb_results)
                elif allow_base_moc:
                    sec_block.append(
                        "> [!WARNING] Nessun contenuto estratto da NotebookLM per questo modulo (anche dopo un secondo tentativo).\n"
                        "> Modalità ibrida: puoi descrivere questo modulo con la tua conoscenza accademica, ma usa solo le voci "
                        "dell'indice qui sopra come perimetro e segnala il modulo nella Diagnosi di Completezza come "
                        "\"non coperto dalle fonti NotebookLM\"."
                    )
                else:
                    sec_block.append(
                        "> [!WARNING] Nessun contenuto estratto da NotebookLM per questo modulo (anche dopo un secondo tentativo).\n"
                        "> Modalità esclusiva: è VIETATO descriverlo con conoscenza esterna o consultare altre fonti. "
                        "Inserisci nel MOC solo le voci dell'indice qui sopra come wikilink futuri, senza spiegazioni, "
                        "e segnala il modulo nella Diagnosi di Completezza come \"non coperto dalle fonti NotebookLM\"."
                    )
                sec_block.append("\n---\n")
                block_extractions.append("\n".join(sec_block))

            # 5. Query di Audit Finale su nlm
            update_status(
                vault_root=vault_root,
                percent=44,
                step_number=2,
                total_steps=6,
                message="🛡️ Audit Finale NotebookLM: verifica completezza teoremi ed esame...",
                detail=f"Audit di garanzia copertura 100% per {topic_clean}",
                status="running",
                target_file=target_rel,
            )
            sys.stderr.write(f"[Orchestrator] Esecuzione Audit Finale su NotebookLM per {topic_clean}...\n")

            audit_query = (
                f"Effettua un controllo critico e di audit completo su tutte le fonti di questo notebook per la materia '{topic_clean}'. "
                "Verifica se ci sono teoremi, proposizioni, lemmi, corollari, definizioni cardine o tipologie di esercizi d'esame "
                "che rischiano di essere stati tralasciati o non approfonditi a sufficienza. "
                "Elenca in modo dettagliato ed esaustivo tutto ciò che è indispensabile per superare l'esame con il massimo dei voti."
            )

            audit_results = []
            audit_answers = query_nlm_parallel([(nb_idx, nb["id"], audit_query) for nb_idx, nb in enumerate(notebooks_list)])
            for nb_idx, nb in enumerate(notebooks_list):
                ext_audit = audit_answers.get(nb_idx, "")
                if ext_audit:
                    audit_results.append(f"##### Audit su `{nb['title']}`\n{ext_audit}")
                    raw_text_parts.append(ext_audit)

            # 6. Scrittura del File extracted_source.md
            full_content: List[str] = [
                "# 🧠 DOSSIER FONTI NOTEBOOKLM E TRACCIA DEL CORSO (A ∪ B)",
                f"- **Materia / Argomento:** `{topic_clean}`",
                f"- **NotebookLM Collegati ({len(notebooks_list)}):** " + ", ".join([f"`{n['title']}` (`{n['id']}`)" for n in notebooks_list]),
                f"- **File Traccia Allegati ({len(syllabus_meta)}):** " + (", ".join([f"`{f['file']}`" for f in syllabus_meta]) if syllabus_meta else "*(Nessun file allegato)*"),
                "- **Traccia Testuale Incollata:** " + ("Presente" if syllabus_text.strip() else "*(Nessun testo incollato)*"),
                f"- **Moduli Tematici Scansionati:** {total_blocks} blocchi",
                f"- **Perimetro del MOC:** {scope_label}",
                "",
                "---",
                "",
                "## 📋 Traccia del Corso (indice del libro come spina dorsale, diario come integrazione)",
                combined_syllabus,
                "",
                "---",
                "",
                "## 🔬 Risultanze Scansione Multi-Query per Modulo Didattico",
                ""
            ]
            full_content.extend(block_extractions)

            full_content.append("## 🛡️ Audit Finale di Completezza ed Evidenze d'Esame")
            if audit_results:
                full_content.extend(audit_results)
            else:
                full_content.append(
                    "> [!INFO] Audit Automatico:\n"
                    "> Verifica durante la stesura del MOC che ogni concetto, teorema e metodo presente nella traccia del corso "
                    "abbia il proprio wikilink dedicato e una spiegazione del filo logico conduttore."
                )

            combined_markdown = "\n".join(full_content)
            extracted_source_file = context_dir / "extracted_source.md"
            extracted_source_file.parent.mkdir(parents=True, exist_ok=True)
            extracted_source_file.write_text(combined_markdown, encoding="utf-8")

            # -------------------------------------------------------------
            # HARD-GATE ANTI-FALLBACK PER MOC
            # -------------------------------------------------------------
            total_real_chars = sum(len(p.strip()) for p in raw_text_parts)
            if total_real_chars < 400:
                err_msg = "❌ Errore: Estrazione da NotebookLM vuota o fallita. Esecuzione bloccata per impedire l'uso della conoscenza base AI."
                detail_msg = (
                    f"Caratteri reali estratti per il MOC: {total_real_chars} (soglia minima obbligatoria: 400). "
                    f"Verifica che la sessione non sia scaduta (esegui 'nlm login' nel terminale) "
                    f"e che il notebook contenga materiale su '{topic_clean}'."
                )
                update_status(
                    vault_root=vault_root,
                    percent=25,
                    step_number=2,
                    total_steps=6,
                    message=err_msg,
                    detail=detail_msg,
                    status="error",
                    target_file=target_rel,
                    error=err_msg,
                )
                sys.stderr.write(f"\n[Orchestrator] 🛑 HARD-GATE TRIGGERED (MOC): {err_msg}\n{detail_msg}\n")
                raise RuntimeError(err_msg)

            # Prova Visiva finale Loading Bar MOC
            formatted_tot = f"{total_real_chars:,}".replace(",", ".")
            nb_names_str = " + ".join(nb["title"] for nb in notebooks_list)
            update_status(
                vault_root=vault_root,
                percent=44,
                step_number=2,
                total_steps=6,
                message=f"📥 NotebookLM: estratti {formatted_tot} caratteri reali da {nb_names_str}",
                detail=f"Dossier MOC completato su {total_blocks} moduli | {formatted_tot} caratteri validati",
                status="running",
                target_file=target_rel,
            )

            result["content_markdown"] = combined_markdown
            result["raw_source_text"] = "\n".join(raw_text_parts)
            result["metadata"] = {
                "notebooks": notebooks_list,
                "count": len(notebooks_list),
                "is_multi": is_multi,
                "id": notebooks_list[0]["id"],
                "title": " + ".join(nb["title"] for nb in notebooks_list),
                "total_blocks": total_blocks,
                "syllabus_files": syllabus_meta,
                "has_syllabus_text": bool(syllabus_text.strip()),
                "scope": scope_label,
                "has_book_index": bool(index_paste.strip() or index_files),
                "has_diary": bool(diary_text.strip()),
                "total_chars": total_real_chars,
            }
            return result

        # =====================================================================
        # FLUSSO NOTEBOOKLM PER NOTA NORMALE (ESTRAZIONE REALE E DETTAGLIATA)
        # =====================================================================
        extracted_sections: List[str] = []
        raw_text_parts: List[str] = []
        notebook_char_counts: List[Dict[str, Any]] = []

        # Query multiple e complementari per ogni notebook, eseguite tutte in parallelo:
        # ogni risposta di NotebookLM ha una lunghezza limitata, quindi dividere la richiesta
        # per aspetto (enunciati / dimostrazioni / esempi) produce un'estrazione più completa.
        if op_type == "moc":
            query_aspects = [
                ("Indice analitico", (
                    f"Fornisci l'indice analitico e la struttura concettuale dettagliata di tutti i capitoli, "
                    f"moduli, definizioni, teoremi e metodi relativi a '{topic_clean}' presenti nelle fonti di questo notebook."
                )),
            ]
        else:
            query_aspects = [
                ("Definizioni, notazione ed enunciati", (
                    f"Riguardo a '{topic_clean}', estrai dalle fonti di questo notebook in modo integrale e rigoroso:\n"
                    f"1) tutte le definizioni formali, con la notazione esatta adottata dal professore e dai testi di riferimento;\n"
                    f"2) gli enunciati completi di tutti i teoremi, proposizioni, lemmi e corollari relativi al tema, con le ipotesi esatte;\n"
                    f"3) le osservazioni, i casi particolari e le convenzioni segnalate nelle fonti.\n"
                    f"Riporta solo ciò che è presente nelle fonti, senza aggiungere nulla."
                )),
                ("Dimostrazioni e passaggi", (
                    f"Riguardo a '{topic_clean}', riporta dalle fonti di questo notebook le dimostrazioni integrali, passo per passo, "
                    f"di tutti i risultati collegati al tema, senza omettere alcun passaggio algebrico o logico presente nelle fonti. "
                    f"Se per un enunciato le fonti non contengono la dimostrazione, dichiaralo esplicitamente."
                )),
                ("Esempi, esercizi e collegamenti", (
                    f"Riguardo a '{topic_clean}', estrai dalle fonti di questo notebook:\n"
                    f"1) tutti gli esempi svolti, i controesempi e le applicazioni;\n"
                    f"2) gli esercizi e le tracce d'esame con il relativo metodo risolutivo;\n"
                    f"3) i prerequisiti e i collegamenti con gli altri argomenti del corso, così come presentati nelle fonti.\n"
                    f"Riporta solo ciò che è presente nelle fonti, senza aggiungere nulla."
                )),
            ]

        nlm_tasks = [
            ((idx, a_idx), nb["id"], aspect_prompt)
            for idx, nb in enumerate(notebooks_list, 1)
            for a_idx, (_, aspect_prompt) in enumerate(query_aspects)
        ]
        nb_names_label = " + ".join(nb["title"] for nb in notebooks_list)
        sys.stderr.write(f"[Orchestrator] Avvio {len(nlm_tasks)} query NotebookLM in parallelo su: {nb_names_label}...\n")
        update_status(
            vault_root=vault_root,
            percent=28,
            step_number=2,
            total_steps=6,
            message=f"📥 {len(nlm_tasks)} query NotebookLM in parallelo: {nb_names_label}...",
            detail=f"Estrazione di enunciati, dimostrazioni ed esempi per {topic_clean}",
            status="running",
            target_file=target_rel,
        )
        nlm_answers = query_nlm_parallel(
            nlm_tasks, timeout_sec=180, include_quotes=(op_type != "moc"),
            on_progress=progress_reporter(
                vault_root, 28, 2, f"📥 Lettura delle fonti NotebookLM: {nb_names_label}", "sources", target_rel
            ),
        )

        for idx, nb in enumerate(notebooks_list, 1):
            nb_id = nb["id"]
            nb_title = nb["title"]

            aspect_texts = [
                (label, nlm_answers.get((idx, a_idx), ""))
                for a_idx, (label, _) in enumerate(query_aspects)
            ]
            extracted_nlm_text = "\n\n".join(
                f"##### {label}\n{text}" for label, text in aspect_texts if text.strip()
            )
            chars_extracted = sum(len(text.strip()) for _, text in aspect_texts)
            if NLM_RATE_LIMITED and op_type != "moc" and chars_extracted < 1500:
                try:
                    import vault_layout
                    extra_terms = vault_layout.requested_sections(vault_root, topic_clean)
                except Exception:
                    extra_terms = []
                passages = local_source_passages(nb_id, topic_clean, extra_terms,
                                                 max_chars=45000 // max(1, len(notebooks_list)))
                if passages:
                    if job_data is not None:
                        job_data["local_sources_used"] = True
                    sys.stderr.write(f"[Orchestrator] Chat NotebookLM al limite: uso {len(passages)} caratteri "
                                     f"del testo originale delle fonti di {nb_title}.\n")
                    extracted_nlm_text = (
                        (extracted_nlm_text + "\n\n" if extracted_nlm_text else "")
                        + "##### Testo originale delle fonti (passaggi pertinenti, senza rielaborazione AI)\n"
                        "> Estratti letterali dei documenti caricati nel notebook. Usa solo ciò che riguarda "
                        f"'{topic_clean}'; ignora il resto.\n\n" + passages
                    )
                    chars_extracted = len(extracted_nlm_text)
            notebook_char_counts.append({"title": nb_title, "id": nb_id, "chars": chars_extracted})

            if extracted_nlm_text:
                formatted_chars = f"{chars_extracted:,}".replace(",", ".")
                ok_queries = sum(1 for _, text in aspect_texts if text.strip())
                sys.stderr.write(f"[Orchestrator] NotebookLM: estratti {formatted_chars} caratteri reali da {nb_title} ({ok_queries}/{len(aspect_texts)} query riuscite).\n")
                update_status(
                    vault_root=vault_root,
                    percent=35,
                    step_number=2,
                    total_steps=6,
                    message=f"📥 NotebookLM: estratti {formatted_chars} caratteri reali da {nb_title}",
                    detail=f"Notebook ID: {nb_id} | {ok_queries}/{len(aspect_texts)} query riuscite | Caratteri validati: {formatted_chars}",
                    status="running",
                    target_file=target_rel,
                )

            sec_lines = [
                f"### Fonte {idx}: {nb_title} (ID: `{nb_id}`)",
                f"- **Nome Notebook:** `{nb_title}`",
                f"- **ID Univoco:** `{nb_id}`",
                f"- **Caratteri Estratti:** `{chars_extracted}`",
                ""
            ]
            if extracted_nlm_text:
                sec_lines.append("#### 📝 Contenuto Estratto:")
                sec_lines.append(extracted_nlm_text)
            else:
                sec_lines.append(
                    "> [!WARNING] Estrazione Fallita o Vuota:\n"
                    f"> Nessun contenuto estratto da {nb_title} ({nb_id}).\n"
                )
            sec_lines.append("\n---\n")

            extracted_sections.append("\n".join(sec_lines))
            if extracted_nlm_text:
                raw_text_parts.append(extracted_nlm_text)

        full_content: List[str] = []
        if is_multi:
            full_content.append(f"# 🧠 FUSIONE MULTI-NOTEBOOK ({len(notebooks_list)} Fonti Interconnesse)")
            full_content.append(f"Sono stati interrogati e combinati **{len(notebooks_list)} NotebookLM** per incrociare le fonti attorno a: `{topic_clean}`.\n")
        else:
            full_content.append(f"# 📓 Fonte NotebookLM: {notebooks_list[0]['title']}")
            full_content.append(f"ID Notebook: `{notebooks_list[0]['id']}`\n")

        full_content.extend(extracted_sections)
        combined_markdown = "\n".join(full_content)

        # Scrittura tassativa del file temporaneo extracted_source.md
        extracted_source_file = context_dir / "extracted_source.md"
        extracted_source_file.parent.mkdir(parents=True, exist_ok=True)
        extracted_source_file.write_text(combined_markdown, encoding="utf-8")

        # -------------------------------------------------------------
        # HARD-GATE ANTI-FALLBACK (Blocco Immediato se l'Estrazione Fallisce)
        # -------------------------------------------------------------
        total_real_chars = sum(len(p.strip()) for p in raw_text_parts)
        if total_real_chars < 400:
            if NLM_RATE_LIMITED:
                err_msg = RATE_LIMIT_ERROR
                detail_msg = "NotebookLM rifiuta ancora le query. Riprova più tardi: il limite si azzera da solo."
            else:
                err_msg = "❌ Errore: Estrazione da NotebookLM vuota o fallita. Esecuzione bloccata per impedire l'uso della conoscenza base AI."
                detail_msg = (
                    f"Caratteri reali estratti: {total_real_chars} (soglia minima obbligatoria: 400). "
                    f"Verifica che la sessione non sia scaduta (esegui 'nlm login' nel terminale) "
                    f"e che il notebook contenga materiale su '{topic_clean}'."
                )
            update_status(
                vault_root=vault_root,
                percent=25,
                step_number=2,
                total_steps=6,
                message=err_msg,
                detail=detail_msg,
                status="error",
                target_file=target_rel,
                error=err_msg,
            )
            sys.stderr.write(f"\n[Orchestrator] 🛑 HARD-GATE TRIGGERED: {err_msg}\n{detail_msg}\n")
            raise RuntimeError(err_msg)

        # Prova Visiva finale Loading Bar (se multi-notebook)
        if is_multi:
            formatted_tot = f"{total_real_chars:,}".replace(",", ".")
            nb_summary = ", ".join([f"{c['title']} ({f'{c['chars']:,}'.replace(',', '.')})" for c in notebook_char_counts])
            update_status(
                vault_root=vault_root,
                percent=40,
                step_number=2,
                total_steps=6,
                message=f"📥 NotebookLM: estratti {formatted_tot} caratteri reali totali ({len(notebooks_list)} notebook)",
                detail=nb_summary,
                status="running",
                target_file=target_rel,
            )

        result["content_markdown"] = combined_markdown
        result["raw_source_text"] = "\n".join(raw_text_parts)
        result["metadata"] = {
            "notebooks": notebooks_list,
            "count": len(notebooks_list),
            "is_multi": is_multi,
            "id": notebooks_list[0]["id"],
            "title": " + ".join(nb["title"] for nb in notebooks_list),
            "char_counts": notebook_char_counts,
            "total_chars": total_real_chars
        }
        return result

    # 5. Solo Vault (Nessun file esterno)
    elif stype == "vault_only":
        result["content_markdown"] = (
            f"# 📂 Operazione Basata Esclusivamente sul Vault\n"
            f"Nessuna fonte esterna richiesta. L'agente Antigravity deve consultare `.antigravity/vault-index.json` "
            f"per organizzare, mappare o sintetizzare i contenuti già esistenti nel vault attorno all'argomento.\n"
        )
        result["raw_source_text"] = ""

    # Nel caso di merge_source, il raw_source_text per PubMed include sia il testo target che la nuova fonte
    if op_type == "edit" and edit_mode == "merge_source":
        target_c = result.get("target_content", "")
        if target_c:
            result["raw_source_text"] = f"{target_c}\n\n{result.get('raw_source_text', '')}"

    return result


# ==============================================================================
# 3. PUBMED SEQUENZIALE INTELLIGENTE (ESTRAZIONE TERMINI DALLA FONTE)
# ==============================================================================

def extract_scientific_query_terms(discipline_name: str, topic: str, source_text: str) -> List[str]:
    """
    Estrae dalla fonte e dal titolo i termini anatomici, biochimici e farmacologici
    effettivamente trattati, traducendoli in inglese medico per le query PubMed.
    """
    detectors = SCIENTIFIC_TERM_DETECTORS.get(discipline_name, [])
    full_text_to_scan = f"{topic}\n{source_text[:12000]}"
    
    detected_english_terms: List[str] = []
    for pattern, eng_term in detectors:
        if re.search(pattern, full_text_to_scan, re.IGNORECASE):
            if eng_term not in detected_english_terms:
                detected_english_terms.append(eng_term)

    # Costruzione di 2-3 query mirate
    queries: List[str] = []
    
    # Query 1: Topic + primi 2 termini scientifici chiave
    if detected_english_terms:
        primary_terms = " AND ".join(detected_english_terms[:2])
        queries.append(f"{primary_terms}")
        if len(detected_english_terms) > 2:
            secondary_terms = " AND ".join(detected_english_terms[2:4])
            queries.append(f"{detected_english_terms[0]} AND {secondary_terms}")
    
    # Query di completamento basata sul topic tradotto/ripulito
    clean_topic = re.sub(r"[^\w\s-]", " ", topic)
    queries.append(clean_topic.strip())

    # Rimuovi duplicati preservando l'ordine
    unique_queries = []
    for q in queries:
        if q and q not in unique_queries:
            unique_queries.append(q)
            
    return unique_queries[:3]


def trigger_auto_tools_sequential(
    discipline_name: str,
    discipline_cfg: Dict[str, Any],
    topic: str,
    source_text: str,
    allegati_dir: Path,
    context_dir: Path,
    tools_dir: Path,
) -> Dict[str, Any]:
    """
    Esegue gli strumenti scientifici in modo sequenziale intelligente:
    - PubMed viene interrogato NON sul solo titolo cieco, ma sui termini biochimici/anatomici
      effettivamente rilevati nel testo della fonte.
    - Science Media Fetch scarica strutture chimiche o modelli anatomici mirati.
    """
    auto_tools = discipline_cfg.get("auto_tools", {})
    results: Dict[str, Any] = {
        "pubmed_evidence": None,
        "science_media": None,
        "targeted_pubmed_queries": []
    }

    # 1. PubMed Sequenziale Intelligente
    if auto_tools.get("pubmed", False):
        targeted_queries = extract_scientific_query_terms(discipline_name, topic, source_text)
        results["targeted_pubmed_queries"] = targeted_queries
        
        sys.stderr.write(f"[Orchestrator] PubMed Sequenziale Intelligente: query generate dalla fonte = {targeted_queries}\n")
        
        combined_articles = []
        seen_pmids = set()

        for q in targeted_queries:
            sys.stderr.write(f"[Orchestrator] Ricerca PubMed per: '{q}'...\n")
            res = run_tool_script(
                "pubmed_search.py",
                [q, "--max-results", "4", "--json"],
                tools_dir,
            )
            if res.returncode == 0 and res.stdout.strip():
                try:
                    p_json = json.loads(res.stdout)
                    for art in p_json.get("articles", []):
                        pmid = art.get("pmid")
                        if pmid and pmid not in seen_pmids:
                            seen_pmids.add(pmid)
                            combined_articles.append(art)
                except Exception:
                    pass

        if combined_articles:
            pubmed_bundle = {
                "queries_executed": targeted_queries,
                "total_articles": len(combined_articles),
                "articles": combined_articles
            }
            results["pubmed_evidence"] = pubmed_bundle
            (context_dir / "pubmed_evidence.json").write_text(
                json.dumps(pubmed_bundle, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            sys.stderr.write(f"[Orchestrator] PubMed: {len(combined_articles)} studi specifici estratti e salvati nel context.\n")

    # 2. Downloader Immagini Scientifiche (PubChem / Wikimedia)
    if auto_tools.get("science_media", False):
        sys.stderr.write(f"[Orchestrator] Attivazione Science Media Fetch per '{topic}'...\n")
        res = run_tool_script(
            "science_media_fetch.py",
            ["--molecule", topic, "--search", topic, "--out-dir", str(allegati_dir), "--max-images", "2", "--json"],
            tools_dir,
        )
        if res.returncode == 0 and res.stdout.strip():
            try:
                media_json = json.loads(res.stdout)
                results["science_media"] = media_json
                (context_dir / "media_evidence.json").write_text(res.stdout, encoding="utf-8")
                sys.stderr.write("[Orchestrator] Science Media scaricati nella cartella allegati.\n")
            except Exception:
                pass

    return results


# ==============================================================================
# 4. COSTRUZIONE DEL PROMPT OPERATIVO VINCOLANTE (NOTE & MOC)
# ==============================================================================

def get_moc_structural_rules_prompt() -> str:
    """Restituisce il blocco vincolante dei 4 vincoli strutturali dei MOC (Legge 4)."""
    return (
        "## I 4 VINCOLI STRUTTURALI TASSATIVI DEI MOC (LEGGE 4 — REGOLE DEFINITIVE)\n\n"
        "1. **ZERO FORMULE, ZERO DIMOSTRAZIONI, ZERO TABELLE NEI MOC:**\n"
        "   - **Divieto Assoluto di LaTeX:** Nei MOC è severamente vietato inserire formule matematiche o simboliche racchiuse tra dollari (`$...$` o `$$...$$`). I concetti vanno descritti esclusivamente mediante la loro denominazione concettuale in prosa italiana accademica (es. scrivere 'aritmetica modulare nell'anello delle classi di resto' e MAI '$\\mathbb{Z}_n$' o '$ax \\equiv b \\pmod n$').\n"
        "   - **Zero Dimostrazioni ed Enunciati Formali:** Il MOC non dimostra teoremi e non ne riporta gli enunciati simbolici con ipotesi e tesi formali. Spiega invece lo scopo teorico del teorema e la ragione logica per cui scaturisce dal concetto precedente.\n"
        "   - **Zero Tabelle Riassuntive:** È severamente vietato inserire tabelle riassuntive, elenchi colonnari o matrici di confronto nei MOC. Tutta la materia deve vivere unicamente nella prosa narrativa continua e nei diagrammi Mermaid.\n"
        "   - **Zero Callout Tecnici e Zero Pannelli Studio:** Nei MOC non devono comparire callout di definizione (`> [!definition]`), teoremi (`> [!theorem]`), decodifiche logico-formali o il blocco Flashcard/Quiz (`%%STUDY_DATA`, `study_panel.js`).\n"
        "   - **Zero Riferimenti Meta e Zero Emoji:** È tassativamente vietato menzionare numeri di lezione, capitoli del libro o nomi di notebook (es. mai scrivere `(Lezioni 1-10)` o `(Cap. 3 del Libro)`). Purga totale di qualsiasi emoji Unicode.\n\n"
        "2. **TESTO 100% DISCORSIVO CAUSALE (Il 'Perché' del Passaggio da una Nota all'Altra):**\n"
        "   - Il MOC deve essere scritto interamente in prosa discorsiva fluida e coerente, articolata in paragrafi narrativi approfonditi.\n"
        "   - La trattazione deve sviscerare sistematicamente il *filo logico causale*:\n"
        "     * Perché nasce un determinato concetto e quale problema pratico o teorico risolve.\n"
        "     * Quale limite strutturale del concetto precedente impone di introdurre il successivo.\n"
        "     * Come e perché da quel concetto scaturiscono rigorosamente i relativi teoremi e metodi applicativi.\n"
        "   - È severamente vietato presentare sezioni costituite da soli elenchi puntati privi di raccordo causale.\n\n"
        "3. **NOMENCLATURA ESPLICITA OBBLIGATORIA E DIVIETO ASSOLUTO DI ALIAS NEI WIKILINK DEL MOC:**\n"
        "   - Per consentire a chi studia di distinguere immediatamente a colpo d'occhio nel testo discorsivo, nel grafo e nella barra laterale la tipologia di ciascuna nota:\n"
        "     * **Note Teorema:** Devono SEMPRE iniziare con il prefisso canonico `Teorema ...` (oppure `Lemma ...`, `Corollario ...`, `Principio ...`, `Criterio ...`) all'interno delle doppie quadre (es. `[[Teorema di Weierstrass]]`, `[[Teorema di Rouché-Capelli]]`, `[[Criterio di Diagonalizzabilità]]`). È severamente vietato scrivere `il teorema di [[Weierstrass]]`.\n"
        "     * **Note Metodo:** Devono SEMPRE iniziare con il prefisso canonico `Metodo ...` (oppure `Studio ...`, `Calcolo ...`, `Risoluzione ...`, `Algoritmo ...`) all'interno delle doppie quadre (es. `[[Metodo di Eliminazione di Gauss]]`, `[[Calcolo dell'Inversa di una Matrice]]`, `[[Risoluzione delle Equazioni Diofantee Lineari]]`).\n"
        "     * **DIVIETO ASSOLUTO DI ALIAS NEI MOC:** Nei MOC è vietato usare pipe/alias nei wikilink (es. MAI `[[Teorema di Weierstrass|teorema]]` né `[[Metodo di Eliminazione di Gauss|algoritmo]]`). Solo ed esclusivamente il wikilink puro col titolo completo della nota: `[[Nome Esatto della Nota]]`.\n"
        "     * **Wikilink Puri:** Mai racchiudere i wikilink tra apici singoli `'[[...]]'`, doppi `\"[[...]]\"` o backtick ``` `[[...]]` ```.\n\n"
        "4. **DOPPIA ARCHITETTURA MERMAID VERTICALE (`flowchart TD`):**\n"
        "   - **1. Diagramma Generale d'Insieme (Top-Level):** Posizionato in cima al MOC, subito dopo l'introduzione, con orientamento verticale `flowchart TD` per visualizzare la propedeuticità e la successione logica dei macro-moduli del corso.\n"
        "   - **2. Diagrammi Modulari Dedicati (End-of-Chapter):** In fondo a **ciascun singolo capitolo/modulo**, è obbligatorio inserire un diagramma `flowchart TD` che mappi l'architettura interna del capitolo: nodi di `[[Concetto]]`, collegati ai rispettivi `[[Teorema ...]]` e `[[Metodo ...]]`.\n"
        "   - **Regole Sintattiche Anti-Crash Mermaid:**\n"
        "     * Nodi centrati verticali (`flowchart TD`).\n"
        "     * Testo di ciascun nodo racchiuso rigorosamente tra doppi apici `\"...\"`.\n"
        "     * Zero formule LaTeX e zero delimitatori `$...$` all'interno dei nodi.\n"
        "     * Zero emoji Unicode nei diagrammi.\n\n"
        "5. **UN MODULO = UNA SEZIONE `##`, TITOLI DELLE NOTE IN ITALIANO CORRETTO E UNICI:**\n"
        "   - Ogni modulo del corso è una sezione di secondo livello `## Titolo del Modulo` (senza numeri, emoji o riferimenti a capitoli): le cartelle del vault vengono create da queste sezioni, nell'ordine del MOC.\n"
        "   - Tutti i wikilink a note da collegare stanno dentro le sezioni dei moduli; la sezione finale `## Note e Paragrafi Collegati` contiene solo la risalita al Macro-MOC e i rimandi ad altri corsi/MOC, che NON sono note da creare.\n"
        "   - **Accenti obbligatori nei titoli:** scrivi le parole italiane con l'accento corretto anche dentro le doppie quadre (es. `[[Teorema di Unicità del Limite]]`, `[[Proprietà di Archimede]]`, `[[Continuità Uniforme]]`), mai `Unicita`, `Proprieta`, `Continuita`.\n"
        "   - **Un concetto, un solo titolo:** non creare due wikilink diversi per lo stesso argomento (es. mai sia `[[Studio del Grafico di una Funzione]]` sia `[[Studio Completo del Grafico di una Funzione]]`). Se un concetto compare nell'elenco dei titoli già esistenti o pianificati in altri MOC della disciplina, usa ESATTAMENTE quel titolo.\n\n"
        "6. **POCHE NOTE, MA SOSTANZIOSE (NOTA MADRE + SEZIONI):**\n"
        "   - Un wikilink a nota separata `[[Titolo]]` solo per gli argomenti che le fonti trattano in modo ampio: concetti con definizione e risultati propri, teoremi importanti con dimostrazione propria (es. Weierstrass, Rolle, Lagrange, Bolzano), metodi che occupano un intero paragrafo delle fonti.\n"
        "   - Varianti dello stesso risultato (es. '... per Successioni' / '... per Funzioni'), corollari, lemmi tecnici, singole proprietà, casi particolari, esempi notevoli e micro-metodi NON hanno una nota propria: diventano sezioni della nota madre e si collegano con `[[Nota Madre#Nome Sezione]]` (es. `[[Limite di una Successione#Unicità del Limite]]`, `[[Funzioni Continue#Permanenza del Segno]]`). Il nome della sezione è breve e senza numeri.\n"
        "   - Ordine di grandezza: un corso universitario completo ha circa 90-130 note separate (6-10 per modulo), non 250. Ogni nota madre deve poter riempire una pagina di appunti con il materiale delle fonti.\n"
        "   - Anche nei diagrammi Mermaid le sezioni si scrivono `[[Nota Madre#Nome Sezione]]`."
    )

def write_planned_titles(vault_root: Path, discipline: str, moc_target: str, context_dir: Path) -> Path:
    """Elenco dei titoli delle note già esistenti e di quelle pianificate negli altri MOC della disciplina:
    chi scrive il MOC li riusa identici, così un concetto condiviso diventa una sola nota."""
    out = context_dir / "titoli-pianificati.md"
    existing: List[str] = []
    planned: Dict[str, List[str]] = {}
    try:
        import vault_layout
        for c in vault_layout.load_courses(vault_root):
            if c.moc_rel == moc_target or (discipline and c.discipline != discipline):
                continue
            planned[c.name] = c.note_titles
        disc_dir = vault_root / discipline
        if discipline and disc_dir.is_dir():
            existing = sorted(p.stem for p in disc_dir.rglob("*.md") if not p.stem.endswith(" MOC"))
    except Exception as e:
        sys.stderr.write(f"[Orchestrator] Titoli pianificati non calcolati: {e}\n")
    lines = [f"# Titoli già usati nella disciplina {discipline}", "",
             "Se il MOC tratta uno di questi concetti, usa esattamente lo stesso titolo nel wikilink.", ""]
    if existing:
        lines += ["## Note già esistenti nel vault", ""] + [f"- {t}" for t in existing] + [""]
    for name, titles in planned.items():
        lines += [f"## Pianificati in {name} MOC", ""] + [f"- {t}" for t in titles] + [""]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def build_moc_operational_prompt(
    job_data: Dict[str, Any],
    discipline_cfg: Dict[str, Any],
    source_results: Dict[str, Any],
    compiled_instructions_path: Path,
    vault_root: Path,
    context_dir: Path,
) -> str:
    """Costruisce current-prompt.md per le 3 modalità di creazione MOC."""
    topic = job_data.get("topic", "Senza Titolo")
    discipline = job_data.get("discipline", "")
    pole = job_data.get("pole", "")
    moc_mode = job_data.get("moc_mode", "start_base_knowledge")
    moc_target = job_data.get("target_file_path") or f"01 MOC's/{topic} MOC.md"
    titles_file = write_planned_titles(vault_root, discipline, moc_target, context_dir)

    prompt_lines: List[str] = []

    # -------------------------------------------------------------
    # CASO A: MOC di Inizio Studio da NotebookLM (Singolo o Multi-Fonte)
    # -------------------------------------------------------------
    if moc_mode == "start_notebooklm":
        notebooks_meta = (source_results.get("metadata") or {}).get("notebooks") or extract_notebooks_list(job_data.get("source", {}), job_data)
        is_multi_nb = len(notebooks_meta) > 1

        mode_label = "🌱 MOC di Inizio Studio — Da NotebookLM (Roadmap completa dalle fonti)"
        if is_multi_nb:
            mode_label += f" [Fusione Multi-Notebook: {len(notebooks_meta)} Fonti]"

        prompt_lines.append(f"# MISSIONE MOC ANTIGRAVITY: {topic.upper()} (INIZIO STUDIO DA NOTEBOOKLM)")
        prompt_lines.append("")
        prompt_lines.append("## Parametri del Job")
        prompt_lines.append(f"- **Argomento / Titolo MOC:** `{topic}`")
        prompt_lines.append(f"- **Tipo Operazione:** `MOC (Map of Content)`")
        prompt_lines.append(f"- **Modalità MOC:** `{mode_label}` (`{moc_mode}`)")
        prompt_lines.append(f"- **Disciplina:** `{discipline}` (Polo: `#{pole}`)")
        if is_multi_nb:
            prompt_lines.append(f"- **NotebookLM Multipli Selezionati ({len(notebooks_meta)} fonti concatenate):**")
            for idx, nb in enumerate(notebooks_meta, 1):
                prompt_lines.append(f"  * Fonte {idx}: `{nb['title']}` (ID: `{nb['id']}`)")
            prompt_lines.append(f"- **Dossier Fonti Concatenate (Multi-Notebook):** `file://{context_dir / 'extracted_source.md'}`")
        else:
            single_nb = notebooks_meta[0] if notebooks_meta else {"title": "NotebookLM", "id": "N/D"}
            prompt_lines.append(f"- **NotebookLM Selezionato:** `{single_nb['title']}` (ID: `{single_nb['id']}`)")
            prompt_lines.append(f"- **Dossier Fonti e Scansione Multi-Query NotebookLM:** `file://{context_dir / 'extracted_source.md'}`")
        allow_base_knowledge = bool(
            job_data.get("allow_base_knowledge", False)
            or job_data.get("source", {}).get("allow_base_knowledge", False)
        )
        knowledge_label = (
            "🧠+🌐 NotebookLM (Fonte Primaria) + Conoscenza di Base AI (Integrativa)"
            if allow_base_knowledge
            else "🔒 Solo NotebookLM (Esclusivo — Zero conoscenza esterna)"
        )
        prompt_lines.append(f"- **Modalità Conoscenza:** `{knowledge_label}` (`allow_base_knowledge: {str(allow_base_knowledge).lower()}`)")
        prompt_lines.append(f"- **Istruzioni Statiche Compilate:** `file://{compiled_instructions_path}`")
        prompt_lines.append(f"- **Indice del Vault:** `file://{resolve_vault_index_path(vault_root)}`")
        prompt_lines.append(f"- **Collegamenti Chirurgici Raccomandati:** `file://{context_dir / 'recommended-links.md'}`")
        prompt_lines.append(f"- **Titoli già esistenti o pianificati nella disciplina (da riusare identici):** `file://{titles_file}`")
        prompt_lines.append("")

        prompt_lines.append("## LE AZIONI OBBLIGATORIE CHE DEVI ESEGUIRE ORA")
        prompt_lines.append("")
        if not allow_base_knowledge:
            prompt_lines.append(
                "> [!DANGER] ⚠️ VINCOLO INDEROGABILE DI ESCLUSIVITÀ NOTEBOOKLM (LEGGE 12 — MODALITÀ STRETTA)\n"
                f"> Questo MOC DEVE basarsi al 100% sul testo estratto da NotebookLM presente in `file://{context_dir / 'extracted_source.md'}` (e sull'eventuale Traccia del Corso fornita).\n"
                "> - **Confinamento Rigoroso:** Puoi inserire nel MOC esclusivamente concetti, moduli, teoremi e metodi trattati in `extracted_source.md`.\n"
                "> - È SEVERAMENTE VIETATO usare la tua conoscenza pre-addestrata per colmare lacune o aggiungere argomenti/convenzioni non presenti nelle fonti del corso.\n"
                "> - Usa ESCLUSIVAMENTE le notazioni, i moduli e le definizioni del professore presenti nell'estrazione.\n"
                "> - Se un argomento non è trattato nelle fonti del corso, NON inserirlo nel MOC.\n"
            )
        else:
            prompt_lines.append(
                "> [!IMPORTANT] 🧠+🌐 PRIMATO DEL NOTEBOOKLM + INTEGRAZIONE AI (LEGGE 12 — MODALITÀ IBRIDA)\n"
                f"> Questo MOC ha come fonte primaria NotebookLM (`file://{context_dir / 'extracted_source.md'}`), integrato dalla tua conoscenza accademica:\n"
                "> 1. **Gerarchia Ferrea:** I moduli didattici, le notazioni e i percorsi del docente estratti comandano al 100%. In caso di contrasto di impostazione o sequenza, vince il NotebookLM.\n"
                "> 2. **Ruolo della Conoscenza di Base nel MOC:**\n"
                ">    - **Colmare buchi didattici d'esame:** Sei autorizzato a colmare eventuali buchi logici tra una lezione e l'altra del professore o omissioni dell'indice, garantendo che la sequenza propedeutica per preparare l'esame sia completa al 100%.\n"
                ">    - **Propedeuticità e Raccordi:** Esplicita i ponti logici e i collegamenti propedeutici tra i moduli, inserendo i wikilink dedicati a tutti i concetti e metodi necessari.\n"
            )
        prompt_lines.append("")
        prompt_lines.append("### 1. Leggi con una Sola Chiamata le Istruzioni Compilate")
        prompt_lines.append(f"- Leggi `file://{compiled_instructions_path}`.")
        prompt_lines.append(
            "  Focalizzati tassativamente sulla **Legge 4 (Filosofia dei MOC)** e sulla **Legge 11 (Sintesi Multi-Fonte Cross-Notebook)**:\n"
            "  * Il MOC deve essere **sempre discorsivo e narrativo**, spiegando nel testo *perché* i concetti si collegano tra loro.\n"
            "  * Struttura gerarchica a 3 livelli: Macro-MOC, Sub-MOC, Note Atomiche.\n"
            "  * **Legge 11 (Fusione Organica):** Non creare blocchi separati per ciascun notebook. Devi fondere organicamente i moduli, evidenziando correlazioni interdisciplinari e convergenze.\n"
            "  * Divieto assoluto di elenchi puntati sterili o asettici.\n"
        )
        prompt_lines.append("### 2. Estrai, Analizza e Fondi l'Architettura Concettuale da Tutti i NotebookLM")
        prompt_lines.append(
            f"- Consulta attentamente il dossier completo `file://{context_dir / 'extracted_source.md'}` dove sono state raccolte le estrazioni multi-query per blocco didattico, l'indice del libro, il diario delle lezioni e l'audit finale.\n"
            "- Ricostruisci l'intera alberatura della materia: moduli didattici, capitoli, definizioni cardine, teoremi e dimostrazioni chiave, metodi applicativi e problemi modello trattati nelle fonti."
        )

        scope = (source_results.get("metadata") or {}).get("scope", "")
        prompt_lines.append("")
        prompt_lines.append("### 2.1. Perimetro e Struttura del MOC")
        if scope == "indice del libro":
            prompt_lines.append(
                "- **L'indice del libro è la spina dorsale:** i moduli del MOC sono i capitoli dell'indice, nello stesso ordine; i paragrafi dell'indice guidano quali concetti, teoremi e metodi collegare in ciascun modulo.\n"
                "- **Il diario delle lezioni (se presente) integra:** gli argomenti fatti a lezione che l'indice non contiene vanno aggiunti nel modulo a cui appartengono logicamente; non cambiano l'ordine né la struttura.\n"
                "- **Fuori perimetro:** materiale del notebook che non appartiene né all'indice né al diario (es. altri libri caricati nello stesso notebook) NON entra nel MOC come modulo o wikilink. Se è rilevante, elencalo solo in fondo, nella sezione `## Argomenti delle Fonti Fuori dall'Indice`, come testo semplice senza doppie quadre.\n"
            )
        elif scope == "diario delle lezioni":
            prompt_lines.append(
                "- **Il diario delle lezioni è la spina dorsale:** i moduli seguono i blocchi di argomenti del diario, nell'ordine in cui sono stati svolti; materiale del notebook mai trattato a lezione non entra nel MOC.\n"
            )
        else:
            prompt_lines.append(
                "- **Nessun indice allegato:** il perimetro è l'intero notebook. Organizza i moduli seguendo l'indice generale estratto da NotebookLM (non l'elenco dei documenti).\n"
            )
        prompt_lines.append(
            "- **Copertura:** dentro il perimetro, ogni concetto, teorema e metodo trattato dalle fonti ha il suo `[[wikilink]]`, immerso nella narrazione che collega i moduli.\n"
        )
        prompt_lines.append("")
        prompt_lines.append("### 3. Incrocia la Mappa con l'Indice del Vault (`vault-index.json`)")
        prompt_lines.append(
            "- Consulta `.antigravity/vault-index.json`:\n"
            "  * **Concetti già presenti nel vault:** Devi utilizzare **esattamente il titolo del file esistente** (es. `[[Titolo Esatto]]`), integrandolo organicamente nella narrazione.\n"
            "  * **Concetti presenti nel NotebookLM ma non ancora creati nel vault:** Devi inserire i `[[wikilink]]` futuri con titoli canonici puliti, autoesplicativi e propedeutici (es. `[[Teorema Fondamentale]]`), trasformando il MOC nella **roadmap completa per lo studio futuro**.\n"
        )
        prompt_lines.append("### 4. Redazione Discorsiva del MOC a Sforzo Cognitivo Zero")
        prompt_lines.append(
            "- Articola il testo con spiegazioni chiare sul *filo logico conduttore* che unisce ciascun modulo al successivo.\n"
            "- Ogni `[[wikilink]]` deve essere immerso in un contesto discorsivo che ne chiarisca la rilevanza e il ruolo propedeutico.\n"
            "- Rispetta le sezioni previste dal profilo della materia (`.antigravity/disciplines/`)."
        )
        prompt_lines.append("")
        prompt_lines.append(get_moc_structural_rules_prompt())
        prompt_lines.append("")
        prompt_lines.append("### 5. Scrittura del File MOC e Raccordo Bidirezionale")
        prompt_lines.append(f"- Salva il MOC completo ESATTAMENTE in: `{moc_target}` (percorso assoluto `{vault_root / moc_target}`), con titolo H1 `# {topic} MOC`.")
        prompt_lines.append(
            "- **Raccordo Bidirezionale:** Se questo è un Sub-MOC, inserisci all'inizio il collegamento di risalita al Macro-MOC della disciplina "
            f"e aggiorna il Macro-MOC inserendo il link discorsivo a `[[{topic}]]`.\n"
        )

    # -------------------------------------------------------------
    # CASO B: MOC di Inizio Studio da Conoscenza Base di Antigravity
    # -------------------------------------------------------------
    elif moc_mode == "start_base_knowledge":
        mode_label = "MOC di Inizio Studio — Dalla Conoscenza Base di Antigravity (Roadmap da Zero)"

        prompt_lines.append(f"# MISSIONE MOC ANTIGRAVITY: {topic.upper()} (INIZIO STUDIO DA CONOSCENZA BASE)")
        prompt_lines.append("")
        prompt_lines.append("## Parametri del Job")
        prompt_lines.append(f"- **Argomento / Titolo MOC:** `{topic}`")
        prompt_lines.append(f"- **Tipo Operazione:** `MOC (Map of Content)`")
        prompt_lines.append(f"- **Modalità MOC:** `{mode_label}` (`{moc_mode}`)")
        prompt_lines.append(f"- **Disciplina:** `{discipline}` (Polo: `#{pole}`)")
        prompt_lines.append(f"- **Istruzioni Statiche Compilate:** `file://{compiled_instructions_path}`")
        prompt_lines.append(f"- **Indice del Vault:** `file://{resolve_vault_index_path(vault_root)}`")
        prompt_lines.append(f"- **Collegamenti Chirurgici Raccomandati:** `file://{context_dir / 'recommended-links.md'}`")
        prompt_lines.append(f"- **Titoli già esistenti o pianificati nella disciplina (da riusare identici):** `file://{titles_file}`")
        prompt_lines.append("")

        prompt_lines.append("## LE 5 AZIONI OBBLIGATORIE CHE DEVI ESEGUIRE ORA")
        prompt_lines.append("")
        prompt_lines.append("### 1. Leggi con una Sola Chiamata le Istruzioni Compilate")
        prompt_lines.append(f"- Leggi `file://{compiled_instructions_path}`.")
        prompt_lines.append(
            "  Focalizzati sulla **Legge 4 della Costituzione Universale (Filosofia dei MOC)**:\n"
            "  * Il MOC è una **narrazione accademica fluida**, non un elenco puntato.\n"
            "  * Struttura gerarchica a 3 livelli: Macro-MOC, Sub-MOC, Note Atomiche.\n"
        )
        prompt_lines.append("### 2. Consulta l'Elenco delle Note Esistenti nel Vault")
        prompt_lines.append(
            f"- Consulta l'elenco filtrato delle note già esistenti nel vault per `{discipline}` (riportate sotto in Contenuto Fonte).\n"
            "- Per ogni concetto già presente, usa rigorosamente il titolo esatto del file già esistente nel vault."
        )
        prompt_lines.append("")
        prompt_lines.append("### 3. Progetta la Roadmap Accademica Completa da Zero")
        prompt_lines.append(
            f"- Attingendo alla tua conoscenza di base profonda da trattato universitario autorevole, progetta da zero una roadmap completa per `{topic}`.\n"
            "- Organizza il percorso dai principi primi / assiomi fondamentali fino agli argomenti avanzati e alle applicazioni.\n"
            "- Crea i `[[wikilink]]` pianificati per tutti i teoremi, concetti e metodologie future da studiare con titoli canonici puliti."
        )
        prompt_lines.append("")
        prompt_lines.append("### 4. Stesura del MOC Discorsivo (Zero Sforzo Cognitivo)")
        prompt_lines.append(
            "- Connetti ogni sezione con una spiegazione chiara e fluida che illustri il *perché* logico della sequenza.\n"
            "- Evita tassativamente gli elenchi puntati spogli: ogni collegamento deve essere accompagnato da una frase di raccordo."
        )
        prompt_lines.append("")
        prompt_lines.append(get_moc_structural_rules_prompt())
        prompt_lines.append("")
        prompt_lines.append("### 5. Scrittura del File MOC e Raccordo")
        prompt_lines.append(f"- Salva il MOC completo ESATTAMENTE in: `{moc_target}` (percorso assoluto `{vault_root / moc_target}`), con titolo H1 `# {topic} MOC`.")
        prompt_lines.append("- Raccorda il MOC con il Macro-MOC sovraordinato della materia.")

    # -------------------------------------------------------------
    # CASO C: MOC di Fine Studio / Consolidamento dalle Note del Vault
    # -------------------------------------------------------------
    elif moc_mode == "end_vault_consolidation":
        mode_label = "MOC di Fine Studio / Consolidamento — Dalle Note Presenti nel Vault"
        dossier_path = context_dir / "vault_notes_summary.md"

        prompt_lines.append(f"# MISSIONE MOC ANTIGRAVITY: {topic.upper()} (FINE STUDIO / CONSOLIDAMENTO NOTE VAULT)")
        prompt_lines.append("")
        prompt_lines.append("## Parametri del Job")
        prompt_lines.append(f"- **Argomento / Titolo MOC:** `{topic}`")
        prompt_lines.append(f"- **Tipo Operazione:** `MOC (Map of Content)`")
        prompt_lines.append(f"- **Modalità MOC:** `{mode_label}` (`{moc_mode}`)")
        prompt_lines.append(f"- **Disciplina:** `{discipline}` (Polo: `#{pole}`)")
        prompt_lines.append(f"- **Dossier Note Esistenti:** `file://{dossier_path}`")
        prompt_lines.append(f"- **Istruzioni Statiche Compilate:** `file://{compiled_instructions_path}`")
        prompt_lines.append(f"- **Indice del Vault:** `file://{resolve_vault_index_path(vault_root)}`")
        prompt_lines.append(f"- **Collegamenti Chirurgici Raccomandati:** `file://{context_dir / 'recommended-links.md'}`")
        prompt_lines.append(f"- **Titoli già esistenti o pianificati nella disciplina (da riusare identici):** `file://{titles_file}`")
        prompt_lines.append("")

        prompt_lines.append("## LE 5 AZIONI OBBLIGATORIE CHE DEVI ESEGUIRE ORA")
        prompt_lines.append("")
        prompt_lines.append("### 1. Leggi con una Sola Chiamata le Istruzioni Compilate")
        prompt_lines.append(f"- Leggi `file://{compiled_instructions_path}` (Costituzione Legge 4 & Profilo Disciplinare).")
        prompt_lines.append("")
        prompt_lines.append("### 2. Studia a Fondo il Dossier delle Note Esistenti")
        prompt_lines.append(
            f"- Leggi `file://{dossier_path}`.\n"
            "  Il dossier contiene per ciascuna nota già scritta nel vault: titolo esatto, struttura H2/H3, introduzione e tutti i wikilink uscenti (esistenti e link rossi)."
        )
        prompt_lines.append("")
        prompt_lines.append("### 3. Costruisci il MOC Discorsivo di Sintesi Finale Pre-Esame")
        prompt_lines.append(
            "- Componi una narrazione organica unitaria che leghi insieme **tutte le note effettivamente create e studiate nel vault**:\n"
            "  * Spiega come ogni concetto, teorema, principio o metodo studiato si incastra con gli altri per fornire la sintesi pre-esame ad altissimo valore aggiunto.\n"
            "  * Collega ciascuna nota esistente con `[[Titolo Esatto]]`.\n"
            "  * Nessun elenco puntato asettico: ogni collegamento deve essere motivato e integrato nel discorso."
        )
        prompt_lines.append("")
        prompt_lines.append("### 4. Inserisci il Callout Diagnostico Obbligatorio di Fine Studio")
        prompt_lines.append(
            "- Inserisci **in fondo al MOC** il callout diagnostico vincolante:\n"
            "  ```markdown\n"
            "  > [!todo] Diagnosi di Completezza (Fine Studio / Pre-Esame)\n"
            "  > Questo callout evidenzia le lacune concettuali e i collegamenti aperti per completare la padronanza della materia prima dell'esame:\n"
            "  > \n"
            "  > ### Link Rossi (Concetti citati nelle note esistenti ma non ancora creati)\n"
            "  > - [[Nome Concetto]]: citato in [[Nota Sorgente]]\n"
            "  > \n"
            "  > ### Argomenti Cardine Mancanti per la Completezza\n"
            "  > - [Analisi critica degli argomenti fondamentali della materia che non risultano ancora presenti tra le note del vault]\n"
            "  ```\n"
            "  Prendi i Link Rossi direttamente dalla Sezione 2 del dossier `vault_notes_summary.md`."
        )
        prompt_lines.append("")
        prompt_lines.append(get_moc_structural_rules_prompt())
        prompt_lines.append("")
        prompt_lines.append("### 5. Scrittura del File MOC e Raccordo")
        prompt_lines.append(f"- Salva il MOC completo ESATTAMENTE in: `{moc_target}` (percorso assoluto `{vault_root / moc_target}`), con titolo H1 `# {topic} MOC`.")
        prompt_lines.append("- Raccorda il MOC con il Macro-MOC sovraordinato o le note correlate nel vault.")

    prompt_lines.append("")
    prompt_lines.append("---")
    prompt_lines.append("## CONTENUTO ESTRATTO DELLA FONTE / DOSSIER")
    prompt_lines.append("")
    prompt_lines.append(source_results.get("content_markdown", "*(Nessun contenuto sorgente estratto)*"))

    return "\n".join(prompt_lines)


def build_edit_operational_prompt(
    job_data: Dict[str, Any],
    discipline_cfg: Dict[str, Any],
    source_results: Dict[str, Any],
    auto_tool_results: Dict[str, Any],
    compiled_instructions_path: Path,
    vault_root: Path,
    context_dir: Path,
    backup_file: Optional[Path] = None,
) -> str:
    """Costruisce current-prompt.md per le 4 modalità di modifica / miglioramento nota esistente."""
    topic = job_data.get("topic") or job_data.get("title", "Senza Titolo")
    target_rel = job_data.get("target_file_path", "")
    discipline = job_data.get("discipline") or job_data.get("disciplina", "")
    pole = job_data.get("pole", "")
    edit_mode = job_data.get("edit_mode", "surgical_prompt")
    user_instructions = (job_data.get("user_instructions") or "").strip()
    target_content = source_results.get("target_content", "")
    if not target_content and target_rel:
        try:
            t_path = vault_root / target_rel
            if t_path.exists():
                target_content = t_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass

    backup_str = str(backup_file) if backup_file else str(vault_root / ".antigravity" / "backups" / "[backup mancante]")

    prompt_lines: List[str] = []

    # -------------------------------------------------------------
    # 1. MODALITÀ: CORREZIONE O AMPLIAMENTO CHIRURGICO (surgical_prompt)
    # -------------------------------------------------------------
    if edit_mode == "surgical_prompt":
        prompt_lines.append(f"# MISSIONE OPERATIVA ANTIGRAVITY: CORREZIONE O AMPLIAMENTO CHIRURGICO — {topic.upper()}")
        prompt_lines.append("")
        prompt_lines.append("## Parametri del Job")
        prompt_lines.append(f"- **Argomento / Nota Target:** `{topic}`")
        prompt_lines.append(f"- **File Target nel Vault:** `{target_rel}`")
        prompt_lines.append(f"- **Backup di Sicurezza:** `file://{backup_str}`")
        prompt_lines.append(f"- **Tipo Operazione:** `Modifica / Migliora Nota Esistente (edit)`")
        prompt_lines.append(f"- **Modalità di Modifica:** `✏️ Correzione o Ampliamento Chirurgico (Prompt Libero)` (`{edit_mode}`)")
        prompt_lines.append(f"- **Disciplina:** `{discipline}` (Polo: `#{pole}`)")
        prompt_lines.append(f"- **Istruzioni Specifiche dell'Utente:**")
        prompt_lines.append(f"  > \"{user_instructions}\"")
        prompt_lines.append(f"- **Istruzioni Statiche Compilate:** `file://{compiled_instructions_path}`")
        prompt_lines.append(f"- **Indice del Vault:** `file://{resolve_vault_index_path(vault_root)}`")
        prompt_lines.append(f"- **Collegamenti Chirurgici Raccomandati:** `file://{context_dir / 'recommended-links.md'}`")
        prompt_lines.append("")

        prompt_lines.append("## LE 5 AZIONI OBBLIGATORIE CHE DEVI ESEGUIRE ORA")
        prompt_lines.append("")
        prompt_lines.append("### 1. Leggi con una Sola Chiamata le Istruzioni Compilate (Legge 7 - Principio di Conservazione)")
        prompt_lines.append(f"- Leggi `file://{compiled_instructions_path}`.")
        prompt_lines.append(
            "  Focalizzati tassativamente sulla **Legge 7 della Costituzione Universale (Principio di Conservazione in Modalità Modifica)**:\n"
            "  * È severamente vietato impoverire, riassumere o cancellare parti della nota non coinvolte dalla richiesta.\n"
            "  * Preserva intatte tutte le dimostrazioni, definizioni, tabelle e dettagli preesistenti.\n"
        )
        prompt_lines.append("### 2. Analizza la Nota Target e Individua il Punto Chirurgico")
        prompt_lines.append(
            f"- Leggi il file originale in: `file://{vault_root / target_rel}` (o consulta la sezione 'Contenuto Attuale della Nota Target' in fondo a questo prompt).\n"
            f"- Esamina con la massima attenzione le istruzioni dell'utente:\n"
            f"  > \"{user_instructions}\"\n"
            "- Individua con precisione chirurgica la sezione, il passaggio algebrico, la formula, la definizione o il callout da correggere o ampliare."
        )
        prompt_lines.append("")
        prompt_lines.append("### 3. Applica la Modifica Chirurgica a Sforzo Cognitivo Zero")
        prompt_lines.append(
            "- Riscrivi o amplia **esclusivamente** la porzione di testo richiesta dall'utente, garantendo:\n"
            "  * **Legge 1 (Linguaggio Semplice ma Rigoroso):** Spiegazione fluida a sforzo mentale zero, visuale ed intuitiva.\n"
            "  * **Legge 2 (Zero Passaggi Sottintesi):** Se modifichi una dimostrazione o un calcolo algebrico, esplicita **tutti i passaggi intermedi**, motivando ogni passaggio con parole semplici e formule LaTeX su righe dedicate.\n"
            "  * Se è un approfondimento concettuale, arricchiscilo con collegamenti concreti e pratici.\n"
            "- **Preserva intatto al 100% tutto il resto della nota:** non alterare gli altri titoli H2/H3, i callout, le tabelle e i testi non interessati dalla correzione."
        )
        prompt_lines.append("")
        prompt_lines.append("### 4. Verifica di Coerenza dei [[Wikilink]] e del Frontmatter")
        prompt_lines.append(
            f"- Se la correzione introduce nuovi concetti, consulta `file://{resolve_vault_index_path(vault_root)}` per utilizzare i wikilink esatti alle note esistenti.\n"
            "- Mantieni inalterato il frontmatter YAML della nota originale, aggiornando unicamente la proprietà `modified` alla data odierna."
        )
        prompt_lines.append("")
        prompt_lines.append("### 5. Sovrascrittura Diretta del File Target e Preservazione Studio")
        prompt_lines.append(f"- Scrivi la versione finale aggiornata e rifinita direttamente nel file: `file://{vault_root / target_rel}`.")
        prompt_lines.append("- Se la correzione tocca nozioni presenti nelle flashcard o nei quiz in fondo alla nota, aggiorna coerentemente il blocco `%%STUDY_DATA` preservando il pannello interattivo.")
        prompt_lines.append("- Non usare MAI placeholder come `# TODO` o `...`. Scrivi la nota per intero, completa e senza abbreviazioni.")

    # -------------------------------------------------------------
    # 2. MODALITÀ: FONDI NUOVA FONTE NELLA NOTA (merge_source)
    # -------------------------------------------------------------
    elif edit_mode == "merge_source":
        prompt_lines.append(f"# MISSIONE OPERATIVA ANTIGRAVITY: FUSIONE NUOVA FONTE NELLA NOTA (MERGE INTELLIGENTE) — {topic.upper()}")
        prompt_lines.append("")
        prompt_lines.append("## Parametri del Job")
        prompt_lines.append(f"- **Argomento / Nota Target:** `{topic}`")
        prompt_lines.append(f"- **File Target nel Vault:** `{target_rel}`")
        prompt_lines.append(f"- **Backup di Sicurezza:** `file://{backup_str}`")
        prompt_lines.append(f"- **Tipo Operazione:** `Modifica / Migliora Nota Esistente (edit)`")
        prompt_lines.append(f"- **Modalità di Modifica:** `➕ Fondi Nuova Fonte nella Nota (Merge Intelligente)` (`{edit_mode}`)")
        prompt_lines.append(f"- **Nuova Fonte Selezionata:** `{source_results.get('label')}` (`{source_results.get('source_type')}`)")
        nb_list = source_results.get("notebooks") or []
        if len(nb_list) > 1:
            nb_names = [nb.get('title', nb.get('id', '')) if isinstance(nb, dict) else str(nb) for nb in nb_list]
            prompt_lines.append(f"- **NotebookLM Multipli da Fondere:** {len(nb_list)} quaderni ({', '.join(nb_names)})")
            prompt_lines.append("  > [!IMPORTANT]")
            prompt_lines.append("  > **Legge 11 (Cross-Notebook):** Integra armoniosamente i concetti e le nozioni provenienti dai molteplici quaderni NotebookLM. Non dividerli in sezioni isolate.")
        is_nb_source = (
            source_results.get("source_type") in ["notebooklm", "notebooklm_manual"]
            or job_data.get("source", {}).get("type") in ["notebooklm", "notebooklm_manual"]
        )
        if is_nb_source:
            allow_base_knowledge = bool(
                job_data.get("allow_base_knowledge", False)
                or job_data.get("source", {}).get("allow_base_knowledge", False)
            )
            mode_label = (
                "🧠+🌐 NotebookLM (Fonte Primaria) + Conoscenza di Base AI (Integrativa)"
                if allow_base_knowledge
                else "🔒 Solo NotebookLM (Esclusivo — Zero conoscenza esterna)"
            )
            prompt_lines.append(f"- **Modalità Conoscenza:** `{mode_label}` (`allow_base_knowledge: {str(allow_base_knowledge).lower()}`)")
        prompt_lines.append(f"- **Disciplina:** `{discipline}` (Polo: `#{pole}`)")
        prompt_lines.append(f"- **Indicazioni Utente per l'Integrazione:**")
        prompt_lines.append(f"  > \"{user_instructions or 'Integra organicamente tutto ciò che è rilevante dalla nuova fonte.'}\"")
        prompt_lines.append(f"- **Istruzioni Statiche Compilate:** `file://{compiled_instructions_path}`")
        prompt_lines.append(f"- **Indice del Vault:** `file://{resolve_vault_index_path(vault_root)}`")
        prompt_lines.append(f"- **Cartella Allegati:** `file://{vault_root / 'allegati'}`")
        prompt_lines.append("")

        prompt_lines.append("## LE 5 AZIONI OBBLIGATORIE CHE DEVI ESEGUIRE ORA")
        prompt_lines.append("")
        if is_nb_source:
            if not allow_base_knowledge:
                prompt_lines.append(
                    "> [!DANGER] ⚠️ VINCOLO INDEROGABILE DI ESCLUSIVITÀ NOTEBOOKLM (LEGGE 12 — MODALITÀ STRETTA)\n"
                    "> Le nuove informazioni da fondere DEVONO provenire al 100% dal testo estratto da NotebookLM.\n"
                    "> - **Confinamento Rigoroso:** È severamente vietato usare la conoscenza pre-addestrata per inventare contenuti non presenti nell'estrazione.\n"
                    "> - Usa esclusivamente le notazioni e le definizioni del notebook.\n"
                )
            else:
                prompt_lines.append(
                    "> [!IMPORTANT] 🧠+🌐 PRIMATO DEL NOTEBOOKLM + INTEGRAZIONE AI (LEGGE 12 — MODALITÀ IBRIDA)\n"
                    "> La nuova fonte NotebookLM è la guida primaria per l'arricchimento. La tua conoscenza base può intervenire come tutor accademico per chiarire, completare passaggi ed espandere le spiegazioni, preservando le notazioni del docente.\n"
                )
            prompt_lines.append("")
        prompt_lines.append("### 1. Leggi le Istruzioni Compilate e Rispetta la Legge 7 (Merge Organico e Armonico)")
        prompt_lines.append(f"- Leggi `file://{compiled_instructions_path}`.")
        prompt_lines.append(
            "  Focalizzati sulla **Legge 7 della Costituzione Universale**:\n"
            "  * Il merge deve essere un **arricchimento incrementale armonico**, non una sostituzione né una sintesi distruttiva.\n"
            "  * Non cancellare e non impoverire le dimostrazioni, spiegazioni, formule e tabelle già presenti nella nota target.\n"
        )
        prompt_lines.append("### 2. Ispezione Visiva dei Media Estratti dalla Nuova Fonte")
        extracted_files = source_results.get("extracted_files", [])
        if extracted_files:
            prompt_lines.append("Dalla nuova fonte sono stati estratti questi file multimediali:")
            for ef in extracted_files:
                prompt_lines.append(f"  - `file://{vault_root / 'allegati' / ef}` (Wikilink: `![[{ef}]]`)")
            prompt_lines.append(
                "> [!IMPORTANT]\n"
                "> Prima di inserire qualsiasi immagine o screenshot nella nota, **ispezionala visivamente** "
                "con il tool di lettura per verificare che contenga setup, diagrammi o passaggi didattici utili, scartando i frame non rilevanti.\n"
            )
        else:
            prompt_lines.append("*(Nessun file multimediale estratto dalla nuova fonte)*\n")

        prompt_lines.append("### 3. Fusione Organica e Non Ridondante nella Struttura Esistente")
        prompt_lines.append(
            f"- Leggi attentamente la nota target originale in `file://{vault_root / target_rel}` e il contenuto della nuova fonte riportato sotto.\n"
            "- Innesta i nuovi concetti, i dettagli tecnici, i casi studio e gli esempi nelle sezioni H2/H3 già presenti dove sono logicamente pertinenti.\n"
            "- Se la nuova fonte tratta aspetti inediti o non ancora coperti dalla nota, crea nuove sezioni H2 o sottosezioni H3 coerenti con lo stile della materia.\n"
            "- Evita duplicazioni verbali mantenendo sempre la formulazione più esaustiva, chiara e priva di passaggi sottintesi."
        )
        prompt_lines.append("")
        prompt_lines.append("### 4. Integrazione Studi Scientifici PubMed e Aggiornamento [[Wikilink]]")
        pubmed_data = auto_tool_results.get("pubmed_evidence")
        if pubmed_data and pubmed_data.get("articles"):
            prompt_lines.append(
                f"- Sono stati estratti **{len(pubmed_data['articles'])} paper PubMed reali** basati sulla nuova fonte e sul testo della nota.\n"
                "  Consulta `.antigravity/job-context/pubmed_evidence.json` ed integra o aggiorna la tabella degli studi scientifici con i link PMID."
            )
        else:
            prompt_lines.append("- *(Nessun nuovo studio PubMed rilevato o richiesto per questa disciplina)*")
        prompt_lines.append(f"- Consulta `file://{resolve_vault_index_path(vault_root)}` per inserire i wikilink verso le note del vault corrispondenti ai nuovi termini.")
        prompt_lines.append("")
        prompt_lines.append("### 5. Scrittura del File Finale, Aggiornamento Palestra d'Esame e MOC")
        prompt_lines.append(f"- Sovrascrivi il file target `file://{vault_root / target_rel}` con la nota fusa e arricchita, aggiornando la data `modified` nel frontmatter YAML.")
        prompt_lines.append("- **Aggiornamento Palestra d'Esame (Legge 8):** Integra nel blocco `%%STUDY_DATA` nuove flashcard e quiz (o inserisci ex novo il callout interattivo se assente) per testare attivamente le nuove nozioni acquisite dalla fonte.")
        prompt_lines.append(
            f"- **Aggiornamento MOC:** Se la nuova fonte ha ampliato il perimetro tematico della nota, individua il MOC o Sub-MOC di riferimento "
            f"per `{discipline}` nel vault ed aggiorna la frase di collegamento discorsivo verso `[[{topic}]]`.\n"
        )

    # -------------------------------------------------------------
    # 3. MODALITÀ: AGGIORNA STUDI PUBMED, IMMAGINI E WIKILINK (refresh_enrichment)
    # -------------------------------------------------------------
    elif edit_mode == "refresh_enrichment":
        prompt_lines.append(f"# MISSIONE OPERATIVA ANTIGRAVITY: AGGIORNAMENTO STUDI PUBMED, IMMAGINI E WIKILINK — {topic.upper()}")
        prompt_lines.append("")
        prompt_lines.append("## Parametri del Job")
        prompt_lines.append(f"- **Argomento / Nota Target:** `{topic}`")
        prompt_lines.append(f"- **File Target nel Vault:** `{target_rel}`")
        prompt_lines.append(f"- **Backup di Sicurezza:** `file://{backup_str}`")
        prompt_lines.append(f"- **Tipo Operazione:** `Modifica / Migliora Nota Esistente (edit)`")
        prompt_lines.append(f"- **Modalità di Modifica:** `🔬 Aggiorna Studi PubMed, Immagini e Wikilink del Vault` (`{edit_mode}`)")
        prompt_lines.append(f"- **Disciplina:** `{discipline}` (Polo: `#{pole}`)")
        prompt_lines.append(f"- **Istruzioni Statiche Compilate:** `file://{compiled_instructions_path}`")
        prompt_lines.append(f"- **Indice del Vault:** `file://{resolve_vault_index_path(vault_root)}`")
        prompt_lines.append(f"- **Cartella Allegati:** `file://{vault_root / 'allegati'}`")
        prompt_lines.append("")

        prompt_lines.append("## LE 5 AZIONI OBBLIGATORIE CHE DEVI ESEGUIRE ORA")
        prompt_lines.append("")
        prompt_lines.append("### 1. Leggi le Istruzioni Compilate e Rispetta la Legge 7")
        prompt_lines.append(f"- Leggi `file://{compiled_instructions_path}`.")
        prompt_lines.append(
            "  Rispetta la **Legge 7 della Costituzione Universale (Principio di Conservazione)**:\n"
            "  * Questa modalità serve ad arricchire la nota con studi recenti, immagini scientifiche e collegamenti al grafo, NON a modificare o accorciare il testo teorico già validato.\n"
        )
        prompt_lines.append("### 2. Analizza il Testo Attuale della Nota Target")
        prompt_lines.append(
            f"- Leggi il file originale in: `file://{vault_root / target_rel}`.\n"
            "- Esamina la struttura attuale delle sezioni, le evidenze già citate e i termini chiave anatomici, biochimici o tecnici presenti nel corpo del testo."
        )
        prompt_lines.append("")
        prompt_lines.append("### 3. Aggiorna la Sezione Evidenze Scientifiche e Media")
        pubmed_data = auto_tool_results.get("pubmed_evidence")
        if pubmed_data and pubmed_data.get("articles"):
            prompt_lines.append(
                f"- Il motore PubMed ha estratto **{len(pubmed_data['articles'])} paper scientifici reali** basandosi sui termini della nota.\n"
                "  Consulta `.antigravity/job-context/pubmed_evidence.json` ed inserisci o aggiorna la tabella dedicata agli studi scientifici:\n"
                "  | Studio (Autori, Anno) | Disegno Sperimentale e Campione | Risultati Chiave | Conclusione Pratica (Zero Sforzo) | PMID |\n"
                "  | :--- | :--- | :--- | :--- | :---: |"
            )
        else:
            prompt_lines.append("- *(Nessun nuovo studio PubMed rilevato per i termini della nota)*")

        media_data = auto_tool_results.get("science_media")
        if media_data and media_data.get("downloaded"):
            prompt_lines.append(f"- Sono state scaricate {len(media_data['downloaded'])} immagini scientifiche in `allegati/`. Ispezionale e integrane le più salienti.")
        prompt_lines.append("")
        prompt_lines.append("### 4. Ricalcolo e Aggiornamento dei [[Wikilink]] con il Vault Index")
        prompt_lines.append(
            f"- Consulta `file://{resolve_vault_index_path(vault_root)}`:\n"
            "  * Scansiona i concetti, teoremi o termini citati nel testo della nota: se ora corrispondono a nuove note create nel vault, "
            "inserisci il wikilink formattato `[[Titolo Esatto|termine nel testo]]`.\n"
            "  * Se alcuni wikilink puntavano a titoli poi rinominati, correggili con il titolo esatto presente nell'indice."
        )
        prompt_lines.append("")
        prompt_lines.append("### 5. Sovrascrittura del File Target e Raccordo col MOC")
        prompt_lines.append(f"- Salva la nota arricchita in: `file://{vault_root / target_rel}`, aggiornando `modified: YYYY-MM-DD` nel frontmatter YAML.")
        prompt_lines.append("- Apri il MOC di riferimento per la disciplina e accertati che il collegamento e la sua frase esplicativa siano aggiornati.")

    # -------------------------------------------------------------
    # 4. MODALITÀ: RISTRUTTURAZIONE ALLO STANDARD DELLA DISCIPLINA (reformat_standard)
    # -------------------------------------------------------------
    elif edit_mode == "reformat_standard":
        prompt_lines.append(f"# MISSIONE OPERATIVA ANTIGRAVITY: RISTRUTTURAZIONE ALLO STANDARD COMPLETO — {topic.upper()}")
        prompt_lines.append("")
        prompt_lines.append("## Parametri del Job")
        prompt_lines.append(f"- **Argomento / Nota Target:** `{topic}`")
        prompt_lines.append(f"- **File Target nel Vault:** `{target_rel}`")
        prompt_lines.append(f"- **Backup di Sicurezza:** `file://{backup_str}`")
        prompt_lines.append(f"- **Tipo Operazione:** `Modifica / Migliora Nota Esistente (edit)`")
        prompt_lines.append(f"- **Modalità di Modifica:** `✨ Riformatta e Porta allo Standard Completo della Disciplina` (`{edit_mode}`)")
        prompt_lines.append(f"- **Disciplina:** `{discipline}` (Polo: `#{pole}`)")
        if user_instructions:
            prompt_lines.append(f"- **Note Particolari dell'Utente:**")
            prompt_lines.append(f"  > \"{user_instructions}\"")
        prompt_lines.append(f"- **Istruzioni Statiche Compilate:** `file://{compiled_instructions_path}`")
        prompt_lines.append(f"- **Indice del Vault:** `file://{resolve_vault_index_path(vault_root)}`")
        prompt_lines.append(f"- **Collegamenti Chirurgici Raccomandati:** `file://{context_dir / 'recommended-links.md'}`")
        prompt_lines.append("")

        prompt_lines.append("## LE 5 AZIONI OBBLIGATORIE CHE DEVI ESEGUIRE ORA")
        prompt_lines.append("")
        prompt_lines.append("### 1. Leggi con una Sola Chiamata le Istruzioni Compilate")
        prompt_lines.append(f"- Leggi `file://{compiled_instructions_path}` (Costituzione, Profilo Disciplina e Blueprint Stilistico).")
        prompt_lines.append(
            f"  Identifica con precisione tutti gli standard formali ed estetici previsti per `{discipline}`:\n"
            "  * Frontmatter YAML canonico (`Type`, `Polo`, `Disciplina`, `tags`, `aliases`, `created`, `modified`).\n"
            "  * Callout di Decodifica / Big Picture ad inizio nota.\n"
            "  * Struttura a sezioni logiche progressive con titoli H2 e H3 chiari.\n"
            "  * Zero passaggi sottintesi (dimostrazioni algebriche o catene causali completamente esplicitate).\n"
            "  * Tabella comparativa o riepilogativa finale.\n"
            "  * Callout di sintesi / checklist applicativa in fondo.\n"
        )
        prompt_lines.append("### 2. Analisi Completa della Nota Originale (100% Conservazione delle Informazioni)")
        prompt_lines.append(
            f"- Leggi il testo della nota originale in `file://{vault_root / target_rel}` (riportato anche sotto).\n"
            "- **Regola Aurea della Ristrutturazione:** Mantieni il 100% delle informazioni, dati, formule, osservazioni pratiche e dettagli presenti negli appunti originali.\n"
            "- È severamente vietato sintetizzare, riassumere o scartare dati: ogni elemento informativo originale deve trovare la sua perfetta collocazione nella nuova architettura."
        )
        prompt_lines.append("")
        prompt_lines.append("### 3. Riorganizzazione Architetturale allo Standard della Disciplina")
        prompt_lines.append(
            "- Riscrivi la nota applicando lo schema d'eccellenza della materia:\n"
            "  * Aggiungi il callout di Decodifica iniziale per dare la Big Picture a sforzo cognitivo zero.\n"
            "  * Esplicita tutti i passaggi matematici o logici che negli appunti originali erano dati per scontati o compressi.\n"
            "  * Se ci sono formule matematiche, formattale in blocchi LaTeX dedicati `$$ ... $$` e spiega ogni simbolo a parole semplici.\n"
            "  * Costruisci una tabella riepilogativa rigorosa che sintetizzi i punti chiave trattati."
        )
        prompt_lines.append("")
        prompt_lines.append("### 4. Potenziamento del Grafo di Wikilink")
        prompt_lines.append(
            f"- Consulta `file://{resolve_vault_index_path(vault_root)}`.\n"
            "- Immergi nel testo i collegamenti ipertestuali a tutti i concetti e teoremi correlati già presenti nel vault (`[[Titolo Esatto|termine nel testo]]`).\n"
            "- Evita wikilink nei titoli H2/H3 o dentro i blocchi LaTeX."
        )
        prompt_lines.append("")
        prompt_lines.append("### 5. Sovrascrittura del File Target, Palestra d'Esame e Raccordo col MOC")
        prompt_lines.append(f"- Sovrascrivi il file target `file://{vault_root / target_rel}` con la nota completamente ristrutturata e priva di qualunque omissione.")
        prompt_lines.append(
            "- **Palestra d'Esame Interattiva (Legge 8 Obbligatoria):** Aggiungi a fondo nota il callout chiuso di default con `.antigravity/scripts/study_panel.js` "
            "e il blocco `%%STUDY_DATA` contenente almeno 6–10 Flashcard e 4–6 Quiz a Scelta Multipla, strutturati secondo i principi scientifici di "
            "Retrieval Practice, Elaborative Interrogation e Desirable Difficulties."
        )
        prompt_lines.append("- Apri il MOC di riferimento della disciplina nel vault e verifica il raccordo discorsivo.")

    # Regole tassative di forma e formattazione per la modalità modifica
    prompt_lines.append("")
    prompt_lines.append("### REGOLE TASSATIVE DI FORMA E FORMATTAZIONE:")
    prompt_lines.append(
        "- **DELIMITAZIONE FORMULE LATEX NELLE NOTE NORMALI:**\n"
        "  Nella prosa Markdown delle Note Normali, ogni espressione matematica LaTeX deve essere racchiusa nei delimitatori appropriati: $...$ inline e $$...$$ per formule isolate. Non lasciare comandi come \\forall, \\exists, \\frac, \\mathbb, \\lim, \\sum o \\in fuori dalla modalità matematica. Controlla anche callout e contenuti di studio.\n"
        "- **DIVIETO DI `\\vline` IN LATEX:**\n"
        "  Obsidian MathJax non supporta `\\vline` e genera errore di parsing rosso. È tassativamente vietato usare `\\vline`.\n"
        "  Per linee verticali in formule matematiche, matrici o insiemi usa sempre `\\vert`, `|` o `\\mid` (es. `\\{x \\in A \\mid P(x)\\}`).\n"
        "- **ZERO EMOJI NELLE NOTE E NEI MOC (PURGA TOTALE):**\n"
        "  Divieto assoluto di usare emoji Unicode all'interno dei testi generati (note e MOC).\n"
        "- **WIKILINK PURI SENZA APICI NÉ BACKTICK:**\n"
        "  Tutti i collegamenti ipertestuali devono essere scritti SEMPRE in formato puro Obsidian: `[[Nome Nota]]` o `[[Nome Nota#Paragrafo|Alias]]`."
    )

    # Sezione finale di contesto per tutte le modalità
    prompt_lines.append("")
    prompt_lines.append("---")
    prompt_lines.append("## TESTO ATTUALE DELLA NOTA TARGET (PRIMA DELLA MODIFICA)")
    prompt_lines.append("")
    prompt_lines.append(target_content or "*(File target attualmente vuoto o non accessibile)*")

    if edit_mode == "merge_source":
        prompt_lines.append("")
        prompt_lines.append("---")
        prompt_lines.append("## CONTENUTO ESTRATTO DALLA NUOVA FONTE DA FONDERE")
        prompt_lines.append("")
        prompt_lines.append(source_results.get("content_markdown", "*(Nessun contenuto estratto dalla nuova fonte)*"))

    return "\n".join(prompt_lines)


def build_operational_prompt(
    job_data: Dict[str, Any],
    discipline_cfg: Dict[str, Any],
    source_results: Dict[str, Any],
    auto_tool_results: Dict[str, Any],
    compiled_instructions_path: Path,
    vault_root: Path,
    context_dir: Optional[Path] = None,
    backup_file: Optional[Path] = None,
) -> str:
    """Costruisce current-prompt.md che guida Antigravity nell'esecuzione del task (Nota Normale, MOC o Edit)."""
    op_type = job_data.get("operation_type") or job_data.get("operation", "normal")

    # Instradamento al generatore dedicato per MOC
    if op_type == "moc":
        ctx_dir = context_dir or (vault_root / ".antigravity" / "job-context")
        return build_moc_operational_prompt(
            job_data=job_data,
            discipline_cfg=discipline_cfg,
            source_results=source_results,
            compiled_instructions_path=compiled_instructions_path,
            vault_root=vault_root,
            context_dir=ctx_dir,
        )

    # Instradamento al generatore dedicato per Modifica / Miglioramento Nota
    if op_type == "edit":
        ctx_dir = context_dir or (vault_root / ".antigravity" / "job-context")
        return build_edit_operational_prompt(
            job_data=job_data,
            discipline_cfg=discipline_cfg,
            source_results=source_results,
            auto_tool_results=auto_tool_results,
            compiled_instructions_path=compiled_instructions_path,
            vault_root=vault_root,
            context_dir=ctx_dir,
            backup_file=backup_file,
        )

    # Flusso standard per Nota Normale
    topic = job_data.get("topic", "Senza Titolo")
    op_label = job_data.get("operation_label", "Nota Normale")
    discipline = job_data.get("discipline", "")
    pole = job_data.get("pole", "")
    target_rel = job_data.get("target_file_path") or f"{discipline}/{topic}.md"

    prompt_lines: List[str] = []
    prompt_lines.append(f"# MISSIONE OPERATIVA ANTIGRAVITY: {topic.upper()}")
    prompt_lines.append("")
    prompt_lines.append("## Parametri del Job")
    prompt_lines.append(f"- **Argomento / Titolo:** `{topic}`")
    prompt_lines.append(f"- **Tipo Operazione:** `{op_label}` (`{op_type}`)")
    prompt_lines.append(f"- **Disciplina:** `{discipline}` (Polo: `#{pole}`)")
    prompt_lines.append(f"- **File Target Obbligatorio:** `{target_rel}` (percorso: `{vault_root / target_rel}`)")
    prompt_lines.append(f"- **Fonte Selezionata:** `{source_results.get('label')}` (`{source_results.get('source_type')}`)")
    try:
        import vault_layout
        moc_sections = vault_layout.requested_sections(vault_root, topic)
    except Exception:
        moc_sections = []
    if moc_sections:
        prompt_lines.append(
            "- **Sezioni richieste dal MOC (obbligatorie):** il MOC collega questi argomenti come paragrafi di questa nota "
            "con `[[" + topic + "#Sezione]]`. Ognuno deve essere un titolo `##` o `###` scritto ESATTAMENTE così, "
            "trattato con il materiale delle fonti: " + "; ".join(f"`{sec}`" for sec in moc_sections)
        )
    ctx_dir = context_dir or (vault_root / ".antigravity" / "job-context")
    recom_links_path = ctx_dir / "recommended-links.md"
    claims_path = ctx_dir / "existing-vault-claims.md"

    notebooks_meta = (source_results.get("metadata") or {}).get("notebooks") or extract_notebooks_list(job_data.get("source", {}), job_data)
    is_notebook_source = (
        source_results.get("source_type") in ["notebooklm", "notebooklm_manual"]
        or job_data.get("source", {}).get("type") in ["notebooklm", "notebooklm_manual"]
        or job_data.get("source_type") in ["notebooklm", "notebooklm_manual"]
        or bool(notebooks_meta)
    )
    allow_base_knowledge = bool(
        job_data.get("allow_base_knowledge", False)
        or job_data.get("source", {}).get("allow_base_knowledge", False)
    )
    is_multi_nb = len(notebooks_meta) > 1
    if is_multi_nb:
        prompt_lines.append(f"- **NotebookLM Multipli Fusi ({len(notebooks_meta)} fonti):**")
        for idx, nb in enumerate(notebooks_meta, 1):
            prompt_lines.append(f"  * Fonte {idx}: `{nb['title']}` (ID: `{nb['id']}`)")
        prompt_lines.append(f"- **Dossier Fonti Concatenate:** `file://{ctx_dir / 'extracted_source.md'}`")
    elif is_notebook_source:
        single_nb = notebooks_meta[0] if notebooks_meta else {"title": source_results.get("label", "NotebookLM"), "id": "N/D"}
        prompt_lines.append(f"- **NotebookLM Selezionato:** `{single_nb.get('title')}` (ID: `{single_nb.get('id')}`)")
        prompt_lines.append(f"- **Dossier Fonte NotebookLM (Estratto Reale):** `file://{ctx_dir / 'extracted_source.md'}`")

    if is_notebook_source:
        mode_label = (
            "🧠+🌐 NotebookLM (Fonte Primaria) + Conoscenza di Base AI (Integrativa)"
            if allow_base_knowledge
            else "🔒 Solo NotebookLM (Esclusivo — Zero conoscenza esterna)"
        )
        prompt_lines.append(f"- **Modalità Conoscenza:** `{mode_label}` (`allow_base_knowledge: {str(allow_base_knowledge).lower()}`)")

    prompt_lines.append(f"- **Istruzioni Statiche Compilate:** `file://{compiled_instructions_path}`")
    prompt_lines.append(f"- **Indice del Vault:** `file://{resolve_vault_index_path(vault_root)}`")
    prompt_lines.append(f"- **Collegamenti Chirurgici Raccomandati:** `file://{recom_links_path}`")
    prompt_lines.append(f"- **Tesi ed Evidenze Preesistenti nel Vault (Controllo Conflitti Epistemici):** `file://{claims_path}`")
    prompt_lines.append(f"- **Cartella Allegati:** `file://{vault_root / 'allegati'}`")
    prompt_lines.append("")

    prompt_lines.append("## LE 5 AZIONI OBBLIGATORIE CHE DEVI ESEGUIRE ORA")
    prompt_lines.append("")
    if is_notebook_source:
        if not allow_base_knowledge:
            prompt_lines.append(
                "> [!DANGER] ⚠️ VINCOLO INDEROGABILE DI ESCLUSIVITÀ NOTEBOOKLM (LEGGE 12 — MODALITÀ STRETTA)\n"
                f"> Questa nota DEVE basarsi al 100% sul testo estratto da NotebookLM presente in `file://{ctx_dir / 'extracted_source.md'}`.\n"
                "> - **Confinamento Rigoroso:** Puoi usare **esclusivamente** le definizioni, i teoremi, le dimostrazioni e gli esempi presenti in `extracted_source.md`.\n"
                "> - È SEVERAMENTE VIETATO usare la tua conoscenza pre-addestrata per colmare lacune o 'inventare' dimostrazioni/definizioni non presenti nelle fonti.\n"
                "> - Usa ESCLUSIVAMENTE le notazioni, i passaggi e le convenzioni del professore presenti nell'estrazione.\n"
                "> - La tua capacità deduttiva è ammessa SOLO per esplicitare passaggi matematici e logici intermedi saltati negli appunti (*Zero Passi Saltati*).\n"
                "> - Se un passaggio o una dimostrazione manca nel testo estratto, dichiara esplicitamente nel testo: `*(Dimostrazione non presente nelle fonti del professore)*` invece di generarla da zero.\n"
            )
        else:
            prompt_lines.append(
                "> [!IMPORTANT] 🧠+🌐 PRIMATO DEL NOTEBOOKLM + INTEGRAZIONE AI (LEGGE 12 — MODALITÀ IBRIDA)\n"
                f"> Questa nota ha come fonte primaria NotebookLM (`file://{ctx_dir / 'extracted_source.md'}`), integrato dalla tua conoscenza accademica:\n"
                "> 1. **Gerarchia Ferrea (Il NotebookLM comanda sempre):** Il materiale estratto da NotebookLM comanda al 100% su struttura, taglio didattico, notazioni del professore, definizioni principali e impostazione delle dimostrazioni. In caso di contrasto o discrepanza tra la tua conoscenza base e il NotebookLM, **vince sempre e indiscutibilmente il NotebookLM**.\n"
                "> 2. **Ruolo della Conoscenza di Base (Integrazione Accademica Autorizzata):**\n"
                ">    - **Completare ed espandere:** Completa ed espandi definizioni, casi particolari, osservazioni o proprietà che negli appunti del NotebookLM sono solo accennati, incompleti o sintetici.\n"
                ">    - **Dimostrazioni complete:** Fornisci dimostrazioni rigorose complete se nelle fonti del NotebookLM è riportato solo l'enunciato o una traccia parziale (adottando rigorosamente i simboli e le convenzioni del professore).\n"
                ">    - **Esempi e Intuizioni:** Aggiungi controesempi classici, interpretazioni geometriche/intuitive ed esempi chiarificatori che arricchiscono la spiegazione del concetto.\n"
                ">    - **Confine Concettuale:** Rispetta sempre il confine concettuale della singola nota (un solo concetto/teorema cardine per nota, senza inglobare teoremi derivati o metodi che appartengono a note separate collegate tramite wikilink).\n"
            )
        prompt_lines.append("")

    prompt_lines.append("### 1. Leggi con una Sola Chiamata le Istruzioni Compilate")
    prompt_lines.append(f"- Leggi `file://{compiled_instructions_path}`.")
    prompt_lines.append("  Esso contiene in un unico documento: la Costituzione Universale, il Profilo della Materia e il Blueprint Stilistico Compresso.")
    if is_notebook_source:
        if not allow_base_knowledge:
            prompt_lines.append(
                "> [!DANGER] ⚠️ VINCOLO INDEROGABILE DI ESCLUSIVITÀ NOTEBOOKLM (LEGGE 12 — MODALITÀ STRETTA):\n"
                f"> Leggi prioritariamente ed integralmente il dossier delle fonti: `file://{ctx_dir / 'extracted_source.md'}`.\n"
                "> Questa nota DEVE attingere unicamente ed esclusivamente dai contenuti reali estratti da NotebookLM. Divieto assoluto di conoscenza base esterna.\n"
            )
        else:
            prompt_lines.append(
                "> [!NOTE] 🧠+🌐 INTEGRAZIONE ACCADEMICA CON PRIMATO DEL NOTEBOOKLM (LEGGE 12 — MODALITÀ IBRIDA):\n"
                f"> Leggi prioritariamente il dossier delle fonti: `file://{ctx_dir / 'extracted_source.md'}` come guida sovrana.\n"
                "> Usa la tua conoscenza pre-addestrata come tutor accademico per colmare omissioni, completare dimostrazioni parziali e aggiungere esempi, mantenendo intatte le convenzioni del docente.\n"
            )
    if is_multi_nb:
        prompt_lines.append(
            "> [!IMPORTANT]\n"
            "> **LEGGE 11 DELLA COSTITUZIONE (Sintesi Multi-Fonte Cross-Notebook — Organica e Non Forzata):**\n"
            "> Ti vengono fornite informazioni estratte da più NotebookLM contemporaneamente.\n"
            "> **Non limitarti a incollarle in blocchi separati.** Devi **fondere organicamente i concetti** "
            "secondo l'evoluzione logica del tema. Non inserire sezioni o confronti interdisciplinari forzati se non giustificati dalle fonti.\n"
        )
    prompt_lines.append("")

    prompt_lines.append("### 2. Ispezione Visiva dei Media Estratti (claude-watch / FFmpeg)")
    extracted_files = source_results.get("extracted_files", [])
    if extracted_files:
        prompt_lines.append("Sono stati estratti e salvati nella cartella allegati questi file multimediali:")
        for ef in extracted_files:
            prompt_lines.append(f"  - `file://{vault_root / 'allegati' / ef}` (Wikilink: `![[{ef}]]`)")
        prompt_lines.append(
            "> [!IMPORTANT]\n"
            "> Prima di inserire qualsiasi immagine nella nota finale, **ispezionala visivamente** "
            "con il tuo tool di lettura file per accertarti che mostri lo schema, grafico o setup saliente "
            "e scarta eventuali fotogrammi non rilevanti.\n"
        )
    else:
        prompt_lines.append("*(Nessun fotogramma estratto per questo job)*\n")

    prompt_lines.append("### 3. Evidenze PubMed Estratte Sequenzialmente")
    pubmed_data = auto_tool_results.get("pubmed_evidence")
    if pubmed_data and pubmed_data.get("articles"):
        queries_used = ", ".join([f"`{q}`" for q in pubmed_data.get("queries_executed", [])])
        prompt_lines.append(f"Il motore PubMed intelligente ha interrogato la letteratura con query estratte dal testo ({queries_used}) trovando **{len(pubmed_data['articles'])} paper reali**.")
        prompt_lines.append("Consulta `.antigravity/job-context/pubmed_evidence.json` ed inserisci nella nota la tabella con i link PMID e le metodiche d'indagine.")
        prompt_lines.append("")
    else:
        prompt_lines.append("*(Nessuna ricerca PubMed richiesta o effettuata)*\n")

    prompt_lines.append("### 4. Rilevamento Conflitti Epistemici (Legge 9) e Collegamenti Chirurgici (Legge 5)")
    prompt_lines.append(
        f"- **Rilevamento Conflitti Epistemici (Legge 9 della Costituzione — Condizionale):**\n"
        f"  Leggi attentamente `file://{claims_path}` contenente i passaggi del vault più correlati al tema.\n"
        "  Confronta le tesi della nuova fonte con quanto già presente nel vault.\n"
        "  Se e solo se rilevi una reale **contraddizione concettuale, discrepanza nei dati o evoluzione scientifica accertata** (nessuna sezione forzata se non vi è conflitto), inserisci nella nota il callout:\n"
        "  ```markdown\n"
        "  > [!warning] Conflitto Epistemico / Evoluzione rispetto a [[Nome Nota Esistente#Paragrafo]]\n"
        "  > - **Cosa riporta la nota precedente nel vault**: <Sintesi fedele>\n"
        "  > - **Cosa afferma la nuova fonte / letteratura**: <Sintesi nuova evidenza>\n"
        "  > - **Risoluzione Critica**: <Spiegazione rigorosa della differenza (diverso contesto, evoluzione del consenso, diverso metodo)>\n"
        "  ```"
    )
    prompt_lines.append(
        f"- **Collegamenti Chirurgici a Paragrafi e Blocchi:**\n"
        f"  Leggi attentamente il dossier `file://{recom_links_path}` e l'indice `file://{resolve_vault_index_path(vault_root)}`:\n"
        "  * **Tabella A (Collegamenti Chirurgici a Paragrafi):** Quando tratti un passaggio logico, una proprietà algebrica, un metodo o un sottoconcetto trattato altrove, usa **obbligatoriamente** il link di sezione `[[Nome Nota#Numero e Titolo Esatto Paragrafo|testo nel discorso]]` (es. `[[Numeri Interi Relativi#4.2 Proprietà di Integrità e Legge di Cancellazione Moltiplicativa|legge di cancellazione moltiplicativa]]`).\n"
        "  * **Tabella B (Callout e Blocchi Semantici):** Quando citi un teorema, una definizione o una decodifica specifica presente nel vault, cita direttamente il blocco con `[[Nome Nota#^id-blocco|testo nel discorso]]`.\n"
        "  * **Tabella C (Note Intere e MOC):** Usa `[[Nome Nota|testo]]` per inquadrare l'oggetto generale o i collegamenti macro.\n"
        "  * **Nuovi ID di Blocco:** Nella nota che stai scrivendo, in fondo ai callout più importanti (`> [!theorem]`, `> [!definition]`, `> [!tip] Dimostrazione...`, `> [!note] Decodifica...`) assegna un ID di blocco semantico pulito in kebab-case (`^teo-...`, `^def-...`, `^decodifica-...`).\n"
        "  * **Sezione Finale:** Nella sezione finale `Note e Paragrafi Collegati`, struttura le voci in modo pulito ed esclusivo: (1) `### Teoremi e Concetti Derivati (Note Separate)` con l'elenco di ciò che hai scorporato con breve raccordo e wikilink; (2) `### Riferimenti Puntuali a Paragrafi` con i link chirurgici a sezioni e blocchi usati nel testo; (3) `### Note Generali e MOC`.\n"
    )

    prompt_lines.append("### REGOLE TASSATIVE DI FORMA E FORMATTAZIONE:")
    prompt_lines.append(
        "- **ZERO RIFERIMENTI META A LEZIONI, CAPITOLI O NOTEBOOK NEL TESTO O NEI TITOLI:**\n"
        "  L'indice del libro e il diario delle lezioni servono esclusivamente dietro le quinte per la completezza del corso.\n"
        "  È TASSATIVAMENTE VIETATO scrivere diciture come `(Lezioni 1–28 | Indice Libro [Alg] Capp. 1, 2)`, `(Dal Diario delle Lezioni)`, `(Cap. 3 del Libro)` o codici come `(SMIA: Analisi 1)` nei titoli, tabelle o corpo del testo.\n"
        "  I titoli e il testo devono essere puramente accademici e disciplinari, come in un vero trattato universitario.\n"
        "- **WIKILINK PURI SENZA APICI NÉ BACKTICK:**\n"
        "  Tutti i collegamenti ipertestuali (nel testo, negli elenchi puntati e dentro le tabelle) devono essere scritti SEMPRE in formato puro Obsidian: `[[Nome Nota]]` o `[[Nome Nota#Paragrafo|Alias]]`.\n"
        "  È SEVERAMENTE VIETATO racchiuderli tra apici singoli `'[[...]]'`, doppi \"[[...]]\" o dentro backtick `` `[[...]]` ``.\n"
        "- **ZERO EMOJI NELLE NOTE E NEI MOC (PURGA TOTALE):**\n"
        "  Divieto assoluto di usare emoji Unicode all'interno dei testi generati (note e MOC).\n"
        "  I titoli delle sezioni, le tabelle e i callout devono essere privi di qualsiasi emoji.\n"
        "  I titoli delle fasi di dimostrazione devono essere: `**1. Strategia della Dimostrazione:**` (non `**1. 🎯 ...**`), `**2. Passaggi Logico-Deduttivi:**` (non `**2. 🪜 ...**`), `**3. Conclusione e Q.E.D.:**` (non `**3. 🏁 ...**`).\n"
        "  Il callout della palestra d'esame deve essere: `> [!abstract]- Palestra d'Esame Interattiva: Flashcard e Quiz` (senza emoji).\n"
        "- **DELIMITAZIONE FORMULE LATEX NELLE NOTE NORMALI:**\n"
        "  Nella prosa Markdown delle Note Normali, ogni espressione matematica LaTeX deve essere racchiusa nei delimitatori appropriati: $...$ inline e $$...$$ per formule isolate. Non lasciare comandi come \\forall, \\exists, \\frac, \\mathbb, \\lim, \\sum o \\in fuori dalla modalità matematica. Controlla anche callout e contenuti di studio.\n"
        "- **DIVIETO DI `\\vline` IN LATEX:**\n"
        "  Obsidian MathJax non supporta `\\vline` e genera errore di parsing rosso. È tassativamente vietato usare `\\vline`.\n"
        "  Per linee verticali in formule matematiche, matrici o insiemi usa sempre `\\vert`, `|` o `\\mid` (es. `\\{x \\in A \\mid P(x)\\}`)."
    )

    prompt_lines.append("### 5. Scrittura della Nota, Criterio di Confine Concettuale e Palestra d'Esame")
    prompt_lines.append(f"- **Scrivi il file completo della nota** direttamente in: `{vault_root / target_rel}` (relativo al vault: `{target_rel}`).")
    prompt_lines.append("- Non troncare mai il testo, non usare mai `# TODO` o `...`.")
    prompt_lines.append("- **Criterio di Confine Concettuale (Regola Fondamentale):** Spiega totalmente l'argomento senza limiti di parole (né minimo né massimo). Non inserire teoremi derivati con nome proprio, concetti con definizione autonoma o procedure operative nella stessa nota: per essi inserisci solo un breve ponte logico e il [[wikilink]], elencandoli nella sottosezione finale `### Teoremi e Concetti Derivati (Note Separate)`. Nel frontmatter YAML usa rigorosamente un solo `Type:` in formato lista (`Type:\\n  - Concetto`).")
    prompt_lines.append("")
    prompt_lines.append("#### Palestra d'Esame Interattiva (Legge 8 della Costituzione — OBBLIGATORIA A FONDO NOTA):")
    prompt_lines.append("In fondo alla nota, prima dei tag finali o dopo la sezione collegamenti, inserisci **obbligatoriamente** il callout interattivo chiuso di default:")
    prompt_lines.append("```markdown")
    prompt_lines.append("> [!abstract]- Palestra d'Esame Interattiva: Flashcard e Quiz (Clicca per aprire)")
    prompt_lines.append("> ```dataviewjs")
    prompt_lines.append('> const panelPath = ".antigravity/scripts/study_panel.js";')
    prompt_lines.append('> if (await app.vault.adapter.exists(panelPath)) {')
    prompt_lines.append('>     const code = await app.vault.adapter.read(panelPath);')
    prompt_lines.append('>     new Function("dv", code)(dv);')
    prompt_lines.append('> } else {')
    prompt_lines.append('>     await dv.view("Scripts/study_panel");')
    prompt_lines.append('> }')
    prompt_lines.append("> ```")
    prompt_lines.append("> ")
    prompt_lines.append("> %%STUDY_DATA")
    prompt_lines.append("> ### FLASHCARD 1: [Titolo Concetto]")
    prompt_lines.append("> **Q:** [Domanda di verifica attiva / Retrieval Practice]")
    prompt_lines.append("> **A:** [Risposta rigorosa, completa e motivata a sforzo zero]")
    prompt_lines.append("> ")
    prompt_lines.append("> ... (minimo 6–10 Flashcard)")
    prompt_lines.append("> ")
    prompt_lines.append("> ### QUIZ 1: [Titolo Argomento]")
    prompt_lines.append("> **Q:** [Domanda a scelta multipla con scenario applicativo o formula]")
    prompt_lines.append("> - [ ] A) [Opzione A]")
    prompt_lines.append("> - [ ] B) [Opzione B]")
    prompt_lines.append("> - [ ] C) [Opzione C]")
    prompt_lines.append("> - [ ] D) [Opzione D]")
    prompt_lines.append("> **CORRECT:** B")
    prompt_lines.append("> **EXPLANATION:** [Spiegazione rigorosa: perché B è vera e perché i distrattori A, C, D sono falsi / analisi delle trappole d'esame]")
    prompt_lines.append("> ")
    prompt_lines.append("> ... (minimo 4–6 Quiz)")
    prompt_lines.append("> %%")
    prompt_lines.append("```")
    prompt_lines.append("- **Criteri Scientifici Obbligatori (Legge 8):**")
    prompt_lines.append("  * **Volumi:** Almeno **6–10 Flashcard** e **4–6 Quiz a Scelta Multipla**.")
    prompt_lines.append("  * **Retrieval Practice & Desirable Difficulties:** Bandite le domande meramente mnemoniche o definitorie. Testa sempre il *Perché* dei vincoli (cosa crolla se cade un'ipotesi), la decodifica dei simboli nelle formule e la scelta del metodo di calcolo ottimale.")
    prompt_lines.append("  * **Analisi Trappole nei Quiz:** I distrattori devono incarnare gli errori concettuali e di calcolo più frequenti negli esami universitari. Nel campo `**EXPLANATION:**` smonta ciascun distrattore punto per punto.")
    prompt_lines.append("")
    prompt_lines.append("#### Schemi Visivi Strutturali con Mermaid.js (Legge 10 Anti-Crash Obbligatoria):")
    prompt_lines.append(
        "- Se la fonte NON fornisce già un'immagine esplicativa per un processo, catena causale, protocollo o architettura, genera direttamente nella nota uno schema ` ```mermaid ` (`flowchart TD/LR` per flussi sequenziali/biochimici/storici, `sequenceDiagram` per protocolli o contratti, `stateDiagram-v2` per transizioni di stato).\n"
        "- **REGOLA SINTATTICA FERREA ANTI-CRASH:** Racchiudi **SEMPRE** il testo di ogni nodo e di ogni freccia tra **doppi apici (`\"...\"`)**, ad esempio:\n"
        "  ```mermaid\n"
        "  flowchart LR\n"
        "    A[\"Stimolo Meccanico (Tensione)\"] -->|\"Attiva sensori\"| B[\"Complesso mTORC1\"]\n"
        "    B --> C[\"Sintesi Proteica (MPS)\"]\n"
        "  ```\n"
        "- Non usare MAI formule LaTeX $...$ nei nodi Mermaid: usa esclusivamente caratteri Unicode puliti tra virgolette (es. `\"∀\"`, `\"∃\"`, `\"→\"`, `\"↑\"`, `\"↓\"`, `\"Δ\"`, `\"α\"`, `\"β\"`)."
    )
    prompt_lines.append("")
    if job_data.get("layout_moc"):
        # Nota già collegata nel suo MOC (batch): il MOC non va toccato, anche perché più note
        # del batch possono essere scritte in contemporanea
        prompt_lines.append(
            f"- **MOC:** la nota è già collegata in `{job_data['layout_moc']}`. NON modificare il MOC né altre note: "
            "scrivi esclusivamente il file target."
        )
    else:
        prompt_lines.append(
            "- **AGGIORNAMENTO BIDIREZIONALE:** Individua il MOC o Sub-MOC di riferimento nel vault per questa disciplina, "
            "aprilo e inserisci il collegamento `[[{topic}]]` nella sezione logica pertinente con una frase di raccordo discorsiva."
        )
    prompt_lines.append("")

    prompt_lines.append("---")
    prompt_lines.append("## CONTENUTO ESTRATTO DELLA FONTE")
    prompt_lines.append("")
    prompt_lines.append(source_results.get("content_markdown", "*(Nessun contenuto sorgente estratto)*"))

    return "\n".join(prompt_lines)


# ==============================================================================
# 5. MAIN ENTRYPOINT
# ==============================================================================

# ==============================================================================
# POST-PROCESSING: VERIFICA DI ESCLUSIVITÀ NOTEBOOKLM E METADATI MOC
# ==============================================================================

GROUNDING_AUDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "unsupported": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "quote": {"type": "string"},
                    "claim": {"type": "string"},
                    "kind": {"type": "string"},
                    "replacement": {"type": "string"},
                },
                "required": ["quote", "claim", "kind", "replacement"],
            },
        }
    },
    "required": ["unsupported"],
}


def resolve_agy_bin() -> Optional[str]:
    """Individua il binario della CLI agy (stesso ordine di run_job.sh)."""
    candidate = Path.home() / ".local" / "bin" / "agy"
    if candidate.exists() and os.access(candidate, os.X_OK):
        return str(candidate)
    for d in os.environ.get("PATH", "").split(os.pathsep):
        p = Path(d) / "agy"
        if p.exists() and os.access(p, os.X_OK):
            return str(p)
    return None


def run_agy_structured(prompt: str, schema: Dict[str, Any], timeout_sec: int = 900,
                       effort: str = "") -> Optional[Dict[str, Any]]:
    """Esegue agy in print mode con output JSON vincolato a uno schema e restituisce structured_output.
    `effort` (low|medium|high) abbassa il ragionamento per i giudizi rapidi."""
    agy_bin = resolve_agy_bin()
    if not agy_bin:
        sys.stderr.write("[Grounding] Binario agy non trovato.\n")
        return None
    cmd = [
        agy_bin, "-p", prompt,
        "--output-format", "json",
        "--json-schema", json.dumps(schema),
        "--print-timeout", f"{timeout_sec}s",
    ] + (["--effort", effort] if effort else [])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec + 60, check=False)
    except subprocess.TimeoutExpired:
        sys.stderr.write(f"[Grounding] Timeout agy ({timeout_sec}s).\n")
        return None
    out = (proc.stdout or "").strip()
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
    sys.stderr.write(f"[Grounding] Output agy non interpretabile: {out[:300]} {proc.stderr[:300]}\n")
    return None


def split_note_for_audit(text: str, max_parts: int = 4, min_chars: int = 6000) -> List[str]:
    """Divide la nota in parti consecutive (ai confini delle sezioni H2) di lunghezza simile,
    così l'audit di esclusività può girare in parallelo su più revisori."""
    _, body_start = parse_simple_frontmatter(text)
    body = text[body_start:]
    sections = re.split(r"(?m)^(?=## )", body)
    sections = [sec for sec in sections if sec.strip()]
    parts = max(1, min(max_parts, len(body) // min_chars, len(sections)))
    if parts == 1:
        return [body]
    target = len(body) / parts
    chunks: List[str] = []
    current = ""
    for sec in sections:
        if current and len(current) + len(sec) / 2 > target and len(chunks) < parts - 1:
            chunks.append(current)
            current = ""
        current += sec
    chunks.append(current)
    return chunks


def build_grounding_audit_prompt(note_text: str, source_text: str, pubmed_text: str, vault_claims_text: str,
                                 part_label: str = "") -> str:
    sections = [
        "Sei un revisore accademico indipendente. Il tuo unico compito è confrontare una NOTA con la sua FONTE "
        "(estratto di NotebookLM) e individuare i contenuti della nota che NON sono supportati dalla fonte.",
        "Non modificare alcun file e non usare strumenti: lavora solo sul testo qui sotto.",
        "",
        "## Cosa devi segnalare (contenuto sostanziale assente dalla FONTE)",
        "- definizioni, enunciati di teoremi/proposizioni/lemmi/corollari, ipotesi o conclusioni non presenti nella fonte;",
        "- dimostrazioni o metodi dimostrativi diversi o aggiuntivi rispetto alla fonte;",
        "- esempi, controesempi, esercizi o applicazioni non presenti nella fonte;",
        "- nomi propri, attribuzioni storiche, date, dati numerici, terminologia specifica (es. 'di Dedekind') assenti dalla fonte;",
        "- proprietà, risultati o casi particolari aggiunti che la fonte non menziona.",
        "",
        "## Cosa NON devi segnalare",
        "- passaggi algebrici o logici intermedi che esplicitano un ragionamento già presente nella fonte;",
        "- riformulazioni didattiche, decodifiche, intuizioni o analogie che non introducono fatti nuovi;",
        "- diagrammi, tabelle riassuntive, flashcard e quiz che si limitano a riprendere contenuti già nella fonte;",
        "- wikilink, sezioni di collegamento, riferimenti a MOC, frontmatter, codice DataviewJS;",
        "- contenuti tratti dalle EVIDENZE PUBMED fornite sotto (sono una fonte ammessa);",
        "- callout di 'Conflitto Epistemico' che riportano il contenuto delle NOTE DEL VAULT fornite sotto.",
        "",
        "## Formato della risposta",
        "Per ogni contenuto non supportato restituisci: `quote` (frase o formula ESATTA copiata dalla nota, max 300 caratteri, "
        "sufficiente a localizzarla), `claim` (l'affermazione in forma autonoma e verificabile, in italiano), "
        "`kind` (definizione | teorema | dimostrazione | esempio | dato | nome | altro), "
        "`replacement` (il testo con cui sostituire ESATTAMENTE `quote` se l'affermazione va eliminata: la stessa frase "
        "senza la parte non supportata, oppure stringa vuota se va eliminata per intero, oppure "
        "`*(Non presente nelle fonti del corso)*` se l'eliminazione spezzerebbe il discorso; mantieni LaTeX e formattazione).",
        "Massimo 40 voci, dalle più rilevanti. Se tutto è supportato restituisci una lista vuota.",
        "",
        "=== FONTE (estratto NotebookLM) ===",
        source_text,
        "=== FINE FONTE ===",
    ]
    if pubmed_text.strip():
        sections += ["", "=== EVIDENZE PUBMED (fonte ammessa) ===", pubmed_text[:30000], "=== FINE EVIDENZE PUBMED ==="]
    if vault_claims_text.strip():
        sections += ["", "=== NOTE DEL VAULT (solo per i callout di Conflitto Epistemico) ===", vault_claims_text[:20000], "=== FINE NOTE DEL VAULT ==="]
    if part_label:
        sections += ["", f"Ricevi solo {part_label} della nota: revisiona esclusivamente questa parte."]
    sections += ["", "=== NOTA DA REVISIONARE ===", note_text, "=== FINE NOTA ==="]
    return "\n".join(sections)


def arbitrate_claims_with_notebooklm(claims: List[Dict[str, Any]], notebooks: List[Dict[str, str]],
                                     on_progress=None) -> Dict[str, Optional[bool]]:
    """
    Sottopone le affermazioni sospette direttamente a NotebookLM (sull'intero notebook, non solo
    sull'estratto). Restituisce {id: True se almeno un notebook la conferma, False se tutti i notebook
    interrogati la negano esplicitamente, None se nessuna risposta è arrivata (non verificabile)}.
    I gruppi senza risposta vengono ritentati una volta, divisi a metà.
    """
    verdicts: Dict[str, Optional[bool]] = {c["id"]: None for c in claims}
    pattern = re.compile(r"\b(C\d+)\b[\s*`]*[|:\-–]\s*[*`]*\s*(S[IÌÍ]|NO)\b", re.IGNORECASE)

    def ask(chunks: List[List[Dict[str, Any]]]) -> None:
        tasks = []
        for ch_idx, chunk in enumerate(chunks):
            listing = "\n".join(f"{c['id']}: {c['claim']}" for c in chunk)
            prompt = (
                "Verifica le seguenti affermazioni basandoti ESCLUSIVAMENTE sulle fonti di questo notebook.\n"
                "Per ciascuna rispondi su una riga nel formato esatto `ID | SI` se le fonti la contengono o la "
                "supportano esplicitamente, oppure `ID | NO` se le fonti non la contengono. Non aggiungere altro.\n\n"
                + listing
            )
            for nb_idx, nb in enumerate(notebooks):
                tasks.append(((ch_idx, nb_idx), nb["id"], prompt))
        for text in query_nlm_parallel(tasks, timeout_sec=300, on_progress=on_progress).values():
            for cid, verdict in pattern.findall(text or ""):
                cid = cid.upper()
                if cid not in verdicts:
                    continue
                if verdict.upper().startswith("S"):
                    verdicts[cid] = True
                elif verdicts[cid] is None:
                    verdicts[cid] = False

    ask([claims[i:i + 12] for i in range(0, len(claims), 12)])
    pending = [c for c in claims if verdicts[c["id"]] is None]
    if pending:
        sys.stderr.write(f"[Grounding] Nuovo tentativo NotebookLM su {len(pending)} affermazioni senza verdetto...\n")
        ask([pending[i:i + 6] for i in range(0, len(pending), 6)])
    pending = [c for c in claims if verdicts[c["id"]] is None]
    if pending and NLM_RATE_LIMITED:
        verdicts.update(arbitrate_claims_locally(pending, notebooks))
    return verdicts


def arbitrate_claims_locally(claims: List[Dict[str, Any]], notebooks: List[Dict[str, str]]) -> Dict[str, Optional[bool]]:
    """Ripiego quando la chat NotebookLM è al limite: per ogni affermazione si cercano i passaggi nel
    testo originale delle fonti (nlm_local) e agy giudica solo su quei passaggi. Nel dubbio None."""
    try:
        import nlm_local
    except Exception:
        return {}
    nb_ids = [nb["id"] for nb in notebooks if nb.get("id")]
    seen, blocks = set(), []
    for c in claims:
        for title, text in nlm_local.search(nb_ids, c["claim"], [c.get("quote", "")], max_chars=6000):
            if text not in seen:
                seen.add(text)
                blocks.append((title, text))
    passages = nlm_local.format_passages(blocks)[:90000]
    if not passages:
        return {}
    sys.stderr.write(f"[Grounding] Chat NotebookLM al limite: verifico {len(claims)} affermazioni sul testo originale delle fonti.\n")
    listing = "\n".join(f"{c['id']}: {c['claim']}" for c in claims)
    prompt = (
        "Sei un verificatore. Per ciascuna affermazione decidi se i PASSAGGI DELLE FONTI qui sotto la contengono "
        "o la supportano esplicitamente (anche con parole diverse o notazione diversa). Non usare conoscenze tue: "
        "conta solo il testo dei passaggi. verdict = \"SI\" se supportata, \"NO\" se i passaggi trattano "
        "l'argomento ma non la contengono, \"INCERTO\" se i passaggi non bastano per decidere.\n\n"
        f"=== AFFERMAZIONI ===\n{listing}\n\n=== PASSAGGI DELLE FONTI ===\n{passages}\n=== FINE PASSAGGI ==="
    )
    schema = {
        "type": "object",
        "properties": {"verdicts": {"type": "array", "items": {
            "type": "object",
            "properties": {"id": {"type": "string"}, "verdict": {"type": "string", "enum": ["SI", "NO", "INCERTO"]}},
            "required": ["id", "verdict"]}}},
        "required": ["verdicts"],
    }
    try:
        result = run_agy_structured(prompt, schema, timeout_sec=600, effort="low") or {}
    except Exception as e:
        sys.stderr.write(f"[Grounding] Verifica locale non riuscita: {e}\n")
        return {}
    out: Dict[str, Optional[bool]] = {}
    valid = {c["id"] for c in claims}
    for v in result.get("verdicts") or []:
        cid = str(v.get("id", "")).strip().upper()
        if cid in valid:
            out[cid] = {"SI": True, "NO": False}.get(str(v.get("verdict", "")).upper())
    return out


def apply_claim_replacements(text: str, claims: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """Applica le sostituzioni proposte dal revisore. Restituisce (testo, affermazioni non localizzate)."""
    not_found = []
    for c in claims:
        quote = c.get("quote", "").strip()
        replacement = c.get("replacement", "")
        tokens = [t for t in re.split(r"[\s>]+", quote) if t]
        if not tokens:
            not_found.append(c)
            continue
        # Tollerante a spaziatura e ai prefissi '>' di callout/blockquote tra una riga e l'altra
        m = re.search(r"(?:[\s>]+)".join(re.escape(t) for t in tokens), text)
        if not m:
            not_found.append(c)
            continue
        start, end = m.start(), m.end()
        line_start = text.rfind("\n", 0, start) + 1
        prefix = re.match(r"[>\s]*", text[line_start:]).group(0)
        line_end = text.find("\n", end)
        line_end = len(text) if line_end < 0 else line_end
        # Se la citazione è l'intestazione di un callout, si elimina l'intero callout
        if re.match(r"\s*>\s*\[!", text[line_start:start + 4]) and "\n" not in text[start:end]:
            block_end = line_end
            while block_end < len(text):
                nxt = text.find("\n", block_end + 1)
                nxt = len(text) if nxt < 0 else nxt
                if not text[block_end + 1:nxt].lstrip().startswith(">"):
                    break
                block_end = nxt
            start, end = line_start, block_end
            prefix = ""
        rep_lines = replacement.split("\n")
        if prefix.strip():
            rep_lines = [rep_lines[0]] + [(prefix + l if l.strip() else prefix.rstrip()) for l in rep_lines[1:]]
        text = text[:start] + "\n".join(rep_lines) + text[end:]
    return text, not_found


def verify_note_grounding(vault_root: Path, job_data: Dict[str, Any], target_rel: str) -> Dict[str, Any]:
    """
    Verifica di esclusività NotebookLM imposta dal codice (non solo dal prompt), in 3 fasi:
    1. Audit: un'istanza agy separata confronta la nota con extracted_source.md ed elenca i contenuti non supportati.
    2. Arbitrato: le affermazioni sospette vengono sottoposte a NotebookLM sull'intero notebook.
    3. Correzione: le affermazioni non confermate vengono rimosse dalla nota (backup preventivo).
    """
    report: Dict[str, Any] = {
        "target": target_rel,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "skipped",
        "flagged": 0,
        "confirmed": [],
        "removed": [],
    }
    target_path = vault_root / target_rel
    ctx_dir = RUNTIME_DIR / "job-context"
    source_path = ctx_dir / "extracted_source.md"
    if not target_path.exists() or not source_path.exists():
        report["status"] = "error"
        report["error"] = "Nota o extracted_source.md mancanti"
        return report

    def read_ctx(name: str) -> str:
        p = ctx_dir / name
        return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""

    update_status(
        vault_root=vault_root, percent=96, step_number=6, total_steps=6,
        message="🛡️ Verifica esclusività NotebookLM: audit dei contenuti della nota...",
        detail="Un revisore separato confronta la nota con l'estratto di NotebookLM",
        status="running", target_file=target_rel, phase="verify",
    )
    # Audit in parallelo: ogni revisore riceve una parte della nota e l'intera fonte
    chunks = split_note_for_audit(target_path.read_text(encoding="utf-8", errors="replace"))
    source_text = source_path.read_text(encoding="utf-8", errors="replace")
    pubmed_text = read_ctx("pubmed_evidence.json")
    vault_claims_text = read_ctx("existing-vault-claims.md")
    report["audit_parts"] = len(chunks)

    def audit_part(idx_chunk: Tuple[int, str]) -> Optional[Dict[str, Any]]:
        idx, chunk = idx_chunk
        label = f"la parte {idx + 1} di {len(chunks)}" if len(chunks) > 1 else ""
        prompt = build_grounding_audit_prompt(chunk, source_text, pubmed_text, vault_claims_text, part_label=label)
        return run_agy_structured(prompt, GROUNDING_AUDIT_SCHEMA, timeout_sec=600)

    def report_audit(done: int) -> None:
        update_status(
            vault_root=vault_root, percent=96, step_number=6, total_steps=6,
            message="🛡️ Verifica esclusività NotebookLM: audit dei contenuti della nota",
            detail=f"{done} di {len(chunks)} parti della nota revisionate", status="running",
            target_file=target_rel, phase="verify",
            progress={"done": done, "total": len(chunks), "unit": "parti"},
        )

    t0 = time.time()
    report_audit(0)
    results: List[Optional[Dict[str, Any]]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(chunks)) as pool:
        futures = [pool.submit(audit_part, item) for item in enumerate(chunks)]
        for fut in concurrent.futures.as_completed(futures):
            try:
                results.append(fut.result())
            except Exception:
                results.append(None)
            report_audit(len(results))
    report["seconds_audit"] = int(time.time() - t0)
    if all(r is None for r in results):
        report["status"] = "error"
        report["error"] = "Audit agy non riuscito"
        return report
    report["audit_parts_failed"] = sum(1 for r in results if r is None)
    audit = {"unsupported": [item for r in results if r for item in (r.get("unsupported") or [])]}

    claims = []
    for i, item in enumerate((audit.get("unsupported") or [])[:60], 1):
        if isinstance(item, dict) and str(item.get("claim", "")).strip():
            claims.append({
                "id": f"C{i}",
                "quote": str(item.get("quote", "")).strip(),
                "claim": str(item.get("claim", "")).strip(),
                "kind": str(item.get("kind", "altro")).strip(),
                "replacement": str(item.get("replacement", "")),
            })
    report["flagged"] = len(claims)
    report["unverified"] = []
    if not claims:
        report["status"] = "clean"
        return report

    notebooks = extract_notebooks_list(job_data.get("source", {}), job_data)
    update_status(
        vault_root=vault_root, percent=97, step_number=6, total_steps=6,
        message=f"🛡️ Verifica esclusività: {len(claims)} affermazioni sospette sottoposte a NotebookLM...",
        detail="NotebookLM verifica ogni affermazione sull'intero notebook",
        status="running", target_file=target_rel, phase="verify",
    )
    t0 = time.time()
    verdicts = arbitrate_claims_with_notebooklm(claims, notebooks, on_progress=progress_reporter(
        vault_root, 97, 6, f"🛡️ Verifica esclusività: NotebookLM controlla {len(claims)} affermazioni sospette",
        "verify", target_rel, unit="verifiche",
    ))
    report["seconds_arbitration"] = int(time.time() - t0)
    # Si rimuove solo ciò che NotebookLM nega esplicitamente; il non verificabile resta e viene segnalato
    report["confirmed"] = [c for c in claims if verdicts.get(c["id"]) is True]
    report["unverified"] = [c for c in claims if verdicts.get(c["id"]) is None]
    unsupported = [c for c in claims if verdicts.get(c["id"]) is False]
    if not unsupported:
        report["status"] = "clean"
        return report

    update_status(
        vault_root=vault_root, percent=98, step_number=6, total_steps=6,
        message=f"🛡️ Verifica esclusività: rimozione di {len(unsupported)} contenuti non presenti nelle fonti...",
        detail=f"{len(report['confirmed'])} affermazioni confermate da NotebookLM",
        status="running", target_file=target_rel, phase="verify",
    )
    backup = create_target_note_backup(vault_root, target_rel)
    report["backup"] = str(backup) if backup else None

    # Correzione deterministica con le sostituzioni del revisore; agy solo per i passaggi non localizzati
    new_text, not_found = apply_claim_replacements(target_path.read_text(encoding="utf-8", errors="replace"), unsupported)
    target_path.write_text(new_text, encoding="utf-8")
    report["removed"] = unsupported
    if not not_found:
        try:
            sanitize_markdown_file(target_path)
        except Exception as e_san:
            sys.stderr.write(f"[Grounding] Errore sanificazione: {e_san}\n")
        report["status"] = "fixed"
        return report

    listing = "\n".join(
        f"{c['id']} [{c['kind']}]\n   Testo nella nota: «{c['quote']}»\n   Affermazione: {c['claim']}"
        for c in not_found
    )
    fix_prompt_path = RUNTIME_DIR / "grounding-fix-prompt.md"
    fix_prompt_path.write_text(
        "# CORREZIONE DI ESCLUSIVITÀ NOTEBOOKLM\n\n"
        f"File da modificare: `{target_path}`\n\n"
        "Le seguenti affermazioni della nota NON sono presenti nelle fonti NotebookLM del corso "
        "(verificato sia sull'estratto sia interrogando direttamente NotebookLM). La nota è in modalità "
        "'Solo NotebookLM', quindi vanno eliminate.\n\n"
        f"{listing}\n\n"
        "## Regole\n"
        "1. Per ciascuna voce elimina il contenuto non supportato. Se l'eliminazione spezza il discorso, sostituiscilo con "
        "`*(Non presente nelle fonti del corso)*`. Se riguarda solo un nome o un'attribuzione (es. 'di Dedekind'), "
        "elimina solo quel nome e mantieni il resto della frase.\n"
        "2. Elimina anche flashcard, quiz, righe di tabelle o nodi di diagrammi basati esclusivamente su contenuti eliminati.\n"
        "3. Non toccare NIENT'ALTRO: struttura, titoli, formattazione, LaTeX, wikilink, ID di blocco, frontmatter, DataviewJS restano identici.\n"
        "4. Non aggiungere contenuti nuovi e non consultare altre fonti.\n"
        "5. Salva il file modificato nello stesso percorso.\n",
        encoding="utf-8",
    )
    agy_bin = resolve_agy_bin()
    if not agy_bin:
        report["status"] = "error"
        report["error"] = "Binario agy non trovato per la correzione"
        return report
    try:
        subprocess.run(
            [agy_bin, "-p", f"Leggi ed esegui esattamente il compito descritto nel file {fix_prompt_path}.",
             "--dangerously-skip-permissions", "--print-timeout", "900s"],
            capture_output=True, text=True, timeout=960, check=False,
        )
    except subprocess.TimeoutExpired:
        report["status"] = "error"
        report["error"] = "Timeout della correzione agy"
        return report
    try:
        sanitize_markdown_file(target_path)
    except Exception as e_san:
        sys.stderr.write(f"[Grounding] Errore sanificazione: {e_san}\n")
    report["removed"] = unsupported
    report["status"] = "fixed"
    return report


def parse_simple_frontmatter(text: str) -> Tuple[Dict[str, Any], int]:
    """Parser YAML minimale (scalari e liste '- x') per il frontmatter. Restituisce (dati, offset fine frontmatter)."""
    if not text.startswith("---"):
        return {}, 0
    end = text.find("\n---", 3)
    if end < 0:
        return {}, 0
    data: Dict[str, Any] = {}
    current_key = None
    for line in text[3:end].splitlines():
        if not line.strip():
            continue
        m_item = re.match(r"^\s+-\s*(.*)$", line)
        if m_item and current_key:
            if not isinstance(data.get(current_key), list):
                data[current_key] = []
            data[current_key].append(m_item.group(1).strip().strip('"\''))
            continue
        m_kv = re.match(r"^([^:\s][^:]*):\s*(.*)$", line)
        if m_kv:
            current_key = m_kv.group(1).strip()
            val = m_kv.group(2).strip()
            if val.startswith("[") and val.endswith("]"):
                data[current_key] = [v.strip().strip('"\'') for v in val[1:-1].split(",") if v.strip()]
            else:
                data[current_key] = val.strip('"\'') if val else []
    close = text.find("\n", end + 4)
    return data, (close + 1 if close >= 0 else len(text))


def write_moc_notebooks_frontmatter(moc_path: Path, notebooks: List[Dict[str, str]]) -> bool:
    """Registra nel frontmatter del MOC i NotebookLM da cui è stato generato (notebooklm_ids + NotebookLM)."""
    if not moc_path.exists() or not notebooks:
        return False
    text = moc_path.read_text(encoding="utf-8", errors="replace")
    ids_block = "notebooklm_ids:\n" + "".join(f"  - {nb['id']}\n" for nb in notebooks)
    titles_block = "NotebookLM:\n" + "".join(f"  - \"{nb['title'].replace(chr(34), '')}\"\n" for nb in notebooks)
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end < 0:
            return False
        fm_body = text[4:end + 1]
        # Rimuove eventuali chiavi precedenti con le relative liste
        fm_body = re.sub(r"(?m)^(notebooklm_ids|NotebookLM):.*\n(?:\s+-.*\n)*", "", fm_body)
        new_text = "---\n" + fm_body + ids_block + titles_block + text[end + 1:]
    else:
        new_text = "---\n" + ids_block + titles_block + "---\n" + text
    moc_path.write_text(new_text, encoding="utf-8")
    return True


def post_process_job(vault_root: Path, job_file: Path) -> int:
    """Eseguito da run_job.sh dopo che l'agente ha finito di scrivere: metadati MOC + verifica di esclusività."""
    try:
        job_data = json.loads(job_file.read_text(encoding="utf-8"))
    except Exception as e:
        sys.stderr.write(f"[PostProcess] Job non leggibile: {e}\n")
        return 1
    op_type = job_data.get("operation_type") or job_data.get("operation", "")
    target_rel = job_data.get("target_file_rel") or job_data.get("target_file_path", "")

    if op_type == "moc" and job_data.get("moc_mode") == "start_notebooklm":
        notebooks = extract_notebooks_list(job_data.get("source", {}), job_data)
        if write_moc_notebooks_frontmatter(vault_root / target_rel, notebooks):
            sys.stdout.write(f"[PostProcess] NotebookLM registrati nel frontmatter di {target_rel}\n")

    if op_type == "moc" and job_data.get("moc_check_required"):
        try:
            import moc_postprocess
            moc_report = moc_postprocess.postprocess_moc(vault_root, job_data, target_rel)
            job_data["grounding_summary"] = moc_report.get("summary", "")
            sanitize_markdown_file(vault_root / target_rel, is_moc=True)
        except Exception as e:
            sys.stderr.write(f"[PostProcess] Verifica del MOC non riuscita: {e}\n")
            traceback.print_exc(file=sys.stderr)
            job_data["grounding_summary"] = f"⚠️ Verifica del MOC non completata: {e}"
        job_file.write_text(json.dumps(job_data, indent=2, ensure_ascii=False), encoding="utf-8")
        sys.stdout.write(f"[PostProcess] {job_data['grounding_summary']}\n")

    if job_data.get("grounding_verification_required"):
        report = verify_note_grounding(vault_root, job_data, target_rel)
        (RUNTIME_DIR / "grounding-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            with open(vault_root / ".antigravity" / "grounding-log.jsonl", "a", encoding="utf-8") as fh:
                fh.write(json.dumps(report, ensure_ascii=False) + "\n")
        except Exception:
            pass
        summary = {
            "clean": f"🛡️ Esclusività verificata: nessun contenuto esterno ({len(report['confirmed'])} confermati da NotebookLM)",
            "fixed": f"🛡️ Esclusività applicata: {len(report['removed'])} contenuti esterni rimossi, {len(report['confirmed'])} confermati"
                     + (f", {len(report.get('unverified', []))} non verificabili (lasciati, vedi grounding-log)" if report.get("unverified") else ""),
            "error": f"⚠️ Verifica di esclusività non completata: {report.get('error', '')}",
        }.get(report["status"], "")
        try:
            local_used = "Testo originale delle fonti" in (RUNTIME_DIR / "job-context" / "extracted_source.md").read_text(encoding="utf-8")
        except Exception:
            local_used = False
        if local_used:
            summary = (summary + " · 📄 chat NotebookLM al limite: scritta dal testo originale delle fonti").strip(" ·")
        job_data["grounding_summary"] = summary
        job_file.write_text(json.dumps(job_data, indent=2, ensure_ascii=False), encoding="utf-8")
        sys.stdout.write(f"[PostProcess] {summary}\n")

    # Sezioni richieste dai MOC con [[Nota#Sezione]]: se mancano, il link del MOC non porta da nessuna parte
    if op_type in ("normal", "edit"):
        try:
            import unicodedata
            import vault_layout
            wanted = vault_layout.requested_sections(vault_root, Path(target_rel).stem)
            if wanted and (vault_root / target_rel).exists():
                fold = lambda x: "".join(c for c in unicodedata.normalize("NFD", x.lower()) if unicodedata.category(c) != "Mn").strip()
                heads = {fold(h) for h in re.findall(r"(?m)^#{1,6}\s+(.+?)\s*$", (vault_root / target_rel).read_text(encoding="utf-8", errors="replace"))}
                missing = [w for w in wanted if fold(w) not in heads]
                job_data["missing_sections"] = missing
                if missing:
                    note = f"⚠️ Sezioni richieste dal MOC mancanti: {', '.join(missing)}"
                    job_data["grounding_summary"] = (job_data.get("grounding_summary", "") + " · " + note).strip(" ·")
                job_file.write_text(json.dumps(job_data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            sys.stderr.write(f"[PostProcess] Controllo sezioni non riuscito: {e}\n")

    # Collocazione nel file explorer: cartella del corso/modulo e ordine di Manual Sorting
    update_status(
        vault_root=vault_root, percent=99, step_number=6, total_steps=6,
        message="🗂️ Sistemazione nel file explorer", detail="Cartella del corso e ordine del MOC",
        status="running", target_file=target_rel, phase="final",
    )
    try:
        import vault_layout
        if op_type == "moc":
            result = vault_layout.sync_course(vault_root, target_rel)
        else:
            result = vault_layout.sync_for_note(
                vault_root, Path(target_rel).stem, job_data.get("discipline", ""), job_data.get("layout_moc", "")
            )
        if result:
            sys.stdout.write(f"[PostProcess] Layout: {json.dumps(result, ensure_ascii=False)}\n")
        moved_to = vault_layout.find_existing_note(vault_root, Path(target_rel).stem)
        if moved_to and moved_to != target_rel:
            job_data["target_file_rel"] = moved_to
            job_file.write_text(json.dumps(job_data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        sys.stderr.write(f"[PostProcess] Layout non aggiornato: {e}\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Orchestratore principale Antigravity per Obsidian Vault.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--job-file",
        "-j",
        type=str,
        default=None,
        help="Percorso del file current-job.json (default: <vault>/.antigravity/current-job.json).",
    )
    parser.add_argument(
        "--no-launch",
        action="store_true",
        help="Esegue solo il pre-processing e genera current-prompt.md.",
    )
    parser.add_argument(
        "--set-status",
        action="store_true",
        help="Aggiorna direttamente job-status.json ed esce (integrazione CLI/Bash/HUD).",
    )
    parser.add_argument("--percent", type=int, default=0, help="Percentuale di avanzamento (0-100).")
    parser.add_argument("--step", type=int, default=1, help="Numero dello step corrente (1-6).")
    parser.add_argument("--total-steps", type=int, default=6, help="Numero totale degli step della pipeline.")
    parser.add_argument("--message", type=str, default="", help="Messaggio di stato sintetico.")
    parser.add_argument("--detail", type=str, default="", help="Dettaglio operativo dello stato.")
    parser.add_argument("--status", type=str, default="running", help="Stato: running, completed, error, cancelled, idle.")
    parser.add_argument("--target-file", type=str, default="", help="Percorso relativo della nota target nel vault.")
    parser.add_argument("--error", type=str, default=None, help="Eventuale messaggio o trace di errore.")
    parser.add_argument("--monitor", action="store_true", help="Avvia il monitor di scrittura della nota target fino al completamento.")
    parser.add_argument("--timeout", type=int, default=900, help="Timeout in secondi per il monitor.")
    parser.add_argument("--sanitize", type=str, default=None, help="Esegue sanitize_markdown_file sul percorso file indicato ed esce.")
    parser.add_argument("--post-process", action="store_true", help="Post-processing dopo la scrittura dell'agente (metadati MOC + verifica di esclusività NotebookLM).")

    args = parser.parse_args()

    vault_root = resolve_vault_root()

    if args.post_process:
        pp_job = Path(args.job_file).resolve() if args.job_file else RUNTIME_DIR / "current-job.json"
        return post_process_job(vault_root, pp_job)

    # Ramo diretto --sanitize per invocazione rapida
    if args.sanitize:
        san_path = Path(args.sanitize).resolve()
        if not san_path.exists():
            san_path = vault_root / args.sanitize
        if san_path.exists():
            changed = sanitize_markdown_file(san_path)
            sys.stdout.write(f"[Sanitize CLI] File sanificato: {san_path} (modificato: {changed})\n")
            return 0
        else:
            sys.stderr.write(f"[Sanitize CLI] File non trovato: {san_path}\n")
            return 1

    # Ramo diretto --set-status per invocazioni esterne
    if args.set_status:
        target_file_val = args.target_file
        if not target_file_val:
            status_file = RUNTIME_DIR / "job-status.json"
            if status_file.exists():
                try:
                    prev_status = json.loads(status_file.read_text(encoding="utf-8"))
                    target_file_val = prev_status.get("target_file", "")
                except Exception:
                    pass
        if not target_file_val:
            job_file = RUNTIME_DIR / "current-job.json"
            if job_file.exists():
                try:
                    jdata = json.loads(job_file.read_text(encoding="utf-8"))
                    target_file_val = jdata.get("target_file_rel") or jdata.get("target_file_path") or ""
                except Exception:
                    pass

        # Risolvi eventuale percorso alternativo per MOC (01 MOC's/)
        if target_file_val and not (vault_root / target_file_val).exists():
            moc_cand = vault_root / "01 MOC's" / Path(target_file_val).name
            if moc_cand.exists():
                target_file_val = str(moc_cand.relative_to(vault_root))

        if args.status == "completed" and target_file_val:
            t_san = vault_root / target_file_val
            if t_san.exists():
                try:
                    sanitize_markdown_file(t_san)
                except Exception as e_s:
                    sys.stderr.write(f"[Orchestrator] Errore sanificazione target file: {e_s}\n")
        update_status(
            vault_root=vault_root,
            percent=args.percent,
            step_number=args.step,
            total_steps=args.total_steps,
            message=args.message,
            detail=args.detail,
            status=args.status,
            target_file=target_file_val,
            error=args.error,
        )
        return 0

    # Ramo diretto --monitor per tracciare la generazione della nota fino al 100%
    if args.monitor:
        target_rel = args.target_file
        job_file = Path(args.job_file).resolve() if args.job_file else RUNTIME_DIR / "current-job.json"
        if not target_rel and job_file.exists():
            try:
                jdata = json.loads(job_file.read_text(encoding="utf-8"))
                target_rel = jdata.get("target_file_rel") or jdata.get("target_file_path") or ""
                if not target_rel:
                    disc = jdata.get("discipline", "")
                    top = jdata.get("topic", "")
                    op_t = jdata.get("operation_type") or jdata.get("operation", "")
                    if op_t == "moc" and top:
                        m_stem = top if top.lower().endswith("moc") else f"{top} MOC"
                        target_rel = f"01 MOC's/{m_stem}.md"
                    elif disc and top:
                        target_rel = f"{disc}/{top}.md"
            except Exception:
                pass
        if not target_rel:
            sys.stderr.write("[Orchestrator Monitor] Errore: target_file non specificato e non trovato nel job.\n")
            return 1
        return monitor_target_generation(vault_root, target_rel, job_file=job_file, timeout_sec=args.timeout)

    antigravity_dir = vault_root / ".antigravity"
    tools_dir = antigravity_dir / "tools"
    allegati_dir = vault_root / "allegati"
    allegati_dir.mkdir(parents=True, exist_ok=True)

    # Context dir e job file isolati in /tmp/antigravity_runtime (zero scritture nel Vault!)
    context_dir = RUNTIME_DIR / "job-context"
    context_dir.mkdir(parents=True, exist_ok=True)

    job_file = Path(args.job_file).resolve() if args.job_file else RUNTIME_DIR / "current-job.json"
    if not job_file.exists():
        fallback_job = antigravity_dir / "current-job.json"
        if fallback_job.exists():
            job_file = fallback_job
    if not job_file.exists():
        err_msg = f"File job non trovato in: {job_file}"
        sys.stderr.write(f"❌ Errore: {err_msg}\n")
        update_status(
            vault_root=vault_root,
            percent=0,
            step_number=0,
            total_steps=6,
            message="File job mancante",
            detail=err_msg,
            status="error",
            error=err_msg,
        )
        return 1

    try:
        job_data = json.loads(job_file.read_text(encoding="utf-8"))
    except Exception as e:
        err_msg = f"Errore nel parsing del job JSON: {e}"
        sys.stderr.write(f"❌ {err_msg}\n")
        update_status(
            vault_root=vault_root,
            percent=0,
            step_number=0,
            total_steps=6,
            message="Job JSON non valido",
            detail=str(e),
            status="error",
            error=str(e),
        )
        return 1

    discipline_name = job_data.get("discipline", "")
    op_type = job_data.get("operation_type") or job_data.get("operation", "normal")
    topic_str = job_data.get("topic", "Senza Titolo")

    # Calcolo percorso target relativo per tracking e apertura automatica
    target_rel = ""
    if op_type == "edit":
        target_rel = job_data.get("target_file_path", "")
    elif op_type == "moc":
        # Un solo nome possibile: 01 MOC's/<Argomento> MOC.md (l'utente scrive solo l'argomento)
        topic_str = re.sub(r"\s*\bMOC\s*$", "", topic_str, flags=re.IGNORECASE).strip() or topic_str
        job_data["topic"] = topic_str
        target_rel = f"01 MOC's/{topic_str} MOC.md"
        job_data["target_file_path"] = target_rel
        job_data["target_file_rel"] = target_rel
        job_data["target_file_abs"] = str(vault_root / target_rel)
        try:
            job_file.write_text(json.dumps(job_data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
    else:
        # Nota collegata a un MOC di corso: <Disciplina>/<Corso>/<NN Modulo>/<Titolo>.md (vault_layout.py)
        target_rel = f"{discipline_name}/{topic_str}.md"
        if op_type == "normal":
            try:
                import vault_layout
                target_rel = vault_layout.resolve_note_path(
                    vault_root, topic_str, discipline_name, job_data.get("layout_moc", ""),
                    notebooks=[n for n in (job_data.get("notebooks") or []) if isinstance(n, str)],
                )
                (vault_root / target_rel).parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                sys.stderr.write(f"[Orchestrator] Percorso del corso non risolto, uso la cartella disciplina: {e}\n")
            job_data["target_file_path"] = target_rel
            job_data["target_file_rel"] = target_rel
            job_data["target_file_abs"] = str(vault_root / target_rel)
            try:
                job_file.write_text(json.dumps(job_data, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass

    try:
        # Step 1/6 (10%): Preparazione ambiente e backup di sicurezza
        update_status(
            vault_root=vault_root,
            percent=10,
            step_number=1,
            total_steps=6,
            message="🧹 Preparazione ambiente e backup di sicurezza...",
            detail=f"Disciplina: {discipline_name} | Target: {target_rel}",
            status="running",
            target_file=target_rel,
        )
        time.sleep(0.35)

        style_file = antigravity_dir / "style-examples.json"
        style_data: Dict[str, Any] = {}
        if style_file.exists():
            try:
                style_data = json.loads(style_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        discipline_cfg = style_data.get("disciplines", {}).get(discipline_name, {})

        print("======================================================================")
        print("   🚀 ANTIGRAVITY ORCHESTRATOR — ELABORAZIONE JOB OTTIMIZZATA        ")
        print("======================================================================")
        print(f"• Titolo / Argomento: {topic_str}")
        print(f"• Tipo Operazione:    {job_data.get('operation_label')} ({op_type})")
        if op_type == "moc":
            print(f"• Modalità MOC:       {job_data.get('moc_mode')}")
        elif op_type == "edit":
            print(f"• Modalità Modifica:  {job_data.get('edit_mode')}")
            print(f"• File Target:        {job_data.get('target_file_path')}")
        print(f"• Disciplina:         {discipline_name} (Polo: #{job_data.get('pole')})")
        print(f"• Vault Root:         {vault_root}")
        print("----------------------------------------------------------------------")

        # 0. Backup Automatico di Sicurezza Immediato (se operazione edit)
        backup_file: Optional[Path] = None
        if op_type == "edit":
            target_edit_rel = job_data.get("target_file_path", "")
            print(f"🛡️ Creazione backup automatico di sicurezza per '{target_edit_rel}'...")
            backup_file = create_target_note_backup(vault_root, target_edit_rel)
            if backup_file:
                job_data["backup_file"] = str(backup_file)
                try:
                    job_data["backup_rel"] = str(backup_file.relative_to(vault_root))
                except Exception:
                    job_data["backup_rel"] = str(backup_file)
                print(f"   Backup salvato in: {backup_file}")
            else:
                print(f"   ⚠️ Impossibile creare il backup per {target_edit_rel}")

        # 1. Pre-Assembly Statico delle Istruzioni (Zero Perdita di Qualità)
        print(f"📚 Compilazione istruzioni statiche per '{discipline_name}'...")
        compiled_inst_path = compile_static_instructions(
            vault_root=vault_root,
            antigravity_dir=antigravity_dir,
            discipline_name=discipline_name,
            context_dir=context_dir,
        )

        # Step 2/6 (25%): Estrazione fonte in corso
        source_info = job_data.get("source") or {}
        update_status(
            vault_root=vault_root,
            percent=25,
            step_number=2,
            total_steps=6,
            message=f"📥 Estrazione fonte in corso ({source_info.get('label', 'Fonte')})...",
            detail=f"Parsing sorgente tipo '{source_info.get('type')}'",
            status="running",
            target_file=target_rel,
        )
        time.sleep(0.35)

        print(f"🔄 Elaborazione rapida fonte: {source_info.get('label')} [tipo: {source_info.get('type')}]...")
        source_results = process_source_fast(
            source_info=source_info,
            vault_root=vault_root,
            allegati_dir=allegati_dir,
            context_dir=context_dir,
            tools_dir=tools_dir,
            job_data=job_data,
        )

        # Salva il contenuto estratto della fonte
        (context_dir / "source_content.md").write_text(source_results["content_markdown"], encoding="utf-8")
        extracted_media_count = len(source_results.get("extracted_files", []))
        source_char_count = len(source_results.get("content_markdown", ""))

        # Step 3/6 (45%): Ricerca evidenze scientifiche su PubMed e media
        update_status(
            vault_root=vault_root,
            percent=45,
            step_number=3,
            total_steps=6,
            message="🔬 Ricerca evidenze scientifiche su PubMed e media...",
            detail=f"{extracted_media_count} media estratti, {source_char_count} caratteri testo",
            status="running",
            target_file=target_rel,
        )
        time.sleep(0.35)

        # Trigger Strumenti Scientifici Sequenziali
        auto_tool_results = {
            "pubmed_evidence": None,
            "science_media": None,
            "targeted_pubmed_queries": [],
        }
        should_run_auto_tools = True
        if op_type == "edit" and job_data.get("edit_mode") in ["surgical_prompt", "reformat_standard"]:
            should_run_auto_tools = False

        if should_run_auto_tools:
            print(f"🔬 Esecuzione PubMed e Tool Scientifici sequenziali per '{discipline_name}'...")
            auto_tool_results = trigger_auto_tools_sequential(
                discipline_name=discipline_name,
                discipline_cfg=discipline_cfg,
                topic=topic_str,
                source_text=source_results.get("raw_source_text", ""),
                allegati_dir=allegati_dir,
                context_dir=context_dir,
                tools_dir=tools_dir,
            )

        pubmed_studies_count = len(auto_tool_results.get("pubmed_evidence", {}).get("articles", []) if auto_tool_results.get("pubmed_evidence") else [])

        # Step 4/6 (60%): Analisi collegamenti chirurgici tra paragrafi e controllo contraddizioni nel Vault
        update_status(
            vault_root=vault_root,
            percent=60,
            step_number=4,
            total_steps=6,
            message="🔗 Analisi collegamenti chirurgici tra paragrafi e controllo contraddizioni nel Vault...",
            detail=f"{pubmed_studies_count} studi PubMed trovati | Indicizzazione BM25 in corso",
            status="running",
            target_file=target_rel,
        )
        time.sleep(0.35)

        print(f"🔗 Calcolo collegamenti chirurgici e tesi per controllo conflitti (paragraph_linker.py)...")
        source_content_path = context_dir / "source_content.md"
        recom_md_path = context_dir / "recommended-links.md"
        claims_md_path = context_dir / "existing-vault-claims.md"
        res_linker = run_tool_script(
            "paragraph_linker.py",
            [
                "--build-index",
                "--query-file", str(source_content_path),
                "--topic", topic_str,
                "--discipline", discipline_name,
                "--out-md", str(recom_md_path),
                "--out-claims", str(claims_md_path),
                "--index-file", str(RUNTIME_DIR / "paragraph-index.json"),
            ],
            tools_dir,
        )
        if res_linker.returncode != 0:
            sys.stderr.write(f"[Orchestrator] Warning paragraph_linker: {res_linker.stderr[:250]}\n")

        # Step 5/6 (70%): Generazione del Prompt Operativo Vincolante
        update_status(
            vault_root=vault_root,
            percent=70,
            step_number=5,
            total_steps=6,
            message="✍️ Antigravity sta generando la nota e gli schemi...",
            detail=f"Compilazione prompt operativo vincolante per {target_rel}...",
            status="running",
            target_file=target_rel,
        )

        print("📝 Generazione prompt operativo vincolante in current-prompt.md...")
        prompt_text = build_operational_prompt(
            job_data=job_data,
            discipline_cfg=discipline_cfg,
            source_results=source_results,
            auto_tool_results=auto_tool_results,
            compiled_instructions_path=compiled_inst_path,
            vault_root=vault_root,
            context_dir=context_dir,
            backup_file=backup_file,
        )

        prompt_path = RUNTIME_DIR / "current-prompt.md"
        prompt_path.write_text(prompt_text, encoding="utf-8")

        # Aggiorna stato nel job
        job_data["status"] = "ready_for_agent"
        job_data["target_file_rel"] = target_rel
        job_data["grounding_verification_required"] = bool(
            op_type == "normal"
            and source_info.get("type") in ["notebooklm", "notebooklm_manual"]
            and not (job_data.get("allow_base_knowledge") or source_info.get("allow_base_knowledge"))
        )
        job_data["moc_check_required"] = op_type == "moc"
        job_data["processed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        job_data["extracted_media_count"] = extracted_media_count
        job_file.write_text(json.dumps(job_data, indent=2, ensure_ascii=False), encoding="utf-8")

        update_status(
            vault_root=vault_root,
            percent=70,
            step_number=5,
            total_steps=6,
            message="✍️ Antigravity sta generando la nota e gli schemi...",
            detail=f"current-prompt.md pronto | In attesa di scrittura su {target_rel}",
            status="running",
            target_file=target_rel,
        )

        print("----------------------------------------------------------------------")
        print(f"✅ Pre-processing completato con successo!")
        print(f"📁 Istruzioni compilate: {compiled_inst_path}")
        if backup_file:
            print(f"🛡️ Backup sicurezza:    {backup_file}")
        print(f"🔗 Link raccomandati:   {recom_md_path}")
        print(f"🏛️ Conflitti epistemici: {claims_md_path}")
        print(f"📁 Context salvato in:   {context_dir}")
        print(f"🖼️ Media salvati in:     {allegati_dir} ({extracted_media_count} file)")
        print(f"🎙️ Sbobinatura audio:    audio_transcribe.py abilitato (MLX Whisper Apple Silicon ready)")
        print(f"📊 Diagrammi Mermaid:    Sintassi anti-crash abilitata (Legge 10: doppi apici obbligatori)")
        print(f"🎯 Palestra d'Esame:     study_panel.js abilitato (Legge 8: 6-10 Flashcard, 4-6 Quiz)")
        print(f"🃏 Sincronizzazione Anki: anki_sync.py configurato (porta 8765 / MathJax ready)")
        print(f"📄 Prompt pronto in:     {prompt_path}")
        print("======================================================================")
        print("")
        print("👉 Antigravity può ora procedere direttamente alla redazione del MOC / della nota")
        print("   leggendo: .antigravity/current-prompt.md")
        print("")

        return 0

    except Exception as e:
        err_detail = traceback.format_exc()
        sys.stderr.write(f"\n❌ ERRORE CRITICO ORCHESTRATOR:\n{err_detail}\n")
        err_msg = str(e)
        display_msg = err_msg if err_msg.startswith("❌") else "Errore durante l'elaborazione del job"
        status_file = RUNTIME_DIR / "job-status.json"
        existing_detail = ""
        if status_file.exists():
            try:
                s_json = json.loads(status_file.read_text(encoding="utf-8"))
                if s_json.get("status") == "error" and s_json.get("detail"):
                    existing_detail = s_json.get("detail")
            except Exception:
                pass
        update_status(
            vault_root=vault_root,
            percent=0,
            step_number=0,
            total_steps=6,
            message=display_msg,
            detail=existing_detail if existing_detail else str(e),
            status="error",
            target_file=target_rel,
            error=str(e),
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())

