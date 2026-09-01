/**
 * Privacy Policy Page
 *
 * Public DSGVO-compliant privacy policy. Legal text must be reviewed
 * and approved by legal counsel before production use.
 */

import React, { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'react-router-dom';
import { LegalPageLayout } from './LegalPageLayout';

export const PrivacyPage: React.FC = () => {
  const { t } = useTranslation();
  const location = useLocation();

  // TF-766: deep-link support for the footer's "Mehr erfahren" link
  // (/privacy#ai-data-flows). Guarded for jsdom, where scrollIntoView is
  // unavailable (same pattern as DocumentLibrary.tsx).
  useEffect(() => {
    if (!location.hash) {
      return;
    }
    const el = document.getElementById(location.hash.slice(1));
    if (el && typeof el.scrollIntoView === 'function') {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [location.hash]);

  return (
    <LegalPageLayout>
      <h1 className="text-3xl font-bold text-gray-900 mb-2">
        {t('legal.privacy.title')}
      </h1>
      <p className="text-sm text-gray-500 mb-8">
        {t('legal.privacy.lastUpdated')}
      </p>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.privacy.controller.title')}
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
        <p>
          {t('legal.privacy.controller.email')}:{' '}
          <a
            href="mailto:support@talent-factory.ch"
            className="text-blue-600 hover:underline"
          >
            support@talent-factory.ch
          </a>
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.privacy.purpose.title')}
        </h2>
        <p>{t('legal.privacy.purpose.text')}</p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.privacy.hosting.title')}
        </h2>
        <p>{t('legal.privacy.hosting.text')}</p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.privacy.subprocessors.title')}
        </h2>
        <p className="mb-4">{t('legal.privacy.subprocessors.intro')}</p>
        <ul className="list-disc pl-5 space-y-2">
          {(t('legal.privacy.subprocessors.items', { returnObjects: true }) as Array<{ name: string; description: string }>).map((item) => (
            <li key={item.name}>
              <strong>{item.name}</strong> — {item.description}
            </li>
          ))}
        </ul>
        <p className="mt-4 text-sm text-gray-600">
          {t('legal.privacy.subprocessors.note')}
        </p>
      </section>

      <section className="mb-8" id="ai-data-flows" data-testid="ai-data-flows-section">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.privacy.ai.title')}
        </h2>
        <p className="mb-4">{t('legal.privacy.ai.humanInTheLoop')}</p>
        <p className="mb-2">{t('legal.privacy.ai.intro')}</p>
        <ul className="list-disc pl-5 space-y-2 mb-4">
          {(
            t('legal.privacy.ai.functions', { returnObjects: true }) as Array<{
              label: string;
              description: string;
            }>
          ).map((item) => (
            <li key={item.label}>
              <strong>{item.label}:</strong> {item.description}
            </li>
          ))}
        </ul>
        <p className="mb-4 text-sm text-gray-600">
          {t('legal.privacy.ai.premiumNote')}
        </p>
        <p className="mb-2">
          <strong>{t('legal.privacy.ai.notTransmittedTitle')}</strong>{' '}
          {t('legal.privacy.ai.notTransmittedText')}
        </p>
        <p className="text-sm text-gray-600">
          {t('legal.privacy.ai.gatewayNote')}
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.privacy.rights.title')}
        </h2>
        <p className="mb-2">{t('legal.privacy.rights.intro')}</p>
        <ul className="list-disc pl-5 space-y-1">
          <li>{t('legal.privacy.rights.access')}</li>
          <li>{t('legal.privacy.rights.rectification')}</li>
          <li>{t('legal.privacy.rights.erasure')}</li>
          <li>{t('legal.privacy.rights.portability')}</li>
          <li>{t('legal.privacy.rights.restriction')}</li>
          <li>{t('legal.privacy.rights.objection')}</li>
        </ul>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-gray-900 mb-3">
          {t('legal.privacy.contact.title')}
        </h2>
        <p>{t('legal.privacy.contact.text')}</p>
      </section>
    </LegalPageLayout>
  );
};
