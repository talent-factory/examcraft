/**
 * App Component - LEGACY
 *
 * This component is deprecated and kept for backward compatibility only.
 * All features have been migrated to the new DashboardLayout with feature-specific pages:
 * - /dashboard → Dashboard
 * - /documents → Documents (DocumentUpload + DocumentLibrary)
 * - /questions/generate → Exams (RAGExamCreator)
 * - /questions/review → Review (ReviewQueue)
 * - /admin → Admin (PromptManagement + UserManagement)
 *
 * Please use the new routing structure in AppWithAuth.tsx instead.
 */

import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Create a QueryClient instance for TanStack Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

/**
 * Legacy App Component
 * This is a fallback component that should not be used directly.
 * Use the new routing structure instead.
 */
function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="card max-w-md w-full p-8 text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Legacy Component
          </h1>
          <p className="text-gray-600 mb-6">
            This component is deprecated. Please use the new dashboard navigation instead.
          </p>
          <a
            href="/dashboard"
            className="btn btn-primary inline-block"
          >
            Go to Dashboard
          </a>
        </div>
      </div>
    </QueryClientProvider>
  );
}

export default App;
