/**
 * ODRAS State Adapter
 *
 * Adapter layer that wraps ODRAS state management to provide a clean interface
 * for the ontology workbench. This allows the workbench to be independent
 * of ODRAS-specific state implementation details.
 */

/**
 * Creates a state adapter that wraps ODRAS state management
 * @param {Function} getAppState - Function to get current app state
 * @param {Function} updateAppState - Function to update app state
 * @returns {StateAdapter} Adapter implementing the state interface
 */
export function createOdrasStateAdapter(getAppState, updateAppState) {
  const listeners = new Set();

  return {
    /**
     * Get current application state
     * @returns {Object} Current application state
     */
    getState() {
      return getAppState();
    },

    /**
     * Update application state
     * @param {Object} updates - Partial state updates
     */
    updateState(updates) {
      updateAppState(updates);
      // Notify listeners
      const currentState = getAppState();
      listeners.forEach(listener => {
        try {
          listener(currentState);
        } catch (error) {
          console.error('Error in state listener:', error);
        }
      });
    },

    /**
     * Subscribe to state changes
     * @param {Function} callback - Callback function called on state changes
     * @returns {Function} Unsubscribe function
     */
    subscribe(callback) {
      listeners.add(callback);
      return () => {
        listeners.delete(callback);
      };
    }
  };
}
