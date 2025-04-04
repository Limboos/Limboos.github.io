# LLM Integration for OLX Bike Parser

This module provides integration with the Ollama LLM (Large Language Model) API to analyze and enrich bike listing data scraped from OLX.

## Features

- Parse and structure raw bicycle listing descriptions using LLM
- Categorize bike listings into appropriate types (road, gravel, MTB, etc.)
- Analyze market value and provide price assessments
- Process bike data from either scraped content, JSON files, or CSV files
- Caching system to reduce redundant API calls

## Setup

1. Make sure you have Ollama installed and running locally:
   - Visit [Ollama website](https://ollama.ai/) for installation instructions
   - Ollama should be running on http://localhost:11434 (default)

2. Pull the required models:
   ```bash
   ollama pull llama3:8b
   ```

3. Install required Python dependencies:
   ```bash
   pip install requests pandas
   ```

## Usage

### Analyzing a Single Bike Description

```python
from LLM_Integration import OllamaParser

parser = OllamaParser()
result = parser.parse_bike_description("Rower szosowy Giant TCR, karbonowa rama, rozmiar M, Shimano 105, koła 28\", stan bardzo dobry...")
print(result)
```

### Processing Multiple Bikes from OLX Scraper

```python
import asyncio
from olx_gravel_scraper import OlxGravelScraper
from LLM_Integration import BikeDataEnricher

async def main():
    # Scrape data
    scraper = OlxGravelScraper(search_query="gravel", max_pages=3)
    bikes = await scraper.scrape()
    
    # Analyze with LLM
    enricher = BikeDataEnricher()
    enriched_bikes = enricher.analyze_scraped_bikes(bikes)
    
    # Save results
    with open("enriched_bikes.json", "w", encoding="utf-8") as f:
        json.dump(enriched_bikes, f, ensure_ascii=False, indent=2)

asyncio.run(main())
```

### Using the Command Line Interface

The module includes a convenient CLI for common tasks:

```bash
# Scrape and analyze data
python -m LLM_Integration.example scrape --query "szosowy" --pages 5

# Analyze existing data
python -m LLM_Integration.example analyze path/to/bikes.json

# Analyze a single text description
python -m LLM_Integration.example text --title "Giant TCR" --description "Sprzedam rower szosowy..."
```

## Module Structure

- `ollama_parser.py` - Core integration with Ollama API
- `adapter.py` - Adapter to connect OlxGravelScraper with OllamaParser
- `example.py` - Example script and CLI interface
- `__init__.py` - Package initialization

## Response Format

The enriched bike data includes three main AI analysis components:

1. **parsed_details** - Structured information extracted from description:
   - bicycle_type
   - brand
   - model
   - frame_size
   - frame_material
   - wheel_size
   - groupset
   - drivetrain
   - condition
   - price

2. **category** - Categorization of the bike:
   - primary_category
   - subcategory
   - intended_use
   - price_category

3. **value** - Market value assessment:
   - estimated_value_range
   - value_assessment
   - selling_points
   - concerns
   - recommendations

## Configuration

You can configure the LLM integration by modifying the OllamaParser class:

```python
from LLM_Integration import OllamaParser

# Use custom Ollama server URL
parser = OllamaParser(ollama_url="http://192.168.1.100:11434")

# Change the LLM model (if you have others pulled)
parser.llm_model = "llama3:70b"
```

## Error Handling

The module includes comprehensive error handling with automatic retries for API calls and fallback mechanisms for unavailable models. All operations are logged for troubleshooting purposes.

## Requirements

- Python 3.8+
- Ollama server running locally or on a network
- Required Python packages: requests, pandas 