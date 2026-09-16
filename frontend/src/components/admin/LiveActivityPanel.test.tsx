import React from 'react';
import { render, screen, act, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import LiveActivityPanel from './LiveActivityPanel';
import * as liveActivityService from '../../services/liveActivityService';
import { LiveActivitySnapshot } from '../../types/liveActivity';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options ? `${key} ${JSON.stringify(options)}` : key,
  }),
}));

const baseSnapshot: LiveActivitySnapshot = {
  generated_at: '2026-09-16T08:00:00+00:00',
  buckets: {
    documents_upload: { value: 0, exact: true },
    questions_generate_rag: { value: 2, exact: true },
    questions_review: { value: 5, exact: false },
    exam_compose: { value: 1, exact: true },
    exam_results_import: { value: 0, exact: true },
    prompt_template_edit: { value: 0, exact: true },
    prompt_wizard_chat: { value: 0, exact: true },
    document_chat_session: { value: 3, exact: true },
    admin_reference_data_edit: { value: 0, exact: true },
  },
};

describe('LiveActivityPanel', () => {
  afterEach(() => {
    jest.restoreAllMocks();
    jest.useRealTimers();
  });

  it('renders all 9 bucket tiles in the fixed BUCKET_ORDER', async () => {
    jest.spyOn(liveActivityService, 'fetchLiveActivity').mockResolvedValue(baseSnapshot);

    render(<LiveActivityPanel />);

    const expectedOrder = [
      'documents_upload',
      'questions_generate_rag',
      'questions_review',
      'exam_compose',
      'exam_results_import',
      'prompt_template_edit',
      'prompt_wizard_chat',
      'document_chat_session',
      'admin_reference_data_edit',
    ];
    for (const bucketId of expectedOrder) {
      expect(await screen.findByTestId(`live-activity-card-${bucketId}`)).toBeInTheDocument();
    }

    const renderedIds = screen
      .getAllByTestId(/^live-activity-card-(?!value-)/)
      .map((el) => el.getAttribute('data-testid'));
    expect(renderedIds).toEqual(expectedOrder.map((id) => `live-activity-card-${id}`));
  });

  it('shows a page-level error and a retry button when the fetch fails', async () => {
    jest.spyOn(liveActivityService, 'fetchLiveActivity').mockRejectedValue(new Error('network down'));

    render(<LiveActivityPanel />);

    expect(await screen.findByText('pages.admin.liveActivity.loadError')).toBeInTheDocument();
    expect(screen.getByText('pages.admin.liveActivity.retry')).toBeInTheDocument();
    expect(screen.queryByTestId('live-activity-card-documents_upload')).not.toBeInTheDocument();
  });

  it('recovers and shows the tiles after clicking retry once the fetch succeeds', async () => {
    const fetchSpy = jest
      .spyOn(liveActivityService, 'fetchLiveActivity')
      .mockRejectedValueOnce(new Error('network down'))
      .mockResolvedValueOnce(baseSnapshot);

    render(<LiveActivityPanel />);
    expect(await screen.findByText('pages.admin.liveActivity.loadError')).toBeInTheDocument();

    fireEvent.click(screen.getByText('pages.admin.liveActivity.retry'));

    expect(await screen.findByTestId('live-activity-card-documents_upload')).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledTimes(2);
    expect(screen.queryByTestId('live-activity-error')).not.toBeInTheDocument();
  });

  it('polls the endpoint again after 10 seconds', async () => {
    jest.useFakeTimers();
    const fetchSpy = jest.spyOn(liveActivityService, 'fetchLiveActivity').mockResolvedValue(baseSnapshot);

    render(<LiveActivityPanel />);
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
    const fetchSpy = jest.spyOn(liveActivityService, 'fetchLiveActivity').mockResolvedValue(baseSnapshot);

    const { unmount } = render(<LiveActivityPanel />);
    await act(async () => {
      await Promise.resolve();
    });
    unmount();

    await act(async () => {
      jest.advanceTimersByTime(30000);
    });
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it('ignores a stale manual retry that resolves after a newer scheduled poll already applied', async () => {
    // Ported from SystemHealthPanel.test.tsx (PR #286 review, I4): this
    // panel copies SystemHealthPanel's requestIdRef generation-counter
    // guard verbatim, but had no test proving it actually works here.
    jest.useFakeTimers();

    let resolveStaleRetry: (value: LiveActivitySnapshot) => void;
    const staleRetryPromise = new Promise<LiveActivitySnapshot>((resolve) => {
      resolveStaleRetry = resolve;
    });
    const newerSnapshot: LiveActivitySnapshot = {
      ...baseSnapshot,
      buckets: {
        ...baseSnapshot.buckets,
        documents_upload: { value: 2, exact: true },
      },
    };

    const fetchSpy = jest
      .spyOn(liveActivityService, 'fetchLiveActivity')
      .mockRejectedValueOnce(new Error('network down')) // initial poll: fails
      .mockImplementationOnce(() => staleRetryPromise) // manual retry: stays pending
      .mockResolvedValueOnce(newerSnapshot); // next scheduled poll: resolves first

    render(<LiveActivityPanel />);
    expect(await screen.findByText('pages.admin.liveActivity.loadError')).toBeInTheDocument();

    fireEvent.click(screen.getByText('pages.admin.liveActivity.retry'));
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
    expect(await screen.findByTestId('live-activity-card-value-documents_upload')).toHaveTextContent('2');

    // The stale manual retry finally resolves with older data — it must be
    // discarded, not overwrite the newer snapshot already on screen.
    await act(async () => {
      resolveStaleRetry(baseSnapshot);
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(screen.getByTestId('live-activity-card-value-documents_upload')).toHaveTextContent('2');
    expect(fetchSpy).toHaveBeenCalledTimes(3);
  });

  it('keeps showing the last snapshot with a stale warning when a later poll fails', async () => {
    jest.useFakeTimers();
    const fetchSpy = jest
      .spyOn(liveActivityService, 'fetchLiveActivity')
      .mockResolvedValueOnce(baseSnapshot)
      .mockRejectedValueOnce(new Error('network down'));

    render(<LiveActivityPanel />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(await screen.findByTestId('live-activity-card-documents_upload')).toBeInTheDocument();

    await act(async () => {
      jest.advanceTimersByTime(10000);
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(fetchSpy).toHaveBeenCalledTimes(2);
    expect(screen.getByTestId('live-activity-stale-warning')).toBeInTheDocument();
    // Stale-but-present data stays visible instead of blanking the screen.
    expect(screen.getByTestId('live-activity-card-documents_upload')).toBeInTheDocument();
  });

  it('renders a bucket missing from the snapshot as unavailable, not as zero — even alongside a genuine zero in the same response', async () => {
    const partialSnapshot: LiveActivitySnapshot = {
      generated_at: baseSnapshot.generated_at,
      buckets: {
        // A genuine zero (present, exact) and a missing bucket (fetch
        // failed) in the same snapshot — proves "absent ≠ zero" holds even
        // when both cases occur together, not just in isolation.
        documents_upload: { value: 0, exact: true },
        // All other buckets intentionally omitted (simulated fetch failure).
      },
    };
    jest.spyOn(liveActivityService, 'fetchLiveActivity').mockResolvedValue(partialSnapshot);

    render(<LiveActivityPanel />);

    expect(await screen.findByTestId('live-activity-card-value-documents_upload')).toHaveTextContent('0');
    expect(screen.getByTestId('live-activity-card-unavailable-questions_review')).toBeInTheDocument();
  });
});
