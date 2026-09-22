"""ChainSentry Case Management Router."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.chainsentry_common.db import get_db
from backend.chainsentry_common.schemas import CaseCreate, CaseUpdate, CaseResponse, EvidenceResponse
from backend.case_svc import crud
from backend.case_svc.audit import log_action
from backend.case_svc.models import User
from backend.api_service.deps import get_current_user, require_role

router = APIRouter(prefix="/cases", tags=["Case Management"])

@router.get("", response_model=List[CaseResponse])
def list_cases(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cases = crud.get_cases(db, status=status, skip=skip, limit=limit)
    res = []
    for c in cases:
        c_dict = CaseResponse.model_validate(c)
        c_dict.alert_count = len(c.alerts)
        res.append(c_dict)
    return res

@router.post("", response_model=CaseResponse)
def create_case(
    case_in: CaseCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = crud.create_case(db, case_in, user_id=current_user.id)
    log_action(
        db=db,
        action="CREATE_CASE",
        actor_id=current_user.id,
        actor_name=current_user.username,
        target_type="case",
        target_id=case.id,
        ip_address=request.client.host if request.client else None,
        metadata={"title": case.title}
    )
    return CaseResponse.model_validate(case)

@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = crud.get_case_by_id(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    c_dict = CaseResponse.model_validate(case)
    c_dict.alert_count = len(case.alerts)
    return c_dict

@router.put("/{case_id}", response_model=CaseResponse)
def update_case(
    case_id: str,
    case_in: CaseUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "lead_investigator", "investigator"))
):
    case = crud.update_case(db, case_id, case_in)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    log_action(
        db=db,
        action="UPDATE_CASE",
        actor_id=current_user.id,
        actor_name=current_user.username,
        target_type="case",
        target_id=case.id,
        ip_address=request.client.host if request.client else None,
        metadata=case_in.model_dump(exclude_unset=True)
    )
    return CaseResponse.model_validate(case)

@router.delete("/{case_id}")
def delete_case(
    case_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "lead_investigator"))
):
    success = crud.delete_case(db, case_id)
    if not success:
        raise HTTPException(status_code=404, detail="Case not found")
    log_action(
        db=db,
        action="DELETE_CASE",
        actor_id=current_user.id,
        actor_name=current_user.username,
        target_type="case",
        target_id=case_id,
        ip_address=request.client.host if request.client else None
    )
    return {"message": "Case deleted successfully"}

@router.post("/{case_id}/evidence", response_model=EvidenceResponse)
def attach_evidence(
    case_id: str,
    file_key: str,
    file_type: Optional[str] = None,
    notes: Optional[str] = None,
    alert_id: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = crud.get_case_by_id(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    ev = crud.add_evidence(
        db=db,
        case_id=case_id,
        file_key=file_key,
        file_type=file_type,
        notes=notes,
        uploaded_by=current_user.id,
        alert_id=alert_id
    )
    log_action(
        db=db,
        action="ATTACH_EVIDENCE",
        actor_id=current_user.id,
        actor_name=current_user.username,
        target_type="evidence",
        target_id=ev.id,
        ip_address=request.client.host if request and request.client else None,
        metadata={"case_id": case_id, "file_key": file_key}
    )
    return EvidenceResponse.model_validate(ev)
