#!/usr/bin/env python3
"""
nlm_local.py — Testo originale delle fonti dei notebook NotebookLM, in cache sul Mac.

Quando la chat di NotebookLM è al limite di utilizzo, `nlm source content` funziona ancora (è il
testo grezzo dei PDF, senza AI). Qui lo si scarica una volta per notebook e si cercano i passaggi
pertinenti a una nota, così la nota resta basata solo sulle fonti del corso.

Uso manuale:
  python3 nlm_local.py --sync <notebook_id>
  python3 nlm_local.py --search <notebook_id> "Numeri Naturali"
"""

import argparse
import fcntl
import json
import math
import re
import subprocess
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

CACHE_DIR = Path.home() / "Library" / "Caches" / "antigravity" / "nlm-sources"
MANIFEST_TTL = 6 * 3600  # elenco delle fonti ricontrollato al massimo ogni 6 ore
CHUNK_CHARS = 1400

STOPWORDS = {
    "della", "delle", "dello", "degli", "dalla", "dalle", "dallo", "dagli", "nella", "nelle", "nello",
    "negli", "sulla", "sulle", "sullo", "sugli", "alla", "alle", "allo", "agli", "come", "anche", "sono",
    "essere", "questo", "questa", "questi", "queste", "quello", "quella", "quindi", "allora", "ogni",
    "tutti", "tutte", "dove", "quando", "mentre", "perche", "infatti", "cioe", "ovvero", "oppure",
    "teorema", "definizione", "proprieta", "metodo", "esempio", "esempi", "caso", "casi", "parte", "uguale",
}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _terms(text: str) -> List[str]:
    """Parole significative ridotte alla radice (prime 6 lettere: naturali/naturale -> natura)."""
    return [w[:6] for w in re.findall(r"[a-z]{4,}", _norm(text)) if w not in STOPWORDS]


def _run_nlm(args: Sequence[str], timeout: int = 120) -> str:
    proc = subprocess.run(["nlm", *args], capture_output=True, text=True, timeout=timeout, check=False)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip()[:300])
    return proc.stdout


def sync_notebook(nb_id: str, force: bool = False) -> Path:
    """Scarica (solo le mancanti) le fonti del notebook. Restituisce la cartella della cache."""
    nb_dir = CACHE_DIR / nb_id
    nb_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = nb_dir / "manifest.json"
    with open(nb_dir / ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}
        if not force and time.time() - manifest.get("checked_at", 0) < MANIFEST_TTL:
            return nb_dir
        sources = json.loads(_run_nlm(["source", "list", nb_id]))
        entries = []
        for src in sources:
            sid, title = src.get("id"), (src.get("title") or "").strip()
            if not sid:
                continue
            txt = nb_dir / f"{sid}.txt"
            if not txt.exists() or txt.stat().st_size == 0:
                try:
                    data = json.loads(_run_nlm(["source", "content", sid, "--json"], timeout=300))
                    txt.write_text(data.get("content") or "", encoding="utf-8")
                except Exception as e:
                    sys.stderr.write(f"[nlm_local] Fonte non scaricata ({title}): {e}\n")
                    continue
            entries.append({"id": sid, "title": title})
        manifest = {"checked_at": time.time(), "sources": entries}
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return nb_dir


def _chunks(nb_id: str) -> List[Tuple[str, int, str]]:
    """[(titolo fonte, posizione, testo)] in blocchi di circa CHUNK_CHARS caratteri."""
    nb_dir = sync_notebook(nb_id)
    try:
        sources = json.loads((nb_dir / "manifest.json").read_text(encoding="utf-8")).get("sources", [])
    except Exception:
        sources = []
    out: List[Tuple[str, int, str]] = []
    for src in sources:
        try:
            text = (nb_dir / f"{src['id']}.txt").read_text(encoding="utf-8")
        except Exception:
            continue
        # i PDF possono contenere caratteri di controllo (anche \x00, che rompe gli argomenti dei comandi)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        buf = ""
        pos = 0
        for para in re.split(r"\n\s*\n", text):
            para = re.sub(r"[ \t]+", " ", para).strip()
            if not para:
                continue
            if buf and len(buf) + len(para) > CHUNK_CHARS:
                out.append((src["title"], pos, buf))
                pos += 1
                buf = ""
            buf = f"{buf}\n\n{para}" if buf else para
        if buf:
            out.append((src["title"], pos, buf))
    return out


def search(nb_ids: Sequence[str], query: str, extra: Sequence[str] = (), max_chars: int = 45000) -> List[Tuple[str, str]]:
    """Passaggi più pertinenti a `query` (+ termini `extra`, es. le sezioni richieste dal MOC).
    Restituisce [(titolo fonte, testo)] in ordine di fonte e posizione, con il blocco successivo a
    ogni blocco scelto (le dimostrazioni proseguono spesso nel blocco dopo)."""
    chunks: List[Tuple[str, int, str]] = []
    for nb_id in nb_ids:
        try:
            chunks.extend(_chunks(nb_id))
        except Exception as e:
            sys.stderr.write(f"[nlm_local] Notebook {nb_id} non disponibile: {e}\n")
    if not chunks:
        return []
    main_terms = _terms(query)
    extra_terms = [t for x in extra for t in _terms(x)]
    if not main_terms and not extra_terms:
        return []
    chunk_terms = [Counter(_terms(c[2])) for c in chunks]
    df = Counter(t for ct in chunk_terms for t in set(ct))
    n = len(chunks)
    phrase = _norm(query).strip()
    scores = []
    for i, ct in enumerate(chunk_terms):
        score = 0.0
        for weight, terms in ((1.0, set(main_terms)), (0.5, set(extra_terms))):
            for t in terms:
                if ct.get(t):
                    score += weight * (1 + math.log(ct[t])) * math.log(1 + n / df[t])
        # tutte le parole del titolo nello stesso blocco, o il titolo per intero: molto pertinente
        if main_terms and all(ct.get(t) for t in set(main_terms)):
            score *= 1.5
        if phrase and phrase in _norm(chunks[i][2]):
            score *= 2
        scores.append(score)
    best = sorted((i for i in range(n) if scores[i] > 0), key=lambda i: -scores[i])
    picked: List[int] = []
    total = 0
    for i in best:
        for j in (i, i + 1):
            if j < n and j not in picked and chunks[j][0] == chunks[i][0]:
                if total + len(chunks[j][2]) > max_chars:
                    break
                picked.append(j)
                total += len(chunks[j][2])
        if total >= max_chars:
            break
    picked.sort()
    return [(chunks[i][0], chunks[i][2]) for i in picked]


def format_passages(passages: List[Tuple[str, str]]) -> str:
    out, last = [], None
    for title, text in passages:
        if title != last:
            out.append(f"\n##### Fonte: {title}")
            last = title
        out.append(text)
    return "\n\n".join(out).strip()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sync", metavar="NB_ID")
    ap.add_argument("--search", nargs=2, metavar=("NB_ID", "QUERY"))
    args = ap.parse_args()
    if args.sync:
        d = sync_notebook(args.sync, force=True)
        print(json.loads((d / "manifest.json").read_text())["sources"].__len__(), "fonti in", d)
    if args.search:
        res = search([args.search[0]], args.search[1])
        print(f"{len(res)} passaggi, {sum(len(t) for _, t in res)} caratteri")
        print(format_passages(res)[:3000])
