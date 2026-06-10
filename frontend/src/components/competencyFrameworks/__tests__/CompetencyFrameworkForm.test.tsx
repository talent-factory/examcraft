import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import CompetencyFrameworkForm from '../CompetencyFrameworkForm';

it('ruft onSubmit mit name + rendered_text bei Create', () => {
  const onSubmit = jest.fn();
  render(<CompetencyFrameworkForm mode="create" onSubmit={onSubmit} onCancel={jest.fn()} />);

  fireEvent.change(screen.getByLabelText(/Name/i), { target: { value: 'Modul C' } });
  fireEvent.change(screen.getByLabelText(/Kompetenzen-Volltext/i), {
    target: { value: 'C1 ... C2 ...' },
  });
  fireEvent.click(screen.getByRole('button', { name: /Speichern/i }));

  expect(onSubmit).toHaveBeenCalledWith(
    expect.objectContaining({ name: 'Modul C', rendered_text: 'C1 ... C2 ...' })
  );
});

it('deaktiviert Speichern, solange name oder rendered_text leer sind', () => {
  render(<CompetencyFrameworkForm mode="create" onSubmit={jest.fn()} onCancel={jest.fn()} />);
  expect(screen.getByRole('button', { name: /Speichern/i })).toBeDisabled();
});

it('befüllt Felder bei mode=edit aus initial', () => {
  render(
    <CompetencyFrameworkForm
      mode="edit"
      initial={{ name: 'Modul B', module_code: 'B', description: '', rendered_text: 'VB', language: 'de', visibility: 'institution' }}
      onSubmit={jest.fn()}
      onCancel={jest.fn()}
    />
  );
  expect(screen.getByLabelText(/Name/i)).toHaveValue('Modul B');
  expect(screen.getByLabelText(/Kompetenzen-Volltext/i)).toHaveValue('VB');
});
