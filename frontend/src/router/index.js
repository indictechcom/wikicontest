/**
 * Vue Router Configuration
 *
 * This file defines all routes for the WikiContest application.
 * Routes are protected based on authentication requirements.
 */

import { createRouter, createWebHistory } from 'vue-router'

// View components
import Home from '../views/Home.vue'
import Contests from '../views/Contests.vue'
import ContestView from '../views/ContestView.vue'
import Dashboard from '../views/Dashboard.vue'
import Profile from '../views/Profile.vue'
import TrustedMembers from '../views/TrustedMembers.vue'
import JuryDashboard from '../components/JuryDashboard.vue'
import ContestLeaderboard from '../components/ContestLeaderboard.vue'

// Store module reference for lazy loading to prevent circular dependencies
let storeModule = null

// Application route definitions
const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/contests',
    name: 'Contests',
    component: Contests,
    meta: { requiresAuth: true }
  },
  {
    path: '/contest/create',
    name: 'CreateContest',
    component: () => import('../views/CreateContest.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/contest/:name/edit',
    name: 'EditContest',
    component: () => import('../views/EditContest.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/contest/:name',
    name: 'ContestView',
    component: ContestView,
    meta: { requiresAuth: true }
  },
  {
    path: '/jurydashboard',
    name: 'JuryDashboard',
    component: JuryDashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: Profile,
    meta: { requiresAuth: true }
  },
  {
    path: '/trusted-members',
    name: 'TrustedMembers',
    component: TrustedMembers,
    meta: { requiresAuth: true }
  },
  {
    path: '/contest/:name/leaderboard',
    name: 'ContestLeaderboard',
    component: ContestLeaderboard,
    meta: { requiresAuth: true }
  },
  {
    // Redirect unknown routes to home page
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

// Initialize router with HTML5 history mode
const router = createRouter({
  history: createWebHistory(),
  routes
})

// Global navigation guard for authentication
router.beforeEach(async (to, from, next) => {
  // Lazy load store to prevent circular dependency issues
  if (!storeModule) {
    storeModule = await import('../store')
  }
  const { useStore } = storeModule
  const store = useStore()

  // Auth caching: if we checked auth within last 30 seconds, use cached result
  const NOW = Date.now()
  const AUTH_CACHE_TTL = 30 * 1000 // 30 seconds in milliseconds
  if (store.lastAuthCheck && (NOW - store.lastAuthCheck) < AUTH_CACHE_TTL) {
    // Use cached auth state
    const hasUserInStore = store.isAuthenticated && store.currentUser
    if (to.meta.requiresAuth && !hasUserInStore) {
      // Build API base URL based on environment
      const getApiBaseUrl = () => {
        if (import.meta.env.DEV) {
          return 'http://localhost:5000/api'
        }
        return '/api'
      }
      // Preserve intended destination for post-login redirect
      if (to.fullPath !== '/') {
        sessionStorage.setItem('oauth_redirect', to.fullPath)
      }
      // Redirect to MediaWiki OAuth login (full page navigation)
      window.location.href = `${getApiBaseUrl()}/user/oauth/login`
      // Cancel the router navigation since we're doing a full page redirect
      return next(false)
    }
    return next()
  }

  // Check if user data exists in store from recent login
  const hasUserInStore = store.isAuthenticated && store.currentUser

  // Verify authentication status with server
  let isAuthenticated = false
  try {
    isAuthenticated = await store.checkAuth()
  } catch (error) {
    // Fallback to store state if server check fails but user recently logged in
    if (hasUserInStore) {
      console.log('Auth check failed but user exists in store, using store state')
      isAuthenticated = true
    } else {
      isAuthenticated = false
    }
  }

  // Handle protected routes
  if (to.meta.requiresAuth && !isAuthenticated) {
    // Build API base URL based on environment
    const getApiBaseUrl = () => {
      if (import.meta.env.DEV) {
        return 'http://localhost:5000/api'
      }
      return '/api'
    }

    // Preserve intended destination for post-login redirect
    if (to.fullPath !== '/') {
      sessionStorage.setItem('oauth_redirect', to.fullPath)
    }

    // Redirect to MediaWiki OAuth login (full page navigation)
    window.location.href = `${getApiBaseUrl()}/user/oauth/login`
    // Cancel the router navigation since we're doing a full page redirect
    next(false)
  } else {
    // Allow navigation for authenticated users or public routes
    next()
  }
})

export default router
