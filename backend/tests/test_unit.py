"""Pure unit tests (no database)."""
from app.core.security import (
    TokenType,
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.ai.question_validator import validate_question
from app.ai.document_processor import _clean_text
from app.models.enums import DifficultyLevel
from app.services.quiz_service import compute_distribution


def test_password_hash_roundtrip():
    h = hash_password("Secret@123")
    assert h != "Secret@123"
    assert verify_password("Secret@123", h)
    assert not verify_password("wrong", h)


def test_jwt_encode_decode():
    token = create_access_token(42, "admin")
    payload = decode_token(token, TokenType.ACCESS)
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"


def test_clean_text_collapses_whitespace():
    assert _clean_text("a\n\n\n\nb   c") == "a\n\nb c"


def test_question_validator_rejects_missing_correct():
    q = {
        "question_type": "mcq",
        "difficulty": "easy",
        "question_text": "What is POSH about?",
        "options": ["A", "B", "C", "D"],
        "correct_answer": "Z",  # not in options
    }
    ok, reason = validate_question(q)
    assert not ok
    assert "correct_answer" in reason


def test_question_validator_accepts_valid():
    q = {
        "question_type": "true_false",
        "difficulty": "medium",
        "question_text": "POSH protects employees.",
        "options": ["True", "False"],
        "correct_answer": "True",
    }
    ok, _ = validate_question(q)
    assert ok


def test_difficulty_distribution_ratio():
    plan = compute_distribution(10, {
        DifficultyLevel.EASY: 100,
        DifficultyLevel.MEDIUM: 100,
        DifficultyLevel.HARD: 100,
    })
    assert plan[DifficultyLevel.EASY] == 4
    assert plan[DifficultyLevel.MEDIUM] == 4
    assert plan[DifficultyLevel.HARD] == 2
    assert sum(plan.values()) == 10


def test_difficulty_distribution_fills_when_bucket_short():
    plan = compute_distribution(10, {
        DifficultyLevel.EASY: 2,
        DifficultyLevel.MEDIUM: 100,
        DifficultyLevel.HARD: 0,
    })
    assert sum(plan.values()) == 10
    assert plan[DifficultyLevel.EASY] <= 2
    assert plan[DifficultyLevel.HARD] == 0
