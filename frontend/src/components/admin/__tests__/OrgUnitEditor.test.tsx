/**
 * OrgUnitEditor tests (org-unit hierarchy, Stufe 0 follow-up).
 *
 * Covers what AdminOrgUnits.test.tsx doesn't: actually submitting the
 * create/edit dialog (name + unit_type dropdown + parent selection), the
 * move_to_root wiring on edit, and the cycle-prevention filter that excludes
 * a unit's own descendants from its parent dropdown.
 */

import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

import OrgUnitEditor from '../OrgUnitEditor';
import { OrgUnitsService } from '../../../services/orgUnitsService';
import { OrgUnitOut } from '../../../types/orgUnit';

jest.mock('../../../services/orgUnitsService');
const mockedService = OrgUnitsService as jest.Mocked<typeof OrgUnitsService>;

const theme = createTheme();
const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={theme}>{children}</ThemeProvider>
);

function makeUnit(overrides: Partial<OrgUnitOut> = {}): OrgUnitOut {
  return {
    id: 1,
    parent_org_unit_id: null,
    unit_type: 'abteilung',
    name: 'Informatik',
    descendant_count: 0,
    created_at: '2026-08-07T00:00:00Z',
    updated_at: '2026-08-07T00:00:00Z',
    ...overrides,
  };
}

async function selectDropdownOption(labelName: string, optionName: string) {
  const combo = screen.getByRole('combobox', { name: labelName });
  fireEvent.mouseDown(combo);
  const option = await screen.findByRole('option', { name: optionName });
  fireEvent.click(option);
}

beforeEach(() => jest.clearAllMocks());

describe('OrgUnitEditor — create', () => {
  it('submits unit_type from the dropdown, not free text', async () => {
    const onSaved = jest.fn();
    const onClose = jest.fn();
    mockedService.create.mockResolvedValue(makeUnit());

    render(
      <Wrapper>
        <OrgUnitEditor
          open
          orgUnit={null}
          allOrgUnits={[]}
          onClose={onClose}
          onSaved={onSaved}
        />
      </Wrapper>,
    );

    fireEvent.change(screen.getByTestId('ou-editor-field-name'), {
      target: { value: 'Backend-Team' },
    });
    await selectDropdownOption('Typ', 'Team');

    fireEvent.click(screen.getByTestId('ou-editor-btn-save'));

    await waitFor(() => expect(mockedService.create).toHaveBeenCalledTimes(1));
    expect(mockedService.create).toHaveBeenCalledWith({
      name: 'Backend-Team',
      unit_type: 'team',
      parent_org_unit_id: null,
    });
    await waitFor(() => expect(onSaved).toHaveBeenCalled());
    await waitFor(() => expect(onClose).toHaveBeenCalled());
  });

  it('offers exactly the known unit types (Abteilung, Team)', () => {
    render(
      <Wrapper>
        <OrgUnitEditor open orgUnit={null} allOrgUnits={[]} onClose={jest.fn()} onSaved={jest.fn()} />
      </Wrapper>,
    );

    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Typ' }));
    expect(screen.getByRole('option', { name: 'Abteilung' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Team' })).toBeInTheDocument();
    expect(screen.getAllByRole('option')).toHaveLength(2);
  });

  it('sends move_to_root: false and the chosen parent when a parent is picked', async () => {
    const abteilung = makeUnit({ id: 1, name: 'Informatik' });
    mockedService.create.mockResolvedValue(makeUnit({ id: 2 }));

    render(
      <Wrapper>
        <OrgUnitEditor
          open
          orgUnit={null}
          allOrgUnits={[abteilung]}
          onClose={jest.fn()}
          onSaved={jest.fn()}
        />
      </Wrapper>,
    );

    fireEvent.change(screen.getByTestId('ou-editor-field-name'), {
      target: { value: 'Backend' },
    });
    await selectDropdownOption('Typ', 'Team');
    await selectDropdownOption('Übergeordnete Einheit', 'Informatik');

    fireEvent.click(screen.getByTestId('ou-editor-btn-save'));

    await waitFor(() => expect(mockedService.create).toHaveBeenCalledTimes(1));
    expect(mockedService.create).toHaveBeenCalledWith({
      name: 'Backend',
      unit_type: 'team',
      parent_org_unit_id: 1,
    });
  });
});

describe('OrgUnitEditor — edit', () => {
  it('excludes the unit itself and all of its descendants from the parent dropdown', () => {
    const root = makeUnit({ id: 1, name: 'Informatik', parent_org_unit_id: null });
    const child = makeUnit({ id: 2, name: 'Backend', parent_org_unit_id: 1 });
    const grandchild = makeUnit({ id: 3, name: 'Platform', parent_org_unit_id: 2 });
    const unrelated = makeUnit({ id: 4, name: 'HR', parent_org_unit_id: null });

    render(
      <Wrapper>
        <OrgUnitEditor
          open
          orgUnit={root}
          allOrgUnits={[root, child, grandchild, unrelated]}
          onClose={jest.fn()}
          onSaved={jest.fn()}
        />
      </Wrapper>,
    );

    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Übergeordnete Einheit' }));
    // Editing "Informatik" (id 1): itself, "Backend" (child), and "Platform"
    // (grandchild) must all be excluded -- only "HR" plus the root option
    // ("— Keine (oberste Ebene) —") may be offered.
    expect(screen.queryByRole('option', { name: 'Informatik' })).not.toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Backend' })).not.toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Platform' })).not.toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'HR' })).toBeInTheDocument();
    expect(
      screen.getByRole('option', { name: '— Keine (oberste Ebene) —' }),
    ).toBeInTheDocument();
  });

  it('disables the unit_type dropdown (immutable after creation)', () => {
    const unit = makeUnit();
    render(
      <Wrapper>
        <OrgUnitEditor
          open
          orgUnit={unit}
          allOrgUnits={[unit]}
          onClose={jest.fn()}
          onSaved={jest.fn()}
        />
      </Wrapper>,
    );
    expect(screen.getByRole('combobox', { name: 'Typ' })).toHaveAttribute(
      'aria-disabled',
      'true',
    );
  });

  it('sends move_to_root: true when the parent is cleared to root', async () => {
    const parent = makeUnit({ id: 1, name: 'Informatik', parent_org_unit_id: null });
    const unit = makeUnit({ id: 2, name: 'Backend', parent_org_unit_id: 1 });
    mockedService.update.mockResolvedValue(unit);

    render(
      <Wrapper>
        <OrgUnitEditor
          open
          orgUnit={unit}
          allOrgUnits={[parent, unit]}
          onClose={jest.fn()}
          onSaved={jest.fn()}
        />
      </Wrapper>,
    );

    await selectDropdownOption('Übergeordnete Einheit', '— Keine (oberste Ebene) —');
    fireEvent.click(screen.getByTestId('ou-editor-btn-save'));

    await waitFor(() => expect(mockedService.update).toHaveBeenCalledTimes(1));
    expect(mockedService.update).toHaveBeenCalledWith(2, {
      name: 'Backend',
      parent_org_unit_id: null,
      move_to_root: true,
    });
  });

  it('sends move_to_root: false with the new parent id when re-parented', async () => {
    const parentA = makeUnit({ id: 1, name: 'Informatik', parent_org_unit_id: null });
    const parentB = makeUnit({ id: 3, name: 'HR', parent_org_unit_id: null });
    const unit = makeUnit({ id: 2, name: 'Backend', parent_org_unit_id: 1 });
    mockedService.update.mockResolvedValue(unit);

    render(
      <Wrapper>
        <OrgUnitEditor
          open
          orgUnit={unit}
          allOrgUnits={[parentA, parentB, unit]}
          onClose={jest.fn()}
          onSaved={jest.fn()}
        />
      </Wrapper>,
    );

    await selectDropdownOption('Übergeordnete Einheit', 'HR');
    fireEvent.click(screen.getByTestId('ou-editor-btn-save'));

    await waitFor(() => expect(mockedService.update).toHaveBeenCalledTimes(1));
    expect(mockedService.update).toHaveBeenCalledWith(2, {
      name: 'Backend',
      parent_org_unit_id: 3,
      move_to_root: false,
    });
  });
});
