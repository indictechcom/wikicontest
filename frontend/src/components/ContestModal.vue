<template>
  <!-- Contest details modal with submissions list for jury/creators -->
  <div class="modal fade" id="contestModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <!-- Modal header with contest name -->
        <div class="modal-header">
          <h5 class="modal-title">{{ contest?.name }}</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body" v-if="contest">
          <div class="row">
            <!-- Contest basic details section -->
            <div :class="canViewSubmissions ? 'col-md-6' : 'col-md-12'">
              <h6>Contest Details</h6>
              <p><strong>Project:</strong> {{ contest.project_name }}</p>
              <p><strong>Created by:</strong> {{ contest.created_by }}</p>
              <p><strong>Status:</strong> <span class="badge bg-primary">{{ contest.status }}</span></p>
              <p v-if="contest.start_date"><strong>Start Date:</strong> {{ formatDate(contest.start_date) }}</p>
              <p v-if="contest.end_date"><strong>End Date:</strong> {{ formatDate(contest.end_date) }}</p>
            </div>
            <!-- Scoring details - only visible to jury/creators -->
            <div v-if="canViewSubmissions" class="col-md-6">
              <h6>Scoring</h6>
              <p><strong>Accepted:</strong> {{ contest.marks_setting_accepted }} points</p>
              <p><strong>Rejected:</strong> {{ contest.marks_setting_rejected }} points</p>
              <p><strong>Submissions:</strong> {{ contest.submission_count }}</p>
            </div>
          </div>
          <!-- Contest description with preserved line breaks -->
          <div v-if="contest.description" class="mt-3 description-section">
            <h6>Description</h6>
            <p class="description-text">{{ contest.description }}</p>
          </div>
          <!-- Jury members list -->
          <div v-if="contest.jury_members && contest.jury_members.length > 0" class="mt-3 jury-section">
            <h6>Jury Members</h6>
            <p>{{ contest.jury_members.join(', ') }}</p>
          </div>

          <!-- Template Link Section -->
          <div v-if="contest.template_link" class="mt-3 template-section">
            <h6>
              <i class="fas fa-file-code me-1"></i>
              Contest Template
            </h6>
            <p class="mb-1">
              <a :href="contest.template_link"
target="_blank"
rel="noopener noreferrer"
class="text-decoration-none">
                {{ contest.template_link }}
                <i class="fas fa-external-link-alt ms-1" style="font-size: 0.8em;"></i>
              </a>
            </p>
            <small class="text-muted">
              <i class="fas fa-info-circle me-1"></i>
              This template will be automatically added to submitted articles that don't already have it.
            </small>
          </div>

          <!-- Submissions Section (for jury and contest creators) -->
          <div v-if="canViewSubmissions" class="mt-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
              <h6>Submissions</h6>
              <!-- Refresh metadata button - updates article data from MediaWiki -->
              <button
                v-if="loadingSubmissions || refreshingMetadata"
                class="btn btn-sm btn-outline-secondary"
                disabled
              >
                <span class="spinner-border spinner-border-sm me-2"></span>
                {{
                  loadingSubmissions ? 'Loading...' : 'Refreshing...'
                }}
              </button>
              <button
                v-else
                class="btn btn-sm btn-outline-light"
                @click="refreshMetadata"
                :disabled="submissions.length === 0"
                title="Refresh article metadata (byte count, author, etc.) from MediaWiki and reload submissions"
                style="color: white; border-color: white;"
              >
                <i class="fas fa-database me-1"></i>Refresh Metadata
              </button>
            </div>

            <!-- Empty state when no submissions exist -->
            <div v-if="submissions.length === 0 && !loadingSubmissions" class="alert alert-info">
              <i class="fas fa-info-circle me-2"></i>No submissions yet for this contest.
            </div>

            <!-- Submissions table with article metadata -->
            <div v-else-if="submissions.length > 0" class="table-responsive">
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
                  <tr v-for="submission in submissions" :key="submission.id">
                    <!-- Article title with preview link and byte count details -->
                    <td>
                      <!-- Clickable article title to open preview modal -->

                        href="#"
                        @click.prevent="showArticlePreview(submission.article_link, submission.article_title)"
                        class="text-decoration-none article-title-link"
                        :title="submission.article_link"
                      >
                        {{ submission.article_title }}
                        <i class="fas fa-eye ms-1" style="font-size: 0.8em;"></i>
                      <!-- Total bytes = Original bytes (at submission) + Expansion bytes (change since submission) -->
                      <div
                        v-if="submission.article_word_count !== null &&
                          submission.article_word_count !== undefined"
                        class="text-muted small mt-1"
                      >
                        <i class="fas fa-file-alt me-1"></i>Total bytes:
                        {{
                          formatByteCountWithExact(
                            (submission.article_word_count || 0) +
                            (submission.article_expansion_bytes || 0)
                          )
                        }}
                      </div>
                      <!-- Original byte count at time of submission -->
                      <div
                        v-if="submission.article_word_count !== null &&
                          submission.article_word_count !== undefined"
                        class="text-muted small mt-1"
                      >
                        <i class="fas fa-clock me-1"></i>Original bytes:
                        {{ formatByteCountWithExact(submission.article_word_count) }}
                      </div>
                      <!-- Expansion bytes showing growth/shrinkage since submission -->
                      <div
                        v-if="submission.article_expansion_bytes !== null &&
                          submission.article_expansion_bytes !== undefined"
                        class="text-muted small mt-1"
                      >
                        <i
                          v-if="submission.article_expansion_bytes !== 0"
                          :class="submission.article_expansion_bytes >= 0
                            ? 'fas fa-arrow-up me-1'
                            : 'fas fa-arrow-down me-1'"
                        ></i>Expansion bytes:
                        <span
                          v-if="submission.article_expansion_bytes !== 0"
                          :class="submission.article_expansion_bytes >= 0 ? 'text-success' : 'text-danger'"
                        >
                          {{ submission.article_expansion_bytes >= 0 ? '+' : '-' }}{{
                            formatByteCountWithExact(Math.abs(submission.article_expansion_bytes))
                          }}
                        </span>
                        <span v-else>
                          {{ formatByteCountWithExact(0) }}
                        </span>
                      </div>
                    </td>
                    <!-- Article author info - shows both original and latest revision authors -->
                    <td>
                      <!-- Original author (from oldest revision) -->
                      <div v-if="submission.article_author">
                        <i class="fas fa-user me-1"></i>{{ submission.article_author }}
                      </div>
                      <div v-else class="text-muted small">Unknown</div>
                      <div v-if="submission.article_created_at" class="text-muted small mt-1">
                        <i class="fas fa-calendar me-1"></i>{{ formatDateShort(submission.article_created_at) }}
                      </div>
                      <!-- Latest revision author (from latest revision, shown below original) -->
                      <div
                        v-if="submission.latest_revision_author"
                        class="mt-2 pt-2"
                        style="border-top: 1px solid #dee2e6;"
                      >
                        <div>
                          <i class="fas fa-user me-1"></i>{{ submission.latest_revision_author }}
                          <span class="badge bg-info ms-1" style="font-size: 0.7em;">Latest</span>
                        </div>
                        <div
                          v-if="submission.latest_revision_timestamp"
                          class="text-muted small mt-1"
                        >
                          <i class="fas fa-calendar me-1"></i>
                          {{ formatDateShort(submission.latest_revision_timestamp) }}
                        </div>
                      </div>
                    </td>
                    <td>{{ submission.username || 'Unknown' }}</td>
                    <!-- Status badge with color coding -->
                    <td>
                      <span :class="`badge bg-${getStatusColor(submission.status)}`">
                        {{ submission.status }}
                      </span>
                    </td>
                    <td>{{ submission.score || 0 }}</td>
                    <td>{{ formatDate(submission.submitted_at) }}</td>
                    <!-- Preview button to open article in modal -->
                    <td>
                      <button
                        @click="showArticlePreview(submission.article_link, submission.article_title)"
                        class="btn btn-sm btn-outline-primary"
                        title="Preview Article"
                      >
                        <i class="fas fa-eye"></i>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <!-- Debug info and auth status -->
          <div class="me-auto">
            <!-- Warning if user is not loaded -->
            <div
              v-if="contest && !currentUser && !checkingAuth"
              class="alert alert-warning py-1 px-2 mb-2"
              style="font-size: 0.75rem;"
            >
              <i class="fas fa-exclamation-triangle me-1"></i>
              <strong>User not loaded!</strong>
              <!-- Manual auth refresh button for troubleshooting -->
              <button class="btn btn-sm btn-outline-warning ms-2" @click="forceAuthRefresh" style="font-size: 0.7rem;">
                <i class="fas fa-sync-alt me-1"></i>Refresh Auth
              </button>
            </div>
          </div>
          <!-- Delete button - only visible to contest creator -->
          <button
            v-if="canDeleteContest"
            class="btn btn-danger"
            @click="handleDeleteContest"
            :disabled="deletingContest"
          >
            <span v-if="deletingContest" class="spinner-border spinner-border-sm me-2"></span>
            <i v-else class="fas fa-trash me-2"></i>
            {{ deletingContest ? 'Deleting...' : 'Delete Contest' }}
          </button>
          <!-- Submit article button - for authenticated non-jury participants -->
          <button
            v-if="contest?.status === 'current' && isAuthenticated && !canViewSubmissions"
            class="btn btn-primary"
            @click="handleSubmitArticle"
          >
            Submit Article
          </button>
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Article Preview Modal -->
  <ArticlePreviewModal
    :article-url="previewArticleUrl"
    :article-title="previewArticleTitle"
  />
</template>

<script>
import { computed, ref, watch } from 'vue'
import { useStore } from '../store'
import api from '../services/api'
import { showAlert } from '../utils/alerts'
import ArticlePreviewModal from './ArticlePreviewModal.vue'

export default {
  name: 'ContestModal',
  components: {
    ArticlePreviewModal
  },
  props: {
    contest: {
      type: Object,
      default: null
    }
  },
  emits: ['submit-article', 'contest-deleted'],
  setup(props, { emit }) {
    const store = useStore()
    // Get reactive references to auth state
    // isAuthenticated should only be true if we have a valid user object
    // Use store.state.currentUser directly for better reactivity
    const currentUser = computed(() => {
      // Try multiple sources to get current user
      // Check store.state.currentUser first (direct reactive state access - most reliable)
      // Then check store.currentUser (computed property)
      // This ensures we get the most up-to-date value
      if (store.state && store.state.currentUser) {
        return store.state.currentUser
      }
      if (store.currentUser) {
        return store.currentUser
      }
      return null
    })
    const isAuthenticated = computed(() => {
      // Only authenticated if we have a valid user object
      // This ensures isAuthenticated and currentUser are always in sync
      const user = currentUser.value
      return !!user && !!user.id && !!user.username
    })

    // State for submissions
    const submissions = ref([])
    const loadingSubmissions = ref(false)
    const refreshingMetadata = ref(false)

    // State for delete operation
    const deletingContest = ref(false)

    // State for delete permission (updated after auth check)
    const canDeleteContest = ref(false)

    // State to track if auth check is in progress
    const checkingAuth = ref(false)

    // State for article preview modal
    const previewArticleUrl = ref('')
    const previewArticleTitle = ref('')

    // Check if user can view submissions (jury member or contest creator)
    const canViewSubmissions = computed(() => {
      if (!isAuthenticated.value || !props.contest || !currentUser.value) {
        return false
      }

      const username = (currentUser.value.username || '').trim().toLowerCase()
      const contest = props.contest

      // Check if user is contest creator (case-insensitive)
      const contestCreator = (contest.created_by || '').trim().toLowerCase()
      if (contestCreator && username === contestCreator) {
        return true
      }

      // Check if user is jury member (case-insensitive)
      if (contest.jury_members && Array.isArray(contest.jury_members)) {
        const juryUsernames = contest.jury_members.map(j => (j || '').trim().toLowerCase())
        return juryUsernames.includes(username)
      }

      return false
    })

    // Check if user can delete contest (must be creator)
    // Works for both regular users and OAuth (Wikimedia) users
    // Backend stores user.username in created_by field for both types
    const checkDeletePermission = () => {
      // Reset to false initially
      canDeleteContest.value = false

      // Get current user from multiple sources to ensure we get the latest value
      // Try computed property first, then direct state access
      const userFromComputed = currentUser.value
      const userFromStore = store.currentUser
      const userFromState = (store.state && store.state.currentUser) || null

      // Use the first available user source
      const userToCheck = userFromComputed || userFromStore || userFromState

      console.log('=== Delete Permission Check ===')
      console.log('isAuthenticated:', isAuthenticated.value)
      console.log('hasContest:', !!props.contest)
      console.log('currentUser.value (computed):', userFromComputed)
      console.log('store.currentUser:', userFromStore)
      console.log('store.state.currentUser:', userFromState)
      console.log('userToCheck (final):', userToCheck)

      // Check basic requirements
      if (!isAuthenticated.value) {
        console.log(' Delete check: Not authenticated')
        canDeleteContest.value = false
        return
      }

      if (!props.contest) {
        console.log(' Delete check: No contest')
        canDeleteContest.value = false
        return
      }

      if (!userToCheck) {
        console.log(' Delete check: No current user object')
        console.log('Store state:', store.state)
        canDeleteContest.value = false
        return
      }

      // Get username from current user (works for both regular and OAuth users)
      const username = (userToCheck.username || '').trim()
      const contestCreator = (props.contest.created_by || '').trim()

      // If either is empty, can't match
      if (!username) {
        console.log(' Delete check: Username is empty', {
          userToCheck,
          currentUser: userFromComputed,
          storeUser: userFromStore,
          stateUser: userFromState
        })
        canDeleteContest.value = false
        return
      }

      if (!contestCreator) {
        console.log(' Delete check: Contest creator is empty', { contest: props.contest })
        canDeleteContest.value = false
        return
      }

      // Check if user is contest creator (case-insensitive comparison)
      // This works for both regular users and OAuth users since both use username
      const usernameLower = username.toLowerCase()
      const creatorLower = contestCreator.toLowerCase()
      const canDelete = usernameLower === creatorLower

      // Debug logging to help troubleshoot
      console.log(' Delete permission check result:', {
        username,
        contestCreator,
        usernameLower,
        creatorLower,
        match: canDelete,
        canDelete,
        note: 'Works for both regular and OAuth (Wikimedia) users'
      })

      canDeleteContest.value = canDelete
      console.log('=== End Delete Permission Check ===')
    }

    // Format date for display in Indian Standard Time (IST)
    // Converts UTC dates from backend to IST timezone for display
    const formatDate = (dateString) => {
      if (!dateString) return 'No date'
      try {
        // Ensure the date string is treated as UTC
        // If it doesn't end with 'Z', append it to indicate UTC timezone
        // This fixes the issue where naive UTC datetimes were being interpreted as local time
        let utcDateString = dateString
        if (!dateString.endsWith('Z') && !dateString.includes('+') && !dateString.includes('-', 10)) {
          // If no timezone indicator, assume it's UTC and append 'Z'
          utcDateString = dateString + 'Z'
        }

        // Convert to IST (Indian Standard Time) timezone
        // IST is UTC+5:30, timezone identifier is 'Asia/Kolkata'
        return new Date(utcDateString).toLocaleString('en-IN', {
          timeZone: 'Asia/Kolkata',
          year: 'numeric',
          month: 'long',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          hour12: true
        })
      } catch (e) {
        return dateString
      }
    }

    // Format date with full date and time in IST (for article creation date)
    // Shows complete date and time information including time in IST timezone
    const formatDateShort = (dateString) => {
      if (!dateString) return ''
      try {
        // Ensure the date string is treated as UTC
        // Append 'Z' if no timezone indicator present
        let utcDateString = dateString
        if (!dateString.endsWith('Z') && !dateString.includes('+') && !dateString.includes('-', 10)) {
          utcDateString = dateString + 'Z'
        }

        // Convert to IST timezone with full date and time
        return new Date(utcDateString).toLocaleString('en-IN', {
          timeZone: 'Asia/Kolkata',
          year: 'numeric',
          month: 'long',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          hour12: true
        })
      } catch (e) {
        return dateString
      }
    }

    // Format byte count for display
    // Converts bytes to appropriate unit (bytes, KB, MB)
    const formatByteCount = (bytes) => {
      if (!bytes) return ''
      if (bytes >= 1048576) {
        return `${(bytes / 1048576).toFixed(1)} MB`
      }
      if (bytes >= 1024) {
        return `${(bytes / 1024).toFixed(1)} KB`
      }
      return `${bytes} bytes`
    }

    // Format byte count with exact bytes in parentheses
    // Shows formatted size (KB/MB) with exact byte count
    // Example: "1.2 KB (1224 bytes)" or "-500 bytes" for negative values
    const formatByteCountWithExact = (bytes) => {
      if (!bytes && bytes !== 0) return ''

      // Handle negative values - use absolute value for formatting
      const absBytes = Math.abs(bytes)

      let formatted = ''
      if (absBytes >= 1048576) {
        formatted = `${(absBytes / 1048576).toFixed(1)} MB (${bytes} bytes)`
      } else if (absBytes >= 1024) {
        formatted = `${(absBytes / 1024).toFixed(1)} KB (${bytes} bytes)`
      } else {
        // For values less than 1 KB, just show bytes
        formatted = `${bytes} bytes`
      }

      return formatted
    }

    // Show article preview modal with given URL and title
    const showArticlePreview = (url, title) => {
      previewArticleUrl.value = url
      previewArticleTitle.value = title || 'Article'

      // Show modal using Bootstrap after slight delay
      setTimeout(() => {
        const modalElement = document.getElementById('articlePreviewModal')
        if (modalElement) {
          const modal = new bootstrap.Modal(modalElement)
          modal.show()
        }
      }, 100)
    }

    // Get Bootstrap badge color based on submission status
    const getStatusColor = (status) => {
      switch (status?.toLowerCase()) {
        case 'accepted':
          return 'success'
        case 'rejected':
          return 'danger'
        case 'pending':
          return 'warning'
        default:
          return 'secondary'
      }
    }

    // Load submissions for the contest from API
    const loadSubmissions = async () => {
      if (!props.contest || !canViewSubmissions.value) {
        return
      }

      loadingSubmissions.value = true
      try {
        const data = await api.get(`/contest/${props.contest.id}/submissions`)
        submissions.value = data || []
      } catch (error) {
        console.error('Failed to load submissions:', error)
        showAlert('Failed to load submissions: ' + error.message, 'danger')
        submissions.value = []
      } finally {
        loadingSubmissions.value = false
      }
    }

    // Refresh article metadata for all submissions in the contest
    // Fetches latest data from MediaWiki (byte count, author, etc.)
    const refreshMetadata = async () => {
      if (!props.contest || !canViewSubmissions.value || submissions.value.length === 0) {
        return
      }

      refreshingMetadata.value = true
      try {
        const response = await api.post(`/submission/contest/${props.contest.id}/refresh-metadata`)
        showAlert(
          `Metadata refreshed: ${response.updated} updated, ${response.failed} failed`,
          response.failed === 0 ? 'success' : 'warning'
        )

        // Reload submissions to show updated data
        await loadSubmissions()
      } catch (error) {
        console.error('Failed to refresh metadata:', error)
        showAlert('Failed to refresh metadata: ' + error.message, 'danger')
      } finally {
        refreshingMetadata.value = false
      }
    }

    // Handle delete contest with confirmation
    const handleDeleteContest = async () => {
      if (!props.contest) return

      // Confirm deletion with user
      const confirmed = confirm(
        `Are you sure you want to delete the contest "${props.contest.name}"?\n\n` +
        'This action cannot be undone and will delete all associated submissions.'
      )

      if (!confirmed) return

      deletingContest.value = true
      try {
        await api.delete(`/contest/${props.contest.id}`)
        showAlert('Contest deleted successfully', 'success')

        // Close modal after successful deletion
        const modalElement = document.getElementById('contestModal')
        const modal = bootstrap.Modal.getInstance(modalElement)
        if (modal) {
          modal.hide()
        }

        // Emit event to parent to reload contests list
        emit('contest-deleted')
      } catch (error) {
        console.error('Failed to delete contest:', error)
        showAlert('Failed to delete contest: ' + error.message, 'danger')
      } finally {
        deletingContest.value = false
      }
    }

    // Handle submit article button click
    const handleSubmitArticle = () => {
      emit('submit-article', props.contest.id)
      // Close this modal before opening submit modal
      const modalElement = document.getElementById('contestModal')
      const modal = bootstrap.Modal.getInstance(modalElement)
      if (modal) {
        modal.hide()
      }
    }

    // Force auth refresh manually for troubleshooting
    const forceAuthRefresh = async () => {
      checkingAuth.value = true
      try {
        console.log('🔄 Manual auth refresh triggered')
        await store.checkAuth()
        await new Promise(resolve => setTimeout(resolve, 200))
        checkDeletePermission()
        console.log('🔄 Auth refresh completed, user:', store.currentUser || (store.state && store.state.currentUser))
      } catch (error) {
        console.error('🔄 Auth refresh failed:', error)
      } finally {
        checkingAuth.value = false
      }
    }

    // Watch for changes in currentUser to update delete permission
    watch(() => currentUser.value, (newUser, oldUser) => {
      if (newUser && props.contest && !checkingAuth.value) {
        console.log('Current user changed, checking delete permission:', newUser)
        // Small delay to ensure reactivity settles
        setTimeout(() => {
          checkDeletePermission()
        }, 50)
      } else if (!newUser && oldUser && props.contest) {
        // User was cleared, reset permission
        console.log('User cleared, resetting delete permission')
        canDeleteContest.value = false
      }
    }, { deep: true, immediate: false })

    // Also watch store state directly as backup (only if store.state exists)
    if (store.state) {
      watch(() => store.state.currentUser, (newUser, oldUser) => {
        if (newUser && props.contest && !checkingAuth.value) {
          console.log('Store state user changed, checking delete permission:', newUser)
          setTimeout(() => {
            checkDeletePermission()
          }, 50)
        } else if (!newUser && oldUser && props.contest) {
          console.log('Store state user cleared, resetting delete permission')
          canDeleteContest.value = false
        }
      }, { deep: true, immediate: false })
    }

    // Also watch store.currentUser computed property
    watch(() => store.currentUser, (newUser, oldUser) => {
      if (newUser && props.contest && !checkingAuth.value) {
        console.log('Store computed user changed, checking delete permission:', newUser)
        setTimeout(() => {
          checkDeletePermission()
        }, 50)
      } else if (!newUser && oldUser && props.contest) {
        console.log('Store computed user cleared, resetting delete permission')
        canDeleteContest.value = false
      }
    }, { deep: true, immediate: false })

    // Watch for contest changes and load data
    watch(() => props.contest, async (newContest) => {
      if (newContest) {
        // Reset state when new contest is opened
        checkingAuth.value = true
        canDeleteContest.value = false

        try {
          console.log('🔍 Modal opened, checking auth for contest:', newContest.name)
          console.log('🔍 Contest created by:', newContest.created_by)

          // First, check if user is already in the store (from login)
          let loadedUser = store.currentUser || (store.state && store.state.currentUser) || currentUser.value

          console.log('📊 Initial user check:', {
            storeCurrentUser: store.currentUser,
            stateCurrentUser: (store.state && store.state.currentUser) || null,
            computedCurrentUser: currentUser.value,
            loadedUser
          })

          // If user is not in store, try to load it via checkAuth
          if (!loadedUser) {
            console.log(' User not in store, calling checkAuth()...')
            let userLoaded = false
            let retries = 0
            const maxRetries = 3

            // Retry auth check up to 3 times if it fails
            while (!userLoaded && retries < maxRetries) {
              try {
                const authResult = await store.checkAuth()

                // Wait for reactive state to update
                await new Promise(resolve => setTimeout(resolve, 150))

                // Check if user is actually loaded now
                const userNow = store.currentUser || (store.state && store.state.currentUser) || currentUser.value
                if (authResult && userNow) {
                  userLoaded = true
                  loadedUser = userNow
                  console.log(' User loaded after auth check:', loadedUser)
                  break
                } else {
                  console.log(` Auth check returned ${authResult} but user not loaded, retrying...`)
                }
              } catch (error) {
                console.error(` Auth check attempt ${retries + 1} failed:`, error)
              }

              if (!userLoaded && retries < maxRetries - 1) {
                console.log(`🔄 Retrying auth check... (${retries + 1}/${maxRetries})`)
                await new Promise(resolve => setTimeout(resolve, 300))
              }
              retries++
            }
          } else {
            console.log(' User already in store, using existing user:', loadedUser)
          }

          // Wait for reactive state to fully propagate
          await new Promise(resolve => setTimeout(resolve, 100))

          // Final user check - try all sources again
          loadedUser = store.currentUser || (store.state && store.state.currentUser) || currentUser.value

          // Log final state for debugging
          console.log('📊 Final user state:', {
            isAuthenticated: store.isAuthenticated,
            currentUser: store.currentUser,
            stateCurrentUser: (store.state && store.state.currentUser) || null,
            computedCurrentUser: currentUser.value,
            loadedUser,
            contestCreator: newContest.created_by
          })

          // Check if user is loaded - if not, we can't check permissions
          if (!loadedUser) {
            console.error(' CRITICAL: User not loaded!')
            console.error('Store currentUser:', store.currentUser)
            console.error('Store state currentUser:', store.state && store.state.currentUser)
            console.error('Computed currentUser:', currentUser.value)
            console.error('This means you are not logged in. Please log in again.')
            canDeleteContest.value = false
            checkingAuth.value = false
            return
          } else {
            console.log(' User loaded successfully:', loadedUser)
          }

          // Now check delete permission with the loaded user
          await new Promise(resolve => setTimeout(resolve, 100))
          checkDeletePermission()

          // If permission check didn't work, try a few more times
          if (!canDeleteContest.value) {
            console.log(' Delete permission false, retrying permission check...')

            // Retry up to 3 times with 150ms delay between attempts
            for (let i = 0; i < 3; i++) {
              await new Promise(resolve => setTimeout(resolve, 150))

              // Re-read user to ensure we have latest state
              const userNow = store.currentUser || (store.state && store.state.currentUser) || currentUser.value
              if (userNow) {
                console.log(`Permission check retry ${i + 1}, user:`, userNow)
                checkDeletePermission()

                // If we got a result, break
                if (canDeleteContest.value) {
                  console.log(' Delete permission granted!')
                  break
                }
              }
            }
          }

          // Final check and logging
          if (!canDeleteContest.value) {
            // Gather final user state for debugging
            const finalUser = store.currentUser || (store.state && store.state.currentUser) || currentUser.value
            console.error(' Delete permission still false after all attempts')
            console.error('Final user check:', finalUser)
            console.error('Contest creator:', newContest.created_by)

            // Compare usernames case-insensitively for debugging
            if (finalUser) {
              console.error('User username:', finalUser.username)
              console.error('Contest creator (lowercase):', (newContest.created_by || '').toLowerCase())
              console.error('User username (lowercase):', (finalUser.username || '').toLowerCase())
              console.error('Match:', (finalUser.username || '').toLowerCase() === (newContest.created_by || '').toLowerCase())
            }
          } else {
            console.log(' Delete permission check successful!')
          }
        } catch (error) {
          console.error(' Failed to check auth:', error)
          canDeleteContest.value = false
        } finally {
          checkingAuth.value = false
        }

        // Load submissions if user can view them
        if (canViewSubmissions.value) {
          loadSubmissions()
        } else {
          submissions.value = []
        }
      } else {
        // Reset state when contest is not available
        submissions.value = []
        canDeleteContest.value = false
      }
    }, { immediate: true })

    return {
      store, // Expose store for template access
      isAuthenticated,
      currentUser,
      submissions,
      loadingSubmissions,
      refreshingMetadata,
      deletingContest,
      checkingAuth,
      canViewSubmissions,
      canDeleteContest,
      formatDate,
      formatDateShort,
      formatByteCount,
      formatByteCountWithExact,
      getStatusColor,
      loadSubmissions,
      handleSubmitArticle,
      handleDeleteContest,
      forceAuthRefresh,
      refreshMetadata,
      showArticlePreview,
      previewArticleUrl,
      previewArticleTitle
    }
  }
}
</script>

<style scoped>

/* Modal header - solid color, no gradient */
.modal-header {
  background-color: var(--wiki-primary);
  color: white;
  border-bottom: none;
  padding: 1.25rem 1.5rem;
  transition: background-color 0.2s ease;
}

.modal-title {
  font-weight: 600;
  font-size: 1.5rem;
}

/* Close button styling with inverted colors */
.modal-header .btn-close {
  filter: invert(1) brightness(1.2);
  opacity: 0.9;
  transition: opacity 0.2s ease;
}

.modal-header .btn-close:hover {
  opacity: 1;
}

.modal-body {
  padding: 1.5rem;
}

/* Section headers with bottom border */
.modal-body h6 {
  color: var(--wiki-primary);
  font-weight: 600;
  margin-bottom: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid rgba(0, 102, 153, 0.2);
  transition: color 0.3s ease;
}

/* Dark mode: white text for better visibility */
[data-theme="dark"] .modal-body h6 {
  color: #ffffff !important;
  border-bottom-color: rgba(93, 184, 230, 0.3);
}

.modal-body p {
  margin-bottom: 0.75rem;
  color: var(--wiki-text);
  transition: color 0.3s ease;
}

.modal-body strong {
  color: var(--wiki-dark);
  font-weight: 600;
  transition: color 0.3s ease;
}

/* Ensure white text for jury section in both modes */
.jury-section p {
  color: #ffffff !important;
}

[data-theme="dark"] .jury-section p {
  color: #ffffff !important;
}

.jury-section h6 {
  color: #ffffff !important;
}

[data-theme="dark"] .jury-section h6 {
  color: #ffffff !important;
}

.description-section {
  margin-top: 1.5rem;
}

/* Preserve line breaks and wrap text naturally */
.description-text {
  white-space: pre-line;
  line-height: 1.6;
  margin-bottom: 0;
  color: var(--wiki-text);
  word-wrap: break-word;
  transition: color 0.3s ease;
}

[data-theme="dark"] .description-text {
  color: var(--wiki-text);
}

.badge {
  font-weight: 500;
  padding: 0.4em 0.8em;
  font-size: 0.85em;
}

.badge.bg-primary {
  background-color: var(--wiki-primary) !important;
}

.badge.bg-success {
  background-color: var(--wiki-success) !important;
}

/* Warning badge with dark text for readability */
.badge.bg-warning {
  background-color: var(--wiki-warning) !important;
  color: #000000 !important;
}

/* Dark mode: maintain dark text on bright orange */
[data-theme="dark"] .badge.bg-warning {
  background-color: var(--wiki-warning) !important;
  color: #000000 !important;
}

.badge.bg-danger {
  background-color: var(--wiki-danger) !important;
}

.table {
  margin-top: 1rem;
}

/* Table header with Wikipedia colors */
.table thead th {
  background-color: rgba(0, 102, 153, 0.1);
  color: var(--wiki-primary);
  font-weight: 600;
  border-bottom: 2px solid var(--wiki-primary);
  padding: 0.75rem;
  transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
}

/* Dark mode table header */
[data-theme="dark"] .table thead th {
  background-color: rgba(93, 184, 230, 0.15);
  border-bottom-color: var(--wiki-primary);
}

.table tbody td {
  padding: 0.75rem;
  vertical-align: middle;
  color: var(--wiki-text);
  transition: color 0.3s ease;
}

/* Hover effect for table rows */
.table tbody tr {
  transition: background-color 0.2s ease;
}

.table tbody tr:hover {
  background-color: var(--wiki-hover-bg);
}

/* Links in table cells */
.table a {
  color: var(--wiki-primary);
  font-weight: 500;
  transition: color 0.2s ease;
}

.table a:hover {
  color: var(--wiki-primary-hover);
  text-decoration: underline;
}

/* Article title link - clickable for preview */
.article-title-link {
  cursor: pointer;
  color: var(--wiki-primary);
  font-weight: 500;
  transition: color 0.2s ease;
}

.article-title-link:hover {
  color: var(--wiki-primary-hover);
  text-decoration: underline;
}

/* Outline primary button */
.btn-outline-primary {
  border-color: var(--wiki-primary);
  color: var(--wiki-primary);
  transition: all 0.2s ease;
}

.btn-outline-primary:hover {
  background-color: var(--wiki-primary);
  border-color: var(--wiki-primary);
  color: white;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 102, 153, 0.3);
}

/* Primary button with hover effect */
.btn-primary {
  background-color: var(--wiki-primary);
  border-color: var(--wiki-primary);
  transition: all 0.2s ease;
}

.btn-primary:hover {
  background-color: var(--wiki-primary-hover);
  border-color: var(--wiki-primary-hover);
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 102, 153, 0.3);
}

/* Danger button with MediaWiki red */
.btn-danger {
  background-color: var(--wiki-danger);
  border-color: var(--wiki-danger);
  color: white;
  transition: all 0.2s ease;
}

.btn-danger:hover {
  background-color: var(--wiki-danger-hover);
  border-color: var(--wiki-danger-hover);
  color: white;
  box-shadow: 0 2px 4px rgba(153, 0, 0, 0.2);
}

/* Dark mode danger button - ensure proper MediaWiki red */
[data-theme="dark"] .btn-danger {
  background-color: #990000;
  border-color: #990000;
  color: white;
}

[data-theme="dark"] .btn-danger:hover {
  background-color: #7a0000;
  border-color: #7a0000;
  color: white;
}

/* Secondary button styling */
.btn-secondary {
  background-color: var(--wiki-text-muted);
  border-color: var(--wiki-text-muted);
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  background-color: var(--wiki-text-muted);
  border-color: var(--wiki-text-muted);
}

/* Dark mode secondary button */
[data-theme="dark"] .btn-secondary {
  background-color: #5a6268;
  border-color: #5a6268;
}

[data-theme="dark"] .btn-secondary:hover {
  background-color: #6c757d;
  border-color: #6c757d;
}

.alert {
  border-radius: 0.5rem;
  border-left: 4px solid;
  padding: 0.75rem 1rem;
}

/* Info alert with Wikipedia blue */
.alert-info {
  background-color: rgba(0, 102, 153, 0.1);
  border-color: var(--wiki-primary);
  color: var(--wiki-primary);
  transition: background-color 0.3s ease, border-color 0.3s ease, color 0.3s ease;
}

/* Dark mode info alert */
[data-theme="dark"] .alert-info {
  background-color: rgba(93, 184, 230, 0.2);
  border-color: var(--wiki-primary);
  color: var(--wiki-primary);
}

/* Warning alert with red tones */
.alert-warning {
  background-color: rgba(153, 0, 0, 0.1);
  border-color: var(--wiki-danger);
  color: var(--wiki-danger);
  transition: background-color 0.3s ease, border-color 0.3s ease, color 0.3s ease;
}

/* Dark mode warning alert */
[data-theme="dark"] .alert-warning {
  background-color: rgba(230, 128, 128, 0.2);
  border-color: var(--wiki-danger);
  color: var(--wiki-danger);
}

.modal-footer {
  border-top: 1px solid var(--wiki-border);
  padding: 1rem 1.5rem;
  background-color: var(--wiki-modal-bg);
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

/* Muted text in footer */
.modal-footer .text-muted {
  font-size: 0.75rem;
  color: var(--wiki-text-muted);
  transition: color 0.3s ease;
}

/* Debug info in footer */
.modal-footer .alert {
  margin-bottom: 0.5rem;
  font-size: 0.75rem;
  padding: 0.5rem 0.75rem;
}

/* Small spinner for loading states */
.spinner-border-sm {
  width: 1rem;
  height: 1rem;
  border-width: 0.15em;
}

/* Icon transitions */
.fas, .fab {
  transition: transform 0.2s ease;
}

/* Scale icons on button hover */
.btn:hover .fas,
.btn:hover .fab {
  transform: scale(1.1);
}

/* Mobile and tablet adjustments */
@media (max-width: 768px) {
  .modal-body {
    padding: 1rem;
  }

  .table {
    font-size: 0.9rem;
  }

  .table thead th,
  .table tbody td {
    padding: 0.5rem;
  }
}
</style>
