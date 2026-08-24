/**
 * HelpWidgetGate
 *
 * Auth gate for the help widget (TF-657).
 *
 * The widget is mounted in `AppWithAuth` outside of `<Routes>` and would
 * therefore also render on the public routes (/login, /register, /auth/*,
 * /verify-email, /registration-success). Gating is deliberately done on auth
 * status rather than an allowlist of public routes — otherwise every new
 * public route would reopen the fix.
 *
 * The guard must sit one level above `HelpWidget`: React hooks can't be
 * called conditionally, so an early return inside `HelpWidget` would still
 * let `useHelpContext` (and its help requests) fire.
 *
 * `isLoading` belongs in the gate too: without it, the FAB briefly flashes
 * during the token bootstrap after a reload, before `isAuthenticated` settles.
 */

import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import HelpWidget from './HelpWidget';

const HelpWidgetGate: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading || !isAuthenticated) return null;

  return <HelpWidget />;
};

export default HelpWidgetGate;
