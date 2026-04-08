/**
 * Review Page
 * Question review and validation
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import ReviewQueue from '../components/ReviewQueue';

export const Review: React.FC = () => {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          {t('pages.review.title')}
        </h1>
        <p className="text-gray-600 mt-2">
          {t('pages.review.subtitle')}
        </p>
      </div>

      {/* Review Queue */}
      <div data-testid="review-queue">
        <ReviewQueue />
      </div>
    </div>
  );
};
