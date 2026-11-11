"""Segmentazione per sezioni, indipendente dall'ordine, con supplementari e intestazioni run-in."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

_NUM = re.compile(r"^\s*(?:(?:\d+|[ivxlc]+)(?:\.\d+)*[.)]?|[A-Z][.)])\s+", re.I)
_MD_HEAD = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_RUN_IN = re.compile(r"^\s*(?:\*\*|__)\s*([^*_\n]{3,70}?)\s*[.:]?\s*(?:\*\*|__)\s*[.:]?\s+(\S.*)$")

# classe -> regex sul testo NORMALIZZATO (casefold, senza numerazione/punteggiatura)
_CLASSES: list[tuple[str, re.Pattern[str]]] = [
    ("supplement", re.compile(r"^(supplement\w*( \w+)?|supporting information|additional files?|online resources?|extended data|appendix( \w+)?)$")),
    ("results_discussion", re.compile(r"^results (and|&) discussion$")),
    ("methods", re.compile(r"^((materials|subjects|patients|participants) (and|&) methods?|methods? (and|&) materials|methods?|methodology|experimental (procedures?|design)|star methods|online methods|methods summary)$")),
    ("results", re.compile(r"^results?$")),
    ("discussion", re.compile(r"^(discussion|limitations?|strengths? (and|&) limitations?|general discussion)$")),
    ("conclusion", re.compile(r"^(conclusions?|practical applications?|perspectives?)$")),
    ("abstract", re.compile(r"^(abstract|summary)$")),
    ("intro", re.compile(r"^(introduction|background)$")),
    ("noise", re.compile(r"^(acknowledge?ments?|conflicts? of interest|competing interests?|funding|author contributions?|references|literature cited|data availability( statement)?|ethics( statement)?|disclosures?)$")),
]
_SUPP_WORD = re.compile(r"^(supplement\w*|supporting|additional file\w*|online|extended data|appendix)\b")


def normalize_heading(raw: str) -> str:
    s = unicodedata.normalize("NFKC", raw)               # ligature: "ﬁ" -> "fi"
    s = re.sub(r"[*_#`]+", "", s)
    s = re.sub(r"(\w)-\s+(\w)", r"\1\2", s)               # de-sillabazione "meth- ods"
    s = _NUM.sub("", s, count=1)
    s = re.sub(r"[\s:.;,]+$", "", s.casefold())
    return re.sub(r"\s+", " ", s).strip()


def classify_heading(raw: str) -> set[str]:
    """Insieme di etichette (multi-label per 'Results and Discussion'); vuoto se non riconosciuta."""
    n = normalize_heading(raw)
    out: set[str] = set()
    for name, rx in _CLASSES:
        if rx.match(n):
            out |= {"results", "discussion"} if name == "results_discussion" else {name}
            break
    if not out and _SUPP_WORD.match(n):
        out.add("supplement")
    # 'Supplementary Methods' -> supplement + methods (testo metodologico nel supplemento)
    if "supplement" in out and re.search(r"\bmethods?\b", n):
        out.add("methods")
    return out


def heading_level(raw_line: str, md_hashes: Optional[int]) -> int:
    if md_hashes:
        return md_hashes
    m = re.match(r"^\s*(\d+(?:\.\d+)*)", raw_line)
    return m.group(1).count(".") + 1 if m else 1


@dataclass
class Segmented:
    sections: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


def _is_heading(line: str) -> Optional[tuple[int, str]]:
    s = line.strip()
    if not s:
        return None
    m = _MD_HEAD.match(s)
    if m:
        return len(m.group(1)), m.group(2)
    if len(s) <= 70 and not s.endswith((".", ",")) and classify_heading(s) and (s.isupper() or _NUM.match(s) or len(s.split()) <= 4):
        return heading_level(s, None), s
    return None


def segment(markdown: str) -> Segmented:
    buf: dict[str, list[str]] = {k: [] for k in ("methods", "results", "discussion", "methods_supplement", "supplement_other")}
    cur: set[str] = set()
    cur_level = 0
    supp_level: Optional[int] = None
    flags: list[str] = []

    def key_for(cls: set[str], in_supp: bool) -> list[str]:
        keys = []
        for c in cls & {"methods", "results", "discussion"}:
            keys.append("methods_supplement" if (in_supp and c == "methods") else ("supplement_other" if in_supp else c))
        if in_supp and "supplement" in cls and not keys:
            keys.append("supplement_other")
        return keys

    for line in markdown.splitlines():
        h = _is_heading(line)
        rest: Optional[str] = None
        if h is None:
            m = _RUN_IN.match(line)
            if m and classify_heading(m.group(1)):
                lvl = (cur_level + 1) if cur else 3
                h, rest = (lvl, m.group(1)), m.group(2)
                flags.append(f"run_in:{normalize_heading(m.group(1))}")
        if h is not None:
            level, text = h
            cls = classify_heading(text)
            if supp_level is not None and level <= supp_level and "supplement" not in cls:
                supp_level = None
            if "supplement" in cls and supp_level is None:
                supp_level = level
            if "noise" in cls:
                cur, cur_level = set(), level
            elif cls:
                cur, cur_level = cls, level
            elif cur and level > cur_level:
                pass                                   # sotto-sezione: eredita il contesto
            else:
                cur, cur_level = set(), level
            if rest is not None:
                for k in key_for(cur, supp_level is not None):
                    buf[k].append(rest)
            continue
        for k in key_for(cur, supp_level is not None):
            buf[k].append(line)

    sections = {k: "\n".join(v).strip() for k, v in buf.items() if "\n".join(v).strip()}
    missing = [k for k in ("methods", "results") if k not in sections]
    if "methods" not in sections and "methods_supplement" in sections:
        flags.append("methods_only_in_supplement")
    if "methods" in missing and "methods_supplement" not in sections:
        flags.append("methods_unavailable_do_not_infer")
    return Segmented(sections=sections, missing=missing, flags=flags)


def bold_lead_ins_from_pdf(pdf_path: str, max_pages: int = 30) -> list[str]:
    """Rileva intestazioni run-in dai FLAG DI STILE del PDF (PyMuPDF), perche' il Markdown perde il grassetto.
    NON TESTATO su corpus reali: restituisce righe 'Etichetta. testo' da re-iniettare prima di segment()."""
    import fitz  # PyMuPDF

    out: list[str] = []
    with fitz.open(pdf_path) as doc:
        for page in list(doc)[:max_pages]:
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    spans = line["spans"]
                    if not spans or not (spans[0]["flags"] & 16):      # bit 16 = bold in PyMuPDF
                        continue
                    lead = spans[0]["text"].strip().rstrip(".:")
                    if 3 <= len(lead) <= 70 and classify_heading(lead):
                        rest = "".join(s["text"] for s in spans[1:]).strip()
                        out.append(f"**{lead}.** {rest}")
    return out
