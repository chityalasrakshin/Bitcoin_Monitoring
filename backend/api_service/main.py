"""ChainSentry FastAPI Main Application.
Entry point for the AI-Powered Bitcoin Transaction Monitoring & Forensics Platform (SIH26146).
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.chainsentry_common.config import settings
from backend.chainsentry_common.db import init_db, SessionLocal
from backend.chainsentry_common.logging import logger
from backend.ingestion_svc.connectors.geoip import GeoIPResolver
from backend.api_service.routers import auth, cases, alerts, graph, ingestion, search, reports

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    logger.info("Initializing ChainSentry platform...")
    init_db()
    GeoIPResolver.get_instance()

    # Pre-seed demo data and populate in-memory graph
    try:
        from backend.case_svc.models import Alert, SanctionedWallet
        from backend.api_service.routers.ingestion import execute_full_pipeline
        from backend.ingestion_svc.parsers.csv_parser import parse_transactions_csv, parse_network_observations_csv
        from backend.graph_svc.graph_engine import ForensicGraphEngine
        from backend.ingestion_svc.correlation import CorrelationEngine
        from backend.graph_svc.clustering import EntityClusteringEngine
        from backend.graph_svc.risk_propagation import RiskPropagationEngine

        engine = ForensicGraphEngine.get_instance()
        if engine.graph.number_of_nodes() == 0:
            tx_csv = settings.SAMPLE_DATA_DIR / "transactions.csv"
            net_csv = settings.SAMPLE_DATA_DIR / "network_observations.csv"
            if tx_csv.exists() and net_csv.exists():
                logger.info("Initializing in-memory forensic graph from sample dataset...")
                with open(tx_csv, "r", encoding="utf-8") as f:
                    txs = parse_transactions_csv(f.read())
                with open(net_csv, "r", encoding="utf-8") as f:
                    obs = parse_network_observations_csv(f.read())

                with SessionLocal() as session:
                    existing_alert = session.query(Alert).first()
                    if not existing_alert:
                        execute_full_pipeline(txs, obs, session)
                    else:
                        correlator = CorrelationEngine()
                        correlations = correlator.correlate(txs, obs)
                        for tx in txs:
                            engine.add_transaction(tx, correlations.get(tx.txid))
                        EntityClusteringEngine().cluster_transactions(txs, update_graph=True)
                        sanctioned_records = session.query(SanctionedWallet.address).all()
                        seeds = [s[0] for s in sanctioned_records] if sanctioned_records else []
                        if not seeds:
                            seeds = [
                                "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                                "bc1qa5wkgaew2dkv56kfvj49j0av5nml45x9ek9hz6",
                                "sbc18d20c1d613b34c0e6946f41fc34692fc9daf10"
                            ]
                        RiskPropagationEngine().propagate_risk(seeds, update_graph=True)
                logger.info(f"Forensic graph populated with {engine.graph.number_of_nodes()} nodes and {engine.graph.number_of_edges()} edges.")
    except Exception as e:
        logger.warning(f"Forensic graph initialization deferred: {e}")

    logger.info("ChainSentry API ready for investigative queries.")
    yield
    logger.info("Shutting down ChainSentry platform.")

app = FastAPI(
    title=f"{settings.APP_NAME} — Bitcoin Forensics Platform",
    description="Offline AI-Powered Monitoring & Forensic Correlation of Bitcoin Transaction Traffic (SIH26146)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# Register Routers
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(cases.router, prefix=settings.API_PREFIX)
app.include_router(alerts.router, prefix=settings.API_PREFIX)
app.include_router(graph.router, prefix=settings.API_PREFIX)
app.include_router(ingestion.router, prefix=settings.API_PREFIX)
app.include_router(search.router, prefix=settings.API_PREFIX)
app.include_router(reports.router, prefix=settings.API_PREFIX)

@app.get("/health")
def healthcheck():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0"
    }

# Mount Frontend SPA if built
frontend_dist = settings.BASE_DIR / "frontend" / "dist"
if frontend_dist.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

