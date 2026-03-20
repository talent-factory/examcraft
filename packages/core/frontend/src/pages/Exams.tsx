/**
 * Exams Page
 * Exam generation and management
 *
 * In Full deployment mode, uses Premium RAGExamCreator via dynamic import.
 * In Core deployment mode, falls back to stub component.
 */

import React from 'react';
import { loadRAGExamCreator } from '../utils/componentLoader';

// Dynamically load RAGExamCreator from Premium package
const RAGExamCreator = loadRAGExamCreator();

export const Exams: React.FC = () => {
  const handleExamGenerated = (exam: any) => {
    console.log('Exam generated:', exam);
    // Do nothing - let RAGExamCreator handle the display
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          Prüfungsgenerierung
        </h1>
        <p className="text-gray-600 mt-2">
          Erstelle intelligente Prüfungsaufgaben mit KI-Unterstützung
        </p>
      </div>

      {/* RAG Exam Creator */}
      <RAGExamCreator
        selectedDocuments={[]}
        onExamGenerated={handleExamGenerated}
      />
    </div>
  );
};
