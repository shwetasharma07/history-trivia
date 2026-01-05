"""
BrainRace Game Engine Module.

This module handles the core game logic for BrainRace trivia games,
including:
- Score calculation with difficulty-based points
- Streak tracking and bonus multipliers
- Lives system (3 lives, lose one per wrong answer)
- Immutable game state management

The engine is designed to be stateless - it receives game state and
returns updated state, making it easy to test and integrate with
different frontends (CLI, web, etc.).

This module does NOT handle:
- Question loading (see question_bank module)
- User I/O or display
- Persistence (see leaderboard module)
"""

from __future__ import annotations
from typing import TypedDict, Optional, Any

# Points awarded per difficulty level
DIFFICULTY_POINTS: dict[str, int] = {
    "easy": 10,
    "medium": 20,
    "hard": 30,
}

# Streak bonus multipliers (streak_length: multiplier)
# When a player reaches a streak threshold, they get the corresponding multiplier
STREAK_BONUSES: dict[int, float] = {
    3: 1.5,   # 50% bonus at 3 streak
    5: 2.0,   # 100% bonus at 5 streak
    10: 3.0,  # 200% bonus at 10 streak
}

# Number of lives players start with
STARTING_LIVES: int = 3


class Question(TypedDict):
    """
    TypedDict representing a single trivia question.

    Attributes:
        question: The question text to display.
        options: List of 4 answer choices.
        answer: Index (0-3) of the correct answer in options.
        explanation: Educational explanation shown after answering.
        difficulty: Difficulty level ('easy', 'medium', or 'hard').
    """
    question: str
    options: list[str]
    answer: int
    explanation: str
    difficulty: str


class GameState(TypedDict):
    """
    TypedDict representing the complete state of a game session.

    The game state is immutable - functions return new state objects
    rather than modifying the existing state.

    Attributes:
        questions: List of all questions for this game.
        current_question_index: Index of the next question to answer.
        score: Cumulative score earned.
        lives: Remaining lives (game ends at 0).
        streak: Current consecutive correct answers.
        max_streak: Best streak achieved this game.
        correct_answers: Total correct answers given.
        total_answered: Total questions answered (correct or not).
    """
    questions: list[Question]
    current_question_index: int
    score: int
    lives: int
    streak: int
    max_streak: int
    correct_answers: int
    total_answered: int


def start_game(questions: list[Question]) -> GameState:
    """
    Initialize a new game session with the provided questions.

    Creates a fresh game state with:
    - All questions loaded
    - Score at 0
    - Full lives (STARTING_LIVES)
    - No streak or answers recorded

    Args:
        questions: List of Question TypedDicts to use for this game.
            Typically obtained from the question_bank module.

    Returns:
        A new GameState ready for the first question.
    """
    return GameState(
        questions=questions,
        current_question_index=0,
        score=0,
        lives=STARTING_LIVES,
        streak=0,
        max_streak=0,
        correct_answers=0,
        total_answered=0,
    )


def get_current_question(game_state: GameState) -> Optional[Question]:
    """
    Get the current question to be answered.

    Args:
        game_state: The current game state.

    Returns:
        The current Question if there are remaining questions,
        or None if all questions have been answered.
    """
    index = game_state["current_question_index"]
    questions = game_state["questions"]

    if index >= len(questions):
        return None
    return questions[index]


def _calculate_streak_multiplier(streak: int) -> float:
    """
    Calculate the score multiplier based on current streak.

    The multiplier is determined by the highest streak threshold
    that has been reached. Thresholds are defined in STREAK_BONUSES.

    Args:
        streak: The current number of consecutive correct answers.

    Returns:
        The multiplier to apply to base points (1.0 if no bonus applies).
    """
    multiplier = 1.0
    for threshold, bonus in sorted(STREAK_BONUSES.items()):
        if streak >= threshold:
            multiplier = bonus
    return multiplier


def submit_answer(
    game_state: GameState,
    answer_index: int
) -> tuple[bool, int, GameState]:
    """
    Submit an answer for the current question and update game state.

    This is the main game action function. It:
    - Checks if the answer is correct
    - Updates score with difficulty-based points and streak bonuses
    - Updates streak (increment on correct, reset on wrong)
    - Decrements lives on wrong answers
    - Advances to the next question

    The function returns a new GameState rather than modifying
    the input state (immutable update pattern).

    Args:
        game_state: The current game state.
        answer_index: Index (0-3) of the selected answer option.

    Returns:
        A tuple containing:
        - is_correct: Whether the answer was correct
        - points_earned: Points awarded for this answer (0 if wrong)
        - new_state: Updated GameState with all changes applied
    """
    question = get_current_question(game_state)
    if question is None:
        return (False, 0, game_state)

    is_correct = answer_index == question["answer"]
    points_earned = 0

    # Create new state (immutable update)
    new_state = GameState(
        questions=game_state["questions"],
        current_question_index=game_state["current_question_index"] + 1,
        score=game_state["score"],
        lives=game_state["lives"],
        streak=game_state["streak"],
        max_streak=game_state["max_streak"],
        correct_answers=game_state["correct_answers"],
        total_answered=game_state["total_answered"] + 1,
    )

    if is_correct:
        # Update streak
        new_streak = game_state["streak"] + 1
        new_state["streak"] = new_streak
        new_state["max_streak"] = max(game_state["max_streak"], new_streak)
        new_state["correct_answers"] = game_state["correct_answers"] + 1

        # Calculate points with streak bonus
        base_points = DIFFICULTY_POINTS.get(question["difficulty"], 10)
        multiplier = _calculate_streak_multiplier(new_streak)
        points_earned = int(base_points * multiplier)
        new_state["score"] = game_state["score"] + points_earned
    else:
        # Wrong answer: lose life and reset streak
        new_state["lives"] = game_state["lives"] - 1
        new_state["streak"] = 0

    return (is_correct, points_earned, new_state)


def is_game_over(game_state: GameState) -> bool:
    """
    Check if the game has ended.

    The game ends under two conditions:
    1. The player has run out of lives (lives <= 0)
    2. All questions have been answered

    Args:
        game_state: The current game state to check.

    Returns:
        True if the game is over, False if play should continue.
    """
    no_lives = game_state["lives"] <= 0
    no_questions = game_state["current_question_index"] >= len(game_state["questions"])
    return no_lives or no_questions


def get_final_score(game_state: GameState) -> dict[str, Any]:
    """
    Get comprehensive final game statistics.

    Calculates and returns all relevant statistics for displaying
    end-of-game results and saving to the leaderboard.

    Args:
        game_state: The final game state after game over.

    Returns:
        A dictionary containing:
        - score: Total points earned
        - correct_answers: Number of correct answers
        - total_answered: Total questions attempted
        - accuracy: Percentage of correct answers (0-100)
        - max_streak: Longest streak of consecutive correct answers
        - lives_remaining: Lives left at game end (0 if ran out)
        - completed: Whether all questions were answered
    """
    total = game_state["total_answered"]
    correct = game_state["correct_answers"]
    accuracy = (correct / total * 100) if total > 0 else 0.0

    return {
        "score": game_state["score"],
        "correct_answers": correct,
        "total_answered": total,
        "accuracy": round(accuracy, 1),
        "max_streak": game_state["max_streak"],
        "lives_remaining": game_state["lives"],
        "completed": game_state["current_question_index"] >= len(game_state["questions"]),
    }


# --- Tests ---
if __name__ == "__main__":
    # Mock questions for testing
    mock_questions: list[Question] = [
        {
            "question": "In what year did World War II end?",
            "options": ["1943", "1944", "1945", "1946"],
            "answer": 2,
            "explanation": "WWII ended in 1945 with Germany's surrender in May and Japan's in September.",
            "difficulty": "easy",
        },
        {
            "question": "Who was the first Roman Emperor?",
            "options": ["Julius Caesar", "Augustus", "Nero", "Caligula"],
            "answer": 1,
            "explanation": "Augustus (Octavian) became the first Roman Emperor in 27 BC.",
            "difficulty": "medium",
        },
        {
            "question": "Which treaty ended World War I?",
            "options": ["Treaty of Paris", "Treaty of Versailles", "Treaty of Vienna", "Treaty of Westphalia"],
            "answer": 1,
            "explanation": "The Treaty of Versailles was signed on June 28, 1919.",
            "difficulty": "easy",
        },
        {
            "question": "What year was the Magna Carta signed?",
            "options": ["1066", "1215", "1415", "1515"],
            "answer": 1,
            "explanation": "The Magna Carta was signed by King John in 1215.",
            "difficulty": "hard",
        },
        {
            "question": "Who led the Mongol Empire at its peak?",
            "options": ["Genghis Khan", "Kublai Khan", "Tamerlane", "Attila"],
            "answer": 0,
            "explanation": "Genghis Khan founded and led the Mongol Empire to its greatest conquests.",
            "difficulty": "medium",
        },
    ]

    print("=== History Trivia Game Engine Test ===\n")

    # Start game
    state = start_game(mock_questions)
    print(f"Game started with {len(mock_questions)} questions")
    print(f"Starting lives: {state['lives']}\n")

    # Simulate gameplay: correct, correct, correct (streak!), wrong, correct
    test_answers = [2, 1, 1, 0, 0]  # indices to submit

    for i, answer in enumerate(test_answers):
        if is_game_over(state):
            print("Game Over!")
            break

        question = get_current_question(state)
        if question is None:
            break

        print(f"Q{i+1}: {question['question']}")
        print(f"  Difficulty: {question['difficulty']}")
        print(f"  Your answer: {question['options'][answer]}")

        is_correct, points, state = submit_answer(state, answer)

        if is_correct:
            print(f"  CORRECT! +{points} points (streak: {state['streak']})")
        else:
            print(f"  WRONG! Lost a life. Lives remaining: {state['lives']}")
        print(f"  Current score: {state['score']}\n")

    # Final results
    print("=== Final Results ===")
    results = get_final_score(state)
    for key, value in results.items():
        print(f"  {key}: {value}")
