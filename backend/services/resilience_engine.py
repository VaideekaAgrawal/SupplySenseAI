"""
Network Resilience Score engine.

Computes a 0–100 composite score measuring how resilient the current
supply chain network is to disruptions. Sub-metrics:
  1. Route Redundancy — % of OD pairs with 2+ alternative routes
  2. Carrier Diversity — inverse Herfindahl–Hirschman Index
  3. Geographic Spread — Shannon entropy of hub distribution
  4. Buffer Capacity — avg slack between ETA and deadline
  5. Recovery Speed — historical disruption resolution speed

Design pattern: Pure functions, composable sub-scorers.
"""

from __future__ import annotations
import math
from typing import List, Dict, Tuple
from datetime import datetime, timezone

import networkx as nx

from models.schemas import (
    Shipment, Disruption, ResilienceScore, ResilienceBreakdown
)


# ─── Sub-metric functions ─────────────────────────────────────────────────────

def _route_redundancy_score(G: nx.DiGraph) -> float:
    """
    What % of origin–destination pairs have 2+ vertex-disjoint paths?
    More redundant routes = higher score.
    """
    if len(G.nodes) < 2:
        return 50.0

    pairs_with_multiple = 0
    total_pairs = 0

    nodes = list(G.nodes)
    sampled = nodes[:min(20, len(nodes))]  # Sample for performance

    for i in range(len(sampled)):
        for j in range(len(sampled)):
            if i == j:
                continue
            total_pairs += 1
            try:
                paths = list(nx.all_simple_paths(G, sampled[i], sampled[j], cutoff=3))
                if len(paths) >= 2:
                    pairs_with_multiple += 1
            except Exception:
                pass

    if total_pairs == 0:
        return 60.0
    return round((pairs_with_multiple / total_pairs) * 100, 1)


def _carrier_diversity_score(shipments: List[Shipment]) -> float:
    """
    Inverse Herfindahl–Hirschman Index.
    Perfectly distributed = 100, all one carrier = low score.
    """
    if not shipments:
        return 50.0

    carrier_counts: Dict[str, int] = {}
    for s in shipments:
        carrier_counts[s.carrier] = carrier_counts.get(s.carrier, 0) + 1

    total = len(shipments)
    shares = [count / total for count in carrier_counts.values()]

    hhi = sum(s ** 2 for s in shares)  # 0 = perfectly diverse, 1 = monopoly
    # Normalize: HHI of 1/n (perfectly even) → 100, HHI of 1 → 0
    n = len(shares)
    min_hhi = 1 / n if n > 0 else 1
    diversity = max(0, (1 - hhi) / (1 - min_hhi + 1e-9))
    return round(diversity * 100, 1)


def _geographic_spread_score(G: nx.DiGraph) -> float:
    """
    Shannon entropy of hub locations.
    Well-distributed hubs = resilient to regional disruptions.
    """
    if len(G.nodes) < 2:
        return 50.0

    # Bin nodes into geographic quadrants (India-specific)
    regions: Dict[str, int] = {}
    for node, data in G.nodes(data=True):
        lat = data.get("lat", 20.0)
        lng = data.get("lng", 77.0)
        # Rough India quadrants
        ns = "N" if lat >= 20 else "S"
        ew = "E" if lng >= 77 else "W"
        quadrant = f"{ns}{ew}"
        regions[quadrant] = regions.get(quadrant, 0) + 1

    total = sum(regions.values())
    if total == 0:
        return 50.0

    # Shannon entropy
    entropy = -sum((c / total) * math.log2(c / total) for c in regions.values() if c > 0)
    max_entropy = math.log2(len(regions)) if len(regions) > 1 else 1

    return round((entropy / max_entropy) * 100, 1) if max_entropy > 0 else 50.0


def _buffer_capacity_score(shipments: List[Shipment]) -> float:
    """
    Average slack between ETA and deadline, normalized.
    48h+ buffer = 100, 0h buffer = 0.
    """
    now = datetime.now(timezone.utc)
    buffers = []

    for s in shipments:
        try:
            eta_hrs = (s.eta - now).total_seconds() / 3600
            deadline_hrs = (s.deadline - now).total_seconds() / 3600
            buffer = max(0, deadline_hrs - eta_hrs)
            buffers.append(buffer)
        except Exception:
            buffers.append(4.0)

    if not buffers:
        return 60.0

    avg_buffer = sum(buffers) / len(buffers)
    return round(min(avg_buffer / 48 * 100, 100), 1)


def _recovery_speed_score(disruptions: List[Disruption]) -> float:
    """
    How quickly have past disruptions been mitigated?
    <4h resolution = high score, >24h = low score.
    """
    resolved = [d for d in disruptions if d.status == "resolved" and d.detected_at]
    if not resolved:
        return 75.0  # Default when no history

    recovery_times = []
    for d in resolved:
        if d.estimated_end:
            hours = (d.estimated_end - d.detected_at).total_seconds() / 3600
            recovery_times.append(max(0, hours))

    if not recovery_times:
        return 75.0

    avg_recovery = sum(recovery_times) / len(recovery_times)
    # <2h → 95, 4h → 80, 8h → 60, 12h → 40, 24h → 10
    score = max(0, 100 - avg_recovery * 3.5)
    return round(score, 1)


def _generate_recommendation(weakest_link: str, score: float) -> str:
    recs = {
        "Route Redundancy": (
            f"Route redundancy is at {round(score)}%. "
            "Add 2+ alternative routes for your highest-volume lanes. "
            "Target: pre-negotiate contracts with at least 2 highway options."
        ),
        "Carrier Diversity": (
            f"Carrier concentration is high (score: {round(score)}%). "
            "Diversify by onboarding 1 backup carrier on your top 3 routes. "
            "No single carrier should exceed 40% of shipment volume."
        ),
        "Geographic Spread": (
            f"Hub distribution is imbalanced (score: {round(score)}%). "
            "Consider adding a regional hub in an underserved geographic quadrant "
            "to reduce single-region dependency."
        ),
        "Buffer Capacity": (
            f"Average delivery buffers are tight (score: {round(score)}%). "
            "Increase scheduled delivery windows by 20% for standard shipments "
            "to absorb minor delays without SLA breaches."
        ),
        "Recovery Speed": (
            f"Disruption resolution is slow (score: {round(score)}%). "
            "Define pre-approved rerouting policies for common disruption types "
            "to enable auto-mitigation within 2 hours."
        ),
    }
    return recs.get(weakest_link, f"Improve {weakest_link} to boost network resilience.")


# ─── Main score function ──────────────────────────────────────────────────────

def compute_resilience(
    G: nx.DiGraph,
    shipments: List[Shipment],
    disruptions: List[Disruption],
    trend: List[float],
) -> ResilienceScore:
    """
    Compute the full network resilience score.

    Sub-metric weights:
      Route Redundancy:  25%
      Carrier Diversity: 20%
      Geographic Spread: 20%
      Buffer Capacity:   15%
      Recovery Speed:    20%
    """
    r_redundancy = _route_redundancy_score(G)
    r_diversity = _carrier_diversity_score(shipments)
    r_geo = _geographic_spread_score(G)
    r_buffer = _buffer_capacity_score(shipments)
    r_recovery = _recovery_speed_score(disruptions)

    # Cap all sub-scores
    r_redundancy = min(r_redundancy, 100)
    r_diversity = min(r_diversity, 100)
    r_geo = min(r_geo, 100)
    r_buffer = min(r_buffer, 100)
    r_recovery = min(r_recovery, 100)

    overall = (
        0.25 * r_redundancy +
        0.20 * r_diversity +
        0.20 * r_geo +
        0.15 * r_buffer +
        0.20 * r_recovery
    )
    overall = round(overall, 1)

    breakdown = ResilienceBreakdown(
        route_redundancy=round(r_redundancy, 1),
        carrier_diversity=round(r_diversity, 1),
        geographic_spread=round(r_geo, 1),
        buffer_capacity=round(r_buffer, 1),
        recovery_speed=round(r_recovery, 1),
    )

    scores_dict = {
        "Route Redundancy": r_redundancy,
        "Carrier Diversity": r_diversity,
        "Geographic Spread": r_geo,
        "Buffer Capacity": r_buffer,
        "Recovery Speed": r_recovery,
    }
    weakest = min(scores_dict, key=scores_dict.get)
    recommendation = _generate_recommendation(weakest, scores_dict[weakest])

    return ResilienceScore(
        score=overall,
        breakdown=breakdown,
        weakest_link=weakest,
        recommendation=recommendation,
        trend=trend[-5:],  # Last 5 readings
    )
