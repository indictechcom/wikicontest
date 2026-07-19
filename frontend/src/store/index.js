/**
 * Composable Store for WikiContest Application
 *
 * This composable manages global application state including:
 * - User authentication
 * - Contest data
 * - UI state
 *
 * Uses Vue 3 Composition API with reactive state management.
 */

import { reactive, computed } from 'vue'
import api from '../services/api'

// Global state (reactive object)
const state = reactive({
  // Current authenticated user
  currentUser: null,
  // Timestamp of last auth check (for caching)
  lastAuthCheck: 0,
  // Contest data cache
  contests: {
    current: [],
    upcoming: [],
    past: []
  },
  // Loading states
  loading: {
    contests: false,
    dashboard: false
  },
  // Dashboard access permissions
  dashboardAccess: {
    participant: true,
    organizer: false,
    jury: false
  },
  dashboardAccessLoaded: false,
  // Theme state - default to light mode, or load from localStorage
  theme: localStorage.getItem('theme') || 'light'
})

// Store composable function
export function useStore() {
  // Computed properties
  const isAuthenticated = computed(() => !!state.currentUser)
  const currentUser = computed(() => state.currentUser)
  const contests = computed(() => state.contests)

  // Check if user is authenticated
  const checkAuth = async () => {
    try {
      console.log(' Checking authentication...')
      const response = await api.get('/cookie')
      console.log(' Auth API response:', response)
      console.log(' Response role value:', response?.role)
      console.log(' Response role type:', typeof response?.role)

      // Double-check response is valid and has required fields
      // Must have userId and it must be a valid number > 0
      if (response && response.userId && typeof response.userId === 'number' && response.userId > 0) {
        // Ensure username and email are set (handle cases where they might be missing)
        // IMPORTANT: Use the role from response, but ensure it's a string and lowercase
        const roleFromResponse = response.role
        console.log(' Role from response (raw):', roleFromResponse)

        // Normalize role: convert to string, lowercase, and default to 'user' if missing/null/undefined
        let normalizedRole = 'user'
        if (roleFromResponse) {
          normalizedRole = String(roleFromResponse).toLowerCase().trim()
          // CRITICAL: Don't override if role is explicitly 'superadmin'
          if (normalizedRole === 'superadmin') {
            console.log(' [ROLE] Detected superadmin role - preserving it')
          }
        }
        console.log(' Normalized role:', normalizedRole)
        console.log(' Role comparison - normalizedRole === "superadmin":', normalizedRole === 'superadmin')

        const newUser = {
          id: response.userId,
          username: response.username || response.email || 'User',
          email: response.email || '',
          // Store role from backend so we can detect admin / superadmin in UI.
          // Use normalized role to ensure consistency
          role: normalizedRole,
          // Include trusted member status to check if user can create contests
          is_trusted_member: response.is_trusted_member || false,
          // Include trusted member request status
          trusted_member_request: response.trusted_member_request || false,
          trusted_member_request_status: response.trusted_member_request_status || null
        }

        console.log(' Setting current user:', newUser)
        console.log(' User role being stored:', newUser.role)
        state.currentUser = newUser
        console.log(' Current user set. State:', state.currentUser)
        // Update last auth check timestamp for caching
        state.lastAuthCheck = Date.now()
        return true
      } else {
        // No valid user data - clear state
        console.log(' Invalid response, clearing user')
        state.currentUser = null
        // Update last auth check timestamp for caching
        state.lastAuthCheck = Date.now()
        return false
      }
    } catch (error) {
      // User is not authenticated - this is normal after logout or if cookie isn't set yet
      // Always clear state on auth failure (unless we already have a user set from login)
      // Don't clear if we just logged in and cookie is still being set
      console.log(' Auth check failed:', {
        status: error.status,
        message: error.message,
        error
      })

      // Only clear state if we don't already have a user set
      // This prevents clearing state immediately after login when cookie might still be setting
      if (!state.currentUser) {
        state.currentUser = null
      }

      // Update last auth check timestamp for caching
      state.lastAuthCheck = Date.now()
      // Only log if it's not a 401 (which is expected for logged out users)
      if (error.status !== 401 && error.status !== undefined) {
        console.log('Auth check error:', error.message)
      }
      return false
    }
  }

  // Login user
  const login = async ({ email, password }) => {
    try {
      const response = await api.post('/user/login', { email, password })

      // Set user state immediately after successful login
      // The backend sets the JWT cookie, but we also set state here
      // so the UI updates immediately

      // Normalize role: convert to string, lowercase, and default to 'user' if missing/null/undefined
      // This ensures consistency with checkAuth function
      let normalizedRole = 'user'
      if (response.role) {
        normalizedRole = String(response.role).toLowerCase().trim()
      }

      state.currentUser = {
        id: response.userId,
        username: response.username,
        email,
        // Include role from login response so admin/superadmin can be used in UI.
        // Use normalized role to ensure consistency across the app
        role: normalizedRole,
        // Include trusted member status
        is_trusted_member: response.is_trusted_member || false,
        // Include trusted member request status
        trusted_member_request: response.trusted_member_request || false,
        trusted_member_request_status: response.trusted_member_request_status || null
      }

      // Verify the state was set correctly
      if (!state.currentUser) {
        console.error('Failed to set user state after login')
      }

      // Wait a bit for the cookie to be set by the browser
      // This ensures the cookie is available for subsequent requests
      await new Promise(resolve => setTimeout(resolve, 200))

      // Update last auth check timestamp for caching
      state.lastAuthCheck = Date.now()
      return { success: true, data: response }
    } catch (error) {
      // Ensure state is cleared on login failure
      state.currentUser = null
      return { success: false, error: error.message }
    }
  }

  // Register new user
  const register = async ({ username, email, password }) => {
    try {
      const response = await api.post('/user/register', { username, email, password })
      return { success: true, data: response }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  // Logout user
  const logout = async () => {
    // Always clear local state FIRST (before API call)
    // This ensures UI updates immediately
    state.currentUser = null

    try {
      await api.post('/user/logout')
      // After successful logout, ensure state is still null
      // (in case checkAuth was called during logout)
      state.currentUser = null
      return { success: true }
    } catch (error) {
      // Even if logout fails, local state is already cleared
      // This handles cases where the token is invalid or expired
      console.log('Logout API call failed, but local state cleared:', error.message)
      // Ensure state is null even if API fails
      state.currentUser = null
      return { success: true } // Return success since we cleared local state
    }
  }

  // Load contests
  const loadContests = async () => {
    state.loading.contests = true
    try {
      const response = await api.get('/contest')
      state.contests = response
      return { success: true, data: response }
    } catch (error) {
      return { success: false, error: error.message }
    } finally {
      state.loading.contests = false
    }
  }

  // Create contest
  const createContest = async (contestData) => {
    try {
      console.log('[STORE] Creating contest with data:', contestData)
      const response = await api.post('/contest', contestData)
      console.log('[STORE] Contest created successfully:', response)
      // Reload contests after creation
      await loadContests()
      return { success: true, data: response }
    } catch (error) {
      console.error('[STORE] Error creating contest:', error)
      const errorMessage = error.response?.data?.error || error.message || 'Unknown error occurred'
      return { success: false, error: errorMessage }
    }
  }

  // Request contest creation (for non-privileged users)
  const requestContest = async (contestData) => {
    try {
      const response = await api.post('/contest/requests', contestData)
      return { success: true, data: response }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  // Get contests by category
  const getContestsByCategory = (category) => {
    return state.contests[category] || []
  }

  // Check loading state
  const isLoading = (key) => {
    return state.loading[key] || false
  }

  // Toggle theme between light and dark
  const toggleTheme = () => {
    // Switch theme
    state.theme = state.theme === 'light' ? 'dark' : 'light'

    // Save to localStorage
    localStorage.setItem('theme', state.theme)

    // Apply theme to document
    applyTheme(state.theme)

    return state.theme
  }

  // Set theme explicitly
  const setTheme = (theme) => {
    if (theme === 'light' || theme === 'dark') {
      state.theme = theme
      localStorage.setItem('theme', theme)
      applyTheme(theme)
    }
  }

  // Apply theme to document element
  const applyTheme = (theme) => {
    const html = document.documentElement
    if (theme === 'dark') {
      html.setAttribute('data-theme', 'dark')
    } else {
      html.removeAttribute('data-theme')
    }
  }

  // Initialize theme on store creation
  // This ensures theme is applied when store is first used
  if (typeof document !== 'undefined') {
    applyTheme(state.theme)
  }

  // Load dashboard access permissions
  const loadDashboardAccess = async () => {
    // Skip if already loaded
    if (state.dashboardAccessLoaded) {
      return
    }

    try {
      const data = await api.get('/user/dashboard/access')
      console.log('[DashboardAccess] API response:', data)
      if (data) {
        state.dashboardAccess = {
          participant: data.can_access_participant !== false,
          organizer: data.can_access_organizer === true,
          jury: data.can_access_jury === true
        }
        console.log('[DashboardAccess] Updated:', state.dashboardAccess)
      }
    } catch (error) {
      console.error('[DashboardAccess] API call failed:', error)
      // Fallback: derive access from the main dashboard endpoint
      try {
        const dashboardData = await api.get('/user/dashboard')
        state.dashboardAccess = {
          participant: true,
          organizer: (dashboardData.organized_contests?.length || 0) > 0,
          jury: (dashboardData.jury_contests?.length || 0) > 0
        }
        console.log('[DashboardAccess] Fallback from /user/dashboard:', state.dashboardAccess)
      } catch (fallbackError) {
        console.error('[DashboardAccess] Fallback also failed:', fallbackError)
        state.dashboardAccess = {
          participant: true,
          organizer: false,
          jury: false
        }
      }
    } finally {
      state.dashboardAccessLoaded = true
    }
  }

  return {
    // State (expose for direct access if needed)
    state,
    // Computed
    isAuthenticated,
    currentUser,
    contests,
    dashboardAccess: computed(() => state.dashboardAccess),
    // Theme
    theme: computed(() => state.theme),
    // Actions
    checkAuth,
    login,
    register,
    logout,
    loadContests,
    loadDashboardAccess,
    createContest,
    requestContest,
    getContestsByCategory,
    isLoading,
    toggleTheme,
    setTheme
  }
}

