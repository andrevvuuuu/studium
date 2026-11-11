import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[3] / "Scripts"


class TestTemplaterSafety(unittest.TestCase):
    def test_no_js_in_subfolders_of_user_scripts(self):
        # Templater carica ricorsivamente ogni .js di Scripts/ come funzione utente: uno che non lo è rompe tutti i modelli
        self.assertEqual([str(p.relative_to(SCRIPTS)) for p in SCRIPTS.rglob("*.js") if p.parent != SCRIPTS], [])


if __name__ == "__main__":
    unittest.main()
