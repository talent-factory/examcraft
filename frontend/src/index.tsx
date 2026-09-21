import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import { AppWithAuth } from './AppWithAuth';
import { initErrorReporting } from './utils/errorReporting';
import './i18n';

// Initialize client-side error reporting before rendering the app (TF-866)
initErrorReporting();

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <AppWithAuth />
  </React.StrictMode>
);
