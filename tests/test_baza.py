"""Testy relacji, kont, migracji i bezpiecznego importu katalogu."""

import copy
import io
import json
import os
import sqlite3
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from app.database import initialize_database, polaczenie
from app.konta import pobierz_konto, utworz_konto, zaloguj
from app.radon import ZESTAW_STARTOWY, importuj_z_api, pobierz_katalog


class TestBazy(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.sciezka = Path(self.folder.name) / "rekomendacje_studiow.db"
        self.srodowisko = patch.dict(os.environ, {"DATABASE_PATH": str(self.sciezka)})
        self.srodowisko.start()
        initialize_database()

    def tearDown(self):
        self.srodowisko.stop()
        self.folder.cleanup()

    def admin(self):
        return utworz_konto("admin@example.test", "Haslo-testowe-123!", pierwszy_administrator=True)

    def odpowiedz(self, rekordy, token=None):
        return io.BytesIO(json.dumps({"results": rekordy, "pagination": {"token": token}}).encode())

    def rekord(self):
        rekordy = json.loads(ZESTAW_STARTOWY.read_text(encoding="utf-8"))["dane"]["results"]
        return copy.deepcopy(next(rekord for rekord in rekordy if rekord.get("courseInstances")))

    def test_start_bez_internetu_i_ponowna_inicjalizacja(self):
        self.assertGreaterEqual(len(pobierz_katalog()), 20)
        with patch("urllib.request.urlopen", side_effect=AssertionError("Start nie moze laczyc sie z API")):
            initialize_database()
        with polaczenie() as baza:
            self.assertEqual(baza.execute("SELECT COUNT(*) FROM historia_importow").fetchone()[0], 1)
            self.assertEqual(baza.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(baza.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_migracja_poprzedniej_bazy_zachowuje_dane(self):
        inny_folder = Path(self.folder.name) / "migracja"
        inny_folder.mkdir()
        with sqlite3.connect(inny_folder / "app.db") as baza:
            baza.execute("CREATE TABLE app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            baza.execute("INSERT INTO app_metadata VALUES ('created_at', 'stara-data')")
        with patch.dict(os.environ, {"DATABASE_PATH": str(inny_folder / "rekomendacje_studiow.db")}):
            initialize_database()
            with polaczenie() as baza:
                self.assertEqual(baza.execute("SELECT wartosc FROM metadane_aplikacji WHERE klucz = 'created_at'").fetchone()[0], "stara-data")
                self.assertIsNone(baza.execute("SELECT 1 FROM sqlite_master WHERE name = 'app_metadata'").fetchone())
        self.assertTrue((inny_folder / "app.db").exists())

    def test_administrator_rejestracja_i_logowanie(self):
        administrator = self.admin()
        self.assertEqual(zaloguj("ADMIN@example.test", "Haslo-testowe-123!"), administrator)
        self.assertIsNone(zaloguj("admin@example.test", "zle-haslo"))
        with self.assertRaises(ValueError):
            utworz_konto("drugi@example.test", "Haslo-testowe-123!", pierwszy_administrator=True)
        kandydat = utworz_konto("kandydat@example.test", "Haslo-testowe-123!")
        self.assertEqual(pobierz_konto(kandydat)["rola"], "kandydat")
        with self.assertRaises(ValueError):
            utworz_konto("KANDYDAT@example.test", "Haslo-testowe-123!")
        with patch("urllib.request.urlopen") as pobieranie:
            with self.assertRaises(PermissionError):
                importuj_z_api(kandydat)
            pobieranie.assert_not_called()
        with polaczenie() as baza:
            hasla = [wiersz[0] for wiersz in baza.execute("SELECT skrot_hasla FROM uzytkownicy")]
            self.assertNotEqual(hasla[0], hasla[1])
            self.assertTrue(all(haslo.startswith("scrypt$") for haslo in hasla))
            self.assertEqual(baza.execute("SELECT COUNT(*) FROM profile_kandydatow").fetchone()[0], 1)

    def test_ograniczenia_wynikow_i_klucze_obce(self):
        administrator = self.admin()
        with self.assertRaises(sqlite3.IntegrityError):
            with polaczenie() as baza:
                baza.execute("INSERT INTO wyniki_matur (id_uzytkownika, przedmiot, poziom, wynik_procentowy, rok_matury) VALUES (?, 'matematyka', 'rozszerzony', 101, 2026)", (administrator,))
        with self.assertRaises(sqlite3.IntegrityError):
            with polaczenie() as baza:
                baza.execute("INSERT INTO odpowiedzi_ankiety (id_uzytkownika, kod_pytania, wartosc_odpowiedzi) VALUES (-99, 'zainteresowania', 'informatyka')")

    def test_import_zachowuje_ulubione_opisy_i_kryteria(self):
        administrator = self.admin()
        rekord = self.rekord()
        with polaczenie() as baza:
            wariant = baza.execute("SELECT id, id_kierunku FROM warianty_studiow WHERE id_radon = ?", (rekord["courseInstances"][0]["courseInstanceUuid"],)).fetchone()
            baza.execute("INSERT INTO ulubione (id_uzytkownika, id_wariantu) VALUES (?, ?)", (administrator, wariant["id"]))
            baza.execute("UPDATE kierunki_studiow SET opis = 'Opis administratora' WHERE id = ?", (wariant["id_kierunku"],))
            baza.execute("INSERT INTO kryteria_kierunkow (id_kierunku, typ_kryterium, kod_kryterium, waga) VALUES (?, 'matura', 'matematyka_rozszerzona', 0.5)", (wariant["id_kierunku"],))
            liczba = baza.execute("SELECT COUNT(*) FROM kierunki_studiow").fetchone()[0]
        rekord["courseInstances"][0]["statusCode"] = "6"
        rekord["courseInstances"][0]["statusName"] = "zlikwidowane"
        with patch("urllib.request.urlopen", side_effect=[self.odpowiedz([rekord]), self.odpowiedz([])]):
            self.assertEqual(importuj_z_api(administrator), (1, len(rekord["courseInstances"])))
        with polaczenie() as baza:
            self.assertEqual(baza.execute("SELECT COUNT(*) FROM kierunki_studiow").fetchone()[0], liczba)
            self.assertEqual(baza.execute("SELECT id_wariantu FROM ulubione").fetchone()[0], wariant["id"])
            self.assertEqual(baza.execute("SELECT opis FROM kierunki_studiow WHERE id = ?", (wariant["id_kierunku"],)).fetchone()[0], "Opis administratora")
            self.assertEqual(baza.execute("SELECT COUNT(*) FROM kryteria_kierunkow").fetchone()[0], 1)
            self.assertEqual(baza.execute("SELECT kod_statusu FROM warianty_studiow WHERE id = ?", (wariant["id"],)).fetchone()[0], "6")

    def test_blad_danych_wycofuje_caly_import(self):
        administrator = self.admin()
        poprawny, bledny = self.rekord(), self.rekord()
        stara_nazwa = poprawny["courseName"]
        poprawny["courseName"] = "Zmieniona nazwa"
        bledny["courseUuid"] = "nowy-bledny-rekord"
        bledny["courseInstances"][0]["numberOfSemesters"] = "-1"
        with patch("urllib.request.urlopen", side_effect=[self.odpowiedz([poprawny, bledny]), self.odpowiedz([])]):
            with self.assertRaises(ValueError):
                importuj_z_api(administrator)
        with polaczenie() as baza:
            self.assertEqual(baza.execute("SELECT nazwa FROM kierunki_studiow WHERE id_radon = ?", (poprawny["courseUuid"],)).fetchone()[0], stara_nazwa)
            self.assertEqual(baza.execute("SELECT COUNT(*) FROM historia_importow").fetchone()[0], 1)

    def test_paginacja_tokenow_i_obydwa_poziomy_studiow(self):
        administrator = self.admin()
        rekord = self.rekord()
        with patch("urllib.request.urlopen", side_effect=[self.odpowiedz([rekord], "nastepna"), self.odpowiedz([]), self.odpowiedz([])]) as pobieranie:
            importuj_z_api(administrator, 2)
        zapytania = [parse_qs(urlparse(wywolanie.args[0].full_url).query) for wywolanie in pobieranie.call_args_list]
        self.assertEqual(zapytania[1]["token"], ["nastepna"])
        self.assertEqual(zapytania[2]["levelCode"], ["1"])
        self.assertNotIn("token", zapytania[2])

    def test_niedostepne_api_nie_zmienia_katalogu(self):
        administrator = self.admin()
        przed = pobierz_katalog()
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("brak internetu")):
            with self.assertRaises(ValueError):
                importuj_z_api(administrator)
        self.assertEqual(pobierz_katalog(), przed)


if __name__ == "__main__":
    unittest.main()
