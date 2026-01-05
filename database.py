"""
Database configuration module for BrainRace trivia game.

This module sets up SQLAlchemy ORM with SQLite database for storing
game scores and related data. It provides the database engine,
session factory, and dependency injection for FastAPI routes.

Example:
    from database import get_db, engine, Base

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Use in FastAPI route
    @app.get("/items")
    def get_items(db: Session = Depends(get_db)):
        return db.query(Item).all()
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# SQLite database file location
SQLALCHEMY_DATABASE_URL: str = "sqlite:///./trivia.db"

# Create SQLAlchemy engine with SQLite-specific configuration
# check_same_thread=False is required for SQLite with FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Session factory for creating database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative ORM models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session for FastAPI routes.

    Creates a new SQLAlchemy Session for each request, and ensures
    the session is properly closed after the request completes,
    regardless of whether an exception occurred.

    Yields:
        Session: A SQLAlchemy database session.

    Example:
        @app.get("/scores")
        def get_scores(db: Session = Depends(get_db)):
            return db.query(Score).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
