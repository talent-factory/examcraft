import { AppError, AppErrorCode, appErrorFromResponse } from '../errors';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface HelpStatus {
  modes: { onboarding: boolean; context: boolean; chat: boolean };
}

/** Progress within an optional deep-dive track (TF-625). */
export interface TrackProgressEntry {
  current_step: number;
  completed_steps: number[];
  skipped_steps: number[];
  completed: boolean;
}

export interface OnboardingStatus {
  id?: number;
  role: string;
  current_step: number;
  completed_steps: number[];
  skipped_steps: number[];
  completed: boolean;
  /** Keyed by track id; tracks without an entry were never started. */
  track_progress: Record<string, TrackProgressEntry>;
}

export interface ContextHint {
  i18n_key: string | null;
  hint_id: number | null;
}

export interface HelpMessage {
  answer: string;
  confidence: number;
  sources: Array<{ file: string; section: string }>;
  docs_links: string[];
  escalate: boolean;
  from_cache: boolean;
}

export interface FeedbackRequest {
  question: string;
  answer?: string;
  confidence?: number;
  rating: 'up' | 'down';
  route: string;
}

class HelpService {
  private getHeaders(token: string): HeadersInit {
    return {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    };
  }

  /**
   * One help request, with the failing operation's code (TF-772).
   *
   * `fetch` itself rejecting (offline, DNS failure, CORS) is a separate
   * failure mode from a non-ok `Response` — there is no body for
   * `appErrorFromResponse` to read, so it is caught here and given the same
   * operation code directly, the same pattern `gradesService`'s `request()`
   * uses.
   */
  private async request<T>(url: string, init: RequestInit = {}, code: AppErrorCode): Promise<T> {
    let response: Response;
    try {
      response = await fetch(url, init);
    } catch (err) {
      throw new AppError(code, err instanceof Error ? err.message : undefined);
    }
    if (!response.ok) throw await appErrorFromResponse(response, code);
    return response.json();
  }

  async getStatus(): Promise<HelpStatus> {
    return this.request(`${API_BASE_URL}/api/v1/help/status`, {}, 'help.statusFailed');
  }

  async getOnboardingStatus(token: string): Promise<OnboardingStatus> {
    return this.request(
      `${API_BASE_URL}/api/v1/help/onboarding/status`,
      { headers: this.getHeaders(token) },
      'help.onboardingStatusFailed',
    );
  }

  async completeOnboardingStep(token: string, step: number): Promise<OnboardingStatus> {
    return this.request(
      `${API_BASE_URL}/api/v1/help/onboarding/step`,
      { method: 'PUT', headers: this.getHeaders(token), body: JSON.stringify({ step }) },
      'help.onboardingStepFailed',
    );
  }

  async skipOnboardingStep(token: string, step: number): Promise<OnboardingStatus> {
    return this.request(
      `${API_BASE_URL}/api/v1/help/onboarding/skip`,
      { method: 'PUT', headers: this.getHeaders(token), body: JSON.stringify({ step }) },
      'help.onboardingSkipFailed',
    );
  }

  /**
   * Record progress within a deep-dive track (TF-625).
   *
   * `totalSteps` is sent along because only the client knows the track length
   * from help-onboarding-steps.json — the backend deliberately keeps no second
   * list, to avoid drift like TF-604.
   */
  async updateTrackStep(
    token: string,
    trackId: string,
    step: number,
    totalSteps: number,
    skipped = false
  ): Promise<OnboardingStatus> {
    return this.request(
      `${API_BASE_URL}/api/v1/help/onboarding/track/${encodeURIComponent(trackId)}/step`,
      {
        method: 'PUT',
        headers: this.getHeaders(token),
        body: JSON.stringify({ step, total_steps: totalSteps, skipped }),
      },
      'help_onboarding_track_step_failed',
    );
  }

  async getContextHint(token: string, route: string): Promise<ContextHint> {
    const path = route.replace(/^\//, '');
    return this.request(
      `${API_BASE_URL}/api/v1/help/context/${path}`,
      { headers: this.getHeaders(token) },
      'help.contextHintFailed',
    );
  }

  async dismissHint(token: string, hintId: number): Promise<void> {
    await this.request(
      `${API_BASE_URL}/api/v1/help/context/dismiss`,
      {
        method: 'POST',
        headers: this.getHeaders(token),
        body: JSON.stringify({ hint_id: hintId }),
      },
      'help.hintDismissFailed',
    );
  }

  async sendMessage(
    token: string,
    question: string,
    route: string,
    conversationHistory?: Array<{ role: string; content: string }>
  ): Promise<HelpMessage> {
    return this.request(
      `${API_BASE_URL}/api/v1/help/message`,
      {
        method: 'POST',
        headers: this.getHeaders(token),
        body: JSON.stringify({ question, route, conversation_history: conversationHistory }),
      },
      'help.messageFailed',
    );
  }

  async submitFeedback(token: string, feedback: FeedbackRequest): Promise<void> {
    await this.request(
      `${API_BASE_URL}/api/v1/help/feedback`,
      { method: 'POST', headers: this.getHeaders(token), body: JSON.stringify(feedback) },
      'help.feedbackFailed',
    );
  }
}

export const helpService = new HelpService();
