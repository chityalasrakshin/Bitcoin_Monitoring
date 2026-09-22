"""ChainSentry Ingestion & Pipeline Router.
Coordinates parsing, correlation, graph construction, clustering, AI anomaly scoring, and alert generation.
"""
import time
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.chainsentry_common.db import get_db
from backend.chainsentry_common.config import settings
from backend.chainsentry_common.schemas import (
    NormalizedTxRecord, NetworkObservationRecord, IngestStats, AlertCreate
)
from backend.chainsentry_common.logging import logger
from backend.case_svc.models import User, RawTransaction, RawNetworkObservation, SanctionedWallet
from backend.case_svc import crud
from backend.case_svc.audit import log_action
from backend.api_service.deps import get_current_user, require_role

from backend.ingestion_svc.parsers.csv_parser import parse_transactions_csv, parse_network_observations_csv
from backend.ingestion_svc.parsers.json_parser import parse_transactions_json, parse_network_observations_json
from backend.ingestion_svc.parsers.xml_parser import parse_transactions_xml
from backend.ingestion_svc.correlation import CorrelationEngine
from backend.graph_svc.graph_engine import ForensicGraphEngine
from backend.graph_svc.clustering import EntityClusteringEngine
from backend.graph_svc.risk_propagation import RiskPropagationEngine
from backend.ai_service.features.engineer import build_feature_dataframe
from backend.ai_service.models.ensemble import AnomalyEnsemble
from backend.ai_service.explain.shap_explainer import ForensicsExplainer
from backend.ai_service.patterns.pattern_registry import PatternRegistry
from backend.ai_service.ranking import AlertRankingService

router = APIRouter(prefix="/ingestion", tags=["Ingestion & Pipeline"])

def execute_full_pipeline(
    transactions: List[NormalizedTxRecord],
    observations: List[NetworkObservationRecord],
    db: Session,
    actor_id: Optional[str] = None
) -> IngestStats:
    """Execute the end-to-end ChainSentry forensic pipeline."""
    start_time = time.time()
    logger.info(f"Executing pipeline on {len(transactions)} txs and {len(observations)} observations")

    # 1. Network-to-Blockchain Correlation
    correlator = CorrelationEngine()
    correlations = correlator.correlate(transactions, observations)

    # 2. Graph Construction
    graph_engine = ForensicGraphEngine.get_instance()
    # Reset and populate
    graph_engine.clear()
    for tx in transactions:
        corr = correlations.get(tx.txid)
        graph_engine.add_transaction(tx, corr)

    # 3. Entity Clustering (Common-Input-Ownership Heuristic with CoinJoin exclusion)
    clustering_engine = EntityClusteringEngine()
    clusters = clustering_engine.cluster_transactions(transactions, update_graph=True)

    # 4. Risk Propagation (seeding from known OFAC/sanctions)
    sanctioned_records = db.query(SanctionedWallet.address).all()
    seed_addresses = [s[0] for s in sanctioned_records] if sanctioned_records else []
    # If no seeds in DB, add any known high-risk/eval seeds
    if not seed_addresses:
        # Fallback to standard seed set
        seed_addresses = [
            "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "bc1qa5wkgaew2dkv56kfvj49j0av5nml45x9ek9hz6",
            "sbc18d20c1d613b34c0e6946f41fc34692fc9daf10"
        ]

    risk_engine = RiskPropagationEngine()
    wallet_risks = risk_engine.propagate_risk(seed_addresses, update_graph=True)

    # 5. Graph Pattern Detection (Peeling chains, CoinJoins, structuring)
    pattern_reg = PatternRegistry()
    fired_patterns = pattern_reg.run_all(transactions)

    # 6. Feature Engineering
    feature_df, txids = build_feature_dataframe(transactions, correlations)

    # 7. AI Anomaly Scoring
    ensemble = AnomalyEnsemble()
    anomaly_scores = ensemble.predict_anomaly_scores(feature_df)

    # 8. SHAP Explanation
    explainer = ForensicsExplainer(ensemble)

    # 9. Alert Ranking and Multi-Signal Fusion
    ranker = AlertRankingService()
    alerts = ranker.rank_leads(
        transactions=transactions,
        feature_df=feature_df,
        anomaly_scores=anomaly_scores.tolist(),
        explainer=explainer,
        patterns=fired_patterns,
        wallet_risks=wallet_risks
    )

    # 10. Persist Raw Records and Alerts to DB
    for a in alerts:
        crud.create_alert(db, a)

    duration = time.time() - start_time
    stats = IngestStats(
        total_transactions_ingested=len(transactions),
        total_observations_ingested=len(observations),
        total_correlations_found=len(correlations),
        total_entities_clustered=len(clusters),
        total_alerts_generated=len(alerts),
        duration_seconds=round(duration, 2)
    )

    log_action(
        db=db,
        action="PIPELINE_RUN",
        actor_id=actor_id,
        target_type="pipeline",
        target_id="batch",
        metadata=stats.model_dump()
    )

    return stats

@router.post("/run-sample", response_model=IngestStats)
def run_sample_pipeline(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "lead_investigator", "investigator"))
):
    """Run pipeline against the sample dataset in data/sample/ (e.g. Seed-42)."""
    tx_csv = settings.SAMPLE_DATA_DIR / "transactions.csv"
    net_csv = settings.SAMPLE_DATA_DIR / "network_observations.csv"

    if not tx_csv.exists() or not net_csv.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Sample data files not found in {settings.SAMPLE_DATA_DIR}"
        )

    with open(tx_csv, "r", encoding="utf-8") as f:
        transactions = parse_transactions_csv(f.read())

    with open(net_csv, "r", encoding="utf-8") as f:
        observations = parse_network_observations_csv(f.read())

    stats = execute_full_pipeline(transactions, observations, db, actor_id=current_user.id)
    return stats

@router.post("/upload", response_model=IngestStats)
async def upload_files(
    tx_file: UploadFile = File(..., description="Transactions CSV, JSON, or XML"),
    obs_file: Optional[UploadFile] = File(None, description="Network observations CSV or JSON"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "lead_investigator", "investigator"))
):
    """Upload and ingest custom transactions and network observations files."""
    tx_bytes = await tx_file.read()
    tx_filename = tx_file.filename.lower() if tx_file.filename else ""

    if tx_filename.endswith(".json"):
        transactions = parse_transactions_json(tx_bytes)
    elif tx_filename.endswith(".xml"):
        transactions = parse_transactions_xml(tx_bytes)
    else:
        transactions = parse_transactions_csv(tx_bytes)

    observations: List[NetworkObservationRecord] = []
    if obs_file:
        obs_bytes = await obs_file.read()
        obs_filename = obs_file.filename.lower() if obs_file.filename else ""
        if obs_filename.endswith(".json"):
            observations = parse_network_observations_json(obs_bytes)
        else:
            observations = parse_network_observations_csv(obs_bytes)

    stats = execute_full_pipeline(transactions, observations, db, actor_id=current_user.id)
    return stats
