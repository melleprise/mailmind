import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
// import path from 'path'; // No longer needed for basic alias
import { fileURLToPath, URL } from 'url'; // Use url module for ESM path handling

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: { // Add resolve configuration
    alias: {
      // Use import.meta.url for ESM-compatible path resolution
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: 8080,
    proxy: {
      // Proxy API requests
      '/api': {
        // Target the backend service name for API requests
        target: 'http://caddy:80',
        changeOrigin: true,
        secure: false, // If target is http
      },
      // Proxy WebSocket connections
      '/ws': {
        // Target the backend service name for WebSocket connections
        target: 'ws://caddy:80',
        ws: true, // Enable WebSocket proxying
        changeOrigin: true,
        secure: false, // If target is ws
      }
    }
  },
  // optimizeDeps: { // Temporär auskommentiert
  //   exclude: ['@rollup/rollup-linux-arm64-musl'],
  //   esbuildOptions: {
  //     target: 'esnext',
  //     supported: {
  //       'top-level-await': true
  //     }
  //   }
  // },
  build: {
    target: 'esnext',
    sourcemap: true
  },
  esbuild: {
    target: 'esnext',
    logOverride: { 'this-is-undefined-in-esm': 'silent' }
  },
  logLevel: 'info'
}); 