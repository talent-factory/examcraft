/**
 * Terms of Service Page
 *
 * Public terms of service. Legal text must be reviewed and approved
 * by legal counsel before production use.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { LegalPageLayout } from './LegalPageLayout';

export const TermsPage: React.FC = () => {
  const { t } = useTranslation();

  return (
    <LegalPageLayout>
      <h1 className="text-3xl font-bold text-gray-900 mb-2">
        {t('legal.terms.title')}
      </h1>
      <p className="text-sm text-gray-500 mb-8">
        {t('legal.terms.lastUpdated')}
      </p>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.terms.scope.title')}
        </h2>
        <p>{t('legal.terms.scope.text')}</p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.terms.accounts.title')}
        </h2>
        <p>{t('legal.terms.accounts.text')}</p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.terms.use.title')}
        </h2>
        <p>{t('legal.terms.use.text')}</p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.terms.ai.title')}
        </h2>
        <p>{t('legal.terms.ai.text')}</p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.terms.subscriptions.title')}
        </h2>
        <p>{t('legal.terms.subscriptions.text')}</p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.terms.liability.title')}
        </h2>
        <p>{t('legal.terms.liability.text')}</p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.terms.changes.title')}
        </h2>
        <p>{t('legal.terms.changes.text')}</p>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.terms.law.title')}
        </h2>
        <p>{t('legal.terms.law.text')}</p>
      </section>
    </LegalPageLayout>
  );
};
