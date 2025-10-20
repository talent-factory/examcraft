/**
 * Admin Page
 * Admin panel and settings
 */

import React from 'react';

export const Admin: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          Admin-Panel
        </h1>
        <p className="text-gray-600 mt-2">
          Verwalte Benutzer, Einstellungen und Systemkonfiguration
        </p>
      </div>

      {/* Content Placeholder */}
      <div className="card p-12 text-center">
        <div className="text-6xl mb-4">⚙️</div>
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">
          Admin-Panel
        </h2>
        <p className="text-gray-600 mb-6">
          Diese Seite wird in Phase 3 mit der bestehenden PromptManagement und Admin-Komponenten integriert.
        </p>
        <div className="inline-block px-6 py-3 bg-gray-600 text-white rounded-lg font-medium">
          Zu den Admin-Tools
        </div>
      </div>
    </div>
  );
};

