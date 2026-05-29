import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import DocumentLibraryToolbar from '../DocumentLibraryToolbar';

const base = {
  params: {} as any,
  view: 'cards' as const,
  availableTags: [] as any[],
  onChange: jest.fn(),
  onReset: jest.fn(),
};
const renderIt = (overrides: any = {}) =>
  render(
    <ThemeProvider theme={createTheme()}>
      <DocumentLibraryToolbar {...base} {...overrides} />
    </ThemeProvider>,
  );

afterEach(() => jest.clearAllMocks());

test('debounced search calls onChange("q") after typing', async () => {
  const onChange = jest.fn();
  renderIt({ onChange });
  const input = screen.getByPlaceholderText(/such/i);
  fireEvent.change(input, { target: { value: 'mathe' } });
  await waitFor(() => expect(onChange).toHaveBeenCalledWith('q', 'mathe'), { timeout: 1500 });
});

test('view toggle switches to list', () => {
  const onChange = jest.fn();
  renderIt({ onChange });
  fireEvent.click(screen.getByRole('button', { name: /liste|list/i }));
  expect(onChange).toHaveBeenCalledWith('view', 'list');
});

test('active visibility filter renders a chip whose delete clears it', () => {
  const onChange = jest.fn();
  renderIt({ onChange, params: { visibility: 'own' } });
  const cancel = screen.getByTestId('CancelIcon'); // single active chip → single delete icon
  fireEvent.click(cancel);
  expect(onChange).toHaveBeenCalledWith('visibility', undefined);
});

test('reset-all appears with >=2 active filters and calls onReset', () => {
  const onReset = jest.fn();
  renderIt({ onReset, params: { visibility: 'own', status: ['processed'] } });
  fireEvent.click(screen.getByText(/zur(ü|u)cksetzen|reset all/i));
  expect(onReset).toHaveBeenCalled();
});
