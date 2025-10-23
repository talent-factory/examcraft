import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import { AppWithAuth } from './AppWithAuth';
import { initSentry } from './config/sentry';

// Initialize Sentry before rendering the app
initSentry();

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <AppWithAuth />
  </React.StrictMode>
);
