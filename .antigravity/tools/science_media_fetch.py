#!/usr/bin/env python3
"""
science_media_fetch.py
======================
Downloader di strutture molecolari 2D (PubChem PUG-REST) e immagini cliniche/scientifiche
ad alta risoluzione (Wikimedia Commons API) per il vault Obsidian.

Pensato per le discipline:
- Droghe / Farmacologia
- Chimica
- Biologia
- Neuroscienze / Medicina

Uso CLI:
    python3 science_media_fetch.py --molecule "MDMA" --out-dir "$VAULT/allegati"
    python3 science_media_fetch.py --search "mydriasis" --max-images 3
    python3 science_media_fetch.py --molecule "LSD" --search "serotonin synapse" --json
"""

import argparse
import html
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

USER_AGENT = "AntigravityObsidianBot/1.0 (macOS; +https://github.com/andrevvuuuu/studium) Python-requests/2.31"
REQUEST_TIMEOUT = 25


def resolve_default_out_dir() -> Path:
    """Risolve la cartella allegati predefinita dell'Obsidian Vault."""
    script_path = Path(__file__).resolve()
    # Script in: <Vault>/.antigravity/tools/science_media_fetch.py
    # Vault root: script_path.parents[2]
    vault_root = script_path.parents[2]
    allegati_dir = vault_root / "allegati"
    if allegati_dir.exists() and allegati_dir.is_dir():
        return allegati_dir
    # Fallback su cartella allegati nella directory corrente o creata ad hoc
    cwd_allegati = Path.cwd() / "allegati"
    cwd_allegati.mkdir(parents=True, exist_ok=True)
    return cwd_allegati


def sanitize_filename(text: str) -> str:
    """Genera uno slug pulito e sicuro per il filesystem e i wikilink di Obsidian."""
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text.strip("_")


def clean_html(raw_html: str) -> str:
    """Pulisce i tag HTML e converte entità HTML in testo semplice."""
    if not raw_html:
        return ""
    # Sostituisce tag di linea o interruzioni con spazi
    clean = re.sub(r"<br\s*/?>|</p>|</div>", " ", raw_html, flags=re.IGNORECASE)
    # Rimuove tutti i restanti tag HTML
    clean = re.sub(r"<[^<]+?>", "", clean)
    clean = html.unescape(clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def fetch_pubchem_structure(molecule: str, out_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Scarica la struttura chimica 2D ad alta risoluzione da PubChem PUG-REST API
    e recupera le proprietà chimiche salienti (Formula, Peso Molecolare, IUPAC).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = sanitize_filename(molecule)
    dest_filename = f"struttura_chimica_{slug}.png"
    dest_path = out_dir / dest_filename

    encoded_mol = urllib.parse.quote(molecule.strip())
    image_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded_mol}/PNG?image_size=large"
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(image_url, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200 or not resp.content:
            sys.stderr.write(f"[PubChem] Errore download immagine per '{molecule}': HTTP {resp.status_code}\n")
            return None
        
        # Scrivi il file PNG ad alta risoluzione
        dest_path.write_bytes(resp.content)
    except Exception as e:
        sys.stderr.write(f"[PubChem] Eccezione download immagine per '{molecule}': {e}\n")
        return None

    # Recupera metadati molecolari opzionali da PubChem
    prop_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{encoded_mol}/property/MolecularFormula,MolecularWeight,IUPACName/JSON"
    formula = ""
    weight = ""
    iupac = ""
    cid = None

    try:
        p_resp = requests.get(prop_url, headers=headers, timeout=REQUEST_TIMEOUT)
        if p_resp.status_code == 200:
            data = p_resp.json()
            props = data.get("PropertyTable", {}).get("Properties", [{}])[0]
            formula = props.get("MolecularFormula", "")
            weight = str(props.get("MolecularWeight", ""))
            iupac = props.get("IUPACName", "")
            cid = props.get("CID")
    except Exception:
        # Se le proprietà falliscono non interrompiamo il salvataggio della struttura
        pass

    return {
        "molecule": molecule,
        "cid": cid,
        "formula": formula,
        "molecular_weight": weight,
        "iupac_name": iupac,
        "filename": dest_filename,
        "absolute_path": str(dest_path.resolve()),
        "wikilink": f"![[{dest_filename}]]",
        "pubchem_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}" if cid else f"https://pubchem.ncbi.nlm.nih.gov/#query={encoded_mol}",
        "bytes_size": len(resp.content),
    }


def search_wikimedia_commons(
    query: str,
    out_dir: Path,
    max_images: int = 3,
    min_width: int = 300,
    min_height: int = 300,
) -> List[Dict[str, Any]]:
    """
    Cerca e scarica fotografie ed illustrazioni scientifiche reali da Wikimedia Commons API.
    Filtra rigorosamente formati raster validi (.jpg, .jpeg, .png) escludendo icone, logo e SVG.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": USER_AGENT}
    api_url = "https://commons.wikimedia.org/w/api.php"

    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query.strip(),
        "gsrnamespace": 6,  # 6 corrisponde al namespace 'File:' in Wikimedia Commons
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "format": "json",
        "gsrlimit": max(15, max_images * 4),
    }

    try:
        resp = requests.get(api_url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            sys.stderr.write(f"[Wikimedia] Errore ricerca HTTP {resp.status_code}\n")
            return []
        data = resp.json()
    except Exception as e:
        sys.stderr.write(f"[Wikimedia] Eccezione richiesta API: {e}\n")
        return []

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return []

    results: List[Dict[str, Any]] = []
    ignored_keywords = ["icon", "logo", "flag", "banner", "button", "symbol", "stub", "placeholder"]

    for page_id, page_info in pages.items():
        if len(results) >= max_images:
            break

        imageinfo_list = page_info.get("imageinfo", [])
        if not imageinfo_list:
            continue

        info = imageinfo_list[0]
        mime = info.get("mime", "").lower()
        width = info.get("width", 0)
        height = info.get("height", 0)
        file_url = info.get("url", "")
        title = page_info.get("title", "")

        # Filtro MIME e dimensioni minime
        if mime not in ["image/jpeg", "image/png"]:
            continue
        if width < min_width or height < min_height:
            continue

        # Filtro per parole chiave inutili
        title_lower = title.lower()
        if any(kw in title_lower for kw in ignored_keywords):
            continue

        # Determina estensione
        ext = ".png" if mime == "image/png" else ".jpg"
        
        # Estrai nome pulito per il file
        clean_title = re.sub(r"^File:", "", title, flags=re.IGNORECASE)
        clean_title = re.sub(r"\.(jpg|jpeg|png)$", "", clean_title, flags=re.IGNORECASE)
        file_slug = sanitize_filename(clean_title)
        if not file_slug:
            file_slug = f"commons_{page_id}"
        
        # Limita lunghezza nome file
        file_slug = file_slug[:60]
        dest_filename = f"scienza_{file_slug}{ext}"
        dest_path = out_dir / dest_filename

        # Evita conflitti di nome mantenendo unicità
        counter = 1
        while dest_path.exists():
            dest_filename = f"scienza_{file_slug}_{counter}{ext}"
            dest_path = out_dir / dest_filename
            counter += 1

        # Scarica l'immagine
        try:
            dl_resp = requests.get(file_url, headers=headers, timeout=REQUEST_TIMEOUT, stream=True)
            if dl_resp.status_code == 200:
                with open(dest_path, "wb") as f:
                    for chunk in dl_resp.iter_content(chunk_size=16384):
                        if chunk:
                            f.write(chunk)
            else:
                continue
        except Exception as e:
            sys.stderr.write(f"[Wikimedia] Errore download {file_url}: {e}\n")
            continue

        # Estrai metadati descrittivi e licenza
        extmetadata = info.get("extmetadata", {})
        desc_raw = extmetadata.get("ImageDescription", {}).get("value", "")
        if not desc_raw:
            desc_raw = extmetadata.get("ObjectName", {}).get("value", "")
        desc = clean_html(desc_raw)
        
        credit = clean_html(extmetadata.get("Credit", {}).get("value", ""))
        license_name = extmetadata.get("LicenseShortName", {}).get("value", "Wikimedia Commons")

        results.append({
            "title": title,
            "filename": dest_filename,
            "absolute_path": str(dest_path.resolve()),
            "wikilink": f"![[{dest_filename}]]",
            "width": width,
            "height": height,
            "description": desc,
            "credit": credit,
            "license": license_name,
            "source_url": info.get("descriptionurl", file_url),
            "original_file_url": file_url,
            "bytes_size": dest_path.stat().st_size if dest_path.exists() else 0,
        })

    return results


def format_markdown_report(pubchem_data: Optional[Dict[str, Any]], commons_results: List[Dict[str, Any]]) -> str:
    """Genera un report Markdown pronto per essere incorporato o letto dall'agente."""
    lines: List[str] = []
    lines.append("# Media Scientifici Estratti per Obsidian\n")

    if pubchem_data:
        lines.append("## Struttura Molecolare 2D (PubChem)")
        lines.append(f"- **Molecola:** `{pubchem_data['molecule']}`")
        if pubchem_data.get("formula"):
            lines.append(f"- **Formula Chimica:** `{pubchem_data['formula']}`")
        if pubchem_data.get("molecular_weight"):
            lines.append(f"- **Peso Molecolare:** `{pubchem_data['molecular_weight']} g/mol`")
        if pubchem_data.get("iupac_name"):
            lines.append(f"- **Nome IUPAC:** `{pubchem_data['iupac_name']}`")
        lines.append(f"- **File Vault:** `{pubchem_data['filename']}`")
        lines.append(f"- **Wikilink Obsidian:** `{pubchem_data['wikilink']}`")
        lines.append(f"- **Percorso Assoluto:** `{pubchem_data['absolute_path']}`")
        lines.append(f"- **Fonte Ufficiale:** [{pubchem_data['pubchem_url']}]({pubchem_data['pubchem_url']})")
        lines.append(f"\n{pubchem_data['wikilink']}\n")

    if commons_results:
        lines.append(f"## Immagini Cliniche e Schemi Scientifici (Wikimedia Commons: {len(commons_results)} trovate)")
        for idx, item in enumerate(commons_results, 1):
            lines.append(f"### {idx}. {item['title']}")
            lines.append(f"- **File Vault:** `{item['filename']}` ({item['width']}x{item['height']} px)")
            lines.append(f"- **Wikilink Obsidian:** `{item['wikilink']}`")
            lines.append(f"- **Percorso Assoluto:** `{item['absolute_path']}`")
            if item.get("description"):
                lines.append(f"- **Descrizione:** {item['description']}")
            if item.get("credit"):
                lines.append(f"- **Autore / Credito:** {item['credit']}")
            lines.append(f"- **Licenza:** {item.get('license', 'Public Domain / CC')}")
            lines.append(f"- **Fonte:** [{item['source_url']}]({item['source_url']})")
            lines.append(f"\n{item['wikilink']}\n")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Downloader di immagini chimico-molecolari e mediche per Obsidian Vault.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--molecule",
        "-m",
        type=str,
        default=None,
        help="Nome in inglese della sostanza o molecola (es. 'MDMA', 'LSD', 'caffeine', 'dopamine').",
    )
    parser.add_argument(
        "--search",
        "-s",
        type=str,
        default=None,
        help="Query di ricerca immagini cliniche o schemi su Wikimedia Commons (es. 'mydriasis', 'serotonin synapse').",
    )
    parser.add_argument(
        "--out-dir",
        "-o",
        type=str,
        default=None,
        help="Cartella di destinazione per salvare le immagini (default: cartella allegati del Vault).",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=3,
        help="Numero massimo di immagini cliniche da scaricare da Wikimedia Commons.",
    )
    parser.add_argument(
        "--min-dim",
        type=int,
        default=300,
        help="Dimensione minima in pixel (larghezza e altezza) per le immagini da Wikimedia Commons.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Restituisce il risultato in formato JSON strutturato.",
    )

    args = parser.parse_args()

    if not args.molecule and not args.search:
        parser.print_help()
        sys.stderr.write("\nErrore: Specificare almeno uno tra --molecule e --search.\n")
        return 1

    out_dir = Path(args.out_dir).resolve() if args.out_dir else resolve_default_out_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    pubchem_res = None
    if args.molecule:
        pubchem_res = fetch_pubchem_structure(args.molecule, out_dir)

    commons_res: List[Dict[str, Any]] = []
    if args.search:
        commons_res = search_wikimedia_commons(
            query=args.search,
            out_dir=out_dir,
            max_images=args.max_images,
            min_width=args.min_dim,
            min_height=args.min_dim,
        )

    if args.json:
        payload = {
            "out_dir": str(out_dir),
            "pubchem": pubchem_res,
            "commons": commons_res,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(format_markdown_report(pubchem_res, commons_res))

    return 0


if __name__ == "__main__":
    sys.exit(main())
