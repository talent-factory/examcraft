import React from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Box, Typography } from '@mui/material';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import ResendVerificationButton from './ResendVerificationButton';
import { useAuth } from '../../contexts/AuthContext';

const EmailVerificationBanner: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();

  // Don't show banner if user is verified or not logged in
  if (!user || user.is_email_verified) {
    return null;
  }

  return (
    <Alert
      severity="warning"
      icon={<WarningAmberIcon />}
      sx={{
        mb: 3,
        borderRadius: 2,
        '& .MuiAlert-message': {
          width: '100%',
        },
      }}
    >
      <Box
        sx={{
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          alignItems: { xs: 'flex-start', sm: 'center' },
          justifyContent: 'space-between',
          gap: 2,
        }}
      >
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mb: 0.5 }}>
            {t('auth.verification.bannerTitle')}
          </Typography>
          <Typography variant="body2">
            {t('auth.verification.bannerText')}
          </Typography>
        </Box>
        <Box sx={{ flexShrink: 0 }}>
          <ResendVerificationButton email={user.email} variant="outlined" />
        </Box>
      </Box>
    </Alert>
  );
};

export default EmailVerificationBanner;
