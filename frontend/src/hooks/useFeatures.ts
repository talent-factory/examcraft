/**
 * useFeatures Hook
 * React hook for fetching and caching user features and subscription tier
 *
 * This hook calls the /api/auth/features endpoint and caches the result
 * to avoid unnecessary API calls. It integrates with the authentication
 * context to automatically refetch when the user changes.
 *
 * @example
 * const { features, tier, quotas, evaluationLimits, hasFeature, isLoading, error } = useFeatures();
 *
 * if (hasFeature('document_chatbot')) {
 *   // Show premium feature
 * }
 */

import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { AppError, translateError } from '../errors';

// ============================================================================
// Types
// ============================================================================

/**
 * Evaluation tier limits from `services/auswertung_quotas.py::TierLimits`
 * (TF-1055). `-1` = unlimited. Used to disable gated actions up front; the
 * backend's 402 stays the actual gate.
 */
export interface EvaluationLimits {
  tier: string;
  label: string;
  exams_per_month: number;
  submissions_per_exam: number;
  drivers: string[];
  llm_grading: boolean;
  class_history_stats: boolean;
  review_bulk: boolean;
  custom_grading_schemes: boolean;
  custom_llm_model: boolean;
}

export interface UserFeatures {
  subscription_tier: string;
  features: string[];
  quotas: {
    max_documents: number;
    max_questions_per_month: number;
    max_users: number;
  };
  evaluation_limits: EvaluationLimits;
}

export interface UseFeaturesReturn {
  /** User's subscription tier (free, starter, professional, enterprise) */
  tier: string | null;
  /** List of enabled feature names */
  features: string[];
  /** Quota limits for the user's institution */
  quotas: UserFeatures['quotas'] | null;
  /** Evaluation tier limits; null while loading or when the request failed */
  evaluationLimits: EvaluationLimits | null;
  /** Check if a specific feature is enabled */
  hasFeature: (featureName: string) => boolean;
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: string | null;
  /** Manually refetch features */
  refetch: () => Promise<void>;
}

// ============================================================================
// Constants
// ============================================================================

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const CACHE_KEY = 'examcraft_user_features';
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

// ============================================================================
// Hook Implementation
// ============================================================================

export const useFeatures = (): UseFeaturesReturn => {
  const { user, accessToken, isAuthenticated } = useAuth();
  const { t } = useTranslation();
  const [data, setData] = useState<UserFeatures | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  /**
   * Fetch features from API
   */
  const fetchFeatures = useCallback(async () => {
    if (!isAuthenticated || !accessToken) {
      setData(null);
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/api/auth/features`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new AppError('features_load_failed', response.statusText, response.status);
      }

      const featuresData: UserFeatures = await response.json();

      // Cache the result
      localStorage.setItem(CACHE_KEY, JSON.stringify({
        data: featuresData,
        userId: user?.id,
        timestamp: Date.now(),
      }));

      setData(featuresData);
    } catch (err) {
      setError(translateError(err, t, 'errors.features_load_failed'));
      console.error('[useFeatures] Error fetching features:', err);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, accessToken, user?.id, t]);

  /**
   * Load features from cache or fetch from API
   */
  useEffect(() => {
    if (!isAuthenticated || !accessToken) {
      setData(null);
      setIsLoading(false);
      return;
    }

    // Try to load from cache first
    const cached = localStorage.getItem(CACHE_KEY);
    if (cached) {
      try {
        const { data: cachedData, userId: cachedUserId, timestamp } = JSON.parse(cached);
        const age = Date.now() - timestamp;

        // Entries cached before TF-1055 lack `evaluation_limits`; refetch
        // instead of treating every gated action as unknown for 5 minutes.
        // The cache is shared across logins, so only reuse it for the same user.
        if (
          age < CACHE_DURATION &&
          cachedData?.evaluation_limits &&
          cachedUserId === user?.id
        ) {
          // Cache is still valid
          setData(cachedData);
          setIsLoading(false);
          return;
        }
      } catch (err) {
        console.warn('[useFeatures] Failed to parse cached features:', err);
      }
    }

    // Cache miss or expired - fetch from API
    fetchFeatures();
  }, [isAuthenticated, accessToken, user?.id, fetchFeatures]);

  /**
   * Check if a specific feature is enabled
   */
  const hasFeature = useCallback((featureName: string): boolean => {
    if (!data) return false;
    return data.features.includes(featureName);
  }, [data]);

  return {
    tier: data?.subscription_tier || null,
    features: data?.features || [],
    quotas: data?.quotas || null,
    evaluationLimits: data?.evaluation_limits || null,
    hasFeature,
    isLoading,
    error,
    refetch: fetchFeatures,
  };
};

export default useFeatures;
