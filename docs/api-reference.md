# ChainSentry REST API Reference

Base URL: `http://localhost:8000/api`  
Interactive OpenAPI Documentation: `http://localhost:8000/docs`  
Authentication: HTTP Bearer JWT Token (`Authorization: Bearer <token>`)

---

## 1. Authentication Endpoints

### `POST /auth/login`
Authenticate investigator credentials and obtain session tokens.
- **Request Body:**
  ```json
  {
    "username": "admin",
    "password": "chainsentry2026!"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "refresh_token": "eyJhbGciOi...",
    "user": {
      "id": "21ba07a3-...",
      "username": "admin",
      "role": "admin",
      "full_name": "Lead System Administrator"
    }
  }
  ```

### `GET /auth/me`
Retrieve profile of currently authenticated user.
- **Headers:** `Authorization: Bearer <access_token>`
- **Response (200 OK):** `UserResponse`

---

## 2. Ingestion & Pipeline Endpoints

### `POST /ingestion/run-sample`
Executes the full forensic pipeline on the built-in reference dataset (Seed-42).
- **Permissions:** `admin`, `lead_investigator`, `investigator`
- **Response (200 OK):**
  ```json
  {
    "total_transactions_ingested": 109,
    "total_observations_ingested": 368,
    "total_correlations_found": 95,
    "total_entities_clustered": 179,
    "total_alerts_generated": 47,
    "duration_seconds": 2.03
  }
  ```

### `POST /ingestion/upload`
Upload and correlate custom datasets.
- **Form Data:**
  - `tx_file`: Blockchain transaction metadata file (`.csv`, `.json`, `.xml`)
  - `obs_file`: (Optional) Network observation file (`.csv`, `.json`)
- **Response (200 OK):** `IngestStats`

---

## 3. Forensic Graph & Link Analysis

### `GET /graph/neighborhood`
Extract k-hop ego subgraph formatted for Cytoscape.js visualization.
- **Query Parameters:**
  - `entity_id` (string, required): Wallet address or transaction ID
  - `depth` (integer, default: 2): Hop expansion depth (1 to 5)
  - `max_nodes` (integer, default: 150): Node cap for visual performance
- **Response (200 OK):**
  ```json
  {
    "nodes": [
      {
        "data": {
          "id": "sbc18d20c1d613b34c0e6946f41fc34692fc9daf10",
          "label": "sbc18d...af10",
          "type": "wallet",
          "risk_score": 1.0,
          "cluster_id": "entity-sbc18d20",
          "tags": ["Seed Target"]
        }
      }
    ],
    "edges": [
      {
        "data": {
          "id": "sbc18d..._b85038..._in_0",
          "source": "sbc18d...",
          "target": "b85038...",
          "label": "INPUT_TO",
          "amount": 0.740384
        }
      }
    ]
  }
  ```

### `GET /graph/stats`
Returns total node counts, edge counts, clustered entities, and P2P IPs.

---

## 4. Alerts & Investigative Leads

### `GET /alerts`
List ranked leads sorted descending by multi-signal combined confidence.
- **Query Parameters:**
  - `status` (string, optional): `new`, `reviewing`, `confirmed`, `dismissed`
  - `min_confidence` (float, optional): e.g. `0.75`
  - `limit` (integer, default: 100)
- **Response (200 OK):** Array of `AlertResponse` objects containing SHAP explanations and fired typologies.

### `PUT /alerts/{alert_id}/status`
Update triage status of an alert and/or link to a case.

---

## 5. Cases & Evidence

### `GET /cases`
List active forensic cases.

### `POST /cases`
Open a new forensic case.
- **Request Body:**
  ```json
  {
    "title": "OPERATION DARK-TRAIL",
    "description": "Tracing peel chain from SamSam ransomware affiliate",
    "status": "open"
  }
  ```

### `GET /reports/{case_id}/markdown`
Generate and download the formatted Markdown forensic case dossier.
