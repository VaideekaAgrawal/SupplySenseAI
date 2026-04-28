"""
Shipments router — CRUD + risk scoring for individual shipments.

Endpoints:
  GET  /shipments              — List with status/limit/offset filters
  GET  /shipments/{id}         — Single shipment with full risk breakdown
  GET  /shipments/{id}/risk    — Re-score risk on demand
  GET  /shipments/{id}/risk-explain — Detailed risk explanation for hover tooltip
  GET  /shipments/top-risk     — Top 5 high-risk shipments with auto-reroute suggestions
  PATCH /shipments/{id}/status — Update shipment status
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any

from services.data_store import DataStore
from services.risk_scorer import score_shipment
from services.route_optimizer import optimize_routes
from models.schemas import ShipmentListResponse, Shipment, RiskResult

router = APIRouter()
store = DataStore.get()


@router.get("/top-risk", response_model=List[Dict[str, Any]])
def top_risk_shipments(count: int = Query(5, ge=1, le=20)):
    """
    Get top N high-risk shipments with auto-generated reroute suggestions.
    Used on the dashboard to show the most critical shipments with recommended actions.
    """
    all_ships = store.get_shipments()
    # Sort by risk score descending
    sorted_ships = sorted(all_ships, key=lambda s: s.risk_score, reverse=True)[:count]
    
    results = []
    for s in sorted_ships:
        # Score risk with ML model
        risk = score_shipment(s)
        
        # Generate reroute options
        try:
            reroute = optimize_routes(s, active_disruptions=store.get_disruptions())
            recommended = None
            for alt in reroute.alternatives:
                if alt.is_recommended:
                    recommended = alt
                    break
            if not recommended and reroute.alternatives:
                recommended = reroute.alternatives[0]
        except Exception:
            recommended = None
            reroute = None
        
        result = {
            "shipment": s.model_dump(),
            "risk_result": risk.model_dump(),
            "risk_explanation": _build_risk_explanation(s, risk),
            "reroute": {
                "recommended": recommended.model_dump() if recommended else None,
                "alternatives": [a.model_dump() for a in reroute.alternatives] if reroute else [],
                "comparison": reroute.comparison.model_dump() if reroute else None,
            } if reroute else None,
        }
        results.append(result)
    
    return results


def _build_risk_explanation(shipment: Shipment, risk: RiskResult) -> Dict[str, Any]:
    """Build a human-readable risk explanation for tooltip/hover display."""
    factors_text = []
    for f in risk.top_factors:
        pct = round(f.contribution * 100)
        factors_text.append({
            "name": f.name,
            "contribution_pct": pct,
            "detail": f.detail,
            "icon": _factor_icon(f.name),
        })
    
    # Generate summary sentence
    top_factor = risk.top_factors[0] if risk.top_factors else None
    level_str = risk.risk_level.value if hasattr(risk.risk_level, 'value') else str(risk.risk_level)
    if level_str in ("CRITICAL", "HIGH"):
        urgency = "Immediate action recommended."
    elif level_str == "MEDIUM":
        urgency = "Monitor closely."
    else:
        urgency = "Within acceptable limits."
    
    summary = (
        f"Risk score {risk.risk_score:.0f}/100 ({level_str}). "
        f"Primary driver: {top_factor.name.lower() if top_factor else 'multiple factors'}. "
        f"{urgency}"
    )
    
    return {
        "summary": summary,
        "score": risk.risk_score,
        "level": level_str,
        "confidence": risk.confidence,
        "factors": factors_text,
        "route": f"{shipment.origin.city} → {shipment.destination.city}",
        "carrier": shipment.carrier,
        "mode": shipment.shipping_mode,
        "distance_km": shipment.route.distance_km,
    }


def _factor_icon(name: str) -> str:
    """Map risk factor names to emoji icons."""
    name_lower = name.lower()
    if "weather" in name_lower or "season" in name_lower:
        return "🌧️"
    if "carrier" in name_lower:
        return "🚛"
    if "disaster" in name_lower or "disruption" in name_lower:
        return "⚠️"
    if "distance" in name_lower or "route" in name_lower:
        return "📏"
    if "buffer" in name_lower or "eta" in name_lower:
        return "⏱️"
    if "region" in name_lower:
        return "📍"
    if "mode" in name_lower or "shipping" in name_lower:
        return "📦"
    if "congestion" in name_lower:
        return "🚧"
    if "overdue" in name_lower:
        return "🔥"
    return "📊"


@router.get("", response_model=ShipmentListResponse)
def list_shipments(
    status: Optional[str] = Query(None, description="Filter by status"),
    risk_level: Optional[str] = Query(None, description="Filter by risk_level"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List shipments with optional filtering and pagination."""
    shipments = store.get_shipments()

    if status:
        shipments = [s for s in shipments if s.status == status]
    if risk_level:
        shipments = [s for s in shipments if (s.risk_level.value if hasattr(s.risk_level, 'value') else s.risk_level) == risk_level]

    total = len(shipments)
    page = shipments[offset: offset + limit]

    return ShipmentListResponse(
        shipments=page,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/rescore")
def rescore_shipments():
    """
    Re-score all shipments using the live risk scorer.
    Factors in active disruptions, overdue deadlines, and weather.
    Also auto-removes delivered shipments and updates priorities.
    """
    store.rescore_all_shipments()
    ships = store.get_shipments()
    return {
        "rescored": len(ships),
        "critical": sum(1 for s in ships if s.priority == "critical"),
        "high": sum(1 for s in ships if s.priority == "high"),
        "medium": sum(1 for s in ships if s.priority == "medium"),
        "low": sum(1 for s in ships if s.priority == "low"),
    }


@router.get("/{shipment_id}", response_model=Shipment)
def get_shipment(shipment_id: str):
    """Get a single shipment by ID."""
    shipment = store.get_shipment(shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    return shipment


@router.get("/{shipment_id}/risk", response_model=RiskResult)
def get_shipment_risk(shipment_id: str):
    """Re-score risk for a single shipment using the live risk scorer."""
    shipment = store.get_shipment(shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    return score_shipment(shipment)


@router.get("/{shipment_id}/risk-explain")
def get_shipment_risk_explain(shipment_id: str):
    """
    Get a detailed risk explanation for a shipment — used for hover tooltips.
    Returns human-readable breakdown of why the risk score was assigned.
    """
    shipment = store.get_shipment(shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    risk = score_shipment(shipment)
    return _build_risk_explanation(shipment, risk)


@router.patch("/{shipment_id}/status")
def update_shipment_status(shipment_id: str, status: str):
    """Update shipment status (e.g., mark as rerouted or resolved)."""
    shipment = store.get_shipment(shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")

    valid_statuses = {"in_transit", "disrupted", "at_risk", "delivered", "rerouted", "pending"}
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid values: {valid_statuses}")

    shipment.status = status  # type: ignore[assignment]
    store.update_shipment(shipment)
    return {"id": shipment_id, "status": status}


@router.delete("/{shipment_id}")
def delete_shipment(shipment_id: str):
    """Delete a shipment by ID."""
    if not store.delete_shipment(shipment_id):
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    return {"id": shipment_id, "deleted": True}
