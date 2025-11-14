/**
 * Metadata Helpers
 *
 * Functions for managing metadata (creation/modification timestamps, user info).
 * Uses adapter pattern to get user info from state adapter.
 */

/**
 * Get current username from app state or localStorage
 * @param {Object} stateAdapter - Optional state adapter instance
 * @returns {string} Current username
 */
export function getCurrentUsername(stateAdapter = null) {
  try {
    if (stateAdapter) {
      const state = stateAdapter.getState ? stateAdapter.getState() : stateAdapter.get();
      if (state?.user?.username) return state.user.username;
    }
    const username = localStorage.getItem('odras_user');
    if (username && typeof username === 'string' && username.trim() !== '') {
      return username.trim();
    }
    return 'system';
  } catch (e) {
    console.error('Error getting current username:', e);
    return 'system';
  }
}

/**
 * Get current timestamp in ISO format
 * @returns {string} ISO timestamp
 */
export function getCurrentTimestamp() {
  return new Date().toISOString();
}

/**
 * Get current date in YYYY-MM-DD format
 * @returns {string} Date string
 */
export function getCurrentDate() {
  return new Date().toISOString().split('T')[0]; // YYYY-MM-DD format
}

/**
 * Add creation metadata to attributes
 * @param {Object} attrs - Existing attributes
 * @returns {Object} Attributes with creation metadata
 */
export function addCreationMetadata(attrs = {}) {
  const currentUser = getCurrentUsername();
  const timestamp = getCurrentTimestamp();
  return {
    ...attrs,
    creator: currentUser,
    created_date: getCurrentDate(),
    created_timestamp: timestamp,
    last_modified_by: currentUser,
    last_modified_date: getCurrentDate(),
    last_modified_timestamp: timestamp
  };
}

/**
 * Update modification metadata in attributes
 * @param {Object} attrs - Existing attributes
 * @param {Function} getStateFn - Optional function to get app state
 * @returns {Object} Attributes with updated modification metadata
 */
export function updateModificationMetadata(attrs = {}, getStateFn = null) {
  const currentUser = getCurrentUsername();
  const timestamp = getCurrentTimestamp();
  return {
    ...attrs,
    last_modified_by: currentUser,
    last_modified_date: getCurrentDate(),
    last_modified_timestamp: timestamp
  };
}
