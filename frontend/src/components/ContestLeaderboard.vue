<template>
    <div class="container py-5">
        <!-- Header with Back Button -->
        <div class="mb-4 d-flex justify-content-between align-items-center">
            <!-- Back button to return to contest details -->
            <button class="btn btn-outline-secondary" @click="goBack">
                <i class="fas fa-arrow-left me-2"></i>Back to Contest
            </button>

            <button v-if="!loading" class="btn btn-primary" @click="refreshLeaderboard" :disabled="refreshing">
                <span v-if="refreshing" class="spinner-border spinner-border-sm me-2"></span>
                <i v-else class="fas fa-sync-alt me-2"></i>
                {{ refreshing ? 'Refreshing...' : 'Refresh' }}
            </button>
        </div>

        <!-- Loading State -->
        <div v-if="loading" class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3 text-muted">Loading leaderboard...</p>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="alert alert-danger">
            <i class="fas fa-exclamation-circle me-2"></i>{{ error }}
            <button class="btn btn-sm btn-outline-danger ms-3" @click="goBack">
                Go Back
            </button>
        </div>

        <!-- Leaderboard Content -->
        <div v-else-if="contest" class="leaderboard-view">
            <!-- Contest Header -->
            <div class="contest-header-section mb-4">
                <h1 class="contest-title">
                    <i class="fas fa-trophy me-3 trophy-icon"></i>{{ contest.name }}
                </h1>
                <div class="contest-meta">
                    <span class="badge bg-primary me-2">Leaderboard</span>
                    <span class="badge" :class="getStatusBadgeClass(contest.status)">
                        {{ getStatusLabel(contest.status) }}
                    </span>
                </div>
            </div>

            <!-- Empty State -->
            <div v-if="sortedLeaderboard.length === 0" class="card empty-state-card">
                <div class="card-body text-center py-5">
                    <i class="fas fa-trophy empty-state-icon mb-3"></i>
                    <h4 class="mb-3">No participants found</h4>
                    <p class="text-muted mb-0">No submissions have been made to this contest yet</p>
                </div>
            </div>

            <!-- Leaderboard Table -->
            <div v-else class="card leaderboard-card">
                <div class="card-header">
                    <div class="d-flex justify-content-between align-items-center">
                        <h5 class="mb-0">
                            <i class="fas fa-list me-2"></i>Participants
                        </h5>
                        <span class="badge bg-secondary">{{ pagination.total_results }} participants</span>
                    </div>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover mb-0 leaderboard-table">
                            <thead>
                                <tr>
                                    <th>Username</th>
                                    <th class="text-center">Submissions</th>
                                    <th class="text-center">Total Marks</th>
                                    <th class="text-center">Reviewed</th>
                                    <th class="text-center">Pending</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="participant in sortedLeaderboard" :key="participant.user_id">
                                    <td>
                                        <div class="username-cell">
                                            <i class="fas fa-user me-2 text-muted"></i>
                                            <strong>{{ participant.username }}</strong>
                                        </div>
                                    </td>
                                    <td class="text-center">
                                        <span class="badge bg-light text-dark submissions-badge">
                                            {{ participant.total_submissions }}
                                        </span>
                                    </td>
                                    <td class="text-center">
                                        <strong class="marks-highlight">{{ participant.total_marks }}</strong>
                                    </td>
                                    <td class="text-center">
                                        <span class="badge bg-success">{{ participant.reviewed_count }}</span>
                                    </td>
                                    <td class="text-center">
                                        <span class="badge bg-warning text-dark">{{ participant.pending_count }}</span>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Pagination -->
            <div v-if="pagination.total_pages > 1" class="d-flex justify-content-center mt-4">
                <nav>
                    <ul class="pagination">
                        <li class="page-item" :class="{ disabled: pagination.page === 1 }">
                            <button class="page-link" @click="changePage(pagination.page - 1)"
                                :disabled="pagination.page === 1">
                                <i class="fas fa-chevron-left"></i>
                            </button>
                        </li>
                        <li v-for="page in visiblePages" :key="page" class="page-item"
                            :class="{ active: page === pagination.page }">
                            <button class="page-link" @click="changePage(page)">{{ page }}</button>
                        </li>
                        <li class="page-item" :class="{ disabled: pagination.page === pagination.total_pages }">
                            <button class="page-link" @click="changePage(pagination.page + 1)"
                                :disabled="pagination.page === pagination.total_pages">
                                <i class="fas fa-chevron-right"></i>
                            </button>
                        </li>
                    </ul>
                </nav>
            </div>
        </div>
    </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '../services/api'

export default {
    name: 'ContestLeaderboard',

    setup() {
        const router = useRouter()
        const route = useRoute()

        const contest = ref(null)
        const contestStats = ref({
            total_submissions: 0,
            total_reviewed: 0,
            total_pending: 0,
            total_marks_awarded: 0
        })
        const leaderboard = ref([])
        const loading = ref(true)
        const refreshing = ref(false)
        const error = ref(null)

        const pagination = ref({
            page: 1,
            per_page: 50,
            total_pages: 1,
            total_results: 0
        })

        // Alphabetically sorted computed property — updates automatically when leaderboard data changes
        const sortedLeaderboard = computed(() =>
            [...leaderboard.value].sort((a, b) =>
                a.username.localeCompare(b.username, undefined, { sensitivity: 'base' })
            )
        )

        const getContestId = async () => {
            const contestName = route.params.name
            const contestData = await api.get(`/contest/name/${contestName}`)
            return contestData.id
        }

        const loadLeaderboard = async (showLoading = true) => {
            if (showLoading) loading.value = true
            else refreshing.value = true
            error.value = null

            try {
                const contestId = await getContestId()

                const params = {
                    page: pagination.value.page,
                    per_page: pagination.value.per_page
                }

                const data = await api.get(`/contest/${contestId}/leaderboard`, { params })

                contest.value = data.contest
                contestStats.value = data.contest_stats
                leaderboard.value = data.leaderboard
                pagination.value = data.pagination
            } catch (err) {
                console.error('Error loading leaderboard:', err)
                error.value = 'Failed to load leaderboard: ' + (err.message || 'Unknown error')
            } finally {
                loading.value = false
                refreshing.value = false
            }
        }

        const refreshLeaderboard = () => loadLeaderboard(false)

        const changePage = (page) => {
            if (page < 1 || page > pagination.value.total_pages) return
            pagination.value.page = page
            loadLeaderboard(false)
            window.scrollTo({ top: 0, behavior: 'smooth' })
        }

        const visiblePages = computed(() => {
            const total = pagination.value.total_pages
            const current = pagination.value.page
            const delta = 2
            const pages = []
            for (let i = Math.max(1, current - delta); i <= Math.min(total, current + delta); i++) {
                pages.push(i)
            }
            return pages
        })

        const getStatusLabel = (status) => {
            const labels = { current: 'Active', upcoming: 'Upcoming', past: 'Ended', unknown: 'Unknown' }
            return labels[status] || 'Unknown'
        }

        const getStatusBadgeClass = (status) => {
            const classes = { current: 'bg-success', upcoming: 'bg-warning', past: 'bg-secondary', unknown: 'bg-secondary' }
            return classes[status] || 'bg-secondary'
        }

        const goBack = () => {
            router.push({ name: 'ContestView', params: { name: route.params.name } })
        }

        onMounted(() => loadLeaderboard())

        return {
            contest,
            contestStats,
            sortedLeaderboard,
            loading,
            refreshing,
            error,
            pagination,
            visiblePages,
            refreshLeaderboard,
            changePage,
            getStatusLabel,
            getStatusBadgeClass,
            goBack
        }
    }
}
</script>

<style scoped>
/* Leaderboard View - Matching WikiContest Theme */
.leaderboard-view {
    max-width: 1200px;
    margin: 0 auto;
}

/* Contest Header Section - Matching ContestView style */
.contest-header-section {
    border-bottom: 2px solid var(--wiki-primary);
    padding-bottom: 1rem;
    margin-bottom: 1.5rem;
}

.contest-title {
    color: var(--wiki-dark);
    font-weight: 700;
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
    transition: color 0.3s ease;
}

/* Dark mode title color */
[data-theme="dark"] .contest-title {
    color: #ffffff !important;
}

.trophy-icon {
    color: var(--wiki-primary);
}

.contest-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.contest-meta .badge {
    font-weight: 500;
    padding: 0.4em 0.8em;
    font-size: 0.85em;
}

.card {
    border: 1px solid var(--wiki-border);
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    transition: box-shadow 0.2s ease;
}


/* Dark mode card styling */
[data-theme="dark"] .card {
    background-color: #2a2a2a;
    border-color: #444;
}

.card:hover {
    box-shadow: 0 4px 8px rgba(0, 102, 153, 0.15);
}

/* Card header with brand color background */
.card-header {
    background-color: var(--wiki-primary);
    color: white;
    border-bottom: none;
    padding: 1rem 1.5rem;
    font-weight: 600;
    border-radius: 8px 8px 0 0;
}

.card-body {
    padding: 1.5rem;
}

.empty-state-card .card-body {
    padding: 3rem 1.5rem;
}

/* Large faded icon for empty state */
.empty-state-icon {
    font-size: 4rem;
    color: var(--wiki-primary);
    opacity: 0.3;
}

.empty-state-card h4 {
    color: var(--wiki-dark);
    font-weight: 600;
}

/* Dark mode empty state heading */
[data-theme="dark"] .empty-state-card h4 {
    color: #ffffff;
}

/* Leaderboard Table - Matching ContestView table style */
.leaderboard-table {
    font-size: 1rem;
    margin: 0;
}

/* Table header with brand color accent */
.leaderboard-table thead th {
    background-color: rgba(0, 102, 153, 0.1);
    color: var(--wiki-primary);
    font-weight: 600;
    border-bottom: 2px solid var(--wiki-primary);
    padding: 0.75rem;
    white-space: nowrap;
}


/* Dark mode table header */
[data-theme="dark"] .leaderboard-table thead th {
    background-color: rgba(93, 184, 230, 0.15);
    border-bottom-color: var(--wiki-primary);
}

.leaderboard-table tbody tr {
    transition: background-color 0.2s ease;
    border-bottom: 1px solid var(--wiki-border);
}

/* Dark mode row border */
[data-theme="dark"] .leaderboard-table tbody tr {
    border-bottom-color: #444;
}

/* Hover effect for table rows */
.leaderboard-table tbody tr:hover {
    background-color: var(--wiki-hover-bg);
}

.leaderboard-table tbody td {
    padding: 0.75rem;
    vertical-align: middle;
    color: var(--wiki-text);
}

/* Username Cell */
.username-cell {
    display: flex;
    align-items: center;
}

.username-cell strong {
    color: var(--wiki-dark);
    font-weight: 600;
}

/* Dark mode username color */
[data-theme="dark"] .username-cell strong {
    color: #ffffff;
}

/* Marks Highlight */
/* Emphasize total marks with brand color and larger size */
.marks-highlight {
    color: var(--wiki-primary);
    font-size: 1.15rem;
    font-weight: 700;
}

/* Badges - Matching ContestView badge style */
.badge {
    font-weight: 500;
    padding: 0.4em 0.8em;
    font-size: 0.85em;
}

.submissions-badge {
    border: 1px solid #dee2e6;
}

/* Dark mode submissions badge */
[data-theme="dark"] .submissions-badge {
    background-color: #3a3a3a !important;
    color: #ffffff !important;
    border-color: #555;
}

.badge.bg-primary {
    background-color: var(--wiki-primary) !important;
}

/* Button Styling - Matching ContestView buttons */
.btn-primary {
    background-color: var(--wiki-primary);
    border-color: var(--wiki-primary);
    transition: all 0.2s ease;
}

/* Hover effect with lift animation */
.btn-primary:hover:not(:disabled) {
    background-color: var(--wiki-primary-hover);
    border-color: var(--wiki-primary-hover);
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0, 102, 153, 0.3);
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

/* Pagination - Matching ContestView pagination */
.pagination {
    margin: 0;
}

.pagination .page-link {
    color: var(--wiki-primary);
    border-color: var(--wiki-border);
    padding: 0.5rem 0.75rem;
    transition: all 0.2s ease;
}

[data-theme="dark"] .pagination .page-link {
    background-color: #2a2a2a;
    border-color: #444;
    color: var(--wiki-primary);
}

.pagination .page-item.active .page-link {
    background-color: var(--wiki-primary);
    border-color: var(--wiki-primary);
    color: white;
}

.pagination .page-link:hover:not(.disabled) {
    background-color: rgba(0, 102, 153, 0.1);
    color: var(--wiki-primary);
    border-color: var(--wiki-primary);
}

.pagination .page-item.disabled .page-link {
    opacity: 0.5;
    cursor: not-allowed;
}

/* Alert Styling - Matching ContestView alerts */
.alert {
    border-radius: 0.5rem;
    border-left: 4px solid;
    padding: 0.75rem 1rem;
}

.alert-danger {
    background-color: rgba(153, 0, 0, 0.1);
    border-color: var(--wiki-danger);
    color: var(--wiki-danger);
}

/* Spinner - Matching ContestView spinner */
.spinner-border.text-primary {
    color: var(--wiki-primary) !important;
    width: 3rem;
    height: 3rem;
    border-width: 0.3em;
}

/* Responsive */
@media (max-width: 768px) {
    .contest-title {
        font-size: 1.5rem;
    }

    .leaderboard-table {
        font-size: 0.9rem;
    }
}
</style>