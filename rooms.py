"""
Rooms Module for BrainRace Asynchronous Multiplayer.

This module handles the persistence layer for asynchronous multiplayer games
where players can play the same quiz at different times. Features include:
- Room creation with unique 6-character codes
- Player joining and tracking
- Score submission and ranking within rooms
- Automatic room expiration (default 24 hours)

Rooms are stored in SQLite alongside the leaderboard data. Each room has:
- A unique alphanumeric code for sharing
- Pre-selected questions that all players answer
- Expiration time for automatic cleanup
- Player list with individual scores

This is distinct from the WebSocket-based real-time multiplayer,
which uses the websocket_manager module for live synchronized games.
"""

import sqlite3
import json
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Any

# Path to the SQLite database file (shared with leaderboard)
DATABASE_PATH: str = "leaderboard.db"


def _get_connection() -> sqlite3.Connection:
    """
    Create and return a SQLite database connection.

    The connection is configured with sqlite3.Row as the row factory,
    enabling dict-like access to query results.

    Returns:
        A sqlite3.Connection object ready for queries.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_rooms_db() -> None:
    """
    Initialize the rooms database tables.

    Creates two tables if they don't exist:

    1. rooms: Stores room metadata
       - id: Auto-incrementing primary key
       - room_code: Unique shareable code (e.g., 'ABC123')
       - created_at/expires_at: Timestamps for lifecycle management
       - host_name: Creator's display name
       - categories/difficulty: Game settings
       - question_ids: JSON array of question IDs
       - status: Room state ('waiting', 'playing', etc.)

    2. room_players: Stores player data within rooms
       - Links to room via room_id foreign key
       - Tracks score, correct count, streak
       - completion status and timestamp

    This function is called automatically on module import.
    """
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
    """
    Generate a random alphanumeric room code.

    Creates a code using uppercase letters and digits that players
    can share to join the same room. Uniqueness is verified by the
    caller (create_room function).

    Args:
        length: Number of characters in the code (default 6).

    Returns:
        A random string like 'ABC123' or 'XY7Z9W'.
    """
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def create_room(
    host_name: str,
    question_ids: list[int],
    categories: Optional[str] = None,
    difficulty: Optional[str] = None,
    expires_hours: int = 24
) -> dict[str, Any]:
    """
    Create a new asynchronous multiplayer game room.

    Generates a unique room code and stores the room configuration
    in the database. The host is automatically added as the first
    player in the room.

    Args:
        host_name: Display name of the player creating the room.
        question_ids: List of question IDs that all players will answer.
        categories: Comma-separated category filter string (for display).
        difficulty: Difficulty mode used (for display).
        expires_hours: Hours until the room expires (default 24).

    Returns:
        A dictionary containing:
        - success: Always True on successful creation
        - room_code: The shareable code (e.g., 'ABC123')
        - room_id: Database ID of the room
        - expires_at: Timestamp when the room will expire
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


def get_room(room_code: str) -> Optional[dict[str, Any]]:
    """
    Retrieve room information by room code.

    Looks up a room and returns its full details if found and not expired.
    Room codes are case-insensitive (converted to uppercase).

    Args:
        room_code: The unique room code (e.g., 'ABC123').

    Returns:
        A dictionary containing room details:
        - id: Database ID
        - room_code: The room code
        - created_at/expires_at: Timestamps
        - host_name: Creator's name
        - categories/difficulty: Game settings
        - question_ids: List of question IDs (parsed from JSON)
        - status: Current room status

        Returns None if the room doesn't exist or has expired.
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


def join_room(room_code: str, player_name: str) -> dict[str, Any]:
    """
    Join an existing game room.

    Adds a player to the room's player list. If the player has
    already joined, returns their current status without duplicating.

    Args:
        room_code: The room code to join.
        player_name: Display name of the player joining.

    Returns:
        A dictionary containing:
        - success: Whether the join was successful
        - error: Error message if success is False
        - room: Full room details (if successful)
        - already_joined: Whether player was already in the room
        - already_completed: Whether player already finished the game
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


def get_room_players(room_code: str) -> list[dict[str, Any]]:
    """
    Get all players in a room with their scores.

    Returns the player list sorted by score (descending) and then
    by completion time for players with equal scores.

    Args:
        room_code: The room code to look up.

    Returns:
        A list of player dictionaries, each containing:
        - player_name: The player's display name
        - score: Total points achieved
        - correct_count: Number of correct answers
        - best_streak: Longest answer streak
        - completed: Whether they've finished the game
        - completed_at: Timestamp of completion (if completed)

        Returns empty list if the room doesn't exist.
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
) -> dict[str, Any]:
    """
    Save a player's final score for a room-based game.

    Updates the player's record in the room with their final score
    and marks them as completed. This is called when a player
    finishes answering all questions in the room's quiz.

    Args:
        room_code: The room code.
        player_name: The player's display name.
        score: Total points achieved.
        correct_count: Number of correct answers.
        best_streak: Longest consecutive correct answer streak.

    Returns:
        A dictionary containing:
        - success: Whether the save was successful
        - error: Error message if success is False
        - rank: Player's position in the room standings
        - players: Full updated player list with scores
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
    Remove expired rooms and their associated player data.

    Deletes rooms that have passed their expiration time, along with
    all player records for those rooms. This can be called periodically
    to keep the database clean.

    Returns:
        The number of rooms that were deleted.
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
