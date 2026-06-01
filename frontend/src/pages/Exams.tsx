/**
 * Exams Page
 * Exam generation and management
 *
 * In Full deployment mode, uses Premium RAGExamCreator via dynamic import.
 * In Core deployment mode, falls back to stub component.
 */

import React, { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { loadRAGExamCreator } from '../utils/componentLoader';

// Dynamically load RAGExamCreator from Premium package
const RAGExamCreator = loadRAGExamCreator();

// Navigation state shape used by the Documents page when the user clicks
// "RAG-Prüfung erstellen" — see Documents.tsx::handleCreateRAGExam and the
// route `/questions/generate` it navigates to.
type ExamsLocationState = {
  selectedDocuments?: readonly number[];
};

export const Exams: React.FC = () => {
  const { t } = useTranslation();
  const location = useLocation();

  // Direct navigation has no state — fall back to an empty selection to
  // preserve prior behavior.
  const initialSelectedDocuments = useMemo<number[]>(() => {
    const state = location.state as ExamsLocationState | null;
    const ids = state?.selectedDocuments;
    if (!Array.isArray(ids)) {
      return [];
    }
    return ids.filter(
      (id): id is number => Number.isInteger(id) && (id as number) > 0,
    );
  }, [location.state]);

  const handleExamGenerated = (exam: any) => {
    console.log('Exam generated:', exam);
    // Do nothing - let RAGExamCreator handle the display
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          {t('pages.exams.title')}
        </h1>
        <p className="text-gray-600 mt-2">
          {t('pages.exams.subtitle')}
        </p>
      </div>

      {/* RAG Exam Creator */}
      <div data-testid="exam-config">
        <RAGExamCreator
          selectedDocuments={initialSelectedDocuments}
          onExamGenerated={handleExamGenerated}
        />
      </div>
    </div>
  );
};
