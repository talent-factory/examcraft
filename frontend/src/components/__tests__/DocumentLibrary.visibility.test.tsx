/**
 * Tests for the document-card visibility icon + quick-edit dialog (TF-354).
 *
 * Mocks react-i18next (t returns the key), useAuth, and DocumentService.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { MemoryRouter } from 'react-router-dom';
import DocumentLibrary from '../DocumentLibrary';
import { DocumentService } from '../../services/DocumentService';
import { OrgUnitsService } from '../../services/orgUnitsService';
import { Document, DocumentStatus, DocumentVisibility } from '../../types/document';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: unknown) =>
      opts && typeof opts === 'object' && 'institution' in opts
        ? `${key}:${(opts as Record<string, unknown>).institution}`
        : key,
    i18n: { language: 'de' },
  }),
}));

const mockUseAuth = jest.fn();
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

jest.mock('../../services/DocumentService');
const mockDocumentService = DocumentService as jest.Mocked<typeof DocumentService>;

jest.mock('../../services/orgUnitsService');
const mockOrgUnitsService = OrgUnitsService as jest.Mocked<typeof OrgUnitsService>;

const theme = createTheme();
const wrap = (ui: React.ReactElement) => (
  <ThemeProvider theme={theme}>
    <MemoryRouter>{ui}</MemoryRouter>
  </ThemeProvider>
);

// TF-355: DocumentLibrary now loads via the paginated `listDocuments` contract.
const paged = (docs: Document[]) => ({
  documents: docs,
  total: docs.length,
  page: 1,
  page_size: 24,
  total_pages: 1,
  stats: { total: docs.length, processed: docs.length, with_vectors: 0, in_progress: 0 },
});

const makeDoc = (overrides: Partial<Document>): Document => ({
  id: 1,
  filename: 'doc.pdf',
  original_filename: 'doc.pdf',
  title: 'My Document',
  mime_type: 'application/pdf',
  status: DocumentStatus.PROCESSED,
  created_at: '2026-05-28T10:00:00Z',
  has_vectors: true,
  user_id: 42,
  visibility: DocumentVisibility.PRIVATE,
  ...overrides,
});

beforeEach(() => {
  jest.clearAllMocks();
  mockUseAuth.mockReturnValue({
    user: { id: 42, institution_id: 7, institution: { id: 7, name: 'Test University' } },
  });
  mockDocumentService.listDocumentTags.mockResolvedValue([]);
  mockOrgUnitsService.mine.mockResolvedValue({ items: [] });
});

describe('DocumentLibrary visibility (TF-354)', () => {
  it('renders the lock icon for a private document', async () => {
    mockDocumentService.listDocuments.mockResolvedValue(paged([makeDoc({ visibility: DocumentVisibility.PRIVATE })]));
    render(wrap(<DocumentLibrary />));
    await screen.findByText('My Document');
    expect(screen.getByTestId('LockOutlinedIcon')).toBeInTheDocument();
  });

  it('renders the business icon for an institution document', async () => {
    mockDocumentService.listDocuments.mockResolvedValue(paged([
      makeDoc({ visibility: DocumentVisibility.INSTITUTION }),
    ]));
    render(wrap(<DocumentLibrary />));
    await screen.findByText('My Document');
    expect(screen.getByTestId('BusinessIcon')).toBeInTheDocument();
  });

  it('owner clicking the icon opens the visibility edit dialog and saves', async () => {
    mockDocumentService.listDocuments.mockResolvedValue(paged([makeDoc({})]));
    mockDocumentService.updateVisibility.mockResolvedValue(
      makeDoc({ visibility: DocumentVisibility.INSTITUTION }),
    );
    render(wrap(<DocumentLibrary />));
    await screen.findByText('My Document');

    fireEvent.click(screen.getByLabelText('components.documentLibrary.visibilityEditAria'));

    // Dialog opened.
    expect(await screen.findByText('components.documentVisibility.title')).toBeInTheDocument();

    // Pick the institution radio (2nd in the dialog) and save.
    const radios = screen.getAllByRole('radio') as HTMLInputElement[];
    fireEvent.click(radios[radios.length - 1]);
    fireEvent.click(screen.getByText('components.documentVisibility.save'));

    await waitFor(() => {
      expect(mockDocumentService.updateVisibility).toHaveBeenCalledWith(
        1,
        DocumentVisibility.INSTITUTION,
        undefined,
      );
    });
  });

  it('non-owner sees a static icon (no edit button)', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: 99, institution_id: 7, institution: { id: 7, name: 'Test University' } },
    });
    mockDocumentService.listDocuments.mockResolvedValue(paged([
      makeDoc({ visibility: DocumentVisibility.INSTITUTION, user_id: 42 }),
    ]));
    render(wrap(<DocumentLibrary />));
    await screen.findByText('My Document');
    expect(
      screen.queryByLabelText('components.documentLibrary.visibilityEditAria'),
    ).not.toBeInTheDocument();
  });

  it('logs and gracefully falls back when loading Org-Unit memberships fails', async () => {
    // Regression for the bug where a rejected OrgUnitsService.mine() call was
    // silently swallowed into an empty list with no trace anywhere (TF-620).
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockOrgUnitsService.mine.mockRejectedValue(new Error('network down'));
    mockDocumentService.listDocuments.mockResolvedValue(paged([makeDoc({})]));
    render(wrap(<DocumentLibrary />));
    await screen.findByText('My Document');

    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Failed to load Org-Unit memberships:',
        expect.any(Error),
      );
    });

    consoleErrorSpy.mockRestore();
  });

  describe('team visibility (TF-620)', () => {
    const teamOrgUnits = [
      {
        id: 42,
        parent_org_unit_id: null,
        unit_type: 'team',
        name: 'Backend',
        descendant_count: 0,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ];

    it('owner can switch to team visibility and pick an Org-Unit', async () => {
      mockOrgUnitsService.mine.mockResolvedValue({ items: teamOrgUnits });
      mockDocumentService.listDocuments.mockResolvedValue(paged([makeDoc({})]));
      mockDocumentService.updateVisibility.mockResolvedValue(
        makeDoc({ visibility: DocumentVisibility.TEAM, org_unit_id: 42 }),
      );
      render(wrap(<DocumentLibrary />));
      await screen.findByText('My Document');

      fireEvent.click(screen.getByLabelText('components.documentLibrary.visibilityEditAria'));
      expect(await screen.findByText('components.documentVisibility.title')).toBeInTheDocument();

      // Order: private, team, institution — Team must be enabled now that
      // the caller has an Org-Unit membership.
      await waitFor(() => {
        const radios = screen.getAllByRole('radio') as HTMLInputElement[];
        expect(radios[1]).not.toBeDisabled();
      });
      fireEvent.click((screen.getAllByRole('radio') as HTMLInputElement[])[1]);

      // Save stays disabled until an Org-Unit is picked (isIncompleteTeamSelection).
      const saveButton = screen.getByRole('button', {
        name: 'components.documentVisibility.save',
      });
      expect(saveButton).toBeDisabled();

      fireEvent.mouseDown(
        screen.getByText('components.documentVisibility.orgUnitPickerPlaceholder'),
      );
      fireEvent.click(screen.getByText('Backend'));

      expect(saveButton).not.toBeDisabled();
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mockDocumentService.updateVisibility).toHaveBeenCalledWith(
          1,
          DocumentVisibility.TEAM,
          42,
        );
      });
    });

    it('team radio stays disabled when the caller has no Org-Unit memberships', async () => {
      mockDocumentService.listDocuments.mockResolvedValue(paged([makeDoc({})]));
      render(wrap(<DocumentLibrary />));
      await screen.findByText('My Document');

      fireEvent.click(screen.getByLabelText('components.documentLibrary.visibilityEditAria'));
      await screen.findByText('components.documentVisibility.title');

      const radios = screen.getAllByRole('radio') as HTMLInputElement[];
      expect(radios[1]).toBeDisabled();
    });
  });
});
