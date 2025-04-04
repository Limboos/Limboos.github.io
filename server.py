import os
import json
import asyncio
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
from datetime import datetime
import statistics as stats
import time
import threading

# Import scrapera
from olx_gravel_scraper import OlxGravelScraper
# Import LLM Integration
from LLM_Integration import BikeDataEnricher

app = FastAPI(title="OLX Gravel Bike Scraper API")

# Montowanie folderu statycznego
app.mount("/static", StaticFiles(directory="static"), name="static")

# Ścieżki do plików danych
DATA_DIR = "data"
BIKES_FILE = os.path.join(DATA_DIR, "gravel_bikes.json")
STATS_FILE = os.path.join(DATA_DIR, "statistics.json")
ENRICHED_BIKES_FILE = os.path.join(DATA_DIR, "enriched_bikes.json")
HTML_FILE = os.path.join("static", "index.html")

# Globalny obiekt do śledzenia postępu analizy AI
class AnalysisProgress:
    def __init__(self):
        self.current = 0
        self.total = 0
        self.status = "Nie rozpoczęto"
        self.is_running = False
        self.clients = set()
        
    def reset(self):
        self.current = 0
        self.total = 0
        self.status = "Inicjalizacja analizy..."
        self.is_running = True
        
    def update(self, current, total, status):
        self.current = current
        self.total = total
        self.status = status
        self.notify_clients()
        
    def complete(self):
        self.status = "Zakończono analizę"
        self.is_running = False
        self.notify_clients()
        
    def add_client(self, client):
        self.clients.add(client)
        return client
        
    def remove_client(self, client):
        self.clients.discard(client)
        
    def notify_clients(self):
        message = json.dumps({
            "current": self.current,
            "total": self.total,
            "status": self.status
        })
        for client in self.clients:
            client.put(f"data: {message}\n\n")

# Inicjalizacja obiektu postępu
analysis_progress = AnalysisProgress()

# Model danych roweru
class GravelBike(BaseModel):
    title: str
    price: float
    location: str
    date_added: str
    url: str
    brand: Optional[str] = None
    size: Optional[str] = None
    year: Optional[int] = None
    description: Optional[str] = None
    condition: Optional[str] = None
    color: Optional[str] = None
    derailleur_type: Optional[str] = None
    brake_type: Optional[str] = None
    frame_material: Optional[str] = None
    wheel_size: Optional[str] = None
    seller_type: Optional[str] = None
    bike_type: Optional[str] = None
    frame_size_desc: Optional[str] = None
    gears: Optional[str] = None
    weight: Optional[str] = None
    suspension: Optional[str] = None
    parameters: Optional[Dict[str, str]] = None
    ai_analysis: Optional[Dict[str, Any]] = None


# Funkcja do rozszerzania statystyk
def enhance_statistics():
    """Rozszerza statystyki o dodatkowe dane na podstawie enriched_bikes."""
    try:
        # Wczytaj podstawowe statystyki, jeśli istnieją
        base_stats = {}
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                base_stats = json.load(f)
        
        # Jeśli nie ma wzbogaconych danych, zwróć podstawowe statystyki
        if not os.path.exists(ENRICHED_BIKES_FILE):
            return base_stats
        
        # Wczytaj wzbogacone dane rowerów
        with open(ENRICHED_BIKES_FILE, 'r', encoding='utf-8') as f:
            bikes = json.load(f)
        
        # Jeśli nie ma żadnych danych, zwróć podstawowe statystyki
        if not bikes:
            return base_stats
        
        # Inicjalizacja nowych statystyk
        bicycle_type_counts = {}
        avg_price_by_type = {}
        avg_price_by_brand = {}
        frame_material_counts = {}
        wheel_size_counts = {}
        condition_counts = {}
        used_vs_new = {"new": 0, "used": 0, "avg_price_new": 0, "avg_price_used": 0}
        value_assessment_counts = {"fair": 0, "overpriced": 0, "underpriced": 0}
        monthly_counts = {}
        
        # Suma cen dla obliczania średnich
        price_sum_by_type = {}
        price_sum_by_brand = {}
        price_sum_new = 0
        price_sum_used = 0
        
        # Licznik identyfikacji
        identified_bike_types = 0
        identified_condition = 0
        
        # Analiza wszystkich rowerów
        for bike in bikes:
            # Typ roweru
            if bike.get('ai_analysis') and bike['ai_analysis'].get('parsed_details'):
                parsed_details = bike['ai_analysis']['parsed_details']
                
                # Typ roweru
                bike_type = parsed_details.get('bicycle_type')
                if bike_type:
                    identified_bike_types += 1
                    bicycle_type_counts[bike_type] = bicycle_type_counts.get(bike_type, 0) + 1
                    
                    if bike.get('price'):
                        price_sum_by_type[bike_type] = price_sum_by_type.get(bike_type, 0) + bike['price']
                
                # Materiał ramy
                frame_material = parsed_details.get('frame_material')
                if frame_material:
                    frame_material_counts[frame_material] = frame_material_counts.get(frame_material, 0) + 1
                
                # Rozmiar kół
                wheel_size = parsed_details.get('wheel_size')
                if wheel_size:
                    wheel_size_counts[wheel_size] = wheel_size_counts.get(wheel_size, 0) + 1
                
                # Stan roweru
                condition = parsed_details.get('condition')
                if condition:
                    identified_condition += 1
                    condition_counts[condition] = condition_counts.get(condition, 0) + 1
                    
                    # Używane vs nowe
                    if condition.lower() == 'nowy':
                        used_vs_new["new"] += 1
                        if bike.get('price'):
                            price_sum_new += bike['price']
                    else:
                        used_vs_new["used"] += 1
                        if bike.get('price'):
                            price_sum_used += bike['price']
            
            # Ceny według marki
            if bike.get('brand') and bike.get('price'):
                brand = bike['brand']
                avg_price_by_brand[brand] = avg_price_by_brand.get(brand, 0) + bike['price']
            
            # Ocena wartości
            if bike.get('ai_analysis') and bike['ai_analysis'].get('value') and bike['ai_analysis']['value'].get('value_analysis'):
                value_assessment = bike['ai_analysis']['value']['value_analysis'].get('value_assessment')
                if value_assessment:
                    value_assessment_counts[value_assessment] = value_assessment_counts.get(value_assessment, 0) + 1
            
            # Sezonowość (miesiące dodania ogłoszeń)
            if bike.get('date_added'):
                try:
                    # Próba parsowania daty - może być w różnych formatach
                    date_str = bike['date_added']
                    # Sprawdź różne formaty daty
                    date_formats = ["%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y", "%Y.%m.%d"]
                    
                    for date_format in date_formats:
                        try:
                            date = datetime.strptime(date_str, date_format)
                            month_name = date.strftime("%B")  # Pełna nazwa miesiąca
                            monthly_counts[month_name] = monthly_counts.get(month_name, 0) + 1
                            break
                        except ValueError:
                            continue
                except Exception:
                    # Ignoruj błędy podczas parsowania daty
                    pass
        
        # Obliczanie średnich cen
        for bike_type, total in price_sum_by_type.items():
            if bicycle_type_counts.get(bike_type, 0) > 0:
                avg_price_by_type[bike_type] = total / bicycle_type_counts[bike_type]
        
        for brand, total in avg_price_by_brand.items():
            brand_count = 0
            for bike in bikes:
                if bike.get('brand') == brand:
                    brand_count += 1
            if brand_count > 0:
                avg_price_by_brand[brand] = total / brand_count
        
        # Średnie ceny dla nowych i używanych
        if used_vs_new["new"] > 0:
            used_vs_new["avg_price_new"] = price_sum_new / used_vs_new["new"]
        if used_vs_new["used"] > 0:
            used_vs_new["avg_price_used"] = price_sum_used / used_vs_new["used"]
        
        # Dodaj nowe statystyki do podstawowych
        base_stats.update({
            "bicycle_type_counts": bicycle_type_counts,
            "avg_price_by_type": avg_price_by_type,
            "avg_price_by_brand": avg_price_by_brand,
            "frame_material_counts": frame_material_counts,
            "wheel_size_counts": wheel_size_counts,
            "condition_counts": condition_counts,
            "used_vs_new": used_vs_new,
            "value_assessment_counts": value_assessment_counts,
            "monthly_counts": monthly_counts,
            "identified_bike_types": identified_bike_types,
            "identified_condition": identified_condition
        })
        
        return base_stats
    
    except Exception as e:
        print(f"Błąd podczas rozszerzania statystyk: {str(e)}")
        # W przypadku błędu zwróć podstawowe statystyki
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}


@app.get("/")
async def get_index():
    """Zwraca stronę główną aplikacji."""
    return FileResponse(HTML_FILE)


@app.get("/api/scrape")
async def scrape_data(pages: int = Query(5, ge=1, le=20)):
    """Pobiera nowe dane z OLX."""
    try:
        # Utworzenie katalogu danych, jeśli nie istnieje
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Inicjalizacja i uruchomienie scrapera
        scraper = OlxGravelScraper(max_pages=pages)
        bikes = await scraper.scrape()
        
        # Zapisanie danych
        scraper.save_to_csv(os.path.join(DATA_DIR, "gravel_bikes.csv"))
        scraper.save_to_json(BIKES_FILE)
        
        # Generowanie i zapisanie statystyk
        stats = scraper.generate_statistics()
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        # Zwrócenie danych jako JSON
        return JSONResponse(content=[bike.__dict__ for bike in bikes])
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd scraping'u: {str(e)}")


@app.get("/api/data/bikes", response_model=List[GravelBike])
async def get_bikes():
    """Zwraca zapisane dane rowerów."""
    try:
        print(f"API: get_bikes called, checking if {BIKES_FILE} exists")
        if not os.path.exists(BIKES_FILE):
            print(f"API: {BIKES_FILE} does not exist, returning empty list")
            return []
        
        print(f"API: Reading data from {BIKES_FILE}")
        with open(BIKES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"API: Loaded {len(data)} bikes from file")
            return data
    
    except Exception as e:
        print(f"API: Error reading bike data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Błąd odczytu danych: {str(e)}")


@app.get("/api/data/statistics", response_model=Dict[str, Any])
async def get_statistics():
    """Zwraca rozszerzone statystyki."""
    try:
        print("API: get_statistics called")
        # Używamy funkcji rozszerzającej statystyki
        extended_stats = enhance_statistics()
        print(f"API: Enhanced statistics: {extended_stats}")
        return extended_stats
    
    except Exception as e:
        print(f"API: Error reading statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Błąd odczytu statystyk: {str(e)}")


@app.get("/api/ai-analyze")
async def analyze_bikes():
    """Analizuje zapisane dane rowerów za pomocą LLM."""
    global analysis_progress
    
    try:
        if not os.path.exists(BIKES_FILE):
            raise HTTPException(status_code=404, detail="Brak danych do analizy. Najpierw pobierz dane z OLX.")
        
        # Jeśli analiza już jest w trakcie, zwróć informację
        if analysis_progress.is_running:
            return JSONResponse(content={"status": "Analiza już jest w trakcie"})
        
        # Resetuj postęp
        analysis_progress.reset()
        
        # Uruchom analizę w osobnym wątku
        def run_analysis():
            try:
                # Wczytaj dane rowerów
                with open(BIKES_FILE, 'r', encoding='utf-8') as f:
                    bikes = json.load(f)
                
                # Ustaw całkowitą liczbę rowerów
                analysis_progress.update(0, len(bikes), "Przygotowanie do analizy...")
                
                # Inicjalizacja BikeDataEnricher
                enricher = BikeDataEnricher()
                enricher.set_progress_callback(lambda current, total, status: 
                    analysis_progress.update(current, total, status))
                
                # Analiza danych
                enriched_bikes = enricher.process_bikes_from_json(BIKES_FILE, ENRICHED_BIKES_FILE)
                
                # Zakończ postęp
                analysis_progress.complete()
                
            except Exception as e:
                analysis_progress.status = f"Błąd analizy: {str(e)}"
                analysis_progress.is_running = False
        
        # Uruchom wątek
        threading.Thread(target=run_analysis).start()
        
        # Zwróć natychmiast status, analiza będzie kontynuowana w tle
        return JSONResponse(content={"status": "Rozpoczęto analizę AI"})
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd analizy AI: {str(e)}")


@app.get("/api/ai-analyze/progress")
async def analysis_progress_stream():
    """Strumieniuje aktualizacje postępu analizy AI za pomocą SSE."""
    async def event_generator():
        queue = asyncio.Queue()
        client = analysis_progress.add_client(queue)
        
        # Wyślij początkowe dane postępu
        initial_data = json.dumps({
            "current": analysis_progress.current,
            "total": analysis_progress.total,
            "status": analysis_progress.status
        })
        yield f"data: {initial_data}\n\n"
        
        try:
            while True:
                data = await queue.get()
                yield data
        except asyncio.CancelledError:
            # Usuń klienta przy zamknięciu połączenia
            analysis_progress.remove_client(client)
            raise
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/data/enriched-bikes")
async def get_enriched_bikes():
    """Zwraca wzbogacone dane rowerów."""
    try:
        print(f"API: get_enriched_bikes called, checking if {ENRICHED_BIKES_FILE} exists")
        if not os.path.exists(ENRICHED_BIKES_FILE):
            print(f"API: {ENRICHED_BIKES_FILE} does not exist, returning empty list")
            return []
        
        print(f"API: Reading enriched data from {ENRICHED_BIKES_FILE}")
        with open(ENRICHED_BIKES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"API: Loaded {len(data)} enriched bikes from file")
            return data
    
    except Exception as e:
        print(f"API: Error reading enriched bike data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Błąd odczytu wzbogaconych danych: {str(e)}")


if __name__ == "__main__":
    # Uruchomienie serwera
    uvicorn.run(app, host="0.0.0.0", port=8000)