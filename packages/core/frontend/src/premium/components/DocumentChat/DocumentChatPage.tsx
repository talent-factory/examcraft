/**
 * Premium DocumentChat Stub
 *
 * This file serves as a stub for the Premium DocumentChat component.
 * In Full deployment mode, this will be replaced by the actual Premium implementation
 * via symlink or build process.
 *
 * In Core deployment mode, this returns null (component should never be loaded
 * because RBAC checks prevent access).
 */

import React from 'react';

/**
 * Stub component - should be replaced in Full deployment
 */
export const DocumentChatPage: React.FC = () => {
  // This stub should never be rendered in production
  // The Core DocumentChatPage only loads this when:
  // 1. User has document_chatbot permission (Professional/Enterprise)
  // 2. isFullDeployment() returns true
  //
  // In Core deployment, isFullDeployment() returns false, so this won't load.
  // In Full deployment, this file should be symlinked to the real Premium component.

  console.error('Premium DocumentChatPage stub was loaded - this should not happen!');
  console.error('Please check deployment configuration (REACT_APP_DEPLOYMENT_MODE)');

  return (
    <div style={{ padding: '20px', textAlign: 'center' }}>
      <h2>Configuration Error</h2>
      <p>Premium component not available. Please contact your administrator.</p>
    </div>
  );
};

export default DocumentChatPage;
