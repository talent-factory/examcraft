/**
 * Chat Service
 * API client for Document ChatBot functionality
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface Document {
  id: number;
  title: string;
  filename: string;
  status: string;
}

export interface ChatSession {
  id: string;
  title: string;
  document_ids: number[];
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Array<{
    document_id: number;
    filename: string;
    similarity_score: number;
  }>;
  confidence?: number;
  timestamp: string;
}

export interface ChatRequest {
  session_id: string;
  message: string;
}

export interface ChatSessionCreate {
  title: string;
  document_ids: number[];
}

export interface ChatExportRequest {
  session_id: string;
  format: 'markdown' | 'pdf';
}

class ChatService {
  /**
   * Create a new chat session
   */
  async createSession(
    accessToken: string,
    title: string,
    documentIds: number[]
  ): Promise<ChatSession> {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        title,
        document_ids: documentIds,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create chat session');
    }

    return response.json();
  }

  /**
   * Get all chat sessions for current user
   */
  async listSessions(accessToken: string): Promise<ChatSession[]> {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to load chat sessions');
    }

    const data = await response.json();
    return data.sessions || [];
  }

  /**
   * Get a specific chat session
   */
  async getSession(accessToken: string, sessionId: string): Promise<ChatSession> {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions/${sessionId}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to load chat session');
    }

    return response.json();
  }

  /**
   * Send a message to the chatbot
   */
  async sendMessage(
    accessToken: string,
    sessionId: string,
    message: string
  ): Promise<ChatMessage> {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat/message`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        message,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to send message');
    }

    return response.json();
  }

  /**
   * Get chat history for a session
   */
  async getHistory(accessToken: string, sessionId: string): Promise<ChatMessage[]> {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions/${sessionId}/messages`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to load chat history');
    }

    const data = await response.json();
    return data.messages || [];
  }

  /**
   * Delete a chat session
   */
  async deleteSession(accessToken: string, sessionId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete chat session');
    }
  }

  /**
   * Export chat session to document
   */
  async exportToDocument(
    accessToken: string,
    sessionId: string
  ): Promise<{ document_id: number }> {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions/${sessionId}/to-document`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to export chat to document');
    }

    return response.json();
  }

  /**
   * Download chat session as markdown
   */
  async downloadAsMarkdown(accessToken: string, sessionId: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat/sessions/${sessionId}/download`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to download chat');
    }

    return response.blob();
  }
}

export default new ChatService();

