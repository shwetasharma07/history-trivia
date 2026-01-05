"""
WebSocket Manager for BrainRace real-time multiplayer.

Handles real-time game rooms with synchronized gameplay.
"""

import json
import asyncio
import random
import string
from typing import Optional
from dataclasses import dataclass, field
from fastapi import WebSocket


@dataclass
class Player:
    """Represents a player in a real-time game."""
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
    """Represents a real-time multiplayer room."""
    code: str
    host_name: str
    players: dict[str, Player] = field(default_factory=dict)
    questions: list[dict] = field(default_factory=list)
    question_ids: list[int] = field(default_factory=list)
    current_question_index: int = 0
    status: str = "waiting"  # waiting, countdown, playing, showing_answer, finished
    categories: str = ""
    difficulty: str = "progressive"
    countdown_task: Optional[asyncio.Task] = None


class WebSocketManager:
    """Manages WebSocket connections and real-time game rooms."""

    def __init__(self):
        self.rooms: dict[str, RealTimeRoom] = {}
        self.player_rooms: dict[str, str] = {}  # player_name -> room_code

    def _generate_code(self, length: int = 5) -> str:
        """Generate a unique room code."""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choice(chars) for _ in range(length))
            if code not in self.rooms:
                return code

    async def create_room(
        self,
        host_name: str,
        websocket: WebSocket,
        questions: list[dict],
        question_ids: list[int],
        categories: str = "",
        difficulty: str = "progressive"
    ) -> RealTimeRoom:
        """Create a new real-time room."""
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
        """Join an existing room."""
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

    async def leave_room(self, player_name: str):
        """Remove a player from their room."""
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
        """Get a room by code."""
        return self.rooms.get(room_code.upper())

    def _get_player_list(self, room: RealTimeRoom) -> list[dict]:
        """Get list of players with their scores."""
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

    async def broadcast_to_room(self, room_code: str, message: dict):
        """Send a message to all players in a room."""
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

    async def send_to_player(self, room_code: str, player_name: str, message: dict):
        """Send a message to a specific player."""
        room = self.rooms.get(room_code)
        if not room or player_name not in room.players:
            return

        try:
            await room.players[player_name].websocket.send_json(message)
        except Exception:
            await self.leave_room(player_name)

    async def start_game(self, room_code: str):
        """Start the game with a countdown."""
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

    async def send_question(self, room_code: str):
        """Send the current question to all players."""
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

    async def _question_timer(self, room_code: str, seconds: int):
        """Timer for answering questions."""
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

    async def submit_answer(self, room_code: str, player_name: str, answer: int):
        """Submit an answer for a player."""
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

    async def show_answer(self, room_code: str):
        """Show the correct answer and update scores."""
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

    async def end_game(self, room_code: str):
        """End the game and show final results."""
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
