"""
User Authentication Module for BrainRace.

Handles user registration, login, sessions, and game history tracking.
Uses SQLite for persistent storage with password hashing for security.
"""

import sqlite3
import hashlib
import secrets
import os
from datetime import datetime, timedelta
from typing import Optional

# Database path
DB_PATH = "users.db"


def _get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """
    Hash a password with a salt using SHA-256.

    Args:
        password: The plain text password
        salt: Optional salt, generates new one if not provided

    Returns:
        Tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)

    salted = f"{salt}{password}"
    hashed = hashlib.sha256(salted.encode()).hexdigest()
    return hashed, salt


def init_auth_db() -> None:
    """Initialize the authentication database tables."""
    conn = _get_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            display_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            total_games INTEGER DEFAULT 0,
            total_score INTEGER DEFAULT 0,
            highest_score INTEGER DEFAULT 0,
            total_correct INTEGER DEFAULT 0,
            total_answered INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            favorite_category TEXT
        )
    """)

    # Sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Game history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            correct_answers INTEGER NOT NULL,
            total_questions INTEGER NOT NULL,
            best_streak INTEGER NOT NULL,
            difficulty TEXT,
            categories TEXT,
            game_mode TEXT,
            timed_mode INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 1,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


def register_user(username: str, password: str, display_name: Optional[str] = None) -> dict:
    """
    Register a new user.

    Args:
        username: Unique username (case-insensitive)
        password: Plain text password
        display_name: Optional display name, defaults to username

    Returns:
        Dict with success status and user info or error message
    """
    if not username or len(username) < 3:
        return {"success": False, "error": "Username must be at least 3 characters"}

    if not password or len(password) < 4:
        return {"success": False, "error": "Password must be at least 4 characters"}

    username = username.lower().strip()
    display_name = display_name or username

    conn = _get_connection()
    cursor = conn.cursor()

    # Check if username exists
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return {"success": False, "error": "Username already taken"}

    # Hash password and create user
    password_hash, salt = _hash_password(password)

    cursor.execute("""
        INSERT INTO users (username, password_hash, salt, display_name)
        VALUES (?, ?, ?, ?)
    """, (username, password_hash, salt, display_name))

    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "user": {
            "id": user_id,
            "username": username,
            "display_name": display_name
        }
    }


def login_user(username: str, password: str) -> dict:
    """
    Authenticate a user and create a session.

    Args:
        username: The username
        password: Plain text password

    Returns:
        Dict with success status, session token, and user info
    """
    username = username.lower().strip()

    conn = _get_connection()
    cursor = conn.cursor()

    # Get user
    cursor.execute("""
        SELECT id, username, password_hash, salt, display_name,
               total_games, highest_score, best_streak
        FROM users WHERE username = ?
    """, (username,))

    user = cursor.fetchone()
    if not user:
        conn.close()
        return {"success": False, "error": "Invalid username or password"}

    # Verify password
    password_hash, _ = _hash_password(password, user["salt"])
    if password_hash != user["password_hash"]:
        conn.close()
        return {"success": False, "error": "Invalid username or password"}

    # Create session
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=30)

    cursor.execute("""
        INSERT INTO sessions (user_id, session_token, expires_at)
        VALUES (?, ?, ?)
    """, (user["id"], session_token, expires_at))

    # Update last login
    cursor.execute("""
        UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
    """, (user["id"],))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "session_token": session_token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "display_name": user["display_name"],
            "total_games": user["total_games"],
            "highest_score": user["highest_score"],
            "best_streak": user["best_streak"]
        }
    }


def get_user_from_session(session_token: str) -> Optional[dict]:
    """
    Get user info from a session token.

    Args:
        session_token: The session token from cookie

    Returns:
        User dict if valid session, None otherwise
    """
    if not session_token:
        return None

    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT u.id, u.username, u.display_name, u.total_games,
               u.total_score, u.highest_score, u.total_correct,
               u.total_answered, u.best_streak, u.favorite_category,
               u.created_at
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.session_token = ? AND s.expires_at > CURRENT_TIMESTAMP
    """, (session_token,))

    user = cursor.fetchone()
    conn.close()

    if not user:
        return None

    return dict(user)


def logout_user(session_token: str) -> bool:
    """
    Delete a user's session.

    Args:
        session_token: The session token to invalidate

    Returns:
        True if session was deleted
    """
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE session_token = ?", (session_token,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def save_game_result(user_id: int, result: dict) -> dict:
    """
    Save a game result and update user stats.

    Args:
        user_id: The user's ID
        result: Game result dict with score, correct, total, streak, etc.

    Returns:
        Updated user stats
    """
    conn = _get_connection()
    cursor = conn.cursor()

    # Insert game history
    cursor.execute("""
        INSERT INTO game_history
        (user_id, score, correct_answers, total_questions, best_streak,
         difficulty, categories, game_mode, timed_mode, completed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        result.get("score", 0),
        result.get("correct", 0),
        result.get("total", 0),
        result.get("best_streak", 0),
        result.get("difficulty", ""),
        result.get("categories", ""),
        result.get("game_mode", "solo"),
        1 if result.get("timed_mode") else 0,
        1 if result.get("completed", True) else 0
    ))

    # Update user stats
    cursor.execute("""
        UPDATE users SET
            total_games = total_games + 1,
            total_score = total_score + ?,
            highest_score = MAX(highest_score, ?),
            total_correct = total_correct + ?,
            total_answered = total_answered + ?,
            best_streak = MAX(best_streak, ?)
        WHERE id = ?
    """, (
        result.get("score", 0),
        result.get("score", 0),
        result.get("correct", 0),
        result.get("total", 0),
        result.get("best_streak", 0),
        user_id
    ))

    # Get updated stats
    cursor.execute("""
        SELECT total_games, total_score, highest_score, best_streak
        FROM users WHERE id = ?
    """, (user_id,))

    stats = cursor.fetchone()
    conn.commit()
    conn.close()

    return dict(stats) if stats else {}


def get_user_stats(user_id: int) -> dict:
    """
    Get comprehensive stats for a user.

    Args:
        user_id: The user's ID

    Returns:
        Dict with user stats and recent games
    """
    conn = _get_connection()
    cursor = conn.cursor()

    # Get user stats
    cursor.execute("""
        SELECT username, display_name, total_games, total_score,
               highest_score, total_correct, total_answered, best_streak,
               created_at
        FROM users WHERE id = ?
    """, (user_id,))

    user = cursor.fetchone()
    if not user:
        conn.close()
        return {}

    # Get recent games
    cursor.execute("""
        SELECT score, correct_answers, total_questions, best_streak,
               difficulty, game_mode, timed_mode, played_at
        FROM game_history
        WHERE user_id = ?
        ORDER BY played_at DESC
        LIMIT 10
    """, (user_id,))

    recent_games = [dict(row) for row in cursor.fetchall()]

    # Calculate accuracy
    accuracy = 0
    if user["total_answered"] > 0:
        accuracy = round((user["total_correct"] / user["total_answered"]) * 100, 1)

    conn.close()

    return {
        **dict(user),
        "accuracy": accuracy,
        "recent_games": recent_games
    }


def get_user_rank(user_id: int) -> dict:
    """
    Get a user's ranking compared to others.

    Args:
        user_id: The user's ID

    Returns:
        Dict with rank info
    """
    conn = _get_connection()
    cursor = conn.cursor()

    # Get rank by highest score
    cursor.execute("""
        SELECT COUNT(*) + 1 as rank
        FROM users
        WHERE highest_score > (SELECT highest_score FROM users WHERE id = ?)
    """, (user_id,))

    rank = cursor.fetchone()

    # Get total users
    cursor.execute("SELECT COUNT(*) as total FROM users WHERE total_games > 0")
    total = cursor.fetchone()

    conn.close()

    return {
        "rank": rank["rank"] if rank else 0,
        "total_players": total["total"] if total else 0
    }


# Initialize database on module load
init_auth_db()
