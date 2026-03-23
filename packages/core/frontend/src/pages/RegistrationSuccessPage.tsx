import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Box, Container, Paper, Typography, Button, Alert } from '@mui/material';
import MarkEmailReadIcon from '@mui/icons-material/MarkEmailRead';
import ResendVerificationButton from '../components/auth/ResendVerificationButton';

const RegistrationSuccessPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation();
  const email = (location.state as any)?.email || '';

  const handleGoToDashboard = () => {
    navigate('/dashboard');
  };

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Paper
          elevation={3}
          sx={{
            p: 4,
            width: '100%',
            textAlign: 'center',
          }}
        >
          <MarkEmailReadIcon
            sx={{ fontSize: 80, color: 'primary.main', mb: 2 }}
          />
          <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold' }}>
            {t('pages.registrationSuccess.title')}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            {t('pages.registrationSuccess.subtitle')}
          </Typography>
          <Alert severity="info" sx={{ mb: 3 }}>
            <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
              {email}
            </Typography>
          </Alert>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            {t('pages.registrationSuccess.checkInbox')}
          </Typography>

          <Box sx={{ mb: 3 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {t('pages.registrationSuccess.didntReceive')}
            </Typography>
            {email && <ResendVerificationButton email={email} variant="outlined" fullWidth />}
          </Box>

          <Button
            variant="contained"
            size="large"
            onClick={handleGoToDashboard}
            fullWidth
            sx={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              '&:hover': {
                background: 'linear-gradient(135deg, #5568d3 0%, #63408a 100%)',
              },
            }}
          >
            {t('pages.registrationSuccess.continueToDashboard')}
          </Button>

          <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
            {t('pages.registrationSuccess.limitedAccess')}
          </Typography>
        </Paper>
      </Box>
    </Container>
  );
};

export default RegistrationSuccessPage;
