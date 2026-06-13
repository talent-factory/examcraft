/**
 * TF-397: PromptEditor uses the managed-tag autocomplete and submits tag_ids.
 *
 * Verifies that inline-typed tags are created as global kind='prompt' tags and
 * that createPrompt receives the resolved tag_ids (no free-text `tags`).
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { PromptEditor } from '../PromptEditor';
import { PromptCategory } from '../../../types/prompt';
import { promptsApi } from '../../../api/promptsApi';
import { tagsApi } from '../../../api/tagsApi';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

// TF-410: PromptEditor now reads the auth context (useAuth) to gate the
// visibility-tier controls. Mock it so this tag-focused test neither needs an
// AuthProvider nor pulls in the real AuthContext → i18n.ts side-effect import
// (which would otherwise hit `.use(initReactI18next)` with the mocked module).
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { is_superuser: false }, hasRole: () => false }),
}));

jest.mock('../../MarkdownRenderer', () => () => null);

jest.mock('../../../api/promptsApi', () => ({
  promptsApi: {
    getPrompt: jest.fn(),
    createPrompt: jest.fn().mockResolvedValue({ id: 'p1', version: 1, tags: [] }),
    updatePrompt: jest.fn(),
  },
}));

jest.mock('../../../api/tagsApi', () => {
  const actual = jest.requireActual('../../../api/tagsApi');
  return {
    ...actual,
    tagsApi: {
      listTags: jest.fn().mockResolvedValue([]),
      createTag: jest.fn().mockResolvedValue({
        id: 7,
        name: 'single_choice',
        scope: 'global',
        kind: 'prompt',
        institution_id: null,
        usage_count: 0,
        is_archived: false,
        is_own: true,
      }),
    },
  };
});

const renderEditor = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <PromptEditor
        initialData={{
          name: 'My Prompt',
          content: 'Some prompt content here',
          category: PromptCategory.SYSTEM_PROMPT,
          use_case: 'question_generation_single_choice',
        }}
      />
    </QueryClientProvider>
  );
};

describe('PromptEditor managed tags (TF-397)', () => {
  beforeEach(() => jest.clearAllMocks());

  it('creates an inline prompt tag and submits tag_ids on save', async () => {
    renderEditor();

    // Inline-create a tag via the autocomplete (deferred → pending).
    // Target the tag autocomplete by its label (the category/use_case Selects
    // also expose a combobox role).
    const input = screen.getByRole('combobox', {
      name: 'admin.promptEditor.tagsLabel',
    });
    await userEvent.type(input, 'single_choice');
    await userEvent.keyboard('{Enter}');

    // Save.
    await userEvent.click(
      screen.getByRole('button', { name: 'admin.promptEditor.btnSave' })
    );

    await waitFor(() =>
      expect(tagsApi.createTag).toHaveBeenCalledWith(
        'single_choice',
        'global',
        'prompt'
      )
    );
    await waitFor(() => expect(promptsApi.createPrompt).toHaveBeenCalled());

    const payload = (promptsApi.createPrompt as jest.Mock).mock.calls[0][0];
    expect(payload.tag_ids).toEqual([7]);
    // No legacy free-text tags field in the write payload.
    expect(payload.tags).toBeUndefined();
  });
});
