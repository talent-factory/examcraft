/**
 * Dashboard Page
 * Main dashboard with quick actions and statistics
 */

import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { QuickActionCard } from '../components/cards/QuickActionCard';
import { StatsCard } from '../components/cards/StatsCard';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-primary-600 to-secondary-600 rounded-lg p-8 text-white">
        <h1 className="text-4xl font-bold mb-2">
          Willkommen{user?.first_name ? `, ${user.first_name}` : ''}! 👋
        </h1>
        <p className="text-lg text-primary-100">
          Erstelle intelligente Prüfungsaufgaben mit KI-Unterstützung
        </p>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Schnellzugriff
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <QuickActionCard
            icon="📄"
            title="Dokumente"
            description="Lade Lehrmaterialien hoch und verwalte deine Dokumentenbibliothek"
            path="/documents"
            color="primary"
          />
          <QuickActionCard
            icon="✨"
            title="Fragen generieren"
            description="Erstelle automatisch Prüfungsfragen mit KI"
            path="/questions/generate"
            color="secondary"
          />
          <QuickActionCard
            icon="✅"
            title="Review Queue"
            description="Überprüfe und validiere generierte Fragen"
            path="/questions/review"
            color="success"
          />
          <QuickActionCard
            icon="📝"
            title="Prüfungen"
            description="Komponiere und exportiere Prüfungen"
            path="/exams/compose"
            color="warning"
          />
        </div>
      </div>

      {/* Statistics */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Statistiken
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsCard
            icon="📊"
            label="Generierte Fragen"
            value="0"
            color="primary"
          />
          <StatsCard
            icon="📚"
            label="Dokumente"
            value="0"
            color="secondary"
          />
          <StatsCard
            icon="✅"
            label="Validierte Fragen"
            value="0"
            color="success"
          />
          <StatsCard
            icon="📝"
            label="Prüfungen"
            value="0"
            color="warning"
          />
        </div>
      </div>

      {/* Recent Activity */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Letzte Aktivitäten
        </h2>
        <div className="card p-6">
          <div className="text-center py-12">
            <p className="text-gray-500">
              Keine Aktivitäten vorhanden. Starten Sie mit dem Hochladen von Dokumenten!
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
