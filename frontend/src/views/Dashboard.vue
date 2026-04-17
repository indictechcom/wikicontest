<template>
  <div class="container py-5">
    <h2 class="mb-4 page-header">Dashboard</h2>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
    </div>

    <!-- Dashboard Content -->
    <div v-else-if="dashboardData">
      <!-- Statistics Cards -->
      <div class="row mb-4">
        <div class="col-12 col-sm-6 col-md-4 mb-3 mb-md-4">
          <div class="card text-center h-100">
            <div class="card-body">
              <h5 class="card-title">Total Score</h5>
              <h2 class="text-primary">{{ dashboardData.total_score || 0 }}</h2>
            </div>
          </div>
        </div>
        <div class="col-12 col-sm-6 col-md-4 mb-3 mb-md-4">
          <div class="card text-center h-100">
            <div class="card-body">
              <h5 class="card-title">Participated Contests</h5>
              <h2 class="text-success">{{ dashboardData.participated_contests?.length || 0 }}</h2>
            </div>
          </div>
        </div>
        <div class="col-12 col-sm-6 col-md-4 mb-3 mb-md-4">
          <div class="card text-center h-100">
            <div class="card-body">
              <h5 class="card-title">Jury Member</h5>
              <h2 class="text-warning">{{ dashboardData.jury_contests?.length || 0 }}</h2>
            </div>
          </div>
        </div>
      </div>

      <!-- Submissions and Scores -->
      <div class="row">
        <!-- Recent Submissions -->
        <div class="col-12 col-md-6 mb-3 mb-md-4">
          <h4 class="mb-3">Recent Submissions</h4>
          <div class="card h-100">
            <div class="card-body p-0">
              <div v-if="dashboardData.submissions_by_contest?.length > 0" class="scroll-area">
                <div class="scroll-inner">
                  <div v-for="contest in dashboardData.submissions_by_contest" :key="contest.contest_id"
                    class="contest-group">
                    <h6 class="contest-group-title">{{ contest.contest_name }}</h6>
                    <div v-for="submission in contest.submissions" :key="submission.id"
                      class="submission-item d-flex justify-content-between align-items-center mb-2 flex-wrap"
                      :class="{ 'submission-clickable': submission.reviewed_at }"
                      @click="handleSubmissionClick(submission)">
                      <span class="me-2 mb-1 submission-title">
                        {{ submission.article_title }}
                      </span>
                      <div class="d-flex align-items-center gap-2">
                        <span :class="`badge bg-${getStatusColor(submission.status)}`">
                          {{ submission.status }}
                        </span>
                        <button v-if="submission.reviewed_at" class="btn btn-sm btn-info feedback-btn"
                          @click.stop="openFeedbackModal(submission)" title="View Feedback">
                          <i class="fas fa-comment-dots"></i>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <p v-else class="text-muted no-submissions px-3 py-3">No submissions yet.</p>
            </div>
          </div>
        </div>

        <!-- Contest Scores -->
        <div class="col-12 col-md-6 mb-3 mb-md-4">
          <h4 class="mb-3">Contest Scores</h4>
          <div class="card h-100">
            <div class="card-body p-0">
              <div v-if="dashboardData.contest_wise_scores?.length > 0" class="scroll-area">
                <div class="scroll-inner">
                  <div v-for="score in dashboardData.contest_wise_scores" :key="score.contest_id"
                    class="score-item d-flex justify-content-between align-items-center flex-wrap">
                    <span class="score-name me-2">{{ score.contest_name }}</span>
                    <span class="badge bg-primary">{{ score.contest_score }} points</span>
                  </div>
                </div>
              </div>
              <p v-else class="text-muted no-scores px-3 py-3">No scores yet.</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Participated Contests Table -->
      <div class="row mt-4">
        <div class="col-12">
          <h4 class="mb-3">Participated Contests</h4>
          <div class="card contests-table-card">
            <div class="card-body p-0">

              <div v-if="dashboardData.participated_contests?.length > 0" class="table-responsive">
                <table class="table table-hover mb-0">
                  <thead>
                    <tr>
                      <th scope="col">Contest Name</th>
                      <th scope="col">Project</th>
                      <th scope="col">Status</th>
                      <th scope="col">Submitted On</th>
                      <th scope="col">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="contest in paginatedContests" :key="contest.id" @click="viewContest(contest.id)"
                      class="table-row-clickable">
                      <td>
                        <div class="contest-name-cell">
                          <i class="fas fa-trophy contest-icon"></i>
                          <strong>{{ contest.name }}</strong>
                        </div>
                      </td>
                      <td>
                        <span class="project-name">{{ contest.project_name || 'N/A' }}</span>
                      </td>
                      <td>
                        <span class="status-badge" :class="`status-${getStatusBadgeColor(contest.status)}`">
                          <i :class="getStatusIcon(contest.status)"></i>
                          {{ contest.status || 'Unknown' }}
                        </span>
                      </td>
                      <td>
                        <span class="date-cell">
                          <i class="fas fa-calendar-alt date-icon"></i>
                          {{ formatDate(contest.submitted_at) }}
                        </span>
                      </td>
                      <td>
                        <button class="btn btn-sm view-btn" @click.stop="viewContest(contest.id)">
                          <i class="fas fa-eye me-1"></i>View
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>

                <!-- Pagination Controls -->
                <div v-if="totalPages > 1"
                  class="d-flex justify-content-between align-items-center flex-wrap gap-2 px-3 py-2 border-top pagination-bar">
                  <span class="pagination-info">
                    Showing {{ (currentPage - 1) * itemsPerPage + 1 }}–{{ Math.min(currentPage * itemsPerPage,
                      dashboardData.participated_contests.length) }}
                    of {{ dashboardData.participated_contests.length }} contests
                  </span>
                  <div class="d-flex gap-1 flex-wrap">
                    <button class="btn btn-sm btn-outline-secondary pg-btn" :disabled="currentPage === 1"
                      @click="currentPage--">
                      ‹ Prev
                    </button>
                    <button v-for="page in totalPages" :key="page" class="btn btn-sm pg-btn"
                      :class="page === currentPage ? 'btn-primary pg-active' : 'btn-outline-secondary'"
                      @click="currentPage = page">
                      {{ page }}
                    </button>
                    <button class="btn btn-sm btn-outline-secondary pg-btn" :disabled="currentPage === totalPages"
                      @click="currentPage++">
                      Next ›
                    </button>
                  </div>
                </div>

              </div>

              <div v-else class="text-center py-5 px-3">
                <div class="empty-state">
                  <i class="fas fa-inbox empty-icon"></i>
                  <p class="text-muted mb-0 no-contests">
                    You haven't participated in any contests yet.
                  </p>
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="alert alert-danger">
      {{ error }}
    </div>

    <!-- Submit Article Modal -->
    <SubmitArticleModal v-if="submittingToContestId" :contest-id="submittingToContestId"
      @submitted="handleArticleSubmitted" />

    <!-- Jury Feedback Modal -->
    <JuryFeedbackModal :submission="selectedSubmission" :reviewer-name="reviewerName"
      :loading-reviewer="loadingReviewer" />
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useStore } from '../store'
import api from '../services/api'
import { showAlert } from '../utils/alerts'
import { slugify } from '../utils/slugify'
import SubmitArticleModal from '../components/SubmitArticleModal.vue'
import JuryFeedbackModal from '../components/JuryFeedbackModal.vue'

export default {
  name: 'Dashboard',
  components: {
    SubmitArticleModal,
    JuryFeedbackModal
  },
  setup() {
    const router = useRouter()
    const store = useStore()
    const dashboardData = ref(null)
    const loading = ref(true)
    const error = ref(null)
    const submittingToContestId = ref(null)

    // Feedback modal state
    const selectedSubmission = ref(null)
    const reviewerName = ref('')
    const loadingReviewer = ref(false)

    // Pagination state
    const currentPage = ref(1)
    const itemsPerPage = 5

    // Paginated contests computed
    const paginatedContests = computed(() => {
      const contests = dashboardData.value?.participated_contests || []
      const start = (currentPage.value - 1) * itemsPerPage
      return contests.slice(start, start + itemsPerPage)
    })

    // Total pages computed
    const totalPages = computed(() => {
      const total = dashboardData.value?.participated_contests?.length || 0
      return Math.ceil(total / itemsPerPage)
    })

    // Load dashboard data
    const loadDashboard = async () => {
      loading.value = true
      error.value = null
      currentPage.value = 1
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

    // Get status color for badges
    const getStatusColor = (status) => {
      const statusColors = {
        accepted: 'success',
        rejected: 'danger',
        pending: 'warning'
      }
      return statusColors[status] || 'secondary'
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

    // Format date for display
    const formatDate = (dateString) => {
      if (!dateString) return 'N/A'
      try {
        const date = new Date(dateString)
        return date.toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'short',
          day: 'numeric'
        })
      } catch (e) {
        return dateString
      }
    }

    // Handle submission click (only if reviewed)
    const handleSubmissionClick = (submission) => {
      if (submission.reviewed_at) {
        openFeedbackModal(submission)
      }
    }

    // Fetch reviewer username
    const fetchReviewerName = async (reviewerId) => {
      if (!reviewerId) {
        reviewerName.value = 'Jury Member'
        return
      }

      loadingReviewer.value = true
      try {
        const userData = await api.get(`/user/${reviewerId}/username`)
        if (userData && userData.username) {
          reviewerName.value = userData.username
        } else {
          reviewerName.value = 'Jury Member'
        }
      } catch (err) {
        console.warn('Could not fetch reviewer name:', err)
        reviewerName.value = 'Jury Member'
      } finally {
        loadingReviewer.value = false
      }
    }

    // Open feedback modal
    const openFeedbackModal = async (submission) => {
      if (!submission || !submission.reviewed_at) {
        showAlert('This submission has not been reviewed yet', 'info')
        return
      }

      selectedSubmission.value = submission

      if (submission.reviewed_by) {
        await fetchReviewerName(submission.reviewed_by)
      } else {
        reviewerName.value = 'Jury Member'
      }

      const modalEl = document.getElementById('juryFeedbackModal')
      if (!modalEl) {
        console.error('JuryFeedbackModal DOM not found')
        return
      }

      const modal = new window.bootstrap.Modal(modalEl)
      modal.show()
    }

    // View contest details - navigate to full page view
    const viewContest = (contestId) => {
      let contestData = null

      if (dashboardData.value?.created_contests) {
        contestData = dashboardData.value.created_contests.find(c => c.id === contestId)
      }

      if (!contestData && dashboardData.value?.participated_contests) {
        contestData = dashboardData.value.participated_contests.find(c => c.id === contestId)
      }

      if (!contestData) {
        api.get(`/contest/${contestId}`)
          .then(contest => {
            if (contest?.name) {
              router.push({ name: 'ContestView', params: { name: slugify(contest.name) } })
            } else {
              showAlert('Contest not found', 'danger')
            }
          })
          .catch(err => showAlert('Failed to load contest: ' + err.message, 'danger'))
        return
      }

      if (contestData?.name) {
        router.push({ name: 'ContestView', params: { name: slugify(contestData.name) } })
      } else {
        showAlert('Contest not found', 'danger')
      }
    }

    // Handle submit article
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

    // Handle article submitted
    const handleArticleSubmitted = () => {
      submittingToContestId.value = null
      loadDashboard()
    }

    // Load data on mount
    onMounted(() => {
      loadDashboard()
    })

    return {
      dashboardData,
      loading,
      error,
      submittingToContestId,
      selectedSubmission,
      reviewerName,
      loadingReviewer,
      currentPage,
      itemsPerPage,
      totalPages,
      paginatedContests,
      getStatusColor,
      getStatusBadgeColor,
      getStatusIcon,
      formatDate,
      viewContest,
      handleSubmitArticle,
      handleArticleSubmitted,
      handleSubmissionClick,
      openFeedbackModal
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

h2.text-primary,
h2.text-success,
h2.text-warning {
  font-size: 2.5rem !important;
  font-weight: 700;
  margin: 0;
}

[data-theme="dark"] h2.text-primary {
  color: #006699 !important;
}

[data-theme="dark"] h2.text-success {
  color: #339966 !important;
}

[data-theme="dark"] h2.text-warning {
  color: #ffc107 !important;
}



.scroll-area {
  max-height: 700px;
  overflow-y: auto;
  overflow-x: hidden;
}

.scroll-area::-webkit-scrollbar {
  width: 5px;
}

.scroll-area::-webkit-scrollbar-track {
  background: transparent;
}

.scroll-area::-webkit-scrollbar-thumb {
  background: var(--wiki-border);
  border-radius: 10px;
}

.scroll-area::-webkit-scrollbar-thumb:hover {
  background: var(--wiki-primary);
}

[data-theme="dark"] .scroll-area::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
}

[data-theme="dark"] .scroll-area::-webkit-scrollbar-thumb:hover {
  background: #006699;
}

.scroll-inner {
  padding: 1rem;
}




.contest-group {
  margin-bottom: 1rem;
}

.contest-group:last-child {
  margin-bottom: 0;
}

.contest-group-title {
  font-weight: 600;
  color: var(--wiki-dark);
  margin-bottom: 0.5rem;
  font-size: 0.95rem;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid var(--wiki-border);
}

[data-theme="dark"] .contest-group-title {
  color: #ffffff !important;
  border-bottom-color: rgba(255, 255, 255, 0.1);
}


.score-item {
  background-color: var(--wiki-light-bg);
  border: 1px solid var(--wiki-border);
  border-radius: 4px;
  padding: 0.75rem 1rem;
  margin-bottom: 0.5rem;
  transition: all 0.2s ease;
}

.score-item:last-child {
  margin-bottom: 0;
}

.score-item:hover {
  background-color: var(--wiki-hover-bg);
  border-color: var(--wiki-primary);
}

.score-name {
  font-size: 0.9rem;
  color: var(--wiki-dark);
}

[data-theme="dark"] .score-item {
  background-color: rgba(93, 184, 230, 0.05);
}

[data-theme="dark"] .score-name {
  color: #ffffff !important;
}



.submission-item {
  background-color: var(--wiki-light-bg);
  border: 1px solid var(--wiki-border);
  border-radius: 4px;
  padding: 0.75rem 1rem;
  margin-bottom: 0.5rem;
  transition: all 0.2s ease;
}

[data-theme="dark"] .submission-item {
  background-color: rgba(93, 184, 230, 0.05);
}

.submission-clickable {
  cursor: pointer;
}

.submission-clickable:hover {
  background-color: var(--wiki-hover-bg);
  border-color: var(--wiki-primary);
  transform: translateX(2px);
}

.submission-clickable:hover .submission-title {
  color: var(--wiki-primary);
}

[data-theme="dark"] .submission-item span {
  color: #ffffff !important;
}

.feedback-btn {
  color: white;
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
  transition: all 0.2s ease;
}

.feedback-btn:hover {
  transform: scale(1.05);
}

.feedback-btn i {
  font-size: 0.875rem;
}

h6 {
  font-weight: 600;
  color: var(--wiki-dark);
  margin: 0;
  font-size: 1rem;
}

[data-theme="dark"] h6 {
  color: #ffffff !important;
}

.badge {
  padding: 0.35em 0.7em;
  border-radius: 4px;
  font-weight: 500;
  font-size: 0.85rem;
}

[data-theme="dark"] .badge.bg-primary {
  background-color: #006699 !important;
  color: #ffffff !important;
}

[data-theme="dark"] .badge.bg-success {
  background-color: #339966 !important;
  color: #ffffff !important;
}

[data-theme="dark"] .badge.bg-warning {
  background-color: #ffc107 !important;
  color: #000000 !important;
}

[data-theme="dark"] .badge.bg-danger {
  background-color: #990000 !important;
  color: #ffffff !important;
}



.contests-table-card {
  overflow: hidden;
}

.table {
  margin-bottom: 0;
  color: var(--wiki-dark);
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

.table thead th {
  background-color: var(--wiki-light-bg);
  border-bottom: 2px solid var(--wiki-border);
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.8rem;
  letter-spacing: 0.6px;
  color: var(--wiki-text-muted);
  padding: 0.85rem 1rem;
  position: sticky;
  top: 0;
  z-index: 10;
}

[data-theme="dark"] .table thead th {
  background-color: rgba(93, 184, 230, 0.1);
  border-bottom-color: var(--wiki-border);
  color: #b8b8b8 !important;
}

.table tbody td {
  padding: 0.9rem 1rem;
  vertical-align: middle;
  border-bottom: 1px solid var(--wiki-border);
  background-color: var(--wiki-card-bg);
  font-size: 0.92rem;
}

[data-theme="dark"] .table tbody td {
  background-color: var(--wiki-card-bg);
  color: #ffffff !important;
}

[data-theme="dark"] .table tbody td strong {
  color: #ffffff !important;
}

.table tbody tr {
  transition: all 0.2s ease;
  background-color: var(--wiki-card-bg);
}

.table-row-clickable {
  cursor: pointer;
}

.table-row-clickable:hover td {
  background-color: var(--wiki-hover-bg) !important;
}

[data-theme="dark"] .table-row-clickable:hover td {
  background-color: rgba(0, 102, 153, 0.08) !important;
}

.table tbody tr:last-child td {
  border-bottom: none;
}

.table-responsive {
  border-radius: 4px;
  overflow: hidden;
}

/* Contest name cell */
.contest-name-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.contest-icon {
  color: var(--wiki-primary);
  font-size: 0.8rem;
  opacity: 0.7;
  flex-shrink: 0;
}

[data-theme="dark"] .contest-icon {
  color: #006699 !important;
}

/* Project name */
.project-name {
  color: var(--wiki-text-muted);
  font-size: 0.88rem;
}

[data-theme="dark"] .project-name {
  color: #b8b8b8 !important;
}

/* Date cell */
.date-cell {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.88rem;
  color: var(--wiki-text-muted);
}

.date-icon {
  font-size: 0.78rem;
  opacity: 0.6;
}

[data-theme="dark"] .date-cell {
  color: #b8b8b8 !important;
}

/* Status badge (custom — replaces plain Bootstrap badge in table) */
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

/* View button */
.view-btn {
  background-color: transparent;
  border: 1px solid var(--wiki-primary);
  color: var(--wiki-primary);
  border-radius: 4px;
  padding: 0.25rem 0.75rem;
  font-size: 0.82rem;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.view-btn:hover {
  background-color: var(--wiki-primary);
  color: #ffffff;
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(0, 102, 153, 0.25);
}

[data-theme="dark"] .view-btn {
  border-color: #006699;
  color: #5db8e6;
}

[data-theme="dark"] .view-btn:hover {
  background-color: #006699;
  color: #ffffff;
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



.pagination-bar {
  background-color: var(--wiki-light-bg);
  border-top: 1px solid var(--wiki-border) !important;
}

[data-theme="dark"] .pagination-bar {
  background-color: rgba(93, 184, 230, 0.05);
}

.pagination-info {
  font-size: 0.85rem;
  color: var(--wiki-text-muted);
}

[data-theme="dark"] .pagination-info {
  color: #b8b8b8 !important;
}

.pg-btn {
  min-width: 36px;
  border-radius: 4px !important;
  font-size: 0.85rem;
  transition: all 0.15s ease;
}

.pg-btn:not(.pg-active):not(:disabled):hover {
  border-color: var(--wiki-primary);
  color: var(--wiki-primary);
}

.pg-active {
  background-color: var(--wiki-primary) !important;
  border-color: var(--wiki-primary) !important;
  color: #ffffff !important;
}

[data-theme="dark"] .pg-btn {
  border-color: var(--wiki-border);
  color: #ffffff;
  background-color: transparent;
}

[data-theme="dark"] .pg-btn:not(.pg-active):not(:disabled):hover {
  border-color: #006699;
  color: #006699;
}

[data-theme="dark"] .pg-active {
  background-color: #006699 !important;
  border-color: #006699 !important;
  color: #ffffff !important;
}

[data-theme="dark"] .pg-btn:disabled {
  color: #555 !important;
  border-color: #333 !important;
}



.spinner-border.text-primary {
  width: 3rem;
  height: 3rem;
  border-width: 0.25em;
  color: var(--wiki-primary);
}



[data-theme="dark"] .text-muted {
  color: #b8b8b8 !important;
}

[data-theme="dark"] .no-submissions,
[data-theme="dark"] .no-scores,
[data-theme="dark"] .no-contests {
  color: #b8b8b8 !important;
}



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

  h2.text-primary,
  h2.text-success,
  h2.text-warning {
    font-size: 2rem !important;
  }

  .submission-item {
    flex-direction: column;
    align-items: flex-start !important;
  }

  .submission-item>div {
    margin-top: 0.5rem;
    width: 100%;
    justify-content: space-between;
  }

  .pagination-bar {
    flex-direction: column;
    align-items: flex-start !important;
    gap: 0.5rem;
  }

  .scroll-area {
    max-height: 500px;
  }

  .contest-name-cell {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }
}
</style>