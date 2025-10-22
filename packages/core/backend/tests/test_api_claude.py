"""
Tests für Claude API Endpoints - Health Check und Usage Statistics
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from main import app


class TestClaudeAPIEndpoints:
    """Test Suite für Claude API Endpoints"""

    @pytest.fixture
    def client(self):
        """Test Client Fixture"""
        return TestClient(app)

    @pytest.fixture
    def mock_claude_service(self):
        """Mock Claude Service Fixture"""
        mock_service = Mock()
        mock_service.api_key = "test-api-key"
        mock_service.model = "claude-3-sonnet-20240229"
        mock_service.get_usage_stats.return_value = {
            "total_cost": 0.0456,
            "total_input_tokens": 1500,
            "total_output_tokens": 800,
            "requests_last_minute": 3,
            "demo_mode": False,
        }
        return mock_service

    def test_claude_health_endpoint_healthy(self, client, mock_claude_service):
        """Test Claude Health Endpoint - Healthy Status"""
        with patch("main.claude_service", mock_claude_service):
            response = client.get("/api/v1/claude/health")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "healthy"
            assert data["service"] == "Claude API"
            assert not data["demo_mode"]
            assert data["api_key_configured"]
            assert data["model"] == "claude-3-sonnet-20240229"
            assert "usage" in data

    def test_claude_health_endpoint_demo_mode(self, client):
        """Test Claude Health Endpoint - Demo Mode"""
        mock_service = Mock()
        mock_service.api_key = None
        mock_service.model = "claude-3-sonnet-20240229"
        mock_service.get_usage_stats.return_value = {
            "total_cost": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "requests_last_minute": 0,
            "demo_mode": True,
        }

        with patch("main.claude_service", mock_service):
            response = client.get("/api/v1/claude/health")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "demo_mode"
            assert data["demo_mode"]
            assert not data["api_key_configured"]

    def test_claude_usage_endpoint(self, client, mock_claude_service):
        """Test Claude Usage Statistics Endpoint"""
        with patch("main.claude_service", mock_claude_service):
            response = client.get("/api/v1/claude/usage")

            assert response.status_code == 200
            data = response.json()

            assert data["total_cost"] == 0.0456
            assert data["total_input_tokens"] == 1500
            assert data["total_output_tokens"] == 800
            assert data["requests_last_minute"] == 3
            assert not data["demo_mode"]

    def test_claude_usage_endpoint_demo_mode(self, client):
        """Test Claude Usage Endpoint im Demo Mode"""
        mock_service = Mock()
        mock_service.get_usage_stats.return_value = {
            "total_cost": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "requests_last_minute": 0,
            "demo_mode": True,
        }

        with patch("main.claude_service", mock_service):
            response = client.get("/api/v1/claude/usage")

            assert response.status_code == 200
            data = response.json()

            assert data["total_cost"] == 0.0
            assert data["demo_mode"]

    def test_generate_exam_endpoint_with_claude_success(
        self, client, mock_claude_service
    ):
        """Test Exam Generation mit erfolgreichem Claude API Call"""
        # Mock successful question generation
        mock_claude_service.generate_questions.return_value = [
            {
                "id": "1",
                "type": "multiple_choice",
                "question": "Was ist Python?",
                "options": ["Sprache", "Schlange", "Framework", "Datenbank"],
                "correct_answer": "Sprache",
                "explanation": "Python ist eine Programmiersprache",
                "difficulty": "medium",
                "topic": "Python Grundlagen",
            }
        ]

        with patch("main.claude_service", mock_claude_service):
            response = client.post(
                "/api/v1/generate-exam",
                json={
                    "topic": "Python Grundlagen",
                    "difficulty": "medium",
                    "question_count": 1,
                    "question_types": ["multiple_choice"],
                    "language": "de",
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert data["topic"] == "Python Grundlagen"
            assert len(data["questions"]) == 1
            assert data["questions"][0]["question"] == "Was ist Python?"
            assert "metadata" in data

    def test_generate_exam_endpoint_fallback_to_demo(self, client):
        """Test Exam Generation mit Fallback zu Demo Mode"""
        mock_service = Mock()
        mock_service.generate_questions.side_effect = Exception("API Error")

        with patch("main.claude_service", mock_service):
            response = client.post(
                "/api/v1/generate-exam",
                json={"topic": "Python", "difficulty": "medium", "question_count": 1},
            )

            # Should still return 200 with demo questions
            assert response.status_code == 200

    def test_generate_exam_endpoint_invalid_request(self, client):
        """Test Exam Generation mit invaliden Daten"""
        response = client.post(
            "/api/v1/generate-exam",
            json={
                "topic": "",  # Leeres Topic
                "difficulty": "invalid",  # Invalide Schwierigkeit
                "question_count": -1,  # Negative Anzahl
            },
        )

        assert response.status_code == 422  # Validation Error

    def test_generate_exam_endpoint_missing_fields(self, client):
        """Test Exam Generation mit fehlenden Feldern"""
        response = client.post(
            "/api/v1/generate-exam",
            json={
                # Fehlendes topic
                "difficulty": "medium"
            },
        )

        assert response.status_code == 422  # Validation Error


class TestClaudeServiceEndToEnd:
    """End-to-End Tests für Claude Service Integration"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_full_exam_generation_workflow(self, client):
        """Test kompletter Exam Generation Workflow"""
        # Test 1: Health Check
        health_response = client.get("/api/v1/claude/health")
        assert health_response.status_code == 200

        # Test 2: Usage Stats (sollte initial 0 sein)
        usage_response = client.get("/api/v1/claude/usage")
        assert usage_response.status_code == 200
        usage_response.json()

        # Test 3: Exam Generation
        exam_response = client.post(
            "/api/v1/generate-exam",
            json={
                "topic": "Software Testing",
                "difficulty": "medium",
                "question_count": 2,
                "question_types": ["multiple_choice", "open_ended"],
                "language": "de",
            },
        )

        assert exam_response.status_code == 200
        exam_data = exam_response.json()

        assert exam_data["topic"] == "Software Testing"
        assert len(exam_data["questions"]) == 2
        assert "exam_id" in exam_data
        assert "created_at" in exam_data

        # Test 4: Usage Stats nach Exam Generation
        final_usage_response = client.get("/api/v1/claude/usage")
        assert final_usage_response.status_code == 200
        final_usage_response.json()

        # Im Demo Mode sollten sich die Stats nicht ändern
        # Im echten API Mode würden sich Token Counts erhöhen

    def test_concurrent_requests_rate_limiting(self, client):
        """Test Rate Limiting bei gleichzeitigen Requests"""
        import concurrent.futures

        def make_request():
            return client.post(
                "/api/v1/generate-exam",
                json={
                    "topic": "Concurrent Testing",
                    "difficulty": "easy",
                    "question_count": 1,
                },
            )

        # Sende mehrere gleichzeitige Requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [future.result() for future in futures]

        # Alle Requests sollten erfolgreich sein (Demo Mode oder Rate Limiting)
        for response in responses:
            assert response.status_code in [200, 429]  # 429 = Rate Limited

    def test_error_handling_and_recovery(self, client):
        """Test Error Handling und Recovery"""
        # Test mit verschiedenen invaliden Inputs
        test_cases = [
            {
                "topic": "A" * 1000,
                "difficulty": "medium",
                "question_count": 1,
            },  # Sehr langes Topic
            {
                "topic": "Test",
                "difficulty": "medium",
                "question_count": 100,
            },  # Zu viele Fragen
            {
                "topic": "Test",
                "difficulty": "impossible",
                "question_count": 1,
            },  # Invalide Schwierigkeit
        ]

        for test_case in test_cases:
            response = client.post("/api/v1/generate-exam", json=test_case)
            # Sollte entweder validiert werden (422) oder erfolgreich sein (200)
            assert response.status_code in [200, 422]


if __name__ == "__main__":
    pytest.main([__file__])
