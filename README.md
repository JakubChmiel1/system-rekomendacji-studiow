# System rekomendacji kierunków studiów

Minimalny szkielet aplikacji: Python, Streamlit, SQLite i Docker Compose.

## Uruchomienie

Zainstaluj Git i Docker Desktop. Na Windows uruchom Docker Desktop z WSL 2
i kontenerami Linux. Sklonuj repozytorium i otwórz terminal w jego folderze:

```powershell
git clone ADRES_REPOZYTORIUM projekt
cd projekt
docker compose up --build -d --wait
```

Otwórz [localhost:8501](http://localhost:8501). Pierwsze budowanie wymaga internetu.

## Praca zespołu

Wszyscy pracujemy bezpośrednio na gałęzi `main`. Uzgadniamy podział zadań,
żeby nie zmieniać jednocześnie tych samych fragmentów kodu.

Przed rozpoczęciem zadania, po wysłaniu wcześniejszych zmian, pobierz aktualny kod:

```powershell
git switch main
git pull --ff-only
docker compose up --build -d --wait
```

Kod znajduje się w `app/`. Zmiany są widoczne po zapisaniu pliku i odświeżeniu strony.
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

Każdy ma własną bazę SQLite w wolumenie `sqlite_data`. Dane pozostają po
odtworzeniu kontenera. GitHub synchronizuje kod, a zawartość baz jest lokalna.

```powershell
docker compose down
```

Polecenie zatrzymuje aplikację i zachowuje bazę. Dodanie `-v` usuwa również bazę.

Folder `output/` zawiera materiały robocze i dokumenty; jest pomijany przez Git.
