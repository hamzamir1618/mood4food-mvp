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
    // 127.0.0.1, not localhost: Vite resolves localhost to ::1 here, where uvicorn isn't.
    proxy: Object.fromEntries(
      [
        '/submit',
        '/recalculate',
        '/decision_blueprint',
        '/alternate',
        '/health',
        '/personas',
        '/chat',
        '/approve',
        '/areas',
        '/auth',
        '/profile',
      ].map((path) => [path, 'http://127.0.0.1:8000']),
    ),
  },
});
