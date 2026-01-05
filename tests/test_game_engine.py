"""Tests for game_engine module."""

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from game_engine import (
    start_game,
    get_current_question,
    submit_answer,
    is_game_over,
    get_final_score,
    _calculate_streak_multiplier,
    DIFFICULTY_POINTS,
    STREAK_BONUSES,
    STARTING_LIVES,
    Question,
    GameState,
)


# Fixtures and test data
@pytest.fixture
def sample_questions() -> list[Question]:
    """Create sample questions for testing."""
    return [
        {
            "question": "When did WWII end?",
            "options": ["1943", "1944", "1945", "1946"],
            "answer": 2,
            "explanation": "WWII ended in 1945.",
            "difficulty": "easy",
        },
        {
            "question": "Who was the first Roman Emperor?",
            "options": ["Julius Caesar", "Augustus", "Nero", "Caligula"],
            "answer": 1,
            "explanation": "Augustus became the first Emperor in 27 BC.",
            "difficulty": "medium",
        },
        {
            "question": "What year was the Magna Carta signed?",
            "options": ["1066", "1215", "1415", "1515"],
            "answer": 1,
            "explanation": "The Magna Carta was signed in 1215.",
            "difficulty": "hard",
        },
    ]


@pytest.fixture
def easy_questions() -> list[Question]:
    """Create easy questions for consistent scoring tests."""
    return [
        {
            "question": f"Easy question {i}",
            "options": ["A", "B", "C", "D"],
            "answer": 0,
            "explanation": "Answer is A.",
            "difficulty": "easy",
        }
        for i in range(15)
    ]


@pytest.fixture
def mixed_difficulty_questions() -> list[Question]:
    """Questions with mixed difficulties for scoring tests."""
    return [
        {"question": "Q1", "options": ["A", "B", "C", "D"], "answer": 0, "explanation": "E", "difficulty": "easy"},
        {"question": "Q2", "options": ["A", "B", "C", "D"], "answer": 0, "explanation": "E", "difficulty": "medium"},
        {"question": "Q3", "options": ["A", "B", "C", "D"], "answer": 0, "explanation": "E", "difficulty": "hard"},
    ]


@pytest.fixture
def game_state(sample_questions) -> GameState:
    """Create a fresh game state for testing."""
    return start_game(sample_questions)


class TestStartGame:
    """Tests for start_game function."""

    def test_returns_game_state(self, sample_questions):
        """Should return a GameState dict."""
        state = start_game(sample_questions)
        assert isinstance(state, dict)

    def test_initializes_questions(self, sample_questions):
        """Should store provided questions."""
        state = start_game(sample_questions)
        assert state["questions"] == sample_questions
        assert len(state["questions"]) == 3

    def test_starts_at_first_question(self, sample_questions):
        """Should start at question index 0."""
        state = start_game(sample_questions)
        assert state["current_question_index"] == 0

    def test_initializes_score_to_zero(self, sample_questions):
        """Should start with 0 score."""
        state = start_game(sample_questions)
        assert state["score"] == 0

    def test_initializes_lives(self, sample_questions):
        """Should start with STARTING_LIVES."""
        state = start_game(sample_questions)
        assert state["lives"] == STARTING_LIVES
        assert state["lives"] == 3

    def test_initializes_streak_to_zero(self, sample_questions):
        """Should start with 0 streak."""
        state = start_game(sample_questions)
        assert state["streak"] == 0

    def test_initializes_max_streak_to_zero(self, sample_questions):
        """Should start with 0 max_streak."""
        state = start_game(sample_questions)
        assert state["max_streak"] == 0

    def test_initializes_correct_answers_to_zero(self, sample_questions):
        """Should start with 0 correct answers."""
        state = start_game(sample_questions)
        assert state["correct_answers"] == 0

    def test_initializes_total_answered_to_zero(self, sample_questions):
        """Should start with 0 total answered."""
        state = start_game(sample_questions)
        assert state["total_answered"] == 0

    def test_empty_questions_list(self):
        """Should handle empty questions list."""
        state = start_game([])
        assert state["questions"] == []
        assert state["current_question_index"] == 0


class TestGetCurrentQuestion:
    """Tests for get_current_question function."""

    def test_returns_first_question(self, game_state, sample_questions):
        """Should return the first question initially."""
        question = get_current_question(game_state)
        assert question == sample_questions[0]

    def test_returns_correct_question_after_advance(self, game_state, sample_questions):
        """Should return question at current index."""
        game_state["current_question_index"] = 1
        question = get_current_question(game_state)
        assert question == sample_questions[1]

    def test_returns_none_when_exhausted(self, game_state):
        """Should return None when all questions answered."""
        game_state["current_question_index"] = len(game_state["questions"])
        question = get_current_question(game_state)
        assert question is None

    def test_returns_none_for_empty_questions(self):
        """Should return None for empty questions list."""
        state = start_game([])
        question = get_current_question(state)
        assert question is None

    def test_returns_none_when_index_exceeds_length(self, game_state):
        """Should return None when index exceeds questions length."""
        game_state["current_question_index"] = 100
        question = get_current_question(game_state)
        assert question is None


class TestCalculateStreakMultiplier:
    """Tests for _calculate_streak_multiplier function."""

    def test_no_streak_returns_one(self):
        """Should return 1.0 for no streak."""
        assert _calculate_streak_multiplier(0) == 1.0

    def test_streak_below_three_returns_one(self):
        """Should return 1.0 for streak 1-2."""
        assert _calculate_streak_multiplier(1) == 1.0
        assert _calculate_streak_multiplier(2) == 1.0

    def test_streak_three_returns_1_5(self):
        """Should return 1.5 at streak 3."""
        assert _calculate_streak_multiplier(3) == 1.5

    def test_streak_four_returns_1_5(self):
        """Streak 4 should still use 1.5 multiplier."""
        assert _calculate_streak_multiplier(4) == 1.5

    def test_streak_five_returns_2_0(self):
        """Should return 2.0 at streak 5."""
        assert _calculate_streak_multiplier(5) == 2.0

    def test_streak_between_five_and_ten(self):
        """Streaks 6-9 should use 2.0 multiplier."""
        for i in range(6, 10):
            assert _calculate_streak_multiplier(i) == 2.0

    def test_streak_ten_returns_3_0(self):
        """Should return 3.0 at streak 10."""
        assert _calculate_streak_multiplier(10) == 3.0

    def test_streak_above_ten_returns_3_0(self):
        """Streaks above 10 should use 3.0 multiplier."""
        assert _calculate_streak_multiplier(15) == 3.0
        assert _calculate_streak_multiplier(100) == 3.0


class TestSubmitAnswer:
    """Tests for submit_answer function."""

    def test_returns_tuple(self, game_state):
        """Should return a tuple of (bool, int, GameState)."""
        result = submit_answer(game_state, 2)
        assert isinstance(result, tuple)
        assert len(result) == 3
        is_correct, points, new_state = result
        assert isinstance(is_correct, bool)
        assert isinstance(points, int)
        assert isinstance(new_state, dict)

    def test_correct_answer_returns_true(self, game_state):
        """Should return True for correct answer."""
        # First question has answer=2
        is_correct, _, _ = submit_answer(game_state, 2)
        assert is_correct is True

    def test_wrong_answer_returns_false(self, game_state):
        """Should return False for wrong answer."""
        is_correct, _, _ = submit_answer(game_state, 0)
        assert is_correct is False

    def test_correct_answer_awards_points(self, game_state):
        """Should award points for correct answer."""
        # First question is easy (10 points)
        _, points, _ = submit_answer(game_state, 2)
        assert points == 10

    def test_wrong_answer_awards_zero_points(self, game_state):
        """Should award 0 points for wrong answer."""
        _, points, _ = submit_answer(game_state, 0)
        assert points == 0

    def test_advances_question_index(self, game_state):
        """Should advance to next question."""
        _, _, new_state = submit_answer(game_state, 2)
        assert new_state["current_question_index"] == 1

    def test_increments_total_answered(self, game_state):
        """Should increment total_answered count."""
        _, _, new_state = submit_answer(game_state, 2)
        assert new_state["total_answered"] == 1

    def test_correct_increments_correct_answers(self, game_state):
        """Should increment correct_answers for correct answer."""
        _, _, new_state = submit_answer(game_state, 2)
        assert new_state["correct_answers"] == 1

    def test_wrong_does_not_increment_correct_answers(self, game_state):
        """Should not increment correct_answers for wrong answer."""
        _, _, new_state = submit_answer(game_state, 0)
        assert new_state["correct_answers"] == 0

    def test_correct_increments_streak(self, game_state):
        """Should increment streak for correct answer."""
        _, _, new_state = submit_answer(game_state, 2)
        assert new_state["streak"] == 1

    def test_wrong_resets_streak(self, game_state):
        """Should reset streak to 0 for wrong answer."""
        # First build a streak
        _, _, state = submit_answer(game_state, 2)
        assert state["streak"] == 1
        # Then answer wrong
        _, _, new_state = submit_answer(state, 0)  # Q2 has answer=1
        assert new_state["streak"] == 0

    def test_wrong_decrements_lives(self, game_state):
        """Should decrement lives for wrong answer."""
        _, _, new_state = submit_answer(game_state, 0)
        assert new_state["lives"] == 2

    def test_correct_does_not_affect_lives(self, game_state):
        """Should not change lives for correct answer."""
        _, _, new_state = submit_answer(game_state, 2)
        assert new_state["lives"] == 3

    def test_updates_max_streak(self, game_state):
        """Should track maximum streak achieved."""
        _, _, state = submit_answer(game_state, 2)
        assert state["max_streak"] == 1
        _, _, state = submit_answer(state, 1)  # Q2 answer is 1
        assert state["max_streak"] == 2

    def test_max_streak_preserved_after_wrong(self, game_state):
        """Max streak should be preserved even after wrong answer."""
        # Build streak of 2
        _, _, state = submit_answer(game_state, 2)
        _, _, state = submit_answer(state, 1)
        assert state["max_streak"] == 2
        # Wrong answer
        _, _, state = submit_answer(state, 0)  # Q3 answer is 1
        assert state["streak"] == 0
        assert state["max_streak"] == 2  # Still 2

    def test_immutable_state_update(self, game_state):
        """Should not modify original state."""
        original_score = game_state["score"]
        original_lives = game_state["lives"]
        _, _, new_state = submit_answer(game_state, 2)
        assert game_state["score"] == original_score
        assert game_state["lives"] == original_lives
        assert new_state is not game_state

    def test_submit_when_no_question(self, game_state):
        """Should handle submission when no current question."""
        game_state["current_question_index"] = 100
        is_correct, points, new_state = submit_answer(game_state, 0)
        assert is_correct is False
        assert points == 0
        assert new_state == game_state


class TestScoringByDifficulty:
    """Tests for scoring based on difficulty levels."""

    def test_easy_question_base_points(self, easy_questions):
        """Easy questions should award 10 base points."""
        state = start_game(easy_questions)
        _, points, _ = submit_answer(state, 0)
        assert points == DIFFICULTY_POINTS["easy"]
        assert points == 10

    def test_medium_question_base_points(self):
        """Medium questions should award 20 base points."""
        questions = [
            {"question": "Q", "options": ["A", "B", "C", "D"], "answer": 0, "explanation": "E", "difficulty": "medium"}
        ]
        state = start_game(questions)
        _, points, _ = submit_answer(state, 0)
        assert points == DIFFICULTY_POINTS["medium"]
        assert points == 20

    def test_hard_question_base_points(self):
        """Hard questions should award 30 base points."""
        questions = [
            {"question": "Q", "options": ["A", "B", "C", "D"], "answer": 0, "explanation": "E", "difficulty": "hard"}
        ]
        state = start_game(questions)
        _, points, _ = submit_answer(state, 0)
        assert points == DIFFICULTY_POINTS["hard"]
        assert points == 30

    def test_unknown_difficulty_defaults_to_ten(self):
        """Unknown difficulty should default to 10 points."""
        questions = [
            {"question": "Q", "options": ["A", "B", "C", "D"], "answer": 0, "explanation": "E", "difficulty": "unknown"}
        ]
        state = start_game(questions)
        _, points, _ = submit_answer(state, 0)
        assert points == 10


class TestStreakBonusScoring:
    """Tests for streak bonus multipliers on scoring."""

    def test_no_bonus_at_streak_one(self, easy_questions):
        """First correct answer should not have bonus."""
        state = start_game(easy_questions)
        _, points, _ = submit_answer(state, 0)
        assert points == 10  # No multiplier

    def test_no_bonus_at_streak_two(self, easy_questions):
        """Second correct answer should not have bonus."""
        state = start_game(easy_questions)
        _, _, state = submit_answer(state, 0)
        _, points, _ = submit_answer(state, 0)
        assert points == 10  # Still no multiplier

    def test_1_5x_bonus_at_streak_three(self, easy_questions):
        """Third consecutive correct should get 1.5x bonus."""
        state = start_game(easy_questions)
        for _ in range(2):
            _, _, state = submit_answer(state, 0)
        _, points, _ = submit_answer(state, 0)
        assert points == 15  # 10 * 1.5

    def test_2x_bonus_at_streak_five(self, easy_questions):
        """Fifth consecutive correct should get 2x bonus."""
        state = start_game(easy_questions)
        for _ in range(4):
            _, _, state = submit_answer(state, 0)
        _, points, _ = submit_answer(state, 0)
        assert points == 20  # 10 * 2.0

    def test_3x_bonus_at_streak_ten(self, easy_questions):
        """Tenth consecutive correct should get 3x bonus."""
        state = start_game(easy_questions)
        for _ in range(9):
            _, _, state = submit_answer(state, 0)
        _, points, _ = submit_answer(state, 0)
        assert points == 30  # 10 * 3.0

    def test_bonus_applied_to_difficulty_points(self):
        """Streak bonus should multiply difficulty points."""
        # Hard question (30 points) at streak 3 (1.5x)
        hard_questions = [
            {"question": f"Q{i}", "options": ["A", "B", "C", "D"], "answer": 0, "explanation": "E", "difficulty": "hard"}
            for i in range(5)
        ]
        state = start_game(hard_questions)
        for _ in range(2):
            _, _, state = submit_answer(state, 0)
        _, points, _ = submit_answer(state, 0)
        assert points == 45  # 30 * 1.5

    def test_cumulative_score_with_streak(self, easy_questions):
        """Total score should accumulate with streak bonuses."""
        state = start_game(easy_questions)
        # Answer 5 correct in a row: 10 + 10 + 15 + 15 + 20 = 70
        for _ in range(5):
            _, _, state = submit_answer(state, 0)
        assert state["score"] == 70


class TestStreakReset:
    """Tests for streak reset behavior."""

    def test_streak_resets_on_wrong_answer(self, easy_questions):
        """Streak should reset to 0 after wrong answer."""
        state = start_game(easy_questions)
        # Build streak of 3
        for _ in range(3):
            _, _, state = submit_answer(state, 0)
        assert state["streak"] == 3
        # Wrong answer
        _, _, state = submit_answer(state, 1)  # Wrong
        assert state["streak"] == 0

    def test_bonus_lost_after_streak_reset(self, easy_questions):
        """Next correct answer after reset should not have bonus."""
        state = start_game(easy_questions)
        # Build streak of 3
        for _ in range(3):
            _, _, state = submit_answer(state, 0)
        # Wrong answer resets streak
        _, _, state = submit_answer(state, 1)
        # Next correct should have no bonus
        _, points, _ = submit_answer(state, 0)
        assert points == 10  # No multiplier

    def test_streak_can_be_rebuilt(self, easy_questions):
        """Can rebuild streak after reset."""
        state = start_game(easy_questions)
        # Build, reset, rebuild
        for _ in range(3):
            _, _, state = submit_answer(state, 0)
        _, _, state = submit_answer(state, 1)  # Reset
        for _ in range(3):
            _, _, state = submit_answer(state, 0)
        assert state["streak"] == 3
        _, points, _ = submit_answer(state, 0)
        assert points == 15  # 1.5x bonus


class TestLivesSystem:
    """Tests for lives management."""

    def test_starts_with_three_lives(self, game_state):
        """Should start with 3 lives."""
        assert game_state["lives"] == 3

    def test_lose_life_on_wrong_answer(self, game_state):
        """Should lose one life per wrong answer."""
        _, _, state = submit_answer(game_state, 0)  # Wrong
        assert state["lives"] == 2
        _, _, state = submit_answer(state, 0)  # Wrong
        assert state["lives"] == 1

    def test_lives_can_reach_zero(self, game_state):
        """Lives can decrease to zero."""
        state = game_state
        for _ in range(3):
            _, _, state = submit_answer(state, 0)  # All wrong
        assert state["lives"] == 0

    def test_lives_can_go_negative(self, sample_questions):
        """Implementation allows lives to go negative."""
        # This depends on whether game checks lives before processing
        state = start_game(sample_questions)
        state["lives"] = 0
        _, _, new_state = submit_answer(state, 0)
        assert new_state["lives"] == -1


class TestIsGameOver:
    """Tests for is_game_over function."""

    def test_not_over_at_start(self, game_state):
        """Game should not be over at start."""
        assert is_game_over(game_state) is False

    def test_over_when_lives_zero(self, game_state):
        """Game should be over when lives reach 0."""
        game_state["lives"] = 0
        assert is_game_over(game_state) is True

    def test_over_when_lives_negative(self, game_state):
        """Game should be over when lives negative."""
        game_state["lives"] = -1
        assert is_game_over(game_state) is True

    def test_over_when_all_questions_answered(self, sample_questions):
        """Game should be over when all questions answered."""
        state = start_game(sample_questions)
        state["current_question_index"] = len(sample_questions)
        assert is_game_over(state) is True

    def test_not_over_mid_game(self, game_state):
        """Game should not be over mid-game."""
        game_state["current_question_index"] = 1
        game_state["lives"] = 2
        assert is_game_over(game_state) is False

    def test_over_on_last_life_lost(self, sample_questions):
        """Game ends when last life is lost."""
        state = start_game(sample_questions)
        # Lose all 3 lives
        for _ in range(3):
            _, _, state = submit_answer(state, 3)  # All wrong
        assert is_game_over(state) is True

    def test_empty_questions_is_game_over(self):
        """Empty questions list should be game over."""
        state = start_game([])
        assert is_game_over(state) is True


class TestGetFinalScore:
    """Tests for get_final_score function."""

    def test_returns_dict(self, game_state):
        """Should return a dictionary."""
        result = get_final_score(game_state)
        assert isinstance(result, dict)

    def test_contains_score(self, game_state):
        """Should contain score field."""
        result = get_final_score(game_state)
        assert "score" in result
        assert result["score"] == 0

    def test_contains_correct_answers(self, game_state):
        """Should contain correct_answers field."""
        result = get_final_score(game_state)
        assert "correct_answers" in result

    def test_contains_total_answered(self, game_state):
        """Should contain total_answered field."""
        result = get_final_score(game_state)
        assert "total_answered" in result

    def test_contains_accuracy(self, game_state):
        """Should contain accuracy field."""
        result = get_final_score(game_state)
        assert "accuracy" in result

    def test_contains_max_streak(self, game_state):
        """Should contain max_streak field."""
        result = get_final_score(game_state)
        assert "max_streak" in result

    def test_contains_lives_remaining(self, game_state):
        """Should contain lives_remaining field."""
        result = get_final_score(game_state)
        assert "lives_remaining" in result

    def test_contains_completed(self, game_state):
        """Should contain completed field."""
        result = get_final_score(game_state)
        assert "completed" in result

    def test_accuracy_calculation(self, sample_questions):
        """Should calculate accuracy correctly."""
        state = start_game(sample_questions)
        # Answer 2 correct, 1 wrong
        _, _, state = submit_answer(state, 2)  # Correct
        _, _, state = submit_answer(state, 1)  # Correct
        _, _, state = submit_answer(state, 0)  # Wrong
        result = get_final_score(state)
        assert result["accuracy"] == 66.7  # 2/3 * 100 = 66.666...

    def test_accuracy_zero_when_no_answers(self, game_state):
        """Accuracy should be 0 when no questions answered."""
        result = get_final_score(game_state)
        assert result["accuracy"] == 0.0

    def test_accuracy_100_when_all_correct(self, sample_questions):
        """Accuracy should be 100 when all correct."""
        state = start_game(sample_questions)
        _, _, state = submit_answer(state, 2)
        _, _, state = submit_answer(state, 1)
        _, _, state = submit_answer(state, 1)
        result = get_final_score(state)
        assert result["accuracy"] == 100.0

    def test_completed_true_when_all_answered(self, sample_questions):
        """Completed should be true when all questions answered."""
        state = start_game(sample_questions)
        for answer in [2, 1, 1]:
            _, _, state = submit_answer(state, answer)
        result = get_final_score(state)
        assert result["completed"] is True

    def test_completed_false_when_game_over_early(self, sample_questions):
        """Completed should be false when game ends early."""
        state = start_game(sample_questions)
        # Lose all lives on first question
        state["lives"] = 1
        _, _, state = submit_answer(state, 0)  # Wrong, game over
        result = get_final_score(state)
        assert result["completed"] is False


class TestGameStateTransitions:
    """Tests for complete game state transitions."""

    def test_full_game_all_correct(self, sample_questions):
        """Test complete game with all correct answers."""
        state = start_game(sample_questions)
        correct_answers = [2, 1, 1]

        for answer in correct_answers:
            is_correct, _, state = submit_answer(state, answer)
            assert is_correct is True

        assert is_game_over(state) is True
        result = get_final_score(state)
        assert result["completed"] is True
        assert result["correct_answers"] == 3
        assert result["lives_remaining"] == 3

    def test_full_game_all_wrong(self, sample_questions):
        """Test complete game with all wrong answers."""
        state = start_game(sample_questions)

        for _ in range(3):
            is_correct, _, state = submit_answer(state, 3)  # Always wrong
            assert is_correct is False

        assert is_game_over(state) is True
        result = get_final_score(state)
        assert result["completed"] is False  # Ran out of lives
        assert result["correct_answers"] == 0
        assert result["lives_remaining"] == 0

    def test_game_ends_on_lives_not_questions(self, easy_questions):
        """Game can end due to lives before questions exhausted."""
        state = start_game(easy_questions)  # 15 questions

        # Answer 3 wrong
        for _ in range(3):
            _, _, state = submit_answer(state, 1)  # Wrong

        assert is_game_over(state) is True
        assert state["current_question_index"] == 3  # Only answered 3
        result = get_final_score(state)
        assert result["completed"] is False

    def test_mixed_answers_scoring(self, mixed_difficulty_questions):
        """Test scoring with mixed difficulties and outcomes."""
        state = start_game(mixed_difficulty_questions)

        # Correct easy (10), wrong medium (0, lose life), correct hard (30)
        _, points1, state = submit_answer(state, 0)  # Easy correct
        assert points1 == 10

        _, points2, state = submit_answer(state, 1)  # Medium wrong
        assert points2 == 0

        _, points3, state = submit_answer(state, 0)  # Hard correct (no streak bonus, reset)
        assert points3 == 30

        assert state["score"] == 40
        assert state["lives"] == 2


class TestEdgeCases:
    """Edge case tests."""

    def test_single_question_game(self):
        """Test game with single question."""
        questions = [
            {"question": "Q", "options": ["A", "B", "C", "D"], "answer": 0, "explanation": "E", "difficulty": "easy"}
        ]
        state = start_game(questions)
        _, _, state = submit_answer(state, 0)
        assert is_game_over(state) is True
        result = get_final_score(state)
        assert result["completed"] is True

    def test_zero_questions_game(self):
        """Test game with no questions."""
        state = start_game([])
        assert is_game_over(state) is True
        question = get_current_question(state)
        assert question is None

    def test_answer_index_out_of_bounds(self, game_state):
        """Test submitting answer index that might be out of bounds."""
        # The implementation doesn't validate answer range
        is_correct, _, _ = submit_answer(game_state, 99)
        assert is_correct is False

    def test_negative_answer_index(self, game_state):
        """Test submitting negative answer index."""
        is_correct, _, _ = submit_answer(game_state, -1)
        # Python negative indexing might make this "correct" depending on answer
        # This tests the actual behavior
        assert isinstance(is_correct, bool)

    def test_very_long_streak(self, easy_questions):
        """Test very long streak maintains max bonus."""
        state = start_game(easy_questions)
        for _ in range(14):
            _, points, state = submit_answer(state, 0)

        # After 10, should stay at 3x
        assert state["streak"] == 14
        _, last_points, _ = submit_answer(state, 0)
        assert last_points == 30  # 10 * 3.0

    def test_state_after_game_over(self, sample_questions):
        """Test behavior when submitting after game over."""
        state = start_game(sample_questions)
        state["lives"] = 0  # Manually set game over

        is_correct, points, new_state = submit_answer(state, 0)
        # Implementation still processes the answer
        assert isinstance(is_correct, bool)

    def test_final_score_with_zero_division(self):
        """Test final score doesn't crash with 0 total_answered."""
        state = start_game([])
        result = get_final_score(state)
        assert result["accuracy"] == 0.0


class TestConstants:
    """Tests for module constants."""

    def test_difficulty_points_values(self):
        """Verify difficulty point values."""
        assert DIFFICULTY_POINTS["easy"] == 10
        assert DIFFICULTY_POINTS["medium"] == 20
        assert DIFFICULTY_POINTS["hard"] == 30

    def test_streak_bonus_values(self):
        """Verify streak bonus multiplier values."""
        assert STREAK_BONUSES[3] == 1.5
        assert STREAK_BONUSES[5] == 2.0
        assert STREAK_BONUSES[10] == 3.0

    def test_starting_lives_value(self):
        """Verify starting lives constant."""
        assert STARTING_LIVES == 3
