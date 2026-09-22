"""ChainSentry Forensic Reports Router."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from backend.chainsentry_common.db import get_db
from backend.case_svc.reports import generate_case_dossier, generate_markdown_report
from backend.case_svc.audit import log_action
from backend.case_svc.models import User
from backend.api_service.deps import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports & Export"])

@router.get("/{case_id}/dossier")
def get_dossier(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        return generate_case_dossier(db, case_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{case_id}/markdown")
def get_markdown(
    case_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        dossier = generate_case_dossier(db, case_id)
        md_text = generate_markdown_report(dossier)

        log_action(
            db=db,
            action="EXPORT_REPORT",
            actor_id=current_user.id,
            actor_name=current_user.username,
            target_type="case_report",
            target_id=case_id,
            ip_address=request.client.host if request.client else None,
            metadata={"format": "markdown"}
        )

        return Response(content=md_text, media_type="text/markdown")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
