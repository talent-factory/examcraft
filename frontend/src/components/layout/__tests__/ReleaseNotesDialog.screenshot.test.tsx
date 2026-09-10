import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { ReleaseNotesDialog } from '../ReleaseNotesDialog';

// Review fix: the screenshot-rendering behaviour used to be exercised only
// via the real v1.11.0 production entry, which coupled this test to
// whatever placeholder/real image happened to be committed under
// public/release-notes/1.11.0/ at the time. That entry has since had its
// screenshot removed (see public/release-notes/README.md), so this test
// exercises the rendering logic against a synthetic fixture instead —
// independent of whatever the current release manifest actually contains.
jest.mock('../../../data/releaseNotes', () => ({
  RELEASE_NOTES: [
    {
      version: '9.9.9',
      date: '2026-01-01',
      groups: [
        {
          kind: 'new',
          items: [
            { id: 'fixture_with_screenshot', screenshot: 'fixture.png' },
            { id: 'fixture_without_screenshot' },
          ],
        },
      ],
    },
  ],
  RELEASE_NOTE_GROUP_EMOJI: { new: '✨', improvements: '🧹', fixes: '🐛', security: '🔐' },
}));

jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: null }),
}));

const theme = createTheme();

const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>{children}</ThemeProvider>
);

describe('ReleaseNotesDialog screenshot rendering', () => {
  it('renders an image, with the translated entry text as alt, for an item that declares a screenshot', () => {
    render(<ReleaseNotesDialog open onClose={jest.fn()} />, { wrapper: Wrapper });

    const img = screen.getByRole('img');
    // The global react-i18next mock (setupTests.ts) falls back to the raw
    // key for an id with no translation.json entry — proving the alt text
    // goes through t(`releaseNotes.entries.<id>`) rather than the filename.
    expect(img).toHaveAttribute('alt', 'releaseNotes.entries.fixture_with_screenshot');
    expect(img).toHaveAttribute('src', '/release-notes/9.9.9/fixture.png');
  });

  it('renders exactly one image when only one of two items declares a screenshot', () => {
    render(<ReleaseNotesDialog open onClose={jest.fn()} />, { wrapper: Wrapper });
    expect(screen.getAllByRole('img')).toHaveLength(1);
  });
});
