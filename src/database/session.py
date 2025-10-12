"""Database session management"""
from contextlib import contextmanager
from .base import SessionLocal, engine, Base


def init_db():
    """Initialize database, create all tables"""
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")


def get_session():
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Don't close here, caller is responsible


@contextmanager
def get_db_context():
    """Get database session as context manager"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

