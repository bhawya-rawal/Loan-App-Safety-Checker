import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
from google_play_scraper import reviews as play_reviews, Sort

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join("data", "raw", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_path(app_id: str) -> str:
    return os.path.join(CACHE_DIR, f"reviews_{app_id}.json")

def load_cached_reviews(app_id: str, max_age_days: int = 1) -> Optional[List[Dict[str, Any]]]:
    path = get_cache_path(app_id)
    if os.path.exists(path):
        mtime = os.path.getmtime(path)
        age_seconds = time.time() - mtime
        if age_seconds < max_age_days * 86400:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read reviews cache for {app_id}: {e}")
    return None

def save_to_cache(app_id: str, data: List[Dict[str, Any]]) -> None:
    path = get_cache_path(app_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to write reviews cache for {app_id}: {e}")

def fetch_app_reviews(app_id: str, target_count: int = 100, country: str = "in", use_cache: bool = True) -> List[Dict[str, Any]]:
    """
    Fetch up to target_count reviews for a given app. Uses local caching and rate limiting.
    """
    if use_cache:
        cached = load_cached_reviews(app_id)
        if cached is not None:
            logger.info(f"Loaded {len(cached)} reviews for {app_id} from cache.")
            return cached

    logger.info(f"Fetching reviews for {app_id} (target: {target_count})...")
    all_reviews = []
    continuation_token = None
    
    # We fetch in chunks of 100 (or max 200)
    chunk_size = min(100, target_count)
    retries = 3
    backoff = 2.0
    
    for attempt in range(retries):
        try:
            if continuation_token:
                result, continuation_token = play_reviews(
                    app_id,
                    continuation_token=continuation_token
                )
            else:
                result, continuation_token = play_reviews(
                    app_id,
                    lang="en",
                    country=country,
                    sort=Sort.NEWEST,
                    count=chunk_size
                )
            
            all_reviews.extend(result)
            
            # If we got enough reviews or no more reviews are available, stop
            if len(all_reviews) >= target_count or not continuation_token:
                break
                
            time.sleep(1.0) # Polite delay between pages
            
        except Exception as e:
            logger.error(f"Error fetching reviews for {app_id} on attempt {attempt+1}: {e}")
            if attempt < retries - 1:
                time.sleep(backoff ** attempt)
            else:
                logger.error(f"Max retries reached when fetching reviews for {app_id}.")
                break
                
    # Trim to exact target count
    final_reviews = all_reviews[:target_count]
    save_to_cache(app_id, final_reviews)
    logger.info(f"Successfully collected {len(final_reviews)} reviews for {app_id}.")
    return final_reviews
