import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orchestrator import add_lessons_frontmatter  # noqa: E402
from tutor import edit_job, insert_after_in_moc, lesson_batch_notes  # noqa: E402


class TestMoc(unittest.TestCase):
    def test_insert_after(self):
        moc = "## 04 Divisibilità\n- [[Massimo Comune Divisore]]\n- [[Numeri Primi]]\n"
        self.assertEqual(insert_after_in_moc(moc, "Identità di Bézout", "Massimo Comune Divisore"),
                         "## 04 Divisibilità\n- [[Massimo Comune Divisore]]\n- [[Identità di Bézout]]\n- [[Numeri Primi]]\n")

    def test_insert_keeps_indent_and_marker(self):
        moc = "1. [[A]]\n   * [[B]] — testo\n   * [[C]]\n"
        self.assertEqual(insert_after_in_moc(moc, "D", "B"), "1. [[A]]\n   * [[B]] — testo\n   * [[D]]\n   * [[C]]\n")

    def test_insert_is_idempotent(self):
        moc = "- [[Identità di Bézout]]\n"
        self.assertEqual(insert_after_in_moc(moc, "Identità di Bézout", None), moc)

    def test_prose_anchor_goes_at_end_of_its_section(self):
        moc = ("## Gli Insiemi\nIl corso parte da [[Insiemi e Operazioni]] e arriva a [[Relazioni]].\n\n"
               "```mermaid\nA --> B[\"[[Relazioni]]\"]\n```\n\n## I Numeri\nPoi [[Numeri Naturali]].\n")
        self.assertEqual(insert_after_in_moc(moc, "Relazioni di Equivalenza", "Relazioni"),
                         "## Gli Insiemi\nIl corso parte da [[Insiemi e Operazioni]] e arriva a [[Relazioni]].\n\n"
                         "```mermaid\nA --> B[\"[[Relazioni]]\"]\n```\n\n- [[Relazioni di Equivalenza]]\n\n## I Numeri\nPoi [[Numeri Naturali]].\n")

    def test_list_anchor_with_children_keeps_children_in_place(self):
        moc = "## Divisibilità\n- [[MCD]]\n  - [[Euclide]]\n- [[Primi]]\n"
        self.assertEqual(insert_after_in_moc(moc, "Bézout", "MCD"), "## Divisibilità\n- [[MCD]]\n  - [[Euclide]]\n- [[Bézout]]\n- [[Primi]]\n")

    def test_without_anchor_never_lands_in_raccordo_section(self):
        moc = "## Gli Insiemi\nTesto con [[A]].\n\n## Note e Paragrafi Collegati\n- [[Analisi 2 MOC]]\n"
        self.assertEqual(insert_after_in_moc(moc, "C", "Inesistente"),
                         "## Gli Insiemi\nTesto con [[A]].\n\n- [[C]]\n\n## Note e Paragrafi Collegati\n- [[Analisi 2 MOC]]\n")

    def test_duplicate_check_ignores_case_and_anchors(self):
        moc = "## X\nVedi [[identità di bézout#Enunciato]].\n"
        self.assertEqual(insert_after_in_moc(moc, "Identità di Bézout", None), moc)


class TestJobs(unittest.TestCase):
    STATE = {"courses": [{"id": "algebra", "lessons": [{"date": "2026-10-26", "items": [
        {"status": "da_creare", "concept": "Bézout", "title": "Identità di Bézout", "after": "Massimo Comune Divisore", "reason": "r"},
        {"status": "da_completare", "concept": "MCD", "note": "Massimo Comune Divisore", "missing": "dimostrazione dell'unicità", "reason": "r"},
        {"status": "coperto", "concept": "Euclide", "note": "Algoritmo di Euclide", "reason": "r"}]}]}]}

    def test_batch_notes_only_missing_with_diary(self):
        notes = lesson_batch_notes(self.STATE, "algebra", "2026-10-26", "Algoritmo di Euclide. Bézout.")
        self.assertEqual([(n["title"], n["after"]) for n in notes], [("Identità di Bézout", "Massimo Comune Divisore")])
        self.assertEqual(notes[0]["diary"], "Algoritmo di Euclide. Bézout.")
        self.assertEqual(notes[0]["lessons"], ["2026-10-26"])

    def test_edit_job_instructions(self):
        job = edit_job(self.STATE, "algebra", "2026-10-26", "Massimo Comune Divisore", "Testo della lezione.", "Matematica/MCD.md")
        self.assertEqual(job["operation"], "edit")
        self.assertIn("dimostrazione dell'unicità", job["user_instructions"])
        self.assertIn("Testo della lezione.", job["user_instructions"])
        self.assertEqual(job["lessons"], ["2026-10-26"])
        self.assertEqual(job["target_file_path"], "Matematica/MCD.md")


class TestFrontmatter(unittest.TestCase):
    def test_lessons_frontmatter(self):
        note = "---\nDisciplina: Matematica\n---\n# X\n"
        out = add_lessons_frontmatter(add_lessons_frontmatter(note, ["2026-10-26"]), ["2026-10-21", "2026-10-26"])
        self.assertIn("Lezioni:\n  - 2026-10-21\n  - 2026-10-26\n", out)
        self.assertTrue(out.endswith("# X\n"))
        self.assertEqual(out.count("Lezioni:"), 1)

    def test_no_frontmatter_creates_one(self):
        self.assertTrue(add_lessons_frontmatter("# X\n", ["2026-10-26"]).startswith("---\nLezioni:\n  - 2026-10-26\n---\n# X"))


if __name__ == "__main__":
    unittest.main()


class TestGuards(unittest.TestCase):
    def test_job_running_only_for_live_running_job(self):
        import os
        from tutor import job_running
        rt = Path(tempfile.mkdtemp())
        self.assertFalse(job_running(rt))
        (rt / "job-status.json").write_text(json.dumps({"status": "running", "pid": os.getpid()}))
        self.assertTrue(job_running(rt))
        (rt / "job-status.json").write_text(json.dumps({"status": "running", "pid": 999999}))
        self.assertFalse(job_running(rt))
        (rt / "job-status.json").write_text(json.dumps({"status": "completed", "pid": os.getpid()}))
        self.assertFalse(job_running(rt))

    def test_gmail_url_carries_key_and_course(self):
        from diary_sources import gmail_request_url
        url = gmail_request_url({"gmail_url": "https://script.google.com/macros/s/X/exec", "gmail_key": "k"}, "Analisi Matematica I")
        self.assertEqual(url, "https://script.google.com/macros/s/X/exec?key=k&corso=Analisi+Matematica+I")
