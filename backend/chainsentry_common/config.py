"""ChainSentry Configuration Module.
Loads environment variables and sets sensible defaults for offline, self-contained, or production modes.
"""
import os
from pathlib import Path
from typing import List, Optional, Any, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "ChainSentry"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database: SQLite by default for zero-daemon offline mode; PostgreSQL for production
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'chainsentry.db'}"

    # Neo4j: optional external Bolt connection; in-memory NetworkX engine runs automatically when Neo4j is offline
    NEO4J_URI: Optional[str] = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "chainsentry123"
    ENABLE_NEO4J: bool = False

    # Security & Auth
    SECRET_KEY: str = "chainsentry-dev-super-secret-key-replace-in-production-0987654321"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours in dev
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000"
    ]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Any) -> Any:
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                import json
                try:
                    return json.loads(v_stripped)
                except Exception:
                    pass
            return [origin.strip() for origin in v_stripped.split(",") if origin.strip()]
        return v

    # Task Processing: eager synchronous execution when Redis is not running
    CELERY_ALWAYS_EAGER: bool = True
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"

    # Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = DATA_DIR
    SAMPLE_DATA_DIR: Path = DATA_DIR / "sample"
    REFERENCE_DATA_DIR: Path = DATA_DIR / "reference"
    GEOIP_DATA_DIR: Path = DATA_DIR / "geoip"
    TAGPACKS_DATA_DIR: Path = DATA_DIR / "tagpacks"

    # AI & Heuristics
    ANOMALY_PERCENTILE_THRESHOLD: float = 0.85
    MAX_HOPS_PEELING_CHAIN: int = 15
    MIN_HOPS_PEELING_CHAIN: int = 3
    COINJOIN_MIN_EQUAL_OUTPUTS: int = 3

    # LLM Narrative (Optional offline toggle)
    ENABLE_LLM_NARRATIVE: bool = False
    ANTHROPIC_API_KEY: Optional[str] = None

settings = Settings()
