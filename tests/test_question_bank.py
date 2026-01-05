"""Tests for question_bank module."""

import pytest
from unittest.mock import patch, mock_open
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from question_bank import (
    get_questions,
    get_categories,
    get_difficulties,
    _load_questions_from_file,
    _flatten_questions,
)


# Sample test data matching the expected structure
SAMPLE_QUESTIONS_DATA = {
    "ancient": {
        "easy": [
            {
                "question": "Who built the pyramids?",
                "options": ["Romans", "Egyptians", "Greeks", "Persians"],
                "correct_answer": 1,
                "explanation": "The ancient Egyptians built the pyramids."
            },
            {
                "question": "What was the capital of ancient Rome?",
                "options": ["Athens", "Rome", "Sparta", "Carthage"],
                "correct_answer": 1,
                "explanation": "Rome was the capital of the Roman Empire."
            }
        ],
        "medium": [
            {
                "question": "Who was the first Roman Emperor?",
                "options": ["Julius Caesar", "Augustus", "Nero", "Caligula"],
                "correct_answer": 1,
                "explanation": "Augustus became the first Roman Emperor in 27 BC."
            }
        ],
        "hard": [
            {
                "question": "In what year was Julius Caesar assassinated?",
                "options": ["44 BC", "31 BC", "27 BC", "14 AD"],
                "correct_answer": 0,
                "explanation": "Caesar was assassinated on the Ides of March, 44 BC."
            }
        ]
    },
    "medieval": {
        "easy": [
            {
                "question": "What was the Magna Carta?",
                "options": ["A map", "A charter of rights", "A weapon", "A ship"],
                "correct_answer": 1,
                "explanation": "The Magna Carta was a charter of rights signed in 1215."
            }
        ],
        "medium": [],
        "hard": []
    },
    "modern": {
        "easy": [],
        "medium": [
            {
                "question": "When did World War I begin?",
                "options": ["1912", "1914", "1916", "1918"],
                "correct_answer": 1,
                "explanation": "WWI began in 1914."
            }
        ],
        "hard": []
    },
    "world-wars": {
        "easy": [
            {
                "question": "When did WWII end?",
                "options": ["1943", "1944", "1945", "1946"],
                "correct_answer": 2,
                "explanation": "WWII ended in 1945."
            }
        ],
        "medium": [],
        "hard": []
    }
}


class TestGetCategories:
    """Tests for get_categories function."""

    def test_returns_list(self):
        """Should return a list."""
        result = get_categories()
        assert isinstance(result, list)

    def test_contains_expected_categories(self):
        """Should contain all expected categories."""
        categories = get_categories()
        expected = ["ancient-civilizations", "medieval-europe", "world-wars", "cold-war", "ancient-philosophy", "revolutionary-periods", "science"]
        assert categories == expected

    def test_returns_seven_categories(self):
        """Should return exactly seven categories."""
        assert len(get_categories()) == 7


class TestGetDifficulties:
    """Tests for get_difficulties function."""

    def test_returns_list(self):
        """Should return a list."""
        result = get_difficulties()
        assert isinstance(result, list)

    def test_contains_expected_difficulties(self):
        """Should contain all expected difficulty levels."""
        difficulties = get_difficulties()
        expected = ["easy", "medium", "hard"]
        assert difficulties == expected

    def test_returns_three_difficulties(self):
        """Should return exactly three difficulty levels."""
        assert len(get_difficulties()) == 3


class TestFlattenQuestions:
    """Tests for _flatten_questions helper function."""

    def test_flatten_all_questions(self):
        """Should flatten all questions when no filters applied."""
        result = _flatten_questions(SAMPLE_QUESTIONS_DATA)
        # Count non-empty question lists in sample data
        expected_count = 7  # 2+1+1 from ancient, 1 from medieval, 1 from modern, 1 from world-wars
        assert len(result) == expected_count

    def test_flatten_with_category_filter(self):
        """Should only include questions from specified category."""
        result = _flatten_questions(SAMPLE_QUESTIONS_DATA, category="ancient")
        assert len(result) == 4  # 2 easy + 1 medium + 1 hard
        for q in result:
            assert q["category"] == "ancient"

    def test_flatten_with_difficulty_filter(self):
        """Should only include questions with specified difficulty."""
        result = _flatten_questions(SAMPLE_QUESTIONS_DATA, difficulty="easy")
        # ancient(2) + medieval(1) + modern(0) + world-wars(1) = 4
        assert len(result) == 4
        for q in result:
            assert q["difficulty"] == "easy"

    def test_flatten_with_both_filters(self):
        """Should filter by both category and difficulty."""
        result = _flatten_questions(
            SAMPLE_QUESTIONS_DATA,
            category="ancient",
            difficulty="easy"
        )
        assert len(result) == 2
        for q in result:
            assert q["category"] == "ancient"
            assert q["difficulty"] == "easy"

    def test_adds_category_metadata(self):
        """Should add category field to each question."""
        result = _flatten_questions(SAMPLE_QUESTIONS_DATA, category="ancient")
        for q in result:
            assert "category" in q
            assert q["category"] == "ancient"

    def test_adds_difficulty_metadata(self):
        """Should add difficulty field to each question."""
        result = _flatten_questions(SAMPLE_QUESTIONS_DATA, category="ancient", difficulty="easy")
        for q in result:
            assert "difficulty" in q
            assert q["difficulty"] == "easy"

    def test_preserves_original_question_fields(self):
        """Should preserve all original question fields."""
        result = _flatten_questions(SAMPLE_QUESTIONS_DATA, category="ancient", difficulty="easy")
        assert len(result) > 0
        q = result[0]
        assert "question" in q
        assert "options" in q
        assert "correct_answer" in q
        assert "explanation" in q

    def test_invalid_category_returns_empty(self):
        """Should return empty list for non-existent category."""
        result = _flatten_questions(SAMPLE_QUESTIONS_DATA, category="nonexistent")
        assert result == []

    def test_invalid_difficulty_returns_empty(self):
        """Should return empty list for non-existent difficulty."""
        result = _flatten_questions(SAMPLE_QUESTIONS_DATA, difficulty="impossible")
        assert result == []

    def test_empty_data_returns_empty(self):
        """Should return empty list for empty data."""
        result = _flatten_questions({})
        assert result == []

    def test_category_with_no_questions_at_difficulty(self):
        """Should return empty when category exists but has no questions at difficulty."""
        result = _flatten_questions(SAMPLE_QUESTIONS_DATA, category="medieval", difficulty="medium")
        assert result == []


class TestGetQuestions:
    """Tests for get_questions function."""

    @patch('question_bank._load_questions_from_file')
    def test_returns_list(self, mock_load):
        """Should return a list of questions."""
        mock_load.return_value = SAMPLE_QUESTIONS_DATA
        result = get_questions(count=5)
        assert isinstance(result, list)

    @patch('question_bank._load_questions_from_file')
    def test_returns_requested_count(self, mock_load):
        """Should return the requested number of questions."""
        mock_load.return_value = SAMPLE_QUESTIONS_DATA
        result = get_questions(count=3)
        assert len(result) == 3

    @patch('question_bank._load_questions_from_file')
    def test_default_count_is_ten(self, mock_load):
        """Should default to 10 questions when count not specified."""
        # Need more questions in mock data for this test
        large_data = {
            "ancient": {
                "easy": [
                    {"question": f"Q{i}", "options": ["A", "B", "C", "D"], "correct_answer": 0, "explanation": "E"}
                    for i in range(15)
                ],
                "medium": [],
                "hard": []
            }
        }
        mock_load.return_value = large_data
        result = get_questions()
        assert len(result) == 10

    @patch('question_bank._load_questions_from_file')
    def test_returns_all_when_count_exceeds_available(self, mock_load):
        """Should return all questions when count exceeds available."""
        mock_load.return_value = SAMPLE_QUESTIONS_DATA
        result = get_questions(count=100)
        assert len(result) == 7  # Total questions in sample data

    @patch('question_bank._load_questions_from_file')
    def test_filter_by_category(self, mock_load):
        """Should filter questions by category."""
        mock_load.return_value = SAMPLE_QUESTIONS_DATA
        result = get_questions(count=10, category="ancient")
        for q in result:
            assert q["category"] == "ancient"

    @patch('question_bank._load_questions_from_file')
    def test_filter_by_difficulty(self, mock_load):
        """Should filter questions by difficulty."""
        mock_load.return_value = SAMPLE_QUESTIONS_DATA
        result = get_questions(count=10, difficulty="easy")
        for q in result:
            assert q["difficulty"] == "easy"

    @patch('question_bank._load_questions_from_file')
    def test_filter_by_both_category_and_difficulty(self, mock_load):
        """Should filter by both category and difficulty."""
        mock_load.return_value = SAMPLE_QUESTIONS_DATA
        result = get_questions(count=10, category="ancient", difficulty="easy")
        assert len(result) == 2
        for q in result:
            assert q["category"] == "ancient"
            assert q["difficulty"] == "easy"

    @patch('question_bank._load_questions_from_file')
    def test_randomization(self, mock_load):
        """Should return questions in random order."""
        large_data = {
            "ancient": {
                "easy": [
                    {"question": f"Q{i}", "options": ["A", "B", "C", "D"], "correct_answer": 0, "explanation": "E"}
                    for i in range(20)
                ],
                "medium": [],
                "hard": []
            }
        }
        mock_load.return_value = large_data

        # Get multiple samples and check they're not always identical
        results = [tuple(q["question"] for q in get_questions(count=5)) for _ in range(10)]
        unique_orders = set(results)
        # With 20 questions choosing 5, should get different orders
        assert len(unique_orders) > 1, "Questions should be randomized"

    @patch('question_bank._load_questions_from_file')
    def test_question_structure(self, mock_load):
        """Should return questions with correct structure."""
        mock_load.return_value = SAMPLE_QUESTIONS_DATA
        result = get_questions(count=1)
        assert len(result) == 1
        q = result[0]
        assert "question" in q
        assert "options" in q
        assert "correct_answer" in q
        assert "explanation" in q
        assert "category" in q
        assert "difficulty" in q

    @patch('question_bank._load_questions_from_file')
    def test_options_has_four_choices(self, mock_load):
        """Each question should have exactly 4 options."""
        mock_load.return_value = SAMPLE_QUESTIONS_DATA
        result = get_questions(count=5)
        for q in result:
            assert len(q["options"]) == 4

    @patch('question_bank._load_questions_from_file')
    def test_correct_answer_in_valid_range(self, mock_load):
        """Correct answer index should be 0-3."""
        mock_load.return_value = SAMPLE_QUESTIONS_DATA
        result = get_questions(count=5)
        for q in result:
            assert 0 <= q["correct_answer"] <= 3


class TestGetQuestionsEdgeCases:
    """Edge case tests for get_questions."""

    @patch('question_bank._load_questions_from_file')
    def test_zero_count_returns_empty(self, mock_load):
        """Should return empty list when count is 0."""
        mock_load.return_value = SAMPLE_QUESTIONS_DATA
        result = get_questions(count=0)
        assert result == []

    @patch('question_bank._load_questions_from_file')
    def test_empty_question_bank(self, mock_load):
        """Should handle empty question bank gracefully."""
        mock_load.return_value = {}
        result = get_questions(count=5)
        assert result == []

    @patch('question_bank._load_questions_from_file')
    def test_invalid_category_returns_empty(self, mock_load):
        """Should return empty list for non-existent category."""
        mock_load.return_value = SAMPLE_QUESTIONS_DATA
        result = get_questions(count=5, category="future")
        assert result == []

    @patch('question_bank._load_questions_from_file')
    def test_invalid_difficulty_returns_empty(self, mock_load):
        """Should return empty list for non-existent difficulty."""
        mock_load.return_value = SAMPLE_QUESTIONS_DATA
        result = get_questions(count=5, difficulty="impossible")
        assert result == []

    @patch('question_bank._load_questions_from_file')
    def test_category_with_empty_difficulties(self, mock_load):
        """Should handle category with all empty difficulty levels."""
        empty_category_data = {
            "empty_cat": {
                "easy": [],
                "medium": [],
                "hard": []
            }
        }
        mock_load.return_value = empty_category_data
        result = get_questions(count=5, category="empty_cat")
        assert result == []

    @patch('question_bank._load_questions_from_file')
    def test_single_question_available(self, mock_load):
        """Should work with only one question available."""
        single_q_data = {
            "ancient": {
                "easy": [
                    {"question": "Only Q", "options": ["A", "B", "C", "D"], "correct_answer": 0, "explanation": "E"}
                ],
                "medium": [],
                "hard": []
            }
        }
        mock_load.return_value = single_q_data
        result = get_questions(count=5)
        assert len(result) == 1

    @patch('question_bank._load_questions_from_file')
    def test_negative_count_behavior(self, mock_load):
        """Should handle negative count (implementation-dependent)."""
        mock_load.return_value = SAMPLE_QUESTIONS_DATA
        # random.sample with negative count raises ValueError
        with pytest.raises(ValueError):
            get_questions(count=-1)


class TestLoadQuestionsFromFile:
    """Tests for _load_questions_from_file function."""

    def test_loads_real_questions_file(self):
        """Should load the actual questions.json file."""
        result = _load_questions_from_file()
        assert isinstance(result, dict)
        # Should have the expected categories
        assert "ancient-civilizations" in result
        assert "medieval-europe" in result

    def test_real_file_has_expected_structure(self):
        """Real file should have nested category->difficulty structure."""
        result = _load_questions_from_file()
        for category in result:
            assert isinstance(result[category], dict)
            # Each category should have difficulty keys
            for difficulty in result[category]:
                assert isinstance(result[category][difficulty], list)


class TestIntegration:
    """Integration tests using actual question data."""

    def test_get_real_questions(self):
        """Should successfully get questions from real data."""
        result = get_questions(count=5)
        assert len(result) == 5
        for q in result:
            assert "question" in q
            assert "options" in q

    def test_filter_real_ancient_questions(self):
        """Should filter real ancient history questions."""
        result = get_questions(count=20, category="ancient-civilizations")
        assert len(result) > 0
        for q in result:
            assert q["category"] == "ancient-civilizations"

    def test_filter_real_hard_questions(self):
        """Should filter real hard questions."""
        result = get_questions(count=20, difficulty="hard")
        assert len(result) > 0
        for q in result:
            assert q["difficulty"] == "hard"

    def test_all_categories_have_questions(self):
        """Each category should have at least one question."""
        for category in get_categories():
            result = get_questions(count=1, category=category)
            assert len(result) >= 1, f"Category {category} should have questions"

    def test_all_difficulties_have_questions(self):
        """Each difficulty should have at least one question."""
        for difficulty in get_difficulties():
            result = get_questions(count=1, difficulty=difficulty)
            assert len(result) >= 1, f"Difficulty {difficulty} should have questions"
