const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface HelpStatus {
  modes: { onboarding: boolean; context: boolean; chat: boolean };
}

export interface OnboardingStatus {
  id?: number;
  role: string;
  current_step: number;
  completed_steps: number[];
  skipped_steps: number[];
  completed: boolean;
}

export interface ContextHint {
  hint_text: string | null;
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
    if (!response.ok) throw new Error('Failed to fetch help status');
    return response.json();
  }

  async getOnboardingStatus(token: string): Promise<OnboardingStatus> {
    const response = await fetch(`${API_BASE_URL}/api/v1/help/onboarding/status`, {
      headers: this.getHeaders(token),
    });
    if (!response.ok) throw new Error('Failed to fetch onboarding status');
    return response.json();
  }

  async completeOnboardingStep(token: string, step: number): Promise<OnboardingStatus> {
    const response = await fetch(`${API_BASE_URL}/api/v1/help/onboarding/step`, {
      method: 'PUT',
      headers: this.getHeaders(token),
      body: JSON.stringify({ step }),
    });
    if (!response.ok) throw new Error('Failed to complete onboarding step');
    return response.json();
  }

  async skipOnboardingStep(token: string, step: number): Promise<OnboardingStatus> {
    const response = await fetch(`${API_BASE_URL}/api/v1/help/onboarding/skip`, {
      method: 'PUT',
      headers: this.getHeaders(token),
      body: JSON.stringify({ step }),
    });
    if (!response.ok) throw new Error('Failed to skip onboarding step');
    return response.json();
  }

  async getContextHint(token: string, route: string): Promise<ContextHint> {
    const path = route.replace(/^\//, '');
    const response = await fetch(`${API_BASE_URL}/api/v1/help/context/${path}`, {
      headers: this.getHeaders(token),
    });
    if (!response.ok) throw new Error('Failed to fetch context hint');
    return response.json();
  }

  async dismissHint(token: string, hintId: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/v1/help/context/dismiss`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify({ hint_id: hintId }),
    });
    if (!response.ok) throw new Error('Failed to dismiss hint');
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
      const err = new Error('Failed to send help message') as Error & { status: number };
      err.status = response.status;
      throw err;
    }
    return response.json();
  }

  async submitFeedback(token: string, feedback: FeedbackRequest): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/v1/help/feedback`, {
      method: 'POST',
      headers: this.getHeaders(token),
      body: JSON.stringify(feedback),
    });
    if (!response.ok) throw new Error('Failed to submit feedback');
  }
}

export const helpService = new HelpService();
