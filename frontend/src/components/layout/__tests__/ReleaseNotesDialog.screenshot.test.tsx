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
//
// TF-810: only RELEASE_NOTES/RELEASE_NOTE_GROUP_EMOJI are faked — the real
// resolveScreenshotSrc (via requireActual) is kept so the map-form/fallback
// tests below exercise the actual resolution logic, not a re-implementation
// of it.
jest.mock('../../../data/releaseNotes', () => ({
  ...jest.requireActual('../../../data/releaseNotes'),
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
            // Map form: the global react-i18next mock (setupTests.ts) pins
            // i18n.language to 'de', so this exercises the map form's `de`
            // branch end-to-end through the real component. Language
            // switching itself is covered at the pure-function level by
            // resolveScreenshotSrc's own tests in releaseNotes.test.ts —
            // same split as formatReleaseDate's tests, since this global
            // mock cannot vary the rendered language within one test file.
            { id: 'fixture_with_language_map_screenshot', screenshot: { de: 'fixture-de.png' } },
            // No `de` entry at all — must still render via the "first
            // available entry" fallback instead of no image.
            { id: 'fixture_with_no_de_screenshot', screenshot: { fr: 'fixture-fr.png' } },
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

    // The global react-i18next mock (setupTests.ts) falls back to the raw
    // key for an id with no translation.json entry — proving the alt text
    // goes through t(`releaseNotes.entries.<id>`) rather than the filename.
    const img = screen.getByAltText('releaseNotes.entries.fixture_with_screenshot');
    expect(img).toHaveAttribute('src', '/release-notes/9.9.9/fixture.png');
  });

  it('renders exactly one image per item that declares a screenshot, none for the one that does not', () => {
    render(<ReleaseNotesDialog open onClose={jest.fn()} />, { wrapper: Wrapper });
    // fixture_with_screenshot, fixture_with_language_map_screenshot,
    // fixture_with_no_de_screenshot — fixture_without_screenshot renders none.
    expect(screen.getAllByRole('img')).toHaveLength(3);
  });

  // TF-810
  it('resolves a per-language screenshot map to its `de` entry under the pinned de mock', () => {
    render(<ReleaseNotesDialog open onClose={jest.fn()} />, { wrapper: Wrapper });

    const img = screen.getByAltText('releaseNotes.entries.fixture_with_language_map_screenshot');
    expect(img).toHaveAttribute('src', '/release-notes/9.9.9/fixture-de.png');
  });

  // TF-810
  it('falls back to whichever language is present when the map has no `de` entry', () => {
    render(<ReleaseNotesDialog open onClose={jest.fn()} />, { wrapper: Wrapper });

    const img = screen.getByAltText('releaseNotes.entries.fixture_with_no_de_screenshot');
    expect(img).toHaveAttribute('src', '/release-notes/9.9.9/fixture-fr.png');
  });
});
