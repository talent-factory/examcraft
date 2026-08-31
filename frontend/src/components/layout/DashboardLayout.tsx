/**
 * Dashboard Layout Component
 * Main layout wrapper with NavigationBar and Sidebar for authenticated pages
 */

import React, { useState } from 'react';
import { NavigationBar } from './NavigationBar';
import { Sidebar } from './Sidebar';
import { Footer } from './Footer';
import { ImpersonationBanner } from './ImpersonationBanner';
import { useAuth } from '../../contexts/AuthContext';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { isImpersonating } = useAuth();

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
