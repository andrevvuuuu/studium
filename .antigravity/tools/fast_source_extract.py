#!/usr/bin/env python3
"""
.antigravity/tools/fast_source_extract.py
=========================================
Modulo ad altissime prestazioni per l'estrazione istantanea di fonti video e web
per l'automazione del Vault Obsidian.

Funzionalità Chiave:
1. YouTube Ibrido e Sinergico (Testo in 0.3s + Fotogrammi Chiave via claude-watch / FFmpeg):
   - Estrazione istantanea del trascritto con timestamp esatti [MM:SS] tramite
     `youtube-transcript-api` (con fallback automatico su `yt-dlp`).
   - Esecuzione concorrente/parallela di `claude-watch` (FFmpeg) per catturare i fotogrammi
     chiave salienti (grafici, schemi, lavagne, setup) direttamente in allegati/.
   - Generazione di un documento sincronizzato che inserisce i wikilink ![[yt_...png]]
     al secondo esatto del testo.
2. Estrazione Markdown Pulito da Siti Online (`trafilatura`):
   - Estrae il corpo principale di articoli, paper e saggi in formato Markdown pulito
     (eliminando pubblicità, cookie banner, barre laterali e menu di navigazione).
   - Fallback automatico su `https://r.jina.ai/<url>` se il sito blocca lo scraping locale
     o richiede rendering JavaScript avanzato.

Uso CLI:
    python3 fast_source_extract.py youtube "https://www.youtube.com/watch?v=..."
    python3 fast_source_extract.py youtube "https://youtu.be/..." --no-frames --json
    python3 fast_source_extract.py web "https://example.com/article" --json
    python3 fast_source_extract.py test
"""

import argparse
import concurrent.futures
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Iniezione del PATH completo di macOS per subshell e GUI
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

# Configurazione cartelle Vault
VAULT_ROOT = Path(__file__).resolve().parent.parent.parent
ALLEGATI_DIR = VAULT_ROOT / "allegati"
ALLEGATI_DIR.mkdir(parents=True, exist_ok=True)

# Import del modulo youtube_watch per l'estrazione dei fotogrammi tramite FFmpeg / claude-watch
TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

try:
    import youtube_watch
except ImportError:
    youtube_watch = None

# Librerie di terze parti con fallback
try:
    import youtube_transcript_api
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

try:
    import trafilatura
except ImportError:
    trafilatura = None


# ==============================================================================
# 1. PARSING ID E URL YOUTUBE
# ==============================================================================

_YOUTUBE_REGEXES = [
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?(?:.*&)?v=([A-Za-z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtu\.be/([A-Za-z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/embed/([A-Za-z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([A-Za-z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/v/([A-Za-z0-9_-]{11})"),
    re.compile(r"^([A-Za-z0-9_-]{11})$"),
]

def extract_youtube_id(input_str: str) -> Optional[str]:
    """Estrae l'ID a 11 caratteri da qualsiasi URL o stringa YouTube."""
    input_str = input_str.strip()
    for rx in _YOUTUBE_REGEXES:
        m = rx.search(input_str)
        if m:
            return m.group(1)
    return None

def format_timestamp(seconds: float) -> str:
    """Formatta i secondi in [MM:SS] o [HH:MM:SS]."""
    total = int(round(seconds))
    hrs = total // 3600
    mins = (total % 3600) // 60
    secs = total % 60
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


# ==============================================================================
# 2. MOTORE YOUTUBE: TRASCRIZIONE ISTANTANEA (0.3s) + FOTOGRAMMI CHIAVE
# ==============================================================================

def get_transcript_via_api(video_id: str, languages: Tuple[str, ...] = ("it", "en", "es", "fr", "de")) -> Optional[List[Dict[str, Any]]]:
    """Scarica i sottotitoli in millisecondi tramite youtube-transcript-api."""
    if not YouTubeTranscriptApi:
        return None

    # Adattatore per compatibilità con versioni classiche (metodo di classe) e recenti (istanza)
    raw_snippets = None
    try:
        if hasattr(YouTubeTranscriptApi, "get_transcript"):
            raw_snippets = YouTubeTranscriptApi.get_transcript(video_id, languages=list(languages))
        else:
            api_instance = YouTubeTranscriptApi()
            raw_snippets = api_instance.fetch(video_id, languages=list(languages))
    except Exception as e_direct:
        # Tentativo con list_transcripts per cercare sottotitoli generati automaticamente
        try:
            if hasattr(YouTubeTranscriptApi, "list_transcripts"):
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            else:
                api_instance = YouTubeTranscriptApi()
                transcript_list = api_instance.list(video_id)
            
            # Cerca lingua manuale o auto-generata
            found = None
            for lang in languages:
                try:
                    found = transcript_list.find_transcript([lang])
                    break
                except Exception:
                    pass
            if not found:
                for lang in languages:
                    try:
                        found = transcript_list.find_generated_transcript([lang])
                        break
                    except Exception:
                        pass
            if found:
                raw_snippets = found.fetch()
        except Exception as e_list:
            sys.stderr.write(f"[FastSource] youtube-transcript-api non disponibile per {video_id}: {e_list}\n")
            return None

    if not raw_snippets:
        return None

    formatted_cues: List[Dict[str, Any]] = []
    for snippet in raw_snippets:
        if isinstance(snippet, dict):
            text = snippet.get("text", "")
            start = float(snippet.get("start", 0.0))
            duration = float(snippet.get("duration", 0.0))
        else:
            text = getattr(snippet, "text", "")
            start = float(getattr(snippet, "start", 0.0))
            duration = float(getattr(snippet, "duration", 0.0))
        
        # Pulizia testo
        text = text.replace("\n", " ").strip()
        if text:
            formatted_cues.append({
                "start": start,
                "duration": duration,
                "end": start + duration,
                "text": text
            })

    return formatted_cues


def get_transcript_via_ytdlp(video_id: str) -> List[Dict[str, Any]]:
    """Fallback su yt-dlp per scaricare VTT nativi se le API dirette sono bloccate."""
    if not youtube_watch:
        return []
    url = f"https://www.youtube.com/watch?v={video_id}"
    return youtube_watch.fetch_subtitles(url)


def extract_youtube_fast(
    url_or_id: str,
    capture_frames: bool = True,
    max_frames: int = 8,
    out_dir: Optional[Path] = None,
    languages: Tuple[str, ...] = ("it", "en")
) -> Dict[str, Any]:
    """
    Esegue l'estrazione ibrida e sinergica di YouTube:
    - Thread 1: Trascrizione testuale ultra-veloce (0.3 secondi via youtube-transcript-api).
    - Thread 2: Cattura fotogrammi salienti ad alta risoluzione via FFmpeg / claude-watch in allegati/.
    """
    start_time = time.time()
    video_id = extract_youtube_id(url_or_id)
    if not video_id:
        raise ValueError(f"URL o ID YouTube non valido: {url_or_id}")

    full_url = f"https://www.youtube.com/watch?v={video_id}"
    target_out_dir = Path(out_dir) if out_dir else ALLEGATI_DIR
    target_out_dir.mkdir(parents=True, exist_ok=True)

    result_data: Dict[str, Any] = {
        "video_id": video_id,
        "url": full_url,
        "title": f"YouTube Video ({video_id})",
        "author": "Autore YouTube",
        "duration": 0.0,
        "transcript_source": "none",
        "cues": [],
        "transcript_text": "",
        "frames": [],
        "synchronized_markdown": "",
        "execution_time_seconds": 0.0
    }

    # Recupero metadati di base (titolo/durata)
    meta = None
    if youtube_watch:
        try:
            meta = youtube_watch.get_video_metadata(full_url)
            if meta:
                result_data["title"] = meta.get("title", result_data["title"])
                result_data["author"] = meta.get("author", result_data["author"])
                result_data["duration"] = meta.get("duration", 0.0)
        except Exception as e:
            sys.stderr.write(f"[FastSource] Avviso lettura metadati: {e}\n")

    # Esecuzione concorrente: Trascrizione + Fotogrammi FFmpeg
    def task_transcript():
        sys.stderr.write(f"[FastSource] Estrazione rapida testo per {video_id}...\n")
        cues = get_transcript_via_api(video_id, languages)
        source = "youtube-transcript-api"
        if not cues:
            sys.stderr.write(f"[FastSource] Fallback su yt-dlp per i sottotitoli di {video_id}...\n")
            cues = get_transcript_via_ytdlp(video_id)
            source = "yt-dlp"
        return cues, source

    def task_frames():
        if not capture_frames or not youtube_watch:
            return []
        sys.stderr.write(f"[FastSource] Avvio cattura fotogrammi chiave FFmpeg (max={max_frames})...\n")
        try:
            return youtube_watch.detect_and_extract_frames(
                url=full_url,
                video_id=video_id,
                out_dir=target_out_dir,
                max_frames=max_frames,
                scene_threshold=0.3
            )
        except Exception as e:
            sys.stderr.write(f"[FastSource] Errore estrazione fotogrammi claude-watch: {e}\n")
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        fut_trans = executor.submit(task_transcript)
        fut_frames = executor.submit(task_frames)
        
        cues, trans_source = fut_trans.result()
        frames = fut_frames.result()

    result_data["cues"] = cues
    result_data["transcript_source"] = trans_source
    result_data["frames"] = frames

    # Formattazione del testo grezzo
    transcript_lines = []
    for c in cues:
        ts_str = format_timestamp(c["start"])
        transcript_lines.append(f"[{ts_str}] {c['text']}")
    result_data["transcript_text"] = "\n".join(transcript_lines)

    # Costruzione del Markdown sincronizzato con i fotogrammi inseriti al secondo corretto
    sync_blocks = []
    sync_blocks.append(f"# {result_data['title']}\n")
    sync_blocks.append(f"**Fonte Video**: [{result_data['url']}]({result_data['url']})  ")
    sync_blocks.append(f"**Canale/Autore**: {result_data['author']}  ")
    if result_data['duration'] > 0:
        sync_blocks.append(f"**Durata**: {format_timestamp(result_data['duration'])}  ")
    sync_blocks.append(f"**Metodo Trascrizione**: `{trans_source}`  ")
    sync_blocks.append(f"**Fotogrammi Salienti Estratti**: {len(frames)}\n\n---\n")

    sorted_frames = sorted(frames, key=lambda x: x.get("timestamp", 0.0))
    frame_idx = 0

    for cue in cues:
        cue_time = cue["start"]
        # Inserisci i fotogrammi che precedono o coincidono con questo cue
        while frame_idx < len(sorted_frames) and sorted_frames[frame_idx].get("timestamp", 0.0) <= cue_time:
            f = sorted_frames[frame_idx]
            f_ts = format_timestamp(f.get("timestamp", 0.0))
            wikilink = f.get("vault_wikilink", f"![[{f.get('filename')}]]")
            sync_blocks.append(f"\n> [!image] Fotogramma Chiave [{f_ts}]\n> {wikilink}\n")
            frame_idx += 1

        ts_str = format_timestamp(cue_time)
        sync_blocks.append(f"**[{ts_str}]** {cue['text']}  ")

    # Eventuali fotogrammi rimasti alla fine del video
    while frame_idx < len(sorted_frames):
        f = sorted_frames[frame_idx]
        f_ts = format_timestamp(f.get("timestamp", 0.0))
        wikilink = f.get("vault_wikilink", f"![[{f.get('filename')}]]")
        sync_blocks.append(f"\n> [!image] Fotogramma Chiave Finale [{f_ts}]\n> {wikilink}\n")
        frame_idx += 1

    result_data["synchronized_markdown"] = "\n".join(sync_blocks)
    result_data["execution_time_seconds"] = round(time.time() - start_time, 2)
    sys.stderr.write(f"[FastSource] Completato in {result_data['execution_time_seconds']}s ({len(cues)} segmenti, {len(frames)} immagini).\n")

    return result_data


# ==============================================================================
# 3. MOTORE SITI WEB: ESTRAZIONE MARKDOWN PULITO (TRAFILATURA + JINA.AI)
# ==============================================================================

def extract_web_fast(url: str, timeout: int = 15) -> Dict[str, Any]:
    """
    Estrae l'intero articolo o documento da una pagina web in formato Markdown pulito.
    Usa `trafilatura` locale per rimuovere clutter/pubblicità, con fallback automatico
    su `https://r.jina.ai/<url>` per siti protetti da bot o richiedenti rendering JS.
    """
    start_time = time.time()
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    result_data: Dict[str, Any] = {
        "url": url,
        "title": "",
        "source": "none",
        "markdown": "",
        "char_count": 0,
        "execution_time_seconds": 0.0
    }

    # Tentativo 1: Trafilatura locale
    trafilatura_success = False
    if trafilatura:
        try:
            sys.stderr.write(f"[FastSource] Download e parsing con trafilatura per {url}...\n")
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                extracted = trafilatura.extract(
                    downloaded,
                    output_format="markdown",
                    include_tables=True,
                    include_links=True,
                    include_images=True,
                    favor_precision=True
                )
                if extracted and len(extracted.strip()) > 200:
                    result_data["markdown"] = extracted.strip()
                    result_data["source"] = "trafilatura"
                    result_data["char_count"] = len(result_data["markdown"])
                    # Estrai titolo con metadati trafilatura se possibile
                    meta = trafilatura.extract_metadata(downloaded)
                    if meta and meta.title:
                        result_data["title"] = meta.title
                    trafilatura_success = True
        except Exception as e:
            sys.stderr.write(f"[FastSource] Avviso trafilatura: {e}\n")

    # Tentativo 2: Fallback su r.jina.ai (per JS-heavy o Cloudflare/Bot-blocked sites)
    if not trafilatura_success or not result_data["markdown"]:
        sys.stderr.write(f"[FastSource] Fallback su lettore cloud r.jina.ai per {url}...\n")
        try:
            jina_url = f"https://r.jina.ai/{url}"
            req = urllib.request.Request(jina_url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_text = resp.read().decode("utf-8", errors="replace")
                if raw_text and len(raw_text.strip()) > 100:
                    result_data["markdown"] = raw_text.strip()
                    result_data["source"] = "jina_ai"
                    result_data["char_count"] = len(result_data["markdown"])
                    
                    # Estrai titolo dalle prime righe di jina
                    lines = result_data["markdown"].splitlines()
                    for line in lines[:5]:
                        if line.startswith("# ") or line.startswith("Title:"):
                            result_data["title"] = line.replace("# ", "").replace("Title:", "").strip()
                            break
        except Exception as e:
            sys.stderr.write(f"[FastSource] Errore fallback jina.ai: {e}\n")

    # Se ancora vuoto, fai una richiesta diretta e ripulisci i tag HTML elementari
    if not result_data["markdown"]:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                html = resp.read().decode("utf-8", errors="replace")
                # Estrazione rozza di fallback
                text_clean = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
                text_clean = re.sub(r"<style.*?</style>", "", text_clean, flags=re.DOTALL | re.IGNORECASE)
                text_clean = re.sub(r"<[^>]+>", " ", text_clean)
                text_clean = re.sub(r"\s+", " ", text_clean).strip()
                result_data["markdown"] = text_clean[:5000]
                result_data["source"] = "raw_html_fallback"
                result_data["char_count"] = len(result_data["markdown"])
        except Exception as e:
            sys.stderr.write(f"[FastSource] Errore finale download web: {e}\n")

    if not result_data["title"]:
        parsed = urllib.parse.urlparse(url)
        result_data["title"] = parsed.netloc + parsed.path

    result_data["execution_time_seconds"] = round(time.time() - start_time, 2)
    sys.stderr.write(f"[FastSource] Articolo estratto in {result_data['execution_time_seconds']}s ({result_data['char_count']} caratteri, fonte: {result_data['source']}).\n")
    return result_data


# ==============================================================================
# 4. CLI ENTRYPOINT & SELF-TEST
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Estrattore rapido e sinergico di fonti (YouTube & Web)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: youtube
    yt_parser = subparsers.add_parser("youtube", help="Estrae trascrizione rapida e fotogrammi chiave YouTube")
    yt_parser.add_argument("url", help="URL o ID del video YouTube")
    yt_parser.add_argument("--max-frames", type=int, default=8, help="Numero massimo di fotogrammi da catturare con FFmpeg")
    yt_parser.add_argument("--no-frames", action="store_true", help="Disabilita la cattura immagini, estrai solo il testo")
    yt_parser.add_argument("--out-dir", default=str(ALLEGATI_DIR), help="Cartella destinazione immagini")
    yt_parser.add_argument("--json", action="store_true", help="Stampa l'output come JSON")
    yt_parser.add_argument("--output", help="File opzionale dove salvare il Markdown sincronizzato")

    # Subcommand: web
    web_parser = subparsers.add_parser("web", help="Estrae il testo pulito in Markdown da qualsiasi sito web")
    web_parser.add_argument("url", help="URL della pagina o articolo web")
    web_parser.add_argument("--json", action="store_true", help="Stampa l'output come JSON")
    web_parser.add_argument("--output", help="File opzionale dove salvare il Markdown")

    # Subcommand: test
    subparsers.add_parser("test", help="Esegue un test diagnostico rapido delle funzionalità")

    args = parser.parse_args()

    if args.command == "youtube":
        res = extract_youtube_fast(
            url_or_id=args.url,
            capture_frames=not args.no_frames,
            max_frames=args.max_frames,
            out_dir=Path(args.out_dir)
        )
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        elif args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(res["synchronized_markdown"])
            print(f"[OK] Markdown sincronizzato salvato in: {args.output}")
        else:
            print(res["synchronized_markdown"])

    elif args.command == "web":
        res = extract_web_fast(args.url)
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        elif args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(res["markdown"])
            print(f"[OK] Markdown estratto salvato in: {args.output}")
        else:
            print(f"# {res['title']}\n\n**Fonte**: {res['url']} (Estratto via `{res['source']}`)\n\n---\n")
            print(res["markdown"])

    elif args.command == "test":
        print("=== SELF-TEST FAST SOURCE EXTRACT ===")
        # Test 1: YouTube ID Parsing
        sample_urls = [
            "https://www.youtube.com/watch?v=M7lc1UVf-VE",
            "https://youtu.be/dQw4w9WgXcQ",
            "M7lc1UVf-VE"
        ]
        for u in sample_urls:
            vid = extract_youtube_id(u)
            assert vid is not None, f"Fallito parsing ID per {u}"
            print(f"[+] Parsing URL YouTube OK: {u} -> {vid}")

        # Test 2: YouTube Fast Transcript API
        print("[*] Test download trascrizione istantanea YouTube (M7lc1UVf-VE)...")
        t0 = time.time()
        cues = get_transcript_via_api("M7lc1UVf-VE", ("en",))
        dt = time.time() - t0
        assert cues and len(cues) > 0, "Trascrizione non recuperata"
        print(f"[+] Trascrizione API completata in {dt:.2f}s ({len(cues)} battute estraibili)")

        # Test 3: Web Article Extraction
        print("[*] Test estrazione Markdown da sito web...")
        w_res = extract_web_fast("https://it.wikipedia.org/wiki/Numero_primo")
        assert w_res["char_count"] > 1000, f"Estrazione web fallita o troppo corta ({w_res['char_count']} chars)"
        print(f"[+] Estrazione Web completata in {w_res['execution_time_seconds']}s ({w_res['char_count']} caratteri, metodo: {w_res['source']})")

        print("\n[OK] TUTTI I TEST SUPERATI CON SUCCESSO!")


if __name__ == "__main__":
    main()
