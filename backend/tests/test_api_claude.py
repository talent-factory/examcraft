"""
Tests for the development-only Claude endpoints in main.py:
GET /api/v1/claude/health, GET /api/v1/claude/usage, POST /api/v1/generate-exam

All three answer 404 outside ENVIRONMENT=development. The Claude service is
mocked via main.get_claude_service, so no gateway call is made.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from main import app

USAGE_STATS = {
    "total_cost": 0.0,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "requests_last_minute": 0,
    "demo_mode": False,
}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def development(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")


def _mock_service(demo_mode=False):
    service = Mock()
    service.demo_mode = demo_mode
    service.model = "test-model"
    service.get_usage_stats.return_value = {**USAGE_STATS, "demo_mode": demo_mode}
    service.generate_questions = AsyncMock()
    return service


def test_claude_health_endpoint_healthy(client, development, monkeypatch):
    monkeypatch.setenv("LLM_GATEWAY_URL", "http://gateway.test")
    with patch("main.get_claude_service", return_value=_mock_service()):
        response = client.get("/api/v1/claude/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Claude API"
    assert data["demo_mode"] is False
    assert data["gateway_configured"] is True
    assert data["model"] == "test-model"
    assert data["usage"] == USAGE_STATS


def test_claude_health_endpoint_demo_mode(client, development, monkeypatch):
    monkeypatch.delenv("LLM_GATEWAY_URL", raising=False)
    with patch("main.get_claude_service", return_value=_mock_service(demo_mode=True)):
        response = client.get("/api/v1/claude/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "demo_mode"
    assert data["demo_mode"] is True
    assert data["gateway_configured"] is False


def test_claude_usage_endpoint(client, development):
    with patch("main.get_claude_service", return_value=_mock_service()):
        response = client.get("/api/v1/claude/usage")

    assert response.status_code == 200
    assert response.json() == USAGE_STATS


def test_generate_exam_endpoint_success(client, development):
    service = _mock_service()
    service.generate_questions.return_value = [
        {
            "id": "1",
            "type": "single_choice",
            "question": "Was ist Python?",
            "options": ["Sprache", "Schlange", "Framework", "Datenbank"],
            "correct_answer": "Sprache",
            "explanation": "Python ist eine Programmiersprache",
            "difficulty": "medium",
            "topic": "Python Grundlagen",
        }
    ]

    with patch("main.get_claude_service", return_value=service):
        response = client.post(
            "/api/v1/generate-exam",
            json={
                "topic": "Python Grundlagen",
                "difficulty": "medium",
                "question_count": 1,
                "question_types": ["single_choice"],
                "language": "de",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["topic"] == "Python Grundlagen"
    assert len(data["questions"]) == 1
    assert data["questions"][0]["question"] == "Was ist Python?"
    assert data["metadata"]["generated_by"] == "ExamCraft AI with Claude"
    service.generate_questions.assert_awaited_once_with(
        topic="Python Grundlagen",
        difficulty="medium",
        question_count=1,
        question_types=["single_choice"],
        language="de",
    )


def test_generate_exam_endpoint_service_error_returns_500(client, development):
    service = _mock_service()
    service.generate_questions.side_effect = RuntimeError("gateway down")

    with patch("main.get_claude_service", return_value=service):
        response = client.post(
            "/api/v1/generate-exam",
            json={"topic": "Python", "question_count": 1},
        )

    assert response.status_code == 500


def test_generate_exam_endpoint_missing_topic(client, development):
    response = client.post("/api/v1/generate-exam", json={"difficulty": "medium"})

    assert response.status_code == 422


@pytest.mark.parametrize(
    "method, path",
    [
        ("GET", "/api/v1/claude/health"),
        ("GET", "/api/v1/claude/usage"),
        ("POST", "/api/v1/generate-exam"),
    ],
)
def test_endpoints_are_hidden_outside_development(client, monkeypatch, method, path):
    monkeypatch.setenv("ENVIRONMENT", "production")
    service = _mock_service()

    with patch("main.get_claude_service", return_value=service):
        response = client.request(method, path, json={"topic": "Python"})

    assert response.status_code == 404
    service.get_usage_stats.assert_not_called()
    service.generate_questions.assert_not_called()
