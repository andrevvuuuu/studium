#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audio_transcribe.py
===================
Sbobinatore Locale ad Alte Prestazioni per Lezioni e File Audio.

Caratteristiche:
1. Ottimizzato per Apple Silicon su macOS tramite MLX (`mlx-community/whisper-large-v3-turbo`
   oppure `whisper-medium-mlx`), con fallback su `whisper` standard se MLX non è presente.
2. Segmentazione temporale pulita con timestamp formattati a blocchi (`[MM:SS]`).
3. Supporto per tutti i formati audio comuni: .m4a, .mp3, .wav, .aac, .ogg, .flac.
4. Esportazione automatica in .antigravity/job-context/audio_transcript_<nomefile>.txt
   per alimentazione diretta dell'orchestratore e di Antigravity.
5. Zero placeholder, gestione robusta degli errori e interfaccia CLI completa.
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


SUPPORTED_AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".aac", ".ogg", ".flac", ".m4b", ".mp4"}
DEFAULT_MLX_MODEL = "mlx-community/whisper-large-v3-turbo"
FALLBACK_MLX_MODELS = [
    "mlx-community/whisper-large-v3-turbo",
    "mlx-community/whisper-medium-mlx",
    "mlx-community/whisper-small-mlx",
    "mlx-community/whisper-tiny"
]


def resolve_vault_root() -> Path:
    """Risolve la radice del vault Obsidian."""
    curr = Path(__file__).resolve().parent
    for parent in [curr] + list(curr.parents):
        if (parent / ".obsidian").is_dir() or (parent / ".antigravity").is_dir():
            return parent
    return Path.cwd()


def format_timestamp(seconds: float) -> str:
    """Formatta un tempo in secondi nel formato [MM:SS] o [HH:MM:SS]."""
    total_sec = max(0, int(seconds))
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hours > 0:
        return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"
    return f"[{minutes:02d}:{secs:02d}]"


def sanitize_filename(name: str) -> str:
    """Rende sicuro un nome file per il salvataggio."""
    clean = re.sub(r"[^\w\-_.]", "_", name)
    return re.sub(r"_+", "_", clean).strip("_")


# ==============================================================================
# 1. TRASCRIZIONE TRAMITE MLX-WHISPER (APPLE SILICON PRIMARIA)
# ==============================================================================

def transcribe_with_mlx(
    audio_path: Path,
    model_name: str = DEFAULT_MLX_MODEL,
    language: Optional[str] = "it",
    verbose: bool = True
) -> Dict[str, Any]:
    """Trascrive il file audio usando mlx_whisper su hardware Apple Silicon."""
    import mlx_whisper

    if verbose:
        sys.stderr.write(f"[AudioTranscribe] Avvio trascrizione con MLX ({model_name})...\n")
        sys.stderr.write(f"[AudioTranscribe] File: {audio_path.name} | Lingua: {language or 'auto'}\n")

    t_start = time.time()
    
    # Tentativo con il modello primario o fallback progressivo sui modelli MLX più leggeri
    last_err: Optional[Exception] = None
    models_to_try = [model_name] + [m for m in FALLBACK_MLX_MODELS if m != model_name]

    for m_cand in models_to_try:
        try:
            kwargs: Dict[str, Any] = {
                "path_or_hf_repo": m_cand,
                "verbose": False,
                "word_timestamps": False
            }
            if language:
                kwargs["language"] = language

            result = mlx_whisper.transcribe(str(audio_path), **kwargs)
            elapsed = time.time() - t_start
            if verbose:
                sys.stderr.write(f"[AudioTranscribe] Trascrizione completata con successo con {m_cand} in {elapsed:.1f}s!\n")
            result["engine"] = f"mlx_whisper ({m_cand})"
            result["elapsed_seconds"] = elapsed
            return result
        except Exception as e:
            last_err = e
            if verbose:
                sys.stderr.write(f"[AudioTranscribe] Modello MLX '{m_cand}' non avviabile: {e}. Provo il successivo...\n")
            continue

    raise RuntimeError(f"Tutti i modelli MLX hanno fallito: {last_err}")


# ==============================================================================
# 2. TRASCRIZIONE TRAMITE WHISPER STANDARD (FALLBACK)
# ==============================================================================

def transcribe_with_standard_whisper(
    audio_path: Path,
    language: Optional[str] = "it",
    verbose: bool = True
) -> Dict[str, Any]:
    """Fallback su openai-whisper standard se mlx_whisper non è presente."""
    import whisper

    if verbose:
        sys.stderr.write(f"[AudioTranscribe] Fallback su whisper standard...\n")

    t_start = time.time()
    model = whisper.load_model("medium")
    
    kwargs: Dict[str, Any] = {"verbose": False}
    if language:
        kwargs["language"] = language

    result = model.transcribe(str(audio_path), **kwargs)
    elapsed = time.time() - t_start
    if verbose:
        sys.stderr.write(f"[AudioTranscribe] Trascrizione completata con whisper standard in {elapsed:.1f}s!\n")
    result["engine"] = "openai_whisper (medium)"
    result["elapsed_seconds"] = elapsed
    return result


# ==============================================================================
# 3. FORMATTAZIONE DEL TESTO E GENERAZIONE OUTPUT
# ==============================================================================

def format_transcript_content(
    audio_path: Path,
    raw_result: Dict[str, Any]
) -> str:
    """Formatta la trascrizione con intestazione strutturata e blocchi orari [MM:SS]."""
    text_content = raw_result.get("text", "").strip()
    segments = raw_result.get("segments", [])
    engine = raw_result.get("engine", "Sconosciuto")
    elapsed = raw_result.get("elapsed_seconds", 0.0)

    lines: List[str] = []
    lines.append(f"# 🎙️ TRASCRIZIONE AUDIO LEZIONE: {audio_path.stem.upper()}")
    lines.append(f"- **File Sorgente:** `{audio_path.name}`")
    lines.append(f"- **Motore Usato:** `{engine}`")
    lines.append(f"- **Tempo Elaborazione:** `{elapsed:.1f}s`")
    lines.append(f"- **Data Sbobinatura:** `{time.strftime('%Y-%m-%d %H:%M:%S')}`")
    lines.append("")
    lines.append("---")
    lines.append("")

    if segments:
        lines.append("## ⏱️ Trascrizione Cronologica con Marcatori Temporali")
        lines.append("")
        for seg in segments:
            start_str = format_timestamp(seg.get("start", 0.0))
            end_str = format_timestamp(seg.get("end", 0.0))
            seg_text = seg.get("text", "").strip()
            if seg_text:
                lines.append(f"**{start_str} - {end_str}** {seg_text}\n")
    else:
        lines.append("## 📄 Testo Integrale")
        lines.append("")
        lines.append(text_content)

    return "\n".join(lines).strip()


def run_transcription(
    audio_path: Path,
    out_dir: Optional[Path] = None,
    model_name: str = DEFAULT_MLX_MODEL,
    language: Optional[str] = "it",
    verbose: bool = True
) -> Dict[str, Any]:
    """Esegue la trascrizione automatica selezionando il miglior motore disponibile."""
    if not audio_path.exists():
        raise FileNotFoundError(f"File audio non trovato: {audio_path}")

    ext = audio_path.suffix.lower()
    if ext not in SUPPORTED_AUDIO_EXTENSIONS:
        sys.stderr.write(f"[AudioTranscribe] Attenzione: estensione {ext} non standard per audio, tento comunque l'apertura...\n")

    # Scelta del motore (MLX prima, Whisper standard poi)
    raw_result: Optional[Dict[str, Any]] = None
    engine_used = ""

    try:
        raw_result = transcribe_with_mlx(audio_path, model_name=model_name, language=language, verbose=verbose)
        engine_used = raw_result.get("engine", "mlx_whisper")
    except ImportError:
        if verbose:
            sys.stderr.write("[AudioTranscribe] mlx_whisper non installato, tentativo con whisper standard...\n")
        try:
            raw_result = transcribe_with_standard_whisper(audio_path, language=language, verbose=verbose)
            engine_used = raw_result.get("engine", "openai_whisper")
        except ImportError:
            raise RuntimeError("Né 'mlx_whisper' né 'whisper' sono disponibili nell'ambiente Python. Installa 'mlx_whisper' o 'openai-whisper'.")
    except Exception as mlx_err:
        if verbose:
            sys.stderr.write(f"[AudioTranscribe] mlx_whisper ha riscontrato un errore ({mlx_err}), provo whisper standard...\n")
        try:
            raw_result = transcribe_with_standard_whisper(audio_path, language=language, verbose=verbose)
            engine_used = raw_result.get("engine", "openai_whisper")
        except Exception as std_err:
            raise RuntimeError(f"Errore trascrizione sia con MLX ({mlx_err}) sia con Whisper standard ({std_err})")

    # Formattazione
    formatted_markdown = format_transcript_content(audio_path, raw_result)
    raw_clean_text = raw_result.get("text", "").strip()

    # Salvataggio su file isolato in /tmp/antigravity_runtime
    runtime_dir = Path("/tmp/antigravity_runtime")
    target_dir = out_dir if out_dir else runtime_dir / "job-context"
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_stem = sanitize_filename(audio_path.stem)
    out_file = target_dir / f"audio_transcript_{safe_stem}.txt"
    out_file.write_text(formatted_markdown, encoding="utf-8")

    if verbose:
        print(f"✅ Trascrizione completata per '{audio_path.name}':")
        print(f"   • Motore:    {engine_used}")
        print(f"   • File txt:  {out_file}")
        print(f"   • Caratteri: {len(raw_clean_text)}")

    return {
        "status": "success",
        "audio_path": str(audio_path),
        "transcript_file": str(out_file),
        "transcript_markdown": formatted_markdown,
        "raw_text": raw_clean_text,
        "engine": engine_used,
        "segments_count": len(raw_result.get("segments", [])),
        "elapsed_seconds": raw_result.get("elapsed_seconds", 0.0)
    }


# ==============================================================================
# 4. ENTRYPOINT CLI
# ==============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sbobinatore locale ad alte prestazioni per file audio di lezioni ed esami.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("audio_path", type=str, help="Percorso del file audio da sbobinare (.m4a, .mp3, .wav, ecc.)")
    parser.add_argument("--out-dir", type=str, default=None, help="Cartella in cui salvare il file di trascrizione.")
    parser.add_argument("--model", type=str, default=DEFAULT_MLX_MODEL, help="Modello Whisper da utilizzare.")
    parser.add_argument("--language", "-l", type=str, default="it", help="Codice lingua (default: 'it'). Usa '' per auto-rilevamento.")
    parser.add_argument("--json", action="store_true", help="Stampa l'output JSON completo sullo standard output.")
    parser.add_argument("--quiet", action="store_true", help="Sopprime i messaggi di progresso.")

    args = parser.parse_args()

    audio_file = Path(args.audio_path).resolve()
    if not audio_file.exists():
        sys.stderr.write(f"❌ Errore: File audio non trovato: {audio_file}\n")
        return 1

    out_directory = Path(args.out_dir).resolve() if args.out_dir else None
    lang_val = args.language if args.language.strip() else None

    try:
        res = run_transcription(
            audio_path=audio_file,
            out_dir=out_directory,
            model_name=args.model,
            language=lang_val,
            verbose=not args.quiet
        )
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        sys.stderr.write(f"❌ Errore durante la trascrizione di {audio_file.name}: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
