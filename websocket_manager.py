"""
WebSocket Manager for BrainRace Real-Time Multiplayer.

This module handles live, synchronized multiplayer games where all players
answer questions simultaneously with a shared timer. Key features:
- Real-time room creation and player connections
- Synchronized question display with countdown timers
- Live score updates as players submit answers
- Streak tracking and bonus calculations
- Automatic cleanup when players disconnect

This is distinct from the async multiplayer in the rooms module, which
allows players to complete the quiz at different times.

Architecture:
- WebSocketManager: Singleton managing all active rooms
- RealTimeRoom: State container for a live game session
- Player: Individual player connection and score state

The manager handles the game lifecycle:
1. Room creation (host connects with "create" room code)
2. Players join (connect with room code)
3. Host starts game (countdown, then questions)
4. Questions cycle with timer (all answer same question)
5. Game ends, final standings displayed
"""

import json
import asyncio
import random
import string
from typing import Optional, Any
from dataclasses import dataclass, field
from fastapi import WebSocket


@dataclass
class Player:
    """
    Represents a player in a real-time multiplayer game.

    Tracks the player's WebSocket connection and game state including
    score, streaks, and current answer for the active question.

    Attributes:
        name: Display name of the player.
        websocket: The WebSocket connection for real-time communication.
        score: Cumulative points earned in this game.
        correct_count: Number of questions answered correctly.
        streak: Current consecutive correct answers.
        best_streak: Highest streak achieved in this game.
        current_answer: Index of answer submitted for current question (None if not answered).
        answered: Whether the player has answered the current question.
    """
    name: str
    websocket: WebSocket
    score: int = 0
    correct_count: int = 0
    streak: int = 0
    best_streak: int = 0
    current_answer: Optional[int] = None
    answered: bool = False


@dataclass
class RealTimeRoom:
    """
    Represents a real-time multiplayer game room.

    Contains all state for a synchronized game session including
    players, questions, and game progress.

    Attributes:
        code: Unique 5-character room code for joining.
        host_name: Name of the player who created the room (controls game start).
        players: Dictionary mapping player names to Player objects.
        questions: List of question dictionaries for this game.
        question_ids: List of question IDs (for answer checking via main module).
        current_question_index: Index of the current/next question.
        status: Game state - 'waiting', 'countdown', 'playing', 'showing_answer', 'finished'.
        categories: Category filter string used when creating the room.
        difficulty: Difficulty mode used when creating the room.
        countdown_task: Asyncio task for the current question timer (can be cancelled).
    """
    code: str
    host_name: str
    players: dict[str, Player] = field(default_factory=dict)
    questions: list[dict[str, Any]] = field(default_factory=list)
    question_ids: list[int] = field(default_factory=list)
    current_question_index: int = 0
    status: str = "waiting"  # waiting, countdown, playing, showing_answer, finished
    categories: str = ""
    difficulty: str = "progressive"
    countdown_task: Optional[asyncio.Task[None]] = None


class WebSocketManager:
    """
    Manages WebSocket connections and real-time game rooms.

    This is the central coordinator for all real-time multiplayer games.
    It maintains active rooms and player connections, handling the full
    game lifecycle from room creation through game completion.

    A single global instance ('manager') is created at module load and
    used by the main application's WebSocket endpoint.

    Attributes:
        rooms: Dictionary mapping room codes to RealTimeRoom objects.
        player_rooms: Dictionary mapping player names to their current room code.
    """

    def __init__(self) -> None:
        """Initialize an empty WebSocket manager."""
        self.rooms: dict[str, RealTimeRoom] = {}
        self.player_rooms: dict[str, str] = {}  # player_name -> room_code

    def _generate_code(self, length: int = 5) -> str:
        """
        Generate a unique alphanumeric room code.

        Keeps generating codes until finding one not already in use.

        Args:
            length: Number of characters in the code (default 5).

        Returns:
            A unique room code string.
        """
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choice(chars) for _ in range(length))
            if code not in self.rooms:
                return code

    async def create_room(
        self,
        host_name: str,
        websocket: WebSocket,
        questions: list[dict[str, Any]],
        question_ids: list[int],
        categories: str = "",
        difficulty: str = "progressive"
    ) -> RealTimeRoom:
        """
        Create a new real-time multiplayer room.

        The host is automatically added as the first player in the room.
        The room starts in 'waiting' status until the host starts the game.

        Args:
            host_name: Display name of the room creator.
            websocket: The host's WebSocket connection.
            questions: List of question dictionaries for the game.
            question_ids: Corresponding question IDs for answer validation.
            categories: Category filter string (for display purposes).
            difficulty: Difficulty mode string (for display purposes).

        Returns:
            The newly created RealTimeRoom object.
        """
        code = self._generate_code()
        room = RealTimeRoom(
            code=code,
            host_name=host_name,
            questions=questions,
            question_ids=question_ids,
            categories=categories,
            difficulty=difficulty
        )
        room.players[host_name] = Player(name=host_name, websocket=websocket)
        self.rooms[code] = room
        self.player_rooms[host_name] = code
        return room

    async def join_room(
        self,
        room_code: str,
        player_name: str,
        websocket: WebSocket
    ) -> Optional[RealTimeRoom]:
        """
        Join an existing real-time room.

        Players can only join rooms that are in 'waiting' status
        (before the game has started). If a player with the same name
        was previously in the room (disconnected), their connection
        is updated rather than creating a duplicate.

        Args:
            room_code: The room code to join (case-insensitive).
            player_name: Display name of the joining player.
            websocket: The player's WebSocket connection.

        Returns:
            The RealTimeRoom if successfully joined,
            or None if room not found or game already started.
        """
        room = self.rooms.get(room_code.upper())
        if not room:
            return None

        if room.status != "waiting":
            return None  # Can't join a game in progress

        if player_name in room.players:
            # Reconnect existing player
            room.players[player_name].websocket = websocket
        else:
            room.players[player_name] = Player(name=player_name, websocket=websocket)

        self.player_rooms[player_name] = room_code
        return room

    async def leave_room(self, player_name: str) -> None:
        """
        Remove a player from their room and clean up if necessary.

        Handles player disconnection by:
        - Removing them from the room's player list
        - If the host leaves, closing the entire room
        - If the room becomes empty, deleting it
        - Notifying remaining players of the departure

        Args:
            player_name: The name of the player who disconnected.
        """
        room_code = self.player_rooms.get(player_name)
        if not room_code:
            return

        room = self.rooms.get(room_code)
        if room and player_name in room.players:
            del room.players[player_name]
            del self.player_rooms[player_name]

            # If room is empty or host left, delete room
            if not room.players or player_name == room.host_name:
                if room.countdown_task:
                    room.countdown_task.cancel()
                del self.rooms[room_code]
                # Notify remaining players
                await self.broadcast_to_room(room_code, {
                    "type": "room_closed",
                    "reason": "Host left the game"
                })
            else:
                # Notify others that player left
                await self.broadcast_to_room(room_code, {
                    "type": "player_left",
                    "player": player_name,
                    "players": self._get_player_list(room)
                })

    def get_room(self, room_code: str) -> Optional[RealTimeRoom]:
        """
        Look up a room by its code.

        Args:
            room_code: The room code (case-insensitive).

        Returns:
            The RealTimeRoom if found, or None if not exists.
        """
        return self.rooms.get(room_code.upper())

    def _get_player_list(self, room: RealTimeRoom) -> list[dict[str, Any]]:
        """
        Generate a player list for broadcasting to clients.

        Args:
            room: The room to get players from.

        Returns:
            A list of player info dictionaries containing:
            - name: Player's display name
            - score: Current score
            - correct_count: Number of correct answers
            - streak: Current answer streak
            - answered: Whether they've answered the current question
            - is_host: Whether this player is the room host
        """
        return [
            {
                "name": p.name,
                "score": p.score,
                "correct_count": p.correct_count,
                "streak": p.streak,
                "answered": p.answered,
                "is_host": p.name == room.host_name
            }
            for p in room.players.values()
        ]

    async def broadcast_to_room(self, room_code: str, message: dict[str, Any]) -> None:
        """
        Send a JSON message to all players in a room.

        Handles connection errors gracefully by removing disconnected
        players from the room.

        Args:
            room_code: The room code to broadcast to.
            message: Dictionary to send as JSON to all players.
        """
        room = self.rooms.get(room_code)
        if not room:
            return

        disconnected = []
        for player_name, player in room.players.items():
            try:
                await player.websocket.send_json(message)
            except Exception:
                disconnected.append(player_name)

        # Clean up disconnected players
        for name in disconnected:
            await self.leave_room(name)

    async def send_to_player(
        self,
        room_code: str,
        player_name: str,
        message: dict[str, Any]
    ) -> None:
        """
        Send a JSON message to a specific player.

        Handles connection errors by removing disconnected players.

        Args:
            room_code: The room containing the player.
            player_name: The name of the player to message.
            message: Dictionary to send as JSON.
        """
        room = self.rooms.get(room_code)
        if not room or player_name not in room.players:
            return

        try:
            await room.players[player_name].websocket.send_json(message)
        except Exception:
            await self.leave_room(player_name)

    async def start_game(self, room_code: str) -> None:
        """
        Start a game with a countdown sequence.

        Can only be called when room is in 'waiting' status. This method:
        1. Resets all player scores to 0
        2. Broadcasts a 3-2-1 countdown
        3. Transitions to 'playing' status
        4. Sends the first question

        Args:
            room_code: The room code to start.
        """
        room = self.rooms.get(room_code)
        if not room or room.status != "waiting":
            return

        room.status = "countdown"
        room.current_question_index = 0

        # Reset all player scores
        for player in room.players.values():
            player.score = 0
            player.correct_count = 0
            player.streak = 0
            player.best_streak = 0

        # Countdown
        for i in range(3, 0, -1):
            await self.broadcast_to_room(room_code, {
                "type": "countdown",
                "count": i
            })
            await asyncio.sleep(1)

        await self.broadcast_to_room(room_code, {
            "type": "game_start",
            "total_questions": len(room.questions)
        })

        room.status = "playing"
        await self.send_question(room_code)

    async def send_question(self, room_code: str) -> None:
        """
        Send the current question to all players and start the timer.

        Resets all players' answered status before sending. If there are
        no more questions, ends the game instead.

        The question message includes:
        - Question number and total
        - Question text and choices
        - Category and difficulty
        - Time limit (15 seconds)

        Args:
            room_code: The room to send the question to.
        """
        room = self.rooms.get(room_code)
        if not room or room.status != "playing":
            return

        if room.current_question_index >= len(room.questions):
            await self.end_game(room_code)
            return

        # Reset answered status for all players
        for player in room.players.values():
            player.answered = False
            player.current_answer = None

        question = room.questions[room.current_question_index]
        question_id = room.question_ids[room.current_question_index]

        await self.broadcast_to_room(room_code, {
            "type": "question",
            "question_number": room.current_question_index + 1,
            "total_questions": len(room.questions),
            "question_id": question_id,
            "question": question["question"],
            "choices": question["options"],
            "category": question["category"],
            "difficulty": question["difficulty"],
            "time_limit": 15  # 15 seconds per question
        })

        # Start answer timer
        room.countdown_task = asyncio.create_task(
            self._question_timer(room_code, 15)
        )

    async def _question_timer(self, room_code: str, seconds: int) -> None:
        """
        Run the countdown timer for a question.

        Broadcasts remaining time each second. Ends early if all players
        have answered. When time expires (or all answered), triggers
        showing the answer.

        Args:
            room_code: The room running the timer.
            seconds: Number of seconds for the countdown.
        """
        room = self.rooms.get(room_code)
        if not room:
            return

        for remaining in range(seconds, 0, -1):
            await asyncio.sleep(1)

            # Check if all players have answered
            if all(p.answered for p in room.players.values()):
                break

            # Broadcast time remaining
            await self.broadcast_to_room(room_code, {
                "type": "timer",
                "remaining": remaining - 1
            })

        # Time's up - show answer
        await self.show_answer(room_code)

    async def submit_answer(self, room_code: str, player_name: str, answer: int) -> None:
        """
        Record a player's answer for the current question.

        Only accepts answers during 'playing' status and if the player
        hasn't already answered. Notifies all players when someone answers.
        If all players have now answered, cancels the timer and shows results.

        Args:
            room_code: The room the player is in.
            player_name: The name of the player submitting.
            answer: The index (0-3) of the chosen answer.
        """
        room = self.rooms.get(room_code)
        if not room or room.status != "playing":
            return

        player = room.players.get(player_name)
        if not player or player.answered:
            return

        player.answered = True
        player.current_answer = answer

        # Notify all players that this player answered
        await self.broadcast_to_room(room_code, {
            "type": "player_answered",
            "player": player_name,
            "players": self._get_player_list(room)
        })

        # Check if all players have answered
        if all(p.answered for p in room.players.values()):
            if room.countdown_task:
                room.countdown_task.cancel()
            await self.show_answer(room_code)

    async def show_answer(self, room_code: str) -> None:
        """
        Reveal the correct answer and update all player scores.

        Calculates points for each player based on:
        - Whether they answered correctly
        - The question difficulty (easy: 10, medium: 20, hard: 30)
        - Streak bonus (up to +10 for consecutive correct answers)

        Broadcasts detailed results including who got it right/wrong
        and updated standings. After a 4-second delay, advances to
        the next question.

        Args:
            room_code: The room to show results for.
        """
        room = self.rooms.get(room_code)
        if not room:
            return

        room.status = "showing_answer"
        question = room.questions[room.current_question_index]
        correct_answer = question["correct_answer"]

        # Calculate points based on difficulty
        points_map = {"easy": 10, "medium": 20, "hard": 30}
        base_points = points_map.get(question["difficulty"], 10)

        # Update scores
        results = []
        for player in room.players.values():
            is_correct = player.current_answer == correct_answer
            points_earned = 0

            if is_correct:
                player.correct_count += 1
                player.streak += 1
                if player.streak > player.best_streak:
                    player.best_streak = player.streak
                # Bonus for streak
                streak_bonus = min(player.streak - 1, 5) * 2
                points_earned = base_points + streak_bonus
                player.score += points_earned
            else:
                player.streak = 0

            results.append({
                "name": player.name,
                "answer": player.current_answer,
                "correct": is_correct,
                "points_earned": points_earned,
                "score": player.score,
                "streak": player.streak
            })

        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)

        await self.broadcast_to_room(room_code, {
            "type": "answer_result",
            "correct_answer": correct_answer,
            "explanation": question["explanation"],
            "results": results,
            "standings": self._get_player_list(room)
        })

        # Wait before next question
        await asyncio.sleep(4)

        room.current_question_index += 1
        room.status = "playing"
        await self.send_question(room_code)

    async def end_game(self, room_code: str) -> None:
        """
        End the game and broadcast final results.

        Sets the room status to 'finished' and sends the final standings
        sorted by score. The room is automatically deleted after 60 seconds.

        Args:
            room_code: The room to end.
        """
        room = self.rooms.get(room_code)
        if not room:
            return

        room.status = "finished"

        # Sort players by score
        final_standings = sorted(
            [
                {
                    "name": p.name,
                    "score": p.score,
                    "correct_count": p.correct_count,
                    "best_streak": p.best_streak
                }
                for p in room.players.values()
            ],
            key=lambda x: x["score"],
            reverse=True
        )

        await self.broadcast_to_room(room_code, {
            "type": "game_over",
            "standings": final_standings,
            "total_questions": len(room.questions)
        })

        # Clean up room after a delay
        await asyncio.sleep(60)
        if room_code in self.rooms:
            del self.rooms[room_code]


# Global manager instance
manager = WebSocketManager()
