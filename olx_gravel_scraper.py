import asyncio
import aiohttp
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
import pandas as pd
from pathlib import Path
import signal
import sys
import platform

@dataclass
class GravelBike:
    """Klasa przechowująca dane o rowerze gravel."""
    title: str
    price: float
    location: str
    date_added: str
    url: str
    brand: Optional[str] = None
    size: Optional[str] = None
    year: Optional[int] = None
    description: Optional[str] = None
    # Dodatkowe parametry z sekcji technicznej
    condition: Optional[str] = None  # Stan
    color: Optional[str] = None  # Kolor
    derailleur_type: Optional[str] = None  # Rodzaj przerzutki
    brake_type: Optional[str] = None  # Typ hamulca
    frame_material: Optional[str] = None  # Materiał ramy
    wheel_size: Optional[str] = None  # Rozmiar koła
    seller_type: Optional[str] = None  # Prywatne/Firmowe
    bike_type: Optional[str] = None  # Typ roweru
    frame_size_desc: Optional[str] = None  # Opis rozmiaru ramy
    gears: Optional[str] = None  # Liczba przerzutek
    weight: Optional[str] = None  # Waga
    suspension: Optional[str] = None  # Amortyzacja
    parameters: Optional[Dict[str, str]] = None  # Wszystkie parametry jako słownik

class OlxGravelScraper:
    """Scraper do pobierania danych o rowerach gravel z OLX."""
    
    BASE_URL = "https://www.olx.pl/sport-hobby/rowery/"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    def __init__(self, search_query: str = "gravel", max_pages: int = 25):
        self.search_query = search_query
        self.max_pages = max_pages
        self.bikes: List[GravelBike] = []
        self.common_brands = [
            "specialized", "trek", "cannondale", "giant", "kross", "cube", "merida", 
            "scott", "orbea", "canyon", "focus", "bombtrack", "ridley", "marin", 
            "gt", "rondo", "diamant", "bmc", "triban", "decathlon", "btwin", "vitus",
            "cervelo", "cinelli", "fuji", "genesis", "gravelone", "pinnacle", "ribble",
            "salsa", "santa cruz", "surly", "norco", "topeak", "tern", "wilier", "ragley",
            "lauf", "diverge", "checkpoint", "topstone", "revolt", "grade", "aspero", "grizl",
            "niner", "poseidon", "state bicycle", "jamis", "felt", "polygon", "saracen",
            "nuroad", "trex", "romet", "fulcrum", "serious", "votec", "rose"
        ]
    
    async def fetch_page(self, session: aiohttp.ClientSession, url: str, max_retries: int = 3) -> str:
        """Pobiera zawartość strony z możliwością ponownych prób."""
        retries = 0
        while retries < max_retries:
            try:
                headers = self.HEADERS.copy()
                # Dodanie losowego User-Agent, aby zapobiec blokowaniu
                user_agents = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36"
                ]
                headers["User-Agent"] = user_agents[retries % len(user_agents)]
                
                # Użycie timeoutu dla wszystkich operacji
                timeout = aiohttp.ClientTimeout(total=30, sock_connect=10, sock_read=10)
                
                async with session.get(url, headers=headers, timeout=timeout, ssl=False) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 404:
                        print(f"Strona nie istnieje: {url}")
                        return ""
                    elif response.status == 429:  # Too Many Requests
                        print(f"Za dużo zapytań, czekam {5 * (retries + 1)} sekund przed ponowieniem próby: {url}")
                        await asyncio.sleep(5 * (retries + 1))  # Increased delay for rate limit
                        retries += 1
                    else:
                        print(f"Błąd HTTP {response.status} dla URL: {url}")
                        retries += 1
                        await asyncio.sleep(2 * retries)  # Increasing delay between retries
            except (aiohttp.ClientError, asyncio.TimeoutError, asyncio.exceptions.TimeoutError) as e:
                print(f"Błąd połączenia dla {url}: {e}")
                retries += 1
                await asyncio.sleep(2 * retries)
            except (OSError, ConnectionResetError, ConnectionError) as e:
                print(f"Błąd sieci dla {url}: {e}")
                retries += 1
                await asyncio.sleep(3 * retries)  # Dłuższy czas oczekiwania dla błędów sieci
            except Exception as e:
                print(f"Nieoczekiwany błąd dla {url}: {e}")
                retries += 1
                await asyncio.sleep(2 * retries)
            finally:
                # Krótki odpoczynek po każdej próbie, aby zapobiec przeciążeniu
                await asyncio.sleep(0.5)
        
        print(f"Nie udało się pobrać strony po {max_retries} próbach: {url}")
        return ""
    
    def extract_listing_urls(self, html: str) -> List[str]:
        """Wyciąga linki do ogłoszeń z listingu."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Próba różnych selektorów dla linków ogłoszeń
        selectors = [
            'a[data-cy="listing-ad-title"]',
            'a[data-testid="listing-ad-title"]',
            'a.css-rc5s2u',
            'div.css-1sw7q4x a',
            'div[data-cy="l-card"] a',
            # Dodatkowe selektory na podstawie struktury strony 
            '.css-1bbgabe a',                # Links in listing cards
            'a[href*="/oferta/"]',           # Any link containing '/oferta/' in href
            'h6 a',                          # Common title links in listings
            '[data-cy="l-card"] a'           # Standard OLX listing card links
        ]
        
        # Filtrowanie tylko unikalnych linków do ogłoszeń
        urls = []
        
        # Próbujemy każdy selektor po kolei
        for selector in selectors:
            if urls:  # Jeśli już znaleźliśmy linki, przerywamy
                break
                
            links = soup.select(selector)
            for a in links:
                if a.has_attr('href'):
                    url = a['href']
                    
                    # Weryfikacja, czy to jest link do ogłoszenia
                    if '/oferta/' in url or '/d/oferta/' in url:
                        # Upewnienie się, że link jest pełnym URL-em
                        if not url.startswith('http'):
                            url = f"https://www.olx.pl{url}"
                        
                        # Unikalne linki
                        if url not in urls:
                            urls.append(url)
        
        # Jeśli nie znaleźliśmy żadnych linków przez selektory, szukamy standardowo przez '/oferta/'
        if not urls:
            for a in soup.find_all('a', href=True):
                if '/oferta/' in a['href']:
                    url = a['href']
                    if not url.startswith('http'):
                        url = f"https://www.olx.pl{url}"
                    if url not in urls:
                        urls.append(url)
        
        print(f"Znaleziono {len(urls)} linków do ogłoszeń")
        return urls
    
    async def parse_bike_details(self, session: aiohttp.ClientSession, url: str) -> Optional[GravelBike]:
        """Pobiera i analizuje szczegóły roweru z ogłoszenia."""
        try:
            html = await self.fetch_page(session, url)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Wydobycie tytułu - więcej selektorów dla większej kompatybilności
            title_element = (
                soup.select_one('h1[data-cy="ad_title"]') or 
                soup.select_one('h1.css-1soizd2') or
                soup.select_one('h1[data-testid="ad-title"]') or
                soup.select_one('h1[data-testid="heading"]') or
                soup.select_one('h1.css-1gnqkte') or
                # Jeśli nie znaleziono elementu h1, szukamy w tytule strony
                soup.select_one('title')
            )
            
            title = title_element.text.strip() if title_element else "Brak tytułu"
            
            # Wydobycie ceny - kontynuujemy z różnymi selektorami
            price_element = (
                soup.select_one('div[data-testid="ad-price-container"] h3') or 
                soup.select_one('h3[data-testid="ad-price-container"]') or
                soup.select_one('h3.css-okktvh-Text')
            )
            price_text = price_element.text.strip() if price_element else "0 zł"
            price = float(re.sub(r'[^\d.]', '', price_text.replace(',', '.')))
            
            # Wydobycie lokalizacji - próbujemy ją wyodrębnić z pola lokalizacja-data
            location_date_element = (
                soup.select_one('p[data-testid="location-date"]') or
                soup.select_one('p.css-vbz67q') or
                soup.select_one('p.css-b5m1rv') or
                soup.select_one('p[data-cy="location-date"]')
            )
            
            # Domyślna wartość
            location = "Nieznana"
            date_added = datetime.now().strftime("%d.%m.%Y")
            
            # Jeśli znaleźliśmy element lokalizacja-data, wydzielamy części
            if location_date_element:
                location_date_text = location_date_element.text.strip()
                
                # Format zwykle to: "Lokalizacja - Data"
                if " - " in location_date_text:
                    parts = location_date_text.split(" - ")
                    location = parts[0].strip()
                    if len(parts) > 1:
                        date_added = parts[1].strip()
                        # Usunięcie "Odświeżono dnia" jeśli występuje
                        if "Odświeżono dnia" in date_added:
                            date_added = date_added.replace("Odświeżono dnia", "").strip()
                else:
                    # Jeśli nie ma separatora, to przyjmujemy całą zawartość jako lokalizację
                    location = location_date_text
            
            # Wydobycie opisu
            description_element = (
                soup.select_one('div[data-cy="ad_description"]') or
                soup.select_one('div.css-g5mtbi-Text') or
                soup.select_one('div[data-testid="description"]')
            )
            description = description_element.text.strip() if description_element else ""
            
            # Ekstrakcja marki (pozostawiamy bez zmian)
            brand = None
            for b in self.common_brands:
                if b.lower() in title.lower() or b.lower() in description.lower():
                    brand = b.capitalize()
                    break
            
            # Zaktualizowane regexy dla rozmiaru i roku
            size_match = re.search(
                r'(?i)(?:rozmiar|rama)[:\s]*(\d{2,3}\s?cm|\d{1,2}"|\d+\.?\d*\s?cale?|XS|S|M|L|XL)',
                description
            )
            size = size_match.group(1) if size_match else None
            
            year_match = re.search(
                r'(?i)(?:rok\s*produkcji|model\s*roku|rok)[:\s]*(\d{4})',
                description
            )
            if not year_match:
                # Szukamy samego roku w tytule lub opisie
                year_match = re.search(r'(?i).*\b(20[0-2]\d)\b', title + " " + description)
                
            year = int(year_match.group(1)) if year_match else None
            
            # Wydobycie parametrów technicznych
            # Szukamy kontenera z parametrami
            parameters = {}
            parameters_container = (
                soup.select_one('div[data-testid="ad-parameters-container"]') or
                soup.select_one('div.css-41yf00')
            )
            
            # Wartości domyślne
            condition = None
            color = None
            derailleur_type = None
            brake_type = None 
            frame_material = None
            wheel_size = None
            seller_type = None
            bike_type = None
            frame_size_desc = None
            gears = None
            weight = None
            suspension = None
            
            if parameters_container:
                # Pobierz wszystkie wiersze parametrów
                param_rows = parameters_container.select('div.css-ae1s7g')
                
                for row in param_rows:
                    # Znajdź tekst parametru
                    param_text = row.select_one('p')
                    if param_text:
                        param_text = param_text.text.strip()
                        
                        # Jeśli mamy ":" w tekście, to jest to para klucz-wartość
                        if ":" in param_text:
                            key, value = param_text.split(":", 1)
                            key = key.strip()
                            value = value.strip()
                            parameters[key] = value
                            
                            # Mapowanie znanych parametrów
                            if key.lower() == "marka":
                                if not brand:  # Tylko jeśli nie znaleźliśmy marki wcześniej
                                    brand = value
                            elif key.lower() == "stan":
                                condition = value
                            elif key.lower() == "kolor":
                                color = value
                            elif key.lower() == "rodzaj przerzutki":
                                derailleur_type = value
                            elif key.lower() == "typ hamulca":
                                brake_type = value
                            elif key.lower() == "materiał ramy":
                                frame_material = value
                            elif key.lower() == "rozmiar koła":
                                wheel_size = value
                            elif key.lower() == "rozmiar ramy":
                                frame_size_desc = value
                                if not size:  # Jeśli nie wyciągnęliśmy wcześniej z opisu
                                    size = value
                            elif key.lower() == "waga":
                                weight = value
                            elif key.lower() == "amortyzacja":
                                suspension = value
                            elif key.lower() == "liczba biegów" or key.lower() == "przerzutki":
                                gears = value
                            elif key.lower() == "typ roweru":
                                bike_type = value
                        else:
                            # Jeśli nie ma ":", to może być np. "Prywatne"
                            if "prywatne" in param_text.lower():
                                seller_type = "Prywatne"
                                parameters["Typ sprzedawcy"] = "Prywatne"
                            elif "firmowe" in param_text.lower():
                                seller_type = "Firmowe"
                                parameters["Typ sprzedawcy"] = "Firmowe"
                            else:
                                # Dodaj jako pojedynczy parametr bez przypisanej kategorii
                                parameters[param_text] = "Tak"
            
            return GravelBike(
                title=title,
                price=price,
                location=location,
                date_added=date_added,
                url=url,
                brand=brand,
                size=size,
                year=year,
                description=description,
                condition=condition,
                color=color,
                derailleur_type=derailleur_type,
                brake_type=brake_type,
                frame_material=frame_material,
                wheel_size=wheel_size,
                seller_type=seller_type,
                bike_type=bike_type,
                frame_size_desc=frame_size_desc,
                gears=gears,
                weight=weight,
                suspension=suspension,
                parameters=parameters
            )
        except Exception as e:
            print(f"Błąd podczas parsowania {url}: {e}")
            return None
    
    async def scrape(self) -> List[GravelBike]:
        """Główna metoda do pobierania danych."""
        # Semafor do ograniczenia liczby jednoczesnych połączeń
        semaphore = asyncio.Semaphore(5)  # Limit do 5 jednoczesnych połączeń
        
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False, limit=10)) as session:
            # Pobieranie linków z wielu stron
            listing_urls = []
            for page_num in range(1, self.max_pages + 1):
                page_url = f"{self.BASE_URL}q-{self.search_query}/?page={page_num}"
                html = await self.fetch_page(session, page_url)
                page_listings = self.extract_listing_urls(html)
                listing_urls.extend(page_listings)
                print(f"Pobrano {len(page_listings)} linków ze strony {page_num}")
                # Krótka pauza między stronami, aby uniknąć blokady
                await asyncio.sleep(1)
            
            # Funkcja pomocnicza do bezpiecznego pobierania szczegółów
            async def safe_parse_bike(url):
                async with semaphore:
                    try:
                        return await self.parse_bike_details(session, url)
                    except Exception as e:
                        print(f"Błąd podczas analizy {url}: {e}")
                        return None
            
            # Pobieranie danych ze wszystkich ogłoszeń z limitem jednoczesnych połączeń
            tasks = [safe_parse_bike(url) for url in listing_urls]
            results = []
            
            # Przetwarzanie wyników w miarę ich ukończenia
            for future in asyncio.as_completed(tasks):
                try:
                    bike = await future
                    if bike:
                        results.append(bike)
                except Exception as e:
                    print(f"Błąd podczas przetwarzania zadania: {e}")
            
            # Filtrowanie None (błędnych wyników)
            self.bikes = [bike for bike in results if bike]
            return self.bikes
    
    def save_to_csv(self, filename: str = "gravel_bikes.csv"):
        """Zapisuje dane do pliku CSV."""
        df = pd.DataFrame([asdict(bike) for bike in self.bikes])
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"Zapisano {len(self.bikes)} rowerów do pliku {filename}")
    
    def save_to_json(self, filename: str = "gravel_bikes.json"):
        """Zapisuje dane do pliku JSON."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump([asdict(bike) for bike in self.bikes], f, ensure_ascii=False, indent=2)
        print(f"Zapisano {len(self.bikes)} rowerów do pliku {filename}")
    
    def generate_statistics(self) -> Dict[str, Any]:
        """Generuje podstawowe statystyki o danych."""
        if not self.bikes:
            return {}
        
        df = pd.DataFrame([asdict(bike) for bike in self.bikes])
        
        # Podstawowe statystyki
        stats = {
            "total_count": len(df),
            "avg_price": df["price"].mean(),
            "min_price": df["price"].min(),
            "max_price": df["price"].max(),
            "median_price": df["price"].median(),
            "brand_counts": df["brand"].value_counts().to_dict(),
            "top_locations": df["location"].value_counts().head(5).to_dict(),
        }
        
        # Dodatkowe statystyki dla nowych parametrów
        for param in [
            "condition", "color", "derailleur_type", "brake_type", 
            "frame_material", "wheel_size", "seller_type", "bike_type",
            "frame_size_desc", "gears", "weight", "suspension"
        ]:
            if param in df.columns and df[param].notna().any():
                stats[f"{param}_counts"] = df[param].value_counts().to_dict()
        
        # Dodatkowe statystyki jeśli dostępne
        if "year" in df.columns and df["year"].notna().any():
            stats["year_counts"] = df["year"].value_counts().to_dict()
            stats["avg_year"] = df["year"].mean()
        
        if "size" in df.columns and df["size"].notna().any():
            stats["size_counts"] = df["size"].value_counts().to_dict()
        
        # Analiza korelacji między ceną a parametrami
        if len(df) > 5:  # Tylko jeśli mamy wystarczająco dużo danych
            # Korelacja między rokiem a ceną (jeśli dostępne)
            if "year" in df.columns and df["year"].notna().any():
                year_price_corr = df["year"].corr(df["price"])
                stats["year_price_correlation"] = year_price_corr
            
            # Średnie ceny dla różnych materiałów ramy
            if "frame_material" in df.columns and df["frame_material"].notna().any():
                frame_material_prices = df.groupby("frame_material")["price"].mean().to_dict()
                stats["avg_price_by_frame_material"] = frame_material_prices
            
            # Średnie ceny dla różnych typów hamulców
            if "brake_type" in df.columns and df["brake_type"].notna().any():
                brake_type_prices = df.groupby("brake_type")["price"].mean().to_dict()
                stats["avg_price_by_brake_type"] = brake_type_prices
        
        return stats
    
    def save_partial_results(self, filename_prefix: str = "partial_results"):
        """Zapisuje częściowe wyniki, jeśli scraping zostanie przerwany."""
        if not self.bikes:
            print("Brak danych do zapisania.")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/{filename_prefix}_{timestamp}"
        
        # Zapisz dane w formacie CSV i JSON
        df = pd.DataFrame([asdict(bike) for bike in self.bikes])
        df.to_csv(f"{filename}.csv", index=False, encoding='utf-8')
        
        with open(f"{filename}.json", 'w', encoding='utf-8') as f:
            json.dump([asdict(bike) for bike in self.bikes], f, ensure_ascii=False, indent=2)
            
        print(f"Zapisano {len(self.bikes)} częściowych wyników do plików {filename}.csv i {filename}.json")

    def print_parameters_summary(self):
        """Wyświetla podsumowanie znalezionych parametrów technicznych rowerów."""
        if not self.bikes:
            print("Brak danych do analizy.")
            return
            
        # Zbierz wszystkie unikalne parametry z różnych ogłoszeń
        all_params = {}
        for bike in self.bikes:
            if bike.parameters:
                for key, value in bike.parameters.items():
                    if key not in all_params:
                        all_params[key] = []
                    if value not in all_params[key]:
                        all_params[key].append(value)
        
        # Wyświetl podsumowanie
        print("\n=== PODSUMOWANIE PARAMETRÓW TECHNICZNYCH ===")
        print(f"Znaleziono {len(all_params)} różnych parametrów w {len(self.bikes)} ogłoszeniach:")
        
        for param, values in sorted(all_params.items()):
            print(f"\n* {param}:")
            if len(values) <= 10:  # Jeśli mało wartości, wyświetl wszystkie
                for val in sorted(values):
                    print(f"  - {val}")
            else:  # Jeśli dużo wartości, wyświetl tylko liczbę
                print(f"  - {len(values)} różnych wartości")
                # Przykładowe wartości
                print(f"  - Przykłady: {', '.join(sorted(values)[:5])}...")
        
        # Statystyki dot. kompletności danych
        print("\n=== KOMPLETNOŚĆ DANYCH ===")
        param_counts = {param: 0 for param in all_params}
        
        for bike in self.bikes:
            if bike.parameters:
                for param in bike.parameters:
                    param_counts[param] += 1
        
        for param, count in sorted(param_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(self.bikes)) * 100
            print(f"{param}: {count}/{len(self.bikes)} ({percentage:.1f}%)")
            
        # Dodaj wynik do pliku statystyk
        stats_file = "data/parameters_summary.txt"
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write("=== PODSUMOWANIE PARAMETRÓW TECHNICZNYCH ===\n")
            f.write(f"Znaleziono {len(all_params)} różnych parametrów w {len(self.bikes)} ogłoszeniach:\n\n")
            
            for param, values in sorted(all_params.items()):
                f.write(f"* {param}:\n")
                if len(values) <= 20:  # W pliku można więcej wyświetlić
                    for val in sorted(values):
                        f.write(f"  - {val}\n")
                else:
                    f.write(f"  - {len(values)} różnych wartości\n")
                    f.write(f"  - Przykłady: {', '.join(sorted(values)[:10])}...\n")
                f.write("\n")
            
            f.write("=== KOMPLETNOŚĆ DANYCH ===\n")
            for param, count in sorted(param_counts.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(self.bikes)) * 100
                f.write(f"{param}: {count}/{len(self.bikes)} ({percentage:.1f}%)\n")
        
        print(f"\nSzczegółowe podsumowanie zapisano do pliku: {stats_file}")


async def main():
    # Windows-specific fix dla problemów z asyncio ProactorEventLoop
    if platform.system() == 'Windows':
        # Zapobieganie problemom z zamykaniem socketów w Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Zwiększenie limitu połączeń
        import socket
        socket.setdefaulttimeout(30)  # 30 sekund timeout
    
    # Utworzenie katalogu data jeśli nie istnieje
    Path("data").mkdir(exist_ok=True)
    
    # Definicja zapytań do wyszukiwania
    search_queries = ["gravel", "rower gravel", "gravela"]
    
    # Zmienne globalne dla obsługi sygnałów
    current_scraper = None
    stopping = False
    
    # Funkcja obsługi sygnału przerwania
    def signal_handler(sig, frame):
        nonlocal stopping
        if stopping:
            print("\nWymuszenie zakończenia programu...")
            sys.exit(1)
        
        stopping = True
        print("\nOtrzymano sygnał przerwania. Zapisywanie częściowych wyników i zakończenie...")
        
        if current_scraper and current_scraper.bikes:
            current_scraper.save_partial_results("interrupted_results")
        
        sys.exit(0)
    
    # Rejestracja obsługi sygnału
    signal.signal(signal.SIGINT, signal_handler)
    
    all_bikes = []
    
    # Pobieranie danych dla różnych zapytań
    for query in search_queries:
        if stopping:
            break
            
        print(f"\nRozpoczynanie wyszukiwania dla zapytania: '{query}'")
        
        # Inicjalizacja i uruchomienie scrapera
        scraper = OlxGravelScraper(search_query=query, max_pages=5)
        current_scraper = scraper  # Przypisanie do zmiennej globalnej
        
        try:
            bikes = await scraper.scrape()
            all_bikes.extend(bikes)
            
            # Zapisanie danych dla konkretnego zapytania
            filename_base = f"data/{query.replace(' ', '_')}"
            scraper.save_to_csv(f"{filename_base}.csv")
            scraper.save_to_json(f"{filename_base}.json")
            
            print(f"Znaleziono {len(bikes)} rowerów dla zapytania '{query}'")
            
            # Okresowe zapisywanie częściowych wyników
            scraper.save_partial_results(f"partial_{query.replace(' ', '_')}")
            
        except Exception as e:
            print(f"Błąd podczas scrapowania dla zapytania '{query}': {e}")
            if scraper.bikes:
                scraper.save_partial_results(f"error_{query.replace(' ', '_')}")
    
    # Usunięcie duplikatów na podstawie URL
    unique_bikes = []
    unique_urls = set()
    
    for bike in all_bikes:
        if bike.url not in unique_urls:
            unique_bikes.append(bike)
            unique_urls.add(bike.url)
    
    if not unique_bikes:
        print("Nie znaleziono żadnych danych. Kończenie programu.")
        return
    
    # Zapisanie zbiorczych danych
    combined_scraper = OlxGravelScraper()
    combined_scraper.bikes = unique_bikes
    
    combined_scraper.save_to_csv("data/all_gravel_bikes.csv")
    combined_scraper.save_to_json("data/all_gravel_bikes.json")
    
    # Wyświetl podsumowanie parametrów
    combined_scraper.print_parameters_summary()
    
    # Generowanie i zapisanie statystyk
    stats = combined_scraper.generate_statistics()
    with open("data/statistics.json", 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"\nŁącznie znaleziono {len(unique_bikes)} unikalnych rowerów gravel")
    
    if 'avg_price' in stats:
        print(f"Średnia cena: {stats['avg_price']:.2f} zł")
    
    if 'brand_counts' in stats:
        print(f"Najpopularniejsze marki: {list(stats['brand_counts'].keys())[:5]}")
        
    # Wyświetl najciekawsze statystyki techniczne
    print("\n=== STATYSTYKI TECHNICZNE ===")
    
    if 'frame_material_counts' in stats:
        print("\nRozkład materiałów ramy:")
        for material, count in sorted(stats['frame_material_counts'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"- {material}: {count} rowerów")
            
    if 'brake_type_counts' in stats:
        print("\nRozkład typów hamulców:")
        for brake, count in sorted(stats['brake_type_counts'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"- {brake}: {count} rowerów")
            
    if 'avg_price_by_frame_material' in stats:
        print("\nŚrednia cena według materiału ramy:")
        for material, avg_price in sorted(stats['avg_price_by_frame_material'].items(), key=lambda x: x[1], reverse=True):
            print(f"- {material}: {avg_price:.2f} zł")
            
    if 'year_price_correlation' in stats:
        corr = stats['year_price_correlation']
        print(f"\nKorelacja roku produkcji z ceną: {corr:.2f}")
        if corr > 0.6:
            print("Silna dodatnia korelacja - nowsze rowery są znacznie droższe.")
        elif corr > 0.3:
            print("Umiarkowana dodatnia korelacja - nowsze rowery są nieco droższe.")
        elif corr > 0:
            print("Słaba dodatnia korelacja - rok produkcji ma niewielki wpływ na cenę.")
        else:
            print("Brak lub ujemna korelacja - rok produkcji nie ma wpływu na cenę lub starsze rowery są droższe.")


if __name__ == "__main__":
    # Windows-specific fix dla problemów z asyncio ProactorEventLoop
    if platform.system() == 'Windows':
        # Zapobieganie problemom z zamykaniem socketów w Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Zwiększenie limitu połączeń
        import socket
        socket.setdefaulttimeout(30)  # 30 sekund timeout
    
    try:
        # Ustawienie limitu dla ilości zadań asynchronicznych
        asyncio.get_event_loop().set_debug(False)
        if hasattr(asyncio, 'WindowsProactorEventLoopPolicy') and platform.system() == 'Windows':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram przerwany przez użytkownika.")
    except (OSError, ConnectionResetError) as e:
        print(f"\nBłąd połączenia: {e}")
        print("Ten błąd jest często spowodowany ograniczeniami Windows z aiohttp.")
        print("Spróbuj uruchomić program ponownie z mniejszą liczbą jednoczesnych połączeń.")
    except Exception as e:
        print(f"Nieoczekiwany błąd: {e}")
        import traceback
        traceback.print_exc()