import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from diary_sources import Lesson  # noqa: E402
from tutor import acquire_lock, build_state, release_lock, should_run, write_state  # noqa: E402
from tutor_store import Course  # noqa: E402

COURSES = [
    Course("algebra", "Algebra", "m.md", 2026, {"tipo": "malvenuto_site"}, [{"giorno": "lun", "ora": "10:00"}], [{"nome": "Prima prova in itinere", "data": "2026-11-19"}]),
    Course("analisi", "Analisi", "a.md", 2026, {"tipo": "gmail_forum"}, [], [{"nome": "Primo esonero", "data": "2026-11-13"}]),
]
MISSING = {"concept": "Bézout", "kind": "teorema", "status": "da_creare", "title": "Identità di Bézout", "reason": "manca"}


class TestRun(unittest.TestCase):
    def setUp(self):
        self.lock = Path(tempfile.mkdtemp()) / "tutor.lock"

    def test_runs_once_a_day(self):
        self.assertFalse(should_run({"last_run_day": "2026-11-03"}, "2026-11-03", force=False))
        self.assertTrue(should_run({"last_run_day": "2026-11-03"}, "2026-11-03", force=True))
        self.assertTrue(should_run({}, "2026-11-03", force=False))

    def test_lock_blocks_second_run_and_ignores_dead_pid(self):
        self.assertTrue(acquire_lock(self.lock))
        self.assertFalse(acquire_lock(self.lock))
        self.lock.write_text("999999")
        self.assertTrue(acquire_lock(self.lock))
        release_lock(self.lock)
        self.assertFalse(self.lock.exists())


class TestState(unittest.TestCase):
    def test_error_keeps_previous_lessons(self):
        prev = {"courses": [{"id": "algebra", "lessons": [{"date": "2026-10-30", "items": []}]}]}
        st = build_state(COURSES, {}, {}, {}, {"algebra": "segno mancante"}, "2026-11-03", prev)
        alg = next(c for c in st["courses"] if c["id"] == "algebra")
        self.assertEqual(alg["errore"], "segno mancante")
        self.assertEqual(alg["lessons"][0]["date"], "2026-10-30")
        self.assertEqual(st["last_run_day"], "2026-11-03")

    def test_new_analysis_replaces_same_date_and_sorts(self):
        prev = {"courses": [{"id": "algebra", "lessons": [{"date": "2026-10-30", "items": []}, {"date": "2026-10-26", "items": []}]}]}
        st = build_state(COURSES, {"algebra": [{"date": "2026-10-30", "items": [MISSING]}]}, {}, {}, {}, "2026-11-03", prev)
        alg = next(c for c in st["courses"] if c["id"] == "algebra")
        self.assertEqual([l["date"] for l in alg["lessons"]], ["2026-10-26", "2026-10-30"])
        self.assertEqual(alg["lessons"][1]["items"], [MISSING])

    def test_recupero_when_old_lessons_have_missing_notes(self):
        st = build_state(COURSES, {"algebra": [{"date": "2026-10-02", "items": [MISSING]}]}, {}, {}, {}, "2026-11-03", {})
        self.assertTrue(st["recupero"])
        st = build_state(COURSES, {"algebra": [{"date": "2026-11-02", "items": [MISSING]}]}, {}, {}, {}, "2026-11-03", {})
        self.assertFalse(st["recupero"])

    def test_exams_merged_future_only_and_forecast(self):
        exams = {"algebra": [{"nome": "Prima prova in itinere", "data": "2026-11-19"}, {"nome": "Seconda prova in itinere", "data": "2027-01-15"}]}
        forecast = {"algebra": [Lesson("algebra", "2026-11-02", "Equazioni diofantee.", "site", 18)]}
        st = build_state(COURSES, {}, forecast, exams, {}, "2026-11-20", {})
        alg = next(c for c in st["courses"] if c["id"] == "algebra")
        self.assertEqual(alg["esami"], [{"nome": "Seconda prova in itinere", "data": "2027-01-15"}])
        self.assertEqual(alg["previsione"], ["Equazioni diofantee."])

    def test_next_lesson_from_schedule(self):
        st = build_state(COURSES, {}, {}, {}, {}, "2026-11-03", {})  # martedì
        alg = next(c for c in st["courses"] if c["id"] == "algebra")
        self.assertEqual(alg["prossima_lezione"], {"data": "2026-11-09", "ora": "10:00"})
        self.assertIsNone(next(c for c in st["courses"] if c["id"] == "analisi")["prossima_lezione"])

    def test_write_state_is_atomic_json(self):
        path = Path(tempfile.mkdtemp()) / "state.json"
        write_state(path, {"a": 1})
        self.assertEqual(json.loads(path.read_text()), {"a": 1})
        self.assertFalse(path.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
