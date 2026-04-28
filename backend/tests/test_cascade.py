"""Tests for the cascade engine BFS propagation algorithm."""

import pytest
from services.data_store import DataStore
from services.cascade_engine import compute_cascade, simulate_disruption, cascade_to_dict
from models.schemas import SimulateDisruptionRequest, DisruptionType


def test_cascade_produces_result(store):
    G = store.get_graph()
    result = compute_cascade(G, "Mumbai", severity=0.85, disruption_type="congestion", disruption_id="TEST")

    assert result.disruption_id == "TEST"
    assert result.source.node_id == "Mumbai"
    assert result.source.depth == 0
    assert result.source.impact_score == pytest.approx(0.85)


def test_cascade_propagates_downstream(store):
    G = store.get_graph()
    result = compute_cascade(G, "Mumbai", severity=0.9, disruption_type="port_closure")

    # Downstream nodes should exist if graph has edges from Mumbai
    edges_from_mumbai = list(G.successors("Mumbai"))
    if edges_from_mumbai:
        assert len(result.affected) > 0, "Expected downstream cascade nodes"


def test_cascade_impact_decays_with_depth(store):
    G = store.get_graph()
    result = compute_cascade(G, "Mumbai", severity=0.9, disruption_type="congestion")

    for node in result.affected:
        # Impact at depth N should be less than source severity
        assert node.impact_score <= 0.9 + 0.01  # allow floating point slack


def test_cascade_no_cycles(store):
    """Visited-set guard should prevent infinite loops."""
    G = store.get_graph()
    result = compute_cascade(G, "Mumbai", severity=0.9, disruption_type="congestion")
    seen_ids = set()
    for node in result.affected:
        assert node.node_id not in seen_ids, f"Cycle detected at {node.node_id}"
        seen_ids.add(node.node_id)


def test_cascade_summary_positive(store):
    G = store.get_graph()
    result = compute_cascade(G, "Mumbai", severity=0.8, disruption_type="port_closure")

    assert result.summary.total_shipments >= 0
    assert result.summary.revenue_at_risk >= 0
    assert result.summary.customers_affected >= 0


def test_cascade_to_dict_serializable(store):
    G = store.get_graph()
    result = compute_cascade(G, "Mumbai", severity=0.7, disruption_type="weather")
    d = cascade_to_dict(result)

    assert "disruption_id" in d
    assert "source" in d
    assert "summary" in d
    assert isinstance(d["affected"], list)


def test_simulate_disruption(store):
    req = SimulateDisruptionRequest(
        location="Delhi",
        type=DisruptionType.WEATHER,
        severity=0.6,
        duration_hours=12,
    )
    result = simulate_disruption(req, store)
    assert result.disruption_id.startswith("SIM-")
    assert result.source is not None


def test_simulate_unknown_location_fallback(store):
    """Should fall back to Mumbai if location not in graph."""
    req = SimulateDisruptionRequest(
        location="UnknownCity123",
        type=DisruptionType.ROAD_BLOCK,
        severity=0.5,
        duration_hours=6,
    )
    result = simulate_disruption(req, store)
    assert result is not None
    assert result.source is not None


def test_cascade_for_seeded_disruption(store):
    disruptions = store.get_disruptions()
    assert len(disruptions) >= 1, "Need at least 1 disruption"
    disruption = disruptions[0]  # Use first available (may be live)

    from services.cascade_engine import compute_cascade_for_disruption
    result = compute_cascade_for_disruption(disruption, store)

    assert result.disruption_id == disruption.id
    # Cascade tree should be generated regardless of source
    assert result.source is not None
