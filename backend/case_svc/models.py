"""SQLAlchemy Models for ChainSentry.
Defines relational schemas for users, cases, alerts, evidence, attribution tags, sanctioned wallets, audit logs, and raw transactions.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, Numeric, Integer, BigInteger, JSON, ForeignKey
)
from sqlalchemy.orm import relationship

from backend.chainsentry_common.db import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="investigator")
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    cases_created = relationship("Case", foreign_keys="Case.created_by", back_populates="creator")
    cases_assigned = relationship("Case", foreign_keys="Case.assigned_to", back_populates="assignee")

class Case(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="open", index=True)  # open, in_review, escalated, closed
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    assigned_to = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    creator = relationship("User", foreign_keys=[created_by], back_populates="cases_created")
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="cases_assigned")
    alerts = relationship("Alert", back_populates="case", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=True, index=True)
    entity_type = Column(String(50), nullable=False)  # wallet, transaction, cluster
    entity_ref = Column(String(255), nullable=False, index=True)
    anomaly_score = Column(Numeric(5, 4), default=0.0)
    risk_score = Column(Numeric(5, 4), default=0.0)
    combined_confidence = Column(Numeric(5, 4), default=0.0, index=True)
    fired_patterns = Column(JSON, default=list)
    shap_explanation = Column(JSON, nullable=True)
    narrative = Column(Text, nullable=True)
    status = Column(String(50), default="new", index=True)  # new, reviewing, confirmed, dismissed
    created_at = Column(DateTime(timezone=True), default=utc_now)

    case = relationship("Case", back_populates="alerts")
    evidence = relationship("Evidence", back_populates="alert")

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    alert_id = Column(String(36), ForeignKey("alerts.id"), nullable=True, index=True)
    file_key = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=True)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), default=utc_now)
    notes = Column(Text, nullable=True)

    case = relationship("Case", back_populates="evidence")
    alert = relationship("Alert", back_populates="evidence")

class AttributionTag(Base):
    __tablename__ = "attribution_tags"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    address = Column(String(120), nullable=False, index=True)
    tag = Column(String(255), nullable=False)
    category = Column(String(100), default="other")  # exchange, mixer, darknet_market, ransomware, sanctioned, other
    source = Column(String(100), default="manual")
    confidence = Column(Numeric(3, 2), default=1.0)
    created_at = Column(DateTime(timezone=True), default=utc_now)

class SanctionedWallet(Base):
    __tablename__ = "sanctioned_wallets"

    address = Column(String(120), primary_key=True)
    program = Column(String(100), nullable=False)  # OFAC SDN, UK OFSI, etc.
    entity_name = Column(String(255), nullable=True)
    listed_on = Column(String(50), nullable=True)
    source_url = Column(String(500), nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_id = Column(String(36), nullable=True)
    actor_name = Column(String(100), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    target_type = Column(String(50), nullable=True)
    target_id = Column(String(255), nullable=True)
    ip_address = Column(String(50), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)

class RawTransaction(Base):
    __tablename__ = "raw_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    txid = Column(String(64), nullable=False, index=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    src_ip = Column(String(50), nullable=True, index=True)
    dst_ip = Column(String(50), nullable=True)
    src_port = Column(Integer, nullable=True)
    dst_port = Column(Integer, nullable=True)
    input_addresses = Column(JSON, default=list)
    output_addresses = Column(JSON, default=list)
    input_amounts = Column(JSON, default=list)
    output_amounts = Column(JSON, default=list)
    fee = Column(Numeric(16, 8), nullable=True)
    script_type = Column(String(50), default="UNKNOWN")
    geo_country = Column(String(10), nullable=True)
    asn = Column(String(50), nullable=True)
    source = Column(String(50), default="synthetic")
    provenance = Column(String(100), nullable=True)
    dataset_id = Column(String(100), nullable=True)
    ingest_batch_id = Column(String(36), nullable=False, default=generate_uuid)

class RawNetworkObservation(Base):
    __tablename__ = "raw_network_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    observation_id = Column(String(64), nullable=False, index=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    src_ip = Column(String(50), nullable=False, index=True)
    dst_ip = Column(String(50), nullable=True)
    src_port = Column(Integer, nullable=True)
    dst_port = Column(Integer, nullable=True)
    txid = Column(String(64), nullable=False, index=True)
    provenance = Column(String(100), nullable=True)
    dataset_id = Column(String(100), nullable=True)
    geo_country = Column(String(10), nullable=True)
    asn = Column(String(50), nullable=True)
