import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from diary_sources import Lesson  # noqa: E402
from tutor import analyze, build_prompt, moc_notes, validate  # noqa: E402
from tutor_store import Course  # noqa: E402

NOTES = [{"title": "Massimo Comune Divisore", "aliases": ["MCD"], "headings": ["Esistenza e unicità"], "exists": True},
         {"title": "Algoritmo di Euclide", "aliases": [], "headings": [], "exists": True}]
COURSE = Course("algebra", "Algebra", "01 MOC's/Algebra MOC.md", 2026, {"tipo": "malvenuto_site"})
LESSON = Lesson("algebra", "2026-10-26", "Algoritmo di Euclide. Identità di Bézout.", "malvenuto_site", 14)


def make_vault() -> Path:
    vault = Path(tempfile.mkdtemp())
    (vault / "01 MOC's").mkdir()
    (vault / "01 MOC's" / "Algebra MOC.md").write_text(
        "---\nType:\n  - MOC\n---\n# Algebra\n\n## Divisibilità\n- [[Massimo Comune Divisore]]\n- [[Numeri Primi]]\n", encoding="utf-8")
    (vault / "Matematica").mkdir()
    (vault / "Matematica" / "Massimo Comune Divisore.md").write_text(
        "---\naliases:\n  - MCD\n---\n# Massimo Comune Divisore\n\n## Esistenza e unicità\n", encoding="utf-8")
    return vault


class TestMocNotes(unittest.TestCase):
    def test_lists_notes_in_moc_order_with_aliases_and_headings(self):
        notes = moc_notes(make_vault(), "01 MOC's/Algebra MOC.md")
        self.assertEqual([n["title"] for n in notes], ["Massimo Comune Divisore", "Numeri Primi"])
        self.assertEqual(notes[0]["aliases"], ["MCD"])
        self.assertIn("Esistenza e unicità", notes[0]["headings"])
        self.assertFalse(notes[1]["exists"])


class TestValidate(unittest.TestCase):
    def test_invented_existing_note_becomes_missing(self):
        raw = {"lessons": [{"date": "2026-10-26", "items": [
            {"concept": "Identità di Bézout", "kind": "teorema", "status": "coperto", "note": "Identità di Bézout", "reason": "c'è"}]}]}
        item = validate(raw, NOTES)[0]["items"][0]
        self.assertEqual(item["status"], "da_creare")
        self.assertEqual(item["title"], "Identità di Bézout")

    def test_new_title_that_exists_as_alias_is_not_created(self):
        raw = {"lessons": [{"date": "2026-10-21", "items": [
            {"concept": "MCD", "kind": "definizione", "status": "da_creare", "title": "MCD", "reason": "manca"}]}]}
        item = validate(raw, NOTES)[0]["items"][0]
        self.assertEqual(item["status"], "coperto")
        self.assertEqual(item["note"], "Massimo Comune Divisore")

    def test_item_without_reason_is_dropped(self):
        raw = {"lessons": [{"date": "2026-10-26", "items": [{"concept": "X", "kind": "concetto", "status": "da_creare", "title": "X", "reason": ""}]}]}
        self.assertEqual(validate(raw, NOTES)[0]["items"], [])


class TestAnalyze(unittest.TestCase):
    def test_prompt_lists_lessons_and_notes(self):
        prompt = build_prompt(COURSE, [LESSON], NOTES)
        self.assertIn("Identità di Bézout", prompt)
        self.assertIn("Massimo Comune Divisore · MCD · Esistenza e unicità", prompt)

    def test_analyze_returns_none_when_agy_fails(self):
        self.assertIsNone(analyze(COURSE, [LESSON], make_vault(), ask=lambda *a, **k: None))

    def test_analyze_validates_agy_answer(self):
        answer = {"lessons": [{"date": "2026-10-26", "items": [
            {"concept": "Identità di Bézout", "kind": "teorema", "status": "da_creare", "title": "Identità di Bézout", "after": "Massimo Comune Divisore", "reason": "non c'è nessuna nota"}]}]}
        got = analyze(COURSE, [LESSON], make_vault(), ask=lambda *a, **k: answer)
        self.assertEqual(got[0]["items"][0]["status"], "da_creare")


if __name__ == "__main__":
    unittest.main()
