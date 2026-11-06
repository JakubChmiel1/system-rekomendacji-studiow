ALTER TABLE uczelnie ADD COLUMN kraj TEXT;
ALTER TABLE uczelnie ADD COLUMN ulica TEXT;
ALTER TABLE uczelnie ADD COLUMN numer_budynku TEXT;
ALTER TABLE uczelnie ADD COLUMN numer_lokalu TEXT;
ALTER TABLE uczelnie ADD COLUMN kod_pocztowy TEXT;
ALTER TABLE uczelnie ADD COLUMN adres_strony TEXT;
ALTER TABLE uczelnie ADD COLUMN email TEXT;
ALTER TABLE uczelnie ADD COLUMN telefon TEXT;
ALTER TABLE uczelnie ADD COLUMN nip TEXT;
ALTER TABLE uczelnie ADD COLUMN regon TEXT;
ALTER TABLE uczelnie ADD COLUMN krs TEXT;
ALTER TABLE uczelnie ADD COLUMN status TEXT;
ALTER TABLE uczelnie ADD COLUMN kod_statusu TEXT;
ALTER TABLE uczelnie ADD COLUMN data_zmiany_zrodla TEXT;
ALTER TABLE historia_importow ADD COLUMN liczba_instytucji INTEGER NOT NULL DEFAULT 0;
ALTER TABLE historia_importow ADD COLUMN zakres TEXT NOT NULL DEFAULT 'czesciowy' CHECK (zakres IN ('czesciowy', 'pelny'));

CREATE TABLE dane_zrodlowe_api (
    id INTEGER PRIMARY KEY,
    adres_api TEXT NOT NULL,
    id_radon TEXT NOT NULL,
    tresc_json TEXT NOT NULL CHECK (json_valid(tresc_json)),
    wersja_api TEXT,
    data_pobrania TEXT NOT NULL,
    UNIQUE (adres_api, id_radon)
);
