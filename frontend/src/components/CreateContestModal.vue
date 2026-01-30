<template>
  <!-- Full-screen modal for creating new contests -->
  <div class="modal fade" id="createContestModal" tabindex="-1">
    <div class="modal-dialog modal-fullscreen">
      <div class="modal-content">
        <!-- Modal header with Wikipedia primary color -->
        <div class="modal-header">
          <h5 class="modal-title">Create New Contest</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" :disabled="loading"></button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="handleSubmit">
            <!-- Basic contest information: name and project -->
            <div class="row">
              <div class="col-md-6 mb-3">
                <label for="contestName" class="form-label">Contest Name *</label>
                <input type="text" class="form-control" id="contestName" v-model="formData.name" required
                  :disabled="loading" />
              </div>
              <div class="col-md-6 mb-3">
                <label for="projectName" class="form-label">Project Name *</label>
                <input type="text" class="form-control" id="projectName" v-model="formData.project_name" required
                  :disabled="loading" />
              </div>
            </div>

            <!-- Contest description field -->
            <div class="mb-3">
              <label for="contestDescription" class="form-label">Description</label>
              <textarea class="form-control" id="contestDescription" rows="3" v-model="formData.description"
                :disabled="loading"></textarea>
            </div>

            <!-- Contest rules - required field -->
            <div class="mb-3">
              <label for="contestRules" class="form-label">Contest Rules *</label>
              <textarea class="form-control" id="contestRules" rows="4"
                placeholder="Write rules about how articles must be submitted." v-model="formData.rules_text" required
                :disabled="loading"></textarea>
            </div>

            <!-- Submission type selector: new, expansion, or both -->
            <div class="mb-3">
              <label for="allowedType" class="form-label">Allowed Submission Type</label>
              <select id="allowedType" class="form-control" v-model="formData.allowed_submission_type"
                :disabled="loading">
                <option value="new">New Article Only</option>
                <option value="expansion">Improved Article Only</option>
                <option value="both">Both(New Article + Improved Article)</option>
              </select>
            </div>

            <!-- Contest duration: start and end dates -->
            <div class="row">
              <div class="col-md-6 mb-3">
                <label for="startDate" class="form-label">Start Date *</label>
                <input type="date" class="form-control" id="startDate" v-model="formData.start_date" required
                  :disabled="loading" />
              </div>
              <div class="col-md-6 mb-3">
                <label for="endDate" class="form-label">End Date *</label>
                <input type="date" class="form-control" id="endDate" v-model="formData.end_date" required
                  :disabled="loading" />
              </div>
            </div>

            <!--  FIXED SCORING SECTION - Radio buttons with complete conditional content -->
            <div class="card mb-4">
              <div class="card-header">
                <p class="mb-0">
                  <i class="fas fa-chart-line me-2"></i> Scoring System Configuration
                </p>
                <p class="text-muted mb-0 mt-2" style="font-size: 0.8rem;">
                  Choose how submissions will be scored. You can select only ONE scoring method for this contest.
                </p>
              </div>

              <div class="card-body">
                <!-- Radio Button Selection -->
                <div class="row mb-4">
                  <!-- Simple Scoring Option -->
                  <div class="col-md-6">
                    <label :class="{ 'active': !enableMultiParameterScoring }">
                      <input type="radio" name="scoringMode" :value="false" v-model="enableMultiParameterScoring"
                        :disabled="loading" />
                      <h6>Simple Scoring</h6>
                    </label>
                  </div>

                  <!-- Multi-Parameter Scoring Option -->
                  <div class="col-md-6">
                    <label :class="{ 'active': enableMultiParameterScoring }">
                      <input type="radio" name="scoringMode" :value="true" v-model="enableMultiParameterScoring"
                        :disabled="loading" />
                      <div>
                        <h6>Multi-Parameter Scoring</h6>
                      </div>
                    </label>
                  </div>
                </div>

                <!--  SIMPLE SCORING CONTENT - Shown when enableMultiParameterScoring is FALSE -->
                <div v-if="!enableMultiParameterScoring">
                  <div class="alert alert-success">
                    <i class="fas fa-check-circle me-2"></i>
                    <strong>Simple Scoring Enabled:</strong> Jury will assign a single score for each submission.
                  </div>

                  <div class="row">
                    <div class="col-md-6 mb-3">
                      <label for="marksAccepted" class="form-label">Points for Accepted Submissions *</label>
                      <input type="number" class="form-control" id="marksAccepted"
                        v-model.number="formData.marks_setting_accepted" min="0" required :disabled="loading" />
                      <small class="form-text text-muted">
                        Maximum points that can be awarded. Jury can assign points from 0 up to this value for accepted
                        submissions.
                      </small>
                    </div>
                    <div class="col-md-6 mb-3">
                      <label for="marksRejected" class="form-label">Points for Rejected Submissions *</label>
                      <input type="number" class="form-control" id="marksRejected"
                        v-model.number="formData.marks_setting_rejected" min="0" required :disabled="loading" />
                      <small class="form-text text-muted">
                        Fixed points awarded automatically for rejected submissions (usually 0 or negative).
                      </small>
                    </div>
                  </div>
                </div>

                <!--  MULTI-PARAMETER SCORING CONTENT - Shown when enableMultiParameterScoring is TRUE -->
                <div v-else>
                  <div class="alert alert-primary">
                    <i class="fas fa-star me-2"></i>
                    <strong>Multi-Parameter Scoring Enabled:</strong> Jury will score submissions on multiple parameters
                    with weighted calculation.
                  </div>

                  <!-- Maximum and Minimum score settings -->
                  <div class="row mb-3">
                    <div class="col-md-6">
                      <label class="form-label">Maximum Score (Accepted Submissions) *</label>
                      <input type="number" class="form-control" v-model.number="maxScore" min="1" max="100"
                        placeholder="0" required :disabled="loading" />
                      <small class="text-muted">Final calculated score will be scaled to this value</small>
                    </div>

                    <div class="col-md-6">
                      <label class="form-label">Minimum Score (Rejected Submissions) *</label>
                      <input type="number" class="form-control" v-model.number="minScore" min="0" max="100"
                        placeholder="0" required :disabled="loading" />
                      <small class="text-muted">Score for rejected submissions</small>
                    </div>
                  </div>

                  <!-- Scoring Parameters -->
                  <div class="mb-3">
                    <label class="form-label">
                      <strong>Scoring Parameters</strong>
                      <span class="badge bg-secondary ms-2">Weights must total 100%</span>
                    </label>

                    <div class="parameters-list">
                      <!-- Each parameter -->
                      <div v-for="(param, index) in scoringParameters" :key="index">

                        <div class="row align-items-center">
                          <div class="col-md-3">
                            <input type="text" class="form-control" v-model="param.name" placeholder="Parameter name"
                              required :disabled="loading" />
                          </div>
                          <div class="col-md-3">
                            <div class="input-group">
                              <input type="number" class="form-control" v-model.number="param.weight" min="0" max="100"
                                placeholder="Weight" required :disabled="loading" />
                              <span class="input-group-text">%</span>
                            </div>
                          </div>
                          <div class="col-md-5">
                            <input type="text" class="form-control" v-model="param.description"
                              placeholder="Description (optional)" :disabled="loading" />
                          </div>
                          <div class="col-md-1 text-end">
                            <button type="button" class="btn btn-sm btn-outline-danger" @click="removeParameter(index)"
                              :disabled="scoringParameters.length <= 1 || loading">
                              <i class="fas fa-times"></i>
                            </button>
                          </div>
                        </div>

                      </div>
                    </div>

                    <button type="button" class="btn btn-sm btn-outline-primary mt-2" @click="addParameter"
                      :disabled="loading">
                      <i class="fas fa-plus me-1"></i>Add Parameter
                    </button>

                    <!-- Weight validation -->
                    <div class="mt-3 p-3 rounded" :class="weightTotalClass">
                      <strong>Total Weight: {{ totalWeight }}%</strong>
                      <span v-if="totalWeight !== 100" class="ms-2 text-danger">
                        <i class="fas fa-exclamation-triangle"></i>
                        Must equal 100%
                      </span>
                      <span v-else class="ms-2 text-success">
                        <i class="fas fa-check-circle"></i>
                        Valid
                      </span>
                    </div>
                  </div>

                  <!-- Reset to default parameters -->
                  <button type="button" class="btn btn-sm btn-outline-secondary" @click="loadDefaultParameters"
                    :disabled="loading">
                    <i class="fas fa-redo me-1"></i>Load Default Parameters
                  </button>
                </div>
              </div>
            </div>

            <!-- Organizers section with autocomplete search -->
            <div class="mb-3">
              <label class="form-label">Organizers</label>

              <!-- Display selected organizers as removable badges -->
              <div class="mb-2 p-2 border rounded bg-light organizer-selection-box" style="min-height: 40px;">
                <small v-if="selectedOrganizers.length === 0" class="organizer-placeholder-text">
                  No additional organizers added
                </small>
                <span v-for="username in selectedOrganizers" :key="username" class="badge bg-success me-2 mb-2"
                  style="font-size: 0.9rem; cursor: pointer;">
                  {{ username }}
                  <i class="fas fa-times ms-1" @click="removeOrganizer(username)"></i>
                </span>
              </div>

              <!-- Organizer search input with autocomplete dropdown -->
              <div style="position: relative;">
                <input type="text" class="form-control" v-model="organizerSearchQuery" @input="searchOrganizers"
                  placeholder="Type username to add additional organizers..." autocomplete="off" :disabled="loading" />

                <!-- Autocomplete results dropdown -->
                <div v-if="organizerSearchResults.length > 0 && organizerSearchQuery.length >= 2"
                  class="organizer-autocomplete position-absolute w-100 border rounded-bottom"
                  style="max-height: 200px; overflow-y: auto; z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                  <div v-for="user in organizerSearchResults" :key="user.username"
                    class="p-2 border-bottom cursor-pointer" :class="{ 'bg-info-subtle': isCurrentUser(user.username) }"
                    style="cursor: pointer;" @click="addOrganizer(user.username)">
                    <div class="d-flex align-items-center justify-content-between">
                      <div class="d-flex align-items-center">
                        <i class="fas fa-user-tie me-2 text-success"></i>
                        <strong>{{ user.username }}</strong>
                      </div>
                      <div v-if="isCurrentUser(user.username)" class="badge bg-info">
                        You (already added as creator)
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <small class="form-text text-muted mt-1">
                <i class="fas fa-info-circle me-1"></i>
                You will be automatically added as an organizer. Add others who should manage this contest.
              </small>
            </div>

            <!-- Jury Members section with autocomplete and self-selection warning -->
            <div class="mb-3">
              <label for="juryInput" class="form-label">
                Jury Members *
                <span class="badge bg-info">Type to search users</span>
              </label>

              <!-- Display selected jury members as removable badges -->
              <div class="mb-2 p-2 border rounded bg-light jury-selection-box" style="min-height: 40px;">
                <small v-if="selectedJury.length === 0" class="jury-placeholder-text">
                  No jury members selected yet
                </small>
                <span v-for="username in selectedJury" :key="username" class="badge bg-primary me-2 mb-2"
                  style="font-size: 0.9rem; cursor: pointer;">
                  {{ username }}
                  <i class="fas fa-times ms-1" @click="removeJury(username)"></i>
                </span>
              </div>

              <!-- Jury search input with autocomplete dropdown -->
              <div style="position: relative;">
                <input type="text" class="form-control" id="juryInput" v-model="jurySearchQuery" @input="searchJury"
                  placeholder="Type username to search..." autocomplete="off" :disabled="loading" />
                <!-- Autocomplete results with self-selection warning -->
                <div v-if="jurySearchResults.length > 0 && jurySearchQuery.length >= 2"
                  class="jury-autocomplete position-absolute w-100 border rounded-bottom"
                  style="max-height: 200px; overflow-y: auto; z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                  <div v-for="user in jurySearchResults" :key="user.username" class="p-2 border-bottom cursor-pointer"
                    :class="{ 'bg-warning-subtle self-selection-warning': isCurrentUser(user.username) }"
                    style="cursor: pointer;" @click="addJury(user.username)">
                    <div class="d-flex align-items-center justify-content-between">
                      <div class="d-flex align-items-center">
                        <i class="fas fa-user me-2 text-primary"></i>
                        <strong>{{ user.username }}</strong>
                      </div>
                      <div v-if="isCurrentUser(user.username)" class="self-warning-badge">
                        <i class="fas fa-exclamation-triangle me-1"></i>
                        <strong>This is you - Not Recommended</strong>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Article size requirement in bytes -->
            <div class="mb-3">
              <label for="minByteCount" class="form-label">Minimum Byte Count *</label>
              <input type="number" class="form-control" id="minByteCount" v-model.number="formData.min_byte_count"
                min="0" placeholder="e.g., 1000" required :disabled="loading" />
              <small class="form-text text-muted">Articles must have at least this many bytes</small>
            </div>

            <!-- Minimum reference/citation requirement -->
            <div class="mb-3">
              <label for="minReferenceCount" class="form-label">Minimum Reference Count</label>
              <input type="number" class="form-control" id="minReferenceCount"
                v-model.number="formData.min_reference_count" min="0" placeholder="e.g., 5" :disabled="loading" />
              <small class="form-text text-muted">
                Articles must have at least this many references (external links). Leave as 0 for no requirement.
              </small>
            </div>

            <!-- MediaWiki category URLs for article validation -->
            <div class="mb-3">
              <label class="form-label">
                Category URLs *
                <span class="text-muted">(MediaWiki category pages)</span>
              </label>

              <div v-for="(category, index) in formData.categories" :key="index" class="mb-2">
                <div class="input-group">
                  <input type="url" class="form-control" v-model="formData.categories[index]"
                    :placeholder="index === 0 ? 'https://en.wikipedia.org/wiki/Category:Example' : 'Add another category URL'"
                    required :disabled="loading" />
                  <button v-if="formData.categories.length > 1" type="button" class="btn btn-outline-danger"
                    @click="removeCategory(index)" title="Remove category" :disabled="loading">
                    <i class="fas fa-times"></i>
                  </button>
                </div>
              </div>

              <button type="button" class="btn btn-outline-primary btn-sm" @click="addCategory" :disabled="loading">
                <i class="fas fa-plus me-1"></i>Add Category
              </button>

              <small class="form-text text-muted d-block mt-2">
                At least one MediaWiki category URL is required. Articles must belong to these categories.
              </small>
            </div>

            <!-- Template Link (Optional) -->
            <div class="mb-3">
              <label for="templateLink" class="form-label">
                Contest Template Link
                <span class="badge bg-secondary ms-1">Optional</span>
              </label>
              <input type="url" class="form-control" id="templateLink" v-model="formData.template_link"
                placeholder="https://en.wikipedia.org/wiki/Template:YourContestTemplate" :disabled="loading" />
              <small class="form-text text-muted d-block mt-2">
                <i class="fas fa-info-circle me-1"></i>
                If set, this template will be automatically added to submitted articles that don't already have it.
                The URL must point to a Wiki Template namespace page (e.g., Template:Editathon2025).
              </small>
            </div>

            <!-- Outreach Dashboard URL (Optional) -->
            <div class="mb-3">
              <label for="outreachDashboardUrl" class="form-label">
                Outreach Dashboard URL
                <span class="badge bg-secondary ms-1">Optional</span>
              </label>
              <input type="url" class="form-control" id="outreachDashboardUrl" v-model="formData.outreach_dashboard_url"
                placeholder="https://outreachdashboard.wmflabs.org/courses/WikiClub_Tech_SHUATS/Wikipedia_25_B_Day_Celebration_by_WikiClub_Tech_SHUATS" :disabled="loading" />
              <small class="form-text text-muted d-block mt-2">
                <i class="fas fa-info-circle me-1"></i>
                Link this contest to an Outreach Dashboard course. If provided, course statistics and information will be displayed in a dedicated tab.
                Format: https://outreachdashboard.wmflabs.org/courses/{school}/{course_slug}
              </small>
            </div>

          </form>
        </div>

        <!-- Modal footer with action buttons -->
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" :disabled="loading">Cancel</button>
          <button type="submit" class="btn btn-primary" @click="handleSubmit" :disabled="loading">
            <span v-if="loading">
              <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
              Creating...
            </span>
            <span v-else>Create Contest</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useStore } from '../store'
import { showAlert } from '../utils/alerts'
import api from '../services/api'

export default {
  name: 'CreateContestModal',
  emits: ['created'],
  setup(props, { emit }) {
    const store = useStore()
    const loading = ref(false)
    const selectedJury = ref([])
    const jurySearchQuery = ref('')
    const jurySearchResults = ref([])
    let searchTimeout = null
    const enableMultiParameterScoring = ref(false)
    const maxScore = ref(10)
    const minScore = ref(0)
    const selectedOrganizers = ref([])
    const organizerSearchQuery = ref('')
    const organizerSearchResults = ref([])
    let organizerSearchTimeout = null

    // Default scoring parameters with weights
    const scoringParameters = ref([
      { name: 'Quality', weight: 40, description: 'Article structure & content quality' },
      { name: 'Sources', weight: 30, description: 'References & citations' },
      { name: 'Neutrality', weight: 20, description: 'Unbiased writing' },
      { name: 'Formatting', weight: 10, description: 'Presentation & formatting' }
    ])

    // Calculate total weight of all parameters
    const totalWeight = computed(() => {
      return scoringParameters.value.reduce((sum, param) => sum + (param.weight || 0), 0)
    })

    // Determine background class based on weight validity
    const weightTotalClass = computed(() => {
      return totalWeight.value === 100 ? 'bg-success-subtle' : 'bg-danger-subtle'
    })

    // Add new scoring parameter
    const addParameter = () => {
      scoringParameters.value.push({
        name: '',
        weight: 0,
        description: ''
      })
    }

    // Remove scoring parameter by index
    const removeParameter = (index) => {
      if (scoringParameters.value.length > 1) {
        scoringParameters.value.splice(index, 1)
      }
    }

    // Reset to default parameter configuration
    const loadDefaultParameters = () => {
      scoringParameters.value = [
        { name: 'Quality', weight: 40, description: 'Article structure & content quality' },
        { name: 'Sources', weight: 30, description: 'References & citations' },
        { name: 'Neutrality', weight: 20, description: 'Unbiased writing' },
        { name: 'Formatting', weight: 10, description: 'Presentation & formatting' }
      ]
    }

    // Watch for scoring mode changes
    watch(enableMultiParameterScoring, (newValue) => {
      console.log(`[SCORING] Mode changed to: ${newValue ? 'Multi-Parameter' : 'Simple'}`)

      if (!newValue) {
        // Switching to simple - ensure simple scoring values are set
        if (!formData.marks_setting_accepted) {
          formData.marks_setting_accepted = 10
        }
        if (!formData.marks_setting_rejected && formData.marks_setting_rejected !== 0) {
          formData.marks_setting_rejected = 0
        }
      } else {
        // Switching to multi - ensure parameters are initialized
        if (scoringParameters.value.length === 0) {
          loadDefaultParameters()
        }
      }
    })

    // Reactive computed property for current user from multiple sources
    const currentUser = computed(() => {
      // Check store.state.currentUser first (direct reactive state access - most reliable)
      if (store.state && store.state.currentUser) {
        return store.state.currentUser
      }
      // Then check store.currentUser (computed property)
      if (store.currentUser) {
        return store.currentUser
      }
      return null
    })

    // Form data model for all contest fields
    const formData = reactive({
      name: '',
      project_name: '',
      description: '',
      start_date: '',
      end_date: '',
      jury_members: [],
      organizers: [],
      marks_setting_accepted: 10,
      marks_setting_rejected: 0,
      rules_text: '',
      allowed_submission_type: 'both',
      min_byte_count: 0,
      categories: [''],
      template_link: '',
      outreach_dashboard_url: '',
      min_reference_count: 0
    })

    // Initialize default dates on component mount
    onMounted(async () => {
      const today = new Date()
      const tomorrow = new Date(today)
      tomorrow.setDate(tomorrow.getDate() + 1)
      const nextWeek = new Date(today)
      nextWeek.setDate(nextWeek.getDate() + 7)

      formData.start_date = tomorrow.toISOString().split('T')[0]
      formData.end_date = nextWeek.toISOString().split('T')[0]

      // Ensure current user is loaded from store with retries
      let retries = 0
      const maxRetries = 3
      while (!currentUser.value && retries < maxRetries) {
        await store.checkAuth()
        // Wait a bit for reactive state to update
        await new Promise(resolve => setTimeout(resolve, 200))
        retries++
      }

      if (currentUser.value) {
        console.log('[MODAL] User loaded:', currentUser.value.username)
      } else {
        console.warn('[MODAL] User not loaded after retries')
      }
    })

    // Listen for modal shown event to ensure user is loaded
    onMounted(() => {
      const modalElement = document.getElementById('createContestModal')
      if (modalElement) {
        modalElement.addEventListener('shown.bs.modal', async () => {
          console.log('[MODAL] Modal shown, ensuring user is loaded...')
          if (!currentUser.value) {
            await store.checkAuth()
            await new Promise(resolve => setTimeout(resolve, 200))
          }
          if (currentUser.value) {
            console.log('[MODAL] User loaded after modal shown:', currentUser.value.username)
          }
        })
      }
    })

    // Watch for user changes to log and check self-selection
    watch(currentUser, (newUser, oldUser) => {
      if (newUser) {
        console.log('[MODAL] User loaded/changed:', {
          username: newUser.username,
          oldUser: oldUser?.username,
          selectedJury: selectedJury.value
        })
        // If user just loaded and we have selected jury, check for self-selection
        if (selectedJury.value.length > 0 && !oldUser) {
          console.log('[MODAL] User loaded with jury selected, checking for self-selection...')
        }
      }
    }, { immediate: true })

    // Debounced search for jury members with filtering
    const searchJury = async () => {
      const query = jurySearchQuery.value.trim()

      if (query.length < 2) {
        jurySearchResults.value = []
        return
      }

      // Debounce search requests
      if (searchTimeout) {
        clearTimeout(searchTimeout)
      }

      searchTimeout = setTimeout(async () => {
        try {
          const response = await api.get(`/user/search?q=${encodeURIComponent(query)}&limit=10`)
          // Filter out already selected users
          jurySearchResults.value = (response.users || []).filter(
            user => !selectedJury.value.includes(user.username)
          )
        } catch (error) {
          console.error('User search error:', error)
          jurySearchResults.value = []
        }
      }, 300)
    }

    // Check if username matches current user (case-insensitive)
    const isCurrentUser = (username) => {
      // Use the computed currentUser property for reactivity
      const currentUsername = currentUser.value?.username
      if (!currentUsername || !username) {
        return false
      }
      // Normalize usernames for comparison (case-insensitive, trimmed)
      const normalizedCurrent = String(currentUsername).trim().toLowerCase()
      const normalizedUsername = String(username).trim().toLowerCase()
      return normalizedCurrent === normalizedUsername
    }

    // Add jury member with self-selection warning
    const addJury = async (username) => {
      // Check if user is trying to add themselves
      if (isCurrentUser(username)) {
        // Show confirmation dialog before adding
        const confirmed = window.confirm(
          ' WARNING: Self-Selection as Jury Member\n\n' +
          'You are about to select yourself as a jury member.\n\n' +
          'It is strongly recommended to select other users as jury members to maintain fairness and objectivity.\n\n' +
          'Are you sure you want to proceed with selecting yourself?'
        )

        // If user cancels, don't add them
        if (!confirmed) {
          return
        }
      }

      // Add the jury member if not already selected
      if (!selectedJury.value.includes(username)) {
        selectedJury.value.push(username)
        formData.jury_members = [...selectedJury.value]
        jurySearchQuery.value = ''
        jurySearchResults.value = []
      }
    }

    // Remove jury member from selection
    const removeJury = (username) => {
      selectedJury.value = selectedJury.value.filter(u => u !== username)
      formData.jury_members = [...selectedJury.value]
    }

    // Add new category URL field
    const addCategory = () => {
      formData.categories.push('')
    }

    // Remove category URL field by index
    const removeCategory = (index) => {
      if (formData.categories.length > 1) {
        formData.categories.splice(index, 1)
      }
    }

    // Debounced search for organizers with filtering
    const searchOrganizers = async () => {
      const query = organizerSearchQuery.value.trim()

      if (query.length < 2) {
        organizerSearchResults.value = []
        return
      }

      // Debounce search requests
      if (organizerSearchTimeout) {
        clearTimeout(organizerSearchTimeout)
      }

      organizerSearchTimeout = setTimeout(async () => {
        try {
          const response = await api.get(`/user/search?q=${encodeURIComponent(query)}&limit=10`)
          // Filter out already selected organizers and current user
          organizerSearchResults.value = (response.users || []).filter(
            user => !selectedOrganizers.value.includes(user.username) &&
              !isCurrentUser(user.username)
          )
        } catch (error) {
          console.error('Organizer search error:', error)
          organizerSearchResults.value = []
        }
      }, 300)
    }

    // Add organizer (prevent adding current user)
    const addOrganizer = (username) => {
      // Don't add current user (they're already creator)
      if (isCurrentUser(username)) {
        showAlert('You will be added automatically as contest creator', 'info')
        return
      }

      // Add the organizer if not already selected
      if (!selectedOrganizers.value.includes(username)) {
        selectedOrganizers.value.push(username)
        formData.organizers = [...selectedOrganizers.value]
        organizerSearchQuery.value = ''
        organizerSearchResults.value = []
      }
    }

    // Remove organizer from selection
    const removeOrganizer = (username) => {
      selectedOrganizers.value = selectedOrganizers.value.filter(u => u !== username)
      formData.organizers = [...selectedOrganizers.value]
    }

    // Validate and submit contest creation form
    const handleSubmit = async () => {
      // Prevent multiple submissions
      if (loading.value) {
        return
      }

      // Basic validation
      if (!formData.name.trim()) {
        showAlert('Contest name is required', 'warning')
        return
      }
      if (!formData.project_name.trim()) {
        showAlert('Project name is required', 'warning')
        return
      }
      if (!formData.start_date) {
        showAlert('Start date is required', 'warning')
        return
      }
      if (!formData.end_date) {
        showAlert('End date is required', 'warning')
        return
      }
      if (selectedJury.value.length === 0) {
        showAlert('At least one jury member is required', 'warning')
        return
      }
      if (new Date(formData.start_date) >= new Date(formData.end_date)) {
        showAlert('End date must be after start date', 'warning')
        return
      }
      if (
        formData.min_byte_count === null ||
        formData.min_byte_count === undefined ||
        isNaN(formData.min_byte_count) ||
        formData.min_byte_count < 0
      ) {
        showAlert(
          'Minimum byte count is required and must be a non-negative number',
          'warning'
        )
        return
      }

      // Validate categories
      const validCategories = formData.categories.filter(cat => cat && cat.trim())
      if (validCategories.length === 0) {
        showAlert('At least one category URL is required', 'warning')
        return
      }

      // Validate category URLs format
      for (const category of validCategories) {
        if (!category.startsWith('http://') && !category.startsWith('https://')) {
          showAlert('All category URLs must be valid HTTP/HTTPS URLs', 'warning')
          return
        }
      }

      // Validate template link if provided
      if (formData.template_link && formData.template_link.trim()) {
        const templateLink = formData.template_link.trim()
        // Basic URL format validation
        if (!templateLink.startsWith('http://') && !templateLink.startsWith('https://')) {
          showAlert('Template link must be a valid HTTP/HTTPS URL', 'warning')
          return
        }
        // Check if URL appears to point to a Template namespace page
        // This is a basic check - backend will do comprehensive validation
        const urlLower = templateLink.toLowerCase()
        if (!urlLower.includes('template:') && !urlLower.includes('/template/')) {
          showAlert(
            'Template link should point to a Template namespace page (e.g., Template:YourTemplate)',
            'warning'
          )
          return
        }
      }

      // Validate Outreach Dashboard URL if provided
      if (formData.outreach_dashboard_url && formData.outreach_dashboard_url.trim()) {
        const outreachUrl = formData.outreach_dashboard_url.trim()
        // Basic URL format validation
        if (!outreachUrl.startsWith('http://') && !outreachUrl.startsWith('https://')) {
          showAlert('Outreach Dashboard URL must be a valid HTTP/HTTPS URL', 'warning')
          return
        }
        // Check if it's an Outreach Dashboard URL
        if (!outreachUrl.includes('outreachdashboard.wmflabs.org')) {
          showAlert(
            'Outreach Dashboard URL must point to outreachdashboard.wmflabs.org',
            'warning'
          )
          return
        }
      }

      // Scoring-specific validation
      if (enableMultiParameterScoring.value) {
        if (totalWeight.value !== 100) {
          showAlert(
            'Multi-Parameter Scoring requires weights to sum to 100%. ' +
            `Current total: ${totalWeight.value}%`,
            'warning'
          )
          return
        }

        // Validate all parameters have names
        const invalidParams = scoringParameters.value.filter(p => !p.name.trim())
        if (invalidParams.length > 0) {
          showAlert('All scoring parameters must have names', 'warning')
          return
        }
      } else {
        // Simple scoring validation
        if (formData.marks_setting_accepted < 0) {
          showAlert('Points for accepted submissions must be non-negative', 'warning')
          return
        }
      }

      // Set loading state to prevent multiple submissions
      loading.value = true

      try {
        // Build scoring parameters payload
        let scoringParametersPayload = null

        console.log('[CREATE] enableMultiParameterScoring:', enableMultiParameterScoring.value)
        console.log('[CREATE] scoringParameters:', scoringParameters.value)
        console.log('[CREATE] totalWeight:', totalWeight.value)

        if (enableMultiParameterScoring.value) {
          scoringParametersPayload = {
            enabled: true,
            max_score: Number(maxScore.value),
            min_score: Number(minScore.value),
            parameters: scoringParameters.value.map(param => ({
              name: String(param.name || ''),
              weight: Number(param.weight || 0),
              description: String(param.description || '')
            }))
          }

          console.log('[CREATE] Built scoring payload:', JSON.stringify(scoringParametersPayload, null, 2))
        } else {
          scoringParametersPayload = {
            enabled: false,
            max_score: Number(formData.marks_setting_accepted),
            min_score: Number(formData.marks_setting_rejected),
            parameters: []
          }

          console.log('[CREATE] Simple scoring payload:', scoringParametersPayload)
        }

        // Prepare template link: trim if provided, otherwise set to null
        let templateLinkValue = null
        if (formData.template_link && typeof formData.template_link === 'string') {
          const trimmed = formData.template_link.trim()
          templateLinkValue = trimmed.length > 0 ? trimmed : null
        }

        // Prepare Outreach Dashboard URL: trim if provided, otherwise set to null
        let outreachUrlValue = null
        if (formData.outreach_dashboard_url && typeof formData.outreach_dashboard_url === 'string') {
          const trimmed = formData.outreach_dashboard_url.trim()
          outreachUrlValue = trimmed.length > 0 ? trimmed : null
        }

        // Construct contest data payload with all form values
        const contestData = {
          ...formData,
          jury_members: selectedJury.value,
          organizers: selectedOrganizers.value,
          rules: {
            text: formData.rules_text.trim()
          },
          // Byte count field: required, must be a valid non-negative number
          min_byte_count: Number(formData.min_byte_count),
          // Categories: filter out empty strings and trim
          categories: formData.categories.filter(cat => cat && cat.trim()).map(cat => cat.trim()),
          // Template link (optional): trim or set to null if empty
          template_link: templateLinkValue,
          // Outreach Dashboard URL (optional): trim or set to null if empty
          outreach_dashboard_url: outreachUrlValue,
          scoring_parameters: scoringParametersPayload,
          min_reference_count: formData.min_reference_count || 0
        }

        // Submit contest creation request
        console.log('[CREATE CONTEST] Submitting contest data:', contestData)
        const result = await store.createContest(contestData)
        console.log('[CREATE CONTEST] Result:', result)
        
        if (result.success) {
          showAlert('Contest created successfully!', 'success')
          emit('created')

          // Wait a bit for alert to show
          await new Promise(resolve => setTimeout(resolve, 100))

          // Close modal programmatically
          const modalElement = document.getElementById('createContestModal')
          const modal = bootstrap.Modal.getInstance(modalElement)
          if (modal) {
            modal.hide()
          }

          // Reset form
          resetForm()
        } else {
          console.error('[CREATE CONTEST] Error:', result.error)
          showAlert(result.error || 'Failed to create contest', 'danger')
        }
      } catch (error) {
        console.error('[CREATE CONTEST] Exception:', error)
        showAlert('Failed to create contest: ' + (error.message || 'Unknown error'), 'danger')
      } finally {
        // Always reset loading state
        loading.value = false
      }
    }

    // Reset form to initial state
    const resetForm = () => {
      formData.name = ''
      formData.project_name = ''
      formData.description = ''
      selectedJury.value = []
      formData.jury_members = []
      selectedOrganizers.value = []
      formData.organizers = []
      formData.rules_text = ''
      formData.min_byte_count = 0
      formData.categories = ['']
      formData.template_link = ''
      formData.outreach_dashboard_url = ''
      formData.min_reference_count = 0

      // Reset dates to default (tomorrow and next week)
      const today = new Date()
      const tomorrow = new Date(today)
      tomorrow.setDate(tomorrow.getDate() + 1)
      const nextWeek = new Date(today)
      nextWeek.setDate(nextWeek.getDate() + 7)
      formData.start_date = tomorrow.toISOString().split('T')[0]
      formData.end_date = nextWeek.toISOString().split('T')[0]
      enableMultiParameterScoring.value = false
      maxScore.value = 10
      minScore.value = 0
      loadDefaultParameters()
    }

    return {
      formData,
      selectedJury,
      jurySearchQuery,
      jurySearchResults,
      selectedOrganizers,
      organizerSearchQuery,
      organizerSearchResults,
      loading,
      isCurrentUser,
      currentUser,
      searchJury,
      addJury,
      removeJury,
      searchOrganizers,
      addOrganizer,
      removeOrganizer,
      addCategory,
      removeCategory,
      handleSubmit,
      store,
      enableMultiParameterScoring,
      maxScore,
      minScore,
      scoringParameters,
      totalWeight,
      weightTotalClass,
      addParameter,
      removeParameter,
      loadDefaultParameters
    }
  }
}
</script>


<style scoped>
/* Modal header with Wikipedia primary color */
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

/* Close button with inverted colors */
.modal-header .btn-close {
  filter: invert(1) brightness(1.2);
  opacity: 0.9;
}

/* Dark mode: brighter close button */
[data-theme="dark"] .modal-header .btn-close {
  filter: invert(1) brightness(2);
}

/* Modal body background adapts to theme */
.modal-body {
  background-color: var(--wiki-modal-bg);
  color: var(--wiki-text);
  transition: background-color 0.3s ease, color 0.3s ease;
}

/* Form labels with consistent styling */
.form-label {
  color: var(--wiki-dark);
  font-weight: 500;
  margin-bottom: 0.5rem;
  transition: color 0.3s ease;
}

/* All form inputs with theme-aware styling */
.form-control {
  border-color: var(--wiki-input-border);
  background-color: var(--wiki-input-bg);
  color: var(--wiki-text);
  transition: all 0.2s ease;
}

/* Dark mode: ensure visible borders */
[data-theme="dark"] .form-control {
  border-width: 1px;
  border-style: solid;
}

/* Textarea with vertical resize only */
textarea.form-control {
  resize: vertical;
  min-height: 80px;
}

/* Focus state with Wikipedia blue accent */
.form-control:focus {
  border-color: var(--wiki-primary);
  box-shadow: 0 0 0 0.2rem rgba(0, 102, 153, 0.25);
  background-color: var(--wiki-input-bg);
  color: var(--wiki-text);
  outline: none;
}

/* Dark mode: adjusted focus shadow */
[data-theme="dark"] .form-control:focus {
  box-shadow: 0 0 0 0.2rem rgba(93, 184, 230, 0.3);
  border-color: var(--wiki-primary);
}

/* Placeholder text adapts to theme */
.form-control::placeholder {
  color: var(--wiki-text-muted);
  opacity: 0.7;
  transition: color 0.3s ease;
}

/* Dark mode: slightly dimmer placeholder */
[data-theme="dark"] .form-control::placeholder {
  opacity: 0.6;
}

/* Jury input placeholder - enhanced visibility */
#juryInput::placeholder {
  color: #666666 !important;
  opacity: 1 !important;
  font-weight: 500;
}

/* Dark mode: white placeholder for jury input */
[data-theme="dark"] #juryInput::placeholder {
  color: #ffffff !important;
  opacity: 0.9 !important;
}

/* Date input color scheme adaptation */
input[type="date"].form-control {
  color-scheme: light;
}

/* Dark mode: dark color scheme for date picker */
[data-theme="dark"] input[type="date"].form-control {
  color-scheme: dark;
}

/* Base badge styling */
.badge {
  font-weight: 500;
  padding: 0.4em 0.8em;
}

/* Primary badge with Wikipedia blue */
.badge.bg-primary {
  background-color: var(--wiki-primary) !important;
}

/* Info badge also uses primary color */
.badge.bg-info {
  background-color: var(--wiki-primary) !important;
  color: white;
}

/* Text-dark badges adapt to theme */
.badge.text-dark {
  color: var(--wiki-dark) !important;
  transition: color 0.3s ease;
}

/* Dark mode: light text for readability */
[data-theme="dark"] .badge.text-dark {
  color: #f0f0f0 !important;
}

/* Light background box for selected items */
.bg-light {
  background-color: var(--wiki-hover-bg) !important;
  border-color: var(--wiki-primary) !important;
  border: 1px solid var(--wiki-border);
  border-radius: 4px;
  padding: 1rem;
  transition: background-color 0.2s ease, border-color 0.2s ease;
}

/* Dark mode: subtle blue tint */
[data-theme="dark"] .bg-light {
  background-color: rgba(93, 184, 230, 0.1) !important;
}

/* Placeholder text in jury selection box */
.jury-selection-box .jury-placeholder-text {
  color: #333333 !important;
  font-weight: 500;
}

/* Dark mode: white placeholder text */
[data-theme="dark"] .jury-selection-box .jury-placeholder-text {
  color: #ffffff !important;
}

/* Jury member badges with hover effect */
.badge.bg-primary {
  background-color: var(--wiki-primary) !important;
  color: white;
  cursor: pointer;
  transition: all 0.2s ease;
}

.badge.bg-primary:hover {
  background-color: var(--wiki-primary-hover) !important;
}

/* Dropdown container with theme-aware styling */
.jury-autocomplete {
  border: 1px solid var(--wiki-border);
  border-top: none;
  border-radius: 0 0 4px 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  background-color: var(--wiki-card-bg);
  transition: background-color 0.2s ease, border-color 0.2s ease;
}

/* Dark mode: stronger shadow */
[data-theme="dark"] .jury-autocomplete {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

/* Dropdown items with hover state */
.jury-autocomplete .p-2 {
  transition: background-color 0.2s ease;
  color: var(--wiki-text);
}

.jury-autocomplete .p-2:hover {
  background-color: var(--wiki-hover-bg) !important;
}

/* Enhanced warning background for self-selection */
.jury-autocomplete .bg-warning-subtle.self-selection-warning {
  background-color: rgba(255, 193, 7, 0.25) !important;
  border-left: 5px solid #ffc107;
  border-right: 2px solid rgba(255, 193, 7, 0.3);
  animation: pulse-warning 2s ease-in-out infinite;
}

/* Dark mode: stronger warning colors */
[data-theme="dark"] .jury-autocomplete .bg-warning-subtle.self-selection-warning {
  background-color: rgba(255, 193, 7, 0.35) !important;
  border-left: 5px solid #ffc107;
  border-right: 2px solid rgba(255, 193, 7, 0.4);
}

/* Hover state for warning */
.jury-autocomplete .bg-warning-subtle.self-selection-warning:hover {
  background-color: rgba(255, 193, 7, 0.35) !important;
  border-left: 5px solid #ff9800;
}

/* Dark mode: hover state */
[data-theme="dark"] .jury-autocomplete .bg-warning-subtle.self-selection-warning:hover {
  background-color: rgba(255, 193, 7, 0.45) !important;
  border-left: 5px solid #ff9800;
}

/* Enhanced warning badge for self-selection */
.self-warning-badge {
  background-color: #ffc107;
  color: #000;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
  white-space: nowrap;
  display: flex;
  align-items: center;
  box-shadow: 0 2px 4px rgba(255, 193, 7, 0.4);
  border: 1px solid rgba(255, 193, 7, 0.6);
}

/* Dark mode: orange warning badge with white text */
[data-theme="dark"] .self-warning-badge {
  background-color: #ff9800;
  color: #fff;
  box-shadow: 0 2px 4px rgba(255, 152, 0, 0.5);
  border: 1px solid rgba(255, 152, 0, 0.7);
}

/* Pulse animation for warning indicator */
@keyframes pulse-warning {

  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(255, 193, 7, 0.4);
  }

  50% {
    box-shadow: 0 0 0 4px rgba(255, 193, 7, 0);
  }
}

/* Dark mode: warning hover state */
[data-theme="dark"] .jury-autocomplete .bg-warning-subtle:hover {
  background-color: rgba(255, 193, 7, 0.35) !important;
}

/* Primary text color in dropdown */
.jury-autocomplete .text-primary {
  color: var(--wiki-primary) !important;
}

/* Primary button with Wikipedia blue */
.btn-primary {
  background-color: var(--wiki-primary);
  border-color: var(--wiki-primary);
  font-weight: 500;
  transition: all 0.2s ease;
}

/* Primary button hover with shadow */
.btn-primary:hover {
  background-color: var(--wiki-primary-hover);
  border-color: var(--wiki-primary-hover);
  box-shadow: 0 2px 4px rgba(0, 102, 153, 0.2);
}

/* Disabled button state */
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

/* Dark mode: adjusted secondary button */
[data-theme="dark"] .btn-secondary {
  background-color: #5a6268;
  border-color: #5a6268;
}

[data-theme="dark"] .btn-secondary:hover {
  background-color: #6c757d;
  border-color: #6c757d;
}

/* Footer with theme-aware styling */
.modal-footer {
  border-top: 1px solid var(--wiki-border);
  padding: 1rem 1.5rem;
  background-color: var(--wiki-modal-bg);
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

/* Muted text color */
.text-muted {
  color: var(--wiki-text-muted) !important;
  transition: color 0.3s ease;
}

/* Small spinner for loading states */
.spinner-border-sm {
  width: 1rem;
  height: 1rem;
  border-width: 0.15em;
  border-color: currentColor;
  border-right-color: transparent;
}

/* Modal takes full viewport */
.modal-fullscreen {
  width: 100vw;
  max-width: 100%;
  height: 100vh;
  margin: 0;
  padding: 0;
}

/* Content fills viewport with flexbox */
.modal-fullscreen .modal-content {
  height: 100vh;
  border: 0;
  border-radius: 0;
  display: flex;
  flex-direction: column;
}

/* Body scrolls with flex grow */
.modal-fullscreen .modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

/* Better spacing for full screen layout */
.modal-fullscreen .modal-body .row {
  margin-bottom: 1rem;
}

.modal-fullscreen .modal-body .mb-3 {
  margin-bottom: 1.5rem !important;
}

/* Center form with max width */
.modal-fullscreen .modal-body form {
  max-width: 1200px;
  margin: 0 auto;
}

/* Organizer selection box with green accent */
.organizer-selection-box {
  background-color: var(--wiki-hover-bg) !important;
  border-color: #28a745 !important;
  border: 1px solid var(--wiki-border);
  border-radius: 4px;
  padding: 1rem;
  transition: background-color 0.2s ease, border-color 0.2s ease;
}

/* Dark mode: green tint */
[data-theme="dark"] .organizer-selection-box {
  background-color: rgba(40, 167, 69, 0.1) !important;
}

/* Organizer placeholder text */
.organizer-selection-box .organizer-placeholder-text {
  color: #333333 !important;
  font-weight: 500;
}

/* Dark mode: white placeholder */
[data-theme="dark"] .organizer-selection-box .organizer-placeholder-text {
  color: #ffffff !important;
}

/* Success badge for organizers */
.badge.bg-success {
  background-color: #28a745 !important;
  color: white;
  cursor: pointer;
  transition: all 0.2s ease;
}

.badge.bg-success:hover {
  background-color: #218838 !important;
}

/* Organizer dropdown styling */
.organizer-autocomplete {
  border: 1px solid var(--wiki-border);
  border-top: none;
  border-radius: 0 0 4px 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  background-color: var(--wiki-card-bg);
  transition: background-color 0.2s ease, border-color 0.2s ease;
}

/* Dark mode: stronger shadow */
[data-theme="dark"] .organizer-autocomplete {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

/* Dropdown items with hover */
.organizer-autocomplete .p-2 {
  transition: background-color 0.2s ease;
  color: var(--wiki-text);
}

.organizer-autocomplete .p-2:hover {
  background-color: var(--wiki-hover-bg) !important;
}

/* Current user indicator in organizer dropdown */
.organizer-autocomplete .bg-info-subtle {
  background-color: rgba(13, 202, 240, 0.15) !important;
  border-left: 3px solid #0dcaf0;
}

/* Dark mode: info indicator */
[data-theme="dark"] .organizer-autocomplete .bg-info-subtle {
  background-color: rgba(13, 202, 240, 0.25) !important;
}

/* Success text color */
.organizer-autocomplete .text-success {
  color: #28a745 !important;
}

/* Secondary badge for informational text */
.badge.bg-secondary {
  background-color: #6c757d !important;
  color: white;
}
</style>
