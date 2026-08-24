import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

jest.mock('../../api/tagsApi', () => {
  const actual = jest.requireActual('../../api/tagsApi');
  return {
    ...actual,
    tagsApi: {
      listTags: jest.fn().mockResolvedValue([]),
      createTag: jest.fn(),
      setQuestionTags: jest.fn().mockResolvedValue({ tags: [] }),
    },
  };
});
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fbOrParams?: string | Record<string, unknown>) => {
      if (typeof fbOrParams === 'string') return fbOrParams;
      const map: Record<string, string> = {
        'components.questionEditor.cancel': 'Abbrechen',
        'components.questionEditor.saveChanges': 'Speichern',
      };
      return map[key] ?? key;
    },
  }),
}));
jest.mock('../MarkdownRenderer', () => ({ __esModule: true, default: ({ content }: any) => <div>{content}</div> }));

import { tagsApi } from '../../api/tagsApi';
import { QuestionEditor } from '../QuestionEditor';

const mockQuestion: any = {
  id: 1,
  question_text: 'Was ist 1+1?',
  options: ['1', '2', '3'],
  correct_answer: '2',
  explanation: '',
  difficulty: 'easy',
  bloom_level: 1,
  estimated_time_minutes: 1,
  tags: [],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  status: 'pending',
  source_documents: [],
};

const renderEditor = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const onSave = jest.fn().mockResolvedValue(undefined);
  const onClose = jest.fn();
  render(
    <QueryClientProvider client={qc}>
      <QuestionEditor
        question={mockQuestion}
        open={true}
        onSave={onSave}
        onClose={onClose}
      />
    </QueryClientProvider>
  );
  return { onSave, onClose };
};

describe('QuestionEditor — Pending Tags beim Speichern', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (tagsApi.createTag as jest.Mock).mockResolvedValue({
      id: 99, name: 'NeuTag', scope: 'institution', institution_id: 1,
      usage_count: 0, is_archived: false, is_own: true,
    });
  });

  it('ruft createTag nicht auf wenn Cancel geklickt wird', async () => {
    renderEditor();

    const cancelButton = screen.getByRole('button', { name: /abbrechen/i });
    fireEvent.click(cancelButton);

    expect(tagsApi.createTag).not.toHaveBeenCalled();
    expect(tagsApi.setQuestionTags).not.toHaveBeenCalled();
  });

  it('ruft setQuestionTags beim Speichern auf (ohne pending Tags)', async () => {
    renderEditor();

    // Make a change to activate the Save button
    const textField = screen.getByRole('textbox', { name: /components\.questionEditor\.questionText/i });
    fireEvent.change(textField, { target: { value: 'Was ist 1+1? (aktualisiert)' } });

    const saveButton = screen.getByRole('button', { name: /speichern/i });
    fireEvent.click(saveButton);

    await waitFor(() => expect(tagsApi.setQuestionTags).toHaveBeenCalledWith(1, []));
  });

  it('existierende Tags werden direkt an setQuestionTags übergeben (ohne createTag)', async () => {
    const existingTag = { id: 5, name: 'BestandTag', scope: 'institution' as const, institution_id: 1, usage_count: 1, is_archived: false, is_own: true };

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const onSave = jest.fn().mockResolvedValue(undefined);
    render(
      <QueryClientProvider client={qc}>
        <QuestionEditor
          question={{ ...mockQuestion, tags: [existingTag] }}
          open={true}
          onSave={onSave}
          onClose={jest.fn()}
        />
      </QueryClientProvider>
    );

    // Make a change so the Save button becomes active
    const textField = screen.getByRole('textbox', { name: /components\.questionEditor\.questionText/i });
    fireEvent.change(textField, { target: { value: 'Was ist 1+1? (aktualisiert)' } });

    const saveButton = screen.getByRole('button', { name: /speichern/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(tagsApi.createTag).not.toHaveBeenCalled();
      expect(tagsApi.setQuestionTags).toHaveBeenCalledWith(1, [5]);
    });
  });
});
