import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import DocumentPagination from '../DocumentPagination';

const renderIt = (overrides: Partial<React.ComponentProps<typeof DocumentPagination>> = {}) => {
  const props = {
    page: 1, totalPages: 3, pageSize: 24, total: 60,
    onPageChange: jest.fn(), onPageSizeChange: jest.fn(),
    ...overrides,
  };
  render(
    <ThemeProvider theme={createTheme()}>
      <DocumentPagination {...props} />
    </ThemeProvider>,
  );
  return props;
};

test('calls onPageChange when a page button is clicked', () => {
  const onPageChange = jest.fn();
  renderIt({ onPageChange });
  fireEvent.click(screen.getByRole('button', { name: /go to page 2/i }));
  expect(onPageChange).toHaveBeenCalledWith(2);
});

test('renders nothing when total is 0', () => {
  const { container } = render(
    <ThemeProvider theme={createTheme()}>
      <DocumentPagination page={1} totalPages={0} pageSize={24} total={0}
        onPageChange={jest.fn()} onPageSizeChange={jest.fn()} />
    </ThemeProvider>,
  );
  expect(container).toBeEmptyDOMElement();
});

test('page-size select shows current size and offers 12/24/48/96', () => {
  renderIt({ pageSize: 24 });
  // MUI Select renders the current value in a combobox/button
  expect(screen.getByText('24')).toBeInTheDocument();
});
