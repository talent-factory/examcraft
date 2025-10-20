/**
 * Review Page
 * Question review and validation
 */

import React from 'react';

export const Review: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          Fragen-Review
        </h1>
        <p className="text-gray-600 mt-2">
          Überprüfe und validiere generierte Prüfungsfragen
        </p>
      </div>

      {/* Content Placeholder */}
      <div className="card p-12 text-center">
        <div className="text-6xl mb-4">✅</div>
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">
          Fragen-Review
        </h2>
        <p className="text-gray-600 mb-6">
          Diese Seite wird in Phase 3 mit der bestehenden ReviewQueue Komponente integriert.
        </p>
        <div className="inline-block px-6 py-3 bg-green-600 text-white rounded-lg font-medium">
          Zur Review Queue
        </div>
      </div>
    </div>
  );
};

