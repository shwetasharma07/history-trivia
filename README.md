# BrainRace

A fast-paced, multiplayer trivia game built with FastAPI, featuring real-time WebSocket gameplay, multiple game modes, and a comprehensive leaderboard system.

## Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Installation](#installation)
- [Running the Game](#running-the-game)
- [Game Modes](#game-modes)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Features

### Game Modes
- **Solo Mode** - Play alone with 3 lives and compete for the high score
- **Local Multiplayer** - Hot-seat play for 2-4 players on the same device
- **Online Rooms** - Create a room, share the code, and play at your own pace asynchronously
- **Live Battle** - Real-time WebSocket multiplayer with synchronized gameplay and live scoring

### Categories
- Ancient Civilizations
- Medieval Europe
- World Wars
- Cold War
- Ancient Philosophy
- Revolutionary Periods
- Science

### Difficulty Options
- **Progressive** - Starts with easy questions, gradually increases difficulty
- **Easy/Medium/Hard** - Fixed difficulty throughout the game
- **Mixed** - Random difficulty for each question

### Power-Ups (Solo/Local Modes)
- **50/50** - Removes 2 incorrect answers
- **Skip** - Skip a question without losing a life
- **Double Points** - Earn 2x points for the next correct answer
- **Hint** - Shows the explanation early (50% point penalty)

### Scoring System
- Base points vary by difficulty: Easy (10), Medium (20), Hard (30)
- Streak bonuses: 3-streak (1.5x), 5-streak (2x), 10-streak (3x)
- Speed bonus in timed mode: +5 points for answers under 5 seconds

### Timed Mode
- 15 seconds per question
- Speed bonus rewards quick thinking

## Screenshots

> Screenshots coming soon! The game features a clean, responsive UI that works on both desktop and mobile devices.

## Installation

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd history-trivia
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. (Optional) Install development dependencies for testing:
```bash
pip install -r requirements-dev.txt
```

## Running the Game

Start the server:
```bash
python main.py
```

The application will be available at `http://localhost:8000`

### Alternative: Using Uvicorn directly
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Game Modes

### Solo Mode
Play by yourself and try to beat your high score. You start with 3 lives and lose one for each wrong answer. Build streaks for bonus points!

1. Navigate to the home page
2. Click "Play Solo"
3. Select categories and difficulty
4. Answer questions and track your score

### Local Multiplayer
Perfect for game nights! Players take turns answering questions on the same device.

1. Select "Local Multiplayer" from the home page
2. Enter player names (2-4 players)
3. Take turns answering questions
4. See the winner at the end

### Online Rooms (Asynchronous)
Create a room and share the code with friends. Everyone can play at their own pace within 24 hours.

1. Go to `/lobby`
2. Create a room or enter a room code to join
3. Configure game settings (host only)
4. Share the room code with friends
5. Each player completes the quiz at their own pace
6. View results on the room results page

### Live Battle (Real-time)
Compete head-to-head with synchronized questions and live scoring.

1. Navigate to `/realtime`
2. Create a room or join with a code
3. Wait for all players to join
4. Host starts the game
5. Answer questions simultaneously with a 15-second timer
6. See live updates as players answer
7. View final standings after all questions

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Template Engine | [Jinja2](https://jinja.palletsprojects.com/) |
| Database | [SQLite](https://sqlite.org/) with SQLAlchemy ORM |
| Real-time Communication | WebSockets (native FastAPI support) |
| Frontend | Vanilla JavaScript, HTML5, CSS3 |
| Testing | [pytest](https://pytest.org/) |

## Project Structure

```
history-trivia/
├── main.py                 # FastAPI application and all route handlers
├── question_bank.py        # Question loading, filtering, and selection logic
├── game_engine.py          # Core game logic: scoring, streaks, lives management
├── leaderboard.py          # SQLite-based high score storage and retrieval
├── rooms.py                # Async room-based multiplayer management
├── websocket_manager.py    # Real-time WebSocket game room management
├── database.py             # SQLAlchemy database configuration
├── models.py               # SQLAlchemy ORM models
├── questions.json          # Question database organized by category and difficulty
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development/testing dependencies
├── static/
│   ├── style.css           # Global styles
│   ├── game.js             # Solo/local game client logic
│   ├── room-game.js        # Room-based async game client
│   └── realtime-game.js    # WebSocket real-time game client
├── templates/
│   ├── index.html          # Home page
│   ├── game.html           # Solo/local game interface
│   ├── results.html        # Solo game results
│   ├── leaderboard.html    # High scores display
│   ├── lobby.html          # Room creation/joining
│   ├── room.html           # Room waiting area
│   ├── room-game.html      # Room game interface
│   ├── room-results.html   # Room game results
│   ├── realtime-lobby.html # Live game lobby
│   └── realtime-game.html  # Live game interface
└── tests/
    ├── __init__.py
    ├── test_question_bank.py   # Question bank unit tests
    ├── test_game_engine.py     # Game engine unit tests
    ├── test_leaderboard.py     # Leaderboard module tests
    ├── test_rooms.py           # Room management tests
    └── test_websocket.py       # WebSocket manager tests
```

## API Documentation

### Game Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/questions` | Get questions with optional filters (`count`, `categories`, `difficulty`) |
| GET | `/api/categories` | Get available question categories |
| POST | `/api/check-answer` | Validate an answer and get explanation |
| POST | `/api/save-score` | Submit a score to the leaderboard |
| GET | `/api/leaderboard` | Get top 10 scores |

### Room Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rooms/create` | Create a new game room |
| POST | `/api/rooms/join` | Join an existing room |
| GET | `/api/rooms/{code}` | Get room details |
| GET | `/api/rooms/{code}/questions` | Get questions for a room |
| POST | `/api/rooms/{code}/score` | Submit room game score |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `WS /ws/{room_code}/{player_name}` | Real-time game connection |

#### WebSocket Message Types

**Client to Server:**
- `start_game` - Host starts the game
- `submit_answer` - Submit an answer `{"type": "submit_answer", "answer": 0}`
- `chat` - Send chat message

**Server to Client:**
- `room_created` / `room_joined` - Room status
- `player_joined` / `player_left` - Player updates
- `countdown` - Game starting countdown
- `question` - New question with choices
- `timer` - Time remaining
- `player_answered` - Player submitted answer
- `answer_result` - Correct answer and scores
- `game_over` - Final standings

### Interactive API Documentation

When the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testing

Run all tests:
```bash
pytest tests/ -v
```

Run specific test file:
```bash
pytest tests/test_question_bank.py -v
```

Run with coverage report:
```bash
pytest tests/ --cov=. --cov-report=html
```

### Test Structure
- `test_question_bank.py` - Tests for question loading, filtering, and selection
- `test_game_engine.py` - Tests for scoring, streaks, lives, and game state
- `test_leaderboard.py` - Tests for score saving and retrieval
- `test_rooms.py` - Tests for room creation, joining, and management
- `test_websocket.py` - Tests for WebSocket manager functionality

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes and add tests
4. Run the test suite to ensure all tests pass:
   ```bash
   pytest tests/ -v
   ```
5. Commit your changes with a descriptive message:
   ```bash
   git commit -m "Add: description of your feature"
   ```
6. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
7. Open a Pull Request

### Code Style Guidelines
- Follow PEP 8 for Python code
- Add docstrings to all functions and classes
- Include type hints for function parameters and return values
- Write tests for new functionality
- Keep functions focused and single-purpose

### Adding New Questions

Questions are stored in `questions.json` with the following structure:
```json
{
  "category-name": {
    "easy": [
      {
        "question": "Question text",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer": 0,
        "explanation": "Explanation of the correct answer"
      }
    ],
    "medium": [...],
    "hard": [...]
  }
}
```

## License

MIT License

Copyright (c) 2024

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
