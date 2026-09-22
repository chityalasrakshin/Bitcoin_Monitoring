"""ChainSentry Audit Service.
Append-only forensic event logging for compliance, chain-of-custody, and investigator accountability.
"""
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from backend.case_svc.models import AuditLog
from backend.chainsentry_common.logging import logger

def log_action(
    db: Session,
    action: str,
    actor_id: Optional[str] = None,
    actor_name: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """Record an immutable audit event."""
    try:
        entry = AuditLog(
            actor_id=actor_id,
            actor_name=actor_name,
            action=action,
            target_type=target_type,
            target_id=target_id,
            ip_address=ip_address,
            metadata_json=metadata or {}
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        logger.info(f"AUDIT: [{action}] by={actor_name or actor_id or 'SYSTEM'} target={target_type}:{target_id}")
        return entry
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to write audit log: {e}")
        raise
