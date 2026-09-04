import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

import { UpgradePrompt } from '../UpgradePrompt';

describe('UpgradePrompt', () => {
  it('zeigt die Beschriftungen übersetzt statt englisch hart codiert', () => {
    render(
      <UpgradePrompt
        featureNameKey="components.featureGate.documentChat.name"
        requiredTier="professional"
        currentTier="free"
      />,
    );
    expect(screen.getByText('Dein Tarif')).toBeInTheDocument();
    expect(screen.getByText('Benötigter Tarif')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Jetzt upgraden' })).toBeInTheDocument();
  });

  it('löst featureNameKey/featureDescriptionKey über t() auf, statt den Schlüssel selbst anzuzeigen', () => {
    // Regression guard for the bug this prop rename fixed: the previous
    // `featureName`/`featureDescription` props rendered whatever string was
    // passed verbatim, so every real caller (componentLoader.tsx) showed
    // hardcoded English prose to German users while the chrome around it was
    // translated. Asserting against the real de/translation.json content —
    // not a literal the test itself supplies — is what actually catches that.
    render(
      <UpgradePrompt
        featureNameKey="components.featureGate.documentChat.name"
        featureDescriptionKey="components.featureGate.documentChat.description"
        requiredTier="professional"
        currentTier="free"
      />,
    );
    expect(screen.getByText('Dokument-Chat')).toBeInTheDocument();
    expect(
      screen.getByText('Chatte mit deinen Dokumenten mittels KI-gestützter Unterhaltungen.'),
    ).toBeInTheDocument();
    // Neither the raw key nor English source prose should ever reach the DOM.
    expect(screen.queryByText('components.featureGate.documentChat.name')).not.toBeInTheDocument();
    expect(screen.queryByText(/Chat with your documents/)).not.toBeInTheDocument();
  });

  it('zeigt keine Beschreibung, wenn featureDescriptionKey fehlt', () => {
    render(
      <UpgradePrompt
        featureNameKey="components.featureGate.ragExamCreator.name"
        requiredTier="starter"
        currentTier="free"
      />,
    );
    expect(screen.getByText('RAG-Prüfungsersteller')).toBeInTheDocument();
  });

  it('zeigt keine hart codierten Preise mehr', () => {
    render(
      <UpgradePrompt
        featureNameKey="components.featureGate.documentChat.name"
        requiredTier="professional"
        currentTier="free"
      />,
    );
    expect(screen.queryByText(/\$\d/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Contact Sales/)).not.toBeInTheDocument();
  });

  it('navigiert standardmässig zur eingebundenen /billing-Seite, nicht zum nicht existenten /pricing', () => {
    // TF-671 follow-up: the previous '/pricing' default pointed at a path
    // the SPA router never registers (only '/billing' is wired up in
    // AppWithAuth.tsx) — clicking "Upgrade Now" was a dead link for every
    // caller that didn't override upgradeUrl explicitly (none currently do).
    const originalLocation = window.location;
    // jsdom's window.location isn't directly assignable; replace it for this test.
    // @ts-expect-error -- intentional test-only override of a read-only global
    delete window.location;
    // @ts-expect-error -- minimal stub, only `href` is exercised by handleUpgrade
    window.location = { href: '' };

    render(
      <UpgradePrompt
        featureNameKey="components.featureGate.documentChat.name"
        requiredTier="professional"
        currentTier="free"
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Jetzt upgraden' }));
    expect(window.location.href).toBe('/billing');

    window.location = originalLocation;
  });
});
