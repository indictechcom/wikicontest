<template>
  <div class="container py-5">
    <!-- Navigation and Action Buttons -->
    <div class="mb-4 d-flex justify-content-between align-items-center">
      <button class="btn btn-outline-secondary" @click="goBack">
        <i class="fas fa-arrow-left me-2"></i>Back to Contest
      </button>
      <div class="d-flex gap-2">
        <button
          v-if="canViewSubmissions && canEditOrDelete"
          class="btn btn-primary"
          @click="goToEditPage"
        >
          <i class="fas fa-edit me-2"></i>Edit Contest
        </button>
        <button
          v-if="canViewSubmissions && canDeleteContest"
          class="btn btn-danger"
          @click="handleDeleteContest"
          :disabled="deletingContest"
        >
          <span v-if="deletingContest" class="spinner-border spinner-border-sm me-2"></span>
            <i v-else class="fas fa-trash me-2"></i>
          {{ deletingContest ? 'Deleting...' : 'Delete Contest' }}
        </button>
      </div>
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
      <button class="btn btn-sm btn-outline-danger ms-3" @-click="goBack">Go Back</button>
    </div>

    <!-- Contest Details and Submissions -->
    <div v-else-if="contest" class="contest-view">
      <!-- Header Section -->
      <div class="contest-header-section mb-4">
        <h1 class="contest-title">{{ contest.name }}</h1>
        <div class="contest-meta">
          <span class="badge bg-primary me-2">{{ getStatusLabel(contest.status) }}</span>
          <span class="text-muted">
            <i class="fas fa-calendar-alt me-1"></i>
            Created {{ formatDate(contest.created_at) }}
          </span>
        </div>
      </div>

      <!-- Submissions Table (Visible to Jury and Organizers) -->
      <div v-if="canViewSubmissions" class="card mb-4">
        <div class="card-header">
          <div class="d-flex justify-content-between align-items-center">
            <h5 class="mb-0"><i class="fas fa-file-alt me-2"></i>Submissions</h5>
<div class="d-flex align-items-center gap-2">
  <!-- Loading/Refreshing state -->
  <button v-if="loadingSubmissions"
    class="btn btn-sm btn-outline-secondary"
    disabled>
    <span class="spinner-border spinner-border-sm me-2"></span>Loading...
  </button>
  <!-- Refresh metadata fetches latest article data from MediaWiki -->
  <button v-else
    class="btn btn-sm btn-outline-light"
    @click="refreshMetadata"
    :disabled="submissions.length === 0"
    title="Refresh article metadata"
    style="color: white; border-color: white;"
  >
    <i class="fas fa-database me-1"></i>Refresh Metadata
  </button>
</div>
          </div>
        </div>
        <div class="card-body">
          <!-- Filter Tabs (automated scoring only) -->
          <div v-if="contestScoringMode === 'automated' && submissions.length > 0" class="mb-3">
            <div class="btn-group" role="group" aria-label="Filter submissions">
              <button
                type="button"
                class="btn btn-sm"
                :class="submissionFilter === 'all' ? 'btn-primary' : 'btn-outline-primary'"
                @click="submissionFilter = 'all'"
              >
                All <span class="badge bg-light text-dark ms-1">{{ submissions.length }}</span>
              </button>
              <button
                type="button"
                class="btn btn-sm"
                :class="submissionFilter === 'accepted' ? 'btn-success' : 'btn-outline-success'"
                @click="submissionFilter = 'accepted'"
              >
                Accepted
                <span class="badge bg-light text-dark ms-1">
                  {{ submissions.filter(s => s.status === 'accepted').length }}
                </span>
              </button>
              <button
                type="button"
                class="btn btn-sm"
                :class="submissionFilter === 'rejected' ? 'btn-danger' : 'btn-outline-danger'"
                @click="submissionFilter = 'rejected'"
              >
                Rejected
                <span class="badge bg-light text-dark ms-1">
                  {{ submissions.filter(s => s.status === 'rejected').length }}
                </span>
              </button>
              <button
                type="button"
                class="btn btn-sm"
                :class="submissionFilter === 'pending' ? 'btn-warning' : 'btn-outline-warning'"
                @click="submissionFilter = 'pending'"
              >
                Pending
                <span class="badge bg-light text-dark ms-1">
                  {{ submissions.filter(s => s.status === 'pending').length }}
                </span>
              </button>
            </div>
          </div>

          <div v-if="filteredSubmissions.length === 0 && !loadingSubmissions" class="text-center py-5">
            <i class="fas fa-file-alt mb-3" style="font-size: 3rem; opacity: 0.3;"></i>
            <h4 class="mb-3">No Submissions Yet</h4>
            <p class="text-muted mb-0">No articles have been submitted to this contest yet.</p>
          </div>

          <div v-else-if="filteredSubmissions.length > 0" class="table-responsive">
            <table class="table table-sm table-hover">
              <thead>
                <tr>
                  <th>Article Title</th>
                  <th>Article Author</th>
                  <th>Submitted By</th>
                  <th>Status</th>
                  <th>Score</th>
                  <th>Submitted At</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="submission in filteredSubmissions" :key="submission.id">
                  <!-- Article Title with Metadata -->
                  <td>
                    <a href="#"
@click.prevent="showArticlePreview(submission)"
class="text-decoration-none article-title-link"
:title="submission.article_link">
                      {{ submission.article_title }}
                    </a>
                    <!-- Expansion bytes (can be negative for content removal) -->
                    <div
                      v-if="
                        submission.article_expansion_bytes !== null &&
                        submission.article_expansion_bytes !== undefined
                      "
                      class="text-muted small mt-1"
                    >
                      <i
                        class="me-1"
                        :class="
                          submission.article_expansion_bytes > 0
                            ? 'fas fa-arrow-up'
                            : submission.article_expansion_bytes < 0
                            ? 'fas fa-arrow-down'
                            : 'fas fa-arrows-left-right'
                        "
                      ></i>
                      Expansion bytes:
                      <span
                        :class="
                          submission.article_expansion_bytes > 0
                            ? 'text-success'
                            : submission.article_expansion_bytes < 0
                            ? 'text-danger'
                            : 'text-muted'
                        "
                      >
                        {{
                          submission.article_expansion_bytes > 0
                            ? '+'
                            : submission.article_expansion_bytes < 0
                            ? '-'
                            : ''
                        }}{{ formatByteCountWithExact(Math.abs(submission.article_expansion_bytes)) }}
                      </span>
                    </div>
                  </td>
                  <!-- Author Information with Latest Revision -->
                  <td>
                    <div v-if="submission.article_author">
                      <i class="fas fa-user me-1"></i>{{ submission.article_author }}
                    </div>
                    <div v-else class="text-muted small">Unknown</div>
                    <div v-if="submission.article_created_at" class="text-muted small mt-1">
                      <i class="fas fa-calendar me-1"></i>{{ formatDateShort(submission.article_created_at) }}
                    </div>
                    <!-- Latest revision author may differ from original -->
                    <div
                      v-if="submission.latest_revision_author"
                      class="mt-2 pt-2"
                      style="border-top: 1px solid #dee2e6;"
                    >
                      <div>
                        <i class="fas fa-user me-1"></i
                        >{{ submission.latest_revision_author }}
                        <span class="badge bg-info ms-1" style="font-size: 0.7em;">Latest</span>
                      </div>
                      <div
                        v-if="submission.latest_revision_timestamp"
                        class="text-muted small mt-1"
                      >
                        <i class="fas fa-calendar me-1"></i
                        >{{ formatDateShort(submission.latest_revision_timestamp) }}
                      </div>
                    </div>
                  </td>
                  <td>{{ submission.username || 'Unknown' }}</td>
                  <td>
                    <span
                      :class="`badge bg-${getStatusColor(submission.status)}`"
                      :style="
                        (submission.evaluation_reason && contestScoringMode === 'automated')
                          ? 'cursor: pointer;'
                          : ''
                      "
                      @click="showEvaluationDetails(submission)"
                      :title="
                        (submission.evaluation_reason && contestScoringMode === 'automated')
                          ? 'Click to see details'
                          : ''
                      "
                    >
                      {{ submission.status }}
                    </span>
                    <div
                      v-if="submission.already_reviewed"
                      class="text-muted small mt-1"
                    >
                      <i class="fas fa-check-circle me-1"></i>Reviewed
                    </div>
                  </td>
                  <td>
                    <span
                      :style="
                        (submission.evaluation_reason && contestScoringMode === 'automated')
                          ? 'cursor: pointer; text-decoration: underline;'
                          : ''
                      "
                      @click="showEvaluationDetails(submission)"
                      :title="
                        (submission.evaluation_reason && contestScoringMode === 'automated')
                          ? 'Click to see score breakdown'
                          : ''
                      "
                    >
                      {{ submission.score || 0 }}
                    </span>
                  </td>
                  <td>{{ formatDate(submission.submitted_at) }}</td>
                  <td>
                    <button
                      v-if="canViewSubmissions"
                      @click="handleDeleteSubmission(submission)"
                      class="btn btn-sm btn-outline-danger"
                      title="Delete Submission"
                      :disabled="deletingSubmissionId === submission.id"
                    >
                      <span
                        v-if="deletingSubmissionId === submission.id"
                        class="spinner-border spinner-border-sm"
                      ></span>
                      <i v-else class="fas fa-trash"></i>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- No access message (when user can't view submissions) -->
      <div v-else class="card mb-4">
        <div class="card-body text-center py-5">
          <i class="fas fa-lock empty-state-icon mb-3" style="font-size: 3rem; opacity: 0.3;"></i>
          <h4 class="mb-3">Submissions Not Available</h4>
          <p class="text-muted mb-0">You don't have permission to view submissions for this contest.</p>
          <p class="text-muted">Contact the contest organizer if you believe you should have access.</p>
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
  name: 'ContestSubmissionsView',
  setup() {
    const router = useRouter()
    const route = useRoute()
    const store = useStore()
    const contest = ref(null)
    const loading = ref(true)
    const error = ref(null)
    const submissions = ref([])
    const loadingSubmissions = ref(false)
    const submissionFilter = ref('all')
    const deletingContest = ref(false)
    const deletingSubmissionId = ref(null)

    // Get contest ID from route params
    const contestId = Number(route.params.contestId)

    // Check if user can view submissions (organizer, jury, or admin)
    const canViewSubmissions = computed(() => {
      const user = store.currentUser.value
      if (!user || !contest.value) return false

      const username = (user.username || '').trim().toLowerCase()
      const role = (user.role || '').trim().toLowerCase()
      const contestData = contest.value

      // Admin/superadmin can view all submissions
      if (role === 'admin' || role === 'superadmin') {
        return true
      }

      // Contest creator can view submissions
      const contestCreator = (contestData.created_by || '').trim().toLowerCase()
      if (contestCreator && username === contestCreator) {
        return true
      }

      // Organizers can view submissions
      if (contestData.organizers && Array.isArray(contestData.organizers)) {
        const organizerUsernames = contestData.organizers.map(o => (o || '').trim().toLowerCase())
        if (organizerUsernames.includes(username)) {
          return true
        }
      }

      // Jury members can view submissions
      if (contestData.jury_members && Array.isArray(contestData.jury_members)) {
        const juryUsernames = contestData.jury_members.map(j => (j || '').trim().toLowerCase())
        if (juryUsernames.includes(username)) {
          return true
        }
      }

      return false
    })

    // Check if user can edit/delete contest (creator or admin/superadmin)
    const canEditOrDelete = computed(() => {
      const user = store.currentUser.value
      if (!user || !contest.value) return false
      const username = (user.username || '').trim().toLowerCase()
      const role = (user.role || '').trim().toLowerCase()
      const creator = (contest.value.created_by || '').trim().toLowerCase()
      return username === creator || role === 'admin' || role === 'superadmin'
    })

    // Check if user can delete contest (creator or admin/superadmin)
    const canDeleteContest = computed(() => {
      const user = store.currentUser.value
      if (!user || !contest.value) return false
      const username = (user.username || '').trim().toLowerCase()
      const role = (user.role || '').trim().toLowerCase()
      const creator = (contest.value.created_by || '').trim().toLowerCase()
      return username === creator || role === 'admin' || role === 'superadmin'
    })

    // Filter submissions based on selected tab
    const filteredSubmissions = computed(() => {
      if (!submissions.value) return []
      if (submissionFilter.value === 'all') return submissions.value
      return submissions.value.filter(s => s.status === submissionFilter.value)
    })

    // Load contest and submissions data
    const loadContestAndSubmissions = async () => {
      loading.value = true
      error.value = null
      try {
        // Fetch contest data
        const contestData = await api.get(`/contest/${contestId}`)
        contest.value = contestData

        // Fetch submissions for this contest
        const submissionsData = await api.get(`/submission/contest/${contestId}`)
        submissions.value = submissionsData || []
      } catch (err) {
        console.error('Failed to load contest data:', err)
        error.value = err.message || 'Failed to load contest data'
        showAlert(error.value, 'danger')
      } finally {
        loading.value = false
      }
    }

    // Refresh metadata for submissions (fetches latest article data)
    const refreshMetadata = async () => {
      if (!contest.value) return
      try {
        const response = await api.post(`/submission/contest/${contestId}/refresh-metadata`)
        showAlert(`Refreshed metadata for ${response.updated} submissions`, 'success')
        // Reload submissions to get updated data
        const submissionsData = await api.get(`/submission/contest/${contestId}`)
        submissions.value = submissionsData || []
      } catch (err) {
        console.error('Failed to refresh metadata:', err)
        showAlert('Failed to refresh metadata: ' + (err.message || 'Unknown error'), 'danger')
      }
    }

    // Delete contest with confirmation
    const handleDeleteContest = async () => {
      if (!contest.value) return

      const confirmed = confirm(
        `Are you sure you want to delete the contest "${contest.value.name}"?\n\n` +
          'This action cannot be undone and will delete all associated submissions.'
      )

      if (!confirmed) return

      deletingContest.value = true
      try {
        await api.delete(`/contest/${contestId}`)
        showAlert('Contest deleted successfully', 'success')
        router.push({ name: 'Contests' })
      } catch (err) {
        console.error('Failed to delete contest:', err)
        showAlert('Failed to delete contest: ' + (err.message || 'Unknown error'), 'danger')
      } finally {
        deletingContest.value = false
      }
    }

    // Delete submission
    const handleDeleteSubmission = async (submission) => {
      if (!submission) return

      const confirmed = confirm(
        `Are you sure you want to delete the submission "${submission.article_title}"?\n\n` +
          'This action cannot be undone.'
      )

      if (!confirmed) return

      deletingSubmissionId.value = submission.id
      try {
        await api.delete(`/submission/${submission.id}`)
        showAlert('Submission deleted successfully', 'success')
        // Remove deleted submission from list
        submissions.value = submissions.value.filter(s => s.id !== submission.id)
      } catch (err) {
        console.error('Failed to delete submission:', err)
        showAlert('Failed to delete submission: ' + (err.message || 'Unknown error'), 'danger')
      } finally {
        deletingSubmissionId.value = null
      }
    }

    // Navigate to contest edit page
    const goToEditPage = () => {
      if (!contest.value) return
      router.push({ name: 'EditContest', params: { contestId: contest.value.id } })
    }

    // Navigate back to contest view
    const goBack = () => {
      if (!contest.value) {
        router.push({ name: 'Contests' })
        return
      }
      router.push({ name: 'ContestView', params: { contestId: contest.value.id } })
    }

    // Show article preview modal
    const showArticlePreview = (submission) => {
      // Emit event to parent or use event bus to show modal
      // For now, we'll just log - in a real implementation this would show a modal
      console.log('Show article preview for:', submission.article_link)
    }

    // Show evaluation details modal
    const showEvaluationDetails = (submission) => {
      // Emit event to parent or use event bus to show modal
      console.log('Show evaluation details for submission:', submission.id)
    }

    // Format date for display
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

    // Format date short for display
    const formatDateShort = (dateString) => {
      if (!dateString) return ''
      try {
        const date = new Date(dateString)
        return date.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric'
        })
      } catch (e) {
        return dateString
      }
    }

    // Format byte count with appropriate units
    const formatByteCountWithExact = (bytes) => {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    // Determine contest scoring mode
    const contestScoringMode = computed(() => {
      if (!contest.value) return 'simple'
      if (contest.value.automated_settings?.enabled === true) return 'automated'
      if (contest.value.scoring_parameters?.enabled === true) return 'multi_parameter'
      return 'simple'
    })

    // Get status color class for badge
    const getStatusColor = (status) => {
      const colors = {
        accepted: 'success',
        rejected: 'danger',
        pending: 'warning',
        auto_rejected: 'danger'
      }
      return colors[status] || 'secondary'
    }

    // Get status label
    const getStatusLabel = (status) => {
      const labels = {
        current: 'Active',
        upcoming: 'Upcoming',
        past: 'Past',
        unknown: 'Unknown',
        pending: 'Pending',
        accepted: 'Accepted',
        rejected: 'Rejected'
      }
      return labels[status] || status
    }

    // Get organizers list for display
    const getOrganizers = (contest) => {
      const organizers = []
      if (contest.created_by) organizers.push(contest.created_by)
      if (contest.organizers && Array.isArray(contest.organizers)) {
        contest.organizers.forEach(org => {
          if (org && org !== contest.created_by) organizers.push(org)
        })
      }
      return organizers
    }

    // Get initials from username for avatar display
    const getInitials = (username) => {
      if (!username) return '?'
      const parts = username.trim().split(/\s+/)
      if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase()
      } else {
        return username.substring(0, 2).toUpperCase()
      }
    }

    // Load data when component mounts
    onMounted(() => {
      loadContestAndSubmissions()
    })

    // Refetch data if contest ID changes
    watch(
      () => route.params.contestId,
      (newId) => {
        if (newId !== route.params.contestId) return
        loadContestAndSubmissions()
      }
    )

    return {
      contest,
      loading,
      error,
      submissions,
      loadingSubmissions,
      submissionFilter,
      filteredSubmissions,
      deletingContest,
      deletingSubmissionId,
      canViewSubmissions,
      canEditOrDelete,
      canDeleteContest,
      loadContestAndSubmissions,
      refreshMetadata,
      handleDeleteContest,
      handleDeleteSubmission,
      goToEditPage,
      goBack,
      showArticlePreview,
      showEvaluationDetails,
      formatDate,
      formatDateShort,
      formatByteCountWithExact,
      contestScoringMode,
      getStatusColor,
      getStatusLabel,
      getOrganizers,
      getInitials
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

/* Empty State Icon */
.empty-state-icon {
  color: var(--wiki-primary, #006699);
}

[data-theme="dark"] .empty-state-icon {
  color: #4da6cc;
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

/* Contest Card Action Buttons */
.contest-card .btn-sm {
  padding: 0.25rem 0.75rem;
  font-size: 0.85rem;
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
