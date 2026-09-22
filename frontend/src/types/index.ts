export type Role = 'admin' | 'lead_investigator' | 'investigator' | 'analyst' | 'viewer';
export type CaseStatus = 'open' | 'in_review' | 'escalated' | 'closed';
export type AlertStatus = 'new' | 'reviewing' | 'confirmed' | 'dismissed';
export type EntityType = 'wallet' | 'transaction' | 'cluster' | 'ip';

export interface User {
  id: string;
  username: string;
  full_name?: string;
  role: Role;
  is_active: boolean;
}

export interface FiredPattern {
  pattern: string;
  confidence: number;
  description: string;
  tx_chain: string[];
  involved_addresses: string[];
  metrics: Record<string, any>;
}

export interface SHAPFeatureContribution {
  feature_name: string;
  value: number;
  contribution: number;
  description: string;
}

export interface SHAPExplanation {
  base_value: number;
  anomaly_score: number;
  top_features: SHAPFeatureContribution[];
  summary: string;
}

export interface Alert {
  id: string;
  case_id?: string | null;
  entity_type: EntityType;
  entity_ref: string;
  anomaly_score: number;
  risk_score: number;
  combined_confidence: number;
  fired_patterns: FiredPattern[];
  shap_explanation?: SHAPExplanation | null;
  narrative?: string | null;
  status: AlertStatus;
  created_at: string;
}

export interface Case {
  id: string;
  title: string;
  description?: string;
  status: CaseStatus;
  created_by?: string;
  assigned_to?: string;
  created_at: string;
  updated_at: string;
  alert_count?: number;
  alerts?: Alert[];
}

export interface CytoscapeNodeData {
  id: string;
  label: string;
  type: string; // 'wallet' | 'transaction' | 'ip' | 'cluster'
  risk_score: number;
  cluster_id?: string;
  category?: string;
  tags?: string[];
  extra?: Record<string, any>;
}

export interface CytoscapeNode {
  data: CytoscapeNodeData;
}

export interface CytoscapeEdgeData {
  id: string;
  source: string;
  target: string;
  label: string;
  amount?: number;
  latency_ms?: number;
  confidence?: number;
}

export interface CytoscapeEdge {
  data: CytoscapeEdgeData;
}

export interface GraphData {
  nodes: CytoscapeNode[];
  edges: CytoscapeEdge[];
}

export interface IngestStats {
  total_transactions_ingested: number;
  total_observations_ingested: number;
  total_correlations_found: number;
  total_entities_clustered: number;
  total_alerts_generated: number;
  duration_seconds: number;
}

export interface SearchResult {
  wallets: Array<{
    address: string;
    risk_score: number;
    cluster_id?: string;
    tags: string[];
  }>;
  transactions: Array<{
    txid: string;
    total_value: number;
    fee: number;
    timestamp: string;
  }>;
  cases: Array<{
    id: string;
    title: string;
    status: string;
    created_at: string;
  }>;
  alerts: Array<{
    id: string;
    entity_ref: string;
    confidence: number;
    status: string;
  }>;
  tags: Array<{
    address: string;
    tag: string;
    category: string;
  }>;
}

export interface AttributionTag {
  id: string;
  address: string;
  tag: string;
  category: string;
  source: string;
  confidence: number;
  created_at: string;
}
