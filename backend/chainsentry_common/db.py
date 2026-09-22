"""ChainSentry Database Session Management.
Supports both SQLite (for zero-daemon standalone offline execution) and PostgreSQL.
Provides session dependencies and database initialization routines.
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from .config import settings
from .logging import logger

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables and seed default users if needed."""
    from backend.case_svc.models import User, AttributionTag, SanctionedWallet
    from backend.chainsentry_common.security import hash_password
    from backend.chainsentry_common.schemas import RoleEnum

    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    # Seed default admin and investigator if users table is empty
    with SessionLocal() as session:
        existing = session.query(User).first()
        if not existing:
            logger.info("Seeding default administrative and investigator accounts...")
            admin_user = User(
                username="admin",
                password_hash=hash_password("chainsentry2026!"),
                role=RoleEnum.ADMIN.value,
                full_name="Lead System Administrator",
                is_active=True
            )
            investigator_user = User(
                username="investigator",
                password_hash=hash_password("forensics2026!"),
                role=RoleEnum.INVESTIGATOR.value,
                full_name="Forensics Investigator",
                is_active=True
            )
            session.add_all([admin_user, investigator_user])
            session.commit()
            logger.info("Default users created: admin, investigator")
