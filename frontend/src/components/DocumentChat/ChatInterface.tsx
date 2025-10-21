import React, { useState, useEffect, useRef } from 'react';
import { Send, FileText, Loader2, Download, FileDown } from 'lucide-react';
import { Button } from '@mui/material';
import { TextField, Card, CardContent, CardHeader, Typography, Box, Chip, IconButton, Dialog, DialogTitle, DialogContent, DialogActions } from '@mui/material';
import MarkdownRenderer from '../MarkdownRenderer';
import { useAuth } from '../../contexts/AuthContext';
import ChatService from '../../services/ChatService';

// Use ChatMessage from ChatService
import type { ChatMessage } from '../../services/ChatService';

interface ChatInterfaceProps {
  sessionId: string;
  documentIds: number[];
  onClose?: () => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  sessionId,
  documentIds,
  onClose
}) => {
  const { accessToken } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionTitle, setSessionTitle] = useState('');
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [exportFileName, setExportFileName] = useState('');
  const [exportFormat, setExportFormat] = useState<'markdown' | 'json'>('markdown');
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll zu neuesten Nachrichten
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Chat-Historie laden
  useEffect(() => {
    if (!accessToken) return;

    const loadChatHistory = async () => {
      try {
        const session = await ChatService.getSession(accessToken, sessionId);
        setMessages(session.messages || []);
        setSessionTitle(session.title || '');
      } catch (error) {
        console.error('Failed to load chat history:', error);
        setMessages([]);
      }
    };

    loadChatHistory();
  }, [sessionId, accessToken]);

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading || !accessToken) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString(),
    };

    const messageContent = inputMessage;
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const assistantMessage = await ChatService.sendMessage(accessToken, sessionId, messageContent);
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      // Error handling - zeige Fehlermeldung
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '⚠️ Fehler beim Senden der Nachricht. Bitte versuche es erneut.',
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportClick = (format: 'markdown' | 'json') => {
    // Setze Standard-Dateinamen basierend auf Chat-Titel
    const defaultName = sessionTitle || `chat_${new Date().toISOString().split('T')[0]}`;
    const extension = format === 'json' ? 'json' : 'md';
    setExportFileName(`${defaultName}.${extension}`);
    setExportFormat(format);
    setShowExportDialog(true);
  };

  const handleExportConfirm = async () => {
    if (!accessToken || !exportFileName.trim()) return;

    try {
      // Stelle sicher, dass der Dateiname die richtige Endung hat
      const fileExtension = exportFormat === 'json' ? '.json' : '.md';
      const finalFileName = exportFileName.endsWith(fileExtension)
        ? exportFileName
        : `${exportFileName}${fileExtension}`;

      // Download content from backend
      const url = `http://localhost:8000/api/v1/chat/sessions/${sessionId}/download?format=${exportFormat}&filename=${encodeURIComponent(finalFileName)}`;

      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Download failed: ${response.statusText}`);
      }

      const blob = await response.blob();

      // WICHTIGER FIX: Erstelle einen data-URL statt blob-URL
      // Dies zwingt den Browser, den download-Attribut zu respektieren
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = reader.result as string;
        const downloadLink = document.createElement('a');
        downloadLink.href = dataUrl;
        downloadLink.download = finalFileName;
        downloadLink.style.display = 'none';

        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
      };
      reader.readAsDataURL(blob);

      setShowExportDialog(false);
    } catch (error) {
      console.error('Export failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unbekannter Fehler';
      alert(`❌ Export fehlgeschlagen: ${errorMessage}`);
    }
  };

  const handleConvertToDocument = async () => {
    if (!accessToken) return;
    try {
      const result = await ChatService.exportToDocument(accessToken, sessionId);
      alert(`✅ Chat wurde als Dokument gespeichert: "${result.document_title || 'Neues Dokument'}"`);
    } catch (error) {
      console.error('Conversion failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unbekannter Fehler';
      alert(`❌ Konvertierung fehlgeschlagen: ${errorMessage}`);
    }
  };

  return (
    <Card sx={{ display: 'flex', flexDirection: 'column', height: '600px' }}>
      <CardHeader
        title={
          <Box display="flex" alignItems="center" gap={1}>
            <FileText size={20} />
            <Typography variant="h6">Dokument Chat</Typography>
            <Chip 
              label={`${documentIds.length} Dokument(e)`} 
              size="small" 
              sx={{ ml: 'auto' }}
            />
          </Box>
        }
        action={
          <Box>
            <IconButton onClick={() => handleExportClick('markdown')} title="Als Markdown exportieren">
              <Download size={20} />
            </IconButton>
            <IconButton onClick={handleConvertToDocument} title="Als Dokument speichern">
              <FileDown size={20} />
            </IconButton>
          </Box>
        }
      />
      
      <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2, overflow: 'hidden' }}>
        {/* Chat Messages */}
        <Box sx={{ flex: 1, overflowY: 'auto', pr: 1 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {messages.map((msg, idx) => (
              <ChatMessageBubble key={idx} message={msg} />
            ))}
            {isLoading && (
              <Box display="flex" alignItems="center" gap={1} color="text.secondary">
                <Loader2 size={16} className="animate-spin" />
                <Typography variant="body2">Denkt nach...</Typography>
              </Box>
            )}
            <div ref={scrollRef} />
          </Box>
        </Box>

        {/* Input Area */}
        <Box display="flex" gap={1}>
          <TextField
            fullWidth
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder="Stelle eine Frage zu deinen Dokumenten..."
            disabled={isLoading}
            multiline
            maxRows={3}
            size="small"
          />
          <Button 
            onClick={sendMessage} 
            disabled={isLoading || !inputMessage.trim()}
            variant="contained"
            sx={{ minWidth: '50px' }}
          >
            <Send size={20} />
          </Button>
        </Box>
      </CardContent>

      {/* Export Dialog */}
      <Dialog open={showExportDialog} onClose={() => setShowExportDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          Chat als {exportFormat === 'json' ? 'JSON' : 'Markdown'} exportieren
        </DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
            Geben Sie einen Namen für die Datei ein:
          </Typography>
          <TextField
            fullWidth
            value={exportFileName}
            onChange={(e) => setExportFileName(e.target.value)}
            placeholder="z.B. mein-chat.md"
            autoFocus
            onKeyPress={(e) => e.key === 'Enter' && handleExportConfirm()}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowExportDialog(false)}>Abbrechen</Button>
          <Button
            onClick={handleExportConfirm}
            variant="contained"
            disabled={!exportFileName.trim()}
          >
            Herunterladen
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
};

// Sub-Komponente für Message Bubble
const ChatMessageBubble: React.FC<{ message: ChatMessage }> = ({ message }) => {
  const isUser = message.role === 'user';
  
  return (
    <Box display="flex" justifyContent={isUser ? 'flex-end' : 'flex-start'}>
      <Box
        sx={{
          maxWidth: '80%',
          borderRadius: 2,
          p: 2,
          bgcolor: isUser ? 'primary.main' : 'grey.100',
          color: isUser ? 'primary.contrastText' : 'text.primary',
          '& h1, & h2, & h3, & h4, & h5, & h6': {
            mt: 2,
            mb: 1,
            fontWeight: 'bold'
          },
          '& h1': { fontSize: '1.5rem' },
          '& h2': { fontSize: '1.3rem' },
          '& h3': { fontSize: '1.1rem' },
          '& p': { mb: 1 },
          '& ul, & ol': {
            pl: 3,
            mb: 1
          },
          '& li': { mb: 0.5 },
          '& code': {
            bgcolor: isUser ? 'rgba(0,0,0,0.1)' : 'rgba(0,0,0,0.05)',
            px: 0.5,
            py: 0.25,
            borderRadius: 0.5,
            fontFamily: 'monospace',
            fontSize: '0.9em'
          },
          '& pre': {
            bgcolor: isUser ? 'rgba(0,0,0,0.1)' : 'rgba(0,0,0,0.05)',
            p: 1.5,
            borderRadius: 1,
            overflow: 'auto',
            mb: 1
          },
          '& pre code': {
            bgcolor: 'transparent',
            p: 0
          },
          '& blockquote': {
            borderLeft: '3px solid',
            borderColor: isUser ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.2)',
            pl: 2,
            ml: 0,
            fontStyle: 'italic'
          },
          '& a': {
            color: isUser ? 'inherit' : 'primary.main',
            textDecoration: 'underline'
          }
        }}
      >
        <MarkdownRenderer content={message.content} variant="compact" />
        
        {/* Source Citations */}
        {message.sources && message.sources.length > 0 && (
          <Box mt={1} pt={1} borderTop={1} borderColor="divider">
            <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
              Quellen:
            </Typography>
            <Box display="flex" flexWrap="wrap" gap={0.5}>
              {message.sources.map((source, idx) => {
                const score = source.score ?? source.similarity_score ?? 0;
                const title = source.metadata?.title || source.filename || 'Dokument';
                return (
                  <Chip
                    key={idx}
                    label={`${title} (${(score * 100).toFixed(0)}%)`}
                    size="small"
                    variant="outlined"
                  />
                );
              })}
            </Box>
          </Box>
        )}
        
        {/* Confidence Score */}
        {message.confidence !== undefined && message.confidence > 0 && (
          <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
            Konfidenz: {(message.confidence * 100).toFixed(0)}%
          </Typography>
        )}
        
        <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
          {new Date(message.timestamp).toLocaleTimeString('de-CH')}
        </Typography>
      </Box>
    </Box>
  );
};

