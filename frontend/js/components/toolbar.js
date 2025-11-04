/**
 * Toolbar Component Module
 * 
 * Manages the top and bottom toolbars in ODRAS application.
 */

class ToolbarManager {
  constructor() {
    this.topbar = null;
    this.bottombar = null;
    this.initialized = false;
  }

  /**
   * Initialize toolbar
   */
  initialize() {
    if (this.initialized) {
      return;
    }

    this.topbar = document.querySelector('.topbar');
    this.bottombar = document.querySelector('.bottombar');

    if (!this.topbar || !this.bottombar) {
      console.warn('⚠️ Toolbar elements not found');
      return;
    }

    this.setupEventListeners();
    this.initialized = true;
    console.log('✅ Toolbar initialized');
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // Workbench switching buttons
    const workbenchButtons = this.topbar?.querySelectorAll('[data-workbench]');
    workbenchButtons?.forEach(button => {
      button.addEventListener('click', (e) => {
        e.preventDefault();
        const workbench = button.getAttribute('data-workbench');
        if (typeof eventBus !== 'undefined') {
          eventBus.emit('workbench:switch', { workbench });
        }
      });
    });

    // Project selector
    const projectSelect = this.topbar?.querySelector('#projectSelect');
    if (projectSelect) {
      projectSelect.addEventListener('change', (e) => {
        const projectId = e.target.value;
        if (projectId && typeof eventBus !== 'undefined') {
          eventBus.emit('project:switch', { projectId });
        }
      });
    }

    // Settings button
    const settingsButton = this.topbar?.querySelector('[data-action="settings"]');
    settingsButton?.addEventListener('click', () => {
      if (typeof eventBus !== 'undefined') {
        eventBus.emit('ui:show-settings');
      }
    });

    // Help button
    const helpButton = this.topbar?.querySelector('[data-action="help"]');
    helpButton?.addEventListener('click', () => {
      if (typeof eventBus !== 'undefined') {
        eventBus.emit('ui:show-help');
      }
    });
  }

  /**
   * Update project selector
   */
  updateProjects(projects) {
    const projectSelect = this.topbar?.querySelector('#projectSelect');
    if (!projectSelect) {
      return;
    }

    // Clear existing options except the first one
    while (projectSelect.options.length > 1) {
      projectSelect.remove(1);
    }

    // Add projects
    projects.forEach(project => {
      const option = document.createElement('option');
      option.value = project.project_id;
      option.textContent = project.name;
      projectSelect.appendChild(option);
    });
  }

  /**
   * Set active workbench
   */
  setActiveWorkbench(workbench) {
    const workbenchButtons = this.topbar?.querySelectorAll('[data-workbench]');
    workbenchButtons?.forEach(button => {
      const buttonWorkbench = button.getAttribute('data-workbench');
      if (buttonWorkbench === workbench) {
        button.classList.add('active');
      } else {
        button.classList.remove('active');
      }
    });
  }

  /**
   * Set current project
   */
  setCurrentProject(projectId) {
    const projectSelect = this.topbar?.querySelector('#projectSelect');
    if (projectSelect) {
      projectSelect.value = projectId || '';
    }
  }

  /**
   * Update bottom bar status
   */
  updateStatus(message, type = 'info') {
    const statusElement = this.bottombar?.querySelector('.status');
    if (statusElement) {
      statusElement.textContent = message;
      statusElement.className = `status ${type}`;
    }
  }

  /**
   * Clear status
   */
  clearStatus() {
    const statusElement = this.bottombar?.querySelector('.status');
    if (statusElement) {
      statusElement.textContent = '';
      statusElement.className = 'status';
    }
  }
}

// Create singleton instance
const toolbarManager = new ToolbarManager();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    toolbarManager.initialize();
  });
} else {
  toolbarManager.initialize();
}

// Export for use in other modules (ES6 module format)
export function initializeToolbar() {
  return toolbarManager.initialize();
}

export { ToolbarManager, toolbarManager };
