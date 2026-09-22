---
name: chainsentry-backend
description: Use whenever writing or modifying backend code for ChainSentry (FastAPI + Neo4j + PostgreSQL Bitcoin forensics system). Enforces the project's service structure and conventions.
---

# ChainSentry Backend Standards

Follow the architecture in /docs/bitcoin-forensics-blueprint.md exactly. Key rules:

- Services live under backend/{api_service,ingestion_svc,graph_svc,ai_service,case_svc}/
  — never put business logic directly in a FastAPI router; routers call into service
  modules only.
- Every request/response is a typed Pydantic model. No raw dict payloads.
- All DB writes go through chainsentry_common/db.py session factories — no ad hoc
  connections per file.
- Cypher queries live only in graph_svc/ — never string-built, always parameterized.
- SQL goes through SQLAlchemy ORM or parameterized text() — never string-concatenated.
- Long-running work (ingestion, GDS algorithm runs, ML scoring) is a Celery task,
  never inline in a request handler.
- Every new endpoint needs: a Pydantic schema, a service-layer function, a unit test,
  and an RBAC role check via require_role(...).
- Reference the canonical schema in shared/schemas/tx_record.schema.json before adding
  any new ingest field — keep frontend TS types and backend Pydantic types generated
  from the same source.
