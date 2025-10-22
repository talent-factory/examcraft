/**
 * OAuth Callback Handler Component
 * Handles OAuth callback and token exchange
 */

import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Box, CircularProgress, Typography, Alert } from '@mui/material';
import AuthService from '../../services/AuthService';

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
        
        // Get authorization code from URL
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');

        if (error) {
          console.error('[OAuthCallback] OAuth error:', error);
          setError(`OAuth error: ${error}`);
          setIsProcessing(false);
          return;
        }

        if (!code) {
          console.error('[OAuthCallback] No authorization code received');
          setError('No authorization code received');
          setIsProcessing(false);
          return;
        }

        console.log('[OAuthCallback] Exchanging code for tokens...');
        // Exchange code for tokens
        const response = await AuthService.exchangeOAuthCode(code, state || '');
        const { access_token: accessToken, refresh_token: refreshToken } = response;

        if (!accessToken || !refreshToken) {
          console.error('[OAuthCallback] Missing tokens!');
          setError('Missing authentication tokens');
          setIsProcessing(false);
          return;
        }

        console.log('[OAuthCallback] Storing tokens in localStorage...');
        // Store tokens in localStorage
        localStorage.setItem('examcraft_access_token', accessToken);
        localStorage.setItem('examcraft_refresh_token', refreshToken);

        console.log('[OAuthCallback] Redirecting to dashboard...');
        // Redirect to dashboard - AuthContext will fetch user profile automatically
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

