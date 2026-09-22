"""ChainSentry Omnibox Search Router.
Fast search across transactions, addresses, clusters, tags, cases, and alerts.
"""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.chainsentry_common.db import get_db
from backend.graph_svc.graph_engine import ForensicGraphEngine
from backend.case_svc.models import Case, Alert, AttributionTag, User
from backend.api_service.deps import get_current_user

router = APIRouter(prefix="/search", tags=["Search"])

@router.get("")
def search(
    q: str = Query(..., min_length=2, description="Search query string"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, List[Dict[str, Any]]]:
    q_clean = q.strip().lower()
    engine = ForensicGraphEngine.get_instance()

    matched_wallets = []
    matched_txs = []

    # Search in-memory graph
    for node, data in engine.graph.nodes(data=True):
        ntype = data.get("node_type")
        node_lower = node.lower()
        if q_clean in node_lower:
            if ntype == "wallet":
                matched_wallets.append({
                    "address": node,
                    "risk_score": data.get("risk_score", 0.0),
                    "cluster_id": data.get("cluster_id"),
                    "tags": data.get("tags", [])
                })
            elif ntype == "transaction":
                matched_txs.append({
                    "txid": node,
                    "total_value": data.get("total_value", 0.0),
                    "fee": data.get("fee", 0.0),
                    "timestamp": data.get("timestamp")
                })
        if len(matched_wallets) >= 20 and len(matched_txs) >= 20:
            break

    # Search Cases
    cases = db.query(Case).filter(
        (Case.title.ilike(f"%{q_clean}%")) | (Case.description.ilike(f"%{q_clean}%"))
    ).limit(10).all()
    matched_cases = [{
        "id": c.id,
        "title": c.title,
        "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None
    } for c in cases]

    # Search Alerts
    alerts = db.query(Alert).filter(Alert.entity_ref.ilike(f"%{q_clean}%")).limit(10).all()
    matched_alerts = [{
        "id": a.id,
        "entity_ref": a.entity_ref,
        "confidence": float(a.combined_confidence or 0.0),
        "status": a.status
    } for a in alerts]

    # Search Tags
    tags = db.query(AttributionTag).filter(
        (AttributionTag.tag.ilike(f"%{q_clean}%")) | (AttributionTag.address.ilike(f"%{q_clean}%"))
    ).limit(10).all()
    matched_tags = [{
        "address": t.address,
        "tag": t.tag,
        "category": t.category
    } for t in tags]

    return {
        "wallets": matched_wallets,
        "transactions": matched_txs,
        "cases": matched_cases,
        "alerts": matched_alerts,
        "tags": matched_tags
    }
