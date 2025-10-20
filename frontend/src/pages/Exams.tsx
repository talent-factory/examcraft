/**
 * Exams Page
 * Exam generation and management
 */

import React from 'react';

export const Exams: React.FC = () => {
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

      {/* Content Placeholder */}
      <div className="card p-12 text-center">
        <div className="text-6xl mb-4">✨</div>
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">
          Prüfungsgenerierung
        </h2>
        <p className="text-gray-600 mb-6">
          Diese Seite wird in Phase 3 mit der bestehenden RAGExamCreator Komponente integriert.
        </p>
        <div className="inline-block px-6 py-3 bg-secondary-600 text-white rounded-lg font-medium">
          Neue Prüfung erstellen
        </div>
      </div>
    </div>
  );
};

