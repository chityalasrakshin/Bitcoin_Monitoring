"""ChainSentry Canonical Pydantic Schemas.
Shared across API, ingestion, graph, AI, and case services.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict

# --- Enums ---

class ScriptType(str, Enum):
    P2PKH = "P2PKH"
    P2SH = "P2SH"
    P2WPKH = "P2WPKH"
    P2WSH = "P2WSH"
    P2TR = "P2TR"
    MULTISIG = "MULTISIG"
    UNKNOWN = "UNKNOWN"

class SourceEnum(str, Enum):
    ELLIPTIC = "elliptic"
    ESPLORA = "esplora"
    BITNODES = "bitnodes"
    MANUAL_UPLOAD = "manual_upload"
    P2P_CAPTURE = "p2p_capture"
    SYNTHETIC = "synthetic"

class RoleEnum(str, Enum):
    ADMIN = "admin"
    LEAD_INVESTIGATOR = "lead_investigator"
    INVESTIGATOR = "investigator"
    ANALYST = "analyst"
    VIEWER = "viewer"

class CaseStatus(str, Enum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    ESCALATED = "escalated"
    CLOSED = "closed"

class AlertStatus(str, Enum):
    NEW = "new"
    REVIEWING = "reviewing"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"

class EntityType(str, Enum):
    WALLET = "wallet"
    TRANSACTION = "transaction"
    CLUSTER = "cluster"
    IP = "ip"

# --- Authentication & User Schemas ---

class UserBase(BaseModel):
    username: str
    full_name: Optional[str] = None
    role: RoleEnum = RoleEnum.INVESTIGATOR
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    user: UserResponse

# --- Transaction & Network Ingest Schemas ---

class NormalizedTxRecord(BaseModel):
    txid: str = Field(..., description="64-character hex transaction ID")
    timestamp: datetime
    input_addresses: List[str] = Field(default_factory=list)
    output_addresses: List[str] = Field(default_factory=list)
    input_amounts: List[float] = Field(default_factory=list)
    output_amounts: List[float] = Field(default_factory=list)
    fee: Optional[float] = None
    script_type: str = "UNKNOWN"
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    geo_country: Optional[str] = None
    asn: Optional[Union[str, int]] = None
    source: str = "synthetic"
    provenance: Optional[str] = None
    dataset_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class NetworkObservationRecord(BaseModel):
    observation_id: str
    timestamp: datetime
    src_ip: str
    dst_ip: Optional[str] = None
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    txid: str
    provenance: Optional[str] = None
    dataset_id: Optional[str] = None
    geo_country: Optional[str] = None
    asn: Optional[Union[str, int]] = None

    model_config = ConfigDict(from_attributes=True)

class CorrelationResult(BaseModel):
    txid: str
    relay_ip: str
    dst_ip: Optional[str] = None
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    geo_country: Optional[str] = None
    asn: Optional[Union[str, int]] = None
    first_seen_timestamp: datetime
    blockchain_timestamp: datetime
    latency_ms: float
    confidence: float
    observation_count: int = 1

# --- Graph Models (Cytoscape.js compatible) ---

class CytoscapeNodeData(BaseModel):
    id: str
    label: str
    type: str  # wallet, transaction, ip, cluster, tag
    risk_score: float = 0.0
    cluster_id: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)

class CytoscapeNode(BaseModel):
    data: CytoscapeNodeData

class CytoscapeEdgeData(BaseModel):
    id: str
    source: str
    target: str
    label: str  # INPUT_TO, OUTPUT_TO, FIRST_RELAYED_BY, SAME_ENTITY_AS
    amount: Optional[float] = None
    latency_ms: Optional[float] = None
    confidence: Optional[float] = None

class CytoscapeEdge(BaseModel):
    data: CytoscapeEdgeData

class GraphData(BaseModel):
    nodes: List[CytoscapeNode] = Field(default_factory=list)
    edges: List[CytoscapeEdge] = Field(default_factory=list)

# --- AI & Detection Schemas ---

class FiredPattern(BaseModel):
    pattern: str  # peeling_chain, coinjoin_mixing, rapid_hops, etc.
    confidence: float
    description: str
    tx_chain: List[str] = Field(default_factory=list)
    involved_addresses: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)

class SHAPFeatureContribution(BaseModel):
    feature_name: str
    value: float
    contribution: float  # impact on anomaly score
    description: str

class SHAPExplanation(BaseModel):
    base_value: float = 0.0
    anomaly_score: float = 0.0
    top_features: List[SHAPFeatureContribution] = Field(default_factory=list)
    summary: str = ""

# --- Alerts & Cases ---

class AlertBase(BaseModel):
    entity_type: EntityType
    entity_ref: str
    anomaly_score: float = 0.0
    risk_score: float = 0.0
    combined_confidence: float = 0.0
    fired_patterns: List[FiredPattern] = Field(default_factory=list)
    shap_explanation: Optional[SHAPExplanation] = None
    status: AlertStatus = AlertStatus.NEW
    narrative: Optional[str] = None

class AlertCreate(AlertBase):
    case_id: Optional[str] = None

class AlertResponse(AlertBase):
    id: str
    case_id: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CaseBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: CaseStatus = CaseStatus.OPEN
    assigned_to: Optional[str] = None

class CaseCreate(CaseBase):
    pass

class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CaseStatus] = None
    assigned_to: Optional[str] = None

class CaseResponse(CaseBase):
    id: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    alert_count: int = 0
    alerts: List[AlertResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)

class EvidenceResponse(BaseModel):
    id: str
    case_id: str
    alert_id: Optional[str] = None
    file_key: str
    file_type: Optional[str] = None
    uploaded_by: Optional[str] = None
    uploaded_at: datetime
    notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class AttributionTagCreate(BaseModel):
    address: str
    tag: str
    category: str = "other"  # exchange, mixer, darknet_market, ransomware, sanctioned, other
    source: str = "manual"
    confidence: float = 1.0

class AttributionTagResponse(AttributionTagCreate):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SanctionedWalletResponse(BaseModel):
    address: str
    program: str
    entity_name: Optional[str] = None
    listed_on: Optional[str] = None
    source_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class AuditLogResponse(BaseModel):
    id: int
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    ip_address: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class IngestStats(BaseModel):
    total_transactions_ingested: int
    total_observations_ingested: int
    total_correlations_found: int
    total_entities_clustered: int
    total_alerts_generated: int
    duration_seconds: float
