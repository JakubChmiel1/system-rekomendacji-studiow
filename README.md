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

Kod znajduje się w `app/`. Zmiany są widoczne po zapisaniu pliku i odświeżeniu
strony. Każdy pracuje na swojej gałęzi i wysyła zmiany przez Pull Request.

Po zapisaniu własnej pracy i przejściu na wspólną gałąź pobierz aktualizacje:

```powershell
git pull --ff-only
docker compose up --build -d --wait
```

Ta sama gałąź i commit oznaczają ten sam etap projektu. Wersje bibliotek są
zapisane w `requirements.txt`, a obraz Pythona jest przypięty w `Dockerfile`.

## Baza i zatrzymanie

Każdy ma własną bazę SQLite w wolumenie `sqlite_data`. Dane pozostają po
odtworzeniu kontenera. GitHub synchronizuje kod, a zawartość baz jest lokalna.

```powershell
docker compose down
```

Polecenie zatrzymuje aplikację i zachowuje bazę. Dodanie `-v` usuwa również bazę.

Folder `output/` zawiera materiały robocze i dokumenty; jest pomijany przez Git.
