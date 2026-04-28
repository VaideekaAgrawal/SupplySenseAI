"""
Synthetic dataset generator for SupplySense AI risk scoring model.

Generates a realistic labelled dataset from the same feature distributions
used in the live data store. Labels are derived from the rule-based scorer
so the XGBoost model learns to replicate and generalise those patterns.

Usage:
    python ml/generate_dataset.py              # writes ml/dataset.csv
    python ml/generate_dataset.py --rows 5000  # custom row count
"""

from __future__ import annotations
import argparse
import csv
import random
import math
import sys
import os
from datetime import datetime, timedelta, timezone
from typing import List

# Allow running from project root or backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.risk_scorer import (
    CARRIER_LATE_RATES, MODE_RISK, SEASON_RISK, REGION_RISK, RuleBasedScorer
)
from models.schemas import (
    Shipment, Location, LatLng, Route, RouteWaypoint, RiskFactor,
    ShipmentStatus, RiskLevel
)

random.seed(0)

CARRIERS = list(CARRIER_LATE_RATES.keys())
MODES = list(MODE_RISK.keys())
REGIONS = list(REGION_RISK.keys())
MONTHS = list(range(1, 13))

# India city coordinates (same as data_store)
CITIES = {
    "Mumbai": ("Maharashtra", 19.0760, 72.8777),
    "Delhi": ("Delhi", 28.6139, 77.2090),
    "Chennai": ("Tamil Nadu", 13.0827, 80.2707),
    "Kolkata": ("West Bengal", 22.5726, 88.3639),
    "Bangalore": ("Karnataka", 12.9716, 77.5946),
    "Hyderabad": ("Telangana", 17.3850, 78.4867),
    "Pune": ("Maharashtra", 18.5204, 73.8567),
    "Ahmedabad": ("Gujarat", 23.0225, 72.5714),
    "Jaipur": ("Rajasthan", 26.9124, 75.7873),
    "Lucknow": ("Uttar Pradesh", 26.8467, 80.9462),
    "Surat": ("Gujarat", 21.1702, 72.8311),
    "Nagpur": ("Maharashtra", 21.1458, 79.0882),
    "Coimbatore": ("Tamil Nadu", 11.0168, 76.9558),
    "Kochi": ("Kerala", 9.9312, 76.2673),
    "Patna": ("Bihar", 25.5941, 85.1376),
    "Indore": ("Madhya Pradesh", 22.7196, 75.8577),
    "Visakhapatnam": ("Andhra Pradesh", 17.6868, 83.2185),
    "Chandigarh": ("Punjab", 30.7333, 76.7794),
    "Bhopal": ("Madhya Pradesh", 23.2599, 77.4126),
}
CITY_NAMES = list(CITIES.keys())


def _haversine(lat1, lng1, lat2, lng2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(max(0, a)))


def _make_shipment(month: int, carrier: str, mode: str, origin_city: str, dest_city: str, revenue: float) -> Shipment:
    """Build a minimal Shipment object suitable for risk scoring."""
    now = datetime(2025, month, random.randint(1, 28), tzinfo=timezone.utc)
    origin_state, olat, olng = CITIES[origin_city]
    dest_state, dlat, dlng = CITIES[dest_city]

    origin = Location(city=origin_city, state=origin_state, lat=olat, lng=olng)
    dest = Location(city=dest_city, state=dest_state, lat=dlat, lng=dlng)

    dist_km = _haversine(olat, olng, dlat, dlng) * 1.3
    speed = {"Standard Class": 55, "Second Class": 65, "First Class": 700, "Same Day": 45}.get(mode, 55)
    est_hours = dist_km / speed

    # Buffer: 0–18 hours between ETA and deadline
    buffer_hours = random.uniform(0, 18)
    eta = now + timedelta(hours=est_hours)
    deadline = eta + timedelta(hours=buffer_hours)

    mid_lat = (olat + dlat) / 2
    mid_lng = (olng + dlng) / 2

    route = Route(
        distance_km=round(dist_km, 1),
        estimated_hours=round(est_hours, 1),
        waypoints=[
            RouteWaypoint(lat=olat, lng=olng, name=origin_city),
            RouteWaypoint(lat=mid_lat, lng=mid_lng),
            RouteWaypoint(lat=dlat, lng=dlng, name=dest_city),
        ],
    )

    return Shipment(
        id=f"SYN-{random.randint(10000, 99999)}",
        order_id=f"ORD-SYN",
        origin=origin,
        destination=dest,
        current_position=LatLng(lat=mid_lat, lng=mid_lng),
        status=ShipmentStatus.ON_TRACK,
        risk_score=0,
        risk_level=RiskLevel.LOW,
        risk_factors=[],
        confidence=0.5,
        shipping_mode=mode,
        carrier=carrier,
        eta=eta,
        original_eta=eta,
        deadline=deadline,
        revenue=revenue,
        category="FMCG",
        route=route,
        updated_at=now,
    )


def generate(n_rows: int = 3000) -> List[dict]:
    scorer = RuleBasedScorer()
    rows = []

    for _ in range(n_rows):
        carrier = random.choice(CARRIERS)
        mode = random.choice(MODES)
        month = random.choice(MONTHS)
        origin_city = random.choice(CITY_NAMES)
        # Ensure origin != dest
        dest_city = random.choice([c for c in CITY_NAMES if c != origin_city])
        revenue = random.uniform(5000, 250000)

        shipment = _make_shipment(month, carrier, mode, origin_city, dest_city, revenue)
        result = scorer.score(shipment)

        # Binary label: 1 = HIGH or CRITICAL risk, 0 = LOW or MEDIUM
        label = 1 if result.risk_score >= 55 else 0

        from ml.feature_config import shipment_to_features, FEATURE_NAMES
        features = shipment_to_features(shipment)

        row = {"label": label, "risk_score": round(result.risk_score, 1)}
        for name, val in zip(FEATURE_NAMES, features):
            row[name] = round(val, 5)
        rows.append(row)

    return rows


def write_csv(rows: List[dict], path: str):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[generate_dataset] Written {len(rows)} rows → {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic risk dataset")
    parser.add_argument("--rows", type=int, default=3000, help="Number of rows to generate")
    parser.add_argument("--out", type=str, default=None, help="Output CSV path")
    args = parser.parse_args()

    out_path = args.out or os.path.join(os.path.dirname(__file__), "dataset.csv")
    rows = generate(args.rows)
    write_csv(rows, out_path)
