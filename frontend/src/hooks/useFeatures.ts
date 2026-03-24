/**
 * useFeatures Hook
 * React hook for fetching and caching user features and subscription tier
 *
 * This hook calls the /api/auth/features endpoint and caches the result
 * to avoid unnecessary API calls. It integrates with the authentication
 * context to automatically refetch when the user changes.
 *
 * @example
 * const { features, tier, quotas, hasFeature, isLoading, error } = useFeatures();
 *
 * if (hasFeature('document_chatbot')) {
 *   // Show premium feature
 * }
 */

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';

// ============================================================================
// Types
// ============================================================================

export interface UserFeatures {
  subscription_tier: string;
  features: string[];
  quotas: {
    max_documents: number;
    max_questions_per_month: number;
    max_users: number;
  };
}

export interface UseFeaturesReturn {
  /** User's subscription tier (free, starter, professional, enterprise) */
  tier: string | null;
  /** List of enabled feature names */
  features: string[];
  /** Quota limits for the user's institution */
  quotas: UserFeatures['quotas'] | null;
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
        throw new Error(`Failed to fetch features: ${response.statusText}`);
      }

      const featuresData: UserFeatures = await response.json();

      // Cache the result
      localStorage.setItem(CACHE_KEY, JSON.stringify({
        data: featuresData,
        timestamp: Date.now(),
      }));

      setData(featuresData);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch features';
      setError(errorMessage);
      console.error('[useFeatures] Error fetching features:', err);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, accessToken]);

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
        const { data: cachedData, timestamp } = JSON.parse(cached);
        const age = Date.now() - timestamp;

        if (age < CACHE_DURATION) {
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
    hasFeature,
    isLoading,
    error,
    refetch: fetchFeatures,
  };
};

export default useFeatures;
