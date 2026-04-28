"""
Chat router — Gemini 2.0 Flash AI chat with function calling.

Endpoints:
  POST /chat  — Send message, receive AI-powered response with optional visualization
"""

from fastapi import APIRouter
from services.data_store import DataStore
from services.gemini_service import chat
from models.schemas import ChatRequest, ChatResponse

router = APIRouter()
store = DataStore.get()


@router.post("", response_model=ChatResponse)
def send_message(request: ChatRequest):
    """
    Process a chat message via Gemini 2.0 Flash.
    Provides real-time supply chain context to the AI.
    """
    kpis = store.get_kpis()
    disruptions = store.get_disruptions()
    shipments = store.get_shipments()

    # Build concise summaries for context
    top_risk = sorted(shipments, key=lambda s: s.risk_score, reverse=True)[:10]
    shipments_summary = "\n".join(
        f"- {s.id}: {s.origin.city}→{s.destination.city}, risk={s.risk_score:.0f}, status={s.status}, carrier={s.carrier}, revenue=₹{s.revenue:,.0f}"
        for s in top_risk
    )

    disruptions_summary = "\n".join(
        f"- {d.id}: {d.title} at {d.location.city} (severity={d.severity:.0%}, status={d.status}, affecting {len(d.affected_shipment_ids)} shipments)"
        for d in disruptions
    )

    context = {
        "kpis": kpis,
        "active_disruptions": len([d for d in disruptions if d.status == "active"]),
        "shipments_summary": shipments_summary,
        "disruptions_summary": disruptions_summary,
    }
    return chat(request, context)
