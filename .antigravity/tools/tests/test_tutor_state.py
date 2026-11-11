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


class TestReconcile(unittest.TestCase):
    def setUp(self):
        from tutor import reconcile  # noqa: F401
        self.vault = Path(tempfile.mkdtemp())
        (self.vault / "Matematica").mkdir()

    def state(self):
        return {"recupero": True, "courses": [{"id": "algebra", "lessons": [{"date": "2026-10-02", "items": [
            {"status": "da_creare", "concept": "Bézout", "title": "Identità di Bézout", "reason": "r"},
            {"status": "da_completare", "concept": "MCD", "note": "Massimo Comune Divisore", "missing": "unicità", "reason": "r"}]}]}]}

    def test_created_note_becomes_covered(self):
        from tutor import reconcile
        (self.vault / "Matematica" / "Identità di Bézout.md").write_text("# B\n")
        item = reconcile(self.state(), self.vault, "2026-11-03")["courses"][0]["lessons"][0]["items"][0]
        self.assertEqual((item["status"], item["note"]), ("coperto", "Identità di Bézout"))

    def test_completed_note_is_recognized_by_its_lessons_frontmatter(self):
        from tutor import reconcile
        mcd = self.vault / "Matematica" / "Massimo Comune Divisore.md"
        mcd.write_text("---\nLezioni:\n  - 2026-10-21\n---\n# MCD\n")
        self.assertEqual(reconcile(self.state(), self.vault, "2026-11-03")["courses"][0]["lessons"][0]["items"][1]["status"], "da_completare")
        mcd.write_text("---\nLezioni:\n  - 2026-10-02\n---\n# MCD\n")
        self.assertEqual(reconcile(self.state(), self.vault, "2026-11-03")["courses"][0]["lessons"][0]["items"][1]["status"], "coperto")

    def test_recupero_recomputed(self):
        from tutor import reconcile
        (self.vault / "Matematica" / "Identità di Bézout.md").write_text("# B\n")
        (self.vault / "Matematica" / "Massimo Comune Divisore.md").write_text("---\nLezioni:\n  - 2026-10-02\n---\n")
        self.assertFalse(reconcile(self.state(), self.vault, "2026-11-03")["recupero"])


class TestRun(unittest.TestCase):
    def setUp(self):
        import tutor
        self.t = tutor
        self.dir = Path(tempfile.mkdtemp())
        self.saved = {k: getattr(tutor, k) for k in ("TUTOR_DIR", "STORE", "STATE", "LOCK", "read_course", "analyze", "VAULT")}
        tutor.TUTOR_DIR, tutor.STORE, tutor.STATE, tutor.LOCK = self.dir, self.dir / "lessons.jsonl", self.dir / "state.json", self.dir / "tutor.lock"
        tutor.VAULT = self.dir
        (self.dir / "courses.json").write_text(json.dumps([
            {"id": "algebra", "nome": "Algebra", "moc": "a.md", "start_year": 2026, "fonte": {"tipo": "x"}},
            {"id": "analisi", "nome": "Analisi", "moc": "b.md", "start_year": 2026, "fonte": {"tipo": "x"}}]))
        tutor.read_course = lambda c: ([Lesson(c.id, "2026-10-02", f"lezione di {c.id}", "x"), Lesson(c.id, "2026-10-05", f"seconda di {c.id}", "x")], [], [])

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(self.t, k, v)

    def test_one_course_crashing_does_not_lose_the_other_and_state_is_written(self):
        def analyze(c, lessons, vault):
            if c.id == "analisi":
                raise FileNotFoundError("b.md")
            return [{"date": "2026-10-02", "items": []}, {"date": "2026-10-05", "items": []}]
        self.t.analyze = analyze
        self.t.run(force=True)
        st = json.loads(self.t.STATE.read_text())
        self.assertIn("b.md", next(c for c in st["courses"] if c["id"] == "analisi")["errore"])
        self.assertEqual(len(next(c for c in st["courses"] if c["id"] == "algebra")["lessons"]), 2)
        self.assertTrue(st["last_run_day"])
        from tutor_store import pending
        self.assertEqual(pending(self.t.STORE, "algebra"), [])
        self.assertEqual(len(pending(self.t.STORE, "analisi")), 2)

    def test_lessons_missing_from_agy_answer_stay_pending(self):
        self.t.analyze = lambda c, lessons, vault: [{"date": "2026-10-02", "items": []}]
        self.t.run(force=True)
        from tutor_store import pending
        self.assertEqual([l.date for l in pending(self.t.STORE, "algebra")], ["2026-10-05"])
