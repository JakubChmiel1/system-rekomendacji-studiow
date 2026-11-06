"""Odczyt i zapis danych konkretnego konta. Wszystkie zapytania sa parametryzowane."""

import json
import math
from datetime import datetime, timezone

from app.database import polaczenie
from app.konta import pobierz_konto, wymagaj_administratora
from app.ustawienia import OBSZARY, PYTANIA, PRZEDMIOTY, POZIOMY, STRONY, TRYBY, WOJEWODZTWA


def teraz():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def tekst_komorki(wartosc):
    if wartosc is None or isinstance(wartosc,float) and not math.isfinite(wartosc):
        return ""
    return str(wartosc).strip()


def wymagaj_konta(identyfikator):
    if not pobierz_konto(identyfikator):
        raise PermissionError("Zaloguj się ponownie.")


def pobierz_profil(identyfikator) -> dict:
    wymagaj_konta(identyfikator)
    with polaczenie() as baza:
        baza.execute("INSERT OR IGNORE INTO profile_kandydatow (id_uzytkownika) VALUES (?)", (identyfikator,))
        return dict(baza.execute("SELECT * FROM profile_kandydatow WHERE id_uzytkownika=?", (identyfikator,)).fetchone())


def pobierz_wyniki(identyfikator) -> list[dict]:
    with polaczenie() as baza:
        return [dict(x) for x in baza.execute("SELECT przedmiot,poziom,wynik_procentowy,rok_matury FROM wyniki_matur WHERE id_uzytkownika=? ORDER BY przedmiot,poziom", (identyfikator,))]


def pobierz_kwalifikacje(identyfikator) -> list[dict]:
    with polaczenie() as baza:
        return [dict(x) for x in baza.execute("SELECT kod_kwalifikacji,nazwa_kwalifikacji FROM kwalifikacje_kandydatow WHERE id_uzytkownika=? ORDER BY kod_kwalifikacji", (identyfikator,))]


def zapisz_profil(identyfikator, imie, typ_szkoly, tryb, kompletne, wyniki, kwalifikacje):
    wymagaj_konta(identyfikator)
    if len(imie.strip()) > 80 or tryb not in ["Bez preferencji", *TRYBY]:
        raise ValueError("Sprawdź imię i wybrany tryb studiów.")
    poprawne, unikalne = [], set()
    for wiersz in wyniki:
        przedmiot = tekst_komorki(wiersz.get("przedmiot"))
        if not przedmiot:
            if tekst_komorki(wiersz.get("wynik_procentowy")):
                raise ValueError("Przy każdym wyniku wybierz przedmiot.")
            continue
        poziom = wiersz.get("poziom")
        if przedmiot not in PRZEDMIOTY or poziom not in POZIOMY:
            raise ValueError("Wybierz przedmiot i poziom z listy.")
        try:
            wynik, rok = float(wiersz["wynik_procentowy"]), float(wiersz["rok_matury"])
        except (ValueError, TypeError, KeyError):
            raise ValueError("Każdy wynik wymaga wartości procentowej i roku matury.")
        if not math.isfinite(wynik) or not 0 <= wynik <= 100 or not math.isfinite(rok) or not rok.is_integer() or not 2000 <= rok <= 2100:
            raise ValueError("Wynik musi wynosić 0–100%, a rok 2000–2100.")
        klucz = (przedmiot, poziom, int(rok))
        if klucz in unikalne:
            raise ValueError("Ten sam przedmiot, poziom i rok występują dwukrotnie.")
        unikalne.add(klucz)
        poprawne.append((identyfikator, przedmiot, poziom, wynik, int(rok)))
    kwal, kody = [], set()
    for wiersz in kwalifikacje:
        kod = tekst_komorki(wiersz.get("kod_kwalifikacji")).upper()
        nazwa = tekst_komorki(wiersz.get("nazwa_kwalifikacji"))
        if not kod and not nazwa:
            continue
        if not kod or not nazwa or len(kod) > 30 or len(nazwa) > 250:
            raise ValueError("Podaj kod i nazwę każdej kwalifikacji.")
        if kod in kody:
            raise ValueError("Kod kwalifikacji nie może się powtarzać.")
        kody.add(kod)
        kwal.append((identyfikator, kod, nazwa))
    with polaczenie() as baza:
        baza.execute("INSERT OR IGNORE INTO profile_kandydatow (id_uzytkownika) VALUES (?)", (identyfikator,))
        baza.execute("UPDATE profile_kandydatow SET imie=?,typ_szkoly=?,tryb_studiow=?,matura_uzupelniona=?,data_aktualizacji=? WHERE id_uzytkownika=?", (imie.strip(),typ_szkoly,tryb,int(kompletne),teraz(),identyfikator))
        baza.execute("DELETE FROM wyniki_matur WHERE id_uzytkownika=?", (identyfikator,))
        baza.executemany("INSERT INTO wyniki_matur (id_uzytkownika,przedmiot,poziom,wynik_procentowy,rok_matury) VALUES (?,?,?,?,?)", poprawne)
        baza.execute("DELETE FROM kwalifikacje_kandydatow WHERE id_uzytkownika=?", (identyfikator,))
        baza.executemany("INSERT INTO kwalifikacje_kandydatow (id_uzytkownika,kod_kwalifikacji,nazwa_kwalifikacji) VALUES (?,?,?)", kwal)


def zapisz_lokalizacje(identyfikator, miejsce, szerokosc, dlugosc, dystans=300):
    wymagaj_konta(identyfikator)
    if not -90 <= float(szerokosc) <= 90 or not -180 <= float(dlugosc) <= 180 or not 0 <= int(dystans) <= 1500:
        raise ValueError("Wskaż poprawną lokalizację i dystans.")
    with polaczenie() as baza:
        baza.execute("INSERT OR IGNORE INTO profile_kandydatow (id_uzytkownika) VALUES (?)", (identyfikator,))
        baza.execute("UPDATE profile_kandydatow SET miejsce_zamieszkania=?,szerokosc=?,dlugosc=?,maksymalny_dystans=?,data_aktualizacji=? WHERE id_uzytkownika=?", (miejsce[:150],float(szerokosc),float(dlugosc),int(dystans),teraz(),identyfikator))


def pobierz_ankiete(identyfikator):
    with polaczenie() as baza:
        wiersze = baza.execute("SELECT kod_pytania,wartosc_odpowiedzi FROM odpowiedzi_ankiety WHERE id_uzytkownika=?", (identyfikator,)).fetchall()
    wynik = {}
    for wiersz in wiersze:
        try:
            wynik[wiersz[0]] = json.loads(wiersz[1])
        except json.JSONDecodeError:
            wynik[wiersz[0]] = wiersz[1]
    return wynik


def zapisz_ankiete(identyfikator, odpowiedzi):
    wymagaj_konta(identyfikator)
    if set(odpowiedzi) != set(PYTANIA):
        raise ValueError("Uzupełnij wszystkie pytania ankiety.")
    for kod, (_, opcje) in PYTANIA.items():
        wartosc = odpowiedzi[kod]
        if kod in ["zainteresowania", "mocne_strony", "slabe_strony"]:
            dozwolone = set(OBSZARY) if kod == "zainteresowania" else set(opcje)
            if not isinstance(wartosc, list) or len(wartosc) > 6 or any(x not in dozwolone for x in wartosc):
                raise ValueError("Wybierz maksymalnie sześć odpowiedzi z listy.")
            if kod in ["zainteresowania", "mocne_strony"] and not wartosc:
                raise ValueError("Wybierz co najmniej jedno zainteresowanie i jedną mocną stronę.")
        elif opcje == "tekst":
            if not isinstance(wartosc,str) or len(wartosc) > 1500:
                raise ValueError("Dodatkowy opis może mieć do 1500 znaków.")
        elif wartosc not in opcje:
            raise ValueError("Wybierz odpowiedzi z dostępnych opcji.")
    with polaczenie() as baza:
        baza.execute("DELETE FROM odpowiedzi_ankiety WHERE id_uzytkownika=?", (identyfikator,))
        baza.executemany("INSERT INTO odpowiedzi_ankiety (id_uzytkownika,kod_pytania,wartosc_odpowiedzi) VALUES (?,?,?)", [(identyfikator,kod,json.dumps(wartosc,ensure_ascii=False)) for kod,wartosc in odpowiedzi.items()])
        baza.execute("INSERT INTO wersje_ankiety (id_uzytkownika,odpowiedzi_json) VALUES (?,?)", (identyfikator,json.dumps(odpowiedzi,ensure_ascii=False)))


def pobierz_preferencje_czatu(identyfikator):
    with polaczenie() as baza:
        wiersz = baza.execute("SELECT preferencje_json FROM preferencje_czatu WHERE id_uzytkownika=?", (identyfikator,)).fetchone()
    return json.loads(wiersz[0]) if wiersz else {}


def waliduj_preferencje(zmiany):
    if not isinstance(zmiany, dict):
        return {}
    wynik = {}
    for klucz, opcje in {"preferowane_obszary": list(OBSZARY), "wykluczone_obszary": list(OBSZARY), "preferowane_wojewodztwa": WOJEWODZTWA}.items():
        if klucz in zmiany and isinstance(zmiany[klucz], list):
            wynik[klucz] = list(dict.fromkeys(x for x in zmiany[klucz] if isinstance(x,str) and x in opcje))[:6]
    for klucz, opcje in {"preferowany_tryb": ["Bez preferencji",*TRYBY], "preferowany_jezyk": ["Bez preferencji","polski","angielski"], "priorytet": ["zainteresowania","wyniki","odleglosc","zrownowazony"]}.items():
        if zmiany.get(klucz) in opcje:
            wynik[klucz] = zmiany[klucz]
    dystans = zmiany.get("maksymalny_dystans")
    if isinstance(dystans, (int,float)) and not isinstance(dystans,bool) and math.isfinite(dystans) and 0 <= dystans <= 1500:
        wynik["maksymalny_dystans"] = int(dystans)
    return wynik


def zapisz_preferencje_czatu(identyfikator, zmiany):
    wymagaj_konta(identyfikator)
    poprawne = waliduj_preferencje(zmiany)
    obecne = pobierz_preferencje_czatu(identyfikator)
    obecne.update(poprawne)
    if "preferowane_obszary" in poprawne and "wykluczone_obszary" not in poprawne:
        obecne["wykluczone_obszary"] = [x for x in obecne.get("wykluczone_obszary",[]) if x not in poprawne["preferowane_obszary"]]
    if "wykluczone_obszary" in poprawne:
        obecne["preferowane_obszary"] = [x for x in obecne.get("preferowane_obszary",[]) if x not in poprawne["wykluczone_obszary"]]
    with polaczenie() as baza:
        baza.execute("INSERT INTO preferencje_czatu (id_uzytkownika,preferencje_json,data_aktualizacji) VALUES (?,?,?) ON CONFLICT(id_uzytkownika) DO UPDATE SET preferencje_json=excluded.preferencje_json,data_aktualizacji=excluded.data_aktualizacji", (identyfikator,json.dumps(obecne,ensure_ascii=False),teraz()))
    return poprawne


def wyczysc_preferencje_czatu(identyfikator):
    wymagaj_konta(identyfikator)
    with polaczenie() as baza:
        baza.execute("DELETE FROM preferencje_czatu WHERE id_uzytkownika=?", (identyfikator,))


def pobierz_ulubione(identyfikator) -> set[int]:
    with polaczenie() as baza:
        return {x[0] for x in baza.execute("SELECT id_wariantu FROM ulubione WHERE id_uzytkownika=?", (identyfikator,))}


def przelacz_ulubione(identyfikator, id_wariantu):
    wymagaj_konta(identyfikator)
    with polaczenie() as baza:
        baza.execute("BEGIN IMMEDIATE")
        istnieje = baza.execute("SELECT 1 FROM ulubione WHERE id_uzytkownika=? AND id_wariantu=?", (identyfikator,id_wariantu)).fetchone()
        if istnieje:
            baza.execute("DELETE FROM ulubione WHERE id_uzytkownika=? AND id_wariantu=?", (identyfikator,id_wariantu))
        else:
            baza.execute("INSERT INTO ulubione (id_uzytkownika,id_wariantu) VALUES (?,?)", (identyfikator,id_wariantu))


def pobierz_wiadomosci(identyfikator, limit=20):
    with polaczenie() as baza:
        rows = baza.execute("SELECT id,rola,tresc FROM wiadomosci_czatu WHERE id_uzytkownika=? ORDER BY id DESC LIMIT ?", (identyfikator,min(int(limit),100))).fetchall()
    return [dict(x) for x in reversed(rows)]


def zapisz_wiadomosc(identyfikator, rola, tresc):
    wymagaj_konta(identyfikator)
    if rola not in ["uzytkownik","asystent"] or not str(tresc).strip() or len(tresc) > 12000:
        raise ValueError("Wiadomość jest pusta lub zbyt długa.")
    with polaczenie() as baza:
        baza.execute("INSERT INTO wiadomosci_czatu (id_uzytkownika,rola,tresc) VALUES (?,?,?)", (identyfikator,rola,tresc))


def wyczysc_rozmowe(identyfikator):
    wymagaj_konta(identyfikator)
    with polaczenie() as baza:
        baza.execute("DELETE FROM wiadomosci_czatu WHERE id_uzytkownika=?", (identyfikator,))


def pobierz_wymagania(rok):
    with polaczenie() as baza:
        return [dict(x) for x in baza.execute("SELECT * FROM wymagania_rekrutacyjne WHERE rok_rekrutacji=? AND zweryfikowane=1", (rok,))]


def zapisz_wymaganie(admin, kierunek, rok, grupa, przedmiot, poziom, minimum, adres, potwierdzone):
    wymagaj_administratora(admin)
    if przedmiot not in PRZEDMIOTY or poziom not in POZIOMY or not 0 <= float(minimum) <= 100 or not 2020 <= int(rok) <= 2100 or not 1 <= int(grupa) <= 30:
        raise ValueError("Sprawdź przedmiot, poziom, rok i minimalny wynik.")
    if not adres.startswith("https://") or len(adres) > 2000 or not potwierdzone:
        raise ValueError("Podaj adres HTTPS źródła uczelni i potwierdź sprawdzenie zasad.")
    with polaczenie() as baza:
        baza.execute("INSERT INTO wymagania_rekrutacyjne (id_kierunku,rok_rekrutacji,grupa,przedmiot,poziom,minimalny_wynik,adres_zrodla,zweryfikowane) VALUES (?,?,?,?,?,?,?,1) ON CONFLICT(id_kierunku,rok_rekrutacji,grupa,przedmiot,poziom) DO UPDATE SET minimalny_wynik=excluded.minimalny_wynik,adres_zrodla=excluded.adres_zrodla,zweryfikowane=1", (int(kierunek),int(rok),int(grupa),przedmiot,poziom,float(minimum),adres))
