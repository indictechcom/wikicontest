<template>
  <div class="container py-5">
    <!-- Page Header with Create Button -->
    <div class="d-flex flex-column flex-sm-row justify-content-between align-items-start align-items-sm-center mb-4">
      <h2 class="page-header mb-0">Organizer Dashboard</h2>
      <!-- Show Create Contest button for superadmin users (they can create contests directly) -->
      <button
        v-if="canCreateContests"
        class="btn btn-primary mt-2 mt-sm-0"
        @click="showCreateContestModal"
      >
        <i class="fas fa-plus me-2"></i>Create Contest
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="alert alert-danger">
      <i class="fas fa-exclamation-circle me-2"></i>{{ error }}
      <button class="btn btn-sm btn-outline-danger ms-3" @click="loadDashboard">Retry</button>
    </div>

    <!-- Contest Content -->
    <div v-else-if="dashboardData">
      <!-- Contest Category Tabs -->
      <ul class="nav nav-tabs mb-4" id="organizerTabs">
        <li class="nav-item">
          <button class="nav-link"
            :class="{ active: activeCategory === 'current' }"
            @click="setActiveCategory('current')">
            Current
          </button>
        </li>
        <li class="nav-item">
          <button class="nav-link"
            :class="{ active: activeCategory === 'upcoming' }"
            @click="setActiveCategory('upcoming')">
            Upcoming
          </button>
        </li>
        <li class="nav-item">
          <button class="nav-link" :class="{ active: activeCategory === 'past' }" @click="setActiveCategory('past')">
            Past
          </button>
        </li>
      </ul>

      <!-- Contest List -->
      <div id="contestList">
        <!-- Empty State Message -->
        <div v-if="filteredContests.length === 0" class="alert alert-info text-center">
          <i class="fas fa-info-circle me-2"></i>
          No {{ activeCategory }} contests available.
        </div>

        <!-- Contest Cards -->
        <div v-else class="contest-list">
          <div v-for="contest in filteredContests"
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
                <div class="organizers-section" v-if="getOrganizers(contest).length > 0">
                  <span class="organizers-label"><i class="fas fa-user-cog"></i>
                  </span>
                  <div class="organizers-avatars">
                    <div v-for="(organizer, index) in getOrganizers(contest)"
                      :key="index"
                      class="organizer-avatar"
                      :title="organizer">
                      {{ getInitials(organizer) }}
                    </div>
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
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useStore } from '../store'
import api from '../services/api'
import { showAlert } from '../utils/alerts'

export default {
  name: 'OrganizerDashboard',
  setup() {
    const router = useRouter()
    const route = useRoute()
    const store = useStore()
    const VALID_CATEGORIES = ['current', 'upcoming', 'past']
    const dashboardData = ref(null)
    const loading = ref(true)
    const error = ref(null)
    const activeCategory = ref('current')

    // Restore the active subsection from the URL query parameter (?tab=...)
    const getCategoryFromUrl = () => {
      const tab = route.query.tab
      return VALID_CATEGORIES.includes(tab) ? tab : 'current'
    }

    // Reflect the active subsection in the URL without adding history entries.
    // The URL always shows the current tab, including the default "current".
    const syncUrlWithCategory = (category) => {
      if (route.query.tab !== category) {
        router.replace({ query: { ...route.query, tab: category } })
      }
    }

    // Organized contests data
    const organizedContests = computed(() => {
      return dashboardData.value?.organized_contests || []
    })

    // Get contests for currently selected category
    const filteredContests = computed(() => {
      return organizedContests.value.filter(c => c.status === activeCategory.value)
    })

    // Check if user can create contests
    const canCreateContests = computed(() => {
      const user = store.currentUser.value
      if (!user) return false
      const role = String(user.role || '').toLowerCase().trim()
      return role === 'superadmin' || user.is_trusted_member === true
    })

    // Load dashboard data
    const loadDashboard = async () => {
      loading.value = true
      error.value = null
      try {
        const data = await api.get('/user/dashboard')
        dashboardData.value = data
      } catch (err) {
        error.value = err.message || 'Failed to load dashboard'
        showAlert(error.value, 'danger')
      } finally {
        loading.value = false
      }
    }

    // Navigate to contest detail page using slugified name
    const viewContest = (contest) => {
      router.push({ name: 'ContestView', params: { name: contest.slug || contest.name } })
    }

    // Navigate to contest creation page
    const showCreateContestModal = () => {
      router.push({ name: 'CreateContest' })
    }

    // Switch between current, upcoming, and past contests
    const setActiveCategory = (category) => {
      activeCategory.value = category
      syncUrlWithCategory(category)
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
        return (parts[0][0] + parts[1][0]).toUpperCase()
      } else {
        return username.substring(0, 2).toUpperCase()
      }
    }

    // Generate consistent color for avatar based on username hash
    const getAvatarColor = (username) => {
      if (!username) return '#6c757d'

      let hash = 0
      for (let i = 0; i < username.length; i++) {
        hash = username.charCodeAt(i) + ((hash << 5) - hash)
      }

      const hue = hash % 360
      return `hsl(${hue}, 65%, 50%)`
    }

    // Load contests on component mount
    onMounted(async () => {
      // Restore the active subsection from the shared URL, if present
      activeCategory.value = getCategoryFromUrl()
      // Default the URL bar to showing the current tab
      syncUrlWithCategory(activeCategory.value)
      await loadDashboard()
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
      dashboardData,
      loading,
      error,
      organizedContests,
      filteredContests,
      activeCategory,
      canCreateContests,
      viewContest,
      showCreateContestModal,
      setActiveCategory,
      formatDate,
      formatDateRange,
      getStatusLabel,
      getStatusClass,
      getStatusIcon,
      getOrganizers,
      getInitials,
      getAvatarColor
    }
  }
}
</script>

<style scoped>
/* Page Title / Header */
h2.page-header {
  font-size: 2rem;
  font-weight: 600;
  color: var(--wiki-dark);
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

/* Category Navigation Tabs */
.nav-tabs {
  border-bottom: 1px solid var(--wiki-border);
  margin-bottom: 2rem;
  transition: border-color 0.3s ease;
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
    border-width: 1.5rem;
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
