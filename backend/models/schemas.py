"""Pydantic v2 schemas for all SupplySense AI entities."""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ShipmentStatus(str, Enum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    DISRUPTED = "disrupted"
    REROUTED = "rerouted"
    DELIVERED = "delivered"


class DisruptionType(str, Enum):
    WEATHER = "weather"
    PORT_CLOSURE = "port_closure"
    ROAD_BLOCK = "road_block"
    CARRIER_FAILURE = "carrier_failure"
    CONGESTION = "congestion"
    STRIKE = "strike"
    INFRASTRUCTURE = "infrastructure"
    FLOOD = "flood"
    EARTHQUAKE = "earthquake"
    CYBER_ATTACK = "cyber_attack"


# ─── Geographic ────────────────────────────────────────────────────────────────

class LatLng(BaseModel):
    lat: float
    lng: float


class Location(BaseModel):
    city: str
    state: str
    lat: float
    lng: float


# ─── Risk ──────────────────────────────────────────────────────────────────────

class RiskFactor(BaseModel):
    name: str
    contribution: float = Field(ge=0.0, le=1.0)
    detail: str


class RiskResult(BaseModel):
    risk_score: float = Field(ge=0, le=100)
    risk_level: RiskLevel
    confidence: float = Field(ge=0, le=1)
    top_factors: List[RiskFactor]


# ─── Route ─────────────────────────────────────────────────────────────────────

class RouteWaypoint(BaseModel):
    lat: float
    lng: float
    name: Optional[str] = None


class Route(BaseModel):
    polyline: Optional[str] = None
    distance_km: float
    estimated_hours: float
    waypoints: List[RouteWaypoint] = []


class RouteOption(BaseModel):
    id: str
    name: str
    description: str
    time_hours: float
    cost_inr: float
    carbon_kg: float
    risk_score: float
    composite_score: float
    polyline: Optional[str] = None
    waypoints: List[RouteWaypoint] = []
    is_recommended: bool = False
    recommendation_reason: Optional[str] = None


class RouteComparison(BaseModel):
    do_nothing: Dict[str, Any]
    recommended: Dict[str, Any]


class OptimizeRoutesResponse(BaseModel):
    shipment_id: str
    current_route: Dict[str, Any]
    alternatives: List[RouteOption]
    comparison: RouteComparison


class AcceptRouteRequest(BaseModel):
    shipment_id: str
    route_id: str


# ─── Shipment ──────────────────────────────────────────────────────────────────

class Shipment(BaseModel):
    id: str
    order_id: str
    origin: Location
    destination: Location
    current_position: LatLng
    status: ShipmentStatus
    risk_score: float = Field(ge=0, le=100)
    risk_level: RiskLevel
    risk_factors: List[RiskFactor]
    confidence: float = Field(ge=0, le=1)
    shipping_mode: str
    carrier: str
    eta: datetime
    original_eta: datetime
    deadline: datetime
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    revenue: float
    category: str
    route: Route
    updated_at: datetime

    model_config = {"use_enum_values": True}


class ShipmentListResponse(BaseModel):
    shipments: List[Shipment]
    total: int
    limit: int = 20
    offset: int = 0


# ─── Cascade ───────────────────────────────────────────────────────────────────

class CascadeNode(BaseModel):
    node_id: str
    node_type: Literal["source", "shipment", "warehouse", "retailer"]
    name: str
    location: LatLng
    impact_score: float = Field(ge=0, le=1)
    depth: int
    delay_hours: float
    revenue_at_risk: float
    customers_affected: int
    parent_id: Optional[str] = None
    children: List["CascadeNode"] = []
    risk_factors: List[RiskFactor] = []


CascadeNode.model_rebuild()


class CascadeSummary(BaseModel):
    total_shipments: int
    total_retailers: int
    revenue_at_risk: float
    customers_affected: int
    max_delay_hours: float


class CascadeResult(BaseModel):
    disruption_id: str
    source: CascadeNode
    affected: List[CascadeNode]
    summary: CascadeSummary
    time_horizon_hours: int = 48


class SimulateDisruptionRequest(BaseModel):
    location: str
    type: DisruptionType
    severity: float = Field(default=0.7, ge=0, le=1)
    duration_hours: int = Field(default=24, gt=0)


# ─── Disruption ────────────────────────────────────────────────────────────────

class Disruption(BaseModel):
    id: str
    type: DisruptionType
    title: str
    location: Location
    severity: float = Field(ge=0, le=1)
    status: Literal["active", "mitigated", "resolved"]
    detected_at: datetime
    estimated_end: Optional[datetime] = None
    cascade: Optional[CascadeSummary] = None
    affected_shipment_ids: List[str] = []
    mitigation_applied: bool = False
    mitigation_action: Optional[str] = None
    created_at: datetime

    model_config = {"use_enum_values": True}


# ─── Carrier ───────────────────────────────────────────────────────────────────

class Carrier(BaseModel):
    id: str
    name: str
    on_time_rate: float = Field(ge=0, le=1)
    avg_delay_hours: float
    total_shipments: int
    risk_score: float = Field(ge=0, le=100)
    trend: Literal["improving", "stable", "declining"]


# ─── Resilience ────────────────────────────────────────────────────────────────

class ResilienceBreakdown(BaseModel):
    route_redundancy: float
    carrier_diversity: float
    geographic_spread: float
    buffer_capacity: float
    recovery_speed: float


class ResilienceScore(BaseModel):
    score: float = Field(ge=0, le=100)
    breakdown: ResilienceBreakdown
    weakest_link: str
    recommendation: str
    trend: List[float]


# ─── Alert ─────────────────────────────────────────────────────────────────────

class Alert(BaseModel):
    id: str
    type: Literal[
        "disruption_detected", "risk_threshold", "auto_reroute", "resilience_drop"
    ]
    severity: Literal["info", "warning", "critical"]
    title: str
    message: str
    shipment_id: Optional[str] = None
    disruption_id: Optional[str] = None
    read: bool = False
    created_at: datetime


class AlertListResponse(BaseModel):
    alerts: List[Alert]
    total: int
    unread: int


# ─── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class MapOverlay(BaseModel):
    type: Literal["disruption_zone", "route", "marker"]
    center: Optional[LatLng] = None
    radius_km: Optional[float] = None
    polyline: Optional[str] = None
    label: Optional[str] = None
    color: Optional[str] = "#ef4444"


class ChatVisualization(BaseModel):
    type: str = "text"
    data: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    visualization: Optional[ChatVisualization] = None
    function_called: Optional[str] = None
    suggestions: List[str] = []


# ─── KPI ───────────────────────────────────────────────────────────────────────

class KPIData(BaseModel):
    active_shipments: int
    at_risk_count: int
    disrupted_count: int
    revenue_at_risk: float
    resilience_score: float
    auto_mitigated_today: int
    revenue_saved_today: float


# ─── Optimize request ──────────────────────────────────────────────────────────

class OptimizeRoutesRequest(BaseModel):
    shipment_id: str
    weights: Dict[str, float] = Field(
        default={"cost": 0.25, "time": 0.35, "carbon": 0.15, "risk": 0.25}
    )


# ─── Shipment Creation ────────────────────────────────────────────────────────

class CreateShipmentRequest(BaseModel):
    origin_city: str
    destination_city: str
    carrier: Optional[str] = None
    shipping_mode: str = "Standard Class"
    category: str = "Electronics"
    revenue: float = Field(default=50000, ge=0)
    deadline_hours: int = Field(default=48, gt=0)


class CreateShipmentResponse(BaseModel):
    shipment: Shipment
    routes: List[RouteOption]
    risk_breakdown: RiskResult


# ─── Node / Port Risk Analysis ────────────────────────────────────────────────

class NodeRiskAnalysis(BaseModel):
    city: str
    state: str
    lat: float
    lng: float
    total_shipments_through: int
    active_disruptions: List[str]
    risk_score: float
    risk_level: RiskLevel
    risk_factors: List[RiskFactor]
    weather: Optional[Dict[str, Any]] = None
    festival_impact: Optional[Dict[str, Any]] = None
    resilience_score: float
    bottleneck_score: float
    throughput_rank: int


# ─── Enhanced Simulation ──────────────────────────────────────────────────────

class SimulateNodeRequest(BaseModel):
    node: str
    disruption_type: DisruptionType = DisruptionType.CONGESTION
    severity: float = Field(default=0.7, ge=0, le=1)
    duration_hours: int = Field(default=24, gt=0)


class SimulateNodeResponse(BaseModel):
    node: str
    cascade: CascadeResult
    affected_shipments: List[str]
    revenue_at_risk: float
    alternative_routes_available: int
    recommendations: List[str]
