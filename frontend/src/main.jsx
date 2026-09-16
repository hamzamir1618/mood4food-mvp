import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ToastProvider } from './components/Toast.jsx';
import App from './App.jsx';

// Anton for the wordmark, Bodoni Moda for display, Libre Franklin for the UI.
import '@fontsource/anton/400.css';
import '@fontsource/bodoni-moda/400.css';
import '@fontsource/bodoni-moda/700.css';
import '@fontsource/bodoni-moda/900.css';
import '@fontsource/bodoni-moda/400-italic.css';
import '@fontsource/libre-franklin/400.css';
import '@fontsource/libre-franklin/500.css';
import '@fontsource/libre-franklin/600.css';
import '@fontsource/libre-franklin/700.css';

import './style.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ToastProvider>
      <App />
    </ToastProvider>
  </StrictMode>,
);
