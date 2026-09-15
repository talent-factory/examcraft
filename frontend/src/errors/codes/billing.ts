/**
 * Error codes reachable through `paymentService` on
 * `SubscriptionManagementPage` (TF-772 PR 7), router
 * `core/backend/api/v1/billing.py`.
 *
 * The page rendered `response.data.detail`, and for the portal a hard-coded
 * English fallback («Failed to open subscription management») the i18n guard
 * did not see. Found in the closeout sweep of PR 7.
 *
 * BACKEND CODES, from POST `/customer-portal`, texts verbatim from
 * `core/backend/locales/t.*.json` (`billing_service_not_configured` in the
 * informal wording of TF-773 PR 2a): `billing_no_institution`,
 * `billing_portal_failed`, `billing_portal_owner_only`,
 * `billing_service_not_configured`, `billing_subscription_not_found`.
 * GET `/subscription` raises no code of its own.
 *
 * `billing_portal_failed` doubles as the portal fallback — the backend already
 * names that sentence. `billing_subscription_load_failed` is frontend-only,
 * text of `pages.subscription.loadError`.
 *
 * Scope is this page only. `billing.py` raises a dozen more codes from the
 * checkout, invoice, payment-method and sync endpoints; their consumers do not
 * render the response body and are not registered here.
 */
export const BILLING_ERROR_CODES = [
  'billing_no_institution',
  'billing_portal_failed',
  'billing_portal_owner_only',
  'billing_service_not_configured',
  'billing_subscription_load_failed',
  'billing_subscription_not_found',
] as const;
