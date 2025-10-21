/**
 * Select Component Tests
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { Select } from '../Select';

const options = [
  { value: 'option1', label: 'Option 1' },
  { value: 'option2', label: 'Option 2' },
  { value: 'option3', label: 'Option 3' },
];

describe('Select Component', () => {
  it('renders select field', () => {
    const { container } = render(
      <Select options={options} />
    );

    const select = container.querySelector('select');
    expect(select).toBeInTheDocument();
  });

  it('renders label when provided', () => {
    render(
      <Select label="Choose option" options={options} />
    );

    expect(screen.getByText('Choose option')).toBeInTheDocument();
  });

  it('renders required asterisk', () => {
    render(
      <Select label="Choose option" options={options} required />
    );

    expect(screen.getByText('*')).toBeInTheDocument();
  });

  it('renders all options', () => {
    render(
      <Select options={options} />
    );

    expect(screen.getByText('Option 1')).toBeInTheDocument();
    expect(screen.getByText('Option 2')).toBeInTheDocument();
    expect(screen.getByText('Option 3')).toBeInTheDocument();
  });

  it('renders error message', () => {
    render(
      <Select options={options} error="Please select an option" />
    );

    expect(screen.getByText('Please select an option')).toBeInTheDocument();
  });

  it('renders helper text', () => {
    render(
      <Select options={options} helperText="Select one option" />
    );

    expect(screen.getByText('Select one option')).toBeInTheDocument();
  });

  it('does not render helper text when error is present', () => {
    render(
      <Select
        options={options}
        error="Please select an option"
        helperText="Select one option"
      />
    );

    expect(screen.queryByText('Select one option')).not.toBeInTheDocument();
  });

  it('applies disabled state', () => {
    const { container } = render(
      <Select options={options} disabled />
    );

    const select = container.querySelector('select');
    expect(select).toBeDisabled();
  });

  it('applies fullWidth class', () => {
    const { container } = render(
      <Select options={options} fullWidth />
    );

    const wrapper = container.querySelector('div');
    expect(wrapper).toHaveClass('w-full');
  });
});

