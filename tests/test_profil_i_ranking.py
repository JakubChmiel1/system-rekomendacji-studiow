import copy
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from app import dane
from app.database import initialize_database, polaczenie
from app.doradca import odpowiedz_doradcy, przygotuj_kontekst
from app.geo import dystans_km, znajdz_miasto
from app.konta import zapewnij_konto_admina, zaloguj, utworz_konto, skrot_hasla
from app.rekomendacje import pobierz_oferty, policz_dopasowanie, top_kierunki, filtruj
from app.ustawienia import PYTANIA


class TestProfiluIRankingu(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ,{"DATABASE_PATH":str(Path(self.folder.name)/"profil.db")})
        self.env.start()
        initialize_database()
        zapewnij_konto_admina()
        with polaczenie() as baza:
            self.admin=baza.execute("SELECT id FROM uzytkownicy WHERE email='admin'").fetchone()[0]
        self.user=utworz_konto("uczen@example.test","Haslo-testowe-123!")

    def tearDown(self):
        self.env.stop()
        self.folder.cleanup()

    def ankieta(self,obszar="technologie"):
        wynik={k:([] if k in ["zainteresowania","mocne_strony","slabe_strony"] else "" if opcje=="tekst" else opcje[0]) for k,(_,opcje) in PYTANIA.items()}
        wynik["zainteresowania"]=[obszar]
        wynik["mocne_strony"]=["Myślenie analityczne"]
        return wynik

    def wyniki(self):
        return [{"przedmiot":"matematyka","poziom":"rozszerzony","wynik_procentowy":90,"rok_matury":2026},{"przedmiot":"informatyka","poziom":"rozszerzony","wynik_procentowy":95,"rok_matury":2026}]

    def oferty(self):
        baza=pobierz_oferty()[0]
        wynik=[]
        for i,(nazwa,kod,obszar) in enumerate([("Informatyka","0613","technologie"),("Kierunek lekarski","0912","zdrowie"),("Prawo","0421","prawo")],1):
            oferta=dict(baza,id=i,id_kierunku=i,nazwa=nazwa,kod_isced=kod,obszar=obszar)
            wynik.append(oferta)
        return wynik

    def test_admin_demo_haslo_i_brak_resetowania_przy_starcie(self):
        self.assertEqual(zaloguj("admin","admin"),self.admin)
        with polaczenie() as baza:
            baza.execute("UPDATE uzytkownicy SET skrot_hasla=? WHERE id=?",(skrot_hasla("Nowe-testowe-haslo"),self.admin))
        zapewnij_konto_admina()
        self.assertIsNone(zaloguj("admin","admin"))
        self.assertEqual(zaloguj("admin","Nowe-testowe-haslo"),self.admin)

    def test_walidacja_email_hasla_i_blokada_prob(self):
        for email in ["bez-malpy","x@y","x@ y.pl"]:
            with self.assertRaises(ValueError): utworz_konto(email,"Haslo-testowe-123!")
        with self.assertRaises(ValueError): utworz_konto("nowy@example.test","admin")
        for _ in range(5): self.assertIsNone(zaloguj("uczen@example.test","zle"))
        with self.assertRaises(ValueError): zaloguj("uczen@example.test","Haslo-testowe-123!")

    def test_zapis_wynikow_jest_atomowy_i_odizolowany(self):
        dane.zapisz_profil(self.user,"Ola","Technikum","Bez preferencji",True,self.wyniki(),[])
        bledne=self.wyniki(); bledne[1]["wynik_procentowy"]=101
        with self.assertRaises(ValueError): dane.zapisz_profil(self.user,"Zmienione","Technikum","Bez preferencji",True,bledne,[])
        self.assertEqual(dane.pobierz_profil(self.user)["imie"],"Ola")
        self.assertEqual(len(dane.pobierz_wyniki(self.user)),2)
        self.assertEqual(dane.pobierz_wyniki(self.admin),[])

    def test_ponowne_wypelnienie_ankiety_zapisuje_najnowsza_wersje(self):
        dane.zapisz_ankiete(self.user,self.ankieta())
        dane.zapisz_ankiete(self.user,self.ankieta("prawo"))
        self.assertEqual(dane.pobierz_ankiete(self.user)["zainteresowania"],["prawo"])
        self.assertEqual(dane.pobierz_ankiete(self.admin),{})
        with polaczenie() as baza:
            self.assertEqual(baza.execute("SELECT COUNT(*) FROM wersje_ankiety WHERE id_uzytkownika=?",(self.user,)).fetchone()[0],2)
            self.assertEqual(baza.execute("SELECT COUNT(*) FROM odpowiedzi_ankiety WHERE id_uzytkownika=?",(self.user,)).fetchone()[0],len(PYTANIA))

    def test_ranking_top10_dedup_i_reakcja_na_zainteresowania(self):
        oferty=self.oferty()
        profil={"matura_uzupelniona":True}
        wyniki=policz_dopasowanie(oferty,profil,self.wyniki(),self.ankieta(),[],{})
        self.assertEqual(top_kierunki(wyniki)[0]["obszar"],"technologie")
        zmienione=policz_dopasowanie(oferty,profil,self.wyniki(),self.ankieta("prawo"),[],{"priorytet":"zainteresowania"})
        self.assertEqual(top_kierunki(zmienione)[0]["obszar"],"prawo")
        duplikaty=wyniki+[dict(wyniki[0],id=999)]
        self.assertEqual(len(top_kierunki(duplikaty)),3)
        self.assertTrue(all(0<=x["dopasowanie"]<=100 for x in wyniki))

    def test_brak_biologii_nie_jest_automatyczna_odmowa(self):
        oferty=self.oferty()
        wynik=policz_dopasowanie(oferty,{"matura_uzupelniona":True},self.wyniki(),self.ankieta("zdrowie"),[],{})[1]
        self.assertGreater(wynik["dopasowanie"],0)
        self.assertLessEqual(wynik["dopasowanie"],40)
        self.assertEqual(wynik["status_wymagan"],"brak_danych")

    def test_potwierdzone_wymagania_alternatywy_i_komplet_matury(self):
        oferty=self.oferty()
        reguly=[{"id_kierunku":2,"grupa":1,"przedmiot":p,"poziom":"rozszerzony","minimalny_wynik":30} for p in ["biologia","chemia"]]
        brak=policz_dopasowanie(oferty,{"matura_uzupelniona":True},self.wyniki(),self.ankieta(),[],{},reguly)[1]
        self.assertEqual(brak["dopasowanie"],0)
        self.assertNotIn(2,[x["id_kierunku"] for x in top_kierunki([brak])])
        niepelne=policz_dopasowanie(oferty,{"matura_uzupelniona":False},self.wyniki(),self.ankieta(),[],{},reguly)[1]
        self.assertEqual(niepelne["status_wymagan"],"do_sprawdzenia")
        chemia=self.wyniki()+[{"przedmiot":"chemia","poziom":"rozszerzony","wynik_procentowy":80,"rok_matury":2026}]
        pasuje=policz_dopasowanie(oferty,{"matura_uzupelniona":True},chemia,self.ankieta(),[],{},reguly)[1]
        self.assertEqual(pasuje["status_wymagan"],"spelnione")

    def test_odleglosc_i_filtry(self):
        warszawa=znajdz_miasto("Warszawa","mazowieckie")
        krakow=znajdz_miasto("Kraków","małopolskie")
        dystans=dystans_km(warszawa["szerokosc"],warszawa["dlugosc"],krakow["szerokosc"],krakow["dlugosc"])
        self.assertTrue(240<dystans<270)
        dane.zapisz_lokalizacje(self.user,"Warszawa",52.23,21.01,300)
        self.assertAlmostEqual(dane.pobierz_profil(self.user)["szerokosc"],52.23)
        oferta=policz_dopasowanie(self.oferty(),{},[],{},[],{})[0]
        oferta.update(wojewodztwo="mazowieckie",dystans_km=25)
        self.assertEqual(len(filtruj([oferta],{"szukaj":"INFORMATYKA","wojewodztwa":["mazowieckie"],"dystans":30})),1)
        self.assertEqual(filtruj([oferta],{"dystans":10}),[])

    def test_czat_zmienia_tylko_preferencje_wlasnego_konta(self):
        dane.zapisz_ankiete(self.user,self.ankieta())
        dane.zapisz_profil(self.user,"Ola","Technikum","Bez preferencji",True,self.wyniki(),[])
        oferty=policz_dopasowanie(self.oferty(),dane.pobierz_profil(self.user),self.wyniki(),self.ankieta(),[],{})
        odpowiedz={"odpowiedz":"Uwzględnię prawo.","strona":"Przegląd","zmiany_rankingu":{"preferowane_obszary":["prawo"]},"kierunki":[3,999999]}
        with patch("app.doradca.zapytaj_model",return_value=odpowiedz):
            wynik=odpowiedz_doradcy(self.user,"Preferuję prawo",top_kierunki(oferty),oferty,"Przegląd")
        self.assertEqual(dane.pobierz_preferencje_czatu(self.user)["preferowane_obszary"],["prawo"])
        self.assertEqual(dane.pobierz_preferencje_czatu(self.admin),{})
        self.assertEqual(dane.pobierz_ankiete(self.user)["zainteresowania"],["technologie"])
        self.assertEqual(dane.pobierz_wyniki(self.user),sorted(self.wyniki(),key=lambda x:(x["przedmiot"],x["poziom"])))
        self.assertNotIn(999999,wynik["kierunki"])
        self.assertEqual(len(dane.pobierz_wiadomosci(self.user)),2)
        self.assertEqual(dane.pobierz_wiadomosci(self.admin),[])
        kontekst=przygotuj_kontekst(self.user,"pomoc",[],oferty,"Przegląd")
        serial=json.dumps(kontekst)
        self.assertNotIn("skrot_hasla",serial)
        self.assertNotIn("uczen@example.test",serial)
        self.assertNotIn("szerokosc",serial)

    def test_preferencje_modelu_maja_ograniczone_pola(self):
        wynik=dane.zapisz_preferencje_czatu(self.user,{"rola":"administrator","id_uzytkownika":self.admin,"preferowane_obszary":["prawo","nieistniejacy"],"maksymalny_dystans":-100})
        self.assertEqual(wynik,{"preferowane_obszary":["prawo"]})

    def test_szybka_nawigacja_nie_wymaga_modelu(self):
        with patch("app.doradca.zapytaj_model") as model:
            wynik=odpowiedz_doradcy(self.user,"Gdzie mogę wpisać swoje wyniki matury?",[],[],"Przegląd")
            model.assert_not_called()
        self.assertEqual(wynik["strona"],"Mój profil")
        self.assertEqual(len(dane.pobierz_wiadomosci(self.user)),2)

    def test_migracja_wersji_2_zachowuje_profile(self):
        import sqlite3
        sciezka=str(Path(self.folder.name)/"wersja2.db")
        schemat=Path(__file__).with_name("dane")/"schemat_v2.sql"
        with sqlite3.connect(sciezka) as baza:
            baza.executescript(schemat.read_text(encoding="utf-8"))
            baza.execute("PRAGMA user_version=2")
            baza.execute("INSERT INTO metadane_aplikacji VALUES ('zestaw_startowy_radon','zapisany')")
            baza.execute("INSERT INTO uzytkownicy (id,email,skrot_hasla) VALUES (1,'stary@example.test','stary-skrot')")
            baza.execute("INSERT INTO profile_kandydatow (id_uzytkownika,imie) VALUES (1,'Ala')")
        with patch.dict(os.environ,{"DATABASE_PATH":sciezka}):
            initialize_database()
            self.assertEqual(dane.pobierz_profil(1)["imie"],"Ala")
            self.assertEqual(dane.pobierz_profil(1)["matura_uzupelniona"],0)
            dane.zapisz_lokalizacje(1,"Warszawa",52.23,21.01)
