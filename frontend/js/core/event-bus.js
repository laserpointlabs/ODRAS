/**
 * Event Bus Module
 * 
 * Centralized event system for ODRAS frontend.
 * Provides pub/sub pattern for component communication.
 */

class EventBus {
  constructor() {
    this.listeners = new Map();
    this.onceListeners = new Map();
  }

  /**
   * Subscribe to an event
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);

    // Return unsubscribe function
    return () => {
      const callbacks = this.listeners.get(event);
      if (callbacks) {
        const index = callbacks.indexOf(callback);
        if (index > -1) {
          callbacks.splice(index, 1);
        }
      }
    };
  }

  /**
   * Subscribe to an event once
   */
  once(event, callback) {
    if (!this.onceListeners.has(event)) {
      this.onceListeners.set(event, []);
    }
    this.onceListeners.get(event).push(callback);
  }

  /**
   * Unsubscribe from an event
   */
  off(event, callback) {
    if (callback) {
      // Remove specific callback
      const callbacks = this.listeners.get(event);
      if (callbacks) {
        const index = callbacks.indexOf(callback);
        if (index > -1) {
          callbacks.splice(index, 1);
        }
      }
    } else {
      // Remove all listeners for event
      this.listeners.delete(event);
      this.onceListeners.delete(event);
    }
  }

  /**
   * Emit an event
   */
  emit(event, data = null) {
    // Regular listeners
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in event listener for ${event}:`, error);
        }
      });
    }

    // Once listeners (remove after calling)
    const onceCallbacks = this.onceListeners.get(event);
    if (onceCallbacks) {
      onceCallbacks.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in once listener for ${event}:`, error);
        }
      });
      this.onceListeners.delete(event);
    }

    // Wildcard listeners
    const wildcardCallbacks = this.listeners.get('*');
    if (wildcardCallbacks) {
      wildcardCallbacks.forEach(callback => {
        try {
          callback(event, data);
        } catch (error) {
          console.error(`Error in wildcard listener:`, error);
        }
      });
    }
  }

  /**
   * Wait for an event (returns a Promise)
   */
  waitFor(event, timeout = 5000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.off(event, callback);
        reject(new Error(`Event ${event} timed out after ${timeout}ms`));
      }, timeout);

      const callback = (data) => {
        clearTimeout(timer);
        resolve(data);
      };

      this.once(event, callback);
    });
  }
}

// Create singleton instance
const eventBus = new EventBus();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { EventBus, eventBus };
}
