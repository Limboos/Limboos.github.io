import requests
import json
import time
import re
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("ollama_parser")

class LRUCache:
    """Limited size cache with time expiration"""
    def __init__(self, capacity: int = 100, ttl: int = 60):
        self.capacity = capacity
        self.ttl = ttl  # Time to live in seconds
        self.cache = {}
        self.timestamps = {}
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get an item from the cache if it exists and is not expired"""
        with self.lock:
            if key not in self.cache:
                return None
            
            current_time = time.time()
            if current_time - self.timestamps[key] > self.ttl:
                # Item expired
                del self.cache[key]
                del self.timestamps[key]
                return None
            
            # Move to front of LRU (by updating timestamp)
            self.timestamps[key] = current_time
            return self.cache[key]
    
    def put(self, key: str, value: Any) -> None:
        """Put an item in the cache"""
        with self.lock:
            current_time = time.time()
            
            # If key exists, just update
            if key in self.cache:
                self.cache[key] = value
                self.timestamps[key] = current_time
                return
            
            # If at capacity, remove oldest item
            if len(self.cache) >= self.capacity:
                oldest_key = min(self.timestamps, key=self.timestamps.get)
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]
            
            # Add new item
            self.cache[key] = value
            self.timestamps[key] = current_time
    
    def invalidate(self, pattern: str) -> int:
        """Invalidate all cache entries that match a pattern"""
        with self.lock:
            keys_to_delete = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.cache[key]
                del self.timestamps[key]
            return len(keys_to_delete)

class OllamaParser:
    """
    Integration class for OLLAMA models to parse and analyze OLX bike listings.
    """
    # Configure retry parameters
    MAX_RETRIES = 3
    RETRY_BACKOFF = [1, 3, 5]  # Seconds between retries
    REQUEST_TIMEOUT = 10  # Seconds
    
    def __init__(self, ollama_url="http://localhost:11434"):
        self.ollama_url = ollama_url
        self.llm_model = "deepseek-r1:14b"  # Primary LLM for text analysis
        self.fallback_llm_model = "deepseek-r1:14b"  # Fallback if primary unavailable
        
        # Initialize caching system
        self.analysis_cache = LRUCache(capacity=200, ttl=600)  # 10 minute TTL
        
        # Session for connection pooling
        self.session = requests.Session()
        
        # Check available models and set up
        self.available_models = self._get_available_models()
        self._setup_models()
        
        logger.info(f"OllamaParser initialized with URL: {ollama_url}")
        logger.info(f"LLM: {self.llm_model} (Available: {self.is_llm_available})")

    def _get_available_models(self) -> List[str]:
        """Get list of available models from Ollama"""
        try:
            response = self.session.get(
                f"{self.ollama_url}/api/tags",
                timeout=self.REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                return [model["name"] for model in response.json().get("models", [])]
            return []
        except Exception as e:
            logger.error(f"Failed to get available models: {str(e)}")
            return []

    def _setup_models(self) -> None:
        """Set up models based on availability"""
        # Check main LLM
        self.is_llm_available = self.llm_model in self.available_models
        if not self.is_llm_available and self.fallback_llm_model in self.available_models:
            logger.warning(f"Primary LLM {self.llm_model} not available, using fallback {self.fallback_llm_model}")
            self.llm_model = self.fallback_llm_model
            self.is_llm_available = True
        
        # Log warnings for missing models
        if not self.is_llm_available:
            logger.warning(f"LLM model {self.llm_model} is not available. Text analysis will be disabled.")

    def parse_bike_description(self, description: str) -> Dict[str, Any]:
        """
        Parse the bike description text to extract structured information.
        
        Args:
            description: Raw text description from the OLX listing
            
        Returns:
            A dictionary with structured information about the bike
        """
        if not self.is_llm_available:
            return {"error": "LLM model is unavailable"}

        # Check cache
        cache_key = f"bike_desc_{hash(description[:250])}"
        cached_result = self.analysis_cache.get(cache_key)
        if cached_result:
            logger.debug("Using cached bike description parsing result")
            return cached_result

        prompt = self._create_bike_parsing_prompt(description)
        
        # Try multiple times with backoff
        for attempt in range(self.MAX_RETRIES):
            try:
                data = {
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                }
                
                response = self.session.post(
                    f"{self.ollama_url}/api/generate", 
                    json=data,
                    timeout=self.REQUEST_TIMEOUT
                )
                
                if response.status_code == 200:
                    result = self._parse_ollama_response(response.json().get("response", "{}"))
                    if result:
                        # Cache successful result
                        self.analysis_cache.put(cache_key, result)
                        return result
                else:
                    logger.warning(f"API error (attempt {attempt+1}): {response.status_code}")
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt+1})")
            except Exception as e:
                logger.error(f"Error parsing bike description (attempt {attempt+1}): {str(e)}")
            
            # Sleep before retry (except on last attempt)
            if attempt < self.MAX_RETRIES - 1:
                time.sleep(self.RETRY_BACKOFF[attempt])
        
        return {"error": "Failed to parse bike description"}

    def _create_bike_parsing_prompt(self, description: str) -> str:
        """
        Create a structured prompt for parsing bike descriptions.
        """
        return f"""
        === BICYCLE LISTING PARSING REQUEST ===
        
        === TEXT DESCRIPTION ===
        {description}
        
        === TASK ===
        Extract the following information from the bicycle listing description above:
        
        1. Basic Information:
           - Brand and model
           - Year of production
           - Condition (new, used, etc.)
           - Color
           - Seller type (private/business)
        
        2. Technical Specifications:
           - Frame size and description
           - Frame material
           - Wheel size
           - Groupset/Drivetrain details
           - Brake type
           - Number of gears
           - Weight
           - Suspension details
        
        3. Additional Information:
           - Price and currency
           - Location
           - Date added
           - URL
           - Any accessories included
           - Any issues or damage mentioned
           - Any upgrades or modifications
        
        === REQUIRED JSON FORMAT ===
        {{
            "title": string,
            "price": {{
                "amount": number,
                "currency": string,
                "negotiable": boolean
            }},
            "location": string,
            "date_added": string,
            "url": string,
            "brand": string or null,
            "size": string or null,
            "year": number or null,
            "description": string or null,
            "condition": string or null,
            "color": string or null,
            "derailleur_type": string or null,
            "brake_type": string or null,
            "frame_material": string or null,
            "wheel_size": string or null,
            "seller_type": string or null,
            "bike_type": string or null,
            "frame_size_desc": string or null,
            "gears": string or null,
            "weight": string or null,
            "suspension": string or null,
            "parameters": {{
                "accessories": [string],
                "issues": [string],
                "upgrades": [string],
                "is_shipping_available": boolean,
                "confidence_score": number
            }}
        }}
        
        Format your entire response as valid JSON only. If you're unsure about any field, use null.
        For confidence_score in parameters, rate how confident you are in your overall extraction from 1-10.
        """

    def categorize_bike(self, title: str, description: str) -> Dict[str, Any]:
        """
        Categorize the bike based on title and description.
        
        Args:
            title: The title of the listing
            description: The description of the listing
            
        Returns:
            A dictionary with category information
        """
        if not self.is_llm_available:
            return {"error": "LLM model is unavailable"}

        # Check cache
        cache_key = f"bike_cat_{hash(title + description[:100])}"
        cached_result = self.analysis_cache.get(cache_key)
        if cached_result:
            logger.debug("Using cached bike categorization result")
            return cached_result

        prompt = f"""
        === BICYCLE CATEGORIZATION REQUEST ===
        
        === LISTING ===
        Title: {title}
        
        Description: {description}
        
        === TASK ===
        Categorize this bicycle listing into the appropriate category and subcategory:
        
        === REQUIRED JSON FORMAT ===
        {{
            "primary_category": string (e.g., "road", "gravel", "mtb", "city", "trekking", "kids", "electric", "other"),
            "subcategory": string (e.g., "race", "endurance", "hardtail", "full-suspension", etc.),
            "intended_use": string (e.g., "racing", "commuting", "touring", "all-road", etc.),
            "price_category": string (e.g., "budget", "mid-range", "high-end", "premium"),
            "confidence": number (1-10)
        }}
        
        Format your response as valid JSON only. If you're unsure about any field, provide your best guess.
        """
        
        # Try multiple times with backoff
        for attempt in range(self.MAX_RETRIES):
            try:
                data = {
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                }
                
                response = self.session.post(
                    f"{self.ollama_url}/api/generate", 
                    json=data,
                    timeout=self.REQUEST_TIMEOUT
                )
                
                if response.status_code == 200:
                    result = self._parse_ollama_response(response.json().get("response", "{}"))
                    if result:
                        # Cache successful result
                        self.analysis_cache.put(cache_key, result)
                        return result
                else:
                    logger.warning(f"API error (attempt {attempt+1}): {response.status_code}")
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt+1})")
            except Exception as e:
                logger.error(f"Error categorizing bike (attempt {attempt+1}): {str(e)}")
            
            # Sleep before retry (except on last attempt)
            if attempt < self.MAX_RETRIES - 1:
                time.sleep(self.RETRY_BACKOFF[attempt])
        
        return {"error": "Failed to categorize bike"}

    def identify_bike_value(self, bike_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a bike to identify its market value and key selling points.
        
        Args:
            bike_data: Structured bike data
            
        Returns:
            Value analysis information
        """
        if not self.is_llm_available:
            return {"error": "LLM model is unavailable"}

        # Check cache
        bike_data_flat = json.dumps(bike_data)
        cache_key = f"bike_value_{hash(bike_data_flat)}"
        cached_result = self.analysis_cache.get(cache_key)
        if cached_result:
            logger.debug("Using cached bike value analysis result")
            return cached_result

        prompt = f"""
        === BICYCLE VALUE ANALYSIS REQUEST ===
        
        === BIKE DATA ===
        {bike_data_flat}
        
        === TASK ===
        Analyze this bicycle and provide:
        1. Estimated market value (fair price range)
        2. Key selling points
        3. Any concerns or red flags
        4. Whether the listed price (if available) is fair, high, or low
        
        === REQUIRED JSON FORMAT ===
        {{
            "value_analysis": {{
                "estimated_value_range": {{
                    "low": number,
                    "high": number,
                    "currency": string
                }},
                "value_assessment": string (e.g., "fair", "overpriced", "underpriced", "unknown"),
                "price_difference_percent": number or null (compared to estimated fair value)
            }},
            "selling_points": [list of strings],
            "concerns": [list of strings],
            "overall_recommendation": string,
            "confidence": number (1-10)
        }}
        
        Format your response as valid JSON only.
        """
        
        # Try multiple times with backoff
        for attempt in range(self.MAX_RETRIES):
            try:
                data = {
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                }
                
                response = self.session.post(
                    f"{self.ollama_url}/api/generate", 
                    json=data,
                    timeout=self.REQUEST_TIMEOUT
                )
                
                if response.status_code == 200:
                    result = self._parse_ollama_response(response.json().get("response", "{}"))
                    if result:
                        # Cache successful result
                        self.analysis_cache.put(cache_key, result)
                        return result
                else:
                    logger.warning(f"API error (attempt {attempt+1}): {response.status_code}")
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt+1})")
            except Exception as e:
                logger.error(f"Error analyzing bike value (attempt {attempt+1}): {str(e)}")
            
            # Sleep before retry (except on last attempt)
            if attempt < self.MAX_RETRIES - 1:
                time.sleep(self.RETRY_BACKOFF[attempt])
        
        return {"error": "Failed to analyze bike value"}

    def _parse_ollama_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse Ollama response text into a JSON object"""
        try:
            # First try direct JSON parsing
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from text
            json_pattern = r'```json\s*(.*?)\s*```|(\{.*\})'
            json_match = re.search(json_pattern, response_text, re.DOTALL)
            
            if json_match:
                # Get the match from whichever group matched
                json_str = json_match.group(1) if json_match.group(1) else json_match.group(2)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse extracted JSON: {json_str[:100]}...")
            
            logger.error(f"Could not parse response as JSON: {response_text[:100]}...")
            return None 