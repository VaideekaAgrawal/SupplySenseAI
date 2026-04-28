"""Tests for the rule-based risk scorer."""

import pytest
from services.risk_scorer import score_shipment, _risk_level_from_score, RuleBasedScorer
from models.schemas import RiskLevel


def test_score_returns_valid_range(sample_shipment):
    result = score_shipment(sample_shipment)
    assert 0 <= result.risk_score <= 100


def test_score_returns_matching_risk_level(sample_shipment):
    result = score_shipment(sample_shipment)
    expected_level = _risk_level_from_score(result.risk_score)
    assert result.risk_level == expected_level


def test_score_has_confidence(sample_shipment):
    result = score_shipment(sample_shipment)
    assert 0 <= result.confidence <= 1


def test_score_has_top_factors(sample_shipment):
    result = score_shipment(sample_shipment)
    assert len(result.top_factors) >= 1
    for f in result.top_factors:
        assert 0 <= f.contribution <= 1
        assert len(f.name) > 0
        assert len(f.detail) > 0


def test_risk_level_thresholds():
    assert _risk_level_from_score(80) == RiskLevel.CRITICAL
    assert _risk_level_from_score(60) == RiskLevel.HIGH
    assert _risk_level_from_score(40) == RiskLevel.MEDIUM
    assert _risk_level_from_score(20) == RiskLevel.LOW


def test_score_all_shipments(store):
    scorer = RuleBasedScorer()
    for shipment in store.get_shipments():
        result = scorer.score(shipment)
        assert 0 <= result.risk_score <= 100, f"Out-of-range score for {shipment.id}"


def test_high_risk_carrier_scores_higher(store):
    """Shipments with unreliable carriers should score higher than FedEx."""
    ships = store.get_shipments()
    fedex_ships = [s for s in ships if s.carrier == "FedEx India"]
    shadow_ships = [s for s in ships if s.carrier == "Shadowfax"]

    if fedex_ships and shadow_ships:
        scorer = RuleBasedScorer()
        fedex_avg = sum(scorer.score(s).risk_score for s in fedex_ships) / len(fedex_ships)
        shadow_avg = sum(scorer.score(s).risk_score for s in shadow_ships) / len(shadow_ships)
        assert shadow_avg >= fedex_avg, "Shadowfax (less reliable) should score >= FedEx"
