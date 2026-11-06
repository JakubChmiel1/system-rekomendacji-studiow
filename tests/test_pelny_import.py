import copy
import base64
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
from app.konta import utworz_konto
from app.radon import ADRES_API, ADRES_INSTYTUCJI, ZESTAW_STARTOWY, _pobierz_wszystkie_strony, importuj_wszystko


class TestPelnegoImportu(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.srodowisko = patch.dict(os.environ, {"DATABASE_PATH": str(Path(self.folder.name) / "baza.db")})
        self.srodowisko.start()
        initialize_database()
        self.admin = utworz_konto("admin@example.test", "Haslo-testowe-123!", pierwszy_administrator=True)
        self.rekord = copy.deepcopy(next(x for x in json.loads(ZESTAW_STARTOWY.read_text(encoding="utf-8"))["dane"]["results"] if x.get("courseInstances")))
        self.instytucja = {
            "institutionUuid": self.rekord["leadingInstitutionUuid"], "name": "Nazwa z API instytucji",
            "city": "Miasto instytucji", "iKindName": "Uczelnia publiczna", "www": "https://example.test",
            "branches": [{"branchUuid": "filia-1", "branchName": "Filia testowa"}],
            "dodatkowePole": {"lista": [1, 2, 3]},
        }

    def tearDown(self):
        self.srodowisko.stop()
        self.folder.cleanup()

    def strona(self, rekordy, razem, token=None):
        return {"results": rekordy, "pagination": {"maxCount": razem, "token": token}, "version": "test"}

    def odpowiedzi(self):
        return [self.strona([self.instytucja], 1), self.strona([self.rekord], 1)]

    def test_wszystkie_strony_i_pelne_rekordy_json_bez_filtrow(self):
        druga_instytucja = dict(self.instytucja, institutionUuid="instytucja-2")
        drugi_kierunek = copy.deepcopy(self.rekord)
        drugi_kierunek.update(courseUuid="kierunek-2", levelCode="3", levelName="drugiego stopnia")
        drugi_kierunek["courseInstances"] = []
        self.rekord["nieznanePole"] = {"zawartosc": "zachowana"}
        strony = [self.strona([self.instytucja], 2, "inst-token"), self.strona([druga_instytucja], 2),
                  self.strona([self.rekord], 2, "kier-token"), self.strona([drugi_kierunek], 2)]
        postep = []
        with patch("app.radon._pobierz_strone", side_effect=strony) as pobieranie:
            wynik = importuj_wszystko(self.admin, lambda *wartosci: postep.append(wartosci))
        self.assertEqual(wynik["instytucje"], 2)
        self.assertEqual(wynik["kierunki"], 2)
        zapytania = [parse_qs(urlparse(x.args[0]).query) for x in pobieranie.call_args_list]
        self.assertEqual(zapytania[1]["token"], ["inst-token"])
        self.assertEqual(zapytania[3]["token"], ["kier-token"])
        self.assertTrue(all("levelCode" not in x and "currentStatusCode" not in x for x in zapytania))
        self.assertTrue(all(x["resultNumbers"] == ["100"] for x in zapytania))
        self.assertEqual(postep[-1], ("zapis", 1, 1))
        with polaczenie() as baza:
            for adres, klucz, rekord in [(ADRES_INSTYTUCJI, "institutionUuid", self.instytucja), (ADRES_API, "courseUuid", self.rekord)]:
                zapis = baza.execute("SELECT tresc_json FROM dane_zrodlowe_api WHERE adres_api = ? AND id_radon = ?", (adres, rekord[klucz])).fetchone()[0]
                self.assertEqual(json.loads(zapis), rekord)
            self.assertEqual(baza.execute("SELECT COUNT(*) FROM historia_importow WHERE zakres = 'pelny'").fetchone()[0], 2)
            self.assertEqual(baza.execute("SELECT adres_strony FROM uczelnie WHERE id_radon = ?", (self.instytucja["institutionUuid"],)).fetchone()[0], "https://example.test")
            self.assertEqual(baza.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_ponowny_import_nie_duplikuje_i_zachowuje_ulubione(self):
        with polaczenie() as baza:
            wariant = baza.execute("SELECT id FROM warianty_studiow WHERE id_radon = ?", (self.rekord["courseInstances"][0]["courseInstanceUuid"],)).fetchone()[0]
            baza.execute("INSERT INTO ulubione (id_uzytkownika, id_wariantu) VALUES (?, ?)", (self.admin, wariant))
        with patch("app.radon._pobierz_strone", side_effect=self.odpowiedzi() * 2):
            importuj_wszystko(self.admin)
            importuj_wszystko(self.admin)
        with polaczenie() as baza:
            self.assertEqual(baza.execute("SELECT COUNT(*) FROM dane_zrodlowe_api WHERE adres_api = ?", (ADRES_INSTYTUCJI,)).fetchone()[0], 1)
            self.assertEqual(baza.execute("SELECT id_wariantu FROM ulubione WHERE id_uzytkownika = ?", (self.admin,)).fetchone()[0], wariant)

    def test_awaria_drugiego_api_nie_zapisuje_niczego(self):
        with polaczenie() as baza:
            przed = baza.execute("SELECT COUNT(*) FROM dane_zrodlowe_api").fetchone()[0]
        with patch("app.radon._pobierz_strone", side_effect=[self.odpowiedzi()[0], ValueError("awaria API")]):
            with self.assertRaises(ValueError):
                importuj_wszystko(self.admin)
        with polaczenie() as baza:
            self.assertEqual(baza.execute("SELECT COUNT(*) FROM dane_zrodlowe_api").fetchone()[0], przed)
            self.assertEqual(baza.execute("SELECT COUNT(*) FROM historia_importow").fetchone()[0], 1)

    def test_blad_zapisu_wycofuje_obydwa_zrodla(self):
        self.rekord["courseInstances"][0]["numberOfSemesters"] = "-1"
        with patch("app.radon._pobierz_strone", side_effect=self.odpowiedzi()):
            with self.assertRaises(ValueError):
                importuj_wszystko(self.admin)
        with polaczenie() as baza:
            self.assertEqual(baza.execute("SELECT COUNT(*) FROM dane_zrodlowe_api WHERE adres_api = ?", (ADRES_INSTYTUCJI,)).fetchone()[0], 0)
            self.assertEqual(baza.execute("SELECT COUNT(*) FROM historia_importow").fetchone()[0], 1)

    def test_kandydat_nie_moze_uruchomic_pobierania(self):
        kandydat = utworz_konto("kandydat@example.test", "Haslo-testowe-123!")
        with patch("app.radon._pobierz_strone") as pobieranie:
            with self.assertRaises(PermissionError):
                importuj_wszystko(kandydat)
            pobieranie.assert_not_called()

    def test_import_bez_konta_zapisuje_historie_bez_administratora(self):
        with patch("app.radon._pobierz_strone", side_effect=self.odpowiedzi()):
            wynik = importuj_wszystko()
        self.assertEqual(wynik["instytucje"], 1)
        with polaczenie() as baza:
            historia = baza.execute("SELECT id_administratora FROM historia_importow WHERE zakres = 'pelny'").fetchall()
            self.assertEqual(len(historia), 2)
            self.assertTrue(all(wiersz[0] is None for wiersz in historia))

    def test_niepelne_lub_zapetlone_strony_sa_bledem(self):
        for strony in [[self.strona([self.instytucja], 2)],
                       [self.strona([self.instytucja], 2, "ten-sam"), self.strona([self.instytucja], 2, "ten-sam")]]:
            with self.subTest(strony=strony):
                with patch("app.radon._pobierz_strone", side_effect=strony):
                    with self.assertRaises(ValueError):
                        _pobierz_wszystkie_strony(ADRES_INSTYTUCJI, "institutionUuid", "instytucje", None)

    def test_nakladka_stron_obejmuje_rekordy_o_tym_samym_czasie(self):
        pierwszy = dict(self.instytucja, lastRefresh="100")
        drugi = dict(self.instytucja, institutionUuid="drugi", lastRefresh="100")
        trzeci = dict(self.instytucja, institutionUuid="trzeci", lastRefresh="101")
        token = base64.b64encode(b"100").decode()
        strony = [self.strona([pierwszy], 3, token), self.strona([pierwszy, drugi, trzeci], 3)]
        with patch("app.radon._pobierz_strone", side_effect=strony) as pobieranie:
            rekordy, _ = _pobierz_wszystkie_strony(ADRES_INSTYTUCJI, "institutionUuid", "instytucje", None)
        self.assertEqual(len(rekordy), 3)
        zapytanie = parse_qs(urlparse(pobieranie.call_args_list[1].args[0]).query)
        self.assertEqual(base64.b64decode(zapytanie["token"][0]), b"99")

    def test_migracja_wersji_1_zachowuje_konto_i_ulubione(self):
        sciezka = str(Path(self.folder.name) / "stara.db")
        schemat = Path(__file__).with_name("dane") / "schemat_v1.sql"
        with sqlite3.connect(sciezka) as baza:
            baza.executescript(schemat.read_text(encoding="utf-8"))
            baza.execute("PRAGMA user_version = 1")
            baza.execute("INSERT INTO metadane_aplikacji VALUES ('zestaw_startowy_radon', 'stara-data')")
            baza.execute("INSERT INTO uzytkownicy (id,email,skrot_hasla,rola) VALUES (1,'stary@example.test','skrot','administrator')")
            baza.execute("INSERT INTO uczelnie (id,id_radon,nazwa,data_pobrania) VALUES (1,'uczelnia','Uczelnia','data')")
            baza.execute("INSERT INTO kierunki_studiow (id,id_radon,id_uczelni,nazwa,poziom,kod_poziomu,status,kod_statusu,adres_zrodla,data_pobrania) VALUES (1,'kierunek',1,'Kierunek','pierwszego stopnia','2','prowadzone','3','adres','data')")
            baza.execute("INSERT INTO warianty_studiow (id,id_radon,id_kierunku,nazwa,tryb_studiow,kod_trybu,status,kod_statusu,data_pobrania) VALUES (1,'wariant',1,'Wariant','stacjonarne','1','prowadzone','3','data')")
            baza.execute("INSERT INTO ulubione (id_uzytkownika,id_wariantu) VALUES (1,1)")
        with patch.dict(os.environ, {"DATABASE_PATH": sciezka}):
            initialize_database()
            initialize_database()
            with polaczenie() as baza:
                self.assertEqual(baza.execute("PRAGMA user_version").fetchone()[0], 2)
                self.assertEqual(baza.execute("SELECT email FROM uzytkownicy WHERE id=1").fetchone()[0], "stary@example.test")
                self.assertEqual(baza.execute("SELECT id_wariantu FROM ulubione WHERE id_uzytkownika=1").fetchone()[0], 1)
                baza.execute("SELECT tresc_json FROM dane_zrodlowe_api")
