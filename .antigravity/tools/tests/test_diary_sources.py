import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from diary_sources import DiaryFormatError, parse_it_date, parse_malvenuto  # noqa: E402

FIXTURES = Path(__file__).with_name("fixtures")

SMALL = """<html><body><p>Diario delle lezioni</p>
<p>1) Venerdì&nbsp; 2 ottobre (lezioni 1-2 CM): Insiemi.</p>
<p>2) Lunedì&nbsp; 5 <span>ottobre</span> (lezioni 3-4 CM): Connettivi.</p>
<p>Diario aggiornato fin qui______________________</p>
<p>3) Martedì&nbsp; 6 ottobre (lezioni 5-6 DV): Relazioni dell'anno scorso.</p>
</body></html>"""


class TestMalvenuto(unittest.TestCase):
    def setUp(self):
        self.html = (FIXTURES / "malvenuto.html").read_text(encoding="utf-8")

    def test_only_entries_above_marker_are_done(self):
        done, forecast, _ = parse_malvenuto(self.html, "algebra", 2026)
        self.assertEqual(done[0].number, 1)
        self.assertEqual(done[0].date, "2026-10-02")
        self.assertEqual(done[-1].number, 17)
        self.assertEqual(done[-1].date, "2026-10-30")
        self.assertEqual(forecast[0].number, 18)

    def test_text_keeps_topics(self):
        done, _, _ = parse_malvenuto(self.html, "algebra", 2026)
        self.assertIn("Identità di Bézout", next(l for l in done if l.number == 14).text)

    def test_missing_marker_raises(self):
        with self.assertRaises(DiaryFormatError):
            parse_malvenuto(self.html.replace("Diario aggiornato fin qui", "xxx"), "algebra", 2026)

    def test_moved_marker(self):
        done, forecast, _ = parse_malvenuto(SMALL, "algebra", 2026)
        self.assertEqual([l.number for l in done], [1, 2])
        self.assertEqual(done[1].date, "2026-10-05")
        self.assertEqual([l.number for l in forecast], [3])
        moved = SMALL.replace("<p>Diario aggiornato fin qui______________________</p>\n", "").replace(
            "<p>Diario delle lezioni</p>", "<p>Diario delle lezioni</p>").replace(
            "</body>", "<p>Diario aggiornato fin qui___</p></body>")
        done, forecast, _ = parse_malvenuto(moved, "algebra", 2026)
        self.assertEqual([l.number for l in done], [1, 2, 3])
        self.assertEqual(forecast, [])

    def test_exam_dates(self):
        _, _, exams = parse_malvenuto(self.html, "algebra", 2026)
        self.assertIn({"nome": "Prima prova in itinere", "data": "2026-11-19"}, exams)


class TestDates(unittest.TestCase):
    def test_irregular_italian_dates(self):
        self.assertEqual(parse_it_date("Lezione del 1° ottobre 2026", 2026), "2026-10-01")
        self.assertEqual(parse_it_date("Lezione dell'8 ottobre 2026", 2026), "2026-10-08")
        self.assertEqual(parse_it_date("Venerdì  8 gennaio", 2026), "2027-01-08")
        self.assertIsNone(parse_it_date("nessuna data", 2026))


if __name__ == "__main__":
    unittest.main()
