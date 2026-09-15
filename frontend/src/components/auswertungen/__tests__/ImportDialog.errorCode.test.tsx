/**
 * ImportDialog: what a failed import request renders, end to end
 * (TF-772 PR 7).
 *
 * No service is mocked. `fetch` answers; the real `SubmissionsService` →
 * `ensureOk` → shared body reader builds the `ApiError`; `ImportDialog`
 * renders it. This is the path TF-773 PR 2c's import codes will take, so it
 * is pinned before they exist: today the import endpoints send no code of
 * their own, but the reserved `validation_error` from the framework handler
 * reaches them already.
 *
 * `detail` differs from every expected sentence, so rendering it — the
 * pre-PR-7 behaviour — fails each case.
 */

import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import ImportDialog from '../ImportDialog';

jest.mock('../../../api/apiClient');

global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

const respond = (status: number, body: unknown): Response =>
  ({
    ok: status >= 200 && status < 300,
    status,
    statusText: '',
    text: jest.fn().mockResolvedValue(JSON.stringify(body)),
    json: jest.fn().mockResolvedValue(body),
  }) as unknown as Response;

const RAW = 'ROHER BACKEND-TEXT';

/** Answer the Moodle probe with "no connection", the preview with `preview`. */
function routeFetch(preview: Response) {
  mockFetch.mockImplementation(async (input) => {
    const url = String(input);
    if (url.includes('/moodle-connections')) return respond(200, { items: [] });
    if (url.includes('/import/preview')) return preview;
    throw new Error(`unexpected fetch in test: ${url}`);
  });
}

async function runPreview() {
  render(
    <ImportDialog open examId={42} examTitle="Allgemeinbildung" onClose={jest.fn()} onImported={jest.fn()} />,
  );
  fireEvent.click(screen.getByTestId('import-next-source'));
  // The hidden file input sits inside the «JSON-Datei wählen» label.
  fireEvent.change(screen.getByLabelText('JSON-Datei wählen'), {
    target: { files: [new File(['[[]]'], 'klasse.json', { type: 'application/json' })] },
  });
  fireEvent.click(screen.getByTestId('import-run-preview'));
  return screen.findByTestId('import-error');
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe('ImportDialog: failed preview, end to end', () => {
  it('renders a backend error_code translated', async () => {
    routeFetch(respond(422, { detail: RAW, error_code: 'validation_error' }));

    const alert = await runPreview();

    expect(alert).toHaveTextContent('Die Anfrage ist ungültig. Bitte prüf deine Eingaben.');
    expect(alert).not.toHaveTextContent(RAW);
  });

  it('renders a tier-quota 402 as the tier sentence, not detail.message', async () => {
    routeFetch(
      respond(402, {
        detail: {
          error_code: 'auswertung_driver_not_in_tier',
          message: RAW,
          tier: 'free',
          driver: 'moodle_json',
        },
      }),
    );

    const alert = await runPreview();

    expect(alert).toHaveTextContent(
      'Tier free schaltet den Driver "moodle_json" nicht frei. Upgrade auf Professional oder höher.',
    );
    expect(alert).not.toHaveTextContent(RAW);
  });

  it('renders the operation fallback for an uncoded service text', async () => {
    // Today's import failures: hand-written German from submissions.py, no
    // code. TF-773 PR 2c replaces these with codes.
    routeFetch(respond(400, { detail: RAW }));

    const alert = await runPreview();

    expect(alert).toHaveTextContent('Vorschau fehlgeschlagen.');
    expect(alert).not.toHaveTextContent(RAW);
  });
});
