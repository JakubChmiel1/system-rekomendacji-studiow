# Baza danych

SQLite: `/data/rekomendacje_studiow.db` w wolumenie `sqlite_data`.
Nie wymaga osobnego kontenera ani instalowania serwera bazy danych.
Schemat znajduje się w `app/schemat.sql`, a jego utworzenie i import zestawu
startowego odbywają się automatycznie podczas uruchomienia kontenera aplikacji.

## Tabele

| Tabela | Najważniejsze kolumny |
| --- | --- |
| `uzytkownicy` | `id`, `email`, `skrot_hasla`, `rola`, `aktywny`, `data_utworzenia` |
| `profile_kandydatow` | `id_uzytkownika`, `imie`, `typ_szkoly`, `preferowane_miasto`, `tryb_studiow`, `miejsce_zamieszkania`, `szerokosc`, `dlugosc`, `maksymalny_dystans`, `matura_uzupelniona`, `data_aktualizacji` |
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
| `wersje_ankiety` | `id`, `id_uzytkownika`, `odpowiedzi_json`, `data_utworzenia` |
| `preferencje_czatu` | `id_uzytkownika`, `preferencje_json`, `data_aktualizacji` |
| `wymagania_rekrutacyjne` | `id`, `id_kierunku`, `rok_rekrutacji`, `grupa`, `przedmiot`, `poziom`, `minimalny_wynik`, `adres_zrodla`, `zweryfikowane` |
| `proby_logowania` | `identyfikator`, `liczba_prob`, `blokada_do` |
| `metadane_aplikacji` | `klucz`, `wartosc` |

Jedna uczelnia prowadzi wiele kierunków. Jeden kierunek może mieć wiele
wariantów, np. studia stacjonarne i niestacjonarne lub różne języki kształcenia.
W ulubionych zapisujemy konkretny wariant. Identyfikatory RAD-on są unikalne,
więc ponowne pobranie danych aktualizuje wpisy i zachowuje ich lokalne identyfikatory.

## Dostęp do aplikacji

Aplikacja wymaga zalogowania. Konto demonstracyjne administratora **admin / admin**
powstaje przy pierwszym starcie. Hasło w istniejącym koncie nie jest resetowane.
Rejestracja kandydatów wymaga poprawnego e-maila, zgodnych haseł i 12–256 znaków.
Hasła są zapisane jako skróty scrypt z oddzielną losową solą. Pięć nieudanych
prób logowania blokuje kolejne próby dla tego loginu na minutę.

Import danych oraz edycja potwierdzonych wymagań są dostępne tylko administratorowi.
Kandydat ma dostęp do własnych wyników, ankiety, ulubionych i rozmowy. Zapytania
wiążą dane z identyfikatorem aktualnego konta; model nie otrzymuje identyfikatorów
innych kont, haseł, e-maila ani dokładnych współrzędnych domu.

Każdy komputer ma oddzielną bazę, konta i model zapisane w swoich wolumenach.

## Profil, ankieta i preferencje

Zapis profilu i wyników jest transakcyjny. Wyniki spoza 0–100%, niepoprawne lata
oraz powtórzone kombinacje przedmiotu, poziomu i roku są odrzucane. Dla przygotowania
przedmiotowego wybierany jest najlepszy przeskalowany wynik danego przedmiotu;
sprawdzanie wymagań używa natomiast konkretnego poziomu i oryginalnego wyniku.

Ankieta ma 12 pytań o zainteresowania, mocne i słabe strony, sposób nauki, środowisko
pracy i preferencje studiów. Najnowsze odpowiedzi znajdują się w `odpowiedzi_ankiety`.
Każdy ponowny zapis tworzy także wersję w `wersje_ankiety`.
Preferencje z rozmowy są osobne: nie nadpisują ankiety ani matury. Można je wyczyścić.

## Dopasowanie top 10

Ranking jest deterministyczny i działa bez LLM. Najpierw odczytuje prowadzone studia
pierwszego stopnia i jednolite magisterskie, a następnie liczy punktację zgodności:

| Składnik | Domyślna waga |
| --- | --- |
| Zainteresowania | 40% |
| Przygotowanie przedmiotowe | 30% |
| Mocne strony | 15% |
| Preferencje nauki, trybu, języka, lokalizacji i innych wyborów | 15% |

Obszar kierunku jest określany heurystycznie z nazwy i kodu ISCED. Przygotowanie
przedmiotowe to ważona średnia właściwych dla obszaru przedmiotów. Wynik podstawowy
ma współczynnik 0,7, a rozszerzony i dwujęzyczny 1. To współczynniki rekomendacji,
nie oficjalne przeliczniki uczelni. Pasująca kwalifikacja daje do 8 punktów bonusu
w składniku przygotowania. Użytkownik może zmienić priorytet przez rozmowę.

Brak danych w nieukończonym profilu daje ocenę neutralną, zamiast automatycznej
odmowy. Gdy kandydat oznaczy maturę jako kompletną, brak przedmiotu jest uwzględniany
w przygotowaniu. Dla kierunku lekarskiego brak obu rozszerzeń: biologii i chemii,
ogranicza dopasowanie do 40% i pokazuje uwagę. Nie oznacza to zerowych szans.

Wyłącznie zweryfikowane wymagania przedmiotowe dla wybranego roku mogą dać 0%
i wykluczenie. Warunki z tej samej grupy są alternatywami (OR), osobne grupy muszą
być spełnione łącznie (AND). Brakujące wyniki przy niekompletnym profilu oznaczają
„do sprawdzenia”. Zapisane warunki nie obejmują automatycznie całej procedury
rekrutacyjnej, np. konkursu punktów, portfolio czy egzaminu wstępnego.

Wynik jest zaokrąglany do 0,1 punktu (w kartach prezentowany jako pełny procent).
Top 10 nie powtarza tego samego kierunku na tej samej uczelni i poziomie; wybiera
najwyżej oceniony wariant. **Procent jest dopasowaniem, nie prawdopodobieństwem
przyjęcia.** To heurystyka, która wymaga dalszej oceny z użytkownikami, a nie
wytrenowany model prognozowania rekrutacji. Tabela `kryteria_kierunkow` pozostaje
przygotowana do przyszłej indywidualizacji kryteriów; aktualny algorytm używa
jawnych reguł w `app/rekomendacje.py`.

## Mapa i doradca

Współrzędne 3870 polskich miejscowości pochodzą z GeoNames, CC BY 4.0, i są dołączone
w `app/dane/miejscowosci.json` wraz z datą i źródłem. Nie wysyłamy lokalizacji domu
do zewnętrznego geokodera. Użytkownik wybiera miejscowość lub zapisuje punkt z mapy.
Odległość haversine jest w linii prostej do środka miejscowości uczelni. Nie jest
odległością drogową, czasem dojazdu ani pomiarem do konkretnego budynku. Podkład
OpenStreetMap i zasoby mapy w przeglądarce wymagają internetu; lokalne współrzędne
oraz wyliczanie odległości go nie wymagają.

Doradca korzysta z bieżącego kontekstu SQLite (RAG): własny profil, matura, ankieta,
kwalifikacje, aktualne top 10 i do 5 dodatkowych ofert wyszukanych według pytania.
Nie wykonujemy osobnego trenowania Qwena na danych kont. Każde konto ma osobną
historię i preferencje. Odpowiedź modelu jest walidowana schematem JSON, a zmiany
preferencji ograniczone do ustalonych pól i wartości. Model nie wykonuje SQL,
nie nadaje ról i nie zmienia wyników matury ani odpowiedzi ankiety. Nawigacja
jest ograniczona do istniejących widoków. Wybrane proste polecenia nawigacyjne
obsługuje lokalna reguła bez oczekiwania na LLM.

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

Przycisk **Pobierz wszystkie dane z API** w zakładce „Administracja” pobiera:

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
w `PRAGMA user_version`; obecnie ma numer 3. Migracje 1→2→3 dodają pola
instytucji, dane API, rozszerzony profil, wersje ankiety, preferencje rozmowy
i wymagania przedmiotowe, zachowując istniejące dane.

Nie wysyłaj lokalnej bazy ani kont na GitHuba. W repozytorium zapisujemy schemat,
kod i publiczny zestaw startowy. `docker compose down` zachowuje dane,
a `docker compose down -v` usuwa także bazę i model.

Działają konta, profil z wynikami i kwalifikacjami, ponawiana ankieta, ulubione,
filtry, mapa, ranking, lokalny doradca, import i edycja warunków administratora.
Materiały edukacyjne, automatyczne pobieranie kompletnych zasad rekrutacji oraz
opłaty i terminy uczelni nie są częścią obecnego katalogu.

## Testy w kontenerze

```powershell
docker compose exec -T app python -m unittest discover -s tests -v
```

Testy korzystają z tymczasowych baz i nie zmieniają danych użytkowników.
