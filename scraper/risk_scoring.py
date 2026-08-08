import logging
from typing import Dict, List, Any, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# List of common free email providers
FREE_EMAIL_PROVIDERS = [
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", 
    "live.com", "icloud.com", "aol.com", "protonmail.com", "zoho.com"
]

def check_free_email(email: str) -> bool:
    if not email:
        return True
    domain = email.split("@")[-1].lower() if "@" in email else ""
    return domain in FREE_EMAIL_PROVIDERS

def evaluate_signals(
    metadata: Dict[str, Any],
    perms_analysis: Dict[str, Any],
    reviews_analysis: Dict[str, Any],
    web_research: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Generate evidence signals from play store metadata, permissions, reviews, and web research.
    """
    signals = []
    
    # 1. Regulatory Warning Signal
    reg_warnings = [w for w in web_research if w.get("source_type") == "regulatory" and w.get("relevance") in ["high", "medium"]]
    if reg_warnings:
        signals.append({
            "signal": "regulatory_warning",
            "severity": "critical",
            "confidence": "high",
            "evidence_count": len(reg_warnings),
            "sources": ["regulatory"],
            "explanation": f"Found {len(reg_warnings)} regulatory notice(s) or alert(s) related to this app/developer."
        })
        
    # 2. Harassment & Debt Collection Threats
    harass_reviews_count = reviews_analysis.get("themes", {}).get("harassment", {}).get("count", 0)
    harass_web_count = sum(1 for w in web_research if "harass" in w.get("summary", "").lower() or "threat" in w.get("summary", "").lower())
    
    if harass_reviews_count > 0 or harass_web_count > 0:
        evidence_count = harass_reviews_count + harass_web_count
        sources = []
        if harass_reviews_count > 0:
            sources.append("google_play")
        if harass_web_count > 0:
            sources.append("web")
            
        # Determine confidence
        if harass_reviews_count >= 8 or (harass_reviews_count >= 3 and harass_web_count > 0):
            confidence = "high"
        elif harass_reviews_count >= 3 or harass_web_count > 0:
            confidence = "medium"
        else:
            confidence = "low"
            
        signals.append({
            "signal": "harassment_threats",
            "severity": "high",
            "confidence": confidence,
            "evidence_count": evidence_count,
            "sources": sources,
            "explanation": f"Users reported aggressive debt collection, threats, or harassment ({harass_reviews_count} reviews, {harass_web_count} web references)."
        })
        
    # 3. Contacts / Privacy Abuse (Sensitive permission Contacts + user complaints)
    has_contacts_perm = "Contacts" in perms_analysis.get("sensitive_permissions", {})
    contacts_complaints = reviews_analysis.get("themes", {}).get("contacting_contacts", {}).get("count", 0)
    
    if has_contacts_perm and contacts_complaints > 0:
        sources = ["google_play"]
        confidence = "high" if contacts_complaints >= 5 else ("medium" if contacts_complaints >= 2 else "low")
        signals.append({
            "signal": "contacts_abuse",
            "severity": "high",
            "confidence": confidence,
            "evidence_count": contacts_complaints,
            "sources": sources,
            "explanation": f"App requests Contacts permission and {contacts_complaints} user reviews allege that collectors contacted their personal contacts."
        })
    elif contacts_complaints > 3: # even without declared perm (maybe bypassed or old version)
        signals.append({
            "signal": "contacts_abuse",
            "severity": "high",
            "confidence": "medium",
            "evidence_count": contacts_complaints,
            "sources": ["google_play"],
            "explanation": f"Users allege that collectors accessed and contacted their personal contacts list ({contacts_complaints} reports)."
        })

    # 4. Hidden or Misleading Fees / Short Tenure
    fees_count = reviews_analysis.get("themes", {}).get("hidden_fees", {}).get("count", 0)
    tenure_count = reviews_analysis.get("themes", {}).get("repayment_problems", {}).get("count", 0)
    evidence_count = fees_count + tenure_count
    
    if evidence_count > 0:
        confidence = "high" if evidence_count >= 10 else ("medium" if evidence_count >= 3 else "low")
        signals.append({
            "signal": "hidden_fees_misleading_terms",
            "severity": "medium",
            "confidence": confidence,
            "evidence_count": evidence_count,
            "sources": ["google_play"],
            "explanation": f"Multiple user reviews complain of hidden charges, extremely high interest rates, or short/7-day repayment periods ({fees_count} fee complaints, {tenure_count} tenure/repayment complaints)."
        })

    # 5. Fraud or Scam Allegations
    scam_reviews_count = reviews_analysis.get("themes", {}).get("fraud_scam", {}).get("count", 0)
    scam_web_count = sum(1 for w in web_research if w.get("relevance") == "high" and w.get("source_type") in ["news", "consumer_complaint"])
    
    if scam_reviews_count > 0 or scam_web_count > 0:
        evidence_count = scam_reviews_count + scam_web_count
        sources = []
        if scam_reviews_count > 0:
            sources.append("google_play")
        if scam_web_count > 0:
            sources.append("web")
            
        confidence = "high" if (scam_reviews_count >= 10 or scam_web_count >= 2) else ("medium" if (scam_reviews_count >= 3 or scam_web_count > 0) else "low")
        signals.append({
            "signal": "fraud_scam_allegations",
            "severity": "high",
            "confidence": confidence,
            "evidence_count": evidence_count,
            "sources": sources,
            "explanation": f"Users or news reports allege fraudulent behavior, fake application status, or stolen money ({scam_reviews_count} reviews, {scam_web_count} articles/complaints)."
        })

    # 6. Unclear Developer Identity / Legitimacy
    dev_email = metadata.get("developerEmail", "")
    dev_website = metadata.get("developerWebsite", "")
    privacy_policy = metadata.get("privacyPolicy", "")
    
    dev_reasons = []
    if check_free_email(dev_email):
        dev_reasons.append("developer uses a free/public email address (e.g. Gmail)")
    if not dev_website or dev_website.strip() == "" or "example.com" in dev_website:
        dev_reasons.append("developer website is missing or generic")
    if not privacy_policy or privacy_policy.strip() == "":
        dev_reasons.append("privacy policy URL is missing")
        
    if dev_reasons:
        signals.append({
            "signal": "unclear_developer_identity",
            "severity": "medium",
            "confidence": "high",
            "evidence_count": len(dev_reasons),
            "sources": ["google_play"],
            "explanation": "Developer legitimacy signals are unclear: " + ", ".join(dev_reasons) + "."
        })

    # 7. Review Manipulation Detected
    manip_data = reviews_analysis.get("manipulation", {})
    if manip_data.get("detected"):
        reasons = manip_data.get("reasons", [])
        signals.append({
            "signal": "suspicious_review_patterns",
            "severity": "low",
            "confidence": "medium",
            "evidence_count": len(reasons),
            "sources": ["google_play"],
            "explanation": f"Possible review manipulation signals detected: {'; '.join(reasons)}."
        })

    # 8. Excessive Permissions Requested
    sensitive_perms = perms_analysis.get("sensitive_permissions", {})
    # Standard loan apps shouldn't require contacts, SMS, call logs, camera, location all together
    excessive_categories = [c for c in ["Contacts", "SMS", "Call logs", "Camera", "Location"] if c in sensitive_perms]
    if len(excessive_categories) >= 3:
        signals.append({
            "signal": "excessive_permissions",
            "severity": "medium",
            "confidence": "high",
            "evidence_count": len(excessive_categories),
            "sources": ["google_play"],
            "explanation": f"App requests {len(excessive_categories)} highly sensitive permission groups: {', '.join(excessive_categories)}."
        })
        
    return signals

def calculate_risk_score_and_verdict(
    metadata: Dict[str, Any],
    perms_analysis: Dict[str, Any],
    reviews_analysis: Dict[str, Any],
    web_research: List[Dict[str, Any]],
    signals: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate risk score (0-100) and assign verdict level.
    """
    score = 0
    
    # Weight values for severity levels
    severity_weights = {
        "critical": 45,
        "high": 25,
        "medium": 15,
        "low": 5,
        "none": 0
    }
    
    # Weight values for confidence levels
    confidence_weights = {
        "high": 1.0,
        "medium": 0.7,
        "low": 0.4
    }
    
    # Calculate score based on signals
    for sig in signals:
        sev = sig.get("severity", "none")
        conf = sig.get("confidence", "low")
        
        weight = severity_weights.get(sev, 0)
        multiplier = confidence_weights.get(conf, 0.4)
        
        # Corroboration multiplier: if signal has multiple source types (e.g. google_play and web/regulatory)
        corroboration = 1.0
        sources = sig.get("sources", [])
        if len(sources) > 1:
            corroboration = 1.2
            
        signal_contribution = weight * multiplier * corroboration
        score += signal_contribution
        
    # Cap score
    score = min(100, int(score))
    
    # Positive factors mitigation (only if score is not zero and no critical signal)
    has_critical = any(sig.get("severity") == "critical" for sig in signals)
    if score > 0 and not has_critical:
        # Check positive indicators
        mitigations = 0
        
        dev_email = metadata.get("developerEmail", "")
        dev_website = metadata.get("developerWebsite", "")
        rating = metadata.get("score", 0)
        installs = metadata.get("installs", "0")
        
        # 1. Corporate email
        if dev_email and not check_free_email(dev_email):
            mitigations += 4
        # 2. Real website
        if dev_website and dev_website.strip() != "" and "example.com" not in dev_website:
            mitigations += 4
        # 3. High Rating (> 4.2) and no manipulation
        has_manip = any(sig.get("signal") == "suspicious_review_patterns" for sig in signals)
        if rating > 4.2 and not has_manip:
            mitigations += 4
            
        score = max(0, score - mitigations)
        
    # Assign Verdict
    # Verdict levels: LOWER_RISK, CAUTION, HIGH_RISK, INSUFFICIENT_EVIDENCE
    sentiment_data = reviews_analysis.get("sentiment", {})
    reviews_count = (sentiment_data.get("positive", 0) or 0) + (sentiment_data.get("negative", 0) or 0) + (sentiment_data.get("neutral", 0) or 0)
    total_reviews = metadata.get("reviews", 0)
    
    # If the app has very little data to evaluate (no reviews, no web research and low score)
    if len(signals) == 0 and not web_research:
        # Check if we actually fetched data
        if perms_analysis.get("status") == "unavailable" and metadata.get("title") is None:
            verdict = "INSUFFICIENT_EVIDENCE"
            score = 0
        else:
            verdict = "LOWER_RISK"
    elif score >= 60 or has_critical or any(sig.get("severity") == "high" and sig.get("confidence") == "high" for sig in signals):
        verdict = "HIGH_RISK"
    elif score >= 30:
        verdict = "CAUTION"
    else:
        verdict = "LOWER_RISK"
        
    # Create key reasons
    reasons = []
    strongest_evidence = None
    uncertainties = []
    
    # Sort signals by risk score impact to find strongest evidence
    sorted_signals = sorted(
        signals,
        key=lambda x: severity_weights.get(x.get("severity"), 0) * confidence_weights.get(x.get("confidence"), 0),
        reverse=True
    )
    
    for sig in sorted_signals:
        reasons.append(sig["explanation"])
        
    if sorted_signals:
        strongest_evidence = sorted_signals[0]["explanation"]
        
    # Add generic lower risk text if no signals
    if not reasons:
        reasons.append("Evidence currently shows relatively few significant warning signals.")
        
    # Limit to 5 reasons
    reasons = reasons[:5]
    
    # Uncertainties detection
    if perms_analysis.get("status") == "unavailable":
        uncertainties.append("App permissions could not be retrieved from the Play Store.")
    if not metadata.get("developerWebsite"):
        uncertainties.append("Developer website is missing, preventing verification of licensing or physical address.")
    if not metadata.get("privacyPolicy"):
        uncertainties.append("Privacy policy link is missing on the Play Store.")
    if len(web_research) == 0:
        uncertainties.append("We found no search results or external references for this app, limiting external verification.")
        
    if not uncertainties:
        uncertainties.append("No major data gaps were detected during analysis.")
        
    return {
        "score": score,
        "level": verdict,
        "reasons": reasons,
        "strongest_evidence": strongest_evidence,
        "important_uncertainties": uncertainties
    }
