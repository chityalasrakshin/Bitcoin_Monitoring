"""ChainSentry Forensic Graph Router.
Provides Cytoscape/3D subgraphs, neighborhood expansions, attribution tags,
and dynamic on-chain address/tx resolution.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.chainsentry_common.db import get_db
from backend.chainsentry_common.schemas import GraphData, AttributionTagCreate, AttributionTagResponse
from backend.chainsentry_common.logging import logger
from backend.graph_svc.graph_engine import ForensicGraphEngine
from backend.graph_svc.clustering import EntityClusteringEngine
from backend.case_svc import crud
from backend.case_svc.models import User, RawTransaction
from backend.api_service.deps import get_current_user
from backend.ingestion_svc.connectors.blockchain import LiveBlockchainConnector

router = APIRouter(prefix="/graph", tags=["Forensic Graph & Link Analysis"])

@router.get("/neighborhood", response_model=GraphData)
def get_neighborhood(
    entity_id: str = Query(..., description="Wallet address, TXID, or IP to center graph expansion on"),
    depth: int = Query(2, ge=1, le=5, description="Expansion hop depth"),
    max_nodes: int = Query(150, ge=10, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    engine = ForensicGraphEngine.get_instance()
    entity_clean = entity_id.strip()

    # If entity is not in the graph, attempt dynamic on-chain lookup
    if not engine.graph.has_node(entity_clean):
        logger.info(f"Entity '{entity_clean}' not in local graph. Attempting dynamic on-chain lookup...")
        connector = LiveBlockchainConnector()

        # Check if it's a 64-char transaction hash or an address
        if len(entity_clean) == 64 and all(c in "0123456789abcdefABCDEF" for c in entity_clean):
            tx = connector.fetch_transaction(entity_clean)
            if tx:
                engine.add_transaction(tx)
                EntityClusteringEngine().cluster_transactions([tx], update_graph=True)
                # Persist to DB
                raw_tx = RawTransaction(
                    txid=tx.txid,
                    ts=tx.timestamp,
                    input_addresses=tx.input_addresses,
                    output_addresses=tx.output_addresses,
                    input_amounts=tx.input_amounts,
                    output_amounts=tx.output_amounts,
                    fee=tx.fee,
                    script_type=tx.script_type,
                    source="live_blockchain",
                    provenance="mempool.space"
                )
                db.add(raw_tx)
                db.commit()
        else:
            txs = connector.fetch_address_transactions(entity_clean, limit=10)
            if txs:
                for tx in txs:
                    engine.add_transaction(tx)
                    raw_tx = RawTransaction(
                        txid=tx.txid,
                        ts=tx.timestamp,
                        input_addresses=tx.input_addresses,
                        output_addresses=tx.output_addresses,
                        input_amounts=tx.input_amounts,
                        output_amounts=tx.output_amounts,
                        fee=tx.fee,
                        script_type=tx.script_type,
                        source="live_blockchain",
                        provenance="mempool.space"
                    )
                    db.add(raw_tx)
                EntityClusteringEngine().cluster_transactions(txs, update_graph=True)
                db.commit()

    data = engine.get_neighborhood(entity_id=entity_clean, depth=depth, max_nodes=max_nodes)
    return data

@router.get("/wallets")
def get_wallets(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    sort_by: str = Query("risk"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    engine = ForensicGraphEngine.get_instance()
    return engine.get_wallets_paginated(skip=skip, limit=limit, search=search, sort_by=sort_by)

@router.get("/transactions")
def get_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    sort_by: str = Query("time"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    engine = ForensicGraphEngine.get_instance()
    return engine.get_transactions_paginated(skip=skip, limit=limit, search=search, sort_by=sort_by)

@router.get("/stats")
def get_graph_stats(current_user: User = Depends(get_current_user)):
    engine = ForensicGraphEngine.get_instance()
    return engine.get_stats()

@router.get("/tags/{address}", response_model=List[AttributionTagResponse])
def get_address_tags(
    address: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tags = crud.get_tags_for_address(db, address)
    return [AttributionTagResponse.model_validate(t) for t in tags]

@router.post("/tags", response_model=AttributionTagResponse)
def add_address_tag(
    tag_in: AttributionTagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tag_obj = crud.add_attribution_tag(db, tag_in)
    ForensicGraphEngine.get_instance().add_wallet_tag(tag_in.address, tag_in.tag)
    return AttributionTagResponse.model_validate(tag_obj)
