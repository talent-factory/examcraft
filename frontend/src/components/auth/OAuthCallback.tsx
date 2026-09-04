/**
 * OAuth Callback Handler Component
 * Handles OAuth callback and token exchange
 */

import React, { useEffect, useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Box, CircularProgress, Typography, Alert } from '@mui/material';
import AuthService from '../../services/AuthService';
import { useAuth } from '../../contexts/AuthContext';
import { translateError } from '../../errors';

export const OAuthCallback: React.FC = () => {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { loginWithTokens } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);
  const hasProcessed = useRef(false);

  useEffect(() => {
    const handleCallback = async () => {
      // Prevent double execution in React StrictMode
      if (hasProcessed.current) {
        console.log('[OAuthCallback] Already processed, skipping...');
        return;
      }

      hasProcessed.current = true;

      try {
        console.log('[OAuthCallback] Processing OAuth callback...');

        // Check for error from OAuth provider
        const error = searchParams.get('error');
        if (error) {
          console.error('[OAuthCallback] OAuth error:', error);
          setError(t('errors.oauth.providerError'));
          setIsProcessing(false);
          return;
        }

        const code = searchParams.get('code');

        if (!code) {
          console.error('[OAuthCallback] No authorization code or tokens received');
          setError(t('auth.oauth.noCodeError'));
          setIsProcessing(false);
          return;
        }

        console.log('[OAuthCallback] Exchanging code for tokens...');

        // Exchange short-lived OAuth code for tokens via dedicated endpoint
        const response = await AuthService.exchangeOAuthCode(code);
        const { access_token: newAccessToken, refresh_token: newRefreshToken } = response;

        if (!newAccessToken || !newRefreshToken) {
          console.error('[OAuthCallback] Missing tokens!');
          setError(t('auth.oauth.missingTokens'));
          setIsProcessing(false);
          return;
        }

        console.log('[OAuthCallback] Setting auth state via context...');
        await loginWithTokens(newAccessToken, newRefreshToken);

        console.log('[OAuthCallback] Redirecting to dashboard...');
        navigate('/dashboard', { replace: true });
      } catch (err) {
        console.error('[OAuthCallback] Error:', err);
        setError(translateError(err, t, 'errors.oauth.callbackFailed'));
        setIsProcessing(false);
      }
    };

    handleCallback();
    // `t` intentionally omitted below: this effect is meant to run once per
    // mount (guarded by hasProcessed.current above), not re-fire on a
    // language switch mid-callback.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, navigate, loginWithTokens]);

  if (isProcessing) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          gap: 2,
        }}
      >
        <CircularProgress />
        <Typography variant="body1" color="textSecondary">
          {t('auth.oauth.processing')}
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          gap: 2,
          p: 2,
        }}
      >
        <Alert severity="error" sx={{ maxWidth: 500 }}>
          <Typography variant="h6">{t('auth.oauth.errorTitle')}</Typography>
          <Typography variant="body2">{error}</Typography>
        </Alert>
        <Typography
          variant="body2"
          color="primary"
          sx={{ cursor: 'pointer', textDecoration: 'underline' }}
          onClick={() => navigate('/login')}
        >
          {t('auth.oauth.returnToLogin')}
        </Typography>
      </Box>
    );
  }

  return null;
};
