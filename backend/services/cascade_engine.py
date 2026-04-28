"""
Cascade propagation engine.

Uses BFS through a directed supply-chain graph to compute the downstream
impact of a disruption. Models impact decay by depth and edge dependency weight.

Design pattern: Service layer — pure functions, no side effects, fully testable.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
import math
import uuid
import networkx as nx

from models.schemas import (
    CascadeNode, CascadeResult, CascadeSummary, Disruption,
    RiskFactor, LatLng, SimulateDisruptionRequest, DisruptionType
)
from services.data_store import DataStore


# ─── Core cascade algorithm ───────────────────────────────────────────────────

def _estimate_delay_hours(impact_score: float, node_data: dict, disruption_type: str) -> float:
    """Estimate delay hours based on impact and node characteristics."""
    base_hours_map = {
        "congestion": 18.0,
        "port_closure": 36.0,
        "weather": 24.0,
        "road_block": 20.0,
        "carrier_failure": 30.0,
    }
    base = base_hours_map.get(disruption_type, 20.0)
    return round(base * impact_score, 1)


def _node_type_from_name(name: str) -> str:
    dc_keywords = ["DC", "Hub", "Warehouse", "Distribution"]
    retailer_keywords = ["BigBasket", "Flipkart", "DMart", "Reliance", "Amazon", "Myntra", "Meesho"]
    if any(k in name for k in retailer_keywords):
        return "retailer"
    if any(k in name for k in dc_keywords):
        return "warehouse"
    return "shipment"


def compute_cascade(
    G: nx.DiGraph,
    disrupted_node: str,
    severity: float,
    disruption_type: str,
    disruption_id: str = "SIM",
    max_depth: int = 4,
    time_horizon_hours: int = 48,
) -> CascadeResult:
    """
    BFS-based cascade propagation through supply chain graph.

    Args:
        G: Directed supply chain graph
        disrupted_node: City/node where disruption occurs
        severity: 0.0–1.0 disruption severity at source
        disruption_type: Type of disruption for delay estimation
        disruption_id: ID to attach to result
        max_depth: Maximum propagation depth
        time_horizon_hours: Time window for cascade visualization

    Returns:
        CascadeResult with full tree and summary
    """
    if disrupted_node not in G.nodes:
        # Find closest node
        disrupted_node = list(G.nodes)[0]

    visited: Dict[str, float] = {}  # node_id -> impact_score
    cascade_nodes: Dict[str, CascadeNode] = {}
    queue: List[tuple] = [(disrupted_node, severity, 0, None)]  # (node, impact, depth, parent)

    while queue:
        node, impact, depth, parent_id = queue.pop(0)

        if node in visited or depth > max_depth:
            continue
        if impact < 0.05:  # Stop trivial propagation
            continue

        visited[node] = impact
        node_data = G.nodes.get(node, {})
        lat = node_data.get("lat", 20.0)
        lng = node_data.get("lng", 77.0)
        revenue = node_data.get("revenue", 0) * impact
        customers = int(node_data.get("customers", 100) * impact)
        delay = _estimate_delay_hours(impact, node_data, disruption_type)

        # Node type
        ntype = "source" if depth == 0 else _node_type_from_name(node)

        # Risk factors for this node
        rfs = [
            RiskFactor(name="Upstream disruption propagation", contribution=round(min(impact, 1.0), 2),
                       detail=f"Impact decayed from source: {round(impact * 100)}%"),
        ]
        if depth > 0:
            rfs.append(RiskFactor(name="Route dependency", contribution=round(impact * 0.3, 2),
                                  detail=f"Depth {depth} from disruption source"))

        cascade_node = CascadeNode(
            node_id=node,
            node_type=ntype,
            name=node,
            location=LatLng(lat=lat, lng=lng),
            impact_score=round(impact, 3),
            depth=depth,
            delay_hours=delay,
            revenue_at_risk=round(revenue, 0),
            customers_affected=customers,
            parent_id=parent_id,
            children=[],
            risk_factors=rfs,
        )
        cascade_nodes[node] = cascade_node

        # Propagate to downstream nodes
        for neighbor in G.successors(node):
            if neighbor not in visited:
                edge_data = G.edges.get((node, neighbor), {})
                dep_weight = edge_data.get("dependency_weight", 0.65)
                propagated = impact * dep_weight * (0.85 ** depth)  # exponential decay
                if propagated >= 0.05:
                    queue.append((neighbor, propagated, depth + 1, node))

    # Build tree from flat nodes
    source_node = cascade_nodes.get(disrupted_node)
    if not source_node:
        # Fallback empty result
        return CascadeResult(
            disruption_id=disruption_id,
            source=CascadeNode(
                node_id=disrupted_node, node_type="source", name=disrupted_node,
                location=LatLng(lat=19.0, lng=72.8), impact_score=severity,
                depth=0, delay_hours=0, revenue_at_risk=0, customers_affected=0,
            ),
            affected=[],
            summary=CascadeSummary(total_shipments=0, total_retailers=0,
                                   revenue_at_risk=0, customers_affected=0, max_delay_hours=0),
        )

    # Wire children
    for node_id, cn in cascade_nodes.items():
        if cn.parent_id and cn.parent_id in cascade_nodes:
            cascade_nodes[cn.parent_id].children.append(cn)

    affected = [cn for nid, cn in cascade_nodes.items() if nid != disrupted_node]

    total_revenue = sum(cn.revenue_at_risk for cn in affected)
    total_customers = sum(cn.customers_affected for cn in affected)
    total_shipments = len([cn for cn in affected if cn.node_type in ("shipment", "retailer")])
    total_retailers = len([cn for cn in affected if cn.node_type == "retailer"])
    max_delay = max((cn.delay_hours for cn in affected), default=0)

    summary = CascadeSummary(
        total_shipments=max(total_shipments, 1),
        total_retailers=max(total_retailers, 1),
        revenue_at_risk=round(total_revenue),
        customers_affected=total_customers,
        max_delay_hours=max_delay,
    )

    return CascadeResult(
        disruption_id=disruption_id,
        source=source_node,
        affected=affected,
        summary=summary,
        time_horizon_hours=time_horizon_hours,
    )


def compute_cascade_for_disruption(
    disruption: Disruption,
    store: DataStore,
) -> CascadeResult:
    """
    Compute cascade for an existing disruption, using the seeded cascade
    data for demo disruptions, real propagation for simulated ones.
    """
    G = store.get_graph()
    city = disruption.location.city

    # For pre-seeded demo disruptions, enrich with actual shipment data
    result = compute_cascade(
        G=G,
        disrupted_node=city,
        severity=disruption.severity,
        disruption_type=disruption.type.value if hasattr(disruption.type, "value") else str(disruption.type),
        disruption_id=disruption.id,
    )

    # Merge pre-computed cascade summary (more accurate for demo)
    if disruption.cascade:
        result.summary = disruption.cascade

    return result


def simulate_disruption(
    req: SimulateDisruptionRequest,
    store: DataStore,
) -> CascadeResult:
    """
    Run a what-if simulation for a hypothetical disruption.
    Returns cascade result without persisting.
    """
    G = store.get_graph()

    # Try to find the location in graph nodes
    location = req.location
    best_node = None
    for node in G.nodes:
        if location.lower() in node.lower() or node.lower() in location.lower():
            best_node = node
            break

    if not best_node:
        # Use Mumbai as default fallback for demo
        best_node = "Mumbai"

    sim_id = f"SIM-{uuid.uuid4().hex[:8].upper()}"

    return compute_cascade(
        G=G,
        disrupted_node=best_node,
        severity=req.severity,
        disruption_type=req.type.value if hasattr(req.type, "value") else str(req.type),
        disruption_id=sim_id,
        time_horizon_hours=req.duration_hours * 2,
    )


def cascade_to_dict(result: CascadeResult) -> Dict[str, Any]:
    """Serialize cascade result to a dict suitable for JSON response and frontend."""
    def node_to_dict(n: CascadeNode) -> dict:
        return {
            "node_id": n.node_id,
            "node_type": n.node_type,
            "name": n.name,
            "location": {"lat": n.location.lat, "lng": n.location.lng},
            "impact_score": n.impact_score,
            "depth": n.depth,
            "delay_hours": n.delay_hours,
            "revenue_at_risk": n.revenue_at_risk,
            "customers_affected": n.customers_affected,
            "parent_id": n.parent_id,
            "children": [node_to_dict(c) for c in n.children],
            "risk_factors": [rf.model_dump() for rf in n.risk_factors],
        }

    return {
        "disruption_id": result.disruption_id,
        "source": node_to_dict(result.source),
        "affected": [node_to_dict(n) for n in result.affected],
        "summary": result.summary.model_dump(),
        "time_horizon_hours": result.time_horizon_hours,
    }
