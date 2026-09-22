# AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic
## Complete Implementation Blueprint — "ChainSentry"

**Problem Statement:** SIH26146 (Problem Statement 5) — Offline system that ingests bulk Bitcoin transaction/network metadata, correlates network-layer (IP/port/timing) with blockchain-layer (wallet/TXID/amount) data, applies AI/ML for anomaly detection, entity clustering, laundering-pattern detection, and risk-scored explainable leads, presented via a dashboard/link-analysis UI.

**Codename used throughout this document:** `ChainSentry`

**Audience:** This document is written to be consumed directly by developers and by AI coding agents (e.g. Claude Code) to scaffold and build the system with minimal further clarification.

---

## 0. Executive Summary & Key Architectural Decisions

The original problem statement suggests a *synthetic* dataset. This blueprint deliberately upgrades that: wherever a real, legally-obtainable, open dataset or live public API exists, ChainSentry uses it instead of fabricated data, because real data produces a genuinely useful prototype and a far more credible SIH demo. Synthetic data is used only for the one field category that literally cannot be obtained without capturing live P2P traffic yourself (raw peer-to-peer relay timing between a specific TXID and the IP that first relayed it to *your* node) — for that narrow case we document exactly how to *actually capture it yourself* offline with a real Bitcoin Core node, which is both real and more impressive than a fabricated CSV.

| Layer | Real data source used | Nature |
|---|---|---|
| Blockchain layer (TXID, addresses, amounts, fees, script types, UTXO graph) | **Blockstream Esplora API** (self-hostable, MIT) + Bitcoin Core full node (optional, for offline mode) | 100% real, live Bitcoin mainnet/testnet data |
| Labeled ground truth for illicit/licit classification (to train/evaluate the AI model) | **Elliptic++ dataset** (Kaggle / GitHub, CC-based academic license) — 203,769 real transactions + 822,942 real wallet addresses, hand-labeled illicit/licit by Elliptic Co. and MIT-IBM Watson AI Lab | 100% real, published, peer-reviewed |
| Known illicit / sanctioned wallets (seed nodes for risk propagation) | **OpenSanctions `CryptoWallet` dataset** (OFAC SDN, Israel NBCTF, UK OFSI, Japan MoF — 13,000+ sanctioned wallets), free JSON/CSV export, MIT-licensed tooling | 100% real, government-sourced |
| Network-layer P2P metadata (peer IP, port, ASN, geo, node reachability) | **Bitnodes.io API** (live crawl of the reachable Bitcoin P2P network, public, free) for the "network-layer" side of correlation | 100% real, live |
| Peer relay-timing for a *specific* TXID→IP first-seen mapping (the one thing no public API exposes, because it's local to each observing node) | **Self-captured**, by running Bitcoin Core / a lightweight P2P listener (e.g. `bitcoin-p2p-listener` pattern) on your own offline node and logging `INV`/`tx` message arrival per peer | Real capture methodology, run by the team, not fabricated |
| GeoIP enrichment (IP → country/ASN) | **MaxMind GeoLite2** free database (City + ASN, CC BY-SA 4.0 + MaxMind EULA, offline `.mmdb` file) | 100% real, offline-usable |

This gives every module in the pipeline something real to chew on, while still running **fully offline** after an initial data pull (all datasets/DBs are downloaded once and cached locally; the system does not require live internet access to run investigations).

### Top-level architectural decisions (with justification)

| Decision | Choice | Why |
|---|---|---|
| Backend language/framework | **Python 3.12 + FastAPI** | Best AI/ML ecosystem (PyOD, PyGOD, scikit-learn, NetworkX, SHAP) lives in Python; FastAPI gives async I/O, automatic OpenAPI docs, and Pydantic validation — ideal for an investigator-facing REST/WS API |
| Graph database | **Neo4j 5.x Community Edition + Graph Data Science (GDS) library** | Wallet/TX/IP relationships are inherently graph-shaped; Neo4j's Cypher query language plus GDS's built-in Louvain, PageRank, WCC, and FastRP embedding algorithms give entity clustering and risk propagation "for free" instead of hand-rolling graph algorithms |
| Relational/time-series store | **PostgreSQL 16 + TimescaleDB extension** | Case management, users, alerts, and audit logs need ACID relational storage; TimescaleDB hypertables give efficient time-bucketed queries over millions of timestamped transactions without a separate time-series DB |
| Cache / task queue broker | **Redis 7** | Backs Celery for async ingestion jobs and caches hot graph queries |
| Async task processing | **Celery** | Bulk CSV/JSON/XML ingestion, GDS algorithm runs, and ML scoring are long-running — must not block the API; Celery is the mature, boring, well-documented choice |
| Full-text / address search | **Meilisearch** | Investigators need instant fuzzy search over addresses, TXIDs, tags, and case notes; Meilisearch is a single static binary, sub-50ms search, far simpler to run offline than Elasticsearch/OpenSearch for a prototype of this size |
| Object storage (evidence files, exported reports, PCAP snippets) | **MinIO** (S3-compatible, open source) | Lets the backend use the standard S3 SDK while staying 100% offline/on-prem |
| Frontend | **React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui** | Fast dev loop, huge component ecosystem, Tailwind/shadcn give a professional look without a design team |
| Graph/link-analysis visualization | **Cytoscape.js** | Purpose-built for exactly this problem (interactive network graphs with custom node/edge styling, layouts like `cose-bilkent`, click-to-expand); MIT licensed, mature, used by real OSINT/forensics tools |
| Charts/dashboards | **Apache ECharts** (via `echarts-for-react`) | Rich chart types (Sankey diagrams are perfect for fund-flow visualization), good performance on larger datasets |
| Geo map (ASN/country view) | **Leaflet + react-leaflet** with local MaxMind GeoLite2 lookups | Free OSM tiles can be cached locally for offline use; no Google Maps key needed |
| Auth | **JWT (access + refresh tokens) via `python-jose` + `passlib[bcrypt]`**, custom RBAC middleware | Simple, dependency-light, fully auditable — avoids pulling in a heavyweight IdP (Keycloak/Ory) for a single-team investigative tool, while remaining swappable later |
| Entity clustering | Multi-input common-ownership heuristic (graph pre-processing) **+ Neo4j GDS Louvain/WCC** on the resulting address graph **+ FastRP graph embeddings → HDBSCAN** for a second, embedding-based clustering signal that catches entities the heuristic misses | Combines the classical, explainable heuristic (union-find over co-spent inputs) used by all serious chain-analysis tools with a modern embedding-based ML signal, as the problem statement explicitly asks for "graph embeddings" |
| Anomaly detection | **PyOD** (Isolation Forest, ECOD, AutoEncoder ensembles) on engineered per-transaction/per-address features, trained/evaluated on Elliptic++ | PyOD is the most mature, widely used (38M+ downloads) Python anomaly-detection toolkit, with a consistent `fit`/`decision_function` API across 40+ algorithms — lets the team A/B multiple detectors with almost no extra code |
| Graph-native anomaly detection (stretch) | **PyGOD** (graph neural network autoencoders, e.g. `DOMINANT`, `CoLA`) | Captures structural anomalies (e.g., an address whose *neighborhood* looks like a mixer even if its own features look normal) that flat-feature models miss |
| Peeling-chain / mixer detection | Custom rule + graph-pattern miner (NetworkX) implementing published heuristics (peeling-chain shape, equal-output CoinJoin detection, round-number/no-return-address heuristics) | No mature, actively-maintained open-source *library* does this well out of the box; the detection logic itself is the core "differentiator" the problem statement wants, so it is hand-built but grounded in cited, publicly documented heuristics (see §12) |
| Risk scoring / taint propagation | **Neo4j GDS Personalized PageRank** seeded from OpenSanctions + Elliptic-labeled illicit wallets | This is the standard, well-documented technique for "taint"/guilt-by-association propagation in blockchain forensics, and GDS ships it as a single Cypher procedure call — no need to hand-implement power iteration |
| Explainability | **SHAP** (feature attribution for the PyOD/classifier scores) + rule-based natural-language templates for graph-pattern flags + optional **Claude API (`claude-sonnet-5`)** to turn the structured evidence bundle into a plain-English investigative narrative | Every alert must ship with "why," per the problem statement; SHAP explains the ML score, the graph engine explains *which* pattern fired, and the LLM step (fully optional/offline-toggleable) turns both into an analyst-readable paragraph |
| Deployment shape for the prototype | **Docker Compose**, single Linux host, no Kubernetes/cloud | Problem statement explicitly asks for an **offline, Linux-platform** solution; Compose is the minimum orchestration needed to run 7 local services reproducibly — anything heavier is out of scope per the brief given for this document |

---

## 1. Existing Open-Source Solutions Research

Full due-diligence table for every reused project. All were checked to be **actively maintained** (commits/releases within roughly the last 12 months, or, for smaller focused libraries, still the de-facto standard with recent releases) as of this writing (Sept 2026); anything abandoned (e.g. the once-popular `BlockSci` graph-analysis engine, whose last meaningful activity predates 2022) was deliberately excluded.

### 1.1 GraphSense (reference architecture, not directly embedded)
- **GitHub:** https://github.com/graphsense (org with `graphsense-lib`, `graphsense-python`, `graphsense-REST`, etc.)
- **Website:** https://graphsense.org/
- **License:** MIT (core components)
- **Activity:** Actively maintained by AIT Austrian Institute of Technology; `graphsense-lib` has ongoing commit activity
- **Why selected:** GraphSense is the most credible published open-source *architecture* for cryptoasset analytics (address clustering, TagPacks for collaborative attribution tagging, REST API). We do **not** embed its Spark+Cassandra stack directly (too heavy for a Linux-laptop prototype and out of scope per the "no heavy infra" instruction), but ChainSentry's clustering pipeline and its "TagPack" style attribution-tag model are explicitly modeled on GraphSense's published design.
- **Module it replaces/informs:** Entity clustering data model, attribution-tag schema
- **Integration approach:** Design-pattern reuse (schema + heuristic), not a runtime dependency; optionally, ChainSentry can import GraphSense **TagPacks** (public YAML attribution tag files at https://github.com/graphsense/graphsense-tagpacks) directly as seed attribution data
- **Advantages:** Battle-tested clustering heuristics, published TagPack corpus of real known-entity labels (exchanges, mixers, darknet markets)
- **Limitations:** Full platform requires Spark + Cassandra, which is unnecessary operational weight for this prototype

### 1.2 Elliptic++ Dataset
- **GitHub/Source:** https://github.com/git-disl/EllipticPlusPlus ; original Kaggle release: https://www.kaggle.com/datasets/ellipticco/elliptic-data-set
- **License:** Released by Elliptic for research use (Kaggle dataset terms); academic citation required
- **Why selected:** The only large-scale, **real**, publicly labeled Bitcoin transaction+address graph in existence — 203,769 real transactions (165 features each) and 822,942 real wallet addresses, hand-labeled licit/illicit by Elliptic in collaboration with the MIT-IBM Watson AI Lab. This is the dataset the entire academic AML/blockchain-forensics literature benchmarks against.
- **Module it replaces:** Synthetic training data generation (explicitly avoided per this document's brief)
- **Integration approach:** Downloaded once (`elliptic_txs_features.csv`, `elliptic_txs_classes.csv`, `elliptic_txs_edgelist.csv`, plus the Elliptic++ wallet-level extension `wallets_features.csv`, `wallets_classes.csv`, `AddrTx_edgelist.csv`) into `/data/raw/elliptic/`; used both to **train/validate** the anomaly and classification models and to **seed** a realistic demo graph in Neo4j (transactions are re-hydrated into the ChainSentry schema, with real TXIDs preserved where available and IP/network-layer fields joined on from the network-layer sources below)
- **Advantages:** Real, large, peer-reviewed labels; both transaction-level and address-level graphs (the "Elliptic++" extension)
- **Limitations:** Anonymized/scaled numeric features (raw amounts are not literal on-chain BTC values, by design, to protect Elliptic's data sources) — for genuinely live amounts, ChainSentry cross-references live TXIDs against Esplora

### 1.3 Blockstream Esplora / esplora-electrs
- **GitHub:** https://github.com/Blockstream/esplora (frontend) and https://github.com/Blockstream/electrs (indexer/backend, a Rust fork of Electrum server)
- **Website:** https://blockstream.info (public instance) / self-hosted docs in repo
- **License:** MIT
- **GitHub stars / activity:** 1,000+ stars on `esplora`, actively maintained by Blockstream; public API rate-limited to ~50 req/s / burst 100
- **Why selected:** The standard open-source way to get real, indexed Bitcoin blockchain data (address balances/history, tx details, UTXO sets, mempool state) via a clean REST API, with no API key required, and it is fully self-hostable against your own Bitcoin Core node for a 100% offline deployment.
- **Module it replaces:** Bulk blockchain-layer ingestion (would otherwise require hand-parsing raw block files)
- **Integration approach:** ChainSentry's `blockchain-ingest` service calls the Esplora REST API (public instance during development; a locally self-hosted `electrs` instance pointed at a local `bitcoind` for the fully offline/air-gapped deployment mode) to pull transactions for addresses/TXIDs of interest and to batch-backfill historical data referenced in the Elliptic++ dataset
- **Advantages:** MIT license, mature, privacy-respecting (no tracking), works against testnet/signet for safe development
- **Limitations:** Public instance has rate limits; self-hosting requires a fully synced Bitcoin Core node (~600GB+ disk) for full historical coverage — the prototype defaults to querying only addresses/TXIDs relevant to loaded cases rather than requiring a full local index

### 1.4 mempool.space (mempool/mempool)
- **GitHub:** https://github.com/mempool/mempool
- **Website:** https://mempool.space
- **License:** AGPL-3.0
- **Activity:** Very active, large community, one-click self-host installers for Umbrel/Start9/RaspiBlitz
- **Why selected:** Best real-time mempool visualizer/API — fee-rate estimates, unconfirmed transaction graph, and a WebSocket feed, complementing Esplora's confirmed-chain view
- **Module it replaces:** Real-time mempool/fee-market monitoring
- **Integration approach:** Optional module — ChainSentry's ingestion service can subscribe to a self-hosted or public mempool.space WebSocket for live unconfirmed-transaction alerts (useful for a "live monitoring" demo mode); not required for the core offline investigative workflow
- **Advantages:** Real-time, self-hostable, WebSocket push (efficient vs. polling)
- **Limitations:** AGPL-3.0 means any modified redistributed version of *mempool.space itself* must be open-sourced — irrelevant here since ChainSentry only calls its API/WebSocket as an external service, not embeds its code

### 1.5 Bitnodes (bitcoin network crawler)
- **GitHub:** https://github.com/ayeowch/bitnodes
- **Website:** https://bitnodes.io
- **License:** MIT
- **Why selected:** The standard open-source Bitcoin P2P network crawler; its public API (https://bitnodes.io/api/) returns a live, real snapshot of every reachable node's **IP address, port, user agent, ASN, and geolocation** — exactly the "network-layer" fields the problem statement asks to correlate against the blockchain layer, sourced from the real live network rather than invented
- **Module it replaces:** Fabricated `src_ip/dst_ip/geo/asn` fields
- **Integration approach:** `network-ingest` service periodically pulls a Bitnodes snapshot (`GET /api/v1/snapshots/latest/`) and stores it as the **IP↔ASN↔Geo reference table**; it is also runnable **fully offline** by cloning the crawler and pointing it at your own Bitcoin Core node's `getpeerinfo` RPC (which ChainSentry does by default in offline mode — see §9.3)
- **Advantages:** MIT license, real data, works fully offline against your own node
- **Limitations:** The public crawler only sees *reachable* (listening) nodes, not every network participant (many wallets/exchanges run non-listening nodes) — ChainSentry documents this as a known coverage caveat in the technical write-up

### 1.6 Neo4j Graph Data Science (GDS) Library
- **GitHub:** https://github.com/neo4j/graph-data-science
- **Website:** https://neo4j.com/docs/graph-data-science/current/
- **License:** GPL v3 (Community Edition compatible; some enterprise-only algorithms excluded, but Louvain, WCC, PageRank/Personalized PageRank, and FastRP embeddings are all in the free Community tier used here)
- **GitHub stars:** ~670+, actively maintained (commits through 2025), 66 watchers, healthy issue/PR activity
- **Why selected:** Ships production-grade, tested implementations of exactly the graph algorithms the problem statement's "Suggested AI/ML Focus Areas" call for — Louvain/WCC for entity clustering, Personalized PageRank for risk-score propagation, and FastRP for graph embeddings — as single Cypher procedure calls, avoiding the need to hand-implement and validate these algorithms
- **Module it replaces:** Hand-rolled union-find clustering, hand-rolled PageRank, hand-rolled node2vec
- **Integration approach:** Installed as a Neo4j plugin (`.jar` dropped into `plugins/`) on the same Neo4j instance holding the wallet/TX graph; called via `CALL gds.louvain.stream(...)`, `CALL gds.pageRank.stream(...)`, `CALL gds.fastRP.mutate(...)` from the Python backend over the Bolt driver
- **Advantages:** Well-documented, in-database (no data movement to a separate ML framework for the core algorithms), horizontally tunable via graph projections
- **Limitations:** Some advanced GDS algorithms (e.g. certain ML pipelines) are Enterprise-only; the prototype only uses Community-tier algorithms, all confirmed free

### 1.7 PyOD (Python Outlier Detection)
- **GitHub:** https://github.com/yzhao062/pyod
- **Website/Docs:** https://pyod.readthedocs.io
- **License:** BSD-2-Clause
- **Activity:** Very active — now on "PyOD 3," 38M+ downloads, JMLR-published, continuously maintained since 2017
- **Why selected:** The de-facto standard Python toolkit for outlier/anomaly detection, with 40+ algorithms behind one consistent `fit`/`decision_function` API — lets the team benchmark Isolation Forest, ECOD, AutoEncoder, and ensemble combinations on the Elliptic++ feature set with minimal glue code
- **Module it replaces:** Hand-implemented anomaly scoring
- **Integration approach:** `pip install pyod`; used inside the `ai-service` for the "statistically unusual transactions/flows" detection use case
- **Advantages:** Mature, benchmarked, consistent API, good documentation, active community
- **Limitations:** Purely feature-based (flat-vector) — does not natively understand graph structure, which is why PyGOD is added alongside it

### 1.8 PyGOD (Python Graph Outlier Detection)
- **GitHub:** https://github.com/pygod-team/pygod
- **Website/Docs:** https://docs.pygod.org
- **License:** BSD-2-Clause
- **Why selected:** Sibling project to PyOD, purpose-built for **graph** anomaly detection (e.g. `DOMINANT`, `CoLA`, `AnomalyDAE` — GNN-autoencoder architectures) — directly applicable to spotting an address whose local subgraph topology resembles known mixing/laundering structures even when its own transaction features look unremarkable
- **Module it replaces:** N/A — new capability, addresses a gap flat-feature detectors have
- **Integration approach:** Optional/"stretch" module run on the Neo4j-exported subgraph around each case's wallets (via `torch_geometric` `Data` objects), scored asynchronously by Celery workers
- **Advantages:** State-of-the-art graph anomaly detection, PyTorch Geometric backend (GPU-accelerable if available, CPU-fine for prototype scale)
- **Limitations:** Heavier dependency footprint (PyTorch); marked optional/feature-flagged so the core system runs without a GPU

### 1.9 OpenSanctions (crypto wallet sanctions data + `nomenklatura`/`opensanctions` tooling)
- **GitHub:** https://github.com/opensanctions/opensanctions (data pipeline) and https://github.com/opensanctions/nomenklatura (entity resolution library)
- **Website:** https://www.opensanctions.org
- **License:** Data: free for non-commercial/OSS use under OpenSanctions' data license (commercial use requires a paid license — flagged clearly for the team so a production deployment budgets for it); tooling code: MIT
- **Why selected:** Ships a structured, machine-readable `CryptoWallet` schema covering 13,000+ **real, government-designated sanctioned wallet addresses** (US OFAC SDN, Israel NBCTF, UK HMT/OFSI, Japan MoF) — the perfect real "seed set" for risk-propagation, replacing any invented "known-bad wallet" list
- **Module it replaces:** Fabricated seed/ground-truth illicit-wallet list
- **Integration approach:** Nightly (or on-demand, for offline mode: one-time) pull of the `CryptoWallet`-schema entities via the free bulk data export (JSON/CSV), loaded into Postgres as the `sanctioned_wallets` reference table and used to tag matching Neo4j `Wallet` nodes as **seed illicit nodes** for the Personalized PageRank risk-propagation job
- **Advantages:** Authoritative, government-sourced, actively updated, free for this (non-commercial, educational/hackathon) use case
- **Limitations:** Only covers *designated* wallets (a small, known subset of all illicit activity) — used as high-confidence seeds, not as the sole detection mechanism

### 1.10 NetworkX
- **GitHub:** https://github.com/networkx/networkx
- **Website:** https://networkx.org
- **License:** BSD-3-Clause
- **Why selected:** Mature, pure-Python graph library used for the bespoke pattern-mining logic (peeling-chain and CoinJoin-shape detection) that isn't a single GDS procedure call — lets the team prototype and unit-test graph-traversal heuristics quickly in Python before/without touching Neo4j for small per-case subgraphs
- **Module it replaces:** Hand-rolled graph traversal code
- **Integration approach:** Used inside `ai-service/patterns/` on subgraphs pulled from Neo4j into memory (via the Bolt driver → NetworkX `DiGraph`) for pattern-specific analysis
- **Advantages:** Simple API, huge algorithm library, easy to unit test
- **Limitations:** In-memory only — not used for graph-wide operations (those stay in Neo4j/GDS)

### 1.11 Cytoscape.js
- **GitHub:** https://github.com/cytoscape/cytoscape.js
- **Website:** https://js.cytoscape.org
- **License:** MIT
- **Why selected:** Purpose-built, actively maintained JS graph-visualization library designed for exactly this use case (interactive link-analysis with rich node/edge styling, expandable subgraphs, multiple layout algorithms) — the same category of tool real OSINT/forensics products use, as opposed to a generic charting library
- **Module it replaces:** Custom D3.js force-graph code (would take far longer to reach the same UX quality)
- **Integration approach:** Wrapped via `react-cytoscapejs`; fed graph JSON from the backend's `/api/graph/{entity_id}/neighborhood` endpoint
- **Advantages:** Mature, MIT, huge plugin ecosystem (`cytoscape-cose-bilkent` for clean force-directed layout, `cytoscape-context-menus` for right-click investigative actions)
- **Limitations:** Performance degrades above a few thousand nodes rendered at once — ChainSentry paginates/expands subgraphs on demand rather than rendering the entire case graph at once

### 1.12 MaxMind GeoLite2
- **Website:** https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
- **License:** CC BY-SA 4.0 + MaxMind GeoLite2 EULA (free registration required, redistribution of the raw DB restricted per EULA — documented for the team)
- **Why selected:** The standard free, offline-usable IP→(country, ASN, approximate city) database, shipped as a compact binary `.mmdb` file queryable with zero network calls — essential for the "geo_country/asn" field the problem statement explicitly requests, and for genuinely offline operation
- **Integration approach:** Downloaded once (registration required) into `/data/geoip/`, queried via the `geoip2` Python library inside `network-ingest`
- **Limitations:** City-level accuracy is approximate; ASN/country level is reliable and sufficient for this use case

---

## 2. APIs & External Services

| Service | Docs | Website | Pricing | API key? | Auth | Rate limits | SDK | Alternatives | Why required | Integration |
|---|---|---|---|---|---|---|---|---|---|---|
| **Blockstream Esplora API** | https://github.com/Blockstream/esplora/blob/master/API.md | https://blockstream.info | Free (public instance); self-host is free/infra-cost only | No | None | ~50 req/s / burst 100 on public instance | None official; plain REST/JSON, `esplora-client` npm package for JS side if needed | mempool.space API (identical Esplora-compatible schema), Blockchair (proprietary), BlockCypher (proprietary) | Primary source of real, confirmed blockchain-layer data (tx details, address history, UTXOs) | `blockchain-ingest` service, REST calls, cached in Postgres |
| **mempool.space API/WebSocket** | https://mempool.space/docs/api/rest | https://mempool.space | Free (public); self-host free | No | None | Reasonable-use, no hard published cap on public instance | `mempool.js` (official) | Blockstream Esplora (confirmed-only) | Real-time unconfirmed tx / fee-market data for the "live monitoring" demo mode | `network-ingest`/`ws-listener` module, optional |
| **Bitnodes API** | https://bitnodes.io/api/ | https://bitnodes.io | Free | No | None | Reasonable-use | None official; plain REST | Self-run crawler (same codebase), manual `getpeerinfo` polling of own node | Real network-layer IP/ASN/geo snapshot of the reachable P2P network | `network-ingest` service, scheduled Celery task |
| **OpenSanctions bulk data / API** | https://www.opensanctions.org/docs/api/ | https://www.opensanctions.org | Free for non-commercial/OSS; paid license for commercial use | API key for the hosted matching API (free tier available); bulk JSON/CSV export needs no key | API-key header (hosted API only) | Free tier: reasonable-use limits documented on site | Python: no official SDK, plain `requests`; `nomenklatura` for entity-resolution utilities | US Treasury OFAC SDN list directly (narrower coverage, harder to parse) | Real seed list of sanctioned/known-illicit wallets for risk propagation | One-time/nightly bulk pull into Postgres `sanctioned_wallets` table |
| **MaxMind GeoLite2** | https://dev.maxmind.com/geoip/docs/databases | https://www.maxmind.com | Free (registration required) | "License key" (free account) for automated downloads via `geoipupdate` | License key in download URL | Download-frequency limits (daily updates only) | `geoip2` (official Python), `maxminddb` | IP2Location LITE (similar free tier) | Offline IP→country/ASN/city resolution | `network-ingest`, local `.mmdb` file, `geoip2.database.Reader` |
| **Elliptic++ dataset (Kaggle)** | https://www.kaggle.com/datasets/ellipticco/elliptic-data-set | https://www.kaggle.com | Free | Kaggle account/API token for programmatic download (`kaggle` CLI) | Kaggle API token | N/A (one-time download) | `kaggle` Python package | Elliptic++ GitHub mirror (https://github.com/git-disl/EllipticPlusPlus) | Real labeled training/evaluation data (avoids synthetic data per this brief) | One-time download into `/data/raw/elliptic/`, ETL'd into Neo4j + feature store |
| **GraphSense TagPacks** | https://github.com/graphsense/graphsense-tagpacks | https://graphsense.org | Free (open data, CC0/CC-BY depending on pack) | No | None | N/A | N/A | Manual OSINT tagging | Real, community-curated entity-attribution tags (exchange/mixer/darknet-market labels) | One-time import into `attribution_tags` table |
| **Anthropic Claude API** (optional, for narrative report generation) | https://docs.claude.com/en/api/overview | https://www.anthropic.com | Pay-per-token; see current pricing at https://docs.claude.com | Yes, `ANTHROPIC_API_KEY` | Bearer API key header | Per-org tier limits, see https://docs.claude.com | Official Python SDK (`anthropic`) | Any local LLM (e.g. via `llama.cpp`) if the deployment must be 100% air-gapped with zero external calls; feature-flagged off by default | Turns the structured evidence bundle (SHAP values + fired graph patterns) into a readable investigative narrative for the report screen | `ai-service/narrative.py`, called on-demand when an investigator clicks "Generate Report Summary"; **fully optional** — the system is 100% functional and offline without it |

> **Note on "offline" requirement:** every item above except the optional Claude API call is used in a **pull-once-cache-locally** pattern. After the initial data sync (documented as a `make bootstrap-data` step in §9), ChainSentry runs with zero outbound network calls, satisfying "Workable complete offline solution for linux platform."

---

## 3. Solution Architecture

### 3.1 Overall System Architecture (component diagram, described)

```
                         ┌──────────────────────────────────────────────┐
                         │                 FRONTEND                      │
                         │   React + TS + Vite + Tailwind + shadcn/ui    │
                         │   Cytoscape.js (graph) · ECharts (dashboards) │
                         │   Leaflet (geo)                               │
                         └───────────────────────┬────────────────────────┘
                                                  │ HTTPS (REST + WebSocket), JWT
                         ┌───────────────────────▼────────────────────────┐
                         │                API GATEWAY LAYER                │
                         │       FastAPI (`api-service`) — REST + WS       │
                         │   AuthN/AuthZ (JWT, RBAC) · Rate limiting       │
                         │   OpenAPI docs at /docs                         │
                         └───┬───────────┬───────────┬───────────┬────────┘
                             │           │           │           │
              ┌──────────────▼┐  ┌───────▼──────┐ ┌──▼─────────┐ ┌▼──────────────┐
              │  ingestion-svc │  │  ai-service  │ │ graph-svc  │ │  case-svc      │
              │ (Celery workers)│ │ (Celery/     │ │ (Bolt →    │ │ (cases, alerts,│
              │ CSV/JSON/XML    │ │  FastAPI     │ │  Neo4j GDS │ │  evidence,     │
              │ parsers, Esplora│ │  sub-app)    │ │  wrapper)  │ │  audit log)    │
              │ /Bitnodes pull  │ │ PyOD/PyGOD/  │ │ Louvain/   │ │                │
              │                 │ │ SHAP/Claude  │ │ PageRank/  │ │                │
              │                 │ │ (optional)   │ │ FastRP     │ │                │
              └───────┬─────────┘  └──────┬───────┘ └────┬───────┘ └───────┬────────┘
                      │                    │              │                │
       ┌──────────────▼─────────┐  ┌───────▼──────────────▼────┐  ┌────────▼─────────┐
       │   Redis (Celery broker  │  │        Neo4j 5.x            │  │   PostgreSQL 16   │
       │   + result backend +    │  │   (+ GDS plugin)             │  │  + TimescaleDB     │
       │   hot-query cache)      │  │  Wallet/TX/IP entity graph    │  │ users, cases,      │
       └──────────────────────────┘  └──────────────────────────────┘  │ alerts, audit,      │
                                                                          │ sanctioned_wallets, │
                                                                          │ tx metadata (TS)    │
                                                                          └─────────┬───────────┘
                                                              ┌──────────────────────┼───────────────┐
                                                     ┌────────▼────────┐   ┌─────────▼───────┐  ┌─────▼─────┐
                                                     │   Meilisearch    │   │      MinIO        │  │ (external, │
                                                     │  full-text index │   │ evidence/reports   │  │  cached)   │
                                                     │  (addr/tx/tags/  │   │  object storage    │  │ GeoLite2   │
                                                     │  case notes)     │   │                    │  │ .mmdb file │
                                                     └──────────────────┘   └────────────────────┘  └───────────┘
```

### 3.2 Data Flow (end-to-end)

1. **Bulk ingestion**: An investigator uploads a CSV/JSON/XML metadata file (or the system auto-pulls a case's addresses/TXIDs from Esplora) → `ingestion-svc` validates schema → normalizes into the canonical internal schema (§6) → writes raw rows to Postgres (`raw_transactions` hypertable) and enqueues a Celery `graph_ingest` task.
2. **Graph construction**: `graph_ingest` upserts `Wallet`, `Transaction`, `IPObservation`, and `ASN`/`Country` nodes plus `SENT`/`RECEIVED`/`OBSERVED_FROM`/`SAME_ENTITY_AS` relationships into Neo4j via parameterized Cypher `MERGE` statements (idempotent — safe to re-run).
3. **Correlation**: a scheduled job joins blockchain-layer transactions (by timestamp proximity, ±configurable window) to network-layer `IPObservation` nodes captured either from the self-hosted P2P listener or from Bitnodes snapshots, creating `FIRST_RELAYED_BY` edges — this is the literal "correlate network-layer observations with blockchain-layer data" requirement.
4. **Entity clustering**: `ai-service` runs (a) the multi-input heuristic (pure Cypher, near-instant) to build a `Cluster` node per connected component of co-spent addresses, then (b) `gds.louvain` / `gds.wcc` for a second clustering pass over the full transaction graph, and (c) `gds.fastRP.mutate` → embeddings exported to a feature store → `HDBSCAN` clustering as a third, independent signal; clusters from all three are reconciled (majority-vote / union) into a final `entity_id`.
5. **Anomaly detection**: engineered per-address/per-transaction feature vectors (mirroring the Elliptic++ feature schema) are scored by the trained PyOD ensemble (and optionally PyGOD on the graph structure); each score is stored with its SHAP explanation.
6. **Pattern detection**: `ai-service/patterns/` pulls relevant subgraphs into NetworkX and runs the peeling-chain and CoinJoin-shape detectors; matches are written as `Alert` rows referencing the specific transaction chain.
7. **Risk scoring**: `graph-svc` runs `gds.pageRank` personalized to seed nodes (`sanctioned_wallets` + Elliptic-labeled-illicit wallets) → every wallet gets a 0–1 propagated risk score, recomputed incrementally as new data arrives.
8. **Alert generation**: `case-svc` merges anomaly scores + pattern matches + risk scores into a single ranked, deduplicated `Alert` list per case, each carrying a confidence score and a structured "evidence bundle" (which heuristic/model fired, which subgraph, SHAP top features).
9. **Investigation**: the investigator opens a case in the dashboard, explores the Cytoscape.js link-analysis graph, filters/searches via Meilisearch, attaches evidence (stored in MinIO), and optionally generates an AI-drafted narrative summary (Claude API) — all actions are audit-logged in Postgres.

### 3.3 Investigation Workflow (user journey)

`Ingest data → Auto-cluster & score → Ranked alert queue → Analyst opens alert → Link-analysis graph exploration → Attach evidence / tag entities → Escalate to case → Generate report → Export (PDF/CSV/JSON) → Close case`

### 3.4 Backend Architecture

- **`api-service`** (FastAPI): thin HTTP/WS layer; all business logic delegated to service modules below it; every route is Pydantic-typed for request/response validation, which also generates the OpenAPI spec at `/docs` automatically.
- **`ingestion-svc`**: Celery workers + pure-Python parser modules per format (`csv_parser.py`, `json_parser.py`, `xml_parser.py`) sharing a common `NormalizedTxRecord` Pydantic model; also owns scheduled pulls from Esplora/Bitnodes/OpenSanctions/GeoLite2.
- **`graph-svc`**: a thin wrapper around the official `neo4j` Python driver, exposing typed functions (`get_neighborhood(entity_id, depth)`, `run_louvain()`, `run_personalized_pagerank(seed_ids)`, `run_fastrp()`), so Cypher never leaks into the API layer.
- **`ai-service`**: hosts the PyOD/PyGOD models, the pattern-mining code, SHAP explainers, and the optional Claude-API narrative generator; runs both as importable functions (for synchronous small requests) and as Celery tasks (for full-case batch scoring).
- **`case-svc`**: CRUD + business rules for cases, alerts, evidence, tags, and the audit log; the only service allowed to write to `audit_log`.
- **Shared library `chainsentry-common`**: Pydantic schemas, DB session factories, auth utilities, logging config — imported by every service to avoid duplication (see folder structure §4).

### 3.5 Frontend Architecture

- **Vite + React 18 + TypeScript**, file-based routing via `react-router-dom`.
- **State/data-fetching:** TanStack Query (React Query) for all server state (caching, refetch-on-focus, optimistic updates for tagging); Zustand for small pieces of local UI state (selected node, active filters).
- **Styling:** Tailwind CSS + shadcn/ui component primitives for a consistent, professional look without custom design work.
- **Graph view:** a dedicated `<InvestigationGraph>` component wrapping `react-cytoscapejs`, fed by `/api/graph/neighborhood`; supports click-to-expand, right-click context menu (tag, flag, add to case), and saved layouts.
- **Charts:** `echarts-for-react` for the dashboard (alert volume over time, risk distribution, Sankey fund-flow diagrams).
- **Auth:** JWT stored in memory + httpOnly refresh cookie; an Axios interceptor handles silent refresh and 401 redirect-to-login.

### 3.6 AI Architecture

Three independent, composable "signal producers," each stored as its own scored artifact so the explainability layer can cite exactly which one(s) fired:

1. **Statistical anomaly signal** (PyOD ensemble on flat features) → `anomaly_score` (0–1) + SHAP top-5 contributing features.
2. **Graph-pattern signal** (rule/heuristic pattern miner) → `pattern_matches: [{pattern: "peeling_chain", confidence, tx_chain: [...]}]`.
3. **Propagated-risk signal** (Personalized PageRank from real seed wallets) → `risk_score` (0–1) + `shortest_path_to_seed` (the literal path used as the "why," e.g. "3 hops from OFAC-designated wallet `bc1q...`").

A final **Alert Ranking Service** combines the three signals with a transparent, tunable weighted formula (weights configurable per investigation, defaulting to equal thirds), rather than a black-box meta-model — this keeps the *ranking itself* explainable, which the problem statement explicitly requires ("why a wallet/transaction was flagged, with a confidence score").

### 3.7 Database Architecture

Polyglot persistence, each store used for what it's actually good at:
- **Neo4j** — the wallet/TX/IP/entity graph itself (native traversal, GDS algorithms)
- **PostgreSQL+TimescaleDB** — everything relational/tabular: users, cases, alerts, audit log, raw ingested rows (as a TimescaleDB hypertable partitioned by `timestamp`, so range queries over millions of rows stay fast), and reference tables (`sanctioned_wallets`, `attribution_tags`)
- **Meilisearch** — denormalized, eventually-consistent search index (address, TXID, tag, case-note free text)
- **MinIO** — binary evidence (uploaded files, exported PDF/CSV reports, screenshot attachments)
- **Redis** — Celery broker/result backend + short-TTL cache for expensive graph queries

### 3.8 Blockchain Analysis Pipeline

See §12 for full algorithmic detail. Summary pipeline order: **Ingest → Normalize → Graph-build → Correlate (network↔blockchain) → Cluster (heuristic + Louvain + FastRP/HDBSCAN) → Feature-engineer → Anomaly-score (PyOD/PyGOD) → Pattern-detect (peeling/mixing) → Risk-propagate (Personalized PageRank) → Rank & explain → Alert**.

### 3.9 Authentication Flow

1. `POST /auth/login` (username+password) → `case-svc` verifies bcrypt hash (`passlib`) → issues short-lived JWT **access token** (15 min) + long-lived **refresh token** (7 days, httpOnly cookie), both signed with a server-side secret (`HS256` for the prototype; documented upgrade path to `RS256` with rotating keys for production).
2. Every subsequent request carries `Authorization: Bearer <access_token>`; FastAPI dependency `get_current_user` decodes+validates it and loads the user's `role` for RBAC checks.
3. `POST /auth/refresh` (refresh cookie) → new access token, refresh-token rotation (old one invalidated in a Postgres `revoked_tokens` table) to mitigate replay.
4. All authz decisions are role-based, enforced by a FastAPI dependency `require_role("investigator", "admin")` on each route (see §7 for the role matrix).
5. Every login, logout, and privileged action is written to `audit_log` (actor, action, target, timestamp, IP).

### 3.10 Module Interactions (sequence, textual)

`Frontend → api-service → {ingestion-svc | ai-service | graph-svc | case-svc}` — the four backend services never call each other's internal Python functions directly across a network boundary in this prototype (they run as a single FastAPI app with Celery workers, not separate microservice deployments, to keep operational complexity down per the "avoid unnecessary complexity" instruction); they communicate via **shared Postgres/Neo4j state and Celery task queues**, not synchronous RPC. This "modular monolith" shape can be split into true microservices later (per-service Dockerfiles are already separate, see §4) without an architectural rewrite.

---

## 4. Folder Structure

```
chainsentry/
├── backend/
│   ├── api_service/                 # FastAPI app: routers, request/response schemas, deps
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── cases.py
│   │   │   ├── alerts.py
│   │   │   ├── graph.py
│   │   │   ├── ingestion.py
│   │   │   ├── search.py
│   │   │   └── reports.py
│   │   └── deps.py                  # auth/RBAC dependencies
│   ├── ingestion_svc/
│   │   ├── parsers/                 # csv_parser.py, json_parser.py, xml_parser.py
│   │   ├── connectors/              # esplora.py, mempool_ws.py, bitnodes.py, opensanctions.py, geoip.py, kaggle_elliptic.py
│   │   ├── p2p_listener/            # self-capture P2P relay-timing tool (Python, python-bitcoinlib based)
│   │   └── tasks.py                 # Celery task definitions
│   ├── graph_svc/
│   │   ├── driver.py                # Neo4j Bolt driver singleton
│   │   ├── schema.cql               # node/relationship constraints & indexes
│   │   ├── clustering.py            # heuristic + Louvain + FastRP/HDBSCAN
│   │   └── risk_propagation.py      # personalized PageRank wrapper
│   ├── ai_service/
│   │   ├── features/                # feature engineering (mirrors Elliptic++ schema)
│   │   ├── models/                  # PyOD ensemble def, PyGOD models, trained artifacts (.pkl/.pt)
│   │   ├── patterns/                # peeling_chain.py, coinjoin_detect.py, pattern_registry.py
│   │   ├── explain/                 # shap_explainer.py, narrative.py (Claude API, optional)
│   │   ├── ranking.py               # alert ranking/combination logic
│   │   └── train.py                 # offline training script against Elliptic++
│   ├── case_svc/
│   │   ├── models.py                # SQLAlchemy models
│   │   ├── crud.py
│   │   └── audit.py
│   ├── chainsentry_common/          # shared pip-installable internal package
│   │   ├── schemas.py               # Pydantic models shared across services
│   │   ├── db.py                    # Postgres session factory (SQLAlchemy + TimescaleDB helpers)
│   │   ├── security.py              # JWT/bcrypt helpers
│   │   ├── config.py                # pydantic-settings based env config
│   │   └── logging.py
│   ├── alembic/                     # DB migrations
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/                # small sample CSV/JSON/XML + mini Elliptic subset for CI
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                     # routes/pages
│   │   │   ├── dashboard/
│   │   │   ├── cases/
│   │   │   ├── investigation/       # graph explorer screen
│   │   │   ├── wallet-explorer/
│   │   │   ├── tx-explorer/
│   │   │   ├── alerts/
│   │   │   ├── reports/
│   │   │   └── admin/
│   │   ├── components/
│   │   │   ├── graph/                # Cytoscape wrapper + layouts + context menus
│   │   │   ├── charts/                # ECharts wrappers (Sankey, timeline, risk histogram)
│   │   │   ├── geo/                   # Leaflet map components
│   │   │   └── ui/                    # shadcn/ui-based primitives
│   │   ├── hooks/
│   │   ├── lib/                       # api client (Axios + interceptors), auth store
│   │   └── types/                     # TS types mirrored from backend Pydantic schemas
│   ├── package.json
│   └── Dockerfile
├── ai/                               # standalone research/training notebooks (not shipped in prod image)
│   ├── notebooks/
│   │   ├── 01_elliptic_eda.ipynb
│   │   ├── 02_feature_engineering.ipynb
│   │   ├── 03_pyod_benchmark.ipynb
│   │   ├── 04_pygod_experiments.ipynb
│   │   └── 05_pattern_validation.ipynb
│   └── requirements-research.txt
├── data/
│   ├── raw/elliptic/                 # downloaded once, gitignored
│   ├── geoip/                        # GeoLite2 .mmdb, gitignored
│   ├── tagpacks/                     # GraphSense TagPacks import
│   └── sample/                       # small real-format sample CSV/JSON/XML for demo/dev
├── shared/
│   └── schemas/                      # JSON Schema definitions for the canonical ingest format (source of truth for both Pydantic and TS types)
├── infra/
│   ├── docker-compose.yml            # local, offline-friendly multi-service stack
│   ├── docker-compose.override.yml   # dev-only overrides (hot reload, exposed DB ports)
│   ├── neo4j/
│   │   └── neo4j.conf
│   └── env/
│       ├── .env.example
│       └── secrets.example.env
├── scripts/
│   ├── bootstrap_data.sh             # one-time: pull Elliptic++, GeoLite2, OpenSanctions, Bitnodes, TagPacks
│   ├── seed_demo_case.py             # loads /data/sample into a ready-to-demo case
│   └── train_models.sh               # runs ai_service/train.py end-to-end
├── docs/
│   ├── technical-writeup.md          # required deliverable: approach, model choice, explainability method
│   ├── api-reference.md              # generated/curated from OpenAPI
│   ├── architecture-decision-records/
│   └── user-guide.md
├── Makefile
└── README.md
```

**Purpose of top-level folders:** `backend/` — all Python services and the shared internal library; `frontend/` — the investigator UI; `ai/` — exploratory notebooks kept separate from production code so research experiments never accidentally ship; `data/` — all locally cached datasets (gitignored except `sample/`); `shared/` — the single source of truth for the ingest schema, consumed by both the Python and TypeScript type generators to guarantee frontend/backend never drift; `infra/` — everything needed to stand the whole stack up locally with Compose; `scripts/` — one-shot operational scripts; `docs/` — the required technical write-up plus supporting documentation.

---

## 5. Tech Stack (with versions)

| Category | Technology | Version |
|---|---|---|
| Backend language | Python | 3.12 |
| Backend framework | FastAPI | 0.115.x |
| ASGI server | Uvicorn (with `uvloop`) | 0.32.x |
| ORM / DB toolkit | SQLAlchemy | 2.0.x |
| Migrations | Alembic | 1.14.x |
| Relational DB | PostgreSQL | 16 |
| Time-series extension | TimescaleDB | 2.17.x |
| Graph DB | Neo4j Community Edition | 5.24.x (LTS) |
| Graph algorithms | Neo4j GDS | 2.11.x |
| Cache/broker | Redis | 7.4.x |
| Task queue | Celery | 5.4.x |
| Search | Meilisearch | 1.10.x |
| Object storage | MinIO | RELEASE.2025-x (latest stable) |
| AI/ML — anomaly detection | PyOD | 2.x |
| AI/ML — graph anomaly detection | PyGOD | 1.1.x |
| AI/ML — general | scikit-learn, NumPy, pandas | latest stable |
| AI/ML — graph embeddings | Neo4j GDS FastRP (in-DB) + `hdbscan` (Python) | GDS 2.11 / hdbscan 0.8.x |
| AI/ML — explainability | SHAP | 0.46.x |
| AI/ML — graph library (Python-side) | NetworkX | 3.4.x |
| LLM (optional narrative gen) | Anthropic Claude API, model `claude-sonnet-5` | via `anthropic` Python SDK |
| Auth | `python-jose[cryptography]`, `passlib[bcrypt]` | latest stable |
| Frontend framework | React | 18.3.x |
| Frontend language | TypeScript | 5.6.x |
| Build tool | Vite | 5.4.x |
| CSS | Tailwind CSS | 3.4.x |
| UI components | shadcn/ui | latest |
| Graph visualization | Cytoscape.js + `react-cytoscapejs` | 3.30.x |
| Charts | Apache ECharts (`echarts-for-react`) | 5.5.x |
| Maps | Leaflet + `react-leaflet` | 1.9.x / 4.2.x |
| Data fetching | TanStack Query | 5.x |
| Client state | Zustand | 5.x |
| Containerization | Docker + Docker Compose | Docker 27.x, Compose v2 |
| GeoIP | MaxMind GeoLite2 (City + ASN) | monthly snapshot |

---

## 6. Database Design

### 6.1 Canonical Ingest Schema (shared JSON Schema, `shared/schemas/tx_record.schema.json`)

Minimum fields, matching and extending the problem statement's list:

```json
{
  "timestamp": "ISO-8601 datetime",
  "src_ip": "string (IPv4/IPv6, nullable)",
  "dst_ip": "string (IPv4/IPv6, nullable)",
  "src_port": "integer (nullable)",
  "dst_port": "integer (nullable)",
  "txid": "string (64-char hex)",
  "input_addresses": ["string"],
  "output_addresses": ["string"],
  "input_amounts": ["number (BTC)"],
  "output_amounts": ["number (BTC)"],
  "fee": "number (BTC, nullable — derivable as sum(inputs)-sum(outputs))",
  "script_type": "string (p2pkh | p2sh | p2wpkh | p2wsh | p2tr | unknown)",
  "geo_country": "string (ISO 3166-1 alpha-2, nullable — enriched via GeoLite2 if src_ip present)",
  "asn": "integer (nullable — enriched via GeoLite2)",
  "source": "string (enum: elliptic | esplora | bitnodes | manual_upload | p2p_capture)"
}
```

### 6.2 PostgreSQL Schema (relational/time-series)

```sql
-- TimescaleDB hypertable for raw ingested transaction rows
CREATE TABLE raw_transactions (
    id              BIGSERIAL,
    txid            TEXT NOT NULL,
    ts              TIMESTAMPTZ NOT NULL,
    src_ip          INET,
    dst_ip          INET,
    src_port        INT,
    dst_port        INT,
    input_addresses TEXT[],
    output_addresses TEXT[],
    input_amounts   NUMERIC(16,8)[],
    output_amounts  NUMERIC(16,8)[],
    fee             NUMERIC(16,8),
    script_type     TEXT,
    geo_country     TEXT,
    asn             INT,
    source          TEXT NOT NULL,
    ingested_by     UUID REFERENCES users(id),
    ingest_batch_id UUID NOT NULL,
    PRIMARY KEY (id, ts)
);
SELECT create_hypertable('raw_transactions', 'ts');
CREATE INDEX idx_raw_tx_txid ON raw_transactions (txid);
CREATE INDEX idx_raw_tx_src_ip ON raw_transactions (src_ip);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin','lead_investigator','investigator','analyst','viewer')),
    full_name TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    status TEXT CHECK (status IN ('open','in_review','escalated','closed')) DEFAULT 'open',
    created_by UUID REFERENCES users(id),
    assigned_to UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(id),
    entity_type TEXT CHECK (entity_type IN ('wallet','transaction','cluster')),
    entity_ref TEXT NOT NULL,          -- wallet address / txid / cluster id (Neo4j node id/uuid)
    anomaly_score NUMERIC(5,4),
    risk_score NUMERIC(5,4),
    combined_confidence NUMERIC(5,4),
    fired_patterns JSONB,              -- e.g. [{"pattern":"peeling_chain","confidence":0.87,"tx_chain":[...]}]
    shap_explanation JSONB,
    status TEXT CHECK (status IN ('new','reviewing','confirmed','dismissed')) DEFAULT 'new',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_alerts_confidence ON alerts (combined_confidence DESC);

CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES cases(id),
    alert_id UUID REFERENCES alerts(id),
    file_key TEXT NOT NULL,            -- MinIO object key
    file_type TEXT,
    uploaded_by UUID REFERENCES users(id),
    uploaded_at TIMESTAMPTZ DEFAULT now(),
    notes TEXT
);

CREATE TABLE attribution_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    address TEXT NOT NULL,
    tag TEXT NOT NULL,                 -- e.g. "Binance hot wallet", "known mixer"
    category TEXT,                     -- exchange | mixer | darknet_market | ransomware | sanctioned | other
    source TEXT,                       -- e.g. "GraphSense TagPack" | "OpenSanctions" | "manual"
    confidence NUMERIC(3,2) DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX idx_tags_address_tag ON attribution_tags (address, tag, source);

CREATE TABLE sanctioned_wallets (
    address TEXT PRIMARY KEY,
    program TEXT,                       -- e.g. "OFAC SDN", "UK OFSI"
    entity_name TEXT,
    listed_on DATE,
    source_url TEXT
);

CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    actor_id UUID REFERENCES users(id),
    action TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    ip_address INET,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE revoked_tokens (
    jti UUID PRIMARY KEY,
    revoked_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);
```

### 6.3 Neo4j Graph Schema

**Node labels & key properties:**
- `(:Wallet {address, first_seen, last_seen, risk_score, cluster_id, entity_label})`
- `(:Transaction {txid, timestamp, fee, total_input_value, total_output_value, script_types})`
- `(:Cluster {cluster_id, method, size, label})`
- `(:IPObservation {ip, port, first_seen_ts, asn, country})`
- `(:ASN {number, org_name})`
- `(:Country {iso_code, name})`
- `(:AttributionTag {name, category})`

**Relationship types:**
- `(:Wallet)-[:INPUT_TO {amount}]->(:Transaction)`
- `(:Transaction)-[:OUTPUT_TO {amount, vout_index}]->(:Wallet)`
- `(:Wallet)-[:SAME_ENTITY_AS {method, confidence}]->(:Wallet)` (from heuristic clustering)
- `(:Wallet)-[:MEMBER_OF]->(:Cluster)`
- `(:Transaction)-[:FIRST_RELAYED_BY {latency_ms}]->(:IPObservation)` — the network↔blockchain correlation edge
- `(:IPObservation)-[:BELONGS_TO]->(:ASN)` and `(:IPObservation)-[:LOCATED_IN]->(:Country)`
- `(:Wallet)-[:TAGGED]->(:AttributionTag)`
- `(:Wallet)-[:SANCTIONED]->(:AttributionTag {name:"OFAC SDN"})` for seed-node marking

**Constraints & indexes (Cypher, `schema.cql`):**
```cypher
CREATE CONSTRAINT wallet_addr IF NOT EXISTS FOR (w:Wallet) REQUIRE w.address IS UNIQUE;
CREATE CONSTRAINT tx_id IF NOT EXISTS FOR (t:Transaction) REQUIRE t.txid IS UNIQUE;
CREATE CONSTRAINT ip_obs IF NOT EXISTS FOR (i:IPObservation) REQUIRE (i.ip, i.port, i.first_seen_ts) IS UNIQUE;
CREATE INDEX wallet_risk IF NOT EXISTS FOR (w:Wallet) ON (w.risk_score);
CREATE INDEX tx_timestamp IF NOT EXISTS FOR (t:Transaction) ON (t.timestamp);
```

**Query optimization strategy:** all hot-path traversals (neighborhood expansion, path-to-seed for explainability) are bounded by an explicit max-depth (default 4 hops) to prevent runaway queries on hub nodes (e.g. large exchange wallets with millions of edges); GDS algorithms run on **named graph projections** (`gds.graph.project`) restricted to the relevant subgraph rather than the whole database, both for performance and to let per-case analyses use different projections (e.g. "last 90 days only").

---

## 7. User Roles

| Role | Permissions | Dashboards | Investigation workflow | Access control |
|---|---|---|---|---|
| **Admin** | Full system access: user management, data-source configuration, model retraining triggers, all cases | System admin panel, all dashboards | Can view/edit any case | `require_role("admin")` on admin routes |
| **Lead Investigator** | Create/assign/close cases, override alert ranking weights, approve report exports, view all cases in their team | Team overview dashboard, case management | Owns end-to-end investigation lifecycle including sign-off | `require_role("admin","lead_investigator")` |
| **Investigator** | Create/work assigned cases, explore graph, tag entities, attach evidence, generate report drafts | Personal case queue, alert feed | Core day-to-day investigative work | `require_role("admin","lead_investigator","investigator")` |
| **Analyst** | Read/query access to graph, dashboards, and search; cannot modify cases or tags | Analytics dashboard (aggregate trends, not case-specific detail) | Supports investigators with ad-hoc queries, no case ownership | `require_role(..., "analyst")` on read-only routes |
| **Viewer** (e.g. auditor/observer) | Read-only access to closed/completed case reports | Report archive | No active investigation actions | `require_role(..., "viewer")` on report-view routes only |

All role checks are enforced server-side via a FastAPI dependency; the frontend also hides unavailable actions per role for UX clarity (never relied on alone for security).

---

## 8. Security

- **JWT authentication** — short-lived access tokens (15 min), rotating refresh tokens (7 days, httpOnly+`SameSite=Strict` cookie), `jti` claim checked against `revoked_tokens` on refresh/logout.
- **RBAC** — centralized `require_role(...)` FastAPI dependency, role matrix in §7, enforced on every mutating route and every case-scoped read.
- **Password hashing** — `bcrypt` via `passlib`, cost factor 12; no plaintext password ever logged (log redaction middleware strips `password`/`token` keys).
- **Input validation** — every request body is a Pydantic model with explicit types/constraints (e.g. `txid: constr(regex=r"^[0-9a-f]{64}$")`); uploaded CSV/JSON/XML is schema-validated against `shared/schemas/tx_record.schema.json` before any DB write, with row-level rejection + error report rather than all-or-nothing failure.
- **Secure API design** — all endpoints behind HTTPS in any non-local deployment (self-signed cert acceptable for the offline prototype, documented in `infra/`); CORS locked to the known frontend origin; consistent, non-leaky error responses (no stack traces to the client); pagination enforced (max page size) on all list endpoints to prevent resource-exhaustion.
- **File upload validation** — MIME-type and extension allow-list (`.csv`, `.json`, `.xml` only for ingestion; images/PDF for evidence), file-size cap, filename sanitization before MinIO key generation, virus-scan hook point documented (ClamAV integration point, not required for the offline prototype but stubbed in `ingestion_svc/parsers/__init__.py`).
- **Audit logs** — every login, logout, role change, case status change, alert status change, evidence upload, and report export is written to the immutable `audit_log` table (`actor_id`, `action`, `target`, `timestamp`, `ip_address`); the audit log itself is append-only at the application layer (no `UPDATE`/`DELETE` routes exposed for it).
- **Basic OWASP protections** — parameterized queries everywhere (SQLAlchemy ORM + parameterized Cypher, no string-concatenated queries anywhere in the codebase — enforced by a `bandit` + custom lint rule in CI), rate limiting on `/auth/login` (`slowapi`, 5 attempts/min/IP) to blunt brute-force, security headers middleware (`X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`) on all API responses, dependency vulnerability scanning (`pip-audit`, `npm audit`) as a documented pre-release check.

---

## 9. AI Integration

### 9.1 Models & Prompting Strategy
- **Entity clustering:** unsupervised, no LLM — see §12.1.
- **Anomaly detection:** PyOD unsupervised/semi-supervised ensemble (Isolation Forest + ECOD + AutoEncoder), trained offline once on Elliptic++ features, shipped as a versioned artifact (`ai_service/models/pyod_ensemble_v1.pkl`); re-trainable via `scripts/train_models.sh` when new labeled data is available.
- **Graph anomaly detection (optional):** PyGOD `DOMINANT` autoencoder, trained on the Elliptic++ address-transaction bipartite graph.
- **Risk scoring:** deterministic graph algorithm (Personalized PageRank), not a trained model — fully explainable by construction (the "why" is literally the shortest weighted path to a seed node).
- **Narrative/report generation (optional, LLM-based):** the *only* generative-AI component. Called with a strict, structured prompt that includes **only already-computed evidence** (SHAP top features, fired pattern names + parameters, risk-propagation path, entity tags) — the LLM is explicitly instructed to summarize and explain that evidence in plain English, **never to invent new findings or make an independent illicit/licit determination**. This is enforced by prompt design (system prompt: *"You are a report-drafting assistant. Only restate and explain the evidence provided. Do not assert new facts."*) and by keeping this step feature-flagged/optional so the core system's alerts never depend on it.

### 9.2 Entity Extraction
Not free-text NLP extraction (there's no free text in blockchain data) — "entity extraction" here means **entity resolution**: mapping many wallet *addresses* to one real-world *entity/cluster*, via the multi-input heuristic + graph clustering described in §12.1.

### 9.3 Risk Scoring (implementation detail)
```
CALL gds.graph.project(
  'walletGraph', 'Wallet',
  {SAME_ENTITY_AS: {orientation: 'UNDIRECTED'}, INPUT_TO: {orientation: 'NATURAL'}, OUTPUT_TO: {orientation: 'NATURAL'}}
)
CALL gds.pageRank.stream('walletGraph', {
  sourceNodes: $seed_wallet_node_ids,   -- from sanctioned_wallets + Elliptic-labeled-illicit
  dampingFactor: 0.85,
  maxIterations: 20
})
YIELD nodeId, score
```
Scores are min-max normalized to [0,1] and written back to `Wallet.risk_score`; a nightly Celery task recomputes this as the seed set and graph grow.

### 9.4 Report Generation
The `/api/reports/{case_id}/generate` endpoint assembles a structured JSON evidence bundle (all alerts in the case + their SHAP/pattern/risk explanations), renders it into a Markdown/PDF template (via `WeasyPrint`) deterministically (no LLM required for the *structured* report), and **optionally** calls the Claude API to prepend a one-paragraph plain-English executive summary — clearly labeled in the output as "AI-generated summary — verify against evidence below."

### 9.5 Transaction Summarization / Wallet Analysis
Deterministic, template-based summaries (e.g. "Wallet `bc1q...` received 42 inputs totaling 3.4 BTC over 6 months from 3 clusters, 2 of which are tagged 'exchange withdrawal', and propagated a risk score of 0.71 via a 2-hop path to OFAC-designated wallet `bc1q...`") are generated in Python string templates from the graph query results — **no LLM dependency** for this core, always-on feature, keeping the system's primary functionality independent of any external API call.

### 9.6 Classification
The PyOD ensemble's continuous anomaly score is thresholded (configurable, default top-5%-by-score = "flagged") rather than trained as a hard binary classifier, because unsupervised/semi-supervised scoring generalizes better to genuinely novel laundering patterns than a classifier trained only on Elliptic's specific historical illicit examples — this rationale is documented explicitly in the required technical write-up (`docs/technical-writeup.md`).

---

## 10. Blockchain Intelligence

| Capability | Approach |
|---|---|
| **Wallet analysis** | Aggregate in/out volume, counterparty diversity, active-time window, tag lookup, risk score — computed via a single Cypher query + Postgres tag join, exposed at `GET /api/wallets/{address}` |
| **Transaction tracing** | Recursive Cypher path traversal (`MATCH p = (w:Wallet)-[:INPUT_TO\|OUTPUT_TO*1..8]-(target)`) bounded by depth/amount-decay thresholds, visualized as a Sankey diagram (ECharts) showing fund flow and dilution over hops |
| **Wallet clustering** | Multi-input heuristic + Louvain/WCC + FastRP/HDBSCAN, §12.1 |
| **Address attribution** | Join against `attribution_tags` (GraphSense TagPacks + OpenSanctions + manual analyst tags) |
| **Cross-chain tracking** | Out of scope for the MVP (problem statement is Bitcoin-specific); architecture leaves room via the `Wallet.currency` property and pluggable `connectors/` modules — documented as a Phase-6/future-work item, not built now, per "avoid unnecessary complexity" |
| **Exchange identification** | Attribution tags (`category = 'exchange'`) combined with a structural heuristic (very high in/out-degree + many small "sweep" transactions) flagged as "likely exchange hot wallet" even when untagged |
| **Mixer detection** | Structural heuristic: transactions with N inputs ≈ N equal-value outputs (CoinJoin shape) or a `Wallet` whose neighborhood clustering coefficient and in/out amount entropy exceed thresholds tuned on known mixer addresses from TagPacks, §12.2 |
| **Risk scoring** | Personalized PageRank from real seed wallets, §9.3 |
| **Entity labeling** | Union of attribution tags + cluster-majority-vote label (if 60%+ of a cluster's addresses share a tag, the whole cluster inherits it) |
| **Timeline generation** | Time-bucketed Postgres query (`time_bucket()` from TimescaleDB) over `raw_transactions`, rendered as an ECharts timeline in the investigation view |
| **Graph traversal** | Cypher for graph-native queries; NetworkX for one-off in-memory pattern analysis on pulled subgraphs |

---

## 11. UI/UX Design

| Screen | Purpose |
|---|---|
| **Dashboard** | At-a-glance system health: new alerts today, open cases by status, risk-score distribution histogram, alert-volume timeline, top-10 highest-risk entities |
| **Investigation Workspace** | The core screen: split view — Cytoscape.js link-analysis graph on the left, entity detail panel (wallet/tx metadata, tags, risk score, SHAP explanation) on the right, timeline scrubber along the bottom |
| **Wallet Explorer** | Search/filter wallets by address, risk score range, tag, cluster; wallet detail page with in/out history table and mini fund-flow Sankey |
| **Transaction Explorer** | Search by TXID/date range/amount; transaction detail with full input/output breakdown and the network-layer `FIRST_RELAYED_BY` correlation if available |
| **Interactive Graph Visualization** | (embedded in Investigation Workspace) click-to-expand neighborhoods, right-click context menu ("Add to case," "Tag entity," "Mark reviewed"), saved custom layouts per case |
| **Timeline** | Zoomable, time-bucketed transaction/alert activity view, supports "play forward" animation of fund flow for presentations |
| **Alerts (queue)** | Ranked, filterable/sortable table (by confidence, pattern type, date), bulk-action toolbar (assign, dismiss, escalate) |
| **Reports** | List of generated case reports, "Generate New Report" wizard, PDF/Markdown/CSV export, optional AI-summary toggle |
| **Evidence Collection** | Per-case evidence list (uploaded files, screenshots, linked external references), drag-drop upload to MinIO |
| **Search** | Global Meilisearch-backed omnibox (⌘K-style) across addresses, TXIDs, tags, case titles, notes |
| **Filters** | Persistent filter bar (date range, risk-score threshold, tag category, source) shared across Wallet/Transaction/Alert screens |
| **Case Management** | Kanban-style board (Open → In Review → Escalated → Closed), case detail page aggregating its alerts/evidence/graph/report |

---

## 12. AI/ML Detection Use Cases — Full Algorithmic Detail

### 12.1 Entity Clustering
**Step 1 — Common-Input-Ownership Heuristic (deterministic, explainable):** for every transaction with ≥2 input addresses (excluding known CoinJoin/mixer-shaped transactions, filtered out first via §12.2's detector so they don't wrongly merge unrelated users), union all its input addresses into the same cluster (classic union-find). This is the single most-used, most-trusted heuristic in real chain analysis and is 100% explainable ("these addresses were co-spent in TXID X").

**Step 2 — Neo4j GDS Louvain/WCC (graph-ML refinement):** run on the full `SAME_ENTITY_AS`-projected graph to detect communities the pure heuristic misses (e.g. via shared change-address patterns) — `CALL gds.louvain.stream('walletGraph')`.

**Step 3 — FastRP graph embeddings + HDBSCAN (the explicit "graph embeddings" requirement):** `CALL gds.fastRP.mutate('walletGraph', {embeddingDimension: 128, randomSeed: 42})` exports a 128-dim vector per wallet; these are clustered with `hdbscan.HDBSCAN(min_cluster_size=5)` in Python as a third, independent signal, specifically to catch entities connected mainly through *behavioral similarity* (transaction timing/amount patterns) rather than direct co-spending.

**Reconciliation:** a wallet's final `cluster_id` = the heuristic cluster if one exists (highest confidence/most explainable), else the Louvain community, with the HDBSCAN result stored separately as a `secondary_cluster_id` used only to *surface a suggestion* to the analyst ("these two clusters show high behavioral similarity — possible same entity?") rather than silently auto-merging, since embedding-based clustering is less directly explainable.

### 12.2 Anomaly Detection
**Feature engineering** (mirrors the real, published Elliptic++ feature categories, so the trained model transfers cleanly to live data): per-transaction — input/output count, total value, fee rate, script-type mix, time-of-day, value round-number-ness; per-wallet — in/out-degree, counterparty entropy, active lifespan, average holding time before re-spend, one-hop and two-hop aggregated neighbor statistics (mirroring Elliptic's local+aggregated feature design).

**Model:** a PyOD ensemble — `IForest` (global outliers), `ECOD` (distribution-based, parameter-free, fast), and `AutoEncoder` (captures non-linear feature interactions) — combined via PyOD's `combination.average` or `maximization` utilities; trained/validated on Elliptic++'s labeled illicit/licit split (standard 70/30 temporal split, since the dataset has explicit time-steps, avoiding train/test leakage across time).

**Explainability:** `shap.TreeExplainer`/`shap.KernelExplainer` (algorithm-appropriate per model in the ensemble) computed on-demand for any flagged transaction, returning the top-5 features driving the score (e.g. "unusually high fee-to-value ratio," "output count far above wallet's historical average").

### 12.3 Peeling-Chain / Mixing Detection
**Peeling chain:** a NetworkX pattern miner walks chains of transactions where (a) each transaction has exactly 2 outputs, (b) one output is "peeled off" (small, sent onward) while the other returns to a fresh address controlled by the same apparent entity (detected via the change-address heuristic: same script type as an input, non-round amount), and (c) the chain length exceeds a configurable threshold (default 5+ hops) — this published pattern (funds "peeled" in small increments down a long chain to obscure trail) is flagged with a confidence proportional to chain length and value-decay consistency.

**CoinJoin-like / mixing detection:** flags transactions where the number of equal-value outputs ≥ some threshold (e.g. 3+ outputs of exactly the same amount, a hallmark of CoinJoin-style mixing) combined with an input count ≥ output-equal-value count (participants ≥ outputs); wallets that are repeat participants in such transactions are tagged `category='mixer_participant'` and excluded from Step 1 of §12.1's clustering (to avoid wrongly merging unrelated mixer participants into one "entity").

### 12.4 Risk Scoring
Personalized PageRank from real seed nodes, §9.3 — chosen over a simple "N-hop taint" rule because PageRank naturally down-weights risk through high-volume "dilution" hubs (e.g., a large exchange) the way real forensic taint-analysis methodology does, while remaining a single well-documented, auditable graph algorithm rather than a black box.

---

## 13. Testing Plan

| Level | Scope | Tooling |
|---|---|---|
| **Unit** | Parsers (CSV/JSON/XML → `NormalizedTxRecord`), feature-engineering functions, pattern-detector logic (peeling-chain/CoinJoin on hand-crafted fixture graphs with known expected output), JWT/RBAC helpers | `pytest`, `pytest-cov` (target ≥80% on `ai_service`/`ingestion_svc`) |
| **Integration** | Full ingestion→graph-build→clustering pipeline against a small real fixture (a curated ~500-tx slice of Elliptic++ plus matching sample CSV); Neo4j/Postgres/Redis spun up via `testcontainers-python` | `pytest` + `testcontainers` |
| **API** | Every route: auth flows (login/refresh/expired-token/wrong-role), CRUD on cases/alerts/evidence, ingestion endpoint with valid/invalid files, pagination/filter params | `pytest` + FastAPI `TestClient` |
| **Model evaluation** | PyOD ensemble precision/recall/AUPRC against the held-out Elliptic++ temporal test split (the standard published benchmark split), regression-tested so re-training never silently degrades performance | dedicated `ai/notebooks/03_pyod_benchmark.ipynb` promoted into a CI-runnable `tests/model_eval/` script with a minimum-AUPRC assertion |
| **End-to-End** | Full user journey through the running Compose stack: login → upload sample dataset → wait for processing → see ranked alerts → open investigation graph → tag entity → generate report → verify PDF | Playwright (TypeScript), run against `docker-compose -f infra/docker-compose.yml up` in CI |
| **Security** | Static analysis (`bandit` for Python, `npm audit`/`eslint-plugin-security` for TS), dependency scanning (`pip-audit`), manual OWASP-Top-10 checklist review before each milestone demo | `bandit`, `pip-audit`, `npm audit` |

---

## 14. Development Roadmap

### Phase 1 — Foundations & Real Data Pipeline (Weeks 1–2)
- **Deliverables:** repo scaffold (folder structure §4); Docker Compose stack running (Postgres+TimescaleDB, Neo4j+GDS, Redis, Meilisearch, MinIO); `scripts/bootstrap_data.sh` pulling Elliptic++, GeoLite2, OpenSanctions, Bitnodes snapshot, GraphSense TagPacks; canonical ingest schema (`shared/schemas/tx_record.schema.json`) finalized; CSV/JSON/XML parsers with unit tests; JWT auth + RBAC skeleton; DB migrations for the full Postgres schema and Neo4j constraints.
- **Dependencies:** none (first phase).
- **Priority:** Critical — everything else depends on this.

### Phase 2 — Graph Construction & Correlation (Weeks 3–4)
- **Deliverables:** ingestion → Neo4j graph-build pipeline (Wallet/Transaction/IPObservation nodes, all relationship types from §6.3) working end-to-end on Elliptic++ + Bitnodes/GeoLite2-enriched data; the network↔blockchain `FIRST_RELAYED_BY` correlation job; self-capture P2P listener tool for genuinely live relay-timing data (offline mode); basic `graph-svc` neighborhood-query API.
- **Dependencies:** Phase 1 data pipeline and schema.
- **Priority:** Critical.

### Phase 3 — AI/ML Core: Clustering, Anomaly Detection, Risk Scoring (Weeks 5–7)
- **Deliverables:** multi-input clustering heuristic + Louvain/WCC + FastRP/HDBSCAN (§12.1); PyOD ensemble trained/evaluated on Elliptic++ with documented benchmark results; SHAP explainability wired to alert generation; Personalized PageRank risk propagation from real seed wallets; peeling-chain and CoinJoin pattern detectors (§12.3) validated against known-mixer TagPack addresses; Alert Ranking Service combining all three signals.
- **Dependencies:** Phase 2 graph.
- **Priority:** Critical — this is the core "working model, not just rules" deliverable the problem statement demands.

### Phase 4 — Investigator Dashboard & Link-Analysis UI (Weeks 6–9, overlapping Phase 3)
- **Deliverables:** full frontend (§4/§11 screens); Cytoscape.js investigation graph with expand/tag/context-menu actions; ECharts dashboard/timeline/Sankey views; Leaflet geo view; Meilisearch-backed global search; case management Kanban; alert queue with filters/sorting.
- **Dependencies:** stable `graph-svc`/`ai-service`/`case-svc` APIs from Phases 2–3 (can start against mocked API responses earlier to parallelize).
- **Priority:** High.

### Phase 5 — Reporting, Explainability Polish, Optional LLM Narrative, Hardening (Weeks 9–11)
- **Deliverables:** PDF/Markdown/CSV report generation (WeasyPrint templates); optional Claude-API narrative-summary integration (feature-flagged); full security hardening pass (§8 checklist); audit-log UI for admins; complete test suite (§13) green in CI; required technical write-up (`docs/technical-writeup.md`) finalized covering approach, model choice, and explainability method.
- **Dependencies:** Phases 2–4 substantially complete.
- **Priority:** High.

### Phase 6 (Stretch, post-MVP, explicitly out of scope for the SIH deliverable but documented for future work)
- PyGOD graph-autoencoder anomaly detection as a second, corroborating signal; cross-chain (Ethereum/Litecoin) support via the already-pluggable `connectors/` pattern; collaborative multi-analyst real-time case editing; automated periodic re-training pipeline as new labeled cases are confirmed by investigators (active-learning loop).

---

## 15. Getting Started (local, offline-first)

```bash
git clone <repo> chainsentry && cd chainsentry
cp infra/env/.env.example infra/env/.env        # fill in KAGGLE_*, MAXMIND_LICENSE_KEY, (optional) ANTHROPIC_API_KEY
./scripts/bootstrap_data.sh                     # one-time: pulls Elliptic++, GeoLite2, OpenSanctions, Bitnodes, TagPacks
docker compose -f infra/docker-compose.yml up -d --build
python scripts/seed_demo_case.py                # loads /data/sample into a ready-to-demo case
./scripts/train_models.sh                       # trains the PyOD ensemble on Elliptic++, writes model artifact
# Frontend: http://localhost:5173   Backend API docs: http://localhost:8000/docs   Neo4j Browser: http://localhost:7474
```

After `bootstrap_data.sh` completes once, the stack requires **no further internet access** — all subsequent runs (`docker compose up`) work fully offline, satisfying the problem statement's "workable complete offline solution for linux platform" requirement. The only feature that calls out to the internet at runtime is the optional Claude-API narrative summary, which is off by default and clearly toggled in Settings.
