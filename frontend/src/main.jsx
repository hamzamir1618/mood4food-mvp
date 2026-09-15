import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ToastProvider } from './components/Toast.jsx';
import App from './App.jsx';
import '@fontsource-variable/outfit'; // Self-hosted Outfit (wght 100-900) — logo wordmark, UI labels

// ── Tier 1: Workhorse serif (all functional UI text) ──
import '@fontsource-variable/source-serif-4'; // Source Serif 4 (wght 200-900) — body, prices, buttons, nav

// ── Tier 2: Cuisine display fonts (dish names, cuisine headers only) ──
import '@fontsource/cinzel/400.css';           // Desi + Middle Eastern — ornamental old-world formal
import '@fontsource/cinzel/700.css';
import '@fontsource/cinzel-decorative/400.css'; // Middle Eastern alt — Ottoman-court elegance
import '@fontsource/cinzel-decorative/700.css';
import '@fontsource-variable/noto-serif';       // Chinese/Asian — legitimate high-contrast serif
import '@fontsource-variable/playfair-display'; // Continental — classic Didone fine-dining
import '@fontsource/bebas-neue/400.css';        // Fast Food — bold punchy condensed
import '@fontsource-variable/fraunces';         // Café/Bakery — warm soft contemporary
import '@fontsource/almendra/400.css';          // Desi alt — ornamental, calligraphic

import './style.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ToastProvider>
      <App />
    </ToastProvider>
  </StrictMode>
);
