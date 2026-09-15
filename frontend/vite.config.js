import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        styleguide: resolve(__dirname, 'styleguide.html'),
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/submit': 'http://localhost:8000',
      '/recalculate': 'http://localhost:8000',
      '/decision_blueprint': 'http://localhost:8000',
      '/alternate': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/personas': 'http://localhost:8000',
    },
  },
});
