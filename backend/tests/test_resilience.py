"""Tests for the resilience scoring engine."""

import pytest
from services.resilience_engine import (
    compute_resilience,
    _carrier_diversity_score,
    _geographic_spread_score,
    _buffer_capacity_score,
    _recovery_speed_score,
)


def test_resilience_score_valid_range(store):
    G = store.get_graph()
    shipments = store.get_shipments()
    disruptions = store.get_disruptions()
    result = compute_resilience(G, shipments, disruptions, [73.0])

    assert 0 <= result.score <= 100


def test_resilience_breakdown_all_metrics_present(store):
    G = store.get_graph()
    result = compute_resilience(G, store.get_shipments(), store.get_disruptions(), [70.0])
    b = result.breakdown

    assert 0 <= b.route_redundancy <= 100
    assert 0 <= b.carrier_diversity <= 100
    assert 0 <= b.geographic_spread <= 100
    assert 0 <= b.buffer_capacity <= 100
    assert 0 <= b.recovery_speed <= 100


def test_resilience_identifies_weakest_link(store):
    G = store.get_graph()
    result = compute_resilience(G, store.get_shipments(), store.get_disruptions(), [70.0])

    valid_links = [
        "Route Redundancy", "Carrier Diversity", "Geographic Spread",
        "Buffer Capacity", "Recovery Speed"
    ]
    assert result.weakest_link in valid_links


def test_resilience_has_recommendation(store):
    G = store.get_graph()
    result = compute_resilience(G, store.get_shipments(), store.get_disruptions(), [70.0])
    assert len(result.recommendation) > 10


def test_carrier_diversity_monopoly():
    """Single carrier = low diversity."""
    from models.schemas import Shipment, Location, Route, RouteWaypoint, LatLng, RiskLevel, ShipmentStatus
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    loc = Location(city="Mumbai", state="Maharashtra", lat=19.07, lng=72.87)
    route = Route(distance_km=1200, estimated_hours=22)
    s = Shipment(
        id="T001", order_id="O001", origin=loc, destination=loc,
        current_position=LatLng(lat=19.0, lng=72.8),
        status=ShipmentStatus.ON_TRACK, risk_score=50, risk_level=RiskLevel.MEDIUM,
        risk_factors=[], confidence=0.7,
        shipping_mode="Standard Class", carrier="Delhivery",
        eta=now + timedelta(hours=24), original_eta=now + timedelta(hours=24),
        deadline=now + timedelta(hours=30), revenue=50000,
        category="FMCG", route=route, updated_at=now,
    )
    # All same carrier
    ships = [s] * 10
    score = _carrier_diversity_score(ships)
    assert score <= 20, f"Single-carrier diversity should be low, got {score}"


def test_carrier_diversity_many_carriers():
    """Many different carriers = high diversity."""
    from models.schemas import Shipment, Location, Route, LatLng, RiskLevel, ShipmentStatus
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    carrier_names = ["BlueDart", "FedEx India", "Delhivery", "DTDC", "DHL Express",
                     "XpressBees", "Ecom Express", "Shadowfax"]
    loc = Location(city="Mumbai", state="Maharashtra", lat=19.07, lng=72.87)
    route = Route(distance_km=1000, estimated_hours=18)
    ships = []
    for i, c in enumerate(carrier_names):
        s = Shipment(
            id=f"T{i}", order_id=f"O{i}", origin=loc, destination=loc,
            current_position=LatLng(lat=19.0, lng=72.8),
            status=ShipmentStatus.ON_TRACK, risk_score=30, risk_level=RiskLevel.LOW,
            risk_factors=[], confidence=0.8,
            shipping_mode="Standard Class", carrier=c,
            eta=now + timedelta(hours=24), original_eta=now + timedelta(hours=24),
            deadline=now + timedelta(hours=36), revenue=40000,
            category="FMCG", route=route, updated_at=now,
        )
        ships.append(s)

    score = _carrier_diversity_score(ships)
    assert score >= 80, f"8-carrier diversity should be high, got {score}"


def test_recovery_speed_no_history():
    score = _recovery_speed_score([])
    assert score == 75.0  # Default when no history
