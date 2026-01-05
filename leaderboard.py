"""
Leaderboard Module for BrainRace Trivia Game.

This module handles persistent storage and retrieval of player high scores
using a SQLite database. Features include:
- Saving game scores with metadata (category, difficulty, date)
- Retrieving top scores for display on the leaderboard
- Looking up individual player's best scores
- Automatic database initialization on module import

The leaderboard is stored in a local SQLite database file (leaderboard.db).
"""

import sqlite3
from datetime import datetime
from typing import Optional, Any

# Path to the SQLite database file
DATABASE_PATH: str = "leaderboard.db"


def _get_connection() -> sqlite3.Connection:
    """
    Create and return a SQLite database connection.

    The connection is configured with sqlite3.Row as the row factory,
    allowing column access by name (dict-like) in addition to index.

    Returns:
        A sqlite3.Connection object ready for queries.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Initialize the leaderboard database table.

    Creates the high_scores table if it doesn't exist. This function
    is automatically called on module import to ensure the database
    is ready for use.

    The table schema includes:
    - id: Auto-incrementing primary key
    - player_name: Display name of the player
    - score: Total points achieved
    - date: Timestamp of when the score was recorded
    - category: Optional category filter used
    - difficulty: Optional difficulty setting used
    - total_questions: Number of questions in the game
    """
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
) -> dict[str, Any]:
    """
    Save a player's score to the leaderboard.

    Records the score with timestamp and optional game metadata.
    Also checks if the score qualifies for the top 10 leaderboard.

    Args:
        player_name: Display name of the player.
        score: The total score achieved.
        category: Category filter used in the game (e.g., 'ancient-civilizations').
        difficulty: Difficulty setting used (e.g., 'progressive', 'hard').
        total_questions: Number of questions in the game session.

    Returns:
        A dictionary containing:
        - success: Always True on successful save
        - made_leaderboard: Whether the score is in the top 10
        - rank: Position in top 10 (1-10) or None if not ranked
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


def get_top_scores(limit: int = 10) -> list[dict[str, Any]]:
    """
    Get the top scores from the leaderboard.

    Retrieves scores ordered by score descending, typically for
    displaying on the leaderboard page.

    Args:
        limit: Maximum number of scores to return (default 10).

    Returns:
        A list of score dictionaries, each containing:
        - rank: Position (1-based) in the leaderboard
        - player_name: Display name of the player
        - score: Total points achieved
        - date: Date portion of the timestamp (YYYY-MM-DD)
        - category: Category filter used (may be None)
        - difficulty: Difficulty setting used (may be None)
        - total_questions: Number of questions in the game
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


def get_player_best(player_name: str) -> Optional[dict[str, Any]]:
    """
    Get a player's personal best score.

    Looks up the highest score achieved by a specific player,
    useful for displaying personal records or achievements.

    Args:
        player_name: The exact display name to search for.

    Returns:
        A dictionary with the player's best score containing:
        - player_name: The player's name
        - score: Their highest score
        - date: Date of the record (YYYY-MM-DD)
        - category: Category filter used
        - difficulty: Difficulty setting used

        Returns None if the player has no recorded scores.
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
