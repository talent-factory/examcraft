/**
 * AiNotice Tests (EU AI Act Art. 50, TF-747)
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { AiNotice } from '../AiNotice';
import deTranslation from '../../../locales/de/translation.json';
import enTranslation from '../../../locales/en/translation.json';
import frTranslation from '../../../locales/fr/translation.json';
import itTranslation from '../../../locales/it/translation.json';

describe('AiNotice', () => {
  it('shows label and hint for AI-generated task drafts', () => {
    render(<AiNotice kind="taskDraft" />);
    const notice = screen.getByTestId('ai-notice-taskDraft');
    expect(notice).toHaveTextContent('KI-generierter Aufgabenentwurf');
    expect(notice).toHaveTextContent('von einem KI-System entworfen');
  });

  it('shows the AI-assisted grading suggestion label', () => {
    render(<AiNotice kind="gradingSuggestion" />);
    expect(screen.getByTestId('ai-notice-gradingSuggestion')).toHaveTextContent(
      'KI-gestützter Bewertungsvorschlag'
    );
  });

  it('tells chat users they talk to an AI system', () => {
    render(<AiNotice kind="chat" />);
    expect(screen.getByTestId('ai-notice-chat')).toHaveTextContent('KI-System, nicht mit einem Menschen');
  });

  it('renders a compact chip with only the label', () => {
    render(<AiNotice kind="taskDraft" variant="chip" />);
    const chip = screen.getByTestId('ai-notice-taskDraft');
    expect(chip).toHaveTextContent('KI-generierter Aufgabenentwurf');
    expect(chip).not.toHaveTextContent('Bitte inhaltlich prüfen');
  });

  it.each([
    ['de', deTranslation],
    ['en', enTranslation],
    ['fr', frTranslation],
    ['it', itTranslation],
  ])('has label and hint for every kind in %s', (_locale, translation) => {
    const aiAct = (translation as { aiAct: Record<string, { label: string; hint: string }> }).aiAct;
    for (const kind of ['taskDraft', 'gradingSuggestion', 'chat']) {
      expect(aiAct[kind].label).toBeTruthy();
      expect(aiAct[kind].hint).toBeTruthy();
    }
  });
});
