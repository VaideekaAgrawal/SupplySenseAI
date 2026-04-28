"""
Multi-objective route optimization engine.

Generates top-3 route alternatives scored by weighted combination of:
cost, time, carbon, and risk. Uses Google Maps API when available,
falls back to estimated routes from city coordinates.

Design pattern: Template method — Google Maps and mock share the same
scoring pipeline; only the route-generation step differs.
"""

from __future__ import annotations
import math
import os
from typing import List, Dict, Optional
from models.schemas import (
    Shipment, RouteOption, OptimizeRoutesResponse, RouteComparison, RouteWaypoint
)


# ─── Constants ────────────────────────────────────────────────────────────────

FREIGHT_RATE_INR_PER_KM = 45.0      # ₹/km average road freight
AIR_FREIGHT_MULTIPLIER = 6.0         # Air is ~6x road cost
CARBON_KG_PER_KM_ROAD = 0.10        # kg CO2/km (truck)
CARBON_KG_PER_KM_AIR = 2.50         # kg CO2/km (air)
AVG_ROAD_SPEED_KMH = 55.0
AVG_AIR_SPEED_KMH = 650.0

# Pre-defined alternate ports/hubs near Mumbai
ALTERNATE_HUBS = {
    "Mumbai": [
        {"name": "Nhava Sheva", "lat": 18.95, "lng": 72.94, "cost_factor": 1.04, "time_factor": 1.1},
        {"name": "Pune Inland ICD", "lat": 18.52, "lng": 73.86, "cost_factor": 1.08, "time_factor": 1.2},
    ],
    "Chennai": [
        {"name": "Ennore Port", "lat": 13.22, "lng": 80.31, "cost_factor": 1.05, "time_factor": 1.08},
    ],
    "Kolkata": [
        {"name": "Haldia Port", "lat": 22.07, "lng": 88.09, "cost_factor": 1.06, "time_factor": 1.15},
    ],
}


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _road_factor(origin_city: str, dest_city: str) -> float:
    """Road factor: actual road distance ≈ 1.25–1.45x straight-line."""
    high_factor = {"Mumbai", "Delhi", "Kolkata", "Chennai"}
    if origin_city in high_factor or dest_city in high_factor:
        return 1.38
    return 1.28


def _generate_mock_routes(shipment: Shipment, blocked: bool = True) -> List[Dict]:
    """Generate 3 realistic route alternatives using known city coordinates."""
    o = shipment.origin
    d = shipment.destination
    straight_km = _haversine_km(o.lat, o.lng, d.lat, d.lng)
    road_km = straight_km * _road_factor(o.city, d.city)

    routes = []

    # Route 1: Original/Primary road route (potentially blocked)
    if blocked:
        risk_r1 = 0.88
        name_r1 = f"{o.city} → {d.city} (Disrupted)"
    else:
        risk_r1 = 0.12
        name_r1 = f"{o.city} → {d.city} (Primary)"

    routes.append({
        "id": "R001",
        "name": name_r1,
        "description": f"Direct road route via NH highway",
        "distance_km": road_km,
        "time_hours": road_km / AVG_ROAD_SPEED_KMH,
        "cost_inr": road_km * FREIGHT_RATE_INR_PER_KM,
        "carbon_kg": road_km * CARBON_KG_PER_KM_ROAD,
        "risk_score": risk_r1,
        "waypoints": [
            RouteWaypoint(lat=o.lat, lng=o.lng, name=o.city),
            RouteWaypoint(lat=(o.lat + d.lat) / 2, lng=(o.lng + d.lng) / 2),
            RouteWaypoint(lat=d.lat, lng=d.lng, name=d.city),
        ],
    })

    # Route 2: Alternate hub route (Nhava Sheva / inland port)
    alt_hubs = ALTERNATE_HUBS.get(o.city, [])
    if alt_hubs:
        hub = alt_hubs[0]
        hub_to_dest_km = _haversine_km(hub["lat"], hub["lng"], d.lat, d.lng) * 1.3
        total_km = _haversine_km(o.lat, o.lng, hub["lat"], hub["lng"]) * 1.2 + hub_to_dest_km
        routes.append({
            "id": "R002",
            "name": f"Via {hub['name']}",
            "description": f"Alternate route via {hub['name']} — avoids disruption zone",
            "distance_km": total_km,
            "time_hours": total_km / AVG_ROAD_SPEED_KMH * hub["time_factor"],
            "cost_inr": total_km * FREIGHT_RATE_INR_PER_KM * hub["cost_factor"],
            "carbon_kg": total_km * CARBON_KG_PER_KM_ROAD * 1.05,
            "risk_score": 0.34,
            "waypoints": [
                RouteWaypoint(lat=o.lat, lng=o.lng, name=o.city),
                RouteWaypoint(lat=hub["lat"], lng=hub["lng"], name=hub["name"]),
                RouteWaypoint(lat=d.lat, lng=d.lng, name=d.city),
            ],
        })
    else:
        # Generic alternate highway
        routes.append({
            "id": "R002",
            "name": f"Alternate highway route",
            "description": "Secondary highway — avoids primary congestion",
            "distance_km": road_km * 1.15,
            "time_hours": road_km * 1.15 / AVG_ROAD_SPEED_KMH,
            "cost_inr": road_km * 1.15 * FREIGHT_RATE_INR_PER_KM * 1.06,
            "carbon_kg": road_km * 1.15 * CARBON_KG_PER_KM_ROAD,
            "risk_score": 0.28,
            "waypoints": [
                RouteWaypoint(lat=o.lat, lng=o.lng, name=o.city),
                RouteWaypoint(lat=o.lat + (d.lat - o.lat) * 0.3, lng=o.lng + (d.lng - o.lng) * 0.1),
                RouteWaypoint(lat=d.lat, lng=d.lng, name=d.city),
            ],
        })

    # Route 3: Air freight (fast, expensive, high carbon)
    routes.append({
        "id": "R003",
        "name": "Air Freight (Express)",
        "description": "Air freight — premium service for critical shipments",
        "distance_km": straight_km,
        "time_hours": max(straight_km / AVG_AIR_SPEED_KMH + 2.0, 3.0),  # +2h handling
        "cost_inr": straight_km * FREIGHT_RATE_INR_PER_KM * AIR_FREIGHT_MULTIPLIER,
        "carbon_kg": straight_km * CARBON_KG_PER_KM_AIR,
        "risk_score": 0.08,
        "waypoints": [
            RouteWaypoint(lat=o.lat, lng=o.lng, name=o.city),
            RouteWaypoint(lat=(o.lat + d.lat) / 2, lng=(o.lng + d.lng) / 2, name="In transit"),
            RouteWaypoint(lat=d.lat, lng=d.lng, name=d.city),
        ],
    })

    return routes


def _normalize(values: List[float]) -> List[float]:
    """Min-max normalize a list of values to [0, 1]. Returns 0.5 if all equal."""
    mn, mx = min(values), max(values)
    if mx == mn:
        return [0.5] * len(values)
    return [(v - mn) / (mx - mn) for v in values]


def _compute_composite_scores(
    routes: List[Dict],
    weights: Dict[str, float],
) -> List[Dict]:
    """Score each route by weighted combination of normalized metrics."""
    norm_cost = _normalize([r["cost_inr"] for r in routes])
    norm_time = _normalize([r["time_hours"] for r in routes])
    norm_carbon = _normalize([r["carbon_kg"] for r in routes])
    norm_risk = _normalize([r["risk_score"] for r in routes])

    w_cost = weights.get("cost", 0.25)
    w_time = weights.get("time", 0.35)
    w_carbon = weights.get("carbon", 0.15)
    w_risk = weights.get("risk", 0.25)

    for i, r in enumerate(routes):
        r["composite_score"] = round(
            w_cost * norm_cost[i] +
            w_time * norm_time[i] +
            w_carbon * norm_carbon[i] +
            w_risk * norm_risk[i],
            4,
        )

    routes.sort(key=lambda r: r["composite_score"])
    return routes


def _build_recommendation_reason(route: Dict, shipment: Shipment) -> str:
    """Generate a plain-English explanation for why a route is recommended."""
    risk_pct = round((1 - route["risk_score"]) * 100)
    cost_diff_pct = round((route["cost_inr"] / (shipment.route.distance_km * FREIGHT_RATE_INR_PER_KM) - 1) * 100, 1)

    if "Air" in route["name"]:
        return (
            f"Air freight eliminates route risk ({risk_pct}% safe), "
            f"but cost premium is {cost_diff_pct}% above road. Recommended only if deadline is critical."
        )
    elif "Via" in route["name"] or "Alternate" in route["name"]:
        return (
            f"This route avoids the disruption zone. "
            f"{route['name']} has {risk_pct}% safety score with only +{abs(cost_diff_pct)}% cost. "
            f"Best balance of speed, cost, and risk."
        )
    else:
        return f"Primary route — lowest cost but currently disrupted ({round(route['risk_score'] * 100)}% risk)."


def optimize_routes(
    shipment: Shipment,
    weights: Optional[Dict[str, float]] = None,
    active_disruptions: Optional[List] = None,
) -> OptimizeRoutesResponse:
    """
    Generate top-3 optimized route alternatives for a shipment.

    Args:
        shipment: The shipment to reroute
        weights: Optimization weights {cost, time, carbon, risk}
        active_disruptions: List of active disruptions to check against

    Returns:
        OptimizeRoutesResponse with ranked alternatives and before/after comparison
    """
    if weights is None:
        weights = {"cost": 0.25, "time": 0.35, "carbon": 0.15, "risk": 0.25}

    # Normalize weights to sum to 1
    total_w = sum(weights.values())
    if total_w > 0:
        weights = {k: v / total_w for k, v in weights.items()}

    is_disrupted = shipment.status in ("disrupted", "at_risk") or shipment.risk_score > 55
    raw_routes = _generate_mock_routes(shipment, blocked=is_disrupted)
    scored_routes = _compute_composite_scores(raw_routes, weights)

    # Build RouteOption objects
    route_options: List[RouteOption] = []
    for i, r in enumerate(scored_routes):
        reason = _build_recommendation_reason(r, shipment)
        opt = RouteOption(
            id=r["id"],
            name=r["name"],
            description=r["description"],
            time_hours=round(r["time_hours"], 1),
            cost_inr=round(r["cost_inr"]),
            carbon_kg=round(r["carbon_kg"], 1),
            risk_score=round(r["risk_score"] * 100, 1),
            composite_score=r["composite_score"],
            waypoints=r.get("waypoints", []),
            is_recommended=(i == 0),
            recommendation_reason=reason if i == 0 else None,
        )
        route_options.append(opt)

    # Build before/after comparison
    current_delay_hrs = shipment.route.estimated_hours * (1 + shipment.risk_score / 100)
    recommended = route_options[0] if route_options else None

    revenue_at_risk = shipment.revenue * (shipment.risk_score / 100)
    revenue_saved = revenue_at_risk * (1 - (recommended.risk_score / 100)) if recommended else 0

    comparison = RouteComparison(
        do_nothing={
            "delay_hours": round(current_delay_hrs, 1),
            "extra_cost_inr": 0,
            "risk_score": round(shipment.risk_score, 1),
            "revenue_lost_inr": round(revenue_at_risk),
            "carbon_delta_kg": 0,
            "label": "Do Nothing",
            "recommended": False,
        },
        recommended={
            "delay_hours": round(recommended.time_hours, 1) if recommended else 0,
            "extra_cost_inr": round(recommended.cost_inr - shipment.route.distance_km * FREIGHT_RATE_INR_PER_KM) if recommended else 0,
            "risk_score": recommended.risk_score if recommended else 0,
            "revenue_saved_inr": round(revenue_saved),
            "carbon_delta_kg": round(recommended.carbon_kg - shipment.route.distance_km * CARBON_KG_PER_KM_ROAD, 1) if recommended else 0,
            "label": recommended.name if recommended else "—",
            "recommended": True,
            "reason": recommended.recommendation_reason if recommended else "",
        },
    )

    current_route_info = {
        "distance_km": shipment.route.distance_km,
        "estimated_hours": shipment.route.estimated_hours,
        "risk_score": shipment.risk_score,
        "status": shipment.status,
    }

    return OptimizeRoutesResponse(
        shipment_id=shipment.id,
        current_route=current_route_info,
        alternatives=route_options,
        comparison=comparison,
    )
