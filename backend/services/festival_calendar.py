"""
Indian Festival Calendar & Seasonal Congestion Engine.

Uses real Indian festival dates (2025-2027) to compute logistics congestion
factors. During peak festival seasons, supply chain disruptions increase due to:
- Warehouse staffing shortages (Diwali, Holi, Eid)
- Highway traffic surges (Durga Puja, Ganesh Chaturthi)
- Port/customs delays (year-end, pre-festival stockpiling)
- E-commerce demand spikes (Diwali, Christmas, Republic Day sales)

No API needed — dates are deterministic based on Hindu, Islamic, and national calendars.
"""

from __future__ import annotations
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple


# ─── Real Indian festival dates (2025–2027) ──────────────────────────────────

FESTIVALS: List[Dict] = [
    # 2025
    {"name": "Makar Sankranti", "date": date(2025, 1, 14), "duration_days": 2, "congestion": 0.15, "regions": ["Gujarat", "Maharashtra", "Karnataka", "Tamil Nadu"]},
    {"name": "Republic Day", "date": date(2025, 1, 26), "duration_days": 1, "congestion": 0.20, "regions": ["Delhi", "all"]},
    {"name": "Maha Shivaratri", "date": date(2025, 2, 26), "duration_days": 1, "congestion": 0.10, "regions": ["all"]},
    {"name": "Holi", "date": date(2025, 3, 14), "duration_days": 3, "congestion": 0.30, "regions": ["Uttar Pradesh", "Rajasthan", "Delhi", "Bihar", "Madhya Pradesh"]},
    {"name": "Ugadi/Gudi Padwa", "date": date(2025, 3, 30), "duration_days": 2, "congestion": 0.15, "regions": ["Maharashtra", "Karnataka", "Andhra Pradesh", "Telangana"]},
    {"name": "Eid ul-Fitr", "date": date(2025, 3, 31), "duration_days": 3, "congestion": 0.25, "regions": ["all"]},
    {"name": "Ram Navami", "date": date(2025, 4, 6), "duration_days": 1, "congestion": 0.10, "regions": ["all"]},
    {"name": "Baisakhi", "date": date(2025, 4, 13), "duration_days": 2, "congestion": 0.15, "regions": ["Punjab", "Haryana"]},
    {"name": "Buddha Purnima", "date": date(2025, 5, 12), "duration_days": 1, "congestion": 0.05, "regions": ["all"]},
    {"name": "Eid ul-Adha", "date": date(2025, 6, 7), "duration_days": 3, "congestion": 0.20, "regions": ["all"]},
    {"name": "Rath Yatra", "date": date(2025, 6, 27), "duration_days": 3, "congestion": 0.15, "regions": ["West Bengal", "Bihar"]},
    {"name": "Independence Day", "date": date(2025, 8, 15), "duration_days": 1, "congestion": 0.20, "regions": ["Delhi", "all"]},
    {"name": "Raksha Bandhan", "date": date(2025, 8, 9), "duration_days": 2, "congestion": 0.25, "regions": ["all"]},
    {"name": "Janmashtami", "date": date(2025, 8, 16), "duration_days": 2, "congestion": 0.15, "regions": ["Uttar Pradesh", "Gujarat", "Maharashtra"]},
    {"name": "Ganesh Chaturthi", "date": date(2025, 8, 27), "duration_days": 11, "congestion": 0.35, "regions": ["Maharashtra", "Karnataka", "Andhra Pradesh", "Telangana", "Goa"]},
    {"name": "Onam", "date": date(2025, 9, 5), "duration_days": 10, "congestion": 0.25, "regions": ["Kerala"]},
    {"name": "Navratri", "date": date(2025, 10, 2), "duration_days": 9, "congestion": 0.30, "regions": ["Gujarat", "Maharashtra", "Rajasthan", "all"]},
    {"name": "Dussehra", "date": date(2025, 10, 2), "duration_days": 3, "congestion": 0.30, "regions": ["all"]},
    {"name": "Karwa Chauth", "date": date(2025, 10, 5), "duration_days": 1, "congestion": 0.10, "regions": ["Rajasthan", "Punjab", "Uttar Pradesh"]},
    {"name": "Diwali", "date": date(2025, 10, 20), "duration_days": 5, "congestion": 0.50, "regions": ["all"]},
    {"name": "Bhai Dooj", "date": date(2025, 10, 23), "duration_days": 1, "congestion": 0.20, "regions": ["all"]},
    {"name": "Chhath Puja", "date": date(2025, 10, 28), "duration_days": 4, "congestion": 0.25, "regions": ["Bihar", "Uttar Pradesh"]},
    {"name": "Guru Nanak Jayanti", "date": date(2025, 11, 5), "duration_days": 1, "congestion": 0.15, "regions": ["Punjab"]},
    {"name": "Christmas", "date": date(2025, 12, 25), "duration_days": 3, "congestion": 0.20, "regions": ["Kerala", "Goa", "all"]},

    # 2026
    {"name": "Makar Sankranti", "date": date(2026, 1, 14), "duration_days": 2, "congestion": 0.15, "regions": ["Gujarat", "Maharashtra", "Karnataka", "Tamil Nadu"]},
    {"name": "Republic Day", "date": date(2026, 1, 26), "duration_days": 1, "congestion": 0.20, "regions": ["Delhi", "all"]},
    {"name": "Holi", "date": date(2026, 3, 3), "duration_days": 3, "congestion": 0.30, "regions": ["Uttar Pradesh", "Rajasthan", "Delhi", "Bihar", "Madhya Pradesh"]},
    {"name": "Eid ul-Fitr", "date": date(2026, 3, 20), "duration_days": 3, "congestion": 0.25, "regions": ["all"]},
    {"name": "Ram Navami", "date": date(2026, 3, 26), "duration_days": 1, "congestion": 0.10, "regions": ["all"]},
    {"name": "Baisakhi", "date": date(2026, 4, 13), "duration_days": 2, "congestion": 0.15, "regions": ["Punjab", "Haryana"]},
    {"name": "Eid ul-Adha", "date": date(2026, 5, 27), "duration_days": 3, "congestion": 0.20, "regions": ["all"]},
    {"name": "Rath Yatra", "date": date(2026, 6, 16), "duration_days": 3, "congestion": 0.15, "regions": ["West Bengal", "Bihar"]},
    {"name": "Independence Day", "date": date(2026, 8, 15), "duration_days": 1, "congestion": 0.20, "regions": ["Delhi", "all"]},
    {"name": "Raksha Bandhan", "date": date(2026, 8, 28), "duration_days": 2, "congestion": 0.25, "regions": ["all"]},
    {"name": "Janmashtami", "date": date(2026, 9, 4), "duration_days": 2, "congestion": 0.15, "regions": ["Uttar Pradesh", "Gujarat", "Maharashtra"]},
    {"name": "Ganesh Chaturthi", "date": date(2026, 9, 17), "duration_days": 11, "congestion": 0.35, "regions": ["Maharashtra", "Karnataka", "Andhra Pradesh", "Telangana", "Goa"]},
    {"name": "Onam", "date": date(2026, 8, 25), "duration_days": 10, "congestion": 0.25, "regions": ["Kerala"]},
    {"name": "Navratri", "date": date(2026, 10, 21), "duration_days": 9, "congestion": 0.30, "regions": ["Gujarat", "Maharashtra", "Rajasthan", "all"]},
    {"name": "Dussehra", "date": date(2026, 10, 21), "duration_days": 3, "congestion": 0.30, "regions": ["all"]},
    {"name": "Diwali", "date": date(2026, 11, 8), "duration_days": 5, "congestion": 0.50, "regions": ["all"]},
    {"name": "Chhath Puja", "date": date(2026, 11, 16), "duration_days": 4, "congestion": 0.25, "regions": ["Bihar", "Uttar Pradesh"]},
    {"name": "Guru Nanak Jayanti", "date": date(2026, 11, 24), "duration_days": 1, "congestion": 0.15, "regions": ["Punjab"]},
    {"name": "Christmas", "date": date(2026, 12, 25), "duration_days": 3, "congestion": 0.20, "regions": ["Kerala", "Goa", "all"]},
]

# ─── E-commerce sale seasons (add extra demand surge) ─────────────────────────
ECOMMERCE_SEASONS: List[Dict] = [
    {"name": "Amazon Great Indian Festival", "start": date(2025, 10, 8), "end": date(2025, 10, 15), "surge": 0.35},
    {"name": "Flipkart Big Billion Days", "start": date(2025, 10, 6), "end": date(2025, 10, 13), "surge": 0.40},
    {"name": "Republic Day Sale", "start": date(2025, 1, 20), "end": date(2025, 1, 26), "surge": 0.20},
    {"name": "Amazon Great Indian Festival", "start": date(2026, 10, 5), "end": date(2026, 10, 12), "surge": 0.35},
    {"name": "Flipkart Big Billion Days", "start": date(2026, 10, 3), "end": date(2026, 10, 10), "surge": 0.40},
    {"name": "Diwali Sale Season", "start": date(2026, 11, 1), "end": date(2026, 11, 10), "surge": 0.45},
    {"name": "Republic Day Sale", "start": date(2026, 1, 20), "end": date(2026, 1, 26), "surge": 0.20},
    {"name": "Year-End Clearance", "start": date(2026, 12, 20), "end": date(2026, 12, 31), "surge": 0.25},
]

# ─── Monsoon season (heavy rains) ────────────────────────────────────────────
MONSOON_SEASON = {"start_month": 6, "end_month": 9, "base_congestion": 0.15}

# ─── State-to-city mapping ───────────────────────────────────────────────────
CITY_STATES = {
    "Mumbai": "Maharashtra", "Delhi": "Delhi", "Chennai": "Tamil Nadu",
    "Kolkata": "West Bengal", "Bangalore": "Karnataka", "Hyderabad": "Telangana",
    "Pune": "Maharashtra", "Ahmedabad": "Gujarat", "Jaipur": "Rajasthan",
    "Lucknow": "Uttar Pradesh", "Surat": "Gujarat", "Nagpur": "Maharashtra",
    "Nhava Sheva": "Maharashtra", "Coimbatore": "Tamil Nadu", "Bhopal": "Madhya Pradesh",
    "Kochi": "Kerala", "Chandigarh": "Punjab", "Patna": "Bihar",
    "Indore": "Madhya Pradesh", "Visakhapatnam": "Andhra Pradesh",
}


def get_active_festivals(target_date: Optional[date] = None) -> List[Dict]:
    """Get all festivals active on the given date."""
    if target_date is None:
        target_date = date.today()

    active = []
    for f in FESTIVALS:
        start = f["date"]
        end = start + timedelta(days=f["duration_days"])
        if start <= target_date <= end:
            active.append(f)
    return active


def get_ecommerce_surge(target_date: Optional[date] = None) -> Optional[Dict]:
    """Check if an e-commerce sale season is active."""
    if target_date is None:
        target_date = date.today()

    for season in ECOMMERCE_SEASONS:
        if season["start"] <= target_date <= season["end"]:
            return season
    return None


def is_monsoon(target_date: Optional[date] = None) -> bool:
    """Check if current date falls in Indian monsoon season."""
    if target_date is None:
        target_date = date.today()
    return MONSOON_SEASON["start_month"] <= target_date.month <= MONSOON_SEASON["end_month"]


def get_festival_congestion_for_city(city: str, target_date: Optional[date] = None) -> Dict:
    """
    Compute total festival/seasonal congestion factor for a city.
    Returns: {congestion: 0.0-1.0, festivals: [...], ecommerce: ..., monsoon: bool}
    """
    if target_date is None:
        target_date = date.today()

    state = CITY_STATES.get(city, "")
    active = get_active_festivals(target_date)

    # Filter festivals affecting this city's region
    city_festivals = []
    total_congestion = 0.0
    for f in active:
        if "all" in f["regions"] or state in f["regions"]:
            city_festivals.append({"name": f["name"], "congestion": f["congestion"]})
            total_congestion += f["congestion"]

    # E-commerce surge
    ecom = get_ecommerce_surge(target_date)
    if ecom:
        total_congestion += ecom["surge"]

    # Monsoon
    monsoon_active = is_monsoon(target_date)
    if monsoon_active:
        # Heavier in coastal/eastern states
        coastal = {"Kerala", "Tamil Nadu", "West Bengal", "Maharashtra", "Andhra Pradesh", "Gujarat"}
        monsoon_factor = 0.20 if state in coastal else MONSOON_SEASON["base_congestion"]
        total_congestion += monsoon_factor

    # Cap at 0.8
    total_congestion = min(total_congestion, 0.8)

    return {
        "congestion": round(total_congestion, 3),
        "festivals": city_festivals,
        "ecommerce": {"name": ecom["name"], "surge": ecom["surge"]} if ecom else None,
        "monsoon": monsoon_active,
        "is_peak_season": total_congestion > 0.3,
    }


def get_upcoming_festivals(days_ahead: int = 30) -> List[Dict]:
    """Get festivals in the next N days."""
    today = date.today()
    end = today + timedelta(days=days_ahead)
    upcoming = []
    for f in FESTIVALS:
        if today <= f["date"] <= end:
            upcoming.append({
                "name": f["name"],
                "date": f["date"].isoformat(),
                "days_away": (f["date"] - today).days,
                "congestion": f["congestion"],
                "regions": f["regions"],
                "duration_days": f["duration_days"],
            })
    upcoming.sort(key=lambda x: x["days_away"])
    return upcoming
