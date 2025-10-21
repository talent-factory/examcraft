import React, { useState, useEffect } from 'react';
import { Box, Container, Typography, Button, Dialog, DialogContent, DialogTitle, IconButton } from '@mui/material';
import { MessageSquare, X, Trash2 } from 'lucide-react';
import { DocumentSelector } from './DocumentSelector';
import { ChatInterface } from './ChatInterface';
import { useAuth } from '../../contexts/AuthContext';
import ChatService from '../../services/ChatService';

interface Document {
  id: number;
  title: string;
  filename: string;
  status: string;
}

interface ChatSession {
  id: string;
  title: string;
  document_ids: number[];
  message_count: number;
  created_at: string;
  updated_at: string;
}

export const DocumentChatPage: React.FC = () => {
  const { accessToken } = useAuth();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [showDocumentSelector, setShowDocumentSelector] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!accessToken) return;
    loadDocuments();
    loadChatSessions();
  }, [accessToken]);

  const loadDocuments = async () => {
    if (!accessToken) return;
    try {
      const response = await fetch('/api/v1/documents/', {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });
      const data = await response.json();
      // API returns { documents: [...], total: N }
      const docs = data.documents || data;
      setDocuments(Array.isArray(docs) ? docs.filter((doc: Document) => doc.status === 'processed') : []);
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  };

  const loadChatSessions = async () => {
    if (!accessToken) return;
    try {
      const sessions = await ChatService.listSessions(accessToken);
      setChatSessions(sessions);
    } catch (error) {
      console.error('Failed to load chat sessions:', error);
      setChatSessions([]);
    }
  };

  const handleStartChat = async (documentIds: number[], title: string) => {
    if (!accessToken) return;
    setIsLoading(true);
    try {
      const newSession = await ChatService.createSession(accessToken, title, documentIds);
      setCurrentSessionId(newSession.id);
      setShowDocumentSelector(false);
      loadChatSessions(); // Refresh list
    } catch (error) {
      console.error('Failed to create chat session:', error);
      alert('Fehler beim Erstellen der Chat-Session');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenSession = (sessionId: string) => {
    setCurrentSessionId(sessionId);
  };

  const handleCloseChat = () => {
    setCurrentSessionId(null);
    loadChatSessions(); // Refresh list
  };

  const handleDeleteSession = async (sessionId: string, event: React.MouseEvent) => {
    if (!accessToken) return;
    event.stopPropagation(); // Verhindere onClick auf Parent

    if (!window.confirm('Möchten Sie diese Chat-Session wirklich löschen?')) {
      return;
    }

    try {
      await ChatService.deleteSession(accessToken, sessionId);

      // Wenn aktuell geöffnet, schließen
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
      }

      loadChatSessions(); // Refresh list
    } catch (error) {
      console.error('Failed to delete chat session:', error);
      alert('Fehler beim Löschen der Chat-Session');
    }
  };

  const currentSession = chatSessions.find(s => s.id === currentSessionId);

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box mb={4}>
        <Typography variant="h4" gutterBottom>
          📚 Dokument ChatBot
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Stelle Fragen zu deinen hochgeladenen Dokumenten und erhalte KI-gestützte Antworten mit Quellenreferenzen.
        </Typography>
      </Box>

      {/* Action Buttons */}
      <Box mb={4} display="flex" gap={2}>
        <Button
          variant="contained"
          startIcon={<MessageSquare />}
          onClick={() => setShowDocumentSelector(true)}
          disabled={documents.length === 0}
        >
          Neuer Chat
        </Button>
      </Box>

      {/* Current Chat */}
      {currentSessionId && currentSession && (
        <Box mb={4}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">{currentSession.title}</Typography>
            <IconButton onClick={handleCloseChat} size="small">
              <X size={20} />
            </IconButton>
          </Box>
          <ChatInterface
            sessionId={currentSessionId}
            documentIds={currentSession.document_ids}
            onClose={handleCloseChat}
          />
        </Box>
      )}

      {/* Chat Sessions List */}
      {!currentSessionId && (
        <Box>
          <Typography variant="h6" gutterBottom>
            Deine Chat-Sessions
          </Typography>
          
          {chatSessions.length === 0 ? (
            <Box 
              sx={{ 
                p: 4, 
                textAlign: 'center', 
                bgcolor: 'background.paper', 
                borderRadius: 2,
                border: '1px dashed',
                borderColor: 'divider'
              }}
            >
              <MessageSquare size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
              <Typography variant="body1" color="text.secondary">
                Noch keine Chat-Sessions vorhanden.
              </Typography>
              <Typography variant="body2" color="text.secondary" mt={1}>
                Klicke auf "Neuer Chat" um zu starten.
              </Typography>
            </Box>
          ) : (
            <Box display="flex" flexDirection="column" gap={2}>
              {chatSessions.map(session => (
                <Box
                  key={session.id}
                  sx={{
                    p: 2,
                    bgcolor: 'background.paper',
                    borderRadius: 2,
                    border: '1px solid',
                    borderColor: 'divider',
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    '&:hover': { bgcolor: 'action.hover' }
                  }}
                  onClick={() => handleOpenSession(session.id)}
                >
                  <Box flex={1}>
                    <Typography variant="h6">{session.title}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {session.message_count} Nachrichten • {session.document_ids.length} Dokument(e)
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Zuletzt aktualisiert: {new Date(session.updated_at).toLocaleString('de-CH')}
                    </Typography>
                  </Box>
                  <IconButton
                    size="small"
                    color="error"
                    onClick={(e) => handleDeleteSession(session.id, e)}
                    sx={{ ml: 2 }}
                    title="Chat löschen"
                  >
                    <Trash2 size={18} />
                  </IconButton>
                </Box>
              ))}
            </Box>
          )}
        </Box>
      )}

      {/* Document Selector Dialog */}
      <Dialog 
        open={showDocumentSelector} 
        onClose={() => setShowDocumentSelector(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">Neuer Chat</Typography>
            <IconButton onClick={() => setShowDocumentSelector(false)} size="small">
              <X size={20} />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          <DocumentSelector
            documents={documents}
            onStartChat={handleStartChat}
          />
        </DialogContent>
      </Dialog>
    </Container>
  );
};

