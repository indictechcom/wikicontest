<template>
  <div id="app">
    <!-- Navigation Bar -->
    <nav class="navbar navbar-expand-lg navbar-light bg-light">
      <div class="container">
        <!-- Left: WikiContest -->
        <router-link class="navbar-brand" to="/">
          WikiContest
        </router-link>

        <button class="navbar-toggler"
type="button"
data-bs-toggle="collapse"
data-bs-target="#navbarNav">
          <span class="navbar-toggler-icon"></span>
        </button>

        <div class="collapse navbar-collapse" id="navbarNav">
          <!-- Middle: Navigation Links (Centered) -->
          <ul class="navbar-nav mx-auto">
            <li class="nav-item">
              <!-- Home link - will show active indicator when on exact / route -->
              <router-link class="nav-link" to="/">Home</router-link>
            </li>
            <li class="nav-item" v-if="isAuthenticated">
              <!-- Contests link - shows active indicator when on /contests page -->
              <router-link class="nav-link" to="/contests">Contests</router-link>
            </li>
            <li class="nav-item" v-if="isAuthenticated">
              <!-- Dashboard link - shows active indicator when on /dashboard page -->
              <router-link class="nav-link" to="/dashboard">Dashboard</router-link>
            </li>
          </ul>

          <!-- Right: Theme Toggle and Login/User Menu -->
          <ul class="navbar-nav">
            <!-- Theme Toggle Button - Always visible -->
            <li class="nav-item me-2">
              <button class="btn btn-outline-secondary theme-toggle"
type="button"
@click="toggleTheme"
                :title="theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'">
                <i :class="theme === 'light' ? 'fas fa-moon' : 'fas fa-sun'"></i>
              </button>
            </li>
            <!-- Show login button when not authenticated -->
            <template v-if="!isAuthenticated">
              <li class="nav-item">
                <a :href="`${getApiBaseUrl()}/user/oauth/login`"
class="btn btn-login-brand"
                  style="text-decoration: none; display: inline-block;"
title="Log in using Wikimedia OAuth 1.0a">
                  <i class="fab fa-wikipedia-w me-2"></i>Log in
                </a>
              </li>
            </template>
            <!-- Show user menu when authenticated -->
            <template v-else>
              <li class="nav-item">
                <div class="dropdown">
                  <button class="btn btn-outline-secondary dropdown-toggle"
type="button"
id="userDropdown"
                    data-bs-toggle="dropdown">
                    <i class="fas fa-user me-1"></i>{{ currentUser?.username || 'User' }}
                  </button>
                  <ul class="dropdown-menu dropdown-menu-end">
                    <li>
                      <router-link class="dropdown-item" to="/profile">
                        <i class="fas fa-user me-2"></i>Profile
                      </router-link>
                    </li>
                    <!-- Trusted Members link - only visible to superadmins -->
                    <li v-if="isSuperadmin">
                      <router-link class="dropdown-item" to="/trusted-members">
                        <i class="fas fa-user-shield me-2"></i>Trusted Members
                      </router-link>
                    </li>
                    <!-- Jury Dashboard link - only visible to jury members -->
                    <li v-if="isJury">
                      <router-link class="dropdown-item" to="/jurydashboard">
                        <i class="fas fa-tachometer-alt me-2"></i>Jury Dashboard
                      </router-link>
                    </li>
                    <li>
                      <hr class="dropdown-divider" />
                    </li>
                    <li>
                      <a class="dropdown-item text-danger" href="#" @click.prevent="handleLogout">
                        <i class="fas fa-sign-out-alt me-2"></i>Logout
                      </a>
                    </li>
                  </ul>
                </div>
              </li>
            </template>
          </ul>
        </div>
      </div>
    </nav>

    <!-- Alert Container -->
    <AlertContainer />

    <!-- Main Content Area -->
    <main class="container-fluid">
      <router-view />
    </main>
  </div>
</template>

<script>
import { onMounted, ref, computed } from 'vue'
import { useStore } from './store'
import { useRouter } from 'vue-router'
import AlertContainer from './components/AlertContainer.vue'
import api from './services/api'

export default {
  name: 'App',
  components: {
    AlertContainer
  },
  setup() {
    const store = useStore()
    const router = useRouter()
    const isJury = ref(false)

    // Access reactive store properties directly without wrapping
    const isAuthenticated = store.isAuthenticated
    const currentUser = store.currentUser
    const theme = store.theme

    // Check if user is superadmin
    const isSuperadmin = computed(() => {
      const role = currentUser.value?.role || store.currentUser?.role || ''
      return String(role).toLowerCase() === 'superadmin'
    })

    // Toggle between light and dark theme
    const toggleTheme = () => {
      store.toggleTheme()
    }

    // Return appropriate API base URL based on environment
    const getApiBaseUrl = () => {
      // In development, use full URL to Flask backend
      if (import.meta.env.DEV) {
        return 'http://localhost:5000/api'
      }
      // In production, use relative URL
      return '/api'
    }

    // Initialize app state and check authentication on mount
    onMounted(async () => {
      // Apply saved theme preference from localStorage
      if (typeof document !== 'undefined') {
        const savedTheme = localStorage.getItem('theme') || 'light'
        store.setTheme(savedTheme)
      }

      // Verify user authentication status
      try {
        // Force a fresh auth check - this will clear state if not authenticated
        await store.checkAuth()
      } catch (error) {
        // Silently fail - user is not authenticated
        // This is normal for users who aren't logged in
        // checkAuth already clears state on error
        console.log('Auth check completed - user not logged in')
      }
      // Determine if user has jury privileges
      try {
        const data = await api.get('/user/dashboard')

        // Frontend-only check: user is jury if they have assigned contests
        isJury.value = Array.isArray(data.jury_contests) && data.jury_contests.length > 0
      } catch (e) {
        isJury.value = false
      }
    })

    // Handle user logout and cleanup
    const handleLogout = async () => {
      try {
        // Clear user session and state
        await store.logout()

        // Small delay to ensure cookies are cleared on backend
        await new Promise(resolve => setTimeout(resolve, 200))

        // Verify logout by forcing fresh auth check
        await store.checkAuth()

        // Show success message
        const { showAlert } = await import('./utils/alerts')
        showAlert('Logged out successfully', 'success')

        // Redirect to home page
        router.push('/')
      } catch (error) {
        // Ensure state is cleared even if logout request fails
        await store.checkAuth()

        const { showAlert } = await import('./utils/alerts')
        showAlert('Logged out (session cleared)', 'info')
        router.push('/')
      }
    }

    return {
      isAuthenticated,
      currentUser,
      theme,
      toggleTheme,
      handleLogout,
      getApiBaseUrl,
      isJury,
      isSuperadmin
    }
  }
}
</script>

<style>
/* Wikipedia/Wikimedia Brand Colors:
 * Sea Blue: #006699 (primary)
 * Illuminating Emerald: #339966 (success)
 * Crimson Red: #990000 (danger/warning)
 * Outer Space: #484848 (text/dark)
 */

/* --- Brand Colors --- */
:root {
  --crimson: #990000;
  --emerald: #339966;
  --seablue: #006699;
  --outerspace: #484848;

  /* UI Shades */
  --nav-bg-light: #ffffff;
  --nav-bg-dark: #1b1b1b;
  --hover-bg-light: rgba(0, 0, 0, 0.05);
  --hover-bg-dark: rgba(255, 255, 255, 0.1);

  --text-dark: #2b2b2b;
  --text-light: #f1f1f1;

  --border-light: rgba(0, 0, 0, 0.12);
  --border-dark: rgba(255, 255, 255, 0.15);

  --transition: 0.25s ease;
}

/* Typography Upgrade - Using Google Fonts Inter */
body,
button,
input {
  font-family: 'Inter', "Segoe UI", system-ui, sans-serif;
  letter-spacing: 0.2px;
}

.navbar {
  background: var(--wiki-navbar-bg) !important;
  border-bottom: 1px solid var(--wiki-border);
  padding: 0.75rem 0;
  transition: background 0.3s ease, border-color 0.3s ease;
  z-index: 1000 !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

/* Dark mode navbar styling */
[data-theme="dark"] .navbar {
  background: var(--wiki-navbar-bg) !important;
  border-bottom: 1px solid var(--wiki-border);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

/* Brand logo - professional styling */
.navbar-brand {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--wiki-primary) !important;
  letter-spacing: -0.02em;
  transition: color 0.2s ease;
  text-decoration: none !important;
}

.navbar-brand:hover {
  color: var(--wiki-primary-hover) !important;
  text-decoration: none !important;
}

/* Dark mode - WikiContest in white, no underline */
[data-theme="dark"] .navbar-brand {
  color: #ffffff !important;
  text-decoration: none !important;
}

[data-theme="dark"] .navbar-brand:hover {
  color: #e0e0e0 !important;
  text-decoration: none !important;
}

/* Navigation links - clean professional style */
.nav-link {
  font-weight: 500;
  color: var(--wiki-text) !important;
  padding: 0.5rem 1rem !important;
  border-radius: 4px;
  transition: all 0.2s ease;
  font-size: 0.95rem;
  position: relative;
}

[data-theme="dark"] .nav-link {
  color: var(--wiki-text) !important;
}

.nav-link:hover {
  background: var(--wiki-hover-bg);
  color: var(--wiki-primary) !important;
}

[data-theme="dark"] .nav-link:hover {
  background: var(--wiki-hover-bg);
}

/* Active navigation link indicator - shows which page user is on */
.nav-link.router-link-active,
.nav-link.router-link-exact-active {
  color: var(--wiki-primary) !important;
  font-weight: 600;
  /* Add bottom border as active indicator */
  border-bottom: 2px solid var(--wiki-primary);
  padding-bottom: calc(0.5rem - 2px);
  /* Adjust padding to account for border */
}

/* Active link in dark mode */
[data-theme="dark"] .nav-link.router-link-active,
[data-theme="dark"] .nav-link.router-link-exact-active {
  color: var(--wiki-primary) !important;
  border-bottom-color: var(--wiki-primary);
}

/* Optional: Add subtle background for active link */
.nav-link.router-link-active,
.nav-link.router-link-exact-active {
  background: var(--wiki-hover-bg);
}

.btn-primary {
  background: var(--wiki-primary);
  border: 1px solid var(--wiki-primary);
  font-weight: 500;
  transition: all 0.2s ease;
  border-radius: 4px;
}

.btn-primary:hover {
  background: var(--wiki-primary-hover);
  border-color: var(--wiki-primary-hover);
  box-shadow: 0 2px 4px rgba(0, 102, 153, 0.2);
}

.btn-outline-primary {
  border-color: var(--wiki-primary);
  color: var(--wiki-primary);
  font-weight: 500;
  border-radius: 4px;
}

.btn-outline-primary:hover {
  background: var(--wiki-primary);
  border-color: var(--wiki-primary);
  color: #fff;
}

/* Brand blue login button - uses Wikimedia brand color #006699 */
.btn-login-brand {
  background: #006699;
  border: 1px solid #006699;
  color: #ffffff !important;
  font-weight: 500;
  transition: all 0.2s ease;
  border-radius: 4px;
}

.btn-login-brand:hover {
  background: #005580;
  border-color: #005580;
  color: #ffffff !important;
  box-shadow: 0 2px 4px rgba(0, 102, 153, 0.2);
}

/* Wikimedia icon in login button - white color */
.btn-login-brand .fab.fa-wikipedia-w {
  color: #ffffff !important;
  font-size: 1.1em;
}

/* Theme Toggle Button - professional */
.theme-toggle {
  border-radius: 4px;
  transition: all 0.2s ease;
  border: 1px solid var(--wiki-border);
  background-color: transparent;
  color: var(--wiki-text);
}

.theme-toggle:hover {
  background: var(--wiki-hover-bg);
  border-color: var(--wiki-primary);
  color: var(--wiki-primary);
}

[data-theme="dark"] .theme-toggle:hover {
  background: var(--wiki-hover-bg);
}

.dropdown-menu {
  border-radius: 4px;
  padding: 0.25rem 0;
  border: 1px solid var(--wiki-border);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  background: var(--wiki-card-bg);
  z-index: 2000 !important;
}

[data-theme="dark"] .dropdown-menu {
  background: var(--wiki-card-bg);
  border: 1px solid var(--wiki-border);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.dropdown-item {
  padding: 0.5rem 1rem;
  font-weight: 400;
  transition: all 0.2s ease;
  font-size: 0.95rem;
  color: var(--wiki-text);
}

.dropdown-item:hover {
  background: var(--wiki-hover-bg);
  color: var(--wiki-primary);
}

[data-theme="dark"] .dropdown-item:hover {
  background: var(--wiki-hover-bg);
}

/* Logout item special - MediaWiki red */
.dropdown-item.text-danger {
  color: var(--wiki-danger) !important;
}

.dropdown-item.text-danger:hover {
  background: rgba(153, 0, 0, 0.1);
  color: #990000 !important;
}

/* Ensure proper MediaWiki red in dark mode */
[data-theme="dark"] .dropdown-item.text-danger {
  color: #990000 !important;
}

[data-theme="dark"] .dropdown-item.text-danger:hover {
  background: rgba(153, 0, 0, 0.15);
  color: #990000 !important;
}

.card {
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  border: 1px solid var(--wiki-border);
  background-color: var(--wiki-card-bg);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  border-radius: 4px;
}

[data-theme="dark"] .card {
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.card:hover {
  border-color: var(--wiki-primary);
  box-shadow: 0 2px 8px rgba(0, 102, 153, 0.1);
}

[data-theme="dark"] .card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.card-title {
  color: var(--wiki-dark);
  font-weight: 600;
  font-size: 1.1rem;
}

@media (max-width: 768px) {
  .navbar-brand {
    font-size: 1.3rem;
  }

  .dropdown-menu {
    width: 100%;
  }
}
</style>
