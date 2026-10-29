#!/usr/bin/env python3
"""
pdf_extract.py
==============
Estrattore ad alte prestazioni di testo strutturato e grafici/schemi visivi
dai PDF delle lezioni universitarie o articoli accademici tramite PyMuPDF (fitz).

Pensato per la fonte:
    📚 Lezione / File Locali

Funzionalità:
1. Estrazione testo pagina per pagina con separatori espliciti (--- PAGINA X ---).
2. Estrazione immagini raster incorporate ad alta risoluzione.
3. Filtraggio intelligente di icone, loghi e bordi (ignora immagini < 200x200 px).
4. De-duplicazione per xref (evita di risalvare lo stesso logo di ateneo su ogni slide).
5. Nomi file normalizzati per Obsidian: `lezione_<nomepdf>_pagX_figY.<ext>`.
6. Supporto opzionale rendering vettoriale (--render-pages) per diapositive con formule o grafici vettoriali.

Uso CLI:
    python3 pdf_extract.py "percorso/della/lezione.pdf"
    python3 pdf_extract.py "lezione.pdf" --out-dir "$VAULT/allegati" --min-dim 250
    python3 pdf_extract.py "lezione.pdf" --json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        sys.stderr.write("Errore: PyMuPDF non è installato nel Python corrente. Esegui: pip install pymupdf\n")
        sys.exit(1)


def resolve_default_out_dir() -> Path:
    """Risolve la cartella allegati predefinita dell'Obsidian Vault."""
    script_path = Path(__file__).resolve()
    vault_root = script_path.parents[2]
    allegati_dir = vault_root / "allegati"
    if allegati_dir.exists() and allegati_dir.is_dir():
        return allegati_dir
    cwd_allegati = Path.cwd() / "allegati"
    cwd_allegati.mkdir(parents=True, exist_ok=True)
    return cwd_allegati


def sanitize_filename(text: str) -> str:
    """Genera uno slug pulito per il filesystem e i wikilink di Obsidian."""
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text.strip("_")


def extract_pdf_data(
    pdf_path: Path,
    out_dir: Path,
    min_width: int = 200,
    min_height: int = 200,
    render_pages: bool = False,
    dpi: int = 150,
) -> Dict[str, Any]:
    """
    Estrae testo strutturato per pagina e immagini/figure dal file PDF.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"File PDF non trovato: {pdf_path}")

    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_stem = sanitize_filename(pdf_path.stem)
    if not pdf_stem:
        pdf_stem = "lezione"
    pdf_stem = pdf_stem[:45]  # Tronca lo slug per non eccedere la lunghezza del percorso

    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)

    pages_data: List[Dict[str, Any]] = []
    extracted_images: List[Dict[str, Any]] = []
    seen_xrefs: Set[int] = set()

    for page_idx in range(total_pages):
        page_num = page_idx + 1
        page = doc[page_idx]

        # 1. Estrazione testo
        text = page.get_text("text").strip()

        # 2. Estrazione immagini raster incorporate
        image_list = page.get_images(full=True)
        page_images_info: List[Dict[str, Any]] = []
        fig_counter = 1

        for img_info in image_list:
            xref = img_info[0]
            # De-duplica immagini identiche (es. loghi presenti in ogni slide)
            if xref in seen_xrefs:
                continue

            try:
                base_image = doc.extract_image(xref)
            except Exception as e:
                sys.stderr.write(f"[PDF Extract] Errore estrazione xref {xref} pag {page_num}: {e}\n")
                continue

            if not base_image:
                continue

            width = base_image.get("width", 0)
            height = base_image.get("height", 0)
            image_bytes = base_image.get("image", b"")
            ext = base_image.get("ext", "png").lower()
            if ext == "jpeg":
                ext = "jpg"

            # Filtro dimensioni minime (elimina icone, bordi, pallini di elenchi)
            if width < min_width or height < min_height:
                continue

            # Segna come visto per evitare duplicati
            seen_xrefs.add(xref)

            img_filename = f"lezione_{pdf_stem}_pag{page_num:02d}_fig{fig_counter:02d}.{ext}"
            img_path = out_dir / img_filename
            
            # Evita sovrascrittura accidentale
            counter = 1
            while img_path.exists():
                img_filename = f"lezione_{pdf_stem}_pag{page_num:02d}_fig{fig_counter:02d}_{counter}.{ext}"
                img_path = out_dir / img_filename
                counter += 1

            img_path.write_bytes(image_bytes)

            img_record = {
                "page": page_num,
                "figure_index": fig_counter,
                "filename": img_filename,
                "absolute_path": str(img_path.resolve()),
                "wikilink": f"![[{img_filename}]]",
                "width": width,
                "height": height,
                "format": ext,
                "bytes_size": len(image_bytes),
                "type": "raster_embedded",
            }
            extracted_images.append(img_record)
            page_images_info.append(img_record)
            fig_counter += 1

        # 3. Rendering opzionale della pagina (per grafici vettoriali o slide grafiche)
        if render_pages:
            matrix = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            rendered_filename = f"slide_{pdf_stem}_pag{page_num:02d}.png"
            rendered_path = out_dir / rendered_filename
            pix.save(str(rendered_path))

            rendered_record = {
                "page": page_num,
                "figure_index": 0,
                "filename": rendered_filename,
                "absolute_path": str(rendered_path.resolve()),
                "wikilink": f"![[{rendered_filename}]]",
                "width": pix.width,
                "height": pix.height,
                "format": "png",
                "bytes_size": rendered_path.stat().st_size,
                "type": "rendered_page",
            }
            extracted_images.append(rendered_record)
            page_images_info.append(rendered_record)

        pages_data.append({
            "page": page_num,
            "text": text,
            "images": page_images_info,
            "char_count": len(text),
        })

    doc.close()

    return {
        "pdf_file": str(pdf_path.resolve()),
        "pdf_name": pdf_path.name,
        "total_pages": total_pages,
        "total_images_extracted": len(extracted_images),
        "output_directory": str(out_dir.resolve()),
        "images": extracted_images,
        "pages": pages_data,
    }


def format_markdown_output(data: Dict[str, Any], include_text: bool = True) -> str:
    """Formatta i risultati in Markdown ottimizzato per Obsidian e per l'agente."""
    lines: List[str] = []
    lines.append(f"# Estrazione PDF: {data['pdf_name']}")
    lines.append(f"- **Pagine Totali:** {data['total_pages']}")
    lines.append(f"- **Figure / Grafici Estratti:** {data['total_images_extracted']}")
    lines.append(f"- **Cartella Allegati:** `{data['output_directory']}`\n")

    if data["images"]:
        lines.append("## 🖼️ Mappa delle Figure e Schemi Estratti")
        for img in data["images"]:
            lines.append(
                f"- **Pagina {img['page']}** | `{img['filename']}` ({img['width']}x{img['height']} px, {img['type']}): `{img['wikilink']}`"
            )
        lines.append("")

    if include_text:
        lines.append("## 📝 Contenuto Strutturato delle Pagine")
        for p in data["pages"]:
            lines.append(f"\n--- PAGINA {p['page']} ---")
            if p["images"]:
                lines.append(f"> [!INFO] Figure trovate a pagina {p['page']}: " + ", ".join(f"`{im['filename']}`" for im in p["images"]))
                for im in p["images"]:
                    lines.append(f"{im['wikilink']}")
            if p["text"]:
                lines.append(p["text"])
            else:
                lines.append("*(Nessun testo rilevato in questa pagina)*")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Estrae testo strutturato e grafici salienti da PDF universitari per Obsidian.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("pdf_path", type=str, help="Percorso del file PDF da analizzare.")
    parser.add_argument(
        "--out-dir",
        "-o",
        type=str,
        default=None,
        help="Cartella di destinazione per salvare le immagini (default: cartella allegati del Vault).",
    )
    parser.add_argument(
        "--min-dim",
        type=int,
        default=200,
        help="Dimensione minima in pixel (larghezza e altezza) per filtrare icone e loghi.",
    )
    parser.add_argument(
        "--render-pages",
        action="store_true",
        help="Effettua anche il rendering ad alta risoluzione (150 DPI) dell'intera pagina (utile per slide piene di vettori/formule).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="DPI per il rendering delle intere pagine quando --render-pages è attivo.",
    )
    parser.add_argument(
        "--no-text",
        action="store_true",
        help="Esclude il corpo del testo nell'output stampato a terminale (mostra solo l'elenco dei grafici estratti).",
    )
    parser.add_argument(
        "--save-text",
        type=str,
        default=None,
        help="Salva l'intero testo estratto in un file Markdown separato.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Restituisce il risultato completo in formato JSON.",
    )

    args = parser.parse_args()
    pdf_path = Path(args.pdf_path).resolve()
    if not pdf_path.exists():
        sys.stderr.write(f"Errore: File non trovato: {pdf_path}\n")
        return 1

    out_dir = Path(args.out_dir).resolve() if args.out_dir else resolve_default_out_dir()

    try:
        data = extract_pdf_data(
            pdf_path=pdf_path,
            out_dir=out_dir,
            min_width=args.min_dim,
            min_height=args.min_dim,
            render_pages=args.render_pages,
            dpi=args.dpi,
        )
    except Exception as e:
        sys.stderr.write(f"Errore durante l'elaborazione del PDF: {e}\n")
        return 1

    if args.save_text:
        save_path = Path(args.save_text).resolve()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        full_md = format_markdown_output(data, include_text=True)
        save_path.write_text(full_md, encoding="utf-8")
        sys.stderr.write(f"Testo salvato in: {save_path}\n")

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(format_markdown_output(data, include_text=not args.no_text))

    return 0


if __name__ == "__main__":
    sys.exit(main())
