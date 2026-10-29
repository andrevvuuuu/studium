#!/usr/bin/env python3
"""
.antigravity/tools/pubmed_search.py

Motore di ricerca scientifica PubMed Live Evidence tramite API ufficiali NCBI Entrez.
Effettua una doppia ricerca:
  1. Priorità 1 (Gold Standard): Meta-Analysis, Systematic Review, Randomized Controlled Trial.
  2. Priorità 2 (Completamento): Ricerca libera sui paper più rilevanti/recenti.
Estrae abstract strutturati, autori, DOI, rivista, tipo di pubblicazione,
e classifica automaticamente il campione e i metodi di misura sperimentali.
"""

import sys
import os
import json
import re
import argparse
import urllib.parse
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional

try:
    import requests
except ImportError:
    print("ERRORE: La libreria 'requests' non è installata. Esegui: pip3 install requests", file=sys.stderr)
    sys.exit(1)

# Configurazione NCBI Entrez
NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DEFAULT_USER_AGENT = "AntigravityObsidianEngine/1.0 (academic research and evidence synthesis tool)"


def get_headers(custom_agent: Optional[str] = None) -> Dict[str, str]:
    """Restituisce gli header HTTP con User-Agent valido per evitare blocchi NCBI."""
    return {
        "User-Agent": custom_agent or DEFAULT_USER_AGENT,
        "Accept": "application/json, application/xml, text/xml, */*"
    }


def search_pubmed_ids(
    query: str,
    max_results: int = 8,
    years: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """
    Esegue la ricerca a due stadi su esearch.fcgi:
      - Priorità 1: Gold Standard (Meta-Analysis, Systematic Review, RCT)
      - Priorità 2: Ricerca libera per completare la quota se necessario
    Restituisce una lista di tuple o dict con pmid e priorità.
    """
    if headers is None:
        headers = get_headers()

    esearch_url = f"{NCBI_BASE_URL}/esearch.fcgi"

    # Parsing range di anni se presente
    mindate = None
    maxdate = None
    if years:
        if ":" in years:
            parts = years.split(":")
            mindate = parts[0].strip() if parts[0].strip() else None
            maxdate = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
        elif "-" in years:
            parts = years.split("-")
            mindate = parts[0].strip() if parts[0].strip() else None
            maxdate = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
        else:
            mindate = years.strip()

    # 1. Priorità 1: Gold standard filter
    gold_filter = "(Meta-Analysis[pt] OR Systematic Review[pt] OR Randomized Controlled Trial[pt])"
    query_p1 = f"({query}) AND {gold_filter}"

    params_p1: Dict[str, Any] = {
        "db": "pubmed",
        "term": query_p1,
        "retmode": "json",
        "sort": "relevance",
        "retmax": max_results
    }
    if mindate:
        params_p1["mindate"] = mindate
        params_p1["datetype"] = "pdat"
    if maxdate:
        params_p1["maxdate"] = maxdate
        params_p1["datetype"] = "pdat"

    p1_pmids: List[str] = []
    try:
        resp_p1 = requests.get(esearch_url, params=params_p1, headers=headers, timeout=15)
        if resp_p1.status_code == 200:
            data_p1 = resp_p1.json()
            p1_pmids = data_p1.get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"[PubMed Warning] Ricerca Priorità 1 non riuscita: {e}", file=sys.stderr)

    selected: List[Dict[str, Any]] = []
    seen = set()

    for pmid in p1_pmids:
        if pmid not in seen:
            seen.add(pmid)
            selected.append({"pmid": pmid, "priority": "Gold Standard (Meta/Review/RCT)"})

    # 2. Priorità 2: Completamento se mancano risultati
    if len(selected) < max_results:
        needed = max_results - len(selected)
        params_p2: Dict[str, Any] = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "sort": "relevance",
            "retmax": max_results + len(selected)
        }
        if mindate:
            params_p2["mindate"] = mindate
            params_p2["datetype"] = "pdat"
        if maxdate:
            params_p2["maxdate"] = maxdate
            params_p2["datetype"] = "pdat"

        try:
            resp_p2 = requests.get(esearch_url, params=params_p2, headers=headers, timeout=15)
            if resp_p2.status_code == 200:
                data_p2 = resp_p2.json()
                p2_pmids = data_p2.get("esearchresult", {}).get("idlist", [])
                for pmid in p2_pmids:
                    if pmid not in seen:
                        seen.add(pmid)
                        selected.append({"pmid": pmid, "priority": "Primary Literature / Observational"})
                    if len(selected) >= max_results:
                        break
        except Exception as e:
            print(f"[PubMed Warning] Ricerca Priorità 2 non riuscita: {e}", file=sys.stderr)

    return selected[:max_results]


def classify_evidence_tags(title: str, abstract_text: str) -> Dict[str, List[str]]:
    """
    Analizza testo e titolo per determinare la popolazione del campione (trained vs untrained, umano vs animale)
    e le metodiche di misurazione (MRI, Ultrasound, DXA, sEMG, isotopi, biopsia, fMRI, ecc.).
    """
    full_text = f"{title} {abstract_text}".lower()

    # Campione / Popolazione
    sample_tags = []
    if re.search(r"\b(resistance-trained|trained men|trained women|trained individuals|trained subjects|athletes|bodybuilders|powerlifters|elite)\b", full_text):
        sample_tags.append("Trained / Athletes")
    if re.search(r"\b(untrained|recreationally active|sedentary|naive|non-trained|healthy volunteers|healthy young)\b", full_text):
        sample_tags.append("Untrained / Recreationally Active")
    if re.search(r"\b(elderly|older adults|older men|older women|aging|sarcopen)\b", full_text):
        sample_tags.append("Elderly / Aging")
    if re.search(r"\b(rat|rats|mouse|mice|murine|rodent|rodents|swine|rabbit|animal model)\b", full_text):
        sample_tags.append("Animal Model (Rodents)")
    if re.search(r"\b(in vitro|cell culture|myoblasts|c2c12|myotubes)\b", full_text):
        sample_tags.append("In Vitro / Cellular")
    if not sample_tags:
        if re.search(r"\b(men|women|patients|participants|subjects|humans)\b", full_text):
            sample_tags.append("Human (General)")

    # Metodi di misura
    method_tags = []
    if re.search(r"\b(mri|magnetic resonance imaging)\b", full_text):
        method_tags.append("MRI (Gold Standard Volume)")
    if re.search(r"\b(ultrasound|ultrasonography|muscle thickness|pennation angle|fascicle length)\b", full_text):
        method_tags.append("Ultrasound (Muscle Thickness)")
    if re.search(r"\b(dxa|dexa|dual-energy x-ray absorptiometry)\b", full_text):
        method_tags.append("DXA (Lean Mass)")
    if re.search(r"\b(emg|semg|electromyograph|surface electromyography|muscle activity)\b", full_text):
        method_tags.append("sEMG (Neural Activation)")
    if re.search(r"\b(biopsy|muscle biopsy|fiber cross-sectional area|fcsa|cross-sectional area)\b", full_text):
        method_tags.append("Muscle Biopsy (fCSA)")
    if re.search(r"\b(tracer|isotope|fractional synthetic rate|fsr|deuterium|d2o|protein synthesis|mps)\b", full_text):
        method_tags.append("Isotope Tracers / FSR (MPS)")
    if re.search(r"\b(fmri|functional magnetic resonance|pet scan|positron emission|spectroscopy)\b", full_text):
        method_tags.append("Neuroimaging (fMRI/PET)")
    if re.search(r"\b(microdialysis|hplc|chromatography|mass spectrometry)\b", full_text):
        method_tags.append("Analytical Biochemistry / Microdialysis")

    return {
        "sample": sample_tags if sample_tags else ["Not Specified"],
        "methods": method_tags if method_tags else ["Standard Outcome Measures"]
    }


def fetch_pubmed_details(
    pmid_records: List[Dict[str, Any]],
    headers: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """
    Scarica i dettagli completi e l'abstract per ogni PMID usando efetch.fcgi (XML).
    """
    if not pmid_records:
        return []

    if headers is None:
        headers = get_headers()

    pmid_map = {r["pmid"]: r.get("priority", "Standard") for r in pmid_records}
    pmid_list = list(pmid_map.keys())

    efetch_url = f"{NCBI_BASE_URL}/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(pmid_list),
        "retmode": "xml"
    }

    try:
        resp = requests.get(efetch_url, params=params, headers=headers, timeout=25)
        if resp.status_code != 200:
            print(f"[PubMed Error] efetch status {resp.status_code}", file=sys.stderr)
            return []
        xml_content = resp.content
    except Exception as e:
        print(f"[PubMed Error] Chiamata efetch fallita: {e}", file=sys.stderr)
        return []

    results: List[Dict[str, Any]] = []

    try:
        root = ET.fromstring(xml_content)
    except Exception as e:
        print(f"[PubMed Error] Parsing XML fallito: {e}", file=sys.stderr)
        return []

    articles = root.findall(".//PubmedArticle")
    for article in articles:
        # PMID
        pmid_elem = article.find(".//MedlineCitation/PMID")
        pmid = pmid_elem.text.strip() if pmid_elem is not None and pmid_elem.text else ""
        if not pmid:
            continue

        priority = pmid_map.get(pmid, "Standard")

        # Titolo
        title_elem = article.find(".//MedlineCitation/Article/ArticleTitle")
        title = "".join(title_elem.itertext()).strip() if title_elem is not None else "Nessun titolo disponibile"

        # Autori
        author_list_elem = article.findall(".//MedlineCitation/Article/AuthorList/Author")
        authors = []
        for a in author_list_elem:
            last = a.find("LastName")
            fore = a.find("ForeName")
            last_text = last.text.strip() if last is not None and last.text else ""
            fore_text = fore.text.strip() if fore is not None and fore.text else ""
            if last_text and fore_text:
                authors.append(f"{last_text} {fore_text}")
            elif last_text:
                authors.append(last_text)

        if len(authors) > 2:
            first_author_display = f"{authors[0]} et al."
        elif len(authors) == 2:
            first_author_display = f"{authors[0]} & {authors[1]}"
        elif len(authors) == 1:
            first_author_display = authors[0]
        else:
            first_author_display = "Autore non specificato"

        # Anno di pubblicazione
        year = ""
        year_elem = article.find(".//MedlineCitation/Article/Journal/JournalIssue/PubDate/Year")
        if year_elem is not None and year_elem.text:
            year = year_elem.text.strip()
        else:
            art_date = article.find(".//MedlineCitation/Article/ArticleDate/Year")
            if art_date is not None and art_date.text:
                year = art_date.text.strip()
            else:
                medline_date = article.find(".//MedlineCitation/Article/Journal/JournalIssue/PubDate/MedlineDate")
                if medline_date is not None and medline_date.text:
                    m = re.search(r"\b(19\d\d|20\d\d)\b", medline_date.text)
                    if m:
                        year = m.group(1)

        # Rivista
        journal = ""
        journal_elem = article.find(".//MedlineCitation/Article/Journal/Title")
        if journal_elem is not None and journal_elem.text:
            journal = journal_elem.text.strip()
        else:
            iso_elem = article.find(".//MedlineCitation/Article/Journal/ISOAbbreviation")
            if iso_elem is not None and iso_elem.text:
                journal = iso_elem.text.strip()

        # DOI
        doi = ""
        doi_elem = article.find(".//MedlineCitation/Article/ELocationID[@EIdType='doi']")
        if doi_elem is not None and doi_elem.text:
            doi = doi_elem.text.strip()
        else:
            article_id_doi = article.find(".//PubmedData/ArticleIdList/ArticleId[@IdType='doi']")
            if article_id_doi is not None and article_id_doi.text:
                doi = article_id_doi.text.strip()

        # Tipo di pubblicazione
        pub_types = []
        for pt in article.findall(".//MedlineCitation/Article/PublicationTypeList/PublicationType"):
            if pt.text:
                pub_types.append(pt.text.strip())

        # Abstract strutturato
        abstract_sections: Dict[str, str] = {}
        full_abstract_parts: List[str] = []

        abstract_elems = article.findall(".//MedlineCitation/Article/Abstract/AbstractText")
        for ab in abstract_elems:
            label = ab.get("Label") or ab.get("NlmCategory") or ""
            text = "".join(ab.itertext()).strip()
            if not text:
                continue

            if label:
                label_clean = label.strip().capitalize()
                abstract_sections[label_clean] = text
                full_abstract_parts.append(f"**{label_clean}**: {text}")
            else:
                full_abstract_parts.append(text)

        full_abstract = "\n\n".join(full_abstract_parts) if full_abstract_parts else "Nessun abstract disponibile su PubMed."

        # Se non avevamo sezioni con label, controlla se sono nel testo
        if not abstract_sections and full_abstract:
            for sec_name in ["Background", "Methods", "Results", "Conclusions", "Objective", "Discussion"]:
                m = re.search(rf"\b{sec_name}\b\s*:\s*(.*?)(?=(?:Background|Methods|Results|Conclusions|Objective|Discussion)\s*:|$)", full_abstract, re.DOTALL | re.IGNORECASE)
                if m:
                    abstract_sections[sec_name] = m.group(1).strip()

        # Tag di evidenza e classificazione sperimentale
        classifications = classify_evidence_tags(title, full_abstract)

        pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

        results.append({
            "pmid": pmid,
            "title": title,
            "first_author": first_author_display,
            "authors": authors,
            "year": year or "N/D",
            "journal": journal or "N/D",
            "doi": doi or "N/D",
            "url": pubmed_url,
            "priority": priority,
            "publication_types": pub_types,
            "sample_tags": classifications["sample"],
            "methods_tags": classifications["methods"],
            "abstract_structured": abstract_sections,
            "abstract": full_abstract
        })

    # Ordina i risultati per preservare l'ordine di ranking
    ordered_results = []
    found_by_pmid = {r["pmid"]: r for r in results}
    for rec in pmid_records:
        pmid = rec["pmid"]
        if pmid in found_by_pmid:
            ordered_results.append(found_by_pmid[pmid])

    return ordered_results


def format_markdown_output(query: str, results: List[Dict[str, Any]]) -> str:
    """Formatta i risultati in un report Markdown chiaro, rigoroso ed evidenza-centrico."""
    lines = []
    lines.append(f"# 🔬 PubMed Evidence Report: \"{query}\"")
    lines.append(f"**Totale Paper Recuperati:** {len(results)}\n")

    if not results:
        lines.append("> ⚠️ Nessun articolo trovato per i criteri specificati.")
        return "\n".join(lines)

    # Tabella di riepilogo
    lines.append("## 📊 Tabella Sinottica delle Evidenze")
    lines.append("| PMID | Autore / Anno | Tipo Studio | Campione | Metodica di Misura | Titolo |")
    lines.append("|:---:|:---:|:---:|:---:|:---:|:---|")

    for r in results:
        pmid_link = f"[{r['pmid']}]({r['url']})"
        author_year = f"{r['first_author']} ({r['year']})"
        ptype = ", ".join(r["publication_types"][:2]) if r["publication_types"] else r["priority"]
        sample = ", ".join(r["sample_tags"])
        methods = ", ".join(r["methods_tags"])
        title_escaped = r["title"].replace("|", "\\|")
        lines.append(f"| {pmid_link} | {author_year} | {ptype} | {sample} | {methods} | {title_escaped} |")

    lines.append("\n---\n")

    # Schede dettagliate per ciascun articolo
    lines.append("## 📑 Schede Analitiche degli Studi")

    for i, r in enumerate(results, 1):
        lines.append(f"### {i}. {r['title']}")
        lines.append(f"- **Autori:** {', '.join(r['authors'][:5])}{' et al.' if len(r['authors']) > 5 else ''}")
        lines.append(f"- **Rivista & Anno:** *{r['journal']}* ({r['year']})")
        lines.append(f"- **PMID:** [{r['pmid']}]({r['url']}) | **DOI:** {r['doi']}")
        lines.append(f"- **Grado di Evidenza:** `{r['priority']}`")
        lines.append(f"- **Tipologia Pubblicazione:** {', '.join(r['publication_types']) if r['publication_types'] else 'N/D'}")
        lines.append(f"- **Popolazione / Campione:** `{', '.join(r['sample_tags'])}`")
        lines.append(f"- **Metodiche Strumentali:** `{', '.join(r['methods_tags'])}`")
        lines.append("")

        if r["abstract_structured"]:
            lines.append("#### Abstract Strutturato")
            for sec, text in r["abstract_structured"].items():
                lines.append(f"> **{sec}**: {text}\n>")
        else:
            lines.append("#### Abstract")
            for para in r["abstract"].split("\n\n"):
                lines.append(f"> {para}\n>")

        lines.append("\n---\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Motore di ricerca PubMed Live Evidence con doppio stadio e classificazione metodologica."
    )
    parser.add_argument("query", type=str, help="Query di ricerca (es. 'resistance training proximity to failure hypertrophy')")
    parser.add_argument("--max-results", "-n", type=int, default=8, help="Numero massimo di paper da scaricare (default: 8)")
    parser.add_argument("--years", "-y", type=str, default=None, help="Filtro anni, es. '2018:2026' o '2020'")
    parser.add_argument("--json", action="store_true", help="Stampa l'output unicamente come JSON strutturato")
    parser.add_argument("--out-file", "-o", type=str, default=None, help="Salva l'output in un file su disco")

    args = parser.parse_args()

    headers = get_headers()
    pmid_records = search_pubmed_ids(
        query=args.query,
        max_results=args.max_results,
        years=args.years,
        headers=headers
    )

    if not pmid_records:
        if args.json:
            out_str = json.dumps({"query": args.query, "total": 0, "results": []}, indent=2)
        else:
            out_str = f"⚠️ Nessun risultato trovato per la query: '{args.query}'"
        print(out_str)
        if args.out_file:
            with open(args.out_file, "w", encoding="utf-8") as f:
                f.write(out_str)
        return

    detailed_results = fetch_pubmed_details(pmid_records, headers=headers)

    if args.json:
        payload = {
            "query": args.query,
            "years_filter": args.years,
            "total_found": len(detailed_results),
            "results": detailed_results
        }
        output_text = json.dumps(payload, indent=2, ensure_ascii=False)
    else:
        output_text = format_markdown_output(args.query, detailed_results)

    print(output_text)

    if args.out_file:
        with open(args.out_file, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"\n[Info] Output salvato su: {args.out_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
