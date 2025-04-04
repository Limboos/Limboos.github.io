from typing import Dict, Any, List, Optional, Callable
from .ollama_parser import OllamaParser
import logging
import json
from pathlib import Path
import pandas as pd
import sys
import os
from dataclasses import asdict

# Add parent directory to path to import OlxGravelScraper
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from olx_gravel_scraper import GravelBike, OlxGravelScraper

logger = logging.getLogger("llm_adapter")

class BikeDataEnricher:
    """
    Adapter class that connects the OlxGravelScraper with OllamaParser
    to enrich bike data with AI analysis.
    """
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.parser = OllamaParser(ollama_url=ollama_url)
        self.progress_callback = None
        
    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """
        Set a callback function to report progress.
        
        Args:
            callback: Function taking current count, total count, and status message
        """
        self.progress_callback = callback
        
    def _report_progress(self, current: int, total: int, status: str):
        """
        Report progress through the callback if set.
        
        Args:
            current: Current item number
            total: Total number of items
            status: Status message
        """
        if self.progress_callback:
            self.progress_callback(current, total, status)
        
    def analyze_scraped_bikes(self, bikes: List[GravelBike]) -> List[Dict[str, Any]]:
        """
        Enrich the list of scraped bikes with AI analysis.
        
        Args:
            bikes: List of GravelBike objects from scraper
            
        Returns:
            List of enriched bike data dictionaries
        """
        enriched_bikes = []
        
        for bike in bikes:
            enriched_bike = self._enrich_bike(bike)
            enriched_bikes.append(enriched_bike)
            
        return enriched_bikes
    
    def _enrich_bike(self, bike: GravelBike) -> Dict[str, Any]:
        """
        Enrich a single bike with AI analysis.
        
        Args:
            bike: GravelBike object from scraper
            
        Returns:
            Dictionary with original and enriched data
        """
        # Convert bike to dictionary using dataclasses.asdict()
        bike_dict = asdict(bike)
        
        logger.info(f"Enriching bike: {bike.title[:50]}...")
        
        # Skip AI analysis if no description available
        if not bike.description:
            logger.warning(f"No description available for bike: {bike.title[:50]}...")
            bike_dict["ai_analysis"] = {"error": "No description available"}
            return bike_dict
        
        # Parse description using LLM
        try:
            parsed_data = self.parser.parse_bike_description(bike.description)
            # If parsing succeeded, categorize the bike
            if "error" not in parsed_data:
                category_data = self.parser.categorize_bike(bike.title, bike.description)
                
                # If both succeeded, analyze value
                if "error" not in category_data:
                    # Combine parsed data and category data for value analysis
                    combined_data = {**parsed_data, **category_data}
                    value_data = self.parser.identify_bike_value(combined_data)
                    
                    # Create the full AI analysis
                    bike_dict["ai_analysis"] = {
                        "parsed_details": parsed_data,
                        "category": category_data,
                        "value": value_data
                    }
                else:
                    bike_dict["ai_analysis"] = {
                        "parsed_details": parsed_data,
                        "category": category_data,
                        "value": {"error": "Could not analyze value due to categorization error"}
                    }
            else:
                bike_dict["ai_analysis"] = {
                    "parsed_details": parsed_data,
                    "category": {"error": "Could not categorize due to parsing error"},
                    "value": {"error": "Could not analyze value due to parsing error"}
                }
                
        except Exception as e:
            logger.error(f"Error during AI analysis for bike {bike.title[:50]}: {str(e)}")
            bike_dict["ai_analysis"] = {"error": f"Analysis error: {str(e)}"}
            
        return bike_dict
    
    def analyze_raw_descriptions(self, descriptions: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Analyze a list of raw bike descriptions.
        
        Args:
            descriptions: List of dictionaries with 'title' and 'description' keys
            
        Returns:
            List of analysis results
        """
        results = []
        
        for item in descriptions:
            title = item.get("title", "")
            description = item.get("description", "")
            
            if not description:
                results.append({
                    "title": title,
                    "analysis": {"error": "No description provided"}
                })
                continue
                
            # Parse description using LLM
            try:
                parsed_data = self.parser.parse_bike_description(description)
                category_data = self.parser.categorize_bike(title, description)
                
                # If both succeeded, analyze value
                if "error" not in parsed_data and "error" not in category_data:
                    combined_data = {**parsed_data, **category_data}
                    value_data = self.parser.identify_bike_value(combined_data)
                    
                    results.append({
                        "title": title,
                        "analysis": {
                            "parsed_details": parsed_data,
                            "category": category_data,
                            "value": value_data
                        }
                    })
                else:
                    results.append({
                        "title": title,
                        "analysis": {
                            "parsed_details": parsed_data,
                            "category": category_data,
                            "value": {"error": "Could not analyze value"}
                        }
                    })
            except Exception as e:
                logger.error(f"Error during analysis for '{title[:50]}': {str(e)}")
                results.append({
                    "title": title,
                    "analysis": {"error": f"Analysis error: {str(e)}"}
                })
                
        return results
    
    def process_bikes_from_json(self, json_file_path: str, output_file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Process bikes from a JSON file and save enriched data.
        
        Args:
            json_file_path: Path to JSON file with bike data
            output_file_path: Path to save enriched data (optional)
            
        Returns:
            List of enriched bike data
        """
        try:
            # Load bikes from JSON
            with open(json_file_path, 'r', encoding='utf-8') as f:
                bikes_data = json.load(f)
                
            # Convert to GravelBike objects if needed
            bikes = []
            for item in bikes_data:
                if isinstance(item, dict):
                    # Create GravelBike with all fields from the dictionary
                    bikes.append(GravelBike(**item))
                elif isinstance(item, GravelBike):
                    bikes.append(item)
            print(bikes_data[0])
            
            # Report initial progress
            total_bikes = len(bikes)
            self._report_progress(0, total_bikes, "Rozpoczynam analizę rowerów...")
            
            # Process each bike
            enriched_bikes = []
            for i, bike in enumerate(bikes):
                # Report progress for current bike
                self._report_progress(i, total_bikes, f"Analiza roweru {i+1}/{total_bikes}: {bike.title[:30]}...")
                
                # Enrich the bike
                enriched_bike = self._enrich_bike(bike)
                enriched_bikes.append(enriched_bike)
            
            # Report completion
            self._report_progress(total_bikes, total_bikes, "Zakończono analizę wszystkich rowerów")
            
            # Save to file if output path provided
            if output_file_path:
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    json.dump(enriched_bikes, f, ensure_ascii=False, indent=2)
            
            return enriched_bikes
        
        except Exception as e:
            logger.error(f"Error processing bikes from JSON: {str(e)}")
            # Report error in progress
            self._report_progress(0, 0, f"Błąd podczas analizy: {str(e)}")
            raise
    
    def process_bikes_from_csv(self, csv_file_path: str, output_file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Process bikes from a CSV file and save enriched data.
        
        Args:
            csv_file_path: Path to CSV file with bike data
            output_file_path: Path to save enriched data (optional)
            
        Returns:
            List of enriched bike data
        """
        try:
            # Load bikes from CSV
            df = pd.read_csv(csv_file_path)
            
            # Convert to GravelBike objects
            bikes = []
            for _, row in df.iterrows():
                bikes.append(GravelBike(
                    title=row.get("title", ""),
                    price=float(row.get("price", 0)),
                    location=row.get("location", ""),
                    date_added=row.get("date_added", ""),
                    url=row.get("url", ""),
                    brand=row.get("brand"),
                    size=row.get("size"),
                    year=row.get("year") if not pd.isna(row.get("year")) else None,
                    description=row.get("description") if not pd.isna(row.get("description")) else None
                ))
                
            # Analyze bikes
            enriched_bikes = self.analyze_scraped_bikes(bikes)
            
            # Save to output file if specified
            if output_file_path:
                if output_file_path.endswith('.json'):
                    with open(output_file_path, 'w', encoding='utf-8') as f:
                        json.dump(enriched_bikes, f, ensure_ascii=False, indent=2)
                elif output_file_path.endswith('.csv'):
                    # Flatten the nested AI analysis for CSV format
                    flat_data = []
                    for bike in enriched_bikes:
                        flat_bike = bike.copy()
                        if "ai_analysis" in flat_bike:
                            analysis = flat_bike.pop("ai_analysis")
                            # Extract key information from analysis
                            if "parsed_details" in analysis:
                                parsed = analysis["parsed_details"]
                                flat_bike["ai_bicycle_type"] = parsed.get("bicycle_type")
                                flat_bike["ai_brand"] = parsed.get("brand")
                                flat_bike["ai_model"] = parsed.get("model")
                                flat_bike["ai_frame_size"] = parsed.get("frame_size")
                                flat_bike["ai_frame_material"] = parsed.get("frame_material")
                                
                            if "category" in analysis:
                                cat = analysis["category"]
                                flat_bike["ai_primary_category"] = cat.get("primary_category")
                                flat_bike["ai_subcategory"] = cat.get("subcategory")
                                
                            if "value" in analysis and isinstance(analysis["value"], dict):
                                val = analysis["value"]
                                if "value_analysis" in val:
                                    va = val["value_analysis"]
                                    if "estimated_value_range" in va:
                                        flat_bike["ai_estimated_value_low"] = va["estimated_value_range"].get("low")
                                        flat_bike["ai_estimated_value_high"] = va["estimated_value_range"].get("high")
                                    flat_bike["ai_value_assessment"] = va.get("value_assessment")
                                flat_bike["ai_recommendation"] = val.get("overall_recommendation")
                                
                        flat_data.append(flat_bike)
                    
                    # Convert to DataFrame and save as CSV
                    pd.DataFrame(flat_data).to_csv(output_file_path, index=False)
                    
                logger.info(f"Saved enriched data to {output_file_path}")
                
            return enriched_bikes
            
        except Exception as e:
            logger.error(f"Error processing bikes from CSV: {str(e)}")
            return [] 