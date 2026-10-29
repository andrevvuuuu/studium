#!/usr/bin/env python3
"""
youtube_watch.py
================
Motore di estrazione video YouTube, trascrizione sincronizzata e cattura keyframe
salienti per Obsidian Vault.

Pensato per la fonte:
    🎥 Video YouTube

Funzionalità:
1. Iniezione automatica del PATH completo di macOS (Homebrew, Python user bin, local bin).
2. Lettura automatica dell'URL da CLI o da `.antigravity/job-context.json`.
3. Estrazione metadati (Titolo, Canale, Durata, ID, Data).
4. Download e parsing trascrizioni WebVTT (lingue native it/en e auto-generate).
5. De-duplicazione intelligente dei sottotitoli rolling di YouTube.
6. Scene detection automatica con FFmpeg per catturare cambi di slide, grafici e dimostrazioni.
7. Salvataggio diretto dei fotogrammi nella cartella `allegati/` del vault con nomi coerenti:
   `yt_<videoid>_<mm>_<ss>.png`
8. Generazione di testo sincronizzato con le immagini posizionate al minuto esatto:
   `![[yt_<videoid>_<mm>_<ss>.png]]`

Uso CLI:
    python3 youtube_watch.py "https://www.youtube.com/watch?v=..."
    python3 youtube_watch.py --max-frames 12 --out-dir "$VAULT/allegati"
    python3 youtube_watch.py "https://youtu.be/..." --subtitles-only --json
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Iniezione tassativa del PATH per ambienti GUI / Obsidian / subshell macOS
EXTRA_PATHS = [
    "/opt/homebrew/bin",
    "/opt/homebrew/sbin",
    str(Path.home() / ".local/bin"),
    str(Path.home() / "Library/Python/3.14/bin"),
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

_TS_RX = re.compile(
    r"(?:(\d+):)?(\d{1,2}):(\d{2})(?:[.,](\d{1,3}))?\s*-->\s*"
    r"(?:(\d+):)?(\d{1,2}):(\d{2})(?:[.,](\d{1,3}))?"
)
_ROLLING_OVERLAP_MIN = 8


def resolve_default_out_dir() -> Path:
    """Risolve la cartella allegati predefinita dell'Obsidian Vault."""
    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        cand = parent / "allegati"
        if cand.exists() and cand.is_dir():
            return cand
    vault_root = script_path.parents[2] if len(script_path.parents) > 2 else Path.cwd()
    allegati_dir = vault_root / "allegati"
    allegati_dir.mkdir(parents=True, exist_ok=True)
    return allegati_dir


def read_job_context_url() -> Optional[str]:
    """Tenta di leggere l'URL YouTube dal runtime isolato o dal Vault."""
    runtime_job = Path("/tmp/antigravity_runtime/current-job.json")
    if runtime_job.exists():
        try:
            data = json.loads(runtime_job.read_text(encoding="utf-8"))
            src = data.get("source", {})
            val = src.get("value", "") if isinstance(src, dict) else str(src)
            if val and ("youtube.com" in val or "youtu.be" in val):
                return val.strip()
        except Exception:
            pass

    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        job_file = parent / ".antigravity" / "job-context.json"
        if job_file.exists():
            try:
                data = json.loads(job_file.read_text(encoding="utf-8"))
                val = data.get("source_value", "")
                if val and ("youtube.com" in val or "youtu.be" in val):
                    return val.strip()
            except Exception:
                pass
    return None


def sanitize_slug(text: str) -> str:
    """Slug per nomi file."""
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text.strip("_")


def format_timestamp(seconds: float) -> str:
    """Formatta i secondi in mm:ss o hh:mm:ss."""
    tot = int(round(seconds))
    hh = tot // 3600
    mm = (tot % 3600) // 60
    ss = tot % 60
    if hh > 0:
        return f"{hh:02d}:{mm:02d}:{ss:02d}"
    return f"{mm:02d}:{ss:02d}"


def format_filename_ts(seconds: float) -> str:
    """Formatta i secondi per i nomi dei file: mm_ss oppure hh_mm_ss."""
    tot = int(round(seconds))
    hh = tot // 3600
    mm = (tot % 3600) // 60
    ss = tot % 60
    if hh > 0:
        return f"{hh:02d}_{mm:02d}_{ss:02d}"
    return f"{mm:02d}_{ss:02d}"


def get_video_metadata(url: str) -> Dict[str, Any]:
    """Estrae i metadati essenziali del video tramite yt-dlp -j."""
    cmd = ["yt-dlp", "-j", "--no-playlist", url]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Impossibile leggere i metadati con yt-dlp: {proc.stderr.strip()[:300]}")
    
    info = json.loads(proc.stdout)
    video_id = info.get("id") or "youtube_video"
    title = info.get("title") or "Senza Titolo"
    duration = float(info.get("duration") or 0.0)
    channel = info.get("uploader") or info.get("channel") or "Sconosciuto"
    upload_date = info.get("upload_date") or ""
    webpage_url = info.get("webpage_url") or url

    return {
        "id": video_id,
        "title": title,
        "duration_s": duration,
        "duration_str": format_timestamp(duration),
        "channel": channel,
        "upload_date": upload_date,
        "webpage_url": webpage_url,
    }


def parse_vtt_cues(vtt_text: str) -> List[Dict[str, Any]]:
    """Estrae i blocchi di testo e i relativi timestamp temporali dal file WebVTT."""
    cues: List[Dict[str, Any]] = []
    lines = vtt_text.splitlines()
    i = 0

    def _to_sec(h: Optional[str], m: str, s: str, ms: Optional[str]) -> float:
        return (int(h) if h else 0) * 3600 + int(m) * 60 + int(s) + (int(ms) / 1000.0 if ms else 0.0)

    while i < len(lines):
        match = _TS_RX.search(lines[i])
        if not match:
            i += 1
            continue
        t_start = _to_sec(match.group(1), match.group(2), match.group(3), match.group(4))
        t_end = _to_sec(match.group(5), match.group(6), match.group(7), match.group(8))
        i += 1

        text_lines: List[str] = []
        while i < len(lines) and lines[i].strip():
            # Rimuove tag di stile o colore <c.color...> o <b>, </i>
            clean_l = re.sub(r"<[^>]+>", "", lines[i]).strip()
            if clean_l and not clean_l.startswith("WEBVTT") and not clean_l.startswith("Kind:"):
                text_lines.append(clean_l)
            i += 1

        joined = " ".join(text_lines).strip()
        if joined:
            cues.append({"t_start": t_start, "t_end": t_end, "text": joined})

    return cues


def deduplicate_cues(cues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rimuove le sovrapposizioni a nastro (rolling captions) generate dai sottotitoli automatici di YouTube.
    """
    if not cues:
        return []

    deduped: List[Dict[str, Any]] = []
    for c in cues:
        if not deduped:
            deduped.append(dict(c))
            continue

        prev = deduped[-1]
        c_text = c["text"]
        prev_text = prev["text"]

        # 1. Testo identico: estendi la fine del precedente
        if prev_text == c_text:
            prev["t_end"] = max(prev["t_end"], c["t_end"])
            continue

        # 2. Estensione a nastro (il nuovo cue inizia con tutto il testo del precedente)
        if len(c_text) > len(prev_text) and c_text.startswith(prev_text):
            prev["t_end"] = c["t_end"]
            prev["text"] = c_text
            continue

        # 3. Il nuovo cue è già interamente contenuto alla fine del precedente
        if prev_text.endswith(c_text):
            prev["t_end"] = max(prev["t_end"], c["t_end"])
            continue

        # 4. Sovrapposizione suffisso-prefisso
        max_overlap_check = min(len(prev_text), len(c_text))
        overlap = 0
        for k in range(max_overlap_check, _ROLLING_OVERLAP_MIN - 1, -1):
            if prev_text[-k:] == c_text[:k]:
                overlap = k
                break

        if overlap > 0:
            tail = c_text[overlap:].lstrip()
            if tail:
                deduped.append({"t_start": c["t_start"], "t_end": c["t_end"], "text": tail})
            else:
                prev["t_end"] = max(prev["t_end"], c["t_end"])
            continue

        # 5. Cue distinto
        deduped.append(dict(c))

    return deduped


def fetch_subtitles(url: str, temp_dir: Path) -> List[Dict[str, Any]]:
    """Scarica e processa la trascrizione del video."""
    sub_dir = temp_dir / "subtitles"
    sub_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--ignore-errors",
        "--sub-langs", "it.*,en.*,it,en,de.*,all",
        "--sub-format", "vtt",
        "-o", str(sub_dir / "%(id)s.%(ext)s"),
        url,
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=False)

    vtt_files = sorted(sub_dir.glob("*.vtt"))
    if not vtt_files:
        return []

    # Priorità lingue: italiano (.it.), poi inglese (.en.), poi primo file disponibile
    best_vtt = None
    for vtt in vtt_files:
        name_lower = vtt.name.lower()
        if ".it." in name_lower or name_lower.endswith(".it.vtt"):
            best_vtt = vtt
            break
    if not best_vtt:
        for vtt in vtt_files:
            name_lower = vtt.name.lower()
            if ".en." in name_lower or name_lower.endswith(".en.vtt"):
                best_vtt = vtt
                break
    if not best_vtt:
        best_vtt = vtt_files[0]

    content = best_vtt.read_text(encoding="utf-8", errors="replace")
    raw_cues = parse_vtt_cues(content)
    cleaned_cues = deduplicate_cues(raw_cues)
    return cleaned_cues


def detect_and_extract_frames(
    url: str,
    video_id: str,
    duration: float,
    out_dir: Path,
    temp_dir: Path,
    max_frames: int = 15,
    resolution: int = 960,
    scene_threshold: float = 0.30,
) -> List[Dict[str, Any]]:
    """
    Scarica il flusso video ed estrae i fotogrammi salienti mediante FFmpeg scene change detection.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    template = str(temp_dir / "video.%(ext)s")

    # Download in formato compatto (max 720p) per velocità ed efficienza
    sys.stderr.write("[YouTube Watch] Download stream video per analisi fotogrammi...\n")
    dl_cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "-o", template,
        url,
    ]
    proc = subprocess.run(dl_cmd, capture_output=True, text=True, check=False)
    video_matches = sorted(temp_dir.glob("video.*"))
    if not video_matches:
        sys.stderr.write(f"[YouTube Watch] Impossibile scaricare il video per i frame: {proc.stderr.strip()[:200]}\n")
        return []

    video_path = video_matches[0]

    # Scene change detection con FFmpeg
    sys.stderr.write(f"[YouTube Watch] Rilevamento cambi di scena con FFmpeg (threshold={scene_threshold})...\n")
    scene_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-i", str(video_path),
        "-vf", f"select=gt(scene\\,{scene_threshold}),showinfo",
        "-f", "null",
        "-",
    ]
    scene_proc = subprocess.run(scene_cmd, capture_output=True, text=True, check=False)
    
    # Estrai i timestamp delle scene individuate da showinfo
    detected_timestamps: List[float] = []
    # Includi sempre l'inizio del video (es. secondo 2) per dare contesto iniziale
    if duration > 3.0:
        detected_timestamps.append(min(2.0, duration / 2.0))

    pts_rx = re.compile(r"pts_time:([0-9.]+)")
    for match in pts_rx.finditer(scene_proc.stderr):
        t = float(match.group(1))
        if t <= duration and (not detected_timestamps or (t - detected_timestamps[-1] >= 10.0)):
            detected_timestamps.append(t)

    # Se le scene rilevate sono poche, aggiungi campionamento uniforme (coverage floor)
    target_count = min(max_frames, max(4, int(duration // 60)))
    if len(detected_timestamps) < target_count and duration > 10.0:
        step = duration / (target_count + 1)
        for idx in range(1, target_count + 1):
            cand_t = idx * step
            if all(abs(cand_t - exist_t) > 15.0 for exist_t in detected_timestamps):
                detected_timestamps.append(cand_t)

    detected_timestamps = sorted(list(set(detected_timestamps)))

    # Limita al budget massimo di frame
    if len(detected_timestamps) > max_frames:
        step = len(detected_timestamps) / max_frames
        detected_timestamps = [detected_timestamps[int(i * step)] for i in range(max_frames)]

    extracted_frames: List[Dict[str, Any]] = []
    sys.stderr.write(f"[YouTube Watch] Estrazione di {len(detected_timestamps)} fotogrammi in {out_dir}...\n")

    for idx, t in enumerate(detected_timestamps, 1):
        ts_slug = format_filename_ts(t)
        filename = f"yt_{video_id}_{ts_slug}.png"
        dest_path = out_dir / filename

        # Estrazione singolo fotogramma con FFmpeg
        ff_cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-nostdin",
            "-y",
            "-ss", f"{t:.3f}",
            "-i", str(video_path),
            "-frames:v", "1",
            "-vf", f"scale={resolution}:-2",
            "-q:v", "2",
            str(dest_path),
        ]
        res = subprocess.run(ff_cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0 and dest_path.exists():
            extracted_frames.append({
                "index": idx,
                "timestamp_seconds": t,
                "timestamp_str": format_timestamp(t),
                "filename": filename,
                "absolute_path": str(dest_path.resolve()),
                "wikilink": f"![[{filename}]]",
                "bytes_size": dest_path.stat().st_size,
            })

    return extracted_frames


def build_synchronized_markdown(
    meta: Dict[str, Any],
    frames: List[Dict[str, Any]],
    cues: List[Dict[str, Any]],
) -> str:
    """
    Costruisce il documento Markdown finale inserendo i fotogrammi salienti
    esattamente in corrispondenza del minuto del parlato.
    """
    lines: List[str] = []
    lines.append(f"# {meta['title']}")
    lines.append(f"- **Canale / Autore:** {meta['channel']}")
    lines.append(f"- **Durata:** {meta['duration_str']}")
    lines.append(f"- **Link Originale:** [{meta['webpage_url']}]({meta['webpage_url']})")
    lines.append(f"- **ID Video:** `{meta['id']}`")
    lines.append(f"- **Fotogrammi Salienti Estratti:** {len(frames)}\n")

    if frames:
        lines.append("## 📸 Galleria Fotogrammi Chiave")
        for fr in frames:
            lines.append(f"- `[{fr['timestamp_str']}]` `{fr['filename']}`: `{fr['wikilink']}`")
        lines.append("")

    lines.append("## 🎙️ Trascrizione Completa e Sincronizzata con i Frame\n")

    if not cues:
        lines.append("*(Nessuna trascrizione o sottotitolo disponibile per questo video)*\n")
        for fr in frames:
            lines.append(f"### Fotogramma al minuto {fr['timestamp_str']}")
            lines.append(f"{fr['wikilink']}\n")
        return "\n".join(lines)

    # Associa ogni frame al primo cue che supera o eguaglia il suo timestamp
    frames_by_cue_idx: Dict[int, List[Dict[str, Any]]] = {}
    frame_idx = 0

    for c_idx, cue in enumerate(cues):
        while frame_idx < len(frames) and frames[frame_idx]["timestamp_seconds"] <= cue["t_start"]:
            frames_by_cue_idx.setdefault(c_idx, []).append(frames[frame_idx])
            frame_idx += 1

    while frame_idx < len(frames):
        frames_by_cue_idx.setdefault(len(cues) - 1, []).append(frames[frame_idx])
        frame_idx += 1

    last_header_time = -999.0

    for c_idx, cue in enumerate(cues):
        if c_idx in frames_by_cue_idx:
            for fr in frames_by_cue_idx[c_idx]:
                lines.append(f"\n> [!NOTE] 🖼️ **Fotogramma Chiave al minuto [{fr['timestamp_str']}]**")
                lines.append(f"> {fr['wikilink']}\n")

        if cue["t_start"] - last_header_time >= 35.0:
            ts_str = format_timestamp(cue["t_start"])
            lines.append(f"\n**[{ts_str}]** {cue['text']}")
            last_header_time = cue["t_start"]
        else:
            if lines and not lines[-1].startswith("\n>"):
                lines[-1] = lines[-1] + " " + cue["text"]
            else:
                lines.append(cue["text"])

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analizzatore video YouTube per Obsidian: estrae trascrizione e frame salienti.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("source", nargs="?", default=None, help="URL del video YouTube.")
    parser.add_argument("--url", "-u", type=str, default=None, help="URL esplicito del video YouTube.")
    parser.add_argument(
        "--out-dir",
        "-o",
        type=str,
        default=None,
        help="Cartella allegati in cui salvare i frame (default: cartella allegati del Vault).",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=12,
        help="Numero massimo di fotogrammi salienti da estrarre.",
    )
    parser.add_argument(
        "--resolution",
        type=int,
        default=960,
        help="Larghezza in pixel per i frame estratti.",
    )
    parser.add_argument(
        "--scene-threshold",
        type=float,
        default=0.30,
        help="Soglia di sensibilità per la rilevazione scene di FFmpeg.",
    )
    parser.add_argument(
        "--subtitles-only",
        "--no-frames",
        action="store_true",
        help="Estrae solo i metadati e la trascrizione, saltando il download video e l'estrazione frame.",
    )
    parser.add_argument(
        "--save-markdown",
        type=str,
        default=None,
        help="Salva il report Markdown completo nel percorso specificato.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Restituisce i dati strutturati in formato JSON.",
    )

    args = parser.parse_args()

    # Risoluzione URL: CLI -> --url -> job-context.json
    video_url = args.source or args.url
    if not video_url:
        video_url = read_job_context_url()

    if not video_url:
        parser.print_help()
        sys.stderr.write("\nErrore: Nessun URL YouTube specificato e nessun job-context.json rilevato.\n")
        return 1

    out_dir = Path(args.out_dir).resolve() if args.out_dir else resolve_default_out_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="antigravity_yt_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)

        try:
            sys.stderr.write(f"[YouTube Watch] Risoluzione metadati per: {video_url}\n")
            meta = get_video_metadata(video_url)
        except Exception as e:
            sys.stderr.write(f"Errore lettura metadati: {e}\n")
            return 1

        sys.stderr.write(f"[YouTube Watch] Video: '{meta['title']}' ({meta['duration_str']})\n")
        sys.stderr.write("[YouTube Watch] Ricerca e download sottotitoli / trascrizione...\n")
        cues = fetch_subtitles(video_url, temp_dir)
        sys.stderr.write(f"[YouTube Watch] Trascrizione completata: {len(cues)} segmenti parlati rilevati.\n")

        frames: List[Dict[str, Any]] = []
        if not args.subtitles_only:
            frames = detect_and_extract_frames(
                url=video_url,
                video_id=meta["id"],
                duration=meta["duration_s"],
                out_dir=out_dir,
                temp_dir=temp_dir,
                max_frames=args.max_frames,
                resolution=args.resolution,
                scene_threshold=args.scene_threshold,
            )

        markdown_doc = build_synchronized_markdown(meta, frames, cues)

        if args.save_markdown:
            save_path = Path(args.save_markdown).resolve()
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_text(markdown_doc, encoding="utf-8")
            sys.stderr.write(f"[YouTube Watch] Markdown salvato in: {save_path}\n")

        if args.json:
            result_payload = {
                "metadata": meta,
                "output_directory": str(out_dir),
                "frames": frames,
                "transcript_cues": cues,
                "markdown": markdown_doc,
            }
            print(json.dumps(result_payload, indent=2, ensure_ascii=False))
        else:
            print(markdown_doc)

    return 0


if __name__ == "__main__":
    sys.exit(main())
