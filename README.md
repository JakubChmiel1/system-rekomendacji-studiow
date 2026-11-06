# System rekomendacji kierunków studiów

Kierunek. — osobisty wybór studiów. Python, Streamlit, SQLite i lokalny model
Qwen działają wspólnie w Docker Compose.

## Uruchomienie

Zainstaluj Docker Desktop i uruchom go. Na Windows użyj WSL 2 i kontenerów Linux.
Na Linux można użyć Docker Engine z wtyczką Compose. Komputer musi mieć pamięć
wystarczającą dla modelu; domyślna wersja korzysta z CPU.

Pobierz repozytorium:

```powershell
git clone https://github.com/JakubChmiel1/system-rekomendacji-studiow.git projekt
cd projekt
```

W folderze projektu wykonaj jedno polecenie:

```powershell
docker compose up --build -d --wait
```

Otwórz [localhost:8501](http://localhost:8501).

Załóż konto w zakładce **Utwórz konto**. Rejestracja wymaga poprawnego e-maila
i hasła o długości 12–256 znaków. Panel administratora został usunięty;
istniejące konta zachowują swoje dane i mogą nadal się logować.

Po zalogowaniu:

1. W **Mój profil** dodaj wyniki matury, poziomy przedmiotów i kwalifikacje.
2. Wypełnij **Ankietę**. Możesz później zmienić odpowiedzi i zapisać kolejną wersję.
3. Na **Mapie uczelni** wybierz miejscowość lub kliknij punkt zamieszkania i zapisz go.
4. Odkryj **top 10** oraz **Katalog kierunków**. Filtruj nazwę, województwo, uczelnię,
   miasto, obszar, tryb, język, poziom, rodzaj uczelni i dystans.
5. Zapisuj ulubione i rozmawiaj z doradcą w prawym panelu. Preferencje z rozmowy
   zmieniają punktację rankingu; można je cofnąć.

Procent to **dopasowanie do profilu**, a nie szansa przyjęcia. Algorytm działa
niezależnie od czatu. Przy niepełnym profilu pokazuje wstępne propozycje.


Compose uruchamia Ollamę, przygotowuje model `qwen3.5:4b`, a następnie uruchamia
aplikację. Zakończenie kontenera `model-init` z kodem 0 jest prawidłowe:
przygotował model i zakończył zadanie. Pierwsze uruchomienie wymaga internetu
i pobrania kilku GB danych.
Później zapisany model jest używany ponownie. Bez internetu można uruchomić
wcześniej przygotowany projekt, jeśli obrazy i wolumeny pozostają na komputerze:

```powershell
docker compose up -d --wait --pull never --no-build
```

Na nowym komputerze pierwsze uruchomienie wymaga internetu albo wcześniejszego
przeniesienia gotowych obrazów i danych modelu.

Nie trzeba instalować osobno Pythona ani Ollamy. SQLite działa wewnątrz aplikacji.
Modele i dane są przechowywane w wolumenach Dockera, poza repozytorium Git.
Adres Ollamy dla kodu Pythona jest dostępny w zmiennej `OLLAMA_BASE_URL`, a nazwa
modelu w `OLLAMA_MODEL`. Ollama jest dostępna tylko wewnątrz sieci kontenerów.
Rozmowę z modelem w kontenerze można przetestować poleceniem:

```powershell
docker compose exec ollama ollama run qwen3.5:4b
```

## Przyspieszenie NVIDIA

Na komputerze z obsługiwaną kartą NVIDIA można uruchomić całość jednym poleceniem:

```powershell
docker compose -f compose.yaml -f compose.gpu.yaml up --build -d --wait
```

Wymaga to obsługi GPU przez Docker i zgodnych sterowników. Na Windows używaj
Docker Desktop z WSL 2; na Linux potrzebny jest NVIDIA Container Toolkit.
Wersja CPU działa bez dostępu do GPU, ale odpowiedzi mogą być wolniejsze.

## Praca zespołu

Wszyscy pracujemy bezpośrednio na gałęzi `main`. Uzgadniamy podział zadań,
żeby nie zmieniać jednocześnie tych samych fragmentów kodu.

Przed rozpoczęciem zadania, po wysłaniu wcześniejszych zmian, pobierz aktualny kod:

```powershell
git switch main
git pull --ff-only
docker compose up --build -d --wait
```

Kod znajduje się w `app/`. Po jego zmianie przebuduj aplikację poleceniem
`docker compose up --build -d --wait`, a następnie odśwież stronę.
Po wykonaniu zadania zapisz zmiany i pobierz ewentualne aktualizacje od pozostałych:

```powershell
git add .
git commit -m "Opis wykonanych zmian"
git pull --rebase
```

Jeśli pojawią się konflikty, rozwiąż je, dodaj poprawione pliki przez `git add`
i dokończ operację poleceniem `git rebase --continue`.

Uruchom aplikację i sprawdź działanie połączonych zmian:

```powershell
docker compose up --build -d --wait
```

Następnie wyślij zmiany do wspólnego repozytorium:

```powershell
git push
```

Wysyłamy małe, działające zmiany. Wersje bibliotek są zapisane w `requirements.txt`,
a obraz Pythona jest przypięty w `Dockerfile`.

## Baza i zatrzymanie

Wolumen `sqlite_data` przechowuje bazę SQLite, a `ollama_data` model językowy.
Każdy komputer ma własne dane. Pozostają one po zatrzymaniu i odtworzeniu kontenerów.

```powershell
docker compose down
```

Polecenie zatrzymuje wszystkie elementy projektu i zachowuje dane. Dodanie `-v`
usuwa również lokalną bazę i pobrany model. Kolejne uruchomienie wymaga wtedy
ponownego pobrania modelu.

Docker przechowuje obrazy i wolumeny w swoim katalogu danych. Jeśli chcesz używać
dysku D, ustaw lokalizację danych w Docker Desktop; projekt nie narzuca litery dysku.


## Dane, ranking i doradca

SQLite `rekomendacje_studiow.db` przechowuje oddzielne profile, ankiety, oceny,
ulubione, wiadomości i preferencje każdego konta. Baza jest zapisana w wolumenie
Dockera. Migracje schematu wykonują się automatycznie, bez kasowania danych.

Startowy katalog zawiera 140 prawdziwych kierunków. Osobna usługa Dockera
`aktualizacja-danych` sprawdza co minutę datę ostatniego udanego pełnego importu.
Jeśli import jest starszy niż 24 godziny albo jeszcze go nie było, pobiera
wszystkie strony katalogów instytucji i kierunków RAD-on w tle.

Gdy zapisane dane są świeże, uruchomienie lub odświeżenie aplikacji nie powoduje
ponownego pobierania. W razie awarii API pozostaje poprzedni katalog, a próba
jest ponawiana po 15 minutach. Jednocześnie może działać tylko jeden importer.
Pełne rekordy API są zachowane w SQLite; import aktualizuje wpisy bez duplikatów
oraz nie zmienia kont, ankiet, ocen, wiadomości ani ulubionych.

W menu bocznym widać datę ostatniego pełnego importu i informację o pobieraniu.
Nowy katalog pojawia się przy kolejnej interakcji ze stroną. Synchronizacja działa,
gdy usługi Dockera są uruchomione, także bez otwartej strony i zalogowanego konta.
Po przerwie kontrola daty następuje przy starcie usługi.

Logi aktualizacji:

```powershell
docker compose logs --tail 30 aktualizacja-danych
```

Ranking łączy zainteresowania, przygotowanie przedmiotowe, mocne strony oraz
preferencje. Nie zgaduje progów ani kosztów studiów. Brak biologii nie oznacza
z automatu braku możliwości przyjęcia na medycynę. Twarde wykluczenie dotyczy
wyłącznie niespełnionych, zweryfikowanych wymagań: gdy znane są wyniki wszystkich
alternatyw danej grupy albo kandydat oznaczył maturę jako kompletną.
Opis algorytmu i ograniczeń: [BAZA_DANYCH.md](BAZA_DANYCH.md).

Model otrzymuje aktualny kontekst z bazy: dane zalogowanego kandydata, ranking
i wybrane pasujące oferty. Nie jest osobno trenowany na kontach. Nie dostaje haseł,
innych kont ani dokładnych współrzędnych domu. Nie wykonuje SQL i nie zmienia ocen
ani ankiety; może zapisać wyłącznie kontrolowane preferencje rankingu oraz wskazać
widok aplikacji. Proste skróty nawigacyjne działają natychmiast bez wywołania LLM.
Pierwsza odpowiedź po załadowaniu modelu może trwać dłużej; kolejne korzystają
z modelu pozostającego w pamięci.

Współrzędne miejscowości są dołączone lokalnie z [GeoNames](https://www.geonames.org/)
([źródło](https://download.geonames.org/export/dump/), CC BY 4.0). Znaczniki pokazują
miejscowości uczelni, nie budynki kampusów. Dystans jest przybliżony, w linii prostej.
Podkład OpenStreetMap i biblioteki mapy pobierane przez przeglądarkę wymagają internetu.
Bez niego nadal można wybrać miejscowość z lokalnej listy i korzystać z odległości,
profilu, rankingu oraz wcześniej przygotowanego lokalnego modelu.

## Sprawdzenie działania

```powershell
docker compose exec -T app python -m unittest discover -s tests -v
```

Testy korzystają z tymczasowych baz: obejmują konta, walidację, izolację danych,
ponowne wypełnianie ankiety, ranking, wymagania, odległości, import i formularze.
Nie zmieniają danych użytkowników. Testowanie samego modelu wymaga działającej Ollamy.

## Dokumentacja

- [Ollama w Dockerze](https://docs.ollama.com/docker)
- [Kolejność uruchamiania usług](https://docs.docker.com/compose/how-tos/startup-order/)
- [Obsługa GPU](https://docs.docker.com/compose/how-tos/gpu-support/)
