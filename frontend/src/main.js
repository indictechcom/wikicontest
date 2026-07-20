/**
 * WikiEval Vue.js Application Entry Point
 *
 * This is the main entry point for the Vue.js application.
 * It initializes Vue, Vue Router, and mounts the app to the DOM.
 */

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { useStore } from './store'
import './style.css'
import { processOAuthCallback } from './utils/oauth'

// Create and mount the Vue application
const app = createApp(App)

// Use Vue Router for navigation
app.use(router)

// Wait for router to be ready before processing OAuth callback
router.isReady().then(() => {
  const store = useStore()
  // Handle OAuth redirect from Wikimedia login
  processOAuthCallback(store, router)
})

// Mount the app to the DOM
app.mount('#app')
