import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import NestLayout from './components/NestLayout';
import ErrorBoundary from './components/ErrorBoundary';
import DiagnosticOverlay, { diagMark } from './components/DiagnosticOverlay';
import App from './App';
import './styles/theme.css';

diagMark('01 main.tsx загрузился', 'ok');

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter basename="/dragons">
        <AuthProvider>
          <NestLayout>
            <App />
          </NestLayout>
        </AuthProvider>
      </BrowserRouter>
      <DiagnosticOverlay />
    </ErrorBoundary>
  </React.StrictMode>,
);
