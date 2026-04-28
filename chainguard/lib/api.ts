/**
 * SupplySense AI API client.
 * All calls go to NEXT_PUBLIC_API_URL (default: http://localhost:8000).
 */

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = `${BASE}/api/v1`;

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API POST ${path} → ${res.status}`);
  return res.json();
}

async function del_<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "DELETE",
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API DELETE ${path} → ${res.status}`);
  return res.json();
}

// ── Endpoints ──────────────────────────────────────────────────────────────

export const api = {
  kpis: () => get<KPIData>("/kpis"),
  shipments: (params?: { status?: string; risk_level?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.risk_level) qs.set("risk_level", params.risk_level);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    return get<ShipmentListResponse>(`/shipments${qs.toString() ? `?${qs}` : ""}`);
  },
  shipment: (id: string) => get<Shipment>(`/shipments/${id}`),
  shipmentRisk: (id: string) => get<RiskResult>(`/shipments/${id}/risk`),
  shipmentRiskExplain: (id: string) => get<RiskExplanation>(`/shipments/${id}/risk-explain`),
  topRiskShipments: (count = 5) => get<TopRiskShipment[]>(`/shipments/top-risk?count=${count}`),
  disruptions: () => get<Disruption[]>("/disruptions"),
  disruption: (id: string) => get<Disruption>(`/disruptions/${id}`),
  cascade: (disruptionId: string) => get<CascadeResult>(`/cascade/${disruptionId}`),
  simulateCascade: (req: SimulateRequest) => post<CascadeResult>("/cascade/simulate", req),
  optimizeRoutes: (req: OptimizeRequest) => post<OptimizeResponse>("/optimize/routes", req),
  acceptRoute: (shipmentId: string, routeId: string) =>
    post<{ status: string }>("/optimize/accept", { shipment_id: shipmentId, route_id: routeId }),
  chat: (message: string, sessionId = "default") =>
    post<ChatResponse>("/chat", { message, session_id: sessionId }),
  resilience: () => get<ResilienceScore>("/resilience"),
  resilienceHistory: () => get<ResilienceHistory>("/resilience/history"),
  alerts: (unreadOnly = false) => get<AlertListResponse>(`/alerts${unreadOnly ? "?unread_only=true" : ""}`),
  markAlertRead: (id: string) => post<{ read: boolean }>(`/alerts/${id}/read`, {}),

  // ── New endpoints ──
  nodes: () => get<NodeSummary[]>("/nodes"),
  nodeRisk: (city: string) => get<NodeRiskAnalysis>(`/nodes/${encodeURIComponent(city)}/risk`),
  createShipment: (req: CreateShipmentRequest) => post<CreateShipmentResponse>("/shipments/create", req),
  simulateNode: (req: SimulateNodeRequest) => post<SimulateNodeResponse>("/simulate/node", req),
  deleteShipment: (id: string) => del_<{ id: string; deleted: boolean }>(`/shipments/${id}`),
  rescoreShipments: () => post<{ rescored: number; critical: number; high: number; medium: number; low: number }>("/shipments/rescore", {}),
  festivals: () => get<FestivalData>("/festivals"),
  festivalImpact: () => get<FestivalCityImpact[]>("/festivals/impact"),
};

// ── Type definitions ───────────────────────────────────────────────────────

export interface KPIData {
  active_shipments: number;
  at_risk_count: number;
  disrupted_count: number;
  revenue_at_risk: number;
  resilience_score: number;
  auto_mitigated_today: number;
  revenue_saved_today: number;
}

export interface Location {
  city: string;
  state: string;
  lat: number;
  lng: number;
}

export interface RiskFactor {
  name: string;
  contribution: number;
  detail: string;
}

export interface RiskResult {
  risk_score: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  confidence: number;
  top_factors: RiskFactor[];
}

export interface RiskExplanationFactor {
  name: string;
  contribution_pct: number;
  detail: string;
  icon: string;
}

export interface RiskExplanation {
  summary: string;
  score: number;
  level: string;
  confidence: number;
  factors: RiskExplanationFactor[];
  route: string;
  carrier: string;
  mode: string;
  distance_km: number;
}

export interface TopRiskShipment {
  shipment: Shipment;
  risk_result: RiskResult;
  risk_explanation: RiskExplanation;
  reroute: {
    recommended: RouteOption | null;
    alternatives: RouteOption[];
    comparison: {
      do_nothing: Record<string, unknown>;
      recommended: Record<string, unknown>;
    } | null;
  } | null;
}

export interface RouteWaypoint { lat: number; lng: number; name?: string; }

export interface Route {
  distance_km: number;
  estimated_hours: number;
  waypoints: RouteWaypoint[];
}

export interface Shipment {
  id: string;
  order_id: string;
  origin: Location;
  destination: Location;
  current_position: { lat: number; lng: number };
  status: string;
  risk_score: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  risk_factors: RiskFactor[];
  confidence: number;
  shipping_mode: string;
  carrier: string;
  eta: string;
  original_eta: string;
  deadline: string;
  priority: "low" | "medium" | "high" | "critical";
  revenue: number;
  category: string;
  route: Route;
  updated_at: string;
}

export interface ShipmentListResponse {
  shipments: Shipment[];
  total: number;
  limit: number;
  offset: number;
}

export interface Disruption {
  id: string;
  type: string;
  title: string;
  location: Location;
  severity: number;
  status: string;
  detected_at: string;
  estimated_end?: string;
  cascade?: {
    total_shipments: number;
    total_retailers: number;
    revenue_at_risk: number;
    customers_affected: number;
    max_delay_hours: number;
  };
  affected_shipment_ids: string[];
}

export interface CascadeNode {
  node_id: string;
  node_type: string;
  name: string;
  location: { lat: number; lng: number };
  impact_score: number;
  depth: number;
  delay_hours: number;
  revenue_at_risk: number;
  customers_affected: number;
  parent_id?: string;
  children: CascadeNode[];
  risk_factors: RiskFactor[];
}

export interface CascadeResult {
  disruption_id: string;
  source: CascadeNode;
  affected: CascadeNode[];
  summary: {
    total_shipments: number;
    total_retailers: number;
    revenue_at_risk: number;
    customers_affected: number;
    max_delay_hours: number;
  };
  time_horizon_hours: number;
}

export interface SimulateRequest {
  location: string;
  type: string;
  severity: number;
  duration_hours: number;
}

export interface RouteOption {
  id: string;
  name: string;
  description: string;
  time_hours: number;
  cost_inr: number;
  carbon_kg: number;
  risk_score: number;
  composite_score: number;
  waypoints: RouteWaypoint[];
  is_recommended: boolean;
  recommendation_reason?: string;
}

export interface OptimizeRequest {
  shipment_id: string;
  weights?: { cost: number; time: number; carbon: number; risk: number };
}

export interface OptimizeResponse {
  shipment_id: string;
  current_route: Record<string, unknown>;
  alternatives: RouteOption[];
  comparison: {
    do_nothing: Record<string, unknown>;
    recommended: Record<string, unknown>;
  };
}

export interface ChatResponse {
  session_id: string;
  message: string;
  visualization?: { type: string; data?: Record<string, unknown> };
  function_called?: string;
  suggestions: string[];
}

export interface ResilienceBreakdown {
  route_redundancy: number;
  carrier_diversity: number;
  geographic_spread: number;
  buffer_capacity: number;
  recovery_speed: number;
}

export interface ResilienceScore {
  score: number;
  breakdown: ResilienceBreakdown;
  weakest_link: string;
  recommendation: string;
  trend: number[];
}

export interface ResilienceHistory {
  trend: { timestamp: string; score: number; label: string }[];
  delta_7d: number;
}

export interface Alert {
  id: string;
  type: string;
  severity: "info" | "warning" | "critical";
  title: string;
  message: string;
  shipment_id?: string;
  disruption_id?: string;
  read: boolean;
  created_at: string;
}

export interface AlertListResponse {
  alerts: Alert[];
  total: number;
  unread: number;
}

// ── New types for nodes, simulation, festivals ─────────────────────────────

export interface NodeSummary {
  city: string;
  state: string;
  lat: number;
  lng: number;
  shipment_count: number;
  disruption_count: number;
  avg_risk_score: number;
  risk_level: string;
  festival_congestion: number;
  active_festivals: string[];
  is_peak_season: boolean;
  monsoon: boolean;
  degree: number;
  is_bottleneck: boolean;
}

export interface NodeRiskAnalysis {
  city: string;
  state: string;
  lat: number;
  lng: number;
  total_shipments_through: number;
  active_disruptions: { id: string; type: string; severity: number }[];
  risk_score: number;
  risk_level: string;
  risk_factors: RiskFactor[];
  weather: Record<string, unknown> | null;
  festival_impact: Record<string, unknown>;
  resilience_score: number;
  bottleneck_score: number;
  throughput_rank: number;
  degree: number;
  carriers: string[];
}

export interface CreateShipmentRequest {
  origin_city: string;
  destination_city: string;
  carrier: string;
  shipping_mode: string;
  category: string;
  revenue: number;
  deadline_hours?: number;
}

export interface CreateShipmentResponse {
  shipment: Shipment;
  routes: RouteOption[];
  risk_breakdown: RiskResult;
}

export interface SimulateNodeRequest {
  node: string;
  disruption_type: string;
  severity: number;
  duration_hours: number;
}

export interface SimulateNodeResponse {
  node: string;
  disruption_type: string;
  severity: number;
  duration_hours: number;
  cascade: Record<string, unknown>;
  affected_shipments: {
    id: string;
    route: string;
    risk_score: number;
    revenue: number;
  }[];
  revenue_at_risk: number;
  alternative_routes_available: number;
  recommendations: string[];
  festival_impact: Record<string, unknown>;
}

export interface FestivalData {
  upcoming: { name: string; date: string; congestion_factor: number; affected_regions: string[] }[];
  active_today: { name: string; congestion_factor: number; affected_regions: string[] }[];
  ecommerce_surge: { name: string; congestion_boost: number } | null;
  monsoon: boolean;
  is_peak_season: boolean;
}

export interface FestivalCityImpact {
  city: string;
  state: string;
  congestion: number;
  festivals: string[];
  ecommerce: string | null;
  monsoon: boolean;
  is_peak_season: boolean;
}
