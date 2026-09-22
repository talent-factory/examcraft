import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import { AppWithAuth } from './AppWithAuth';
import { initErrorReporting } from './utils/errorReporting';
import { initSessionReplay } from './utils/sessionReplay';
import './i18n';

// Initialize client-side error reporting before rendering the app (TF-866)
initErrorReporting();
// Initialize session-replay recording before rendering the app (TF-867)
initSessionReplay();

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <AppWithAuth />
  </React.StrictMode>
);
