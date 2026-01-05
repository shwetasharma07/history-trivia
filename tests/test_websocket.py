"""Tests for websocket_manager module."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from websocket_manager import (
    WebSocketManager,
    Player,
    RealTimeRoom,
    manager as global_manager
)


class TestPlayer:
    """Tests for Player dataclass."""

    def test_player_creation(self):
        """Should create a Player with required fields."""
        mock_ws = MagicMock()
        player = Player(name="TestPlayer", websocket=mock_ws)

        assert player.name == "TestPlayer"
        assert player.websocket == mock_ws

    def test_player_default_values(self):
        """Player should have correct default values."""
        mock_ws = MagicMock()
        player = Player(name="TestPlayer", websocket=mock_ws)

        assert player.score == 0
        assert player.correct_count == 0
        assert player.streak == 0
        assert player.best_streak == 0
        assert player.current_answer is None
        assert player.answered is False


class TestRealTimeRoom:
    """Tests for RealTimeRoom dataclass."""

    def test_room_creation(self):
        """Should create a RealTimeRoom with required fields."""
        room = RealTimeRoom(code="ABC123", host_name="Host")

        assert room.code == "ABC123"
        assert room.host_name == "Host"

    def test_room_default_values(self):
        """Room should have correct default values."""
        room = RealTimeRoom(code="ABC123", host_name="Host")

        assert room.players == {}
        assert room.questions == []
        assert room.question_ids == []
        assert room.current_question_index == 0
        assert room.status == "waiting"
        assert room.categories == ""
        assert room.difficulty == "progressive"
        assert room.countdown_task is None


class TestWebSocketManagerInit:
    """Tests for WebSocketManager initialization."""

    def test_manager_initialization(self):
        """Manager should initialize with empty rooms."""
        manager = WebSocketManager()
        assert manager.rooms == {}
        assert manager.player_rooms == {}

    def test_global_manager_exists(self):
        """Global manager instance should exist."""
        assert global_manager is not None
        assert isinstance(global_manager, WebSocketManager)


class TestGenerateCode:
    """Tests for room code generation."""

    def test_generates_string(self):
        """Should generate a string code."""
        manager = WebSocketManager()
        code = manager._generate_code()
        assert isinstance(code, str)

    def test_default_length_is_five(self):
        """Default code length should be 5."""
        manager = WebSocketManager()
        code = manager._generate_code()
        assert len(code) == 5

    def test_custom_length(self):
        """Should respect custom length."""
        manager = WebSocketManager()
        code = manager._generate_code(length=8)
        assert len(code) == 8

    def test_uppercase_and_digits(self):
        """Code should be uppercase letters and digits."""
        manager = WebSocketManager()
        code = manager._generate_code()
        for char in code:
            assert char.isupper() or char.isdigit()

    def test_unique_codes(self):
        """Should not generate duplicate codes."""
        manager = WebSocketManager()
        # Pre-populate some codes
        manager.rooms["AAAAA"] = MagicMock()
        manager.rooms["BBBBB"] = MagicMock()

        # Generate new code - should not be one of existing
        code = manager._generate_code()
        assert code not in ["AAAAA", "BBBBB"]


class TestCreateRoom:
    """Tests for create_room method."""

    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return WebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_creates_room(self, manager, mock_websocket):
        """Should create a new room."""
        room = await manager.create_room(
            host_name="TestHost",
            websocket=mock_websocket,
            questions=[{"question": "Q1"}],
            question_ids=[1]
        )

        assert room is not None
        assert room.host_name == "TestHost"
        assert room.code in manager.rooms

    @pytest.mark.asyncio
    async def test_adds_host_as_player(self, manager, mock_websocket):
        """Host should be added as first player."""
        room = await manager.create_room(
            host_name="TestHost",
            websocket=mock_websocket,
            questions=[],
            question_ids=[]
        )

        assert "TestHost" in room.players
        assert room.players["TestHost"].name == "TestHost"

    @pytest.mark.asyncio
    async def test_stores_questions(self, manager, mock_websocket):
        """Should store questions and IDs."""
        questions = [{"question": "Q1"}, {"question": "Q2"}]
        question_ids = [10, 20]

        room = await manager.create_room(
            host_name="TestHost",
            websocket=mock_websocket,
            questions=questions,
            question_ids=question_ids
        )

        assert room.questions == questions
        assert room.question_ids == question_ids

    @pytest.mark.asyncio
    async def test_stores_settings(self, manager, mock_websocket):
        """Should store categories and difficulty."""
        room = await manager.create_room(
            host_name="TestHost",
            websocket=mock_websocket,
            questions=[],
            question_ids=[],
            categories="history,science",
            difficulty="hard"
        )

        assert room.categories == "history,science"
        assert room.difficulty == "hard"

    @pytest.mark.asyncio
    async def test_tracks_player_room(self, manager, mock_websocket):
        """Should track which room player is in."""
        room = await manager.create_room(
            host_name="TestHost",
            websocket=mock_websocket,
            questions=[],
            question_ids=[]
        )

        assert manager.player_rooms["TestHost"] == room.code


class TestJoinRoom:
    """Tests for join_room method."""

    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return WebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_join_nonexistent_room(self, manager, mock_websocket):
        """Should return None for non-existent room."""
        result = await manager.join_room("NOTEXIST", "Player", mock_websocket)
        assert result is None

    @pytest.mark.asyncio
    async def test_join_existing_room(self, manager, mock_websocket):
        """Should successfully join existing room."""
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])

        result = await manager.join_room(room.code, "Player", mock_websocket)

        assert result is not None
        assert result.code == room.code
        assert "Player" in room.players

    @pytest.mark.asyncio
    async def test_cannot_join_started_game(self, manager, mock_websocket):
        """Should not allow joining a game in progress."""
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])
        room.status = "playing"

        result = await manager.join_room(room.code, "Player", mock_websocket)
        assert result is None

    @pytest.mark.asyncio
    async def test_case_insensitive_code(self, manager, mock_websocket):
        """Room code should be case-insensitive."""
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])

        result = await manager.join_room(room.code.lower(), "Player", mock_websocket)
        assert result is not None

    @pytest.mark.asyncio
    async def test_reconnect_existing_player(self, manager, mock_websocket):
        """Should allow reconnecting for existing player."""
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])

        # First join
        ws1 = AsyncMock()
        await manager.join_room(room.code, "Player", ws1)

        # Reconnect with new websocket
        ws2 = AsyncMock()
        result = await manager.join_room(room.code, "Player", ws2)

        assert result is not None
        assert room.players["Player"].websocket == ws2


class TestLeaveRoom:
    """Tests for leave_room method."""

    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_leave_removes_player(self):
        """Should remove player from room."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])

        player_ws = AsyncMock()
        await manager.join_room(room.code, "Player", player_ws)

        await manager.leave_room("Player")

        assert "Player" not in room.players
        assert "Player" not in manager.player_rooms

    @pytest.mark.asyncio
    async def test_leave_nonexistent_player(self):
        """Should handle non-existent player gracefully."""
        manager = WebSocketManager()
        # Should not raise
        await manager.leave_room("NonExistent")

    @pytest.mark.asyncio
    async def test_host_leaving_closes_room(self):
        """Room should close when host leaves."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])
        room_code = room.code

        await manager.leave_room("Host")

        assert room_code not in manager.rooms


class TestGetRoom:
    """Tests for get_room method."""

    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_get_existing_room(self):
        """Should return existing room."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])

        result = manager.get_room(room.code)
        assert result == room

    def test_get_nonexistent_room(self):
        """Should return None for non-existent room."""
        manager = WebSocketManager()
        result = manager.get_room("NOTEXIST")
        assert result is None

    @pytest.mark.asyncio
    async def test_case_insensitive_lookup(self):
        """Should be case-insensitive."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])

        result = manager.get_room(room.code.lower())
        assert result == room


class TestGetPlayerList:
    """Tests for _get_player_list method."""

    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_returns_list(self):
        """Should return a list."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])

        result = manager._get_player_list(room)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_includes_all_players(self):
        """Should include all players."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])

        player_ws = AsyncMock()
        await manager.join_room(room.code, "Player1", player_ws)

        result = manager._get_player_list(room)
        names = [p["name"] for p in result]

        assert "Host" in names
        assert "Player1" in names

    @pytest.mark.asyncio
    async def test_player_structure(self):
        """Each player should have expected fields."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])

        result = manager._get_player_list(room)
        player = result[0]

        assert "name" in player
        assert "score" in player
        assert "correct_count" in player
        assert "streak" in player
        assert "answered" in player
        assert "is_host" in player

    @pytest.mark.asyncio
    async def test_host_flag(self):
        """Host should have is_host=True."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])

        player_ws = AsyncMock()
        await manager.join_room(room.code, "Player", player_ws)

        result = manager._get_player_list(room)
        host_entry = [p for p in result if p["name"] == "Host"][0]
        player_entry = [p for p in result if p["name"] == "Player"][0]

        assert host_entry["is_host"] is True
        assert player_entry["is_host"] is False


class TestBroadcastToRoom:
    """Tests for broadcast_to_room method."""

    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_broadcasts_to_all_players(self):
        """Should send message to all players."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])

        player_ws = AsyncMock()
        await manager.join_room(room.code, "Player", player_ws)

        message = {"type": "test", "data": "hello"}
        await manager.broadcast_to_room(room.code, message)

        host_ws.send_json.assert_called_with(message)
        player_ws.send_json.assert_called_with(message)

    @pytest.mark.asyncio
    async def test_handles_nonexistent_room(self):
        """Should handle non-existent room gracefully."""
        manager = WebSocketManager()
        # Should not raise
        await manager.broadcast_to_room("NOTEXIST", {"type": "test"})

    @pytest.mark.asyncio
    async def test_handles_disconnected_player(self):
        """Should handle disconnected players gracefully."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])

        # Make the websocket throw an exception
        host_ws.send_json.side_effect = Exception("Connection closed")

        # Should not raise
        await manager.broadcast_to_room(room.code, {"type": "test"})


class TestSendToPlayer:
    """Tests for send_to_player method."""

    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_sends_to_specific_player(self):
        """Should send message to specific player only."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])

        player_ws = AsyncMock()
        await manager.join_room(room.code, "Player", player_ws)

        message = {"type": "private"}
        await manager.send_to_player(room.code, "Player", message)

        player_ws.send_json.assert_called_with(message)
        # Host should not receive
        assert host_ws.send_json.call_count == 0

    @pytest.mark.asyncio
    async def test_handles_nonexistent_player(self):
        """Should handle non-existent player gracefully."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])

        # Should not raise
        await manager.send_to_player(room.code, "NonExistent", {"type": "test"})


class TestSubmitAnswer:
    """Tests for submit_answer method."""

    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_records_answer(self):
        """Should record player's answer."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [{"question": "Q1"}], [1])
        room.status = "playing"

        await manager.submit_answer(room.code, "Host", 2)

        assert room.players["Host"].current_answer == 2
        assert room.players["Host"].answered is True

    @pytest.mark.asyncio
    async def test_ignores_if_not_playing(self):
        """Should ignore answer if game not in playing state."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])
        room.status = "waiting"

        await manager.submit_answer(room.code, "Host", 2)

        assert room.players["Host"].current_answer is None

    @pytest.mark.asyncio
    async def test_ignores_already_answered(self):
        """Should ignore if player already answered."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [{"question": "Q1"}], [1])
        room.status = "playing"

        await manager.submit_answer(room.code, "Host", 1)
        await manager.submit_answer(room.code, "Host", 2)

        # Should still be 1
        assert room.players["Host"].current_answer == 1


class TestStartGame:
    """Tests for start_game method."""

    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_changes_status_to_countdown(self):
        """Should change status during countdown."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [{"question": "Q"}], [1])

        # Start in background to avoid blocking
        with patch.object(manager, 'send_question', new_callable=AsyncMock):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                await manager.start_game(room.code)

    @pytest.mark.asyncio
    async def test_resets_player_scores(self):
        """Should reset all player scores."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])

        # Set some scores
        room.players["Host"].score = 100
        room.players["Host"].correct_count = 5

        with patch.object(manager, 'send_question', new_callable=AsyncMock):
            with patch('asyncio.sleep', new_callable=AsyncMock):
                await manager.start_game(room.code)

        assert room.players["Host"].score == 0
        assert room.players["Host"].correct_count == 0

    @pytest.mark.asyncio
    async def test_ignores_already_started(self):
        """Should ignore if game already started."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])
        room.status = "playing"

        # Should not change anything
        await manager.start_game(room.code)


class TestEndGame:
    """Tests for end_game method."""

    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_changes_status_to_finished(self):
        """Should set status to finished."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])

        with patch('asyncio.sleep', new_callable=AsyncMock):
            await manager.end_game(room.code)

        assert room.status == "finished"

    @pytest.mark.asyncio
    async def test_broadcasts_game_over(self):
        """Should broadcast game_over message."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        room = await manager.create_room("Host", host_ws, [], [])

        with patch('asyncio.sleep', new_callable=AsyncMock):
            await manager.end_game(room.code)

        # Find the game_over call
        calls = host_ws.send_json.call_args_list
        game_over_call = [c for c in calls if c[0][0].get("type") == "game_over"]
        assert len(game_over_call) > 0


class TestShowAnswer:
    """Tests for show_answer method."""

    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return WebSocketManager()

    @pytest.mark.asyncio
    async def test_calculates_scores(self):
        """Should update player scores correctly."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        questions = [{
            "question": "Q1",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 2,
            "explanation": "Explanation",
            "difficulty": "easy",
            "category": "test"
        }]
        room = await manager.create_room("Host", host_ws, questions, [1])
        room.status = "showing_answer"
        room.players["Host"].current_answer = 2  # Correct answer

        with patch('asyncio.sleep', new_callable=AsyncMock):
            with patch.object(manager, 'send_question', new_callable=AsyncMock):
                await manager.show_answer(room.code)

        # Score should be updated (10 for easy)
        assert room.players["Host"].score == 10
        assert room.players["Host"].correct_count == 1

    @pytest.mark.asyncio
    async def test_resets_streak_on_wrong(self):
        """Should reset streak on wrong answer."""
        manager = WebSocketManager()
        host_ws = AsyncMock()
        questions = [{
            "question": "Q1",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 2,
            "explanation": "Explanation",
            "difficulty": "easy",
            "category": "test"
        }]
        room = await manager.create_room("Host", host_ws, questions, [1])
        room.status = "showing_answer"
        room.players["Host"].streak = 3
        room.players["Host"].current_answer = 0  # Wrong answer

        with patch('asyncio.sleep', new_callable=AsyncMock):
            with patch.object(manager, 'send_question', new_callable=AsyncMock):
                await manager.show_answer(room.code)

        assert room.players["Host"].streak == 0
