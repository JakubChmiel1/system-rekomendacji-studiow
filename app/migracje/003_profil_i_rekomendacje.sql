ALTER TABLE profile_kandydatow ADD COLUMN miejsce_zamieszkania TEXT;
ALTER TABLE profile_kandydatow ADD COLUMN szerokosc REAL CHECK (szerokosc BETWEEN -90 AND 90);
ALTER TABLE profile_kandydatow ADD COLUMN dlugosc REAL CHECK (dlugosc BETWEEN -180 AND 180);
ALTER TABLE profile_kandydatow ADD COLUMN maksymalny_dystans INTEGER NOT NULL DEFAULT 300 CHECK (maksymalny_dystans BETWEEN 0 AND 1500);
ALTER TABLE profile_kandydatow ADD COLUMN matura_uzupelniona INTEGER NOT NULL DEFAULT 0 CHECK (matura_uzupelniona IN (0,1));
ALTER TABLE profile_kandydatow ADD COLUMN data_aktualizacji TEXT;

CREATE TABLE wersje_ankiety (
    id INTEGER PRIMARY KEY,
    id_uzytkownika INTEGER NOT NULL REFERENCES uzytkownicy(id) ON DELETE CASCADE,
    odpowiedzi_json TEXT NOT NULL CHECK (json_valid(odpowiedzi_json)),
    data_utworzenia TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE preferencje_czatu (
    id_uzytkownika INTEGER PRIMARY KEY REFERENCES uzytkownicy(id) ON DELETE CASCADE,
    preferencje_json TEXT NOT NULL CHECK (json_valid(preferencje_json)),
    data_aktualizacji TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE wymagania_rekrutacyjne (
    id INTEGER PRIMARY KEY,
    id_kierunku INTEGER NOT NULL REFERENCES kierunki_studiow(id) ON DELETE CASCADE,
    rok_rekrutacji INTEGER NOT NULL CHECK (rok_rekrutacji BETWEEN 2020 AND 2100),
    grupa INTEGER NOT NULL CHECK (grupa > 0),
    przedmiot TEXT NOT NULL,
    poziom TEXT NOT NULL CHECK (poziom IN ('podstawowy','rozszerzony','dwujezyczny')),
    minimalny_wynik REAL NOT NULL CHECK (minimalny_wynik BETWEEN 0 AND 100),
    adres_zrodla TEXT NOT NULL,
    zweryfikowane INTEGER NOT NULL DEFAULT 0 CHECK (zweryfikowane IN (0,1)),
    UNIQUE(id_kierunku,rok_rekrutacji,grupa,przedmiot,poziom)
);
CREATE TABLE proby_logowania (
    identyfikator TEXT PRIMARY KEY,
    liczba_prob INTEGER NOT NULL DEFAULT 0,
    blokada_do INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX indeks_wersji_ankiety ON wersje_ankiety(id_uzytkownika,id);
CREATE INDEX indeks_wymagan_kierunku ON wymagania_rekrutacyjne(id_kierunku,rok_rekrutacji);
