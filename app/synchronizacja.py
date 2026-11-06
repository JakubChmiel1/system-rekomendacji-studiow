"""Samodzielna usluga Dockera: pelny import, gdy poprzedni ma ponad 24 godziny."""

import argparse
import json
import logging
import signal
import uuid
from datetime import datetime, timedelta, timezone
from threading import Event

from app.database import initialize_database, polaczenie
from app.radon import synchronizuj_katalog

WIEK_DANYCH = timedelta(days=1)
ODSTEP_PROB = timedelta(minutes=15)
CZAS_BLOKADY = timedelta(minutes=15)


def teraz():
    return datetime.now(timezone.utc)


def odczytaj_date(wartosc):
    try:
        wynik = datetime.fromisoformat(wartosc)
        return wynik.replace(tzinfo=timezone.utc) if wynik.tzinfo is None else wynik.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _metadane(baza, klucz):
    wiersz = baza.execute("SELECT wartosc FROM metadane_aplikacji WHERE klucz=?", (klucz,)).fetchone()
    return wiersz[0] if wiersz else None


def _zapisz(baza, klucz, wartosc):
    baza.execute("INSERT INTO metadane_aplikacji (klucz,wartosc) VALUES (?,?) ON CONFLICT(klucz) DO UPDATE SET wartosc=excluded.wartosc", (klucz,wartosc))


def _stan(baza):
    try:
        wynik = json.loads(_metadane(baza,"synchronizacja_stan") or "{}")
        return wynik if isinstance(wynik,dict) else {}
    except (ValueError,TypeError):
        return {}


def _ostatni_import(baza):
    historia = baza.execute("SELECT MAX(data_importu) FROM historia_importow WHERE rodzaj='api' AND zakres='pelny'").fetchone()[0]
    daty = [odczytaj_date(historia),odczytaj_date(_metadane(baza,"ostatni_pelny_import"))]
    return max((x for x in daty if x is not None),default=None)


def wymaga_aktualizacji(ostatni_import, chwila=None):
    chwila = chwila or teraz()
    return ostatni_import is None or chwila-ostatni_import > WIEK_DANYCH


def stan_synchronizacji():
    with polaczenie() as baza:
        stan = _stan(baza)
        ostatni = _ostatni_import(baza)
    stan["ostatni_import"] = ostatni
    blokada = odczytaj_date(stan.get("blokada_do"))
    if stan.get("stan")=="pobieranie" and (not blokada or blokada < teraz()):
        stan["stan"] = "oczekuje"
    return stan


def _zajmij_import(chwila):
    with polaczenie() as baza:
        baza.execute("BEGIN IMMEDIATE")
        if not wymaga_aktualizacji(_ostatni_import(baza),chwila):
            return None
        stan = _stan(baza)
        blokada = odczytaj_date(stan.get("blokada_do"))
        kolejna = odczytaj_date(stan.get("kolejna_proba"))
        if blokada and blokada > chwila or kolejna and kolejna > chwila:
            return None
        token = uuid.uuid4().hex
        _zapisz(baza,"synchronizacja_stan",json.dumps({"stan":"pobieranie","token":token,"rozpoczecie":chwila.isoformat(),"blokada_do":(chwila+CZAS_BLOKADY).isoformat()},ensure_ascii=False))
        return token


def _postep(token,etap,pobrano,razem):
    with polaczenie() as baza:
        baza.execute("BEGIN IMMEDIATE")
        stan = _stan(baza)
        if stan.get("token") != token:
            raise RuntimeError("Synchronizacja utracila blokade; import przerwany.")
        stan.update(etap=etap,pobrano=pobrano,razem=razem,blokada_do=(teraz()+CZAS_BLOKADY).isoformat())
        _zapisz(baza,"synchronizacja_stan",json.dumps(stan,ensure_ascii=False))


def sprawdz_i_aktualizuj(chwila=None):
    """Jeden przebieg; brak pracy dla swiezego katalogu lub aktywnego importu."""
    token = _zajmij_import(chwila or teraz())
    if token is None:
        return False
    logging.info("Katalog starszy niz doba albo brak pelnego importu. Pobieranie RAD-on.")
    try:
        wynik = synchronizuj_katalog(lambda etap,pobrano,razem:_postep(token,etap,pobrano,razem))
        with polaczenie() as baza:
            baza.execute("BEGIN IMMEDIATE")
            if _stan(baza).get("token") == token:
                _zapisz(baza,"synchronizacja_stan",json.dumps({"stan":"aktualne","zakonczenie":teraz().isoformat(),"wynik":wynik},ensure_ascii=False))
        logging.info("Import zakonczony: %s",wynik)
        return True
    except Exception as blad:
        # Importer zatwierdza oba zrodla razem. Nie zmieniamy daty ostatniego
        # udanego importu przy bledzie i nie uruchamiamy ciaglych ponowien.
        with polaczenie() as baza:
            baza.execute("BEGIN IMMEDIATE")
            if _stan(baza).get("token") == token:
                _zapisz(baza,"synchronizacja_stan",json.dumps({"stan":"blad","kolejna_proba":(teraz()+ODSTEP_PROB).isoformat(),"komunikat":"Nie udalo sie pobrac aktualnych danych. Poprzedni katalog jest dostepny."},ensure_ascii=False))
        logging.warning("Nieudany import; kolejna proba za 15 minut: %s",blad)
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raz",action="store_true",help="Sprawdz date i zakoncz po jednym przebiegu.")
    argumenty = parser.parse_args()
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
    initialize_database()
    logging.info("Automatyczna synchronizacja aktywna: kontrola co minute, import po ponad 24 h od ostatniego sukcesu.")
    ostatni = stan_synchronizacji().get("ostatni_import")
    logging.info("Ostatni pelny import: %s",ostatni.isoformat() if ostatni else "brak")
    koniec = Event()
    for sygnal in [signal.SIGTERM,signal.SIGINT]:
        signal.signal(sygnal,lambda *_:koniec.set())
    while not koniec.is_set():
        try:
            sprawdz_i_aktualizuj()
        except Exception:
            logging.exception("Blad sprawdzania synchronizacji; ponowne sprawdzenie za minute.")
        if argumenty.raz or koniec.wait(60):
            break


if __name__=="__main__":
    main()
