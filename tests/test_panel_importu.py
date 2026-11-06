import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app.database import initialize_database


class TestPaneluImportu(unittest.TestCase):
    def test_import_bez_logowania_postep_sukces_i_blad(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"DATABASE_PATH": str(Path(folder) / "panel.db")}):
                initialize_database()
                sciezka_aplikacji = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
                aplikacja = AppTest.from_file(str(sciezka_aplikacji)).run(timeout=20)
                self.assertFalse(aplikacja.exception)
                nazwa = "Pobierz wszystkie dane z API"
                self.assertTrue(any(x.label == nazwa for x in aplikacja.button))
                self.assertFalse(aplikacja.get("form"))
                self.assertFalse(any("hasło" in x.label.casefold() or "e-mail" in x.label.casefold() for x in aplikacja.text_input))

                def pobierz(*, postep):
                    postep("instytucje", 2, 2)
                    postep("kierunki", 3, 3)
                    postep("zapis", 1, 1)
                    return {"instytucje": 2, "kierunki": 3, "warianty": 4}

                with patch("app.radon.importuj_wszystko", side_effect=pobierz) as importowanie:
                    next(x for x in aplikacja.button if x.label == nazwa).click().run(timeout=20)
                    importowanie.assert_called_once()
                self.assertFalse(aplikacja.exception)
                self.assertTrue(any("2 instytucji" in x.value for x in aplikacja.success))
                with patch("app.radon.importuj_wszystko", side_effect=ValueError("Blad zrodla. Baza bez zmian.")):
                    next(x for x in aplikacja.button if x.label == nazwa).click().run(timeout=20)
                self.assertFalse(aplikacja.exception)
                self.assertTrue(any("Blad zrodla" in x.value for x in aplikacja.error))
