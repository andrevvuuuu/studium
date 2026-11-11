"""JATS XML -> Markdown (sezioni con sec-type, tabelle <table-wrap>, supplementari)."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

XLINK = "{http://www.w3.org/1999/xlink}href"


def _t(el: ET.Element | None) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip() if el is not None else ""


def _table_md(tw: ET.Element) -> tuple[str, bool]:
    label, cap = _t(tw.find("label")), _t(tw.find("caption"))
    tbl = tw.find(".//table")
    head = f"**{label}** {cap}".strip()
    if tbl is None:
        return f"{head}\n\n[TABELLA COME IMMAGINE: nessun <table>, richiede OCR o lettura manuale]\n", True
    rows = []
    for tr in tbl.iter("tr"):
        cells = []
        for c in tr:
            if c.tag in ("td", "th"):
                span = int(c.get("colspan", "1") or 1)
                cells += [_t(c).replace("|", "\\|")] + [""] * (span - 1)
        if cells:
            rows.append(cells)
    if not rows:
        return head + "\n", True
    w = max(len(r) for r in rows)
    rows = [r + [""] * (w - len(r)) for r in rows]
    md = [head, "", "| " + " | ".join(rows[0]) + " |", "|" + " --- |" * w]
    md += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(md) + "\n", False


@dataclass
class JatsDoc:
    markdown: str
    has_fulltext: bool
    supplementary: list[str] = field(default_factory=list)
    table_images: int = 0
    meta: dict = field(default_factory=dict)


def parse_jats(xml_bytes: bytes, min_body_chars: int = 3000) -> JatsDoc:
    root = ET.fromstring(xml_bytes)
    art = root if root.tag == "article" else (root.find(".//article") or root)
    body = art.find(".//body")
    meta = {
        "title": _t(art.find(".//article-title")),
        "journal": _t(art.find(".//journal-title")),
        "doi": _t(art.find(".//article-id[@pub-id-type='doi']")),
        "pmid": _t(art.find(".//article-id[@pub-id-type='pmid']")),
        "pmcid": _t(art.find(".//article-id[@pub-id-type='pmc']")),
        "year": _t(art.find(".//pub-date/year")),
    }
    lines: list[str] = []
    table_images = 0
    abstract = art.find(".//abstract")
    if abstract is not None:
        lines += ["## Abstract", "", _t(abstract), ""]
    supp = [m.get(XLINK) or _t(m) for m in art.iter("supplementary-material")]

    def walk(sec: ET.Element, depth: int) -> None:
        nonlocal table_images
        title = _t(sec.find("title")) or (sec.get("sec-type") or "").replace("|", " and ").replace("-", " ").title()
        if title:
            lines.extend(["#" * min(depth + 1, 6) + " " + title, ""])
        for ch in sec:
            if ch.tag == "sec":
                walk(ch, depth + 1)
            elif ch.tag == "p":
                lines.extend([_t(ch), ""])
            elif ch.tag == "table-wrap":
                md, img = _table_md(ch)
                table_images += int(img)
                lines.extend([md, ""])

    chars = 0
    if body is not None:
        for ch in body:
            if ch.tag == "sec":
                walk(ch, 1)
            elif ch.tag == "p":
                lines.extend([_t(ch), ""])
        chars = len(_t(body))
    has_full = body is not None and chars >= min_body_chars     # abstract-only XML NON e' full text
    return JatsDoc("\n".join(lines).strip(), has_full, [s for s in supp if s], table_images, meta)
