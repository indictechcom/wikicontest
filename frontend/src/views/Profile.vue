<template>
  <div class="profile-container">

    <h2 class="page-title">Your Profile</h2>

    <transition name="fade-scale">

      <!-- User Profile Card -->
      <div v-if="currentUser" class="profile-card">

        <!-- Profile Header with Avatar and Badge -->
        <div class="profile-header">
          <div class="avatar">
            <i class="fas fa-user"></i>
          </div>
          <div class="username-with-badge">
            <h3>{{ displayUsername }}</h3>
            <!-- Role badge color changes based on user role -->
            <span
              class="role-badge"
              :class="userRole === 'superadmin' ? 'badge-superadmin' : 'badge-user'"
            >
              {{ formattedRole }}
            </span>
          </div>
          <p class="tagline">Wikimedia Contributor</p>
        </div>

        <!-- User Information Section -->
        <div class="info-section">
          <div class="info-item">
            <i class="fas fa-user-circle"></i>
            <span><strong>Username</strong> : {{ displayUsername }}</span>
          </div>

          <div class="info-item">
            <i class="fas fa-envelope"></i>
            <span><strong>Email</strong> : {{ displayEmail }}</span>
          </div>

          <div class="info-item">
            <i class="fas fa-id-card"></i>
            <span><strong>User ID</strong> : {{ displayUserId }}</span>
          </div>

          <div class="info-item">
            <i class="fas fa-shield-alt"></i>
            <span>
              <strong>Role</strong> :
              <!-- Role text with dynamic styling -->
              <span
                class="role-text"
                :class="userRole === 'superadmin' ? 'role-superadmin' : 'role-user'"
              >
                {{ formattedRole }}
              </span>
            </span>
          </div>

          <!-- Trusted Member Status -->
          <div class="info-item" v-if="!isSuperadmin">
            <i class="fas fa-users-shield"></i>
            <span>
              <strong>Trusted Member</strong> :
              <span v-if="isTrustedMember" class="badge bg-success">Yes</span>
              <span v-else-if="hasRequested" class="badge bg-warning">Request Pending</span>
              <span v-else class="badge bg-secondary">No</span>
            </span>
          </div>

          <!-- Request Trusted Member Button -->
          <div v-if="!isSuperadmin && !isTrustedMember && !hasRequested" class="info-item">
            <button
              class="btn btn-primary w-100"
              @click="requestTrustedMember"
              :disabled="processing"
            >
              <i class="fas fa-user-plus me-2"></i>Request Trusted Member Status
            </button>
          </div>

          <!-- Info message for trusted members -->
          <div v-if="isTrustedMember && !isSuperadmin" class="alert alert-success mt-3">
            <i class="fas fa-check-circle me-2"></i>
            You are a trusted member and can create contests.
          </div>

          <!-- Info message for pending requests -->
          <div v-if="hasRequested && !isTrustedMember" class="alert alert-warning mt-3">
            <i class="fas fa-clock me-2"></i>
            Your trusted member request is pending. A superadmin will review it.
          </div>
        </div>

      </div>

      <!-- Fallback message if not logged in -->
      <div v-else class="alert-message">
        <i class="fas fa-exclamation-triangle"></i>
        Please login to view your profile.
      </div>

    </transition>

  </div>
</template>


<script>
import { computed, onMounted, watch, onActivated, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useStore } from '../store'
import api from '../services/api'
import { showAlert } from '../utils/alerts'

export default {
  name: 'Profile',
  setup() {
    const store = useStore()
    const route = useRoute()
    const currentUser = computed(() => store.currentUser)

    // Refresh user data from backend to get latest role information
    const refreshUserData = async () => {
      console.log('🔄 Refreshing user data...')
      try {
        // Force auth check to fetch latest data from database
        await store.checkAuth()
        // Allow time for reactive state to propagate
        await new Promise(resolve => setTimeout(resolve, 300))

        // Log refreshed data for debugging
        console.log('🔄 After refresh - currentUser:', JSON.stringify(currentUser.value, null, 2))
        console.log('🔄 After refresh - role:', currentUser.value?.role)
      } catch (error) {
        console.error('🔄 Error refreshing user data:', error)
      }
    }

    // Refresh user data when profile page loads
    onMounted(async () => {
      console.log('📄 Profile page mounted')
      console.log('📄 Current user before refresh:', JSON.stringify(currentUser.value, null, 2))
      console.log('📄 Current user role before refresh:', currentUser.value?.role)

      // Refresh to ensure latest role data
      await refreshUserData()

      // Debug logging to verify role is loaded correctly
      console.log('📄 Profile mounted - currentUser after refresh:', JSON.stringify(currentUser.value, null, 2))
      console.log('📄 Profile mounted - currentUser.role after refresh:', currentUser.value?.role)
      console.log('📄 Store currentUser:', JSON.stringify(store.currentUser, null, 2))
      console.log('📄 Store state.currentUser:', JSON.stringify(store.state?.currentUser, null, 2))

      // Final verification of role value
      if (currentUser.value) {
        console.log('📄 FINAL ROLE CHECK:')
        console.log('  - currentUser.value.role:', currentUser.value.role)
        console.log('  - typeof:', typeof currentUser.value.role)
        console.log('  - String value:', String(currentUser.value.role))
        console.log('  - userRole computed:', userRole.value)
      }
    })

    // Refresh when route is activated for keep-alive scenarios
    onActivated(async () => {
      console.log('📄 Profile page activated - refreshing data')
      await refreshUserData()
    })

    // Watch for route changes to refresh when navigating to profile
    watch(() => route.path, async (newPath) => {
      if (newPath === '/profile') {
        console.log('📄 Route changed to profile - refreshing data')
        await refreshUserData()
      }
    }, { immediate: false })

    // Watch for role changes to log updates
    watch(() => currentUser.value?.role, (newRole, oldRole) => {
      console.log('📄 Role changed:', { oldRole, newRole })
      // Special check for known superadmin user
      if (currentUser.value?.username === 'Adityakumar0545' && newRole !== 'superadmin') {
        console.error(' [ERROR] Adityakumar0545 role is not superadmin! Current:', newRole)
      }
    })

    // Watch store state directly for immediate role updates
    watch(() => store.state?.currentUser?.role, (newRole) => {
      console.log('📄 Store state role changed to:', newRole)
      if (newRole === 'superadmin') {
        console.log('Superadmin role detected in store state!')
      }
    }, { immediate: true })

    // Format role for display with capitalization
    const formattedRole = computed(() => {
      // Check multiple sources to ensure we get the latest role
      const role = currentUser.value?.role ||
                   store.currentUser?.role ||
                   store.state?.currentUser?.role ||
                   'user'

      if (!role || role === 'N/A') {
        return 'User'
      }

      // Normalize and capitalize first letter
      const normalizedRole = String(role).toLowerCase().trim()
      return normalizedRole.charAt(0).toUpperCase() + normalizedRole.slice(1)
    })

    // Get lowercase role for CSS class application
    const userRole = computed(() => {
      // Check multiple sources to ensure we get the latest role
      const role = currentUser.value?.role ||
                   store.currentUser?.role ||
                   store.state?.currentUser?.role ||
                   'user'

      if (!role || role === 'N/A') {
        return 'user'
      }

      return String(role).toLowerCase().trim()
    })

    // Display username with fallback to multiple sources
    const displayUsername = computed(() => {
      return currentUser.value?.username ||
             store.currentUser?.username ||
             store.state?.currentUser?.username ||
             'N/A'
    })

    // Display email with fallback to multiple sources
    const displayEmail = computed(() => {
      return currentUser.value?.email ||
             store.currentUser?.email ||
             store.state?.currentUser?.email ||
             'N/A'
    })

    // Display user ID with fallback to multiple sources
    const displayUserId = computed(() => {
      return currentUser.value?.id ||
             store.currentUser?.id ||
             store.state?.currentUser?.id ||
             'N/A'
    })

    // Check if user is superadmin
    const isSuperadmin = computed(() => {
      const role = currentUser.value?.role || store.currentUser?.role || ''
      return String(role).toLowerCase() === 'superadmin'
    })

    // Check if user is trusted member
    const isTrustedMember = computed(() => {
      return currentUser.value?.is_trusted_member ||
             store.currentUser?.is_trusted_member ||
             false
    })

    // Check if user has requested trusted member status
    const hasRequested = computed(() => {
      return currentUser.value?.trusted_member_request ||
             store.currentUser?.trusted_member_request ||
             false
    })

    // Request trusted member status
    const processing = ref(false)
    const requestTrustedMember = async () => {
      if (processing.value) return

      try {
        processing.value = true
        await api.post('/user/trusted-members/request')
        showAlert('Trusted member request submitted successfully. A superadmin will review your request.', 'success')
        // Refresh user data to update the UI
        await store.checkAuth()
      } catch (error) {
        console.error('Error requesting trusted member:', error)
        showAlert(error.response?.data?.error || 'Failed to submit request', 'error')
      } finally {
        processing.value = false
      }
    }

    return {
      currentUser,
      formattedRole,
      userRole,
      displayUsername,
      displayEmail,
      displayUserId,
      isSuperadmin,
      isTrustedMember,
      hasRequested,
      processing,
      requestTrustedMember
    }
  }
}
</script>

<style scoped>
/* Profile Page Styling */

/* Main Container */
.profile-container {
  max-width: 700px;
  margin: auto;
  padding: 3rem 1rem;
}

/* Page Title */
.page-title {
  text-align: center;
  font-size: 2rem;
  font-weight: 600;
  letter-spacing: -0.02em;
  margin-bottom: 2rem;
  color: var(--wiki-dark);
  border-bottom: 2px solid var(--wiki-primary);
  padding-bottom: 0.5rem;
}

/* Profile Card Container */
.profile-card {
  background-color: var(--wiki-card-bg);
  border-radius: 4px;
  padding: 2rem;
  border: 1px solid var(--wiki-border);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

[data-theme="dark"] .profile-card {
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

/* Profile Header Section */
.profile-header {
  text-align: center;
  margin-bottom: 2.2rem;
}

/* User Avatar Circle */
.avatar {
  width: 80px;
  height: 80px;
  margin: auto;
  border-radius: 50%;
  background: var(--wiki-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 2rem;
  margin-bottom: 1rem;
  box-shadow: 0 2px 4px rgba(0, 102, 153, 0.2);
  transition: background-color 0.2s ease;
}

.avatar:hover {
  background: var(--wiki-primary-hover);
}

/* Username and Badge Container */
.username-with-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.profile-header h3 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--wiki-dark);
  margin-bottom: 0.25rem;
}

/* Role Badge Styling */
.role-badge {
  display: inline-block;
  padding: 0.35rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: all 0.2s ease;
}

/* User role badge in blue */
.badge-user {
  background-color: rgba(0, 123, 255, 0.15);
  color: #007bff;
  border: 1px solid rgba(0, 123, 255, 0.4);
  font-weight: 600;
}

[data-theme="dark"] .badge-user {
  background-color: rgba(0, 123, 255, 0.2);
  color: #4da3ff;
  border-color: rgba(0, 123, 255, 0.5);
}

/* Superadmin role badge in red for emphasis */
.badge-superadmin {
  background-color: rgba(220, 53, 69, 0.15);
  color: #dc3545;
  border: 1px solid rgba(220, 53, 69, 0.4);
  font-weight: 700;
}

[data-theme="dark"] .badge-superadmin {
  background-color: rgba(220, 53, 69, 0.25);
  color: #ff6b7a;
  border-color: rgba(220, 53, 69, 0.5);
}

/* Tagline Text */
.tagline {
  font-size: 0.95rem;
  color: var(--wiki-text-muted);
  margin-top: 0.25rem;
}

/* User Information Section */
.info-section {
  margin-top: 1rem;
}

/* Individual Info Item */
.info-item {
  display: flex;
  align-items: center;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 0.75rem;
  background-color: var(--wiki-light-bg);
  border: 1px solid var(--wiki-border);
  transition: all 0.2s ease;
}

[data-theme="dark"] .info-item {
  background-color: rgba(93, 184, 230, 0.05);
  border-color: var(--wiki-border);
}

/* Info Item Icon */
.info-item i {
  font-size: 1.25rem;
  margin-right: 1rem;
  color: var(--wiki-primary);
  transition: color 0.2s ease;
}

/* Info Item Hover Effect */
.info-item:hover {
  background-color: var(--wiki-hover-bg);
  border-color: var(--wiki-primary);
}

.info-item:hover i {
  color: var(--wiki-primary-hover);
}

/* Info Item Label */
.info-item strong {
  color: var(--wiki-dark);
  font-size: 0.95rem;
  font-weight: 600;
}

/* Role Text in Info Section */
.role-text {
  font-weight: 600;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  display: inline-block;
}

/* User role text styling */
.role-user {
  color: #007bff;
  background-color: rgba(0, 123, 255, 0.15);
  font-weight: 600;
}

[data-theme="dark"] .role-user {
  color: #4da3ff;
  background-color: rgba(0, 123, 255, 0.2);
}

/* Superadmin role text styling */
.role-superadmin {
  color: #dc3545;
  background-color: rgba(220, 53, 69, 0.15);
  font-weight: 700;
}

[data-theme="dark"] .role-superadmin {
  color: #ff6b7a;
  background-color: rgba(220, 53, 69, 0.25);
}

/* Alert Message for Logged Out Users */
.alert-message {
  background-color: rgba(153, 0, 0, 0.1);
  color: var(--wiki-danger);
  padding: 1.25rem;
  border-radius: 4px;
  border-left: 4px solid var(--wiki-danger);
  border: 1px solid var(--wiki-danger);
  text-align: center;
  font-size: 1rem;
  font-weight: 500;
}

[data-theme="dark"] .alert-message {
  background-color: rgba(230, 128, 128, 0.15);
}

.alert-message i {
  margin-right: 8px;
  font-size: 1.1rem;
}

/* Fade and Scale Transition */
.fade-scale-enter-active {
  transition: opacity 0.3s ease;
}
.fade-scale-enter-from {
  opacity: 0;
}
</style>
