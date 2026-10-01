/**
 * Template list + editor with a mocked API (TF-988): create, edit and delete
 * a template with 2 phases × 2 criteria, rubric fields following max_points,
 * marking invalid input before sending, read-only view for non-owners, and
 * the 409s the backend answers with once assessments use a template.
 */
import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PortfolioTemplatesPage from '../PortfolioTemplatesPage';
import { portfolioApi } from '../../../api/portfolioApi';
import { AppError } from '../../../errors';
import { OrgUnitsService } from '../../../services/orgUnitsService';
import type { PortfolioTemplate } from '../../../types/portfolio';

let mockUser = { id: 1, is_superuser: false };
let mockPermissions: string[] = [];
jest.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    hasPermission: (permission: string) => mockPermissions.includes(permission),
  }),
}));

jest.mock('../../../api/portfolioApi', () => ({
  portfolioApi: {
    listTemplates: jest.fn(),
    createTemplate: jest.fn(),
    updateTemplate: jest.fn(),
    deleteTemplate: jest.fn(),
  },
}));

jest.mock('../../../services/orgUnitsService', () => ({
  OrgUnitsService: {
    mine: jest.fn().mockResolvedValue({ items: [{ id: 4, name: 'Informatik' }] }),
  },
}));

const api = portfolioApi as jest.Mocked<typeof portfolioApi>;
const mineOrgUnits = OrgUnitsService.mine as jest.Mock;

function criterion(id: string, position: number, name: string) {
  return {
    id,
    position,
    name,
    type_tag: null,
    max_points: 1,
    rubric_by_score: { '0': 'nicht erfüllt', '1': 'erfüllt' },
    checklist_items: null,
  };
}

function template(overrides: Partial<PortfolioTemplate> = {}): PortfolioTemplate {
  return {
    id: 't-1',
    name: 'HERMES-Diplomarbeit',
    description: 'Vorlage',
    visibility: 'team',
    org_unit_id: 4,
    institution_id: 1,
    created_by: 1,
    version: 3,
    is_active: true,
    created_at: null,
    updated_at: null,
    phases: [
      {
        id: 'p-1',
        position: 0,
        name: 'Initialisierung',
        description: null,
        expected_folder_patterns: null,
        criteria: [criterion('c-1', 0, 'Ausgangslage'), criterion('c-2', 1, 'Zeitplan')],
      },
      {
        id: 'p-2',
        position: 1,
        name: 'Umsetzung',
        description: null,
        expected_folder_patterns: ['src'],
        criteria: [criterion('c-3', 0, 'Code'), criterion('c-4', 1, 'Tests')],
      },
    ],
    ...overrides,
  };
}

const foreign = template({ id: 't-2', name: 'Fremdes Template', created_by: 99, visibility: 'institution', org_unit_id: null });

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <PortfolioTemplatesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const change = (testId: string, value: string) =>
  fireEvent.change(screen.getByTestId(testId), { target: { value } });

function fillCriterion(phase: number, index: number, name: string) {
  const id = `pt-phase-${phase}-criterion-${index}`;
  change(`${id}-name`, name);
  change(`${id}-max-points`, '1');
  change(`${id}-rubric-0`, `${name}: nichts`);
  change(`${id}-rubric-1`, `${name}: alles`);
}

beforeEach(() => {
  jest.clearAllMocks();
  mockUser = { id: 1, is_superuser: false };
  mockPermissions = ['portfolio_templates:read', 'portfolio_templates:manage'];
  api.listTemplates.mockResolvedValue([template(), foreign]);
});

describe('PortfolioTemplatesPage — list', () => {
  it('shows visibility, phase count, version and status; owner gets edit + delete', async () => {
    api.listTemplates.mockResolvedValue([template({ is_active: false }), foreign]);
    renderPage();

    const own = within(await screen.findByTestId('pt-row-t-1'));
    expect(own.getByText('HERMES-Diplomarbeit')).toBeInTheDocument();
    expect(own.getByText('Eigenes')).toBeInTheDocument();
    expect(own.getByText('Team')).toBeInTheDocument();
    expect(own.getByText('Inaktiv')).toBeInTheDocument();
    expect(own.getByText('3')).toBeInTheDocument();
    expect(own.getByLabelText('Bearbeiten: HERMES-Diplomarbeit')).toBeInTheDocument();
    expect(own.getByTestId('pt-delete-t-1')).toBeInTheDocument();

    const other = within(screen.getByTestId('pt-row-t-2'));
    expect(other.getByText('Institution')).toBeInTheDocument();
    expect(other.getByText('Aktiv')).toBeInTheDocument();
    expect(other.getByLabelText('Ansehen: Fremdes Template')).toBeInTheDocument();
    expect(other.queryByTestId('pt-delete-t-2')).not.toBeInTheDocument();
  });

  it('without manage permission even the own template is read-only and nothing can be created', async () => {
    mockPermissions = ['portfolio_templates:read'];
    renderPage();

    await screen.findByTestId('pt-row-t-1');
    expect(screen.queryByTestId('pt-create')).not.toBeInTheDocument();
    expect(screen.queryByTestId('pt-delete-t-1')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Ansehen: HERMES-Diplomarbeit')).toBeInTheDocument();
  });

  it('a SuperUser may edit and delete templates of others', async () => {
    mockUser = { id: 7, is_superuser: true };
    renderPage();

    await screen.findByTestId('pt-row-t-2');
    expect(screen.getByTestId('pt-delete-t-2')).toBeInTheDocument();
    expect(screen.getByLabelText('Bearbeiten: Fremdes Template')).toBeInTheDocument();
  });
});

describe('PortfolioTemplatesPage — read-only view', () => {
  it('non-owners see the template without any edit action', async () => {
    renderPage();
    fireEvent.click(await screen.findByTestId('pt-open-t-2'));

    const dialog = within(await screen.findByTestId('pt-editor-dialog'));
    expect(dialog.getByText('Portfolio-Template ansehen')).toBeInTheDocument();
    expect(dialog.getByTestId('pt-editor-readonly')).toBeInTheDocument();
    expect(dialog.getByTestId('pt-field-name')).toHaveAttribute('readonly');
    expect(dialog.getByTestId('pt-phase-0-criterion-0-rubric-1')).toHaveAttribute('readonly');
    expect(dialog.queryByTestId('pt-editor-save')).not.toBeInTheDocument();
    expect(dialog.queryByTestId('pt-add-phase')).not.toBeInTheDocument();
    expect(dialog.queryByTestId('pt-phase-0-add-criterion')).not.toBeInTheDocument();
    expect(dialog.queryByTestId('pt-phase-0-remove')).not.toBeInTheDocument();
    expect(dialog.getByText('Schliessen')).toBeInTheDocument();
  });
});

describe('PortfolioTemplatesPage — create', () => {
  it('creates a template with 2 phases × 2 criteria', async () => {
    api.createTemplate.mockResolvedValue(template({ id: 't-new' }));
    renderPage();
    fireEvent.click(await screen.findByTestId('pt-create'));
    await screen.findByTestId('pt-editor-dialog');

    change('pt-field-name', 'Neue Vorlage');
    change('pt-phase-0-name', 'Planung');
    change('pt-phase-0-folder-patterns', '01_plan, planung');
    fillCriterion(0, 0, 'Ziele');
    fireEvent.click(screen.getByTestId('pt-phase-0-add-criterion'));
    fillCriterion(0, 1, 'Risiken');
    change('pt-phase-0-criterion-1-checklist', 'Liste\nBewertung');

    fireEvent.click(screen.getByTestId('pt-add-phase'));
    change('pt-phase-1-name', 'Abschluss');
    fillCriterion(1, 0, 'Fazit');
    fireEvent.click(screen.getByTestId('pt-phase-1-add-criterion'));
    fillCriterion(1, 1, 'Reflexion');

    fireEvent.click(screen.getByTestId('pt-editor-save'));

    await waitFor(() => expect(api.createTemplate).toHaveBeenCalledTimes(1));
    const payload = api.createTemplate.mock.calls[0][0];
    expect(payload).toMatchObject({
      name: 'Neue Vorlage',
      description: null,
      visibility: 'private',
      org_unit_id: null,
      is_active: true,
    });
    expect(payload.phases.map((p) => p.name)).toEqual(['Planung', 'Abschluss']);
    expect(payload.phases[0].expected_folder_patterns).toEqual(['01_plan', 'planung']);
    expect(payload.phases[0].criteria[1]).toEqual({
      name: 'Risiken',
      type_tag: null,
      max_points: 1,
      rubric_by_score: { '0': 'Risiken: nichts', '1': 'Risiken: alles' },
      checklist_items: ['Liste', 'Bewertung'],
    });
    expect(payload.phases[1].criteria.map((c) => c.name)).toEqual(['Fazit', 'Reflexion']);

    await waitFor(() => expect(screen.queryByTestId('pt-editor-dialog')).not.toBeInTheDocument());
    // The list is refetched after saving.
    expect(api.listTemplates).toHaveBeenCalledTimes(2);
  });

  it('rubric fields follow max_points', async () => {
    renderPage();
    fireEvent.click(await screen.findByTestId('pt-create'));
    await screen.findByTestId('pt-editor-dialog');
    const id = 'pt-phase-0-criterion-0';

    // Default 3 points → scores 0…3.
    expect(screen.getByTestId(`${id}-rubric-3`)).toBeInTheDocument();
    expect(screen.queryByTestId(`${id}-rubric-4`)).not.toBeInTheDocument();

    change(`${id}-rubric-1`, 'bleibt');
    change(`${id}-max-points`, '5');
    expect(screen.getByTestId(`${id}-rubric-5`)).toBeInTheDocument();
    // Required fields append « *» to the label; singular for 1.
    expect(screen.getByLabelText(/^5 Punkte/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^1 Punkt\b(?!e)/)).toBeInTheDocument();

    change(`${id}-max-points`, '1');
    expect(screen.queryByTestId(`${id}-rubric-2`)).not.toBeInTheDocument();
    expect(screen.getByTestId(`${id}-rubric-1`)).toHaveValue('bleibt');

    change(`${id}-max-points`, '0');
    expect(screen.queryByTestId(`${id}-rubric-0`)).not.toBeInTheDocument();
    expect(screen.getByTestId(`${id}-rubric-hint`)).toBeInTheDocument();
  });

  it('marks invalid input before sending and sends nothing', async () => {
    renderPage();
    fireEvent.click(await screen.findByTestId('pt-create'));
    await screen.findByTestId('pt-editor-dialog');

    change('pt-phase-0-criterion-0-name', 'Ziele');
    change('pt-phase-0-criterion-0-max-points', '101');
    fireEvent.click(screen.getByTestId('pt-add-phase'));
    change('pt-phase-1-criterion-0-name', 'Fazit');
    change('pt-phase-1-criterion-0-max-points', '1');
    change('pt-phase-1-criterion-0-rubric-0', 'nichts');

    fireEvent.click(screen.getByTestId('pt-editor-save'));

    expect(await screen.findByTestId('pt-editor-field-hint')).toBeInTheDocument();
    expect(screen.getByTestId('pt-field-name')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByTestId('pt-phase-0-name')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByTestId('pt-phase-0-criterion-0-max-points')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByText('Ganze Zahl von 1 bis 100 eingeben.')).toBeInTheDocument();
    expect(screen.getByTestId('pt-phase-1-criterion-0-rubric-0')).toHaveAttribute('aria-invalid', 'false');
    expect(screen.getByTestId('pt-phase-1-criterion-0-rubric-1')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByText('Rubrik-Text fehlt für: 1 Punkte')).toBeInTheDocument();
    expect(api.createTemplate).not.toHaveBeenCalled();

    // Fixing a field clears its mark live.
    change('pt-field-name', 'Jetzt mit Name');
    expect(screen.getByTestId('pt-field-name')).toHaveAttribute('aria-invalid', 'false');
  });

  it('requires an org unit for team visibility', async () => {
    renderPage();
    fireEvent.click(await screen.findByTestId('pt-create'));
    const dialog = within(await screen.findByTestId('pt-editor-dialog'));

    fireEvent.mouseDown(dialog.getByRole('combobox', { name: /Sichtbarkeit/ }));
    fireEvent.click(await screen.findByRole('option', { name: 'Team' }));
    fireEvent.click(screen.getByTestId('pt-editor-save'));

    expect(await screen.findByTestId('pt-field-org-unit-error')).toHaveTextContent(
      'Für «Team» eine Org-Unit wählen.',
    );
    expect(api.createTemplate).not.toHaveBeenCalled();
  });

  it('shows a rubric error of the API at the named criterion', async () => {
    api.createTemplate.mockRejectedValue(
      new AppError('portfolio_template_incomplete_rubric', 'x', 422, { criterion: 'Ziele', missing: '1' }),
    );
    renderPage();
    fireEvent.click(await screen.findByTestId('pt-create'));
    await screen.findByTestId('pt-editor-dialog');
    change('pt-field-name', 'Neu');
    change('pt-phase-0-name', 'Planung');
    fillCriterion(0, 0, 'Ziele');

    fireEvent.click(screen.getByTestId('pt-editor-save'));

    expect(
      await screen.findByText('Kriterium „Ziele“: Bewertungsrubrik fehlt für Punktwert(e) 1.'),
    ).toBeInTheDocument();
    expect(screen.queryByTestId('pt-editor-error')).not.toBeInTheDocument();
  });

  it('shows the visibility refusal of the API at the visibility field', async () => {
    api.createTemplate.mockRejectedValue(
      new AppError('portfolio_template_visibility_system_forbidden', 'x', 403),
    );
    renderPage();
    fireEvent.click(await screen.findByTestId('pt-create'));
    await screen.findByTestId('pt-editor-dialog');
    change('pt-field-name', 'Neu');
    change('pt-phase-0-name', 'Planung');
    fillCriterion(0, 0, 'Ziele');

    fireEvent.click(screen.getByTestId('pt-editor-save'));

    const message = await screen.findByText('Nur Superuser dürfen system-weite Templates anlegen.');
    expect(message).toHaveClass('MuiFormHelperText-root');
  });
});

describe('PortfolioTemplatesPage — edit', () => {
  async function openOwn() {
    renderPage();
    fireEvent.click(await screen.findByTestId('pt-open-t-1'));
    return within(await screen.findByTestId('pt-editor-dialog'));
  }

  it('sends the full template on PUT, including unchanged master data', async () => {
    api.updateTemplate.mockResolvedValue(template());
    const dialog = await openOwn();
    expect(dialog.getByText('Portfolio-Template bearbeiten')).toBeInTheDocument();
    await dialog.findByText('Informatik');

    change('pt-field-name', 'Umbenannt');
    fireEvent.click(dialog.getByTestId('pt-phase-1-up'));
    fireEvent.click(dialog.getByTestId('pt-phase-0-criterion-1-remove'));
    fireEvent.click(dialog.getByTestId('pt-editor-save'));

    await waitFor(() => expect(api.updateTemplate).toHaveBeenCalledTimes(1));
    const [id, payload] = api.updateTemplate.mock.calls[0];
    expect(id).toBe('t-1');
    expect(payload).toMatchObject({
      name: 'Umbenannt',
      description: 'Vorlage',
      visibility: 'team',
      org_unit_id: 4,
      is_active: true,
    });
    expect(payload.phases.map((p) => p.name)).toEqual(['Umsetzung', 'Initialisierung']);
    expect(payload.phases[0].criteria.map((c) => c.name)).toEqual(['Code']);
    expect(payload.phases[0].expected_folder_patterns).toEqual(['src']);
  });

  it('the last phase and the last criterion cannot be removed', async () => {
    api.listTemplates.mockResolvedValue([
      template({ phases: [{ ...template().phases[0], criteria: [criterion('c-1', 0, 'Einzig')] }] }),
    ]);
    const dialog = await openOwn();
    expect(dialog.getByTestId('pt-phase-0-remove')).toBeDisabled();
    expect(dialog.getByTestId('pt-phase-0-criterion-0-remove')).toBeDisabled();
    expect(dialog.getByTestId('pt-phase-0-up')).toBeDisabled();
  });

  it('explains the phase lock and still saves master data after discarding phase changes', async () => {
    api.updateTemplate
      .mockRejectedValueOnce(new AppError('portfolio_template_phases_locked', 'x', 409))
      .mockResolvedValueOnce(template());
    const dialog = await openOwn();

    change('pt-field-name', 'Neuer Name');
    change('pt-phase-0-name', 'Geänderte Phase');
    fireEvent.click(dialog.getByTestId('pt-editor-save'));

    const lock = await dialog.findByTestId('pt-editor-phases-locked');
    expect(lock).toHaveTextContent('bereits von Portfolio-Bewertungen verwendet');
    expect(dialog.getByTestId('pt-editor-save')).toBeDisabled();

    fireEvent.click(dialog.getByTestId('pt-editor-revert-phases'));
    expect(dialog.getByTestId('pt-phase-0-name')).toHaveValue('Initialisierung');
    expect(dialog.getByTestId('pt-phase-0-name')).toHaveAttribute('readonly');
    expect(dialog.queryByTestId('pt-add-phase')).not.toBeInTheDocument();
    expect(dialog.getByTestId('pt-field-name')).toHaveValue('Neuer Name');

    fireEvent.click(dialog.getByTestId('pt-editor-save'));
    await waitFor(() => expect(api.updateTemplate).toHaveBeenCalledTimes(2));
    const payload = api.updateTemplate.mock.calls[1][1];
    expect(payload.name).toBe('Neuer Name');
    expect(payload.phases.map((p) => p.name)).toEqual(['Initialisierung', 'Umsetzung']);
  });

  it('shows any other API error above the form', async () => {
    api.updateTemplate.mockRejectedValue(new AppError('portfolio_template_edit_forbidden', 'x', 403));
    const dialog = await openOwn();
    fireEvent.click(dialog.getByTestId('pt-editor-save'));

    expect(await dialog.findByTestId('pt-editor-error')).toHaveTextContent(
      'Du darfst dieses Portfolio-Template nicht bearbeiten.',
    );
  });
});

describe('PortfolioTemplatesPage — delete', () => {
  it('deletes after confirmation', async () => {
    api.deleteTemplate.mockResolvedValue({ id: 't-1' });
    renderPage();
    fireEvent.click(await screen.findByTestId('pt-delete-t-1'));

    const dialog = within(await screen.findByTestId('pt-delete-dialog'));
    expect(dialog.getByText(/«HERMES-Diplomarbeit» wird endgültig gelöscht/)).toBeInTheDocument();
    expect(api.deleteTemplate).not.toHaveBeenCalled();
    fireEvent.click(dialog.getByTestId('pt-delete-confirm'));

    await waitFor(() => expect(api.deleteTemplate).toHaveBeenCalledWith('t-1'));
    await waitFor(() => expect(api.listTemplates).toHaveBeenCalledTimes(2));
  });

  it('cancelling does not delete', async () => {
    renderPage();
    fireEvent.click(await screen.findByTestId('pt-delete-t-1'));
    fireEvent.click(within(await screen.findByTestId('pt-delete-dialog')).getByText('Abbrechen'));
    await waitFor(() => expect(screen.queryByTestId('pt-delete-dialog')).not.toBeInTheDocument());
    expect(api.deleteTemplate).not.toHaveBeenCalled();
  });

  it('explains why a template in use cannot be deleted', async () => {
    api.deleteTemplate.mockRejectedValue(new AppError('portfolio_template_delete_blocked', 'x', 409));
    renderPage();
    fireEvent.click(await screen.findByTestId('pt-delete-t-1'));
    fireEvent.click(within(await screen.findByTestId('pt-delete-dialog')).getByTestId('pt-delete-confirm'));

    expect(await screen.findByTestId('pt-delete-error')).toHaveTextContent(
      'Das Template kann nicht gelöscht werden, da es bereits in Portfolio-Assessments verwendet wird.',
    );
  });
});

describe('PortfolioTemplatesPage — review follow-ups', () => {
  async function openOwn() {
    fireEvent.click(await screen.findByTestId('pt-open-t-1'));
    return within(await screen.findByTestId('pt-editor-dialog'));
  }

  async function openCreate() {
    fireEvent.click(await screen.findByTestId('pt-create'));
    await screen.findByTestId('pt-editor-dialog');
    change('pt-field-name', 'Neu');
    change('pt-phase-0-name', 'Planung');
    fillCriterion(0, 0, 'Ziele');
  }

  it('a master-data-only edit sends the stored phases verbatim (no false phase change)', async () => {
    const stored = template();
    stored.phases[0].description = '';
    stored.phases[0].criteria[0] = {
      ...stored.phases[0].criteria[0],
      type_tag: '',
      checklist_items: [],
      rubric_by_score: { '0': ' nicht erfüllt ', '1': 'erfüllt', '2': 'übrig' },
    };
    api.listTemplates.mockResolvedValue([stored]);
    api.updateTemplate.mockResolvedValue(stored);
    renderPage();
    const dialog = await openOwn();

    change('pt-field-name', 'Nur umbenannt');
    fireEvent.click(dialog.getByTestId('pt-editor-save'));

    await waitFor(() => expect(api.updateTemplate).toHaveBeenCalledTimes(1));
    const payload = api.updateTemplate.mock.calls[0][1];
    expect(payload.name).toBe('Nur umbenannt');
    expect(payload.phases[0].description).toBe('');
    expect(payload.phases[0].criteria[0]).toEqual({
      name: 'Ausgangslage',
      type_tag: '',
      max_points: 1,
      rubric_by_score: { '0': ' nicht erfüllt ', '1': 'erfüllt', '2': 'übrig' },
      checklist_items: [],
    });
  });

  it('a second phase lock after discarding shows a message instead of looping', async () => {
    api.updateTemplate.mockRejectedValue(new AppError('portfolio_template_phases_locked', 'x', 409));
    renderPage();
    const dialog = await openOwn();
    change('pt-phase-0-name', 'Geändert');
    fireEvent.click(dialog.getByTestId('pt-editor-save'));
    fireEvent.click(await dialog.findByTestId('pt-editor-revert-phases'));
    fireEvent.click(dialog.getByTestId('pt-editor-save'));

    expect(await dialog.findByTestId('pt-editor-error')).toHaveTextContent(
      'Die gespeicherten Phasen lassen sich nicht unverändert zurücksenden',
    );
    expect(dialog.queryByTestId('pt-editor-revert-phases')).not.toBeInTheDocument();
  });

  it('maps invalid_max_points to the max-points field of that criterion', async () => {
    api.createTemplate.mockRejectedValue(
      new AppError('portfolio_template_invalid_max_points', 'x', 422, { criterion: 'Ziele', max: 100 }),
    );
    renderPage();
    await openCreate();
    fireEvent.click(screen.getByTestId('pt-editor-save'));

    await waitFor(() =>
      expect(screen.getByTestId('pt-phase-0-criterion-0-max-points')).toHaveAttribute('aria-invalid', 'true'),
    );
    expect(screen.getByText('Kriterium „Ziele“: max_points muss zwischen 1 und 100 liegen.')).toBeInTheDocument();
  });

  it('keeps a rubric error of an unknown criterion visible above the form', async () => {
    api.createTemplate.mockRejectedValue(
      new AppError('portfolio_template_incomplete_rubric', 'x', 422, { criterion: 'Weg', missing: '0' }),
    );
    renderPage();
    await openCreate();
    fireEvent.click(screen.getByTestId('pt-editor-save'));

    expect(await screen.findByTestId('pt-editor-error')).toHaveTextContent('Kriterium „Weg“');
  });

  it('shows a failed org-unit load (with retry) rather than «choose one»', async () => {
    mineOrgUnits.mockRejectedValueOnce(new Error('offline'));
    renderPage();
    fireEvent.click(await screen.findByTestId('pt-create'));
    const dialog = within(await screen.findByTestId('pt-editor-dialog'));
    fireEvent.mouseDown(dialog.getByRole('combobox', { name: /Sichtbarkeit/ }));
    fireEvent.click(await screen.findByRole('option', { name: 'Team' }));
    fireEvent.click(screen.getByTestId('pt-editor-save'));

    const loadError = await screen.findByTestId('pt-field-org-unit-load-error');
    expect(loadError).toHaveTextContent('Team-Liste konnte nicht geladen werden');
    expect(screen.queryByTestId('pt-field-org-unit-error')).not.toBeInTheDocument();

    fireEvent.click(within(loadError).getByText('Erneut versuchen'));
    await waitFor(() => expect(screen.queryByTestId('pt-field-org-unit-load-error')).not.toBeInTheDocument());
    expect(mineOrgUnits).toHaveBeenCalledTimes(2);
  });

  it('offers «System» only to SuperUsers', async () => {
    renderPage();
    fireEvent.click(await screen.findByTestId('pt-create'));
    const dialog = within(await screen.findByTestId('pt-editor-dialog'));
    fireEvent.mouseDown(dialog.getByRole('combobox', { name: /Sichtbarkeit/ }));
    await screen.findByRole('option', { name: 'Team' });
    expect(screen.queryByRole('option', { name: /System/ })).not.toBeInTheDocument();
  });

  it('reopening resets the editor (no leftover lock or content)', async () => {
    api.updateTemplate.mockRejectedValue(new AppError('portfolio_template_phases_locked', 'x', 409));
    renderPage();
    const dialog = await openOwn();
    change('pt-phase-0-name', 'Geändert');
    fireEvent.click(dialog.getByTestId('pt-editor-save'));
    await dialog.findByTestId('pt-editor-phases-locked');
    fireEvent.click(dialog.getByTestId('pt-editor-cancel'));
    await waitFor(() => expect(screen.queryByTestId('pt-editor-dialog')).not.toBeInTheDocument());

    fireEvent.click(screen.getByTestId('pt-create'));
    await screen.findByTestId('pt-editor-dialog');
    expect(screen.getByTestId('pt-field-name')).toHaveValue('');
    expect(screen.queryByTestId('pt-editor-phases-locked')).not.toBeInTheDocument();
    expect(screen.getByTestId('pt-editor-save')).toBeEnabled();
  });

  it('refetches the list when a template vanished (404 on save or delete)', async () => {
    api.updateTemplate.mockRejectedValue(new AppError('portfolio_template_not_found', 'x', 404));
    api.deleteTemplate.mockRejectedValue(new AppError('portfolio_template_not_found', 'x', 404));
    renderPage();
    const dialog = await openOwn();
    fireEvent.click(dialog.getByTestId('pt-editor-save'));
    expect(await dialog.findByTestId('pt-editor-error')).toHaveTextContent('Portfolio-Template nicht gefunden.');
    await waitFor(() => expect(api.listTemplates).toHaveBeenCalledTimes(2));

    fireEvent.click(dialog.getByTestId('pt-editor-cancel'));
    fireEvent.click(await screen.findByTestId('pt-delete-t-1'));
    fireEvent.click(within(await screen.findByTestId('pt-delete-dialog')).getByTestId('pt-delete-confirm'));
    expect(await screen.findByTestId('pt-delete-error')).toBeInTheDocument();
    await waitFor(() => expect(api.listTemplates).toHaveBeenCalledTimes(3));
  });
});
