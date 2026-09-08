/**
 * Admin Page
 * Admin panel with RBAC-controlled navigation (TF-799).
 *
 * Institution-scoped and platform-scoped ("Super-Admin") functions are kept
 * visually and structurally separate: a categorized sub-navigation (left
 * rail on desktop, stacked above the content on mobile) replaces the old
 * single-row tab bar (which overflowed once the page grew past ~7 tabs), and
 * superusers additionally get a scope switcher next to the page title to
 * move between "my institution" and "platform (all institutions)".
 * Switching into platform scope shows a page-local banner — deliberately NOT
 * the app-wide fixed ImpersonationBanner mechanism (that would mean touching
 * DashboardLayout/NavigationBar/Sidebar's hardcoded offsets for a change
 * that only concerns this page).
 */

import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Building2, Check, ChevronDown, ShieldCheck } from 'lucide-react';
import { UserManagementPage } from '../components/admin/UserManagementPage';
import { InstitutionManagementPage } from '../components/admin/InstitutionManagementPage';
import AdminRoles from './AdminRoles';
import SubscriptionTierOverview from '../components/admin/SubscriptionTierOverview';
import HelpFeedbackQueue from '../components/admin/HelpFeedbackQueue';
import TagSettingsPage from './TagSettingsPage';
import CompetencyFrameworkSettingsPage from './CompetencyFrameworkSettingsPage';
import { useAuth } from '../contexts/AuthContext';
import { UserRole } from '../types/auth';
import AdminGradingSchemes from './AdminGradingSchemes';
import AdminOrgUnits from './AdminOrgUnits';
import AuditLogView from '../components/admin/AuditLogView';
import SystemHealthPanel from '../components/admin/SystemHealthPanel';
import OpsChatWidget from '../components/admin/OpsChatWidget';
import { isFullDeployment } from '../utils/deploymentMode';

type AdminTab = 'users' | 'institutions' | 'roles' | 'audit' | 'subscription' | 'help-feedback' | 'tags' | 'competency-frameworks' | 'grading-schemes' | 'org-units' | 'system-health';
type AdminScope = 'institution' | 'platform';

// Closed set of sidebar section ids. Kept as a literal union (rather than
// grouping tabs by their translated label string) so a typo'd or duplicated
// assignment is a compile error, and so a missing translation degrades to a
// harmless fallback label instead of silently merging two categories under
// one heading — see categoryLabels below for the id → translated-label map.
type AdminCategoryId = 'userAccess' | 'organization' | 'contentEvaluation' | 'billingCompliance' | 'tenants' | 'security' | 'system' | 'support';

interface TabConfig {
  key: AdminTab;
  label: string;
  visible: boolean;
  scope: AdminScope;
  categoryId: AdminCategoryId;
}

interface TabGroup {
  categoryId: AdminCategoryId;
  tabs: TabConfig[];
}

const groupByCategory = (tabs: TabConfig[]): TabGroup[] =>
  tabs.reduce<TabGroup[]>((groups, tab) => {
    const existing = groups.find((group) => group.categoryId === tab.categoryId);
    if (existing) {
      existing.tabs.push(tab);
    } else {
      groups.push({ categoryId: tab.categoryId, tabs: [tab] });
    }
    return groups;
  }, []);

// The onboarding tour (help-onboarding-steps.json, track "admin-benutzer")
// highlights the scope-switcher menu and its "platform" option and waits for
// a real click on them; its own popover controls (Next/close) render outside
// this page's DOM subtree (see HelpOnboarding.tsx). Any outside-click-to-close
// handling on the switcher menu must not treat a click on that popover as
// "outside", or the tour's own "Next" click would close the menu before the
// next step's target (`admin-scope-option-platform`) can be found in the DOM.
const TOUR_POPOVER_SELECTOR = '[data-testid="onboarding-popover"]';

export const Admin: React.FC = () => {
  const { user, hasRole, hasPermission } = useAuth();
  const { t } = useTranslation();
  const isSuperuser = user?.is_superuser ?? false;
  const isAdmin = isSuperuser || hasRole(UserRole.ADMIN);
  const canManageGradingSchemes = hasPermission('grading_schemes:manage');
  const canManageOrgUnits = hasPermission('manage_org_units');
  // GET /api/v1/ops/health is only registered in Full deployment (it probes
  // Fly/RabbitMQ/Celery, which don't exist in Core) — hide the tab in Core
  // instead of showing a permanently-erroring, endlessly-polling panel.
  const showSystemHealth = isSuperuser && isFullDeployment();

  const categoryLabels: Record<AdminCategoryId, string> = {
    userAccess: t('pages.admin.categories.userAccess', 'Benutzer & Zugriff'),
    organization: t('pages.admin.categories.organization', 'Organisation'),
    contentEvaluation: t('pages.admin.categories.contentEvaluation', 'Inhalte & Bewertung'),
    billingCompliance: t('pages.admin.categories.billingCompliance', 'Abrechnung & Compliance'),
    tenants: t('pages.admin.categories.tenants', 'Mandanten'),
    security: t('pages.admin.categories.security', 'Sicherheit'),
    system: t('pages.admin.categories.system', 'System'),
    support: t('pages.admin.categories.support', 'Support'),
  };

  const tabs: TabConfig[] = [
    { key: 'users', label: t('pages.admin.tabUsers'), visible: true, scope: 'institution', categoryId: 'userAccess' },
    { key: 'org-units', label: t('pages.admin.tabOrgUnits'), visible: canManageOrgUnits, scope: 'institution', categoryId: 'organization' },
    { key: 'tags', label: t('nav.sidebar.tagSettings', 'Tag-Verwaltung'), visible: isAdmin, scope: 'institution', categoryId: 'contentEvaluation' },
    { key: 'competency-frameworks', label: t('nav.sidebar.competencyFrameworks', 'Kompetenzrahmen'), visible: isAdmin, scope: 'institution', categoryId: 'contentEvaluation' },
    { key: 'grading-schemes', label: t('pages.admin.tabGradingSchemes'), visible: canManageGradingSchemes, scope: 'institution', categoryId: 'contentEvaluation' },
    { key: 'subscription', label: t('pages.admin.tabSubscription'), visible: isAdmin, scope: 'institution', categoryId: 'billingCompliance' },
    { key: 'audit', label: t('pages.admin.tabAudit'), visible: isAdmin, scope: 'institution', categoryId: 'billingCompliance' },
    { key: 'institutions', label: t('pages.admin.tabInstitutions'), visible: isSuperuser, scope: 'platform', categoryId: 'tenants' },
    { key: 'roles', label: t('pages.admin.tabRoles'), visible: isSuperuser, scope: 'platform', categoryId: 'security' },
    { key: 'system-health', label: t('pages.admin.tabSystemHealth'), visible: showSystemHealth, scope: 'platform', categoryId: 'system' },
    { key: 'help-feedback', label: 'Help Feedback', visible: isSuperuser, scope: 'platform', categoryId: 'support' },
  ].filter((tab): tab is TabConfig => tab.visible);

  const institutionTabs = tabs.filter((tab) => tab.scope === 'institution');
  const platformTabs = tabs.filter((tab) => tab.scope === 'platform');
  // Defensive only — not reachable today: institutions/roles/help-feedback
  // are all unconditionally visible for any superuser, so platformTabs is
  // never actually empty. Kept in case a future platform tab gets gated
  // behind an extra permission (the way institution-scope tabs like
  // audit/tags already are via isAdmin), which would make this guard
  // meaningful.
  const hasPlatformScope = isSuperuser && platformTabs.length > 0;

  const [scope, setScope] = useState<AdminScope>('institution');
  const [switcherOpen, setSwitcherOpen] = useState(false);
  const switcherRef = useRef<HTMLDivElement>(null);
  const effectiveScope: AdminScope = hasPlatformScope && scope === 'platform' ? 'platform' : 'institution';
  const visibleTabs = effectiveScope === 'platform' ? platformTabs : institutionTabs;
  const groupedTabs = groupByCategory(visibleTabs);

  const [activeTab, setActiveTab] = useState<AdminTab>(visibleTabs[0]?.key ?? 'users');
  const effectiveTab = visibleTabs.some((tab) => tab.key === activeTab)
    ? activeTab
    : (visibleTabs[0]?.key ?? 'users');

  // Remembers which tab was active in each scope, so a superuser who peeks at
  // platform scope and returns lands back where they left off in their
  // institution (rather than always resetting to the first tab).
  const lastTabByScopeRef = useRef<Partial<Record<AdminScope, AdminTab>>>({});

  useEffect(() => {
    if (!switcherOpen) return undefined;
    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if ((target as Element)?.closest?.(TOUR_POPOVER_SELECTOR)) return;
      if (switcherRef.current && !switcherRef.current.contains(target)) {
        setSwitcherOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setSwitcherOpen(false);
      }
    };
    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [switcherOpen]);

  const institutionName = user?.institution?.name;
  const institutionDisplayName = institutionName
    ?? t('pages.admin.scopeSwitcher.myInstitutionFallback', 'Meine Institution');

  const handleScopeChange = (nextScope: AdminScope) => {
    setSwitcherOpen(false);
    if (nextScope === effectiveScope) return;

    lastTabByScopeRef.current[effectiveScope] = activeTab;
    setScope(nextScope);

    const nextTabs = nextScope === 'platform' ? platformTabs : institutionTabs;
    const remembered = lastTabByScopeRef.current[nextScope];
    const target = remembered && nextTabs.some((tab) => tab.key === remembered)
      ? remembered
      : nextTabs[0]?.key;
    if (target && target !== activeTab) {
      setActiveTab(target);
    }
  };

  return (
    <div className="space-y-6">
      {effectiveScope === 'platform' && (
        <div
          data-testid="admin-platform-banner"
          className="flex items-center justify-between gap-3 px-4 py-2.5 rounded-lg bg-secondary-700 text-white text-sm"
        >
          <span className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
            {t('pages.admin.platformBanner.text', 'Plattform-Modus aktiv — Änderungen betreffen alle Institutionen')}
          </span>
          <button
            type="button"
            data-testid="admin-platform-banner-exit"
            onClick={() => handleScopeChange('institution')}
            className="flex-shrink-0 px-3 py-1 rounded-full bg-white/15 hover:bg-white/25 transition-colors font-medium"
          >
            {institutionName
              ? t('pages.admin.platformBanner.exit', { defaultValue: 'Zurück zu {{institution}}', institution: institutionName })
              : t('pages.admin.platformBanner.exitFallback', 'Zurück zur eigenen Institution')}
          </button>
        </div>
      )}

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{t('pages.admin.title')}</h1>
          <p className="text-gray-600 mt-2">
            {effectiveScope === 'platform'
              ? t('pages.admin.subtitlePlatform', 'Plattformweite Einstellungen für alle Institutionen')
              : t('pages.admin.subtitle')}
          </p>
        </div>

        {hasPlatformScope && (
          <div className="relative" ref={switcherRef}>
            <button
              type="button"
              data-testid="admin-scope-switcher-toggle"
              onClick={() => setSwitcherOpen((open) => !open)}
              aria-haspopup="menu"
              aria-expanded={switcherOpen}
              aria-describedby="admin-scope-switcher-hint"
              className={`flex items-center gap-2 px-3.5 py-2 rounded-full border text-sm font-semibold transition-colors ${
                effectiveScope === 'platform'
                  ? 'bg-secondary-100 border-secondary-200 text-secondary-700'
                  : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              {effectiveScope === 'platform' ? (
                <ShieldCheck className="w-4 h-4" aria-hidden="true" />
              ) : (
                <Building2 className="w-4 h-4" aria-hidden="true" />
              )}
              {effectiveScope === 'platform'
                ? t('pages.admin.scopeSwitcher.platform', 'Plattform (alle Institutionen)')
                : institutionDisplayName}
              <ChevronDown className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
            <span id="admin-scope-switcher-hint" className="sr-only">
              {t('pages.admin.scopeSwitcher.ariaLabel', 'Verwaltungsbereich wechseln')}
            </span>

            {switcherOpen && (
              <div
                role="menu"
                aria-label={t('pages.admin.scopeSwitcher.ariaLabel', 'Verwaltungsbereich wechseln')}
                data-testid="admin-scope-switcher-menu"
                className="absolute right-0 mt-2 w-72 bg-white border border-gray-200 rounded-lg shadow-lg p-2 z-20"
              >
                <div role="group" aria-labelledby="admin-scope-group-institution">
                  <div
                    id="admin-scope-group-institution"
                    className="px-2.5 pt-1.5 pb-1 text-xs font-semibold uppercase tracking-wider text-gray-400"
                  >
                    {t('pages.admin.scopeSwitcher.myInstitutionGroup', 'Meine Institution')}
                  </div>
                  <button
                    type="button"
                    role="menuitemradio"
                    aria-checked={effectiveScope === 'institution'}
                    data-testid="admin-scope-option-institution"
                    onClick={() => handleScopeChange('institution')}
                    className={`w-full flex items-center justify-between gap-2 px-2.5 py-2 rounded-lg text-sm transition-colors ${
                      effectiveScope === 'institution'
                        ? 'bg-gray-100 text-gray-900 font-medium'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <Building2 className="w-4 h-4" aria-hidden="true" />
                      {institutionDisplayName}
                    </span>
                    {effectiveScope === 'institution' && <Check className="w-4 h-4 text-primary-600" aria-hidden="true" />}
                  </button>
                </div>

                <div className="h-px bg-gray-200 my-1.5 mx-1" aria-hidden="true" />

                <div role="group" aria-labelledby="admin-scope-group-platform">
                  <div
                    id="admin-scope-group-platform"
                    className="px-2.5 pt-1 pb-1 text-xs font-semibold uppercase tracking-wider text-gray-400"
                  >
                    {t('pages.admin.scopeSwitcher.superAdminLabel', 'Super-Admin')}
                  </div>
                  <button
                    type="button"
                    role="menuitemradio"
                    aria-checked={effectiveScope === 'platform'}
                    data-testid="admin-scope-option-platform"
                    onClick={() => handleScopeChange('platform')}
                    className="w-full flex items-center justify-between gap-2 px-2.5 py-2 rounded-lg text-sm text-secondary-700 hover:bg-secondary-50 transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4" aria-hidden="true" />
                      {t('pages.admin.scopeSwitcher.platform', 'Plattform (alle Institutionen)')}
                    </span>
                    {effectiveScope === 'platform' && <Check className="w-4 h-4 text-secondary-700" aria-hidden="true" />}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex flex-col md:flex-row items-start gap-6">
        <nav
          data-testid="admin-category-nav"
          aria-label={t('pages.admin.title')}
          className="w-full md:w-60 md:flex-shrink-0 bg-white border border-gray-200 rounded-lg p-2"
        >
          {groupedTabs.map((group) => (
            <div key={group.categoryId} className="mb-1 last:mb-0">
              <div className="px-2.5 pt-2 pb-1 text-xs font-semibold uppercase tracking-wider text-gray-400">
                {categoryLabels[group.categoryId]}
              </div>
              {group.tabs.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  data-testid={`admin-tab-btn-${tab.key}`}
                  onClick={() => setActiveTab(tab.key)}
                  aria-current={effectiveTab === tab.key ? 'page' : undefined}
                  className={`w-full flex items-center px-2.5 py-2 rounded-lg text-sm text-left transition-colors ${
                    effectiveTab === tab.key
                      ? 'bg-primary-100 text-primary-700 font-medium'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="card p-6 flex-1 min-w-0 w-full">
          {effectiveTab === 'users' && (
            <div data-testid="admin-tab-content-users">
              <UserManagementPage />
            </div>
          )}
          {effectiveTab === 'institutions' && (
            <div data-testid="admin-tab-content-institutions">
              <InstitutionManagementPage />
            </div>
          )}
          {effectiveTab === 'roles' && (
            <div data-testid="admin-tab-content-roles">
              <AdminRoles />
            </div>
          )}
          {effectiveTab === 'system-health' && (
            <div data-testid="admin-tab-content-system-health">
              <SystemHealthPanel />
              <OpsChatWidget />
            </div>
          )}
          {effectiveTab === 'audit' && (
            <div data-testid="admin-tab-content-audit">
              <AuditLogView isSuperuser={isSuperuser} />
            </div>
          )}
          {effectiveTab === 'subscription' && (
            <div data-testid="admin-tab-content-subscription">
              <SubscriptionTierOverview />
            </div>
          )}
          {effectiveTab === 'tags' && (
            <div data-testid="admin-tab-content-tags">
              <TagSettingsPage />
            </div>
          )}
          {effectiveTab === 'competency-frameworks' && (
            <div data-testid="admin-tab-content-competency-frameworks">
              <CompetencyFrameworkSettingsPage />
            </div>
          )}
          {effectiveTab === 'grading-schemes' && (
            <div data-testid="admin-tab-content-grading-schemes">
              <AdminGradingSchemes />
            </div>
          )}
          {effectiveTab === 'org-units' && (
            <div data-testid="admin-tab-content-org-units">
              <AdminOrgUnits />
            </div>
          )}
          {effectiveTab === 'help-feedback' && (
            <div data-testid="admin-tab-content-help-feedback">
              <HelpFeedbackQueue />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
