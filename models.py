"""
SQLAlchemy ORM models for BrainRace trivia game.

This module defines the database models for storing game data,
including player scores and game statistics.

Example:
    from models import Score
    from database import get_db

    # Create a new score entry
    new_score = Score(
        player_name="Alice",
        score=150,
        total_questions=10
    )
    db.add(new_score)
    db.commit()
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime

from database import Base


class Score(Base):
    """
    Model for storing player game scores.

    This model represents a single game score entry in the leaderboard,
    tracking the player's name, score achieved, number of questions,
    and when the score was recorded.

    Attributes:
        id: Primary key, auto-incremented unique identifier.
        player_name: Name of the player (max 50 characters).
        score: Total points scored in the game.
        total_questions: Number of questions in the game session.
        created_at: Timestamp when the score was recorded (UTC).

    Example:
        score = Score(
            player_name="Bob",
            score=200,
            total_questions=15
        )
    """

    __tablename__ = "scores"

    id: int = Column(Integer, primary_key=True, index=True)
    player_name: str = Column(String(50), nullable=False)
    score: int = Column(Integer, nullable=False)
    total_questions: int = Column(Integer, nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        """Return string representation of the Score instance."""
        return f"<Score(player_name='{self.player_name}', score={self.score})>"
