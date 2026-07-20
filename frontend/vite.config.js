/**
 * Vite Configuration for WikiEval Frontend
 *
 * This configuration sets up the Vue.js build process with Vite.
 * The build output will be in the 'dist' directory, which Flask will serve.
 */

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // Build configuration
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    // Generate source maps for debugging
    sourcemap: false,
    // Optimize for production
    minify: 'esbuild',
    // Rollup options
    rollupOptions: {
      output: {
        // Organize output files
        manualChunks: (id) => {
          if (id.includes('node_modules/vue') || id.includes('node_modules/vue-router')) {
            return 'vue-vendor'
          }
          if (id.includes('node_modules/axios')) {
            return 'axios-vendor'
          }
        }
      }
    }
  },
  // Development server configuration
  server: {
    port: 5173,
    proxy: {
      // Proxy API requests to Flask backend during development
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  },
  // Base path for production (empty for root)
  base: '/'
})

