import React, { useState, useEffect, useRef } from 'react';
import { Send, FileText, Loader2, Download, FileDown } from 'lucide-react';
import { Button } from '@mui/material';
import { TextField, Card, CardContent, CardHeader, Typography, Box, Chip, IconButton } from '@mui/material';

interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: Array<{
    document_id: number;
    chunk_id: string;
    score: number;
    metadata: any;
  }>;
  confidence?: number;
}

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
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll zu neuesten Nachrichten
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Chat-Historie laden
  useEffect(() => {
    loadChatHistory();
  }, [sessionId]);

  const loadChatHistory = async () => {
    try {
      const response = await fetch(`/api/v1/chat/sessions/${sessionId}`);
      const data = await response.json();
      setMessages(data.messages || []);
    } catch (error) {
      console.error('Failed to load chat history:', error);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/v1/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: inputMessage,
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const assistantMessage: ChatMessage = await response.json();
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

  const handleExport = async (format: 'markdown' | 'json') => {
    try {
      const response = await fetch(`/api/v1/chat/sessions/${sessionId}/export?export_format=${format}`, {
        method: 'POST'
      });
      
      if (!response.ok) throw new Error('Export failed');
      
      const data = await response.json();
      
      // Download file
      const blob = new Blob([data.content], { 
        type: format === 'json' ? 'application/json' : 'text/markdown' 
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = data.filename;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Export fehlgeschlagen');
    }
  };

  const handleConvertToDocument = async () => {
    try {
      const response = await fetch(`/api/v1/chat/sessions/${sessionId}/to-document`, {
        method: 'POST'
      });
      
      if (!response.ok) throw new Error('Conversion failed');
      
      const data = await response.json();
      alert(`✅ ${data.message}`);
    } catch (error) {
      console.error('Conversion failed:', error);
      alert('Konvertierung fehlgeschlagen');
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
            <IconButton onClick={() => handleExport('markdown')} title="Als Markdown exportieren">
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
          color: isUser ? 'primary.contrastText' : 'text.primary'
        }}
      >
        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
          {message.content}
        </Typography>
        
        {/* Source Citations */}
        {message.sources && message.sources.length > 0 && (
          <Box mt={1} pt={1} borderTop={1} borderColor="divider">
            <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
              Quellen:
            </Typography>
            <Box display="flex" flexWrap="wrap" gap={0.5}>
              {message.sources.map((source, idx) => (
                <Chip
                  key={idx}
                  label={`${source.metadata?.title || 'Dokument'} (${(source.score * 100).toFixed(0)}%)`}
                  size="small"
                  variant="outlined"
                />
              ))}
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

