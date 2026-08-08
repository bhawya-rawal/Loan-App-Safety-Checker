import os
import json
import time
import logging
from typing import Dict, List, Any, Optional
from google_play_scraper import permissions as play_permissions

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join("data", "raw", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_path(app_id: str) -> str:
    return os.path.join(CACHE_DIR, f"permissions_{app_id}.json")

def load_cached_permissions(app_id: str, max_age_days: int = 1) -> Optional[Dict[str, Any]]:
    path = get_cache_path(app_id)
    if os.path.exists(path):
        mtime = os.path.getmtime(path)
        age_seconds = time.time() - mtime
        if age_seconds < max_age_days * 86400:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read permissions cache for {app_id}: {e}")
    return None

def save_to_cache(app_id: str, data: Dict[str, Any]) -> None:
    path = get_cache_path(app_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to write permissions cache for {app_id}: {e}")

# Key sensitive permissions to look for
SENSITIVE_PERMISSIONS_MAPPING = {
    "Contacts": [
        "android.permission.READ_CONTACTS",
        "android.permission.WRITE_CONTACTS",
        "android.permission.GET_ACCOUNTS"
    ],
    "SMS": [
        "android.permission.READ_SMS",
        "android.permission.SEND_SMS",
        "android.permission.RECEIVE_SMS",
        "android.permission.RECEIVE_MMS",
        "android.permission.RECEIVE_WAP_PUSH"
    ],
    "Call logs": [
        "android.permission.READ_CALL_LOG",
        "android.permission.WRITE_CALL_LOG",
        "android.permission.PROCESS_OUTGOING_CALLS"
    ],
    "Phone": [
        "android.permission.READ_PHONE_STATE",
        "android.permission.CALL_PHONE",
        "android.permission.READ_PHONE_NUMBERS"
    ],
    "Location": [
        "android.permission.ACCESS_FINE_LOCATION",
        "android.permission.ACCESS_COARSE_LOCATION",
        "android.permission.ACCESS_BACKGROUND_LOCATION"
    ],
    "Camera": [
        "android.permission.CAMERA"
    ],
    "Microphone": [
        "android.permission.RECORD_AUDIO"
    ],
    "Storage": [
        "android.permission.READ_EXTERNAL_STORAGE",
        "android.permission.WRITE_EXTERNAL_STORAGE",
        "android.permission.MANAGE_EXTERNAL_STORAGE"
    ],
    "Accessibility": [
        "android.permission.BIND_ACCESSIBILITY_SERVICE"
    ],
    "Device administration": [
        "android.permission.BIND_DEVICE_ADMIN"
    ]
}

def fetch_app_permissions(app_id: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Fetch app permissions and parse them into sensitive categories.
    """
    if use_cache:
        cached = load_cached_permissions(app_id)
        if cached is not None:
            return cached

    logger.info(f"Fetching permissions for {app_id}...")
    raw_perms = {}
    try:
        # play_permissions returns a dict of permission descriptions/groups
        raw_perms = play_permissions(app_id)
        save_to_cache(app_id, raw_perms)
    except Exception as e:
        logger.error(f"Failed to fetch permissions for {app_id}: {e}")
        # Return empty list cached, but store it as error
        raw_perms = {"error": str(e)}
        save_to_cache(app_id, raw_perms)

    analyzed = analyze_permissions(raw_perms)
    return analyzed

def analyze_permissions(raw_perms: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze raw permissions list to classify sensitive permissions.
    """
    if "error" in raw_perms or not raw_perms:
        return {
            "declared_permissions": [],
            "sensitive_permissions": {},
            "status": "unavailable"
        }

    # Extract all permission strings from raw_perms.
    # Typically raw_perms is a dict like: {'Permission Group Name': ['permission 1', 'permission 2']}
    # Or sometimes it contains dictionaries/tuples. Let's flatten everything to uppercase/lowercase strings.
    declared = []
    for group, perms_list in raw_perms.items():
        if isinstance(perms_list, list):
            for perm in perms_list:
                if isinstance(perm, str):
                    declared.append(perm)
                elif isinstance(perm, dict) and "name" in perm:
                    # In some library versions, it returns details as dicts
                    declared.append(perm["name"])
        elif isinstance(perms_list, str):
            declared.append(perms_list)

    sensitive_found = {}
    for category, pattern_list in SENSITIVE_PERMISSIONS_MAPPING.items():
        found_in_category = []
        for p in declared:
            for pattern in pattern_list:
                # Direct check or substring match for safety
                if pattern.lower() in p.lower():
                    found_in_category.append(p)
                    break
        if found_in_category:
            sensitive_found[category] = list(set(found_in_category))

    return {
        "declared_permissions": list(set(declared)),
        "sensitive_permissions": sensitive_found,
        "status": "success"
    }
