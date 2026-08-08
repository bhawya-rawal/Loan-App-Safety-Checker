import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
from google_play_scraper import search, app as play_app

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join("data", "raw", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_path(app_id: str) -> str:
    return os.path.join(CACHE_DIR, f"playstore_{app_id}.json")

def load_cached_app(app_id: str, max_age_days: int = 1) -> Optional[Dict[str, Any]]:
    path = get_cache_path(app_id)
    if os.path.exists(path):
        # Check cache age
        mtime = os.path.getmtime(path)
        age_seconds = time.time() - mtime
        if age_seconds < max_age_days * 86400:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read cache for {app_id}: {e}")
    return None

def save_to_cache(app_id: str, data: Dict[str, Any]) -> None:
    path = get_cache_path(app_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to write cache for {app_id}: {e}")

def discover_loan_apps(queries: List[str] = None, target_count: int = 30, country: str = "in") -> List[str]:
    """
    Search for loan-related apps and return a list of unique package IDs.
    """
    if not queries:
        queries = ["loan", "instant loan", "personal loan", "cash loan", "quick loan", "fast credit"]
    
    unique_ids = set()
    logger.info(f"Starting discovery using queries: {queries}")
    
    for query in queries:
        logger.info(f"Searching for query: '{query}'")
        try:
            results = search(query, lang="en", country=country, n_hits=30)
            for res in results:
                app_id = res.get("appId")
                if app_id:
                    unique_ids.add(app_id)
            # Sleep to be polite
            time.sleep(1.0)
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            
    app_ids = list(unique_ids)
    logger.info(f"Discovered {len(app_ids)} unique apps. Truncating to target of {target_count}.")
    return app_ids[:target_count]

def fetch_app_metadata(app_id: str, country: str = "in", use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """
    Fetch full app metadata with error handling, retries, and caching.
    """
    if use_cache:
        cached = load_cached_app(app_id)
        if cached:
            logger.info(f"Loaded {app_id} details from cache.")
            return cached
            
    retries = 3
    backoff = 2.0
    for attempt in range(retries):
        try:
            logger.info(f"Fetching metadata for {app_id} (Attempt {attempt+1}/{retries})...")
            # google-play-scraper expects app_id, lang, country
            details = play_app(app_id, lang="en", country=country)
            
            # Store in cache
            save_to_cache(app_id, details)
            return details
        except Exception as e:
            logger.error(f"Error fetching metadata for {app_id}: {e}")
            if attempt < retries - 1:
                sleep_time = backoff ** attempt
                logger.info(f"Sleeping for {sleep_time}s before retrying...")
                time.sleep(sleep_time)
            else:
                logger.error(f"Max retries reached for {app_id}. Returning None.")
                
    return None
