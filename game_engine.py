"""
History Trivia Game Engine

Handles game logic including scoring, streaks, lives, and state management.
Does not handle question loading or user I/O.
"""

from __future__ import annotations
from typing import TypedDict, Optional

# Points awarded per difficulty level
DIFFICULTY_POINTS = {
    "easy": 10,
    "medium": 20,
    "hard": 30,
}

# Streak bonus multipliers (streak_length: multiplier)
STREAK_BONUSES = {
    3: 1.5,   # 50% bonus at 3 streak
    5: 2.0,   # 100% bonus at 5 streak
    10: 3.0,  # 200% bonus at 10 streak
}

STARTING_LIVES = 3


class Question(TypedDict):
    question: str
    options: list[str]
    answer: int
    explanation: str
    difficulty: str


class GameState(TypedDict):
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
    Initialize a new game with the provided questions.

    Args:
        questions: List of question dicts from external source

    Returns:
        Initial game state
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
    Get the current question, or None if no more questions.

    Args:
        game_state: Current game state

    Returns:
        Current question dict or None
    """
    index = game_state["current_question_index"]
    questions = game_state["questions"]

    if index >= len(questions):
        return None
    return questions[index]


def _calculate_streak_multiplier(streak: int) -> float:
    """Calculate bonus multiplier based on current streak."""
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
    Submit an answer for the current question.

    Args:
        game_state: Current game state
        answer_index: Index of the selected answer (0-based)

    Returns:
        Tuple of (is_correct, points_earned, updated_game_state)
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

    Game ends when:
    - Player runs out of lives, OR
    - All questions have been answered

    Args:
        game_state: Current game state

    Returns:
        True if game is over
    """
    no_lives = game_state["lives"] <= 0
    no_questions = game_state["current_question_index"] >= len(game_state["questions"])
    return no_lives or no_questions


def get_final_score(game_state: GameState) -> dict:
    """
    Get final game statistics.

    Args:
        game_state: Final game state

    Returns:
        Dict with score, accuracy, max_streak, etc.
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
