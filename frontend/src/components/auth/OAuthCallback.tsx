/**
 * OAuth Callback Handler Component
 * Handles OAuth callback and token exchange
 */

import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
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
        console.log('[OAuthCallback] Starting OAuth callback handling...');
        console.log('[OAuthCallback] Current URL:', window.location.href);

        // Get tokens from URL parameters (backend redirects with tokens)
        const accessToken = searchParams.get('access_token');
        const refreshToken = searchParams.get('refresh_token');
        const errorParam = searchParams.get('error');

        console.log('[OAuthCallback] Access Token present:', !!accessToken);
        console.log('[OAuthCallback] Refresh Token present:', !!refreshToken);
        console.log('[OAuthCallback] Error param:', errorParam);

        if (errorParam) {
          console.error('[OAuthCallback] OAuth error:', errorParam);
          setError(`OAuth error: ${errorParam}`);
          setIsProcessing(false);
          return;
        }

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

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="w-full max-w-md mx-auto">
          <div className="bg-white shadow-md rounded-lg px-8 pt-6 pb-8">
            <div className="text-center">
              <div className="mb-4 text-red-600 text-5xl">✗</div>
              <h2 className="text-2xl font-bold mb-4 text-gray-800">
                Authentication Failed
              </h2>
              <p className="text-gray-600 mb-6">{error}</p>
              <button
                onClick={() => navigate('/login')}
                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
              >
                Back to Login
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="w-full max-w-md mx-auto">
        <div className="bg-white shadow-md rounded-lg px-8 pt-6 pb-8">
          <div className="text-center">
            <div className="mb-4">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
            <h2 className="text-2xl font-bold mb-4 text-gray-800">
              Completing Authentication
            </h2>
            <p className="text-gray-600">
              Please wait while we complete your authentication...
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

