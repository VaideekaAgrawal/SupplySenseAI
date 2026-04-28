"""
Live weather service using OpenWeatherMap API (free tier).

Free tier: 60 calls/min, current weather + 5-day forecast.
Sign up at: https://openweathermap.org/api (free, no credit card)

Falls back to estimated weather risk if API key is not set or API fails.
"""

from __future__ import annotations
import os
import logging
import time
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
WEATHER_MODE = os.getenv("WEATHER_MODE", "mock")
BASE_URL = "https://api.openweathermap.org/data/2.5"

# Cache weather data for 30 minutes to avoid hitting rate limits
_cache: Dict[str, Tuple[dict, float]] = {}
CACHE_TTL = 1800  # 30 minutes


def _is_live() -> bool:
    return WEATHER_MODE == "real" and len(OPENWEATHER_API_KEY) > 5


# ─── Weather severity mapping ─────────────────────────────────────────────────

# OpenWeatherMap weather condition IDs → disruption severity (0–1)
# See: https://openweathermap.org/weather-conditions
WEATHER_SEVERITY: Dict[int, float] = {
    # Thunderstorm group (200-232)
    200: 0.5, 201: 0.65, 202: 0.8,   # thunderstorm with rain
    210: 0.4, 211: 0.55, 212: 0.75,  # thunderstorm
    221: 0.65, 230: 0.5, 231: 0.6, 232: 0.7,

    # Drizzle (300-321)
    300: 0.05, 301: 0.08, 302: 0.12,
    310: 0.1, 311: 0.12, 312: 0.15,
    313: 0.12, 314: 0.18, 321: 0.1,

    # Rain (500-531)
    500: 0.1, 501: 0.2, 502: 0.5, 503: 0.7, 504: 0.85,
    511: 0.6,  # freezing rain
    520: 0.15, 521: 0.3, 522: 0.55, 531: 0.4,

    # Snow (600-622)
    600: 0.2, 601: 0.4, 602: 0.65,
    611: 0.35, 612: 0.4, 613: 0.5,
    615: 0.25, 616: 0.35,
    620: 0.2, 621: 0.4, 622: 0.6,

    # Atmosphere (700-781)
    701: 0.1, 711: 0.25, 721: 0.15,
    731: 0.3, 741: 0.35,  # fog
    751: 0.25, 761: 0.3,
    762: 0.7,  # volcanic ash
    771: 0.6,  # squall
    781: 0.95, # tornado

    # Clear / Clouds (800-804)
    800: 0.0,  # clear
    801: 0.0,  # few clouds
    802: 0.0,  # scattered clouds
    803: 0.02, # broken clouds
    804: 0.03, # overcast
}

# Monsoon/seasonal boost for Indian regions (month → extra severity)
MONSOON_BOOST: Dict[int, float] = {
    6: 0.15, 7: 0.25, 8: 0.22, 9: 0.15,
    10: 0.08, 11: 0.05,
}


def _weather_id_to_severity(weather_id: int, month: int = 0) -> float:
    base = WEATHER_SEVERITY.get(weather_id, 0.05)
    monsoon = MONSOON_BOOST.get(month, 0.0)
    return min(base + monsoon, 1.0)


# ─── API calls ────────────────────────────────────────────────────────────────

async def fetch_weather(lat: float, lng: float, city: str = "") -> dict:
    """
    Fetch current weather for a location.
    Returns a dict with: temp, humidity, wind_speed, weather_id, description,
    severity (0-1), is_live (bool).
    """
    cache_key = f"{round(lat, 2)},{round(lng, 2)}"

    # Check cache
    if cache_key in _cache:
        cached, ts = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return cached

    if _is_live():
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{BASE_URL}/weather",
                    params={
                        "lat": lat, "lon": lng,
                        "appid": OPENWEATHER_API_KEY,
                        "units": "metric",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                weather_id = data["weather"][0]["id"]
                month = datetime.now(timezone.utc).month

                result = {
                    "city": city or data.get("name", "Unknown"),
                    "temp_c": round(data["main"]["temp"], 1),
                    "feels_like_c": round(data["main"]["feels_like"], 1),
                    "humidity": data["main"]["humidity"],
                    "wind_speed_kmh": round(data["wind"]["speed"] * 3.6, 1),
                    "weather_id": weather_id,
                    "description": data["weather"][0]["description"],
                    "icon": data["weather"][0]["icon"],
                    "severity": round(_weather_id_to_severity(weather_id, month), 3),
                    "is_live": True,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
                _cache[cache_key] = (result, time.time())
                return result

        except Exception as e:
            logger.warning(f"OpenWeatherMap API failed for {city} ({lat},{lng}): {e}")

    # ── Fallback: estimated weather based on season + region ──────────────────
    return _estimate_weather(lat, lng, city)


def _estimate_weather(lat: float, lng: float, city: str) -> dict:
    """Heuristic weather estimate when API is unavailable."""
    import random
    month = datetime.now(timezone.utc).month

    # Indian climate heuristics
    is_monsoon = month in (6, 7, 8, 9)
    is_winter = month in (11, 12, 1, 2)
    is_coastal = lng < 74 or lng > 85 or lat < 12
    is_north = lat > 26

    if is_monsoon:
        base_severity = random.uniform(0.15, 0.45)
        desc = random.choice(["moderate rain", "heavy rain", "thunderstorm with rain", "light rain"])
        temp = random.uniform(26, 34)
    elif is_winter and is_north:
        base_severity = random.uniform(0.05, 0.2)
        desc = random.choice(["fog", "mist", "haze", "clear sky"])
        temp = random.uniform(5, 18)
    else:
        base_severity = random.uniform(0.0, 0.1)
        desc = random.choice(["clear sky", "few clouds", "scattered clouds", "haze"])
        temp = random.uniform(28, 40)

    if is_coastal and is_monsoon:
        base_severity += 0.1

    return {
        "city": city,
        "temp_c": round(temp, 1),
        "feels_like_c": round(temp + random.uniform(-2, 3), 1),
        "humidity": random.randint(40, 95),
        "wind_speed_kmh": round(random.uniform(5, 35), 1),
        "weather_id": 500 if is_monsoon else 800,
        "description": desc,
        "icon": "10d" if is_monsoon else "01d",
        "severity": round(min(base_severity, 1.0), 3),
        "is_live": False,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


async def fetch_route_weather(
    origin_lat: float, origin_lng: float,
    dest_lat: float, dest_lng: float,
    origin_city: str = "", dest_city: str = "",
) -> dict:
    """Fetch weather for both origin and destination, return combined risk."""
    origin_wx = await fetch_weather(origin_lat, origin_lng, origin_city)
    dest_wx = await fetch_weather(dest_lat, dest_lng, dest_city)

    # Route weather severity = max of origin and destination
    combined_severity = max(origin_wx["severity"], dest_wx["severity"])

    return {
        "origin": origin_wx,
        "destination": dest_wx,
        "route_severity": round(combined_severity, 3),
        "advisory": _severity_advisory(combined_severity),
    }


def _severity_advisory(severity: float) -> str:
    if severity >= 0.7:
        return "CRITICAL: Severe weather on route. Expect major delays. Consider rerouting."
    elif severity >= 0.4:
        return "WARNING: Adverse weather conditions. Moderate delays likely."
    elif severity >= 0.15:
        return "CAUTION: Mild weather impact possible. Monitor conditions."
    return "CLEAR: No significant weather impact expected."


# ─── Sync versions for startup/batch use ──────────────────────────────────────

def fetch_weather_sync(lat: float, lng: float, city: str = "") -> dict:
    """Synchronous version for use during data store initialization."""
    cache_key = f"{round(lat, 2)},{round(lng, 2)}"

    if cache_key in _cache:
        cached, ts = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return cached

    if _is_live():
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(
                    f"{BASE_URL}/weather",
                    params={
                        "lat": lat, "lon": lng,
                        "appid": OPENWEATHER_API_KEY,
                        "units": "metric",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                weather_id = data["weather"][0]["id"]
                month = datetime.now(timezone.utc).month

                result = {
                    "city": city or data.get("name", "Unknown"),
                    "temp_c": round(data["main"]["temp"], 1),
                    "feels_like_c": round(data["main"]["feels_like"], 1),
                    "humidity": data["main"]["humidity"],
                    "wind_speed_kmh": round(data["wind"]["speed"] * 3.6, 1),
                    "weather_id": weather_id,
                    "description": data["weather"][0]["description"],
                    "icon": data["weather"][0]["icon"],
                    "severity": round(_weather_id_to_severity(weather_id, month), 3),
                    "is_live": True,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
                _cache[cache_key] = (result, time.time())
                return result

        except Exception as e:
            logger.warning(f"OpenWeatherMap sync failed for {city}: {e}")

    return _estimate_weather(lat, lng, city)
