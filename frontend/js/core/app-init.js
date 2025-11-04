/**
 * Application Initialization Module
 * 
 * Handles application startup, configuration loading, and initialization sequence.
 */

class AppInitializer {
  constructor() {
    this.config = null;
    this.initialized = false;
  }

  /**
   * Initialize application
   */
  async initialize() {
    if (this.initialized) {
      return;
    }

    try {
      console.log('🚀 Initializing ODRAS application...');

      // Step 1: Load configuration
      await this.loadConfiguration();

      // Step 2: Initialize authentication
      await this.initializeAuth();

      // Step 3: Load URL parameters
      this.loadURLParameters();

      // Step 4: Initialize UI
      this.initializeUI();

      // Step 5: Set up event listeners
      this.setupEventListeners();

      this.initialized = true;
      console.log('✅ Application initialized successfully');

      // Emit initialization complete event
      if (typeof eventBus !== 'undefined') {
        eventBus.emit('app:initialized', { config: this.config });
      }
    } catch (error) {
      console.error('❌ Failed to initialize application:', error);
      throw error;
    }
  }

  /**
   * Load application configuration
   */
  async loadConfiguration() {
    try {
      const response = await fetch('/api/installation/config');
      this.config = await response.json();
      console.log('✅ Configuration loaded:', this.config);
    } catch (error) {
      console.warn('⚠️ Failed to load configuration:', error);
      this.config = {
        organization: 'ODRAS',
        baseUri: 'http://localhost:8000',
        prefix: 'odras',
        type: 'development'
      };
    }
  }

  /**
   * Initialize authentication
   */
  async initializeAuth() {
    // Check if user is already authenticated
    if (typeof apiClient !== 'undefined') {
      try {
        const user = await apiClient.getCurrentUser();
        if (user && typeof stateManager !== 'undefined') {
          stateManager.set('currentUser', user);
          console.log('✅ User authenticated:', user.username);
        }
      } catch (error) {
        console.log('ℹ️ User not authenticated');
        // Clear any stale token
        if (apiClient) {
          apiClient.saveToken(null);
        }
      }
    }
  }

  /**
   * Load URL parameters
   */
  loadURLParameters() {
    const url = new URL(window.location);
    const projectId = url.searchParams.get('project');
    const workbench = url.searchParams.get('wb');

    if (projectId && typeof stateManager !== 'undefined') {
      stateManager.set('currentProject', projectId);
      console.log('✅ Project loaded from URL:', projectId);
    }

    if (workbench && typeof stateManager !== 'undefined') {
      stateManager.set('currentWorkbench', workbench);
      console.log('✅ Workbench loaded from URL:', workbench);
    }
  }

  /**
   * Initialize UI components
   */
  initializeUI() {
    // Set up keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      // F12: Toggle panels
      if (e.key === 'F12') {
        e.preventDefault();
        if (typeof eventBus !== 'undefined') {
          eventBus.emit('ui:toggle-panels');
        }
      }
    });

    // Handle window resize
    window.addEventListener('resize', () => {
      if (typeof eventBus !== 'undefined') {
        eventBus.emit('ui:resize');
      }
    });

    // Handle beforeunload
    window.addEventListener('beforeunload', () => {
      if (typeof eventBus !== 'undefined') {
        eventBus.emit('app:beforeunload');
      }
    });
  }

  /**
   * Set up global event listeners
   */
  setupEventListeners() {
    if (typeof eventBus === 'undefined') {
      return;
    }

    // Handle authentication events
    eventBus.on('auth:unauthorized', () => {
      console.log('🔒 Authentication required');
      // Redirect to login or show login modal
      if (typeof stateManager !== 'undefined') {
        stateManager.set('currentUser', null);
      }
    });

    // Handle project changes
    eventBus.on('project:changed', (data) => {
      console.log('📁 Project changed:', data);
      // Update URL without reload
      const url = new URL(window.location);
      if (data.projectId) {
        url.searchParams.set('project', data.projectId);
      } else {
        url.searchParams.delete('project');
      }
      window.history.replaceState({}, '', url);
    });

    // Handle workbench changes
    eventBus.on('workbench:changed', (data) => {
      console.log('🛠️ Workbench changed:', data);
      // Update URL without reload
      const url = new URL(window.location);
      if (data.workbench) {
        url.searchParams.set('wb', data.workbench);
      } else {
        url.searchParams.delete('wb');
      }
      window.history.replaceState({}, '', url);
    });
  }

  /**
   * Get configuration
   */
  getConfig() {
    return this.config;
  }

  /**
   * Check if initialized
   */
  isInitialized() {
    return this.initialized;
  }
}

// Create singleton instance
const appInitializer = new AppInitializer();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    appInitializer.initialize().catch(console.error);
  });
} else {
  appInitializer.initialize().catch(console.error);
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { AppInitializer, appInitializer };
}
