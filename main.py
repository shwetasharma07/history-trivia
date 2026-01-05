"""
BrainRace Trivia Game - Main Application Module.

This module serves as the entry point for the BrainRace trivia game,
a FastAPI-based web application that supports:
- Single-player trivia games with configurable difficulty
- Asynchronous multiplayer via room codes
- Real-time multiplayer via WebSocket connections
- Persistent leaderboards and score tracking

The application provides both REST API endpoints for game logic
and HTML template rendering for the frontend.
"""

from fastapi import FastAPI, Request, Depends, Form, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Any
import random
import json

from database import engine, get_db, Base
from models import Score
import question_bank
import leaderboard
import rooms
from websocket_manager import manager

# Store questions in memory for answer checking (keyed by session)
# In production, you'd use a proper session store
_active_questions: dict[int, dict[str, Any]] = {}

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="BrainRace")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """
    Render the home page of the BrainRace trivia game.

    Args:
        request: The incoming HTTP request object.

    Returns:
        HTMLResponse: The rendered index.html template.
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/play", response_class=HTMLResponse)
async def play(request: Request) -> HTMLResponse:
    """
    Render the single-player game page.

    Args:
        request: The incoming HTTP request object.

    Returns:
        HTMLResponse: The rendered game.html template.
    """
    return templates.TemplateResponse("game.html", {"request": request})


@app.get("/api/questions")
async def get_questions(
    count: int = 10,
    categories: Optional[str] = None,
    difficulty: str = "progressive"
) -> dict[str, list[dict[str, Any]]]:
    """
    Retrieve a set of trivia questions for a game session.

    Questions are stored in memory for answer validation. The response
    excludes correct answers to prevent cheating.

    Args:
        count: Number of questions to retrieve (default: 10).
        categories: Comma-separated list of category IDs to filter by.
        difficulty: Difficulty mode - "progressive" (easy to hard),
            "easy", "medium", "hard", or "mixed" (random difficulties).

    Returns:
        A dictionary containing a list of questions, each with:
        - id: Question identifier for answer checking
        - category: The question's category
        - difficulty: The question's difficulty level
        - question: The question text
        - choices: List of answer options
    """
    # Parse categories from comma-separated string
    category_list = None
    if categories:
        category_list = [c.strip() for c in categories.split(",") if c.strip()]

    # Get questions based on difficulty mode
    if difficulty == "progressive":
        questions = question_bank.get_questions_progressive(count, category_list)
    elif difficulty in ["easy", "medium", "hard"]:
        questions = question_bank.get_questions_by_difficulty(count, category_list, difficulty)
    else:  # mixed
        questions = question_bank.get_questions_mixed(count, category_list)

    # Store questions for answer checking and prepare safe response
    safe_questions = []
    for idx, q in enumerate(questions):
        question_id = idx  # Use index as ID for this session
        _active_questions[question_id] = q
        safe_questions.append({
            "id": question_id,
            "category": q["category"],
            "difficulty": q["difficulty"],
            "question": q["question"],
            "choices": q["options"]
        })
    return {"questions": safe_questions}


@app.get("/api/categories")
async def get_categories() -> dict[str, list[dict[str, str]]]:
    """
    Retrieve all available question categories.

    Returns:
        A dictionary with a 'categories' key containing a list of category
        objects, each with 'id' (slug) and 'name' (display name) fields.
    """
    categories = question_bank.get_categories()
    # Return with display names
    display_names = {
        "ancient-civilizations": "Ancient Civilizations",
        "medieval-europe": "Medieval Europe",
        "world-wars": "World Wars",
        "cold-war": "Cold War",
        "ancient-philosophy": "Ancient Philosophy",
        "revolutionary-periods": "Revolutionary Periods",
        "science": "Science"
    }
    return {
        "categories": [
            {"id": cat, "name": display_names.get(cat, cat)}
            for cat in categories
        ]
    }


# Difficulty points for scoring
DIFFICULTY_POINTS = {"easy": 10, "medium": 20, "hard": 30}


@app.post("/api/check-answer")
async def check_answer(
    question_id: int,
    answer: int
) -> dict[str, Any] | JSONResponse:
    """
    Validate a player's answer and return the result.

    Args:
        question_id: The ID of the question being answered.
        answer: The index (0-3) of the selected answer option.

    Returns:
        A dictionary containing:
        - correct: Whether the answer was correct
        - correct_answer: The index of the correct answer
        - fun_fact: Explanation/fact about the answer
        - difficulty: The question's difficulty level
        - points: Points earned (0 if incorrect)

        Returns 404 JSONResponse if question_id not found.
    """
    question = _active_questions.get(question_id)
    if not question:
        return JSONResponse({"error": "Question not found"}, status_code=404)

    is_correct = answer == question["correct_answer"]
    points = DIFFICULTY_POINTS.get(question["difficulty"], 10) if is_correct else 0

    return {
        "correct": is_correct,
        "correct_answer": question["correct_answer"],
        "fun_fact": question["explanation"],
        "difficulty": question["difficulty"],
        "points": points
    }


@app.post("/api/save-score")
async def save_score(
    player_name: str,
    score: int,
    total_questions: int,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Save a player's game score to the leaderboard.

    Saves to both the legacy SQLAlchemy database and the new
    leaderboard module for backwards compatibility.

    Args:
        player_name: The player's display name.
        score: The total score achieved.
        total_questions: Number of questions in the game.
        category: Optional category filter used in the game.
        difficulty: Optional difficulty setting used.
        db: Database session (injected via FastAPI dependency).

    Returns:
        A dictionary with save result, including leaderboard rank if applicable.
    """
    # Save to legacy database for backwards compatibility
    new_score = Score(
        player_name=player_name,
        score=score,
        total_questions=total_questions
    )
    db.add(new_score)
    db.commit()

    # Save to new leaderboard module
    result = leaderboard.save_score(
        player_name=player_name,
        score=score,
        category=category,
        difficulty=difficulty,
        total_questions=total_questions
    )
    return result


@app.get("/api/leaderboard")
async def get_leaderboard() -> dict[str, list[dict[str, Any]]]:
    """
    Retrieve the top 10 scores from the leaderboard.

    Returns:
        A dictionary with a 'scores' key containing a list of score
        records, each including player name, score, date, and game settings.
    """
    scores = leaderboard.get_top_scores(10)
    return {"scores": scores}


@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(request: Request) -> HTMLResponse:
    """
    Render the leaderboard page with top scores.

    Args:
        request: The incoming HTTP request object.

    Returns:
        HTMLResponse: The rendered leaderboard.html template with scores data.
    """
    scores = leaderboard.get_top_scores(10)
    return templates.TemplateResponse(
        "leaderboard.html",
        {"request": request, "scores": scores}
    )


@app.get("/results", response_class=HTMLResponse)
async def results_page(request: Request) -> HTMLResponse:
    """
    Render the game results page.

    This page is shown after a single-player game ends,
    displaying the final score and allowing score submission.

    Args:
        request: The incoming HTTP request object.

    Returns:
        HTMLResponse: The rendered results.html template.
    """
    return templates.TemplateResponse("results.html", {"request": request})


# ============================================
# ROOM-BASED ASYNC MULTIPLAYER
# ============================================

@app.get("/lobby", response_class=HTMLResponse)
async def lobby_page(request: Request) -> HTMLResponse:
    """
    Render the multiplayer lobby page.

    The lobby allows players to create new game rooms or
    join existing rooms using a room code.

    Args:
        request: The incoming HTTP request object.

    Returns:
        HTMLResponse: The rendered lobby.html template.
    """
    return templates.TemplateResponse("lobby.html", {"request": request})


@app.post("/api/rooms/create")
async def create_room(
    host_name: str,
    categories: Optional[str] = None,
    difficulty: str = "progressive",
    question_count: int = 10
) -> dict[str, Any]:
    """
    Create a new asynchronous multiplayer game room.

    Generates a unique room code and pre-selects questions for the game.
    Other players can join using the room code before starting.

    Args:
        host_name: Display name of the room creator.
        categories: Comma-separated list of category IDs to filter questions.
        difficulty: Difficulty mode for question selection.
        question_count: Number of questions for the game (default: 10).

    Returns:
        A dictionary with room creation result including the room_code.
    """
    # Parse categories
    category_list = None
    if categories:
        category_list = [c.strip() for c in categories.split(",") if c.strip()]

    # Get questions based on difficulty mode
    if difficulty == "progressive":
        questions = question_bank.get_questions_progressive(question_count, category_list)
    elif difficulty in ["easy", "medium", "hard"]:
        questions = question_bank.get_questions_by_difficulty(question_count, category_list, difficulty)
    else:
        questions = question_bank.get_questions_mixed(question_count, category_list)

    # Store questions and get their indices
    question_ids = []
    for idx, q in enumerate(questions):
        q_id = len(_active_questions) + idx + 1000  # Offset to avoid collision
        _active_questions[q_id] = q
        question_ids.append(q_id)

    # Create room
    result = rooms.create_room(
        host_name=host_name,
        question_ids=question_ids,
        categories=categories,
        difficulty=difficulty
    )

    return result


@app.post("/api/rooms/join")
async def join_room(room_code: str, player_name: str) -> dict[str, Any]:
    """
    Join an existing game room.

    Args:
        room_code: The unique room code to join.
        player_name: Display name of the player joining.

    Returns:
        A dictionary with join result including room details and status.
    """
    result = rooms.join_room(room_code, player_name)
    return result


@app.get("/api/rooms/{room_code}")
async def get_room_info(room_code: str) -> dict[str, Any] | JSONResponse:
    """
    Retrieve information about a game room.

    Args:
        room_code: The unique room code.

    Returns:
        A dictionary containing room details, player list, and question count.
        Returns 404 JSONResponse if the room is not found or has expired.
    """
    room = rooms.get_room(room_code)
    if not room:
        return JSONResponse({"error": "Room not found or expired"}, status_code=404)

    players = rooms.get_room_players(room_code)
    return {
        "room": room,
        "players": players,
        "question_count": len(room["question_ids"])
    }


@app.get("/api/rooms/{room_code}/questions")
async def get_room_questions(
    room_code: str
) -> dict[str, list[dict[str, Any]]] | JSONResponse:
    """
    Retrieve the questions for a room-based game.

    Questions are returned without correct answers to prevent cheating.

    Args:
        room_code: The unique room code.

    Returns:
        A dictionary with a 'questions' key containing the question list.
        Returns 404 JSONResponse if the room is not found or has expired.
    """
    room = rooms.get_room(room_code)
    if not room:
        return JSONResponse({"error": "Room not found or expired"}, status_code=404)

    # Get questions from memory
    safe_questions = []
    for q_id in room["question_ids"]:
        q = _active_questions.get(q_id)
        if q:
            safe_questions.append({
                "id": q_id,
                "category": q["category"],
                "difficulty": q["difficulty"],
                "question": q["question"],
                "choices": q["options"]
            })

    return {"questions": safe_questions}


@app.post("/api/rooms/{room_code}/score")
async def save_room_score(
    room_code: str,
    player_name: str,
    score: int,
    correct_count: int,
    best_streak: int
) -> dict[str, Any]:
    """
    Save a player's score for a room-based game.

    Args:
        room_code: The unique room code.
        player_name: The player's display name.
        score: Total score achieved.
        correct_count: Number of correct answers.
        best_streak: Longest streak of consecutive correct answers.

    Returns:
        A dictionary with save result and current room standings.
    """
    result = rooms.save_room_score(
        room_code=room_code,
        player_name=player_name,
        score=score,
        correct_count=correct_count,
        best_streak=best_streak
    )
    return result


@app.get("/room/{room_code}", response_class=HTMLResponse)
async def room_page(request: Request, room_code: str) -> HTMLResponse:
    """
    Render the room lobby page showing connected players.

    Players can wait here until the host starts the game.

    Args:
        request: The incoming HTTP request object.
        room_code: The unique room code.

    Returns:
        HTMLResponse: The room.html template with player list,
        or lobby.html with error if room not found.
    """
    room = rooms.get_room(room_code)
    if not room:
        return templates.TemplateResponse("lobby.html", {
            "request": request,
            "error": "Room not found or expired"
        })

    players = rooms.get_room_players(room_code)
    return templates.TemplateResponse("room.html", {
        "request": request,
        "room": room,
        "players": players
    })


@app.get("/room/{room_code}/play", response_class=HTMLResponse)
async def room_play_page(request: Request, room_code: str) -> HTMLResponse:
    """
    Render the game page for a room-based multiplayer game.

    Args:
        request: The incoming HTTP request object.
        room_code: The unique room code.

    Returns:
        HTMLResponse: The room-game.html template,
        or lobby.html with error if room not found.
    """
    room = rooms.get_room(room_code)
    if not room:
        return templates.TemplateResponse("lobby.html", {
            "request": request,
            "error": "Room not found or expired"
        })

    return templates.TemplateResponse("room-game.html", {
        "request": request,
        "room_code": room_code
    })


@app.get("/room/{room_code}/results", response_class=HTMLResponse)
async def room_results_page(request: Request, room_code: str) -> HTMLResponse:
    """
    Render the results page for a room-based multiplayer game.

    Shows final standings and scores for all players in the room.

    Args:
        request: The incoming HTTP request object.
        room_code: The unique room code.

    Returns:
        HTMLResponse: The room-results.html template with player standings.
    """
    room = rooms.get_room(room_code)
    players = rooms.get_room_players(room_code) if room else []

    return templates.TemplateResponse("room-results.html", {
        "request": request,
        "room": room,
        "room_code": room_code,
        "players": players
    })


# ============================================
# REAL-TIME WEBSOCKET MULTIPLAYER
# ============================================

@app.get("/realtime", response_class=HTMLResponse)
async def realtime_lobby_page(request: Request) -> HTMLResponse:
    """
    Render the real-time multiplayer lobby page.

    This lobby is for WebSocket-based synchronous multiplayer where
    all players answer questions simultaneously with a shared timer.

    Args:
        request: The incoming HTTP request object.

    Returns:
        HTMLResponse: The rendered realtime-lobby.html template.
    """
    return templates.TemplateResponse("realtime-lobby.html", {"request": request})


@app.get("/realtime/{room_code}", response_class=HTMLResponse)
async def realtime_game_page(request: Request, room_code: str) -> HTMLResponse:
    """
    Render the real-time multiplayer game page.

    Args:
        request: The incoming HTTP request object.
        room_code: The unique room code for the WebSocket game.

    Returns:
        HTMLResponse: The rendered realtime-game.html template.
    """
    return templates.TemplateResponse("realtime-game.html", {
        "request": request,
        "room_code": room_code
    })


@app.websocket("/ws/{room_code}/{player_name}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, player_name: str) -> None:
    """
    WebSocket endpoint for real-time multiplayer gameplay.

    Handles bidirectional communication for synchronized gameplay including:
    - Room creation (when room_code is "create")
    - Joining existing rooms
    - Game start commands (host only)
    - Answer submissions
    - Chat messages

    The connection is maintained throughout the game session and handles
    automatic cleanup on disconnect.

    Args:
        websocket: The WebSocket connection instance.
        room_code: Room code to join, or "create" for new room.
        player_name: The player's display name.
    """
    await websocket.accept()

    try:
        if room_code == "create":
            # Creating a new room
            # Get settings from first message
            data = await websocket.receive_json()
            categories = data.get("categories", "")
            difficulty = data.get("difficulty", "progressive")

            # Get questions
            category_list = [c.strip() for c in categories.split(",") if c.strip()] if categories else None

            if difficulty == "progressive":
                questions = question_bank.get_questions_progressive(10, category_list)
            elif difficulty in ["easy", "medium", "hard"]:
                questions = question_bank.get_questions_by_difficulty(10, category_list, difficulty)
            else:
                questions = question_bank.get_questions_mixed(10, category_list)

            # Store questions
            question_ids = []
            for idx, q in enumerate(questions):
                q_id = len(_active_questions) + idx + 5000
                _active_questions[q_id] = q
                question_ids.append(q_id)

            # Create room
            room = await manager.create_room(
                host_name=player_name,
                websocket=websocket,
                questions=questions,
                question_ids=question_ids,
                categories=categories,
                difficulty=difficulty
            )

            await websocket.send_json({
                "type": "room_created",
                "room_code": room.code,
                "players": manager._get_player_list(room)
            })

            room_code = room.code

        else:
            # Joining existing room
            room = await manager.join_room(room_code, player_name, websocket)

            if not room:
                await websocket.send_json({
                    "type": "error",
                    "message": "Room not found or game already started"
                })
                await websocket.close()
                return

            await websocket.send_json({
                "type": "room_joined",
                "room_code": room.code,
                "host": room.host_name,
                "players": manager._get_player_list(room)
            })

            # Notify others
            await manager.broadcast_to_room(room_code, {
                "type": "player_joined",
                "player": player_name,
                "players": manager._get_player_list(room)
            })

        # Main message loop
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "start_game":
                room = manager.get_room(room_code)
                if room and player_name == room.host_name:
                    await manager.start_game(room_code)

            elif msg_type == "submit_answer":
                answer = data.get("answer")
                if answer is not None:
                    await manager.submit_answer(room_code, player_name, answer)

            elif msg_type == "chat":
                message = data.get("message", "")[:200]  # Limit message length
                await manager.broadcast_to_room(room_code, {
                    "type": "chat",
                    "player": player_name,
                    "message": message
                })

    except WebSocketDisconnect:
        await manager.leave_room(player_name)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.leave_room(player_name)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
