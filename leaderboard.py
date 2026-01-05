"""
Leaderboard module for History Trivia Game.

Handles saving and retrieving high scores using SQLite.
"""

import sqlite3
from datetime import datetime
from typing import Optional

DATABASE_PATH = "leaderboard.db"


def _get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory for dict-like access."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the leaderboard database table."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS high_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            score INTEGER NOT NULL,
            date TEXT NOT NULL,
            category TEXT,
            difficulty TEXT,
            total_questions INTEGER
        )
    """)
    conn.commit()
    conn.close()


def save_score(
    player_name: str,
    score: int,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    total_questions: Optional[int] = None
) -> dict:
    """
    Save a player's score to the leaderboard.

    Args:
        player_name: Name of the player
        score: The score achieved
        category: Category/era played (e.g., 'ancient', 'medieval', 'modern', 'mixed')
        difficulty: Difficulty level played
        total_questions: Number of questions in the game

    Returns:
        Dict with save result including rank if in top 10
    """
    conn = _get_connection()
    cursor = conn.cursor()

    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        "INSERT INTO high_scores (player_name, score, date, category, difficulty, total_questions) VALUES (?, ?, ?, ?, ?, ?)",
        (player_name, score, date, category, difficulty, total_questions)
    )
    score_id = cursor.lastrowid
    conn.commit()

    # Check rank
    cursor.execute(
        "SELECT id FROM high_scores ORDER BY score DESC LIMIT 10"
    )
    top_ids = [row["id"] for row in cursor.fetchall()]
    conn.close()

    rank = None
    made_leaderboard = score_id in top_ids
    if made_leaderboard:
        rank = top_ids.index(score_id) + 1

    return {
        "success": True,
        "made_leaderboard": made_leaderboard,
        "rank": rank
    }


def get_top_scores(limit: int = 10) -> list[dict]:
    """
    Get top scores from the leaderboard.

    Args:
        limit: Maximum number of scores to return (default 10)

    Returns:
        List of score dicts with rank, player_name, score, date, category, difficulty, total_questions
    """
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT player_name, score, date, category, difficulty, total_questions FROM high_scores ORDER BY score DESC LIMIT ?",
        (limit,)
    )

    scores = []
    for i, row in enumerate(cursor.fetchall()):
        scores.append({
            "rank": i + 1,
            "player_name": row["player_name"],
            "score": row["score"],
            "date": row["date"].split(" ")[0] if row["date"] else None,
            "category": row["category"],
            "difficulty": row["difficulty"],
            "total_questions": row["total_questions"]
        })

    conn.close()
    return scores


def get_player_best(player_name: str) -> Optional[dict]:
    """
    Get a player's best score.

    Args:
        player_name: Name of the player

    Returns:
        Dict with player's best score info, or None if no scores found
    """
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT player_name, score, date, category, difficulty FROM high_scores WHERE player_name = ? ORDER BY score DESC LIMIT 1",
        (player_name,)
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "player_name": row["player_name"],
            "score": row["score"],
            "date": row["date"].split(" ")[0] if row["date"] else None,
            "category": row["category"],
            "difficulty": row["difficulty"]
        }
    return None


# Initialize database on module import
init_db()
