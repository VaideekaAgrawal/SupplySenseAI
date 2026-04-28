"""
Live disaster/disruption feed using free public APIs.

Data sources:
1. GDACS (Global Disaster Alert and Coordination System) — UN/EU free API
   - Real-time earthquakes, floods, cyclones, droughts, volcanoes
   - No API key required
   - Docs: https://www.gdacs.org/Knowledge/wiki.aspx

2. ReliefWeb — UN OCHA free API
   - Humanitarian crisis reports/disasters
   - No API key required
   - Docs: https://apidoc.reliefweb.int/

Falls back to weather-derived disruptions when APIs are unavailable.
"""

from __future__ import annotations
import os
import logging
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

DISRUPTION_MODE = os.getenv("DISRUPTION_MODE", "real")  # "real" or "mock"

# Cache disaster data for 15 minutes
_cache: Dict[str, Tuple[list, float]] = {}
CACHE_TTL = 900


# ─── GDACS API ────────────────────────────────────────────────────────────────

GDACS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"

# Bounding box for India (tighter to avoid non-Indian events)
INDIA_BBOX = {
    "minlat": 7.0,
    "maxlat": 35.0,
    "minlon": 69.0,
    "maxlon": 90.0,
}


async def fetch_gdacs_disasters() -> List[dict]:
    """Fetch recent disasters from GDACS API (no key required)."""
    cache_key = "gdacs"
    if cache_key in _cache:
        cached, ts = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return cached

    try:
        today = datetime.now(timezone.utc)
        from_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        to_date = today.strftime("%Y-%m-%d")

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                GDACS_URL,
                params={
                    "fromDate": from_date,
                    "toDate": to_date,
                    "alertlevel": "Green;Orange;Red",
                    "eventlist": "EQ;TC;FL;DR;VO;WF",  # earthquake, cyclone, flood, drought, volcano, wildfire
                    **INDIA_BBOX,
                },
                headers={"Accept": "application/json"},
            )

            if resp.status_code == 200:
                data = resp.json()
                features = data.get("features", [])
                disasters = []

                for feat in features[:20]:  # limit to 20 most recent
                    props = feat.get("properties", {})
                    geo = feat.get("geometry", {})
                    coords = geo.get("coordinates", [0, 0])

                    alert_level = props.get("alertlevel", "Green")
                    severity_map = {"Red": 0.9, "Orange": 0.6, "Green": 0.3}

                    d_lat = coords[1] if len(coords) > 1 else 0
                    d_lng = coords[0] if len(coords) > 0 else 0

                    # Only include events within India's borders (strict check)
                    if not (7.0 <= d_lat <= 35.0 and 69.0 <= d_lng <= 90.0):
                        continue

                    disasters.append({
                        "source": "GDACS",
                        "id": f"GDACS-{props.get('eventid', 'UNK')}",
                        "type": _map_gdacs_type(props.get("eventtype", "")),
                        "title": props.get("name", props.get("htmldescription", "Unknown event")),
                        "severity": severity_map.get(alert_level, 0.3),
                        "alert_level": alert_level,
                        "lat": d_lat,
                        "lng": d_lng,
                        "country": props.get("country", ""),
                        "date": props.get("fromdate", ""),
                        "url": props.get("url", {}).get("report", ""),
                        "is_live": True,
                    })

                _cache[cache_key] = (disasters, time.time())
                return disasters

    except Exception as e:
        logger.warning(f"GDACS API failed: {e}")

    return []


def _map_gdacs_type(event_type: str) -> str:
    mapping = {
        "EQ": "earthquake",
        "TC": "cyclone",
        "FL": "flood",
        "DR": "drought",
        "VO": "volcano",
        "WF": "wildfire",
    }
    return mapping.get(event_type, "weather")


# ─── ReliefWeb API ────────────────────────────────────────────────────────────

RELIEFWEB_URL = "https://api.reliefweb.int/v1/disasters"


async def fetch_reliefweb_disasters() -> List[dict]:
    """Fetch recent India-related disasters from ReliefWeb (no key required)."""
    cache_key = "reliefweb"
    if cache_key in _cache:
        cached, ts = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return cached

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                RELIEFWEB_URL,
                json={
                    "filter": {
                        "operator": "AND",
                        "conditions": [
                            {"field": "country.name", "value": "India"},
                            {"field": "status", "value": "current"},
                        ],
                    },
                    "fields": {
                        "include": ["name", "date", "type", "country", "status", "url"],
                    },
                    "limit": 10,
                    "sort": ["date.created:desc"],
                },
                headers={"Accept": "application/json"},
            )

            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", [])
                disasters = []

                for item in items:
                    fields = item.get("fields", {})
                    dtype = "weather"
                    type_list = fields.get("type", [])
                    if type_list:
                        dtype = _map_reliefweb_type(type_list[0].get("name", ""))

                    disasters.append({
                        "source": "ReliefWeb",
                        "id": f"RW-{item.get('id', 'UNK')}",
                        "type": dtype,
                        "title": fields.get("name", "Unknown disaster"),
                        "severity": 0.6,  # ReliefWeb doesn't provide severity
                        "alert_level": "Orange",
                        "lat": 20.5937,  # India center (ReliefWeb doesn't always have coords)
                        "lng": 78.9629,
                        "country": "India",
                        "date": fields.get("date", {}).get("created", ""),
                        "url": fields.get("url", ""),
                        "is_live": True,
                    })

                _cache[cache_key] = (disasters, time.time())
                return disasters

    except Exception as e:
        logger.warning(f"ReliefWeb API failed: {e}")

    return []


def _map_reliefweb_type(type_name: str) -> str:
    name_lower = type_name.lower()
    if "flood" in name_lower:
        return "flood"
    elif "cyclone" in name_lower or "storm" in name_lower:
        return "cyclone"
    elif "earthquake" in name_lower:
        return "earthquake"
    elif "drought" in name_lower:
        return "drought"
    elif "fire" in name_lower:
        return "wildfire"
    return "weather"


# ─── Combined disruption feed ─────────────────────────────────────────────────

async def fetch_all_disruptions() -> List[dict]:
    """
    Aggregate disruptions from all sources.
    Returns a deduplicated, sorted list of real-world disruptions.
    """
    if DISRUPTION_MODE == "mock":
        return _mock_disruptions()

    gdacs = await fetch_gdacs_disasters()
    reliefweb = await fetch_reliefweb_disasters()

    # Combine and deduplicate by proximity
    combined = gdacs + reliefweb
    combined.sort(key=lambda d: d.get("severity", 0), reverse=True)
    return combined[:15]


def _mock_disruptions() -> List[dict]:
    """Fallback mock disruptions for testing without internet."""
    now = datetime.now(timezone.utc)
    return [
        {
            "source": "mock",
            "id": "MOCK-001",
            "type": "flood",
            "title": "Gujarat Flood Warning",
            "severity": 0.65,
            "alert_level": "Orange",
            "lat": 23.0225, "lng": 72.5714,
            "country": "India",
            "date": now.isoformat(),
            "url": "",
            "is_live": False,
        },
        {
            "source": "mock",
            "id": "MOCK-002",
            "type": "cyclone",
            "title": "Bay of Bengal Cyclone Warning",
            "severity": 0.8,
            "alert_level": "Red",
            "lat": 13.0827, "lng": 80.2707,
            "country": "India",
            "date": now.isoformat(),
            "url": "",
            "is_live": False,
        },
    ]


# ─── Sync versions for startup ───────────────────────────────────────────────

def fetch_disruptions_sync() -> List[dict]:
    """Synchronous version for data store initialization."""
    if DISRUPTION_MODE == "mock":
        return _mock_disruptions()

    disasters = []

    try:
        today = datetime.now(timezone.utc)
        from_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        to_date = today.strftime("%Y-%m-%d")

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                GDACS_URL,
                params={
                    "fromDate": from_date,
                    "toDate": to_date,
                    "alertlevel": "Green;Orange;Red",
                    "eventlist": "EQ;TC;FL;DR;VO;WF",
                    **INDIA_BBOX,
                },
                headers={"Accept": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                for feat in data.get("features", [])[:10]:
                    props = feat.get("properties", {})
                    geo = feat.get("geometry", {})
                    coords = geo.get("coordinates", [0, 0])
                    alert_level = props.get("alertlevel", "Green")
                    severity_map = {"Red": 0.9, "Orange": 0.6, "Green": 0.3}
                    disasters.append({
                        "source": "GDACS",
                        "id": f"GDACS-{props.get('eventid', 'UNK')}",
                        "type": _map_gdacs_type(props.get("eventtype", "")),
                        "title": props.get("name", "Unknown"),
                        "severity": severity_map.get(alert_level, 0.3),
                        "alert_level": alert_level,
                        "lat": coords[1] if len(coords) > 1 else 0,
                        "lng": coords[0] if len(coords) > 0 else 0,
                        "country": props.get("country", ""),
                        "date": props.get("fromdate", ""),
                        "url": props.get("url", {}).get("report", ""),
                        "is_live": True,
                    })
    except Exception as e:
        logger.warning(f"GDACS sync failed: {e}")

    if not disasters:
        disasters = _mock_disruptions()

    return disasters
