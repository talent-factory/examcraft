/**
 * MoodleConnectionForm tests (TF-336 G4).
 */

import React from 'react';
import {
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

import MoodleConnectionForm from '../MoodleConnectionForm';
import { MoodleConnectionsService } from '../../../services/moodleConnectionsService';
jest.mock('../../../api/apiClient');

jest.mock('../../../services/moodleConnectionsService');
const mocked = MoodleConnectionsService as jest.Mocked<
  typeof MoodleConnectionsService
>;

const theme = createTheme();
const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>{children}</ThemeProvider>
);

beforeEach(() => {
  jest.clearAllMocks();
});

const { ApiError } = jest.requireActual('../../../services/submissionsService');

describe('MoodleConnectionForm', () => {
  // TF-772 PR 7: ApiError.message is log-only; the form renders the code's
  // translation or the operation fallback.
  it('renders the list fallback, not the backend text, when loading fails', async () => {
    mocked.list.mockRejectedValue(
      new ApiError({ kind: 'server', status: 500, message: 'ROHER BACKEND-TEXT' }),
    );

    render(
      <Wrapper>
        <MoodleConnectionForm />
      </Wrapper>,
    );

    const alert = await screen.findByTestId('moodle-form-error');
    expect(alert).toHaveTextContent(
      'Moodle-Verbindungen konnten nicht geladen werden — bitte später erneut versuchen.',
    );
    expect(alert).not.toHaveTextContent('ROHER BACKEND-TEXT');
  });

  it('renders a coded save error translated', async () => {
    mocked.list.mockResolvedValue({ items: [], total: 0 });
    mocked.create.mockRejectedValue(
      new ApiError({
        kind: 'permission',
        status: 403,
        message: 'ROHER BACKEND-TEXT',
        errorCode: 'auth_permission_required',
        errorParams: { permission: 'moodle:configure' },
      }),
    );

    render(
      <Wrapper>
        <MoodleConnectionForm />
      </Wrapper>,
    );

    fireEvent.change(await screen.findByTestId('moodle-base-url'), {
      target: { value: 'https://moodle.example.org' },
    });
    fireEvent.change(screen.getByTestId('moodle-token'), { target: { value: 'secret' } });
    fireEvent.click(screen.getByTestId('moodle-save'));

    const alert = await screen.findByTestId('moodle-form-error');
    expect(alert).toHaveTextContent('Berechtigung «moodle:configure» erforderlich');
    expect(alert).not.toHaveTextContent('ROHER BACKEND-TEXT');
  });

  it('renders the create form when no connection exists', async () => {
    mocked.list.mockResolvedValue({ items: [], total: 0 });

    render(
      <Wrapper>
        <MoodleConnectionForm />
      </Wrapper>,
    );

    await screen.findByTestId('moodle-base-url');
    expect(screen.getByTestId('moodle-token')).toBeInTheDocument();
    expect(screen.getByTestId('moodle-save')).toBeInTheDocument();
    // Create-mode hides Test/Delete.
    expect(screen.queryByTestId('moodle-test')).not.toBeInTheDocument();
  });

  it('creates a new connection on save', async () => {
    // First call: empty (create mode); second call after save: returns
    // the new connection. Order matters: ``mockResolvedValueOnce``
    // must be queued AFTER the default ``mockResolvedValue``.
    mocked.list.mockResolvedValue({
      items: [
        {
          id: 1,
          institution_id: 1,
          base_url: 'https://moodle.example.org',
          token_masked: '****1234',
          last_used_at: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      total: 1,
    });
    mocked.list.mockResolvedValueOnce({ items: [], total: 0 });
    mocked.create.mockResolvedValue({
      id: 1,
      institution_id: 1,
      base_url: 'https://moodle.example.org',
      token_masked: '****1234',
      last_used_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    render(
      <Wrapper>
        <MoodleConnectionForm />
      </Wrapper>,
    );

    await screen.findByTestId('moodle-base-url');
    fireEvent.change(screen.getByTestId('moodle-base-url'), {
      target: { value: 'https://moodle.example.org' },
    });
    fireEvent.change(screen.getByTestId('moodle-token'), {
      target: { value: 'tokenABCDEF1234' },
    });
    fireEvent.click(screen.getByTestId('moodle-save'));

    await waitFor(() =>
      expect(mocked.create).toHaveBeenCalledWith({
        base_url: 'https://moodle.example.org',
        token: 'tokenABCDEF1234',
      }),
    );
  });

  it('runs the connection test', async () => {
    const conn = {
      id: 7,
      institution_id: 1,
      base_url: 'https://moodle.example.org',
      token_masked: '****1234',
      last_used_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    mocked.list.mockResolvedValue({ items: [conn], total: 1 });
    mocked.test.mockResolvedValue({
      ok: true,
      site_name: 'Test Moodle',
      site_url: 'https://moodle.example.org',
      user_full_name: 'Admin',
      error: null,
    });

    render(
      <Wrapper>
        <MoodleConnectionForm />
      </Wrapper>,
    );

    await screen.findByTestId('moodle-test');
    fireEvent.click(screen.getByTestId('moodle-test'));

    await screen.findByTestId('moodle-test-result');
    expect(screen.getByTestId('moodle-test-result')).toHaveTextContent(
      /Test Moodle/,
    );
  });
});
