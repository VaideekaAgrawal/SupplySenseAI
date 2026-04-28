"""
Feature engineering config for XGBoost risk scoring model.

Defines the feature vector that maps a Shipment object → numeric array,
shared between training (train_model.py) and inference (risk_scorer.py).
"""

from __future__ import annotations
from typing import List
from datetime import datetime, timezone

from models.schemas import Shipment
from services.risk_scorer import CARRIER_LATE_RATES, MODE_RISK, SEASON_RISK, REGION_RISK


FEATURE_NAMES: List[str] = [
    "carrier_late_rate",
    "mode_risk",
    "season_risk",
    "distance_km_norm",
    "eta_buffer_hours",
    "origin_region_risk",
    "dest_region_risk",
    "month",
    "day_of_week",
    "is_high_value",     # revenue > ₹75K
    "is_express",        # Same Day or First Class
]

FEATURE_HUMAN_NAMES = {
    "carrier_late_rate": "Carrier Reliability",
    "mode_risk": "Shipping Mode",
    "season_risk": "Seasonal Risk",
    "distance_km_norm": "Route Distance",
    "eta_buffer_hours": "ETA Buffer",
    "origin_region_risk": "Origin Region Risk",
    "dest_region_risk": "Destination Region Risk",
    "month": "Calendar Month",
    "day_of_week": "Day of Week",
    "is_high_value": "High-Value Shipment",
    "is_express": "Express Shipping",
}


def shipment_to_features(shipment: Shipment) -> List[float]:
    """Convert a Shipment to a numeric feature vector."""
    now = datetime.now(timezone.utc)
    month = now.month
    dow = now.weekday()

    carrier_lr = CARRIER_LATE_RATES.get(shipment.carrier, 0.15)
    mode_r = MODE_RISK.get(shipment.shipping_mode, 0.15)
    season_r = SEASON_RISK.get(month, 0.08)
    dist_norm = min(shipment.route.distance_km / 2500, 1.0)

    try:
        eta_hrs = (shipment.eta - now).total_seconds() / 3600
        deadline_hrs = (shipment.deadline - now).total_seconds() / 3600
        buffer_hrs = max(0, deadline_hrs - eta_hrs)
    except Exception:
        buffer_hrs = 4.0

    origin_r = REGION_RISK.get(shipment.origin.state, 0.08)
    dest_r = REGION_RISK.get(shipment.destination.state, 0.08)
    is_high_value = 1.0 if shipment.revenue > 75000 else 0.0
    is_express = 1.0 if shipment.shipping_mode in ("Same Day", "First Class") else 0.0

    return [
        carrier_lr, mode_r, season_r, dist_norm,
        buffer_hrs / 48.0,  # normalize buffer
        origin_r, dest_r,
        month / 12.0, dow / 6.0,
        is_high_value, is_express,
    ]
