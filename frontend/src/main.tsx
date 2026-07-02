import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import NestLayout from './components/NestLayout';
import App from './App';
import './styles/theme.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter basename="/dragons">
      <AuthProvider>
        <NestLayout>
          <App />
        </NestLayout>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
