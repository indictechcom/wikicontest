<template>
  <div class="container py-5">
    <!-- Page Header with Create Button -->
    <div class="d-flex flex-column flex-sm-row justify-content-between align-items-start align-items-sm-center mb-4">
      <h2 class="page-header mb-0">Contests</h2>
      <!-- Show Create Contest button for superadmin users (they can create contests directly) -->
      <button
        v-if="isAuthenticated && isSuperadmin"
        class="btn btn-primary"
        @click="showCreateContestModal"
      >
        <i class="fas fa-plus me-2"></i>Create Contest
      </button>
      <!-- Show Create Contest button for trusted members (non-superadmin privileged users) -->
      <button
        v-else-if="isAuthenticated && canCreateContests"
        class="btn btn-primary"
        @click="showCreateContestModal"
      >
        <i class="fas fa-plus me-2"></i>Create Contest
      </button>
      <!-- Show Request Pending status badge for users with pending requests -->
      <div
        v-else-if="isAuthenticated && requestStatus === 'pending'"
        class="badge bg-warning status-badge"
      >
        <i class="fas fa-clock me-2"></i>Request Pending
      </div>
      <!-- Show Re-request Contest Creator Rights button for users whose request was rejected -->
      <button
        v-else-if="isAuthenticated && requestStatus === 'rejected'"
        class="btn btn-secondary"
        @click="showRequestTrustedMemberModal"
      >
        <i class="fas fa-redo me-2"></i>Re-request Contest Creator Rights
      </button>
      <!-- Show Request Contest Creator Rights button for users who have never requested -->
      <button
        v-else-if="isAuthenticated && canRequest"
        class="btn btn-secondary"
        @click="showRequestTrustedMemberModal"
      >
        <i class="fas fa-user-plus me-2"></i>Request Contest Creator Rights
      </button>
    </div>

    <!-- Login CTA for unauthenticated visitors -->
    <div v-if="!isAuthenticated" class="alert alert-info d-flex align-items-center justify-content-between mb-4">
      <span>
        <i class="fas fa-info-circle me-2"></i>
        Log in with Wikimedia to participate in contests and track your progress.
      </span>
      <a :href="loginUrl" class="btn btn-sm btn-primary ms-3" style="white-space: nowrap;">
        <i class="fab fa-wikipedia-w me-1"></i>Log in
      </a>
    </div>

    <!-- Contest Category Tabs -->
    <ul class="nav nav-tabs mb-4" id="contestTabs">
      <li class="nav-item">
          <button class="nav-link"
:class="{ active: activeCategory === 'current' }"
            @click="setActiveCategory('current')">
            Current <span class="tab-count">({{ currentCount }})</span>
          </button>
      </li>
      <li class="nav-item">
          <button class="nav-link"
:class="{ active: activeCategory === 'upcoming' }"
            @click="setActiveCategory('upcoming')">
            Upcoming <span class="tab-count">({{ upcomingCount }})</span>
          </button>
      </li>
      <li class="nav-item">
          <button class="nav-link" :class="{ active: activeCategory === 'past' }" @click="setActiveCategory('past')">
            Past <span class="tab-count">({{ pastCount }})</span>
          </button>
      </li>
    </ul>

    <!-- Loading Spinner -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
    </div>

    <!-- Contest List -->
    <div v-else id="contestList">
      <!-- Empty State Message -->
      <div v-if="currentContests.length === 0" class="alert alert-info text-center">
        <i class="fas fa-info-circle me-2"></i>
        No {{ activeCategory }} contests available.
      </div>
      <!-- Contest Cards -->
      <div v-else class="contest-list">
        <div v-for="contest in currentContests"
:key="contest.id"
class="contest-item"
@click="viewContest(contest)">
          <div class="contest-card">
            <!-- Contest Header: Title and Creation Timestamp -->
            <div class="contest-header">
              <div class="contest-title-section">
                <span class="contest-title-link" @click.stop="viewContest(contest)">
                  {{ contest.name }}
                </span>
              </div>
              <div class="contest-timestamp">
                {{ formatDate(contest.created_at) }}
              </div>
            </div>

            <!-- Contest Metadata Tags -->
            <div class="contest-tags">
              <!-- Status Badge -->
              <span class="contest-tag status-tag" :class="getStatusClass(contest.status)">
                <i :class="getStatusIcon(contest.status)"></i>
                {{ getStatusLabel(contest.status) }}
              </span>

              <!-- Project/Wiki Badge -->
              <span class="contest-tag project-tag">
                <i class="fas fa-briefcase"></i>
                {{ contest.project_name }}
              </span>

              <!-- Submission Count Badge -->
              <span class="contest-tag submissions-tag">
                <i class="fas fa-file-alt"></i>
                {{ contest.submission_count || 0 }} {{ contest.submission_count === 1 ? 'submission' : 'submissions' }}
              </span>

              <!-- Organizers with Avatar Bubbles -->
              <div class="organizers-section">
                <span class="organizers-label"><i class="fas fa-user-cog"></i>
                </span>
                <div class="organizers-avatars">
                  <!-- Show first 3 organizers -->
                  <div v-for="(organizer, index) in getOrganizers(contest)"
:key="index"
class="organizer-avatar"
                    :title="organizer">
                    {{ getInitials(organizer) }}
                  </div>
                  <!-- Show count of remaining organizers if more than 3 -->
                  <div v-if="getOrganizers(contest).length > 3"
class="organizer-avatar organizer-more"
                    :title="`${getOrganizers(contest).length - 3} more organizers`">
                    +{{ getOrganizers(contest).length - 3 }}
                  </div>
                </div>
              </div>

              <!-- Date Range Badge -->
              <span v-if="contest.start_date || contest.end_date" class="contest-tag date-tag">
                <i class="fas fa-calendar-alt"></i>
                {{ formatDateRange(contest.start_date, contest.end_date) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <SubmitArticleModal
      v-if="submittingToContestId"
      :contest-id="submittingToContestId"
      @submitted="handleArticleSubmitted"
    />

    <RequestContestModal
      ref="requestContestModal"
      @requested="handleContestRequested"
    />

    <RequestTrustedMemberModal
      :show="showRequestTrustedMemberForm"
      @requested="handleTrustedMemberRequested"
      @close="showRequestTrustedMemberForm = false"
    />
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useStore } from '../store'
import { showAlert } from '../utils/alerts'
import SubmitArticleModal from '../components/SubmitArticleModal.vue'
import RequestContestModal from '../components/RequestContestModal.vue'
import RequestTrustedMemberModal from '../components/RequestTrustedMemberModal.vue'

export default {
  name: 'Contests',
  components: {
    SubmitArticleModal,
    RequestContestModal,
    RequestTrustedMemberModal
  },
  setup() {
    const router = useRouter()
    const route = useRoute()
    const store = useStore()
    const VALID_CATEGORIES = ['current', 'upcoming', 'past']
    const activeCategory = ref('current')

    // Restore the active subsection from the URL query parameter (?tab=...)
    const getCategoryFromUrl = () => {
      const tab = route.query.tab
      return VALID_CATEGORIES.includes(tab) ? tab : 'current'
    }

    // Reflect the active subsection in the URL and push into browser history.
    // The URL always shows the current tab, including the default "current".
    const syncUrlWithCategory = (category) => {
      if (route.query.tab !== category) {
        router.push({ name: route.name, query: { ...route.query, tab: category } })
      }
    }
    const loading = ref(false)
    const submittingToContestId = ref(null)
    const showRequestTrustedMemberForm = ref(false)

    // Get contests for currently selected category
    const currentContests = computed(() => {
      return store.getContestsByCategory(activeCategory.value)
    })

    const currentCount = computed(() =>
      store.contests.value.current?.length || 0
    )
    const upcomingCount = computed(() =>
      store.contests.value.upcoming?.length || 0
    )
    const pastCount = computed(() =>
      store.contests.value.past?.length || 0
    )

    const isAuthenticated = computed(() => store.isAuthenticated)

    const loginUrl = computed(() => {
      if (import.meta.env.DEV) {
        return 'http://localhost:5000/api/user/oauth/login'
      }
      return '/api/user/oauth/login'
    })

    // Check if user is superadmin (explicit check for button visibility)
    // Access currentUser.value since it's a computed property
    const isSuperadmin = computed(() => {
      const user = store.currentUser.value
      if (!user) {
        console.log('[isSuperadmin] No current user')
        return false
      }
      const userRole = String(user.role || '').toLowerCase().trim()
      const isSuper = userRole === 'superadmin'
      console.log('[isSuperadmin] User:', user.username, 'Role:', userRole, 'Is superadmin:', isSuper)
      return isSuper
    })

    // Check if user can create contests (superadmin or trusted member)
    // Access currentUser.value since it's a computed property
    const canCreateContests = computed(() => {
      const user = store.currentUser.value
      if (!user) {
        console.log('[canCreateContests] No current user')
        return false
      }

      // Debug logging to help identify issues
      console.log('[canCreateContests] Checking user:', {
        username: user.username,
        role: user.role,
        roleType: typeof user.role,
        is_trusted_member: user.is_trusted_member
      })

      // Superadmins can always create contests
      // Use case-insensitive comparison to handle any role format variations
      const userRole = String(user.role || '').toLowerCase().trim()
      console.log('[canCreateContests] Normalized role:', userRole, 'Comparison:', userRole === 'superadmin')

      if (userRole === 'superadmin') {
        console.log('[canCreateContests] User is superadmin - can create contests')
        return true
      }

      // Trusted members can create contests
      const isTrusted = user.is_trusted_member === true
      console.log('[canCreateContests] User is trusted member:', isTrusted)
      return isTrusted
    })

    // Get the trusted member request status
    const requestStatus = computed(() => {
      const user = store.currentUser.value
      if (!user) {
        return null
      }
      return user.trusted_member_request_status || null
    })

    // Check if user can request (never requested OR was rejected)
    const canRequest = computed(() => {
      const status = requestStatus.value
      return !isSuperadmin.value &&
             !canCreateContests.value &&
             (!status || status === 'rejected')
    })

    // Combine creator and organizers array into single list
    const getOrganizers = (contest) => {
      const organizers = []

      // Add creator first
      if (contest.created_by) {
        organizers.push(contest.created_by)
      }

      // Add additional organizers, excluding duplicates
      if (contest.organizers && Array.isArray(contest.organizers)) {
        contest.organizers.forEach(org => {
          if (org && org !== contest.created_by) {
            organizers.push(org)
          }
        })
      }

      return organizers
    }

    // Extract initials from username for avatar display
    const getInitials = (username) => {
      if (!username) return '?'

      const parts = username.trim().split(/\s+/)

      if (parts.length >= 2) {
        // Multiple words: use first letter of first two words
        return (parts[0][0] + parts[1][0]).toUpperCase()
      } else {
        // Single word: use first two characters
        return username.substring(0, 2).toUpperCase()
      }
    }

    // Generate consistent color for avatar based on username hash
    const getAvatarColor = (username) => {
      if (!username) return '#6c757d'

      // Simple hash function for consistent color generation
      let hash = 0
      for (let i = 0; i < username.length; i++) {
        hash = username.charCodeAt(i) + ((hash << 5) - hash)
      }

      // Convert to HSL for better color variety
      const hue = hash % 360
      return `hsl(${hue}, 65%, 50%)`
    }

    // Switch between current, upcoming, and past contests
    const setActiveCategory = (category) => {
      activeCategory.value = category
      syncUrlWithCategory(category)
    }

    // Truncate long text with ellipsis
    const truncateText = (text, maxLength) => {
      if (!text) return ''
      if (text.length <= maxLength) return text
      return text.substring(0, maxLength) + '...'
    }

    // Format timestamp for display in contest header
    const formatDate = (dateString) => {
      if (!dateString) return ''
      try {
        const date = new Date(dateString)
        return date.toLocaleDateString('en-US', {
          weekday: 'short',
          month: 'short',
          day: 'numeric',
          hour: 'numeric',
          minute: '2-digit'
        })
      } catch (e) {
        return dateString
      }
    }

    // Format start and end dates into readable range
    const formatDateRange = (startDate, endDate) => {
      if (!startDate && !endDate) return ''

      const format = (dateStr) => {
        if (!dateStr) return ''
        try {
          const date = new Date(dateStr)
          return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
        } catch (e) {
          return dateStr
        }
      }

      if (startDate && endDate) {
        return `${format(startDate)} - ${format(endDate)}`
      } else if (startDate) {
        return `Starts: ${format(startDate)}`
      } else if (endDate) {
        return `Ends: ${format(endDate)}`
      }
      return ''
    }

    // Convert status key to human-readable label
    const getStatusLabel = (status) => {
      const labels = {
        current: 'Active',
        upcoming: 'Upcoming',
        past: 'Past',
        unknown: 'Unknown'
      }
      return labels[status] || 'Unknown'
    }

    // Get CSS class for status badge styling
    const getStatusClass = (status) => {
      const classes = {
        current: 'status-active',
        upcoming: 'status-upcoming',
        past: 'status-past',
        unknown: 'status-unknown'
      }
      return classes[status] || 'status-unknown'
    }

    // Get icon class for status badge
    const getStatusIcon = (status) => {
      const icons = {
        current: 'fas fa-circle',
        upcoming: 'fas fa-clock',
        past: 'fas fa-check-circle',
        unknown: 'fas fa-question-circle'
      }
      return icons[status] || 'fas fa-question-circle'
    }

    // Navigate to contest detail page using slugified name
    const viewContest = (contest) => {
      let contestData = contest
      if (typeof contest === 'number' || typeof contest === 'string') {
        contestData = currentContests.value.find(c => c.id === parseInt(contest))
      }

      if (!contestData || !contestData.id) {
        showAlert('Contest not found', 'danger')
        return
      }

      router.push({ name: 'ContestView', params: { contestId: contestData.id } })
    }

    // Open modal to create new contest
    const showCreateContestModal = () => {
      if (!store.isAuthenticated) {
        showAlert('Please login to create a contest', 'warning')
        return
      }

      router.push({ name: 'CreateContest' })
    }

    // Open modal to request contest creation
    const showRequestContestModal = () => {
      if (!store.isAuthenticated) {
        showAlert('Please login to request contest creation', 'warning')
        return
      }

      const modalElement = document.getElementById('requestContestModal')
      if (modalElement) {
        const modal = new bootstrap.Modal(modalElement)
        modal.show()
      }
    }

    // Open fullscreen form to request contest creator rights (trusted member status)
    const showRequestTrustedMemberModal = () => {
      if (!store.isAuthenticated) {
        showAlert('Please login to request contest creator rights', 'warning')
        return
      }

      // Show the fullscreen form
      showRequestTrustedMemberForm.value = true
    }

    // Refresh contest list after new contest is created
    // Refresh contest list after new contest is created
    const handleContestCreated = async () => {
      console.log('[CONTESTS] Contest created, reloading list...')

      //  Reload contests from backend
      loading.value = true
      try {
        await store.loadContests()
        console.log('[CONTESTS] Contests reloaded successfully')

        //  Switch to 'current' tab to show the new contest
        activeCategory.value = 'current'
      } catch (error) {
        console.error('[CONTESTS] Failed to reload contests:', error)
        showAlert('Contest created but failed to refresh list. Please refresh the page.', 'warning')
      } finally {
        loading.value = false
      }
    }

    // Open article submission modal for specific contest
    const handleSubmitArticle = (contestId) => {
      if (!store.isAuthenticated) {
        showAlert('Please login to submit an article', 'warning')
        return
      }
      submittingToContestId.value = contestId

      setTimeout(() => {
        const modalElement = document.getElementById('submitArticleModal')
        if (modalElement) {
          const modal = new bootstrap.Modal(modalElement)
          modal.show()
        }
      }, 100)
    }

    // Refresh after article submission
    const handleArticleSubmitted = () => {
      submittingToContestId.value = null
      store.loadContests()
    }

    // Refresh after contest request is submitted
    const handleContestRequested = () => {
      showAlert('Contest creation request submitted successfully. A superadmin will review your request.', 'success')
    }

    // Refresh user data after trusted member request is submitted
    // This ensures the button updates if user was auto-approved
    const handleTrustedMemberRequested = async () => {
      // Refresh user authentication to get updated trusted member status
      try {
        await store.checkAuth()
        showAlert('Request submitted successfully. If you have 300+ edits, you may have been automatically approved!', 'success')
      } catch (error) {
        console.error('Error refreshing user data:', error)
        showAlert('Request submitted successfully. A superadmin will review your request.', 'success')
      }
    }

    // Load contests on component mount
    onMounted(async () => {
      // Restore the active subsection from the shared URL, if present
      activeCategory.value = getCategoryFromUrl()
      // Default the URL bar to showing the current tab
      syncUrlWithCategory(activeCategory.value)
      loading.value = true
      try {
        await store.loadContests()
      } catch (error) {
        showAlert('Failed to load contests: ' + error.message, 'danger')
      } finally {
        loading.value = false
      }
    })

    // Keep the active subsection in sync when the URL changes
    // (e.g. a shared link is opened, or the user uses back/forward navigation)
    watch(
      () => route.query.tab,
      (tab) => {
        const category = VALID_CATEGORIES.includes(tab) ? tab : 'current'
        if (category !== activeCategory.value) {
          activeCategory.value = category
        }
      }
    )

    return {
      activeCategory,
      currentContests,
      currentCount,
      upcomingCount,
      pastCount,
      loading,
      isAuthenticated,
      loginUrl,
      isSuperadmin,
      canCreateContests,
      requestStatus,
      canRequest,
      submittingToContestId,
      showRequestTrustedMemberForm,
      setActiveCategory,
      truncateText,
      formatDate,
      formatDateRange,
      getStatusLabel,
      getStatusClass,
      getStatusIcon,
      getOrganizers,
      getInitials,
      getAvatarColor,
      viewContest,
      showCreateContestModal,
      showRequestContestModal,
      showRequestTrustedMemberModal,
      handleContestCreated,
      handleSubmitArticle,
      handleArticleSubmitted,
      handleContestRequested,
      handleTrustedMemberRequested
    }
  }
}
</script>

<style scoped>
/* Contests Page Styling with Wikipedia Colors */

/* Page Title / Header */
h2 {
  color: var(--wiki-dark);
  font-weight: 700;
  margin-bottom: 1.5rem;
  transition: color 0.3s ease;
}

[data-theme="dark"] h2 {
  color: #ffffff !important;
}

h2.page-header {
  font-size: 2rem;
  font-weight: 600;
  border-bottom: 2px solid var(--wiki-primary);
  padding-bottom: 0.5rem;
  margin-bottom: 2rem;
  letter-spacing: -0.01em;
}

[data-theme="dark"] h2.page-header {
  color: #ffffff !important;
}

/* Primary Action Button */
.btn-primary {
  background-color: var(--wiki-primary);
  border-color: var(--wiki-primary);
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
  padding: 0.5rem 1rem;
  border-radius: 4px;
}

.btn-primary:hover {
  background-color: var(--wiki-primary-hover);
  border-color: var(--wiki-primary-hover);
  box-shadow: 0 2px 4px rgba(0, 102, 153, 0.2);
}

/* Secondary Button */
.btn-secondary {
  background-color: var(--wiki-text-muted);
  border-color: var(--wiki-text-muted);
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
  padding: 0.5rem 1rem;
  border-radius: 4px;
}

.btn-secondary:hover {
  background-color: #6c757d;
  border-color: #6c757d;
}

/* Status Badge in Page Header */
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-weight: 500;
  font-size: 0.9rem;
  white-space: nowrap;
}

/* Category Navigation Tabs */
.nav-tabs {
  border-bottom: 1px solid var(--wiki-border);
  margin-bottom: 2rem;
  transition: border-color 0.3s ease;
}

.tab-count {
  font-size: 0.85rem;
  font-weight: 400;
  color: var(--wiki-text-muted);
  margin-left: 0.35rem;
  opacity: 0.8;
}

[data-theme="dark"] .tab-count {
  color: #aaa;
}

.nav-tabs .nav-link {
  color: var(--wiki-dark);
  border: none;
  border-bottom: 3px solid transparent;
  padding: 0.75rem 1.5rem;
  font-weight: 500;
  transition: all 0.2s ease;
  margin-right: 0.5rem;
}

[data-theme="dark"] .nav-tabs .nav-link {
  color: #ffffff !important;
}

[data-theme="dark"] .nav-tabs .nav-link:hover {
  color: var(--wiki-primary) !important;
}

[data-theme="dark"] .nav-tabs .nav-link.active {
  color: var(--wiki-primary) !important;
}

.nav-tabs .nav-link:hover {
  color: var(--wiki-primary);
  border-bottom-color: var(--wiki-primary);
  background-color: var(--wiki-hover-bg);
  border-radius: 0.5rem 0.5rem 0 0;
}

.nav-tabs .nav-link.active {
  color: var(--wiki-primary);
  background-color: transparent;
  border-bottom-color: var(--wiki-primary);
  border-bottom-width: 2px;
  font-weight: 600;
}

/* Contest List Container */
.contest-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

/* Individual Contest Item */
.contest-item {
  margin-bottom: 1rem;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.contest-item:hover {
  transform: translateY(-2px);
}

/* Contest Card Styling */
.contest-card {
  background-color: #ffffff;
  border: 1px solid var(--wiki-border);
  border-radius: 8px;
  padding: 1.25rem;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.contest-item:hover .contest-card {
  box-shadow: 0 4px 12px rgba(0, 102, 153, 0.15);
  border-color: var(--wiki-primary);
}

[data-theme="dark"] .contest-card {
  background-color: #2a2a2a;
  border-color: #444;
}

[data-theme="dark"] .contest-item:hover .contest-card {
  border-color: var(--wiki-primary);
  box-shadow: 0 4px 12px rgba(77, 166, 204, 0.2);
}

/* Contest Header Layout */
.contest-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
  gap: 1rem;
}

.contest-title-section {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

/* Contest Title Link */
.contest-title-link {
  color: var(--wiki-primary);
  font-size: 1.4rem;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: color 0.2s ease;
  flex: 1;
}

.contest-title-link:hover {
  color: var(--wiki-primary-hover);
  text-decoration: underline;
}

[data-theme="dark"] .contest-title-link {
  color: #ffffff !important;
}

[data-theme="dark"] .contest-title-link:hover {
  color: #ffffff !important;
  text-decoration: underline;
}

/* Creation Timestamp */
.contest-timestamp {
  color: #666;
  font-size: 0.875rem;
  white-space: nowrap;
  min-width: fit-content;
}

[data-theme="dark"] .contest-timestamp {
  color: #aaa;
}

/* Tags Container */
.contest-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

/* Base Tag Styling */
.contest-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.contest-tag i {
  font-size: 0.65rem;
}

/* Status Badge Variants */
.status-tag {
  background-color: #f5f5f5;
  color: #424242;
  border: 1px solid #e0e0e0;
}

.status-active {
  background-color: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #c8e6c9;
}

.status-upcoming {
  background-color: #fff9e6;
  color: #f57c00;
  border: 1px solid #ffe0b2;
}

.status-past {
  background-color: #f3e5f5;
  color: #7b1fa2;
  border: 1px solid #ce93d8;
}

.status-unknown {
  background-color: #fafafa;
  color: #616161;
  border: 1px solid #e0e0e0;
}

/* Dark mode status badge overrides */
[data-theme="dark"] .status-tag {
  background-color: #f5f5f5 !important;
  color: #424242 !important;
  border-color: #e0e0e0 !important;
}

[data-theme="dark"] .status-active {
  background-color: #e8f5e9 !important;
  color: #2e7d32 !important;
  border-color: #c8e6c9 !important;
}

[data-theme="dark"] .status-upcoming {
  background-color: #fff9e6 !important;
  color: #f57c00 !important;
  border-color: #ffe0b2 !important;
}

[data-theme="dark"] .status-past {
  background-color: #f3e5f5 !important;
  color: #7b1fa2 !important;
  border-color: #ce93d8 !important;
}

/* Project Badge */
.project-tag {
  background-color: #e3f2fd;
  color: #1565c0;
  border: 1px solid #90caf9;
}

[data-theme="dark"] .project-tag {
  background-color: #e3f2fd !important;
  color: #1565c0 !important;
  border-color: #90caf9 !important;
}

/* Submissions Badge */
.submissions-tag {
  background-color: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #a5d6a7;
}

[data-theme="dark"] .submissions-tag {
  background-color: #e8f5e9 !important;
  color: #2e7d32 !important;
  border-color: #a5d6a7 !important;
}

/* Date Range Badge */
.date-tag {
  background-color: #fff3e0;
  color: #e65100;
  border: 1px solid #ffcc80;
  font-weight: 500;
}

[data-theme="dark"] .date-tag {
  background-color: #fff3e0 !important;
  color: #e65100 !important;
  border-color: #ffcc80 !important;
}

/* Organizers Section */
.organizers-section {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.10rem 0.5rem;
  background-color: #f0f7ff;
  border: 1px solid #b3d9ff;
  border-radius: 4px;
}

[data-theme="dark"] .organizers-section {
  background-color: #f0f7ff !important;
  border-color: #b3d9ff !important;
}

.organizers-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #0066cc;
  white-space: nowrap;
}

[data-theme="dark"] .organizers-label {
  color: #0066cc !important;
}

/* Organizer Avatar Bubbles */
.organizers-avatars {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.organizer-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--wiki-primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.65rem;
  font-weight: 700;
  cursor: help;
  transition: transform 0.2s ease;
  flex-shrink: 0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.organizer-avatar:hover {
  transform: scale(1.15);
  z-index: 10;
}

/* +N overflow indicator */
.organizer-more {
  background: var(--wiki-primary);
  font-size: 0.6rem;
}

/* Empty State Alert */
.alert-info {
  background-color: rgba(0, 102, 153, 0.1);
  border: 1px solid var(--wiki-primary);
  border-left: 4px solid var(--wiki-primary);
  color: var(--wiki-primary);
  border-radius: 0.5rem;
  padding: 1rem;
}

[data-theme="dark"] .alert-info {
  background-color: rgba(77, 166, 204, 0.15);
  color: #ffffff;
}

.alert-info i {
  color: var(--wiki-primary);
}

[data-theme="dark"] .alert-info i {
  color: #ffffff;
}

/* Loading Spinner */
.spinner-border.text-primary {
  color: var(--wiki-primary) !important;
  width: 3rem;
  height: 3rem;
  border-width: 0.3em;
}

/* Tablet Responsive */
@media (max-width: 768px) {
  .container {
    padding-left: 1rem;
    padding-right: 1rem;
  }

  h2 {
    font-size: 1.75rem;
  }

  .contest-card {
    padding: 1rem;
  }

  .contest-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .contest-title-section {
    width: 100%;
  }

  .contest-title-link {
    font-size: 1.2rem;
  }

  .contest-timestamp {
    font-size: 0.8rem;
  }

  .contest-tags {
    gap: 0.35rem;
  }

  .contest-tag {
    font-size: 0.7rem;
    padding: 0.2rem 0.45rem;
  }

  .organizers-section {
    padding: 0.2rem 0.45rem;
  }

  .organizers-label {
    font-size: 0.7rem;
  }

  .organizer-avatar {
    width: 22px;
    height: 22px;
    font-size: 0.6rem;
  }

  .nav-tabs .nav-link {
    padding: 0.5rem 0.75rem;
    font-size: 0.9rem;
    margin-right: 0.25rem;
  }
}

/* Mobile Responsive */
@media (max-width: 576px) {
  h2 {
    font-size: 1.5rem;
  }

  .contest-card {
    padding: 0.875rem;
  }

  .contest-title-link {
    font-size: 1.1rem;
  }

  .contest-timestamp {
    font-size: 0.75rem;
  }

  .contest-tags {
    gap: 0.3rem;
  }

  .contest-tag {
    font-size: 0.65rem;
    padding: 0.2rem 0.4rem;
  }

  .organizers-section {
    padding: 0.2rem 0.4rem;
  }

  .organizers-label {
    font-size: 0.65rem;
  }

  .organizer-avatar {
    width: 20px;
    height: 20px;
    font-size: 0.55rem;
    border-width: 1.5px;
  }

  .nav-tabs {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .nav-tabs .nav-link {
    white-space: nowrap;
    padding: 0.5rem;
    font-size: 0.85rem;
  }

  .btn-primary {
    font-size: 0.9rem;
    padding: 0.5rem 0.75rem;
  }
}
</style>
