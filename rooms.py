"""
Rooms module for BrainRace async multiplayer.

Handles room creation, joining, and score tracking using SQLite.
"""

import sqlite3
import json
import random
import string
from datetime import datetime, timedelta
from typing import Optional

DATABASE_PATH = "leaderboard.db"


def _get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory for dict-like access."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_rooms_db() -> None:
    """Initialize the rooms database tables."""
    conn = _get_connection()
    cursor = conn.cursor()

    # Rooms table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_code TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            host_name TEXT NOT NULL,
            categories TEXT,
            difficulty TEXT,
            question_ids TEXT NOT NULL,
            status TEXT DEFAULT 'waiting'
        )
    """)

    # Room players table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS room_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
            player_name TEXT NOT NULL,
            score INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            completed_at TEXT,
            FOREIGN KEY (room_id) REFERENCES rooms(id),
            UNIQUE(room_id, player_name)
        )
    """)

    conn.commit()
    conn.close()


def _generate_room_code(length: int = 6) -> str:
    """Generate a unique room code."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def create_room(
    host_name: str,
    question_ids: list[int],
    categories: Optional[str] = None,
    difficulty: Optional[str] = None,
    expires_hours: int = 24
) -> dict:
    """
    Create a new game room.

    Args:
        host_name: Name of the player creating the room
        question_ids: List of question IDs for this room's game
        categories: Categories selected for the game
        difficulty: Difficulty setting
        expires_hours: Hours until room expires (default 24)

    Returns:
        Dict with room info including room_code
    """
    conn = _get_connection()
    cursor = conn.cursor()

    # Generate unique room code
    room_code = _generate_room_code()
    while True:
        cursor.execute("SELECT id FROM rooms WHERE room_code = ?", (room_code,))
        if not cursor.fetchone():
            break
        room_code = _generate_room_code()

    created_at = datetime.now()
    expires_at = created_at + timedelta(hours=expires_hours)

    cursor.execute("""
        INSERT INTO rooms (room_code, created_at, expires_at, host_name, categories, difficulty, question_ids, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'waiting')
    """, (
        room_code,
        created_at.strftime("%Y-%m-%d %H:%M:%S"),
        expires_at.strftime("%Y-%m-%d %H:%M:%S"),
        host_name,
        categories,
        difficulty,
        json.dumps(question_ids)
    ))

    room_id = cursor.lastrowid

    # Add host as first player
    cursor.execute("""
        INSERT INTO room_players (room_id, player_name) VALUES (?, ?)
    """, (room_id, host_name))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "room_code": room_code,
        "room_id": room_id,
        "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S")
    }


def get_room(room_code: str) -> Optional[dict]:
    """
    Get room info by room code.

    Args:
        room_code: The unique room code

    Returns:
        Room info dict or None if not found/expired
    """
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, room_code, created_at, expires_at, host_name, categories, difficulty, question_ids, status
        FROM rooms WHERE room_code = ?
    """, (room_code.upper(),))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    # Check if expired
    expires_at = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expires_at:
        return None

    return {
        "id": row["id"],
        "room_code": row["room_code"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "host_name": row["host_name"],
        "categories": row["categories"],
        "difficulty": row["difficulty"],
        "question_ids": json.loads(row["question_ids"]),
        "status": row["status"]
    }


def join_room(room_code: str, player_name: str) -> dict:
    """
    Join an existing room.

    Args:
        room_code: The room code to join
        player_name: Name of the player joining

    Returns:
        Dict with success status and room info
    """
    room = get_room(room_code)
    if not room:
        return {"success": False, "error": "Room not found or expired"}

    conn = _get_connection()
    cursor = conn.cursor()

    # Check if player already in room
    cursor.execute("""
        SELECT id, completed FROM room_players WHERE room_id = ? AND player_name = ?
    """, (room["id"], player_name))

    existing = cursor.fetchone()
    if existing:
        conn.close()
        return {
            "success": True,
            "room": room,
            "already_joined": True,
            "already_completed": existing["completed"] == 1
        }

    # Add player to room
    cursor.execute("""
        INSERT INTO room_players (room_id, player_name) VALUES (?, ?)
    """, (room["id"], player_name))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "room": room,
        "already_joined": False,
        "already_completed": False
    }


def get_room_players(room_code: str) -> list[dict]:
    """
    Get all players in a room.

    Args:
        room_code: The room code

    Returns:
        List of player dicts with scores
    """
    room = get_room(room_code)
    if not room:
        return []

    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT player_name, score, correct_count, best_streak, completed, completed_at
        FROM room_players WHERE room_id = ? ORDER BY score DESC, completed_at ASC
    """, (room["id"],))

    players = []
    for row in cursor.fetchall():
        players.append({
            "player_name": row["player_name"],
            "score": row["score"],
            "correct_count": row["correct_count"],
            "best_streak": row["best_streak"],
            "completed": row["completed"] == 1,
            "completed_at": row["completed_at"]
        })

    conn.close()
    return players


def save_room_score(
    room_code: str,
    player_name: str,
    score: int,
    correct_count: int,
    best_streak: int
) -> dict:
    """
    Save a player's score for a room game.

    Args:
        room_code: The room code
        player_name: Player's name
        score: Total score
        correct_count: Number of correct answers
        best_streak: Best streak achieved

    Returns:
        Dict with save result and current standings
    """
    room = get_room(room_code)
    if not room:
        return {"success": False, "error": "Room not found or expired"}

    conn = _get_connection()
    cursor = conn.cursor()

    completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE room_players
        SET score = ?, correct_count = ?, best_streak = ?, completed = 1, completed_at = ?
        WHERE room_id = ? AND player_name = ?
    """, (score, correct_count, best_streak, completed_at, room["id"], player_name))

    conn.commit()
    conn.close()

    # Get updated standings
    players = get_room_players(room_code)

    # Find player's rank
    rank = next((i + 1 for i, p in enumerate(players) if p["player_name"] == player_name), None)

    return {
        "success": True,
        "rank": rank,
        "players": players
    }


def cleanup_expired_rooms() -> int:
    """
    Remove expired rooms and their players.

    Returns:
        Number of rooms cleaned up
    """
    conn = _get_connection()
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Get expired room IDs
    cursor.execute("SELECT id FROM rooms WHERE expires_at < ?", (now,))
    expired_ids = [row["id"] for row in cursor.fetchall()]

    if expired_ids:
        # Delete players from expired rooms
        cursor.execute(
            f"DELETE FROM room_players WHERE room_id IN ({','.join('?' * len(expired_ids))})",
            expired_ids
        )
        # Delete expired rooms
        cursor.execute(
            f"DELETE FROM rooms WHERE id IN ({','.join('?' * len(expired_ids))})",
            expired_ids
        )

    conn.commit()
    conn.close()

    return len(expired_ids)


# Initialize database on module import
init_rooms_db()
