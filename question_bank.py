"""Question bank module for history trivia game."""

import json
import random
from pathlib import Path
from typing import Optional


def _load_questions_from_file() -> dict:
    """Load raw question data from the JSON file."""
    questions_path = Path(__file__).parent / "questions.json"
    with open(questions_path, "r") as f:
        return json.load(f)


def _flatten_questions(
    data: dict,
    category: Optional[str] = None,
    difficulty: Optional[str] = None
) -> list[dict]:
    """Flatten nested question structure into a list, applying filters."""
    questions = []

    categories = [category] if category else data.keys()

    for cat in categories:
        if cat not in data:
            continue
        difficulties = [difficulty] if difficulty else data[cat].keys()

        for diff in difficulties:
            if diff not in data[cat]:
                continue
            for q in data[cat][diff]:
                question_with_meta = {
                    "category": cat,
                    "difficulty": diff,
                    **q
                }
                questions.append(question_with_meta)

    return questions


def get_questions(
    count: int = 10,
    category: Optional[str] = None,
    difficulty: Optional[str] = None
) -> list[dict]:
    """
    Get a random subset of trivia questions.

    Args:
        count: Number of questions to return (default 10)
        category: Filter by category ('ancient-civilizations', 'medieval-europe',
                  'world-wars', 'cold-war', 'ancient-philosophy', 'revolutionary-periods')
        difficulty: Filter by difficulty ('easy', 'medium', 'hard')

    Returns:
        List of question dicts, each containing:
            - category: str
            - difficulty: str
            - question: str
            - options: list of 4 answer choices
            - correct_answer: int (0-3 index of correct option)
            - explanation: str
    """
    data = _load_questions_from_file()
    questions = _flatten_questions(data, category, difficulty)

    if count >= len(questions):
        result = questions.copy()
        random.shuffle(result)
        return result

    return random.sample(questions, count)


def get_questions_progressive(
    count: int = 10,
    categories: Optional[list[str]] = None
) -> list[dict]:
    """
    Get questions with progressive difficulty (easy -> medium -> hard).

    Args:
        count: Number of questions to return (default 10)
        categories: List of categories to include. If None, includes all categories.

    Returns:
        List of question dicts ordered by difficulty (easy first, then medium, then hard)
    """
    data = _load_questions_from_file()

    # Filter by categories
    if categories:
        filtered_data = {k: v for k, v in data.items() if k in categories}
    else:
        filtered_data = data

    # Collect questions by difficulty
    easy_questions = _flatten_questions(filtered_data, difficulty="easy")
    medium_questions = _flatten_questions(filtered_data, difficulty="medium")
    hard_questions = _flatten_questions(filtered_data, difficulty="hard")

    # Shuffle within each difficulty
    random.shuffle(easy_questions)
    random.shuffle(medium_questions)
    random.shuffle(hard_questions)

    # Calculate distribution: roughly 1/3 each, but adjust based on count
    easy_count = count // 3
    medium_count = count // 3
    hard_count = count - easy_count - medium_count

    # Take questions from each pool (or all if not enough)
    selected_easy = easy_questions[:min(easy_count, len(easy_questions))]
    selected_medium = medium_questions[:min(medium_count, len(medium_questions))]
    selected_hard = hard_questions[:min(hard_count, len(hard_questions))]

    # If we don't have enough in a category, fill from others
    total_selected = len(selected_easy) + len(selected_medium) + len(selected_hard)
    remaining = count - total_selected

    if remaining > 0:
        # Try to fill with any remaining questions
        all_remaining = (
            easy_questions[len(selected_easy):] +
            medium_questions[len(selected_medium):] +
            hard_questions[len(selected_hard):]
        )
        random.shuffle(all_remaining)
        extra = all_remaining[:remaining]
        # Sort extras by difficulty and append appropriately
        for q in extra:
            if q["difficulty"] == "easy":
                selected_easy.append(q)
            elif q["difficulty"] == "medium":
                selected_medium.append(q)
            else:
                selected_hard.append(q)

    # Combine in progressive order: easy -> medium -> hard
    return selected_easy + selected_medium + selected_hard


def get_questions_by_difficulty(
    count: int = 10,
    categories: Optional[list[str]] = None,
    difficulty: str = "medium"
) -> list[dict]:
    """
    Get questions of a specific difficulty level.

    Args:
        count: Number of questions to return
        categories: List of categories to include. If None, includes all.
        difficulty: The difficulty level (easy, medium, hard)

    Returns:
        List of question dicts all at the specified difficulty
    """
    data = _load_questions_from_file()

    # Filter by categories
    if categories:
        filtered_data = {k: v for k, v in data.items() if k in categories}
    else:
        filtered_data = data

    questions = _flatten_questions(filtered_data, difficulty=difficulty)
    random.shuffle(questions)

    return questions[:min(count, len(questions))]


def get_questions_mixed(
    count: int = 10,
    categories: Optional[list[str]] = None
) -> list[dict]:
    """
    Get questions with random mixed difficulties.

    Args:
        count: Number of questions to return
        categories: List of categories to include. If None, includes all.

    Returns:
        List of question dicts with random difficulties
    """
    data = _load_questions_from_file()

    # Filter by categories
    if categories:
        filtered_data = {k: v for k, v in data.items() if k in categories}
    else:
        filtered_data = data

    questions = _flatten_questions(filtered_data)
    random.shuffle(questions)

    return questions[:min(count, len(questions))]


def get_categories() -> list[str]:
    """Return available question categories."""
    return [
        "ancient-civilizations",
        "medieval-europe",
        "world-wars",
        "cold-war",
        "ancient-philosophy",
        "revolutionary-periods",
        "science"
    ]


def get_difficulties() -> list[str]:
    """Return available difficulty levels."""
    return ["easy", "medium", "hard"]
