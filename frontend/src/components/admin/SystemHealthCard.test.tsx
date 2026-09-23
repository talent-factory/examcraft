import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
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
  cli_hint: null,
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

  // TF-918: get_backend_health()/get_frontend_health() both populate
  // specula.error_count_5m (replaces the retired Sentry-API integration,
  // TF-788) — both cards, and only once configured with an actual count,
  // should show it.
  describe('Specula error count (backend + frontend)', () => {
    it.each(['backend', 'frontend'] as const)(
      'renders the Specula error count for the %s card when configured',
      (componentKey) => {
        render(
          <SystemHealthCard
            componentKey={componentKey}
            health={{ ...baseHealth, specula: { configured: true, error_count_5m: 3 } }}
          />
        );

        expect(screen.getByText('pages.admin.systemHealth.speculaErrorCount')).toBeInTheDocument();
      }
    );

    it('does not render the caption when Specula is not configured', () => {
      render(
        <SystemHealthCard
          componentKey="backend"
          health={{ ...baseHealth, specula: { configured: false } }}
        />
      );

      expect(
        screen.queryByText('pages.admin.systemHealth.speculaErrorCount')
      ).not.toBeInTheDocument();
    });

    it('does not render the caption when error_count_5m is null (ClickHouse query failed)', () => {
      render(
        <SystemHealthCard
          componentKey="backend"
          health={{ ...baseHealth, specula: { configured: true, error_count_5m: null } }}
        />
      );

      expect(
        screen.queryByText('pages.admin.systemHealth.speculaErrorCount')
      ).not.toBeInTheDocument();
    });

    it('does not render the caption for components without a specula card even if specula is present', () => {
      render(
        <SystemHealthCard
          componentKey="rabbitmq"
          health={{ ...baseHealth, specula: { configured: true, error_count_5m: 3 } }}
        />
      );

      expect(
        screen.queryByText('pages.admin.systemHealth.speculaErrorCount')
      ).not.toBeInTheDocument();
    });
  });

  // TF-817: rabbitmq has no working public deep-link (no public IP on
  // examcraft-rabbitmq), so the backend sends `cli_hint` instead — the card
  // must render a copyable fly-proxy command, not a dead/absent link.
  describe('CLI hint fallback (no working deep_link)', () => {
    const cliHintHealth: OpsComponentHealth = {
      ...baseHealth,
      deep_link: null,
      cli_hint: 'fly proxy 15672 -a examcraft-rabbitmq',
    };

    it('renders the cli_hint command when deep_link is null but cli_hint is set', () => {
      render(<SystemHealthCard componentKey="rabbitmq" health={cliHintHealth} />);

      expect(screen.getByTestId('system-health-card-cli-hint-rabbitmq')).toHaveTextContent(
        'fly proxy 15672 -a examcraft-rabbitmq'
      );
      expect(screen.queryByTestId('system-health-card-link-rabbitmq')).not.toBeInTheDocument();
    });

    it('does not render the cli_hint when a deep_link is present', () => {
      render(
        <SystemHealthCard
          componentKey="celery"
          health={{ ...cliHintHealth, deep_link: 'https://examcraft-flower.fly.dev' }}
        />
      );

      expect(screen.queryByTestId('system-health-card-cli-hint-celery')).not.toBeInTheDocument();
    });

    it('copies the command to the clipboard when the copy button is clicked', async () => {
      const writeText = jest.fn().mockResolvedValue(undefined);
      Object.assign(navigator, { clipboard: { writeText } });

      render(<SystemHealthCard componentKey="rabbitmq" health={cliHintHealth} />);
      fireEvent.click(screen.getByTestId('system-health-card-copy-rabbitmq'));

      expect(writeText).toHaveBeenCalledWith('fly proxy 15672 -a examcraft-rabbitmq');
      expect(await screen.findByText('pages.admin.systemHealth.copied')).toBeInTheDocument();
    });

    it('shows a failure message instead of "copied" when the clipboard write is rejected', async () => {
      const writeText = jest.fn().mockRejectedValue(new Error('denied'));
      Object.assign(navigator, { clipboard: { writeText } });
      const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});

      render(<SystemHealthCard componentKey="rabbitmq" health={cliHintHealth} />);
      fireEvent.click(screen.getByTestId('system-health-card-copy-rabbitmq'));

      expect(await screen.findByText('pages.admin.systemHealth.copyFailed')).toBeInTheDocument();
      expect(screen.queryByText('pages.admin.systemHealth.copied')).not.toBeInTheDocument();
      expect(warnSpy).toHaveBeenCalled();

      warnSpy.mockRestore();
    });
  });
});
