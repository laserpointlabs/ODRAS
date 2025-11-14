/**
 * ODRAS Events Adapter
 *
 * Adapter layer that wraps ODRAS event bus to provide a clean interface
 * for the ontology workbench. This allows the workbench to be independent
 * of ODRAS-specific event implementation details.
 */

/**
 * Creates an events adapter that wraps ODRAS event bus
 * @param {Function} subscribeToEvent - Function to subscribe to events
 * @param {Function} emitEvent - Function to emit events
 * @returns {EventAdapter} Adapter implementing the event interface
 */
export function createOdrasEventsAdapter(subscribeToEvent, emitEvent) {
  const subscriptions = new Map();

  return {
    /**
     * Subscribe to an event
     * @param {string} event - Event name
     * @param {Function} handler - Event handler function
     * @returns {Function} Unsubscribe function
     */
    subscribe(event, handler) {
      // Use ODRAS subscribeToEvent which returns unsubscribe function
      const unsubscribe = subscribeToEvent(event, handler);

      // Track subscription for cleanup
      if (!subscriptions.has(event)) {
        subscriptions.set(event, new Set());
      }
      subscriptions.get(event).add(unsubscribe);

      // Return unsubscribe function
      return () => {
        unsubscribe();
        const eventSubs = subscriptions.get(event);
        if (eventSubs) {
          eventSubs.delete(unsubscribe);
          if (eventSubs.size === 0) {
            subscriptions.delete(event);
          }
        }
      };
    },

    /**
     * Emit an event
     * @param {string} event - Event name
     * @param {*} data - Event data
     */
    emit(event, data) {
      emitEvent(event, data);
    },

    /**
     * Unsubscribe from all events
     */
    unsubscribeAll() {
      subscriptions.forEach((unsubscribers, event) => {
        unsubscribers.forEach(unsubscribe => {
          try {
            unsubscribe();
          } catch (error) {
            console.error(`Error unsubscribing from ${event}:`, error);
          }
        });
      });
      subscriptions.clear();
    }
  };
}
