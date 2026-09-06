import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import SystemHealthCard from './SystemHealthCard';
import { OpsComponentHealth } from '../../types/opsHealth';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const baseHealth: OpsComponentHealth = {
  status: 'green',
  metric_label: 'reachable_machines',
  metric_value: '1/1',
  timestamp: '2026-09-05T08:00:00+00:00',
  detail: null,
  deep_link: null,
};

describe('SystemHealthCard', () => {
  // Regression test for the STATUS_COLOR mapping (green/yellow/red -> MUI
  // Chip success/warning/error): a swapped mapping would still pass
  // text-content-only assertions, since the label text comes from the
  // i18n key, not from the color. Asserting the actual Chip color class is
  // the only way to catch that on an ops dashboard where an inverted
  // red/green is worse than no dashboard at all.
  it.each([
    ['green', 'MuiChip-colorSuccess'],
    ['yellow', 'MuiChip-colorWarning'],
    ['red', 'MuiChip-colorError'],
  ] as const)('renders status "%s" with the %s chip color', (status, expectedClass) => {
    render(<SystemHealthCard componentKey="frontend" health={{ ...baseHealth, status }} />);

    expect(screen.getByTestId('system-health-card-status-frontend')).toHaveClass(expectedClass);
  });

  it('renders a placeholder instead of an empty value when metric_value is null', () => {
    render(
      <SystemHealthCard
        componentKey="rabbitmq"
        health={{ ...baseHealth, status: 'red', metric_value: null, detail: 'connection refused' }}
      />
    );

    expect(screen.getByText('—')).toBeInTheDocument();
  });
});
