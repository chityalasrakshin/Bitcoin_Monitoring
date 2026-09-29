# ChainSentry (SIH26146 Problem Statement 5)
### AI-Powered Monitoring & Forensic Correlation of Bitcoin Transaction Traffic

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18.3-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6.svg)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 14 Passed](https://img.shields.io/badge/Tests-14%20Passed-brightgreen.svg)]()

ChainSentry is a law-enforcement-grade, offline-first Bitcoin transaction monitoring and forensics investigation platform. It solves **Problem Statement 5 (SIH26146)** by ingesting peer-to-peer relay network observations and blockchain ledgers, attributing pseudo-anonymous addresses, detecting laundering typologies (Peeling Chains, CoinJoins, Structured Rapid Hops), and producing court-admissible dossiers with cryptographic audit logging.

---

## 🏛️ System Architecture

ChainSentry operates with an offline-first, dual-engine design. It requires **no external daemon dependencies** to function at full capability (embedded SQLite + in-memory NetworkX with Cytoscape.js export), while maintaining pluggable drivers for enterprise Neo4j property graphs and PostgreSQL databases.

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    ChainSentry SOC Frontend (React 18 + TS)                │
│   • Cytoscape.js Interactive Ego Graph    • Apache ECharts Risk Analytics  │
│   • Monospace Omnibox Explorer            • Court-Admissible Dossier Export│
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │ HTTP / JSON API (Bearer JWT)
┌─────────────────────────────────────▼──────────────────────────────────────┐
│                    FastAPI Forensics Gateway (:8000)                       │
│  /api/auth  •  /api/alerts  •  /api/graph  •  /api/cases  •  /api/reports  │
└──────┬─────────────────┬───────────────────┬───────────────────┬───────────┘
       │                 │                   │                   │
┌──────▼──────┐   ┌──────▼──────┐     ┌──────▼──────┐     ┌──────▼──────┐
│  Ingestion  │   │ Forensic    │     │ AI Anomaly  │     │ Case & Legal│
│  & Parsers  │   │ Graph Engine│     │  & Typology │     │ Management  │
│ CSV/JSON/XML│   │ MultiDiGraph│     │ IsolationF  │     │ Case CRUD   │
│ P2P-to-Ledger   │ Common-Input│     │ ECOD + KNN  │     │ Evidences   │
│ Correlation │   │ Personalized│     │ SHAP Values │     │ Audit Logs  │
│ GeoIP Lookups   │ PageRank    │     │ Rule Engines│     │ Dossiers    │
└──────┬──────┘   └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                 │                   │                   │
┌──────▼─────────────────▼───────────────────▼───────────────────▼───────────┐
│                    Persistence Layer (Dual Backend)                        │
│   Primary: SQLite (chainsentry.db) / PostgreSQL via SQLAlchemy 2.0         │
│   Intelligence Feeds: OFAC Sanctions + GraphSense TagPacks (87 Families)   │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Key Capabilities & Heuristics

1. **P2P Relay-to-Blockchain Correlation Engine**:
   - Matches broadcast transactions to peer network observation logs using a calibrated latency window ($0 \le \Delta t \le 60.0$ s).
   - Resolves relay nodes against local offline GeoIP fixture data (`data/reference/geoip_fixture.json`), isolating peer IPs, ASNs, and physical jurisdictions.

2. **Graph Intelligence & Clustering**:
   - **Common-Input-Ownership Heuristic (CIOH)**: Multi-input transactions collapse sender addresses into unified entity clusters using Union-Find disjoint sets.
   - **CoinJoin Exclusion Filter**: Protects against false cluster mergers by detecting equal-denomination multi-party mixing transactions (Wasabi, Whirlpool, JoinMarket) and isolating their inputs.
   - **Risk Propagation**: Personalized PageRank (PPR) propagating taint from known OFAC sanctioned wallets and high-risk entities across multi-hop counterparty paths.

3. **Multi-Signal AI & Typology Detection Ensemble**:
   - **Machine Learning**: 14-dimensional transaction feature extraction evaluated by an ensemble of PyOD detectors (**Isolation Forest**, **ECOD**, and **k-Nearest Neighbors**).
   - **Explainable AI (SHAP)**: Fast Kernel SHAP generating human-interpretable feature contribution narratives for investigators and legal proceedings.
   - **Rule-Based Typologies**:
     - *Peeling Chains*: Consecutive 1-in-2-out transactions peeling off fixed amounts while spending change back to recursive addresses.
     - *CoinJoin Mixing*: Equal-value outputs with multiple unassociated signers.
     - *Rapid Multi-Hop Layering*: Splitting and hops executed within tight block/timestamp constraints.

4. **Investigator Case Management & Audit Trail**:
   - Complete case workflow (`draft`, `in_review`, `approved`, `escalated`, `closed`).
   - Tamper-evident, cryptographically structured audit logs for all investigator actions.
   - Court-admissible markdown and PDF-ready forensic dossiers detailing entity attributions, hop chronologies, and evidentiary hashes.

---

## 🚀 Quickstart & Installation

### Prerequisites
- **Python**: 3.10+ (Recommended: Python 3.12)
- **Node.js**: 18+ (Required only if modifying/rebuilding the frontend)
- **Docker** *(optional, for containerized deployment)*

### 1. Backend Setup
Clone or navigate to the repository directory:
```bash
cd c:\Users\chity\Documents\Projects\Bitcoin_Monitoring
```

Create and activate a virtual environment:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:
```bash
pip install -r backend/requirements.txt
```

### 2. Launch the Application Server
Run the unified server (serves the REST API and the compiled React SPA):
```powershell
python run.py
```
For active development with hot code reloading:
```powershell
python run.py --reload
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

---

## 🚢 Production Deployment

For complete instructions on deploying with **Docker**, **Docker Compose**, **Render**, **Railway**, **Google Cloud Run**, or **Vercel + Backend API**, see **[DEPLOYMENT.md](file:///c:/Users/chity/Documents/Projects/Bitcoin_Monitoring/DEPLOYMENT.md)**.

Quick Docker start:
```bash
docker compose up --build -d
```

---

## 🔑 Default Investigator Credentials

| Role | Username | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **System Administrator** | `admin` | `chainsentry2026!` | Full Admin, Data Ingestion, User Provisioning |
| **Lead Investigator** | `investigator` | `forensics2026!` | Case Management, Graph Analysis, Dossier Export |

---

## 🖥️ Frontend SPA Development (Optional)

The frontend is pre-built into `frontend/dist/` and served automatically by FastAPI. If you wish to run the Vite development server with hot-module reloading:
```bash
cd frontend
npm install
npm run dev
```
Access the Vite dev server at `http://localhost:5173`.

---

## 🧪 Automated Testing

Execute the comprehensive unit and integration test suite (covers parsers, correlation, CIOH clustering, CoinJoin heuristics, AI anomaly scoring, and authentication):
```bash
.\.venv\Scripts\pytest.exe -v backend/tests
```
Expected output: **11 passed in ~5 seconds**.

---

## 📚 API Reference & Documentation

- Interactive Swagger UI: **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**
- Interactive ReDoc: **[http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)**
- Technical Architecture Deep-Dive: [docs/technical-writeup.md](file:///c:/Users/chity/Documents/Projects/Bitcoin_Monitoring/docs/technical-writeup.md)
- Complete API Specification: [docs/api-reference.md](file:///c:/Users/chity/Documents/Projects/Bitcoin_Monitoring/docs/api-reference.md)
- SIH26146 Forensic Blueprint: [docs/bitcoin-forensics-blueprint.md](file:///c:/Users/chity/Documents/Projects/Bitcoin_Monitoring/docs/bitcoin-forensics-blueprint.md)

---

## 📂 Repository Structure

```
Bitcoin_Monitoring/
├── backend/
│   ├── ai_service/             # ML anomaly ensemble, SHAP explainer, typology rules
│   ├── api_service/            # FastAPI routers (auth, alerts, cases, graph, ingestion)
│   ├── case_svc/               # SQLAlchemy models, CRUD, audit logging, report generator
│   ├── chainsentry_common/     # Configuration, Pydantic schemas, security, DB engine
│   ├── graph_svc/              # NetworkX graph engine, CIOH clustering, risk propagation
│   ├── ingestion_svc/          # CSV/JSON/XML parsers, P2P correlation, GeoIP connector
│   ├── tests/                  # Pytest automated test suite
│   └── requirements.txt        # Backend dependencies
├── frontend/
│   ├── src/                    # React 18 + TS application source
│   ├── dist/                   # Production-compiled single-page application
│   └── package.json            # Node.js dependencies & build scripts
├── data/
│   ├── reference/              # GraphSense TagPacks, OFAC sanctioned addresses
│   └── sample/                 # Seed-42 transactions & network observations
├── docs/                       # Technical write-up, API reference, blueprint
├── scripts/                    # bootstrap_data.py, seed_demo_case.py
├── Dockerfile                  # Multi-stage production container build
├── docker-compose.yml          # Container orchestration with data persistence
├── build.sh                    # PaaS build script (Render/Railway/Linux)
├── run.py                      # Application runner with dynamic $PORT support
├── DEPLOYMENT.md               # Cloud & container deployment documentation
├── .env.example                # Environment variables template
├── pytest.ini                  # Pytest configuration
└── README.md                   # Project overview & quickstart
```

---

## ⚖️ Legal & Ethical Compliance
ChainSentry is built strictly for lawful digital forensic investigations, law enforcement agencies, and sanctioned compliance monitoring. All data correlation complies with evidentiary chain-of-custody standards.
