"""
Resilience router — network-wide resilience scoring.

Endpoints:
  GET /resilience         — Current resilience score with sub-metric breakdown
  GET /resilience/history — Historical trend data (last 7 days)
"""

from fastapi import APIRouter
from typing import List, Dict, Any

from services.data_store import DataStore
from services.resilience_engine import compute_resilience
from models.schemas import ResilienceScore

router = APIRouter()
store = DataStore.get()

# In-memory trend (initialized with realistic values for demo)
_resilience_trend: List[float] = [68.0, 71.0, 70.5, 74.2, 72.8, 73.5, 73.0]


@router.get("", response_model=ResilienceScore)
def get_resilience():
    """
    Compute and return current network resilience score.
    Includes sub-metric breakdown and weakest link identification.
    """
    G = store.get_graph()
    shipments = store.get_shipments()
    disruptions = store.get_disruptions()
    result = compute_resilience(G, shipments, disruptions, _resilience_trend)
    _resilience_trend.append(result.score)
    return result


@router.get("/history")
def get_resilience_history() -> Dict[str, Any]:
    """Return the last 7 resilience score readings for trend visualization."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    data_points = []
    for i, score in enumerate(_resilience_trend[-7:]):
        ts = now - timedelta(days=(len(_resilience_trend[-7:]) - 1 - i))
        data_points.append({
            "timestamp": ts.isoformat(),
            "score": score,
            "label": ts.strftime("%b %d"),
        })

    return {
        "trend": data_points,
        "delta_7d": round(_resilience_trend[-1] - _resilience_trend[0], 1) if len(_resilience_trend) >= 2 else 0,
    }
