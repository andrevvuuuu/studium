#!/usr/bin/env python3
"""
moodle_backfill.py — Recupero una tantum del diario delle lezioni da un forum Moodle (lezioni già passate, che
non sono arrivate per email). Nessuna AI.

Apre Chromium (Playwright) con un profilo temporaneo e la finestra visibile: il login lo fa l'utente, lo script
non vede né salva credenziali. Arrivato sulla pagina del forum, legge ogni discussione ("Lezione del …") e la
aggiunge all'archivio del tutor; alla fine cancella il profilo.

Uso: python3 .antigravity/tools/moodle_backfill.py --forum 829741 [--course analisi]
Richiede: python3 -m pip install --user playwright && python3 -m playwright install chromium
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from diary_sources import parse_forum_messages  # noqa: E402
from tutor_store import append_new, load_courses  # noqa: E402

VAULT = Path(__file__).resolve().parents[2]
TUTOR_DIR = VAULT / ".antigravity" / "tutor"
LOGIN_WAIT_MS = 10 * 60 * 1000


def main() -> int:
    ap = argparse.ArgumentParser(description="Recupero una tantum del diario delle lezioni da Moodle.")
    ap.add_argument("--forum", required=True, help="id del forum (mod/forum/view.php?id=…)")
    ap.add_argument("--course", default="analisi")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    course = next(c for c in load_courses(TUTOR_DIR / "courses.json") if c.id == args.course)
    forum_url = f"https://elearning.uniroma1.it/mod/forum/view.php?id={args.forum}"
    profile = Path(tempfile.mkdtemp(prefix="moodle-backfill-"))
    messages = []
    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(str(profile), headless=False)
            page = ctx.new_page()
            page.goto(forum_url)
            print("Fai il login a Moodle nella finestra che si è aperta: lo script aspetta la pagina del forum.")
            page.wait_for_url(lambda u: f"forum/view.php?id={args.forum}" in u, timeout=LOGIN_WAIT_MS)
            page.wait_for_selector('a[href*="discuss.php?d="]', timeout=60000)
            links = {}
            for a in page.locator('a[href*="discuss.php?d="]').all():
                title = a.inner_text().strip()
                if "lezione" in title.lower():
                    links.setdefault(a.get_attribute("href").split("#")[0], title)
            for href, title in links.items():
                page.goto(href)
                body = page.locator(".post-content-container").first.inner_text().strip()
                messages.append({"subject": title, "date": "", "body": body})
                print(f"  {title}")
            ctx.close()
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    lessons = parse_forum_messages(messages, course.id, course.start_year)
    for l in lessons:
        l.source = "backfill"
    added = append_new(TUTOR_DIR / "lessons.jsonl", lessons)
    print(f"{len(lessons)} lezioni lette, {len(added)} nuove nell'archivio. Profilo temporaneo cancellato.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
