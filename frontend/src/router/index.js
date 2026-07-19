/**
 * Vue Router Configuration
 *
 * This file defines all routes for the WikiEval application.
 * Routes are protected based on authentication requirements.
 */

import { createRouter, createWebHistory } from 'vue-router'

// View components
import Home from '../views/Home.vue'
import Contests from '../views/Contests.vue'
import ContestView from '../views/ContestView.vue'
import Profile from '../views/Profile.vue'
import TrustedMembers from '../views/TrustedMembers.vue'
import JuryDashboard from '../components/JuryDashboard.vue'
import ContestLeaderboard from '../components/ContestLeaderboard.vue'
import ContestSubmissionsView from '../views/ContestSubmissionsView.vue'

// Lazy-loaded views
const Dashboard = () => import('../views/Dashboard.vue')
const OrganizerDashboard = () => import('../views/OrganizerDashboard.vue')

// Store module reference for lazy loading to prevent circular dependencies
let storeModule = null

// Helper to build the OAuth login URL
function getLoginUrl() {
  const base = import.meta.env.DEV ? 'http://localhost:5000/api' : '/api'
  return `${base}/user/oauth/login`
}

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
    component: Contests
  },
  {
    path: '/contest/create',
    name: 'CreateContest',
    component: () => import('../views/CreateContest.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/contest/:contestId/edit',
    name: 'EditContest',
    component: () => import('../views/EditContest.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/contest/:contestId',
    name: 'ContestView',
    component: ContestView,
    meta: { requiresAuth: true }
  },
  {
    path: '/jurydashboard',
    redirect: '/jury/dashboard'
  },
  {
    path: '/my-contests',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/organizer/dashboard',
    name: 'OrganizerDashboard',
    component: OrganizerDashboard,
    meta: { requiresAuth: true, requiredRole: 'organizer' }
  },
  {
    path: '/jury/dashboard',
    name: 'JuryDashboard',
    component: JuryDashboard,
    meta: { requiresAuth: true, requiredRole: 'jury' }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: Profile,
    meta: { requiresAuth: true }
  },
  {
    path: '/trusted-members',
    redirect: '/manage-trusted-members'
  },
  {
    path: '/manage-trusted-members',
    name: 'TrustedMembers',
    component: TrustedMembers,
    meta: { requiresAuth: true }
  },
  {
    path: '/contest/:contestId/submissions',
    name: 'ContestSubmissions',
    component: ContestSubmissionsView,
    meta: { requiresAuth: true }
  },
  {
    path: '/contest/:contestId/leaderboard',
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

  // ── Step 1: Determine authentication status ──────────────────────
  // Use the reactive state directly to access lastAuthCheck
  const NOW = Date.now()
  const AUTH_CACHE_TTL = 5 * 1000 // 5 seconds
  const cachedAuth = store.state.lastAuthCheck
  const cacheValid = cachedAuth && (NOW - cachedAuth) < AUTH_CACHE_TTL

  let isAuthenticated = false

  if (cacheValid) {
    // Trust cached auth state — .value is required for ComputedRef
    isAuthenticated = store.isAuthenticated.value === true
  } else {
    // Verify authentication status with server
    try {
      isAuthenticated = await store.checkAuth()
    } catch (_err) {
      isAuthenticated = false
    }
  }

  // ── Step 2: Redirect unauthenticated users to login ──────────────
  if (to.meta.requiresAuth && !isAuthenticated) {
    if (to.fullPath !== '/') {
      sessionStorage.setItem('oauth_redirect', to.fullPath)
    }
    window.location.href = getLoginUrl()
    return next(false)
  }

  // ── Step 3: Enforce role-based access for dashboard routes ────────
  if (to.meta.requiredRole) {
    try {
      if (!store.state.dashboardAccessLoaded) {
        await store.loadDashboardAccess()
      }

      const access = store.dashboardAccess.value
      const role = to.meta.requiredRole
      const hasAccess =
        (role === 'organizer' && access?.organizer === true) ||
        (role === 'jury' && access?.jury === true)

      if (!hasAccess) {
        return next({ path: '/dashboard', replace: true })
      }
    } catch (_err) {
      // On error, allow navigation — the component can handle it
    }
  }

  // ── Step 4: Allow navigation ─────────────────────────────────────
  next()
})

export default router
