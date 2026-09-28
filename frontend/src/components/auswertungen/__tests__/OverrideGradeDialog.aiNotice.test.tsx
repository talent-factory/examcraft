/**
 * OverrideGradeDialog labels the proposal being overridden as an AI-assisted
 * grading suggestion (EU AI Act Art. 50, TF-747).
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import OverrideGradeDialog from '../OverrideGradeDialog';

describe('OverrideGradeDialog — KI-Kennzeichnung', () => {
  it('zeigt den Hinweis auf den KI-gestützten Bewertungsvorschlag', () => {
    render(
      <OverrideGradeDialog
        open
        gradeId={1}
        initialPoints={2}
        pointsMax={5}
        onClose={() => {}}
        onSuccess={() => {}}
      />,
    );

    expect(screen.getByTestId('ai-notice-gradingSuggestion')).toBeInTheDocument();
  });
});
