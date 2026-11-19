/**
 * Impersonation Reason Dialog Component (TF-743)
 * Confirms the target user and collects the mandatory reason before
 * POST /api/admin/users/{id}/impersonate is called.
 *
 * EXAMCRAFT-126: The step-up (TF-758) is no longer a password field here. The
 * backend demands a fresh IdP login (`auth_reauth_required`, 403); the dialog
 * then sends the admin through `/api/v1/auth/login?reauth=true&return_to=/admin`
 * and, on return, reopens prefilled from the saved request (EXAMCRAFT-144).
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import AdminService, { UserDetailResponse } from '../../services/AdminService';
import { isAppError, translateError } from '../../errors';
import { useAuth } from '../../contexts/AuthContext';
import {
  clearSessionSnapshot,
  readSessionSnapshot,
  writeSessionSnapshot,
} from '../../utils/sessionSnapshot';

const REASON_MIN_LENGTH = 3;
const REASON_MAX_LENGTH = 500;

// EXAMCRAFT-144: the step-up leaves the app for the IdP, so the pending request
// (target user + reason, never a password or token) is kept as a session
// snapshot (TF-608: wiped on logout) and the dialog reopens prefilled on
// return. It is bound to the saving admin, because a step-up can end in a
// different account (`prompt=login`), and one click confirms.
const PENDING_SNAPSHOT_KEY = 'pending-impersonation';
const PENDING_SNAPSHOT_VERSION = 1;
const STEP_UP_RETURN_TO = '/admin';
const PENDING_MAX_AGE_MS = 10 * 60 * 1000;

export interface PendingImpersonation {
  userId: number;
  reason: string;
}

interface StoredPendingImpersonation extends PendingImpersonation {
  adminId: number;
  savedAt: number;
}

function savePendingImpersonation(pending: PendingImpersonation, adminId: number): boolean {
  // A failed write is not fatal: after the step-up the dialog stays closed and
  // the admin re-selects the user and re-enters the reason.
  const saved = writeSessionSnapshot<StoredPendingImpersonation>(
    PENDING_SNAPSHOT_KEY,
    PENDING_SNAPSHOT_VERSION,
    { ...pending, adminId, savedAt: Date.now() },
  );
  if (!saved) {
    console.warn('[ImpersonationReasonDialog] Pending impersonation could not be saved.');
  }
  return saved;
}

/**
 * Read and remove the pending request. Null when absent, stale, malformed or
 * saved by a different admin than `adminId`.
 */
export function takePendingImpersonation(adminId: number): PendingImpersonation | null {
  const data = readSessionSnapshot<StoredPendingImpersonation>(
    PENDING_SNAPSHOT_KEY,
    PENDING_SNAPSHOT_VERSION,
  );
  if (!data) return null;
  clearSessionSnapshot(PENDING_SNAPSHOT_KEY);
  if (
    Number.isInteger(data.userId) &&
    typeof data.reason === 'string' &&
    data.adminId === adminId &&
    typeof data.savedAt === 'number' &&
    Date.now() - data.savedAt <= PENDING_MAX_AGE_MS
  ) {
    return { userId: data.userId, reason: data.reason };
  }
  return null;
}

interface ImpersonationReasonDialogProps {
  userId: number | null;
  /** Reason restored after a step-up round trip. */
  initialReason?: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const ImpersonationReasonDialog: React.FC<ImpersonationReasonDialogProps> = ({
  userId,
  initialReason = '',
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation();
  const { user, startImpersonation, login } = useAuth();
  const [target, setTarget] = useState<UserDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [reason, setReason] = useState('');

  const loadTarget = useCallback(async () => {
    if (!userId) return;

    try {
      setLoading(true);
      setError(null);
      setTarget(await AdminService.getUser(userId));
    } catch (err) {
      setError(translateError(err, t, 'admin.impersonation.dialogLoadFailed'));
    } finally {
      setLoading(false);
    }
  }, [userId, t]);

  useEffect(() => {
    if (isOpen && userId) {
      loadTarget();
    }
    if (!isOpen) {
      // Reset for the next open — a dialog re-opened for a different user
      // must not show the previous reason or a stale target.
      setTarget(null);
      setReason('');
      setError(null);
      setNotice(null);
      setSaving(false);
    }
  }, [isOpen, userId, loadTarget]);

  // After the step-up redirect the browser may restore this page from the
  // back/forward cache (admin pressed "back" at the IdP) with `saving` still
  // set; release the dialog then.
  useEffect(() => {
    const onPageShow = (event: PageTransitionEvent) => {
      if (event.persisted) {
        setSaving(false);
        setNotice(null);
      }
    };
    window.addEventListener('pageshow', onPageShow);
    return () => window.removeEventListener('pageshow', onPageShow);
  }, []);

  // Separate from the load effect: a new `loadTarget` identity (language
  // change) must not overwrite a reason the admin already typed.
  useEffect(() => {
    if (isOpen && userId) setReason(initialReason);
  }, [isOpen, userId, initialReason]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId) return;

    const trimmedReason = reason.trim();
    if (trimmedReason.length < REASON_MIN_LENGTH) {
      setError(t('admin.impersonation.reasonTooShort', { min: REASON_MIN_LENGTH }));
      return;
    }

    let redirecting = false;
    try {
      setSaving(true);
      setError(null);
      setNotice(null);

      const response = await AdminService.impersonateUser(userId, trimmedReason);
      await startImpersonation({
        expiresIn: response.expires_in,
        expiresAt: response.expires_at,
      });

      onSuccess();
      onClose();
    } catch (err) {
      if (isAppError(err) && err.code === 'auth_reauth_required') {
        // Step-up: the IdP login is older than the backend accepts. Keep the
        // request and return to the admin panel, where the dialog reopens.
        const kept = user
          ? savePendingImpersonation({ userId, reason: trimmedReason }, user.id)
          : false;
        if (!user) {
          console.warn('[ImpersonationReasonDialog] No current user, step-up without resume.');
        }
        // EXAMCRAFT-139: tell the admin why the page is about to change; promise
        // kept input only when it really was saved.
        setNotice(
          t(kept ? 'admin.impersonation.reauthRedirect' : 'admin.impersonation.reauthRedirectNoResume'),
        );
        try {
          login({ reauth: true, returnTo: STEP_UP_RETURN_TO });
          // Stay in the saving state while the browser navigates away.
          redirecting = true;
        } catch (loginError) {
          console.error('[ImpersonationReasonDialog] Step-up redirect failed:', loginError);
          setNotice(null);
          setError(translateError(loginError, t, 'admin.impersonation.dialogError'));
        }
        return;
      }
      setError(translateError(err, t, 'admin.impersonation.dialogError'));
    } finally {
      if (!redirecting) setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div
          data-testid="impersonation-dialog-backdrop"
          className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
          onClick={saving ? undefined : onClose}
        ></div>

        {/* Modal panel */}
        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <form onSubmit={handleSubmit}>
            <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
              <div className="sm:flex sm:items-start">
                <div className="mt-3 text-center sm:mt-0 sm:text-left w-full">
                  <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                    {t('admin.impersonation.dialogTitle')}
                  </h3>

                  {loading ? (
                    <div className="flex justify-center py-8">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {error && (
                        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg text-sm">
                          {error}
                        </div>
                      )}

                      {notice && (
                        <div
                          role="status"
                          data-testid="impersonation-reauth-notice"
                          className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-lg text-sm"
                        >
                          {notice}
                        </div>
                      )}

                      {target && (
                        <div className="bg-orange-50 border border-orange-200 p-3 rounded-lg text-sm">
                          <p className="text-orange-900">
                            {t('admin.impersonation.dialogTargetLabel')}{' '}
                            <span className="font-medium">
                              {target.first_name} {target.last_name}
                            </span>{' '}
                            ({target.email})
                          </p>
                        </div>
                      )}

                      <div>
                        <label htmlFor="impersonation-reason" className="block text-sm font-medium text-gray-700 mb-1">
                          {t('admin.impersonation.dialogReasonLabel')}
                        </label>
                        <textarea
                          id="impersonation-reason"
                          name="reason"
                          rows={3}
                          value={reason}
                          onChange={(e) => setReason(e.target.value)}
                          required
                          minLength={REASON_MIN_LENGTH}
                          maxLength={REASON_MAX_LENGTH}
                          placeholder={t('admin.impersonation.dialogReasonPlaceholder')}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                        />
                      </div>

                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
              <button
                type="submit"
                disabled={saving || loading}
                className="w-full inline-flex justify-center rounded-lg border border-transparent shadow-sm px-4 py-2 bg-orange-600 text-base font-medium text-white hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? t('admin.impersonation.dialogStarting') : t('admin.impersonation.dialogConfirm')}
              </button>
              <button
                type="button"
                onClick={onClose}
                disabled={saving}
                className="mt-3 w-full inline-flex justify-center rounded-lg border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {t('admin.impersonation.dialogCancel')}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
