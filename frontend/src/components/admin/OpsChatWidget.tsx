import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Paper,
  TextField,
  Typography,
} from '@mui/material';
import { sendOpsChatMessage } from '../../services/opsChatService';
import { OpsChatTurn } from '../../types/opsChat';

/**
 * Read-only Ops-Chat widget (TF-787), rendered inside the `system-health`
 * Admin tab. History lives only in this component's state — nothing is
 * persisted, so a page reload starts a fresh conversation.
 */
const OpsChatWidget: React.FC = () => {
  const { t } = useTranslation();
  const [messages, setMessages] = useState<OpsChatTurn[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const history = messages;
    setMessages([...history, { role: 'user', content: trimmed }]);
    setInput('');
    setLoading(true);
    setHasError(false);

    try {
      const reply = await sendOpsChatMessage(trimmed, history);
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }]);
    } catch (err) {
      console.error('[OpsChatWidget] sendOpsChatMessage failed', err);
      setHasError(true);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <Box data-testid="ops-chat-widget" sx={{ mt: 3 }}>
      <Typography variant="h6">{t('pages.admin.systemHealth.chat.title')}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t('pages.admin.systemHealth.chat.subtitle')}
      </Typography>

      <Paper variant="outlined" sx={{ p: 2, mb: 2, maxHeight: 320, overflowY: 'auto' }}>
        {messages.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            {t('pages.admin.systemHealth.chat.empty')}
          </Typography>
        )}
        {messages.map((msg, index) => (
          <Box
            key={index}
            data-testid={`ops-chat-message-${msg.role}`}
            sx={{ mb: 1, textAlign: msg.role === 'user' ? 'right' : 'left' }}
          >
            <Typography
              variant="body2"
              component="span"
              sx={{
                display: 'inline-block',
                bgcolor: msg.role === 'user' ? 'primary.main' : 'grey.200',
                color: msg.role === 'user' ? 'primary.contrastText' : 'text.primary',
                borderRadius: 1,
                px: 1.5,
                py: 0.75,
                whiteSpace: 'pre-wrap',
              }}
            >
              {msg.content}
            </Typography>
          </Box>
        ))}
        <div ref={bottomRef} />
      </Paper>

      {hasError && (
        <Alert severity="error" sx={{ mb: 2 }} data-testid="ops-chat-error">
          {t('pages.admin.systemHealth.chat.error')}
        </Alert>
      )}

      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField
          fullWidth
          size="small"
          multiline
          maxRows={3}
          placeholder={t('pages.admin.systemHealth.chat.placeholder')}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          inputProps={{ 'aria-label': t('pages.admin.systemHealth.chat.inputLabel') }}
        />
        <Button variant="contained" onClick={handleSend} disabled={loading || !input.trim()}>
          {loading ? <CircularProgress size={20} /> : t('pages.admin.systemHealth.chat.send')}
        </Button>
      </Box>
    </Box>
  );
};

export default OpsChatWidget;
