"""ChainSentry Forensic Case Report Generator.
Assembles structured case dossiers, risk summaries, typologies, and chain-of-custody audit logs
into exportable forensic report documents (Markdown and JSON).
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.case_svc.models import Case, Alert, Evidence, AuditLog
from backend.chainsentry_common.logging import logger

def generate_case_dossier(db: Session, case_id: str) -> Dict[str, Any]:
    """Compile full forensic evidence bundle and dossier for a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise ValueError(f"Case {case_id} not found")

    alerts = db.query(Alert).filter(Alert.case_id == case_id).order_by(Alert.combined_confidence.desc()).all()
    evidence_items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
    audit_events = db.query(AuditLog).filter(
        AuditLog.target_type == "case",
        AuditLog.target_id == case_id
    ).order_by(AuditLog.created_at.asc()).all()

    alert_dicts = []
    for a in alerts:
        alert_dicts.append({
            "id": a.id,
            "entity_type": a.entity_type,
            "entity_ref": a.entity_ref,
            "combined_confidence": float(a.combined_confidence or 0.0),
            "anomaly_score": float(a.anomaly_score or 0.0),
            "risk_score": float(a.risk_score or 0.0),
            "status": a.status,
            "fired_patterns": a.fired_patterns or [],
            "shap_explanation": a.shap_explanation or {},
            "narrative": a.narrative or "",
            "created_at": a.created_at.isoformat() if a.created_at else None
        })

    evidence_dicts = []
    for e in evidence_items:
        evidence_dicts.append({
            "id": e.id,
            "file_key": e.file_key,
            "file_type": e.file_type,
            "notes": e.notes,
            "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else None
        })

    audit_dicts = []
    for aud in audit_events:
        audit_dicts.append({
            "action": aud.action,
            "actor": aud.actor_name or aud.actor_id or "SYSTEM",
            "timestamp": aud.created_at.isoformat() if aud.created_at else None,
            "ip_address": aud.ip_address,
            "metadata": aud.metadata_json
        })

    dossier = {
        "case_id": case.id,
        "title": case.title,
        "description": case.description,
        "status": case.status,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "updated_at": case.updated_at.isoformat() if case.updated_at else None,
        "assigned_to": case.assigned_to,
        "summary": {
            "total_alerts": len(alerts),
            "high_confidence_alerts": sum(1 for a in alerts if (a.combined_confidence or 0) >= 0.8),
            "total_evidence_files": len(evidence_items),
        },
        "alerts": alert_dicts,
        "evidence": evidence_dicts,
        "audit_trail": audit_dicts
    }
    return dossier

def generate_markdown_report(dossier: Dict[str, Any]) -> str:
    """Render dossier into professional Markdown report."""
    md = []
    md.append(f"# FORENSIC INVESTIGATION REPORT — CASE {dossier['case_id'][:8]}")
    md.append(f"**Classification:** LAW ENFORCEMENT & INVESTIGATIVE SENSITIVE  ")
    md.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ")
    md.append(f"**System:** ChainSentry AI Forensics Platform (SIH26146)\n")
    md.append("---")
    md.append("## 1. Executive Summary")
    md.append(f"- **Case Title:** {dossier['title']}")
    md.append(f"- **Status:** {dossier['status'].upper()}")
    md.append(f"- **Description:** {dossier.get('description', 'N/A')}")
    md.append(f"- **Total Flagged Leads:** {dossier['summary']['total_alerts']}")
    md.append(r"- **High-Confidence Leads ($\ge 0.80$):** " + str(dossier['summary']['high_confidence_alerts']))
    md.append(f"- **Evidence Attachments:** {dossier['summary']['total_evidence_files']}\n")

    md.append("## 2. Priority Forensic Leads & Typologies")
    if not dossier["alerts"]:
        md.append("_No alerts registered to this case._\n")
    else:
        for idx, alert in enumerate(dossier["alerts"]):
            md.append(f"### Lead #{idx+1} — {alert['entity_type'].upper()}: `{alert['entity_ref']}`")
            md.append(f"- **Combined Confidence:** {alert['combined_confidence']:.2%}")
            md.append(f"- **Anomaly Score:** {alert['anomaly_score']:.2f} | **Propagated Risk:** {alert['risk_score']:.2f}")
            md.append(f"- **Status:** {alert['status'].upper()}")
            if alert.get("narrative"):
                md.append(f"- **Investigative Finding:** {alert['narrative']}")

            patterns = alert.get("fired_patterns", [])
            if patterns:
                md.append("\n**Identified Graph Patterns:**")
                for p in patterns:
                    md.append(f"  - **{p.get('pattern')}:** {p.get('description')} (Confidence: {p.get('confidence', 0):.2%})")

            shap = alert.get("shap_explanation", {})
            top_feats = shap.get("top_features", [])
            if top_feats:
                md.append("\n**Key Contributing Indicators (SHAP):**")
                for tf in top_feats:
                    md.append(f"  - `{tf.get('feature_name')}`: value = {tf.get('value')}, impact = {tf.get('contribution')}")
            md.append("\n---")

    md.append("## 3. Chain of Custody & Audit Trail")
    if not dossier["audit_trail"]:
        md.append("_No audit trail entries recorded._\n")
    else:
        md.append("| Timestamp (UTC) | Action | Investigator / Actor | IP Address |")
        md.append("|---|---|---|---|")
        for aud in dossier["audit_trail"]:
            md.append(f"| {aud['timestamp']} | {aud['action']} | {aud['actor']} | {aud.get('ip_address') or 'LOCAL'} |")

    return "\n".join(md)
