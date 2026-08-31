/**
 * Impersonation Banner (TF-743)
 * Persistent bar above the NavigationBar while an admin is impersonating a
 * user — shows who, a live countdown to the TF-741 hard 30-min cap, and a
 * "back to my account" action that ends the session without a fresh login.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { REFRESH_LEAD_MS } from '../../api/tokenRefreshLock';

/**
 * Matches the `h-10` Tailwind class below (40px). NOT read by anything —
 * DashboardLayout, NavigationBar, and Sidebar each hardcode this same value
 * in their own static Tailwind classes (`pt-[104px]`/`top-10`/etc.), because
 * Tailwind's JIT scanner needs literal class names, not an interpolated
 * pixel value built from this constant. Kept in sync by convention across
 * those files, not by import — if this value ever changes, update it here
 * *and* the three hardcoded offsets in those files.
 */
export const IMPERSONATION_BANNER_HEIGHT_PX = 40;

function formatRemaining(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

export const ImpersonationBanner: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { isImpersonating, impersonationExpiresAt, user, endImpersonation } = useAuth();
  const [remainingMs, setRemainingMs] = useState<number | null>(null);
  const [ending, setEnding] = useState(false);
  const [serverEndFailed, setServerEndFailed] = useState(false);

  useEffect(() => {
    if (!isImpersonating || !impersonationExpiresAt) {
      setRemainingMs(null);
      return;
    }
    // The session actually reverts to the admin at REFRESH_LEAD_MS before
    // the hard cap (AuthContext's proactive timer), not at the hard cap
    // itself — count down to that real deadline so this never promises
    // more time than the session actually has left.
    const effectiveDeadlineMs = new Date(impersonationExpiresAt).getTime() - REFRESH_LEAD_MS;
    const tick = () => setRemainingMs(Math.max(0, effectiveDeadlineMs - Date.now()));
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [isImpersonating, impersonationExpiresAt]);

  // Auto-dismiss the "couldn't confirm server-side" notice below — it must
  // outlive the navigate('/dashboard') call in handleReturn (this banner
  // stays mounted across that in-layout navigation), but shouldn't linger
  // forever.
  useEffect(() => {
    if (!serverEndFailed) return;
    const timer = setTimeout(() => setServerEndFailed(false), 8000);
    return () => clearTimeout(timer);
  }, [serverEndFailed]);

  const handleReturn = useCallback(async () => {
    setEnding(true);
    setServerEndFailed(false);
    try {
      // endImpersonation() tells the backend to revoke the impersonation
      // session (TF-741) and restores the admin session locally — the
      // local restore always succeeds even if the backend call failed
      // (network error, or the session already expired server-side and
      // there was nothing left to revoke); backendEndFailed just tells us
      // whether to surface that below, since a support engineer chasing a
      // stuck/duplicate impersonation_sessions row needs a starting point
      // beyond a browser console log nobody was watching.
      const { backendEndFailed } = await endImpersonation();
      setServerEndFailed(backendEndFailed);
    } finally {
      setEnding(false);
      navigate('/dashboard');
    }
  }, [endImpersonation, navigate]);

  if (!isImpersonating && !serverEndFailed) return null;

  if (!isImpersonating) {
    // Impersonation already ended locally; only the transient "couldn't
    // confirm the server-side session was closed" notice remains.
    return (
      <div
        data-testid="impersonation-banner-server-end-failed"
        className="fixed top-0 inset-x-0 z-[60] h-10 bg-amber-500 text-white flex items-center justify-center gap-2 px-4 text-sm shadow-md"
      >
        <span>{t('admin.impersonation.bannerServerEndFailed')}</span>
      </div>
    );
  }

  const targetLabel = user ? `${user.first_name} ${user.last_name} (${user.email})` : '';

  return (
    <div
      data-testid="impersonation-banner"
      className="fixed top-0 inset-x-0 z-[60] h-10 bg-orange-600 text-white flex items-center justify-center gap-3 px-4 text-sm shadow-md"
    >
      <span>
        {t('admin.impersonation.bannerLabel')} <strong>{targetLabel}</strong>
      </span>
      {remainingMs !== null && (
        <span className="font-mono bg-orange-700 px-2 py-0.5 rounded" data-testid="impersonation-banner-countdown">
          {t('admin.impersonation.bannerTimeRemaining', { time: formatRemaining(remainingMs) })}
        </span>
      )}
      <button
        type="button"
        onClick={handleReturn}
        disabled={ending}
        className="ml-2 px-3 py-1 rounded bg-white text-orange-700 font-medium hover:bg-orange-50 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {t('admin.impersonation.bannerReturnButton')}
      </button>
    </div>
  );
};
