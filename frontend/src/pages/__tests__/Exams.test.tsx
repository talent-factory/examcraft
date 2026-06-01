/**
 * Pins the contract that documents pre-selected in the document library
 * (passed via React Router navigation state `selectedDocuments`) are
 * forwarded to the RAGExamCreator, so the user doesn't have to repeat
 * the selection in the RAG generation flow.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';

import { Exams } from '../Exams';

// Replace the dynamically-loaded RAGExamCreator with a stub that renders the
// `selectedDocuments` prop, so we can assert what the page forwards without
// pulling in the real premium component.
jest.mock('../../utils/componentLoader', () => ({
  loadRAGExamCreator: () => (props: { selectedDocuments?: number[] }) => (
    <div data-testid="rag-exam-creator-stub">
      selected:{(props.selectedDocuments ?? []).join(',')}
    </div>
  ),
}));

const renderAt = (initialEntry: { pathname: string; state?: unknown }) =>
  render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Exams />
    </MemoryRouter>,
  );

describe('Exams page — pre-selection from navigation state', () => {
  it('forwards selectedDocuments from location state to RAGExamCreator', () => {
    renderAt({
      pathname: '/questions/generate',
      state: { selectedDocuments: [42, 17] },
    });

    expect(screen.getByTestId('rag-exam-creator-stub')).toHaveTextContent(
      'selected:42,17',
    );
  });

  it('falls back to an empty selection on direct navigation', () => {
    renderAt({ pathname: '/questions/generate' });

    expect(screen.getByTestId('rag-exam-creator-stub')).toHaveTextContent(
      'selected:',
    );
  });

  it('falls back to an empty selection when state lacks selectedDocuments', () => {
    renderAt({
      pathname: '/questions/generate',
      state: { viewTaskId: 'task-1' },
    });

    expect(screen.getByTestId('rag-exam-creator-stub')).toHaveTextContent(
      'selected:',
    );
  });

  it('forwards an explicit empty array unchanged', () => {
    renderAt({
      pathname: '/questions/generate',
      state: { selectedDocuments: [] },
    });

    expect(screen.getByTestId('rag-exam-creator-stub')).toHaveTextContent(
      'selected:',
    );
  });

  it('filters out non-positive-integer entries (strings, null, NaN, floats, zero, negatives)', () => {
    renderAt({
      pathname: '/questions/generate',
      state: {
        selectedDocuments: [
          1,
          'two' as unknown as number,
          3,
          null,
          NaN,
          1.5,
          0,
          -7,
          4,
        ],
      },
    });

    expect(screen.getByTestId('rag-exam-creator-stub')).toHaveTextContent(
      'selected:1,3,4',
    );
  });

  it('ignores malformed state (selectedDocuments is not an array)', () => {
    renderAt({
      pathname: '/questions/generate',
      state: { selectedDocuments: 'not-an-array' as unknown as number[] },
    });

    expect(screen.getByTestId('rag-exam-creator-stub')).toHaveTextContent(
      'selected:',
    );
  });

  it('renders the same selection on a re-render with unchanged state', () => {
    const entry = {
      pathname: '/questions/generate',
      state: { selectedDocuments: [42, 17] },
    };
    const { rerender } = render(
      <MemoryRouter initialEntries={[entry]}>
        <Exams />
      </MemoryRouter>,
    );
    const firstText = screen.getByTestId('rag-exam-creator-stub').textContent;

    rerender(
      <MemoryRouter initialEntries={[entry]}>
        <Exams />
      </MemoryRouter>,
    );

    expect(screen.getByTestId('rag-exam-creator-stub').textContent).toBe(
      firstText,
    );
  });
});
