<template>
  <!-- Modal for displaying jury feedback on submissions -->
  <div class="modal fade"
id="juryFeedbackModal"
tabindex="-1"
aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-lg">
      <div class="modal-content">
        <!-- Modal header with Wikipedia blue background -->
        <div class="modal-header">
          <h5 class="modal-title">
            <i class="fas fa-comment-dots me-2"></i>Jury Feedback
          </h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <!-- Loading state while fetching reviewer data -->
          <div v-if="loadingReviewer" class="text-center py-3">
            <div class="spinner-border spinner-border-sm text-primary" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
          </div>

          <!-- Display feedback if submission has been reviewed -->
          <div v-else-if="submission && submission.reviewed_at">
            <!-- Review status section with color-coded badge -->
            <div class="feedback-section mb-4">
              <h6 class="feedback-section-title">
                <i class="fas fa-check-circle me-2"></i>Review Status
              </h6>
              <div class="feedback-content">
                <span class="status-badge" :class="getStatusClass(submission.status)">
                  {{ getStatusLabel(submission.status) }}
                </span>
              </div>
            </div>

            <!-- Total score awarded to submission -->
            <div class="feedback-section mb-4">
              <h6 class="feedback-section-title">
                <i class="fas fa-star me-2"></i>Marks Awarded
              </h6>
              <div class="feedback-content">
                <div class="marks-display">
                  <span class="total-marks">{{ submission.score || 0 }}</span>
                  <span class="marks-label">points</span>
                </div>
              </div>
            </div>

            <!-- Individual parameter scores with progress bars -->
            <div v-if="submission.parameter_scores" class="feedback-section mb-4">
              <h6 class="feedback-section-title">
                <i class="fas fa-chart-bar me-2"></i>Parameter Scores
              </h6>
              <div class="feedback-content">
                <div class="parameter-scores-grid">
                  <div v-for="(score, paramName) in submission.parameter_scores"
:key="paramName"
                    class="parameter-score-item">
                    <div class="parameter-name">{{ paramName }}</div>
                    <div class="parameter-score">
                      <!-- Visual progress bar for parameter score -->
                      <div class="score-bar-container">
                        <div class="score-bar" :style="{ width: (score * 10) + '%' }"></div>
                      </div>
                      <span class="score-value">{{ score }}/10</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Display jury comments if provided -->
            <div v-if="submission.review_comment" class="feedback-section mb-4">
              <h6 class="feedback-section-title">
                <i class="fas fa-comment me-2"></i>Jury Comments
              </h6>
              <div class="feedback-content">
                <div class="comment-box">
                  {{ submission.review_comment }}
                </div>
              </div>
            </div>

            <!-- Show message when no comments were provided -->
            <div v-else class="feedback-section mb-4">
              <h6 class="feedback-section-title">
                <i class="fas fa-comment me-2"></i>Jury Comments
              </h6>
              <div class="feedback-content">
                <p class="text-muted mb-0">
                  <i class="fas fa-info-circle me-2"></i>
                  No comments provided by the reviewer.
                </p>
              </div>
            </div>
          </div>

          <!-- Empty state when submission hasn't been reviewed yet -->
          <div v-else class="text-center py-4">
            <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
            <p class="text-muted">No feedback available yet.</p>
          </div>
        </div>
        <!-- Modal footer with close button -->
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
            <i class="fas fa-times me-2"></i>Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'JuryFeedbackModal',
  props: {
    submission: {
      type: Object,
      required: true
    },
    reviewerName: {
      type: String,
      default: 'Jury Member'
    },
    loadingReviewer: {
      type: Boolean,
      default: false
    }
  },

  setup() {
    // Format date to IST timezone with full date and time
    const formatDate = (dateString) => {
      if (!dateString) return 'No date'
      try {
        let utcDateString = dateString
        // Append 'Z' if timezone is not specified in date string
        if (!dateString.endsWith('Z') && !dateString.includes('+') && !dateString.includes('-', 10)) {
          utcDateString = dateString + 'Z'
        }

        // Convert to IST with formatted output
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

    // Get human-readable label for submission status
    const getStatusLabel = (status) => {
      const labels = {
        accepted: 'Accepted',
        rejected: 'Rejected',
        pending: 'Pending Review'
      }
      return labels[status?.toLowerCase()] || status || 'Unknown'
    }

    // Get CSS class for status badge color coding
    const getStatusClass = (status) => {
      const classes = {
        accepted: 'status-accepted',
        rejected: 'status-rejected',
        pending: 'status-pending'
      }
      return classes[status?.toLowerCase()] || 'status-unknown'
    }

    return {
      formatDate,
      getStatusLabel,
      getStatusClass
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

/* Modal title styling */
.modal-title {
  font-weight: 600;
  font-size: 1.5rem;
  color: white;
}

/* Close button with inverted colors for visibility */
.modal-header .btn-close {
  filter: invert(1) brightness(1.2);
  opacity: 0.9;
  transition: opacity 0.2s ease;
}

.modal-header .btn-close:hover {
  opacity: 1;
}

/* Modal body with theme-aware background */
.modal-body {
  padding: 2rem 1.5rem;
  background-color: var(--wiki-modal-bg);
  color: var(--wiki-text);
  min-height: 300px;
}

/* Empty state padding override */
.text-center.py-4 {
  padding: 3rem 1rem !important;
}

/* Empty state icon styling */
.text-center .fa-inbox {
  color: var(--wiki-text-muted);
  opacity: 0.5;
}

/* Dark mode: dimmer empty state icon */
[data-theme="dark"] .text-center .fa-inbox {
  opacity: 0.3;
}

/* Empty state text */
.text-center .text-muted {
  color: var(--wiki-text-muted);
  font-size: 1rem;
}

/* Dark mode: lighter muted text */
[data-theme="dark"] .text-center .text-muted {
  color: #b8b8b8;
}

/* Individual feedback section with bottom border */
.feedback-section {
  border-bottom: 1px solid var(--wiki-border);
  padding-bottom: 1.5rem;
  margin-bottom: 0;
}

/* Remove border from last section */
.feedback-section:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

/* Spacing between consecutive sections */
.feedback-section+.feedback-section {
  margin-top: 1.5rem;
}

/* Section title with icon and uppercase styling */
.feedback-section-title {
  color: var(--wiki-primary);
  font-weight: 600;
  font-size: 0.95rem;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Dark mode: lighter blue for section titles */
[data-theme="dark"] .feedback-section-title {
  color: #5db8e6;
}

/* Content area with left padding for hierarchy */
.feedback-content {
  padding-left: 1.75rem;
}

/* Status badge with rounded corners and uppercase text */
.status-badge {
  display: inline-block;
  padding: 0.5rem 1.25rem;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.95rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: all 0.2s ease;
}

/* Accepted status: green background */
.status-accepted {
  background-color: var(--wiki-success);
  color: white;
  border: none;
}

/* Rejected status: red background */
.status-rejected {
  background-color: var(--wiki-danger);
  color: white;
  border: none;
}

/* Pending status: orange background with dark text */
.status-pending {
  background-color: var(--wiki-warning);
  color: #000000;
  border: none;
}

/* Dark mode: maintain original green for accepted */
[data-theme="dark"] .status-accepted {
  background-color: #339966 !important;
  color: #ffffff !important;
}

/* Dark mode: maintain MediaWiki red for rejected */
[data-theme="dark"] .status-rejected {
  background-color: #990000 !important;
  color: #ffffff !important;
}

/* Dark mode: maintain orange for pending */
[data-theme="dark"] .status-pending {
  background-color: #ffc107 !important;
  color: #000000 !important;
}

/* Reviewer information container with hover effect */
.reviewer-info {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 1rem;
  background-color: var(--wiki-light-bg);
  border-radius: 4px;
  border: 1px solid var(--wiki-border);
  transition: all 0.2s ease;
}

/* Highlight border on hover */
.reviewer-info:hover {
  border-color: var(--wiki-primary);
}

/* Dark mode: subtle blue tint background */
[data-theme="dark"] .reviewer-info {
  background-color: rgba(93, 184, 230, 0.05);
}

/* Reviewer name with prominent styling */
.reviewer-name {
  font-weight: 600;
  font-size: 1.1rem;
  color: var(--wiki-dark);
}

/* Dark mode: white reviewer name */
[data-theme="dark"] .reviewer-name {
  color: #ffffff;
}

/* Review date with smaller, muted styling */
.review-date {
  font-size: 0.9rem;
  color: var(--wiki-text-muted);
}

/* Dark mode: lighter date text */
[data-theme="dark"] .review-date {
  color: #b8b8b8;
}

/* Large marks display with baseline alignment */
.marks-display {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  width: fit-content;
  transition: all 0.2s ease;
}

/* Dark mode: shadow on marks display hover */
[data-theme="dark"] .marks-display:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

/* Large numeric score display */
.total-marks {
  font-size: 3.5rem;
  font-weight: 700;
  color: var(--wiki-primary);
  line-height: 1;
}

/* Dark mode: lighter blue for marks */
[data-theme="dark"] .total-marks {
  color: #5db8e6;
}

/* Points label next to score */
.marks-label {
  font-size: 1.25rem;
  color: var(--wiki-text-muted);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Vertical layout for parameter scores */
.parameter-scores-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* Individual parameter score item with hover effect */
.parameter-score-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  background-color: var(--wiki-light-bg);
  border-radius: 4px;
  border: 1px solid var(--wiki-border);
  transition: all 0.2s ease;
}

/* Highlight and shadow on hover */
.parameter-score-item:hover {
  border-color: var(--wiki-primary);
  box-shadow: 0 2px 4px rgba(0, 102, 153, 0.1);
}

/* Dark mode: subtle background for parameter items */
[data-theme="dark"] .parameter-score-item {
  background-color: rgba(93, 184, 230, 0.05);
}

/* Dark mode: stronger shadow on hover */
[data-theme="dark"] .parameter-score-item:hover {
  border-color: var(--wiki-primary);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

/* Parameter name with fixed minimum width */
.parameter-name {
  font-weight: 600;
  color: var(--wiki-dark);
  min-width: 150px;
  font-size: 0.95rem;
}

/* Dark mode: white parameter names */
[data-theme="dark"] .parameter-name {
  color: #ffffff;
}

/* Score display with progress bar and value */
.parameter-score {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: 1;
}

/* Progress bar container with rounded corners */
.score-bar-container {
  flex: 1;
  height: 10px;
  background-color: #e9ecef;
  border-radius: 10px;
  overflow: hidden;
  max-width: 200px;
}

/* Dark mode: darker progress bar background */
[data-theme="dark"] .score-bar-container {
  background-color: #3a3a3a;
}

/* Filled portion of progress bar with gradient */
.score-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--wiki-primary) 0%, #5db8e6 100%);
  transition: width 0.5s ease;
  border-radius: 10px;
}

/* Numeric score value next to progress bar */
.score-value {
  font-weight: 600;
  color: var(--wiki-primary);
  min-width: 50px;
  text-align: right;
  font-size: 0.9rem;
}

/* Dark mode: lighter blue for score value */
[data-theme="dark"] .score-value {
  color: #5db8e6;
}

/* Comment box with left border accent */
.comment-box {
  background-color: var(--wiki-light-bg);
  border: 1px solid var(--wiki-border);
  border-left: 4px solid var(--wiki-primary);
  border-radius: 4px;
  padding: 1.25rem;
  color: var(--wiki-text);
  line-height: 1.7;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 0.95rem;
  transition: all 0.2s ease;
}

/* Shadow on comment box hover */
.comment-box:hover {
  box-shadow: 0 2px 4px rgba(0, 102, 153, 0.1);
}

/* Dark mode: subtle background for comment box */
[data-theme="dark"] .comment-box {
  background-color: rgba(93, 184, 230, 0.05);
}

/* Dark mode: stronger shadow on hover */
[data-theme="dark"] .comment-box:hover {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

/* Modal footer with theme-aware border */
.modal-footer {
  border-top: 1px solid var(--wiki-border);
  padding: 1rem 1.5rem;
  background-color: var(--wiki-modal-bg);
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

/* Secondary button with gray styling */
.btn-secondary {
  background-color: var(--wiki-text-muted);
  border-color: var(--wiki-text-muted);
  transition: all 0.2s ease;
  font-weight: 500;
}

/* Button hover with lift effect */
.btn-secondary:hover {
  background-color: var(--wiki-text-muted);
  border-color: var(--wiki-text-muted);
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* Dark mode: darker gray for secondary button */
[data-theme="dark"] .btn-secondary {
  background-color: #5a6268;
  border-color: #5a6268;
}

[data-theme="dark"] .btn-secondary:hover {
  background-color: #6c757d;
  border-color: #6c757d;
}

/* Small spinner for loading state */
.spinner-border-sm {
  width: 1.5rem;
  height: 1.5rem;
  border-width: 0.2em;
}

/* Mobile responsive adjustments */
@media (max-width: 768px) {

  /* Reduce padding on mobile */
  .modal-body {
    padding: 1rem;
  }

  /* Reduce content padding */
  .feedback-content {
    padding-left: 1rem;
  }

  /* Smaller marks on mobile */
  .total-marks {
    font-size: 2.5rem;
  }

  /* Smaller label on mobile */
  .marks-label {
    font-size: 1rem;
  }

  /* Stack reviewer info vertically */
  .reviewer-info {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  /* Remove left margin on mobile */
  .review-date {
    margin-left: 0 !important;
  }

  /* Stack parameter score items vertically */
  .parameter-score-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  /* Remove minimum width on mobile */
  .parameter-name {
    min-width: auto;
  }

  /* Full width score display */
  .parameter-score {
    width: 100%;
  }

  /* Full width progress bar on mobile */
  .score-bar-container {
    max-width: 100%;
  }
}
</style>
