import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import StyleGuide from './StyleGuide.jsx';

// ── All fonts (same imports as main.jsx) ──
import '@fontsource-variable/outfit';
import '@fontsource-variable/source-serif-4';
import '@fontsource/cinzel/400.css';
import '@fontsource/cinzel/700.css';
import '@fontsource/cinzel-decorative/400.css';
import '@fontsource/cinzel-decorative/700.css';
import '@fontsource-variable/noto-serif';
import '@fontsource-variable/playfair-display';
import '@fontsource/bebas-neue/400.css';
import '@fontsource-variable/fraunces';
import '@fontsource/almendra/400.css';

// ── Ornament styles ──
import './components/ornaments/ornaments.css';

createRoot(document.getElementById('styleguide-root')).render(
  <StrictMode>
    <StyleGuide />
  </StrictMode>
);
