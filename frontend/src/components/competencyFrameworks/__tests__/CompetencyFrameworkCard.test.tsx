import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import CompetencyFrameworkCard from '../CompetencyFrameworkCard';
import type { CompetencyFramework } from '../../../types/competencyFramework';

const framework: CompetencyFramework = {
  id: 7,
  name: 'Modul B – Wirkungsvoll kommunizieren',
  module_code: 'B',
  description: null,
  rendered_text: 'Volltext B',
  language: 'de',
  institution_id: 10,
  created_by: 1,
  visibility: 'institution',
  is_archived: false,
  competencies: [
    { id: 1, code: 'B3', title: 'Konflikte klären', descriptors: [{ text: 'x', ln_level: 2 }], position: 0 },
  ],
};

it('zeigt Name, Modulcode und read-only Competency-Chip', () => {
  render(
    <CompetencyFrameworkCard
      framework={framework}
      canManage
      onEdit={jest.fn()}
      onArchiveToggle={jest.fn()}
    />
  );
  expect(screen.getByText(/Modul B/)).toBeInTheDocument();
  expect(screen.getByText(/B3/)).toBeInTheDocument();
});

it('ruft onEdit beim Klick auf Bearbeiten, wenn canManage', () => {
  const onEdit = jest.fn();
  render(
    <CompetencyFrameworkCard
      framework={framework}
      canManage
      onEdit={onEdit}
      onArchiveToggle={jest.fn()}
    />
  );
  fireEvent.click(screen.getByRole('button', { name: /Bearbeiten/i }));
  expect(onEdit).toHaveBeenCalledWith(framework);
});

it('blendet Aktionen aus, wenn nicht canManage', () => {
  render(
    <CompetencyFrameworkCard
      framework={framework}
      canManage={false}
      onEdit={jest.fn()}
      onArchiveToggle={jest.fn()}
    />
  );
  expect(screen.queryByRole('button', { name: /Bearbeiten/i })).not.toBeInTheDocument();
});
