/**
 * Unit Tests for ChatService
 * 
 * Tests API interactions for:
 * - Session creation
 * - Message sending
 * - Chat export (Markdown & JSON)
 * - Download functionality
 */

import ChatService from '../ChatService';

// Mock fetch globally
global.fetch = jest.fn();

describe('ChatService', () => {
  const mockAccessToken = 'test-access-token';
  const mockSessionId = 'test-session-id';
  
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
  });

  describe('createSession', () => {
    it('should create a new chat session', async () => {
      const mockSession = {
        id: mockSessionId,
        title: 'Test Chat',
        document_ids: [1, 2],
        message_count: 0,
        created_at: '2025-10-21T10:00:00Z',
        updated_at: '2025-10-21T10:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSession,
      });

      const result = await ChatService.createSession(
        mockAccessToken,
        'Test Chat',
        [1, 2]
      );

      expect(result).toEqual(mockSession);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/chat/sessions'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': `Bearer ${mockAccessToken}`,
            'Content-Type': 'application/json',
          }),
          body: JSON.stringify({
            title: 'Test Chat',
            document_ids: [1, 2],
          }),
        })
      );
    });

    it('should throw error on failed session creation', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Session creation failed' }),
      });

      await expect(
        ChatService.createSession(mockAccessToken, 'Test Chat', [1])
      ).rejects.toThrow('Session creation failed');
    });
  });

  describe('sendMessage', () => {
    it('should send a message and return assistant response', async () => {
      const mockResponse = {
        id: 'msg-123',
        session_id: mockSessionId,
        role: 'assistant',
        content: 'This is a test response',
        timestamp: '2025-10-21T10:05:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await ChatService.sendMessage(
        mockAccessToken,
        mockSessionId,
        'What is Heapsort?'
      );

      expect(result).toEqual(mockResponse);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/chat/message'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            session_id: mockSessionId,
            message: 'What is Heapsort?',
          }),
        })
      );
    });
  });

  describe('downloadChat', () => {
    it('should download chat as Markdown blob', async () => {
      const mockBlob = new Blob(['# Test Chat\n\nContent'], { type: 'text/markdown' });

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        blob: async () => mockBlob,
      });

      const result = await ChatService.downloadChat(
        mockAccessToken,
        mockSessionId,
        'markdown',
        'test-chat.md'
      );

      expect(result).toBeInstanceOf(Blob);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/v1/chat/sessions/${mockSessionId}/download`),
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Authorization': `Bearer ${mockAccessToken}`,
          }),
        })
      );
      
      // Verify URL contains format and filename parameters
      const callUrl = (global.fetch as jest.Mock).mock.calls[0][0];
      expect(callUrl).toContain('format=markdown');
      expect(callUrl).toContain('filename=test-chat.md');
    });

    it('should download chat as JSON blob', async () => {
      const mockBlob = new Blob(['{"session_id": "test"}'], { type: 'application/json' });

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        blob: async () => mockBlob,
      });

      const result = await ChatService.downloadChat(
        mockAccessToken,
        mockSessionId,
        'json',
        'test-chat.json'
      );

      expect(result).toBeInstanceOf(Blob);
      
      const callUrl = (global.fetch as jest.Mock).mock.calls[0][0];
      expect(callUrl).toContain('format=json');
      expect(callUrl).toContain('filename=test-chat.json');
    });

    it('should handle download without custom filename', async () => {
      const mockBlob = new Blob(['content'], { type: 'text/markdown' });

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        blob: async () => mockBlob,
      });

      await ChatService.downloadChat(
        mockAccessToken,
        mockSessionId,
        'markdown'
      );

      const callUrl = (global.fetch as jest.Mock).mock.calls[0][0];
      expect(callUrl).toContain('format=markdown');
      expect(callUrl).not.toContain('filename=');
    });

    it('should throw error on failed download', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Download failed' }),
      });

      await expect(
        ChatService.downloadChat(mockAccessToken, mockSessionId, 'markdown')
      ).rejects.toThrow('Download failed');
    });

    it('should properly encode special characters in filename', async () => {
      const mockBlob = new Blob(['content'], { type: 'text/markdown' });

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        blob: async () => mockBlob,
      });

      await ChatService.downloadChat(
        mockAccessToken,
        mockSessionId,
        'markdown',
        'chat-äöü-2025.md'
      );

      const callUrl = (global.fetch as jest.Mock).mock.calls[0][0];
      // Verify URL encoding
      expect(callUrl).toContain('filename=');
      expect(callUrl).toContain(encodeURIComponent('chat-äöü-2025.md'));
    });
  });

  describe('exportToDocument', () => {
    it('should export chat to document', async () => {
      const mockResponse = {
        document_id: 123,
        document_title: 'Chat Export',
        success: true,
        message: 'Export successful',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await ChatService.exportToDocument(
        mockAccessToken,
        mockSessionId
      );

      expect(result).toEqual(mockResponse);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/v1/chat/sessions/${mockSessionId}/to-document`),
        expect.objectContaining({
          method: 'POST',
        })
      );
    });
  });

  describe('listSessions', () => {
    it('should fetch all chat sessions', async () => {
      const mockSessions = [
        {
          id: 'session-1',
          title: 'Chat 1',
          document_ids: [1],
          message_count: 5,
          created_at: '2025-10-21T10:00:00Z',
          updated_at: '2025-10-21T10:30:00Z',
        },
        {
          id: 'session-2',
          title: 'Chat 2',
          document_ids: [2, 3],
          message_count: 10,
          created_at: '2025-10-21T11:00:00Z',
          updated_at: '2025-10-21T11:45:00Z',
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ sessions: mockSessions }),
      });

      const result = await ChatService.listSessions(mockAccessToken);

      expect(result).toEqual(mockSessions);
      expect(result).toHaveLength(2);
    });
  });
});

