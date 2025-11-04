/**
 * State Manager Module
 * 
 * Centralized state management for ODRAS frontend.
 * Provides reactive state updates and persistence.
 */

class StateManager {
  constructor() {
    this.state = {
      // Application state
      currentProject: null,
      currentWorkbench: null,
      currentUser: null,
      
      // UI state
      panels: {
        left: { visible: true, width: 320 },
        right: { visible: true, width: 300 },
        bottom: { visible: false, height: 200 }
      },
      
      // DAS state
      das: {
        open: false,
        docked: 'right', // 'left', 'right', 'bottom'
        minimized: false
      },
      
      // Workbench-specific state
      workbenches: {}
    };

    this.listeners = new Map();
    this.loadState();
  }

  /**
   * Get state value
   */
  get(path) {
    const keys = path.split('.');
    let value = this.state;
    
    for (const key of keys) {
      if (value === null || value === undefined) {
        return undefined;
      }
      value = value[key];
    }
    
    return value;
  }

  /**
   * Set state value
   */
  set(path, value) {
    const keys = path.split('.');
    const lastKey = keys.pop();
    let target = this.state;

    for (const key of keys) {
      if (!target[key] || typeof target[key] !== 'object') {
        target[key] = {};
      }
      target = target[key];
    }

    const oldValue = target[lastKey];
    target[lastKey] = value;

    // Emit change event
    this.emit('change', { path, oldValue, newValue: value });
    this.emit(`change:${path}`, { oldValue, newValue: value });

    // Persist to localStorage
    this.saveState();
  }

  /**
   * Update state (merge objects)
   */
  update(path, updates) {
    const current = this.get(path) || {};
    const merged = { ...current, ...updates };
    this.set(path, merged);
  }

  /**
   * Subscribe to state changes
   */
  subscribe(path, callback) {
    if (!this.listeners.has(path)) {
      this.listeners.set(path, []);
    }
    this.listeners.get(path).push(callback);

    // Return unsubscribe function
    return () => {
      const callbacks = this.listeners.get(path);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    };
  }

  /**
   * Emit event
   */
  emit(event, data) {
    // Global listeners
    const globalListeners = this.listeners.get('*') || [];
    globalListeners.forEach(callback => {
      try {
        callback(event, data);
      } catch (error) {
        console.error('Error in state listener:', error);
      }
    });

    // Event-specific listeners
    const eventListeners = this.listeners.get(event) || [];
    eventListeners.forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error('Error in state listener:', error);
      }
    });
  }

  /**
   * Save state to localStorage
   */
  saveState() {
    try {
      const persistable = {
        currentProject: this.state.currentProject,
        currentWorkbench: this.state.currentWorkbench,
        panels: this.state.panels,
        das: this.state.das
      };
      localStorage.setItem('odras_state', JSON.stringify(persistable));
    } catch (error) {
      console.warn('Failed to save state:', error);
    }
  }

  /**
   * Load state from localStorage
   */
  loadState() {
    try {
      const saved = localStorage.getItem('odras_state');
      if (saved) {
        const parsed = JSON.parse(saved);
        Object.assign(this.state, parsed);
      }
    } catch (error) {
      console.warn('Failed to load state:', error);
    }
  }

  /**
   * Clear state
   */
  clear() {
    this.state = {
      currentProject: null,
      currentWorkbench: null,
      currentUser: null,
      panels: {
        left: { visible: true, width: 320 },
        right: { visible: true, width: 300 },
        bottom: { visible: false, height: 200 }
      },
      das: {
        open: false,
        docked: 'right',
        minimized: false
      },
      workbenches: {}
    };
    localStorage.removeItem('odras_state');
    this.emit('change', { path: '*', oldValue: null, newValue: this.state });
  }
}

// Create singleton instance
const stateManager = new StateManager();

// Export functions for compatibility with requirements workbench
export function getAppState() {
  return stateManager.state;
}

export function updateAppState(newValues, shouldPersist = true) {
  Object.keys(newValues).forEach(key => {
    stateManager.set(key, newValues[key]);
  });
  if (shouldPersist) {
    stateManager.saveState();
  }
}

export function persistState() {
  stateManager.saveState();
}

// Export for use in other modules
export { StateManager, stateManager };

// Make available globally for backwards compatibility
if (typeof window !== 'undefined') {
  window.getAppState = getAppState;
  window.updateAppState = updateAppState;
  window.stateManager = stateManager;
}
