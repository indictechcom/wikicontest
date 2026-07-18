<template>
  <div class="edit-contest-page">
    <!-- Loading State -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="alert alert-danger">
      <i class="fas fa-exclamation-circle me-2"></i>{{ error }}
      <button class="btn btn-sm btn-outline-danger ms-3" @click="goBack">Go Back</button>
    </div>

    <!-- Edit Form -->
    <div v-else-if="contest">
      <form @submit.prevent="saveContestEdits">
        <!-- Basic Information Section -->
        <div class="edit-section">
          <h6 class="section-title">
            <i class="fas fa-info-circle me-2"></i>Basic Information
          </h6>

          <div class="mb-3">
            <label class="form-label">Contest Name *</label>
            <input v-model="editForm.name" class="form-control" required />
          </div>

          <div class="mb-3">
            <label class="form-label">Project Name *</label>
            <input v-model="editForm.project_name" class="form-control" required />
          </div>

          <div class="mb-3">
            <label for="editContestDescription" class="form-label">Description</label>
            <textarea class="form-control" id="editContestDescription" rows="3"
              v-model="editForm.description"></textarea>
          </div>

          <div class="mb-3">
            <label for="editContestRules" class="form-label">Contest Rules *</label>
            <textarea class="form-control" id="editContestRules" rows="4"
              placeholder="Write rules about how articles must be submitted." v-model="editForm.rules"
              required></textarea>
          </div>

          <div class="mb-3">
            <label for="editAllowedType" class="form-label">Allowed Submission Type *</label>
            <select id="editAllowedType" class="form-control" v-model="editForm.allowed_submission_type">
              <option value="new">New Article Only</option>
              <option value="expansion">Improved Article Only</option>
              <option value="both">Both (New Article + Improved Article)</option>
            </select>
          </div>

          <div class="row">
            <div class="col-md-6 mb-3">
              <label for="editStartDate" class="form-label">Start Date *</label>
              <input type="date" class="form-control" id="editStartDate" v-model="editForm.start_date" required />
            </div>
            <div class="col-md-6 mb-3">
              <label for="editEndDate" class="form-label">End Date *</label>
              <input type="date" class="form-control" id="editEndDate" v-model="editForm.end_date" required />
            </div>
          </div>
        </div>

        <!-- Organizers Section -->
        <div class="edit-section">
          <h6 class="section-title">
            <i class="fas fa-user-tie me-2"></i>Organizers
          </h6>

          <div class="mb-2 p-2 border rounded bg-light organizer-selection-box" style="min-height: 40px;">
            <small v-if="editForm.selectedOrganizers.length === 0" class="organizer-placeholder-text">
              No additional organizers added
            </small>
            <span v-for="username in editForm.selectedOrganizers" :key="username" class="badge bg-success me-2 mb-2"
              style="font-size: 0.9rem; cursor: pointer;">
              {{ username }}
              <i class="fas fa-times ms-1" @click="removeOrganizer(username)"></i>
            </span>
          </div>

          <div style="position: relative;">
            <input type="text" class="form-control" v-model="organizerSearchQuery" @input="searchOrganizers"
              placeholder="Type username to add additional organizers..." autocomplete="off" />

            <div v-if="organizerSearchResults.length > 0 && organizerSearchQuery.length >= 2"
              class="organizer-autocomplete position-absolute w-100 border rounded-bottom"
              style="max-height: 200px; overflow-y: auto; z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
              <div v-for="user in organizerSearchResults" :key="user.username"
                class="p-2 border-bottom cursor-pointer"
                :class="{ 'bg-warning-subtle': isCurrentUser(user.username) }" style="cursor: pointer;"
                @click="addOrganizer(user.username)">
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

        <!-- Jury Members Section -->
        <div class="edit-section">
          <h6 class="section-title">
            <i class="fas fa-gavel me-2"></i>Jury Members
          </h6>

          <div class="mb-2 p-2 border rounded bg-light jury-selection-box" style="min-height: 40px;">
            <small v-if="editForm.selectedJuryMembers.length === 0" class="jury-placeholder-text">
              No jury members selected yet
            </small>
            <span v-for="username in editForm.selectedJuryMembers" :key="username"
              class="badge bg-primary me-2 mb-2" style="font-size: 0.9rem; cursor: pointer;">
              <i class="fas fa-gavel me-1"></i>{{ username }}
              <i class="fas fa-times ms-1" @click="removeJuryMember(username)"></i>
            </span>
          </div>

          <div style="position: relative;">
            <input type="text" class="form-control" v-model="jurySearchQuery" @input="searchJuryMembers"
              placeholder="Type username to search and add..." autocomplete="off" />

            <div v-if="jurySearchResults.length > 0 && jurySearchQuery.length >= 2"
              class="jury-autocomplete position-absolute w-100 border rounded-bottom"
              style="max-height: 200px; overflow-y: auto; z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
              <div v-for="user in jurySearchResults" :key="user.username" class="p-2 border-bottom cursor-pointer"
                :class="{ 'bg-warning-subtle': isCurrentUser(user.username) }" style="cursor: pointer;"
                @click="addJuryMember(user.username)">
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

          <small class="form-text text-muted mt-1">
            <i class="fas fa-info-circle me-1"></i>
            Jury members will review and score submissions. It's recommended to select other users.
          </small>
        </div>

        <!-- Scoring System Section -->
        <div class="edit-section scoring-section-edit">
          <h6 class="section-title">
            <i class="fas fa-chart-line me-2"></i>Scoring System
          </h6>

          <!-- Lock Status Banner -->
          <div class="scoring-lock-status mb-3">
            <!-- LOCKED STATE -->
            <div v-if="scoringModeLocked" class="lock-banner locked">
              <div class="lock-banner-icon">
                <i class="fas fa-lock"></i>
              </div>
              <div class="lock-banner-content">
                <div class="lock-banner-title">
                  <strong>Scoring Mode is Locked</strong>
                </div>
                <div class="lock-banner-text">
                  This contest has <strong>{{ reviewedSubmissionsCount }}</strong>
                  reviewed {{ reviewedSubmissionsCount === 1 ? 'submission' : 'submissions' }}.
                  The scoring mode cannot be changed to ensure fairness.
                </div>
              </div>
            </div>

            <!-- UNLOCKED STATE -->
            <div v-else class="lock-banner unlocked">
              <div class="lock-banner-icon">
                <i class="fas fa-unlock-alt"></i>
              </div>
              <div class="lock-banner-content">
                <div class="scoring-mode-badge">
                  <span v-if="contestScoringMode === 'automated'" class="badge-mode automated">
                    <i class="fas fa-robot me-2"></i>Automated Scoring
                  </span>
                  <span v-else-if="contestScoringMode === 'multi_parameter'" class="badge-mode multi">
                    <i class="fas fa-star me-2"></i>Multi-Parameter Scoring
                  </span>
                  <span v-else class="badge-mode simple">
                    <i class="fas fa-calculator me-2"></i>Simple Scoring
                  </span>
                </div>
                <div class="lock-banner-title">
                  <strong>Scoring Mode is Editable:</strong>No submissions have been
                  reviewed yet. You can change the scoring mode if needed.
                </div>
              </div>
            </div>
          </div>

          <!-- LOCKED MODE: Show What Can Be Edited -->
          <div v-if="scoringModeLocked" class="locked-edit-info">
            <div class="alert alert-info mb-3">
              <i class="fas fa-info-circle me-2"></i>
              <strong>What you can edit:</strong>
              <ul class="mb-0 mt-2">
                <li v-if="contestScoringMode === 'automated'">
                  Nothing
                </li>
                <li v-if="contestScoringMode === 'multi_parameter'">
                  Maximum and minimum score values
                </li>
                <li v-if="contestScoringMode === 'multi_parameter'">
                  Parameter weights (must still sum to 100%)
                </li>
                <li v-if="contestScoringMode === 'multi_parameter'">
                  Parameter names and descriptions
                </li>
                <li v-if="contestScoringMode === 'simple'">
                  Points for accepted and rejected submissions
                </li>
              </ul>
            </div>

            <!-- Multi-Parameter Locked Editing -->
            <div v-if="contestScoringMode === 'multi_parameter'">
              <div class="row mb-3">
                <div class="col-md-6">
                  <label class="form-label">Maximum Score (Accepted) *</label>
                  <input type="number" class="form-control" v-model.number="maxScore" min="1" max="1000" required />
                  <small class="text-muted">Final score scaled to this value</small>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Minimum Score (Rejected) *</label>
                  <input type="number" class="form-control" v-model.number="minScore" min="0" max="1000" required />
                  <small class="text-muted">Score for rejected submissions</small>
                </div>
              </div>

              <div class="mb-3">
                <label class="form-label fw-bold">Scoring Parameters *</label>
                <div class="parameters-list">
                  <div v-for="(param, index) in scoringParameters" :key="index" class="parameter-item card mb-2">
                    <div class="card-body p-3">
                      <div class="row align-items-center">
                        <div class="col-md-3">
                          <label class="small text-muted mb-1">Parameter Name</label>
                          <input type="text" class="form-control" v-model="param.name" placeholder="e.g., Quality"
                            required />
                        </div>
                        <div class="col-md-3">
                          <label class="small text-muted mb-1">Weight (%)</label>
                          <div class="input-group">
                            <input type="number" class="form-control" v-model.number="param.weight" min="0"
                              max="100" placeholder="0-100" required />
                            <span class="input-group-text">%</span>
                          </div>
                        </div>
                        <div class="col-md-5">
                          <label class="small text-muted mb-1">Description (Optional)</label>
                          <input type="text" class="form-control" v-model="param.description"
                            placeholder="Brief description" />
                        </div>
                        <div class="col-md-1 text-end">
                          <label class="small text-muted mb-1 d-block">&nbsp;</label>
                          <button type="button" class="btn btn-sm btn-outline-danger"
                            @click="removeParameter(index)" :disabled="scoringParameters.length <= 1"
                            title="Remove parameter">
                            <i class="fas fa-trash"></i>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <button type="button" class="btn btn-sm btn-outline-primary mt-2" @click="addParameter">
                  <i class="fas fa-plus me-1"></i>Add Parameter
                </button>

                <div class="mt-3 p-3 rounded" :class="weightTotalClass">
                  <div class="d-flex justify-content-between align-items-center">
                    <strong>Total Weight: {{ totalWeight }}%</strong>
                    <span v-if="totalWeight !== 100" class="text-danger">
                      <i class="fas fa-exclamation-triangle me-1"></i>
                      Must equal 100%
                    </span>
                    <span v-else class="text-success">
                      <i class="fas fa-check-circle me-1"></i>
                      Valid
                    </span>
                  </div>
                </div>
              </div>

              <button type="button" class="btn btn-sm btn-outline-secondary" @click="loadDefaultParameters">
                <i class="fas fa-redo me-1"></i>Reset to Default Parameters
              </button>
            </div>

            <!-- Simple Scoring Locked Editing -->
            <div v-else-if="contestScoringMode === 'simple'">
              <div class="row">
                <div class="col-md-6 mb-3">
                  <label class="form-label">Points for Accepted Submissions *</label>
                  <input type="number" class="form-control" v-model.number="editForm.marks_setting_accepted" min="0"
                    required />
                  <small class="text-muted">Maximum points for accepted submissions</small>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label">Points for Rejected Submissions *</label>
                  <input type="number" class="form-control" v-model.number="editForm.marks_setting_rejected" min="0"
                    required />
                  <small class="text-muted">Points for rejected submissions (usually 0)</small>
                </div>
              </div>
            </div>

            <!-- Automated Scoring Locked Editing -->
            <div v-else-if="contestScoringMode === 'automated'">
              <div class="mb-4">
                <h6 class="mb-3"><i class="fas fa-filter me-2"></i>Eligibility Criteria</h6>
                <div class="row">
                  <div class="col-md-6 mb-3">
                    <label class="form-label">Minimum Edits</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.eligibility.min_edits" min="0" />
                  </div>
                  <div class="col-md-6 mb-3">
                    <label class="form-label">Minimum Outgoing Links</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.eligibility.min_outgoing_links" min="0" />
                  </div>
                </div>
              </div>

              <div class="mb-4">
                <h6 class="mb-3"><i class="fas fa-calculator me-2"></i>Evaluation Criteria (Points)</h6>
                <div class="row">
                  <div class="col-md-4 mb-3">
                    <label class="form-label">Points per Accepted</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.evaluation.points_per_accepted" min="0" step="0.01" />
                  </div>
                  <div class="col-md-4 mb-3">
                    <label class="form-label">Points per Byte</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.evaluation.points_per_byte" min="0" step="0.0001" />
                  </div>
                  <div class="col-md-4 mb-3">
                    <label class="form-label">Points per Incoming Link</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.evaluation.points_per_incoming_link" min="0" step="0.01" />
                  </div>
                  <div class="col-md-4 mb-3">
                    <label class="form-label">Points per Outgoing Link</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.evaluation.points_per_outgoing_link" min="0" step="0.01" />
                  </div>
                  <div class="col-md-4 mb-3">
                    <label class="form-label">Points per Category</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.evaluation.points_per_category" min="0" step="0.01" />
                  </div>
                  <div class="col-md-4 mb-3">
                    <label class="form-label">Points per New Reference</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.evaluation.points_per_new_reference" min="0" step="0.01" />
                  </div>
                  <div class="col-md-4 mb-3">
                    <label class="form-label">Points per Reused Reference</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.evaluation.points_per_reused_reference" min="0"
                      step="0.01" />
                  </div>
                  <div class="col-md-4 mb-3">
                    <label class="form-label">Points per Infobox</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.evaluation.points_per_infobox" min="0" step="0.01" />
                  </div>
                  <div class="col-md-4 mb-3">
                    <label class="form-label">Points per Image</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.evaluation.points_per_image" min="0" step="0.01" />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- UNLOCKED MODE: Allow Switching -->
          <div v-else class="unlocked-edit-mode">
            <div v-if="contestScoringMode !== 'automated'" class="scoring-mode-toggle mb-2">
              <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" id="editEnableMultiParam"
                  v-model="enableMultiParameterScoring" />
                <label class="form-check-label fw-bold" for="editEnableMultiParam">
                  Enable Multi-Parameter Scoring
                </label>
              </div>
              <small class="text-muted mt-1 d-block">
                <i class="fas fa-lightbulb me-1"></i>
                Multi-parameter scoring allows jury to rate submissions on multiple criteria with weighted scores.
              </small>
            </div>

            <div v-if="contestScoringMode === 'automated'" class="automated-scoring-form">
              <div class="mb-4">
                <h6 class="mb-3"><i class="fas fa-filter me-2"></i>Eligibility Criteria</h6>
                <div class="row">
                  <div class="col-md-6 mb-3">
                    <label class="form-label">Minimum Edits</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.eligibility.min_edits" min="0" />
                  </div>
                  <div class="col-md-6 mb-3">
                    <label class="form-label">Minimum Outgoing Links</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.eligibility.min_outgoing_links" min="0" />
                  </div>
                </div>
              </div>

              <div class="mb-4">
                <h6 class="mb-3"><i class="fas fa-calculator me-2"></i>Evaluation Criteria (Points)</h6>
                <div class="row">
                  <div class="col-md-4 mb-3">
                    <label class="form-label">Points per Accepted</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.evaluation.points_per_accepted" min="0" step="0.01" />
                  </div>
                  <div class="col-md-4 mb-3">
                    <label class="form-label">Points per Byte</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.evaluation.points_per_byte" min="0" step="0.0001" />
                  </div>
                  <div class="col-md-4 mb-3">
                    <label class="form-label">Points per Incoming Link</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.evaluation.points_per_incoming_link" min="0" step="0.01" />
                  </div>
                  <div class="col-md-4 mb-3">
                    <label class="form-label">Points per Outgoing Link</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.evaluation.points_per_outgoing_link" min="0" step="0.01" />
                  </div>
                  <div class="col-md-4 mb-3">
                    <label class="form-label">Points per Category</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.evaluation.points_per_category" min="0" step="0.01" />
                  </div>
                  <div class="col-md-4 mb-3">
                    <label class="form-label">Points per New Reference</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.evaluation.points_per_new_reference" min="0" step="0.01" />
                  </div>
                  <div class="col-md-4 mb-3">
                    <label class="form-label">Points per Reused Reference</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.evaluation.points_per_reused_reference" min="0"
                      step="0.01" />
                  </div>
                  <div class="col-md-4 mb-3">
                    <label class="form-label">Points per Infobox</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.evaluation.points_per_infobox" min="0" step="0.01" />
                  </div>
                  <div class="col-md-4 mb-3">
                    <label class="form-label">Points per Image</label>
                    <input type="number" class="form-control"
                      v-model.number="automatedSettings.evaluation.points_per_image" min="0" step="0.01" />
                  </div>
                </div>
              </div>
            </div>

            <div v-if="contestScoringMode !== 'automated' && !enableMultiParameterScoring"
              class="simple-scoring-form">
              <div class="row">
                <div class="col-md-6 mb-3">
                  <label class="form-label">Points for Accepted Submissions *</label>
                  <input type="number" class="form-control" v-model.number="editForm.marks_setting_accepted" min="0"
                    required />
                  <small class="text-muted">Maximum points that can be awarded</small>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label">Points for Rejected Submissions *</label>
                  <input type="number" class="form-control" v-model.number="editForm.marks_setting_rejected" min="0"
                    required />
                  <small class="text-muted">Points for rejected submissions (usually 0)</small>
                </div>
              </div>
            </div>

            <div v-else-if="contestScoringMode !== 'automated'" class="multi-param-scoring-form">
              <div class="row mb-3">
                <div class="col-md-6">
                  <label class="form-label">Maximum Score (Accepted) *</label>
                  <input type="number" class="form-control" v-model.number="maxScore" min="1" max="1000" required />
                  <small class="text-muted">Final weighted score scaled to this maximum</small>
                </div>
                <div class="col-md-6">
                  <label class="form-label">Minimum Score (Rejected) *</label>
                  <input type="number" class="form-control" v-model.number="minScore" min="0" max="1000" required />
                  <small class="text-muted">Fixed score for rejected submissions</small>
                </div>
              </div>

              <div class="mb-3">
                <label class="form-label fw-bold">Scoring Parameters *</label>
                <div class="parameters-list">
                  <div v-for="(param, index) in scoringParameters" :key="index" class="parameter-item card mb-2">
                    <div class="card-body p-3">
                      <div class="row align-items-center">
                        <div class="col-md-3">
                          <label class="small text-muted mb-1">Parameter Name</label>
                          <input type="text" class="form-control" v-model="param.name" placeholder="e.g., Quality"
                            required />
                        </div>
                        <div class="col-md-3">
                          <label class="small text-muted mb-1">Weight (%)</label>
                          <div class="input-group">
                            <input type="number" class="form-control" v-model.number="param.weight" min="0"
                              max="100" placeholder="0-100" required />
                            <span class="input-group-text">%</span>
                          </div>
                        </div>
                        <div class="col-md-5">
                          <label class="small text-muted mb-1">Description (Optional)</label>
                          <input type="text" class="form-control" v-model="param.description"
                            placeholder="Brief description" />
                        </div>
                        <div class="col-md-1 text-end">
                          <label class="small text-muted mb-1 d-block">&nbsp;</label>
                          <button type="button" class="btn btn-sm btn-outline-danger"
                            @click="removeParameter(index)" :disabled="scoringParameters.length <= 1"
                            title="Remove parameter">
                            <i class="fas fa-trash"></i>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <button type="button" class="btn btn-sm btn-outline-primary mt-2" @click="addParameter">
                  <i class="fas fa-plus me-1"></i>Add Parameter
                </button>

                <div class="mt-3 p-3 rounded" :class="weightTotalClass">
                  <div class="d-flex justify-content-between align-items-center">
                    <strong>Total Weight: {{ totalWeight }}%</strong>
                    <span v-if="totalWeight !== 100" class="text-danger">
                      <i class="fas fa-exclamation-triangle me-1"></i>
                      Must equal 100%
                    </span>
                    <span v-else class="text-success">
                      <i class="fas fa-check-circle me-1"></i>
                      Valid
                    </span>
                  </div>
                </div>
              </div>

              <button type="button" class="btn btn-sm btn-outline-secondary" @click="loadDefaultParameters">
                <i class="fas fa-redo me-1"></i>Load Default Parameters
              </button>
            </div>
          </div>
        </div>

        <!-- Article Requirements Section -->
        <div class="edit-section">
          <h6 class="section-title">
            <i class="fas fa-file-alt me-2"></i>Article Requirements
          </h6>

          <div class="mb-3">
            <label class="form-label">Minimum Byte Count *</label>
            <input type="number" v-model.number="editForm.min_byte_count" class="form-control" min="0"
              placeholder="e.g., 1000" required />
            <small class="form-text text-muted">Articles must have at least this many bytes</small>
          </div>

          <div class="mb-3">
            <label class="form-label">Minimum Reference Count</label>
            <input type="number" v-model.number="editForm.min_reference_count" class="form-control" min="0"
              placeholder="e.g., 5" />
            <small class="form-text text-muted">
              Articles must have at least this many references. Set to 0 for no requirement.
            </small>
          </div>

          <!-- Category URLs (Optional) -->
          <div class="mb-3">
            <label class="form-label">
              Category URLs
              <span class="text-muted">(MediaWiki category pages)</span>
              <span class="badge bg-secondary ms-1">Optional</span>
            </label>

            <div v-for="(category, index) in editForm.categories" :key="index" class="mb-2">
              <div class="input-group">
                <input type="url" class="form-control" v-model="editForm.categories[index]"
                  :placeholder="index === 0 ? 'https://en.wikipedia.org/wiki/Category:Example' : 'Add another category URL'" />
                <button v-if="editForm.categories.length > 1" type="button" class="btn btn-outline-danger"
                  @click="removeCategory(index)" title="Remove category">
                  <i class="fas fa-times"></i>
                </button>
              </div>
            </div>

            <button type="button" class="btn btn-outline-primary btn-sm mt-2" @click="addCategory">
              <i class="fas fa-plus me-1"></i>Add Category
            </button>

            <small class="form-text text-muted d-block mt-2">
              If provided, articles must belong to these MediaWiki categories.
            </small>
          </div>

          <!-- Template Link (Optional) -->
          <div class="mb-3">
            <label for="editTemplateLink" class="form-label">
              Contest Template Link
              <span class="badge bg-secondary ms-1">Optional</span>
            </label>
            <input type="url" class="form-control" id="editTemplateLink" v-model="editForm.template_link"
              placeholder="https://en.wikipedia.org/wiki/Template:YourContestTemplate" />
            <small class="form-text text-muted d-block mt-2">
              <i class="fas fa-info-circle me-1"></i>
              If set, this template will be automatically added to submitted articles that don't already have it.
            </small>
          </div>

          <!-- Outreach Dashboard URL (Optional) -->
          <div class="mb-3">
            <label for="editOutreachDashboardUrl" class="form-label">
              Outreach Dashboard URL
              <span class="badge bg-secondary ms-1">Optional</span>
            </label>
            <input type="url" class="form-control" id="editOutreachDashboardUrl"
              v-model="editForm.outreach_dashboard_url"
              placeholder="https://outreachdashboard.wmflabs.org/courses/WikiClub_Tech_SHUATS/Wikipedia_25_B_Day_Celebration_by_WikiClub_Tech_SHUATS" />
            <small class="form-text text-muted d-block mt-2">
              <i class="fas fa-info-circle me-1"></i>
              Link this contest to an Outreach Dashboard course. If provided, course
              statistics and information will be displayed in a dedicated tab.
              Format: https://outreachdashboard.wmflabs.org/courses/{school}/{course_slug}
            </small>
          </div>
        </div>

        <!-- Page Footer with Action Buttons -->
        <div class="page-footer">
          <button type="button" class="btn btn-secondary" @click="goBack">
            <i class="fas fa-times me-2"></i>Cancel
          </button>
          <button type="submit" class="btn btn-primary" :disabled="savingContest">
            <span v-if="savingContest" class="spinner-border spinner-border-sm me-2"></span>
            <i v-else class="fas fa-save me-2"></i>
            {{ savingContest ? 'Saving...' : 'Save Changes' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script>
import { computed, ref, watch, onMounted, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useStore } from '../store'
import api from '../services/api'
import { showAlert } from '../utils/alerts'

export default {
  name: 'EditContest',
  setup() {
    const router = useRouter()
    const route = useRoute()
    const store = useStore()

    const contest = ref(null)
    const loading = ref(true)
    const error = ref(null)
    const savingContest = ref(false)
    const jurySearchQuery = ref('')
    const jurySearchResults = ref([])
    const organizerSearchQuery = ref('')
    const organizerSearchResults = ref([])
    let jurySearchTimeout = null
    let organizerSearchTimeout = null

    const jurySearchMembers = async () => {
      const query = jurySearchQuery.value.trim()

      if (query.length < 2) {
        jurySearchResults.value = []
        return
      }
      if (jurySearchTimeout) { clearTimeout(jurySearchTimeout) }

      jurySearchTimeout = setTimeout(async () => {
        try {
          const response = await api.get(`/user/search?q=${encodeURIComponent(query)}&limit=10`)
          jurySearchResults.value = (response.users || []).filter(
            user => !editForm.selectedJuryMembers.includes(user.username)
          )
        } catch (error) {
          console.error('Jury search error:', error)
          jurySearchResults.value = []
        }
      }, 300)
    }

    const searchOrganizers = async () => {
      const query = organizerSearchQuery.value.trim()

      if (query.length < 2) {
        organizerSearchResults.value = []
        return
      }
      if (organizerSearchTimeout) {
        clearTimeout(organizerSearchTimeout)
      }
      organizerSearchTimeout = setTimeout(async () => {
        try {
          const response = await api.get(`/user/search?q=${encodeURIComponent(query)}&limit=10`)
          organizerSearchResults.value = (response.users || []).filter(
            user => !editForm.selectedOrganizers.includes(user.username) &&
              !isCurrentUser(user.username)
          )
        } catch (error) {
          console.error('Organizer search error:', error)
          organizerSearchResults.value = []
        }
      }, 300)
    }

    const addJuryMember = (username) => {
      if (isCurrentUser(username)) {
        const confirmed = window.confirm(
          '⚠️ WARNING: Self-Selection as Jury Member\n\n' +
          'You are about to select yourself as a jury member.\n\n' +
          'It is strongly recommended to select other users as jury members to maintain fairness and objectivity.\n\n' +
          'Are you sure you want to proceed with selecting yourself?'
        )

        if (!confirmed) {
          return
        }
      }

      if (!editForm.selectedJuryMembers.includes(username)) {
        editForm.selectedJuryMembers.push(username)
        jurySearchQuery.value = ''
        jurySearchResults.value = []
      }
    }

    const removeJuryMember = (username) => {
      editForm.selectedJuryMembers = editForm.selectedJuryMembers.filter(
        u => u !== username
      )
    }

    const addOrganizer = (username) => {
      if (isCurrentUser(username)) {
        showAlert('You will be added automatically as contest creator', 'info')
        return
      }

      if (!editForm.selectedOrganizers.includes(username)) {
        editForm.selectedOrganizers.push(username)
        organizerSearchQuery.value = ''
        organizerSearchResults.value = []
      }
    }

    const removeOrganizer = (username) => {
      editForm.selectedOrganizers = editForm.selectedOrganizers.filter(
        u => u !== username
      )
    }

    const addCategory = () => {
      editForm.categories.push('')
    }

    const removeCategory = (index) => {
      if (editForm.categories.length > 1) {
        editForm.categories.splice(index, 1)
      }
    }

    // Scoring system state
    const enableMultiParameterScoring = ref(false)
    const maxScore = ref(10)
    const minScore = ref(0)
    const scoringParameters = ref([
      { name: 'Quality', weight: 40, description: 'Article structure & content quality' },
      { name: 'Sources', weight: 30, description: 'References & citations' },
      { name: 'Neutrality', weight: 20, description: 'Unbiased writing' },
      { name: 'Formatting', weight: 10, description: 'Presentation & formatting' }
    ])
    const contestScoringMode = ref('simple')
    const scoringModeLocked = ref(false)
    const reviewedSubmissionsCount = ref(0)

    const automatedSettings = reactive({
      enabled: true,
      eligibility: {
        min_edits: 100,
        min_outgoing_links: 3
      },
      evaluation: {
        points_per_accepted: 10,
        points_per_byte: 0.001,
        points_per_incoming_link: 2,
        points_per_outgoing_link: 1,
        points_per_category: 1,
        points_per_new_reference: 3,
        points_per_reused_reference: 1,
        points_per_infobox: 5,
        points_per_image: 2
      }
    })

    const totalWeight = computed(() => {
      return scoringParameters.value.reduce((sum, param) => sum + (param.weight || 0), 0)
    })

    const weightTotalClass = computed(() => {
      return totalWeight.value === 100 ? 'bg-success-subtle' : 'bg-danger-subtle'
    })

    const currentUser = computed(() => {
      if (store.state && store.state.currentUser) {
        return store.state.currentUser
      }
      if (store.currentUser) {
        return store.currentUser
      }
      return null
    })

    const loadDefaultParameters = () => {
      scoringParameters.value = [
        { name: 'Quality', weight: 40, description: 'Article structure & content quality' },
        { name: 'Sources', weight: 30, description: 'References & citations' },
        { name: 'Neutrality', weight: 20, description: 'Unbiased writing' },
        { name: 'Formatting', weight: 10, description: 'Presentation & formatting' }
      ]
    }

    const loadDefaultAutomatedSettings = () => {
      automatedSettings.eligibility = {
        min_edits: 100,
        min_outgoing_links: 3
      }
      automatedSettings.evaluation = {
        points_per_accepted: 10,
        points_per_byte: 0.001,
        points_per_incoming_link: 2,
        points_per_outgoing_link: 1,
        points_per_category: 1,
        points_per_new_reference: 3,
        points_per_reused_reference: 1,
        points_per_infobox: 5,
        points_per_image: 2
      }
    }

    const addParameter = () => {
      scoringParameters.value.push({
        name: '',
        weight: 0,
        description: ''
      })
    }

    const removeParameter = (index) => {
      if (scoringParameters.value.length > 1) {
        scoringParameters.value.splice(index, 1)
      }
    }

    const isCurrentUser = (username) => {
      const currentUsername = currentUser.value?.username
      if (!currentUsername || !username) return false
      return String(currentUsername).trim().toLowerCase() ===
        String(username).trim().toLowerCase()
    }

    const editForm = reactive({
      name: '',
      project_name: '',
      description: '',
      rules: '',
      start_date: '',
      end_date: '',
      marks_setting_accepted: 0,
      marks_setting_rejected: 0,
      jury_members: '',
      allowed_submission_type: '',
      selectedJuryMembers: [],
      selectedOrganizers: [],
      min_byte_count: 0,
      min_reference_count: 0,
      categories: [''],
      template_link: '',
      outreach_dashboard_url: '',
      scoring_mode: 'simple',
      scoring_parameters: {
        max_score: 10,
        min_score: 0,
        parameters: []
      }
    })

    const loadContest = async () => {
      loading.value = true
      error.value = null

      try {
        const contestName = route.params.name
        if (!contestName) throw new Error('Contest name is required')
        const data = await api.get(`/contest/name/${contestName}`)

        contest.value = {
          ...data,
          scoring_parameters: data.scoring_parameters
            ? { ...data.scoring_parameters }
            : { enabled: false }
        }

        // Populate edit form
        editForm.name = contest.value.name
        editForm.project_name = contest.value.project_name || ''
        editForm.description = contest.value.description || ''
        editForm.rules = contest.value.rules?.text || ''
        editForm.allowed_submission_type = contest.value.allowed_submission_type || 'both'
        editForm.start_date = contest.value.start_date || ''
        editForm.end_date = contest.value.end_date || ''
        editForm.min_byte_count = Number(contest.value.min_byte_count ?? 0)
        editForm.min_reference_count = Number(contest.value.min_reference_count ?? 0)

        if (Array.isArray(contest.value.jury_members)) {
          editForm.selectedJuryMembers = [...contest.value.jury_members]
        } else {
          editForm.selectedJuryMembers = []
        }

        if (Array.isArray(contest.value.organizers)) {
          editForm.selectedOrganizers = [...contest.value.organizers]
        } else {
          editForm.selectedOrganizers = []
        }

        if (Array.isArray(contest.value.categories) && contest.value.categories.length > 0) {
          editForm.categories = [...contest.value.categories]
        } else {
          editForm.categories = ['']
        }

        editForm.template_link = contest.value.template_link || ''
        editForm.outreach_dashboard_url = contest.value.outreach_dashboard_url || ''

        // Since we don't have submissions on this page, scoring is unlocked by default
        reviewedSubmissionsCount.value = 0
        scoringModeLocked.value = false

        // This determines what the contest is CURRENTLY using
        if (contest.value.automated_settings?.enabled === true) {
          contestScoringMode.value = 'automated'
        } else if (contest.value.scoring_parameters?.enabled === true) {
          contestScoringMode.value = 'multi_parameter'
        } else {
          contestScoringMode.value = 'simple'
        }

        if (contestScoringMode.value === 'automated') {
          enableMultiParameterScoring.value = false
          if (contest.value.automated_settings) {
            automatedSettings.eligibility = {
              min_edits: Number(contest.value.automated_settings.eligibility?.min_edits ?? 100),
              min_outgoing_links: Number(contest.value.automated_settings.eligibility?.min_outgoing_links ?? 3)
            }
            automatedSettings.evaluation = {
              points_per_accepted: Number(contest.value.automated_settings.evaluation?.points_per_accepted ?? 10),
              points_per_byte: Number(contest.value.automated_settings.evaluation?.points_per_byte ?? 0.001),
              points_per_incoming_link: Number(contest.value.automated_settings.evaluation?.points_per_incoming_link ?? 2),
              points_per_outgoing_link: Number(contest.value.automated_settings.evaluation?.points_per_outgoing_link ?? 1),
              points_per_category: Number(contest.value.automated_settings.evaluation?.points_per_category ?? 1),
              points_per_new_reference: Number(contest.value.automated_settings.evaluation?.points_per_new_reference ?? 3),
              points_per_reused_reference: Number(contest.value.automated_settings.evaluation?.points_per_reused_reference ?? 1),
              points_per_infobox: Number(contest.value.automated_settings.evaluation?.points_per_infobox ?? 5),
              points_per_image: Number(contest.value.automated_settings.evaluation?.points_per_image ?? 2)
            }
          } else {
            loadDefaultAutomatedSettings()
          }
        } else if (contestScoringMode.value === 'multi_parameter') {
          enableMultiParameterScoring.value = true
          maxScore.value = Number(contest.value.scoring_parameters.max_score ?? 10)
          minScore.value = Number(contest.value.scoring_parameters.min_score ?? 0)

          if (contest.value.scoring_parameters.parameters?.length > 0) {
            scoringParameters.value = contest.value.scoring_parameters.parameters.map(p => ({
              name: p.name || '',
              weight: Number(p.weight || 0),
              description: p.description || ''
            }))
          } else {
            loadDefaultParameters()
          }
        } else {
          enableMultiParameterScoring.value = false
          editForm.marks_setting_accepted = Number(contest.value.marks_setting_accepted ?? 0)
          editForm.marks_setting_rejected = Number(contest.value.marks_setting_rejected ?? 0)
          maxScore.value = 10
          minScore.value = 0
          loadDefaultParameters()
        }
      } catch (err) {
        console.error('Error loading contest:', err)
        error.value = 'Failed to load contest: ' + (err.message || 'Unknown error')
      } finally {
        loading.value = false
      }
    }

    const saveContestEdits = async () => {
      try {
        savingContest.value = true
        const validCategories = editForm.categories.filter(cat => cat && cat.trim())

        for (const category of validCategories) {
          if (!category.startsWith('http://') && !category.startsWith('https://')) {
            showAlert('All category URLs must be valid HTTP/HTTPS URLs', 'warning')
            return
          }
        }

        let scoringParametersPayload = null
        let automatedSettingsPayload = null

        if (contestScoringMode.value === 'automated') {
          automatedSettingsPayload = {
            enabled: true,
            eligibility: {
              min_edits: Number(automatedSettings.eligibility.min_edits) || 0,
              min_outgoing_links: Number(automatedSettings.eligibility.min_outgoing_links) || 0
            },
            evaluation: {
              points_per_accepted: Number(automatedSettings.evaluation.points_per_accepted) || 0,
              points_per_byte: Number(automatedSettings.evaluation.points_per_byte) || 0,
              points_per_incoming_link: Number(automatedSettings.evaluation.points_per_incoming_link) || 0,
              points_per_outgoing_link: Number(automatedSettings.evaluation.points_per_outgoing_link) || 0,
              points_per_category: Number(automatedSettings.evaluation.points_per_category) || 0,
              points_per_new_reference: Number(automatedSettings.evaluation.points_per_new_reference) || 0,
              points_per_reused_reference: Number(automatedSettings.evaluation.points_per_reused_reference) || 0,
              points_per_infobox: Number(automatedSettings.evaluation.points_per_infobox) || 0,
              points_per_image: Number(automatedSettings.evaluation.points_per_image) || 0
            }
          }
          scoringParametersPayload = null
        } else if (enableMultiParameterScoring.value) {
          if (totalWeight.value !== 100) {
            showAlert('Parameter weights must sum to 100%', 'warning')
            return
          }

          scoringParametersPayload = {
            enabled: true,
            max_score: Number(maxScore.value),
            min_score: Number(minScore.value),
            parameters: scoringParameters.value.map(param => ({
              name: String(param.name || '').trim(),
              weight: Number(param.weight || 0),
              description: String(param.description || '').trim()
            }))
          }
        } else {
          scoringParametersPayload = {
            enabled: false,
            max_score: Number(editForm.marks_setting_accepted),
            min_score: Number(editForm.marks_setting_rejected),
            parameters: []
          }
        }

        let templateLinkValue = null
        if (editForm.template_link && typeof editForm.template_link === 'string') {
          const trimmed = editForm.template_link.trim()
          templateLinkValue = trimmed.length > 0 ? trimmed : null
        }

        let outreachUrlValue = null
        if (editForm.outreach_dashboard_url && typeof editForm.outreach_dashboard_url === 'string') {
          const trimmed = editForm.outreach_dashboard_url.trim()
          outreachUrlValue = trimmed.length > 0 ? trimmed : null
        }

        const payload = {
          name: editForm.name || '',
          project_name: editForm.project_name || '',
          description: editForm.description || '',
          rules: {
            text: editForm.rules?.trim() || ''
          },
          start_date: editForm.start_date || null,
          end_date: editForm.end_date || null,
          jury_members: editForm.selectedJuryMembers,
          organizers: editForm.selectedOrganizers,
          allowed_submission_type: editForm.allowed_submission_type,
          min_byte_count: Number(editForm.min_byte_count) || 0,
          min_reference_count: Number(editForm.min_reference_count) || 0,
          categories: validCategories.map(cat => cat.trim()),
          template_link: templateLinkValue,
          outreach_dashboard_url: outreachUrlValue,
          marks_setting_accepted: Number(editForm.marks_setting_accepted),
          marks_setting_rejected: Number(editForm.marks_setting_rejected),
          scoring_parameters: scoringParametersPayload,
          automated_settings: automatedSettingsPayload
        }
        await api.put(`/contest/${contest.value.id}`, payload)

        showAlert('Contest updated successfully', 'success')
        router.push({ name: 'ContestView', params: { name: route.params.name } })
      } catch (error) {
        console.error('[SAVE] Error:', error)
        showAlert(
          'Failed to save: ' + (error.response?.data?.detail || error.message),
          'danger'
        )
      } finally {
        savingContest.value = false
      }
    }

    // Navigation helper
    const goBack = () => {
      router.push({ name: 'ContestView', params: { name: route.params.name } })
    }

    onMounted(() => {
      loadContest()
    })

    return {
      contest,
      loading,
      error,
      savingContest,
      jurySearchQuery,
      jurySearchResults,
      organizerSearchQuery,
      organizerSearchResults,
      searchJuryMembers: jurySearchMembers,
      searchOrganizers,
      addJuryMember,
      removeJuryMember,
      addOrganizer,
      removeOrganizer,
      addCategory,
      removeCategory,
      isCurrentUser,
      editForm,
      enableMultiParameterScoring,
      maxScore,
      minScore,
      scoringParameters,
      totalWeight,
      weightTotalClass,
      loadDefaultParameters,
      addParameter,
      removeParameter,
      automatedSettings,
      loadDefaultAutomatedSettings,
      contestScoringMode,
      scoringModeLocked,
      reviewedSubmissionsCount,
      saveContestEdits,
      goBack
    }
  }
}
</script>

<style scoped>
.edit-contest-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.page-header {
  background-color: var(--wiki-primary);
  color: white;
  border-bottom: none;
  padding: 1.25rem 1.5rem;
  transition: background-color 0.2s ease;
}

.page-title {
  font-weight: 600;
  font-size: 1.5rem;
}

.page-body {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.page-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid var(--wiki-border);
}

.edit-section {
  padding: 1rem;
  margin-bottom: 2rem;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

[data-theme="dark"] .edit-section {
  background: #2a2a2a;
  border-color: #404040;
}

.section-title {
  color: var(--wiki-primary);
  font-weight: 700;
  font-size: 1.1rem;
  margin-bottom: 1.25rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid var(--wiki-primary);
  display: flex;
  align-items: center;
}

[data-theme="dark"] .section-title {
  color: var(--wiki-primary);
}

.scoring-section-edit {
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
  border: 2px solid var(--wiki-primary);
}

[data-theme="dark"] .scoring-section-edit {
  background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
  border-color: var(--wiki-primary);
}

.scoring-lock-status {
  margin-bottom: 1.5rem;
}

.lock-banner {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  padding: 0.5rem 0.5rem;
  border-radius: 8px;
  border: 2px solid;
  transition: all 0.3s ease;
}

.lock-banner.locked {
  background: linear-gradient(135deg, #fff3cd 0%, #fffbf0 100%);
  border-color: #ffc107;
  box-shadow: 0 2px 8px rgba(255, 193, 7, 0.2);
}

[data-theme="dark"] .lock-banner.locked {
  background: linear-gradient(135deg, rgba(255, 193, 7, 0.15) 0%, rgba(255, 193, 7, 0.05) 100%);
  border-color: #ff9800;
}

.lock-banner.unlocked {
  background: linear-gradient(135deg, #d4edda 0%, #f0fdf4 100%);
  border-color: #28a745;
  box-shadow: 0 2px 8px rgba(40, 167, 69, 0.2);
}

[data-theme="dark"] .lock-banner.unlocked {
  background: linear-gradient(135deg, rgba(40, 167, 69, 0.15) 0%, rgba(40, 167, 69, 0.05) 100%);
  border-color: #4ade80;
}

.lock-banner-icon {
  flex-shrink: 0;
  width: 35px;
  height: 35px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 1.25rem;
}

.lock-banner.locked .lock-banner-icon {
  background: #ffc107;
  color: #000;
}

[data-theme="dark"] .lock-banner.locked .lock-banner-icon {
  background: #ff9800;
  color: #fff;
}

.lock-banner.unlocked .lock-banner-icon {
  background: #28a745;
  color: #fff;
}

[data-theme="dark"] .lock-banner.unlocked .lock-banner-icon {
  background: #4ade80;
  color: #000;
}

.lock-banner-content {
  flex: 1;
}

.lock-banner-title {
  font-size: 1rem;
  margin-bottom: 0.25rem;
  color: #1f2937;
}

[data-theme="dark"] .lock-banner-title {
  color: #f3f4f6;
}

.lock-banner-text {
  font-size: 0.9rem;
  color: #4b5563;
  line-height: 1.5;
}

[data-theme="dark"] .lock-banner-text {
  color: #d1d5db;
}

.badge-mode {
  display: inline-flex;
  align-items: center;
  padding: 0.3rem 0.3rem;
  border-radius: 6px;
  font-size: 0.95rem;
  font-weight: 600;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.badge-mode.multi {
  background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
  color: white;
}

.badge-mode.simple {
  background: linear-gradient(135deg, var(--wiki-primary) 0%, #17a2b8 100%);
  color: white;
}

.locked-edit-info .alert ul {
  margin-top: 0.5rem;
  margin-bottom: 0;
  padding-left: 1.5rem;
}

.locked-edit-info .alert li {
  margin-bottom: 0.25rem;
  color: #1e40af;
}

[data-theme="dark"] .locked-edit-info .alert li {
  color: #93c5fd;
}

.scoring-mode-toggle {
  padding: 0.5rem;
  background: #f0f9ff;
  border: 2px dashed var(--wiki-primary);
  border-radius: 8px;
  transition: all 0.3s ease;
}

[data-theme="dark"] .scoring-mode-toggle {
  background: rgba(0, 102, 153, 0.1);
  border-color: var(--wiki-primary);
}

.scoring-mode-toggle:hover {
  background: #e0f2fe;
  box-shadow: 0 2px 6px rgba(0, 102, 153, 0.15);
}

[data-theme="dark"] .scoring-mode-toggle:hover {
  background: rgba(0, 102, 153, 0.15);
}

.form-check {
  display: flex;
  align-items: end;
}

.form-check-input {
  cursor: pointer;
  width: 3rem;
  height: 1.5rem;
}

.form-check-input:checked {
  background-color: var(--wiki-primary);
  border-color: var(--wiki-primary);
}

.organizer-selection-box,
.jury-selection-box {
  min-height: 50px;
  max-height: 150px;
  overflow-y: auto;
}

.organizer-placeholder-text,
.jury-placeholder-text {
  color: #6c757d;
  font-style: italic;
  display: block;
  padding: 0.5rem;
}

.btn-primary {
  background-color: var(--wiki-primary);
  border-color: var(--wiki-primary);
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn-primary:hover {
  background-color: var(--wiki-primary-hover);
  border-color: var(--wiki-primary-hover);
  box-shadow: 0 2px 4px rgba(0, 102, 153, 0.2);
}

.btn-secondary {
  background-color: var(--wiki-text-muted);
  border-color: var(--wiki-text-muted);
  transition: all 0.2s ease;
}

[data-theme="dark"] .btn-secondary {
  background-color: #5a6268;
  border-color: #5a6268;
}

.organizer-autocomplete,
.jury-autocomplete {
  border: 1px solid var(--wiki-border);
  border-top: none;
  border-radius: 0 0 4px 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  background-color: var(--wiki-card-bg);
  transition: background-color 0.2s ease, border-color 0.2s ease;
}

[data-theme="dark"] .organizer-autocomplete,
[data-theme="dark"] .jury-autocomplete {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.organizer-autocomplete .p-2,
.jury-autocomplete .p-2 {
  transition: background-color 0.2s ease;
  color: var(--wiki-text);
}

.organizer-autocomplete .p-2:hover,
.jury-autocomplete .p-2:hover {
  background-color: var(--wiki-hover-bg) !important;
}

.jury-autocomplete .bg-warning-subtle {
  background-color: rgba(255, 193, 7, 0.25) !important;
  border-left: 5px solid #ffc107;
  animation: pulse-warning 2s ease-in-out infinite;
}

@keyframes pulse-warning {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(255, 193, 7, 0.4);
  }

  50% {
    box-shadow: 0 0 0 4px rgba(255, 193, 7, 0);
  }
}

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

[data-theme="dark"] .self-warning-badge {
  background-color: #ff9800;
  color: #fff;
  box-shadow: 0 2px 4px rgba(255, 152, 0, 0.5);
  border: 1px solid rgba(255, 152, 0, 0.7);
}

.spinner-border-sm {
  width: 1rem;
  height: 1rem;
  border-width: 0.15em;
  border-color: currentColor;
  border-right-color: transparent;
}

/* Text muted color */
.text-muted {
  color: var(--wiki-text-muted) !important;
  transition: color 0.3s ease;
}
</style>