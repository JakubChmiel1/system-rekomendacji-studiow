import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app import dane
from app.database import polaczenie, initialize_database
from app.konta import utworz_konto


class TestInterfejsu(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{"DATABASE_PATH":str(Path(self.folder.name)/"gui.db")})
        self.env.start()
        initialize_database()
        self.user=utworz_konto("uczen@example.test","Haslo-testowe-123!")
        self.app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app/streamlit_app.py")).run(timeout=30)
        self.assertFalse(self.app.exception)

    def tearDown(self):
        self.env.stop(); self.folder.cleanup()

    def login(self):
        self.app.text_input(key="email_logowania").set_value("uczen@example.test")
        self.app.text_input(key="haslo_logowania").set_value("Haslo-testowe-123!")
        next(x for x in self.app.button if x.label.startswith("Zaloguj się")).click().run(timeout=30)
        self.assertFalse(self.app.exception)
        return self.app.session_state["id_uzytkownika"]

    def test_walidacja_logowania_wszystkie_strony_i_wylogowanie(self):
        self.assertFalse(any(x.label=="Pobierz wszystkie dane z API" for x in self.app.button))
        next(x for x in self.app.button if x.label.startswith("Zaloguj się")).click().run(timeout=30)
        self.assertTrue(any("Uzupełnij" in x.value for x in self.app.error))
        self.login()
        for strona in ["Katalog kierunków","Mój profil","Ankieta","Mapa uczelni","Ulubione","Przegląd"]:
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

    def test_brak_panelu_recznego_importu_i_automatycznego_pobierania_przy_odswiezaniu(self):
        self.login()
        with polaczenie() as baza:
            baza.execute("UPDATE uzytkownicy SET rola='administrator' WHERE id=?",(self.user,))
        self.app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app/streamlit_app.py"))
        self.app.session_state["id_uzytkownika"]=self.user
        self.app.session_state["nawigacja"]="Administracja"
        with patch("app.synchronizacja.synchronizuj_katalog") as pobieranie:
            self.app.run(timeout=30)
            pobieranie.assert_not_called()
        self.assertFalse(self.app.exception)
        self.assertNotIn("Administracja",self.app.radio(key="nawigacja").options)
        self.assertFalse(any(x.label=="Pobierz wszystkie dane z API" for x in self.app.button))
        self.assertTrue(any("automatycznie" in x.value for x in self.app.caption))
