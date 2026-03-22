import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Box,
  Container,
  Paper,
  Typography,
  CircularProgress,
  Alert,
  Button,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface VerificationResponse {
  success: boolean;
  message: string;
  user?: {
    email: string;
    first_name: string;
    is_email_verified: boolean;
  };
}

const VerifyEmailPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const token = searchParams.get('token');

  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userData, setUserData] = useState<VerificationResponse['user'] | null>(null);

  // Prevent double verification in React 18 Strict Mode
  const verificationAttempted = useRef(false);

  useEffect(() => {
    const verifyEmail = async () => {
      // Prevent double execution in React 18 Strict Mode
      if (verificationAttempted.current) {
        return;
      }
      verificationAttempted.current = true;

      if (!token) {
        setError(t('pages.verifyEmail.noToken'));
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(
          `${API_BASE_URL}/api/auth/verify-email?token=${token}`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Verification failed');
        }

        const data: VerificationResponse = await response.json();

        if (data.success) {
          setSuccess(true);
          setError(null); // Clear any previous errors
          setUserData(data.user || null);

          // Auto-redirect to dashboard after 2 seconds
          setTimeout(() => {
            navigate('/dashboard');
          }, 2000);
        } else {
          setSuccess(false); // Clear success state
          setError(data.message || 'Verification failed');
        }
      } catch (err: any) {
        setSuccess(false); // Clear success state
        setError(err.message || 'Failed to verify email. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    verifyEmail();
  }, [token, navigate, t]);

  const handleGoToDashboard = () => {
    navigate('/dashboard');
  };

  const handleGoToLogin = () => {
    navigate('/login');
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
          {loading && (
            <>
              <CircularProgress size={60} sx={{ mb: 3 }} />
              <Typography variant="h5" gutterBottom>
                {t('pages.verifyEmail.verifying')}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {t('pages.verifyEmail.pleaseWait')}
              </Typography>
            </>
          )}

          {!loading && success && (
            <>
              <CheckCircleIcon
                sx={{ fontSize: 80, color: 'success.main', mb: 2 }}
              />
              <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold' }}>
                {t('pages.verifyEmail.success')}
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                {t('pages.verifyEmail.welcomeUser', { name: userData?.first_name })}
              </Typography>
              <Alert severity="success" sx={{ mb: 3 }}>
                {t('pages.verifyEmail.fullAccess')}
              </Alert>
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
                {t('pages.verifyEmail.goToDashboard')}
              </Button>
            </>
          )}

          {!loading && error && (
            <>
              <ErrorIcon sx={{ fontSize: 80, color: 'error.main', mb: 2 }} />
              <Typography variant="h4" gutterBottom sx={{ fontWeight: 'bold' }}>
                {t('pages.verifyEmail.failed')}
              </Typography>
              <Alert severity="error" sx={{ mb: 3 }}>
                {error}
              </Alert>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                {t('pages.verifyEmail.linkExpired')}
              </Typography>
              <Button
                variant="outlined"
                size="large"
                onClick={handleGoToLogin}
                fullWidth
              >
                {t('pages.verifyEmail.backToLogin')}
              </Button>
            </>
          )}
        </Paper>
      </Box>
    </Container>
  );
};

export default VerifyEmailPage;
