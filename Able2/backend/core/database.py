"""
Database connection and session management for Able2.
Uses SQLAlchemy with PostgreSQL.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from .config import settings
from .logger import database_logger


# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,  # Verify connections before using
    echo=False,  # Set to True to log SQL queries
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Usage:
        with get_db_context() as db:
            db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        database_logger.error(f"Database error: {str(e)}")
        raise
    finally:
        db.close()


def init_database():
    """
    Initialize database - create all tables.
    Should be called on application startup.
    """
    from backend.models import database_models  # Import after Base is defined

    database_logger.info("Initializing database...")

    try:
        Base.metadata.create_all(bind=engine)
        database_logger.info("Database initialized successfully")
    except Exception as e:
        database_logger.error(f"Failed to initialize database: {str(e)}")
        raise


def drop_database():
    """
    Drop all tables - USE WITH CAUTION!
    Only for development/testing.
    """
    database_logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    database_logger.warning("All tables dropped")


def check_database_connection() -> bool:
    """
    Check if database connection is working.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        database_logger.info("Database connection OK")
        return True
    except Exception as e:
        database_logger.error(f"Database connection failed: {str(e)}")
        return False


__all__ = [
    "engine",
    "SessionLocal",
    "Base",
    "get_db",
    "get_db_context",
    "init_database",
    "drop_database",
    "check_database_connection",
]
