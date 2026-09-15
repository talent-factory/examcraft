/**
 * QuotaBanner / translateQuotaError (TF-772 PR 7): the tier-quota sentence
 * comes from `auswertungen.tierBanner.*`, never from the backend's German
 * `detail.message`.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { useTranslation } from 'react-i18next';

import QuotaBanner, { isQuotaError, translateQuotaError } from '../QuotaBanner';
import { ApiError } from '../../../services/submissionsService';

jest.mock('react-router-dom', () => ({ useNavigate: () => jest.fn() }));

const BACKEND_TEXT = 'ROHER BACKEND-TEXT';

const quota = (detail: Record<string, unknown>) =>
  new ApiError({
    kind: 'permission',
    status: 402,
    message: BACKEND_TEXT,
    detail: { message: BACKEND_TEXT, ...detail },
  });

function translate(err: ApiError): string {
  if (!isQuotaError(err)) throw new Error('fixture is not a quota error');
  let result = '';
  const Probe = () => {
    const { t } = useTranslation();
    result = translateQuotaError(err, t);
    return null;
  };
  render(<Probe />);
  return result;
}

describe('translateQuotaError', () => {
  it('renders a known quota code with its parameters', () => {
    expect(
      translate(
        quota({ error_code: 'auswertung_driver_not_in_tier', tier: 'free', driver: 'moodle_api' }),
      ),
    ).toBe(
      'Tier free schaltet den Driver "moodle_api" nicht frei. Upgrade auf Professional oder höher.',
    );
  });

  it('renders the generic tier sentence for a quota code this build does not know', () => {
    expect(translate(quota({ error_code: 'auswertung_from_a_newer_backend' }))).toBe(
      'Diese Funktion ist in deinem aktuellen Tier nicht enthalten.',
    );
  });
});

describe('QuotaBanner', () => {
  it('shows the generic tier sentence, not the error message, for an unstructured error', () => {
    render(
      <QuotaBanner
        error={new ApiError({ kind: 'permission', status: 402, message: BACKEND_TEXT })}
      />,
    );

    expect(screen.getByTestId('quota-banner-fallback')).toHaveTextContent(
      'Diese Funktion ist in deinem aktuellen Tier nicht enthalten.',
    );
    expect(screen.queryByText(BACKEND_TEXT)).not.toBeInTheDocument();
  });
});
