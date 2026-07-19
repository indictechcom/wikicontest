/**
 * API Service for WikiEval Backend Communication
 *
 * This module handles all HTTP requests to the Flask backend API.
 * It includes:
 * - CSRF token management
 * - Cookie handling for JWT authentication
 * - Error handling
 * - Request/response interceptors
 */

import axios from 'axios'

// Configure axios instance with base settings for all API requests
const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Extract cookie value by name from document.cookie string
function getCookie(name) {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) {
    return parts.pop().split(';').shift()
  }
  return null
}

// Request interceptor to inject CSRF token into outgoing requests
api.interceptors.request.use(
  (config) => {
    // Attach CSRF token from cookie to request header for Flask-JWT protection
    const csrfToken = getCookie('csrf_access_token')
    if (csrfToken) {
      config.headers['X-CSRF-TOKEN'] = csrfToken
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for centralized error handling and data extraction
api.interceptors.response.use(
  (response) => {
    // Unwrap response to return data directly instead of full axios response
    return response.data
  },
  (error) => {
    // Handle 401 errors silently to avoid alert spam during auth checks
    if (error.response?.status === 401) {
      const apiError = new Error('Unauthorized')
      apiError.status = 401
      apiError.response = error.response
      return Promise.reject(apiError)
    }

    // Extract meaningful error message from backend response
    const message = error.response?.data?.error || error.message || 'Request failed'

    // Create enriched error object with status and response data
    const apiError = new Error(message)
    apiError.status = error.response?.status
    apiError.response = error.response

    return Promise.reject(apiError)
  }
)

// Exposed API methods wrapping axios HTTP verbs
export default {
  // Standard HTTP methods with consistent interface
  get: (url, config = {}) => api.get(url, config),
  post: (url, data = {}, config = {}) => api.post(url, data, config),
  put: (url, data = {}, config = {}) => api.put(url, data, config),
  delete: (url, config = {}) => api.delete(url, config),
  patch: (url, data = {}, config = {}) => api.patch(url, data, config),

  // Delete a submission
  deleteSubmission: (submissionId) => api.delete(`/submission/${submissionId}`),

  // Get contest submissions
  getContestSubmissions: (contestId) => api.get(`/submission/contest/${contestId}`)
}
