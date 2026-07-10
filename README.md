# 🚀 SupplySense AI — AI-Powered Supply Chain Intelligence Platform

> **"We don't just detect disruptions — we show you their future, and rewrite it."**

SupplySense AI is a comprehensive, production-ready supply chain intelligence platform that **predicts disruptions before they cascade** and **dynamically optimizes routes** in real-time across India's logistics network.

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue?logo=react&logoColor=white)](https://react.dev/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=nextjs&logoColor=white)](https://nextjs.org/)
[![XGBoost](https://img.shields.io/badge/XGBoost-92.25%25_Accuracy-brightgreen)](https://xgboost.readthedocs.io/)

---

## 📊 Key Metrics

| Metric | Achievement |
|--------|-------------|
| **ML Model Accuracy** | 92.25% |
| **ROC-AUC Score** | 0.9821 |
| **Cross-Validation Stability** | 0.9804 ± 0.0021 (5-fold) |
| **API Endpoints** | 25+ |
| **Test Coverage** | 80 tests (100% passing) |
| **Test Categories** | Unit, Integration, ML, Edge Cases |
| **Infrastructure Cost** | $0/month (free tier) |
| **Hub Cities Covered** | 20 across India |
| **Live Data Sources** | 3 (GDACS, ReliefWeb, OpenWeatherMap) |
| **Indian Carriers Modeled** | 8 |
| **Festivals Tracked** | 24+ (2025–2027) |
| **Setup Time** | Minutes (vs. 18+ months for enterprise solutions) |

---

## 🎯 What's the Problem?

### Cascade Blindness: The Supply Chain Crisis
- **85%** of supply chain disruptions are detected **after** delays occur
- **90%** of Indian logistics companies lack AI-powered disruption visibility
- A single delayed shipment spreads like a ripple — cascading across warehouses, retailers, and customers
- **$12 Billion** — cost of a single 6-day port closure cascading globally (2021 Suez Canal incident)
- Mid-market companies ($10M–$500M) cannot afford SAP/Oracle solutions ($500K+ setup)

### SupplySense AI Solves This By:
1. ✅ **Predicting risk** before cascades begin (92% accuracy)
2. ✅ **Showing impact** using graph-based cascade analysis
3. ✅ **Explaining decisions** with SHAP-powered transparency
4. ✅ **Auto-rerouting** with multi-objective optimization
5. ✅ **Costing $0/month** (vs. $500K+ enterprise platforms)

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────┐
│         Frontend (Next.js 14 + React 18)        │
│    Dashboard │ Cascade │ Reroute │ Chat │...    │
│            Leaflet Maps (Dark Theme)            │
└──────────────────────┬──────────────────────────┘
                       │ REST API (JSON)
                       ▼
┌─────────────────────────────────────────────────┐
│       Backend (FastAPI on Google Cloud Run)     │
│  7 Routers × 25+ Endpoints × 7 Services        │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐     │
│  │ Risk     │ │ Cascade  │ │ Route      │     │
│  │ Scorer   │ │ Engine   │ │ Optimizer  │     │
│  └──────────┘ └──────────┘ └────────────┘     │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐     │
│  │ Gemini   │ │Resilience│ │ Disruption │     │
│  │ Service  │ │ Engine   │ │ Feed       │     │
│  └──────────┘ └──────────┘ └────────────┘     │
└──────────────────────┬──────────────────────────┘
                       │
    ┌──────────┬───────┼────────┬──────────┐
    ▼          ▼       ▼        ▼          ▼
┌────────┐┌────────┐┌──────┐┌────────┐┌────────┐
│ GDACS  ││Relief  ││OpenWx││ Gemini ││ Google │
│ (Free) ││Web     ││ API  ││  API   ││ Cloud  │
└────────┘└────────┘└──────┘└────────┘└────────┘
```

---

## ⭐ Key Features

### 1. **Live Supply Chain Command Center (Dashboard)**
- 6 live KPIs: Active Shipments, At Risk, Disrupted, Revenue at Risk, Resilience Score, Revenue Saved
- Real-time disruption cards with severity & cascade preview
- Top 5 high-risk shipments with auto-generated reroutes
- Interactive maps with color-coded risk levels
- Searchable, filterable shipment table with pagination

### 2. **Cascading Impact Engine** (HERO FEATURE)
- BFS graph traversal from disruption source through supply chain network
- Exponential decay: impact reduces 15% per depth level
- Per-node metrics: delay hours, revenue at risk, customers affected
- Interactive cascade tree visualization
- 48-hour propagation window analysis

### 3. **Multi-Objective Route Optimizer**
- 3 intelligent route alternatives per shipment
- Real-time weight sliders for cost ↔ time ↔ carbon ↔ risk
- Before/after comparison with savings breakdown
- One-click accept & auto-rescore all shipments
- Recommendations in plain English

### 4. **AI Chat Assistant (Gemini 2.5 Flash)**
- Natural language supply chain queries
- Context-aware responses with live KPIs
- 10+ intent categories (resilience, delay, route, simulate, carrier, cost, etc.)
- Multi-turn conversation history
- Scenario chips for quick demo setups

### 5. **What-If Disruption Simulator**
- Select any of 20 Indian cities as disruption target
- 7 disruption types: congestion, weather, strike, infrastructure, flood, earthquake, cyber attack
- Adjustable severity (10%–100%) and duration (6h–7d)
- See cascade impact with mitigation recommendations
- Network impact map with highlighted affected nodes

### 6. **Network Resilience Score**
- Composite 0–100 score measuring network resilience
- 5 sub-metrics:
  - Route Redundancy (% of OD pairs with 2+ vertex-disjoint paths)
  - Carrier Diversity (Herfindahl–Hirschman Index)
  - Geographic Spread (Shannon entropy)
  - Buffer Capacity (slack between ETA and deadline)
  - Recovery Speed (historical resolution time)
- Weakest link identification with improvement recommendations
- 7-day trend history

### 7. **Port/Node Risk Intelligence**
- Deep analysis for all 20 logistics hub cities
- Risk factor breakdown: weather, festival, disaster, bottleneck, carriers, disruptions
- Festival/seasonal impact overlay
- Betweenness centrality for bottleneck detection
- Interactive map + sortable table views

### 8. **Explainable AI Risk Scoring**
- Every risk score accompanied by top-3 contributing factors
- SHAP-backed feature importance with visual bars
- Human-readable factor explanations
- Live disruption and overdue penalties dynamically integrated
- 300ms debounced hover tooltips on dashboard

### 9. **Shipment Creation with Instant Risk Analysis**
- User inputs: origin, destination, carrier, mode, category, revenue, deadline
- Instant computation: risk score, 3 route alternatives, priority assignment
- Explainable risk breakdown with visual factors
- Map shows origin, destination, and route alternatives

### 10. **Indian Festival Calendar Engine**
- 24+ festivals with real dates (2025–2027)
- E-commerce sale seasons: Big Billion Days, Great Indian Festival
- Monsoon tracking (June–September) with coastal amplification
- Per-city congestion factors
- Active today + 30-day lookahead

---

## 🛠️ Technology Stack

### Backend
- **Python 3.11** — Core runtime
- **FastAPI** — High-performance async API framework
- **Pydantic v2** — Schema validation (30+ models)
- **XGBoost** — ML risk scoring (92.25% accuracy)
- **SHAP** — Model explainability
- **NetworkX** — Graph algorithms (BFS cascade propagation)
- **Google Generative AI** — Gemini 2.5 Flash chat
- **httpx** — Async HTTP for live APIs
- **Docker** — Containerization

### Frontend
- **Next.js 14** — React framework with server components
- **React 18** — UI library with hooks
- **TypeScript** — Type-safe development
- **Tailwind CSS** — Dark navy theme styling
- **Leaflet** — Interactive dark-themed maps
- **Recharts** — Risk visualizations
- **Framer Motion** — Smooth animations
- **Zustand** — Lightweight state management
- **SWR** — Cache-first data fetching

### Infrastructure
- **Google Cloud Run** — Serverless backend (auto-scaling, $0/month on free tier)
- **Vercel** — Frontend hosting (optimized for Next.js)
- **Docker** — Production-grade containers

### External APIs (All Free)
| API | Purpose | Limit |
|-----|---------|-------|
| OpenWeatherMap | Live weather for 20 cities | 1,000 calls/day |
| GDACS (UN) | Real-time disasters (earthquakes, floods, cyclones) | Unlimited |
| ReliefWeb (UN OCHA) | Humanitarian crisis reports | Unlimited |
| Google Gemini 2.5 Flash | AI chat assistant | 1,500 requests/day |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Google Cloud account (for deployment)
- Gemini API key (optional; set `GEMINI_API_KEY` for real AI)

### Backend Setup

```bash
# Clone repository
git clone https://github.com/VaideekaAgrawal/SupplySenseAI.git
cd SupplySenseAI/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Train ML model (generates model.joblib)
python ml/train_model.py

# Set environment variables
export GEMINI_API_KEY="your_key_here"  # Optional
export CORS_ORIGINS="http://localhost:3000"
export DISRUPTION_MODE="real"

# Run backend (API on http://localhost:8000)
uvicorn main:app --reload
```

### Frontend Setup

```bash
cd ../chainguard

# Install dependencies
npm install

# Set environment variables
echo 'NEXT_PUBLIC_API_BASE_URL=http://localhost:8000' > .env.local

# Run frontend (on http://localhost:3000)
npm run dev
```

### Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (interactive Swagger UI)
- **Dashboard**: http://localhost:3000/dashboard

---

## 📁 Project Structure

```
SupplySenseAI/
├── backend/                          # Python FastAPI backend
│   ├── main.py                      # FastAPI app entry point
│   ├── models/
│   │   └── schemas.py               # 30+ Pydantic models
│   ├── routers/
│   │   ├── shipments.py             # Shipment CRUD, risk scoring
│   │   ├── cascade.py               # Cascade analysis, simulation
│   │   ├── optimization.py          # Route optimization
│   │   ├── chat.py                  # Gemini AI proxy
│   │   ├── resilience.py            # Network resilience
│   │   ├── alerts.py                # Alert management
│   │   └── nodes.py                 # Node analysis, festivals
│   ├── services/
│   │   ├── data_store.py            # In-memory store, graph, KPIs
│   │   ├── risk_scorer.py           # ML + rule-based scoring
│   │   ├── cascade_engine.py        # BFS graph propagation
│   │   ├── route_optimizer.py       # Multi-objective optimization
│   │   ├── resilience_engine.py     # 5-metric resilience score
│   │   ├── gemini_service.py        # Gemini chat integration
│   │   ├── weather_service.py       # OpenWeatherMap integration
│   │   ├── disruption_feed.py       # GDACS + ReliefWeb aggregation
│   │   ├── festival_calendar.py     # Indian festival engine
│   │   └── real_data_loader.py      # Live data enrichment
│   ├── ml/
│   │   ├── train_model.py           # XGBoost training + SHAP
│   │   ├── generate_dataset.py      # Synthetic data generation
│   │   ├── feature_config.py        # Feature definitions
│   │   ├── model.joblib             # Trained XGBoost model
│   │   └── metrics.json             # Performance metrics
│   ├── tests/
│   │   ├── test_api.py              # 30 API tests
│   │   ├── test_cascade.py          # 9 cascade tests
│   │   ├── test_risk_scorer.py      # 7 risk scorer tests
│   │   ├── test_resilience.py       # 8 resilience tests
│   │   ├── test_ml.py               # 15 ML pipeline tests
│   │   ├── test_nodes.py            # 12 node/festival tests
│   │   └── conftest.py              # Shared test fixtures
│   ├── requirements.txt             # Python dependencies
│   ├── Dockerfile                   # Production container
│   └── .env.example                 # Environment template
│
├── chainguard/                      # Next.js frontend
│   ├── app/
│   │   ├── page.tsx                 # Landing (auto-redirect)
│   │   ├── dashboard/page.tsx       # Command center
│   │   ├── create/page.tsx          # Shipment creation
│   │   ├── nodes/page.tsx           # Network overview
│   │   ├── nodes/[city]/page.tsx    # Node detail
│   │   ├── simulate/page.tsx        # What-if simulator
│   │   ├── cascade/page.tsx         # Disruption list
│   │   ├── cascade/[id]/page.tsx    # Cascade tree
│   │   ├── reroute/page.tsx         # Shipment browser
│   │   ├── reroute/[id]/page.tsx    # Route optimizer
│   │   └── chat/page.tsx            # AI chat
│   ├── components/
│   │   ├── Navbar.tsx               # Global navigation
│   │   ├── DynamicMap.tsx           # SSR-safe map wrapper
│   │   └── MapView.tsx              # Leaflet integration
│   ├── lib/
│   │   ├── api.ts                   # API client + TypeScript interfaces
│   │   └── utils.ts                 # Formatting utilities
│   ├── package.json                 # npm dependencies
│   ├── tailwind.config.ts           # Dark navy theme
│   ├── tsconfig.json                # TypeScript config
│   └── next.config.js               # Next.js config
│
├── deploy.sh                        # One-command Google Cloud Run deploy
├── PROJECT_REPORT.md                # Comprehensive technical report
├── README.md                        # This file
└── changelogs.md                    # Development history
```

---

## 📚 Core Algorithms

### BFS Cascade Propagation
Graphs supply chain disruptions using breadth-first search with exponential decay:
```
cascade_impact = disruption_severity × dependency_weight × (0.85 ^ depth)
```
- Stops at depth > 4 or impact < 5%
- Tracks: delay hours, revenue at risk, customers affected per node

### Multi-Objective Route Scoring
Generates Pareto-optimal routes balancing 4 metrics:
```
composite_score = w_cost × norm(cost) + w_time × norm(time) + 
                  w_carbon × norm(carbon) + w_risk × norm(risk)
```
- User adjusts weights via sliders
- Routes re-rank in real-time
- Recommendation reasons in plain English

### Resilience Score Computation
5-metric composite score (0–100):
1. **Route Redundancy** — % OD pairs with ≥2 vertex-disjoint paths
2. **Carrier Diversity** — (1 - HHI) / (1 - 1/n)
3. **Geographic Spread** — Shannon entropy of hub distribution
4. **Buffer Capacity** — Average slack (deadline - ETA)
5. **Recovery Speed** — Historical disruption resolution time

---

## 📊 Machine Learning

### XGBoost Risk Scorer
- **Training Accuracy**: 92.25%
- **ROC-AUC**: 0.9821
- **5-Fold CV Stability**: 0.9804 ± 0.0021
- **Features**: 11 (eta_buffer, month, season_risk, distance, carrier_late_rate, mode_risk, region_risks, day_of_week, is_express, is_high_value)
- **Top Feature**: ETA buffer (SHAP importance: 1.56)
- **Training Data**: 10,000 rows with real Indian logistics distributions
- **Model Size**: 0.12 MB (loads instantly)

### Dual Scoring Strategy
- **ML-based**: XGBoost prediction with real SHAP values (when model.joblib exists)
- **Rule-based**: Weighted heuristics fallback (when model unavailable)
- Both produce identical output: risk_score (0-100), risk_level, confidence, top_factors

### Feature Engineering
| Feature | Source | SHAP Importance |
|---------|--------|-----------------|
| ETA Buffer (hours) | ETA vs Deadline | **1.56** |
| Month | Calendar | 1.34 |
| Season Risk | IMD data | 1.33 |
| Distance (normalized) | Route km / 2500 | 1.32 |
| Carrier Late Rate | Performance data | 0.83 |
| Mode Risk | Shipping mode | 0.31 |
| Origin Region Risk | State-level | 0.10 |
| Dest Region Risk | State-level | 0.05 |
| Day of Week | Logistics patterns | 0.04 |
| Is Express | Same/First Class | 0.04 |
| Is High Value | Revenue > ₹75K | 0.01 |

---

## 🧪 Testing

### 80 Tests — All Passing ✅
```
test_api.py              30 tests  → All endpoints, CRUD, pagination
test_cascade.py           9 tests  → BFS, decay, cycles, simulation
test_risk_scorer.py       7 tests  → Scoring, levels, confidence
test_resilience.py        8 tests  → Sub-metrics, edge cases
test_ml.py               15 tests  → Dataset, features, model, inference
test_nodes.py            12 tests  → Festivals, risk, haversine, cities
───────────────────────────────────
Total                    80 tests  ✅ 100% passing
```

### Running Tests
```bash
cd backend

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api.py -v

# Run with coverage
pytest tests/ --cov=services --cov=routers --cov-report=html
```

---

## 🌍 India-Specific Innovations

### Festival Calendar Engine
- **24+ festivals** with real dates (2025–2027): Diwali, Holi, Eid, Navratri, Ganesh Chaturthi, Onam, etc.
- **E-commerce seasons**: Big Billion Days, Great Indian Festival
- **Congestion factors**: Diwali (+50%), Ganesh Chaturthi (+35%), Holi (+30%)
- **Regional specificity**: Festival impact varies by state

### Monsoon Integration
- **June–September**: 15–25% extra severity
- **Coastal amplification**: Kerala, Tamil Nadu, West Bengal, Maharashtra
- **Top-3 SHAP feature**: Season risk (importance: 1.33)

### Indian Logistics Network
- **20 hub cities**: Mumbai, Delhi, Chennai, Kolkata, Bangalore, Hyderabad, Pune, Ahmedabad, Jaipur, Lucknow, Surat, Nagpur, Nhava Sheva, Coimbatore, Bhopal, Kochi, Chandigarh, Patna, Indore, Visakhapatnam
- **50+ logistics corridors**: Based on real NHAI highway network
- **8 Indian carriers**: BlueDart, FedEx India, DHL Express, Delhivery, DTDC, XpressBees, Ecom Express, Shadowfax
- **State-level risk profiles**: Maharashtra, West Bengal, Tamil Nadu, Kerala, Bihar, Uttar Pradesh, Delhi with region-specific factors
- **INR-native**: All costs in ₹, revenue displayed in lakhs (₹L)

---

## 📡 Live Data Integration

| Source | Protocol | Update Frequency | Data |
|--------|----------|-----------------|------|
| **OpenWeatherMap** | REST API | 30-min cache | Temperature, humidity, wind, weather severity |
| **GDACS (UN/EU)** | REST API | 15-min cache | Earthquakes, floods, cyclones, droughts, volcanoes, wildfires |
| **ReliefWeb (UN OCHA)** | REST API | 15-min cache | Humanitarian crisis reports, disaster status |
| **Google Gemini 2.5 Flash** | REST API | Real-time | AI-powered chat with context injection |

---

## 🚀 Deployment

### Local Development
```bash
# Terminal 1: Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

# Terminal 2: Frontend
cd chainguard
npm install && npm run dev
```

### Google Cloud Run (Production)
```bash
# One-command deployment
bash deploy.sh

# Or manually:
cd backend
gcloud run deploy supplysense-ai \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY="your_key" \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3
```

### Cost Analysis (Monthly Production)
| Service | Free Tier | Est. Cost |
|---------|-----------|-----------|
| Google Cloud Run | 2M requests free | ~$15/month |
| Gemini 2.5 Flash | 1,500 req/day free | $0 |
| GDACS + ReliefWeb | Unlimited free | $0 |
| OpenWeatherMap | 1,000 calls/day free | $0 |
| Vercel (Frontend) | Free hobby tier | $0–$20/month |
| **Total** | | **$0–$35/month** |

---

## 🔑 Environment Variables

### Backend (.env)
```bash
# Gemini AI (optional; set for real chat)
GEMINI_API_KEY=your_gemini_api_key_here

# API Configuration
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
ENVIRONMENT=development  # or production
DISRUPTION_MODE=real     # or synthetic

# Data Modes
DATA_MODE=live           # or demo
WEATHER_MODE=real        # or synthetic
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000  # or production URL
```

---

## 📈 Performance Benchmarks

| Operation | Latency | Notes |
|-----------|---------|-------|
| Risk scoring (single shipment) | ~50ms | XGBoost inference |
| Cascade computation (20 nodes) | ~500ms | BFS with 50+ edges |
| Route optimization (3 alternatives) | ~200ms | Pareto ranking |
| Gemini AI chat response | 1–3s | Context injection + token generation |
| API health check | <10ms | No-op endpoint |
| Dashboard load (all KPIs + map) | <2s | SWR cache + parallel requests |

---

## 🐛 Troubleshooting

### Backend won't start
```bash
# Ensure Python 3.11+
python --version

# Clear __pycache__
find . -type d -name __pycache__ -exec rm -r {} +

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### ML model not loading
```bash
# Retrain model
cd backend && python ml/train_model.py

# Verify model.joblib exists
ls -la ml/model.joblib
```

### Gemini API errors
```bash
# Check API key
echo $GEMINI_API_KEY

# Test connection
curl -H "Authorization: Bearer $GEMINI_API_KEY" \
     https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=$GEMINI_API_KEY
```

### Frontend can't reach backend
```bash
# Check backend is running
curl http://localhost:8000/health

# Verify CORS configuration
# Backend should have: CORS_ORIGINS=http://localhost:3000
```

---

## 📖 Documentation

- **[PROJECT_REPORT.md](./PROJECT_REPORT.md)** — Comprehensive technical report (all features, algorithms, metrics)
- **[API Docs](http://localhost:8000/docs)** — Interactive Swagger UI (live endpoints)
- **Backend inline comments** — Detailed service documentation in code
- **Frontend TypeScript interfaces** — 30+ interfaces documenting data shapes

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -am 'Add your feature'`
4. Push to branch: `git push origin feature/your-feature`
5. Submit a pull request

### Development Guidelines
- Python: Follow PEP 8 with Black formatter
- TypeScript: ESLint + Prettier
- Tests: All new features must include tests (pytest for backend)
- Commits: Clear messages describing the change

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](./LICENSE) file for details.

---

## 🙋 Support

For issues, questions, or suggestions:
1. **GitHub Issues** — [Create an issue](https://github.com/VaideekaAgrawal/SupplySenseAI/issues)
2. **Email** — Contact via repository owner
3. **Documentation** — See [PROJECT_REPORT.md](./PROJECT_REPORT.md) for detailed reference

---

## 🎓 Learn More

### Key Concepts
- **Supply Chain Resilience** — How to measure network robustness and identify weak links
- **Graph Algorithms** — BFS propagation for cascade analysis
- **ML Explainability** — SHAP values for interpretable AI
- **Multi-Objective Optimization** — Pareto frontiers for trade-off analysis
- **Time-Series Risk Scoring** — Dynamic feature computation from live data

### External Resources
- [XGBoost Documentation](https://xgboost.readthedocs.io/)
- [SHAP: Interpretable Machine Learning](https://shap.readthedocs.io/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/)
- [Next.js 14 App Router](https://nextjs.org/docs/app)
- [NetworkX Graph Algorithms](https://networkx.org/)

---

## 🏆 Achievements

- ✅ **92.25% ML accuracy** with 0.9821 ROC-AUC
- ✅ **80 comprehensive tests** (100% passing)
- ✅ **25+ production API endpoints** with full documentation
- ✅ **10 feature-rich pages** with interactive visualizations
- ✅ **$0/month infrastructure cost** using free-tier services
- ✅ **7 backend services + 7 routers** fully integrated
- ✅ **3 live external data sources** (GDACS, ReliefWeb, OpenWeatherMap)
- ✅ **India-first design** with 20 cities, 8 carriers, 24+ festivals
- ✅ **Explainable AI** with SHAP-backed factor attribution
- ✅ **Production-ready** with Docker, security best practices, and graceful fallbacks

---

**Built with ❤️ using Python, FastAPI, XGBoost, Next.js, React, and TypeScript**

*Total codebase: 15,000+ lines across 50+ files*

---

## 🔗 Links

- **Live Demo** — [Deploy on Vercel](https://vercel.com/new) or [Google Cloud Run](https://console.cloud.google.com/run)
- **GitHub Repository** — [VaideekaAgrawal/SupplySenseAI](https://github.com/VaideekaAgrawal/SupplySenseAI)
- **API Documentation** — [FastAPI Docs](http://localhost:8000/docs)
- **Technical Report** — [PROJECT_REPORT.md](./PROJECT_REPORT.md)
