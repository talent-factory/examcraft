/**
 * Smoke tests for the Studi-Liste (TF-336 G3).
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

import AuswertungenStudierende from '../AuswertungenStudierende';
import { StudentsService } from '../../services/studentsService';
import { StudentClassesService } from '../../services/studentClassesService';

jest.mock('../../services/studentsService');
jest.mock('../../services/studentClassesService');

const mockedStudents = StudentsService as jest.Mocked<typeof StudentsService>;
const mockedClasses = StudentClassesService as jest.Mocked<
  typeof StudentClassesService
>;

const theme = createTheme();
const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>
    <MemoryRouter>{children}</MemoryRouter>
  </ThemeProvider>
);

beforeEach(() => {
  jest.clearAllMocks();
  mockedClasses.list.mockResolvedValue({ items: [], total: 0 });
});

describe('AuswertungenStudierende', () => {
  it('renders the table with students', async () => {
    mockedStudents.list.mockResolvedValue({
      items: [
        {
          id: 1,
          external_id: 'anna@example.org',
          display_name: 'Anna B.',
          submission_count: 2,
          avg_percentage: 85.5,
          classes: [{ class_id: 1, class_name: 'INF-23a' }],
        },
        {
          id: 2,
          external_id: 'bruno@example.org',
          display_name: null,
          submission_count: 0,
          avg_percentage: null,
          classes: [],
        },
      ],
      total: 2,
      limit: 200,
      offset: 0,
    });

    render(
      <Wrapper>
        <AuswertungenStudierende />
      </Wrapper>,
    );

    await waitFor(() => screen.getByTestId('studi-table'));
    expect(screen.getByTestId('studi-1')).toHaveTextContent('anna@example.org');
    expect(screen.getByTestId('studi-1')).toHaveTextContent('Anna B.');
    expect(screen.getByTestId('studi-2')).toHaveTextContent(
      'bruno@example.org',
    );
  });

  it('renders the empty state when no students match', async () => {
    mockedStudents.list.mockResolvedValue({
      items: [],
      total: 0,
      limit: 200,
      offset: 0,
    });

    render(
      <Wrapper>
        <AuswertungenStudierende />
      </Wrapper>,
    );

    await waitFor(() => screen.getByRole('alert'));
    expect(screen.getByRole('alert')).toHaveTextContent(/keine|no/i);
  });
});
