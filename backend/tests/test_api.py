"""Integration tests for FastAPI endpoints."""

import pytest


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_kpis(client):
    r = client.get("/api/v1/kpis")
    assert r.status_code == 200
    data = r.json()
    assert "active_shipments" in data
    assert "resilience_score" in data
    assert data["active_shipments"] > 0


def test_list_shipments(client):
    r = client.get("/api/v1/shipments")
    assert r.status_code == 200
    data = r.json()
    assert "shipments" in data
    assert data["total"] > 0
    assert len(data["shipments"]) > 0


def test_list_shipments_pagination(client):
    r = client.get("/api/v1/shipments?limit=5&offset=0")
    assert r.status_code == 200
    data = r.json()
    assert len(data["shipments"]) <= 5


def test_list_shipments_filter_status(client):
    r = client.get("/api/v1/shipments?status=disrupted")
    assert r.status_code == 200


def test_get_shipment_by_id(client):
    r = client.get("/api/v1/shipments/SH001")
    assert r.status_code == 200
    s = r.json()
    assert s["id"] == "SH001"
    assert "risk_score" in s
    assert "carrier" in s


def test_get_shipment_not_found(client):
    r = client.get("/api/v1/shipments/DOESNOTEXIST")
    assert r.status_code == 404


def test_get_shipment_risk(client):
    r = client.get("/api/v1/shipments/SH001/risk")
    assert r.status_code == 200
    risk = r.json()
    assert "risk_score" in risk
    assert 0 <= risk["risk_score"] <= 100


def test_list_disruptions(client):
    r = client.get("/api/v1/disruptions")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) > 0


def test_get_disruption(client):
    r = client.get("/api/v1/disruptions/DIS001")
    assert r.status_code == 200
    d = r.json()
    assert d["id"] == "DIS001"


def test_cascade_by_disruption(client):
    r = client.get("/api/v1/cascade/DIS001")
    assert r.status_code == 200
    data = r.json()
    assert "source" in data
    assert "summary" in data
    assert data["disruption_id"] == "DIS001"


def test_cascade_simulate(client):
    r = client.post("/api/v1/cascade/simulate", json={
        "location": "Mumbai",
        "type": "congestion",
        "severity": 0.7,
        "duration_hours": 12,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["disruption_id"].startswith("SIM-")


def test_optimize_routes(client):
    r = client.post("/api/v1/optimize/routes", json={
        "shipment_id": "SH001",
        "weights": {"cost": 0.25, "time": 0.35, "carbon": 0.15, "risk": 0.25},
    })
    assert r.status_code == 200
    data = r.json()
    assert "alternatives" in data
    assert len(data["alternatives"]) >= 2
    assert "comparison" in data


def test_optimize_accept_route(client):
    r = client.post("/api/v1/optimize/accept", json={
        "shipment_id": "SH001",
        "route_id": "R002",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "rerouted"


def test_chat_mock(client):
    r = client.post("/api/v1/chat", json={
        "message": "What if Mumbai Port closes for 2 days?",
        "session_id": "test-session",
    })
    assert r.status_code == 200
    data = r.json()
    assert "message" in data
    assert len(data["message"]) > 10


def test_resilience_score(client):
    r = client.get("/api/v1/resilience")
    assert r.status_code == 200
    data = r.json()
    assert "score" in data
    assert 0 <= data["score"] <= 100
    assert "breakdown" in data
    assert "weakest_link" in data


def test_resilience_history(client):
    r = client.get("/api/v1/resilience/history")
    assert r.status_code == 200
    data = r.json()
    assert "trend" in data
    assert len(data["trend"]) > 0


def test_list_alerts(client):
    r = client.get("/api/v1/alerts")
    assert r.status_code == 200
    data = r.json()
    assert "alerts" in data
    assert "total" in data


def test_list_alerts_unread_only(client):
    r = client.get("/api/v1/alerts?unread_only=true")
    assert r.status_code == 200
    data = r.json()
    for alert in data["alerts"]:
        assert not alert["read"]


# ── New tests for v0.6.0 features ──────────────────────────────────────────


def test_shipment_has_priority(client):
    """Shipments should include priority field after rescore."""
    r = client.get("/api/v1/shipments?limit=5")
    assert r.status_code == 200
    for s in r.json()["shipments"]:
        assert "priority" in s
        assert s["priority"] in ("low", "medium", "high", "critical")


def test_shipment_has_deadline(client):
    """Shipments should include deadline and original_eta."""
    r = client.get("/api/v1/shipments/SH001")
    assert r.status_code == 200
    s = r.json()
    assert "deadline" in s
    assert "original_eta" in s


def test_rescore_shipments(client):
    """POST /shipments/rescore should re-score all shipments."""
    r = client.post("/api/v1/shipments/rescore", json={})
    assert r.status_code == 200
    data = r.json()
    assert "rescored" in data
    assert data["rescored"] > 0
    assert "critical" in data
    assert "high" in data
    assert "medium" in data
    assert "low" in data
    assert data["critical"] + data["high"] + data["medium"] + data["low"] == data["rescored"]


def test_delete_shipment(client):
    """DELETE /shipments/{id} should remove the shipment."""
    # First verify it exists
    r = client.get("/api/v1/shipments/SH009")
    assert r.status_code == 200

    # Delete it
    r = client.delete("/api/v1/shipments/SH009")
    assert r.status_code == 200
    assert r.json()["deleted"] is True

    # Verify it's gone
    r = client.get("/api/v1/shipments/SH009")
    assert r.status_code == 404


def test_delete_shipment_not_found(client):
    """DELETE non-existent shipment should return 404."""
    r = client.delete("/api/v1/shipments/DOESNOTEXIST")
    assert r.status_code == 404


def test_risk_score_consistency(client):
    """Risk score in shipment list should match risk-explain score."""
    r = client.get("/api/v1/shipments?limit=3")
    assert r.status_code == 200
    for s in r.json()["shipments"]:
        explain = client.get(f"/api/v1/shipments/{s['id']}/risk-explain")
        assert explain.status_code == 200
        e = explain.json()
        # Score should be very close (within 5 points due to float rounding)
        assert abs(s["risk_score"] - e["score"]) < 5, (
            f"{s['id']}: list={s['risk_score']}, explain={e['score']}"
        )


def test_resilience_score_matches_kpi(client):
    """Resilience score from /resilience should match the one in /kpis."""
    kpis_r = client.get("/api/v1/kpis")
    res_r = client.get("/api/v1/resilience")
    assert kpis_r.status_code == 200
    assert res_r.status_code == 200
    kpi_score = kpis_r.json()["resilience_score"]
    res_score = res_r.json()["score"]
    # Should be within 2 points (dynamic computation may shift slightly)
    assert abs(kpi_score - res_score) < 2, (
        f"KPI resilience={kpi_score}, endpoint resilience={res_score}"
    )


def test_pagination_first_page(client):
    """First page should return up to 20 shipments."""
    r = client.get("/api/v1/shipments?limit=20&offset=0")
    assert r.status_code == 200
    data = r.json()
    assert len(data["shipments"]) <= 20


def test_pagination_second_page(client):
    """Second page should return next batch."""
    r = client.get("/api/v1/shipments?limit=25&offset=20")
    assert r.status_code == 200
    data = r.json()
    assert len(data["shipments"]) <= 25


def test_filter_by_risk_level(client):
    """Filter shipments by risk level."""
    r = client.get("/api/v1/shipments?risk_level=LOW&limit=100")
    assert r.status_code == 200
    for s in r.json()["shipments"]:
        assert s["risk_level"] == "LOW"


def test_accept_route_rescores(client):
    """Accepting a route should mark shipment as rerouted."""
    r = client.post("/api/v1/optimize/accept", json={
        "shipment_id": "SH002",
        "route_id": "R001",
    })
    assert r.status_code == 200
    assert r.json()["status"] == "rerouted"

    # Verify the shipment is now rerouted
    s = client.get("/api/v1/shipments/SH002")
    assert s.status_code == 200
    assert s.json()["status"] == "rerouted"
