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
        category: Filter by category ('ancient', 'medieval', 'modern', 'world-wars')
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


def get_categories() -> list[str]:
    """Return available question categories."""
    return ["ancient", "medieval", "modern", "world-wars"]


def get_difficulties() -> list[str]:
    """Return available difficulty levels."""
    return ["easy", "medium", "hard"]
