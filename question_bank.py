"""
Question Bank Module for BrainRace Trivia Game.

This module provides functions for loading, filtering, and retrieving
trivia questions from a JSON file. It supports filtering by category
and difficulty, and offers multiple selection modes:
- Progressive: Questions ordered from easy to hard
- Fixed difficulty: All questions at a specific difficulty level
- Mixed: Random difficulties throughout

The question bank reads from questions.json which contains questions
organized by category and difficulty level.
"""

import json
import random
from pathlib import Path
from typing import Optional, Any


def _load_questions_from_file() -> dict[str, dict[str, list[dict[str, Any]]]]:
    """
    Load raw question data from the JSON file.

    The JSON file contains questions organized in a nested structure:
    {category: {difficulty: [questions]}}

    Returns:
        A nested dictionary with categories as top-level keys,
        difficulties as second-level keys, and lists of questions as values.
    """
    questions_path = Path(__file__).parent / "questions.json"
    with open(questions_path, "r") as f:
        return json.load(f)


def _flatten_questions(
    data: dict[str, dict[str, list[dict[str, Any]]]],
    category: Optional[str] = None,
    difficulty: Optional[str] = None
) -> list[dict[str, Any]]:
    """
    Flatten nested question structure into a flat list with optional filters.

    Takes the nested {category: {difficulty: [questions]}} structure and
    returns a flat list of questions, each augmented with 'category' and
    'difficulty' metadata fields.

    Args:
        data: The nested question data structure.
        category: If provided, only include questions from this category.
        difficulty: If provided, only include questions at this difficulty.

    Returns:
        A flat list of question dictionaries, each containing:
        - category: The question's category slug
        - difficulty: The question's difficulty level
        - question: The question text
        - options: List of answer choices
        - correct_answer: Index of the correct option
        - explanation: Educational explanation of the answer
    """
    questions: list[dict[str, Any]] = []

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
) -> list[dict[str, Any]]:
    """
    Get a random subset of trivia questions.

    Retrieves questions from the question bank, optionally filtered by
    category and/or difficulty. Questions are returned in random order.

    Args:
        count: Number of questions to return (default 10).
        category: Filter by category slug. Valid options include:
            'ancient-civilizations', 'medieval-europe', 'world-wars',
            'cold-war', 'ancient-philosophy', 'revolutionary-periods', 'science'.
        difficulty: Filter by difficulty level ('easy', 'medium', 'hard').

    Returns:
        A list of question dictionaries, each containing:
        - category: The question's category slug
        - difficulty: The difficulty level
        - question: The question text
        - options: List of 4 answer choices
        - correct_answer: Index (0-3) of the correct option
        - explanation: Educational explanation of the answer
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
) -> list[dict[str, Any]]:
    """
    Get questions with progressive difficulty (easy -> medium -> hard).

    Questions are distributed roughly equally across difficulty levels
    and ordered so players start with easier questions and progress
    to harder ones. This creates a natural difficulty curve.

    Args:
        count: Total number of questions to return (default 10).
        categories: List of category slugs to include. If None, includes all.

    Returns:
        A list of question dictionaries ordered by difficulty:
        easy questions first, then medium, then hard.
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
) -> list[dict[str, Any]]:
    """
    Get questions of a specific difficulty level.

    All returned questions will be at the same difficulty level,
    providing a consistent challenge throughout the game.

    Args:
        count: Number of questions to return (default 10).
        categories: List of category slugs to include. If None, includes all.
        difficulty: The difficulty level - 'easy', 'medium', or 'hard'.

    Returns:
        A list of question dictionaries, all at the specified difficulty.
        Questions are returned in random order within that difficulty.
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
) -> list[dict[str, Any]]:
    """
    Get questions with random mixed difficulties.

    Questions are selected randomly from all difficulty levels,
    creating an unpredictable challenge where easy and hard
    questions can appear in any order.

    Args:
        count: Number of questions to return (default 10).
        categories: List of category slugs to include. If None, includes all.

    Returns:
        A list of question dictionaries with randomly mixed difficulties.
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
    """
    Return all available question category slugs.

    Categories are used to organize questions by historical period
    or subject area. These slugs can be passed to question retrieval
    functions to filter results.

    Returns:
        A list of category slug strings.
    """
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
    """
    Return all available difficulty levels.

    Difficulty levels determine question complexity and affect
    scoring in the game engine.

    Returns:
        A list of difficulty level strings: 'easy', 'medium', 'hard'.
    """
    return ["easy", "medium", "hard"]
