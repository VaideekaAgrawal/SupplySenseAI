"""
Route optimization router — multi-objective rerouting.

Endpoints:
  POST /optimize/routes  — Generate top-3 alternatives for a shipment
  POST /optimize/accept  — Accept a recommended route (updates shipment status)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict

from services.data_store import DataStore
from services.route_optimizer import optimize_routes
from models.schemas import OptimizeRoutesResponse, OptimizeRoutesRequest

router = APIRouter()
store = DataStore.get()


@router.post("/routes", response_model=OptimizeRoutesResponse)
def get_optimized_routes(request: OptimizeRoutesRequest):
    """
    Generate top-3 route alternatives optimized by user-specified weights.
    Weights are normalized to sum to 1.0 internally.
    """
    shipment = store.get_shipment(request.shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment {request.shipment_id} not found")

    disruptions = store.get_disruptions()
    weights = request.weights or {"cost": 0.25, "time": 0.35, "carbon": 0.15, "risk": 0.25}

    return optimize_routes(shipment, weights=weights, active_disruptions=disruptions)


class AcceptRouteRequest(BaseModel):
    shipment_id: str
    route_id: str


@router.post("/accept")
def accept_route(request: AcceptRouteRequest):
    """
    Accept the recommended reroute for a shipment.
    Updates shipment status to 'rerouted' and rescores all shipments.
    """
    shipment = store.get_shipment(request.shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment {request.shipment_id} not found")

    shipment.status = "rerouted"
    store.update_shipment(shipment)
    # Rescore all shipments to reflect the change
    store.rescore_all_shipments()
    return {
        "shipment_id": request.shipment_id,
        "route_id": request.route_id,
        "status": "rerouted",
        "message": f"Route {request.route_id} accepted. Shipment {request.shipment_id} marked as rerouted.",
    }
