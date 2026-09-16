/**
 * Upgrade path end to end: a real loader call site → withFeatureGate →
 * UpgradePrompt, with the feature locked.
 *
 * `UpgradePrompt.test.tsx` proves the prompt resolves whatever key it is
 * handed. It cannot prove that the loaders hand it a key at all — the test
 * supplies the key itself. That gap is what let hardcoded English prose sit in
 * `componentLoader.tsx` behind a translated prompt (TF-671), and the English
 * names passed to `FeatureUnavailable` survived it (TF-772 PR 5). So these
 * tests go through the exported loaders and assert on the German text from
 * the real `de/translation.json`, never on a literal the test passes in.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import { loadDocumentChat, loadRAGExamCreator } from '../componentLoader';
import { withFeatureGate } from '../../components/common/withFeatureGate';
import { isFullDeployment } from '../deploymentMode';
import { useFeatures } from '../../hooks/useFeatures';

jest.mock('../deploymentMode', () => ({
  isFullDeployment: jest.fn(),
}));

jest.mock('../../hooks/useFeatures', () => ({
  useFeatures: jest.fn(),
}));

const mockIsFullDeployment = isFullDeployment as jest.MockedFunction<typeof isFullDeployment>;
const mockUseFeatures = useFeatures as jest.MockedFunction<typeof useFeatures>;

const featuresWith = (enabled: string[]) => ({
  tier: 'free',
  features: enabled,
  quotas: null,
  hasFeature: (name: string) => enabled.includes(name),
  isLoading: false,
  error: null,
  refetch: jest.fn(),
});

describe('componentLoader — Upgrade-Pfad', () => {
  beforeEach(() => {
    jest.spyOn(console, 'warn').mockImplementation(() => {});
    mockIsFullDeployment.mockReturnValue(true);
    mockUseFeatures.mockReturnValue(featuresWith([]));
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('zeigt bei gesperrtem Feature den übersetzten Namen und die Beschreibung, nicht den Slug', () => {
    // loadDocumentChat returns the gate itself, so a locked feature renders
    // UpgradePrompt without ever resolving the lazy premium import.
    const DocumentChat = loadDocumentChat();
    render(<DocumentChat />);

    expect(screen.getByText('Dokument-Chat')).toBeInTheDocument();
    expect(
      screen.getByText('Chatte mit deinen Dokumenten mittels KI-gestützter Unterhaltungen.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Jetzt upgraden' })).toBeInTheDocument();

    // Neither the RBAC slug, the raw key nor the old English prose.
    expect(screen.queryByText('document_chatbot')).not.toBeInTheDocument();
    expect(screen.queryByText(/components\.featureGate/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Document Chat|Chat with your documents/)).not.toBeInTheDocument();
  });

  it('zeigt die Komponente, wenn das Feature freigeschaltet ist', () => {
    mockUseFeatures.mockReturnValue(featuresWith(['document_chatbot']));
    const Gated = withFeatureGate(
      () => <div>freigeschaltet</div>,
      'document_chatbot',
      'professional',
      'components.featureGate.documentChat.name',
    );
    render(<Gated />);

    expect(screen.getByText('freigeschaltet')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Jetzt upgraden' })).not.toBeInTheDocument();
  });

  it('fällt ohne featureNameKey auf den Feature-Slug zurück (bewusst beibehalten)', () => {
    // Documented fallback in withFeatureGate: only reachable when a caller
    // omits the key, which no loader does. Pinned so a change is deliberate.
    const Gated = withFeatureGate(() => <div />, 'rag_generation', 'starter');
    render(<Gated />);

    expect(screen.getByText('rag_generation')).toBeInTheDocument();
  });

  it('übersetzt den Feature-Namen auch im Core-Modus (FeatureUnavailable)', () => {
    mockIsFullDeployment.mockReturnValue(false);
    const RAGExamCreator = loadRAGExamCreator();
    render(<RAGExamCreator />);

    expect(screen.getByText('RAG-Prüfungsersteller ist nicht verfügbar')).toBeInTheDocument();
    expect(screen.queryByText(/RAG Exam Creator/)).not.toBeInTheDocument();
  });
});
