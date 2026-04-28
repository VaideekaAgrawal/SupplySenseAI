# SupplySense AI — Hackathon Presentation
## Slide-by-Slide Content for PowerPoint/Google Slides

---

## Slide 1: Title Slide
**SupplySense AI**
*Resilient Logistics & Dynamic Supply Chain Optimization*

- Team: [Your Team Name]
- Built with: Google Gemini AI · Google Cloud Run · Next.js · FastAPI · XGBoost + SHAP

---

## Slide 2: Brief About the Solution
**What is SupplySense AI?**

An AI-powered supply chain intelligence platform that **predicts disruptions before they cascade** and **dynamically optimizes routes** in real-time.

**Core Capabilities:**
- 🔍 Real-time disruption detection (weather, port closures, strikes, floods)
- 🌊 Cascade impact analysis — see how one disruption ripples across the entire network
- 🚚 Multi-objective route optimization (cost, time, risk, carbon)
- 🤖 Gemini 2.0 Flash AI assistant for natural language supply chain queries
- 📊 ML-powered risk scoring with XGBoost + SHAP explainability
- 🏗️ Network resilience scoring across 20 Indian cities

---

## Slide 3: The Opportunity
**$12 Billion** — cost of a single 6-day port closure cascading globally (2021 Suez Canal)

**The Problem Today:**
- 85% of supply chain disruptions are detected **after** delays occur
- Mid-market logistics companies ($10M-$500M) can't afford SAP/Oracle solutions
- No tool connects disruption detection → cascade prediction → automated rerouting

**Market Opportunity:**
- Global supply chain management market: **$19.3B** (2023) → **$31B** (2028)
- Indian logistics market: **$380B**, growing at 10% CAGR
- 90% of Indian logistics companies lack AI-powered disruption visibility

---

## Slide 4: Differentiation — What Makes Us Unique
**SupplySense AI vs. Existing Solutions**

| Feature | SAP/Oracle | Flexport | **SupplySense AI** |
|---------|-----------|----------|-------------------|
| Cascade Analysis | ❌ | ❌ | ✅ BFS graph propagation |
| AI Chat Assistant | ❌ | Basic | ✅ Gemini 2.0 Flash |
| Risk Explainability | ❌ | ❌ | ✅ SHAP + XGBoost |
| Multi-objective Reroute | Limited | Basic | ✅ Cost/Time/Risk/Carbon |
| Setup Time | 18 months | Weeks | **Minutes** |
| Cost | $500K+ | $50K+ | **Free tier** (Google Cloud) |
| India-specific Context | ❌ | ❌ | ✅ Festivals, monsoon, ports |

**Key Differentiator:** We're the only tool that shows the **blast radius** of a disruption before it happens.

---

## Slide 5: Problem-Solving Approach
**Three-Layer Intelligence Architecture:**

1. **Detect** — Real-time disruption feeds (GDACS, ReliefWeb, OpenWeatherMap)
   - Automatic severity classification
   - Geo-matching to active shipments

2. **Predict** — ML + Graph-based cascade analysis
   - XGBoost risk scoring with 11 features
   - BFS cascade propagation across supply chain graph
   - SHAP explainability: "Why is this shipment high risk?"

3. **Act** — Dynamic route optimization + AI recommendations
   - Multi-objective optimization (Pareto-optimal routes)
   - Gemini AI chat for natural language what-if analysis
   - Auto-priority assignment and deadline tracking

---

## Slide 6: USP (Unique Selling Proposition)
**"See the ripple before it spreads."**

SupplySense AI is the **first platform** that combines:

✅ **Cascade Blindness Cure** — Visualize how a port closure in Mumbai affects 5 shipments, ₹3.4L revenue, and 6,670 customers across 4 retailers — in under 2 seconds

✅ **Explainable AI Risk** — Not just "High Risk" — our SHAP-powered explanations show exactly WHY (distance: 32%, cargo value: 18%, weather: 15%, disruption boost: 35%)

✅ **Natural Language Intelligence** — Ask "What if Chennai floods?" and get actionable cascade analysis powered by Gemini 2.0 Flash with real-time network context

✅ **India-First Design** — Festival calendar awareness (Diwali surges), monsoon routing, INR-native, 20 Indian city hubs

---

## Slide 7: Features List
**Platform Features:**

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Command Center Dashboard** | KPIs, live disruption cards, filterable shipment table with pagination |
| 2 | **Cascade Impact Analysis** | BFS graph traversal showing disruption propagation with revenue/customer impact |
| 3 | **Smart Route Optimization** | Multi-objective rerouting with cost/time/risk/carbon weight sliders |
| 4 | **AI Chat (Gemini 2.0 Flash)** | Natural language supply chain queries with real-time context |
| 5 | **Network Resilience Scoring** | Graph-based resilience with diversity, redundancy, and geographic spread metrics |
| 6 | **ML Risk Scoring** | XGBoost model with SHAP explainability, 11-feature risk assessment |
| 7 | **Disruption Simulator** | What-if scenario testing for any city, disruption type, and severity |
| 8 | **Node Intelligence** | Per-city analytics with throughput, festival calendar, and weather data |
| 9 | **Shipment Creator** | Add new shipments with auto-risk-scoring and priority assignment |
| 10 | **Real-time Weather** | OpenWeatherMap integration for live conditions at all hub cities |

---

## Slide 8: Process Flow / Use-Case Diagram

```
[Disruption Detected] → [Risk Scoring Engine] → [Cascade Analysis]
        ↓                       ↓                       ↓
  GDACS/ReliefWeb         XGBoost + SHAP          BFS Propagation
  OpenWeatherMap          11 features              Revenue impact
                          Explainability           Customer count
        ↓                       ↓                       ↓
[Dashboard Alerts] ←→ [AI Chat Assistant] ←→ [Route Optimizer]
                          Gemini 2.0 Flash       Multi-objective
                          What-if analysis       Pareto-optimal
                                ↓
                    [Accept Route → Rescore All]
```

**User Flow:**
1. User opens Dashboard → sees KPIs, disruptions, and at-risk shipments
2. Clicks disruption → sees cascade impact tree (affected shipments, revenue, customers)
3. Navigates to Reroute → adjusts cost/time/risk/carbon weights → sees 3 optimal routes
4. Accepts route → system rescores all shipments and auto-removes delivered ones
5. Uses AI Chat → asks "What if Mumbai port closes?" → gets actionable cascade analysis

---

## Slide 9: Wireframes / Mockups
*(Include screenshots of your running application)*

**Key Screens to Show:**
1. **Dashboard** — KPI bar + disruption cards + shipment table (with filters, pagination, priority badges)
2. **Cascade Impact** — Disruption hero card + BFS cascade tree + impact metrics
3. **Route Optimizer** — Weight sliders + 3 route options + before/after comparison
4. **AI Chat** — Gemini conversation with real-time supply chain context
5. **Node Detail** — City analytics with weather, festivals, throughput
6. **Disruption Simulator** — Configure what-if scenarios

---

## Slide 10: Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                    Frontend                          │
│         Next.js 14 + React 18 + Tailwind CSS        │
│    Dashboard │ Cascade │ Reroute │ Chat │ Simulate   │
│              Leaflet Maps (Dark Theme)               │
└──────────────────────┬──────────────────────────────┘
                       │ REST API (JSON)
                       ▼
┌─────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                  │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐           │
│  │ Shipments│ │ Cascade  │ │ Optimize  │           │
│  │ Router   │ │ Engine   │ │ Engine    │           │
│  └──────────┘ └──────────┘ └───────────┘           │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐           │
│  │ Gemini   │ │Resilience│ │ Risk      │           │
│  │ Service  │ │ Engine   │ │ Scorer    │           │
│  └──────────┘ └──────────┘ └───────────┘           │
│          │              │            │               │
│  ┌───────▼──┐   ┌───────▼──┐  ┌─────▼──────┐      │
│  │Gemini 2.0│   │ NetworkX │  │XGBoost+SHAP│      │
│  │Flash API │   │  Graph   │  │  ML Model  │      │
│  └──────────┘   └──────────┘  └────────────┘      │
└──────────────────────┬──────────────────────────────┘
                       │
    ┌──────────┬───────┼────────┬──────────┐
    ▼          ▼       ▼        ▼          ▼
┌────────┐┌────────┐┌──────┐┌────────┐┌────────┐
│ GDACS  ││Relief  ││OpenWx││ Gemini ││ Google │
│  API   ││Web API ││ API  ││  API   ││Cloud   │
│(Free)  ││(Free)  ││(Free)││(Free)  ││Run     │
└────────┘└────────┘└──────┘└────────┘└────────┘
```

---

## Slide 11: Technologies Used

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 14, React 18, TypeScript | Server-side rendered UI |
| **Styling** | Tailwind CSS (Dark Theme) | Responsive, accessible design |
| **Maps** | Leaflet + CartoDB Dark Tiles | Interactive supply chain visualization |
| **Backend** | FastAPI (Python) | High-performance async API |
| **AI/Chat** | Google Gemini 2.0 Flash | Natural language supply chain assistant |
| **ML Model** | XGBoost + SHAP | Risk scoring with explainability |
| **Graph** | NetworkX | Cascade analysis + resilience scoring |
| **Data Feeds** | GDACS, ReliefWeb, OpenWeatherMap | Real-time disruption & weather data |
| **Deployment** | Google Cloud Run + Docker | Serverless, auto-scaling |
| **Data** | Pydantic v2 + In-Memory Store | Fast prototyping, schema validation |

**Google Technologies Used:** Gemini 2.0 Flash API, Google Cloud Run, Google Cloud Build

---

## Slide 12: Implementation Cost

**Development Cost: $0 (Hackathon)**

**Production Cost (Monthly):**

| Service | Free Tier | Est. Cost (Scale) |
|---------|-----------|-------------------|
| Google Cloud Run (Backend) | 2M requests free | ~$15/month |
| Gemini 2.0 Flash API | 1,500 req/day free | $0 (under free tier) |
| GDACS + ReliefWeb APIs | Unlimited free | $0 |
| OpenWeatherMap API | 1,000 calls/day free | $0 |
| Vercel (Frontend) | Free hobby tier | $0-$20/month |
| **Total** | | **$0 - $35/month** |

**Key Advantage:** Entire platform runs on **Google's free tier** — no cloud costs during demo and early adoption.

---

## Slide 13: Future Development Roadmap

**Phase 1 — Near-Term (1-3 months):**
- 🔐 Firebase Authentication + role-based access control
- 📱 Flutter mobile app for on-the-go supply chain monitoring
- 🗄️ Cloud Firestore for persistent data storage
- 📊 Historical analytics with trend prediction

**Phase 2 — Medium-Term (3-6 months):**
- 🛰️ IoT integration (GPS trackers, temperature sensors)
- 🤖 Predictive disruption detection using historical ML models
- 📋 Automated carrier SLA monitoring and scoring
- 🌍 Multi-country expansion (SE Asia, Middle East corridors)

**Phase 3 — Long-Term (6-12 months):**
- 🔗 Blockchain-based shipment provenance tracking
- 📑 Automated insurance claim filing for disruption losses
- 🏪 Supplier risk scoring and diversification recommendations
- 🧠 Reinforcement learning for continuous route optimization

---

## Slide 14: Thank You / Demo

**SupplySense AI**
*"See the ripple before it spreads."*

🔗 **Live Demo:** [Show running application]
📊 **API Docs:** [backend-url]/docs
💻 **Tech Stack:** Gemini 2.0 Flash · Google Cloud Run · Next.js · FastAPI · XGBoost

**Questions?**
