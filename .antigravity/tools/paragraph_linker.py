#!/usr/bin/env python3
"""
paragraph_linker.py
===================
Motore di Collegamento Chirurgico tra Singoli Paragrafi ([[Nota#Paragrafo|testo]])
e Blocchi Semantici ([[Nota#^id-blocco|testo]]).

Caratteristiche:
1. Zero dipendenze esterne pesanti (Python standard library: re, json, math, collections).
2. Indicizzazione Granulare a 3 Livelli del Vault (.antigravity/paragraph-index.json):
   - Livello 1: Note Intere (titolo, disciplina, alias, tags, intro summary).
   - Livello 2: Singoli Paragrafi / Sottosezioni (##, ###, #### con sintassi Obsidian pronta).
   - Livello 3: Callout Principali e Blocchi Semantici con ID (^id-blocco).
3. Ranking ad Alta Precisione basato su BM25 + Exact Match Boosting:
   - Termini chiave in grassetto (**...**)
   - Corrispondenza esatta nei titoli degli header e delle note
   - Titoli dei callout e formule matematiche
4. Generazione del Dossier (.antigravity/job-context/recommended-links.md):
   - Tabella A: 25 collegamenti chirurgici a paragrafi specifici
   - Tabella B: 15 collegamenti diretti a singoli callout/teoremi con block ID
   - Tabella C: 15 collegamenti a note intere e MOC
"""

import argparse
import collections
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Insieme di Stopwords bilingue (Italiano + Inglese) per raffinare il ranking BM25
STOPWORDS: Set[str] = {
    # Italiano
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "a", "da", "in",
    "con", "su", "per", "tra", "fra", "e", "ed", "o", "od", "ad", "del", "dello",
    "della", "dei", "degli", "delle", "al", "allo", "alla", "ai", "agli", "alle",
    "dal", "dallo", "dalla", "dai", "dagli", "dalle", "nel", "nello", "nella", "nei",
    "negli", "nelle", "sul", "sullo", "sulla", "sui", "sugli", "sulle", "che", "chi",
    "cui", "quale", "quali", "quanto", "quanti", "quanta", "quante", "questo", "questa",
    "questi", "queste", "quello", "quella", "quelli", "quelle", "mio", "tuo", "suo",
    "nostro", "vostro", "loro", "si", "ci", "vi", "ti", "mi", "me", "te", "se",
    "non", "piu", "più", "meno", "molto", "molti", "molte", "poco", "pochi", "poche",
    "tanto", "tanti", "tante", "ogni", "ciascun", "ciascuno", "ciascuna", "tutto",
    "tutti", "tutta", "tutte", "anche", "pure", "ancora", "gia", "già", "mai",
    "sempre", "bene", "male", "come", "cosa", "dove", "quando", "perche", "perché",
    "quindi", "dunque", "pero", "però", "tuttavia", "invece", "mentre", "infatti",
    "ossia", "ovvero", "cioe", "cioè", "sia", "sono", "stato", "stata", "stati",
    "state", "essere", "avere", "ho", "hai", "ha", "abbiamo", "avete", "hanno",
    "era", "erano", "fu", "furono", "sara", "sarà", "saranno", "sarebbe", "sarebbero",
    # English
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "up", "about", "into", "over", "after", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "shall", "will", "should", "would", "may", "might", "must", "can",
    "could", "this", "that", "these", "those", "it", "its", "as", "if"
}

IGNORED_VAULT_DIRS: Set[str] = {
    ".obsidian", ".antigravity", ".trash", "templates", "Templates",
    ".git", "00 Meta", "Prompts"
}


def resolve_vault_root() -> Path:
    """Risolve il percorso assoluto della cartella principale dell'Obsidian Vault."""
    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        if (parent / ".obsidian").exists() or (parent / ".antigravity").exists():
            return parent
    return script_path.parents[2]


def tokenize(text: str) -> List[str]:
    """Tokenizza il testo in token normalizzati in minuscolo, escludendo stopwords e simboli."""
    raw_tokens = re.findall(r"\b[a-zA-Z0-9_\u00C0-\u017F-]{2,}\b", text.lower())
    clean_tokens: List[str] = []
    for tok in raw_tokens:
        tok_stripped = tok.strip("-_")
        if len(tok_stripped) >= 2 and tok_stripped not in STOPWORDS and not tok_stripped.isdigit():
            clean_tokens.append(tok_stripped)
    return clean_tokens


def clean_preview_text(raw_text: str, max_chars: int = 240) -> str:
    """Estrae le prime due frasi pulite di un testo, rimuovendo sintassi Markdown pesante."""
    # Rimuovi callout e citazioni
    clean = re.sub(r"^>.*$", "", raw_text, flags=re.MULTILINE)
    # Rimuovi blocchi di formule LaTeX
    clean = re.sub(r"\$\$[\s\S]*?\$\$", " [formula] ", clean)
    clean = re.sub(r"\$[^$\n]+\$", " [simbolo] ", clean)
    # Rimuovi immagini ed embed
    clean = re.sub(r"!\[\[.*?\]\]", "", clean)
    clean = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", clean)
    # Rimuovi markup markdown
    clean = re.sub(r"[#*_`~|]", " ", clean)
    # Normalizza spazi
    clean = " ".join(clean.split())
    if not clean:
        return ""

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if len(s.strip()) > 8]
    if len(sentences) >= 2:
        preview = f"{sentences[0]} {sentences[1]}"
    elif len(sentences) == 1:
        preview = sentences[0]
    else:
        preview = clean

    if len(preview) > max_chars:
        preview = preview[:max_chars].rstrip() + "..."
    return preview


def slugify_block_id(text: str) -> str:
    """Genera uno slug pulito in kebab-case per identificatori di blocco semantici."""
    clean = re.sub(r"[^\w\s-]", "", text).strip().lower()
    slug = re.sub(r"[-\s]+", "-", clean)
    return slug[:45] if slug else "block-id"


# ==============================================================================
# 1. PARSER DEL SINGOLO FILE MARKDOWN (3 LIVELLI)
# ==============================================================================

def parse_markdown_file_detailed(fpath: Path, vault_root: Path) -> Optional[Dict[str, Any]]:
    """
    Analizza approfonditamente un file markdown ed estrae la struttura a 3 livelli:
    1. Livello 1: Note metadata & sintesi
    2. Livello 2: Singoli paragrafi/sottosezioni (H2, H3, H4)
    3. Livello 3: Callout principali e blocchi identificati con ^id-blocco
    """
    try:
        content = fpath.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        sys.stderr.write(f"[ParagraphLinker] Errore lettura {fpath.name}: {e}\n")
        return None

    try:
        rel_path = str(fpath.relative_to(vault_root))
    except ValueError:
        rel_path = str(fpath)

    note_title = fpath.stem

    # 1. Estrazione Frontmatter YAML
    meta: Dict[str, Any] = {
        "disciplina": "",
        "type": [],
        "tags": [],
        "aliases": []
    }
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

    # Fallback per disciplina da cartella genitore
    if not meta["disciplina"]:
        parts = Path(rel_path).parts
        if len(parts) > 1:
            meta["disciplina"] = parts[0]

    # Intro summary (prime 300 parole pulite del testo prima del primo header)
    heading_pattern = re.compile(r"^(#{2,4})\s+(.+)$", re.MULTILINE)
    first_heading_match = heading_pattern.search(body)
    pre_heading_text = body[:first_heading_match.start()] if first_heading_match else body
    intro_words = clean_preview_text(pre_heading_text, max_chars=800)

    # 2. Estrazione Sezioni H2, H3, H4 (Livello 2)
    heading_matches = list(heading_pattern.finditer(body))
    sections: List[Dict[str, Any]] = []
    blocks: List[Dict[str, Any]] = []

    for idx, match in enumerate(heading_matches):
        h_level = len(match.group(1))
        h_exact = match.group(2).strip()
        start_pos = match.end()
        end_pos = heading_matches[idx + 1].start() if idx + 1 < len(heading_matches) else len(body)
        sec_text = body[start_pos:end_pos].strip()

        # Termini in grassetto (keywords)
        raw_bolds = re.findall(r"\*\*([^*]+)\*\*", sec_text)
        keywords: List[str] = []
        for b in raw_bolds:
            clean_b = b.strip()
            if 2 < len(clean_b) < 60 and clean_b not in keywords and not clean_b.startswith("[!"):
                keywords.append(clean_b)

        # Callouts presenti nel paragrafo
        callout_matches = list(re.finditer(r"^>\s*\[!([a-zA-Z0-9_-]+)\][+-]?\s*(.*)$", sec_text, re.MULTILINE))
        callout_titles: List[str] = []
        for cm in callout_matches:
            c_type = cm.group(1).lower()
            c_title = cm.group(2).strip() or c_type.capitalize()
            callout_titles.append(f"{c_type}: {c_title}")

            # Estrazione del corpo del callout
            c_start = cm.start()
            c_lines: List[str] = []
            for line in sec_text[c_start:].splitlines():
                if line.startswith(">"):
                    c_lines.append(line[1:].strip())
                elif not line.strip() and c_lines:
                    # Linea vuota nel callout
                    continue
                elif c_lines:
                    break

            c_body = " ".join(c_lines)

            # Controllo se ha già un block ID esplicito (^id)
            block_id_match = re.search(r"\^([a-zA-Z0-9_-]+)\s*$", c_body)
            explicit_id = False
            if block_id_match:
                block_id = block_id_match.group(1)
                explicit_id = True
            else:
                block_id = slugify_block_id(f"{c_type}-{c_title}")

            c_preview = clean_preview_text(c_body, max_chars=180) or c_title

            blocks.append({
                "note_title": note_title,
                "path": rel_path,
                "disciplina": meta["disciplina"],
                "type": "callout",
                "callout_tag": c_type,
                "title": c_title,
                "block_id": block_id,
                "is_explicit_id": explicit_id,
                "obsidian_link": f"[[{note_title}#^{block_id}|",
                "parent_heading": h_exact,
                "preview": c_preview,
                "full_text": c_body,
                "tokens": tokenize(f"{c_title} {c_preview} {h_exact}")
            })

        # Ricerca di blocchi semantici non-callout che terminano con ^id-blocco
        for line in sec_text.splitlines():
            m_id = re.search(r"\^([a-zA-Z0-9_-]+)\s*$", line.strip())
            if m_id and not line.strip().startswith(">"):
                b_id = m_id.group(1)
                b_text = re.sub(r"\^" + re.escape(b_id) + r"\s*$", "", line).strip()
                b_prev = clean_preview_text(b_text, max_chars=160) or b_id
                blocks.append({
                    "note_title": note_title,
                    "path": rel_path,
                    "disciplina": meta["disciplina"],
                    "type": "block_id",
                    "callout_tag": "block",
                    "title": f"Blocco {b_id}",
                    "block_id": b_id,
                    "is_explicit_id": True,
                    "obsidian_link": f"[[{note_title}#^{b_id}|",
                    "parent_heading": h_exact,
                    "preview": b_prev,
                    "full_text": b_text,
                    "tokens": tokenize(f"{b_id} {b_prev} {h_exact}")
                })

        # Preview prime due frasi del paragrafo
        sec_preview = clean_preview_text(sec_text, max_chars=260)

        # Token per ranking BM25
        sec_token_source = f"{h_exact} {' '.join(keywords)} {' '.join(callout_titles)} {sec_text[:1200]}"
        sec_tokens = tokenize(sec_token_source)

        sections.append({
            "note_title": note_title,
            "path": rel_path,
            "disciplina": meta["disciplina"],
            "heading_level": h_level,
            "heading_exact": h_exact,
            "obsidian_link": f"[[{note_title}#{h_exact}|",
            "keywords": keywords[:10],
            "callout_titles": callout_titles[:6],
            "preview": sec_preview,
            "full_text": sec_text,
            "tokens": sec_tokens
        })

    # Token per la nota intera (Livello 1)
    all_headings_text = " ".join([s["heading_exact"] for s in sections])
    all_keywords_text = " ".join([" ".join(s["keywords"]) for s in sections])
    note_tokens = tokenize(f"{note_title} {' '.join(meta.get('aliases', []))} {meta['disciplina']} {intro_words} {all_headings_text} {all_keywords_text}")

    note_data = {
        "note_title": note_title,
        "path": rel_path,
        "disciplina": meta["disciplina"],
        "type": meta.get("type", []),
        "aliases": meta.get("aliases", []),
        "tags": meta.get("tags", []),
        "intro_summary": intro_words,
        "sections_count": len(sections),
        "blocks_count": len(blocks),
        "sections": sections,
        "blocks": blocks,
        "tokens": note_tokens
    }

    return note_data


# ==============================================================================
# 2. COSTRUZIONE INDICE GLOBALE (paragraph-index.json)
# ==============================================================================

def build_paragraph_index(vault_root: Path, out_path: Optional[Path] = None) -> Dict[str, Any]:
    """Scansiona tutti i file Markdown del vault e genera .antigravity/paragraph-index.json."""
    start_time = time.time()
    notes_data: List[Dict[str, Any]] = []

    total_sections = 0
    total_blocks = 0

    for fpath in sorted(vault_root.rglob("*.md")):
        try:
            rel = fpath.relative_to(vault_root)
        except ValueError:
            continue

        parts = rel.parts
        if any(part in IGNORED_VAULT_DIRS or part.startswith(".") for part in parts):
            continue

        parsed = parse_markdown_file_detailed(fpath, vault_root)
        if parsed:
            notes_data.append(parsed)
            total_sections += parsed["sections_count"]
            total_blocks += parsed["blocks_count"]

    index_bundle: Dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_notes": len(notes_data),
        "total_sections": total_sections,
        "total_blocks": total_blocks,
        "notes": notes_data
    }

    if out_path is None:
        out_path = vault_root / ".antigravity" / "paragraph-index.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(index_bundle, indent=2, ensure_ascii=False), encoding="utf-8")

    elapsed = time.time() - start_time
    sys.stderr.write(
        f"[ParagraphLinker] Indice generato in {elapsed:.2f}s: "
        f"{len(notes_data)} note, {total_sections} sezioni, {total_blocks} blocchi/callout -> {out_path}\n"
    )

    return index_bundle


def load_or_build_paragraph_index(vault_root: Path, index_path: Optional[Path] = None, force_rebuild: bool = False) -> Dict[str, Any]:
    """Carica l'indice esistente o lo costruisce se assente o se richiesto."""
    if index_path is None:
        index_path = vault_root / ".antigravity" / "paragraph-index.json"

    if not force_rebuild and index_path.exists():
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
            if "notes" in data and len(data["notes"]) > 0:
                return data
        except Exception:
            pass

    return build_paragraph_index(vault_root, index_path)


# ==============================================================================
# 3. ALGORITMO BM25 RANKING + EXACT MATCH BOOSTING
# ==============================================================================

class BM25Ranker:
    """Implementazione standard BM25 senza dipendenze per scoring ad alta velocità."""

    def __init__(self, doc_tokens_list: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.N = len(doc_tokens_list)
        self.doc_lens = [len(tokens) for tokens in doc_tokens_list]
        self.avgdl = sum(self.doc_lens) / self.N if self.N > 0 else 1.0

        # Conteggio frequenza dei documenti per ciascun termine (DF)
        self.df: Dict[str, int] = collections.defaultdict(int)
        self.doc_tfs: List[Dict[str, int]] = []

        for tokens in doc_tokens_list:
            tf = collections.Counter(tokens)
            self.doc_tfs.append(tf)
            for term in tf.keys():
                self.df[term] += 1

        # Calcolo IDF probabilistico con smoothing standard
        self.idf: Dict[str, float] = {}
        for term, freq in self.df.items():
            self.idf[term] = math.log(((self.N - freq + 0.5) / (freq + 0.5)) + 1.0)

    def score(self, query_tokens: List[str], doc_idx: int) -> float:
        """Calcola lo score BM25 tra una query e un documento specificato per indice."""
        if doc_idx >= self.N:
            return 0.0

        doc_len = self.doc_lens[doc_idx]
        tf_dict = self.doc_tfs[doc_idx]
        total_score = 0.0

        len_norm = 1.0 - self.b + self.b * (doc_len / self.avgdl)

        for q in query_tokens:
            if q not in tf_dict:
                continue
            f = tf_dict[q]
            term_idf = self.idf.get(q, 0.0)
            numerator = f * (self.k1 + 1.0)
            denominator = f + self.k1 * len_norm
            total_score += term_idf * (numerator / denominator)

        return total_score


# ==============================================================================
# 4. MOTORE DI RACCOMANDAZIONE LINK MIRATI
# ==============================================================================

def recommend_links(
    vault_root: Path,
    topic: str,
    discipline: str,
    query_text: str,
    index_data: Optional[Dict[str, Any]] = None,
    top_sections: int = 25,
    top_blocks: int = 15,
    top_notes: int = 15,
) -> Dict[str, Any]:
    """
    Calcola tramite BM25 + Exact Match i collegamenti più rilevanti nel vault:
    - Tabella A: 25 sottoparagrafi specifici ([[Nota#Paragrafo|testo]])
    - Tabella B: 15 callout / blocchi (^id-blocco)
    - Tabella C: 15 note intere e MOC
    """
    if index_data is None:
        index_data = load_or_build_paragraph_index(vault_root)

    notes = index_data.get("notes", [])
    if not notes:
        return {"sections": [], "blocks": [], "notes": []}

    # Normalizzazione query e pesatura termini del topic
    topic_tokens = tokenize(topic)
    query_body_tokens = tokenize(query_text[:18000])

    # Unisci i token dando peso raddoppiato ai termini del topic
    combined_query_tokens = (topic_tokens * 3) + query_body_tokens
    query_token_set = set(combined_query_tokens)

    # Termini salienti per exact matching (parole > 3 caratteri)
    exact_match_terms = set(topic_tokens + [t for t in query_body_tokens if len(t) > 3][:60])

    topic_lower = topic.strip().lower()
    disc_lower = discipline.strip().lower()

    # -------------------------------------------------------------
    # A. RANKING LIVELLO 2: SINGOLI PARAGRAFI / SOTTOSEZIONI
    # -------------------------------------------------------------
    all_sections: List[Dict[str, Any]] = []
    for note in notes:
        # Escludi auto-riferimenti alla nota stessa se il titolo coincide esattamente
        if note["note_title"].strip().lower() == topic_lower:
            continue
        for sec in note.get("sections", []):
            all_sections.append(sec)

    sec_tokens_list = [s.get("tokens", []) for s in all_sections]
    sec_ranker = BM25Ranker(sec_tokens_list)

    scored_sections: List[Tuple[float, Dict[str, Any]]] = []
    for idx, sec in enumerate(all_sections):
        bm25_score = sec_ranker.score(combined_query_tokens, idx)
        boost = 0.0

        heading_lower = sec["heading_exact"].lower()
        # Boost per corrispondenza esatta di termini chiave nell'header
        for term in exact_match_terms:
            if term in heading_lower:
                boost += 3.5

        # Boost per termini in grassetto
        for kw in sec.get("keywords", []):
            kw_low = kw.lower()
            if any(t in kw_low for t in topic_tokens):
                boost += 2.5
            elif any(t in kw_low for t in exact_match_terms):
                boost += 1.0

        # Boost per titoli callout
        for ct in sec.get("callout_titles", []):
            ct_low = ct.lower()
            if any(t in ct_low for t in topic_tokens):
                boost += 2.0

        # Boost disciplina coincidente
        sec_disc = sec.get("disciplina", "").lower()
        if disc_lower and (disc_lower in sec_disc or sec_disc in disc_lower):
            boost += 2.0

        total_score = bm25_score + boost
        if total_score > 1.2:
            sec_copy = dict(sec)
            sec_copy["score"] = total_score
            scored_sections.append((total_score, sec_copy))

    scored_sections.sort(key=lambda x: x[0], reverse=True)
    selected_sections = [s[1] for s in scored_sections[:top_sections]]

    # -------------------------------------------------------------
    # B. RANKING LIVELLO 3: SINGOLI CALLOUT E BLOCCHI (^id-blocco)
    # -------------------------------------------------------------
    all_blocks: List[Dict[str, Any]] = []
    for note in notes:
        if note["note_title"].strip().lower() == topic_lower:
            continue
        for blk in note.get("blocks", []):
            all_blocks.append(blk)

    blk_tokens_list = [b.get("tokens", []) for b in all_blocks]
    blk_ranker = BM25Ranker(blk_tokens_list)

    scored_blocks: List[Tuple[float, Dict[str, Any]]] = []
    for idx, blk in enumerate(all_blocks):
        bm25_score = blk_ranker.score(combined_query_tokens, idx)
        boost = 0.0

        title_lower = blk["title"].lower()
        for term in exact_match_terms:
            if term in title_lower:
                boost += 3.0

        # Boost per callout con ID già esplicito nel file
        if blk.get("is_explicit_id"):
            boost += 1.5

        # Boost per tipologie nobili (theorem, definition, decodifica)
        c_tag = blk.get("callout_tag", "").lower()
        if c_tag in ["theorem", "teorema", "definition", "definizione"]:
            boost += 2.5
        elif "decodifica" in title_lower:
            boost += 2.0

        # Boost disciplina
        blk_disc = blk.get("disciplina", "").lower()
        if disc_lower and (disc_lower in blk_disc or blk_disc in disc_lower):
            boost += 1.5

        total_score = bm25_score + boost
        if total_score > 1.0:
            blk_copy = dict(blk)
            blk_copy["score"] = total_score
            scored_blocks.append((total_score, blk_copy))

    scored_blocks.sort(key=lambda x: x[0], reverse=True)
    selected_blocks = [b[1] for b in scored_blocks[:top_blocks]]

    # -------------------------------------------------------------
    # C. RANKING LIVELLO 1: NOTE INTERE E MOC
    # -------------------------------------------------------------
    eligible_notes = [n for n in notes if n["note_title"].strip().lower() != topic_lower]
    note_tokens_list = [n.get("tokens", []) for n in eligible_notes]
    note_ranker = BM25Ranker(note_tokens_list)

    scored_notes: List[Tuple[float, Dict[str, Any]]] = []
    for idx, n in enumerate(eligible_notes):
        bm25_score = note_ranker.score(combined_query_tokens, idx)
        boost = 0.0

        nt_lower = n["note_title"].lower()
        for term in exact_match_terms:
            if term in nt_lower:
                boost += 4.5

        # Boost alias
        for al in n.get("aliases", []):
            al_low = al.lower()
            if any(t in al_low for t in topic_tokens):
                boost += 3.5

        # Boost se è un MOC affine
        if "moc" in nt_lower:
            if disc_lower and disc_lower in nt_lower:
                boost += 5.0
            else:
                boost += 2.0

        # Boost disciplina
        n_disc = n.get("disciplina", "").lower()
        if disc_lower and (disc_lower in n_disc or n_disc in disc_lower):
            boost += 2.5

        total_score = bm25_score + boost
        if total_score > 1.5:
            n_copy = dict(n)
            n_copy["score"] = total_score
            scored_notes.append((total_score, n_copy))

    scored_notes.sort(key=lambda x: x[0], reverse=True)
    selected_notes = [n[1] for n in scored_notes[:top_notes]]

    # -------------------------------------------------------------
    # D. SELEZIONE DEI 10 PASSAGGI CHIAVE PER CONFLITTI EPISTEMICI
    # -------------------------------------------------------------
    candidate_claims: List[Dict[str, Any]] = []
    seen_refs = set()
    combined_candidates = []
    for score, sec in scored_sections:
        combined_candidates.append((score, "section", sec))
    for score, blk in scored_blocks:
        combined_candidates.append((score, "block", blk))

    combined_candidates.sort(key=lambda x: x[0], reverse=True)

    for score, c_type, item in combined_candidates:
        ref_key = f"{item['note_title']}#{item.get('heading_exact') or item.get('title')}"
        if ref_key in seen_refs:
            continue
        seen_refs.add(ref_key)
        item_copy = dict(item)
        item_copy["score"] = score
        item_copy["claim_type"] = c_type
        candidate_claims.append(item_copy)
        if len(candidate_claims) >= 10:
            break

    return {
        "sections": selected_sections,
        "blocks": selected_blocks,
        "notes": selected_notes,
        "top_claims": candidate_claims,
        "stats": {
            "total_sections_scored": len(scored_sections),
            "total_blocks_scored": len(scored_blocks),
            "total_notes_scored": len(scored_notes),
            "total_claims_selected": len(candidate_claims)
        }
    }


# ==============================================================================
# 5. GENERATORE DEL DOSSIER MARKDOWN (recommended-links.md)
# ==============================================================================

def generate_recommended_links_markdown(
    topic: str,
    discipline: str,
    recommendations: Dict[str, Any]
) -> str:
    """Formatta i collegamenti raccomandati in un dossier markdown strutturato in 3 tabelle."""
    sections = recommendations.get("sections", [])
    blocks = recommendations.get("blocks", [])
    notes = recommendations.get("notes", [])

    lines: List[str] = []
    lines.append("# DOSSIER DEI COLLEGAMENTI CHIRURGICI RACCOMANDATI PER IL VAULT")
    lines.append(f"> **Focus Operativo:** `{topic}` | **Disciplina:** `{discipline}` | **Generato il:** `{time.strftime('%Y-%m-%d %H:%M:%S')}`")
    lines.append(
        "> Questo dossier calcola tramite algoritmo BM25 e exact matching i collegamenti più rilevanti del vault "
        "a tre livelli di granularità (Sottoparagrafi specifici, Singoli Callout/Blocchi semantici, Note intere e MOC). "
        "Usa questi collegamenti esatti all'interno del testo della nota per creare un grafo di conoscenza chirurgico ad altissima precisione.\n"
    )

    # -------------------------------------------------------------
    # TABELLA A: SOTTOPARAGRAFI SPECIFICI
    # -------------------------------------------------------------
    lines.append("## TABELLA A — COLLEGAMENTI CHIRURGICI A PARAGRAFI SPECIFICI ([[Nota#Paragrafo|testo]])")
    lines.append(
        "*I 25 sottoparagrafi più pertinenti nel vault da citare quando tratti una tecnica, una proprietà o un passaggio specifico:*\n"
    )

    if not sections:
        lines.append("*(Nessun paragrafo specifico correlato rilevato nel vault)*\n")
    else:
        lines.append("| # | Sintassi Wikilink da Copiare | Disciplina | Contenuto del Paragrafo / Termini Chiave |")
        lines.append("| :---: | :--- | :--- | :--- |")
        for idx, sec in enumerate(sections, 1):
            link_exact = f"{sec['obsidian_link']}testo nel discorso]]"
            disc_str = f"`{sec.get('disciplina') or 'Generale'}`"
            
            # Sintesi del contenuto
            preview = sec.get("preview") or ""
            kw_list = sec.get("keywords", [])
            kw_str = f" [**Keywords**: {', '.join(kw_list[:4])}]" if kw_list else ""
            summary = (preview + kw_str).replace("|", "\\|")
            if len(summary) > 160:
                summary = summary[:160] + "..."

            lines.append(f"| {idx} | {link_exact} | {disc_str} | {summary} |")
        lines.append("")

    # -------------------------------------------------------------
    # TABELLA B: SINGOLI CALLOUT E TEOREMI (^id-blocco)
    # -------------------------------------------------------------
    lines.append("## TABELLA B — COLLEGAMENTI DIRETTI A SINGOLI CALLOUT / TEOREMI ([[Nota#^id-blocco|testo]])")
    lines.append(
        "*I singoli box, teoremi o blocchi concettuali specifici dotati di identificatore o callout di decodifica:*\n"
    )

    if not blocks:
        lines.append("*(Nessun blocco specifico identificato nel vault)*\n")
    else:
        lines.append("| # | Sintassi Wikilink da Copiare | Tipologia | Titolo / Descrizione Callout | Nota di Provenienza |")
        lines.append("| :---: | :--- | :---: | :--- | :--- |")
        for idx, blk in enumerate(blocks, 1):
            link_exact = f"{blk['obsidian_link']}testo nel discorso]]"
            tag_type = blk.get("callout_tag", "block").upper()
            title_clean = blk.get("title", "").replace("|", "\\|")
            note_link = f"[[{blk['note_title']}]]"

            lines.append(f"| {idx} | {link_exact} | `{tag_type}` | {title_clean} | {note_link} |")
        lines.append("")

    # -------------------------------------------------------------
    # TABELLA C: NOTE INTERE E MOC
    # -------------------------------------------------------------
    lines.append("## TABELLA C — COLLEGAMENTI A NOTE INTERE E MOC ([[Nota|testo]])")
    lines.append(
        "*Le note macro e i MOC di riferimento per contestualizzazione generale e ponti interdisciplinari:*\n"
    )

    if not notes:
        lines.append("*(Nessuna nota macro correlata rilevata nel vault)*\n")
    else:
        lines.append("| # | Sintassi Wikilink da Copiare | Disciplina | Ruolo Architetturale / Sintesi Introduttiva |")
        lines.append("| :---: | :--- | :--- | :--- |")
        for idx, n in enumerate(notes, 1):
            link_exact = f"[[{n['note_title']}|testo nel discorso]]"
            disc_str = f"`{n.get('disciplina') or 'Generale'}`"
            summary = (n.get("intro_summary") or "").replace("|", "\\|")
            if not summary:
                types = ", ".join(n.get("type", []))
                summary = f"Nota di tipo {types}" if types else "Nota del vault"
            if len(summary) > 160:
                summary = summary[:160] + "..."

            lines.append(f"| {idx} | {link_exact} | {disc_str} | {summary} |")
        lines.append("")

    lines.append("---")
    lines.append("### Come utilizzare questo dossier durante la scrittura della nota:")
    lines.append("1. **Quando citi una proprietà o una dimostrazione precisa trattata altrove**, consulta la **Tabella A** e copia il link [[Nota#Paragrafo|nome proprietà]].")
    lines.append("2. **Quando citi un teorema o una definizione formale precisa**, consulta la **Tabella B** e cita il blocco [[Nota#^id-blocco|Teorema]].")
    lines.append("3. **Quando citi l'oggetto complessivo o devi aggiornare il MOC**, consulta la **Tabella C** per il collegamento a livello macro.")
    lines.append("4. **In fondo alla nota**, inserisci la sottosezione `### Riferimenti Puntuali a Paragrafi` elencando i link specifici utilizzati.")
    lines.append("")

    return "\n".join(lines)


# ==============================================================================
# 5.5. GENERATORE TESI PREESISTENTI PER CONTROLLO CONFLITTI EPISTEMICI (existing-vault-claims.md)
# ==============================================================================

def read_section_text_fallback(
    vault_root: Path,
    rel_path: str,
    heading_or_title: str,
    claim_type: str = "section"
) -> str:
    """Legge direttamente dal file della nota la porzione integrale di testo se assente nell'indice."""
    fpath = vault_root / rel_path
    if not fpath.exists():
        return ""
    try:
        content = fpath.read_text(encoding="utf-8", errors="replace")
        if claim_type == "section":
            pattern = re.compile(rf"^(#{2,4})\s+{re.escape(heading_or_title)}\s*$", re.MULTILINE)
            m = pattern.search(content)
            if m:
                level = len(m.group(1))
                start_pos = m.end()
                next_h = re.search(rf"^#{{1,{level}}}\s+", content[start_pos:], re.MULTILINE)
                end_pos = (start_pos + next_h.start()) if next_h else len(content)
                return content[start_pos:end_pos].strip()
        else:
            pattern = re.compile(rf"^>\s*\[![^\]]+\][+-]?\s*{re.escape(heading_or_title)}", re.MULTILINE | re.IGNORECASE)
            m = pattern.search(content)
            if m:
                lines = []
                for line in content[m.start():].splitlines():
                    if line.startswith(">"):
                        lines.append(line)
                    elif lines and not line.strip():
                        continue
                    elif lines:
                        break
                return "\n".join(lines).strip()
    except Exception:
        pass
    return ""


def generate_existing_vault_claims_markdown(
    topic: str,
    discipline: str,
    recommendations: Dict[str, Any],
    vault_root: Path
) -> str:
    """
    Formatta il dossier existing-vault-claims.md con il testo integrale dei 10 paragrafi o callout
    più correlati già presenti nel vault per il controllo delle contraddizioni epistemiche.
    """
    claims = recommendations.get("top_claims", [])
    lines: List[str] = []
    lines.append("# TESI ED EVIDENZE PREESISTENTI NEL VAULT (CONTROLLO CONFLITTI EPISTEMICI)")
    lines.append(f"> **Argomento in Elaborazione:** `{topic}` | **Disciplina:** `{discipline}` | **Generato il:** `{time.strftime('%Y-%m-%d %H:%M:%S')}`")
    lines.append(
        "> Questo dossier raccoglie il **testo integrale dei 10 paragrafi o callout più rilevanti già presenti nel tuo vault** Obsidian.\n"
        "> \n"
        "> ### 🛡️ REGOLA DELLA COSTITUZIONE UNIVERSALE (LEGGE 9 — RILEVAZIONE CONFLITTI EPISTEMICI):\n"
        "> Prima di scrivere la nuova nota o applicare la modifica, **confronta attentamente le tesi della nuova fonte (e degli studi PubMed)** con ciascuno dei passaggi riportati sotto.\n"
        "> Se rilevi una **contraddizione concettuale, una discrepanza nei dati/parametri/dosaggi o un'evoluzione scientifica** rispetto a quanto affermato in una nota precedente:\n"
        "> 1. Inserisci nella nuova nota il callout di avviso esplicito:\n"
        ">    ```markdown\n"
        ">    > [!warning] Conflitto Epistemico / Evoluzione rispetto a [[Nome Nota#Paragrafo]]\n"
        ">    > - **Cosa riporta la nota precedente nel vault**: <Sintesi dell'affermazione precedente>\n"
        ">    > - **Cosa afferma la nuova fonte / letteratura**: <Sintesi della nuova evidenza>\n"
        ">    > - **Risoluzione Critica**: <Spiegazione rigorosa del perché c'è questa differenza (es. contesto diverso, campione diverso, evoluzione degli studi recenti o diverso punto di vista filosofico/economico)>\n"
        ">    ```\n"
        "> 2. Se la nota precedente nel vault conteneva un dato ormai superato (es. in Bodybuilding o Nutrizione), aggiungi una breve nota di rimando anche nella nota precedente per mantenerle coerenti.\n"
    )

    if not claims:
        lines.append("*(Nessun passaggio preesistente sufficientemente correlato rilevato nel vault per questo argomento)*\n")
        return "\n".join(lines)

    for idx, clm in enumerate(claims, 1):
        note_title = clm.get("note_title", "")
        h_exact = clm.get("heading_exact") or clm.get("title", "")
        obs_ref = f"[[{note_title}#{h_exact}]]" if "heading_exact" in clm else f"[[{note_title}#^{clm.get('block_id', '')}]]"
        disc = clm.get("disciplina") or "Generale"
        path_rel = clm.get("path", "")
        score = clm.get("score", 0.0)

        full_text = (clm.get("full_text") or "").strip()
        if not full_text and path_rel:
            full_text = read_section_text_fallback(vault_root, path_rel, h_exact, clm.get("claim_type", "section"))
        if not full_text:
            full_text = clm.get("preview", "*(Testo non disponibile)*")

        lines.append("---")
        lines.append("")
        lines.append(f"### {idx}. {obs_ref}")
        lines.append(f"- **Disciplina:** `{disc}` | **File:** `{path_rel}` | **Score Rilevanza:** `{score:.2f}`")
        lines.append("")
        lines.append(full_text)
        lines.append("")

    return "\n".join(lines)


# ==============================================================================
# 6. CLI ENTRYPOINT
# ==============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Indicizzatore e Motore di Collegamento Chirurgico tra Paragrafi e Blocchi per Obsidian Vault.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--build-index",
        action="store_true",
        help="Forza la ricostruzione dell'indice .antigravity/paragraph-index.json."
    )
    parser.add_argument(
        "--index-file",
        type=str,
        default=None,
        help="Percorso alternativo del file paragraph-index.json."
    )
    parser.add_argument(
        "--query-text",
        type=str,
        default="",
        help="Testo per la ricerca semantica BM25."
    )
    parser.add_argument(
        "--query-file",
        type=str,
        default=None,
        help="Percorso di un file di testo da cui estrarre la query (es. source_content.md)."
    )
    parser.add_argument(
        "--topic",
        type=str,
        default="",
        help="Titolo o argomento principale della nota/job."
    )
    parser.add_argument(
        "--discipline",
        type=str,
        default="",
        help="Disciplina della nota/job."
    )
    parser.add_argument(
        "--out-md",
        type=str,
        default=None,
        help="Percorso del file markdown in cui salvare il dossier dei collegamenti raccomandati."
    )
    parser.add_argument(
        "--out-claims",
        type=str,
        default=None,
        help="Percorso del file markdown in cui salvare le tesi preesistenti per il controllo conflitti epistemici."
    )
    parser.add_argument(
        "--out-json",
        type=str,
        default=None,
        help="Percorso opzionale per salvare i collegamenti raccomandati in formato JSON."
    )
    parser.add_argument(
        "--top-sections",
        type=int,
        default=25,
        help="Numero di sottoparagrafi da estrarre per la Tabella A."
    )
    parser.add_argument(
        "--top-blocks",
        type=int,
        default=15,
        help="Numero di callout/blocchi da estrarre per la Tabella B."
    )
    parser.add_argument(
        "--top-notes",
        type=int,
        default=15,
        help="Numero di note macro da estrarre per la Tabella C."
    )

    args = parser.parse_args()

    vault_root = resolve_vault_root()
    antigravity_dir = vault_root / ".antigravity"
    runtime_dir = Path(os.environ.get("ANTIGRAVITY_RUNTIME_DIR") or "/tmp/antigravity_runtime")
    runtime_dir.mkdir(parents=True, exist_ok=True)
    index_file = Path(args.index_file).resolve() if args.index_file else runtime_dir / "paragraph-index.json"

    # 1. Costruzione o caricamento indice
    if args.build_index or not index_file.exists():
        index_data = build_paragraph_index(vault_root, index_file)
    else:
        index_data = load_or_build_paragraph_index(vault_root, index_file, force_rebuild=False)

    # Se non è stata passata alcuna query e non è richiesto output, termina con statistiche
    query_text = args.query_text
    if args.query_file:
        q_path = Path(args.query_file).resolve()
        if q_path.exists():
            try:
                query_text = f"{query_text}\n{q_path.read_text(encoding='utf-8', errors='replace')}"
            except Exception as e:
                sys.stderr.write(f"[ParagraphLinker] Errore lettura query-file {q_path}: {e}\n")

    topic = args.topic.strip()
    discipline = args.discipline.strip()

    if not query_text.strip() and not topic:
        print(f"✅ Indice del vault verificato: {index_data.get('total_notes')} note, {index_data.get('total_sections')} paragrafi, {index_data.get('total_blocks')} blocchi/callout.")
        print(f"📁 Salvato in: {index_file}")
        return 0

    # 2. Esecuzione del Ranking BM25 + Match Chirurgico
    recom = recommend_links(
        vault_root=vault_root,
        topic=topic,
        discipline=discipline,
        query_text=query_text,
        index_data=index_data,
        top_sections=args.top_sections,
        top_blocks=args.top_blocks,
        top_notes=args.top_notes,
    )

    # 3. Generazione e Salvataggio del Dossier Markdown (Collegamenti Raccomandati)
    md_content = generate_recommended_links_markdown(
        topic=topic or "Senza Titolo",
        discipline=discipline or "Generale",
        recommendations=recom
    )

    out_md_path = Path(args.out_md).resolve() if args.out_md else runtime_dir / "job-context" / "recommended-links.md"
    out_md_path.parent.mkdir(parents=True, exist_ok=True)
    out_md_path.write_text(md_content, encoding="utf-8")
    sys.stderr.write(f"[ParagraphLinker] Dossier collegamenti raccomandati generato in: {out_md_path}\n")

    # 4. Generazione e Salvataggio delle Tesi Preesistenti (Controllo Conflitti Epistemici)
    claims_content = generate_existing_vault_claims_markdown(
        topic=topic or "Senza Titolo",
        discipline=discipline or "Generale",
        recommendations=recom,
        vault_root=vault_root
    )
    out_claims_path = Path(args.out_claims).resolve() if args.out_claims else runtime_dir / "job-context" / "existing-vault-claims.md"
    out_claims_path.parent.mkdir(parents=True, exist_ok=True)
    out_claims_path.write_text(claims_content, encoding="utf-8")
    sys.stderr.write(f"[ParagraphLinker] Tesi preesistenti per controllo conflitti salvate in: {out_claims_path}\n")

    if args.out_json:
        out_json_path = Path(args.out_json).resolve()
        out_json_path.parent.mkdir(parents=True, exist_ok=True)
        out_json_path.write_text(json.dumps(recom, indent=2, ensure_ascii=False), encoding="utf-8")

    top_claims_count = len(recom.get("top_claims", []))
    print(f"✅ Paragraph Linker completato: {len(recom['sections'])} paragrafi (Tab. A), {len(recom['blocks'])} blocchi (Tab. B), {len(recom['notes'])} note (Tab. C), {top_claims_count} tesi preesistenti per controllo epistemico.")
    print(f"📄 Dossier collegamenti salvato in: {out_md_path}")
    print(f"🏛️ Tesi preesistenti salvate in:     {out_claims_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
