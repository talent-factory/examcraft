/**
 * Dashboard Page
 * Main dashboard with quick actions and statistics
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { QuickActionCard } from '../components/cards/QuickActionCard';
import { StatsCard } from '../components/cards/StatsCard';
import EmailVerificationBanner from '../components/auth/EmailVerificationBanner';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const { t } = useTranslation();

  return (
    <div className="space-y-8">
      {/* Email Verification Banner */}
      <EmailVerificationBanner />

      {/* Hero Section */}
      <div className="bg-gradient-to-r from-primary-600 to-secondary-600 rounded-lg p-8 text-white">
        <h1 className="text-4xl font-bold mb-2">
          {user?.first_name ? t('pages.dashboard.welcomeName', { name: user.first_name }) : t('pages.dashboard.welcome')}
        </h1>
        <p className="text-lg text-primary-100">
          {t('pages.dashboard.subtitle')}
        </p>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          {t('pages.dashboard.quickAccess')}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <QuickActionCard
            icon="📄"
            title={t('pages.dashboard.documents')}
            description={t('pages.dashboard.documentsDescription')}
            path="/documents"
            color="primary"
          />
          <QuickActionCard
            icon="✨"
            title={t('pages.dashboard.generateQuestions')}
            description={t('pages.dashboard.generateQuestionsDescription')}
            path="/questions/generate"
            color="secondary"
          />
          <QuickActionCard
            icon="✅"
            title={t('pages.dashboard.reviewQueue')}
            description={t('pages.dashboard.reviewQueueDescription')}
            path="/questions/review"
            color="success"
          />
          <QuickActionCard
            icon="📝"
            title={t('pages.dashboard.exams')}
            description={t('pages.dashboard.examsDescription')}
            path="/exams/compose"
            color="warning"
          />
        </div>
      </div>

      {/* Statistics */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          {t('pages.dashboard.statistics')}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsCard
            icon="📊"
            label={t('pages.dashboard.generatedQuestions')}
            value="0"
            color="primary"
          />
          <StatsCard
            icon="📚"
            label={t('pages.dashboard.documents')}
            value="0"
            color="secondary"
          />
          <StatsCard
            icon="✅"
            label={t('pages.dashboard.validatedQuestions')}
            value="0"
            color="success"
          />
          <StatsCard
            icon="📝"
            label={t('pages.dashboard.exams')}
            value="0"
            color="warning"
          />
        </div>
      </div>

      {/* Recent Activity */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          {t('pages.dashboard.recentActivity')}
        </h2>
        <div className="card p-6">
          <div className="text-center py-12">
            <p className="text-gray-500">
              {t('pages.dashboard.noActivity')}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
