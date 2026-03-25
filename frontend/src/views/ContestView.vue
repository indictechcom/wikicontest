<template>
  <div class="container py-5">
    <!-- Navigation and Action Buttons -->
    <div class="mb-4 d-flex justify-content-between align-items-center">
      <button class="btn btn-outline-secondary" @click="goBack">
        <i class="fas fa-arrow-left me-2"></i>Back to Contests
      </button>
      <div class="d-flex gap-2">
        <button v-if="contest && contestScoringMode !== 'automated'"
class="btn btn-primary text-white"
@click="goToLeaderboard"
          title="View Contest Leaderboard">
          <i class="fas fa-trophy me-2"></i>Leaderboard
        </button>
        <!-- Only contest creators and admins can delete -->
        <button v-if="canDeleteContest"
class="btn btn-danger"
@click="handleDeleteContest"
:disabled="deletingContest">
          <span v-if="deletingContest" class="spinner-border spinner-border-sm me-2"></span>
          <i v-else class="fas fa-trash me-2"></i>
          {{ deletingContest ? 'Deleting...' : 'Delete Contest' }}
        </button>

        <button v-if="canDeleteContest" class="btn btn-primary" @click="openEditModal">
          <i class="fas fa-edit me-2"></i>Edit Contest
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
      <button class="btn btn-sm btn-outline-danger ms-3" @click="goBack">Go Back</button>
    </div>

    <!-- Contest Details -->
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

      <!-- Main Content with Tabs -->
      <ul class="nav nav-tabs mb-4" role="tablist" v-if="contest.outreach_dashboard_url">
        <li class="nav-item" role="presentation">
          <button class="nav-link active"
id="overview-tab"
data-bs-toggle="tab"
data-bs-target="#overview"
type="button"
role="tab"
aria-controls="overview"
aria-selected="true">
            <i class="fas fa-info-circle me-2"></i>Overview
          </button>
        </li>
        <li class="nav-item" role="presentation">
          <button class="nav-link"
id="outreach-tab"
data-bs-toggle="tab"
data-bs-target="#outreach"
type="button"
role="tab"
aria-controls="outreach"
aria-selected="false">
            <i class="fas fa-graduation-cap me-2"></i>Outreach Dashboard
          </button>
        </li>
      </ul>

      <div class="tab-content" :class="{ 'mt-0': !contest.outreach_dashboard_url }">
        <!-- Overview Tab -->
        <div v-if="contest.outreach_dashboard_url"
class="tab-pane fade show active"
id="overview"
role="tabpanel"
aria-labelledby="overview-tab">
          <div class="row">
            <div :class="canViewSubmissions ? 'col-md-12' : 'col-md-12'">
          <!-- Basic Contest Information -->
          <div class="card mb-4">
            <div class="card-header">
              <h5 class="mb-0"><i class="fas fa-info-circle me-2"></i>Contest Details</h5>
            </div>
            <div class="card-body">
              <p><strong>Project:</strong> {{ contest.project_name }}</p>
              <p><strong>Status:</strong> <span class="badge bg-primary">{{ contest.status }}</span></p>
              <p v-if="contest.start_date"><strong>Start Date:</strong> {{ formatDate(contest.start_date) }}</p>
              <p v-if="contest.end_date"><strong>End Date:</strong> {{ formatDate(contest.end_date) }}</p>

              <strong>Organizers:</strong>
              <div v-if="contest.organizers && contest.organizers.length > 0" class="organizers-flex">
                <div v-for="organizer in contest.organizers" :key="organizer" class="organizer-chip">
                  <i class="fas fa-user-tie me-2"></i>
                  <strong>{{ organizer }}</strong>
                </div>
              </div>
            </div>
          </div>
          </div>

          <!-- Scoring System Display -->
      <div class="col-md-12">
        <div class="scoring-card">
          <div class="card-header">
            <h5 class="mb-0"><i class="fas fa-chart-line"></i> Scoring System</h5>
          </div>

          <div class="scoring-content">
            <!-- Multi-Parameter Scoring Display -->
            <div v-if="contest.scoring_parameters?.enabled === true">
              <div class="scoring-meta">
                <span class="max-points">Accepted points: {{ contest.scoring_parameters.max_score }}</span>
                <span class="max-points">Rejected points: {{ contest.scoring_parameters.min_score }}</span>
              </div>

              <div class="params-list">
                <div v-for="param in contest.scoring_parameters.parameters" :key="param.name" class="param-item">
                  <div class="param-row">
                    <span class="param-label">{{ param.name }}</span>
                    <span class="param-value">{{ param.weight }}%</span>
                  </div>
                  <p v-if="param.description" class="param-note">{{ param.description }}</p>
                </div>
              </div>

              <div class="info-note">
                <i class="fas fa-info-circle"></i>
                <span>Each parameter scored 0-10, weighted average calculated</span>
              </div>
            </div>

            <!-- Simple Accept/Reject Scoring Display -->
            <div v-else>
              <div class="points-row">
                <div class="point-item">
                  <span class="point-label">Accepted</span>
                  <span class="point-value">{{ contest.marks_setting_accepted }}</span>
                </div>

                <div class="point-item">
                  <span class="point-label">Rejected</span>
                  <span class="point-value">{{ contest.marks_setting_rejected }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Contest Description -->
      <div v-if="contest.description" class="card mb-4 description-section">
        <div class="card-header">
          <h5 class="mb-0"><i class="fas fa-align-left me-2"></i>Description</h5>
        </div>
        <div class="card-body">
          <p class="description-text">{{ contest.description }}</p>
        </div>
      </div>

      <!-- Contest Rules -->
      <div v-if="contest.rules && contest.rules.text" class="card mb-4">
        <div class="card-header">
          <h5 class="mb-0"><i class="fas fa-book me-2"></i>Contest Rules</h5>
        </div>
        <div class="card-body">
          <pre class="rules-text" style="white-space: pre-wrap; font-size: 1rem;">{{ contest.rules.text }}</pre>
        </div>
      </div>

      <!-- Submission Type Information -->
      <div class="card mb-4">
        <div class="card-header">
          <h5 class="mb-0"><i class="fas fa-file-alt me-2"></i>Submission Type Allowed</h5>
        </div>
        <div class="card-body">
          <p>
            <strong>
              {{
                contest.allowed_submission_type === 'new'
                  ? 'New Articles Only'
                  : contest.allowed_submission_type === 'expansion'
                    ? 'Improved Articles Only'
                    : 'Both (New Articles + Improved Articles)'
              }}
            </strong>
          </p>

          <p class="mt-2 small text-muted">
            <em>
              • <strong>New Articles</strong> = Completely new Wikipedia article created during the contest.<br />
              • <strong>Improved Articles</strong> = An existing article improved or expanded with substantial content.
            </em>
          </p>
        </div>
      </div>

      <!-- Required MediaWiki Categories -->
      <div v-if="contest.categories && contest.categories.length > 0" class="card mb-4">
        <div class="card-header">
          <h5 class="mb-0"><i class="fas fa-tags me-2"></i>Required Categories</h5>
        </div>
        <div class="card-body">
          <p class="mb-2">
            <strong>Articles must belong to the following MediaWiki categories:</strong>
          </p>
          <ul class="list-unstyled">
            <li v-for="(category, index) in contest.categories" :key="index" class="mb-2">
              <a :href="category"
target="_blank"
rel="noopener noreferrer"
class="text-decoration-none">
                <i class="fas fa-external-link-alt me-2"></i>{{ getCategoryName(category) }}
              </a>
            </li>
          </ul>
          <small class="text-muted">
            <i class="fas fa-info-circle me-1"></i>
            Submitted articles must be categorized under at least one of these categories.
          </small>
        </div>
      </div>

      <!-- Minimum Reference Requirement -->
      <div v-if="contest.min_reference_count > 0" class="card mb-4">
        <div class="card-header">
          <h5 class="mb-0"><i class="fas fa-link me-2"></i>Minimum Reference Count</h5>
        </div>
        <div class="card-body">
          <p>
            <strong>{{ contest.min_reference_count }} References required</strong>
          </p>
          <small class="text-muted">
            <i class="fas fa-info-circle me-1"></i>
            Submitted articles must have at least {{ contest.min_reference_count }} external references.
          </small>
        </div>
      </div>

      <!-- Jury Members List -->
      <div v-if="contest.jury_members && contest.jury_members.length > 0" class="card mb-4">
        <div class="card-header">
          <h5 class="mb-0"><i class="fas fa-users me-2"></i>Jury Members</h5>
        </div>
        <div class="card-body">
          <div class="organizers-flex">
            <div v-for="jury in contest.jury_members" :key="jury" class="organizer-chip">
              <i class="fas fa-gavel me-2"></i>
              <strong>{{ jury }}</strong>
            </div>
          </div>
        </div>
      </div>

      <!-- Category Crawler Section (for Automated Scoring Contests) -->
      <div v-if="contest.automated_settings?.enabled === true && contest.categories && contest.categories.length > 0 && canImportArticles" class="card mb-4">
        <div class="card-header">
          <h5 class="mb-0"><i class="fas fa-download me-2"></i>Import Articles from Category</h5>
        </div>
        <div class="card-body">
          <p class="text-muted mb-3">Import articles from the contest's configured categories as pending submissions.</p>
          
          <div class="crawler-form">
            <select v-model="selectedCategory" class="form-select crawler-select">
              <option value="">Select a category...</option>
              <option v-for="cat in contest.categories" :key="cat" :value="cat">{{ cat }}</option>
            </select>
            <input
              type="number"
              v-model.number="crawlLimit"
              placeholder="Limit"
              min="1"
              max="5000"
              class="form-control crawler-limit"
            />
            <button
              class="btn btn-primary crawler-btn"
              @click="crawlCategory"
              :disabled="crawling || !selectedCategory"
            >
              <span v-if="crawling">
                <i class="fas fa-spinner fa-spin me-1"></i> Importing...
              </span>
              <span v-else>
                <i class="fas fa-cloud-download-alt me-1"></i> Import Articles
              </span>
            </button>
          </div>
          
          <div v-if="crawlResult" class="crawl-result mt-3">
            <div class="alert alert-success" v-if="crawlResult.total_imported > 0">
              <i class="fas fa-check-circle me-2"></i>
              {{ crawlResult.message }}
              <br />
              <small>Category: {{ crawlResult.category }}</small>
              <br />
              <small>Skipped (duplicates): {{ crawlResult.skipped }}</small>
            </div>
            <div class="alert alert-warning" v-else-if="crawlResult.skipped > 0">
              <i class="fas fa-exclamation-triangle me-2"></i>
              All {{ crawlResult.skipped }} articles were duplicates
            </div>
            <div class="alert alert-info" v-else>
              <i class="fas fa-info-circle me-2"></i>
              No articles found in category
            </div>
          </div>
          <div v-if="crawlError" class="alert alert-danger mt-3">
            <i class="fas fa-exclamation-circle me-2"></i>
            {{ crawlError }}
          </div>
        </div>
      </div>

      <!-- Submissions Table (Visible to Jury and Organizers) -->
      <div v-if="canViewSubmissions" class="card mb-4">
        <div class="card-header">
          <div class="d-flex justify-content-between align-items-center">
            <h5 class="mb-0"><i class="fas fa-file-alt me-2"></i>Submissions</h5>
            <button v-if="loadingSubmissions || refreshingMetadata" class="btn btn-sm btn-outline-secondary" disabled>
              <span class="spinner-border spinner-border-sm me-2"></span>
              {{ loadingSubmissions ? 'Loading...' : 'Refreshing...' }}
            </button>
            <!-- Refresh metadata fetches latest article data from MediaWiki -->
            <button v-else
class="btn btn-sm btn-outline-light"
@click="refreshMetadata"
              :disabled="submissions.length === 0"
title="Refresh article metadata"
              style="color: white; border-color: white;">
              <i class="fas fa-database me-1"></i>Refresh Metadata
            </button>
          </div>
        </div>
        <div class="card-body">
          <!-- Filter Tabs (automated scoring only) -->
          <div v-if="contestScoringMode === 'automated' && submissions.length > 0" class="mb-3">
            <div class="btn-group" role="group" aria-label="Filter submissions">
              <button type="button" class="btn btn-sm" :class="submissionFilter === 'all' ? 'btn-primary' : 'btn-outline-primary'" @click="submissionFilter = 'all'">
                All <span class="badge bg-light text-dark ms-1">{{ submissions.length }}</span>
              </button>
              <button type="button" class="btn btn-sm" :class="submissionFilter === 'accepted' ? 'btn-success' : 'btn-outline-success'" @click="submissionFilter = 'accepted'">
                Accepted <span class="badge bg-light text-dark ms-1">{{ submissions.filter(s => s.status === 'accepted').length }}</span>
              </button>
              <button type="button" class="btn btn-sm" :class="submissionFilter === 'rejected' ? 'btn-danger' : 'btn-outline-danger'" @click="submissionFilter = 'rejected'">
                Rejected <span class="badge bg-light text-dark ms-1">{{ submissions.filter(s => s.status === 'rejected').length }}</span>
              </button>
              <button type="button" class="btn btn-sm" :class="submissionFilter === 'pending' ? 'btn-warning' : 'btn-outline-warning'" @click="submissionFilter = 'pending'">
                Pending <span class="badge bg-light text-dark ms-1">{{ submissions.filter(s => s.status === 'pending').length }}</span>
              </button>
            </div>
          </div>

          <div v-if="submissions.length === 0 && !loadingSubmissions" class="alert alert-info">
            <i class="fas fa-info-circle me-2"></i>No submissions yet for this contest.
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
                    <div v-if="submission.article_expansion_bytes !== null &&
                      submission.article_expansion_bytes !== undefined"
class="text-muted small mt-1">
                      <i class="me-1"
:class="submission.article_expansion_bytes > 0
                        ? 'fas fa-arrow-up'
                        : submission.article_expansion_bytes < 0
                          ? 'fas fa-arrow-down'
                          : 'fas fa-arrows-left-right'
                        "></i>
                      Expansion bytes:
                      <span :class="submission.article_expansion_bytes > 0
                        ? 'text-success'
                        : submission.article_expansion_bytes < 0
                          ? 'text-danger'
                          : 'text-muted'">
                        {{ submission.article_expansion_bytes > 0
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
                    <div v-if="submission.latest_revision_author"
class="mt-2 pt-2"
                      style="border-top: 1px solid #dee2e6;">
                      <div>
                        <i class="fas fa-user me-1"></i>{{ submission.latest_revision_author }}
                        <span class="badge bg-info ms-1" style="font-size: 0.7em;">Latest</span>
                      </div>
                      <div v-if="submission.latest_revision_timestamp" class="text-muted small mt-1">
                        <i class="fas fa-calendar me-1"></i>
                        {{ formatDateShort(submission.latest_revision_timestamp) }}
                      </div>
                    </div>
                  </td>
                  <td>{{ submission.username || 'Unknown' }}</td>
                  <td>
                    <span 
                      :class="`badge bg-${getStatusColor(submission.status)}`"
                      :style="(submission.evaluation_reason && contestScoringMode === 'automated') ? 'cursor: pointer;' : ''"
                      @click="showEvaluationDetails(submission)"
                      :title="(submission.evaluation_reason && contestScoringMode === 'automated') ? 'Click to see details' : ''">
                      {{ submission.status }}
                    </span>
                    <div v-if="submission.already_reviewed" class="text-muted small mt-1">
                      <i class="fas fa-check-circle me-1"></i>Reviewed
                    </div>
                  </td>
                  <td>
                    <span 
                      :style="(submission.evaluation_reason && contestScoringMode === 'automated') ? 'cursor: pointer; text-decoration: underline;' : ''"
                      @click="showEvaluationDetails(submission)"
                      :title="(submission.evaluation_reason && contestScoringMode === 'automated') ? 'Click to see score breakdown' : ''">
                      {{ submission.score || 0 }}
                    </span>
                  </td>
                  <td>{{ formatDate(submission.submitted_at) }}</td>
                  <td>
                    <button v-if="canViewSubmissions"
@click="handleDeleteSubmission(submission)"
                      class="btn btn-sm btn-outline-danger"
title="Delete Submission"
                      :disabled="deletingSubmissionId === submission.id">
                      <span v-if="deletingSubmissionId === submission.id"
                        class="spinner-border spinner-border-sm"></span>
                      <i v-else class="fas fa-trash"></i>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Bottom Action Row -->
      <div class="d-flex justify-content-between align-items-center gap-2 mb-4">
        <!-- Debug warning for auth issues -->
        <div v-if="contest && !currentUser && !checkingAuth" class="alert alert-warning py-1 px-2 mb-0 me-auto">
          <i class="fas fa-exclamation-triangle me-1"></i>
          <strong>User not loaded!</strong>
          <button class="btn btn-sm btn-outline-warning ms-2" @click="forceAuthRefresh">
            <i class="fas fa-sync-alt me-1"></i>Refresh Auth
          </button>
        </div>

        <!-- Submit article button for active contests -->
        <button v-if="contest?.status === 'current' && isAuthenticated && !canViewSubmissions"
          class="btn btn-primary ms-auto"
@click="handleSubmitArticle">
          <i class="fas fa-paper-plane me-2"></i>Submit Article
        </button>
      </div>
        </div>
        </div>

        <!-- Outreach Dashboard Tab -->
        <div v-if="contest.outreach_dashboard_url"
class="tab-pane fade"
id="outreach"
role="tabpanel"
aria-labelledby="outreach-tab">
          <OutreachDashboardTab :base-url="contest.outreach_dashboard_url" :contest-id="contest.id" />
        </div>
      </div>

      <!-- Content when no Outreach Dashboard URL (no tabs) -->
      <div v-if="!contest.outreach_dashboard_url" class="row">
        <div :class="canViewSubmissions ? 'col-md-12' : 'col-md-12'">
          <!-- Basic Contest Information -->
          <div class="card mb-4">
            <div class="card-header">
              <h5 class="mb-0"><i class="fas fa-info-circle me-2"></i>Contest Details</h5>
            </div>
            <div class="card-body">
              <p><strong>Project:</strong> {{ contest.project_name }}</p>
              <p><strong>Status:</strong> <span class="badge bg-primary">{{ contest.status }}</span></p>
              <p v-if="contest.start_date"><strong>Start Date:</strong> {{ formatDate(contest.start_date) }}</p>
              <p v-if="contest.end_date"><strong>End Date:</strong> {{ formatDate(contest.end_date) }}</p>

              <strong>Organizers:</strong>
              <div v-if="contest.organizers && contest.organizers.length > 0" class="organizers-flex">
                <div v-for="organizer in contest.organizers" :key="organizer" class="organizer-chip">
                  <i class="fas fa-user-tie me-2"></i>
                  <strong>{{ organizer }}</strong>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Scoring System Display -->
        <div class="col-md-12">
          <div class="scoring-card">
            <div class="card-header">
              <h5 class="mb-0"><i class="fas fa-chart-line"></i> Scoring System</h5>
            </div>

            <div class="scoring-content">
              <!-- Automated Scoring Display -->
              <div v-if="contest.automated_settings?.enabled === true">
                <div class="automated-header">
                  <i class="fas fa-robot me-2"></i>
                  <strong>Automated Scoring</strong>
                  <span class="badge bg-info ms-2">Auto-evaluated</span>
                </div>

                <!-- Eligibility Criteria -->
                <div class="automated-section">
                  <h6 class="section-title"><i class="fas fa-filter me-2"></i>Eligibility Criteria</h6>
                  <div class="criteria-grid">
                    <div class="criteria-item">
                      <span class="criteria-label">Min Edits</span>
                      <span class="criteria-value">{{ contest.automated_settings.eligibility?.min_edits ?? 0 }}</span>
                    </div>
                    <div class="criteria-item">
                      <span class="criteria-label">Min Outgoing Links</span>
                      <span class="criteria-value">{{ contest.automated_settings.eligibility?.min_outgoing_links ?? 0 }}</span>
                    </div>
                  </div>
                </div>

                <!-- Evaluation Points -->
                <div class="automated-section">
                  <h6 class="section-title"><i class="fas fa-calculator me-2"></i>Evaluation Points</h6>
                  <div class="points-grid">
                    <div class="point-chip">
                      <span class="chip-label">Accepted</span>
                      <span class="chip-value">{{ contest.automated_settings.evaluation?.points_per_accepted ?? 0 }}</span>
                    </div>
                    <div class="point-chip">
                      <span class="chip-label">Per Byte</span>
                      <span class="chip-value">{{ contest.automated_settings.evaluation?.points_per_byte ?? 0 }}</span>
                    </div>
                    <div class="point-chip">
                      <span class="chip-label">Incoming Link</span>
                      <span class="chip-value">{{ contest.automated_settings.evaluation?.points_per_incoming_link ?? 0 }}</span>
                    </div>
                    <div class="point-chip">
                      <span class="chip-label">Outgoing Link</span>
                      <span class="chip-value">{{ contest.automated_settings.evaluation?.points_per_outgoing_link ?? 0 }}</span>
                    </div>
                    <div class="point-chip">
                      <span class="chip-label">Category</span>
                      <span class="chip-value">{{ contest.automated_settings.evaluation?.points_per_category ?? 0 }}</span>
                    </div>
                    <div class="point-chip">
                      <span class="chip-label">New Ref</span>
                      <span class="chip-value">{{ contest.automated_settings.evaluation?.points_per_new_reference ?? 0 }}</span>
                    </div>
                    <div class="point-chip">
                      <span class="chip-label">Reused Ref</span>
                      <span class="chip-value">{{ contest.automated_settings.evaluation?.points_per_reused_reference ?? 0 }}</span>
                    </div>
                    <div class="point-chip">
                      <span class="chip-label">Infobox</span>
                      <span class="chip-value">{{ contest.automated_settings.evaluation?.points_per_infobox ?? 0 }}</span>
                    </div>
                    <div class="point-chip">
                      <span class="chip-label">Image</span>
                      <span class="chip-value">{{ contest.automated_settings.evaluation?.points_per_image ?? 0 }}</span>
                    </div>
                  </div>
                </div>

                <div class="info-note">
                  <i class="fas fa-info-circle"></i>
                  <span>Articles are automatically scored based on metrics and eligibility criteria</span>
                </div>
              </div>

              <!-- Multi-Parameter Scoring Display -->
              <div v-else-if="contest.scoring_parameters?.enabled === true">
                <div class="scoring-meta">
                  <span class="max-points">Accepted points: {{ contest.scoring_parameters.max_score }}</span>
                  <span class="max-points">Rejected points: {{ contest.scoring_parameters.min_score }}</span>
                </div>

                <div class="params-list">
                  <div v-for="param in contest.scoring_parameters.parameters" :key="param.name" class="param-item">
                    <div class="param-row">
                      <span class="param-label">{{ param.name }}</span>
                      <span class="param-value">{{ param.weight }}%</span>
                    </div>
                    <p v-if="param.description" class="param-note">{{ param.description }}</p>
                  </div>
                </div>

                <div class="info-note">
                  <i class="fas fa-info-circle"></i>
                  <span>Each parameter scored 0-10, weighted average calculated</span>
                </div>
              </div>

              <!-- Simple Accept/Reject Scoring Display -->
              <div v-else>
                <div class="points-row">
                  <div class="point-item">
                    <span class="point-label">Accepted</span>
                    <span class="point-value">{{ contest.marks_setting_accepted }}</span>
                  </div>

                  <div class="point-item">
                    <span class="point-label">Rejected</span>
                    <span class="point-value">{{ contest.marks_setting_rejected }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Contest Description -->
        <div v-if="contest.description" class="card mb-4 description-section">
          <div class="card-header">
            <h5 class="mb-0"><i class="fas fa-align-left me-2"></i>Description</h5>
          </div>
          <div class="card-body">
            <p class="description-text">{{ contest.description }}</p>
          </div>
        </div>

        <!-- Contest Rules -->
        <div v-if="contest.rules && contest.rules.text" class="card mb-4">
          <div class="card-header">
            <h5 class="mb-0"><i class="fas fa-book me-2"></i>Contest Rules</h5>
          </div>
          <div class="card-body">
            <pre class="rules-text" style="white-space: pre-wrap; font-size: 1rem;">{{ contest.rules.text }}</pre>
          </div>
        </div>

        <!-- Submission Type Information -->
        <div class="card mb-4">
          <div class="card-header">
            <h5 class="mb-0"><i class="fas fa-file-alt me-2"></i>Submission Type Allowed</h5>
          </div>
          <div class="card-body">
            <p>
              <strong>
                {{
                  contest.allowed_submission_type === 'new'
                    ? 'New Articles Only'
                    : contest.allowed_submission_type === 'expansion'
                      ? 'Improved Articles Only'
                      : 'Both (New Articles + Improved Articles)'
                }}
              </strong>
            </p>

            <p class="mt-2 small text-muted">
              <em>
                • <strong>New Articles</strong> = Completely new Wikipedia article created during the contest.<br />
                • <strong>Improved Articles</strong> = An existing article improved or expanded
                  with substantial content.
              </em>
            </p>
          </div>
        </div>

        <!-- Required MediaWiki Categories -->
        <div v-if="contest.categories && contest.categories.length > 0" class="card mb-4">
          <div class="card-header">
            <h5 class="mb-0"><i class="fas fa-tags me-2"></i>Required Categories</h5>
          </div>
          <div class="card-body">
            <p class="mb-2">
              <strong>Articles must belong to the following MediaWiki categories:</strong>
            </p>
            <ul class="list-unstyled">
              <li v-for="(category, index) in contest.categories" :key="index" class="mb-2">
                <a :href="category"
target="_blank"
rel="noopener noreferrer"
class="text-decoration-none">
                  <i class="fas fa-external-link-alt me-2"></i>{{ getCategoryName(category) }}
                </a>
              </li>
            </ul>
            <small class="text-muted">
              <i class="fas fa-info-circle me-1"></i>
              Submitted articles must be categorized under at least one of these categories.
            </small>
          </div>
        </div>

        <!-- Minimum Reference Requirement -->
        <div v-if="contest.min_reference_count > 0" class="card mb-4">
          <div class="card-header">
            <h5 class="mb-0"><i class="fas fa-link me-2"></i>Minimum Reference Count</h5>
          </div>
          <div class="card-body">
            <p>
              <strong>{{ contest.min_reference_count }} References required</strong>
            </p>
            <small class="text-muted">
              <i class="fas fa-info-circle me-1"></i>
              Submitted articles must have at least {{ contest.min_reference_count }} external references.
            </small>
          </div>
        </div>

        <!-- Jury Members List -->
        <div v-if="contest.jury_members && contest.jury_members.length > 0" class="card mb-4">
          <div class="card-header">
            <h5 class="mb-0"><i class="fas fa-users me-2"></i>Jury Members</h5>
          </div>
          <div class="card-body">
            <div class="organizers-flex">
              <div v-for="jury in contest.jury_members" :key="jury" class="organizer-chip">
                <i class="fas fa-gavel me-2"></i>
                <strong>{{ jury }}</strong>
              </div>
            </div>
          </div>
        </div>

        <!-- Category Crawler Section (for Automated Scoring Contests) -->
        <div v-if="contest.automated_settings?.enabled === true && contest.categories && contest.categories.length > 0 && canImportArticles" class="card mb-4">
          <div class="card-header">
            <h5 class="mb-0"><i class="fas fa-download me-2"></i>Import Articles from Category</h5>
          </div>
          <div class="card-body">
            <p class="text-muted mb-3">Import articles from the contest's configured categories as pending submissions.</p>
            
            <div class="crawler-form">
              <select v-model="selectedCategory" class="form-select crawler-select">
                <option value="">Select a category...</option>
                <option v-for="cat in contest.categories" :key="cat" :value="cat">{{ cat }}</option>
              </select>
              <input
                type="number"
                v-model.number="crawlLimit"
                placeholder="Limit"
                min="1"
                max="5000"
                class="form-control crawler-limit"
              />
              <button
                class="btn btn-primary crawler-btn"
                @click="crawlCategory"
                :disabled="crawling || !selectedCategory"
              >
                <span v-if="crawling">
                  <i class="fas fa-spinner fa-spin me-1"></i> Importing...
                </span>
                <span v-else>
                  <i class="fas fa-cloud-download-alt me-1"></i> Import Articles
                </span>
              </button>
            </div>
            
            <div v-if="crawlResult" class="crawl-result mt-3">
              <div class="alert alert-success" v-if="crawlResult.total_imported > 0">
                <i class="fas fa-check-circle me-2"></i>
                {{ crawlResult.message }}
                <br />
                <small>Category: {{ crawlResult.category }}</small>
                <br />
                <small>Skipped (duplicates): {{ crawlResult.skipped }}</small>
              </div>
              <div class="alert alert-warning" v-else-if="crawlResult.skipped > 0">
                <i class="fas fa-exclamation-triangle me-2"></i>
                All {{ crawlResult.skipped }} articles were duplicates
              </div>
              <div class="alert alert-info" v-else>
                <i class="fas fa-info-circle me-2"></i>
                No articles found in category
              </div>
            </div>
            <div v-if="crawlError" class="alert alert-danger mt-3">
              <i class="fas fa-exclamation-circle me-2"></i>
              {{ crawlError }}
            </div>
          </div>
        </div>

        <!-- Submissions Table (Visible to Jury and Organizers) -->
        <div v-if="canViewSubmissions" class="card mb-4">
          <div class="card-header">
            <div class="d-flex justify-content-between align-items-center">
              <h5 class="mb-0"><i class="fas fa-file-alt me-2"></i>Submissions</h5>
              <button v-if="loadingSubmissions || refreshingMetadata" class="btn btn-sm btn-outline-secondary" disabled>
                <span class="spinner-border spinner-border-sm me-2"></span>
                {{ loadingSubmissions ? 'Loading...' : 'Refreshing...' }}
              </button>
              <!-- Refresh metadata fetches latest article data from MediaWiki -->
              <button v-else
class="btn btn-sm btn-outline-light"
@click="refreshMetadata"
                :disabled="submissions.length === 0"
title="Refresh article metadata"
                style="color: white; border-color: white;">
                <i class="fas fa-database me-1"></i>Refresh Metadata
              </button>
            </div>
          </div>
          <div class="card-body">
            <!-- Filter Tabs (automated scoring only) -->
            <div v-if="contestScoringMode === 'automated' && submissions.length > 0" class="mb-3">
              <div class="btn-group" role="group" aria-label="Filter submissions">
                <button type="button" class="btn btn-sm" :class="submissionFilter === 'all' ? 'btn-primary' : 'btn-outline-primary'" @click="submissionFilter = 'all'">
                  All <span class="badge bg-light text-dark ms-1">{{ submissions.length }}</span>
                </button>
                <button type="button" class="btn btn-sm" :class="submissionFilter === 'accepted' ? 'btn-success' : 'btn-outline-success'" @click="submissionFilter = 'accepted'">
                  Accepted <span class="badge bg-light text-dark ms-1">{{ submissions.filter(s => s.status === 'accepted').length }}</span>
                </button>
                <button type="button" class="btn btn-sm" :class="submissionFilter === 'rejected' ? 'btn-danger' : 'btn-outline-danger'" @click="submissionFilter = 'rejected'">
                  Rejected <span class="badge bg-light text-dark ms-1">{{ submissions.filter(s => s.status === 'rejected').length }}</span>
                </button>
                <button type="button" class="btn btn-sm" :class="submissionFilter === 'pending' ? 'btn-warning' : 'btn-outline-warning'" @click="submissionFilter = 'pending'">
                  Pending <span class="badge bg-light text-dark ms-1">{{ submissions.filter(s => s.status === 'pending').length }}</span>
                </button>
              </div>
            </div>

            <div v-if="submissions.length === 0 && !loadingSubmissions" class="alert alert-info">
              <i class="fas fa-info-circle me-2"></i>No submissions yet for this contest.
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
                      <div v-if="submission.article_expansion_bytes !== null &&
                        submission.article_expansion_bytes !== undefined"
class="text-muted small mt-1">
                        <i class="me-1"
:class="submission.article_expansion_bytes > 0
                          ? 'fas fa-arrow-up'
                          : submission.article_expansion_bytes < 0
                            ? 'fas fa-arrow-down'
                            : 'fas fa-arrows-left-right'
                          "></i>
                        Expansion bytes:
                        <span :class="submission.article_expansion_bytes > 0
                          ? 'text-success'
                          : submission.article_expansion_bytes < 0
                            ? 'text-danger'
                            : 'text-muted'">
                          {{ submission.article_expansion_bytes > 0
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
                      <div v-if="submission.latest_revision_author"
class="mt-2 pt-2"
                        style="border-top: 1px solid #dee2e6;">
                        <div>
                          <i class="fas fa-user me-1"></i>{{ submission.latest_revision_author }}
                          <span class="badge bg-info ms-1" style="font-size: 0.7em;">Latest</span>
                        </div>
                        <div v-if="submission.latest_revision_timestamp" class="text-muted small mt-1">
                          <i class="fas fa-calendar me-1"></i>
                          {{ formatDateShort(submission.latest_revision_timestamp) }}
                        </div>
                      </div>
                    </td>
                    <td>{{ submission.username || 'Unknown' }}</td>
                    <td>
                      <span 
                        :class="`badge bg-${getStatusColor(submission.status)}`"
                        :style="(submission.evaluation_reason && contestScoringMode === 'automated') ? 'cursor: pointer;' : ''"
                        @click="showEvaluationDetails(submission)"
                        :title="(submission.evaluation_reason && contestScoringMode === 'automated') ? 'Click to see details' : ''">
                        {{ submission.status }}
                      </span>
                      <div v-if="submission.already_reviewed" class="text-muted small mt-1">
                        <i class="fas fa-check-circle me-1"></i>Reviewed
                      </div>
                    </td>
                    <td>
                      <span 
                        :style="(submission.evaluation_reason && contestScoringMode === 'automated') ? 'cursor: pointer; text-decoration: underline;' : ''"
                        @click="showEvaluationDetails(submission)"
                        :title="(submission.evaluation_reason && contestScoringMode === 'automated') ? 'Click to see score breakdown' : ''">
                        {{ submission.score || 0 }}
                      </span>
                    </td>
                    <td>{{ formatDate(submission.submitted_at) }}</td>
                    <td>
                      <button v-if="canViewSubmissions"
@click="handleDeleteSubmission(submission)"
                        class="btn btn-sm btn-outline-danger"
title="Delete Submission"
                        :disabled="deletingSubmissionId === submission.id">
                        <span v-if="deletingSubmissionId === submission.id"
                          class="spinner-border spinner-border-sm"></span>
                        <i v-else class="fas fa-trash"></i>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Bottom Action Row -->
        <div class="d-flex justify-content-between align-items-center gap-2 mb-4">
          <!-- Debug warning for auth issues -->
          <div v-if="contest && !currentUser && !checkingAuth" class="alert alert-warning py-1 px-2 mb-0 me-auto">
            <i class="fas fa-exclamation-triangle me-1"></i>
            <strong>User not loaded!</strong>
            <button class="btn btn-sm btn-outline-warning ms-2" @click="forceAuthRefresh">
              <i class="fas fa-sync-alt me-1"></i>Refresh Auth
            </button>
          </div>

          <!-- Submit article button for active contests -->
          <button v-if="contest?.status === 'current' && isAuthenticated && !canViewSubmissions"
            class="btn btn-primary ms-auto"
@click="handleSubmitArticle">
            <i class="fas fa-paper-plane me-2"></i>Submit Article
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Modals -->
  <SubmitArticleModal v-if="submittingToContestId"
:contest-id="submittingToContestId"
    @submitted="handleArticleSubmitted" />

  <ArticlePreviewModal v-if="!!currentSubmission"
:can-review="canUserReview"
    :article-url="currentSubmission.article_link"
:article-title="currentSubmission.article_title"
    :submission-id="currentSubmission.id"
:submission="currentSubmission"
    :contest-scoring-config="contest?.scoring_parameters"
@reviewed="handleSubmissionReviewed"
    @deleted="handleSubmissionDeleted" />

  <!-- ========================================================================== -->
  <!-- EVALUATION DETAILS MODAL - Shows score breakdown or rejection reason -->
  <!-- ========================================================================== -->
  <div class="modal fade" id="evaluationDetailsModal" tabindex="-1">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">
            <i class="fas fa-info-circle me-2"></i>
            Evaluation Details
          </h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body" v-if="selectedEvaluationSubmission">
          <h6 class="mb-3">{{ selectedEvaluationSubmission.article_title }}</h6>
          
          <!-- Status Badge -->
          <div class="mb-3">
            <span :class="`badge bg-${getStatusColor(selectedEvaluationSubmission.status)} fs-6`">
              {{ selectedEvaluationSubmission.status }}
            </span>
            <span class="ms-2 fw-bold">Score: {{ selectedEvaluationSubmission.score || 0 }}</span>
          </div>
          
          <!-- Rejection Reason -->
          <div v-if="selectedEvaluationSubmission.status === 'rejected'" class="alert alert-danger">
            <i class="fas fa-times-circle me-2"></i>
            <strong>Rejection Reason:</strong>
            <p class="mb-0 mt-2">{{ selectedEvaluationSubmission.evaluation_reason }}</p>
          </div>
          
          <!-- Score Breakdown (for accepted) -->
          <div v-if="selectedEvaluationSubmission.status === 'accepted' && selectedEvaluationSubmission.score_breakdown">
            <h6 class="mb-3"><i class="fas fa-calculator me-2"></i>Score Breakdown</h6>
            <table class="table table-sm">
              <tbody>
                <tr v-if="selectedEvaluationSubmission.score_breakdown.base_points">
                  <td>Base Points</td>
                  <td class="text-end">{{ selectedEvaluationSubmission.score_breakdown.base_points }}</td>
                </tr>
                <tr v-if="selectedEvaluationSubmission.score_breakdown.bytes_points">
                  <td>Bytes ({{ selectedEvaluationSubmission.score_breakdown.bytes_count || 0 }})</td>
                  <td class="text-end">{{ selectedEvaluationSubmission.score_breakdown.bytes_points }}</td>
                </tr>
                <tr v-if="selectedEvaluationSubmission.score_breakdown.incoming_links_points">
                  <td>Incoming Links ({{ selectedEvaluationSubmission.score_breakdown.incoming_links_count || 0 }})</td>
                  <td class="text-end">{{ selectedEvaluationSubmission.score_breakdown.incoming_links_points }}</td>
                </tr>
                <tr v-if="selectedEvaluationSubmission.score_breakdown.outgoing_links_points">
                  <td>Outgoing Links ({{ selectedEvaluationSubmission.score_breakdown.outgoing_links_count || 0 }})</td>
                  <td class="text-end">{{ selectedEvaluationSubmission.score_breakdown.outgoing_links_points }}</td>
                </tr>
                <tr v-if="selectedEvaluationSubmission.score_breakdown.new_references_points">
                  <td>New References ({{ selectedEvaluationSubmission.score_breakdown.new_references_count || 0 }})</td>
                  <td class="text-end">{{ selectedEvaluationSubmission.score_breakdown.new_references_points }}</td>
                </tr>
                <tr v-if="selectedEvaluationSubmission.score_breakdown.reused_references_points">
                  <td>Reused References ({{ selectedEvaluationSubmission.score_breakdown.reused_references_count || 0 }})</td>
                  <td class="text-end">{{ selectedEvaluationSubmission.score_breakdown.reused_references_points }}</td>
                </tr>
                <tr v-if="selectedEvaluationSubmission.score_breakdown.infobox_points">
                  <td>Infoboxes ({{ selectedEvaluationSubmission.score_breakdown.infobox_count || 0 }})</td>
                  <td class="text-end">{{ selectedEvaluationSubmission.score_breakdown.infobox_points }}</td>
                </tr>
                <tr v-if="selectedEvaluationSubmission.score_breakdown.image_points">
                  <td>Images ({{ selectedEvaluationSubmission.score_breakdown.image_count || 0 }})</td>
                  <td class="text-end">{{ selectedEvaluationSubmission.score_breakdown.image_points }}</td>
                </tr>
                <tr class="table-primary fw-bold">
                  <td>Total Score</td>
                  <td class="text-end">{{ selectedEvaluationSubmission.score }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
        </div>
      </div>
    </div>
  </div>

  <!-- ========================================================================== -->
  <!-- REFACTORED EDIT CONTEST MODAL - CLEAR UX FOR SCORING MODE LOCK -->
  <!-- ========================================================================== -->
  <div class="modal fade" id="editContestModal" tabindex="-1">
    <div class="modal-dialog modal-fullscreen">
      <div class="modal-content">
        <!-- Modal Header -->
        <div class="modal-header py-2">
          <div class="text-white">WikiContest Tool</div>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>

        <!-- Modal Body -->
        <div class="modal-body">
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
                <textarea class="form-control"
id="editContestDescription"
rows="3"
                  v-model="editForm.description"></textarea>
              </div>

              <div class="mb-3">
                <label for="editContestRules" class="form-label">Contest Rules *</label>
                <textarea class="form-control"
id="editContestRules"
rows="4"
                  placeholder="Write rules about how articles must be submitted."
v-model="editForm.rules"
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
                  <input type="date"
class="form-control"
id="editStartDate"
v-model="editForm.start_date"
required />
                </div>
                <div class="col-md-6 mb-3">
                  <label for="editEndDate" class="form-label">End Date *</label>
                  <input type="date"
class="form-control"
id="editEndDate"
v-model="editForm.end_date"
required />
                </div>
              </div>
            </div>

            <!-- Organizers Section -->
            <div class="edit-section">
              <h6 class="section-title">
                <i class="fas fa-user-tie me-2"></i>Organizers
              </h6>

              <!-- Display selected organizers as removable badges -->
              <div class="mb-2 p-2 border rounded bg-light organizer-selection-box" style="min-height: 40px;">
                <small v-if="editForm.selectedOrganizers.length === 0" class="organizer-placeholder-text">
                  No additional organizers added
                </small>
                <span v-for="username in editForm.selectedOrganizers"
:key="username"
class="badge bg-success me-2 mb-2"
                  style="font-size: 0.9rem; cursor: pointer;">
                  {{ username }}
                  <i class="fas fa-times ms-1" @click="removeOrganizer(username)"></i>
                </span>
              </div>

              <!-- Organizer search input with autocomplete dropdown -->
              <div style="position: relative;">
                <input type="text"
class="form-control"
v-model="organizerSearchQuery"
@input="searchOrganizers"
                  placeholder="Type username to add additional organizers..."
autocomplete="off" />

                <!-- Autocomplete results dropdown -->
                <div v-if="organizerSearchResults.length > 0 && organizerSearchQuery.length >= 2"
                  class="organizer-autocomplete position-absolute w-100 border rounded-bottom"
                  style="max-height: 200px; overflow-y: auto; z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                  <div v-for="user in organizerSearchResults"
:key="user.username"
                    class="p-2 border-bottom cursor-pointer"
                    :class="{ 'bg-warning-subtle': isCurrentUser(user.username) }"
style="cursor: pointer;"
                    @click="addOrganizer(user.username)">
                    <div class="d-flex align-items-center justify-content-between">
                      <div class="d-flex align-items-center">
                        <i class="fas fa-user-tie me-2 text-success"></i>
                        <strong>{{ user.username }}</strong>
                      </div>
                      <!-- Show info badge if user tries to select themselves -->
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

              <!-- Selected Jury Members Display -->
              <div class="mb-2 p-2 border rounded bg-light jury-selection-box" style="min-height: 40px;">
                <small v-if="editForm.selectedJuryMembers.length === 0" class="jury-placeholder-text">
                  No jury members selected yet
                </small>
                <span v-for="username in editForm.selectedJuryMembers"
:key="username"
                  class="badge bg-primary me-2 mb-2"
style="font-size: 0.9rem; cursor: pointer;">
                  <i class="fas fa-gavel me-1"></i>{{ username }}
                  <i class="fas fa-times ms-1" @click="removeJuryMember(username)"></i>
                </span>
              </div>

              <!-- Jury Input with Autocomplete -->
              <div style="position: relative;">
                <input type="text"
class="form-control"
v-model="jurySearchQuery"
@input="searchJuryMembers"
                  placeholder="Type username to search and add..."
autocomplete="off" />

                <!-- Autocomplete Dropdown -->
                <div v-if="jurySearchResults.length > 0 && jurySearchQuery.length >= 2"
                  class="jury-autocomplete position-absolute w-100 border rounded-bottom"
                  style="max-height: 200px; overflow-y: auto; z-index: 1000; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                  <div v-for="user in jurySearchResults"
:key="user.username"
class="p-2 border-bottom cursor-pointer"
                    :class="{ 'bg-warning-subtle': isCurrentUser(user.username) }"
style="cursor: pointer;"
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

            <!-- ====================================================================== -->
            <!-- SCORING SYSTEM SECTION - REDESIGNED FOR CLARITY -->
            <!-- ====================================================================== -->
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
                      <input type="number"
class="form-control"
v-model.number="maxScore"
min="1"
max="1000"
required />
                      <small class="text-muted">Final score scaled to this value</small>
                    </div>
                    <div class="col-md-6">
                      <label class="form-label">Minimum Score (Rejected) *</label>
                      <input type="number"
class="form-control"
v-model.number="minScore"
min="0"
max="1000"
required />
                      <small class="text-muted">Score for rejected submissions</small>
                    </div>
                  </div>

                  <!-- Parameters List -->
                  <div class="mb-3">
                    <label class="form-label fw-bold">Scoring Parameters *</label>
                    <div class="parameters-list">
                      <div v-for="(param, index) in scoringParameters" :key="index" class="parameter-item card mb-2">
                        <div class="card-body p-3">
                          <div class="row align-items-center">
                            <div class="col-md-3">
                              <label class="small text-muted mb-1">Parameter Name</label>
                              <input type="text"
class="form-control"
v-model="param.name"
placeholder="e.g., Quality"
                                required />
                            </div>
                            <div class="col-md-3">
                              <label class="small text-muted mb-1">Weight (%)</label>
                              <div class="input-group">
                                <input type="number"
class="form-control"
v-model.number="param.weight"
min="0"
                                  max="100"
placeholder="0-100"
required />
                                <span class="input-group-text">%</span>
                              </div>
                            </div>
                            <div class="col-md-5">
                              <label class="small text-muted mb-1">Description (Optional)</label>
                              <input type="text"
class="form-control"
v-model="param.description"
                                placeholder="Brief description" />
                            </div>
                            <div class="col-md-1 text-end">
                              <label class="small text-muted mb-1 d-block">&nbsp;</label>
                              <button type="button"
class="btn btn-sm btn-outline-danger"
                                @click="removeParameter(index)"
:disabled="scoringParameters.length <= 1"
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

                    <!-- Weight Validation -->
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
                      <input type="number"
class="form-control"
v-model.number="editForm.marks_setting_accepted"
min="0"
                        required />
                      <small class="text-muted">Maximum points for accepted submissions</small>
                    </div>
                    <div class="col-md-6 mb-3">
                      <label class="form-label">Points for Rejected Submissions *</label>
                      <input type="number"
class="form-control"
v-model.number="editForm.marks_setting_rejected"
min="0"
                        required />
                      <small class="text-muted">Points for rejected submissions</small>
                    </div>
                  </div>
                </div>

                <!-- Automated Scoring Locked Editing -->
                <div v-else-if="contestScoringMode === 'automated'">
                  <!-- Eligibility Criteria -->
                  <div class="mb-4">
                    <h6 class="mb-3"><i class="fas fa-filter me-2"></i>Eligibility Criteria</h6>
                    <div class="row">
                      <div class="col-md-6 mb-3">
                        <label class="form-label">Minimum Edits</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.eligibility.min_edits"
min="0" />
                      </div>
                      <div class="col-md-6 mb-3">
                        <label class="form-label">Minimum Outgoing Links</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.eligibility.min_outgoing_links"
min="0" />
                      </div>
                    </div>
                  </div>

                  <!-- Evaluation Criteria -->
                  <div class="mb-4">
                    <h6 class="mb-3"><i class="fas fa-calculator me-2"></i>Evaluation Criteria (Points)</h6>
                    <div class="row">
                      <div class="col-md-4 mb-3">
                        <label class="form-label">Points per Accepted</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.evaluation.points_per_accepted"
min="0"
step="0.01" />
                      </div>
                      <div class="col-md-4 mb-3">
                        <label class="form-label">Points per Byte</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.evaluation.points_per_byte"
min="0"
step="0.0001" />
                      </div>
                      <div class="col-md-4 mb-3">
                        <label class="form-label">Points per Incoming Link</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.evaluation.points_per_incoming_link"
min="0"
step="0.01" />
                      </div>
                      <div class="col-md-4 mb-3">
                        <label class="form-label">Points per Outgoing Link</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.evaluation.points_per_outgoing_link"
min="0"
step="0.01" />
                      </div>
                      <div class="col-md-4 mb-3">
                        <label class="form-label">Points per Category</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.evaluation.points_per_category"
min="0"
step="0.01" />
                      </div>
                      <div class="col-md-4 mb-3">
                        <label class="form-label">Points per New Reference</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.evaluation.points_per_new_reference"
min="0"
step="0.01" />
                      </div>
                      <div class="col-md-4 mb-3">
                        <label class="form-label">Points per Reused Reference</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.evaluation.points_per_reused_reference"
min="0"
step="0.01" />
                      </div>
                      <div class="col-md-4 mb-3">
                        <label class="form-label">Points per Infobox</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.evaluation.points_per_infobox"
min="0"
step="0.01" />
                      </div>
                      <div class="col-md-4 mb-3">
                        <label class="form-label">Points per Image</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.evaluation.points_per_image"
min="0"
step="0.01" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- UNLOCKED MODE: Allow Switching -->
              <div v-else class="unlocked-edit-mode">
                <!-- Toggle Switch (hidden for automated scoring - modes are mutually exclusive) -->
                <div v-if="contestScoringMode !== 'automated'" class="scoring-mode-toggle mb-2">
                  <div class="form-check form-switch">
                    <input class="form-check-input"
type="checkbox"
id="editEnableMultiParam"
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

                <!-- Automated Scoring Settings (unlocked mode) -->
                <div v-if="contestScoringMode === 'automated'" class="automated-scoring-form">
                  <!-- Eligibility Criteria -->
                  <div class="mb-4">
                    <h6 class="mb-3"><i class="fas fa-filter me-2"></i>Eligibility Criteria</h6>
                    <div class="row">
                      <div class="col-md-6 mb-3">
                        <label class="form-label">Minimum Edits</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.eligibility.min_edits"
min="0" />
                      </div>
                      <div class="col-md-6 mb-3">
                        <label class="form-label">Minimum Outgoing Links</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.eligibility.min_outgoing_links"
min="0" />
                      </div>
                    </div>
                  </div>

                  <!-- Evaluation Criteria -->
                  <div class="mb-4">
                    <h6 class="mb-3"><i class="fas fa-calculator me-2"></i>Evaluation Criteria (Points)</h6>
                    <div class="row">
                      <div class="col-md-4 mb-3">
                        <label class="form-label">Points per Accepted</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.evaluation.points_per_accepted"
min="0"
step="0.01" />
                      </div>
                      <div class="col-md-4 mb-3">
                        <label class="form-label">Points per Incoming Link</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.evaluation.points_per_incoming_link"
min="0"
step="0.01" />
                      </div>
                      <div class="col-md-4 mb-3">
                        <label class="form-label">Points per Outgoing Link</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.evaluation.points_per_outgoing_link"
min="0"
step="0.01" />
                      </div>
                      <div class="col-md-4 mb-3">
                        <label class="form-label">Points per New Reference</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.evaluation.points_per_new_reference"
min="0"
step="0.01" />
                      </div>
                      <div class="col-md-4 mb-3">
                        <label class="form-label">Points per Reused Reference</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.evaluation.points_per_reused_reference"
min="0"
step="0.01" />
                      </div>
                      <div class="col-md-4 mb-3">
                        <label class="form-label">Points per Infobox</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.evaluation.points_per_infobox"
min="0"
step="0.01" />
                      </div>
                      <div class="col-md-4 mb-3">
                        <label class="form-label">Points per Image</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.evaluation.points_per_image"
min="0"
step="0.01" />
                      </div>
                      <div class="col-md-4 mb-3">
                        <label class="form-label">Points per Byte</label>
                        <input type="number"
class="form-control"
v-model.number="automatedSettings.evaluation.points_per_byte"
min="0"
step="0.0001" />
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Simple Scoring Form -->
                <div v-if="contestScoringMode !== 'automated' && !enableMultiParameterScoring" class="simple-scoring-form">
                  <div class="row">
                    <div class="col-md-6 mb-3">
                      <label class="form-label">Points for Accepted Submissions *</label>
                      <input type="number"
class="form-control"
v-model.number="editForm.marks_setting_accepted"
min="0"
                        required />
                      <small class="text-muted">Maximum points that can be awarded</small>
                    </div>
                    <div class="col-md-6 mb-3">
                      <label class="form-label">Points for Rejected Submissions *</label>
                      <input type="number"
class="form-control"
v-model.number="editForm.marks_setting_rejected"
min="0"
                        required />
                      <small class="text-muted">Points for rejected submissions (usually 0)</small>
                    </div>
                  </div>
                </div>

                <!-- Multi-Parameter Scoring Form -->
                <div v-else-if="contestScoringMode !== 'automated'" class="multi-param-scoring-form">
                  <div class="row mb-3">
                    <div class="col-md-6">
                      <label class="form-label">Maximum Score (Accepted) *</label>
                      <input type="number"
class="form-control"
v-model.number="maxScore"
min="1"
max="1000"
required />
                      <small class="text-muted">Final weighted score scaled to this maximum</small>
                    </div>
                    <div class="col-md-6">
                      <label class="form-label">Minimum Score (Rejected) *</label>
                      <input type="number"
class="form-control"
v-model.number="minScore"
min="0"
max="1000"
required />
                      <small class="text-muted">Fixed score for rejected submissions</small>
                    </div>
                  </div>

                  <!-- Parameters List (same as locked mode) -->
                  <div class="mb-3">
                    <label class="form-label fw-bold">Scoring Parameters *</label>
                    <div class="parameters-list">
                      <div v-for="(param, index) in scoringParameters" :key="index" class="parameter-item card mb-2">
                        <div class="card-body p-3">
                          <div class="row align-items-center">
                            <div class="col-md-3">
                              <label class="small text-muted mb-1">Parameter Name</label>
                              <input type="text"
class="form-control"
v-model="param.name"
placeholder="e.g., Quality"
                                required />
                            </div>
                            <div class="col-md-3">
                              <label class="small text-muted mb-1">Weight (%)</label>
                              <div class="input-group">
                                <input type="number"
class="form-control"
v-model.number="param.weight"
min="0"
                                  max="100"
placeholder="0-100"
required />
                                <span class="input-group-text">%</span>
                              </div>
                            </div>
                            <div class="col-md-5">
                              <label class="small text-muted mb-1">Description (Optional)</label>
                              <input type="text"
class="form-control"
v-model="param.description"
                                placeholder="Brief description" />
                            </div>
                            <div class="col-md-1 text-end">
                              <label class="small text-muted mb-1 d-block">&nbsp;</label>
                              <button type="button"
class="btn btn-sm btn-outline-danger"
                                @click="removeParameter(index)"
:disabled="scoringParameters.length <= 1"
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

                    <!-- Weight Validation -->
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
                <input type="number"
v-model.number="editForm.min_byte_count"
class="form-control"
min="0"
                  placeholder="e.g., 1000"
required />
                <small class="form-text text-muted">Articles must have at least this many bytes</small>
              </div>

              <div class="mb-3">
                <label class="form-label">Minimum Reference Count</label>
                <input type="number"
v-model.number="editForm.min_reference_count"
class="form-control"
min="0"
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

                <!-- Dynamic category URL inputs -->
                <div v-for="(category, index) in editForm.categories" :key="index" class="mb-2">
                  <div class="input-group">
                    <input type="url"
class="form-control"
v-model="editForm.categories[index]"
                      :placeholder="index === 0 ? 'https://en.wikipedia.org/wiki/Category:Example' : 'Add another category URL'" />
                    <!-- Allow removing categories -->
                    <button v-if="editForm.categories.length > 1"
type="button"
class="btn btn-outline-danger"
                      @click="removeCategory(index)"
title="Remove category">
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
                <input type="url"
class="form-control"
id="editTemplateLink"
v-model="editForm.template_link"
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
                <input type="url"
class="form-control"
id="editOutreachDashboardUrl"
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

          </form>
        </div>

        <!-- Modal Footer -->
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
            <i class="fas fa-times me-2"></i>Cancel
          </button>
          <button type="button"
class="btn btn-primary"
@click="saveContestEdits"
:disabled="savingContest">
            <span v-if="savingContest" class="spinner-border spinner-border-sm me-2"></span>
            <i v-else class="fas fa-save me-2"></i>
            {{ savingContest ? 'Saving...' : 'Save Changes' }}
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Evaluation Details Modal (for automated scoring contests) -->
  <div class="modal fade" id="evaluationDetailsModal" tabindex="-1" aria-labelledby="evaluationDetailsModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="evaluationDetailsModalLabel">
            <i class="fas fa-chart-bar me-2"></i>Evaluation Details
          </h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body" v-if="selectedEvaluationSubmission">
          <h6 class="mb-3">
            <a :href="selectedEvaluationSubmission.article_link" target="_blank" class="text-decoration-none">
              {{ selectedEvaluationSubmission.article_title }}
              <i class="fas fa-external-link-alt ms-1 small"></i>
            </a>
          </h6>

          <!-- Accepted: Show Score Breakdown -->
          <div v-if="selectedEvaluationSubmission.status === 'accepted' && selectedEvaluationSubmission.score_breakdown">
            <div class="alert alert-success py-2">
              <i class="fas fa-check-circle me-2"></i>
              <strong>Accepted</strong> — Total Score: {{ selectedEvaluationSubmission.score }}
            </div>
            <table class="table table-sm table-bordered">
              <thead class="table-light">
                <tr>
                  <th>Component</th>
                  <th class="text-center">Count</th>
                  <th class="text-end">Points</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="selectedEvaluationSubmission.score_breakdown.base_points">
                  <td><i class="fas fa-star me-1 text-warning"></i>Base Points</td>
                  <td class="text-center">—</td>
                  <td class="text-end">{{ selectedEvaluationSubmission.score_breakdown.base_points }}</td>
                </tr>
                <tr v-if="selectedEvaluationSubmission.score_breakdown.bytes_points !== undefined">
                  <td><i class="fas fa-file-alt me-1 text-info"></i>Bytes</td>
                  <td class="text-center">{{ selectedEvaluationSubmission.score_breakdown.bytes_count || 0 }}</td>
                  <td class="text-end">{{ selectedEvaluationSubmission.score_breakdown.bytes_points }}</td>
                </tr>
                <tr v-if="selectedEvaluationSubmission.score_breakdown.incoming_links_points !== undefined">
                  <td><i class="fas fa-arrow-left me-1 text-primary"></i>Incoming Links</td>
                  <td class="text-center">{{ selectedEvaluationSubmission.score_breakdown.incoming_links_count || 0 }}</td>
                  <td class="text-end">{{ selectedEvaluationSubmission.score_breakdown.incoming_links_points }}</td>
                </tr>
                <tr v-if="selectedEvaluationSubmission.score_breakdown.outgoing_links_points !== undefined">
                  <td><i class="fas fa-arrow-right me-1 text-primary"></i>Outgoing Links</td>
                  <td class="text-center">{{ selectedEvaluationSubmission.score_breakdown.outgoing_links_count || 0 }}</td>
                  <td class="text-end">{{ selectedEvaluationSubmission.score_breakdown.outgoing_links_points }}</td>
                </tr>
                <tr v-if="selectedEvaluationSubmission.score_breakdown.new_references_points !== undefined">
                  <td><i class="fas fa-book me-1 text-success"></i>New References</td>
                  <td class="text-center">{{ selectedEvaluationSubmission.score_breakdown.new_references_count || 0 }}</td>
                  <td class="text-end">{{ selectedEvaluationSubmission.score_breakdown.new_references_points }}</td>
                </tr>
                <tr v-if="selectedEvaluationSubmission.score_breakdown.reused_references_points !== undefined">
                  <td><i class="fas fa-book-open me-1 text-secondary"></i>Reused References</td>
                  <td class="text-center">{{ selectedEvaluationSubmission.score_breakdown.reused_references_count || 0 }}</td>
                  <td class="text-end">{{ selectedEvaluationSubmission.score_breakdown.reused_references_points }}</td>
                </tr>
                <tr v-if="selectedEvaluationSubmission.score_breakdown.infobox_points !== undefined">
                  <td><i class="fas fa-info-circle me-1 text-dark"></i>Infoboxes</td>
                  <td class="text-center">{{ selectedEvaluationSubmission.score_breakdown.infobox_count || 0 }}</td>
                  <td class="text-end">{{ selectedEvaluationSubmission.score_breakdown.infobox_points }}</td>
                </tr>
                <tr v-if="selectedEvaluationSubmission.score_breakdown.image_points !== undefined">
                  <td><i class="fas fa-image me-1 text-danger"></i>Images</td>
                  <td class="text-center">{{ selectedEvaluationSubmission.score_breakdown.image_count || 0 }}</td>
                  <td class="text-end">{{ selectedEvaluationSubmission.score_breakdown.image_points }}</td>
                </tr>
              </tbody>
              <tfoot class="table-light">
                <tr>
                  <th colspan="2">Total Score</th>
                  <th class="text-end">{{ selectedEvaluationSubmission.score }}</th>
                </tr>
              </tfoot>
            </table>
          </div>

          <!-- Rejected: Show Reason -->
          <div v-else-if="selectedEvaluationSubmission.status === 'rejected'">
            <div class="alert alert-danger">
              <i class="fas fa-times-circle me-2"></i>
              <strong>Rejected</strong>
            </div>
            <div class="card">
              <div class="card-body">
                <p class="mb-0"><strong>Reason:</strong></p>
                <p class="mb-0 mt-1 text-danger">{{ selectedEvaluationSubmission.evaluation_reason }}</p>
              </div>
            </div>
          </div>

          <!-- Pending or No Data -->
          <div v-else>
            <div class="alert alert-info">
              <i class="fas fa-clock me-2"></i>
              <span v-if="selectedEvaluationSubmission.evaluation_reason">{{ selectedEvaluationSubmission.evaluation_reason }}</span>
              <span v-else>This submission has not been evaluated yet. Click "Refresh Metadata" to run the evaluation.</span>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref, watch, onMounted, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useStore } from '../store'
import api from '../services/api'
import { showAlert } from '../utils/alerts'
import SubmitArticleModal from '../components/SubmitArticleModal.vue'
import ArticlePreviewModal from '../components/ArticlePreviewModal.vue'
import OutreachDashboardTab from '../components/OutreachDashboardTab.vue'

// Helper function to get CSRF token from cookies
function getCookie(name) {
  return document.cookie
    .split('; ')
    .find(row => row.startsWith(name + '='))
    ?.split('=')[1]
}

export default {
  name: 'ContestView',
  components: {
    SubmitArticleModal,
    ArticlePreviewModal,
    OutreachDashboardTab
  },

  setup() {
    const router = useRouter()
    const route = useRoute()
    const store = useStore()

    // Component state
    const contest = ref(null)
    const loading = ref(true)
    const error = ref(null)
    const submissions = ref([])
    const loadingSubmissions = ref(false)
    const refreshingMetadata = ref(false)
    const deletingContest = ref(false)
    const canDeleteContest = ref(false)
    const checkingAuth = ref(false)
    const submittingToContestId = ref(null)
    const previewArticleUrl = ref('')
    const previewArticleTitle = ref('')
    const jurySearchQuery = ref('')
    const jurySearchResults = ref([])
    const organizerSearchQuery = ref('')
    const organizerSearchResults = ref([])
    const deletingSubmissionId = ref(null)
    const savingContest = ref(false)
    let jurySearchTimeout = null
    let organizerSearchTimeout = null
    let editModal = null

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
    const contestScoringMode = ref('simple') // 'simple', 'multi_parameter', or 'automated'
    const scoringModeLocked = ref(false)
    const reviewedSubmissionsCount = ref(0)

    // Automated scoring settings for edit modal
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

    // Reset to default automated settings
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

    // Submission filter state (for automated scoring dashboard)
    const submissionFilter = ref('all') // 'all', 'accepted', 'rejected', 'pending'

    const filteredSubmissions = computed(() => {
      if (submissionFilter.value === 'all') {
        return submissions.value
      }
      return submissions.value.filter(s => s.status === submissionFilter.value)
    })

    // Category crawler state
    const selectedCategory = ref('')
    const crawlLimit = ref(100)
    const crawling = ref(false)
    const crawlResult = ref(null)
    const crawlError = ref(null)

    // Crawl category and import articles
    const crawlCategory = async () => {
      if (!selectedCategory.value) return

      crawling.value = true
      crawlResult.value = null
      crawlError.value = null

      try {
        const csrfToken = getCookie('csrf_access_token')
        const response = await fetch(`/api/contest/${contest.value.id}/crawl-category`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': csrfToken || ''
          },
          credentials: 'include',
          body: JSON.stringify({
            category_url: selectedCategory.value,
            limit: crawlLimit.value || 100
          })
        })

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.error || 'Failed to crawl category')
        }

        crawlResult.value = data

        // Refresh submissions list to show new imports
        await loadSubmissions()
      } catch (err) {
        crawlError.value = err.message || 'An error occurred while crawling the category'
      } finally {
        crawling.value = false
      }
    }

    // Track current submission for preview modal
    const currentSubmissionId = ref(null)

    // Get submission reactively to ensure updates propagate
    const currentSubmission = computed(() => {
      if (!currentSubmissionId.value) return null
      return submissions.value.find(s => s.id === currentSubmissionId.value)
    })

    // Selected submission for evaluation details modal
    const selectedEvaluationSubmission = ref(null)
    let evaluationDetailsModal = null

    // Show evaluation details modal (for automated scoring)
    const showEvaluationDetails = (submission) => {
      if (!submission.evaluation_reason || contestScoringMode.value !== 'automated') {
        return
      }
      selectedEvaluationSubmission.value = submission
      if (!evaluationDetailsModal) {
        const modalEl = document.getElementById('evaluationDetailsModal')
        if (modalEl) {
          evaluationDetailsModal = new bootstrap.Modal(modalEl)
        }
      }
      if (evaluationDetailsModal) {
        evaluationDetailsModal.show()
      }
    }

    // Get current user from multiple possible store locations
    const currentUser = computed(() => {
      if (store.state && store.state.currentUser) {
        return store.state.currentUser
      }
      if (store.currentUser) {
        return store.currentUser
      }
      return null
    })

    // Check if user is authenticated with valid data
    const isAuthenticated = computed(() => {
      const user = currentUser.value
      return !!user && !!user.id && !!user.username
    })

    // Determine if user can view submissions (organizers and jury only)
    const canViewSubmissions = computed(() => {
      if (!isAuthenticated.value || !contest.value || !currentUser.value) {
        return false
      }

      const username = (currentUser.value.username || '').trim().toLowerCase()
      const contestData = contest.value

      // Contest creator can view submissions
      const contestCreator = (contestData.created_by || '').trim().toLowerCase()
      if (contestCreator && username === contestCreator) {
        return true
      }

      // Jury members can view submissions
      if (contestData.jury_members && Array.isArray(contestData.jury_members)) {
        const juryUsernames = contestData.jury_members.map(j => (j || '').trim().toLowerCase())
        return juryUsernames.includes(username)
      }

      return false
    })

    // Determine if user can import articles (jury member or superadmin only)
    const canImportArticles = computed(() => {
      if (!isAuthenticated.value || !contest.value || !currentUser.value) {
        return false
      }

      const username = (currentUser.value.username || '').trim().toLowerCase()
      const role = (currentUser.value.role || '').trim().toLowerCase()

      // Superadmin can always import
      if (role === 'superadmin') {
        return true
      }

      // Jury members can import
      if (contest.value.jury_members && Array.isArray(contest.value.jury_members)) {
        const juryUsernames = contest.value.jury_members.map(j => (j || '').trim().toLowerCase())
        return juryUsernames.includes(username)
      }

      return false
    })

    // Determine if user can delete contest (creator or admin/superadmin)
    const checkDeletePermission = () => {
      canDeleteContest.value = false

      const userFromComputed = currentUser.value
      const userFromStore = store.currentUser
      const userFromState = (store.state && store.state.currentUser) || null
      const userToCheck = userFromComputed || userFromStore || userFromState

      if (!isAuthenticated.value || !contest.value || !userToCheck) {
        canDeleteContest.value = false
        return
      }

      const username = (userToCheck.username || '').trim()
      const role = (userToCheck.role || '').trim().toLowerCase()
      const contestCreator = (contest.value.created_by || '').trim()

      if (!username || !contestCreator) {
        canDeleteContest.value = false
        return
      }

      const usernameLower = username.toLowerCase()
      const creatorLower = contestCreator.toLowerCase()

      // Allow delete if user is creator or admin-level
      if (usernameLower === creatorLower) {
        canDeleteContest.value = true
        return
      }

      if (role === 'admin' || role === 'superadmin') {
        canDeleteContest.value = true
        return
      }

      canDeleteContest.value = false
    }

    // Format date to IST timezone with full details
    const formatDate = (dateString) => {
      if (!dateString) return 'No date'
      try {
        // Ensure UTC format for consistent parsing
        let utcDateString = dateString
        if (!dateString.endsWith('Z') && !dateString.includes('+') && !dateString.includes('-', 10)) {
          utcDateString = dateString + 'Z'
        }

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

    // Format date in shorter format for table display
    const formatDateShort = (dateString) => {
      if (!dateString) return ''
      try {
        let utcDateString = dateString
        if (!dateString.endsWith('Z') && !dateString.includes('+') && !dateString.includes('-', 10)) {
          utcDateString = dateString + 'Z'
        }

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

    // Convert bytes to human-readable format (KB/MB)
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

    // Format bytes with exact count in parentheses
    const formatByteCountWithExact = (bytes) => {
      if (!bytes && bytes !== 0) return ''

      const absBytes = Math.abs(bytes)

      let formatted = ''
      if (absBytes >= 1048576) {
        formatted = `${(absBytes / 1048576).toFixed(1)} MB (${bytes} bytes)`
      } else if (absBytes >= 1024) {
        formatted = `${(absBytes / 1024).toFixed(1)} KB (${bytes} bytes)`
      } else {
        formatted = `${bytes} bytes`
      }

      return formatted
    }

    // Extract category name from full MediaWiki URL
    const getCategoryName = (categoryUrl) => {
      if (!categoryUrl) return ''

      try {
        const url = new URL(categoryUrl)
        let pageTitle = ''

        // Parse standard MediaWiki URL format
        if (url.pathname.includes('/wiki/')) {
          pageTitle = decodeURIComponent(url.pathname.split('/wiki/')[1])
        } else if (url.searchParams.has('title')) {
          pageTitle = decodeURIComponent(url.searchParams.get('title'))
        } else {
          // Fallback to last path segment
          const parts = url.pathname.split('/').filter(p => p)
          if (parts.length > 0) {
            pageTitle = decodeURIComponent(parts[parts.length - 1])
          }
        }

        return pageTitle || categoryUrl
      } catch (e) {
        return categoryUrl
      }
    }

    // Simple byte count formatter
    const formatWordCount = (bytes) => {
      if (bytes === null || bytes === undefined) return '0 bytes'
      const absBytes = Math.abs(bytes)
      if (absBytes >= 1048576) {
        return `${(absBytes / 1048576).toFixed(1)} MB`
      }
      if (absBytes >= 1024) {
        return `${(absBytes / 1024).toFixed(1)} KB`
      }
      return `${absBytes} bytes`
    }

    // Convert status key to display label
    const getStatusLabel = (status) => {
      const labels = {
        current: 'Active',
        upcoming: 'Upcoming',
        past: 'Past',
        unknown: 'Unknown'
      }
      return labels[status] || 'Unknown'
    }

    // Get Bootstrap color class for submission status
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

    // Load contest by ID or name from route
    const loadContest = async (id = null) => {
      loading.value = true
      error.value = null

      try {
        let data
        if (id) {
          data = await api.get(`/contest/${id}`)
        } else {
          const contestName = route.params.name
          if (!contestName) throw new Error('Contest name is required')
          data = await api.get(`/contest/name/${contestName}`)
        }

        // Ensure scoring parameters are initialized
        contest.value = {
          ...data,
          scoring_parameters: data.scoring_parameters
            ? { ...data.scoring_parameters }
            : { enabled: false }
        }

        // Set contest scoring mode for the view (used by clickable status/score)
        if (data.automated_settings?.enabled === true) {
          contestScoringMode.value = 'automated'
        } else if (data.scoring_parameters?.enabled === true) {
          contestScoringMode.value = 'multi_parameter'
        } else {
          contestScoringMode.value = 'simple'
        }

        // Check permissions after loading contest
        await checkAuthAndPermissions()

        // Load submissions if user has access
        if (canViewSubmissions.value) loadSubmissions()
      } catch (err) {
        console.error('Error loading contest:', err)
        error.value = 'Failed to load contest: ' + (err.message || 'Unknown error')
      } finally {
        loading.value = false
      }
    }

    // Verify user authentication and check permissions
    const checkAuthAndPermissions = async () => {
      checkingAuth.value = true
      canDeleteContest.value = false

      try {
        // Try to get user from store
        let loadedUser = store.currentUser || (store.state && store.state.currentUser) || currentUser.value

        // If not in store, fetch from backend
        if (!loadedUser) {
          await store.checkAuth()
          await new Promise(resolve => setTimeout(resolve, 150))
          loadedUser = store.currentUser || (store.state && store.state.currentUser) || currentUser.value
        }

        // Allow time for reactive updates
        await new Promise(resolve => setTimeout(resolve, 100))

        checkDeletePermission()
      } catch (error) {
        console.error('Failed to check auth:', error)
        canDeleteContest.value = false
      } finally {
        checkingAuth.value = false
      }
    }

    // Fetch all submissions for this contest
    const loadSubmissions = async () => {
      if (!contest.value || !canViewSubmissions.value) {
        return
      }

      loadingSubmissions.value = true
      try {
        const data = await api.get(`/contest/${contest.value.id}/submissions`)
        submissions.value = data || []
      } catch (error) {
        console.error('Failed to load submissions:', error)
        showAlert('Failed to load submissions: ' + error.message, 'danger')
        submissions.value = []
      } finally {
        loadingSubmissions.value = false
      }
    }

    // Refresh article metadata from MediaWiki for all submissions
    const refreshMetadata = async () => {
      if (!contest.value || !canViewSubmissions.value || submissions.value.length === 0) {
        return
      }

      refreshingMetadata.value = true
      try {
        const response = await api.post(`/submission/contest/${contest.value.id}/refresh-metadata`)
        showAlert(
          `Metadata refreshed: ${response.updated} updated, ${response.failed} failed`,
          response.failed === 0 ? 'success' : 'warning'
        )
        await loadSubmissions()
      } catch (error) {
        console.error('Failed to refresh metadata:', error)
        showAlert('Failed to refresh metadata: ' + error.message, 'danger')
      } finally {
        refreshingMetadata.value = false
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
        await api.delete(`/contest/${contest.value.id}`)
        showAlert('Contest deleted successfully', 'success')
        router.push({ name: 'Contests' })
      } catch (error) {
        console.error('Failed to delete contest:', error)
        showAlert('Failed to delete contest: ' + error.message, 'danger')
      } finally {
        deletingContest.value = false
      }
    }

    // Open article submission modal
    const handleSubmitArticle = () => {
      if (!store.isAuthenticated) {
        showAlert('Please login to submit an article', 'warning')
        return
      }
      submittingToContestId.value = contest.value.id
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
      loadContest()
    }

    // Manually refresh authentication status
    const forceAuthRefresh = async () => {
      checkingAuth.value = true
      try {
        await store.checkAuth()
        await new Promise(resolve => setTimeout(resolve, 200))
        checkDeletePermission()
      } catch (error) {
        console.error('Auth refresh failed:', error)
      } finally {
        checkingAuth.value = false
      }
    }

    // Navigate back to contests list
    const goBack = () => {
      router.push({ name: 'Contests' })
    }

    // Show article preview modal for submission
    const showArticlePreview = (submission) => {
      currentSubmissionId.value = submission.id

      setTimeout(() => {
        const modalElement = document.getElementById('articlePreviewModal')
        if (modalElement) {
          const modal = new bootstrap.Modal(modalElement)
          modal.show()
        }
      }, 100)
    }

    // Update submission in array after review
    const handleSubmissionReviewed = (reviewData) => {
      console.log('Review received:', reviewData)

      const submissionIndex = submissions.value.findIndex(
        s => s.id === reviewData.submissionId
      )

      if (submissionIndex !== -1) {
        submissions.value[submissionIndex] = {
          ...submissions.value[submissionIndex],
          status: reviewData.status,
          score: reviewData.score,
          review_comment: reviewData.comment,
          already_reviewed: true,
          reviewed_at: new Date().toISOString()
        }

        // Trigger reactivity
        submissions.value = [...submissions.value]

        showAlert('Submission reviewed successfully', 'success')
      }
    }

    // Handle submission deleted from modal
    const handleSubmissionDeleted = (submissionId) => {
      console.log('Submission deleted:', submissionId)

      // Remove the submission from the array
      const submissionIndex = submissions.value.findIndex(
        s => s.id === submissionId
      )

      if (submissionIndex !== -1) {
        submissions.value.splice(submissionIndex, 1)
        showAlert('Submission deleted successfully', 'success')

        // Update contest submission count if available
        if (contest.value && contest.value.submission_count) {
          contest.value.submission_count -= 1
        }
      }
    }

    // Handle delete submission from table
    const handleDeleteSubmission = async (submission) => {
      // Confirmation dialog
      const confirmed = confirm(
        `Are you sure you want to delete the submission "${submission.article_title}"?\n\n` +
        'This action cannot be undone and will adjust the user\'s score.'
      )

      if (!confirmed) return

      deletingSubmissionId.value = submission.id

      try {
        await api.deleteSubmission(submission.id)

        // Remove from array
        const index = submissions.value.findIndex(s => s.id === submission.id)
        if (index !== -1) {
          submissions.value.splice(index, 1)
        }

        showAlert('Submission deleted successfully', 'success')

        // Update contest submission count
        if (contest.value && contest.value.submission_count) {
          contest.value.submission_count -= 1
        }
      } catch (error) {
        console.error('Failed to delete submission:', error)
        showAlert('Failed to delete submission: ' + error.message, 'danger')
      } finally {
        deletingSubmissionId.value = null
      }
    }

    // Watch for user changes and update permissions
    watch(() => currentUser.value, (newUser) => {
      if (newUser && contest.value && !checkingAuth.value) {
        setTimeout(() => {
          checkDeletePermission()
        }, 50)
      } else if (!newUser && contest.value) {
        canDeleteContest.value = false
      }
    }, { deep: true })

    // Edit form state
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

    onMounted(() => {
      loadContest()
      const modalEl = document.getElementById('editContestModal')
      if (modalEl) editModal = new bootstrap.Modal(modalEl)
    })

    // Check if username matches current user
    const isCurrentUser = (username) => {
      const currentUsername = currentUser.value?.username
      if (!currentUsername || !username) return false
      return String(currentUsername).trim().toLowerCase() ===
        String(username).trim().toLowerCase()
    }

    // Search jury members with debounce
    const searchJuryMembers = async () => {
      const query = jurySearchQuery.value.trim()

      if (query.length < 2) {
        jurySearchResults.value = []
        return
      }
      if (jurySearchTimeout) { clearTimeout(jurySearchTimeout) }
      // Debounce to avoid excessive API calls
      jurySearchTimeout = setTimeout(async () => {
        try {
          const response = await api.get(`/user/search?q=${encodeURIComponent(query)}&limit=10`)
          // Filter out already selected users
          jurySearchResults.value = (response.users || []).filter(
            user => !editForm.selectedJuryMembers.includes(user.username)
          )
        } catch (error) {
          console.error('Jury search error:', error)
          jurySearchResults.value = []
        }
      }, 300)
    }


    // Add jury member with self-selection warning
    const addJuryMember = (username) => {
      // Check if trying to add self
      if (isCurrentUser(username)) {
        // Show confirmation dialog before adding
        const confirmed = window.confirm(
          '⚠️ WARNING: Self-Selection as Jury Member\n\n' +
          'You are about to select yourself as a jury member.\n\n' +
          'It is strongly recommended to select other users as jury members to maintain fairness and objectivity.\n\n' +
          'Are you sure you want to proceed with selecting yourself?'
        )

        // If user cancels, don't add them
        if (!confirmed) {
          return
        }
      }

      // Add if not already in list
      if (!editForm.selectedJuryMembers.includes(username)) {
        editForm.selectedJuryMembers.push(username)
        jurySearchQuery.value = ''
        jurySearchResults.value = []
      }
    }

    // Remove jury member from selection
    const removeJuryMember = (username) => {
      editForm.selectedJuryMembers = editForm.selectedJuryMembers.filter(
        u => u !== username
      )
    }

    // Search organizers with debounce
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
          // Filter out already selected organizers and current user
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

    // Add organizer (prevent adding current user)
    const addOrganizer = (username) => {
      // Don't add current user (they're already creator)
      if (isCurrentUser(username)) {
        showAlert('You will be added automatically as contest creator', 'info')
        return
      }

      // Add the organizer if not already selected
      if (!editForm.selectedOrganizers.includes(username)) {
        editForm.selectedOrganizers.push(username)
        organizerSearchQuery.value = ''
        organizerSearchResults.value = []
      }
    }

    // Remove organizer from selection
    const removeOrganizer = (username) => {
      editForm.selectedOrganizers = editForm.selectedOrganizers.filter(
        u => u !== username
      )
    }

    // Add new category field
    const addCategory = () => {
      editForm.categories.push('')
    }

    // Remove category field if more than one exists
    const removeCategory = (index) => {
      if (editForm.categories.length > 1) {
        editForm.categories.splice(index, 1)
      }
    }

    const openEditModal = () => {
      if (!contest.value) return
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

      // Count reviewed submissions (accepted or rejected)
      const reviewedSubmissions = submissions.value.filter(
        s => s.status === 'accepted' || s.status === 'rejected'
      )
      reviewedSubmissionsCount.value = reviewedSubmissions.length
      scoringModeLocked.value = reviewedSubmissions.length > 0

      // This determines what the contest is CURRENTLY using
      if (contest.value.automated_settings?.enabled === true) {
        contestScoringMode.value = 'automated'
        console.log('[EDIT MODAL] Current scoring mode: AUTOMATED')
      } else if (contest.value.scoring_parameters?.enabled === true) {
        contestScoringMode.value = 'multi_parameter'
        console.log('[EDIT MODAL] Current scoring mode: MULTI-PARAMETER')
      } else {
        contestScoringMode.value = 'simple'
        console.log('[EDIT MODAL] Current scoring mode: SIMPLE')
      }

      if (contestScoringMode.value === 'automated') {
        // Contest is using automated scoring
        enableMultiParameterScoring.value = false

        // Load automated settings
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

        editForm.automated_settings = {
          enabled: true,
          eligibility: { ...automatedSettings.eligibility },
          evaluation: { ...automatedSettings.evaluation }
        }
      } else if (contestScoringMode.value === 'multi_parameter') {
        // Contest is using multi-parameter scoring
        enableMultiParameterScoring.value = true

        // Load multi-parameter values
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

        // Sync to editForm
        editForm.scoring_parameters = {
          enabled: true,
          max_score: maxScore.value,
          min_score: minScore.value,
          parameters: scoringParameters.value.map(p => ({ ...p }))
        }

        // Also sync simple values for consistency
        editForm.marks_setting_accepted = maxScore.value
        editForm.marks_setting_rejected = minScore.value
      } else {
        // Contest is using simple scoring
        enableMultiParameterScoring.value = false

        // Load simple scoring values
        editForm.marks_setting_accepted = Number(contest.value.marks_setting_accepted ?? 0)
        editForm.marks_setting_rejected = Number(contest.value.marks_setting_rejected ?? 0)

        // Reset multi-parameter values to defaults (not loaded from contest)
        maxScore.value = 10
        minScore.value = 0
        loadDefaultParameters()

        editForm.scoring_parameters = {
          enabled: false,
          max_score: 10,
          min_score: 0,
          parameters: []
        }
      }
      jurySearchQuery.value = ''
      jurySearchResults.value = []
      organizerSearchQuery.value = ''
      organizerSearchResults.value = []

      if (editModal) editModal.show()
    }


    const saveContestEdits = async () => {
      try {
        savingContest.value = true
        const validCategories = editForm.categories.filter(cat => cat && cat.trim())

        // Validate category URLs format (only if any are provided)
        for (const category of validCategories) {
          if (!category.startsWith('http://') && !category.startsWith('https://')) {
            showAlert('All category URLs must be valid HTTP/HTTPS URLs', 'warning')
            return
          }
        }

        let scoringParametersPayload = null
        let automatedSettingsPayload = null

        if (contestScoringMode.value === 'automated') {
          // Automated scoring is enabled
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
          // Multi-parameter scoring is enabled (either locked or unlocked)

          // Validate weights sum to 100
          if (totalWeight.value !== 100) {
            showAlert('Parameter weights must sum to 100%', 'warning')
            return
          }

          // Build clean payload
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
          // Simple scoring is enabled
          scoringParametersPayload = {
            enabled: false,
            max_score: Number(editForm.marks_setting_accepted),
            min_score: Number(editForm.marks_setting_rejected),
            parameters: []
          }

          console.log('[SAVE] Simple scoring payload:', scoringParametersPayload)
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
        editModal.hide()

        await loadContest(contest.value.id)
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

    // Check if user can review submissions (jury members only)
    const canUserReview = computed(() => {
      if (!isAuthenticated.value || !contest.value || !currentUser.value) {
        return false
      }

      const username = currentUser.value.username.trim().toLowerCase()

      if (Array.isArray(contest.value.jury_members)) {
        const jury = contest.value.jury_members
          .filter(Boolean)
          .map(j => String(j).trim().toLowerCase())

        if (jury.includes(username)) {
          return true
        }
      }

      return false
    })

    // Navigate to contest leaderboard
    const goToLeaderboard = () => {
      if (!contest.value) return

      router.push({
        name: 'ContestLeaderboard',
        params: { name: route.params.name }
      })
    }

    return {
      contest,
      loading,
      error,
      submissions,
      loadingSubmissions,
      deletingContest,
      canDeleteContest,
      checkingAuth,
      submittingToContestId,
      currentUser,
      isAuthenticated,
      canViewSubmissions,
      currentSubmission,
      deletingSubmissionId,
      formatDate,
      formatDateShort,
      formatByteCount,
      formatByteCountWithExact,
      getStatusLabel,
      formatWordCount,
      getStatusColor,
      getCategoryName,
      loadSubmissions,
      refreshMetadata,
      refreshingMetadata,
      handleDeleteContest,
      handleSubmitArticle,
      handleArticleSubmitted,
      forceAuthRefresh,
      jurySearchQuery,
      jurySearchResults,
      organizerSearchQuery,
      organizerSearchResults,
      searchJuryMembers,
      addJuryMember,
      removeJuryMember,
      searchOrganizers,
      addOrganizer,
      removeOrganizer,
      addCategory,
      removeCategory,
      isCurrentUser,
      goBack,
      goToLeaderboard,
      showArticlePreview,
      handleSubmissionReviewed,
      handleSubmissionDeleted,
      handleDeleteSubmission,
      previewArticleUrl,
      previewArticleTitle,
      editForm,
      openEditModal,
      saveContestEdits,
      canUserReview,
      enableMultiParameterScoring,
      maxScore,
      minScore,
      scoringParameters,
      totalWeight,
      weightTotalClass,
      addParameter,
      removeParameter,
      loadDefaultParameters,
      savingContest,
      scoringModeLocked,
      reviewedSubmissionsCount,
      contestScoringMode,
      automatedSettings,
      loadDefaultAutomatedSettings,
      // Category crawler
      selectedCategory,
      crawlLimit,
      crawling,
      crawlResult,
      crawlError,
      crawlCategory,
      canImportArticles,
      // Evaluation details modal
      showEvaluationDetails,
      selectedEvaluationSubmission,
      // Submission filter tabs
      submissionFilter,
      filteredSubmissions,
    }
  }
}
</script>


<style scoped>
/* --------------------------------------------------------------------------
   Main Container & Layout
   -------------------------------------------------------------------------- */
.contest-view {
  max-width: 1200px;
  margin: 0 auto;
}

/* --------------------------------------------------------------------------
   Header Section
   -------------------------------------------------------------------------- */
.contest-header-section {
  border-bottom: 2px solid var(--wiki-primary);
  padding-bottom: 1rem;
}

.contest-title {
  color: var(--wiki-dark);
  font-weight: 700;
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
  transition: color 0.3s ease;
}

[data-theme="dark"] .contest-title {
  color: #ffffff !important;
}

.contest-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

/* --------------------------------------------------------------------------
   Cards & Content Containers
   -------------------------------------------------------------------------- */
.card {
  border: 1px solid var(--wiki-border);
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.2s ease;
}

[data-theme="dark"] .card {
  background-color: #2a2a2a;
  border-color: #444;
}

.card:hover {
  box-shadow: 0 4px 8px rgba(0, 102, 153, 0.15);
}

.card-header {
  background-color: var(--wiki-primary);
  color: white;
  border-bottom: none;
  padding: 1rem 1.5rem;
  font-weight: 600;
}

.card-body {
  padding: 1.5rem;
  color: var(--wiki-dark);
}

.card-body p {
  margin-bottom: 0.75rem;
  color: var(--wiki-text);
}

[data-theme="dark"] .card-body strong {
  color: #ffffff;
}

/* --------------------------------------------------------------------------
   Badges
   -------------------------------------------------------------------------- */
.badge {
  font-weight: 500;
  padding: 0.4em 0.8em;
  font-size: 0.85em;
}

.badge.bg-primary {
  background-color: var(--wiki-primary) !important;
}

.badge.bg-info {
  background-color: var(--wiki-primary) !important;
  color: white;
}

/* --------------------------------------------------------------------------
   Tables
   -------------------------------------------------------------------------- */
.table {
  margin-top: 0;
}

.table thead th {
  background-color: rgba(0, 102, 153, 0.1);
  color: var(--wiki-primary);
  font-weight: 600;
  border-bottom: 2px solid var(--wiki-primary);
  padding: 0.75rem;
}

[data-theme="dark"] .table thead th {
  background-color: rgba(93, 184, 230, 0.15);
  border-bottom-color: var(--wiki-primary);
}

.table tbody td {
  padding: 0.75rem;
  vertical-align: middle;
  color: var(--wiki-text);
}

.table tbody tr:hover {
  background-color: var(--wiki-hover-bg);
}

.table a {
  color: var(--wiki-primary);
  font-weight: 500;
  transition: color 0.2s ease;
}

.table a:hover {
  color: var(--wiki-primary-hover);
  text-decoration: underline;
}

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

/* --------------------------------------------------------------------------
   Buttons
   -------------------------------------------------------------------------- */
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

[data-theme="dark"] .btn-danger {
  background-color: #990000;
  border-color: #990000;
}

[data-theme="dark"] .btn-danger:hover {
  background-color: #7a0000;
  border-color: #7a0000;
}

.btn-outline-secondary {
  border-color: var(--wiki-text-muted);
  color: var(--wiki-text-muted);
  transition: all 0.2s ease;
}

.btn-outline-secondary:hover {
  background-color: var(--wiki-text-muted);
  border-color: var(--wiki-text-muted);
  color: white;
}

/* --------------------------------------------------------------------------
   Alerts
   -------------------------------------------------------------------------- */
.alert {
  border-radius: 0.5rem;
  border-left: 4px solid;
  padding: 0.75rem 1rem;
}

.alert-info {
  background-color: rgba(0, 102, 153, 0.1);
  border-color: var(--wiki-primary);
  color: var(--wiki-primary);
}

[data-theme="dark"] .alert-info {
  background-color: rgba(93, 184, 230, 0.2);
  border-color: var(--wiki-primary);
  color: var(--wiki-primary);
}

.alert-danger {
  background-color: rgba(153, 0, 0, 0.1);
  border-color: var(--wiki-danger);
  color: var(--wiki-danger);
}

.alert-warning {
  background-color: rgba(153, 0, 0, 0.1);
  border-color: var(--wiki-danger);
  color: var(--wiki-danger);
}

/* --------------------------------------------------------------------------
   Loading Spinners
   -------------------------------------------------------------------------- */
.spinner-border.text-primary {
  color: var(--wiki-primary) !important;
  width: 3rem;
  height: 3rem;
  border-width: 0.3em;
}

/* --------------------------------------------------------------------------
   Description Section
   -------------------------------------------------------------------------- */
.description-section {
  margin-top: 0;
}

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

/* --------------------------------------------------------------------------
   Autocomplete Components
   -------------------------------------------------------------------------- */
.jury-autocomplete,
.organizer-autocomplete {
  border: 1px solid var(--wiki-border);
  border-top: none;
  border-radius: 0 0 4px 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  background-color: var(--wiki-card-bg);
  z-index: 1060;
  transition: background-color 0.2s ease;
}

[data-theme="dark"] .jury-autocomplete,
[data-theme="dark"] .organizer-autocomplete {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.jury-autocomplete .p-2,
.organizer-autocomplete .p-2 {
  transition: background-color 0.2s ease;
  color: var(--wiki-text);
}

.jury-autocomplete .p-2:hover,
.organizer-autocomplete .p-2:hover {
  background-color: var(--wiki-hover-bg) !important;
}

.jury-autocomplete .bg-warning-subtle,
.organizer-autocomplete .bg-warning-subtle {
  background-color: rgba(255, 193, 7, 0.25) !important;
  border-left: 4px solid #ffc107;
}

[data-theme="dark"] .jury-autocomplete .bg-warning-subtle,
[data-theme="dark"] .organizer-autocomplete .bg-warning-subtle {
  background-color: rgba(255, 193, 7, 0.35) !important;
}

.self-warning-badge {
  background-color: #ffc107;
  color: #000;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}

[data-theme="dark"] .self-warning-badge {
  background-color: #ff9800;
  color: #fff;
}

.jury-autocomplete .text-primary,
.organizer-autocomplete .text-primary {
  color: var(--wiki-primary) !important;
}

/* --------------------------------------------------------------------------
   Organizers & Jury Display
   -------------------------------------------------------------------------- */
.organizers-flex {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.organizer-chip {
  display: flex;
  align-items: center;
  padding: 0.50rem 1rem;
  background-color: var(--wiki-primary);
  color: white;
  border-radius: 8px;
  font-size: 0.95rem;
  transition: all 0.2s ease;
  position: relative;
}

.organizer-chip:hover {
  background-color: var(--wiki-primary);
  transform: translateY(-2px);
}

[data-theme="dark"] .organizer-chip {
  background-color: var(--wiki-primary);
}

[data-theme="dark"] .organizer-chip:hover {
  background-color: var(--wiki-primary);
}

/* Selection boxes for organizers/jury in edit modal */
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

/* --------------------------------------------------------------------------
   Scoring System Display (View Mode)
   -------------------------------------------------------------------------- */
.scoring-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 1.5rem;
}

[data-theme="dark"] .scoring-card {
  background: #2a2a2a;
  border-color: #404040;
}

.scoring-content {
  padding: 1.25rem;
}

.scoring-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.max-points {
  color: var(--wiki-primary);
  font-weight: 600;
  font-size: 0.9375rem;
}

.params-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.param-item {
  padding: 0.5rem;
  background: #f9fafb;
  border-radius: 6px;
  border: 1px solid var(--wiki-primary);
}

[data-theme="dark"] .param-item {
  background: #1f1f1f;
}

.param-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.375rem;
}

.param-label {
  font-weight: 600;
  font-size: 0.9375rem;
}

.param-value {
  background: var(--wiki-primary);
  color: white;
  padding: 0.25rem 0.625rem;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.8125rem;
}

.param-note {
  color: #6b7280;
  font-size: 0.8125rem;
  line-height: 1.4;
  margin: 0;
}

[data-theme="dark"] .param-note {
  color: #9ca3af;
}

.info-note {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: #eff6ff;
  border-radius: 4px;
  font-size: 0.8125rem;
  color: #1e40af;
}

[data-theme="dark"] .info-note {
  background: rgba(59, 130, 246, 0.15);
  color: #93c5fd;
}

.info-note i {
  font-size: 0.9375em;
}

/* Automated Scoring Display Styles */
.automated-header {
  display: flex;
  align-items: center;
  margin-bottom: 1.25rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid var(--wiki-border);
  font-size: 1.125rem;
  color: var(--wiki-primary);
}

.automated-section {
  margin-bottom: 1.25rem;
}

.automated-section .section-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--wiki-text);
  margin-bottom: 0.75rem;
}

.criteria-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.75rem;
}

.criteria-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.625rem 0.875rem;
  background: #f3f4f6;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

[data-theme="dark"] .criteria-item {
  background: #1f1f1f;
  border-color: #404040;
}

.criteria-label {
  font-size: 0.875rem;
  color: #6b7280;
}

[data-theme="dark"] .criteria-label {
  color: #9ca3af;
}

.criteria-value {
  font-weight: 600;
  color: var(--wiki-primary);
  font-size: 0.9375rem;
}

.points-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 0.5rem;
}

.point-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.5rem 0.625rem;
  background: rgba(13, 202, 240, 0.1);
  border-radius: 6px;
  border: 1px solid rgba(13, 202, 240, 0.3);
}

[data-theme="dark"] .point-chip {
  background: rgba(13, 202, 240, 0.15);
  border-color: rgba(13, 202, 240, 0.4);
}

.chip-label {
  font-size: 0.75rem;
  color: #6b7280;
  text-align: center;
}

[data-theme="dark"] .chip-label {
  color: #9ca3af;
}

.chip-value {
  font-weight: 600;
  color: #0dcaf0;
  font-size: 0.9375rem;
}

[data-theme="dark"] .chip-value {
  color: #5bc8e6;
}

.points-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.point-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background: #f9fafb;
  border-radius: 6px;
  border: 2px solid var(--wiki-border);
}

[data-theme="dark"] .point-item {
  background: #1f1f1f;
}

.point-label {
  font-weight: 500;
  color: #6b7280;
  font-size: 15px;
}

.point-value {
  font-weight: 700;
  font-size: 1.25rem;
  color: var(--wiki-primary);
}

/* Category Crawler Styles */
.crawler-section {
  margin-top: 1.5rem;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

[data-theme="dark"] .crawler-section {
  background: #1a1a2e;
  border-color: #334155;
}

.crawler-section .section-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--wiki-text);
  margin-bottom: 0.75rem;
}

.crawler-form {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.crawler-select {
  flex: 1;
  min-width: 280px;
  padding: 0.625rem 0.875rem;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  font-size: 0.875rem;
}

[data-theme="dark"] .crawler-select {
  background: #1f1f1f;
  border-color: #404040;
  color: #e5e7eb;
}

.crawler-input {
  flex: 1;
  min-width: 280px;
  padding: 0.625rem 0.875rem;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  font-size: 0.875rem;
}

[data-theme="dark"] .crawler-input {
  background: #1f1f1f;
  border-color: #404040;
  color: #e5e7eb;
}

.crawler-limit {
  width: 100px;
  padding: 0.625rem 0.875rem;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  font-size: 0.875rem;
}

[data-theme="dark"] .crawler-limit {
  background: #1f1f1f;
  border-color: #404040;
  color: #e5e7eb;
}

.crawler-btn {
  padding: 0.625rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  white-space: nowrap;
}

.crawler-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.crawl-result {
  margin-top: 1rem;
}

.crawl-result .alert {
  margin-bottom: 0;
  font-size: 0.875rem;
}

/* --------------------------------------------------------------------------
   Modal Structure
   -------------------------------------------------------------------------- */
.modal-fullscreen {
  width: 100vw;
  max-width: 100%;
  height: 100vh;
  margin: 0;
  padding: 0;
}

.modal-fullscreen .modal-content {
  height: 100vh;
  border: 0;
  border-radius: 0;
  display: flex;
  flex-direction: column;
}

.modal-fullscreen .modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}


.modal-fullscreen .modal-body form {
  max-width: 1200px;
  margin: 0 auto;
}

/* --------------------------------------------------------------------------
   Edit Section Containers
   -------------------------------------------------------------------------- */
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

/* Specific styling for scoring section */
.scoring-section-edit {
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
  border: 2px solid var(--wiki-primary);
}

[data-theme="dark"] .scoring-section-edit {
  background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
  border-color: var(--wiki-primary);
}

/* --------------------------------------------------------------------------
   Lock Status Banner
   -------------------------------------------------------------------------- */
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

/* Locked state styling */
.lock-banner.locked {
  background: linear-gradient(135deg, #fff3cd 0%, #fffbf0 100%);
  border-color: #ffc107;
  box-shadow: 0 2px 8px rgba(255, 193, 7, 0.2);
}

[data-theme="dark"] .lock-banner.locked {
  background: linear-gradient(135deg, rgba(255, 193, 7, 0.15) 0%, rgba(255, 193, 7, 0.05) 100%);
  border-color: #ff9800;
}

/* Unlocked state styling */
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

/* --------------------------------------------------------------------------
   Current Scoring Mode Display
   -------------------------------------------------------------------------- */
.current-scoring-mode {
  padding: 0.75rem;
  background: #f9fafb;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

[data-theme="dark"] .current-scoring-mode {
  background: #1f1f1f;
  border-color: #404040;
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

/* --------------------------------------------------------------------------
   Locked Edit Info
   -------------------------------------------------------------------------- */
.locked-edit-info {
  margin-top: 1rem;
}

.locked-edit-info .alert {
  margin-bottom: 1.5rem;
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

/* --------------------------------------------------------------------------
   Unlocked Edit Mode
   -------------------------------------------------------------------------- */
.unlocked-edit-mode {
  margin-top: 1rem;
}

/* Scoring mode toggle switch */
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

.form-check{
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

.form-check-label {
  cursor: pointer;
  user-select: none;
  margin-left: 5px;
}

/* --------------------------------------------------------------------------
   Simple Scoring Form
   -------------------------------------------------------------------------- */
.simple-scoring-form .alert {
  border-left: 4px solid #17a2b8;
  background: rgba(23, 162, 184, 0.1);
  color: #0c5460;
}

[data-theme="dark"] .simple-scoring-form .alert {
  background: rgba(23, 162, 184, 0.15);
  color: #5db8e6;
}

/* --------------------------------------------------------------------------
   Multi-Parameter Scoring Form
   -------------------------------------------------------------------------- */
.multi-param-scoring-form .alert {
  border-left: 4px solid #28a745;
  background: rgba(40, 167, 69, 0.1);
  color: #155724;
}

[data-theme="dark"] .multi-param-scoring-form .alert {
  background: rgba(40, 167, 69, 0.15);
  color: #4ade80;
}

/* Parameters list container */
.parameters-list {
  margin-top: 0.5rem;
}

.parameter-item {
  transition: all 0.2s ease;
}

.parameter-item:hover {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  transform: translateY(-1px);
}

/* Weight validation styling */
.bg-success-subtle {
  background-color: rgba(40, 167, 69, 0.1) !important;
  border: 2px solid #28a745 !important;
}

[data-theme="dark"] .bg-success-subtle {
  background-color: rgba(40, 167, 69, 0.15) !important;
  border-color: #4ade80 !important;
}

.bg-danger-subtle {
  background-color: rgba(220, 53, 69, 0.1) !important;
  border: 2px solid #dc3545 !important;
}

[data-theme="dark"] .bg-danger-subtle {
  background-color: rgba(220, 53, 69, 0.15) !important;
  border-color: #f87171 !important;
}

/* --------------------------------------------------------------------------
   Responsive Adjustments
   -------------------------------------------------------------------------- */
@media (max-width: 768px) {
  .contest-title {
    font-size: 2rem;
  }

  .card-body {
    padding: 1rem;
  }

  .table {
    font-size: 0.9rem;
  }

  .table thead th,
  .table tbody td {
    padding: 0.5rem;
  }

  .organizers-flex {
    gap: 0.5rem;
  }

  .organizer-chip {
    padding: 0.5rem 0.75rem;
    font-size: 0.85rem;
  }

  .edit-section {
    padding: 1rem;
  }

  .lock-banner {
    flex-direction: column;
    text-align: center;
  }

  .lock-banner-icon {
    margin: 0 auto;
  }

  .modal-fullscreen .modal-body {
    padding: 1rem;
  }
}

@media (max-width: 640px) {
  .scoring-meta {
    flex-direction: column;
    align-items: flex-start;
  }

  .points-row {
    grid-template-columns: 1fr;
  }

  .parameter-item .row {
    gap: 0.75rem;
  }

  .parameter-item .col-md-1 {
    text-align: left !important;
  }
}
</style>
