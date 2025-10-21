/**
 * App Layout Component
 * Main layout wrapper with navigation and sidebar for authenticated pages
 */

import React from 'react';
import { DashboardLayout } from './DashboardLayout';

interface AppLayoutProps {
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  return (
    <DashboardLayout>
      {children}
    </DashboardLayout>
  );
};

