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

    def test_headings_skip_boilerplate_exercises_and_deep_levels(self):
        vault = make_vault()
        (vault / "Matematica" / "Massimo Comune Divisore.md").write_text(
            "# MCD\n## 1. Enunciato\n### Dimostrazione\n#### Passo 1\n## Esercizio: calcolo\n"
            "## Note e Paragrafi Collegati\n### Teoremi e Concetti Derivati (Note Successive)\n", encoding="utf-8")
        self.assertEqual(moc_notes(vault, "01 MOC's/Algebra MOC.md")[0]["headings"], ["1. Enunciato", "Dimostrazione"])


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

    def test_unknown_or_non_iso_dates_are_dropped(self):
        raw = {"lessons": [{"date": "2 ottobre", "items": []}, {"date": "2026-10-26", "items": []}, {"date": "2026-12-01", "items": []}]}
        self.assertEqual([l["date"] for l in validate(raw, NOTES, dates={"2026-10-26"})], ["2026-10-26"])

    def test_non_dict_answer_is_empty(self):
        self.assertEqual(validate(["x"], NOTES), [])

    def test_planned_moc_title_is_used_and_any_vault_note_counts_as_existing(self):
        notes = NOTES + [{"title": "Relazioni di Equivalenza e Partizioni", "aliases": [], "headings": [], "exists": False}]
        raw = {"lessons": [{"date": "2026-10-07", "items": [
            {"concept": "Relazione di equivalenza", "kind": "definizione", "status": "da_creare", "title": "relazioni di equivalenza e partizioni", "reason": "manca"},
            {"concept": "Sommatoria", "kind": "concetto", "status": "da_creare", "title": "Sommatorie e Produttorie", "reason": "manca"}]}]}
        items = validate(raw, notes, vault_titles={"sommatorie e produttorie": "Sommatorie e Produttorie"})[0]["items"]
        self.assertEqual((items[0]["status"], items[0]["title"]), ("da_creare", "Relazioni di Equivalenza e Partizioni"))
        self.assertEqual((items[1]["status"], items[1]["note"]), ("coperto", "Sommatorie e Produttorie"))

    def test_prompt_lists_planned_titles(self):
        notes = NOTES + [{"title": "Numeri Primi", "aliases": [], "headings": [], "exists": False}]
        self.assertIn("Numeri Primi", build_prompt(COURSE, [LESSON], notes).split("PREVISTE")[1])

    def test_prompt_asks_where_missing_content_belongs(self):
        prompt = build_prompt(COURSE, [LESSON], NOTES)
        self.assertIn("DOVE VA IL CONTENUTO", prompt)
        self.assertIn("nota sua", prompt)

    def test_items_for_the_same_new_note_are_merged(self):
        raw = {"lessons": [{"date": "2026-10-26", "items": [
            {"concept": "Divisioni successive", "kind": "concetto", "status": "da_creare", "title": "Algoritmo Euclideo", "reason": "a"},
            {"concept": "Coefficienti di Bézout", "kind": "concetto", "status": "da_creare", "title": "algoritmo euclideo", "reason": "b"}]}]}
        items = validate(raw, NOTES)[0]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["concept"], "Divisioni successive; Coefficienti di Bézout")

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

    def test_many_lessons_are_split_in_small_calls_and_a_failed_call_loses_only_its_lessons(self):
        lessons = [Lesson("algebra", f"2026-10-{d:02d}", f"lezione {d}", "x") for d in range(1, 11)]
        calls = []

        def ask(prompt, *a, **k):
            dates = [l.date for l in lessons if f"[{l.date}]" in prompt]
            calls.append(dates)
            return None if len(calls) == 2 else {"lessons": [{"date": d, "items": []} for d in dates]}
        got = analyze(COURSE, lessons, make_vault(), ask=ask)
        self.assertEqual([len(c) for c in calls], [4, 4, 2])
        self.assertEqual([l["date"] for l in got], calls[0] + calls[2])

    def test_titles_proposed_by_an_earlier_group_are_shown_to_the_next_ones(self):
        lessons = [Lesson("algebra", f"2026-10-{d:02d}", "x", "x") for d in range(1, 6)]
        prompts = []

        def ask(prompt, *a, **k):
            prompts.append(prompt)
            dates = [l.date for l in lessons if f"[{l.date}]" in prompt]
            return {"lessons": [{"date": d, "items": [{"concept": "Algebra dei limiti", "kind": "teorema", "status": "da_creare",
                                                        "title": "algebra dei limiti di successioni" if len(prompts) == 2 else "Algebra dei Limiti di Successioni",
                                                        "reason": "manca"}]} for d in dates]}
        got = analyze(COURSE, lessons, make_vault(), ask=ask)
        self.assertIn("Algebra dei Limiti di Successioni", prompts[1].split("PREVISTE")[1])
        self.assertEqual({it["title"] for l in got for it in l["items"]}, {"Algebra dei Limiti di Successioni"})

    def test_analyze_is_none_only_when_every_call_fails(self):
        lessons = [Lesson("algebra", f"2026-10-{d:02d}", "x", "x") for d in range(1, 6)]
        self.assertIsNone(analyze(COURSE, lessons, make_vault(), ask=lambda *a, **k: None))


if __name__ == "__main__":
    unittest.main()
