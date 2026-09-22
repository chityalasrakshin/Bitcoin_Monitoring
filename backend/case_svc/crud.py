"""CRUD operations for Cases, Alerts, Evidence, and Tags."""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.case_svc.models import Case, Alert, Evidence, AttributionTag, SanctionedWallet, User
from backend.chainsentry_common.schemas import CaseCreate, CaseUpdate, AlertCreate, AttributionTagCreate
from backend.chainsentry_common.logging import logger

def create_case(db: Session, case_in: CaseCreate, user_id: Optional[str] = None) -> Case:
    case = Case(
        title=case_in.title,
        description=case_in.description,
        status=case_in.status.value if hasattr(case_in.status, "value") else str(case_in.status),
        created_by=user_id,
        assigned_to=case_in.assigned_to
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case

def get_cases(db: Session, status: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[Case]:
    query = db.query(Case)
    if status:
        query = query.filter(Case.status == status)
    return query.order_by(desc(Case.updated_at)).offset(skip).limit(limit).all()

def get_case_by_id(db: Session, case_id: str) -> Optional[Case]:
    return db.query(Case).filter(Case.id == case_id).first()

def update_case(db: Session, case_id: str, case_in: CaseUpdate) -> Optional[Case]:
    case = get_case_by_id(db, case_id)
    if not case:
        return None
    if case_in.title is not None:
        case.title = case_in.title
    if case_in.description is not None:
        case.description = case_in.description
    if case_in.status is not None:
        case.status = case_in.status.value if hasattr(case_in.status, "value") else str(case_in.status)
    if case_in.assigned_to is not None:
        case.assigned_to = case_in.assigned_to
    db.commit()
    db.refresh(case)
    return case

def delete_case(db: Session, case_id: str) -> bool:
    case = get_case_by_id(db, case_id)
    if not case:
        return False
    db.delete(case)
    db.commit()
    return True

# --- Alerts CRUD ---

def create_alert(db: Session, alert_in: AlertCreate) -> Alert:
    fired_patterns_dicts = [
        p.model_dump() if hasattr(p, "model_dump") else p
        for p in alert_in.fired_patterns
    ]
    shap_dict = alert_in.shap_explanation.model_dump() if alert_in.shap_explanation and hasattr(alert_in.shap_explanation, "model_dump") else alert_in.shap_explanation

    alert = Alert(
        case_id=alert_in.case_id,
        entity_type=alert_in.entity_type.value if hasattr(alert_in.entity_type, "value") else str(alert_in.entity_type),
        entity_ref=alert_in.entity_ref,
        anomaly_score=alert_in.anomaly_score,
        risk_score=alert_in.risk_score,
        combined_confidence=alert_in.combined_confidence,
        fired_patterns=fired_patterns_dicts,
        shap_explanation=shap_dict,
        narrative=alert_in.narrative,
        status=alert_in.status.value if hasattr(alert_in.status, "value") else str(alert_in.status)
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert

def get_alerts(
    db: Session,
    case_id: Optional[str] = None,
    status: Optional[str] = None,
    entity_type: Optional[str] = None,
    min_confidence: Optional[float] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Alert]:
    query = db.query(Alert)
    if case_id:
        query = query.filter(Alert.case_id == case_id)
    if status:
        query = query.filter(Alert.status == status)
    if entity_type:
        query = query.filter(Alert.entity_type == entity_type)
    if min_confidence is not None:
        query = query.filter(Alert.combined_confidence >= min_confidence)
    return query.order_by(desc(Alert.combined_confidence)).offset(skip).limit(limit).all()

def get_alert_by_id(db: Session, alert_id: str) -> Optional[Alert]:
    return db.query(Alert).filter(Alert.id == alert_id).first()

def update_alert_status(db: Session, alert_id: str, new_status: str, case_id: Optional[str] = None) -> Optional[Alert]:
    alert = get_alert_by_id(db, alert_id)
    if not alert:
        return None
    alert.status = new_status
    if case_id:
        alert.case_id = case_id
    db.commit()
    db.refresh(alert)
    return alert

# --- Evidence & Tags ---

def add_evidence(
    db: Session,
    case_id: str,
    file_key: str,
    file_type: Optional[str] = None,
    notes: Optional[str] = None,
    uploaded_by: Optional[str] = None,
    alert_id: Optional[str] = None
) -> Evidence:
    evidence = Evidence(
        case_id=case_id,
        alert_id=alert_id,
        file_key=file_key,
        file_type=file_type,
        notes=notes,
        uploaded_by=uploaded_by
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence

def add_attribution_tag(db: Session, tag_in: AttributionTagCreate) -> AttributionTag:
    existing = db.query(AttributionTag).filter(
        AttributionTag.address == tag_in.address,
        AttributionTag.tag == tag_in.tag,
        AttributionTag.source == tag_in.source
    ).first()
    if existing:
        existing.category = tag_in.category
        existing.confidence = tag_in.confidence
        db.commit()
        db.refresh(existing)
        return existing

    tag_obj = AttributionTag(
        address=tag_in.address,
        tag=tag_in.tag,
        category=tag_in.category,
        source=tag_in.source,
        confidence=tag_in.confidence
    )
    db.add(tag_obj)
    db.commit()
    db.refresh(tag_obj)
    return tag_obj

def get_tags_for_address(db: Session, address: str) -> List[AttributionTag]:
    return db.query(AttributionTag).filter(AttributionTag.address == address).all()

def get_all_tags(db: Session, skip: int = 0, limit: int = 500) -> List[AttributionTag]:
    return db.query(AttributionTag).offset(skip).limit(limit).all()
