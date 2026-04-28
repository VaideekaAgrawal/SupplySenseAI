"""
Node / Port risk analysis and shipment creation router.

Endpoints:
  GET  /nodes              — List all network nodes with risk summary
  GET  /nodes/{city}/risk  — Detailed risk analysis for a port/city
  POST /shipments/create   — Create a new shipment and get route + risk analysis
  POST /simulate/node      — What-if simulation for any node in the network
  GET  /festivals          — Upcoming Indian festival calendar with congestion impact
  GET  /festivals/impact   — Current festival/seasonal congestion for all cities
"""

from __future__ import annotations
import uuid
import math
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Query

from services.data_store import DataStore, CITIES, CARRIERS_DATA, CATEGORIES, SHIPPING_MODES
from services.risk_scorer import score_shipment
from services.cascade_engine import compute_cascade, cascade_to_dict
from services.route_optimizer import optimize_routes
from services.festival_calendar import (
    get_festival_congestion_for_city,
    get_upcoming_festivals,
    get_active_festivals,
    get_ecommerce_surge,
    is_monsoon,
)
from models.schemas import (
    Shipment, Location, LatLng, Route, RouteWaypoint,
    RiskFactor, RiskResult, RiskLevel, ShipmentStatus,
    CreateShipmentRequest, CreateShipmentResponse,
    NodeRiskAnalysis, SimulateNodeRequest, SimulateNodeResponse,
    DisruptionType, CascadeResult,
)

router = APIRouter()


def _loc(city: str) -> Location:
    c = CITIES[city]
    return Location(city=city, state=c["state"], lat=c["lat"], lng=c["lng"])


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(max(0, a)))


def _build_route(origin: Location, dest: Location, mode: str) -> Route:
    dist = _haversine_km(origin.lat, origin.lng, dest.lat, dest.lng) * 1.3
    speed_map = {"Standard Class": 55, "Second Class": 65, "First Class": 700, "Same Day": 45}
    speed = speed_map.get(mode, 55)
    hours = dist / speed
    mid_lat = (origin.lat + dest.lat) / 2
    mid_lng = (origin.lng + dest.lng) / 2
    return Route(
        distance_km=round(dist, 1),
        estimated_hours=round(hours, 1),
        waypoints=[
            RouteWaypoint(lat=origin.lat, lng=origin.lng, name=origin.city),
            RouteWaypoint(lat=mid_lat, lng=mid_lng),
            RouteWaypoint(lat=dest.lat, lng=dest.lng, name=dest.city),
        ],
    )


def _risk_level(score: float) -> RiskLevel:
    if score >= 75:
        return RiskLevel.CRITICAL
    elif score >= 55:
        return RiskLevel.HIGH
    elif score >= 35:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _compute_comprehensive_risk(
    origin: str, dest: str, carrier_name: str, mode: str, route_dist: float, store: DataStore
) -> tuple:
    """Compute risk score from ALL factors: weather, carrier, route, festival, disaster, operational."""
    factors = []
    total_risk = 0.0

    # 1. Weather risk (from live cache)
    weather_cache = getattr(store, '_weather_cache', {})
    orig_wx = weather_cache.get(origin, {"severity": 0.05})
    dest_wx = weather_cache.get(dest, {"severity": 0.05})
    weather_sev = max(orig_wx.get("severity", 0), dest_wx.get("severity", 0))
    if weather_sev > 0.05:
        factors.append(RiskFactor(
            name="Weather conditions",
            contribution=round(min(weather_sev * 0.5, 0.4), 2),
            detail=f"Live: {orig_wx.get('description', 'conditions')} (severity: {weather_sev:.0%})"
        ))
        total_risk += weather_sev * 25

    # 2. Carrier reliability
    carrier_risk_map = {
        "BlueDart": 0.06, "FedEx India": 0.04, "DHL Express": 0.05,
        "Delhivery": 0.15, "DTDC": 0.22, "Ecom Express": 0.28,
        "Shadowfax": 0.35, "XpressBees": 0.18
    }
    carrier_risk = carrier_risk_map.get(carrier_name, 0.15)
    factors.append(RiskFactor(
        name="Carrier reliability",
        contribution=round(carrier_risk, 2),
        detail=f"{carrier_name}: {round((1 - carrier_risk) * 100)}% on-time rate"
    ))
    total_risk += carrier_risk * 20

    # 3. Route distance risk
    dist_risk = min(route_dist / 2500, 0.4)
    factors.append(RiskFactor(
        name="Route distance",
        contribution=round(dist_risk, 2),
        detail=f"{route_dist:.0f} km — longer routes have more failure points"
    ))
    total_risk += dist_risk * 15

    # 4. Shipping mode risk
    mode_risk_map = {"Standard Class": 0.22, "Second Class": 0.14, "First Class": 0.05, "Same Day": 0.08}
    mode_risk = mode_risk_map.get(mode, 0.15)
    factors.append(RiskFactor(
        name="Shipping mode",
        contribution=round(mode_risk, 2),
        detail=f"{mode}: {'higher' if mode_risk > 0.15 else 'standard'} delay probability"
    ))
    total_risk += mode_risk * 10

    # 5. Festival/seasonal congestion
    orig_festival = get_festival_congestion_for_city(origin)
    dest_festival = get_festival_congestion_for_city(dest)
    festival_cong = max(orig_festival["congestion"], dest_festival["congestion"])
    if festival_cong > 0:
        festival_names = [f["name"] for f in orig_festival["festivals"] + dest_festival["festivals"]]
        detail = f"Active: {', '.join(festival_names[:3])}" if festival_names else "Seasonal congestion"
        if orig_festival.get("monsoon") or dest_festival.get("monsoon"):
            detail += " + Monsoon season"
        if orig_festival.get("ecommerce") or dest_festival.get("ecommerce"):
            ecom = orig_festival.get("ecommerce") or dest_festival.get("ecommerce")
            detail += f" + {ecom['name']}"
        factors.append(RiskFactor(
            name="Festival/seasonal congestion",
            contribution=round(min(festival_cong, 0.5), 2),
            detail=detail
        ))
        total_risk += festival_cong * 20

    # 6. Disaster proximity
    disaster_feed = getattr(store, '_disaster_feed', [])
    for d in disaster_feed:
        for city in [origin, dest]:
            city_info = CITIES.get(city, {})
            dist_to_disaster = _haversine_km(
                city_info.get("lat", 0), city_info.get("lng", 0),
                d.get("lat", 0), d.get("lng", 0)
            )
            if dist_to_disaster < 500:
                sev = d.get("severity", 0.3)
                factors.append(RiskFactor(
                    name="Active disaster proximity",
                    contribution=round(sev * 0.5, 2),
                    detail=f"{d['title']} — {dist_to_disaster:.0f} km from {city}"
                ))
                total_risk += sev * 30
                break

    # 7. Congestion/bottleneck (based on traffic through node in the graph)
    G = store.get_graph()
    for city in [origin, dest]:
        if city in G.nodes:
            degree = G.degree(city)
            if degree > 8:
                bottleneck_risk = 0.15
                factors.append(RiskFactor(
                    name="Hub bottleneck risk",
                    contribution=bottleneck_risk,
                    detail=f"{city} is a high-traffic hub ({degree} connections)"
                ))
                total_risk += bottleneck_risk * 10

    risk_score = round(min(max(total_risk, 2.0), 98.0), 1)
    return risk_score, factors


# ─── POST /shipments/create ───────────────────────────────────────────────────

@router.post("/shipments/create", response_model=CreateShipmentResponse)
def create_shipment(req: CreateShipmentRequest):
    """
    Create a new shipment, compute its risk, and return alternative routes.
    The shipment is added to the live data store.
    """
    store = DataStore.get()

    if req.origin_city not in CITIES:
        raise HTTPException(400, f"Unknown origin city: {req.origin_city}. Available: {list(CITIES.keys())}")
    if req.destination_city not in CITIES:
        raise HTTPException(400, f"Unknown destination city: {req.destination_city}. Available: {list(CITIES.keys())}")
    if req.origin_city == req.destination_city:
        raise HTTPException(400, "Origin and destination must be different")

    carrier_name = req.carrier or random.choice([c["name"] for c in CARRIERS_DATA])
    carrier_names = [c["name"] for c in CARRIERS_DATA]
    if carrier_name not in carrier_names:
        raise HTTPException(400, f"Unknown carrier: {carrier_name}. Available: {carrier_names}")

    if req.shipping_mode not in SHIPPING_MODES:
        raise HTTPException(400, f"Invalid shipping mode. Available: {SHIPPING_MODES}")

    origin = _loc(req.origin_city)
    dest = _loc(req.destination_city)
    route = _build_route(origin, dest, req.shipping_mode)

    # Compute comprehensive risk
    risk_score, risk_factors = _compute_comprehensive_risk(
        req.origin_city, req.destination_city, carrier_name, req.shipping_mode,
        route.distance_km, store
    )

    now = datetime.now(timezone.utc)
    sid = f"SH{str(len(store.shipments) + 1).zfill(3)}"

    # Determine status from risk
    if risk_score >= 65:
        status = ShipmentStatus.DISRUPTED
    elif risk_score >= 40:
        status = ShipmentStatus.AT_RISK
    else:
        status = ShipmentStatus.ON_TRACK

    shipment = Shipment(
        id=sid,
        order_id=f"ORD-{sid}-{uuid.uuid4().hex[:6].upper()}",
        origin=origin,
        destination=dest,
        current_position=LatLng(lat=(origin.lat + dest.lat) / 2, lng=(origin.lng + dest.lng) / 2),
        status=status,
        risk_score=risk_score,
        risk_level=_risk_level(risk_score),
        risk_factors=risk_factors[:5],
        confidence=0.82,
        shipping_mode=req.shipping_mode,
        carrier=carrier_name,
        eta=now + timedelta(hours=route.estimated_hours * (1 + risk_score / 200)),
        original_eta=now + timedelta(hours=route.estimated_hours),
        deadline=now + timedelta(hours=req.deadline_hours),
        revenue=req.revenue,
        category=req.category,
        route=route,
        updated_at=now,
    )

    # Add to store
    store.shipments[sid] = shipment
    store.rebuild_graph()

    # Get route alternatives
    disruptions = store.get_disruptions()
    routes_resp = optimize_routes(shipment, active_disruptions=disruptions)

    risk_result = RiskResult(
        risk_score=risk_score,
        risk_level=_risk_level(risk_score),
        confidence=0.82,
        top_factors=risk_factors[:5],
    )

    return CreateShipmentResponse(
        shipment=shipment,
        routes=routes_resp.alternatives,
        risk_breakdown=risk_result,
    )


# ─── GET /nodes ───────────────────────────────────────────────────────────────

@router.get("/nodes")
def list_nodes():
    """List all network nodes with summary risk data."""
    store = DataStore.get()
    G = store.get_graph()
    shipments = store.get_shipments()
    disruptions = store.get_disruptions()

    nodes = []
    for city, info in CITIES.items():
        # Count shipments through this city
        city_shipments = [
            s for s in shipments
            if s.origin.city == city or s.destination.city == city
        ]
        # Active disruptions at this city
        city_disruptions = [
            d for d in disruptions
            if d.location.city == city and d.status == "active"
        ]

        # Aggregate risk
        avg_risk = sum(s.risk_score for s in city_shipments) / max(len(city_shipments), 1)

        # Festival impact
        festival = get_festival_congestion_for_city(city)

        # Degree centrality (bottleneck indicator)
        degree = G.degree(city) if city in G.nodes else 0

        nodes.append({
            "city": city,
            "state": info["state"],
            "lat": info["lat"],
            "lng": info["lng"],
            "shipment_count": len(city_shipments),
            "disruption_count": len(city_disruptions),
            "avg_risk_score": round(avg_risk, 1),
            "risk_level": _risk_level(avg_risk).value,
            "festival_congestion": festival["congestion"],
            "active_festivals": [f["name"] for f in festival["festivals"]],
            "is_peak_season": festival["is_peak_season"],
            "monsoon": festival["monsoon"],
            "degree": degree,
            "is_bottleneck": degree > 8,
        })

    nodes.sort(key=lambda n: n["shipment_count"], reverse=True)
    return nodes


# ─── GET /nodes/{city}/risk ───────────────────────────────────────────────────

@router.get("/nodes/{city}/risk")
def get_node_risk(city: str):
    """Detailed risk analysis for a port/city/node."""
    if city not in CITIES:
        raise HTTPException(404, f"City not found: {city}. Available: {list(CITIES.keys())}")

    store = DataStore.get()
    G = store.get_graph()
    shipments = store.get_shipments()
    disruptions = store.get_disruptions()
    info = CITIES[city]

    # Shipments passing through
    city_shipments = [s for s in shipments if s.origin.city == city or s.destination.city == city]
    city_disruptions = [d for d in disruptions if d.location.city == city and d.status == "active"]

    # Risk factors for this node
    factors = []

    # 1. Weather
    weather_cache = getattr(store, '_weather_cache', {})
    wx = weather_cache.get(city, {})
    if wx.get("severity", 0) > 0.05:
        factors.append(RiskFactor(
            name="Weather conditions",
            contribution=round(wx["severity"] * 0.4, 2),
            detail=f"Live: {wx.get('description', 'conditions')} (severity: {wx['severity']:.0%})"
        ))

    # 2. Festival/seasonal
    festival = get_festival_congestion_for_city(city)
    if festival["congestion"] > 0:
        detail_parts = [f["name"] for f in festival["festivals"]]
        if festival["monsoon"]:
            detail_parts.append("Monsoon season")
        if festival["ecommerce"]:
            detail_parts.append(festival["ecommerce"]["name"])
        factors.append(RiskFactor(
            name="Festival/seasonal congestion",
            contribution=round(festival["congestion"] * 0.4, 2),
            detail=", ".join(detail_parts) if detail_parts else "Seasonal impact"
        ))

    # 3. Disaster proximity
    disaster_feed = getattr(store, '_disaster_feed', [])
    for d in disaster_feed:
        dist_km = _haversine_km(info["lat"], info["lng"], d.get("lat", 0), d.get("lng", 0))
        if dist_km < 500:
            factors.append(RiskFactor(
                name="Active disaster",
                contribution=round(d.get("severity", 0.3) * 0.5, 2),
                detail=f"{d['title']} ({dist_km:.0f} km away)"
            ))

    # 4. Congestion/bottleneck
    degree = G.degree(city) if city in G.nodes else 0
    if degree > 6:
        factors.append(RiskFactor(
            name="Hub bottleneck",
            contribution=round(min(degree / 30, 0.3), 2),
            detail=f"{degree} active connections — high-traffic node"
        ))

    # 5. Carrier diversity at this node
    carriers_at_node = set(s.carrier for s in city_shipments)
    if len(carriers_at_node) <= 2 and len(city_shipments) > 3:
        factors.append(RiskFactor(
            name="Low carrier diversity",
            contribution=0.15,
            detail=f"Only {len(carriers_at_node)} carriers serve this node"
        ))

    # 6. Active disruptions
    for d in city_disruptions:
        factors.append(RiskFactor(
            name=f"Active disruption: {d.type}",
            contribution=round(d.severity * 0.5, 2),
            detail=d.title
        ))

    # Compute aggregate risk
    total_risk = sum(f.contribution for f in factors) * 100
    risk_score = round(min(max(total_risk, 5.0), 95.0), 1)

    # Bottleneck score: how critical this node is to the network
    if city in G.nodes:
        try:
            centrality = nx.betweenness_centrality(G)
            bottleneck_score = round(centrality.get(city, 0) * 100, 1)
        except Exception:
            bottleneck_score = round(degree / max(len(G.nodes), 1) * 100, 1)
    else:
        bottleneck_score = 0.0

    # Throughput rank
    all_cities_by_shipments = sorted(
        [(c, sum(1 for s in shipments if s.origin.city == c or s.destination.city == c)) for c in CITIES],
        key=lambda x: x[1], reverse=True
    )
    rank = next((i + 1 for i, (c, _) in enumerate(all_cities_by_shipments) if c == city), len(CITIES))

    # Compute a simple resilience score for this node
    resilience_score = round(max(0, min(100, 100 - risk_score + (degree * 2) - (len(city_disruptions) * 10))), 1)

    return {
        "city": city,
        "state": info["state"],
        "lat": info["lat"],
        "lng": info["lng"],
        "total_shipments_through": len(city_shipments),
        "shipments": [{"id": s.id, "route": f"{s.origin.city}→{s.destination.city}", "risk_score": s.risk_score, "status": s.status, "carrier": s.carrier, "revenue": s.revenue} for s in city_shipments],
        "active_disruptions": [{"id": d.id, "title": d.title, "severity": d.severity, "type": d.type} for d in city_disruptions],
        "risk_score": risk_score,
        "risk_level": _risk_level(risk_score).value,
        "risk_factors": [f.model_dump() for f in factors],
        "weather": wx,
        "festival_impact": festival,
        "resilience_score": resilience_score,
        "bottleneck_score": bottleneck_score,
        "throughput_rank": rank,
        "degree": degree,
        "carriers": list(carriers_at_node),
    }


# ─── POST /simulate/node ─────────────────────────────────────────────────────

@router.post("/simulate/node")
def simulate_node_disruption(req: SimulateNodeRequest):
    """
    What-if simulation for ANY node. Shows cascade, affected shipments,
    revenue at risk, and recommendations.
    """
    store = DataStore.get()
    G = store.get_graph()

    if req.node not in CITIES and req.node not in G.nodes:
        raise HTTPException(404, f"Node not found: {req.node}. Available: {list(CITIES.keys())}")

    # Run cascade
    cascade_result = compute_cascade(
        G=G,
        disrupted_node=req.node,
        severity=req.severity,
        disruption_type=req.disruption_type.value,
        disruption_id=f"SIM-{uuid.uuid4().hex[:8].upper()}",
        time_horizon_hours=req.duration_hours * 2,
    )

    # Find affected shipments
    shipments = store.get_shipments()
    affected = [
        s for s in shipments
        if s.origin.city == req.node or s.destination.city == req.node
    ]
    affected_ids = [s.id for s in affected]
    revenue_at_risk = sum(s.revenue for s in affected)

    # Count alternative routes available
    alt_routes = 0
    for s in affected[:5]:
        try:
            routes_resp = optimize_routes(s, active_disruptions=store.get_disruptions())
            alt_routes += len([r for r in routes_resp.alternatives if r.risk_score < 50])
        except Exception:
            pass

    # Generate recommendations
    recommendations = []
    if len(affected) > 0:
        recommendations.append(
            f"Reroute {len(affected)} shipments through alternative corridors to avoid {req.node}"
        )
    if req.severity > 0.7:
        recommendations.append(
            f"High severity ({req.severity:.0%}): Consider air freight for critical shipments"
        )
    if alt_routes > 0:
        recommendations.append(
            f"{alt_routes} low-risk alternative routes available — activate rerouting"
        )

    festival = get_festival_congestion_for_city(req.node)
    if festival["is_peak_season"]:
        recommendations.append(
            f"Peak season at {req.node}: Pre-position inventory and secure backup carriers"
        )

    disruption_types = {
        "congestion": f"Deploy traffic management at {req.node}; stagger shipment timings",
        "port_closure": f"Divert to nearest alternate port; activate inland container depots",
        "weather": f"Monitor weather forecast; prepare for 24-48h delay buffer",
        "road_block": f"Use alternate highways; consider rail freight for bulk shipments",
        "carrier_failure": f"Activate backup carrier agreements; redistribute volume across available carriers",
        "strike": f"Engage backup workforce or third-party labor at {req.node}; pre-negotiate with unions",
        "infrastructure": f"Redirect via alternate infrastructure corridors; assess structural damage timeline",
        "flood": f"Activate waterproof packaging; reroute through elevated corridors away from {req.node}",
        "earthquake": f"Pause operations at {req.node} until structural assessment; activate emergency rerouting",
        "cyber_attack": f"Activate manual tracking fallback; engage cybersecurity response team at {req.node}",
    }
    if req.disruption_type.value in disruption_types:
        recommendations.append(disruption_types[req.disruption_type.value])

    cascade_dict = cascade_to_dict(cascade_result)

    return {
        "node": req.node,
        "disruption_type": req.disruption_type.value,
        "severity": req.severity,
        "duration_hours": req.duration_hours,
        "cascade": cascade_dict,
        "affected_shipments": [
            {"id": s.id, "route": f"{s.origin.city}→{s.destination.city}", "risk_score": s.risk_score, "revenue": s.revenue}
            for s in affected
        ],
        "revenue_at_risk": round(revenue_at_risk),
        "alternative_routes_available": alt_routes,
        "recommendations": recommendations,
        "festival_impact": festival,
    }


# ─── GET /festivals ──────────────────────────────────────────────────────────

@router.get("/festivals")
def get_festivals(days_ahead: int = Query(30, ge=1, le=365)):
    """Upcoming Indian festivals with logistics congestion impact."""
    return {
        "upcoming": get_upcoming_festivals(days_ahead),
        "active_today": get_active_festivals(),
        "ecommerce_surge": get_ecommerce_surge(),
        "monsoon": is_monsoon(),
    }


# ─── GET /festivals/impact ───────────────────────────────────────────────────

@router.get("/festivals/impact")
def get_festival_impact():
    """Festival/seasonal congestion impact for all cities right now."""
    impacts = {}
    for city in CITIES:
        impacts[city] = get_festival_congestion_for_city(city)
    return impacts


# Need to import networkx for betweenness_centrality
import networkx as nx
