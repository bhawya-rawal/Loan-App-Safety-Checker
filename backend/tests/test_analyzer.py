import pytest
from fastapi.testclient import TestClient
from backend.main import app

# Import scraper modules to test logic directly
from scraper.permissions import analyze_permissions
from scraper.review_analysis import analyze_review_themes, analyze_sentiment, detect_review_manipulation
from scraper.risk_scoring import calculate_risk_score_and_verdict, evaluate_signals

@pytest.fixture
def client():
    return TestClient(app)

def test_permissions_classification():
    # Input mockup
    raw_perms = {
        "Personal": [
            "android.permission.READ_CONTACTS",
            "android.permission.WRITE_CONTACTS"
        ],
        "SMS": [
            "android.permission.READ_SMS"
        ]
    }
    
    result = analyze_permissions(raw_perms)
    
    assert "declared_permissions" in result
    assert "sensitive_permissions" in result
    assert "Contacts" in result["sensitive_permissions"]
    assert "SMS" in result["sensitive_permissions"]
    assert len(result["sensitive_permissions"]["Contacts"]) == 2

def test_review_theme_analysis():
    reviews = [
        {"content": "This app is a scam they harass me daily", "score": 1},
        {"content": "Easy application process and fast transfer", "score": 5},
        {"content": "They called my contacts list and threatened me", "score": 1},
        {"content": "High interest processing fee was not disclosed", "score": 2}
    ]
    
    themes = analyze_review_themes(reviews)
    
    assert themes["harassment"]["count"] == 2
    assert themes["easy_application"]["count"] == 1
    assert themes["hidden_fees"]["count"] == 1
    assert themes["contacting_contacts"]["count"] == 1

def test_review_manipulation_detection():
    # Duplicate review text check
    reviews_dup = [
        {"content": "Awesome application very helpful loan", "score": 5},
        {"content": "Awesome application very helpful loan", "score": 5},
        {"content": "Awesome application very helpful loan", "score": 5},
        {"content": "Awesome application very helpful loan", "score": 5},
        {"content": "normal review text that is unique and different", "score": 1}
    ]
    
    result = detect_review_manipulation(reviews_dup)
    assert result["detected"] is True
    assert any("duplicate" in r.lower() for r in result["reasons"])

def test_risk_scoring_and_verdict():
    metadata = {
        "title": "EasyCash Loan",
        "developer": "EasyCash Inc",
        "developerEmail": "scammer@gmail.com",
        "developerWebsite": "http://scam-site.example.com",
        "privacyPolicy": "",
        "score": 4.5
    }
    
    perms = {
        "sensitive_permissions": {
            "Contacts": ["android.permission.READ_CONTACTS"],
            "SMS": ["android.permission.READ_SMS"]
        }
    }
    
    reviews_analysis = {
        "themes": {
            "harassment": {"count": 12, "percentage": 12.0},
            "contacting_contacts": {"count": 8, "percentage": 8.0},
            "hidden_fees": {"count": 4, "percentage": 4.0},
            "fraud_scam": {"count": 10, "percentage": 10.0},
            "repayment_problems": {"count": 0, "percentage": 0.0}
        },
        "sentiment": {"positive": 50, "negative": 50, "neutral": 0, "average_rating": 3.2},
        "manipulation": {"detected": False, "reasons": []}
    }
    
    web_research = [
        {"source_type": "news", "relevance": "high", "summary": "Users reporting harassment from EasyCash loan app."}
    ]
    
    signals = evaluate_signals(metadata, perms, reviews_analysis, web_research)
    
    # Verify signals generated
    signal_names = [s["signal"] for s in signals]
    assert "harassment_threats" in signal_names
    assert "contacts_abuse" in signal_names
    assert "unclear_developer_identity" in signal_names
    
    risk_result = calculate_risk_score_and_verdict(metadata, perms, reviews_analysis, web_research, signals)
    
    assert risk_result["score"] >= 60
    assert risk_result["level"] == "HIGH_RISK"
    assert len(risk_result["reasons"]) > 0

def test_api_endpoints(client):
    # Verify endpoints load successfully (even with empty data file)
    response = client.get("/api/apps")
    assert response.status_code == 200
    assert "data" in response.json()
    assert "total" in response.json()
    
    response_stats = client.get("/api/stats")
    assert response_stats.status_code == 200
    assert "total_apps" in response_stats.json()
