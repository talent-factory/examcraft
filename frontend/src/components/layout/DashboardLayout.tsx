/**
 * Dashboard Layout Component
 * Main layout wrapper with NavigationBar and Sidebar for authenticated pages
 */

import React, { useEffect, useState } from 'react';
import { NavigationBar } from './NavigationBar';
import { Sidebar } from './Sidebar';
import { Footer } from './Footer';
import { ImpersonationBanner } from './ImpersonationBanner';
import { useAuth } from '../../contexts/AuthContext';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

const SIDEBAR_OPEN_STORAGE_KEY = 'examcraft.sidebar.isOpen';

// TF-819: some routes wrap AppLayout at a different depth (e.g. behind an
// extra PermissionGuard), so React remounts DashboardLayout on navigation
// between them — a plain useState(true) would silently reset the collapse
// state on every such navigation. Lazy-initializing from localStorage (same
// try/catch pattern as Sidebar.tsx's GROUPS_STORAGE_KEY) survives remounts.
const readStoredSidebarOpen = (): boolean => {
  try {
    const raw = window.localStorage.getItem(SIDEBAR_OPEN_STORAGE_KEY);
    return raw === null ? true : raw === 'true';
  } catch {
    return true;
  }
};

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(readStoredSidebarOpen);
  const { isImpersonating } = useAuth();

  useEffect(() => {
    try {
      window.localStorage.setItem(SIDEBAR_OPEN_STORAGE_KEY, String(sidebarOpen));
    } catch {
      /* localStorage unavailable (private mode / quota) — non-fatal. */
    }
  }, [sidebarOpen]);

  return (
    <div data-testid="dashboard-layout" className="min-h-screen bg-gray-50">
      {/* Impersonation Banner (TF-743) — sits above the NavigationBar while an admin is impersonating a user */}
      <ImpersonationBanner />

      {/* Navigation Bar */}
      <NavigationBar />

      {/* Main Content Area — offset for the fixed NavigationBar (h-16), plus
          the impersonation banner's own height (h-10) while it is shown. */}
      <div className={`flex ${isImpersonating ? 'pt-[104px]' : 'pt-16'}`}>
        {/* Sidebar */}
        <Sidebar isOpen={sidebarOpen} onToggle={setSidebarOpen} offsetForImpersonationBanner={isImpersonating} />

        {/* Content */}
        <main
          className={`flex-1 transition-all duration-250 ${
            sidebarOpen ? 'ml-sidebar' : 'ml-sidebar-collapsed'
          }`}
        >
          <div
            className={`max-w-7xl mx-auto py-6 sm:px-6 lg:px-8 ${
              isImpersonating ? 'min-h-[calc(100vh-6.5rem)]' : 'min-h-[calc(100vh-4rem)]'
            }`}
          >
            {children}
          </div>
        </main>
      </div>

      {/* Footer */}
      <div
        className={`transition-all duration-250 ${
          sidebarOpen ? 'ml-sidebar' : 'ml-sidebar-collapsed'
        }`}
      >
        <Footer />
      </div>
    </div>
  );
};
