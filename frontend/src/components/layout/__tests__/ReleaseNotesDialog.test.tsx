import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { ReleaseNotesDialog } from '../ReleaseNotesDialog';

// The dialog's language pills go through useLanguageChange (review fix), which
// calls useAuth() — mocked here the same way as the other layout component
// tests (e.g. ImpersonationBanner.test.tsx) so this stays a lightweight unit
// test instead of needing the real AuthProvider. `user: null` is enough: it
// only gates whether useLanguageChange *also* tries to persist the choice to
// an account, which none of these tests assert on.
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: null }),
}));

// This project's global setupTests.ts replaces `react-i18next` with a mock
// that always resolves keys against `locales/de/translation.json` and stubs
// `i18n.changeLanguage` as a no-op jest.fn() (see setupTests.ts for why:
// stable `t`/`i18n` references across renders). So rendered text in these
// tests is always German, and clicking a language pill is verified by
// asserting the *call*, not by re-rendering in another language — actual
// per-language content is instead covered by the translation-completeness
// check below, which reads all four locale files directly.

const theme = createTheme();

const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>{children}</ThemeProvider>
);

const renderDialog = (open = true) =>
  render(<ReleaseNotesDialog open={open} onClose={jest.fn()} />, { wrapper: Wrapper });

describe('ReleaseNotesDialog', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // -------------------------------------------------------------------------
  // Rendering
  // -------------------------------------------------------------------------

  describe('rendering', () => {
    it('does not render when closed', () => {
      renderDialog(false);
      expect(screen.queryByText('Was ist neu in ExamCraft AI')).not.toBeInTheDocument();
    });

    it('renders the dialog title and current version badge', () => {
      renderDialog();
      expect(screen.getByText('Was ist neu in ExamCraft AI')).toBeInTheDocument();
      expect(screen.getByTestId('release-notes-current-version-badge')).toHaveTextContent('1.11.0');
    });

    it('renders the newest release expanded with its "new" badge', () => {
      renderDialog();
      expect(
        screen.getByText(
          'Benutzerverwaltung im Admin-Panel: Aktionen jetzt übersichtlich in einem Kebab-Menü zusammengefasst'
        )
      ).toBeInTheDocument();
      expect(screen.getByText('Neu')).toBeInTheDocument();
    });

    // The general screenshot-rendering mechanics (present/absent, src
    // construction, translated alt) are covered against a synthetic fixture
    // in ReleaseNotesDialog.screenshot.test.tsx, independent of whatever the
    // production manifest currently contains. This test only asserts the
    // one thing that fixture can't: that the actual v1.11.0 entry's
    // screenshot is wired up correctly.
    it('renders the v1.11.0 entry\'s screenshot with a translated alt text', () => {
      renderDialog();
      const images = screen.getAllByRole('img');
      expect(images).toHaveLength(1);
      expect(images[0]).toHaveAttribute('src', '/release-notes/1.11.0/admin-kebab-menu.png');
      expect(images[0]).toHaveAttribute(
        'alt',
        'Benutzerverwaltung im Admin-Panel: Aktionen jetzt übersichtlich in einem Kebab-Menü zusammengefasst'
      );
    });

    it('keeps an older release collapsed by default', () => {
      renderDialog();
      expect(
        screen.queryByText(
          'Resultatimport mit Freitextfragen läuft jetzt zuverlässig im Hintergrund, mit sichtbarem Fortschritt'
        )
      ).not.toBeInTheDocument();
    });

    it('links to the full GitHub releases page as a fallback', () => {
      renderDialog();
      const link = screen.getByRole('link', { name: /GitHub/i });
      expect(link).toHaveAttribute('href', 'https://github.com/talent-factory/examcraft/releases');
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'));
    });
  });

  // -------------------------------------------------------------------------
  // Interaction
  // -------------------------------------------------------------------------

  describe('interaction', () => {
    it('expands an older release on click and shows its content', () => {
      renderDialog();
      fireEvent.click(screen.getByRole('button', { name: /1\.8\.4/ }));
      expect(
        screen.getByText(
          'Resultatimport mit Freitextfragen läuft jetzt zuverlässig im Hintergrund, mit sichtbarem Fortschritt'
        )
      ).toBeInTheDocument();
    });

    it('collapses an expanded release back on a second click', async () => {
      renderDialog();
      const toggle = screen.getByRole('button', { name: /1\.8\.4/ });
      fireEvent.click(toggle);
      fireEvent.click(toggle);
      // MUI's <Collapse unmountOnExit> only unmounts its children once the
      // exit transition finishes, so the removal is asynchronous.
      await waitFor(() =>
        expect(
          screen.queryByText(
            'Resultatimport mit Freitextfragen läuft jetzt zuverlässig im Hintergrund, mit sichtbarem Fortschritt'
          )
        ).not.toBeInTheDocument()
      );
    });

    it('calls onClose when the close button is clicked', () => {
      const onClose = jest.fn();
      render(<ReleaseNotesDialog open onClose={onClose} />, { wrapper: Wrapper });
      fireEvent.click(screen.getByRole('button', { name: 'Schliessen' }));
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  // -------------------------------------------------------------------------
  // Language switcher wiring
  // -------------------------------------------------------------------------

  describe('language switcher', () => {
    it.each([
      ['EN', 'en'],
      ['FR', 'fr'],
      ['IT', 'it'],
      ['DE', 'de'],
    ])('calls i18n.changeLanguage with "%s" when the %s pill is clicked', (label, code) => {
      renderDialog();
      fireEvent.click(screen.getByRole('button', { name: label }));
      const { i18n: mockI18n } = jest.requireMock('react-i18next').useTranslation();
      expect(mockI18n.changeLanguage).toHaveBeenCalledWith(code);
    });
  });
});

// ---------------------------------------------------------------------------
// Translation completeness — real i18n files, no react-i18next involved.
// ---------------------------------------------------------------------------

describe('releaseNotes translation completeness', () => {
  const LANGS = ['de', 'en', 'fr', 'it'];
  const SECTIONS = ['dialog', 'groups', 'entries'] as const;

  const releaseNotesByLang = Object.fromEntries(
    LANGS.map((lang) => [
      lang,
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      require(`../../../locales/${lang}/translation.json`).releaseNotes,
    ])
  );

  it('has a releaseNotes namespace in every supported locale', () => {
    LANGS.forEach((lang) => {
      expect(releaseNotesByLang[lang]).toBeDefined();
    });
  });

  it.each(SECTIONS)('has identical %s keys across de/en/fr/it', (section) => {
    const referenceKeys = Object.keys(releaseNotesByLang.de[section]).sort();
    LANGS.filter((lang) => lang !== 'de').forEach((lang) => {
      expect(Object.keys(releaseNotesByLang[lang][section]).sort()).toEqual(referenceKeys);
    });
  });

  it('has no empty translated strings', () => {
    LANGS.forEach((lang) => {
      SECTIONS.forEach((section) => {
        Object.entries(releaseNotesByLang[lang][section]).forEach(([key, value]) => {
          expect(typeof value).toBe('string');
          expect((value as string).trim().length).toBeGreaterThan(0);
        });
      });
    });
  });
});
