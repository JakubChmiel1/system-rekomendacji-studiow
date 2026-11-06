"""Import publicznego katalogu RAD-on/POL-on do SQLite."""

import json
import http.client
import base64
import binascii
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from app.database import polaczenie
from app.konta import wymagaj_administratora

ADRES_API = "https://radon.nauka.gov.pl/opendata/polon/courses"
ADRES_INSTYTUCJI = "https://radon.nauka.gov.pl/opendata/polon/institutions"
ZESTAW_STARTOWY = Path(__file__).with_name("dane") / "kierunki_radon.json"


def teraz() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _wymagany_tekst(rekord: dict, klucz: str) -> str:
    wartosc = rekord.get(klucz)
    if not isinstance(wartosc, str) or not wartosc.strip():
        raise ValueError(f"Niekompletny rekord RAD-on: brak pola {klucz}.")
    return wartosc


def _liczba(wartosc, typ=float):
    return None if wartosc in (None, "") else typ(wartosc)


def _data_zrodla(wartosc) -> str | None:
    if wartosc in (None, ""):
        return None
    return datetime.fromtimestamp(int(wartosc) / 1000, timezone.utc).isoformat(timespec="milliseconds")


def _zapisz(baza, tabela: str, dane: dict) -> int:
    # Nazwy tabel i kolumn pochodza wylacznie ze stalych mapowan ponizej.
    kolumny = list(dane)
    aktualizacje = ", ".join(f"{kolumna} = excluded.{kolumna}" for kolumna in kolumny if kolumna != "id_radon")
    return baza.execute(
        f"INSERT INTO {tabela} ({', '.join(kolumny)}) VALUES ({', '.join('?' for _ in kolumny)}) "
        f"ON CONFLICT(id_radon) DO UPDATE SET {aktualizacje} RETURNING id",
        tuple(dane.values()),
    ).fetchone()[0]


def _uczelnia(baza, rekord: dict, data_pobrania: str, *, glowna=False) -> int:
    przedrostek = "mainInstitution" if glowna else "leadingInstitution"
    identyfikator = _wymagany_tekst(rekord, przedrostek + "Uuid")
    ta_sama = rekord.get("mainInstitutionUuid") == rekord.get("leadingInstitutionUuid")
    miasto = rekord.get("leadingInstitutionCity") if not glowna or ta_sama else None
    wojewodztwo = (rekord.get("leadingInstitutionVoivodeship") or rekord.get("leadingInstitutionVoiodeship")) if not glowna or ta_sama else None
    rodzaj = rekord.get("mainInstitutionKind") if glowna or ta_sama else None
    return baza.execute(
        "INSERT INTO uczelnie (id_radon, nazwa, miasto, wojewodztwo, rodzaj, data_pobrania) "
        "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(id_radon) DO UPDATE SET "
        "nazwa = excluded.nazwa, miasto = COALESCE(excluded.miasto, uczelnie.miasto), "
        "wojewodztwo = COALESCE(excluded.wojewodztwo, uczelnie.wojewodztwo), "
        "rodzaj = COALESCE(excluded.rodzaj, uczelnie.rodzaj), data_pobrania = excluded.data_pobrania RETURNING id",
        (identyfikator, _wymagany_tekst(rekord, przedrostek + "Name"), miasto, wojewodztwo, rodzaj, data_pobrania),
    ).fetchone()[0]


def _zapisz_dane_zrodlowe(baza, adres, identyfikator, rekord, data_pobrania, wersja=None):
    baza.execute(
        "INSERT INTO dane_zrodlowe_api (adres_api, id_radon, tresc_json, wersja_api, data_pobrania) "
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT(adres_api, id_radon) DO UPDATE SET "
        "tresc_json = excluded.tresc_json, wersja_api = excluded.wersja_api, data_pobrania = excluded.data_pobrania",
        (adres, identyfikator, json.dumps(rekord, ensure_ascii=False), wersja, data_pobrania),
    )


def _zapisz_rekordy(baza, rekordy: list, data_pobrania: str, wersja=None) -> tuple[int, int]:
    kierunki, warianty = set(), set()
    for rekord in rekordy:
        if not isinstance(rekord, dict):
            raise ValueError("Nieprawidlowy rekord RAD-on.")
        id_uczelni = _uczelnia(baza, rekord, data_pobrania)
        id_glownej = _uczelnia(baza, rekord, data_pobrania, glowna=True) if rekord.get("mainInstitutionUuid") else None
        id_radon = _wymagany_tekst(rekord, "courseUuid")
        _zapisz_dane_zrodlowe(baza, ADRES_API, id_radon, rekord, data_pobrania, wersja)
        id_kierunku = _zapisz(baza, "kierunki_studiow", {
            "id_radon": id_radon,
            "id_uczelni": id_uczelni,
            "id_uczelni_glownej": id_glownej,
            "nazwa": _wymagany_tekst(rekord, "courseName"),
            "poziom": _wymagany_tekst(rekord, "levelName"),
            "kod_poziomu": _wymagany_tekst(rekord, "levelCode"),
            "profil": rekord.get("profileName"),
            "kod_profilu": rekord.get("profileCode"),
            "status": _wymagany_tekst(rekord, "currentStatusName"),
            "kod_statusu": _wymagany_tekst(rekord, "currentStatusCode"),
            "kod_isced": rekord.get("iscedCode"),
            "nazwa_isced": rekord.get("iscedName"),
            "adres_zrodla": ADRES_API + "?" + urllib.parse.urlencode({"courseUuid": id_radon}),
            "data_zmiany_zrodla": _data_zrodla(rekord.get("lastRefresh")),
            "data_pobrania": data_pobrania,
        })
        kierunki.add(id_radon)
        # Nie kasujemy starych wariantow: moga byc zapisane w ulubionych.
        baza.execute(
            "UPDATE warianty_studiow SET kod_statusu = 'brak', status = 'brak w ostatnim odczycie' WHERE id_kierunku = ?",
            (id_kierunku,),
        )
        for wariant in rekord.get("courseInstances") or []:
            id_wariantu = _wymagany_tekst(wariant, "courseInstanceUuid")
            _zapisz(baza, "warianty_studiow", {
                "id_radon": id_wariantu,
                "id_kierunku": id_kierunku,
                "nazwa": wariant.get("courseName") or rekord["courseName"],
                "tryb_studiow": _wymagany_tekst(wariant, "formName"),
                "kod_trybu": _wymagany_tekst(wariant, "formCode"),
                "tytul_zawodowy": wariant.get("titleName"),
                "jezyk": wariant.get("languageName"),
                "kod_jezyka": wariant.get("languageCode"),
                "liczba_semestrow": _liczba(wariant.get("numberOfSemesters"), int),
                "punkty_ects": _liczba(wariant.get("ects")),
                "status": _wymagany_tekst(wariant, "statusName"),
                "kod_statusu": _wymagany_tekst(wariant, "statusCode"),
                "data_rozpoczecia": wariant.get("educationStartDate"),
                "data_likwidacji": wariant.get("liquidationDate"),
                "data_pobrania": data_pobrania,
            })
            warianty.add(id_wariantu)
        baza.execute("DELETE FROM dyscypliny_kierunkow WHERE id_kierunku = ?", (id_kierunku,))
        for dyscyplina in rekord.get("disciplines") or []:
            baza.execute(
                "INSERT INTO dyscypliny_kierunkow (id_kierunku, kod_dyscypliny, nazwa_dyscypliny, udzial_procentowy, wiodaca) "
                "VALUES (?, ?, ?, ?, ?)",
                (id_kierunku, _wymagany_tekst(dyscyplina, "disciplineCode"),
                 _wymagany_tekst(dyscyplina, "disciplineName"), _liczba(dyscyplina.get("disciplinePercentageShare")),
                 int(dyscyplina.get("disciplineLeading") == "Tak")),
            )
    return len(kierunki), len(warianty)


def _historia(baza, rodzaj, adres, liczby, data_pobrania, id_administratora=None):
    baza.execute(
        "INSERT INTO historia_importow (id_administratora, rodzaj, adres_zrodla, liczba_kierunkow, liczba_wariantow, data_pobrania) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (id_administratora, rodzaj, adres, *liczby, data_pobrania),
    )


def wczytaj_zestaw_startowy() -> None:
    with polaczenie() as baza:
        baza.execute("BEGIN IMMEDIATE")
        if baza.execute("SELECT 1 FROM metadane_aplikacji WHERE klucz = 'zestaw_startowy_radon'").fetchone():
            return
        zestaw = json.loads(ZESTAW_STARTOWY.read_text(encoding="utf-8"))
        liczby = _zapisz_rekordy(baza, zestaw["dane"]["results"], zestaw["data_pobrania"], zestaw["dane"].get("version"))
        _historia(baza, "zestaw_startowy", zestaw["adres_zrodla"], liczby, zestaw["data_pobrania"])
        baza.execute("INSERT INTO metadane_aplikacji (klucz, wartosc) VALUES ('zestaw_startowy_radon', ?)", (zestaw["data_pobrania"],))


def importuj_z_api(id_administratora: int, liczba_stron: int = 1) -> tuple[int, int]:
    wymagaj_administratora(id_administratora)
    if not 1 <= liczba_stron <= 100:
        raise ValueError("Liczba stron musi wynosic od 1 do 100.")
    # Bez filtra statusu pobieramy takze informacje o zamknietych kierunkach.
    # Import jest czesciowy; nie usuwa rekordow nieobecnych na pobranych stronach.
    rekordy = []
    adres = ADRES_API
    data_pobrania = teraz()
    try:
        # Kody sprawdzone w API: 2 = I stopien, 1 = jednolite magisterskie.
        for poziom in ("2", "1"):
            parametry = {"resultNumbers": 100, "levelCode": poziom}
            tokeny = set()
            for _ in range(liczba_stron):
                zapytanie = urllib.request.Request(
                    ADRES_API + "?" + urllib.parse.urlencode(parametry),
                    headers={"Accept": "application/json", "User-Agent": "RekomendacjeStudiow/1.0"},
                )
                with urllib.request.urlopen(zapytanie, timeout=25) as odpowiedz:
                    dane = json.load(odpowiedz)
                if not isinstance(dane, dict) or not isinstance(dane.get("results"), list):
                    raise ValueError("Nieprawidlowy format odpowiedzi RAD-on.")
                wyniki = dane["results"]
                rekordy.extend(wyniki)
                token = dane.get("pagination", {}).get("token")
                if not wyniki or not token:
                    break
                if token in tokeny:
                    raise ValueError("API zwrocilo powtorzony token strony. Import przerwany.")
                tokeny.add(token)
                parametry["token"] = token
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as blad:
        raise ValueError("Nie udalo sie pobrac danych RAD-on. Zapisany katalog pozostaje dostepny.") from blad
    with polaczenie() as baza:
        baza.execute("BEGIN IMMEDIATE")
        konto = baza.execute("SELECT rola, aktywny FROM uzytkownicy WHERE id = ?", (id_administratora,)).fetchone()
        if not konto or konto["rola"] != "administrator" or not konto["aktywny"]:
            raise PermissionError("Ta operacja wymaga konta administratora.")
        try:
            liczby = _zapisz_rekordy(baza, rekordy, data_pobrania)
        except (sqlite3.IntegrityError, TypeError, OverflowError) as blad:
            raise ValueError("Dane RAD-on nie pasuja do schematu. Import wycofany.") from blad
        _historia(baza, "api", adres, liczby, data_pobrania, id_administratora)
    return liczby


def _pobierz_strone(adres: str) -> dict:
    for proba in range(3):
        try:
            zapytanie = urllib.request.Request(
                adres, headers={"Accept": "application/json", "User-Agent": "RekomendacjeStudiow/1.0"}
            )
            with urllib.request.urlopen(zapytanie, timeout=30) as odpowiedz:
                dane = json.load(odpowiedz)
            if not isinstance(dane, dict) or not isinstance(dane.get("results"), list):
                raise ValueError("Nieprawidlowy format odpowiedzi RAD-on.")
            return dane
        except urllib.error.HTTPError as blad:
            if (blad.code != 429 and blad.code < 500) or proba == 2:
                raise ValueError(f"API RAD-on jest niedostepne (HTTP {blad.code}). Sprobuj ponownie pozniej.") from blad
        except (urllib.error.URLError, OSError, http.client.HTTPException) as blad:
            if proba == 2:
                raise ValueError("Nie udalo sie pobrac wszystkich danych RAD-on. Poprzednia baza pozostaje bez zmian.") from blad
        except json.JSONDecodeError as blad:
            raise ValueError("API RAD-on zwrocilo nieprawidlowe dane. Import przerwany.") from blad
        time.sleep(2**proba)


def _token_z_nakladka(token, wyniki):
    # W sprawdzonej wersji RAD-on token koduje lastRefresh ostatniego rekordu,
    # a nastepna strona pomija inne rekordy o identycznym czasie. Cofniecie o
    # 1 ms tworzy nakladke stron; powtorzone identyfikatory deduplikujemy.
    # Nie zmieniamy tokenow w innym formacie, np. po aktualizacji API.
    try:
        czas = base64.b64decode(token, validate=True).decode("ascii")
        if wyniki and czas == str(wyniki[-1].get("lastRefresh")) and czas.isdigit():
            return base64.b64encode(str(int(czas) - 1).encode("ascii")).decode("ascii")
    except (ValueError, TypeError, UnicodeError, binascii.Error):
        pass
    return token


def _pobierz_wszystkie_strony(adres_api, klucz_id, etap, postep):
    parametry = {"resultNumbers": 100}
    rekordy, tokeny = {}, set()
    oczekiwane, wersja = None, None
    while True:
        dane = _pobierz_strone(adres_api + "?" + urllib.parse.urlencode(parametry))
        if not isinstance(dane.get("pagination", {}), dict):
            raise ValueError("API zwrocilo nieprawidlowe informacje o stronach.")
        paginacja = dane.get("pagination", {})
        if paginacja.get("maxCount") is not None:
            oczekiwane = int(paginacja["maxCount"])
        wersja = dane.get("version")
        for rekord in dane["results"]:
            if not isinstance(rekord, dict):
                raise ValueError("API zwrocilo nieprawidlowy rekord.")
            rekordy[_wymagany_tekst(rekord, klucz_id)] = rekord
        if postep:
            postep(etap, len(rekordy), oczekiwane)
        if oczekiwane is not None and len(rekordy) >= oczekiwane:
            break
        token = _token_z_nakladka(paginacja.get("token"), dane["results"])
        if not dane["results"] or not token:
            if oczekiwane is not None and len(rekordy) < oczekiwane:
                raise ValueError(f"API zwrocilo niepelny katalog: {len(rekordy)} z {oczekiwane} rekordow. Import przerwany.")
            break
        if token in tokeny:
            raise ValueError("API powtorzylo token strony. Import przerwany, aby nie zapisac niepelnych danych.")
        tokeny.add(token)
        parametry["token"] = token
    return list(rekordy.values()), wersja


def _zapisz_instytucje(baza, rekordy, data_pobrania, wersja):
    for rekord in rekordy:
        identyfikator = _wymagany_tekst(rekord, "institutionUuid")
        _zapisz_dane_zrodlowe(baza, ADRES_INSTYTUCJI, identyfikator, rekord, data_pobrania, wersja)
        # Instytuty naukowe zostaja w danych zrodlowych; do katalogu uczelni
        # trafiaja uczelnie i podmioty powiazane z zaimportowanymi kierunkami.
        istnieje = baza.execute("SELECT 1 FROM uczelnie WHERE id_radon = ?", (identyfikator,)).fetchone()
        if not istnieje and not (rekord.get("iKindName") or "").casefold().startswith("uczelnia"):
            continue
        _zapisz(baza, "uczelnie", {
            "id_radon": identyfikator,
            "nazwa": _wymagany_tekst(rekord, "name"),
            "miasto": rekord.get("city"),
            "wojewodztwo": rekord.get("voivodeship"),
            "rodzaj": rekord.get("iKindName"),
            "kraj": rekord.get("country"),
            "ulica": rekord.get("street"),
            "numer_budynku": rekord.get("bNumber"),
            "numer_lokalu": rekord.get("lNumber"),
            "kod_pocztowy": rekord.get("postalCd"),
            "adres_strony": rekord.get("www"),
            "email": rekord.get("eMail"),
            "telefon": rekord.get("phone"),
            "nip": rekord.get("nip"),
            "regon": rekord.get("regon"),
            "krs": rekord.get("krs"),
            "status": rekord.get("status"),
            "kod_statusu": rekord.get("statusCode"),
            "data_zmiany_zrodla": _data_zrodla(rekord.get("lastRefresh")),
            "data_pobrania": data_pobrania,
        })


def importuj_wszystko(id_administratora: int | None = None, postep=None) -> dict:
    """Zachowany interfejs starszych narzedzi; aktualizacja aplikacji dziala w tle."""
    wymagaj_administratora(id_administratora)
    return _importuj_katalog(postep, id_administratora)


def synchronizuj_katalog(postep=None) -> dict:
    """Import publicznych danych dla wewnetrznej uslugi synchronizacji Dockera."""
    return _importuj_katalog(postep)


def _importuj_katalog(postep=None, id_administratora=None) -> dict:
    data_pobrania = teraz()
    instytucje, wersja_instytucji = _pobierz_wszystkie_strony(ADRES_INSTYTUCJI, "institutionUuid", "instytucje", postep)
    kierunki, wersja_kierunkow = _pobierz_wszystkie_strony(ADRES_API, "courseUuid", "kierunki", postep)
    if postep:
        postep("zapis", 0, 1)
    try:
        with polaczenie() as baza:
            baza.execute("BEGIN IMMEDIATE")
            if id_administratora is not None:
                konto = baza.execute("SELECT rola, aktywny FROM uzytkownicy WHERE id = ?", (id_administratora,)).fetchone()
                if not konto or konto["rola"] != "administrator" or not konto["aktywny"]:
                    raise PermissionError("Ta operacja wymaga konta administratora.")
            liczby = _zapisz_rekordy(baza, kierunki, data_pobrania, wersja_kierunkow)
            _zapisz_instytucje(baza, instytucje, data_pobrania, wersja_instytucji)
            baza.execute(
                "INSERT INTO historia_importow (id_administratora, rodzaj, zakres, adres_zrodla, liczba_instytucji, data_pobrania) "
                "VALUES (?, 'api', 'pelny', ?, ?, ?)",
                (id_administratora, ADRES_INSTYTUCJI, len(instytucje), data_pobrania),
            )
            baza.execute(
                "INSERT INTO historia_importow (id_administratora, rodzaj, zakres, adres_zrodla, liczba_kierunkow, liczba_wariantow, data_pobrania) "
                "VALUES (?, 'api', 'pelny', ?, ?, ?, ?)",
                (id_administratora, ADRES_API, *liczby, data_pobrania),
            )
            baza.execute(
                "INSERT INTO metadane_aplikacji (klucz, wartosc) VALUES ('ostatni_pelny_import', ?) "
                "ON CONFLICT(klucz) DO UPDATE SET wartosc = excluded.wartosc", (teraz(),),
            )
    except (sqlite3.IntegrityError, TypeError, OverflowError) as blad:
        raise ValueError("Dane API nie pasuja do schematu. Caly import wycofano; poprzednia baza pozostaje bez zmian.") from blad
    if postep:
        postep("zapis", 1, 1)
    return {"instytucje": len(instytucje), "kierunki": liczby[0], "warianty": liczby[1]}


def pobierz_katalog(szukaj: str = "") -> list[dict]:
    with polaczenie() as baza:
        wiersze = baza.execute(
            "SELECT w.id, w.nazwa AS kierunek, u.nazwa AS uczelnia, u.miasto AS miasto_uczelni, "
            "k.poziom, w.tryb_studiow, w.jezyk, w.tytul_zawodowy, w.liczba_semestrow, k.data_pobrania "
            "FROM warianty_studiow w JOIN kierunki_studiow k ON k.id = w.id_kierunku "
            "JOIN uczelnie u ON u.id = k.id_uczelni "
            "WHERE k.kod_statusu = '3' AND w.kod_statusu = '3' AND k.kod_poziomu IN ('2', '1') "
            "AND (malymi_literami(w.nazwa) LIKE ? OR malymi_literami(u.nazwa) LIKE ? OR malymi_literami(u.miasto) LIKE ?) "
            "ORDER BY w.nazwa, u.nazwa, w.tryb_studiow",
            tuple([f"%{szukaj.strip().casefold()}%"] * 3),
        ).fetchall()
    return [dict(wiersz) for wiersz in wiersze]
