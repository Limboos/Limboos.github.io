# OLX Gravel Bike Scraper & API

Prosty projekt do scrapowania ogłoszeń rowerów typu gravel z serwisu OLX.pl, udostępniający zebrane dane przez podstawowe API webowe oraz prosty interfejs frontendowy.

## Struktura plików

*   `olx_gravel_scraper.py`: Główny skrypt scrapujący. Zawiera logikę pobierania i parsowania stron OLX, ekstrakcji danych o rowerach oraz zapisywania wyników do plików.
*   `server.py`: Serwer webowy oparty na FastAPI. Udostępnia API do uruchamiania scrapera i pobierania zapisanych danych. Serwuje również plik `index.html`.
*   `static/`: Katalog na pliki statyczne (frontend).
    *   `index.html`: Podstawowa strona HTML do wyświetlania danych (wymaga implementacji).
*   `data/`: Katalog na wyniki działania scrapera (tworzony automatycznie).
    *   `gravel_bikes.csv`: Zebrane dane rowerów w formacie CSV.
    *   `gravel_bikes.json`: Zebrane dane rowerów w formacie JSON.
    *   `statistics.json`: Podstawowe statystyki wygenerowane na podstawie danych.
*   `README.md`: Ten plik - opis projektu.
*   `requirements.txt`: (Do utworzenia) Lista zależności Python.

## Działanie

1.  **Scraper (`olx_gravel_scraper.py`):**
    *   Łączy się z OLX.
    *   Przechodzi przez zadaną liczbę stron z listą ogłoszeń rowerów gravel.
    *   Wyciąga linki do poszczególnych ogłoszeń.
    *   Dla każdego ogłoszenia pobiera stronę i parsuje ją, wyciągając dane takie jak: tytuł, cena, lokalizacja, data dodania, opis, marka (jeśli wykryta), rozmiar (jeśli wykryty), rok (jeśli wykryty).
    *   Zapisuje zebrane dane do plików `gravel_bikes.csv` i `gravel_bikes.json` w katalogu `data/`.
    *   Generuje i zapisuje statystyki do pliku `data/statistics.json`.

2.  **Serwer (`server.py`):**
    *   Uruchamia aplikację webową FastAPI za pomocą Uvicorn.
    *   Na żądanie `GET /` zwraca plik `static/index.html`.
    *   Udostępnia następujące endpointy API:
        *   `GET /api/scrape?pages=N`: Uruchamia proces scrapowania dla `N` stron. Zwraca listę znalezionych rowerów jako JSON.
        *   `GET /api/data/bikes`: Zwraca zawartość pliku `data/gravel_bikes.json`.
        *   `GET /api/data/statistics`: Zwraca zawartość pliku `data/statistics.json`.

## Uruchomienie

1.  **Instalacja zależności:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Plik `requirements.txt` musi zostać najpierw utworzony)*

2.  **Uruchomienie samego scrapera (opcjonalnie):**
    ```bash
    python olx_gravel_scraper.py
    ```
    *(Spowoduje to pobranie danych i zapisanie ich w katalogu `data/`)*

3.  **Uruchomienie serwera API:**
    ```bash
    python server.py
    ```
    lub dla trybu deweloperskiego z automatycznym przeładowaniem:
    ```bash
    uvicorn server:app --reload
    ```

4.  **Dostęp do aplikacji:**
    Otwórz przeglądarkę i przejdź pod adres `http://localhost:8000` (lub `http://127.0.0.1:8000`).

## Aktualny stan i problemy

*   **Scraper nie działa:** Obecnie selektory CSS w `olx_gravel_scraper.py` są nieaktualne z powodu zmian na stronie OLX. Skrypt nie jest w stanie znaleźć linków do ogłoszeń. Wymaga to aktualizacji selektorów.
*   **Brak `requirements.txt`:** Należy utworzyć plik z listą zależności.
*   **Pusty `index.html`:** Plik frontendowy jest tylko zaślepką i wymaga implementacji do wyświetlania danych z API.
