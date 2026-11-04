import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import './styles.css';
import { AuthProvider } from './auth';
import { UiProvider } from './ui';
import App from './App';
import ErrorBoundary from './ErrorBoundary';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <UiProvider>
        <AuthProvider>
          <ErrorBoundary><App /></ErrorBoundary>
        </AuthProvider>
      </UiProvider>
    </BrowserRouter>
  </StrictMode>,
);
