/**
 * OAuth Callback Handler Component
 * Handles OAuth callback and token exchange
 */

import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import AuthService from '../../services/AuthService';

export const OAuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Get tokens from URL parameters (backend redirects with tokens)
        const accessToken = searchParams.get('access_token');
        const refreshToken = searchParams.get('refresh_token');
        const errorParam = searchParams.get('error');

        if (errorParam) {
          setError(`OAuth error: ${errorParam}`);
          setIsProcessing(false);
          return;
        }

        if (!accessToken || !refreshToken) {
          setError('Missing authentication tokens');
          setIsProcessing(false);
          return;
        }

        // Store tokens in localStorage
        localStorage.setItem('examcraft_access_token', accessToken);
        localStorage.setItem('examcraft_refresh_token', refreshToken);

        // Fetch user profile
        const user = await AuthService.getProfile(accessToken);
        localStorage.setItem('examcraft_user', JSON.stringify(user));

        // Redirect to dashboard - AuthContext will pick up tokens from localStorage
        navigate('/dashboard', { replace: true });
      } catch (err) {
        console.error('OAuth callback error:', err);
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

