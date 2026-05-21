jest.mock('../../../api/apiClient');
/**
 * Tests for CreateClassDialog (TF-336 G2).
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

import CreateClassDialog from '../CreateClassDialog';
import { StudentClassesService } from '../../../services/studentClassesService';
import { ApiError } from '../../../services/submissionsService';

jest.mock('../../../services/studentClassesService');

const theme = createTheme();
const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>{children}</ThemeProvider>
);

const mocked = StudentClassesService as jest.Mocked<typeof StudentClassesService>;

beforeEach(() => {
  jest.clearAllMocks();
});

describe('CreateClassDialog', () => {
  it('creates a class and notifies the parent', async () => {
    mocked.create.mockResolvedValue({
      id: 1,
      name: 'INF-23a',
      member_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
    const onSaved = jest.fn();
    const onClose = jest.fn();

    render(
      <Wrapper>
        <CreateClassDialog open onClose={onClose} onSaved={onSaved} />
      </Wrapper>,
    );

    fireEvent.change(screen.getByTestId('create-class-name'), {
      target: { value: 'INF-23a' },
    });
    fireEvent.click(screen.getByTestId('create-class-submit'));

    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(mocked.create).toHaveBeenCalledWith('INF-23a');
    expect(onClose).toHaveBeenCalled();
  });

  it('shows duplicate error on 409', async () => {
    mocked.create.mockRejectedValue(
      new ApiError({
        kind: 'validation',
        status: 409,
        message: 'duplicate',
      }),
    );

    render(
      <Wrapper>
        <CreateClassDialog open onClose={jest.fn()} onSaved={jest.fn()} />
      </Wrapper>,
    );

    fireEvent.change(screen.getByTestId('create-class-name'), {
      target: { value: 'INF-23a' },
    });
    fireEvent.click(screen.getByTestId('create-class-submit'));

    await waitFor(() => screen.getByTestId('create-class-error'));
    expect(screen.getByTestId('create-class-error')).toHaveTextContent(
      /existiert bereits/,
    );
  });

  it('renames a class when mode=rename', async () => {
    mocked.rename.mockResolvedValue({
      id: 1,
      name: 'INF-23b',
      member_count: 3,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
    const onSaved = jest.fn();

    render(
      <Wrapper>
        <CreateClassDialog
          open
          mode="rename"
          classId={1}
          initialName="INF-23a"
          onClose={jest.fn()}
          onSaved={onSaved}
        />
      </Wrapper>,
    );

    fireEvent.change(screen.getByTestId('create-class-name'), {
      target: { value: 'INF-23b' },
    });
    fireEvent.click(screen.getByTestId('create-class-submit'));

    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(mocked.rename).toHaveBeenCalledWith(1, 'INF-23b');
  });
});
