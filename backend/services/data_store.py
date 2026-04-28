"""
In-memory data store with LIVE data integration.

Loads data from real sources at startup:
- Weather conditions from OpenWeatherMap API (free)
- Disaster events from GDACS + ReliefWeb (free, no API key)
- Risk scores computed dynamically from live weather + ML model

Falls back to estimated/heuristic data if APIs are unreachable.
Design pattern: Repository pattern — all data access goes through this module.
"""

from __future__ import annotations
import os
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import random
import networkx as nx

from models.schemas import (
    Shipment, Disruption, Carrier, Alert, Route, RouteWaypoint,
    Location, LatLng, RiskFactor, CascadeSummary,
    ShipmentStatus, RiskLevel, DisruptionType
)

logger = logging.getLogger(__name__)

# ─── Seed random (deterministic for consistent demo) ──────────────────────────
random.seed(42)

NOW = datetime.now(timezone.utc)

# ─── City coordinates (India) ─────────────────────────────────────────────────
CITIES: Dict[str, dict] = {
    "Mumbai": {"state": "Maharashtra", "lat": 19.0760, "lng": 72.8777},
    "Delhi": {"state": "Delhi", "lat": 28.6139, "lng": 77.2090},
    "Chennai": {"state": "Tamil Nadu", "lat": 13.0827, "lng": 80.2707},
    "Kolkata": {"state": "West Bengal", "lat": 22.5726, "lng": 88.3639},
    "Bangalore": {"state": "Karnataka", "lat": 12.9716, "lng": 77.5946},
    "Hyderabad": {"state": "Telangana", "lat": 17.3850, "lng": 78.4867},
    "Pune": {"state": "Maharashtra", "lat": 18.5204, "lng": 73.8567},
    "Ahmedabad": {"state": "Gujarat", "lat": 23.0225, "lng": 72.5714},
    "Jaipur": {"state": "Rajasthan", "lat": 26.9124, "lng": 75.7873},
    "Lucknow": {"state": "Uttar Pradesh", "lat": 26.8467, "lng": 80.9462},
    "Surat": {"state": "Gujarat", "lat": 21.1702, "lng": 72.8311},
    "Nagpur": {"state": "Maharashtra", "lat": 21.1458, "lng": 79.0882},
    "Nhava Sheva": {"state": "Maharashtra", "lat": 18.9500, "lng": 72.9400},
    "Coimbatore": {"state": "Tamil Nadu", "lat": 11.0168, "lng": 76.9558},
    "Bhopal": {"state": "Madhya Pradesh", "lat": 23.2599, "lng": 77.4126},
    "Kochi": {"state": "Kerala", "lat": 9.9312, "lng": 76.2673},
    "Chandigarh": {"state": "Punjab", "lat": 30.7333, "lng": 76.7794},
    "Patna": {"state": "Bihar", "lat": 25.5941, "lng": 85.1376},
    "Indore": {"state": "Madhya Pradesh", "lat": 22.7196, "lng": 75.8577},
    "Visakhapatnam": {"state": "Andhra Pradesh", "lat": 17.6868, "lng": 83.2185},
}

CARRIERS_DATA = [
    {"id": "C001", "name": "BlueDart", "on_time_rate": 0.94, "avg_delay_hours": 2.1, "total_shipments": 45200, "risk_score": 12, "trend": "stable"},
    {"id": "C002", "name": "Delhivery", "on_time_rate": 0.89, "avg_delay_hours": 4.3, "total_shipments": 78400, "risk_score": 24, "trend": "improving"},
    {"id": "C003", "name": "DTDC", "on_time_rate": 0.85, "avg_delay_hours": 6.2, "total_shipments": 34100, "risk_score": 31, "trend": "stable"},
    {"id": "C004", "name": "FedEx India", "on_time_rate": 0.97, "avg_delay_hours": 1.2, "total_shipments": 22300, "risk_score": 8, "trend": "improving"},
    {"id": "C005", "name": "DHL Express", "on_time_rate": 0.96, "avg_delay_hours": 1.5, "total_shipments": 18900, "risk_score": 9, "trend": "stable"},
    {"id": "C006", "name": "Ecom Express", "on_time_rate": 0.82, "avg_delay_hours": 8.1, "total_shipments": 56700, "risk_score": 38, "trend": "declining"},
    {"id": "C007", "name": "Shadowfax", "on_time_rate": 0.78, "avg_delay_hours": 10.4, "total_shipments": 29800, "risk_score": 45, "trend": "declining"},
    {"id": "C008", "name": "XpressBees", "on_time_rate": 0.87, "avg_delay_hours": 5.1, "total_shipments": 41600, "risk_score": 27, "trend": "stable"},
]

CATEGORIES = ["Electronics", "Pharmaceuticals", "FMCG", "Apparel", "Automotive", "Industrial", "Food & Beverage"]
SHIPPING_MODES = ["Standard Class", "Second Class", "First Class", "Same Day"]
RETAILERS = ["BigBasket", "Flipkart", "DMart", "Reliance Retail", "Amazon", "Myntra", "Swiggy", "Zomato", "Meesho", "Nykaa"]


def _loc(city: str) -> Location:
    c = CITIES[city]
    return Location(city=city, state=c["state"], lat=c["lat"], lng=c["lng"])


def _midpoint(a: Location, b: Location) -> LatLng:
    return LatLng(lat=(a.lat + b.lat) / 2, lng=(a.lng + b.lng) / 2)


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Approximate distance in km between two lat/lng points."""
    import math
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _route(origin: Location, destination: Location, mode: str) -> Route:
    dist = _haversine_km(origin.lat, origin.lng, destination.lat, destination.lng) * 1.3  # road factor
    speed_map = {"Standard Class": 55, "Second Class": 65, "First Class": 700, "Same Day": 45}
    speed = speed_map.get(mode, 55)
    hours = dist / speed
    mid = _midpoint(origin, destination)
    return Route(
        distance_km=round(dist, 1),
        estimated_hours=round(hours, 1),
        waypoints=[
            RouteWaypoint(lat=origin.lat, lng=origin.lng, name=origin.city),
            RouteWaypoint(lat=mid.lat, lng=mid.lng),
            RouteWaypoint(lat=destination.lat, lng=destination.lng, name=destination.city),
        ],
    )


def _risk_factors_for(score: float, carrier_name: str, mode: str, is_disruption_zone: bool = False) -> List[RiskFactor]:
    factors = []
    if is_disruption_zone:
        factors.append(RiskFactor(name="Active disruption on route", contribution=0.45, detail="Port congestion causing delays"))
    else:
        weather_c = round(random.uniform(0.05, 0.25), 2)
        factors.append(RiskFactor(name="Weather conditions", contribution=weather_c, detail="Moderate conditions on route"))

    carrier_map = {"BlueDart": 0.06, "FedEx India": 0.04, "DHL Express": 0.05, "Delhivery": 0.15, "DTDC": 0.22, "Ecom Express": 0.28, "Shadowfax": 0.35, "XpressBees": 0.18}
    late_rate = carrier_map.get(carrier_name, 0.15)
    factors.append(RiskFactor(name="Carrier reliability", contribution=round(late_rate, 2), detail=f"{carrier_name}: {round((1 - late_rate) * 100)}% on-time rate"))

    mode_risk = {"Standard Class": 0.20, "Second Class": 0.14, "First Class": 0.05, "Same Day": 0.08}
    factors.append(RiskFactor(name="Route congestion history", contribution=mode_risk.get(mode, 0.15), detail=f"Historical delay rate on this lane"))

    return factors[:3]


def _risk_level(score: float) -> RiskLevel:
    if score >= 75:
        return RiskLevel.CRITICAL
    elif score >= 55:
        return RiskLevel.HIGH
    elif score >= 35:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


# ─── Seed data builder ────────────────────────────────────────────────────────

def _build_demo_shipments() -> Dict[str, Shipment]:
    shipments: Dict[str, Shipment] = {}

    # ── Demo shipments for Mumbai Port disruption cascade ──────────────────────
    demo_cascade = [
        ("SH001", "Mumbai", "Nhava Sheva", "Delhivery", "Standard Class", 89.0, ShipmentStatus.DISRUPTED, "FMCG", 124000, "BigBasket"),
        ("SH002", "Mumbai", "Delhi", "BlueDart", "First Class", 76.0, ShipmentStatus.DISRUPTED, "Electronics", 87000, "Flipkart"),
        ("SH003", "Mumbai", "Pune", "DTDC", "Standard Class", 68.0, ShipmentStatus.AT_RISK, "Pharmaceuticals", 62000, "Pune DC"),
        ("SH004", "Pune", "Nagpur", "Ecom Express", "Second Class", 62.0, ShipmentStatus.AT_RISK, "FMCG", 41000, "DMart"),
        ("SH005", "Pune", "Surat", "Shadowfax", "Standard Class", 57.0, ShipmentStatus.AT_RISK, "Apparel", 28000, "Reliance Retail"),
    ]

    for sid, orig, dest, carrier, mode, risk, status, cat, rev, retailer in demo_cascade:
        origin = _loc(orig)
        destination = _loc(dest)
        eta_delta = timedelta(hours=risk / 4)
        is_disrupted = risk > 65
        sh = Shipment(
            id=sid,
            order_id=f"ORD-{sid}",
            origin=origin,
            destination=destination,
            current_position=_midpoint(origin, destination),
            status=status,
            risk_score=risk,
            risk_level=_risk_level(risk),
            risk_factors=_risk_factors_for(risk, carrier, mode, is_disrupted),
            confidence=0.88 if is_disrupted else 0.74,
            shipping_mode=mode,
            carrier=carrier,
            eta=NOW + eta_delta + timedelta(hours=18 if is_disrupted else 8),
            original_eta=NOW + timedelta(hours=6),
            deadline=NOW + timedelta(hours=30),
            revenue=float(rev),
            category=cat,
            route=_route(origin, destination, mode),
            updated_at=NOW,
        )
        shipments[sid] = sh

    # ── NH-48 disruption shipments ─────────────────────────────────────────────
    nh48_cascade = [
        ("SH006", "Mumbai", "Bangalore", "Delhivery", "Standard Class", 71.0, ShipmentStatus.DISRUPTED, "FMCG", 82000, "Swiggy"),
        ("SH007", "Pune", "Hyderabad", "DTDC", "Second Class", 64.0, ShipmentStatus.AT_RISK, "Electronics", 55000, "Amazon"),
        ("SH008", "Ahmedabad", "Bangalore", "XpressBees", "Standard Class", 58.0, ShipmentStatus.AT_RISK, "Apparel", 38000, "Myntra"),
    ]

    for sid, orig, dest, carrier, mode, risk, status, cat, rev, retailer in nh48_cascade:
        origin = _loc(orig)
        destination = _loc(dest)
        eta_delta = timedelta(hours=risk / 5)
        is_disrupted = risk > 65
        sh = Shipment(
            id=sid,
            order_id=f"ORD-{sid}",
            origin=origin,
            destination=destination,
            current_position=_midpoint(origin, destination),
            status=status,
            risk_score=risk,
            risk_level=_risk_level(risk),
            risk_factors=_risk_factors_for(risk, carrier, mode, is_disrupted),
            confidence=0.82 if is_disrupted else 0.69,
            shipping_mode=mode,
            carrier=carrier,
            eta=NOW + eta_delta + timedelta(hours=12 if is_disrupted else 6),
            original_eta=NOW + timedelta(hours=4),
            deadline=NOW + timedelta(hours=28),
            revenue=float(rev),
            category=cat,
            route=_route(origin, destination, mode),
            updated_at=NOW,
        )
        shipments[sid] = sh

    # ── 42 additional shipments (varied risk) ─────────────────────────────────
    city_pairs = [
        ("Delhi", "Lucknow"), ("Bangalore", "Chennai"), ("Hyderabad", "Kochi"),
        ("Kolkata", "Patna"), ("Jaipur", "Delhi"), ("Chennai", "Coimbatore"),
        ("Ahmedabad", "Surat"), ("Bhopal", "Indore"), ("Chandigarh", "Delhi"),
        ("Nagpur", "Hyderabad"), ("Lucknow", "Kolkata"), ("Kochi", "Coimbatore"),
        ("Delhi", "Jaipur"), ("Surat", "Mumbai"), ("Patna", "Kolkata"),
        ("Coimbatore", "Bangalore"), ("Indore", "Bhopal"), ("Visakhapatnam", "Hyderabad"),
        ("Mumbai", "Ahmedabad"), ("Chennai", "Hyderabad"), ("Delhi", "Chandigarh"),
        ("Bangalore", "Kochi"), ("Hyderabad", "Nagpur"), ("Kolkata", "Bhopal"),
        ("Jaipur", "Ahmedabad"), ("Lucknow", "Delhi"), ("Chennai", "Visakhapatnam"),
        ("Pune", "Indore"), ("Mumbai", "Nagpur"), ("Delhi", "Patna"),
        ("Bangalore", "Hyderabad"), ("Ahmedabad", "Jaipur"), ("Surat", "Nagpur"),
        ("Kolkata", "Lucknow"), ("Chennai", "Kochi"), ("Hyderabad", "Visakhapatnam"),
        ("Mumbai", "Coimbatore"), ("Delhi", "Bhopal"), ("Bangalore", "Coimbatore"),
        ("Patna", "Chandigarh"), ("Indore", "Jaipur"), ("Nagpur", "Bhopal"),
    ]

    carrier_list = [c["name"] for c in CARRIERS_DATA]
    for i, (orig, dest) in enumerate(city_pairs):
        sid = f"SH{str(i + 9).zfill(3)}"
        carrier = carrier_list[i % len(carrier_list)]
        mode = SHIPPING_MODES[i % len(SHIPPING_MODES)]
        # Weight towards lower risk for most shipments
        if i < 28:
            risk = round(random.uniform(5, 35), 1)
            status = ShipmentStatus.ON_TRACK
        elif i < 36:
            risk = round(random.uniform(36, 60), 1)
            status = ShipmentStatus.AT_RISK
        else:
            risk = round(random.uniform(61, 80), 1)
            status = ShipmentStatus.DISRUPTED

        origin = _loc(orig)
        destination = _loc(dest)
        cat = CATEGORIES[i % len(CATEGORIES)]
        rev = float(random.randint(15000, 180000))

        sh = Shipment(
            id=sid,
            order_id=f"ORD-{sid}",
            origin=origin,
            destination=destination,
            current_position=_midpoint(origin, destination),
            status=status,
            risk_score=risk,
            risk_level=_risk_level(risk),
            risk_factors=_risk_factors_for(risk, carrier, mode),
            confidence=round(random.uniform(0.65, 0.95), 2),
            shipping_mode=mode,
            carrier=carrier,
            eta=NOW + timedelta(hours=random.randint(4, 72)),
            original_eta=NOW + timedelta(hours=random.randint(3, 48)),
            deadline=NOW + timedelta(hours=random.randint(24, 96)),
            revenue=rev,
            category=cat,
            route=_route(origin, destination, mode),
            updated_at=NOW - timedelta(minutes=random.randint(1, 300)),
        )
        shipments[sid] = sh

    return shipments


def _build_disruptions(shipments: Dict[str, Shipment]) -> Dict[str, Disruption]:
    cascade_mumbai = CascadeSummary(
        total_shipments=5,
        total_retailers=4,
        revenue_at_risk=342000.0,
        customers_affected=6670,
        max_delay_hours=36.0,
    )
    cascade_nh48 = CascadeSummary(
        total_shipments=3,
        total_retailers=3,
        revenue_at_risk=175000.0,
        customers_affected=2850,
        max_delay_hours=24.0,
    )

    d1 = Disruption(
        id="DIS001",
        type=DisruptionType.CONGESTION,
        title="Mumbai Port Congestion",
        location=_loc("Mumbai"),
        severity=0.85,
        status="active",
        detected_at=NOW - timedelta(hours=2),
        estimated_end=NOW + timedelta(hours=22),
        cascade=cascade_mumbai,
        affected_shipment_ids=["SH001", "SH002", "SH003", "SH004", "SH005"],
        mitigation_applied=False,
        created_at=NOW - timedelta(hours=2),
    )
    d2 = Disruption(
        id="DIS002",
        type=DisruptionType.WEATHER,
        title="NH-48 Weather Warning",
        location=Location(city="NH-48 Corridor", state="Maharashtra", lat=18.2, lng=73.2),
        severity=0.6,
        status="active",
        detected_at=NOW - timedelta(hours=5),
        estimated_end=NOW + timedelta(hours=19),
        cascade=cascade_nh48,
        affected_shipment_ids=["SH006", "SH007", "SH008"],
        mitigation_applied=False,
        created_at=NOW - timedelta(hours=5),
    )
    return {d1.id: d1, d2.id: d2}


def _build_carriers() -> Dict[str, Carrier]:
    carriers = {}
    for c in CARRIERS_DATA:
        carrier = Carrier(**c)
        carriers[carrier.id] = carrier
    return carriers


def _build_alerts(shipments: Dict[str, Shipment]) -> Dict[str, Alert]:
    alerts: Dict[str, Alert] = {}
    alert_data = [
        ("ALT001", "disruption_detected", "critical", "Mumbai Port Congestion Detected",
         "High severity congestion at Mumbai Port. 5 shipments at risk. ₹3.42L revenue exposed.", None, "DIS001"),
        ("ALT002", "risk_threshold", "warning", "Shipment SH001 Critical Risk",
         "SH001 to BigBasket crossed CRITICAL threshold (89/100). Immediate action required.", "SH001", "DIS001"),
        ("ALT003", "risk_threshold", "warning", "NH-48 Weather Alert",
         "3 shipments on NH-48 corridor flagged as HIGH risk due to weather.", None, "DIS002"),
        ("ALT004", "disruption_detected", "warning", "NH-48 Weather Warning Active",
         "Moderate weather conditions affecting NH-48. Expected duration: 24 hours.", None, "DIS002"),
        ("ALT005", "auto_reroute", "info", "SH009 Auto-Rerouted",
         "Shipment SH009 automatically rerouted via alternate highway. Cost delta: +2%.", "SH009", None),
    ]
    for i, (aid, atype, sev, title, msg, ship_id, dis_id) in enumerate(alert_data):
        a = Alert(
            id=aid, type=atype, severity=sev, title=title, message=msg,
            shipment_id=ship_id, disruption_id=dis_id, read=i > 2,
            created_at=NOW - timedelta(hours=5 - i),
        )
        alerts[aid] = a
    return alerts


def _build_supply_chain_graph(shipments: Dict[str, Shipment]) -> nx.DiGraph:
    """
    Build a directed graph of the supply chain.
    Nodes: cities (hubs, warehouses, DCs, retailers)
    Edges: routes between them, weighted by dependency + delay risk
    """
    G = nx.DiGraph()

    # Add all origin/destination cities as nodes
    city_revenue: Dict[str, float] = {}
    city_customers: Dict[str, int] = {}

    for s in shipments.values():
        for city in [s.origin.city, s.destination.city]:
            if city not in G.nodes:
                c = CITIES.get(city, {"lat": 20.0, "lng": 77.0})
                G.add_node(city, lat=c["lat"], lng=c["lng"], revenue=0.0, customers=0)
            G.nodes[city]["revenue"] = G.nodes[city].get("revenue", 0) + s.revenue / 2
            G.nodes[city]["customers"] = G.nodes[city].get("customers", 0) + random.randint(50, 500)

    # Add edges for each shipment route
    for s in shipments.values():
        orig = s.origin.city
        dest = s.destination.city
        G.add_edge(
            orig, dest,
            shipment_id=s.id,
            dependency_weight=0.7 + (s.risk_score / 1000),
            avg_transit_hours=s.route.estimated_hours,
            late_rate=s.risk_score / 100,
            revenue=s.revenue,
        )

    return G


# ─── Global state (singleton) ─────────────────────────────────────────────────

class DataStore:
    """Singleton in-memory data store with live data integration."""

    _instance: Optional["DataStore"] = None

    def __init__(self):
        logger.info("Initializing DataStore with live data sources...")

        # ── Import real data loader ────────────────────────────────────────────
        from services.real_data_loader import (
            build_live_shipments, build_live_disruptions, build_live_alerts,
            _get_city_weather_cache, CARRIERS_DATA as LIVE_CARRIERS,
        )
        from services.disruption_feed import fetch_disruptions_sync

        # ── Step 1: Fetch live weather for all cities ──────────────────────────
        logger.info("Fetching live weather data for 20 Indian cities...")
        self._weather_cache = _get_city_weather_cache()
        live_cities = sum(1 for wx in self._weather_cache.values() if wx.get("is_live", False))
        logger.info(f"Weather data ready: {live_cities}/{len(self._weather_cache)} cities with live data")

        # ── Step 2: Fetch real disaster/disruption events ──────────────────────
        logger.info("Fetching real disaster events from GDACS/ReliefWeb...")
        self._disaster_feed = fetch_disruptions_sync()
        live_disasters = sum(1 for d in self._disaster_feed if d.get("is_live", False))
        logger.info(f"Disaster feed ready: {len(self._disaster_feed)} events ({live_disasters} live)")

        # ── Step 3: Build shipments with REAL weather + disaster context ───────
        logger.info("Building shipments with live risk factors...")
        self.shipments: Dict[str, Shipment] = build_live_shipments(
            self._weather_cache, self._disaster_feed
        )

        # ── Step 4: Build disruptions from REAL sources ────────────────────────
        self.disruptions: Dict[str, Disruption] = build_live_disruptions(
            self.shipments, self._weather_cache, self._disaster_feed
        )

        # ── Step 5: Build alerts from real disruptions ─────────────────────────
        self.alerts: Dict[str, Alert] = build_live_alerts(self.shipments, self.disruptions)

        # ── Step 6: Carriers + Graph ───────────────────────────────────────────
        self.carriers: Dict[str, Carrier] = _build_carriers()
        self.graph: nx.DiGraph = _build_supply_chain_graph(self.shipments)
        self._resilience_trend: List[float] = [72.0, 75.0, 74.0, 76.0, 78.0]
        self._mitigated_today: int = 19
        self._revenue_saved: float = 248000.0

        # ── Summary ───────────────────────────────────────────────────────────
        disrupted = sum(1 for s in self.shipments.values() if s.status == ShipmentStatus.DISRUPTED)
        at_risk = sum(1 for s in self.shipments.values() if s.status == ShipmentStatus.AT_RISK)

        # ── Step 7: Assign initial priorities and rescore ──────────────────────
        self.rescore_all_shipments()

        logger.info(
            f"DataStore ready: {len(self.shipments)} shipments "
            f"({disrupted} disrupted, {at_risk} at risk), "
            f"{len(self.disruptions)} disruptions, {len(self.alerts)} alerts"
        )

    @classmethod
    def get(cls) -> "DataStore":
        if cls._instance is None:
            cls._instance = DataStore()
        return cls._instance

    def reset(self) -> None:
        """Reset to fresh demo state (useful for tests)."""
        DataStore._instance = DataStore()

    # ── Shipments ──────────────────────────────────────────────────────────────

    def get_shipments(
        self,
        status: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[Shipment]:
        ships = list(self.shipments.values())
        if status:
            ships = [s for s in ships if s.status == status]
        ships.sort(key=lambda s: s.risk_score, reverse=True)
        return ships[offset: offset + limit]

    def get_shipment(self, shipment_id: str) -> Optional[Shipment]:
        return self.shipments.get(shipment_id)

    def update_shipment(self, shipment: Shipment) -> Shipment:
        shipment.updated_at = datetime.now(timezone.utc)
        self.shipments[shipment.id] = shipment
        return shipment

    def delete_shipment(self, shipment_id: str) -> bool:
        if shipment_id in self.shipments:
            del self.shipments[shipment_id]
            # Remove from disruption affected lists
            for d in self.disruptions.values():
                if shipment_id in d.affected_shipment_ids:
                    d.affected_shipment_ids.remove(shipment_id)
            return True
        return False

    def rescore_all_shipments(self) -> None:
        """Re-score all shipments using the live risk scorer and update priorities."""
        from services.risk_scorer import score_shipment
        now = datetime.now(timezone.utc)
        to_delete = []
        for sid, s in self.shipments.items():
            # Auto-remove delivered shipments
            if s.status == ShipmentStatus.DELIVERED or s.status == "delivered":
                to_delete.append(sid)
                continue
            # Re-score risk
            result = score_shipment(s)
            s.risk_score = result.risk_score
            s.risk_level = result.risk_level
            s.risk_factors = result.top_factors
            s.confidence = result.confidence
            # Check if overdue
            try:
                overdue = s.deadline < now
            except Exception:
                overdue = False
            # Assign priority based on risk + deadline
            level_str = result.risk_level.value if hasattr(result.risk_level, 'value') else str(result.risk_level)
            if overdue or level_str == "CRITICAL":
                s.priority = "critical"
            elif level_str == "HIGH":
                s.priority = "high"
            elif level_str == "MEDIUM":
                s.priority = "medium"
            else:
                s.priority = "low"
            s.updated_at = now
        for sid in to_delete:
            del self.shipments[sid]

    # ── Disruptions ───────────────────────────────────────────────────────────

    def get_disruptions(self, status: Optional[str] = None) -> List[Disruption]:
        disruptions = list(self.disruptions.values())
        if status:
            disruptions = [d for d in disruptions if d.status == status]
        disruptions.sort(key=lambda d: d.severity, reverse=True)
        return disruptions

    def get_disruption(self, disruption_id: str) -> Optional[Disruption]:
        return self.disruptions.get(disruption_id)

    def add_disruption(self, disruption: Disruption) -> Disruption:
        self.disruptions[disruption.id] = disruption
        return disruption

    def update_disruption(self, disruption: Disruption) -> Disruption:
        self.disruptions[disruption.id] = disruption
        return disruption

    # ── Carriers ──────────────────────────────────────────────────────────────

    def get_carriers(self) -> List[Carrier]:
        return list(self.carriers.values())

    def get_carrier_by_name(self, name: str) -> Optional[Carrier]:
        for c in self.carriers.values():
            if c.name == name:
                return c
        return None

    # ── Alerts ────────────────────────────────────────────────────────────────

    def get_alerts(self, unread_only: bool = False) -> List[Alert]:
        alerts = list(self.alerts.values())
        if unread_only:
            alerts = [a for a in alerts if not a.read]
        alerts.sort(key=lambda a: a.created_at, reverse=True)
        return alerts

    def mark_alert_read(self, alert_id: str) -> bool:
        if alert_id in self.alerts:
            self.alerts[alert_id].read = True
            return True
        return False

    def add_alert(self, alert: Alert) -> Alert:
        self.alerts[alert.id] = alert
        return alert

    # ── KPIs ──────────────────────────────────────────────────────────────────

    def get_kpis(self) -> dict:
        ships = list(self.shipments.values())
        # at_risk = shipments with risk level above LOW (MEDIUM, HIGH, CRITICAL)
        at_risk = [s for s in ships if s.risk_level not in (RiskLevel.LOW, "LOW")]
        revenue_at_risk = sum(s.revenue for s in at_risk)
        # disrupted = total unique shipments affected by active disruptions
        active_disruptions = [d for d in self.disruptions.values() if d.status == "active"]
        disrupted_ids: set = set()
        for d in active_disruptions:
            disrupted_ids.update(d.affected_shipment_ids)
        disrupted_count = len(disrupted_ids)
        # Use dynamically computed resilience score
        from services.resilience_engine import compute_resilience
        res = compute_resilience(self.graph, ships, list(self.disruptions.values()), self._resilience_trend)
        return {
            "active_shipments": len(ships),
            "at_risk_count": len(at_risk),
            "disrupted_count": disrupted_count,
            "revenue_at_risk": round(revenue_at_risk),
            "resilience_score": res.score,
            "auto_mitigated_today": self._mitigated_today,
            "revenue_saved_today": self._revenue_saved,
        }

    # ── Graph ─────────────────────────────────────────────────────────────────

    def get_graph(self) -> nx.DiGraph:
        return self.graph

    def rebuild_graph(self) -> None:
        self.graph = _build_supply_chain_graph(self.shipments)

    # ── Resilience trend ──────────────────────────────────────────────────────

    def get_resilience_trend(self) -> List[float]:
        return self._resilience_trend

    def append_resilience(self, score: float) -> None:
        self._resilience_trend.append(round(score, 1))
        if len(self._resilience_trend) > 10:
            self._resilience_trend = self._resilience_trend[-10:]


# Convenience accessor
def get_store() -> DataStore:
    return DataStore.get()
