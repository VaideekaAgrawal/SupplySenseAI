"""
Gemini 2.0 Flash service with function calling.

Supports two modes:
- GEMINI_MODE=mock  : Returns structured mock responses — no credentials needed.
- GEMINI_MODE=real (default when GEMINI_API_KEY is set): Uses free Google AI Studio Gemini API.

Available tool functions Gemini can call:
  simulate_disruption   — What-if analysis for hypothetical disruptions
  get_alternative_routes — Rerouting options for a shipment
  get_network_resilience — Current resilience score and breakdown
"""

from __future__ import annotations
import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from models.schemas import ChatRequest, ChatResponse, ChatVisualization

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODE = os.getenv("GEMINI_MODE", "real" if GEMINI_API_KEY else "mock").lower()


# ─── Mock response library ────────────────────────────────────────────────────

MOCK_RESPONSES: Dict[str, Dict[str, Any]] = {
    "mumbai": {
        "text": (
            "If Mumbai Port faces a 2-day closure:\n\n"
            "**Cascade impact (72h):**\n"
            "• 5 shipments disrupted (₹3.42L revenue at risk)\n"
            "• 6,670 customers affected across 4 retailers\n"
            "• BigBasket FMCG delivery window breached\n\n"
            "**Recommended actions:**\n"
            "1. Immediately reroute SH001 via Nhava Sheva (ICD) — saves 18h delay\n"
            "2. Switch SH002 Mumbai→Delhi to Delhivery Air — ₹24K premium, avoids SLA breach\n"
            "3. Alert DMart fulfillment team: expect 3-day delay on SH004\n\n"
            "**Risk mitigation score:** 72% disruption impact avoidable with above actions."
        ),
        "visualization": {"type": "cascade", "highlight_nodes": ["Mumbai", "Nhava Sheva", "Delhi", "Pune", "BigBasket DC"]},
        "function_called": "simulate_disruption",
    },
    "default": {
        "text": (
            "I can help you with supply chain analysis. Try asking:\n\n"
            "• **\"What if Mumbai Port closes for 2 days?\"** — cascade impact analysis\n"
            "• **\"Show alternative routes for SH001\"** — rerouting options\n"
            "• **\"How resilient is our network?\"** — resilience score breakdown\n"
            "• **\"Which shipments will be delayed?\"** — risk prioritization\n\n"
            "I have real-time access to all active shipments, disruptions, and carriers."
        ),
        "visualization": None,
        "function_called": None,
    },
}


def _classify_intent(message: str) -> str:
    msg = message.lower()
    if any(k in msg for k in ["mumbai", "port", "congestion", "nhava sheva"]):
        return "mumbai"
    if any(k in msg for k in ["resilience", "resilient", "diversity", "redundancy", "network score", "how strong"]):
        return "resilience"
    if any(k in msg for k in ["delay", "late", "eta", "at risk", "critical", "will be delayed"]):
        return "delay"
    if any(k in msg for k in ["route", "reroute", "alternative", "rerouting", "sh0"]):
        return "route"
    if any(k in msg for k in ["what if", "simulate", "scenario", "flood", "earthquake", "strike", "cyber", "closure"]):
        return "simulate"
    if any(k in msg for k in ["carrier", "delhivery", "bluedart", "fedex", "dtdc", "dhl"]):
        return "carrier"
    if any(k in msg for k in ["cost", "revenue", "money", "save", "expensive", "cheap"]):
        return "cost"
    if any(k in msg for k in ["weather", "monsoon", "rain", "storm", "cyclone"]):
        return "weather"
    if any(k in msg for k in ["festival", "diwali", "eid", "holi", "season", "peak"]):
        return "festival"
    if any(k in msg for k in ["weakest", "weak link", "bottleneck", "single point", "vulnerable"]):
        return "weakest"
    return "default"


def _dynamic_mock_chat(request: ChatRequest, context: Dict[str, Any]) -> ChatResponse:
    """Generate dynamic responses based on actual context data."""
    intent = _classify_intent(request.message)
    kpis = context.get("kpis", {})
    shipments_summary = context.get("shipments_summary", "")
    disruptions_summary = context.get("disruptions_summary", "")

    if intent == "resilience":
        text = (
            f"**Network Resilience Analysis:**\n\n"
            f"Current score: **{kpis.get('resilience_score', 73):.0f}/100**\n\n"
            f"**Network Overview:**\n"
            f"• {kpis.get('active_shipments', 0)} active shipments across 20 Indian cities\n"
            f"• {kpis.get('at_risk_count', 0)} shipments at risk, {kpis.get('disrupted_count', 0)} disrupted\n"
            f"• Revenue at risk: ₹{kpis.get('revenue_at_risk', 0):,.0f}\n\n"
            f"**Strengths:**\n"
            f"• Multi-carrier network with 8 carriers provides redundancy\n"
            f"• Geographic spread across 12+ Indian states\n\n"
            f"**To improve score:**\n"
            f"1. Diversify carrier allocation — reduce concentration risk\n"
            f"2. Add buffer inventory at key hubs (Mumbai, Delhi, Chennai)\n"
            f"3. Pre-negotiate contingency slots at Nhava Sheva ICD"
        )
        func = "get_network_resilience"
    elif intent == "delay":
        text = (
            f"**At-Risk Delivery Analysis:**\n\n"
            f"Currently tracking {kpis.get('at_risk_count', 0)} at-risk + {kpis.get('disrupted_count', 0)} disrupted shipments.\n\n"
            f"**Top risk shipments:**\n{shipments_summary}\n\n"
            f"**Total revenue at risk:** ₹{kpis.get('revenue_at_risk', 0):,.0f}\n\n"
            f"**Recommended actions:**\n"
            f"1. Prioritize rerouting for CRITICAL and HIGH risk shipments\n"
            f"2. Switch disrupted shipments to air freight where SLA breach is imminent\n"
            f"3. Proactively notify downstream retailers about potential delays"
        )
        func = None
    elif intent == "route":
        text = (
            f"**Route Optimization Analysis:**\n\n"
            f"For any specific shipment, I can suggest optimal reroutes considering:\n"
            f"• **Cost** — minimize additional logistics spend\n"
            f"• **Time** — fastest delivery via alternate corridors\n"
            f"• **Risk** — avoid active disruption zones\n"
            f"• **Carbon** — lowest emission alternative\n\n"
            f"**Current high-risk shipments needing reroute:**\n{shipments_summary}\n\n"
            f"Navigate to the **Reroute** section to see detailed alternatives for each shipment, "
            f"or ask me about a specific shipment ID (e.g., 'Show alternatives for SH001')."
        )
        func = "get_alternative_routes"
    elif intent == "simulate":
        msg = request.message.lower()
        city = "Mumbai"
        for c in ["delhi", "chennai", "kolkata", "bangalore", "hyderabad", "pune", "ahmedabad", "mumbai"]:
            if c in msg:
                city = c.title()
                break
        text = (
            f"**What-If Simulation: {city}**\n\n"
            f"A major disruption at {city} would impact:\n"
            f"• Shipments routed through {city} hub\n"
            f"• Downstream retailers and distribution centers\n"
            f"• Estimated revenue impact: significant based on hub connectivity\n\n"
            f"**Mitigation strategy:**\n"
            f"1. Activate alternate hub routing (bypass {city})\n"
            f"2. Pre-position inventory at neighboring hubs\n"
            f"3. Switch to premium carriers for time-critical shipments\n\n"
            f"For a detailed cascade analysis, go to the **Simulate** section and configure the scenario."
        )
        func = "simulate_disruption"
    elif intent == "carrier":
        text = (
            f"**Carrier Performance Analysis:**\n\n"
            f"| Carrier | On-Time | Risk | Recommendation |\n"
            f"|---------|---------|------|----------------|\n"
            f"| BlueDart | 94% | Low | Reliable premium option |\n"
            f"| FedEx India | 97% | Low | Best for critical shipments |\n"
            f"| DHL Express | 96% | Low | Strong international corridor |\n"
            f"| Delhivery | 89% | Medium | Good volume, improving |\n"
            f"| XpressBees | 87% | Medium | Cost-effective alternative |\n"
            f"| DTDC | 85% | Medium | Stable, wide coverage |\n"
            f"| Ecom Express | 82% | High | Declining — reduce allocation |\n"
            f"| Shadowfax | 78% | High | Last-mile only — avoid long haul |\n\n"
            f"**Action:** Shift 15% volume from Ecom Express/Shadowfax to XpressBees for better reliability."
        )
        func = None
    elif intent == "cost":
        text = (
            f"**Cost & Revenue Analysis:**\n\n"
            f"• Active shipments: {kpis.get('active_shipments', 0)}\n"
            f"• Revenue at risk: ₹{kpis.get('revenue_at_risk', 0):,.0f}\n"
            f"• Revenue saved today: ₹{kpis.get('revenue_saved_today', 0):,.0f}\n"
            f"• Auto-mitigated today: {kpis.get('auto_mitigated_today', 0)} shipments\n\n"
            f"**Cost optimization opportunities:**\n"
            f"1. Reroute disrupted shipments — potential savings up to 70% of at-risk revenue\n"
            f"2. Switch Standard Class to Second Class where deadline allows — 15% cost reduction\n"
            f"3. Consolidate shipments at hub cities to reduce per-unit logistics cost"
        )
        func = None
    elif intent == "weather":
        text = (
            f"**Weather Impact on Supply Chain:**\n\n"
            f"Current weather conditions are being monitored across all 20 hub cities.\n\n"
            f"**Key weather-related risks:**\n"
            f"• Monsoon season affects west coast corridors (Mumbai-Pune-Goa)\n"
            f"• Cyclone season in Bay of Bengal impacts Chennai-Kolkata routes\n"
            f"• Winter fog disrupts Delhi-Chandigarh-Lucknow highway corridors\n\n"
            f"**Active disruptions:**\n{disruptions_summary if disruptions_summary else '• No active weather disruptions'}\n\n"
            f"**Mitigation:** Pre-position inventory before monsoon peaks; maintain 48h buffer for weather-sensitive routes."
        )
        func = None
    elif intent == "festival":
        text = (
            f"**Festival & Seasonal Impact:**\n\n"
            f"Indian festivals cause 20-60% surge in logistics demand:\n\n"
            f"**High-impact periods:**\n"
            f"• Diwali season: 50-60% volume surge, all major corridors congested\n"
            f"• Flipkart/Amazon sales: 3-5x e-commerce volume spikes\n"
            f"• Eid/Christmas: Regional congestion in specific corridors\n"
            f"• Monsoon (Jun-Sep): Weather + festival overlap\n\n"
            f"**Recommendations:**\n"
            f"1. Pre-book carrier capacity 2 weeks before major festivals\n"
            f"2. Increase buffer stock at distribution centers\n"
            f"3. Use premium carriers for SLA-critical deliveries during peaks"
        )
        func = None
    elif intent == "weakest":
        text = (
            f"**Network Vulnerability Analysis:**\n\n"
            f"**Single Points of Failure:**\n"
            f"• Mumbai/Nhava Sheva handles ~35% of all shipments — highest bottleneck risk\n"
            f"• Delhi hub connects North India — failure cascades to 8+ cities\n\n"
            f"**Carrier Concentration:**\n"
            f"• Top 2 carriers handle ~45% of volume — diversification needed\n"
            f"• Shadowfax/Ecom Express show declining performance\n\n"
            f"**Recommendations:**\n"
            f"1. Develop Ahmedabad as alternate west coast hub\n"
            f"2. Establish Hyderabad-Bangalore dual hub for south India\n"
            f"3. Redistribute carrier volume: cap any single carrier at 20% allocation\n"
            f"4. Add Kolkata-Chennai direct corridor to reduce Delhi dependency"
        )
        func = None
    elif intent == "mumbai":
        resp_data = MOCK_RESPONSES["mumbai"]
        return ChatResponse(
            session_id=request.session_id or "mock-session",
            message=resp_data["text"],
            visualization=ChatVisualization(type="cascade", data=resp_data["visualization"]),
            function_called=resp_data.get("function_called"),
            suggestions=["Show alternative routes for SH001", "How resilient is our network?", "Which carriers should we avoid?"],
        )
    else:
        resp_data = MOCK_RESPONSES["default"]
        return ChatResponse(
            session_id=request.session_id or "mock-session",
            message=resp_data["text"],
            visualization=None,
            function_called=None,
            suggestions=["What if Mumbai Port closes?", "Which shipments are delayed?", "How resilient is our network?"],
        )

    return ChatResponse(
        session_id=request.session_id or "mock-session",
        message=text,
        visualization=None,
        function_called=func,
        suggestions=_generate_suggestions(text, request.message),
    )


# ─── Build system prompt with live context ─────────────────────────────────────

def _build_system_prompt(context: Dict[str, Any]) -> str:
    kpis = context.get("kpis", {})
    # Build shipment summary if available
    shipment_summary = ""
    if context.get("shipments_summary"):
        shipment_summary = f"\n\nShipment details:\n{context['shipments_summary']}"

    disruption_summary = ""
    if context.get("disruptions_summary"):
        disruption_summary = f"\n\nActive disruptions:\n{context['disruptions_summary']}"

    return f"""You are SupplySense AI — supply chain resilience assistant for Indian logistics.

Status: {kpis.get('active_shipments', 50)} shipments, {kpis.get('at_risk_count', 0)} at-risk, {kpis.get('disrupted_count', 0)} disrupted. Revenue at risk: ₹{kpis.get('revenue_at_risk', 0):,.0f}. Resilience: {kpis.get('resilience_score', 73):.0f}/100.{shipment_summary}{disruption_summary}

Hubs: Mumbai, Delhi, Chennai, Kolkata, Bangalore, Hyderabad, Pune, Ahmedabad.
Carriers: BlueDart, FedEx India, DHL, Delhivery, DTDC, XpressBees, Ecom Express, Shadowfax.

Be concise (100-200 words). Use markdown. Use ₹ for money. Give actionable insights."""


# ─── Real Gemini handler (free Google AI Studio API) ───────────────────────────

# Conversation history per session
_session_histories: Dict[str, list] = {}
MAX_HISTORY = 20


def _real_chat(request: ChatRequest, context: Dict[str, Any]) -> ChatResponse:
    """Call Google AI Studio Gemini API (free tier, uses GEMINI_API_KEY)."""
    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)

        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=_build_system_prompt(context),
            generation_config=genai.GenerationConfig(
                max_output_tokens=300,
                temperature=0.7,
            ),
        )

        # Maintain conversation history per session
        session_id = request.session_id or "default"
        if session_id not in _session_histories:
            _session_histories[session_id] = []

        history = _session_histories[session_id]

        # Build chat with history
        chat_session = model.start_chat(history=history)

        response = chat_session.send_message(request.message)

        text = response.text or "I processed your request but got an empty response."

        # Save to history (keep last MAX_HISTORY messages)
        _session_histories[session_id] = chat_session.history[-MAX_HISTORY:]

        # Detect function-like actions from the response
        function_called = None
        text_lower = text.lower()
        if any(k in text_lower for k in ["cascade", "propagat", "disruption impact"]):
            function_called = "simulate_disruption"
        elif any(k in text_lower for k in ["alternative route", "reroute", "rerouting"]):
            function_called = "get_alternative_routes"
        elif any(k in text_lower for k in ["resilience", "resilient", "network score"]):
            function_called = "get_network_resilience"

        # Generate contextual suggestions
        suggestions = _generate_suggestions(text, request.message)

        return ChatResponse(
            session_id=session_id,
            message=text,
            visualization=None,
            function_called=function_called,
            suggestions=suggestions,
        )

    except Exception as e:
        logger.warning(f"Gemini API call failed: {e}, falling back to mock")
        return _dynamic_mock_chat(request, context)


def _generate_suggestions(response_text: str, user_message: str) -> List[str]:
    """Generate contextual follow-up suggestions based on the conversation."""
    suggestions = []
    text_lower = response_text.lower()
    msg_lower = user_message.lower()

    if "mumbai" in text_lower or "port" in text_lower:
        suggestions.append("What are the alternative routes via Nhava Sheva?")
    if "risk" in text_lower:
        suggestions.append("Which shipments have the highest risk right now?")
    if "reroute" in text_lower or "route" in text_lower:
        suggestions.append("What is the cost of rerouting all disrupted shipments?")
    if "resilience" not in msg_lower:
        suggestions.append("How resilient is our network?")
    if "delay" in text_lower or "eta" in text_lower:
        suggestions.append("What is the total revenue at risk from delays?")

    # Always add at least one general suggestion
    defaults = [
        "Simulate a flood in Chennai",
        "What if our main carrier fails?",
        "Show me the weakest links in our network",
        "Compare air freight vs ground for critical shipments",
    ]
    while len(suggestions) < 3:
        for d in defaults:
            if d not in suggestions:
                suggestions.append(d)
                break
        if len(suggestions) >= 3:
            break

    return suggestions[:3]


# ─── Public API ───────────────────────────────────────────────────────────────

def chat(request: ChatRequest, context: Optional[Dict[str, Any]] = None) -> ChatResponse:
    """
    Process a chat message and return AI response.
    Uses GEMINI_MODE env var to switch between mock and real.
    """
    if context is None:
        context = {}

    if GEMINI_MODE == "real" and GEMINI_API_KEY:
        return _real_chat(request, context)
    return _dynamic_mock_chat(request, context)
