/**
 * OAuth Callback Handler Component
 * Handles OAuth callback and token exchange
 */

import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Box, CircularProgress, Typography, Alert } from '@mui/material';
import AuthService from '../../services/AuthService';
import { OAuthProvider } from '../../types/auth';

export const OAuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
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
          setError(`OAuth error: ${error}`);
          setIsProcessing(false);
          return;
        }

        // Check if backend already exchanged tokens (new flow)
        const accessToken = searchParams.get('access_token');
        const refreshToken = searchParams.get('refresh_token');

        if (accessToken && refreshToken) {
          console.log('[OAuthCallback] Tokens received from backend, storing...');
          localStorage.setItem('examcraft_access_token', accessToken);
          localStorage.setItem('examcraft_refresh_token', refreshToken);
          console.log('[OAuthCallback] Redirecting to dashboard...');
          navigate('/dashboard', { replace: true });
          return;
        }

        // Fallback: Old flow with code exchange (for compatibility)
        const code = searchParams.get('code');
        const state = searchParams.get('state');

        if (!code) {
          console.error('[OAuthCallback] No authorization code or tokens received');
          setError('No authorization code received');
          setIsProcessing(false);
          return;
        }

        console.log('[OAuthCallback] Exchanging code for tokens...');

        // Extract provider from state or URL path
        const provider: OAuthProvider = (state || window.location.pathname.split('/')[2] || 'google') as OAuthProvider;

        // Exchange code for tokens
        const response = await AuthService.handleOAuthCallback(provider, code, state || '');
        const { access_token: newAccessToken, refresh_token: newRefreshToken } = response;

        if (!newAccessToken || !newRefreshToken) {
          console.error('[OAuthCallback] Missing tokens!');
          setError('Missing authentication tokens');
          setIsProcessing(false);
          return;
        }

        console.log('[OAuthCallback] Storing tokens in localStorage...');
        localStorage.setItem('examcraft_access_token', newAccessToken);
        localStorage.setItem('examcraft_refresh_token', newRefreshToken);

        console.log('[OAuthCallback] Redirecting to dashboard...');
        navigate('/dashboard', { replace: true });
      } catch (err) {
        console.error('[OAuthCallback] Error:', err);
        setError(err instanceof Error ? err.message : 'OAuth authentication failed');
        setIsProcessing(false);
      }
    };

    handleCallback();
  }, [searchParams, navigate]);

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
          Processing OAuth callback...
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
          <Typography variant="h6">Authentication Error</Typography>
          <Typography variant="body2">{error}</Typography>
        </Alert>
        <Typography
          variant="body2"
          color="primary"
          sx={{ cursor: 'pointer', textDecoration: 'underline' }}
          onClick={() => navigate('/login')}
        >
          Return to login
        </Typography>
      </Box>
    );
  }

  return null;
};
