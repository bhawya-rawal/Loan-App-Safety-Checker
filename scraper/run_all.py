import os
import json
import time
import logging
from typing import List, Dict, Any

from scraper.playstore import discover_loan_apps, fetch_app_metadata
from scraper.reviews import fetch_app_reviews
from scraper.permissions import fetch_app_permissions
from scraper.web_research import perform_app_web_research
from scraper.review_analysis import analyze_app_reviews
from scraper.risk_scoring import evaluate_signals, calculate_risk_score_and_verdict

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "apps.json")
os.makedirs(DATA_DIR, exist_ok=True)

# List of highly recognizable real loan app packages to supplement search if needed
FALLBACK_PACKAGE_IDS = [
    # India popular instant loan apps
    "com.kreditbee.android",
    "com.whizdm.moneyview.android.app",
    "com.naviapp",
    "com.smartcoin",
    "com.slashtechnology.cashe",
    "com.mpokket.mymoney",
    "com.pocketly",
    "com.ideact.ringPay",
    "co.rupeek.customer",
    "com.gopaisa.cashji",
    "com.zestmoney.android",
    "com.lightning.quicklona",
    # US / Global instant credit/cash advance apps
    "com.dave",
    "com.hellobrigit",
    "com.albert",
    "com.activehours",
    "com.floatme",
    "com.cleo.cleoapp",
    "com.klover.android",
    "com.empower.finance",
    "com.chime",
    "com.sofi.mobile"
]

def run_pipeline(target_count: int = 25, country: str = "in", use_cache: bool = True) -> None:
    logger.info("Initializing Loan App Safety Analyzer pipeline...")
    
    # 1. Discover Apps
    discovered_packages = discover_loan_apps(target_count=target_count, country=country)
    
    # Merge with fallback package IDs to ensure we get a solid list of 20-30 apps
    all_packages = list(discovered_packages)
    for pkg in FALLBACK_PACKAGE_IDS:
        if len(all_packages) >= target_count:
            break
        if pkg not in all_packages:
            all_packages.append(pkg)
            
    logger.info(f"Target count: {target_count}. Working with {len(all_packages)} package IDs.")
    
    analyzed_apps = []
    
    for idx, package_id in enumerate(all_packages):
        logger.info(f"[{idx+1}/{len(all_packages)}] Processing app: {package_id}")
        
        try:
            # 2. Collect Metadata
            metadata = fetch_app_metadata(package_id, country=country, use_cache=use_cache)
            if not metadata:
                logger.warning(f"Could not retrieve metadata for {package_id}, skipping.")
                continue
                
            app_name = metadata.get("title")
            developer_name = metadata.get("developer", "")
            
            # 3. Collect Reviews (target 100)
            reviews = fetch_app_reviews(package_id, target_count=100, country=country, use_cache=use_cache)
            
            # 4. Collect Permissions
            perms = fetch_app_permissions(package_id, use_cache=use_cache)
            
            # 5. Perform Web Research
            web_sources = perform_app_web_research(app_name, developer_name)
            
            # 6. Analyze Reviews
            reviews_analysis = analyze_app_reviews(reviews)
            
            # 7. Evaluate Evidence Signals
            signals = evaluate_signals(metadata, perms, reviews_analysis, web_sources)
            
            # 8. Calculate Risk Score and Verdict
            risk_details = calculate_risk_score_and_verdict(metadata, perms, reviews_analysis, web_sources, signals)
            
            # Compile app report
            app_report = {
                "name": app_name,
                "package": package_id,
                "developer": developer_name,
                "developer_email": metadata.get("developerEmail") or "unknown",
                "developer_website": metadata.get("developerWebsite") or "unknown",
                "rating": metadata.get("score"),
                "reviews_count": metadata.get("reviews"),
                "installs": metadata.get("installs"),
                "play_store_url": metadata.get("url"),
                "privacy_policy_url": metadata.get("privacyPolicy"),
                "last_updated": metadata.get("updated"),
                "icon": metadata.get("icon"),
                "description": metadata.get("description"),
                
                "risk": {
                    "score": risk_details["score"],
                    "level": risk_details["level"],
                    "reasons": risk_details["reasons"],
                    "strongest_evidence": risk_details["strongest_evidence"],
                    "important_uncertainties": risk_details["important_uncertainties"]
                },
                
                "signals": signals,
                "reviews_analysis": {
                    "themes": reviews_analysis["themes"],
                    "sentiment": reviews_analysis["sentiment"],
                    "manipulation": reviews_analysis["manipulation"]
                },
                "permissions": perms,
                "web_sources": web_sources,
                "reviews": reviews # store for detail view inspection
            }
            
            analyzed_apps.append(app_report)
            logger.info(f"Finished analyzing {app_name}. Risk Level: {risk_details['level']} ({risk_details['score']}/100)")
            
            # Brief delay between apps to respect APIs
            time.sleep(1.0)
            
        except Exception as e:
            logger.error(f"Error processing package {package_id}: {e}", exc_info=True)
            
    # Write output to apps.json in both data/ and frontend/src/
    logger.info(f"Writing final database to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(analyzed_apps, f, indent=2, default=str)
        
    frontend_db_file = os.path.join("frontend", "src", "apps.json")
    try:
        logger.info(f"Writing frontend copy of database to {frontend_db_file}...")
        os.makedirs(os.path.dirname(frontend_db_file), exist_ok=True)
        with open(frontend_db_file, "w", encoding="utf-8") as f:
            json.dump(analyzed_apps, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to write frontend database copy: {e}")
        
    # Print pipeline summary
    total_apps = len(analyzed_apps)
    if total_apps > 0:
        avg_score = sum(a["risk"]["score"] for a in analyzed_apps) / total_apps
        levels = [a["risk"]["level"] for a in analyzed_apps]
        logger.info("=== Pipeline Execution Summary ===")
        logger.info(f"Total Apps Analyzed: {total_apps}")
        logger.info(f"Average Risk Score: {avg_score:.1f}")
        logger.info(f"Risk Verdicts: HIGH RISK: {levels.count('HIGH_RISK')}, CAUTION: {levels.count('CAUTION')}, LOWER RISK: {levels.count('LOWER_RISK')}, INSUFFICIENT EVIDENCE: {levels.count('INSUFFICIENT_EVIDENCE')}")
    else:
        logger.error("Pipeline finished but no apps were successfully analyzed.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run the Loan App Safety Analyzer collection and scoring pipeline.")
    parser.add_argument("--count", type=int, default=25, help="Number of apps to target (default: 25)")
    parser.add_argument("--country", type=str, default="in", help="Country store code (default: in)")
    parser.add_argument("--force", action="store_true", help="Ignore cache and force fetch")
    args = parser.parse_args()
    
    run_pipeline(target_count=args.count, country=args.country, use_cache=not args.force)
