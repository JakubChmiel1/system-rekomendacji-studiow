import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app import dane
from app.database import polaczenie


class TestInterfejsu(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{"DATABASE_PATH":str(Path(self.folder.name)/"gui.db")})
        self.env.start()
        self.app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app/streamlit_app.py")).run(timeout=30)
        self.assertFalse(self.app.exception)

    def tearDown(self):
        self.env.stop(); self.folder.cleanup()

    def login(self):
        self.app.text_input(key="email_logowania").set_value("admin")
        self.app.text_input(key="haslo_logowania").set_value("admin")
        next(x for x in self.app.button if x.label.startswith("Zaloguj się")).click().run(timeout=30)
        self.assertFalse(self.app.exception)
        return self.app.session_state["id_uzytkownika"]

    def test_walidacja_logowania_wszystkie_strony_i_wylogowanie(self):
        self.assertFalse(any(x.label=="Pobierz wszystkie dane z API" for x in self.app.button))
        next(x for x in self.app.button if x.label.startswith("Zaloguj się")).click().run(timeout=30)
        self.assertTrue(any("Uzupełnij" in x.value for x in self.app.error))
        self.login()
        for strona in ["Katalog kierunków","Mój profil","Ankieta","Mapa uczelni","Ulubione","Administracja","Przegląd"]:
            with self.subTest(strona=strona):
                self.app.radio(key="nawigacja").set_value(strona).run(timeout=30)
                self.assertFalse(self.app.exception)
        next(x for x in self.app.button if x.label=="Wyloguj się").click().run(timeout=30)
        self.assertFalse(self.app.exception)
        self.assertTrue(any(x.key=="haslo_logowania" for x in self.app.text_input))

    def test_rejestracja_walidacja_i_konto_kandydata(self):
        self.app.text_input(key="email_rejestracji").set_value("bledny-email")
        self.app.text_input(key="nowe_haslo").set_value("Haslo-testowe-123!")
        next(x for x in self.app.text_input if x.label=="Powtórz hasło").set_value("inne")
        next(x for x in self.app.button if x.label=="Utwórz moje konto").click().run(timeout=30)
        self.assertTrue(any("Hasła" in x.value for x in self.app.error))
        next(x for x in self.app.text_input if x.label=="Powtórz hasło").set_value("Haslo-testowe-123!")
        next(x for x in self.app.button if x.label=="Utwórz moje konto").click().run(timeout=30)
        self.assertTrue(any("e-mail" in x.value for x in self.app.error))
        self.app.text_input(key="email_rejestracji").set_value("nowy@example.test")
        next(x for x in self.app.button if x.label=="Utwórz moje konto").click().run(timeout=30)
        self.assertFalse(self.app.exception)
        self.assertNotIn("Administracja",self.app.radio(key="nawigacja").options)

    def test_ankieta_ponowny_zapis_profil_i_ulubione(self):
        user=self.login()
        self.app.radio(key="nawigacja").set_value("Ankieta").run(timeout=30)
        self.app.multiselect(key="a_zainteresowania").set_value(["technologie"])
        self.app.multiselect(key="a_mocne_strony").set_value(["Myślenie analityczne"])
        next(x for x in self.app.button if x.label=="Zapisz ankietę i odśwież rekomendacje").click().run(timeout=30)
        self.assertFalse(self.app.exception)
        self.assertEqual(dane.pobierz_ankiete(user)["zainteresowania"],["technologie"])
        self.app.multiselect(key="a_zainteresowania").set_value(["prawo"])
        next(x for x in self.app.button if x.label=="Zapisz ankietę i odśwież rekomendacje").click().run(timeout=30)
        self.assertEqual(dane.pobierz_ankiete(user)["zainteresowania"],["prawo"])
        self.app.radio(key="nawigacja").set_value("Mój profil").run(timeout=30)
        next(x for x in self.app.text_input if x.label=="Jak masz na imię?").set_value("Ola")
        next(x for x in self.app.button if x.label=="Zapisz profil i przelicz ranking").click().run(timeout=30)
        self.assertFalse(self.app.exception)
        self.assertEqual(dane.pobierz_profil(user)["imie"],"Ola")
        self.app.radio(key="nawigacja").set_value("Przegląd").run(timeout=30)
        next(x for x in self.app.button if x.label=="♡ Zapisz kierunek").click().run(timeout=30)
        self.assertEqual(len(dane.pobierz_ulubione(user)),1)
        self.app.radio(key="nawigacja").set_value("Ulubione").run(timeout=30)
        self.assertFalse(self.app.exception)
        self.assertTrue(any(x.label=="♥ Zapisano — usuń" for x in self.app.button))

    def test_przycisk_importu_admina_i_obsluga_bledu(self):
        user=self.login()
        self.app.radio(key="nawigacja").set_value("Administracja").run(timeout=30)
        def pobierz(identyfikator,postep):
            self.assertEqual(identyfikator,user)
            postep("instytucje",2,2); postep("kierunki",3,3); postep("zapis",1,1)
            return {"instytucje":2,"kierunki":3,"warianty":4}
        with patch("app.radon.importuj_wszystko",side_effect=pobierz) as importowanie:
            next(x for x in self.app.button if x.label=="Pobierz wszystkie dane z API").click().run(timeout=30)
            importowanie.assert_called_once()
        self.assertFalse(self.app.exception)
        self.assertTrue(any("2 instytucji" in x.value for x in self.app.success))
        with patch("app.radon.importuj_wszystko",side_effect=ValueError("Błąd źródła. Baza bez zmian.")):
            next(x for x in self.app.button if x.label=="Pobierz wszystkie dane z API").click().run(timeout=30)
        self.assertFalse(self.app.exception)
        self.assertTrue(any("Błąd źródła" in x.value for x in self.app.error))
