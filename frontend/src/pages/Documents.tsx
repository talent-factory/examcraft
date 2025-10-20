/**
 * Documents Page
 * Document management and upload
 */

import React from 'react';

export const Documents: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          Dokumentenbibliothek
        </h1>
        <p className="text-gray-600 mt-2">
          Verwalte deine Lehrmaterialien und Dokumente
        </p>
      </div>

      {/* Content Placeholder */}
      <div className="card p-12 text-center">
        <div className="text-6xl mb-4">📄</div>
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">
          Dokumentenbibliothek
        </h2>
        <p className="text-gray-600 mb-6">
          Diese Seite wird in Phase 3 mit der bestehenden DocumentUpload und DocumentLibrary Komponente integriert.
        </p>
        <div className="inline-block px-6 py-3 bg-primary-600 text-white rounded-lg font-medium">
          Dokument hochladen
        </div>
      </div>
    </div>
  );
};

