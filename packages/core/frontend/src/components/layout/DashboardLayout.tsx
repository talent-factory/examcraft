/**
 * Dashboard Layout Component
 * Main layout wrapper with NavigationBar and Sidebar for authenticated pages
 */

import React, { useState } from 'react';
import { NavigationBar } from './NavigationBar';
import { Sidebar } from './Sidebar';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation Bar */}
      <NavigationBar />

      {/* Main Content Area */}
      <div className="flex pt-16">
        {/* Sidebar */}
        <Sidebar isOpen={sidebarOpen} onToggle={setSidebarOpen} />

        {/* Content */}
        <main
          className={`flex-1 transition-all duration-250 ${
            sidebarOpen ? 'ml-sidebar' : 'ml-sidebar-collapsed'
          }`}
        >
          <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};
