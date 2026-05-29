/**
 * Tests for BulkActionsBar (TF-355 Phase 3, Task 4).
 *
 * (1) count>0 → renders selected-count text and all four buttons.
 * (2) count=0 → renders nothing.
 * (3) Each button click calls its respective callback.
 * (4) RAG button disabled when canRag=false, enabled when canRag=true.
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import BulkActionsBar from '../BulkActionsBar';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallbackOrOpts?: string | Record<string, unknown>) => {
      if (typeof fallbackOrOpts === 'string') return fallbackOrOpts;
      // For interpolated keys like { count }, return a recognisable string
      if (fallbackOrOpts && typeof fallbackOrOpts === 'object' && 'count' in fallbackOrOpts) {
        return `${fallbackOrOpts.count} ausgewählt`;
      }
      return key;
    },
    i18n: { language: 'de' },
  }),
}));

const theme = createTheme();
const wrap = (ui: React.ReactElement) => (
  <ThemeProvider theme={theme}>{ui}</ThemeProvider>
);

const noop = jest.fn();

describe('BulkActionsBar', () => {
  beforeEach(() => jest.clearAllMocks());

  // (1) count>0 renders bar with all buttons
  it('(1) renders selected text and all four buttons when count > 0', () => {
    render(
      wrap(
        <BulkActionsBar
          count={2}
          canRag={true}
          onRagExam={noop}
          onTags={noop}
          onVisibility={noop}
          onDelete={noop}
        />,
      ),
    );

    expect(screen.getByText('2 ausgewählt')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'RAG-Prüfung erstellen' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tags…' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sichtbarkeit…' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Löschen' })).toBeInTheDocument();
  });

  // (2) count=0 renders nothing
  it('(2) renders nothing when count is 0', () => {
    render(
      wrap(
        <BulkActionsBar
          count={0}
          canRag={false}
          onRagExam={noop}
          onTags={noop}
          onVisibility={noop}
          onDelete={noop}
        />,
      ),
    );

    expect(screen.queryByRole('button')).toBeNull();
  });

  // (3) Each button click calls its callback
  it('(3a) clicking RAG button calls onRagExam', () => {
    const onRagExam = jest.fn();
    render(
      wrap(
        <BulkActionsBar
          count={1}
          canRag={true}
          onRagExam={onRagExam}
          onTags={noop}
          onVisibility={noop}
          onDelete={noop}
        />,
      ),
    );

    fireEvent.click(screen.getByRole('button', { name: 'RAG-Prüfung erstellen' }));
    expect(onRagExam).toHaveBeenCalledTimes(1);
  });

  it('(3b) clicking Tags button calls onTags', () => {
    const onTags = jest.fn();
    render(
      wrap(
        <BulkActionsBar
          count={1}
          canRag={false}
          onRagExam={noop}
          onTags={onTags}
          onVisibility={noop}
          onDelete={noop}
        />,
      ),
    );

    fireEvent.click(screen.getByRole('button', { name: 'Tags…' }));
    expect(onTags).toHaveBeenCalledTimes(1);
  });

  it('(3c) clicking Sichtbarkeit button calls onVisibility', () => {
    const onVisibility = jest.fn();
    render(
      wrap(
        <BulkActionsBar
          count={1}
          canRag={false}
          onRagExam={noop}
          onTags={noop}
          onVisibility={onVisibility}
          onDelete={noop}
        />,
      ),
    );

    fireEvent.click(screen.getByRole('button', { name: 'Sichtbarkeit…' }));
    expect(onVisibility).toHaveBeenCalledTimes(1);
  });

  it('(3d) clicking Löschen button calls onDelete', () => {
    const onDelete = jest.fn();
    render(
      wrap(
        <BulkActionsBar
          count={1}
          canRag={false}
          onRagExam={noop}
          onTags={noop}
          onVisibility={noop}
          onDelete={onDelete}
        />,
      ),
    );

    fireEvent.click(screen.getByRole('button', { name: 'Löschen' }));
    expect(onDelete).toHaveBeenCalledTimes(1);
  });

  // (4) RAG button disabled / enabled based on canRag
  it('(4a) RAG button is disabled when canRag=false', () => {
    render(
      wrap(
        <BulkActionsBar
          count={1}
          canRag={false}
          onRagExam={noop}
          onTags={noop}
          onVisibility={noop}
          onDelete={noop}
        />,
      ),
    );

    expect(screen.getByRole('button', { name: 'RAG-Prüfung erstellen' })).toBeDisabled();
  });

  it('(4b) RAG button is enabled when canRag=true', () => {
    render(
      wrap(
        <BulkActionsBar
          count={1}
          canRag={true}
          onRagExam={noop}
          onTags={noop}
          onVisibility={noop}
          onDelete={noop}
        />,
      ),
    );

    expect(screen.getByRole('button', { name: 'RAG-Prüfung erstellen' })).not.toBeDisabled();
  });
});
