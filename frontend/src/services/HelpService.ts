import { AppError } from '../errors';

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

  async getStatus(): Promise<HelpStatus> {
    const response = await fetch(`${API_BASE_URL}/api/v1/help/status`);
    if (!response.ok) throw new AppError('help.statusFailed', undefined, response.status);
    return response.json();
  }

  async getOnboardingStatus(token: string): Promise<OnboardingStatus> {
    const response = await fetch(`${API_BASE_URL}/api/v1/help/onboarding/status`, {
      headers: this.getHeaders(token),
    });
    if (!response.ok) throw new AppError('help.onboardingStatusFailed', undefined, response.status);
    return response.json();
  }

  async completeOnboardingStep(token: string, step: number): Promise<OnboardingStatus> {
    const response = await fetch(`${API_BASE_URL}/api/v1/help/onboarding/step`, {
      method: 'PUT',
      headers: this.getHeaders(token),
      body: JSON.stringify({ step }),
    });
    if (!response.ok) throw new AppError('help.onboardingStepFailed', undefined, response.status);
    return response.json();
  }

  async skipOnboardingStep(token: string, step: number): Promise<OnboardingStatus> {
    const response = await fetch(`${API_BASE_URL}/api/v1/help/onboarding/skip`, {
      method: 'PUT',
      headers: this.getHeaders(token),
      body: JSON.stringify({ step }),
    });
    if (!response.ok) throw new AppError('help.onboardingSkipFailed', undefined, response.status);
    return response.json();
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
    const response = await fetch(
      `${API_BASE_URL}/api/v1/help/onboarding/track/${encodeURIComponent(trackId)}/step`,
      {
        method: 'PUT',
        headers: this.getHeaders(token),
        body: JSON.stringify({ step, total_steps: totalSteps, skipped }),
      }
    );
    if (!response.ok) throw new Error('Failed to update onboarding track step');
    return response.json();
  }

  async getContextHint(token: string, route: string): Promise<ContextHint> {
    const path = route.replace(/^\//, '');
    const response = await fetch(`${API_BASE_URL}/api/v1/help/context/${path}`, {
      headers: this.getHeaders(token),
    });
    if (!response.ok) throw new AppError('help.contextHintFailed', undefined, response.status);
    return response.json();
  }

  async dismissHint(token: string, hintId: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/v1/help/context/dismiss`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify({ hint_id: hintId }),
    });
    if (!response.ok) throw new AppError('help.hintDismissFailed', undefined, response.status);
  }

  async sendMessage(
    token: string,
    question: string,
    route: string,
    conversationHistory?: Array<{ role: string; content: string }>
  ): Promise<HelpMessage> {
    const response = await fetch(`${API_BASE_URL}/api/v1/help/message`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify({ question, route, conversation_history: conversationHistory }),
    });
    if (!response.ok) {
      throw new AppError('help.messageFailed', undefined, response.status);
    }
    return response.json();
  }

  async submitFeedback(token: string, feedback: FeedbackRequest): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/v1/help/feedback`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify(feedback),
    });
    if (!response.ok) throw new AppError('help.feedbackFailed', undefined, response.status);
  }
}

export const helpService = new HelpService();
