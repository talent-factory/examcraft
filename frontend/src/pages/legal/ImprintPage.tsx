/**
 * Imprint Page
 *
 * Legal imprint according to Swiss and German telemedia law.
 * Details must be kept accurate and up to date.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { LegalPageLayout } from './LegalPageLayout';

export const ImprintPage: React.FC = () => {
  const { t } = useTranslation();

  return (
    <LegalPageLayout>
      <h1 className="text-3xl font-bold text-gray-900 mb-2">
        {t('legal.imprint.title')}
      </h1>
      <p className="text-sm text-gray-500 mb-8">
        {t('legal.imprint.lastUpdated')}
      </p>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.imprint.provider.title')}
        </h2>
        <p className="mb-2">
          <strong>{t('legal.provider.name')}</strong>
          <br />
          {t('legal.provider.street')}
          <br />
          {t('legal.provider.city')}
          <br />
          {t('legal.provider.country')}
        </p>
        <p className="mb-1">
          {t('legal.imprint.provider.email')}:{' '}
          <a
            href="mailto:support@talent-factory.ch"
            className="text-blue-600 hover:underline"
          >
            support@talent-factory.ch
          </a>
        </p>
        <p>
          {t('legal.imprint.provider.website')}:{' '}
          <a
            href="https://talent-factory.xyz"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            talent-factory.xyz
          </a>
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.imprint.representation.title')}
        </h2>
        <p>{t('legal.imprint.representation.text')}</p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.imprint.vat.title')}
        </h2>
        <p>{t('legal.imprint.vat.text')}</p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.imprint.responsibility.title')}
        </h2>
        <p>{t('legal.imprint.responsibility.text')}</p>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.imprint.disclaimer.title')}
        </h2>
        <p>{t('legal.imprint.disclaimer.text')}</p>
      </section>
    </LegalPageLayout>
  );
};
