CREATE TABLE IF NOT EXISTS metadane_aplikacji (
    klucz TEXT PRIMARY KEY,
    wartosc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS uzytkownicy (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
    skrot_hasla TEXT NOT NULL,
    rola TEXT NOT NULL DEFAULT 'kandydat' CHECK (rola IN ('kandydat', 'administrator')),
    aktywny INTEGER NOT NULL DEFAULT 1 CHECK (aktywny IN (0, 1)),
    data_utworzenia TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS profile_kandydatow (
    id_uzytkownika INTEGER PRIMARY KEY REFERENCES uzytkownicy(id) ON DELETE CASCADE,
    imie TEXT,
    typ_szkoly TEXT,
    preferowane_miasto TEXT,
    tryb_studiow TEXT
);

CREATE TABLE IF NOT EXISTS wyniki_matur (
    id INTEGER PRIMARY KEY,
    id_uzytkownika INTEGER NOT NULL REFERENCES uzytkownicy(id) ON DELETE CASCADE,
    przedmiot TEXT NOT NULL,
    poziom TEXT NOT NULL CHECK (poziom IN ('podstawowy', 'rozszerzony', 'dwujezyczny')),
    wynik_procentowy REAL NOT NULL CHECK (wynik_procentowy BETWEEN 0 AND 100),
    rok_matury INTEGER NOT NULL CHECK (rok_matury BETWEEN 2000 AND 2100),
    UNIQUE (id_uzytkownika, przedmiot, poziom, rok_matury)
);

CREATE TABLE IF NOT EXISTS kwalifikacje_kandydatow (
    id INTEGER PRIMARY KEY,
    id_uzytkownika INTEGER NOT NULL REFERENCES uzytkownicy(id) ON DELETE CASCADE,
    kod_kwalifikacji TEXT NOT NULL,
    nazwa_kwalifikacji TEXT NOT NULL,
    UNIQUE (id_uzytkownika, kod_kwalifikacji)
);

CREATE TABLE IF NOT EXISTS odpowiedzi_ankiety (
    id INTEGER PRIMARY KEY,
    id_uzytkownika INTEGER NOT NULL REFERENCES uzytkownicy(id) ON DELETE CASCADE,
    kod_pytania TEXT NOT NULL,
    wartosc_odpowiedzi TEXT NOT NULL,
    UNIQUE (id_uzytkownika, kod_pytania)
);

CREATE TABLE IF NOT EXISTS uczelnie (
    id INTEGER PRIMARY KEY,
    id_radon TEXT NOT NULL UNIQUE,
    nazwa TEXT NOT NULL,
    miasto TEXT,
    wojewodztwo TEXT,
    rodzaj TEXT,
    data_pobrania TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS kierunki_studiow (
    id INTEGER PRIMARY KEY,
    id_radon TEXT NOT NULL UNIQUE,
    id_uczelni INTEGER NOT NULL REFERENCES uczelnie(id),
    id_uczelni_glownej INTEGER REFERENCES uczelnie(id),
    nazwa TEXT NOT NULL,
    poziom TEXT NOT NULL,
    kod_poziomu TEXT NOT NULL,
    profil TEXT,
    kod_profilu TEXT,
    status TEXT NOT NULL,
    kod_statusu TEXT NOT NULL,
    kod_isced TEXT,
    nazwa_isced TEXT,
    opis TEXT NOT NULL DEFAULT '',
    adres_rekrutacji TEXT,
    adres_zrodla TEXT NOT NULL,
    data_zmiany_zrodla TEXT,
    data_pobrania TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS warianty_studiow (
    id INTEGER PRIMARY KEY,
    id_radon TEXT NOT NULL UNIQUE,
    id_kierunku INTEGER NOT NULL REFERENCES kierunki_studiow(id),
    nazwa TEXT NOT NULL,
    tryb_studiow TEXT NOT NULL,
    kod_trybu TEXT NOT NULL,
    tytul_zawodowy TEXT,
    jezyk TEXT,
    kod_jezyka TEXT,
    liczba_semestrow INTEGER CHECK (liczba_semestrow > 0),
    punkty_ects REAL CHECK (punkty_ects >= 0),
    status TEXT NOT NULL,
    kod_statusu TEXT NOT NULL,
    data_rozpoczecia TEXT,
    data_likwidacji TEXT,
    data_pobrania TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dyscypliny_kierunkow (
    id_kierunku INTEGER NOT NULL REFERENCES kierunki_studiow(id) ON DELETE CASCADE,
    kod_dyscypliny TEXT NOT NULL,
    nazwa_dyscypliny TEXT NOT NULL,
    udzial_procentowy REAL CHECK (udzial_procentowy BETWEEN 0 AND 100),
    wiodaca INTEGER NOT NULL CHECK (wiodaca IN (0, 1)),
    PRIMARY KEY (id_kierunku, kod_dyscypliny)
);

CREATE TABLE IF NOT EXISTS kryteria_kierunkow (
    id INTEGER PRIMARY KEY,
    id_kierunku INTEGER NOT NULL REFERENCES kierunki_studiow(id) ON DELETE CASCADE,
    typ_kryterium TEXT NOT NULL CHECK (typ_kryterium IN ('matura', 'zainteresowanie', 'mocna_strona', 'slaba_strona', 'kwalifikacja')),
    kod_kryterium TEXT NOT NULL,
    waga REAL NOT NULL CHECK (waga BETWEEN 0 AND 1),
    adres_zrodla TEXT,
    data_aktualizacji TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (id_kierunku, typ_kryterium, kod_kryterium)
);

CREATE TABLE IF NOT EXISTS ulubione (
    id_uzytkownika INTEGER NOT NULL REFERENCES uzytkownicy(id) ON DELETE CASCADE,
    id_wariantu INTEGER NOT NULL REFERENCES warianty_studiow(id),
    data_dodania TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    PRIMARY KEY (id_uzytkownika, id_wariantu)
);

CREATE TABLE IF NOT EXISTS wiadomosci_czatu (
    id INTEGER PRIMARY KEY,
    id_uzytkownika INTEGER NOT NULL REFERENCES uzytkownicy(id) ON DELETE CASCADE,
    rola TEXT NOT NULL CHECK (rola IN ('uzytkownik', 'asystent')),
    tresc TEXT NOT NULL,
    data_utworzenia TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS historia_importow (
    id INTEGER PRIMARY KEY,
    id_administratora INTEGER REFERENCES uzytkownicy(id) ON DELETE SET NULL,
    rodzaj TEXT NOT NULL CHECK (rodzaj IN ('zestaw_startowy', 'api')),
    adres_zrodla TEXT NOT NULL,
    liczba_kierunkow INTEGER NOT NULL DEFAULT 0,
    liczba_wariantow INTEGER NOT NULL DEFAULT 0,
    data_pobrania TEXT NOT NULL,
    data_importu TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS indeks_kierunkow_uczelni ON kierunki_studiow(id_uczelni);
CREATE INDEX IF NOT EXISTS indeks_wariantow_kierunku ON warianty_studiow(id_kierunku);
CREATE INDEX IF NOT EXISTS indeks_wiadomosci_uzytkownika ON wiadomosci_czatu(id_uzytkownika, id);
