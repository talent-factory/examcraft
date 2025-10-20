/**
 * Review Page
 * Question review and validation
 */

import React from 'react';
import ReviewQueue from '../components/ReviewQueue';

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

      {/* Review Queue */}
      <ReviewQueue />
    </div>
  );
};

