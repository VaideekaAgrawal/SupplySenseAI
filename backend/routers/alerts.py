"""
Alerts router — real-time supply chain alerts.

Endpoints:
  GET  /alerts          — List alerts (optionally filter unread only)
  POST /alerts/{id}/read — Mark an alert as read
"""

from fastapi import APIRouter, Query
from typing import Optional

from services.data_store import DataStore
from models.schemas import AlertListResponse

router = APIRouter()
store = DataStore.get()


@router.get("", response_model=AlertListResponse)
def list_alerts(
    unread_only: bool = Query(False, description="Return only unread alerts"),
):
    """List active supply chain alerts."""
    alerts = store.get_alerts()
    if unread_only:
        alerts = [a for a in alerts if not a.read]
    return AlertListResponse(
        alerts=alerts,
        total=len(alerts),
        unread=len([a for a in alerts if not a.read]),
    )


@router.post("/{alert_id}/read")
def mark_alert_read(alert_id: str):
    """Mark an alert as read."""
    updated = store.mark_alert_read(alert_id)
    if not updated:
        # Alert not found — return 200 anyway (idempotent)
        return {"id": alert_id, "read": True}
    return {"id": alert_id, "read": True}
