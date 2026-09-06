import React from 'react';
import { render, screen, act, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import SystemHealthPanel from './SystemHealthPanel';
import * as opsHealthService from '../../services/opsHealthService';
import { OpsHealthSnapshot } from '../../types/opsHealth';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options ? `${key} ${JSON.stringify(options)}` : key,
  }),
}));

const baseSnapshot: OpsHealthSnapshot = {
  generated_at: '2026-09-05T08:00:00+00:00',
  overall_status: 'green',
  components: {
    frontend: {
      status: 'green',
      metric_label: 'reachable_machines',
      metric_value: '1/1',
      timestamp: '2026-09-05T08:00:00+00:00',
      detail: null,
      deep_link: 'https://talent-factory.sentry.io/projects/talent-factory/examcraft-frontend/',
      sentry: { configured: false },
    },
    backend: {
      status: 'green',
      metric_label: 'reachable_machines',
      metric_value: '1/1',
      timestamp: '2026-09-05T08:00:00+00:00',
      detail: null,
      deep_link: null,
      sentry: { configured: false },
    },
    db: {
      status: 'yellow',
      metric_label: 'latency_ms',
      metric_value: 320,
      timestamp: '2026-09-05T08:00:00+00:00',
      detail: null,
      deep_link: null,
    },
    rabbitmq: {
      status: 'green',
      metric_label: 'queued_messages',
      metric_value: 0,
      timestamp: '2026-09-05T08:00:00+00:00',
      detail: null,
      deep_link: 'https://examcraft-rabbitmq.fly.dev',
    },
    celery: {
      status: 'red',
      metric_label: 'online_workers',
      metric_value: 0,
      timestamp: '2026-09-05T08:00:00+00:00',
      detail: 'no workers registered',
      deep_link: 'https://examcraft-flower.fly.dev',
    },
  },
};

describe('SystemHealthPanel', () => {
  afterEach(() => {
    jest.restoreAllMocks();
    jest.useRealTimers();
  });

  it('renders all 5 component cards with their status and metric', async () => {
    jest.spyOn(opsHealthService, 'fetchOpsHealth').mockResolvedValue(baseSnapshot);

    render(<SystemHealthPanel />);

    expect(await screen.findByTestId('system-health-card-frontend')).toBeInTheDocument();
    expect(screen.getByTestId('system-health-card-backend')).toBeInTheDocument();
    expect(screen.getByTestId('system-health-card-db')).toBeInTheDocument();
    expect(screen.getByTestId('system-health-card-rabbitmq')).toBeInTheDocument();
    expect(screen.getByTestId('system-health-card-celery')).toBeInTheDocument();

    const celeryCard = screen.getByTestId('system-health-card-celery');
    expect(celeryCard).toHaveTextContent('pages.admin.systemHealth.status.red');
    expect(celeryCard).toHaveTextContent('pages.admin.systemHealth.metricLabel.online_workers');
  });

  it('renders each card as a link to its deep_link, and no link when deep_link is null', async () => {
    jest.spyOn(opsHealthService, 'fetchOpsHealth').mockResolvedValue(baseSnapshot);

    render(<SystemHealthPanel />);
    expect(await screen.findByTestId('system-health-card-db')).toBeInTheDocument();

    const rabbitmqLink = screen.getByTestId('system-health-card-link-rabbitmq');
    expect(rabbitmqLink).toHaveAttribute('href', 'https://examcraft-rabbitmq.fly.dev');
    expect(screen.queryByTestId('system-health-card-link-db')).not.toBeInTheDocument();
  });

  it('shows a page-level error and a retry button when the fetch fails', async () => {
    jest.spyOn(opsHealthService, 'fetchOpsHealth').mockRejectedValue(new Error('network down'));

    render(<SystemHealthPanel />);

    expect(await screen.findByText('pages.admin.systemHealth.loadError')).toBeInTheDocument();
    expect(screen.getByText('pages.admin.systemHealth.retry')).toBeInTheDocument();
    expect(screen.queryByTestId('system-health-card-frontend')).not.toBeInTheDocument();
  });

  it('recovers and shows the cards after clicking retry once the fetch succeeds', async () => {
    const fetchSpy = jest
      .spyOn(opsHealthService, 'fetchOpsHealth')
      .mockRejectedValueOnce(new Error('network down'))
      .mockResolvedValueOnce(baseSnapshot);

    render(<SystemHealthPanel />);
    expect(await screen.findByText('pages.admin.systemHealth.loadError')).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText('pages.admin.systemHealth.retry'));

    expect(await screen.findByTestId('system-health-card-frontend')).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledTimes(2);
    expect(screen.queryByTestId('system-health-error')).not.toBeInTheDocument();
  });

  it('ignores a stale manual retry that resolves after a newer scheduled poll already applied', async () => {
    // Retry calls `load` directly, outside the tick chain's serialization —
    // this reproduces a retry click whose response is still in flight when
    // the next scheduled 10s poll fires and resolves first. The older,
    // slower response must not be allowed to clobber the newer one when it
    // finally settles.
    jest.useFakeTimers();

    let resolveStaleRetry: (value: OpsHealthSnapshot) => void;
    const staleRetryPromise = new Promise<OpsHealthSnapshot>((resolve) => {
      resolveStaleRetry = resolve;
    });
    const newerSnapshot: OpsHealthSnapshot = {
      ...baseSnapshot,
      components: {
        ...baseSnapshot.components,
        frontend: { ...baseSnapshot.components.frontend, metric_value: '2/2' },
      },
    };

    const fetchSpy = jest
      .spyOn(opsHealthService, 'fetchOpsHealth')
      .mockRejectedValueOnce(new Error('network down')) // initial poll: fails
      .mockImplementationOnce(() => staleRetryPromise) // manual retry: stays pending
      .mockResolvedValueOnce(newerSnapshot); // next scheduled poll: resolves first

    render(<SystemHealthPanel />);
    expect(await screen.findByText('pages.admin.systemHealth.loadError')).toBeInTheDocument();

    fireEvent.click(screen.getByText('pages.admin.systemHealth.retry'));
    await act(async () => {
      await Promise.resolve();
    });

    // The automatic poll scheduled after the initial failure fires now,
    // resolving before the still-pending manual retry does.
    await act(async () => {
      jest.advanceTimersByTime(10000);
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(await screen.findByTestId('system-health-card-frontend')).toHaveTextContent('2/2');

    // The stale manual retry finally resolves with older data — it must be
    // discarded, not overwrite the newer snapshot already on screen.
    await act(async () => {
      resolveStaleRetry(baseSnapshot);
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(screen.getByTestId('system-health-card-frontend')).toHaveTextContent('2/2');
    expect(fetchSpy).toHaveBeenCalledTimes(3);
  });

  it('keeps showing the last snapshot with a stale warning when a later poll fails', async () => {
    jest.useFakeTimers();
    const fetchSpy = jest
      .spyOn(opsHealthService, 'fetchOpsHealth')
      .mockResolvedValueOnce(baseSnapshot)
      .mockRejectedValueOnce(new Error('network down'));

    render(<SystemHealthPanel />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(await screen.findByTestId('system-health-card-frontend')).toBeInTheDocument();

    await act(async () => {
      jest.advanceTimersByTime(10000);
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(fetchSpy).toHaveBeenCalledTimes(2);
    expect(screen.getByTestId('system-health-stale-warning')).toBeInTheDocument();
    // Stale-but-present data stays visible instead of blanking the screen.
    expect(screen.getByTestId('system-health-card-frontend')).toBeInTheDocument();
  });

  it('polls the endpoint again after 10 seconds', async () => {
    jest.useFakeTimers();
    const fetchSpy = jest.spyOn(opsHealthService, 'fetchOpsHealth').mockResolvedValue(baseSnapshot);

    render(<SystemHealthPanel />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    await act(async () => {
      jest.advanceTimersByTime(10000);
      await Promise.resolve();
    });
    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });

  it('stops polling on unmount', async () => {
    jest.useFakeTimers();
    const fetchSpy = jest.spyOn(opsHealthService, 'fetchOpsHealth').mockResolvedValue(baseSnapshot);

    const { unmount } = render(<SystemHealthPanel />);
    await act(async () => {
      await Promise.resolve();
    });
    unmount();

    await act(async () => {
      jest.advanceTimersByTime(30000);
    });
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });
});
