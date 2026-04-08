import React, { useState, useRef, useEffect } from 'react';
import {
  Box, TextField, IconButton, Typography, Divider, Button,
} from '@mui/material';
import { Send, RestartAlt } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { helpService } from '../../services/HelpService';
import HelpMessage from './HelpMessage';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  confidence?: number;
  sources?: Array<{ file: string; section: string }>;
}

interface HelpChatProps {
  route: string;
}

const HelpChat: React.FC<HelpChatProps> = ({ route }) => {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || !accessToken || loading) return;

    const question = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    setLoading(true);

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const result = await helpService.sendMessage(accessToken, question, route, history);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: result.answer,
          confidence: result.confidence,
          sources: result.sources,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: t('help.chatUnavailable') },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
        {messages.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', mt: 4 }}>
            {t('help.chatPlaceholder')}
          </Typography>
        )}
        {messages.map((msg, i) => (
          <HelpMessage
            key={i}
            role={msg.role}
            content={msg.content}
            confidence={msg.confidence}
            sources={msg.sources}
            question={i > 0 ? messages[i - 1]?.content : undefined}
            route={route}
          />
        ))}
        {loading && (
          <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
            ...
          </Typography>
        )}
        <div ref={messagesEndRef} />
      </Box>

      <Divider />

      {messages.length > 0 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 0.5 }}>
          <Button size="small" startIcon={<RestartAlt />} onClick={() => setMessages([])}>
            {t('help.newConversation')}
          </Button>
        </Box>
      )}

      <Box sx={{ display: 'flex', alignItems: 'center', p: 1.5, gap: 1 }}>
        <TextField
          fullWidth
          size="small"
          placeholder={t('help.chatPlaceholder')}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          multiline
          maxRows={3}
        />
        <IconButton onClick={handleSend} disabled={!input.trim() || loading} color="primary">
          <Send />
        </IconButton>
      </Box>
    </Box>
  );
};

export default HelpChat;
