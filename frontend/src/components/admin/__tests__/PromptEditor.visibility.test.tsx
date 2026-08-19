/**
 * TF-641: PromptEditor gains the 'team' visibility tier + Org-Unit picker.
 *
 * Verifies:
 *  - the Team option is offered alongside private/institution/system
 *  - picking Team reveals the Org-Unit selector (populated via OrgUnitsService.mine())
 *  - Save is blocked until an Org-Unit is chosen for the team tier
 *  - a completed team selection is submitted as visibility + org_unit_id
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { PromptEditor } from '../PromptEditor';
import { PromptCategory } from '../../../types/prompt';
import { promptsApi } from '../../../api/promptsApi';
import { OrgUnitsService } from '../../../services/orgUnitsService';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

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
      createTag: jest.fn(),
    },
  };
});

jest.mock('../../../services/orgUnitsService', () => ({
  OrgUnitsService: {
    mine: jest.fn(),
  },
}));

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

describe('PromptEditor team visibility (TF-641)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (OrgUnitsService.mine as jest.Mock).mockResolvedValue({
      items: [
        { id: 1, name: 'Team Alpha', parent_org_unit_id: null, unit_type: 'team', descendant_count: 0, role_id: null, role_name: null, created_at: '', updated_at: '' },
        { id: 2, name: 'Team Beta', parent_org_unit_id: null, unit_type: 'team', descendant_count: 0, role_id: null, role_name: null, created_at: '', updated_at: '' },
      ],
    });
  });

  it('reveals the Org-Unit picker once Team is selected and blocks Save without a choice', async () => {
    renderEditor();
    await waitFor(() => expect(OrgUnitsService.mine).toHaveBeenCalled());

    await userEvent.click(screen.getByLabelText('admin.promptEditor.visibilityLabel'));
    await userEvent.click(screen.getByRole('option', { name: 'admin.promptEditor.visibilityTeam' }));

    // Org-Unit picker appears, but nothing is pre-selected.
    expect(screen.getByText('admin.promptEditor.orgUnitPickerPlaceholder')).toBeInTheDocument();

    // Save is disabled until an Org-Unit is picked.
    expect(screen.getByRole('button', { name: 'admin.promptEditor.btnSave' })).toBeDisabled();
  });

  it('submits visibility=team + the chosen org_unit_id on save', async () => {
    renderEditor();
    await waitFor(() => expect(OrgUnitsService.mine).toHaveBeenCalled());

    await userEvent.click(screen.getByLabelText('admin.promptEditor.visibilityLabel'));
    await userEvent.click(screen.getByRole('option', { name: 'admin.promptEditor.visibilityTeam' }));

    // Open the Org-Unit select and pick "Team Beta".
    await userEvent.click(
      screen.getByRole('combobox', { name: 'admin.promptEditor.orgUnitPickerPlaceholder' })
    );
    await userEvent.click(screen.getByRole('option', { name: 'Team Beta' }));

    const saveButton = screen.getByRole('button', { name: 'admin.promptEditor.btnSave' });
    expect(saveButton).toBeEnabled();
    await userEvent.click(saveButton);

    await waitFor(() => expect(promptsApi.createPrompt).toHaveBeenCalled());
    const payload = (promptsApi.createPrompt as jest.Mock).mock.calls[0][0];
    expect(payload.visibility).toBe('team');
    expect(payload.org_unit_id).toBe(2);
  });

  it('clears the Org-Unit selection when switching away from Team', async () => {
    renderEditor();
    await waitFor(() => expect(OrgUnitsService.mine).toHaveBeenCalled());

    await userEvent.click(screen.getByLabelText('admin.promptEditor.visibilityLabel'));
    await userEvent.click(screen.getByRole('option', { name: 'admin.promptEditor.visibilityTeam' }));

    await userEvent.click(
      screen.getByRole('combobox', { name: 'admin.promptEditor.orgUnitPickerPlaceholder' })
    );
    await userEvent.click(screen.getByRole('option', { name: 'Team Alpha' }));

    // Switch to Institution — the Org-Unit picker should disappear.
    await userEvent.click(screen.getByLabelText('admin.promptEditor.visibilityLabel'));
    await userEvent.click(screen.getByRole('option', { name: 'admin.promptEditor.visibilityInstitution' }));

    expect(screen.queryByText('admin.promptEditor.orgUnitPickerPlaceholder')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'admin.promptEditor.btnSave' }));
    await waitFor(() => expect(promptsApi.createPrompt).toHaveBeenCalled());
    const payload = (promptsApi.createPrompt as jest.Mock).mock.calls[0][0];
    expect(payload.visibility).toBe('institution');
    expect(payload.org_unit_id).toBeNull();
  });
});
