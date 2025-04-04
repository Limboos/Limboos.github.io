import asyncio
import sys
import os
import json
from typing import List, Dict, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("ollama_example")

# Add parent directory to path to import OlxGravelScraper
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from olx_gravel_scraper import OlxGravelScraper
from LLM_Integration import BikeDataEnricher

async def scrape_and_analyze(search_query: str = "gravel", max_pages: int = 3):
    """
    Run the complete pipeline: scrape bike data and analyze it with LLM
    """
    logger.info(f"Starting scraper for query: {search_query}")
    
    # Initialize the scraper
    scraper = OlxGravelScraper(search_query=search_query, max_pages=max_pages)
    
    # Scrape the data
    bikes = await scraper.scrape()
    logger.info(f"Scraped {len(bikes)} bike listings")
    
    # Save raw data
    timestamp = asyncio.get_event_loop().time()
    scraper.save_to_json(f"data/raw_bikes_{timestamp:.0f}.json")
    
    # Initialize the enricher
    enricher = BikeDataEnricher()
    
    # Analyze the bikes
    logger.info("Starting LLM analysis of bike data")
    enriched_bikes = enricher.analyze_scraped_bikes(bikes)
    
    # Save enriched data
    output_path = f"data/enriched_bikes_{timestamp:.0f}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(enriched_bikes, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved enriched data to {output_path}")
    
    # Print sample analysis
    if enriched_bikes:
        sample = enriched_bikes[0]
        logger.info("Sample of analyzed data:")
        logger.info(f"Title: {sample['title']}")
        if 'ai_analysis' in sample and 'parsed_details' in sample['ai_analysis']:
            details = sample['ai_analysis']['parsed_details']
            logger.info(f"  Detected type: {details.get('bicycle_type', 'Unknown')}")
            logger.info(f"  Detected brand: {details.get('brand', 'Unknown')}")
            logger.info(f"  Frame material: {details.get('frame_material', 'Unknown')}")
            
            if 'value' in sample['ai_analysis'] and 'value_analysis' in sample['ai_analysis']['value']:
                value = sample['ai_analysis']['value']['value_analysis']
                if 'estimated_value_range' in value:
                    range_info = value['estimated_value_range']
                    logger.info(f"  Estimated value: {range_info.get('low', 'N/A')} - {range_info.get('high', 'N/A')} {range_info.get('currency', 'PLN')}")
                logger.info(f"  Assessment: {value.get('value_assessment', 'Unknown')}")
    
    return enriched_bikes

async def analyze_existing_data(json_file_path: str):
    """
    Analyze existing bike data from a JSON file
    """
    logger.info(f"Analyzing existing data from: {json_file_path}")
    
    # Initialize the enricher
    enricher = BikeDataEnricher()
    
    # Process the data
    output_path = f"{os.path.splitext(json_file_path)[0]}_enriched.json"
    enriched_bikes = enricher.process_bikes_from_json(json_file_path, output_path)
    
    logger.info(f"Analyzed {len(enriched_bikes)} bike listings")
    logger.info(f"Saved enriched data to {output_path}")
    
    return enriched_bikes

def analyze_raw_text(title: str, description: str):
    """
    Analyze a single raw bike description for testing
    """
    logger.info("Analyzing raw text description")
    
    # Initialize the enricher
    enricher = BikeDataEnricher()
    
    # Analyze the text
    results = enricher.analyze_raw_descriptions([{"title": title, "description": description}])
    
    if results:
        result = results[0]
        logger.info(f"Analysis for: {result['title']}")
        
        if 'analysis' in result and 'parsed_details' in result['analysis']:
            details = result['analysis']['parsed_details']
            logger.info(f"Detected type: {details.get('bicycle_type', 'Unknown')}")
            logger.info(f"Detected brand: {details.get('brand', 'Unknown')}")
            logger.info(f"Frame material: {details.get('frame_material', 'Unknown')}")
            
            if 'value' in result['analysis'] and 'value_analysis' in result['analysis']['value']:
                value = result['analysis']['value']['value_analysis']
                if 'estimated_value_range' in value:
                    range_info = value['estimated_value_range']
                    logger.info(f"Estimated value: {range_info.get('low', 'N/A')} - {range_info.get('high', 'N/A')} {range_info.get('currency', 'PLN')}")
                logger.info(f"Assessment: {value.get('value_assessment', 'Unknown')}")
    
    return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Bike data scraper and analyzer")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Scrape and analyze command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape and analyze bike data")
    scrape_parser.add_argument("--query", type=str, default="gravel", help="Search query for OLX")
    scrape_parser.add_argument("--pages", type=int, default=3, help="Maximum number of pages to scrape")
    
    # Analyze existing data command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze existing bike data from a file")
    analyze_parser.add_argument("file", type=str, help="Path to JSON file with bike data")
    
    # Analyze raw text command
    text_parser = subparsers.add_parser("text", help="Analyze a raw bike description")
    text_parser.add_argument("--title", type=str, required=True, help="Bike listing title")
    text_parser.add_argument("--description", type=str, required=True, help="Bike listing description")
    
    args = parser.parse_args()
    
    if args.command == "scrape":
        asyncio.run(scrape_and_analyze(args.query, args.pages))
    elif args.command == "analyze":
        asyncio.run(analyze_existing_data(args.file))
    elif args.command == "text":
        analyze_raw_text(args.title, args.description)
    else:
        parser.print_help() 