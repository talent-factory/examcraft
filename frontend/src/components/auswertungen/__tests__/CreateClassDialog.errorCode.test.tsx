/**
 * A backend `error_code` travels the whole chain and renders translated
 * (TF-772 PR 7).
 *
 * Nothing between the network and the screen is mocked: `fetch` answers, the
 * real `StudentClassesService` → `httpClient.ensureOk` → shared body reader
 * builds the `ApiError`, and `CreateClassDialog` turns it into text through
 * `appErrorFromApiError` + `translateError`. The i18n mock in `setupTests.ts`
 * resolves the real German `translation.json` and hands back the key itself
 * when one is missing, so an assertion on the German sentence fails on a
 * dropped code (fallback sentence), on a missing key (raw key) and on the old
 * behaviour (`detail` from the body) alike.
 *
 * `detail` deliberately differs from every translation below, so rendering it
 * would be caught too.
 */

import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import CreateClassDialog from '../CreateClassDialog';

jest.mock('../../../api/apiClient');

global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

const respond = (status: number, body: unknown): Response =>
  ({
    ok: false,
    status,
    statusText: '',
    text: jest.fn().mockResolvedValue(JSON.stringify(body)),
    json: jest.fn().mockResolvedValue(body),
  }) as unknown as Response;

const DETAIL_NEVER_RENDERED = 'ROHER BACKEND-TEXT';

function submit(props: Partial<React.ComponentProps<typeof CreateClassDialog>> = {}) {
  render(<CreateClassDialog open onClose={jest.fn()} onSaved={jest.fn()} {...props} />);
  fireEvent.change(screen.getByTestId('create-class-name'), {
    target: { value: 'INF-23a' },
  });
  fireEvent.click(screen.getByTestId('create-class-submit'));
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe('CreateClassDialog: backend error_code end to end', () => {
  it('renders a coded 403 with its interpolated parameter', async () => {
    mockFetch.mockResolvedValue(
      respond(403, {
        detail: DETAIL_NEVER_RENDERED,
        error_code: 'auth_permission_required',
        error_params: { permission: 'students:manage' },
      }),
    );

    submit();

    expect(
      await screen.findByText('Berechtigung «students:manage» erforderlich'),
    ).toBeInTheDocument();
    expect(screen.queryByText(DETAIL_NEVER_RENDERED)).not.toBeInTheDocument();
  });

  it('renders a coded 404 on rename as the backend sentence, not the fallback', async () => {
    mockFetch.mockResolvedValue(
      respond(404, { detail: DETAIL_NEVER_RENDERED, error_code: 'student_classes_not_found' }),
    );

    submit({ mode: 'rename', classId: 7, initialName: 'alt' });

    expect(await screen.findByText('Klasse nicht gefunden')).toBeInTheDocument();
    expect(screen.queryByText('Klasse konnte nicht umbenannt werden.')).not.toBeInTheDocument();
  });

  it('falls back to the operation sentence when the body carries no code', async () => {
    mockFetch.mockResolvedValue(respond(500, { detail: DETAIL_NEVER_RENDERED }));

    submit({ mode: 'rename', classId: 7, initialName: 'alt' });

    expect(await screen.findByText('Klasse konnte nicht umbenannt werden.')).toBeInTheDocument();
    expect(screen.queryByText(DETAIL_NEVER_RENDERED)).not.toBeInTheDocument();
  });
});
