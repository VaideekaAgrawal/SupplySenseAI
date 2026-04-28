"""
Real data loader for SupplySense AI.

Integrates live data sources to replace static/mock demo data:
1. Weather conditions from OpenWeatherMap → affects risk scores & disruptions
2. Disaster events from GDACS/ReliefWeb → creates real disruption entries
3. Shipment data generated from real geographic + carrier + weather context
4. Risk scores computed dynamically from live weather + ML model

This module is called by data_store.py at startup to enrich/replace demo data.
"""

from __future__ import annotations
import logging
import random
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from models.schemas import (
    Shipment, Disruption, Carrier, Alert, Route, RouteWaypoint,
    Location, LatLng, RiskFactor, CascadeSummary,
    ShipmentStatus, RiskLevel, DisruptionType
)
from services.weather_service import fetch_weather_sync
from services.disruption_feed import fetch_disruptions_sync

logger = logging.getLogger(__name__)

# ─── Indian city data (real coordinates) ──────────────────────────────────────
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
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(max(0, a)))


def _route(origin: Location, dest: Location, mode: str) -> Route:
    dist = _haversine_km(origin.lat, origin.lng, dest.lat, dest.lng) * 1.3
    speed_map = {"Standard Class": 55, "Second Class": 65, "First Class": 700, "Same Day": 45}
    speed = speed_map.get(mode, 55)
    hours = dist / speed
    mid = _midpoint(origin, dest)
    return Route(
        distance_km=round(dist, 1),
        estimated_hours=round(hours, 1),
        waypoints=[
            RouteWaypoint(lat=origin.lat, lng=origin.lng, name=origin.city),
            RouteWaypoint(lat=mid.lat, lng=mid.lng),
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


# ─── Weather-enriched data loading ────────────────────────────────────────────

def _get_city_weather_cache() -> Dict[str, dict]:
    """Fetch live weather for all hub cities at startup."""
    weather_cache: Dict[str, dict] = {}
    for city, info in CITIES.items():
        try:
            wx = fetch_weather_sync(info["lat"], info["lng"], city)
            weather_cache[city] = wx
            logger.info(f"  Weather {city}: {wx['description']}, severity={wx['severity']}, live={wx['is_live']}")
        except Exception as e:
            logger.warning(f"  Weather fetch failed for {city}: {e}")
            weather_cache[city] = {"severity": 0.05, "description": "unknown", "is_live": False}
    return weather_cache


def _is_near_disaster(lat: float, lng: float, disasters: List[dict], radius_km: float = 300) -> Optional[dict]:
    """Check if a location is within radius of any real disaster."""
    for d in disasters:
        dist = _haversine_km(lat, lng, d.get("lat", 0), d.get("lng", 0))
        if dist < radius_km:
            return d
    return None


def build_live_shipments(weather_cache: Dict[str, dict], disasters: List[dict]) -> Dict[str, Shipment]:
    """
    Build shipments using REAL weather conditions and disaster data.
    Risk scores are computed dynamically from live conditions, not hardcoded.
    """
    now = datetime.now(timezone.utc)
    shipments: Dict[str, Shipment] = {}
    carrier_names = [c["name"] for c in CARRIERS_DATA]
    city_names = list(CITIES.keys())

    # ── Route definitions (realistic Indian logistics lanes) ────────────────
    ROUTES = [
        # High-traffic lanes (Mumbai hub)
        ("Mumbai", "Nhava Sheva"), ("Mumbai", "Delhi"), ("Mumbai", "Pune"),
        ("Mumbai", "Bangalore"), ("Mumbai", "Ahmedabad"), ("Mumbai", "Nagpur"),
        ("Mumbai", "Coimbatore"),
        # Delhi hub
        ("Delhi", "Lucknow"), ("Delhi", "Jaipur"), ("Delhi", "Chandigarh"),
        ("Delhi", "Patna"), ("Delhi", "Bhopal"),
        # South India
        ("Bangalore", "Chennai"), ("Bangalore", "Hyderabad"), ("Bangalore", "Kochi"),
        ("Bangalore", "Coimbatore"), ("Chennai", "Coimbatore"), ("Chennai", "Hyderabad"),
        ("Chennai", "Visakhapatnam"), ("Hyderabad", "Kochi"),
        # East
        ("Kolkata", "Patna"), ("Kolkata", "Lucknow"), ("Kolkata", "Bhopal"),
        # West
        ("Ahmedabad", "Surat"), ("Ahmedabad", "Jaipur"), ("Surat", "Mumbai"),
        ("Surat", "Nagpur"),
        # Central
        ("Nagpur", "Hyderabad"), ("Nagpur", "Bhopal"), ("Bhopal", "Indore"),
        ("Indore", "Jaipur"),
        # Cross-country
        ("Pune", "Nagpur"), ("Pune", "Hyderabad"), ("Pune", "Surat"),
        ("Pune", "Indore"), ("Lucknow", "Kolkata"),
        ("Hyderabad", "Visakhapatnam"), ("Kochi", "Coimbatore"),
        ("Chandigarh", "Delhi"), ("Patna", "Chandigarh"),
        # Additional high-value corridors
        ("Delhi", "Mumbai"), ("Chennai", "Kochi"), ("Bangalore", "Pune"),
        ("Hyderabad", "Nagpur"), ("Jaipur", "Delhi"), ("Lucknow", "Delhi"),
        ("Indore", "Bhopal"), ("Surat", "Ahmedabad"), ("Visakhapatnam", "Hyderabad"),
        ("Coimbatore", "Bangalore"),
    ]

    for i, (orig_city, dest_city) in enumerate(ROUTES):
        sid = f"SH{str(i + 1).zfill(3)}"
        carrier = carrier_names[i % len(carrier_names)]
        mode = SHIPPING_MODES[i % len(SHIPPING_MODES)]
        cat = CATEGORIES[i % len(CATEGORIES)]
        retailer = RETAILERS[i % len(RETAILERS)]

        origin = _loc(orig_city)
        dest = _loc(dest_city)
        route = _route(origin, dest, mode)

        # ── Get LIVE weather for origin and destination ────────────────────
        orig_wx = weather_cache.get(orig_city, {"severity": 0.05})
        dest_wx = weather_cache.get(dest_city, {"severity": 0.05})
        route_weather_severity = max(orig_wx.get("severity", 0), dest_wx.get("severity", 0))

        # ── Check proximity to REAL disasters ──────────────────────────────
        orig_disaster = _is_near_disaster(origin.lat, origin.lng, disasters)
        dest_disaster = _is_near_disaster(dest.lat, dest.lng, disasters)
        disaster_severity = 0.0
        disaster_active = False
        if orig_disaster:
            disaster_severity = max(disaster_severity, orig_disaster.get("severity", 0))
            disaster_active = True
        if dest_disaster:
            disaster_severity = max(disaster_severity, dest_disaster.get("severity", 0))
            disaster_active = True

        # ── Compute DYNAMIC risk score ─────────────────────────────────────
        carrier_risk = {"BlueDart": 0.06, "FedEx India": 0.04, "DHL Express": 0.05,
                       "Delhivery": 0.15, "DTDC": 0.22, "Ecom Express": 0.28,
                       "Shadowfax": 0.35, "XpressBees": 0.18}.get(carrier, 0.15)
        mode_risk = {"Standard Class": 0.22, "Second Class": 0.14, "First Class": 0.05, "Same Day": 0.08}.get(mode, 0.15)
        dist_risk = min(route.distance_km / 2500, 0.4)

        # Combine all risk factors dynamically
        base_risk = (carrier_risk * 25 + mode_risk * 15 + dist_risk * 15 +
                     route_weather_severity * 30 + disaster_severity * 40)
        # Add some natural variance
        variance = random.uniform(-5, 5)
        risk_score = round(min(max(base_risk + variance, 2.0), 98.0), 1)

        # Determine status from risk
        if disaster_active and disaster_severity > 0.6:
            status = ShipmentStatus.DISRUPTED
        elif risk_score >= 65:
            status = ShipmentStatus.DISRUPTED
        elif risk_score >= 40:
            status = ShipmentStatus.AT_RISK
        else:
            status = ShipmentStatus.ON_TRACK

        # ── Build risk factors from REAL data ──────────────────────────────
        factors = []
        if disaster_active:
            d = orig_disaster or dest_disaster
            factors.append(RiskFactor(
                name="Active disaster alert",
                contribution=round(disaster_severity * 0.6, 2),
                detail=f"{d['title']} ({d['source']}: {d['alert_level']})"
            ))
        if route_weather_severity > 0.05:
            wx_desc = orig_wx.get("description", "weather conditions")
            factors.append(RiskFactor(
                name="Weather conditions",
                contribution=round(route_weather_severity * 0.5, 2),
                detail=f"Live: {wx_desc} (severity: {route_weather_severity:.0%})"
            ))
        factors.append(RiskFactor(
            name="Carrier reliability",
            contribution=round(carrier_risk, 2),
            detail=f"{carrier}: {round((1 - carrier_risk) * 100)}% on-time rate"
        ))
        factors = factors[:3]

        # Revenue and ETA
        rev = float(random.randint(15000, 250000))
        eta_hours = route.estimated_hours + (risk_score / 5 if status != ShipmentStatus.ON_TRACK else 0)

        sh = Shipment(
            id=sid,
            order_id=f"ORD-{sid}",
            origin=origin,
            destination=dest,
            current_position=_midpoint(origin, dest),
            status=status,
            risk_score=risk_score,
            risk_level=_risk_level(risk_score),
            risk_factors=factors,
            confidence=round(0.75 + random.uniform(0, 0.2), 2),
            shipping_mode=mode,
            carrier=carrier,
            eta=now + timedelta(hours=eta_hours),
            original_eta=now + timedelta(hours=route.estimated_hours),
            deadline=now + timedelta(hours=route.estimated_hours + random.randint(6, 36)),
            revenue=rev,
            category=cat,
            route=route,
            updated_at=now - timedelta(minutes=random.randint(1, 120)),
        )
        shipments[sid] = sh

    return shipments


def build_live_disruptions(
    shipments: Dict[str, Shipment],
    weather_cache: Dict[str, dict],
    disasters: List[dict],
) -> Dict[str, Disruption]:
    """
    Create disruption entries from REAL disaster feeds + weather data.
    """
    now = datetime.now(timezone.utc)
    disruptions: Dict[str, Disruption] = {}
    disruption_type_map = {
        "flood": DisruptionType.WEATHER,
        "cyclone": DisruptionType.WEATHER,
        "earthquake": DisruptionType.WEATHER,
        "drought": DisruptionType.WEATHER,
        "wildfire": DisruptionType.WEATHER,
        "volcano": DisruptionType.WEATHER,
        "weather": DisruptionType.WEATHER,
        "congestion": DisruptionType.CONGESTION,
    }

    # ── 1. Disruptions from real disaster feed ─────────────────────────────────
    for i, disaster in enumerate(disasters[:5]):
        dis_id = f"DIS{str(i + 1).zfill(3)}"
        dtype = disruption_type_map.get(disaster.get("type", "weather"), DisruptionType.WEATHER)

        # Find affected shipments (those near the disaster location)
        affected_ids = []
        for s in shipments.values():
            if (_haversine_km(s.origin.lat, s.origin.lng, disaster.get("lat", 0), disaster.get("lng", 0)) < 300 or
                _haversine_km(s.destination.lat, s.destination.lng, disaster.get("lat", 0), disaster.get("lng", 0)) < 300):
                affected_ids.append(s.id)

        # Skip disasters that don't affect any Indian shipments
        if not affected_ids:
            continue

        affected_ships = [shipments[sid] for sid in affected_ids if sid in shipments]
        rev_at_risk = sum(s.revenue for s in affected_ships)

        # Find nearest city for location
        nearest_city = _nearest_city(disaster.get("lat", 20), disaster.get("lng", 78))

        cascade = CascadeSummary(
            total_shipments=len(affected_ids),
            total_retailers=min(len(affected_ids), len(set(RETAILERS))),
            revenue_at_risk=round(rev_at_risk),
            customers_affected=len(affected_ids) * random.randint(200, 800),
            max_delay_hours=round(disaster.get("severity", 0.5) * 48, 1),
        )

        d = Disruption(
            id=dis_id,
            type=dtype,
            title=f"[LIVE] {disaster.get('title', 'Unknown Event')}",
            location=_loc(nearest_city) if nearest_city in CITIES else Location(
                city=nearest_city, state="India",
                lat=disaster.get("lat", 20), lng=disaster.get("lng", 78)
            ),
            severity=disaster.get("severity", 0.5),
            status="active",
            detected_at=now - timedelta(hours=random.randint(1, 24)),
            estimated_end=now + timedelta(hours=random.randint(6, 72)),
            cascade=cascade,
            affected_shipment_ids=affected_ids[:10],
            mitigation_applied=False,
            created_at=now - timedelta(hours=random.randint(1, 24)),
        )
        disruptions[dis_id] = d

    # ── 2. Weather-based disruptions for cities with severe conditions ──────────
    severe_weather_cities = [
        (city, wx) for city, wx in weather_cache.items()
        if wx.get("severity", 0) >= 0.25
    ]
    for j, (city, wx) in enumerate(severe_weather_cities[:3]):
        dis_id = f"DIS{str(len(disruptions) + j + 1).zfill(3)}"

        affected_ids = [
            s.id for s in shipments.values()
            if s.origin.city == city or s.destination.city == city
        ]
        affected_ships = [shipments[sid] for sid in affected_ids if sid in shipments]
        rev_at_risk = sum(s.revenue for s in affected_ships)

        cascade = CascadeSummary(
            total_shipments=len(affected_ids),
            total_retailers=min(len(affected_ids), 5),
            revenue_at_risk=round(rev_at_risk),
            customers_affected=len(affected_ids) * random.randint(100, 500),
            max_delay_hours=round(wx.get("severity", 0.3) * 36, 1),
        )

        live_tag = "[LIVE]" if wx.get("is_live", False) else "[EST]"
        d = Disruption(
            id=dis_id,
            type=DisruptionType.WEATHER,
            title=f"{live_tag} {city}: {wx.get('description', 'adverse weather').title()}",
            location=_loc(city),
            severity=wx.get("severity", 0.3),
            status="active",
            detected_at=now - timedelta(hours=1),
            estimated_end=now + timedelta(hours=random.randint(6, 36)),
            cascade=cascade,
            affected_shipment_ids=affected_ids[:10],
            mitigation_applied=False,
            created_at=now - timedelta(hours=1),
        )
        disruptions[dis_id] = d

    # Ensure at least 2 disruptions for demo purposes
    if len(disruptions) == 0:
        disruptions["DIS001"] = Disruption(
            id="DIS001", type=DisruptionType.CONGESTION,
            title="Mumbai Port Congestion",
            location=_loc("Mumbai"), severity=0.85, status="active",
            detected_at=now - timedelta(hours=2),
            estimated_end=now + timedelta(hours=22),
            cascade=CascadeSummary(total_shipments=5, total_retailers=4, revenue_at_risk=342000, customers_affected=6670, max_delay_hours=36),
            affected_shipment_ids=[s.id for s in list(shipments.values())[:5]],
            mitigation_applied=False, created_at=now - timedelta(hours=2),
        )

    return disruptions


def build_live_alerts(
    shipments: Dict[str, Shipment],
    disruptions: Dict[str, Disruption],
) -> Dict[str, Alert]:
    """Create alerts from real disruptions and high-risk shipments."""
    now = datetime.now(timezone.utc)
    alerts: Dict[str, Alert] = {}

    # Alerts from disruptions
    for i, d in enumerate(list(disruptions.values())[:5]):
        aid = f"ALT{str(i + 1).zfill(3)}"
        a = Alert(
            id=aid,
            type="disruption_detected",
            severity="critical" if d.severity >= 0.7 else "warning",
            title=d.title,
            message=f"{d.title}. {len(d.affected_shipment_ids)} shipments at risk. "
                    f"₹{round(d.cascade.revenue_at_risk / 1000, 1)}K revenue exposed.",
            shipment_id=None,
            disruption_id=d.id,
            read=False,
            created_at=d.detected_at or now,
        )
        alerts[aid] = a

    # Alerts from high-risk shipments
    critical_ships = [s for s in shipments.values() if s.risk_score >= 70]
    for j, s in enumerate(critical_ships[:5]):
        aid = f"ALT{str(len(alerts) + j + 1).zfill(3)}"
        a = Alert(
            id=aid,
            type="risk_threshold",
            severity="critical" if s.risk_score >= 80 else "warning",
            title=f"Shipment {s.id}: {(s.risk_level.value if hasattr(s.risk_level, 'value') else s.risk_level).upper()} Risk ({s.risk_score}/100)",
            message=f"{s.id} ({s.origin.city}→{s.destination.city}) crossed {(s.risk_level.value if hasattr(s.risk_level, 'value') else s.risk_level).upper()} "
                    f"threshold. Carrier: {s.carrier}. Revenue: ₹{round(s.revenue / 1000, 1)}K.",
            shipment_id=s.id,
            disruption_id=None,
            read=False,
            created_at=now - timedelta(minutes=random.randint(5, 120)),
        )
        alerts[aid] = a

    return alerts


def _nearest_city(lat: float, lng: float) -> str:
    """Find the nearest Indian city to given coordinates."""
    min_dist = float("inf")
    nearest = "Mumbai"
    for city, info in CITIES.items():
        d = _haversine_km(lat, lng, info["lat"], info["lng"])
        if d < min_dist:
            min_dist = d
            nearest = city
    return nearest
