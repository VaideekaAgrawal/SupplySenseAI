"""Tests for the new endpoints: nodes, simulation, shipment creation, festivals."""
import pytest
from services.data_store import DataStore


@pytest.fixture(scope="module")
def store():
    return DataStore.get()


# ── Node listing ────────────────────────────────────────────────────────

def test_node_listing_returns_all_cities(store):
    from routers.nodes import router  # just import check
    graph = store.get_graph()
    assert len(list(graph.nodes)) >= 15


# ── Festival calendar ──────────────────────────────────────────────────

def test_festival_calendar_import():
    from services.festival_calendar import get_active_festivals, get_upcoming_festivals
    upcoming = get_upcoming_festivals(365)
    assert isinstance(upcoming, list)


def test_festival_congestion_for_city():
    from services.festival_calendar import get_festival_congestion_for_city
    result = get_festival_congestion_for_city("Mumbai")
    assert "congestion" in result
    assert "monsoon" in result
    assert "is_peak_season" in result
    assert isinstance(result["congestion"], (int, float))


def test_festival_congestion_unknown_city():
    from services.festival_calendar import get_festival_congestion_for_city
    result = get_festival_congestion_for_city("Atlantis")
    assert result["congestion"] >= 0


# ── Comprehensive risk ─────────────────────────────────────────────────

def test_comprehensive_risk_computes(store):
    from routers.nodes import _compute_comprehensive_risk
    score, factors = _compute_comprehensive_risk(
        "Delhi", "Mumbai", "BlueDart", "First Class", 1400, store
    )
    assert 0 <= score <= 100
    assert len(factors) >= 1


def test_comprehensive_risk_air_mode(store):
    from routers.nodes import _compute_comprehensive_risk
    score_ground, _ = _compute_comprehensive_risk("Delhi", "Mumbai", "BlueDart", "Standard Class", 1400, store)
    score_air, _ = _compute_comprehensive_risk("Delhi", "Mumbai", "BlueDart", "First Class", 1400, store)
    assert isinstance(score_air, (int, float))


# ── Simulate node (via cascade engine) ────────────────────────────────

def test_simulate_cascade_at_mumbai(store):
    from services.cascade_engine import compute_cascade
    G = store.get_graph()
    result = compute_cascade(G, "Mumbai", severity=0.8, disruption_type="congestion")
    assert result.source is not None
    assert result.source.node_id == "Mumbai"


# ── Festival helpers ───────────────────────────────────────────────────

def test_monsoon_check():
    from services.festival_calendar import is_monsoon
    result = is_monsoon()
    assert isinstance(result, bool)


def test_ecommerce_surge():
    from services.festival_calendar import get_ecommerce_surge
    result = get_ecommerce_surge()
    # Can be None or dict
    assert result is None or isinstance(result, dict)


# ── Haversine ──────────────────────────────────────────────────────────

def test_haversine_basic():
    from routers.nodes import _haversine_km
    dist = _haversine_km(28.6139, 77.2090, 19.0760, 72.8777)  # Delhi to Mumbai
    assert 1100 < dist < 1500


def test_risk_level_thresholds():
    from routers.nodes import _risk_level
    assert _risk_level(10).value == "LOW"
    assert _risk_level(40).value == "MEDIUM"
    assert _risk_level(60).value == "HIGH"
    assert _risk_level(80).value == "CRITICAL"


# ── CITIES data ────────────────────────────────────────────────────────

def test_cities_data_available():
    from services.data_store import CITIES
    assert "Delhi" in CITIES
    assert "Mumbai" in CITIES
    assert len(CITIES) >= 20
    for city, info in CITIES.items():
        assert 5 <= info["lat"] <= 40, f"{city} lat out of range"
        assert 65 <= info["lng"] <= 100, f"{city} lng out of range"
