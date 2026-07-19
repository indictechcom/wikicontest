<template>
  <div class="container py-5">
    <h2 class="mb-4 page-header">Organizer Dashboard</h2>

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

    <div v-else-if="dashboardData">
      <h4 class="mb-3">Your Contests</h4>

      <!-- Empty State -->
      <div v-if="organizedContests.length === 0" class="text-center py-5 px-3">
        <div class="empty-state">
          <i class="fas fa-folder-open empty-icon"></i>
          <p class="text-muted mb-3 no-contests">You haven't created any contests yet.</p>
          <router-link v-if="canCreateContests" to="/contest/create" class="btn btn-primary">
            <i class="fas fa-plus me-2"></i>Create Contest
          </router-link>
        </div>
      </div>

      <!-- Contest Management Cards -->
      <div v-else class="row g-4">
        <div v-for="contest in organizedContests" :key="contest.id" class="col-12 col-md-6 col-lg-4">
          <div class="card contest-management-card h-100">
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-start mb-2">
                <h5 class="card-title mb-0 contest-card-title">{{ contest.name }}</h5>
                <span class="status-badge ms-2" :class="`status-${getStatusBadgeColor(contest.status)}`">
                  <i :class="getStatusIcon(contest.status)"></i>
                  {{ getStatusLabel(contest.status) }}
                </span>
              </div>
              <p class="text-muted small mb-2">
                <i class="fas fa-briefcase me-1"></i>{{ contest.project_name || 'N/A' }}
              </p>
              <p v-if="contest.start_date || contest.end_date" class="text-muted small mb-2">
                <i class="fas fa-calendar-alt me-1"></i>
                {{ formatDateRange(contest.start_date, contest.end_date) }}
              </p>
              <p class="small text-muted mb-0">
                <i class="fas fa-file-alt me-1"></i>{{ contest.submission_count || 0 }} submissions
              </p>
            </div>
            <div class="card-footer bg-transparent border-top d-flex gap-2 flex-wrap">
              <router-link :to="`/contest/${contest.slug}/edit`"
                class="btn btn-sm btn-outline-primary"
                @click.prevent>
                <i class="fas fa-edit me-1"></i>Edit
              </router-link>
              <router-link v-if="contest.scoring_parameters && !contest.scoring_parameters.enabled"
                :to="`/contest/${contest.slug}/leaderboard`"
                class="btn btn-sm btn-outline-primary"
                @click.prevent>
                <i class="fas fa-trophy me-1"></i>Leaderboard
              </router-link>
              <router-link :to="`/contest/${contest.slug}`" class="btn btn-sm btn-outline-secondary" @click.prevent>
                <i class="fas fa-eye me-1"></i>View
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useStore } from '../store'
import api from '../services/api'
import { showAlert } from '../utils/alerts'

export default {
  name: 'OrganizerDashboard',
  setup() {
    const store = useStore()
    const dashboardData = ref(null)
    const loading = ref(true)
    const error = ref(null)

    // Organized contests data
    const organizedContests = computed(() => {
      return dashboardData.value?.organized_contests || []
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

    // Get status badge color for contest status
    const getStatusBadgeColor = (status) => {
      const statusColors = {
        current: 'success',
        active: 'success',
        upcoming: 'warning',
        past: 'secondary',
        completed: 'info'
      }
      return statusColors[status?.toLowerCase()] || 'primary'
    }

    // Get status icon for contest status
    const getStatusIcon = (status) => {
      const icons = {
        current: 'fas fa-circle-dot',
        active: 'fas fa-circle-dot',
        upcoming: 'fas fa-clock',
        past: 'fas fa-check-circle',
        completed: 'fas fa-check-circle'
      }
      return icons[status?.toLowerCase()] || 'fas fa-circle'
    }

    // Get status label for contest status
    const getStatusLabel = (status) => {
      const labels = {
        current: 'Active',
        upcoming: 'Upcoming',
        past: 'Past',
        active: 'Active',
        completed: 'Completed',
        unknown: 'Unknown'
      }
      return labels[status?.toLowerCase()] || 'Unknown'
    }

    // Format date range for display
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

    onMounted(() => {
      loadDashboard()
    })

    return {
      dashboardData,
      loading,
      error,
      organizedContests,
      canCreateContests,
      getStatusBadgeColor,
      getStatusIcon,
      getStatusLabel,
      formatDateRange
    }
  }
}
</script>

<style scoped>
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

h4 {
  color: var(--wiki-dark);
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 1rem;
  letter-spacing: -0.01em;
}

[data-theme="dark"] h4 {
  color: #ffffff !important;
}

.card {
  border-radius: 4px;
  border: 1px solid var(--wiki-border);
  background-color: var(--wiki-card-bg);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
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

.card-body {
  padding: 1.5rem;
}

.card-title {
  color: var(--wiki-text-muted);
  font-weight: 500;
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

[data-theme="dark"] .card-title {
  color: #b8b8b8 !important;
}

/* Contest Management Card */
.contest-management-card {
  transition: all 0.2s ease;
}

.contest-management-card:hover {
  border-color: var(--wiki-primary);
  box-shadow: 0 4px 12px rgba(0, 102, 153, 0.1);
}

.contest-card-title {
  color: var(--wiki-dark);
  font-size: 1rem;
  font-weight: 600;
}

[data-theme="dark"] .contest-card-title {
  color: #ffffff !important;
}

.contest-management-card .card-footer {
  display: flex;
  gap: 0.5rem;
}

/* Status badge */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.3em 0.65em;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 500;
  letter-spacing: 0.2px;
}

.status-badge i {
  font-size: 0.65rem;
}

/* Status badge variants */
.status-success {
  background-color: rgba(51, 153, 102, 0.12);
  color: #2a7a52;
  border: 1px solid rgba(51, 153, 102, 0.3);
}

.status-warning {
  background-color: rgba(255, 193, 7, 0.12);
  color: #9a7200;
  border: 1px solid rgba(255, 193, 7, 0.3);
}

.status-secondary {
  background-color: rgba(108, 117, 125, 0.1);
  color: #5a6268;
  border: 1px solid rgba(108, 117, 125, 0.25);
}

.status-info {
  background-color: rgba(0, 102, 153, 0.1);
  color: #006699;
  border: 1px solid rgba(0, 102, 153, 0.25);
}

.status-primary {
  background-color: rgba(0, 102, 153, 0.1);
  color: #006699;
  border: 1px solid rgba(0, 102, 153, 0.25);
}

[data-theme="dark"] .status-success {
  background-color: rgba(51, 153, 102, 0.15);
  color: #5dc89a;
  border-color: rgba(51, 153, 102, 0.25);
}

[data-theme="dark"] .status-warning {
  background-color: rgba(255, 193, 7, 0.12);
  color: #ffc107;
  border-color: rgba(255, 193, 7, 0.25);
}

[data-theme="dark"] .status-secondary {
  background-color: rgba(255, 255, 255, 0.06);
  color: #9a9a9a;
  border-color: rgba(255, 255, 255, 0.12);
}

[data-theme="dark"] .status-info,
[data-theme="dark"] .status-primary {
  background-color: rgba(0, 102, 153, 0.15);
  color: #5db8e6;
  border-color: rgba(0, 102, 153, 0.25);
}

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.empty-icon {
  font-size: 2.5rem;
  color: var(--wiki-text-muted);
  opacity: 0.4;
}

/* Spinner */
.spinner-border.text-primary {
  width: 3rem;
  height: 3rem;
  border-width: 0.25em;
  color: var(--wiki-primary);
}

[data-theme="dark"] .text-muted {
  color: #b8b8b8 !important;
}

[data-theme="dark"] .no-contests {
  color: #b8b8b8 !important;
}

/* Responsive */
@media (max-width: 768px) {
  h2.page-header {
    font-size: 1.75rem;
  }

  h4 {
    font-size: 1.125rem;
  }

  .card-body {
    padding: 1.25rem;
  }
}
</style>
