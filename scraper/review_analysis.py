import re
import logging
from collections import Counter
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Keyword sets for theme detection
THEMES_KEYWORDS = {
    # Negative themes
    "harassment": [
        "harass", "threat", "abuse", "torture", "scare", "insult", "shame", 
        "blackmail", "mental", "tortured", "threaten", "vulgar", "dirty word"
    ],
    "contacting_contacts": [
        "contact", "relative", "friend", "family", "message my contact", 
        "call my contact", "contact list", "reference call", "call relative"
    ],
    "hidden_fees": [
        "hidden fee", "processing fee", "gst fee", "deduct", "extra charge", 
        "high interest", "brokerage fee", "service fee", "charge", "interest rate", 
        "high charge", "cut money"
    ],
    "repayment_problems": [
        "repay", "repayment", "pay back", "auto debit", "double payment", 
        "due date", "tenure", "7 days", "seven days", "short tenure", "duration"
    ],
    "loan_not_disbursed": [
        "not disbursed", "not receive", "money not credited", "bank account", 
        "did not get", "pending", "status success but no money"
    ],
    "poor_support": [
        "customer support", "support", "no response", "helpline", "email", 
        "care number", "useless support", "no reply", "not working support"
    ],
    "fraud_scam": [
        "scam", "fraud", "fake app", "cheat", "thief", "steal", "rob", 
        "crook", "dangerous", "illegal", "cheat app"
    ],
    
    # Positive themes
    "successful_loan": [
        "disbursed", "credited", "got loan", "successful", "received loan", 
        "easy loan", "money received"
    ],
    "easy_application": [
        "easy", "fast", "quick", "simple", "smooth", "within minutes", 
        "instant", "fast process"
    ],
    "good_support": [
        "helpful", "good support", "fast reply", "nice customer service", 
        "friendly", "quick support"
    ],
    "transparent": [
        "transparent", "clear fees", "no hidden", "honest"
    ]
}

GENERIC_PRAISE = {
    "nice app", "good app", "very nice", "best loan app", "superb", 
    "awesome", "good", "nice", "excellent", "best app", "super", 
    "very good", "great app", "great", "ok", "cool"
}

def clean_text(text: str) -> str:
    if not text:
        return ""
    # Lowercase and remove special characters/excess whitespace
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())

def analyze_review_themes(reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detect positive and negative themes in reviews.
    """
    themes_stats = {}
    
    # Initialize theme structure
    for theme in THEMES_KEYWORDS.keys():
        themes_stats[theme] = {
            "count": 0,
            "percentage": 0.0,
            "examples": []
        }
        
    total_reviews = len(reviews)
    if total_reviews == 0:
        return themes_stats
        
    for theme, keywords in THEMES_KEYWORDS.items():
        matching_reviews = []
        for r in reviews:
            content = r.get("content", "")
            if not content:
                continue
                
            cleaned = clean_text(content)
            # Check if any keyword matches
            if any(kw in cleaned for kw in keywords):
                matching_reviews.append(r)
                
        themes_stats[theme]["count"] = len(matching_reviews)
        themes_stats[theme]["percentage"] = round((len(matching_reviews) / total_reviews) * 100, 2)
        
        # Save top 3 reviews as representative examples
        # Prioritize reviews with higher thumbsUpCount if available
        sorted_examples = sorted(
            matching_reviews, 
            key=lambda x: x.get("thumbsUpCount", 0), 
            reverse=True
        )
        themes_stats[theme]["examples"] = [
            ex.get("content") for ex in sorted_examples[:3]
        ]
        
    return themes_stats

def analyze_sentiment(reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze review ratings and basic text sentiment.
    """
    total = len(reviews)
    if total == 0:
        return {
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "average_rating": 0.0
        }
        
    positive_count = 0
    negative_count = 0
    neutral_count = 0
    ratings_sum = 0
    
    for r in reviews:
        score = r.get("score", 3)
        ratings_sum += score
        if score >= 4:
            positive_count += 1
        elif score <= 2:
            negative_count += 1
        else:
            neutral_count += 1
            
    return {
        "positive": positive_count,
        "negative": negative_count,
        "neutral": neutral_count,
        "average_rating": round(ratings_sum / total, 2)
    }

def detect_review_manipulation(reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detect review manipulation patterns:
    1. Duplicated review text
    2. Large concentration of short generic 5-star reviews
    3. Stars mismatch (5-star rating containing strong negative scam keywords)
    """
    reasons = []
    manipulation_score = 0
    
    total = len(reviews)
    if total < 5:
        return {
            "detected": False,
            "score": 0,
            "reasons": ["Insufficient review count for manipulation analysis"]
        }
        
    # 1. Duplicated Review Text
    cleaned_texts = []
    for r in reviews:
        content = r.get("content", "")
        cleaned = clean_text(content)
        # Only check duplicate logic for reviews that have actual words (length > 10)
        if len(cleaned) > 10:
            cleaned_texts.append(cleaned)
            
    if cleaned_texts:
        counts = Counter(cleaned_texts)
        duplicates_count = sum(count for text, count in counts.items() if count > 1)
        duplicate_percentage = (duplicates_count / len(cleaned_texts)) * 100
        
        if duplicate_percentage > 15:
            reasons.append(f"High percentage of duplicate review texts ({round(duplicate_percentage, 1)}%)")
            manipulation_score += min(35, int(duplicate_percentage * 1.5))
            
    # 2. Generic 5-star reviews
    fives_count = sum(1 for r in reviews if r.get("score") == 5)
    generic_fives = 0
    for r in reviews:
        if r.get("score") == 5:
            cleaned = clean_text(r.get("content", ""))
            if cleaned in GENERIC_PRAISE or len(cleaned) < 12:
                generic_fives += 1
                
    if fives_count > 0:
        generic_fives_percentage = (generic_fives / fives_count) * 100
        total_fives_percentage = (fives_count / total) * 100
        
        # If total reviews has very high 5-star concentration and many are short/generic
        if total_fives_percentage > 65 and generic_fives_percentage > 50:
            reasons.append(f"Suspicious cluster of generic 5-star reviews ({round(generic_fives_percentage, 1)}% of 5-star reviews are short/repetitive)")
            manipulation_score += 30
            
    # 3. Rating Mismatch (5-star with negative keywords)
    mismatch_count = 0
    scam_keywords = ["scam", "fraud", "cheat", "thief", "steal", "fake", "harass", "threat"]
    for r in reviews:
        if r.get("score") == 5:
            cleaned = clean_text(r.get("content", ""))
            if any(kw in cleaned for kw in scam_keywords):
                mismatch_count += 1
                
    if mismatch_count > 0:
        mismatch_percentage = (mismatch_count / fives_count) * 100 if fives_count > 0 else 0
        if mismatch_percentage > 5:
            reasons.append(f"Rating mismatches detected: {mismatch_count} users gave 5 stars but reported fraud/scam in review text.")
            manipulation_score += min(20, int(mismatch_percentage * 2))
            
    # Normalize final manipulation score to 0-100
    manipulation_score = min(100, manipulation_score)
    detected = manipulation_score >= 35
    
    if not reasons:
        reasons.append("No significant review manipulation patterns detected.")
        
    return {
        "detected": detected,
        "score": manipulation_score,
        "reasons": reasons
    }

def analyze_app_reviews(reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Run full review analysis pipeline.
    """
    return {
        "themes": analyze_review_themes(reviews),
        "sentiment": analyze_sentiment(reviews),
        "manipulation": detect_review_manipulation(reviews)
    }
