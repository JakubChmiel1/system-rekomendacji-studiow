"""Baza SQLite przechowywana w wolumenie Dockera."""

import os
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path


def sciezka_bazy() -> Path:
    return Path(os.environ.get("DATABASE_PATH", "data/rekomendacje_studiow.db"))


@contextmanager
def polaczenie():
    with closing(sqlite3.connect(sciezka_bazy(), timeout=30)) as baza:
        baza.row_factory = sqlite3.Row
        baza.execute("PRAGMA foreign_keys = ON")
        baza.create_function("malymi_literami", 1, lambda tekst: (tekst or "").casefold(), deterministic=True)
        with baza:
            yield baza


def initialize_database() -> None:
    sciezka = sciezka_bazy()
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    # Zachowujemy poprzednia baze podczas zmiany nazwy pliku.
    stara_baza = sciezka.with_name("app.db")
    if sciezka.name == "rekomendacje_studiow.db" and not sciezka.exists() and stara_baza.exists():
        with closing(sqlite3.connect(stara_baza)) as stara:
            with closing(sqlite3.connect(sciezka)) as nowa:
                stara.backup(nowa)

    with polaczenie() as baza:
        baza.execute("PRAGMA journal_mode = WAL")
        wersja = baza.execute("PRAGMA user_version").fetchone()[0]
        if wersja > 2:
            raise RuntimeError("Baza pochodzi z nowszej wersji aplikacji.")
        if wersja == 0:
            schemat = Path(__file__).with_name("schemat.sql").read_text(encoding="utf-8")
            try:
                baza.executescript("BEGIN IMMEDIATE;\n" + schemat)
                stara_tabela = baza.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'app_metadata'"
                ).fetchone()
                if stara_tabela:
                    baza.execute("INSERT OR IGNORE INTO metadane_aplikacji SELECT key, value FROM app_metadata")
                    baza.execute("DROP TABLE app_metadata")
                baza.execute("PRAGMA user_version = 2")
            except Exception:
                baza.rollback()
                raise
        elif wersja == 1:
            migracja = Path(__file__).with_name("migracje") / "002_pelny_import.sql"
            try:
                baza.executescript("BEGIN IMMEDIATE;\n" + migracja.read_text(encoding="utf-8"))
                baza.execute("PRAGMA user_version = 2")
            except Exception:
                baza.rollback()
                raise

    # Start nie wymaga dostepu do RAD-on. Zestaw zawiera publiczne dane z API.
    from app.radon import wczytaj_zestaw_startowy

    wczytaj_zestaw_startowy()
