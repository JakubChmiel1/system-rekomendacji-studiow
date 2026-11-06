"""Tworzenie kont i sprawdzanie uprawnien administratora."""

import hashlib
import hmac
import secrets
import sqlite3
import re
import time

from app.database import polaczenie


def skrot_hasla(haslo: str) -> str:
    sol = secrets.token_bytes(16)
    wynik = hashlib.scrypt(haslo.encode("utf-8"), salt=sol, n=2**17, r=8, p=1, maxmem=256*1024*1024)
    return f"scrypt${sol.hex()}${wynik.hex()}"


def sprawdz_haslo(haslo: str, zapisany_skrot: str) -> bool:
    try:
        algorytm, sol, oczekiwany = zapisany_skrot.split("$")
        if algorytm != "scrypt":
            return False
        wynik = hashlib.scrypt(haslo.encode("utf-8"), salt=bytes.fromhex(sol), n=2**17, r=8, p=1, maxmem=256*1024*1024)
        return hmac.compare_digest(wynik.hex(), oczekiwany)
    except (ValueError, TypeError):
        return False


def istnieje_administrator() -> bool:
    with polaczenie() as baza:
        return baza.execute("SELECT 1 FROM uzytkownicy WHERE rola = 'administrator'").fetchone() is not None


def utworz_konto(email: str, haslo: str, *, pierwszy_administrator: bool = False) -> int:
    email = email.strip().lower()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@.]{2,}", email):
        raise ValueError("Podaj poprawny adres e-mail.")
    if not 12 <= len(haslo) <= 256:
        raise ValueError("Haslo musi miec od 12 do 256 znakow.")
    zapisany_skrot = skrot_hasla(haslo)
    with polaczenie() as baza:
        baza.execute("BEGIN IMMEDIATE")
        if pierwszy_administrator:
            if baza.execute("SELECT 1 FROM uzytkownicy WHERE rola = 'administrator'").fetchone():
                raise ValueError("Konto administratora juz istnieje. Zaloguj sie.")
            rola = "administrator"
        else:
            rola = "kandydat"
        try:
            identyfikator = baza.execute(
                "INSERT INTO uzytkownicy (email, skrot_hasla, rola) VALUES (?, ?, ?)",
                (email, zapisany_skrot, rola),
            ).lastrowid
        except sqlite3.IntegrityError as blad:
            raise ValueError("Konto z takim adresem e-mail juz istnieje.") from blad
        if rola == "kandydat":
            baza.execute("INSERT INTO profile_kandydatow (id_uzytkownika) VALUES (?)", (identyfikator,))
        return identyfikator


def zaloguj(email: str, haslo: str) -> int | None:
    email = email.strip().lower()
    if not email or not haslo or len(email) > 254 or len(haslo) > 256:
        return None
    klucz = hashlib.sha256(email.encode()).hexdigest()
    with polaczenie() as baza:
        proby = baza.execute("SELECT liczba_prob, blokada_do FROM proby_logowania WHERE identyfikator = ?", (klucz,)).fetchone()
        if proby and proby["blokada_do"] > time.time():
            raise ValueError("Zbyt wiele nieudanych prób. Spróbuj ponownie za minutę.")
        konto = baza.execute(
            "SELECT id, skrot_hasla FROM uzytkownicy WHERE email = ? AND aktywny = 1",
            (email,),
        ).fetchone()
    if konto and sprawdz_haslo(haslo, konto["skrot_hasla"]):
        with polaczenie() as baza:
            baza.execute("DELETE FROM proby_logowania WHERE identyfikator = ?", (klucz,))
        return konto["id"]
    with polaczenie() as baza:
        baza.execute("BEGIN IMMEDIATE")
        proby = baza.execute("SELECT liczba_prob, blokada_do FROM proby_logowania WHERE identyfikator = ?", (klucz,)).fetchone()
        liczba = (proby["liczba_prob"] if proby and proby["blokada_do"] == 0 else 0) + 1
        blokada = int(time.time()) + 60 if liczba >= 5 else 0
        baza.execute(
            "INSERT INTO proby_logowania (identyfikator,liczba_prob,blokada_do) VALUES (?,?,?) "
            "ON CONFLICT(identyfikator) DO UPDATE SET liczba_prob=excluded.liczba_prob, blokada_do=excluded.blokada_do",
            (klucz, liczba, blokada),
        )
    return None


def pobierz_konto(id_uzytkownika: int | None) -> dict | None:
    with polaczenie() as baza:
        konto = baza.execute(
            "SELECT id, email, rola FROM uzytkownicy WHERE id = ? AND aktywny = 1", (id_uzytkownika,)
        ).fetchone()
    return dict(konto) if konto else None


def wymagaj_administratora(id_uzytkownika: int) -> None:
    konto = pobierz_konto(id_uzytkownika)
    if not konto or konto["rola"] != "administrator":
        raise PermissionError("Ta operacja wymaga konta administratora.")


def zapewnij_konto_admina() -> None:
    """Jednorazowe konto demonstracyjne wskazane przez wlasciciela projektu."""
    with polaczenie() as baza:
        istnieje = baza.execute("SELECT id FROM uzytkownicy WHERE email = 'admin'").fetchone()
    if istnieje:
        return
    haslo = skrot_hasla("admin")
    with polaczenie() as baza:
        baza.execute("BEGIN IMMEDIATE")
        baza.execute("INSERT OR IGNORE INTO uzytkownicy (email,skrot_hasla,rola) VALUES ('admin',?,'administrator')", (haslo,))
        identyfikator = baza.execute("SELECT id FROM uzytkownicy WHERE email = 'admin'").fetchone()[0]
        baza.execute("INSERT OR IGNORE INTO profile_kandydatow (id_uzytkownika,imie) VALUES (?, 'Administrator')", (identyfikator,))
