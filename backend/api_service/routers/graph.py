"""ChainSentry Forensic Graph Router.
Provides Cytoscape.js subgraphs, neighborhood expansions, and attribution tags.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.chainsentry_common.db import get_db
from backend.chainsentry_common.schemas import GraphData, AttributionTagCreate, AttributionTagResponse
from backend.graph_svc.graph_engine import ForensicGraphEngine
from backend.case_svc import crud
from backend.case_svc.models import User
from backend.api_service.deps import get_current_user

router = APIRouter(prefix="/graph", tags=["Forensic Graph & Link Analysis"])

@router.get("/neighborhood", response_model=GraphData)
def get_neighborhood(
    entity_id: str = Query(..., description="Wallet address, TXID, or IP to center graph expansion on"),
    depth: int = Query(2, ge=1, le=5, description="Expansion hop depth"),
    max_nodes: int = Query(150, ge=10, le=500),
    current_user: User = Depends(get_current_user)
):
    engine = ForensicGraphEngine.get_instance()
    data = engine.get_neighborhood(entity_id=entity_id, depth=depth, max_nodes=max_nodes)
    return data

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
    # Also sync into in-memory graph engine
    ForensicGraphEngine.get_instance().add_wallet_tag(tag_in.address, tag_in.tag)
    return AttributionTagResponse.model_validate(tag_obj)
