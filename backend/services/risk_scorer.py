"""
Risk scoring engine with SHAP-style explainability.

Implements two modes:
1. Rule-based (default, no ML model needed) — computes risk from feature heuristics
2. ML-based (when model.joblib exists) — uses trained XGBoost + real SHAP values

Design pattern: Strategy pattern for scorer selection.
"""

from __future__ import annotations
import os
import math
from typing import List, Dict, Optional
from datetime import datetime, timezone

from models.schemas import RiskFactor, RiskResult, RiskLevel, Shipment


# ─── Feature config ───────────────────────────────────────────────────────────

CARRIER_LATE_RATES: Dict[str, float] = {
    "BlueDart": 0.06,
    "FedEx India": 0.04,
    "DHL Express": 0.05,
    "Delhivery": 0.15,
    "DTDC": 0.22,
    "XpressBees": 0.18,
    "Ecom Express": 0.28,
    "Shadowfax": 0.35,
}

MODE_RISK: Dict[str, float] = {
    "First Class": 0.05,
    "Same Day": 0.08,
    "Second Class": 0.14,
    "Standard Class": 0.22,
}

SEASON_RISK: Dict[int, float] = {
    # Monsoon months (Jun-Sep) have higher risk
    6: 0.25, 7: 0.30, 8: 0.28, 9: 0.20,
    # Winter: 10-Feb mild risk
    10: 0.10, 11: 0.10, 12: 0.12, 1: 0.12, 2: 0.08,
    # Dry season
    3: 0.06, 4: 0.07, 5: 0.15,
}

REGION_RISK: Dict[str, float] = {
    "Maharashtra": 0.15,  # Mumbai port area, monsoon
    "Tamil Nadu": 0.12,   # Cyclone risk
    "West Bengal": 0.18,  # Monsoon, cyclone
    "Karnataka": 0.08,
    "Delhi": 0.10,
    "Gujarat": 0.08,
    "Rajasthan": 0.06,
    "Uttar Pradesh": 0.12,
    "Telangana": 0.08,
    "Kerala": 0.14,       # Heavy monsoon
    "Madhya Pradesh": 0.09,
    "Punjab": 0.07,
    "Bihar": 0.15,
    "Andhra Pradesh": 0.10,
}


def _risk_level_from_score(score: float) -> RiskLevel:
    if score >= 75:
        return RiskLevel.CRITICAL
    elif score >= 55:
        return RiskLevel.HIGH
    elif score >= 35:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _human_readable_factor(feature_key: str, value: float, shipment: Shipment) -> str:
    """Convert feature key/value to human-readable explanation."""
    explanations = {
        "carrier_reliability": f"{shipment.carrier}: {round((1 - value) * 100)}% on-time rate",
        "carrier_late_rate": f"{shipment.carrier}: {round((1 - value) * 100)}% on-time rate",
        "shipping_mode": f"{shipment.shipping_mode} shipping — historical delay correlation",
        "mode_risk": f"{shipment.shipping_mode} shipping — {round(value * 100)}% delay probability",
        "seasonal_risk": f"Month {datetime.now(timezone.utc).month} has {round(value * 100)}% disruption probability (IMD data)",
        "season_risk": f"Current season has {round(value * 100)}% disruption probability (IMD/weather data)",
        "route_congestion": f"This lane has {round(value * 100)}% historical delay rate",
        "distance_factor": f"Long-haul route ({round(shipment.route.distance_km)} km)",
        "distance_km_norm": f"Route distance: {round(shipment.route.distance_km)} km (normalized: {round(value, 2)})",
        "eta_buffer": "Tight delivery deadline relative to ETA",
        "eta_buffer_hours": f"ETA buffer: {round(value * 48, 1)}h — {'tight' if value < 0.25 else 'adequate'} margin",
        "origin_region": f"Origin region ({shipment.origin.state}) has elevated risk",
        "origin_region_risk": f"Origin ({shipment.origin.state}): {round(value * 100)}% regional disruption risk",
        "destination_region": f"Destination region ({shipment.destination.state}) risk factor",
        "dest_region_risk": f"Destination ({shipment.destination.state}): {round(value * 100)}% regional risk",
        "weather_severity": "Adverse weather conditions on route",
        "active_disruption": "Active disruption overlaps with this route",
        "overdue_penalty": "Shipment has exceeded its promised deadline — priority escalated",
        "month": f"Calendar month effect — current month has {round(value * 12)}/12 risk level",
        "day_of_week": f"Day-of-week effect — {'weekend' if value > 0.7 else 'weekday'} logistics patterns",
        "is_high_value": f"{'High' if value > 0.5 else 'Standard'}-value shipment (₹{round(shipment.revenue):,})",
        "is_express": f"{'Express' if value > 0.5 else 'Standard'} shipping mode",
    }
    return explanations.get(feature_key, f"Factor: {feature_key}")


# ─── Rule-based scorer ────────────────────────────────────────────────────────

class RuleBasedScorer:
    """
    Computes risk score using weighted heuristics.
    Each factor contribution mirrors what a trained SHAP explainer would output.
    """

    WEIGHTS = {
        "carrier_reliability": 0.25,
        "shipping_mode": 0.15,
        "seasonal_risk": 0.12,
        "route_congestion": 0.18,
        "distance_factor": 0.10,
        "eta_buffer": 0.12,
        "region_risk": 0.08,
    }

    def score(self, shipment: Shipment) -> RiskResult:
        now = datetime.now(timezone.utc)
        month = now.month

        # ── Check active disruptions ──────────────────────────────────────────
        disruption_boost = 0.0
        try:
            from services.data_store import DataStore
            store = DataStore.get()
            for d in store.get_disruptions(status="active"):
                if shipment.id in d.affected_shipment_ids:
                    disruption_boost = max(disruption_boost, d.severity * 0.35)
                # Check if shipment route passes through disrupted city
                elif (d.location.city == shipment.origin.city or
                      d.location.city == shipment.destination.city):
                    disruption_boost = max(disruption_boost, d.severity * 0.25)
        except Exception:
            pass

        # ── Check overdue ─────────────────────────────────────────────────────
        overdue_boost = 0.0
        try:
            if shipment.deadline < now:
                hours_overdue = (now - shipment.deadline).total_seconds() / 3600
                overdue_boost = min(hours_overdue / 48 * 0.3, 0.3)
        except Exception:
            pass

        # ── Compute raw factor values ─────────────────────────────────────────
        carrier_lr = CARRIER_LATE_RATES.get(shipment.carrier, 0.15)
        mode_r = MODE_RISK.get(shipment.shipping_mode, 0.15)
        season_r = SEASON_RISK.get(month, 0.08)

        # Route distance risk (longer = more risk, normalized)
        dist_r = min(shipment.route.distance_km / 2500, 0.4)

        # ETA buffer risk (tighter deadline = more risk)
        try:
            eta_hrs = (shipment.eta - now).total_seconds() / 3600
            deadline_hrs = (shipment.deadline - now).total_seconds() / 3600
            buffer = max(deadline_hrs - eta_hrs, 0)
            buffer_r = max(0, 1 - (buffer / 12))  # 0 if 12h+ buffer, 1 if no buffer
        except Exception:
            buffer_r = 0.2

        region_r = max(
            REGION_RISK.get(shipment.origin.state, 0.08),
            REGION_RISK.get(shipment.destination.state, 0.08),
        )

        factors_raw = {
            "carrier_reliability": carrier_lr,
            "shipping_mode": mode_r,
            "seasonal_risk": season_r,
            "route_congestion": mode_r * 1.2,
            "distance_factor": dist_r,
            "eta_buffer": buffer_r * 0.3,
            "region_risk": region_r,
        }
        if disruption_boost > 0:
            factors_raw["active_disruption"] = disruption_boost
        if overdue_boost > 0:
            factors_raw["overdue_penalty"] = overdue_boost

        # ── Dynamic weights (include disruption/overdue if present) ───────────
        weights = dict(self.WEIGHTS)
        if disruption_boost > 0:
            weights["active_disruption"] = 0.20
        if overdue_boost > 0:
            weights["overdue_penalty"] = 0.15

        # ── Weighted risk score (0–100) ───────────────────────────────────────
        raw_score = sum(weights.get(k, 0.1) * v for k, v in factors_raw.items())
        # Scale to 0–100 range
        scale_factor = 285 if len(factors_raw) <= 7 else 220
        score = min(raw_score * scale_factor, 100.0)

        # ── Top contributing factors for explainability ───────────────────────
        sorted_factors = sorted(
            [(k, v * weights.get(k, 0.1)) for k, v in factors_raw.items()],
            key=lambda x: x[1],
            reverse=True,
        )

        total_contribution = sum(v for _, v in sorted_factors[:3])
        top_factors: List[RiskFactor] = []

        for key, contrib in sorted_factors[:3]:
            pct = contrib / total_contribution if total_contribution > 0 else 0.33
            top_factors.append(RiskFactor(
                name=key.replace("_", " ").title(),
                contribution=round(pct, 2),
                detail=_human_readable_factor(key, factors_raw[key], shipment),
            ))

        # Confidence inversely proportional to variance in factors
        factor_vals = list(factors_raw.values())
        variance = sum((v - sum(factor_vals) / len(factor_vals)) ** 2 for v in factor_vals) / len(factor_vals)
        confidence = max(0.55, min(0.95, 1 - variance * 5))

        return RiskResult(
            risk_score=round(score, 1),
            risk_level=_risk_level_from_score(score),
            confidence=round(confidence, 2),
            top_factors=top_factors,
        )


# ─── ML scorer (loaded lazily) ────────────────────────────────────────────────

class MLScorer:
    """XGBoost + SHAP scorer. Only used when model.joblib exists."""

    _model = None
    _explainer = None

    @classmethod
    def _load(cls):
        if cls._model is None:
            try:
                import joblib
                model_path = os.path.join(os.path.dirname(__file__), "..", "ml", "model.joblib")
                cls._model = joblib.load(model_path)
                import shap
                cls._explainer = shap.TreeExplainer(cls._model)
            except Exception:
                cls._model = None
                cls._explainer = None
        return cls._model is not None

    def score(self, shipment: Shipment) -> Optional[RiskResult]:
        if not self._load():
            return None
        # Full ML scoring — requires feature engineering matching train_model.py
        # Returns None if model fails, triggering fallback to rule-based
        try:
            import numpy as np
            from ml.feature_config import shipment_to_features, FEATURE_NAMES, FEATURE_HUMAN_NAMES

            features = shipment_to_features(shipment)
            X = np.array(features).reshape(1, -1)

            prob = self._model.predict_proba(X)[0][1]
            score = round(prob * 100, 1)

            shap_vals = self._explainer.shap_values(X)[0]
            sorted_idx = sorted(range(len(shap_vals)), key=lambda i: abs(shap_vals[i]), reverse=True)

            total_abs = sum(abs(shap_vals[i]) for i in sorted_idx[:3]) or 1
            top_factors = [
                RiskFactor(
                    name=FEATURE_HUMAN_NAMES.get(FEATURE_NAMES[i], FEATURE_NAMES[i]),
                    contribution=round(abs(shap_vals[i]) / total_abs, 2),
                    detail=_human_readable_factor(FEATURE_NAMES[i], features[i], shipment),
                )
                for i in sorted_idx[:3]
            ]

            return RiskResult(
                risk_score=score,
                risk_level=_risk_level_from_score(score),
                confidence=round(0.75 + prob * 0.2, 2),
                top_factors=top_factors,
            )
        except Exception:
            return None


# ─── Scorer facade ────────────────────────────────────────────────────────────

_rule_scorer = RuleBasedScorer()
_ml_scorer = MLScorer()


def score_shipment(shipment: Shipment) -> RiskResult:
    """
    Score a shipment's risk. Uses ML model if available, falls back to rules.
    This is the primary entry point.
    """
    ml_result = _ml_scorer.score(shipment)
    if ml_result is not None:
        return ml_result
    return _rule_scorer.score(shipment)


def rescore_all(shipments: List[Shipment]) -> List[Shipment]:
    """Batch re-score all shipments and update their risk fields."""
    updated = []
    for s in shipments:
        result = score_shipment(s)
        s.risk_score = result.risk_score
        s.risk_level = result.risk_level
        s.risk_factors = result.top_factors
        s.confidence = result.confidence
        updated.append(s)
    return updated
