import json
import os
import tempfile
import threading
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch

from app.database import initialize_database,polaczenie
from app.konta import utworz_konto
from app.synchronizacja import _zajmij_import,_postep,sprawdz_i_aktualizuj,stan_synchronizacji,wymaga_aktualizacji


class TestSynchronizacji(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{"DATABASE_PATH":str(Path(self.folder.name)/"sync.db")})
        self.env.start()
        initialize_database()
        self.chwila=datetime.now(timezone.utc)

    def tearDown(self):
        self.env.stop()
        self.folder.cleanup()

    def ustaw_date(self,chwila):
        with polaczenie() as baza:
            baza.execute("INSERT INTO metadane_aplikacji (klucz,wartosc) VALUES ('ostatni_pelny_import',?) ON CONFLICT(klucz) DO UPDATE SET wartosc=excluded.wartosc",(chwila.isoformat(),))

    def importer(self,postep):
        postep("instytucje",2,2)
        postep("kierunki",3,3)
        self.ustaw_date(self.chwila)
        return {"instytucje":2,"kierunki":3,"warianty":4}

    def test_aktualizacja_dopiero_po_przekroczeniu_24_godzin(self):
        self.assertFalse(wymaga_aktualizacji(self.chwila-timedelta(days=1),self.chwila))
        self.assertTrue(wymaga_aktualizacji(self.chwila-timedelta(days=1,seconds=1),self.chwila))
        self.assertTrue(wymaga_aktualizacji(None,self.chwila))
        for wiek in [timedelta(hours=23),timedelta(days=1)]:
            self.ustaw_date(self.chwila-wiek)
            with patch("app.synchronizacja.synchronizuj_katalog") as pobieranie:
                self.assertFalse(sprawdz_i_aktualizuj(self.chwila))
                pobieranie.assert_not_called()

    def test_stary_katalog_pobierany_raz_i_bez_konta(self):
        self.ustaw_date(self.chwila-timedelta(days=2))
        with patch("app.synchronizacja.synchronizuj_katalog",side_effect=self.importer) as pobieranie:
            self.assertTrue(sprawdz_i_aktualizuj(self.chwila))
            self.assertFalse(sprawdz_i_aktualizuj(self.chwila+timedelta(minutes=1)))
            pobieranie.assert_called_once()
        self.assertEqual(stan_synchronizacji()["stan"],"aktualne")
        with polaczenie() as baza:
            self.assertEqual(baza.execute("SELECT COUNT(*) FROM uzytkownicy").fetchone()[0],0)

    def test_zestaw_startowy_nie_zastepuje_pelnego_importu(self):
        self.assertIsNone(stan_synchronizacji()["ostatni_import"])
        with patch("app.synchronizacja.synchronizuj_katalog",side_effect=self.importer) as pobieranie:
            self.assertTrue(sprawdz_i_aktualizuj(self.chwila))
            pobieranie.assert_called_once()

    def test_blad_zachowuje_date_katalog_i_odstep_ponowien(self):
        stara=self.chwila-timedelta(days=2)
        self.ustaw_date(stara)
        with polaczenie() as baza:
            przed=baza.execute("SELECT COUNT(*) FROM kierunki_studiow").fetchone()[0]
        with patch("app.synchronizacja.teraz",return_value=self.chwila):
            with patch("app.synchronizacja.synchronizuj_katalog",side_effect=ValueError("API niedostepne")):
                self.assertFalse(sprawdz_i_aktualizuj())
        self.assertEqual(stan_synchronizacji()["ostatni_import"],stara)
        self.assertEqual(stan_synchronizacji()["stan"],"blad")
        with patch("app.synchronizacja.synchronizuj_katalog") as pobieranie:
            self.assertFalse(sprawdz_i_aktualizuj(self.chwila+timedelta(minutes=14)))
            pobieranie.assert_not_called()
        self.chwila+=timedelta(minutes=16)
        with patch("app.synchronizacja.synchronizuj_katalog",side_effect=self.importer):
            self.assertTrue(sprawdz_i_aktualizuj(self.chwila))
        with polaczenie() as baza:
            self.assertEqual(baza.execute("SELECT COUNT(*) FROM kierunki_studiow").fetchone()[0],przed)

    def test_rownolegly_przebieg_nie_dubluje_pobierania(self):
        zaczeto,koniec=threading.Event(),threading.Event()
        wynik=[]
        def wolny_import(postep):
            zaczeto.set()
            if not koniec.wait(5): raise TimeoutError("test")
            return self.importer(postep)
        with patch("app.synchronizacja.synchronizuj_katalog",side_effect=wolny_import) as pobieranie:
            watek=threading.Thread(target=lambda:wynik.append(sprawdz_i_aktualizuj(self.chwila)))
            watek.start()
            try:
                self.assertTrue(zaczeto.wait(5))
                self.assertFalse(sprawdz_i_aktualizuj(self.chwila))
            finally:
                koniec.set(); watek.join(5)
            pobieranie.assert_called_once()
        self.assertEqual(wynik,[True])

    def test_wygasla_blokada_nie_blokuje_po_restarcie(self):
        stary=_zajmij_import(self.chwila-timedelta(minutes=16))
        nowy=_zajmij_import(self.chwila)
        self.assertIsNotNone(nowy)
        self.assertNotEqual(stary,nowy)
        with self.assertRaises(RuntimeError): _postep(stary,"kierunki",1,10)

    def test_historie_importu_odczytujemy_w_utc(self):
        self.ustaw_date(self.chwila-timedelta(days=2))
        with polaczenie() as baza:
            baza.execute("INSERT INTO historia_importow (rodzaj,zakres,adres_zrodla,data_pobrania,data_importu) VALUES ('api','pelny','https://example.test',?,?)",(self.chwila.isoformat(),self.chwila.isoformat()))
        self.assertEqual(stan_synchronizacji()["ostatni_import"],self.chwila)
        with patch("app.synchronizacja.synchronizuj_katalog") as pobieranie:
            self.assertFalse(sprawdz_i_aktualizuj(self.chwila))
            pobieranie.assert_not_called()

    def test_pierwsza_rejestracja_nie_wymaga_admina(self):
        identyfikator=utworz_konto("pierwszy@example.test","Haslo-testowe-123!")
        with polaczenie() as baza:
            self.assertEqual(baza.execute("SELECT rola FROM uzytkownicy WHERE id=?",(identyfikator,)).fetchone()[0],"kandydat")
