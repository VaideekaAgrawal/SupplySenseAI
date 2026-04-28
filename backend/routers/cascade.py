"""
Cascade router — compute and simulate cascade propagation.

Endpoints:
  GET  /cascade/{disruptionId}  — Cascade tree for an existing disruption
  POST /cascade/simulate        — What-if simulation for a hypothetical disruption
"""

from fastapi import APIRouter, HTTPException
from typing import Any, Dict

from services.data_store import DataStore
from services.cascade_engine import (
    compute_cascade_for_disruption,
    simulate_disruption,
    cascade_to_dict,
)
from models.schemas import SimulateDisruptionRequest, CascadeResult

router = APIRouter()
store = DataStore.get()


@router.get("/{disruption_id}")
def get_cascade(disruption_id: str) -> Dict[str, Any]:
    """
    Return the pre-computed cascade tree for an existing disruption.
    Falls back to live BFS propagation if cascade not pre-computed.
    """
    disruption = store.get_disruption(disruption_id)
    if not disruption:
        raise HTTPException(status_code=404, detail=f"Disruption {disruption_id} not found")

    result = compute_cascade_for_disruption(disruption, store)
    return cascade_to_dict(result)


@router.post("/simulate")
def simulate_cascade(request: SimulateDisruptionRequest) -> Dict[str, Any]:
    """
    Run a what-if simulation for a hypothetical disruption.
    Does NOT persist the result — for analysis only.
    """
    result = simulate_disruption(request, store)
    return cascade_to_dict(result)
