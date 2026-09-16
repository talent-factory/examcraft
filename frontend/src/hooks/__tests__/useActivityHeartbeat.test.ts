import { renderHook, waitFor } from '@testing-library/react';
import { useActivityHeartbeat, __resetActivityHeartbeatDedupForTests } from '../useActivityHeartbeat';
import * as liveActivityService from '../../services/liveActivityService';
import * as deploymentMode from '../../utils/deploymentMode';
import { ActivityBucketId } from '../../types/liveActivity';

describe('useActivityHeartbeat', () => {
  beforeEach(() => {
    __resetActivityHeartbeatDedupForTests();
    jest.spyOn(deploymentMode, 'isFullDeployment').mockReturnValue(true);
  });

  afterEach(() => {
    jest.restoreAllMocks();
    jest.useRealTimers();
  });

  it('sends an immediate heartbeat for the given bucket on mount', () => {
    const heartbeatSpy = jest
      .spyOn(liveActivityService, 'sendActivityHeartbeat')
      .mockResolvedValue(undefined);

    renderHook(() => useActivityHeartbeat('questions_review'));

    expect(heartbeatSpy).toHaveBeenCalledTimes(1);
    expect(heartbeatSpy).toHaveBeenCalledWith('questions_review');
  });

  it('sends no heartbeat when bucketId is null', () => {
    const heartbeatSpy = jest
      .spyOn(liveActivityService, 'sendActivityHeartbeat')
      .mockResolvedValue(undefined);

    renderHook(() => useActivityHeartbeat(null));

    expect(heartbeatSpy).not.toHaveBeenCalled();
  });

  it('sends no heartbeat in Core deployment, even with a bucketId', () => {
    // PR #286 review: most call sites live in core/, the tier mirrored to
    // the public OSS repo — without this gate, Core deployments would loop
    // a failing POST to a route that only exists in Full forever.
    jest.spyOn(deploymentMode, 'isFullDeployment').mockReturnValue(false);
    const heartbeatSpy = jest
      .spyOn(liveActivityService, 'sendActivityHeartbeat')
      .mockResolvedValue(undefined);

    renderHook(() => useActivityHeartbeat('questions_review'));

    expect(heartbeatSpy).not.toHaveBeenCalled();
  });

  it('repeats the heartbeat every 15 seconds while mounted', () => {
    jest.useFakeTimers();
    const heartbeatSpy = jest
      .spyOn(liveActivityService, 'sendActivityHeartbeat')
      .mockResolvedValue(undefined);

    renderHook(() => useActivityHeartbeat('exam_compose'));
    expect(heartbeatSpy).toHaveBeenCalledTimes(1);

    jest.advanceTimersByTime(15000);
    expect(heartbeatSpy).toHaveBeenCalledTimes(2);

    jest.advanceTimersByTime(15000);
    expect(heartbeatSpy).toHaveBeenCalledTimes(3);
  });

  it('stops heartbeats on unmount', () => {
    jest.useFakeTimers();
    const heartbeatSpy = jest
      .spyOn(liveActivityService, 'sendActivityHeartbeat')
      .mockResolvedValue(undefined);

    const { unmount } = renderHook(() => useActivityHeartbeat('document_chat_session'));
    expect(heartbeatSpy).toHaveBeenCalledTimes(1);

    unmount();
    jest.advanceTimersByTime(60000);

    expect(heartbeatSpy).toHaveBeenCalledTimes(1);
  });

  it('restarts the interval and stops the old bucket when bucketId changes', () => {
    jest.useFakeTimers();
    const heartbeatSpy = jest
      .spyOn(liveActivityService, 'sendActivityHeartbeat')
      .mockResolvedValue(undefined);

    const { rerender } = renderHook(({ bucketId }) => useActivityHeartbeat(bucketId), {
      initialProps: { bucketId: 'prompt_template_edit' as ActivityBucketId | null },
    });
    expect(heartbeatSpy).toHaveBeenLastCalledWith('prompt_template_edit');

    rerender({ bucketId: 'prompt_wizard_chat' });
    expect(heartbeatSpy).toHaveBeenLastCalledWith('prompt_wizard_chat');

    heartbeatSpy.mockClear();
    jest.advanceTimersByTime(15000);
    // Only the new bucket's interval should still be ticking.
    expect(heartbeatSpy).toHaveBeenCalledTimes(1);
    expect(heartbeatSpy).toHaveBeenCalledWith('prompt_wizard_chat');
  });

  it('pauses (stops the interval) without unmounting when bucketId transitions to null', () => {
    // The whole point of accepting `null` (see the hook's own doc comment)
    // is exactly this transition — e.g. ImportDialog.tsx's `open ? id :
    // null`, ExamComposer.tsx's `selectedExamId ? id : null`, or
    // PromptLibraryWithUpload.tsx leaving 'editor'/'wizard' for another
    // viewMode — while the *component* itself stays mounted.
    jest.useFakeTimers();
    const heartbeatSpy = jest
      .spyOn(liveActivityService, 'sendActivityHeartbeat')
      .mockResolvedValue(undefined);

    const { rerender } = renderHook(({ bucketId }) => useActivityHeartbeat(bucketId), {
      initialProps: { bucketId: 'exam_results_import' as ActivityBucketId | null },
    });
    expect(heartbeatSpy).toHaveBeenCalledTimes(1);

    rerender({ bucketId: null });
    heartbeatSpy.mockClear();

    jest.advanceTimersByTime(60000);

    expect(heartbeatSpy).not.toHaveBeenCalled();
  });

  it('skips a mount-time beat for a bucket sent less than 15s ago by a different mounted instance', () => {
    // Module-level dedup (PR #286 review): fast remounts on the same bucket
    // (e.g. ReviewQueue -> QuestionReviewDetail -> back) would otherwise
    // each fire an immediate beat, which can exceed the backend's
    // 10-requests-per-minute limit purely from normal navigation.
    jest.useFakeTimers();
    const heartbeatSpy = jest
      .spyOn(liveActivityService, 'sendActivityHeartbeat')
      .mockResolvedValue(undefined);

    const { unmount: unmountFirst } = renderHook(() => useActivityHeartbeat('questions_review'));
    expect(heartbeatSpy).toHaveBeenCalledTimes(1);
    unmountFirst();

    // A second, independent mount of the same bucket within the 15s window.
    renderHook(() => useActivityHeartbeat('questions_review'));
    expect(heartbeatSpy).toHaveBeenCalledTimes(1);

    // Once the window has fully elapsed, a new mount sends again.
    jest.advanceTimersByTime(15000);
    renderHook(() => useActivityHeartbeat('questions_review'));
    expect(heartbeatSpy).toHaveBeenCalledTimes(2);
  });

  it('does not dedup across different buckets', () => {
    jest.useFakeTimers();
    const heartbeatSpy = jest
      .spyOn(liveActivityService, 'sendActivityHeartbeat')
      .mockResolvedValue(undefined);

    renderHook(() => useActivityHeartbeat('questions_review'));
    renderHook(() => useActivityHeartbeat('exam_compose'));

    expect(heartbeatSpy).toHaveBeenCalledTimes(2);
    expect(heartbeatSpy).toHaveBeenCalledWith('questions_review');
    expect(heartbeatSpy).toHaveBeenCalledWith('exam_compose');
  });

  it('logs and swallows a failed heartbeat instead of throwing', async () => {
    const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    jest.spyOn(liveActivityService, 'sendActivityHeartbeat').mockRejectedValue(new Error('network down'));

    renderHook(() => useActivityHeartbeat('admin_reference_data_edit'));

    await waitFor(() =>
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('admin_reference_data_edit'),
        expect.any(Error),
      ),
    );
  });

  it('still logs a heartbeat failure that resolves after the component has already unmounted', async () => {
    // Regression guard: an earlier version gated the console.warn on a
    // `cancelled` flag set in the effect's cleanup, which silently dropped
    // this exact case — contradicting the hook's own "logged and swallowed"
    // contract (console.warn has no post-unmount hazard, unlike setState).
    const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    let rejectHeartbeat: (err: Error) => void;
    const pending = new Promise<void>((_, reject) => {
      rejectHeartbeat = reject;
    });
    jest.spyOn(liveActivityService, 'sendActivityHeartbeat').mockReturnValue(pending);

    const { unmount } = renderHook(() => useActivityHeartbeat('document_chat_session'));
    unmount();
    rejectHeartbeat!(new Error('network down'));

    await waitFor(() =>
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('document_chat_session'),
        expect.any(Error),
      ),
    );
  });
});
