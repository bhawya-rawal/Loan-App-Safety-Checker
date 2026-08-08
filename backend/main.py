import os
import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Loan App Safety Analyzer API",
    description="Backend API providing risk assessments and reputation statistics for loan apps.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = os.path.join("data", "apps.json")

def load_apps_data() -> List[Dict[str, Any]]:
    if not os.path.exists(DATA_FILE):
        logger.warning(f"Database file {DATA_FILE} not found. Returning empty list.")
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load database file {DATA_FILE}: {e}")
        return []

@app.get("/api/apps")
def get_apps(
    search: Optional[str] = Query(None, description="Search term for app name, developer, or package ID"),
    risk: Optional[str] = Query(None, description="Filter by risk level (e.g., HIGH_RISK, CAUTION, LOWER_RISK, INSUFFICIENT_EVIDENCE)"),
    min_rating: Optional[float] = Query(None, description="Minimum rating filter"),
    min_score: Optional[int] = Query(None, description="Minimum risk score"),
    max_score: Optional[int] = Query(None, description="Maximum risk score"),
    sort: Optional[str] = Query("risk_desc", description="Sort criteria: risk_desc, risk_asc, rating_desc, rating_asc, name_asc"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
):
    apps = load_apps_data()
    
    # Apply search filter
    if search:
        search_lower = search.lower()
        apps = [
            a for a in apps
            if search_lower in a.get("name", "").lower()
            or search_lower in a.get("developer", "").lower()
            or search_lower in a.get("package", "").lower()
        ]
        
    # Apply risk level filter
    if risk:
        risk_upper = risk.upper()
        apps = [a for a in apps if a.get("risk", {}).get("level") == risk_upper]
        
    # Apply rating filter
    if min_rating is not None:
        apps = [a for a in apps if a.get("rating") is not None and a.get("rating") >= min_rating]
        
    # Apply risk score filters
    if min_score is not None:
        apps = [a for a in apps if a.get("risk", {}).get("score", 0) >= min_score]
    if max_score is not None:
        apps = [a for a in apps if a.get("risk", {}).get("score", 0) <= max_score]
        
    # Apply sorting
    if sort == "risk_desc":
        apps.sort(key=lambda x: x.get("risk", {}).get("score", 0), reverse=True)
    elif sort == "risk_asc":
        apps.sort(key=lambda x: x.get("risk", {}).get("score", 0))
    elif sort == "rating_desc":
        apps.sort(key=lambda x: x.get("rating") or 0.0, reverse=True)
    elif sort == "rating_asc":
        apps.sort(key=lambda x: x.get("rating") or 5.0)
    elif sort == "name_asc":
        apps.sort(key=lambda x: x.get("name", "").lower())
        
    # Pagination
    total = len(apps)
    start = (page - 1) * limit
    end = start + limit
    paginated_apps = apps[start:end]
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "data": paginated_apps
    }

@app.get("/api/apps/{package}")
def get_app_detail(package: str):
    apps = load_apps_data()
    for app_item in apps:
        if app_item.get("package") == package:
            return app_item
            
    raise HTTPException(status_code=404, detail=f"App with package '{package}' not found.")

@app.get("/api/stats")
def get_stats():
    apps = load_apps_data()
    total_apps = len(apps)
    
    if total_apps == 0:
        return {
            "total_apps": 0,
            "level_counts": {
                "HIGH_RISK": 0,
                "CAUTION": 0,
                "LOWER_RISK": 0,
                "INSUFFICIENT_EVIDENCE": 0
            },
            "average_risk_score": 0.0
        }
        
    level_counts = {
        "HIGH_RISK": sum(1 for a in apps if a.get("risk", {}).get("level") == "HIGH_RISK"),
        "CAUTION": sum(1 for a in apps if a.get("risk", {}).get("level") == "CAUTION"),
        "LOWER_RISK": sum(1 for a in apps if a.get("risk", {}).get("level") == "LOWER_RISK"),
        "INSUFFICIENT_EVIDENCE": sum(1 for a in apps if a.get("risk", {}).get("level") == "INSUFFICIENT_EVIDENCE")
    }
    
    valid_scores = [a.get("risk", {}).get("score", 0) for a in apps if a.get("risk", {}).get("level") != "INSUFFICIENT_EVIDENCE"]
    avg_score = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else 0.0
    
    return {
        "total_apps": total_apps,
        "level_counts": level_counts,
        "average_risk_score": avg_score
    }
