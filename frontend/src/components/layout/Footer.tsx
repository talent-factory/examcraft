/**
 * Footer Component
 *
 * Minimal footer for authenticated pages with links to legal information.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

export const Footer: React.FC = () => {
  const { t } = useTranslation();

  const links = [
    { to: '/privacy', label: t('legal.privacy.title') },
    { to: '/terms', label: t('legal.terms.title') },
    { to: '/imprint', label: t('legal.imprint.title') },
  ];

  return (
    <footer
      className="py-6 px-4 sm:px-6 lg:px-8 border-t border-gray-200 bg-white"
      data-testid="app-footer"
    >
      <div className="max-w-7xl mx-auto flex flex-col gap-3">
        {/* TF-766: short AI/privacy notice, deep-linked to the "Übermittlung
            von Inhalten an KI-Modelle" section (#ai-data-flows) on the
            Privacy Page. Draft text, see TF-766 AC for DPO/Legal sign-off. */}
        <p
          className="text-xs text-gray-500 text-center sm:text-left"
          data-testid="footer-ai-notice"
        >
          {t('footer.aiNoticeText')}{' '}
          <Link
            to="/privacy#ai-data-flows"
            className="text-gray-700 hover:text-gray-900 underline transition-colors"
            aria-label={t('footer.aiNoticeLinkAriaLabel')}
          >
            {t('footer.aiNoticeLinkLabel')}
          </Link>
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-sm text-gray-500">
            &copy; {new Date().getFullYear()} ExamCraft AI — {t('footer.tagline')}
          </p>
          <nav aria-label={t('footer.legalLinks')}>
            <ul className="flex flex-wrap items-center gap-4">
              {links.map((link) => (
                <li key={link.to}>
                  <Link
                    to={link.to}
                    className="text-sm text-gray-600 hover:text-gray-900 underline transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </div>
    </footer>
  );
};
