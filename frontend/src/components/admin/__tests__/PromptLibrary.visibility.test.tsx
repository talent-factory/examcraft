/**
 * TF-641: PromptLibrary renders a visibility badge for the 'team' tier
 * (extends the TF-410 private/institution/system badges).
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import { PromptLibrary } from '../PromptLibrary';
import { PromptCategory, PromptVisibility } from '../../../types/prompt';
import { promptsApi } from '../../../api/promptsApi';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

jest.mock('../../../api/promptsApi', () => ({
  promptsApi: {
    listPrompts: jest.fn(),
    deletePrompt: jest.fn(),
    toggleActive: jest.fn(),
  },
}));

const basePrompt = {
  id: 'p1',
  name: 'Team Prompt',
  content: 'content',
  category: PromptCategory.SYSTEM_PROMPT,
  tags: [],
  use_case: 'question_generation',
  version: 1,
  is_active: true,
  created_at: '',
  updated_at: '',
  usage_count: 0,
};

describe('PromptLibrary visibility badges (TF-641)', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders a Team badge for team-visibility prompts', async () => {
    (promptsApi.listPrompts as jest.Mock).mockResolvedValue([
      { ...basePrompt, visibility: PromptVisibility.TEAM, org_unit_id: 3, can_edit: true },
    ]);

    render(<PromptLibrary />);

    await waitFor(() => expect(promptsApi.listPrompts).toHaveBeenCalled());
    expect(await screen.findByText('admin.promptLibrary.visibilityTeam')).toBeInTheDocument();
  });
});
