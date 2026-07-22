/**
 * OAuth Utility Functions
 *
 * This module handles OAuth callback processing after Wikimedia authentication.
 * It checks for OAuth success in URL parameters and updates the authentication state.
 */

import { showAlert } from './alerts'

/**
 * Process OAuth callback after redirect from Wikimedia
 * This should be called when the app loads to check if we just returned from OAuth
 *
 * @param {Object} store - The store instance from useStore()
 * @param {Object} router - Vue Router instance
 */
export function processOAuthCallback(store, router) {
  // Check if we have OAuth success indicators in the URL
  const urlParams = new URLSearchParams(window.location.search)

  // Check for OAuth success
  const oauthSuccess = urlParams.get('oauth_success')

  if (oauthSuccess === 'true') {
    // OAuth was successful, check authentication
    // Give a small delay to ensure cookies are set
    setTimeout(async () => {
      try {
        const authenticated = await store.checkAuth()
        if (authenticated) {
          showAlert('Successfully logged in with Wikimedia!', 'success')
          // Clean up URL and redirect to contests page
          router.replace('/contests')
        } else {
          // Auth check failed, redirect to home page
          // User can try OAuth login again from there
          showAlert('Authentication failed. Please try again.', 'warning')
          router.replace('/')
        }
      } catch (error) {
        console.error('OAuth callback error:', error)
        showAlert('Failed to verify authentication. Please try logging in again.', 'danger')
        // Redirect to home page - user can try OAuth login again
        router.replace('/')
      }
    }, 200)
  }

  // Check for OAuth errors
  const oauthError = urlParams.get('oauth_error')
  if (oauthError) {
    showAlert(`OAuth login failed: ${oauthError}`, 'danger')
    // Clean up URL and redirect to home page
    // User can try OAuth login again from there
    router.replace('/')
  }
}
