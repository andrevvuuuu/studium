import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from diary_sources import Lesson  # noqa: E402
from tutor_store import append_new, lesson_key, load_courses, load_secrets, mark_analyzed, pending  # noqa: E402


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = self.tmp / "lessons.jsonl"

    def test_append_is_idempotent(self):
        l = Lesson("algebra", "2026-10-02", "Insiemi", "site", 1)
        self.assertEqual(len(append_new(self.store, [l])), 1)
        self.assertEqual(append_new(self.store, [l]), [])

    def test_changed_text_is_new_and_pending(self):
        a = Lesson("algebra", "2026-10-02", "Insiemi", "site", 1)
        append_new(self.store, [a])
        mark_analyzed(self.store, [lesson_key(a)])
        b = Lesson("algebra", "2026-10-02", "Insiemi. Relazioni", "site", 1)
        self.assertEqual(len(append_new(self.store, [b])), 1)
        self.assertEqual([x.text for x in pending(self.store, "algebra")], ["Insiemi. Relazioni"])

    def test_pending_is_per_course(self):
        append_new(self.store, [Lesson("algebra", "2026-10-02", "A", "site"), Lesson("analisi", "2026-10-01", "B", "gmail")])
        self.assertEqual([x.text for x in pending(self.store, "analisi")], ["B"])

    def test_missing_secrets_is_empty(self):
        self.assertEqual(load_secrets(self.tmp / "nope.json"), {})

    def test_load_courses(self):
        path = self.tmp / "courses.json"
        path.write_text(json.dumps([{"id": "algebra", "nome": "Algebra", "moc": "01 MOC's/Algebra Lineare MOC.md", "start_year": 2026,
                                     "fonte": {"tipo": "malvenuto_site", "url": "u"}, "orario": [], "esami": []}]))
        course = load_courses(path)[0]
        self.assertEqual((course.id, course.start_year, course.fonte["tipo"]), ("algebra", 2026, "malvenuto_site"))


if __name__ == "__main__":
    unittest.main()
