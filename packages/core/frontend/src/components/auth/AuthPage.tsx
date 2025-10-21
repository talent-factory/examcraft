/**
 * Auth Page Component
 * Combined login/register page with tab switching
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LoginForm } from './LoginForm';
import { RegisterForm } from './RegisterForm';
import { PasswordResetRequest } from './PasswordResetRequest';

type AuthView = 'login' | 'register' | 'reset-password';

interface AuthPageProps {
  defaultTab?: 'login' | 'register';
}

export const AuthPage: React.FC<AuthPageProps> = ({ defaultTab = 'login' }) => {
  const [view, setView] = useState<AuthView>(defaultTab);
  const navigate = useNavigate();

  const handleSuccess = () => {
    navigate('/dashboard');
  };

  const handleResetSuccess = () => {
    setView('login');
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md">
        {/* Logo/Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl mb-4">
            <svg className="w-9 h-9 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">
            ExamCraft AI
          </h1>
          <p className="text-sm text-gray-600">
            AI-Powered Exam Question Generation
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-white rounded-3xl shadow-sm border border-gray-200 p-10">
          {view !== 'reset-password' && view === 'register' && (
            <div className="mb-6 text-center">
              <button
                type="button"
                onClick={() => setView('login')}
                className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
              >
                ← Back to Login
              </button>
            </div>
          )}

          {/* Content */}
          {view === 'login' && (
            <LoginForm
              onSuccess={handleSuccess}
              onSwitchToRegister={() => setView('register')}
              onForgotPassword={() => setView('reset-password')}
            />
          )}

          {view === 'register' && (
            <RegisterForm
              onSuccess={handleSuccess}
              onSwitchToLogin={() => setView('login')}
            />
          )}

          {view === 'reset-password' && (
            <PasswordResetRequest
              onSuccess={handleResetSuccess}
              onCancel={() => setView('login')}
            />
          )}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-xs text-gray-500">
          <p>
            By continuing, you agree to our{' '}
            <a href="/terms" className="text-gray-700 hover:text-gray-900 underline transition-colors">
              Terms of Service
            </a>{' '}
            and{' '}
            <a href="/privacy" className="text-gray-700 hover:text-gray-900 underline transition-colors">
              Privacy Policy
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

