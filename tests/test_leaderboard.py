"""Tests for leaderboard module."""

import pytest
import sqlite3
import os
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import leaderboard


class TestLeaderboardDatabase:
    """Tests for leaderboard database initialization and connection."""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up a temporary database for each test."""
        # Create a temporary database file
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix='.db')
        self.original_db_path = leaderboard.DATABASE_PATH
        leaderboard.DATABASE_PATH = self.temp_path

        # Initialize the database
        leaderboard.init_db()

        yield

        # Restore original path and clean up
        leaderboard.DATABASE_PATH = self.original_db_path
        os.close(self.temp_fd)
        os.unlink(self.temp_path)

    def test_init_db_creates_table(self):
        """Should create high_scores table on initialization."""
        conn = sqlite3.connect(self.temp_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='high_scores'"
        )
        result = cursor.fetchone()
        conn.close()
        assert result is not None
        assert result[0] == 'high_scores'

    def test_init_db_idempotent(self):
        """Calling init_db multiple times should not cause errors."""
        # Should not raise any exceptions
        leaderboard.init_db()
        leaderboard.init_db()

    def test_get_connection_returns_connection(self):
        """Should return a valid database connection."""
        conn = leaderboard._get_connection()
        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_get_connection_has_row_factory(self):
        """Connection should have row factory for dict-like access."""
        conn = leaderboard._get_connection()
        assert conn.row_factory == sqlite3.Row
        conn.close()


class TestSaveScore:
    """Tests for save_score function."""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up a temporary database for each test."""
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix='.db')
        self.original_db_path = leaderboard.DATABASE_PATH
        leaderboard.DATABASE_PATH = self.temp_path
        leaderboard.init_db()

        yield

        leaderboard.DATABASE_PATH = self.original_db_path
        os.close(self.temp_fd)
        os.unlink(self.temp_path)

    def test_save_score_returns_dict(self):
        """Should return a dictionary with result info."""
        result = leaderboard.save_score("TestPlayer", 100)
        assert isinstance(result, dict)

    def test_save_score_success_flag(self):
        """Should return success=True on successful save."""
        result = leaderboard.save_score("TestPlayer", 100)
        assert result["success"] is True

    def test_save_score_basic(self):
        """Should save a basic score successfully."""
        result = leaderboard.save_score("Alice", 150)
        assert result["success"] is True

        # Verify the score was saved
        scores = leaderboard.get_top_scores(10)
        assert len(scores) == 1
        assert scores[0]["player_name"] == "Alice"
        assert scores[0]["score"] == 150

    def test_save_score_with_category(self):
        """Should save score with category."""
        result = leaderboard.save_score(
            "Bob",
            200,
            category="ancient-civilizations"
        )
        assert result["success"] is True

        scores = leaderboard.get_top_scores(10)
        assert scores[0]["category"] == "ancient-civilizations"

    def test_save_score_with_difficulty(self):
        """Should save score with difficulty."""
        result = leaderboard.save_score(
            "Charlie",
            250,
            difficulty="hard"
        )
        assert result["success"] is True

        scores = leaderboard.get_top_scores(10)
        assert scores[0]["difficulty"] == "hard"

    def test_save_score_with_total_questions(self):
        """Should save score with total questions."""
        result = leaderboard.save_score(
            "Diana",
            300,
            total_questions=15
        )
        assert result["success"] is True

        scores = leaderboard.get_top_scores(10)
        assert scores[0]["total_questions"] == 15

    def test_save_score_with_all_fields(self):
        """Should save score with all optional fields."""
        result = leaderboard.save_score(
            player_name="Eve",
            score=350,
            category="world-wars",
            difficulty="medium",
            total_questions=20
        )
        assert result["success"] is True

        scores = leaderboard.get_top_scores(10)
        assert scores[0]["player_name"] == "Eve"
        assert scores[0]["score"] == 350
        assert scores[0]["category"] == "world-wars"
        assert scores[0]["difficulty"] == "medium"
        assert scores[0]["total_questions"] == 20

    def test_save_score_made_leaderboard_top_score(self):
        """First score should make the leaderboard."""
        result = leaderboard.save_score("Frank", 100)
        assert result["made_leaderboard"] is True
        assert result["rank"] == 1

    def test_save_score_rank_calculation(self):
        """Should calculate correct rank for new scores."""
        leaderboard.save_score("Player1", 100)
        leaderboard.save_score("Player2", 200)
        result = leaderboard.save_score("Player3", 150)

        # Should be rank 2 (between 200 and 100)
        assert result["made_leaderboard"] is True
        assert result["rank"] == 2

    def test_save_score_not_in_top_10(self):
        """Score not in top 10 should not make leaderboard."""
        # Add 10 high scores
        for i in range(10):
            leaderboard.save_score(f"HighPlayer{i}", 1000 - i * 10)

        # Add a low score
        result = leaderboard.save_score("LowPlayer", 50)
        assert result["made_leaderboard"] is False
        assert result["rank"] is None


class TestGetTopScores:
    """Tests for get_top_scores function."""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up a temporary database for each test."""
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix='.db')
        self.original_db_path = leaderboard.DATABASE_PATH
        leaderboard.DATABASE_PATH = self.temp_path
        leaderboard.init_db()

        yield

        leaderboard.DATABASE_PATH = self.original_db_path
        os.close(self.temp_fd)
        os.unlink(self.temp_path)

    def test_get_top_scores_returns_list(self):
        """Should return a list."""
        result = leaderboard.get_top_scores()
        assert isinstance(result, list)

    def test_get_top_scores_empty_db(self):
        """Should return empty list when no scores."""
        result = leaderboard.get_top_scores()
        assert result == []

    def test_get_top_scores_single_score(self):
        """Should return single score when only one exists."""
        leaderboard.save_score("Solo", 100)
        result = leaderboard.get_top_scores()
        assert len(result) == 1
        assert result[0]["player_name"] == "Solo"

    def test_get_top_scores_ordered_by_score_desc(self):
        """Should return scores ordered by score descending."""
        leaderboard.save_score("Low", 50)
        leaderboard.save_score("High", 200)
        leaderboard.save_score("Mid", 100)

        result = leaderboard.get_top_scores()
        assert result[0]["score"] == 200
        assert result[1]["score"] == 100
        assert result[2]["score"] == 50

    def test_get_top_scores_limit_default(self):
        """Default limit should be 10."""
        for i in range(15):
            leaderboard.save_score(f"Player{i}", 100 + i)

        result = leaderboard.get_top_scores()
        assert len(result) == 10

    def test_get_top_scores_custom_limit(self):
        """Should respect custom limit."""
        for i in range(10):
            leaderboard.save_score(f"Player{i}", 100 + i)

        result = leaderboard.get_top_scores(limit=5)
        assert len(result) == 5

    def test_get_top_scores_rank_field(self):
        """Should include correct rank for each score."""
        leaderboard.save_score("Third", 100)
        leaderboard.save_score("First", 300)
        leaderboard.save_score("Second", 200)

        result = leaderboard.get_top_scores()
        assert result[0]["rank"] == 1
        assert result[0]["player_name"] == "First"
        assert result[1]["rank"] == 2
        assert result[1]["player_name"] == "Second"
        assert result[2]["rank"] == 3
        assert result[2]["player_name"] == "Third"

    def test_get_top_scores_date_format(self):
        """Date should be formatted as YYYY-MM-DD."""
        leaderboard.save_score("DateTest", 100)
        result = leaderboard.get_top_scores()

        # Date should match pattern YYYY-MM-DD
        date_str = result[0]["date"]
        assert len(date_str) == 10
        assert date_str[4] == '-'
        assert date_str[7] == '-'

    def test_get_top_scores_structure(self):
        """Each score should have expected fields."""
        leaderboard.save_score(
            "Complete",
            100,
            category="test",
            difficulty="easy",
            total_questions=10
        )
        result = leaderboard.get_top_scores()

        score = result[0]
        assert "rank" in score
        assert "player_name" in score
        assert "score" in score
        assert "date" in score
        assert "category" in score
        assert "difficulty" in score
        assert "total_questions" in score


class TestGetPlayerBest:
    """Tests for get_player_best function."""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up a temporary database for each test."""
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix='.db')
        self.original_db_path = leaderboard.DATABASE_PATH
        leaderboard.DATABASE_PATH = self.temp_path
        leaderboard.init_db()

        yield

        leaderboard.DATABASE_PATH = self.original_db_path
        os.close(self.temp_fd)
        os.unlink(self.temp_path)

    def test_get_player_best_not_found(self):
        """Should return None for non-existent player."""
        result = leaderboard.get_player_best("NonExistent")
        assert result is None

    def test_get_player_best_single_score(self):
        """Should return player's only score."""
        leaderboard.save_score("OnlyScore", 150)
        result = leaderboard.get_player_best("OnlyScore")

        assert result is not None
        assert result["player_name"] == "OnlyScore"
        assert result["score"] == 150

    def test_get_player_best_highest_score(self):
        """Should return player's highest score when multiple exist."""
        leaderboard.save_score("MultiScore", 100)
        leaderboard.save_score("MultiScore", 300)
        leaderboard.save_score("MultiScore", 200)

        result = leaderboard.get_player_best("MultiScore")
        assert result["score"] == 300

    def test_get_player_best_case_sensitive(self):
        """Player name lookup should be case-sensitive."""
        leaderboard.save_score("CaseSensitive", 100)

        result = leaderboard.get_player_best("casesensitive")
        assert result is None

    def test_get_player_best_with_metadata(self):
        """Should include category and difficulty."""
        leaderboard.save_score(
            "MetaPlayer",
            100,
            category="science",
            difficulty="hard"
        )

        result = leaderboard.get_player_best("MetaPlayer")
        assert result["category"] == "science"
        assert result["difficulty"] == "hard"


class TestLeaderboardIntegration:
    """Integration tests for leaderboard functionality."""

    @pytest.fixture(autouse=True)
    def setup_test_db(self):
        """Set up a temporary database for each test."""
        self.temp_fd, self.temp_path = tempfile.mkstemp(suffix='.db')
        self.original_db_path = leaderboard.DATABASE_PATH
        leaderboard.DATABASE_PATH = self.temp_path
        leaderboard.init_db()

        yield

        leaderboard.DATABASE_PATH = self.original_db_path
        os.close(self.temp_fd)
        os.unlink(self.temp_path)

    def test_full_workflow(self):
        """Test complete save and retrieve workflow."""
        # Multiple players save scores
        leaderboard.save_score("Alice", 150, category="history", difficulty="easy")
        leaderboard.save_score("Bob", 200, category="science", difficulty="medium")
        leaderboard.save_score("Alice", 180, category="history", difficulty="hard")
        leaderboard.save_score("Charlie", 175, category="history", difficulty="medium")

        # Get leaderboard
        top_scores = leaderboard.get_top_scores(10)
        assert len(top_scores) == 4
        assert top_scores[0]["player_name"] == "Bob"
        assert top_scores[0]["rank"] == 1

        # Get Alice's best
        alice_best = leaderboard.get_player_best("Alice")
        assert alice_best["score"] == 180

    def test_many_scores_performance(self):
        """Should handle many scores efficiently."""
        # Add 100 scores
        for i in range(100):
            leaderboard.save_score(f"Player{i}", i * 10)

        # Should only return top 10
        result = leaderboard.get_top_scores()
        assert len(result) == 10
        assert result[0]["score"] == 990  # Highest score

    def test_tie_scores(self):
        """Should handle tied scores correctly."""
        leaderboard.save_score("TiePlayer1", 100)
        leaderboard.save_score("TiePlayer2", 100)
        leaderboard.save_score("TiePlayer3", 100)

        result = leaderboard.get_top_scores()
        assert len(result) == 3
        # All should have score 100, ranks 1, 2, 3
        scores = [s["score"] for s in result]
        assert scores == [100, 100, 100]
