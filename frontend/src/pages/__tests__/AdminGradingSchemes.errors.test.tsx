/**
 * AdminGradingSchemes error rendering (TF-772 PR 7).
 *
 * The page had no test. The two cases that matter: a load failure never shows
 * `ApiError.message`, and a delete 409 shows the backend's own reason when it
 * sends one — `is_institution_default` must not read «wird von mindestens
 * einer Prüfung verwendet».
 */

import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import AdminGradingSchemes from '../AdminGradingSchemes';
import { GradingSchemesService } from '../../services/gradingSchemesService';
import { ApiError } from '../../services/submissionsService';
import { GradingSchemeOut } from '../../types/gradingScheme';

jest.mock('../../services/gradingSchemesService');
const mocked = GradingSchemesService as jest.Mocked<typeof GradingSchemesService>;

// TF-838 (PR #286 review): mocked so this suite doesn't fire real, unmocked
// heartbeat POSTs as a side effect on every render.
jest.mock('../../hooks/useActivityHeartbeat', () => ({
  useActivityHeartbeat: jest.fn(),
}));

const RAW = 'ROHER BACKEND-TEXT';

const scheme: GradingSchemeOut = {
  id: 42,
  institution_id: 1,
  name: 'Schweizer Noten',
  display_format: 'numeric',
  config: { type: 'linear', min_pct: 0, max_pct: 100, min_grade: 1, max_grade: 6 },
  is_default_for_institution: true,
  is_system_scheme: false,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

async function deleteWith(error: ApiError) {
  mocked.list.mockResolvedValue({ schemes: [scheme] });
  mocked.delete.mockRejectedValue(error);
  render(<AdminGradingSchemes />);
  fireEvent.click(await screen.findByTestId('gs-btn-delete-42'));
  return screen.findByTestId('gs-page-delete-error');
}

beforeEach(() => {
  jest.clearAllMocks();
});

describe('AdminGradingSchemes errors', () => {
  it('renders the list fallback, not the backend text, when loading fails', async () => {
    mocked.list.mockRejectedValue(new ApiError({ kind: 'server', status: 500, message: RAW }));

    render(<AdminGradingSchemes />);

    const alert = await screen.findByTestId('gs-page-load-error');
    expect(alert).toHaveTextContent('Bewertungsschemata konnten nicht geladen werden.');
    expect(alert).not.toHaveTextContent(RAW);
  });

  it('lets a coded delete 409 win over the generic «in use» sentence', async () => {
    const alert = await deleteWith(
      new ApiError({
        kind: 'conflict',
        status: 409,
        message: RAW,
        errorCode: 'grading_schemes_is_institution_default',
      }),
    );

    expect(alert).toHaveTextContent('bitte zuerst einen anderen Default wählen');
    expect(alert).not.toHaveTextContent('von mindestens einer Prüfung verwendet');
    expect(alert).not.toHaveTextContent(RAW);
  });

  it('keeps the «in use» sentence for a 409 without a code', async () => {
    const alert = await deleteWith(new ApiError({ kind: 'conflict', status: 409, message: RAW }));

    expect(alert).toHaveTextContent(
      'Dieses Schema wird von mindestens einer Prüfung verwendet und kann nicht gelöscht werden.',
    );
  });
});
