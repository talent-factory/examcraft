/**
 * Smoke tests for the Klassen list page (TF-336 G2).
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

import AuswertungenKlassen from '../AuswertungenKlassen';
import { StudentClassesService } from '../../services/studentClassesService';
import { ApiError } from '../../services/submissionsService';

jest.mock('../../services/studentClassesService');
const mocked = StudentClassesService as jest.Mocked<typeof StudentClassesService>;

const theme = createTheme();
const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>
    <MemoryRouter>{children}</MemoryRouter>
  </ThemeProvider>
);

beforeEach(() => {
  jest.clearAllMocks();
});

describe('AuswertungenKlassen', () => {
  it('renders the empty state when no classes exist', async () => {
    mocked.list.mockResolvedValue({ items: [], total: 0 });

    render(
      <Wrapper>
        <AuswertungenKlassen />
      </Wrapper>,
    );

    await waitFor(() => screen.getByRole('alert'));
    expect(screen.getByRole('alert')).toHaveTextContent(/Klassen|class/i);
  });

  it('renders the table with classes', async () => {
    mocked.list.mockResolvedValue({
      items: [
        {
          id: 1,
          name: 'INF-23a',
          member_count: 3,
          created_at: '2026-04-01T00:00:00Z',
          updated_at: '2026-04-01T00:00:00Z',
        },
        {
          id: 2,
          name: 'INF-23b',
          member_count: 0,
          created_at: '2026-04-01T00:00:00Z',
          updated_at: '2026-04-01T00:00:00Z',
        },
      ],
      total: 2,
    });

    render(
      <Wrapper>
        <AuswertungenKlassen />
      </Wrapper>,
    );

    await waitFor(() => screen.getByTestId('klassen-table'));
    expect(screen.getByTestId('klasse-1')).toHaveTextContent('INF-23a');
    expect(screen.getByTestId('klasse-2')).toHaveTextContent('INF-23b');
  });

  it('shows a quota banner on 402', async () => {
    mocked.list.mockRejectedValue(
      new ApiError({
        kind: 'permission',
        status: 402,
        message: 'Klassen-Verlauf nur Enterprise',
        detail: {
          error_code: 'auswertung_class_history_enterprise_only',
          tier: 'professional',
          upgrade_to: 'enterprise',
        },
      }),
    );

    render(
      <Wrapper>
        <AuswertungenKlassen />
      </Wrapper>,
    );

    await waitFor(() => screen.getByTestId('quota-banner'));
    expect(screen.getByTestId('quota-banner-upgrade')).toBeInTheDocument();
  });
});
