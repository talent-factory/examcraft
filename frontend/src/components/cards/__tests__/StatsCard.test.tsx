/**
 * StatsCard Component Tests
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { StatsCard } from '../StatsCard';

describe('StatsCard Component', () => {
  it('renders label and value', () => {
    render(
      <StatsCard
        icon="📊"
        label="Generated Questions"
        value="42"
      />
    );

    expect(screen.getByText('Generated Questions')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('renders icon', () => {
    render(
      <StatsCard
        icon="📊"
        label="Generated Questions"
        value="42"
      />
    );

    expect(screen.getByText('📊')).toBeInTheDocument();
  });

  it('renders trend with up direction', () => {
    render(
      <StatsCard
        icon="📊"
        label="Generated Questions"
        value="42"
        trend={{ value: 15, direction: 'up' }}
      />
    );

    expect(screen.getByText('↑ 15%')).toBeInTheDocument();
  });

  it('renders trend with down direction', () => {
    render(
      <StatsCard
        icon="📊"
        label="Generated Questions"
        value="42"
        trend={{ value: 10, direction: 'down' }}
      />
    );

    expect(screen.getByText('↓ 10%')).toBeInTheDocument();
  });

  it('applies correct color class', () => {
    const { container } = render(
      <StatsCard
        icon="📊"
        label="Generated Questions"
        value="42"
        color="success"
      />
    );

    const card = container.querySelector('.card');
    expect(card).toHaveClass('bg-green-50');
  });

  it('renders numeric value', () => {
    render(
      <StatsCard
        icon="📊"
        label="Generated Questions"
        value={42}
      />
    );

    expect(screen.getByText('42')).toBeInTheDocument();
  });
});
