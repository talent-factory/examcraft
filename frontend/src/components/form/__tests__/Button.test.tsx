/**
 * Button Component Tests
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { Button } from '../Button';

describe('Button Component', () => {
  it('renders button with text', () => {
    render(
      <Button>Click me</Button>
    );

    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('renders button with primary variant', () => {
    const { container } = render(
      <Button variant="primary">Primary</Button>
    );

    const button = container.querySelector('button');
    expect(button).toHaveClass('btn-primary');
  });

  it('renders button with secondary variant', () => {
    const { container } = render(
      <Button variant="secondary">Secondary</Button>
    );

    const button = container.querySelector('button');
    expect(button).toHaveClass('btn-secondary');
  });

  it('renders button with ghost variant', () => {
    const { container } = render(
      <Button variant="ghost">Ghost</Button>
    );

    const button = container.querySelector('button');
    expect(button).toHaveClass('btn-ghost');
  });

  it('renders button with danger variant', () => {
    const { container } = render(
      <Button variant="danger">Delete</Button>
    );

    const button = container.querySelector('button');
    expect(button).toHaveClass('bg-red-600');
  });

  it('renders button with small size', () => {
    const { container } = render(
      <Button size="sm">Small</Button>
    );

    const button = container.querySelector('button');
    expect(button).toHaveClass('btn-sm');
  });

  it('renders button with large size', () => {
    const { container } = render(
      <Button size="lg">Large</Button>
    );

    const button = container.querySelector('button');
    expect(button).toHaveClass('btn-lg');
  });

  it('applies fullWidth class', () => {
    const { container } = render(
      <Button fullWidth>Full Width</Button>
    );

    const button = container.querySelector('button');
    expect(button).toHaveClass('w-full');
  });

  it('disables button when disabled prop is true', () => {
    const { container } = render(
      <Button disabled>Disabled</Button>
    );

    const button = container.querySelector('button');
    expect(button).toBeDisabled();
  });

  it('disables button when loading prop is true', () => {
    const { container } = render(
      <Button loading>Loading</Button>
    );

    const button = container.querySelector('button');
    expect(button).toBeDisabled();
  });

  it('renders loading spinner when loading', () => {
    render(
      <Button loading>Loading</Button>
    );

    expect(screen.getByText('Loading')).toBeInTheDocument();
  });
});
