"""
SupplySense AI — FastAPI application entry point.

Architecture:
  - CORS configured for Next.js frontend (localhost:3000 in dev)
  - All routers mounted under /api/v1
  - In-memory data store (no DB needed for demo)
  - Health check at /health

Run: uvicorn main:app --reload --port 8000
"""

from __future__ import annotations
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()  # Must load .env BEFORE importing routers/services that read env vars

from routers import shipments, cascade, optimization, chat, resilience, alerts, nodes
from services.data_store import DataStore
from services.resilience_engine import compute_resilience
from models.schemas import KPIData

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ─── Startup/shutdown lifecycle ───────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    logger.info("Starting SupplySense AI backend…")
    store = DataStore.get()
    logger.info(f"Data store ready: {len(store.get_shipments())} shipments, {len(store.get_disruptions())} disruptions")

    # Pre-compute resilience score so first request is fast
    try:
        G = store.get_graph()
        result = compute_resilience(G, store.get_shipments(), store.get_disruptions(), [73.0])
        logger.info(f"Network resilience pre-computed: {result.score}/100 ({result.weakest_link} is weakest)")
    except Exception as e:
        logger.warning(f"Resilience pre-compute failed (non-fatal): {e}")

    yield
    logger.info("SupplySense AI backend shutting down.")


# ─── App factory ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="SupplySense AI",
    description="Smart Supply Chain Resilience & Dynamic Optimization API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────

cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
cors_origins = [o.strip() for o in cors_origins_raw.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────

PREFIX = "/api/v1"

app.include_router(shipments.router, prefix=f"{PREFIX}/shipments", tags=["Shipments"])
app.include_router(cascade.router, prefix=f"{PREFIX}/cascade", tags=["Cascade"])
app.include_router(optimization.router, prefix=f"{PREFIX}/optimize", tags=["Optimization"])
app.include_router(chat.router, prefix=f"{PREFIX}/chat", tags=["Chat"])
app.include_router(resilience.router, prefix=f"{PREFIX}/resilience", tags=["Resilience"])
app.include_router(alerts.router, prefix=f"{PREFIX}/alerts", tags=["Alerts"])
app.include_router(nodes.router, prefix=f"{PREFIX}", tags=["Nodes", "Simulation", "Festivals"])


# ─── Core endpoints ───────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    """Service health probe — used by Cloud Run and load balancers."""
    return {"status": "ok", "service": "supplysense-ai", "version": "1.0.0"}


@app.get(f"{PREFIX}/kpis", response_model=KPIData, tags=["Dashboard"])
def get_kpis():
    """
    Dashboard KPI summary — called on every page load.
    Returns aggregated metrics from the in-memory data store.
    """
    store = DataStore.get()
    return store.get_kpis()


@app.get(f"{PREFIX}/disruptions", tags=["Disruptions"])
def list_disruptions():
    """List all active disruptions."""
    store = DataStore.get()
    return [d.model_dump() for d in store.get_disruptions()]


@app.get(f"{PREFIX}/disruptions/{{disruption_id}}", tags=["Disruptions"])
def get_disruption(disruption_id: str):
    """Get a specific disruption by ID."""
    from fastapi import HTTPException
    store = DataStore.get()
    disruption = store.get_disruption(disruption_id)
    if not disruption:
        raise HTTPException(status_code=404, detail=f"Disruption {disruption_id} not found")
    return disruption.model_dump()


@app.get(f"{PREFIX}/weather/{{city}}", tags=["Weather"])
async def get_city_weather(city: str):
    """Get LIVE weather for an Indian city. Uses OpenWeatherMap when available."""
    from services.weather_service import fetch_weather
    from services.real_data_loader import CITIES
    city_key = next((c for c in CITIES if c.lower() == city.lower()), None)
    if not city_key:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"City '{city}' not found")
    info = CITIES[city_key]
    return await fetch_weather(info["lat"], info["lng"], city_key)


@app.get(f"{PREFIX}/weather", tags=["Weather"])
async def get_all_weather():
    """Get LIVE weather for all tracked cities."""
    store = DataStore.get()
    return store._weather_cache


@app.get(f"{PREFIX}/disaster-feed", tags=["Disruptions"])
async def get_disaster_feed():
    """Get LIVE disaster events from GDACS + ReliefWeb APIs."""
    from services.disruption_feed import fetch_all_disruptions
    return await fetch_all_disruptions()


@app.get(f"{PREFIX}/data-sources", tags=["System"])
def get_data_sources():
    """Show which data sources are live vs estimated."""
    import os
    store = DataStore.get()
    live_weather = sum(1 for wx in store._weather_cache.values() if wx.get("is_live", False))
    live_disasters = sum(1 for d in store._disaster_feed if d.get("is_live", False))
    return {
        "weather": {
            "source": "OpenWeatherMap" if os.getenv("WEATHER_MODE") == "real" else "Heuristic estimate",
            "live_cities": live_weather,
            "total_cities": len(store._weather_cache),
            "api_key_set": bool(os.getenv("OPENWEATHER_API_KEY")),
        },
        "disasters": {
            "source": "GDACS + ReliefWeb (UN)",
            "live_events": live_disasters,
            "total_events": len(store._disaster_feed),
        },
        "shipments": {
            "total": len(store.shipments),
            "risk_source": "XGBoost ML + live weather",
        },
        "disruptions": {
            "total": len(store.disruptions),
            "from_real_disasters": sum(1 for d in store.disruptions.values() if "[LIVE]" in d.title),
            "from_weather": sum(1 for d in store.disruptions.values() if "[EST]" in d.title or "[LIVE]" in d.title),
        },
    }
