#!/usr/bin/env python3
"""
diary_sources.py — Lettori dei diari delle lezioni per il tutor (nessuna AI).

Algebra (prof.ssa Malvenuto): una sola lista numerata sul sito del corso. Le lezioni fatte sono solo quelle
sopra la riga "Diario aggiornato fin qui"; sotto resta il diario dell'anno prima, che vale come previsione.
Le date non bastano a separare le due parti (i giorni della settimana coincidono), quindi senza la riga
nessuna lezione è considerata fatta.
"""

import html as html_lib
import re
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

MARKER = "Diario aggiornato fin qui"
MONTHS = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6,
    "luglio": 7, "agosto": 8, "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}
DATE_RE = re.compile(r"(?<!\d)(\d{1,2})\s*°?\s+(" + "|".join(MONTHS) + r")(?:\s+(\d{4}))?", re.I)
ENTRY_RE = re.compile(r"^(\d+)\)\s*(.*)$")
EXAM_RE = re.compile(r"((?:Prima|Seconda|Terza|Quarta|Quinta)\s+prova\s+in\s+itinere|\w+\s+appello)\s*:\s*(\d{1,2}\s*°?\s+\w+\s+\d{4})", re.I)


@dataclass
class Lesson:
    course: str
    date: str
    text: str
    source: str
    number: Optional[int] = None


class DiaryFormatError(Exception):
    pass


def parse_it_date(text: str, start_year: int) -> Optional[str]:
    """Prima data "D mese [AAAA]" del testo (anche "1°", "dell'8"); senza anno, ottobre-dicembre sono
    nell'anno di inizio del corso e gli altri mesi in quello dopo."""
    m = DATE_RE.search(text.replace(" ", " "))
    if not m:
        return None
    day, month = int(m.group(1)), MONTHS[m.group(2).lower()]
    year = int(m.group(3)) if m.group(3) else (start_year if month >= 10 else start_year + 1)
    return f"{year:04d}-{month:02d}-{day:02d}"


def page_lines(page: str) -> List[str]:
    """Testo della pagina, una riga per blocco: i tag inline (span, b, a...) non spezzano le frasi."""
    t = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", "", page)
    t = re.sub(r"</?(span|b|i|strong|em|a|u|font)\b[^>]*>", "", t)
    t = html_lib.unescape(re.sub(r"<[^>]+>", "\n", t)).replace(" ", " ")
    return [re.sub(r"\s+", " ", l).strip() for l in t.splitlines() if l.strip()]


def parse_malvenuto(page: str, course: str, start_year: int) -> Tuple[List[Lesson], List[Lesson], List[Dict[str, str]]]:
    lines = page_lines(page)
    done: List[Lesson] = []
    forecast: List[Lesson] = []
    marker_seen = False
    for line in lines:
        if MARKER.lower() in line.lower():
            marker_seen = True
            continue
        m = ENTRY_RE.match(line)
        if not m:
            continue
        date = parse_it_date(m.group(2), start_year)
        if not date:
            continue
        lesson = Lesson(course=course, date=date, text=m.group(2), source="malvenuto_site", number=int(m.group(1)))
        (forecast if marker_seen else done).append(lesson)
    if not marker_seen:
        raise DiaryFormatError(f"non trovo la riga «{MARKER}» nel diario")
    exams = []
    for line in lines:
        for name, when in EXAM_RE.findall(line):
            date = parse_it_date(when, start_year)
            if date:
                exams.append({"nome": re.sub(r"\s+", " ", name).strip(), "data": date})
    return done, forecast, exams


def read_malvenuto(url: str, course: str, start_year: int) -> Tuple[List[Lesson], List[Lesson], List[Dict[str, str]]]:
    with urllib.request.urlopen(url, timeout=20) as resp:
        page = resp.read().decode("utf-8", errors="replace")
    return parse_malvenuto(page, course, start_year)


# Analisi (prof. Orsina): forum Moodle "Diario delle lezioni", una discussione per lezione ("Lezione del 2 novembre
# 2026"). L'utente è iscritto al forum, i post arrivano nella Gmail della Sapienza e uno Google Apps Script suo
# (Scripts/tutor_gmail.gs) li espone come JSON a un indirizzo segreto. Moodle non dà token agli studenti.

def parse_forum_messages(messages: List[Dict[str, str]], course: str, start_year: int) -> List[Lesson]:
    """Una lezione per data ("Lezione del …" nell'oggetto); per la stessa lezione vale il messaggio più recente."""
    by_date: Dict[str, Tuple[str, Lesson]] = {}
    for msg in messages:
        m = re.search(r"Lezione\s+(?:del|dell'|dello|della)\s*(.*)", msg.get("subject", ""), re.I)
        date = parse_it_date(m.group(1), start_year) if m else None
        body = (msg.get("body") or "").strip()
        if not date or not body:
            continue
        sent = msg.get("date", "")
        if date not in by_date or sent > by_date[date][0]:
            by_date[date] = (sent, Lesson(course=course, date=date, text=body, source="gmail_forum"))
    return [by_date[d][1] for d in sorted(by_date)]


def handle_gmail_response(data, course: str, start_year: int) -> List[Lesson]:
    if isinstance(data, dict) and data.get("error"):
        raise DiaryFormatError(f"Script Google: {data['error']}")
    if not isinstance(data, list):
        raise DiaryFormatError("Script Google: risposta inattesa")
    return parse_forum_messages(data, course, start_year)


def gmail_request_url(secrets: Dict[str, str], corso: str) -> str:
    """Il codice e il nome del corso: lo script Google tiene solo le email di Moodle che citano quel corso."""
    import urllib.parse
    base = secrets["gmail_url"]
    return base + ("&" if "?" in base else "?") + urllib.parse.urlencode({"key": secrets.get("gmail_key", ""), "corso": corso})


def read_gmail_forum(secrets: Dict[str, str], course: str, start_year: int, corso: str = "") -> List[Lesson]:
    import json
    url = gmail_request_url(secrets, corso)
    with urllib.request.urlopen(url, timeout=20) as resp:
        return handle_gmail_response(json.loads(resp.read().decode("utf-8")), course, start_year)
