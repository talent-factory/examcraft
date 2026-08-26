/**
 * Legal Page Layout
 *
 * Shared shell for privacy policy, terms of service and imprint pages.
 * Keeps public legal pages visually consistent with the auth screen.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation } from 'react-router-dom';

interface LegalPageLayoutProps {
  children: React.ReactNode;
}

export const LegalPageLayout: React.FC<LegalPageLayoutProps> = ({ children }) => {
  const { t } = useTranslation();
  const location = useLocation();

  const navItems = [
    { path: '/privacy', label: t('legal.privacy.title') },
    { path: '/terms', label: t('legal.terms.title') },
    { path: '/imprint', label: t('legal.imprint.title') },
  ];

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <Link
            to="/"
            aria-label={t('legal.logoLink')}
            className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl mb-4 hover:bg-blue-700 transition-colors"
          >
            <svg
              className="w-9 h-9 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </Link>
          <div className="text-2xl font-bold text-gray-900">
            ExamCraft AI
          </div>
        </div>

        {/* Navigation */}
        <nav className="mb-8" aria-label={t('legal.legalNavigation')}>
          <ul className="flex flex-wrap justify-center gap-2 sm:gap-4">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-600 text-white'
                        : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200'
                    }`}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Content card */}
        <main className="bg-white rounded-3xl shadow-sm border border-gray-200 p-8 sm:p-12">
          <div className="text-gray-700 leading-relaxed">
            {children}
          </div>
        </main>

        {/* Footer */}
        <div className="mt-8 text-center">
          <Link
            to="/login"
            className="text-sm text-gray-600 hover:text-gray-900 underline transition-colors"
          >
            {t('legal.backToLogin')}
          </Link>
        </div>
      </div>
    </div>
  );
};
