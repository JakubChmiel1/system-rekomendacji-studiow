# Baza danych

SQLite: `/data/rekomendacje_studiow.db` w wolumenie `sqlite_data`.
Nie wymaga osobnego kontenera ani instalowania serwera bazy danych.
Schemat znajduje się w `app/schemat.sql`, a jego utworzenie i import zestawu
startowego odbywają się automatycznie podczas uruchomienia kontenera aplikacji.

## Tabele

| Tabela | Najważniejsze kolumny |
| --- | --- |
| `uzytkownicy` | `id`, `email`, `skrot_hasla`, `rola`, `aktywny`, `data_utworzenia` |
| `profile_kandydatow` | `id_uzytkownika`, `imie`, `typ_szkoly`, `preferowane_miasto`, `tryb_studiow` |
| `wyniki_matur` | `id`, `id_uzytkownika`, `przedmiot`, `poziom`, `wynik_procentowy`, `rok_matury` |
| `kwalifikacje_kandydatow` | `id`, `id_uzytkownika`, `kod_kwalifikacji`, `nazwa_kwalifikacji` |
| `odpowiedzi_ankiety` | `id`, `id_uzytkownika`, `kod_pytania`, `wartosc_odpowiedzi` |
| `uczelnie` | `id`, `id_radon`, `nazwa`, `miasto`, `wojewodztwo`, `rodzaj`, `kraj`, `ulica`, `numer_budynku`, `numer_lokalu`, `kod_pocztowy`, `adres_strony`, `email`, `telefon`, `nip`, `regon`, `krs`, `status`, `kod_statusu`, `data_zmiany_zrodla`, `data_pobrania` |
| `kierunki_studiow` | `id`, `id_radon`, `id_uczelni`, `id_uczelni_glownej`, `nazwa`, `poziom`, `kod_poziomu`, `profil`, `kod_profilu`, `status`, `kod_statusu`, `kod_isced`, `nazwa_isced`, `opis`, `adres_rekrutacji`, `adres_zrodla`, `data_zmiany_zrodla`, `data_pobrania` |
| `warianty_studiow` | `id`, `id_radon`, `id_kierunku`, `nazwa`, `tryb_studiow`, `kod_trybu`, `tytul_zawodowy`, `jezyk`, `kod_jezyka`, `liczba_semestrow`, `punkty_ects`, `status`, `kod_statusu`, `data_rozpoczecia`, `data_likwidacji`, `data_pobrania` |
| `dyscypliny_kierunkow` | `id_kierunku`, `kod_dyscypliny`, `nazwa_dyscypliny`, `udzial_procentowy`, `wiodaca` |
| `kryteria_kierunkow` | `id`, `id_kierunku`, `typ_kryterium`, `kod_kryterium`, `waga`, `adres_zrodla`, `data_aktualizacji` |
| `ulubione` | `id_uzytkownika`, `id_wariantu`, `data_dodania` |
| `wiadomosci_czatu` | `id`, `id_uzytkownika`, `rola`, `tresc`, `data_utworzenia` |
| `historia_importow` | `id`, `id_administratora`, `rodzaj`, `adres_zrodla`, `liczba_kierunkow`, `liczba_wariantow`, `liczba_instytucji`, `zakres`, `data_pobrania`, `data_importu` |
| `dane_zrodlowe_api` | `id`, `adres_api`, `id_radon`, `tresc_json`, `wersja_api`, `data_pobrania` |
| `metadane_aplikacji` | `klucz`, `wartosc` |

Jedna uczelnia prowadzi wiele kierunków. Jeden kierunek może mieć wiele
wariantów, np. studia stacjonarne i niestacjonarne lub różne języki kształcenia.
W ulubionych zapisujemy konkretny wariant. Identyfikatory RAD-on są unikalne,
więc ponowne pobranie danych aktualizuje wpisy i zachowuje ich lokalne identyfikatory.

## Dostęp do aplikacji

Logowanie, rejestracja i tworzenie pierwszego administratora są tymczasowo
wyłączone na stronie. Katalog, historia importów i przycisk pobierania danych
są dostępne od razu, bez konta.

Import uruchomiony bez konta zapisuje `NULL` w `historia_importow.id_administratora`.
Istniejące konta i ich dane pozostają w SQLite do późniejszego wykorzystania.
Kod obsługi kont zachowuje hasła w postaci skrótów scrypt. Każdy komputer ma
własną bazę danych.

## Źródło i mapowanie

Publiczne API RAD-on/POL-on, Ośrodek Przetwarzania Informacji – PIB:

`https://radon.nauka.gov.pl/opendata/polon/courses`

[Oficjalna dokumentacja i przykłady](https://radon.nauka.gov.pl/pomoc/knowledge-base/kierunki-studiow-uruchomienia-pol-on-scenariusze-uzycia-uslugi/).

| Pole API | Miejsce w bazie |
| --- | --- |
| `leadingInstitutionUuid`, `leadingInstitutionName` | `uczelnie.id_radon`, `uczelnie.nazwa`; uczelnia prowadząca |
| `mainInstitutionUuid`, `mainInstitutionName` | `uczelnie`; powiązanie przez `kierunki_studiow.id_uczelni_glownej` |
| `leadingInstitutionCity` | `uczelnie.miasto`; siedziba uczelni, nie gwarantowane miejsce zajęć |
| `courseUuid`, `courseName`, `levelName`, `profileName` | `kierunki_studiow` |
| `courseInstances[]` | `warianty_studiow` |
| `courseInstanceUuid`, `formName`, `titleName`, `languageName` | identyfikator wariantu, tryb, tytuł i język |
| `numberOfSemesters`, `ects` | `warianty_studiow.liczba_semestrow`, `warianty_studiow.punkty_ects` |
| `disciplines[]` | `dyscypliny_kierunkow` |
| `lastRefresh` | `kierunki_studiow.data_zmiany_zrodla`; znacznik czasu źródła |

Zestaw startowy `app/dane/kierunki_radon.json` zawiera 140 kierunków pobranych
z API, wraz z adresami zapytań i datą pobrania. To próbka studiów pierwszego
stopnia i jednolitych magisterskich, nie pełna lista uczelni w Polsce.
Jest wczytywana tylko raz, bez internetu i bez nadpisywania kolejnych aktualizacji.

Przycisk **Pobierz wszystkie dane z API** w sekcji „Aktualizacja danych” pobiera:

- pełny katalog instytucji: `https://radon.nauka.gov.pl/opendata/polon/institutions`;
- pełny katalog kierunków i ich wariantów: `https://radon.nauka.gov.pl/opendata/polon/courses`.

[Oficjalne przykłady API instytucji](https://radon.nauka.gov.pl/pomoc/knowledge-base/414/).
Oba sprawdzone API są publiczne i nie wymagają klucza. Nie korzystamy z wyłączonego
API kierunków ani z jego dawnych kopii w innych portalach.

Pobieranie korzysta z tokenów kolejnych stron, bez limitu ich liczby. Import
obejmuje wszystkie poziomy i statusy studiów. Pasek pokazuje postęp. Liczba
unikalnych rekordów jest porównywana z `maxCount` API; brakujące strony lub
zapętlona paginacja przerywają import. Sprawdzona wersja API pomija czasem
rekordy o identycznym `lastRefresh` na granicy stron. Import odczytuje rozpoznany
token czasu z nakładką 1 ms i deduplikuje rekordy po identyfikatorze. Tokeny
w innym formacie są przekazywane bez zmian, z kontrolą kompletności wyniku.
Przejściowe błędy sieci są ponawiane
maksymalnie trzy razy. Dane z obu źródeł są zatwierdzane w jednej transakcji.
Błąd pobierania albo zapisu zachowuje poprzedni katalog.

W `dane_zrodlowe_api` zapisujemy pełne rekordy JSON, wersję API, źródło i datę
pobrania. Obejmuje to także filie, historię nazw i adresów, podstawy prawne,
jednostki organizacyjne i pozostałe pola, które rzeczywiście zwróci źródło.
Klucze wewnątrz JSON zachowują oryginalne nazwy API. Tabele i kolumny są po polsku.
Praktyczne pola uczelni, kierunków i wariantów trafiają dodatkowo do tabel
relacyjnych. Instytucje naukowe bez kierunków pozostają w danych źródłowych;
nie stają się ofertami studiów. API instytucji uzupełnia adresy i dane kontaktowe.

Ponowny import aktualizuje wpisy po identyfikatorze RAD-on, bez duplikowania
rekordów. Zachowuje konta, wyniki, ulubione, opisy administratora i kryteria.
Nie usuwa lokalnych kierunków nieobecnych w odpowiedzi. Wariant nieobecny
w nowszym odczycie jego kierunku jest oznaczany bez usuwania ulubionych.
Historia zawiera udane importy każdego źródła, ich zakres i liczby rekordów.

W publicznym katalogu kandydat widzi prowadzone studia pierwszego stopnia
oraz jednolite magisterskie. Dane studiów drugiego stopnia i zamkniętych
kierunków również są pobierane i zapisane w bazie, lecz nie są wyświetlane
w katalogu dla maturzystów. Kody API: `2` = pierwszy stopień, `1` = jednolite
magisterskie, `3` = drugi stopień. Wszystkie daty pobrania są zapisywane w UTC.

Rejestr kierunków nie jest bieżącą ofertą rekrutacyjną. Sprawdzona odpowiedź
nie zawiera progów przyjęcia, wag przedmiotów maturalnych, kosztów ani terminów
rekrutacji. Tych danych nie zgadujemy. `opis`, `adres_rekrutacji` i
`kryteria_kierunkow` pozostają do uzupełnienia na podstawie źródeł uczelni.
Kryteria są wagami dopasowania w rekomendacjach, nie oficjalnymi przelicznikami
punktów rekrutacyjnych. Import nie nadpisuje opisów ani kryteriów.

## Docker i zachowanie danych

```powershell
docker compose up --build -d --wait
```

Otwórz [localhost:8501](http://localhost:8501). Gdy w wolumenie istnieje poprzedni
`app.db`, aplikacja kopiuje
go przez mechanizm kopii SQLite do `rekomendacje_studiow.db` i przenosi metadane
do polskiej tabeli. Stary plik zostaje jako kopia. Schemat ma wersję zapisaną
w `PRAGMA user_version`; obecnie ma numer 2. Migracja z wersji 1 automatycznie
dodaje pola instytucji i tabelę pełnych rekordów API, zachowując istniejące dane.

Nie wysyłaj lokalnej bazy ani kont na GitHuba. W repozytorium zapisujemy schemat,
kod i publiczny zestaw startowy. `docker compose down` zachowuje dane,
a `docker compose down -v` usuwa także bazę i model.

Schemat obejmuje dane potrzebne w kolejnych etapach projektu. Formularze matur,
kwalifikacji, ankiety, zapis ulubionych, ranking i właściwy czat nie są jeszcze
zaimplementowane. Obecnie działają katalog i import bez logowania.

## Testy w kontenerze

```powershell
docker compose exec -T app python -m unittest discover -s tests -v
```

Testy korzystają z tymczasowych baz i nie zmieniają danych użytkowników.
