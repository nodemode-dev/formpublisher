import { defineConfig } from 'vite';

const FRONTEND_PORT = 5280;
const PREVIEW_PORT = 5281;
const BACKEND_PORT = 8280;
const engine = { target: `http://127.0.0.1:${BACKEND_PORT}`, changeOrigin: true, ws: true };

export default defineConfig({
  root: '.',
  publicDir: 'public',
  server: {
    fs: { allow: ['..'] },
    port: FRONTEND_PORT,
    host: false,
    strictPort: true,
    proxy: { '/api': engine },
  },
  preview: {
    port: PREVIEW_PORT,
    host: false,
    strictPort: true,
    proxy: { '/api': engine },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    target: 'es2022',
    chunkSizeWarningLimit: 1600,
  },
});
