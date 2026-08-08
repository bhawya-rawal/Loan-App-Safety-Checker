import os
import json
import time
import hashlib
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from typing import List, Dict, Any, Optional
from duckduckgo_search import DDGS
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join("data", "raw", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def get_query_hash(query: str) -> str:
    return hashlib.md5(query.encode("utf-8")).hexdigest()

def get_cache_path(query: str) -> str:
    h = get_query_hash(query)
    return os.path.join(CACHE_DIR, f"search_{h}.json")

def load_cached_search(query: str, max_age_days: int = 7) -> Optional[List[Dict[str, Any]]]:
    path = get_cache_path(query)
    if os.path.exists(path):
        mtime = os.path.getmtime(path)
        age_seconds = time.time() - mtime
        if age_seconds < max_age_days * 86400:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read search cache for query '{query}': {e}")
    return None

def save_to_cache(query: str, data: List[Dict[str, Any]]) -> None:
    path = get_cache_path(query)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to write search cache for query '{query}': {e}")

def classify_source_type(url: str) -> str:
    """
    Classify source type based on domain.
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    if "reddit.com" in domain or "quora.com" in domain:
        return "forum"
    elif any(kw in domain for kw in ["consumercomplaints", "complaintboard", "complaint", "pgportal", "consumerhelpline"]):
        return "consumer_complaint"
    elif any(kw in domain for kw in ["gov", "rbi.org.in", "sec.gov", "ftc.gov"]):
        return "regulatory"
    elif any(kw in domain for kw in ["ndtv.com", "timesofindia", "moneycontrol", "reuters", "bloomberg", "techcrunch", "hindustantimes", "livemint", "economictimes", "indianexpress"]):
        return "news"
    else:
        return "web"

def calculate_relevance(query: str, title: str, snippet: str) -> str:
    """
    Calculate simple relevance (high, medium, low) based on term matching.
    """
    text = (title + " " + snippet).lower()
    keywords = ["scam", "fraud", "harass", "threat", "complaint", "rbi", "fake", "charge"]
    
    match_count = sum(1 for kw in keywords if kw in text)
    if match_count >= 3:
        return "high"
    elif match_count >= 1:
        return "medium"
    return "low"

def execute_serper_search(query: str, max_results: int, api_key: str) -> List[Dict[str, Any]]:
    logger.info(f"Querying Google Search via Serper API for: '{query}'")
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query, "num": max_results})
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    results = []
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            organic_results = data.get("organic", [])
            
            for item in organic_results[:max_results]:
                link = item.get("link")
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                
                if not link:
                    continue
                    
                source_type = classify_source_type(link)
                relevance = calculate_relevance(query, title, snippet)
                published_date = item.get("date")
                
                results.append({
                    "url": link,
                    "title": title,
                    "source_type": source_type,
                    "published_date": published_date,
                    "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "summary": snippet,
                    "relevance": relevance,
                    "confidence": "high" if source_type in ["regulatory", "news"] else ("medium" if source_type == "consumer_complaint" else "low")
                })
        else:
            logger.error(f"Serper API failed with status {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Error calling Serper API: {e}")
        
    return results

def execute_search(query: str, max_results: int = 5, use_cache: bool = True) -> List[Dict[str, Any]]:
    """
    Execute search query with caching and rate limit handling.
    """
    if use_cache:
        cached = load_cached_search(query)
        if cached is not None:
            logger.info(f"Loaded search results for query '{query}' from cache.")
            return cached

    # Check for Serper API Key integration
    serper_key = os.environ.get("SERPER_API_KEY")
    if serper_key and serper_key.strip() != "":
        results = execute_serper_search(query, max_results, serper_key)
        if results:
            save_to_cache(query, results)
            return results

    logger.info(f"Searching web for: '{query}'...")
    results = []
    
    try:
        try:
            # DDGS context manager
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))
                
                for item in raw_results:
                    url = item.get("href")
                    title = item.get("title", "")
                    snippet = item.get("body", "")
                    
                    if not url:
                        continue
                        
                    source_type = classify_source_type(url)
                    relevance = calculate_relevance(query, title, snippet)
                    
                    results.append({
                        "url": url,
                        "title": title,
                        "source_type": source_type,
                        "published_date": None, # DuckDuckGo text search doesn't reliably return date in simple output
                        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "summary": snippet,
                        "relevance": relevance,
                        "confidence": "high" if source_type in ["regulatory", "news"] else ("medium" if source_type == "consumer_complaint" else "low")
                    })
            time.sleep(2.0)
        except Exception as lib_error:
            logger.warning(f"duckduckgo_search API failed for '{query}' ({lib_error}). Trying HTML scraping fallback...")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            }
            url = f"https://html.duckduckgo.com/html/?q={query}"
            
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code in [202, 403]:
                logger.warning(f"HTML fallback rate-limited ({resp.status_code}). Cooling down for 6 seconds...")
                time.sleep(6.0)
                resp = requests.get(url, headers=headers, timeout=10)
                
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                title_tags = soup.find_all('a', class_='result__a')
                snippet_tags = soup.find_all('a', class_='result__snippet')
                
                for a_tag, snip_tag in zip(title_tags[:max_results], snippet_tags[:max_results]):
                    href = a_tag.get('href', '')
                    title = a_tag.text.strip()
                    snippet = snip_tag.text.strip()
                    
                    # Unnest URL from /l/?uddg=...
                    if href.startswith("//"):
                        href = "https:" + href
                    if "/l/?uddg=" in href:
                        parsed_href = urlparse(href)
                        queries = parse_qs(parsed_href.query)
                        real_url = queries.get("uddg", [href])[0]
                    else:
                        real_url = href
                        
                    source_type = classify_source_type(real_url)
                    relevance = calculate_relevance(query, title, snippet)
                    
                    results.append({
                        "url": real_url,
                        "title": title,
                        "source_type": source_type,
                        "published_date": None,
                        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "summary": snippet,
                        "relevance": relevance,
                        "confidence": "high" if source_type in ["regulatory", "news"] else ("medium" if source_type == "consumer_complaint" else "low")
                    })
                # Sleep to prevent HTML-level block
                time.sleep(3.0)
            else:
                logger.error(f"HTML fallback failed with status {resp.status_code}")
                raise lib_error
                
        if results:
            save_to_cache(query, results)
            
    except Exception as e:
        logger.error(f"Search failed for query '{query}': {e}")
        # If blocked or network error, return empty list (or load expired cache if available)
        expired_cache = load_cached_search(query, max_age_days=30)
        if expired_cache:
            logger.info(f"Using expired cache as fallback for query '{query}'.")
            return expired_cache
            
    return results

def perform_app_web_research(app_name: str, developer_name: str) -> List[Dict[str, Any]]:
    """
    Perform web research for a single app.
    Runs 2 highly focused search queries to protect limits and retrieve relevant articles.
    """
    queries = [
        f'"{app_name}" loan scam',
        f'"{app_name}" loan harassment'
    ]
    
    all_results = []
    seen_urls = set()
    
    for query in queries:
        query_results = execute_search(query, max_results=4)
        for r in query_results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                all_results.append(r)
                
    return all_results
