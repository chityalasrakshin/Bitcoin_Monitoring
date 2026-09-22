"""ChainSentry Demo Case Seeder.
Ingests the Seed-42 reference dataset, correlates peer-to-peer network telemetry with on-chain data,
runs clustering and anomaly detection, and scaffolds an active forensic case with attached evidence.
"""
from datetime import datetime, timezone
from backend.chainsentry_common.config import settings
from backend.chainsentry_common.db import init_db, SessionLocal
from backend.chainsentry_common.schemas import CaseCreate, CaseStatus
from backend.chainsentry_common.logging import logger
from backend.case_svc import crud
from backend.case_svc.models import User, Alert
from backend.ingestion_svc.parsers.csv_parser import parse_transactions_csv, parse_network_observations_csv
from backend.api_service.routers.ingestion import execute_full_pipeline
from scripts.bootstrap_data import bootstrap_ofac_sanctions, bootstrap_tagpacks

def seed_demo():
    logger.info("Initializing ChainSentry database and reference tags...")
    init_db()

    with SessionLocal() as session:
        bootstrap_ofac_sanctions(session)
        bootstrap_tagpacks(session)

        # Get investigator user
        investigator = session.query(User).filter(User.username == "investigator").first()
        user_id = investigator.id if investigator else None

        # 1. Parse sample dataset
        tx_csv = settings.SAMPLE_DATA_DIR / "transactions.csv"
        net_csv = settings.SAMPLE_DATA_DIR / "network_observations.csv"

        logger.info(f"Loading sample dataset from {settings.SAMPLE_DATA_DIR}...")
        with open(tx_csv, "r", encoding="utf-8") as f:
            transactions = parse_transactions_csv(f.read())
        with open(net_csv, "r", encoding="utf-8") as f:
            observations = parse_network_observations_csv(f.read())

        # 2. Execute full forensic pipeline
        stats = execute_full_pipeline(transactions, observations, session, actor_id=user_id)
        logger.info(f"Pipeline executed in {stats.duration_seconds}s: {stats.total_alerts_generated} alerts generated")

        # 3. Create active demo case
        case_in = CaseCreate(
            title="OPERATION CYBER-TRACE: SIH26146 Bitcoin Network & Laundering Forensics",
            description=(
                "Forensic correlation of Bitcoin transaction traffic with peer-to-peer relay telemetry. "
                "Investigating multi-hop peeling chains, mixer consolidation, and sanctions risk propagation."
            ),
            status=CaseStatus.IN_REVIEW,
            assigned_to=user_id
        )
        case = crud.create_case(session, case_in, user_id=user_id)
        logger.info(f"Created forensic case: [{case.id[:8]}] {case.title}")

        # 4. Attach top alerts to case
        top_alerts = session.query(Alert).filter(Alert.case_id == None).order_by(Alert.combined_confidence.desc()).limit(15).all()
        for a in top_alerts:
            a.case_id = case.id
            a.status = "reviewing"
        session.commit()
        logger.info(f"Attached {len(top_alerts)} prioritized leads to case {case.id[:8]}")

        # 5. Add initial evidence record
        crud.add_evidence(
            db=session,
            case_id=case.id,
            file_key="evidence/raw_network_pcap_seed42.log",
            file_type="network_log",
            notes="Initial P2P listener raw INV/tx broadcast capture log containing 368 peer relay observations.",
            uploaded_by=user_id,
            alert_id=top_alerts[0].id if top_alerts else None
        )

        logger.info("Demo case successfully seeded and ready for investigation.")

if __name__ == "__main__":
    seed_demo()
