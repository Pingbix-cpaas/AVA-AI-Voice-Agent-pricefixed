import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from models import Base

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ava:ava123@postgres:5432/ava")
# Create engine
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
    echo=False  # Set to True for debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create scoped session for thread safety
Session = scoped_session(SessionLocal)

def get_db():
    """Dependency to get database session"""
    db = Session()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def get_session():
    """Get a database session"""
    return Session()

def close_session():
    """Close the scoped session"""
    Session.remove()
