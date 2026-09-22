"""ChainSentry Alerts & Forensic Leads Router."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.chainsentry_common.db import get_db
from backend.chainsentry_common.schemas import AlertResponse, AlertStatus
from backend.case_svc import crud
from backend.case_svc.audit import log_action
from backend.case_svc.models import User
from backend.api_service.deps import get_current_user, require_role

router = APIRouter(prefix="/alerts", tags=["Alerts & Leads"])

@router.get("", response_model=List[AlertResponse])
def list_alerts(
    case_id: Optional[str] = None,
    status: Optional[str] = None,
    entity_type: Optional[str] = None,
    min_confidence: Optional[float] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    alerts = crud.get_alerts(
        db,
        case_id=case_id,
        status=status,
        entity_type=entity_type,
        min_confidence=min_confidence,
        skip=skip,
        limit=limit
    )
    return [AlertResponse.model_validate(a) for a in alerts]

@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    alert = crud.get_alert_by_id(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse.model_validate(alert)

@router.put("/{alert_id}/status", response_model=AlertResponse)
def update_status(
    alert_id: str,
    new_status: str,
    case_id: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "lead_investigator", "investigator"))
):
    alert = crud.update_alert_status(db, alert_id, new_status, case_id=case_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    log_action(
        db=db,
        action="UPDATE_ALERT_STATUS",
        actor_id=current_user.id,
        actor_name=current_user.username,
        target_type="alert",
        target_id=alert_id,
        ip_address=request.client.host if request and request.client else None,
        metadata={"new_status": new_status, "case_id": case_id}
    )
    return AlertResponse.model_validate(alert)
