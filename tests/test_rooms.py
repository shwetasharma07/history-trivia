"""Tests for rooms module."""

import pytest
import sqlite3
import os
import tempfile
import json
from datetime import datetime, timedelta
from unittest.mock import patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import rooms


class TestRoomsDatabase:
    """Tests for rooms database initialization."""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up a temporary database for each test."""
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix='.db')
        self.original_db_path = rooms.DATABASE_PATH
        rooms.DATABASE_PATH = self.temp_path
        rooms.init_rooms_db()

        yield

        rooms.DATABASE_PATH = self.original_db_path
        os.close(self.temp_fd)
        os.unlink(self.temp_path)

    def test_init_creates_rooms_table(self):
        """Should create rooms table on initialization."""
        conn = sqlite3.connect(self.temp_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='rooms'"
        )
        result = cursor.fetchone()
        conn.close()
        assert result is not None
        assert result[0] == 'rooms'

    def test_init_creates_room_players_table(self):
        """Should create room_players table on initialization."""
        conn = sqlite3.connect(self.temp_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='room_players'"
        )
        result = cursor.fetchone()
        conn.close()
        assert result is not None
        assert result[0] == 'room_players'

    def test_init_idempotent(self):
        """Calling init multiple times should not cause errors."""
        rooms.init_rooms_db()
        rooms.init_rooms_db()


class TestGenerateRoomCode:
    """Tests for room code generation."""

    def test_generates_string(self):
        """Should generate a string."""
        code = rooms._generate_room_code()
        assert isinstance(code, str)

    def test_default_length_is_six(self):
        """Default code length should be 6."""
        code = rooms._generate_room_code()
        assert len(code) == 6

    def test_custom_length(self):
        """Should respect custom length parameter."""
        code = rooms._generate_room_code(length=8)
        assert len(code) == 8

    def test_uppercase_and_digits_only(self):
        """Code should only contain uppercase letters and digits."""
        code = rooms._generate_room_code()
        for char in code:
            assert char.isupper() or char.isdigit()

    def test_different_codes(self):
        """Multiple calls should generate different codes."""
        codes = [rooms._generate_room_code() for _ in range(10)]
        # At least some should be different (probability of all same is negligible)
        assert len(set(codes)) > 1


class TestCreateRoom:
    """Tests for create_room function."""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up a temporary database for each test."""
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix='.db')
        self.original_db_path = rooms.DATABASE_PATH
        rooms.DATABASE_PATH = self.temp_path
        rooms.init_rooms_db()

        yield

        rooms.DATABASE_PATH = self.original_db_path
        os.close(self.temp_fd)
        os.unlink(self.temp_path)

    def test_returns_dict(self):
        """Should return a dictionary."""
        result = rooms.create_room("TestHost", [1, 2, 3])
        assert isinstance(result, dict)

    def test_success_flag(self):
        """Should return success=True."""
        result = rooms.create_room("TestHost", [1, 2, 3])
        assert result["success"] is True

    def test_returns_room_code(self):
        """Should return a room code."""
        result = rooms.create_room("TestHost", [1, 2, 3])
        assert "room_code" in result
        assert len(result["room_code"]) == 6

    def test_returns_room_id(self):
        """Should return a room ID."""
        result = rooms.create_room("TestHost", [1, 2, 3])
        assert "room_id" in result
        assert isinstance(result["room_id"], int)

    def test_returns_expires_at(self):
        """Should return expiration timestamp."""
        result = rooms.create_room("TestHost", [1, 2, 3])
        assert "expires_at" in result

    def test_host_added_as_player(self):
        """Host should be added as first player."""
        result = rooms.create_room("HostPlayer", [1, 2, 3])
        players = rooms.get_room_players(result["room_code"])
        assert len(players) == 1
        assert players[0]["player_name"] == "HostPlayer"

    def test_stores_question_ids(self):
        """Should store question IDs."""
        question_ids = [10, 20, 30, 40]
        result = rooms.create_room("TestHost", question_ids)
        room = rooms.get_room(result["room_code"])
        assert room["question_ids"] == question_ids

    def test_stores_categories(self):
        """Should store categories."""
        result = rooms.create_room(
            "TestHost",
            [1, 2, 3],
            categories="history,science"
        )
        room = rooms.get_room(result["room_code"])
        assert room["categories"] == "history,science"

    def test_stores_difficulty(self):
        """Should store difficulty."""
        result = rooms.create_room(
            "TestHost",
            [1, 2, 3],
            difficulty="hard"
        )
        room = rooms.get_room(result["room_code"])
        assert room["difficulty"] == "hard"

    def test_default_expires_24_hours(self):
        """Default expiration should be 24 hours."""
        result = rooms.create_room("TestHost", [1, 2, 3])
        room = rooms.get_room(result["room_code"])

        created = datetime.strptime(room["created_at"], "%Y-%m-%d %H:%M:%S")
        expires = datetime.strptime(room["expires_at"], "%Y-%m-%d %H:%M:%S")
        delta = expires - created

        # Should be approximately 24 hours
        assert 23 <= delta.total_seconds() / 3600 <= 25

    def test_custom_expires_hours(self):
        """Should respect custom expiration hours."""
        result = rooms.create_room("TestHost", [1, 2, 3], expires_hours=48)
        room = rooms.get_room(result["room_code"])

        created = datetime.strptime(room["created_at"], "%Y-%m-%d %H:%M:%S")
        expires = datetime.strptime(room["expires_at"], "%Y-%m-%d %H:%M:%S")
        delta = expires - created

        assert 47 <= delta.total_seconds() / 3600 <= 49

    def test_initial_status_is_waiting(self):
        """Room status should be 'waiting' initially."""
        result = rooms.create_room("TestHost", [1, 2, 3])
        room = rooms.get_room(result["room_code"])
        assert room["status"] == "waiting"


class TestGetRoom:
    """Tests for get_room function."""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up a temporary database for each test."""
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix='.db')
        self.original_db_path = rooms.DATABASE_PATH
        rooms.DATABASE_PATH = self.temp_path
        rooms.init_rooms_db()

        yield

        rooms.DATABASE_PATH = self.original_db_path
        os.close(self.temp_fd)
        os.unlink(self.temp_path)

    def test_returns_none_for_nonexistent(self):
        """Should return None for non-existent room."""
        result = rooms.get_room("NOTEXIST")
        assert result is None

    def test_returns_room_info(self):
        """Should return room information."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        room = rooms.get_room(create_result["room_code"])

        assert room is not None
        assert room["room_code"] == create_result["room_code"]
        assert room["host_name"] == "Host"

    def test_case_insensitive_code(self):
        """Room code lookup should be case-insensitive."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        code = create_result["room_code"]

        room_upper = rooms.get_room(code.upper())
        room_lower = rooms.get_room(code.lower())

        assert room_upper is not None
        assert room_lower is not None

    def test_returns_none_for_expired(self):
        """Should return None for expired rooms."""
        # Create room with very short expiration
        create_result = rooms.create_room("Host", [1, 2, 3], expires_hours=0)

        # Manually set expiration to the past
        conn = rooms._get_connection()
        cursor = conn.cursor()
        past_time = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "UPDATE rooms SET expires_at = ? WHERE room_code = ?",
            (past_time, create_result["room_code"])
        )
        conn.commit()
        conn.close()

        # Should now return None
        room = rooms.get_room(create_result["room_code"])
        assert room is None

    def test_room_structure(self):
        """Room dict should have expected fields."""
        create_result = rooms.create_room(
            "Host",
            [1, 2, 3],
            categories="history",
            difficulty="medium"
        )
        room = rooms.get_room(create_result["room_code"])

        assert "id" in room
        assert "room_code" in room
        assert "created_at" in room
        assert "expires_at" in room
        assert "host_name" in room
        assert "categories" in room
        assert "difficulty" in room
        assert "question_ids" in room
        assert "status" in room


class TestJoinRoom:
    """Tests for join_room function."""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up a temporary database for each test."""
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix='.db')
        self.original_db_path = rooms.DATABASE_PATH
        rooms.DATABASE_PATH = self.temp_path
        rooms.init_rooms_db()

        yield

        rooms.DATABASE_PATH = self.original_db_path
        os.close(self.temp_fd)
        os.unlink(self.temp_path)

    def test_returns_dict(self):
        """Should return a dictionary."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        result = rooms.join_room(create_result["room_code"], "NewPlayer")
        assert isinstance(result, dict)

    def test_join_nonexistent_room(self):
        """Should return error for non-existent room."""
        result = rooms.join_room("NOTEXIST", "Player")
        assert result["success"] is False
        assert "error" in result

    def test_join_success(self):
        """Should successfully join an existing room."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        result = rooms.join_room(create_result["room_code"], "NewPlayer")

        assert result["success"] is True
        assert result["already_joined"] is False

    def test_adds_player_to_room(self):
        """Joining should add player to room players."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        rooms.join_room(create_result["room_code"], "NewPlayer")

        players = rooms.get_room_players(create_result["room_code"])
        player_names = [p["player_name"] for p in players]
        assert "NewPlayer" in player_names

    def test_rejoin_already_joined(self):
        """Should handle rejoining already joined room."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        rooms.join_room(create_result["room_code"], "Player")

        # Try to join again
        result = rooms.join_room(create_result["room_code"], "Player")
        assert result["success"] is True
        assert result["already_joined"] is True

    def test_returns_room_info(self):
        """Should return room info on successful join."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        result = rooms.join_room(create_result["room_code"], "NewPlayer")

        assert "room" in result
        assert result["room"]["host_name"] == "Host"


class TestGetRoomPlayers:
    """Tests for get_room_players function."""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up a temporary database for each test."""
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix='.db')
        self.original_db_path = rooms.DATABASE_PATH
        rooms.DATABASE_PATH = self.temp_path
        rooms.init_rooms_db()

        yield

        rooms.DATABASE_PATH = self.original_db_path
        os.close(self.temp_fd)
        os.unlink(self.temp_path)

    def test_returns_list(self):
        """Should return a list."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        result = rooms.get_room_players(create_result["room_code"])
        assert isinstance(result, list)

    def test_nonexistent_room_returns_empty(self):
        """Should return empty list for non-existent room."""
        result = rooms.get_room_players("NOTEXIST")
        assert result == []

    def test_includes_host(self):
        """Should include the host."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        players = rooms.get_room_players(create_result["room_code"])
        assert len(players) == 1
        assert players[0]["player_name"] == "Host"

    def test_includes_all_players(self):
        """Should include all joined players."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        rooms.join_room(create_result["room_code"], "Player1")
        rooms.join_room(create_result["room_code"], "Player2")

        players = rooms.get_room_players(create_result["room_code"])
        player_names = [p["player_name"] for p in players]

        assert len(players) == 3
        assert "Host" in player_names
        assert "Player1" in player_names
        assert "Player2" in player_names

    def test_player_structure(self):
        """Each player should have expected fields."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        players = rooms.get_room_players(create_result["room_code"])

        player = players[0]
        assert "player_name" in player
        assert "score" in player
        assert "correct_count" in player
        assert "best_streak" in player
        assert "completed" in player

    def test_default_values(self):
        """New players should have default values."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        players = rooms.get_room_players(create_result["room_code"])

        player = players[0]
        assert player["score"] == 0
        assert player["correct_count"] == 0
        assert player["best_streak"] == 0
        assert player["completed"] is False

    def test_ordered_by_score(self):
        """Players should be ordered by score descending."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        rooms.join_room(create_result["room_code"], "Player1")
        rooms.join_room(create_result["room_code"], "Player2")

        # Save scores
        rooms.save_room_score(create_result["room_code"], "Host", 100, 5, 3)
        rooms.save_room_score(create_result["room_code"], "Player1", 200, 8, 5)
        rooms.save_room_score(create_result["room_code"], "Player2", 150, 6, 4)

        players = rooms.get_room_players(create_result["room_code"])
        assert players[0]["player_name"] == "Player1"  # 200
        assert players[1]["player_name"] == "Player2"  # 150
        assert players[2]["player_name"] == "Host"      # 100


class TestSaveRoomScore:
    """Tests for save_room_score function."""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up a temporary database for each test."""
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix='.db')
        self.original_db_path = rooms.DATABASE_PATH
        rooms.DATABASE_PATH = self.temp_path
        rooms.init_rooms_db()

        yield

        rooms.DATABASE_PATH = self.original_db_path
        os.close(self.temp_fd)
        os.unlink(self.temp_path)

    def test_returns_dict(self):
        """Should return a dictionary."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        result = rooms.save_room_score(
            create_result["room_code"],
            "Host",
            100,
            5,
            3
        )
        assert isinstance(result, dict)

    def test_nonexistent_room_returns_error(self):
        """Should return error for non-existent room."""
        result = rooms.save_room_score("NOTEXIST", "Player", 100, 5, 3)
        assert result["success"] is False
        assert "error" in result

    def test_save_success(self):
        """Should successfully save score."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        result = rooms.save_room_score(
            create_result["room_code"],
            "Host",
            150,
            7,
            4
        )
        assert result["success"] is True

    def test_updates_player_score(self):
        """Should update player's score."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        rooms.save_room_score(
            create_result["room_code"],
            "Host",
            150,
            7,
            4
        )

        players = rooms.get_room_players(create_result["room_code"])
        host = [p for p in players if p["player_name"] == "Host"][0]

        assert host["score"] == 150
        assert host["correct_count"] == 7
        assert host["best_streak"] == 4
        assert host["completed"] is True

    def test_returns_rank(self):
        """Should return player's rank."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        rooms.join_room(create_result["room_code"], "Player1")

        rooms.save_room_score(create_result["room_code"], "Host", 200, 8, 5)
        result = rooms.save_room_score(
            create_result["room_code"],
            "Player1",
            150,
            6,
            3
        )

        assert result["rank"] == 2  # Second place

    def test_returns_players_list(self):
        """Should return updated players list."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        result = rooms.save_room_score(
            create_result["room_code"],
            "Host",
            100,
            5,
            3
        )

        assert "players" in result
        assert len(result["players"]) == 1


class TestCleanupExpiredRooms:
    """Tests for cleanup_expired_rooms function."""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up a temporary database for each test."""
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix='.db')
        self.original_db_path = rooms.DATABASE_PATH
        rooms.DATABASE_PATH = self.temp_path
        rooms.init_rooms_db()

        yield

        rooms.DATABASE_PATH = self.original_db_path
        os.close(self.temp_fd)
        os.unlink(self.temp_path)

    def test_returns_count(self):
        """Should return number of rooms cleaned up."""
        result = rooms.cleanup_expired_rooms()
        assert isinstance(result, int)

    def test_no_expired_rooms(self):
        """Should return 0 when no expired rooms."""
        rooms.create_room("Host", [1, 2, 3])
        result = rooms.cleanup_expired_rooms()
        assert result == 0

    def test_removes_expired_rooms(self):
        """Should remove expired rooms."""
        create_result = rooms.create_room("Host", [1, 2, 3])

        # Manually expire the room
        conn = rooms._get_connection()
        cursor = conn.cursor()
        past_time = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "UPDATE rooms SET expires_at = ? WHERE room_code = ?",
            (past_time, create_result["room_code"])
        )
        conn.commit()
        conn.close()

        result = rooms.cleanup_expired_rooms()
        assert result == 1

    def test_removes_players_of_expired_rooms(self):
        """Should remove players when room is cleaned up."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        rooms.join_room(create_result["room_code"], "Player1")

        # Manually expire the room
        conn = rooms._get_connection()
        cursor = conn.cursor()
        past_time = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "UPDATE rooms SET expires_at = ? WHERE room_code = ?",
            (past_time, create_result["room_code"])
        )
        conn.commit()

        # Verify players exist before cleanup
        cursor.execute("SELECT COUNT(*) FROM room_players")
        count_before = cursor.fetchone()[0]
        assert count_before == 2
        conn.close()

        rooms.cleanup_expired_rooms()

        # Verify players removed
        conn = rooms._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM room_players")
        count_after = cursor.fetchone()[0]
        assert count_after == 0
        conn.close()

    def test_keeps_active_rooms(self):
        """Should not remove active rooms."""
        create_result = rooms.create_room("Host", [1, 2, 3])
        rooms.cleanup_expired_rooms()

        # Room should still exist
        room = rooms.get_room(create_result["room_code"])
        assert room is not None


class TestRoomsIntegration:
    """Integration tests for rooms functionality."""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up a temporary database for each test."""
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix='.db')
        self.original_db_path = rooms.DATABASE_PATH
        rooms.DATABASE_PATH = self.temp_path
        rooms.init_rooms_db()

        yield

        rooms.DATABASE_PATH = self.original_db_path
        os.close(self.temp_fd)
        os.unlink(self.temp_path)

    def test_full_game_workflow(self):
        """Test complete room game workflow."""
        # Host creates room
        create_result = rooms.create_room(
            "Host",
            [1, 2, 3, 4, 5],
            categories="history",
            difficulty="progressive"
        )
        room_code = create_result["room_code"]

        # Players join
        rooms.join_room(room_code, "Player1")
        rooms.join_room(room_code, "Player2")

        # Verify all players in room
        players = rooms.get_room_players(room_code)
        assert len(players) == 3

        # All players complete game
        rooms.save_room_score(room_code, "Host", 150, 6, 4)
        rooms.save_room_score(room_code, "Player1", 200, 8, 5)
        rooms.save_room_score(room_code, "Player2", 175, 7, 3)

        # Check final standings
        players = rooms.get_room_players(room_code)
        assert players[0]["player_name"] == "Player1"  # Winner
        assert players[0]["score"] == 200
        assert all(p["completed"] for p in players)

    def test_multiple_rooms(self):
        """Multiple rooms should work independently."""
        room1 = rooms.create_room("Host1", [1, 2, 3])
        room2 = rooms.create_room("Host2", [4, 5, 6])

        rooms.join_room(room1["room_code"], "Player1")
        rooms.join_room(room2["room_code"], "Player2")

        players1 = rooms.get_room_players(room1["room_code"])
        players2 = rooms.get_room_players(room2["room_code"])

        assert len(players1) == 2
        assert len(players2) == 2
        assert "Player1" in [p["player_name"] for p in players1]
        assert "Player2" in [p["player_name"] for p in players2]
