# System rekomendacji kierunków studiów

Python, Streamlit, SQLite i lokalny model Qwen działają wspólnie w Docker Compose.

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


## Baza danych

Baza SQLite ma nazwę `rekomendacje_studiow.db` i polskie nazwy tabel oraz kolumn.
Przy pierwszym uruchomieniu kontenera automatycznie wczytuje 140 rzeczywistych
kierunków z zestawu startowego RAD-on/POL-on. Dane pozostają w wolumenie Dockera.

Logowanie i rejestracja są tymczasowo wyłączone. Katalog i przycisk
**Pobierz wszystkie dane z API** są dostępne od razu po otwarciu strony.
Przycisk pobiera pełne katalogi instytucji, kierunków i wariantów RAD-on,
pokazując postęp. Pełne rekordy są zachowywane w SQLite, a ponowny import
aktualizuje wpisy bez duplikatów. Każdy komputer ma własną bazę danych.
Rejestr RAD-on nie potwierdza otwartej rekrutacji ani progów przyjęcia.

[Struktura tabel, źródło API i sposób importowania danych](BAZA_DANYCH.md).

## Dokumentacja

- [Ollama w Dockerze](https://docs.ollama.com/docker)
- [Kolejność uruchamiania usług](https://docs.docker.com/compose/how-tos/startup-order/)
- [Obsługa GPU](https://docs.docker.com/compose/how-tos/gpu-support/)
