import MoodleFeedbackPushService from './moodleFeedbackPushService';
import { ApiError } from './submissionsService';

describe('MoodleFeedbackPushService', () => {
  afterEach(() => jest.restoreAllMocks());

  it('startet einen Push und liefert die job id', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({ id: 5, status: 'queued' }),
    }) as unknown as typeof fetch;

    const job = await MoodleFeedbackPushService.start(42);
    expect(job.id).toBe(5);
    expect(job.status).toBe('queued');
    const call = (global.fetch as jest.Mock).mock.calls[0];
    expect(call[0]).toContain('/api/v1/exams/42/moodle/push-feedback');
    expect(call[1].method).toBe('POST');
  });

  it('pollt den Job-Status', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: 5, status: 'completed', students_pushed: 3 }),
    }) as unknown as typeof fetch;

    const job = await MoodleFeedbackPushService.poll(42, 5);
    expect(job.status).toBe('completed');
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain(
      '/api/v1/exams/42/moodle/push-feedback/5',
    );
  });

  it('wirft ApiError bei 412 (keine Moodle-Zuordnung)', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 412,
      json: async () => ({ detail: 'Keine Moodle-Verbindung' }),
    }) as unknown as typeof fetch;

    await expect(MoodleFeedbackPushService.start(42)).rejects.toBeInstanceOf(
      ApiError,
    );
  });
});
