<template>
  <div class="container py-5">
    <h2 class="mb-4 page-header">Manage Trusted Members</h2>

    <!-- Tabs for different sections -->
    <ul class="nav nav-tabs mb-4" role="tablist">
      <li class="nav-item" role="presentation">
        <button
          class="nav-link"
          :class="{ active: activeTab === 'requests' }"
          @click="setActiveTab('requests')"
          type="button"
        >
          <i class="fas fa-inbox me-2"></i>Pending Requests
          <span v-if="requests.length > 0" class="badge bg-warning ms-2">{{ requests.length }}</span>
        </button>
      </li>
      <li class="nav-item" role="presentation">
        <button
          class="nav-link"
          :class="{ active: activeTab === 'members' }"
          @click="setActiveTab('members')"
          type="button"
        >
          <i class="fas fa-users me-2"></i>Trusted Members
        </button>
      </li>
      <li class="nav-item" role="presentation">
        <button
          class="nav-link"
          :class="{ active: activeTab === 'add' }"
          @click="setActiveTab('add')"
          type="button"
        >
          <i class="fas fa-user-plus me-2"></i>Add Member
        </button>
      </li>
    </ul>

    <!-- Pending Requests Tab -->
    <div v-if="activeTab === 'requests'" class="tab-content">
      <div v-if="loading" class="text-center py-5">
        <div class="spinner-border" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
      <div v-else-if="requests.length === 0" class="alert alert-info">
        <i class="fas fa-info-circle me-2"></i>No pending requests
      </div>
      <div v-else class="table-responsive">
        <table class="table table-hover">
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="request in requests" :key="request.id">
              <td>{{ request.username }}</td>
              <td>{{ request.email }}</td>
              <td>
                <span class="badge bg-secondary">{{ request.role }}</span>
              </td>
              <td>
                <button
                  class="btn btn-sm btn-success me-2"
                  @click="approveRequest(request.id)"
                  :disabled="processing"
                >
                  <i class="fas fa-check me-1"></i>Approve
                </button>
                <button
                  class="btn btn-sm btn-danger"
                  @click="rejectRequest(request.id)"
                  :disabled="processing"
                >
                  <i class="fas fa-times me-1"></i>Reject
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Trusted Members Tab -->
    <div v-if="activeTab === 'members'" class="tab-content">
      <div v-if="loading" class="text-center py-5">
        <div class="spinner-border" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
      <div v-else-if="trustedMembers.length === 0" class="alert alert-info">
        <i class="fas fa-info-circle me-2"></i>No trusted members yet
      </div>
      <div v-else class="table-responsive">
        <table class="table table-hover">
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="member in trustedMembers" :key="member.id">
              <td>{{ member.username }}</td>
              <td>{{ member.email }}</td>
              <td>
                <span class="badge bg-secondary">{{ member.role }}</span>
              </td>
              <td>
                <span v-if="member.is_superadmin" class="badge bg-danger">Superadmin</span>
                <span v-else class="badge bg-success">Trusted Member</span>
              </td>
              <td>
                <button
                  v-if="!member.is_superadmin"
                  class="btn btn-sm btn-danger"
                  @click="removeMember(member.id)"
                  :disabled="processing"
                >
                  <i class="fas fa-user-minus me-1"></i>Remove
                </button>
                <span v-else class="text-muted">Cannot remove superadmin</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Add Member Tab -->
    <div v-if="activeTab === 'add'" class="tab-content">
      <div class="card">
        <div class="card-body">
          <h5 class="card-title">Add Trusted Member Manually</h5>
          <p class="text-muted">Add a user as a trusted member by username</p>
          <div class="mb-3">
            <label for="usernameInput" class="form-label">Username</label>
            <input
              type="text"
              class="form-control"
              id="usernameInput"
              v-model="usernameToAdd"
              placeholder="Enter username"
              @keyup.enter="addMember"
            />
          </div>
          <button
            class="btn btn-primary"
            @click="addMember"
            :disabled="!usernameToAdd || processing"
          >
            <i class="fas fa-user-plus me-2"></i>Add Member
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '../services/api'
import { showAlert } from '../utils/alerts'

export default {
  name: 'TrustedMembers',
  setup() {
    const router = useRouter()
    const route = useRoute()
    const VALID_TABS = ['requests', 'members', 'add']
    const activeTab = ref('requests')
    const requests = ref([])
    const trustedMembers = ref([])
    const loading = ref(false)
    const processing = ref(false)
    const usernameToAdd = ref('')

    // Restore the active subsection from the URL query parameter (?tab=...)
    const getTabFromUrl = () => {
      const tab = route.query.tab
      return VALID_TABS.includes(tab) ? tab : 'requests'
    }

    // Reflect the active subsection in the URL and push into browser history.
    const syncUrlWithTab = (tab) => {
      if (route.query.tab !== tab) {
        router.push({ name: route.name, query: { ...route.query, tab } })
      }
    }

    // Switch between subsections and sync the URL
    const setActiveTab = (tab) => {
      activeTab.value = tab
      syncUrlWithTab(tab)
      if (tab === 'requests') {
        loadRequests()
      } else if (tab === 'members') {
        loadMembers()
      }
    }

    // Load pending requests
    const loadRequests = async () => {
      try {
        loading.value = true
        const response = await api.get('/user/trusted-members/requests')
        requests.value = response.requests || []
      } catch (error) {
        console.error('Error loading requests:', error)
        showAlert('Failed to load pending requests', 'error')
      } finally {
        loading.value = false
      }
    }

    // Load trusted members
    const loadMembers = async () => {
      try {
        loading.value = true
        const response = await api.get('/user/trusted-members')
        trustedMembers.value = response.trusted_members || []
      } catch (error) {
        console.error('Error loading trusted members:', error)
        showAlert('Failed to load trusted members', 'error')
      } finally {
        loading.value = false
      }
    }

    // Approve a request
    const approveRequest = async (userId) => {
      if (!confirm('Are you sure you want to approve this request?')) {
        return
      }

      try {
        processing.value = true
        await api.post(`/user/trusted-members/${userId}/approve`)
        showAlert('Request approved successfully', 'success')
        await loadRequests()
        await loadMembers()
      } catch (error) {
        console.error('Error approving request:', error)
        showAlert(error.response?.data?.error || 'Failed to approve request', 'error')
      } finally {
        processing.value = false
      }
    }

    // Reject a request
    const rejectRequest = async (userId) => {
      if (!confirm('Are you sure you want to reject this request?')) {
        return
      }

      try {
        processing.value = true
        await api.post(`/user/trusted-members/${userId}/reject`)
        showAlert('Request rejected', 'info')
        await loadRequests()
      } catch (error) {
        console.error('Error rejecting request:', error)
        showAlert(error.response?.data?.error || 'Failed to reject request', 'error')
      } finally {
        processing.value = false
      }
    }

    // Add member manually
    const addMember = async () => {
      if (!usernameToAdd.value.trim()) {
        showAlert('Please enter a username', 'warning')
        return
      }

      try {
        processing.value = true
        // First, search for the user by username
        const searchResponse = await api.get(`/user/search?q=${encodeURIComponent(usernameToAdd.value.trim())}`)
        const users = searchResponse.users || []
        const user = users.find(u => u.username.toLowerCase() === usernameToAdd.value.trim().toLowerCase())

        if (!user) {
          showAlert('User not found', 'error')
          return
        }

        await api.post(`/user/trusted-members/${user.id}/add`)
        showAlert(`User ${user.username} added as trusted member`, 'success')
        usernameToAdd.value = ''
        await loadMembers()
      } catch (error) {
        console.error('Error adding member:', error)
        showAlert(error.response?.data?.error || 'Failed to add member', 'error')
      } finally {
        processing.value = false
      }
    }

    // Remove member
    const removeMember = async (userId) => {
      const member = trustedMembers.value.find(m => m.id === userId)
      if (!confirm(`Are you sure you want to remove ${member?.username} from trusted members?`)) {
        return
      }

      try {
        processing.value = true
        await api.post(`/user/trusted-members/${userId}/remove`)
        showAlert('Member removed successfully', 'success')
        await loadMembers()
      } catch (error) {
        console.error('Error removing member:', error)
        showAlert(error.response?.data?.error || 'Failed to remove member', 'error')
      } finally {
        processing.value = false
      }
    }

    // Load data on component mount, restoring the subsection from the URL
    onMounted(async () => {
      activeTab.value = getTabFromUrl()
      syncUrlWithTab(activeTab.value)
      // Only load data for the active subsection (no automatic refresh)
      if (activeTab.value === 'requests') {
        loadRequests()
      } else if (activeTab.value === 'members') {
        loadMembers()
      }
    })

    // Keep the active subsection in sync when the URL changes
    // (e.g. a shared link is opened, or the user uses back/forward navigation)
    watch(
      () => route.query.tab,
      (tab) => {
        const next = VALID_TABS.includes(tab) ? tab : 'requests'
        if (next !== activeTab.value) {
          activeTab.value = next
          if (next === 'requests') {
            loadRequests()
          } else if (next === 'members') {
            loadMembers()
          }
        }
      }
    )

    return {
      activeTab,
      requests,
      trustedMembers,
      loading,
      processing,
      usernameToAdd,
      approveRequest,
      rejectRequest,
      addMember,
      removeMember,
      setActiveTab
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
  width: fit-content;
}

[data-theme="dark"] h2.page-header {
  color: #ffffff !important;
}

.nav-tabs {
  border-bottom: 2px solid var(--wiki-border);
}

.nav-tabs .nav-link {
  color: var(--wiki-text-muted);
  border: none;
  border-bottom: 2px solid transparent;
  padding: 0.75rem 1.5rem;
}

.nav-tabs .nav-link:hover {
  border-bottom-color: var(--wiki-primary);
  color: var(--wiki-primary);
}

.nav-tabs .nav-link.active {
  color: var(--wiki-primary);
  border-bottom-color: var(--wiki-primary);
  font-weight: 600;
}

.tab-content {
  min-height: 300px;
}

.table {
  background-color: var(--wiki-card-bg);
  border-radius: 4px;
  overflow: hidden;
}

.table thead {
  background-color: var(--wiki-light-bg);
}

.table th {
  border-bottom: 2px solid var(--wiki-border);
  font-weight: 600;
  color: var(--wiki-dark);
}

.table td {
  vertical-align: middle;
}

.card {
  background-color: var(--wiki-card-bg);
  border: 1px solid var(--wiki-border);
  border-radius: 4px;
}

.card-body {
  padding: 2rem;
}
</style>
