/**
 * Compliance Downloads Page (TF-746)
 *
 * Public download area for schools/school authorities: Muster-AVV
 * (Art. 28 DSGVO) and TOM-Anlage as PDF (and inline, to read without
 * downloading), the subprocessor table, a VVT text module, and
 * state-specific review notes. Content is fetched from
 * GET /api/v1/legal/compliance (services/ComplianceService) — the
 * same source that feeds the PDF exports, so page and PDF cannot
 * drift apart.
 *
 * The legal text itself is German-only (see TF-746 scoping decision);
 * only the page chrome (headings, buttons) is translated.
 */

import React, { useCallback, useEffect, useState } from 'react';
import * as Sentry from '@sentry/react';
import { useTranslation } from 'react-i18next';
import { LegalPageLayout } from './LegalPageLayout';
import {
  AVV_PDF_URL,
  TOM_PDF_URL,
  ComplianceContent,
  ComplianceService,
} from '../../services/ComplianceService';

export const CompliancePage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [content, setContent] = useState<ComplianceContent | null>(null);
  const [error, setError] = useState(false);
  const [copied, setCopied] = useState(false);
  const [clipboardUnavailable, setClipboardUnavailable] = useState(false);

  const loadContent = useCallback(() => {
    let cancelled = false;
    setError(false);
    ComplianceService.getContent()
      .then((data) => {
        if (!cancelled) setContent(data);
      })
      .catch((err) => {
        if (cancelled) return;
        // Keep the real cause out of the user-facing message (it stays a
        // generic "please try again later"), but never drop it silently —
        // this is the only place a broken deploy of a public, unauthenticated
        // page would otherwise go unnoticed.
        console.error('[CompliancePage] ComplianceService.getContent failed', err);
        Sentry.captureException(err, { tags: { feature: 'compliance-page' } });
        setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const cancel = loadContent();
    return cancel;
  }, [loadContent]);

  const handleCopyVvt = async () => {
    if (!content) return;
    try {
      await navigator.clipboard.writeText(content.vvt_text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      // Clipboard API missing (insecure context) or its write blocked
      // (NotAllowedError — plausible on managed/institutional networks,
      // exactly this page's audience). Either way the text stays fully
      // selectable/readable on the page, so this doesn't block the user —
      // but it must not look like the click silently did nothing.
      console.warn(
        '[CompliancePage] clipboard write failed, falling back to manual selection',
        err,
      );
      setClipboardUnavailable(true);
      window.setTimeout(() => setClipboardUnavailable(false), 4000);
    }
  };

  return (
    <LegalPageLayout>
      <h1 className="text-3xl font-bold text-gray-900 mb-2">
        {t('legal.compliance.title')}
      </h1>
      <p className="text-gray-700 mb-4">{t('legal.compliance.intro')}</p>
      {i18n.language?.substring(0, 2) !== 'de' && (
        <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded p-3 mb-8">
          {t('legal.compliance.germanOnlyNotice')}
        </p>
      )}

      {error && (
        <div className="text-red-700 bg-red-50 border border-red-200 rounded p-3 mb-4 flex items-center justify-between gap-4">
          <p>{t('legal.compliance.loadError')}</p>
          <button
            type="button"
            onClick={loadContent}
            className="shrink-0 text-sm font-medium underline hover:no-underline"
          >
            {t('legal.compliance.retry')}
          </button>
        </div>
      )}

      {!content && !error && (
        <p className="text-gray-500">{t('legal.compliance.loading')}</p>
      )}

      {content && (
        <>
          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              {content.avv.title}
            </h2>
            <p className="text-sm text-gray-500 mb-2">{content.avv.last_updated}</p>
            <p className="text-sm italic text-amber-700 mb-4">
              {content.avv.draft_notice}
            </p>
            <a
              href={AVV_PDF_URL}
              className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 mb-4"
            >
              {t('legal.compliance.avv.downloadPdf')}
            </a>
            {content.avv.sections.map((section) => (
              <div key={section.heading} className="mb-4">
                <h3 className="text-base font-semibold text-gray-900 mb-1">
                  {section.heading}
                </h3>
                {section.paragraphs.map((paragraph, index) => (
                  <p key={index} className="text-sm text-gray-700 mb-2">
                    {paragraph}
                  </p>
                ))}
              </div>
            ))}
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              {content.tom.title}
            </h2>
            <p className="text-sm text-gray-500 mb-2">{content.tom.last_updated}</p>
            <p className="text-sm italic text-amber-700 mb-4">
              {content.tom.draft_notice}
            </p>
            <a
              href={TOM_PDF_URL}
              className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 mb-4"
            >
              {t('legal.compliance.tom.downloadPdf')}
            </a>
            {content.tom.sections.map((section) => (
              <div key={section.heading} className="mb-4">
                <h3 className="text-base font-semibold text-gray-900 mb-1">
                  {section.heading}
                </h3>
                {section.paragraphs.map((paragraph, index) => (
                  <p key={index} className="text-sm text-gray-700 mb-2">
                    {paragraph}
                  </p>
                ))}
              </div>
            ))}
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-3">
              {t('legal.compliance.subprocessors.heading')}
            </h2>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm border-collapse">
                <thead>
                  <tr className="text-left border-b border-gray-300">
                    <th className="py-2 pr-4">
                      {t('legal.compliance.subprocessors.columnService')}
                    </th>
                    <th className="py-2 pr-4">
                      {t('legal.compliance.subprocessors.columnPurpose')}
                    </th>
                    <th className="py-2 pr-4">
                      {t('legal.compliance.subprocessors.columnLocation')}
                    </th>
                    <th className="py-2 pr-4">
                      {t('legal.compliance.subprocessors.columnTransfer')}
                    </th>
                    <th className="py-2 pr-4">
                      {t('legal.compliance.subprocessors.columnChangeNotice')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {content.subprocessors.map((sp) => (
                    <tr key={sp.name} className="border-b border-gray-100 align-top">
                      <td className="py-2 pr-4 font-medium">{sp.name}</td>
                      <td className="py-2 pr-4">{sp.purpose}</td>
                      <td className="py-2 pr-4">{sp.location}</td>
                      <td className="py-2 pr-4">{sp.transfer_mechanism}</td>
                      <td className="py-2 pr-4">{sp.change_notice}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              {t('legal.compliance.vvt.heading')}
            </h2>
            <p className="text-sm text-gray-600 mb-3">
              {t('legal.compliance.vvt.intro')}
            </p>
            <pre className="whitespace-pre-wrap text-sm bg-gray-50 border border-gray-200 rounded p-4 mb-3">
              {content.vvt_text}
            </pre>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleCopyVvt}
                className="bg-gray-200 text-gray-900 px-4 py-2 rounded hover:bg-gray-300"
              >
                {copied
                  ? t('legal.compliance.vvt.copied')
                  : t('legal.compliance.vvt.copyButton')}
              </button>
              {clipboardUnavailable && (
                <p className="text-sm text-gray-600">
                  {t('legal.compliance.vvt.copyUnavailable')}
                </p>
              )}
            </div>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">
              {content.state_specific_notes.heading}
            </h2>
            {content.state_specific_notes.paragraphs.map((paragraph, index) => (
              <p key={index} className="text-sm text-gray-700 mb-2">
                {paragraph}
              </p>
            ))}
          </section>
        </>
      )}
    </LegalPageLayout>
  );
};
