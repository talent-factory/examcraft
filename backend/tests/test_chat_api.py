"""
Unit Tests für Chat API Endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import uuid


class TestChatAPI:
    """Test Suite für Chat API"""
    
    @pytest.fixture
    def client(self):
        """FastAPI Test Client"""
        from main import app
        return TestClient(app)
    
    @pytest.fixture
    def sample_documents(self, db_session):
        """Sample Documents für Tests"""
        from models.document import Document
        
        doc1 = Document(
            id=1,
            title="Test Dokument 1",
            filename="test1.pdf",
            mime_type="application/pdf",
            status="processed"
        )
        doc2 = Document(
            id=2,
            title="Test Dokument 2",
            filename="test2.pdf",
            mime_type="application/pdf",
            status="processed"
        )
        
        db_session.add(doc1)
        db_session.add(doc2)
        db_session.commit()
        
        return [doc1, doc2]
    
    def test_create_chat_session(self, client, sample_documents):
        """Test Chat-Session Erstellung"""
        response = client.post("/api/v1/chat/sessions", json={
            "document_ids": [1, 2],
            "title": "Test Chat"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["title"] == "Test Chat"
        assert len(data["document_ids"]) == 2
        assert data["message_count"] == 0
        assert data["is_exported_as_document"] is False
    
    def test_create_chat_session_auto_title(self, client, sample_documents):
        """Test Chat-Session mit automatischem Titel"""
        response = client.post("/api/v1/chat/sessions", json={
            "document_ids": [1, 2]
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "Chat mit 2 Dokumenten" in data["title"]
    
    def test_create_chat_session_invalid_documents(self, client):
        """Test Chat-Session mit ungültigen Dokumenten"""
        response = client.post("/api/v1/chat/sessions", json={
            "document_ids": [999, 1000],
            "title": "Test"
        })
        
        assert response.status_code == 404
        assert "nicht gefunden" in response.json()["detail"]
    
    def test_send_chat_message(self, client, sample_documents):
        """Test Nachricht senden"""
        # Erstelle Session
        session_response = client.post("/api/v1/chat/sessions", json={
            "document_ids": [1],
            "title": "Test Chat"
        })
        session_id = session_response.json()["id"]
        
        # Mock ChatBot Service
        with patch('api.v1.chat.chatbot_service.generate_response') as mock_generate:
            mock_generate.return_value = {
                "content": "Test Antwort",
                "sources": [],
                "confidence": 0.9
            }
            
            # Sende Nachricht
            response = client.post("/api/v1/chat/message", json={
                "session_id": session_id,
                "message": "Test Frage"
            })
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["role"] == "assistant"
            assert data["content"] == "Test Antwort"
            assert data["confidence"] == 0.9
    
    def test_get_chat_session(self, client, sample_documents):
        """Test Chat-Session abrufen"""
        # Erstelle Session
        session_response = client.post("/api/v1/chat/sessions", json={
            "document_ids": [1],
            "title": "Test Chat"
        })
        session_id = session_response.json()["id"]
        
        # Lade Session
        response = client.get(f"/api/v1/chat/sessions/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == session_id
        assert data["title"] == "Test Chat"
        assert isinstance(data["messages"], list)
    
    def test_get_nonexistent_session(self, client):
        """Test nicht-existierende Session abrufen"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/chat/sessions/{fake_id}")
        
        assert response.status_code == 404
    
    def test_list_chat_sessions(self, client, sample_documents):
        """Test Chat-Sessions auflisten"""
        # Erstelle mehrere Sessions
        for i in range(3):
            client.post("/api/v1/chat/sessions", json={
                "document_ids": [1],
                "title": f"Test Chat {i}"
            })
        
        # Liste Sessions
        response = client.get("/api/v1/chat/sessions")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 3
    
    def test_list_chat_sessions_pagination(self, client, sample_documents):
        """Test Chat-Sessions Pagination"""
        # Erstelle mehrere Sessions
        for i in range(5):
            client.post("/api/v1/chat/sessions", json={
                "document_ids": [1],
                "title": f"Test Chat {i}"
            })
        
        # Liste mit Limit
        response = client.get("/api/v1/chat/sessions?limit=2&offset=0")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) <= 2
    
    def test_delete_chat_session(self, client, sample_documents):
        """Test Chat-Session löschen"""
        # Erstelle Session
        session_response = client.post("/api/v1/chat/sessions", json={
            "document_ids": [1],
            "title": "Test Chat"
        })
        session_id = session_response.json()["id"]
        
        # Lösche Session
        response = client.delete(f"/api/v1/chat/sessions/{session_id}")
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Verify deleted
        get_response = client.get(f"/api/v1/chat/sessions/{session_id}")
        assert get_response.status_code == 404
    
    def test_export_chat_as_markdown(self, client, sample_documents):
        """Test Chat Export als Markdown"""
        # Erstelle Session mit Nachrichten
        session_response = client.post("/api/v1/chat/sessions", json={
            "document_ids": [1],
            "title": "Test Chat"
        })
        session_id = session_response.json()["id"]
        
        # Export
        response = client.post(
            f"/api/v1/chat/sessions/{session_id}/export",
            params={"export_format": "markdown"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["format"] == "markdown"
        assert "content" in data
        assert "filename" in data
        assert data["filename"].endswith(".md")
    
    def test_export_chat_as_json(self, client, sample_documents):
        """Test Chat Export als JSON"""
        # Erstelle Session
        session_response = client.post("/api/v1/chat/sessions", json={
            "document_ids": [1],
            "title": "Test Chat"
        })
        session_id = session_response.json()["id"]
        
        # Export
        response = client.post(
            f"/api/v1/chat/sessions/{session_id}/export",
            params={"export_format": "json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["format"] == "json"
        assert "content" in data
        assert data["filename"].endswith(".json")
    
    def test_export_invalid_format(self, client, sample_documents):
        """Test Export mit ungültigem Format"""
        session_response = client.post("/api/v1/chat/sessions", json={
            "document_ids": [1],
            "title": "Test Chat"
        })
        session_id = session_response.json()["id"]
        
        response = client.post(
            f"/api/v1/chat/sessions/{session_id}/export",
            params={"export_format": "invalid"}
        )
        
        assert response.status_code == 400
    
    def test_convert_chat_to_document(self, client, sample_documents):
        """Test Chat-zu-Dokument Konvertierung"""
        # Erstelle Session
        session_response = client.post("/api/v1/chat/sessions", json={
            "document_ids": [1],
            "title": "Test Chat"
        })
        session_id = session_response.json()["id"]
        
        # Konvertiere
        response = client.post(f"/api/v1/chat/sessions/{session_id}/to-document")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "document_id" in data
        assert "document_title" in data
        assert "Chat Wissen" in data["document_title"]

