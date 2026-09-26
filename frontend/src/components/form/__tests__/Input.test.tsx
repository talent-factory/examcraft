/**
 * Input Component Tests
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { Input } from '../Input';

describe('Input Component', () => {
  it('renders input field', () => {
    render(
      <Input placeholder="Test input" />
    );

    const input = screen.getByRole('textbox');
    expect(input).toBeInTheDocument();
  });

  it('renders label when provided', () => {
    render(
      <Input label="Email" />
    );

    expect(screen.getByText('Email')).toBeInTheDocument();
  });

  it('renders required asterisk', () => {
    render(
      <Input label="Email" required />
    );

    expect(screen.getByText('*')).toBeInTheDocument();
  });

  it('renders error message', () => {
    render(
      <Input label="Email" error="Email is required" />
    );

    expect(screen.getByText('Email is required')).toBeInTheDocument();
  });

  it('renders helper text', () => {
    render(
      <Input label="Email" helperText="Enter a valid email" />
    );

    expect(screen.getByText('Enter a valid email')).toBeInTheDocument();
  });

  it('does not render helper text when error is present', () => {
    render(
      <Input
        label="Email"
        error="Email is required"
        helperText="Enter a valid email"
      />
    );

    expect(screen.queryByText('Enter a valid email')).not.toBeInTheDocument();
  });

  it('applies disabled state', () => {
    render(
      <Input disabled />
    );

    const input = screen.getByRole('textbox');
    expect(input).toBeDisabled();
  });

  it('applies fullWidth class', () => {
    render(
      <Input fullWidth />
    );

    // The input sits directly inside the wrapper div that carries the width class.
    const wrapper = screen.getByRole('textbox').closest('div');
    expect(wrapper).toHaveClass('w-full');
  });
});
