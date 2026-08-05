import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PromptLibrary } from '../PromptLibrary';

// PromptManagement pulls in prompt data-fetching, tabs, editor, etc. that are
// unrelated to the heading fix under test here — stub it out, the same way
// DashboardLayout.test.tsx stubs Sidebar for its own unrelated-concern tests.
jest.mock('../../components/admin/PromptManagement', () => ({
  PromptManagement: () => <div data-testid="prompt-management" />,
}));

describe('PromptLibrary page', () => {
  it('renders the heading via the shared sidebar i18n key (TF-506)', () => {
    // Regression: this heading previously used its own pages.promptLibrary.title
    // key, which was literally "Prompt Library" in English even in the German
    // locale file — a real localization bug. Fixed by reusing
    // nav.sidebar.promptLibrary, which is correctly translated in all locales.
    render(<PromptLibrary />);

    expect(screen.getByRole('heading', { level: 1, name: 'Prompt-Bibliothek' })).toBeInTheDocument();
  });
});
