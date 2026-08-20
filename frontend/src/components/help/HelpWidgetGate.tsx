/**
 * HelpWidgetGate
 *
 * Auth-Gate für das Hilfe-Widget (TF-657).
 *
 * Das Widget hängt in `AppWithAuth` ausserhalb von `<Routes>` und würde damit
 * auch auf den öffentlichen Routen (/login, /register, /auth/*, /verify-email,
 * /registration-success) rendern. Gegated wird bewusst am Auth-Status statt an
 * einer Allowlist öffentlicher Routen — sonst reisst jede neue Public-Route den
 * Fix wieder auf.
 *
 * Der Guard muss eine Ebene über `HelpWidget` sitzen: React-Hooks lassen sich
 * nicht bedingt aufrufen, ein Early-Return innerhalb von `HelpWidget` würde
 * `useHelpContext` (und dessen Help-Requests) weiterhin feuern lassen.
 *
 * `isLoading` gehört mit ins Gate: ohne das blitzt der FAB während des
 * Token-Bootstraps nach einem Reload kurz auf, bevor `isAuthenticated` steht.
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
