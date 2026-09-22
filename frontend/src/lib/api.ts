import {
  User, Case, Alert, GraphData, IngestStats, SearchResult, AttributionTag
} from '../types';

const API_BASE = '/api';

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('chainsentry_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
    ...(options.headers as Record<string, string> || {}),
  };

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem('chainsentry_token');
      localStorage.removeItem('chainsentry_user');
    }
    const errData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errData.detail || `Request failed with status ${res.status}`);
  }

  return res.json();
}

// Auth
export async function login(username: string, password: string):Promise<{ access_token: string; user: User }> {
  const data = await request<{ access_token: string; user: User }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  localStorage.setItem('chainsentry_token', data.access_token);
  localStorage.setItem('chainsentry_user', JSON.stringify(data.user));
  return data;
}

export function logout(): void {
  localStorage.removeItem('chainsentry_token');
  localStorage.removeItem('chainsentry_user');
}

export function getCurrentUser(): User | null {
  const userStr = localStorage.getItem('chainsentry_user');
  return userStr ? JSON.parse(userStr) : null;
}

// Cases
export async function fetchCases(status?: string): Promise<Case[]> {
  const q = status ? `?status=${status}` : '';
  return request<Case[]>(`/cases${q}`);
}

export async function fetchCaseById(caseId: string): Promise<Case> {
  return request<Case>(`/cases/${caseId}`);
}

export async function createCase(data: { title: string; description?: string; status?: string; assigned_to?: string }): Promise<Case> {
  return request<Case>('/cases', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateCase(caseId: string, data: Partial<Case>): Promise<Case> {
  return request<Case>(`/cases/${caseId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// Alerts
export async function fetchAlerts(params?: { case_id?: string; status?: string; min_confidence?: number; limit?: number }): Promise<Alert[]> {
  const sp = new URLSearchParams();
  if (params?.case_id) sp.set('case_id', params.case_id);
  if (params?.status) sp.set('status', params.status);
  if (params?.min_confidence) sp.set('min_confidence', String(params.min_confidence));
  if (params?.limit) sp.set('limit', String(params.limit));
  const query = sp.toString() ? `?${sp.toString()}` : '';
  return request<Alert[]>(`/alerts${query}`);
}

export async function fetchAlertById(alertId: string): Promise<Alert> {
  return request<Alert>(`/alerts/${alertId}`);
}

export async function updateAlertStatus(alertId: string, status: string, caseId?: string): Promise<Alert> {
  const sp = new URLSearchParams({ new_status: status });
  if (caseId) sp.set('case_id', caseId);
  return request<Alert>(`/alerts/${alertId}/status?${sp.toString()}`, {
    method: 'PUT',
  });
}

// Graph
export async function fetchGraphNeighborhood(entityId: string, depth = 2, maxNodes = 150): Promise<GraphData> {
  return request<GraphData>(`/graph/neighborhood?entity_id=${encodeURIComponent(entityId)}&depth=${depth}&max_nodes=${maxNodes}`);
}

export async function fetchGraphStats(): Promise<Record<string, any>> {
  return request<Record<string, any>>('/graph/stats');
}

export async function fetchAddressTags(address: string): Promise<AttributionTag[]> {
  return request<AttributionTag[]>(`/graph/tags/${encodeURIComponent(address)}`);
}

export async function addAddressTag(data: { address: string; tag: string; category?: string }): Promise<AttributionTag> {
  return request<AttributionTag>('/graph/tags', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// Ingestion & Pipeline
export async function runSamplePipeline(): Promise<IngestStats> {
  return request<IngestStats>('/ingestion/run-sample', {
    method: 'POST',
  });
}

export async function uploadDataset(txFile: File, obsFile?: File): Promise<IngestStats> {
  const formData = new FormData();
  formData.append('tx_file', txFile);
  if (obsFile) {
    formData.append('obs_file', obsFile);
  }

  const token = localStorage.getItem('chainsentry_token');
  const res = await fetch(`${API_BASE}/ingestion/upload`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Upload failed');
  }

  return res.json();
}

// Search
export async function searchOmnibox(q: string): Promise<SearchResult> {
  return request<SearchResult>(`/search?q=${encodeURIComponent(q)}`);
}

// Reports
export async function fetchCaseDossier(caseId: string): Promise<any> {
  return request<any>(`/reports/${caseId}/dossier`);
}

export async function fetchCaseMarkdownReport(caseId: string): Promise<string> {
  const headers = getAuthHeader();
  const res = await fetch(`${API_BASE}/reports/${caseId}/markdown`, { headers });
  if (!res.ok) throw new Error('Failed to generate report');
  return res.text();
}
