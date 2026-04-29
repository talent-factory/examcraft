/**
 * Dashboard Page
 * Main dashboard with quick actions, real statistics and activity feed (TF-319)
 */

import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { formatDistanceToNow } from 'date-fns';
import { de, enUS, fr, it } from 'date-fns/locale';
import { useAuth } from '../contexts/AuthContext';
import { QuickActionCard } from '../components/cards/QuickActionCard';
import { StatsCard } from '../components/cards/StatsCard';
import EmailVerificationBanner from '../components/auth/EmailVerificationBanner';
import {
  fetchDashboardStats,
  fetchDashboardActivity,
  DashboardStatsResponse,
  ActivityItem,
} from '../api/dashboard';

const DATE_FNS_LOCALES: Record<string, Locale> = { de, en: enUS, fr, it };

const ACTIVITY_ICONS: Record<string, string> = {
  document_uploaded: '📄',
  document_deleted: '🗑️',
  questions_generated: '✨',
  exam_created: '📝',
  question_approved: '✅',
  question_rejected: '❌',
  exam_deleted: '🗑️',
};

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const { t, i18n } = useTranslation();

  const [stats, setStats] = useState<DashboardStatsResponse | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState(false);

  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [activitiesLoading, setActivitiesLoading] = useState(true);
  const [activitiesError, setActivitiesError] = useState(false);

  useEffect(() => {
    let cancelled = false;

    fetchDashboardStats()
      .then((data) => { if (!cancelled) setStats(data); })
      .catch(() => { if (!cancelled) setStatsError(true); })
      .finally(() => { if (!cancelled) setStatsLoading(false); });

    fetchDashboardActivity()
      .then((data) => { if (!cancelled) setActivities(data.activities); })
      .catch(() => { if (!cancelled) setActivitiesError(true); })
      .finally(() => { if (!cancelled) setActivitiesLoading(false); });

    return () => { cancelled = true; };
  }, []);

  const locale = DATE_FNS_LOCALES[i18n.language?.substring(0, 2)] ?? de;

  const formatRelativeDate = (timestamp: string) =>
    formatDistanceToNow(new Date(timestamp), { addSuffix: true, locale });

  return (
    <div data-testid="dashboard-content" className="space-y-8">
      <EmailVerificationBanner />

      {/* Hero Section */}
      <div className="bg-gradient-to-r from-primary-600 to-secondary-600 rounded-lg p-8 text-white">
        <h1 className="text-4xl font-bold mb-2">
          {user?.first_name
            ? t('pages.dashboard.welcomeName', { name: user.first_name })
            : t('pages.dashboard.welcome')}
        </h1>
        <p className="text-lg text-primary-100">{t('pages.dashboard.subtitle')}</p>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          {t('pages.dashboard.quickAccess')}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <QuickActionCard icon="📄" title={t('pages.dashboard.documents')} description={t('pages.dashboard.documentsDescription')} path="/documents" color="primary" />
          <QuickActionCard icon="✨" title={t('pages.dashboard.generateQuestions')} description={t('pages.dashboard.generateQuestionsDescription')} path="/questions/generate" color="secondary" />
          <QuickActionCard icon="✅" title={t('pages.dashboard.reviewQueue')} description={t('pages.dashboard.reviewQueueDescription')} path="/questions/review" color="success" />
          <QuickActionCard icon="📝" title={t('pages.dashboard.exams')} description={t('pages.dashboard.examsDescription')} path="/exams/compose" color="warning" />
        </div>
      </div>

      {/* Statistics */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          {t('pages.dashboard.statistics')}
        </h2>
        {statsError && (
          <p className="text-sm text-red-500 mb-2">{t('pages.dashboard.statsError')}</p>
        )}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsCard icon="📊" label={t('pages.dashboard.generatedQuestions')} value={statsLoading ? '…' : String(stats?.generated_questions ?? 0)} color="primary" />
          <StatsCard icon="📚" label={t('pages.dashboard.documents')} value={statsLoading ? '…' : String(stats?.documents ?? 0)} color="secondary" />
          <StatsCard icon="✅" label={t('pages.dashboard.validatedQuestions')} value={statsLoading ? '…' : String(stats?.validated_questions ?? 0)} color="success" />
          <StatsCard icon="📝" label={t('pages.dashboard.exams')} value={statsLoading ? '…' : String(stats?.exams ?? 0)} color="warning" />
        </div>
      </div>

      {/* Recent Activity */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          {t('pages.dashboard.recentActivity')}
        </h2>
        <div className="card p-6">
          {activitiesLoading ? (
            <div className="text-center py-12">
              <p className="text-gray-400">…</p>
            </div>
          ) : activitiesError ? (
            <p className="text-sm text-red-500 text-center py-4">
              {t('pages.dashboard.activityError')}
            </p>
          ) : activities.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500">{t('pages.dashboard.noActivity')}</p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {activities.map((item) => (
                <li key={item.id} className="flex items-center gap-4 py-3">
                  <span className="text-2xl">{ACTIVITY_ICONS[item.type] ?? '🔔'}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{item.title}</p>
                    <p className="text-xs text-gray-500">
                      {t(`pages.dashboard.activityTypes.${item.type}`)}
                    </p>
                  </div>
                  <span className="text-xs text-gray-400 whitespace-nowrap">
                    {formatRelativeDate(item.timestamp)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
};
