/**
 * ImportDialog: what a failed import request renders, end to end
 * (TF-772 PR 7).
 *
 * No service is mocked. `fetch` answers; the real `SubmissionsService` →
 * `ensureOk` → shared body reader builds the `ApiError`; `ImportDialog`
 * renders it. The file was written before TF-773 PR 2c to pin that path; the
 * second block below is that PR arriving, with the import codes the endpoints
 * now really send.
 *
 * `detail` differs from every expected sentence, so rendering it — the
 * pre-PR-7 behaviour — fails each case.
 *
 * Why an end-to-end test and not an assertion on the code: a backend code that
 * is not listed in `errors/codes/submissions.ts` is dropped by `selectCode`
 * and silently replaced by the operation fallback. Nothing in the backend, and
 * no type, notices. Only rendering the sentence proves the code arrived.
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
    // Still reachable: a 500 from the unhandled-exception handler, or any
    // endpoint on this router that PR 2c did not convert.
    routeFetch(respond(400, { detail: RAW }));

    const alert = await runPreview();

    expect(alert).toHaveTextContent('Vorschau fehlgeschlagen.');
    expect(alert).not.toHaveTextContent(RAW);
  });
});

describe('ImportDialog: the import codes from TF-773 PR 2c', () => {
  it('tells an empty file apart from a broken one', async () => {
    routeFetch(respond(400, { detail: RAW, error_code: 'submissions_import_file_empty' }));

    const alert = await runPreview();

    expect(alert).toHaveTextContent('Die Datei ist leer.');
    expect(alert).not.toHaveTextContent('Vorschau fehlgeschlagen.');
    expect(alert).not.toHaveTextContent(RAW);
  });

  it('names the JSON syntax error as its own reason', async () => {
    routeFetch(
      respond(400, { detail: RAW, error_code: 'submissions_import_file_not_json' }),
    );

    const alert = await runPreview();

    expect(alert).toHaveTextContent('Die Datei ist kein gültiges JSON.');
    expect(alert).not.toHaveTextContent(RAW);
  });

  it('interpolates the quiz id the teacher typed', async () => {
    routeFetch(
      respond(400, {
        detail: RAW,
        error_code: 'submissions_import_quiz_not_found',
        error_params: { quiz_id: 4242 },
      }),
    );

    const alert = await runPreview();

    expect(alert).toHaveTextContent('Das Moodle-Quiz 4242 wurde nicht gefunden.');
    expect(alert).not.toHaveTextContent('{{quiz_id}}');
  });

  it('interpolates the count of answers that miss the exam', async () => {
    routeFetch(
      respond(422, {
        detail: RAW,
        error_code: 'submissions_import_exam_mismatch',
        error_params: { count: 3 },
      }),
    );

    const alert = await runPreview();

    expect(alert).toHaveTextContent('3 Antworten gehören nicht zu dieser Prüfung.');
    expect(alert).not.toHaveTextContent('{{count}}');
  });

  it('keeps developer wording off the screen for an internal failure', async () => {
    routeFetch(
      respond(400, {
        detail: 'MoodleApiDriver braucht eine DB-Session',
        error_code: 'submissions_import_internal_error',
      }),
    );

    const alert = await runPreview();

    expect(alert).toHaveTextContent('Der Import ist an einem internen Fehler gescheitert.');
    expect(alert).not.toHaveTextContent('MoodleApiDriver');
  });
});
