import React from 'react';
import { Box, Typography, Button, Alert } from '@mui/material';
import { LightbulbOutlined } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { helpService, ContextHint } from '../../services/HelpService';

interface HelpContextHintProps {
  hint: ContextHint;
  onDismiss: () => void;
  onDismissPermanently: () => void;
}

const HelpContextHint: React.FC<HelpContextHintProps> = ({ hint, onDismiss, onDismissPermanently }) => {
  const { t } = useTranslation();
  const { accessToken } = useAuth();

  if (!hint.hint_text) return null;

  const handleDismissPermanently = async () => {
    if (accessToken && hint.hint_id) {
      await helpService.dismissHint(accessToken, hint.hint_id);
    }
    onDismissPermanently();
  };

  return (
    <Box sx={{ p: 2 }}>
      <Alert icon={<LightbulbOutlined />} severity="info" sx={{ mb: 2 }}>
        <Typography variant="body2" sx={{ mb: 1 }}>
          {hint.hint_text}
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button size="small" variant="outlined" onClick={onDismiss}>
            {t('help.context.understood')}
          </Button>
          <Button size="small" color="inherit" onClick={handleDismissPermanently}>
            {t('help.context.dontShowAgain')}
          </Button>
        </Box>
      </Alert>
    </Box>
  );
};

export default HelpContextHint;
