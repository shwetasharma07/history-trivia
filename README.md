# BrainRace

A fast-paced trivia game with multiple game modes, power-ups, and multiplayer support.

## Features

### Game Modes
- **Solo Mode** - Play alone with 3 lives and try to beat your high score
- **Local Multiplayer** - Hot-seat play for 2-4 players on the same device
- **Online Rooms** - Create a room, share the code, play at your own pace
- **Live Battle** - Real-time WebSocket multiplayer with synchronized gameplay

### Categories
- Ancient Civilizations
- Medieval Europe
- World Wars
- Cold War
- Ancient Philosophy
- Revolutionary Periods
- Science

### Difficulty Options
- **Progressive** - Starts easy, gets harder
- **Easy/Medium/Hard** - Fixed difficulty
- **Mixed** - Random difficulty per question

### Power-Ups
- **50/50** - Removes 2 wrong answers
- **Skip** - Skip a question without losing a life
- **Double Points** - 2x points for the next correct answer
- **Hint** - Shows the explanation early (50% point penalty)

### Timed Mode
- 15 seconds per question
- Speed bonus for fast answers (+5 points if answered in under 5 seconds)

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Database**: SQLite (for leaderboards and rooms)
- **Real-time**: WebSockets for live multiplayer

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd history-trivia

# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
```

The app will be available at `http://localhost:8000`

## Project Structure

```
history-trivia/
├── main.py              # FastAPI application and routes
├── question_bank.py     # Question loading and management
├── game_engine.py       # Game logic and scoring
├── leaderboard.py       # SQLite leaderboard storage
├── rooms.py             # Async room-based multiplayer
├── websocket_manager.py # Real-time WebSocket multiplayer
├── questions.json       # Question database
├── static/
│   ├── style.css        # Global styles
│   ├── game.js          # Solo/local game logic
│   ├── room-game.js     # Room-based game logic
│   └── realtime-game.js # WebSocket game client
└── templates/
    ├── index.html       # Home page
    ├── game.html        # Game interface
    ├── results.html     # Results page
    ├── lobby.html       # Room creation/join
    ├── room.html        # Room waiting area
    ├── room-game.html   # Room game interface
    ├── room-results.html# Room results
    ├── realtime-lobby.html # Live game lobby
    └── realtime-game.html  # Live game interface
```

## API Endpoints

### Game API
- `GET /api/questions` - Get questions with optional filters
- `POST /api/check-answer` - Validate an answer

### Leaderboard API
- `GET /api/leaderboard` - Get top scores
- `POST /api/leaderboard` - Submit a score

### Room API
- `POST /api/rooms/create` - Create a new room
- `POST /api/rooms/join` - Join an existing room
- `GET /api/rooms/{code}` - Get room details
- `POST /api/rooms/{code}/score` - Submit room score

### WebSocket
- `WS /ws/{room_code}/{player_name}` - Real-time game connection

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_question_bank.py -v
```

## License

MIT
