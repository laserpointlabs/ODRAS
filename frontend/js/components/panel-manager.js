/**
 * Panel Manager Module
 * 
 * Manages left, right, and bottom panels including resizing, toggling, and persistence.
 */

class PanelManager {
  constructor() {
    this.panels = {
      left: { element: null, resizer: null, visible: true, width: 320 },
      right: { element: null, resizer: null, visible: true, width: 300 },
      bottom: { element: null, resizer: null, visible: false, height: 200 }
    };
    this.resizing = null;
    this.initialized = false;
  }

  /**
   * Initialize panel manager
   */
  initialize() {
    if (this.initialized) {
      return;
    }

    // Find panel elements
    this.panels.left.element = document.querySelector('.sidebar-left, .left-panel, [data-panel="left"]');
    this.panels.right.element = document.querySelector('.sidebar-right, .right-panel, [data-panel="right"]');
    this.panels.bottom.element = document.querySelector('.bottom-panel, [data-panel="bottom"]');

    // Find resizers
    this.panels.left.resizer = document.querySelector('.resizer-left, [data-resizer="left"]');
    this.panels.right.resizer = document.querySelector('.resizer-right, [data-resizer="right"]');
    this.panels.bottom.resizer = document.querySelector('.resizer-bottom, [data-resizer="bottom"]');

    // Load saved state
    if (typeof stateManager !== 'undefined') {
      const savedPanels = stateManager.get('panels');
      if (savedPanels) {
        Object.assign(this.panels.left, savedPanels.left || {});
        Object.assign(this.panels.right, savedPanels.right || {});
        Object.assign(this.panels.bottom, savedPanels.bottom || {});
      }
    }

    // Apply initial state
    this.applyState();

    // Setup event listeners
    this.setupEventListeners();

    this.initialized = true;
    console.log('✅ Panel manager initialized');
  }

  /**
   * Apply panel state
   */
  applyState() {
    // Left panel
    if (this.panels.left.element) {
      this.panels.left.element.style.width = `${this.panels.left.width}px`;
      this.panels.left.element.style.display = this.panels.left.visible ? 'block' : 'none';
    }

    // Right panel
    if (this.panels.right.element) {
      this.panels.right.element.style.width = `${this.panels.right.width}px`;
      this.panels.right.element.style.display = this.panels.right.visible ? 'block' : 'none';
    }

    // Bottom panel
    if (this.panels.bottom.element) {
      this.panels.bottom.element.style.height = `${this.panels.bottom.height}px`;
      this.panels.bottom.element.style.display = this.panels.bottom.visible ? 'flex' : 'none';
    }
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // Left panel resizer
    if (this.panels.left.resizer) {
      this.panels.left.resizer.addEventListener('mousedown', (e) => {
        e.preventDefault();
        this.startResize('left', 'horizontal', e.clientX);
      });
    }

    // Right panel resizer
    if (this.panels.right.resizer) {
      this.panels.right.resizer.addEventListener('mousedown', (e) => {
        e.preventDefault();
        this.startResize('right', 'horizontal', e.clientX);
      });
    }

    // Bottom panel resizer
    if (this.panels.bottom.resizer) {
      this.panels.bottom.resizer.addEventListener('mousedown', (e) => {
        e.preventDefault();
        this.startResize('bottom', 'vertical', e.clientY);
      });
    }

    // Global mouse events for resizing
    document.addEventListener('mousemove', (e) => {
      if (this.resizing) {
        this.handleResize(e);
      }
    });

    document.addEventListener('mouseup', () => {
      if (this.resizing) {
        this.stopResize();
      }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      // F12: Toggle panels
      if (e.key === 'F12') {
        e.preventDefault();
        this.togglePanels();
      }
    });

    // Listen for toggle events
    if (typeof eventBus !== 'undefined') {
      eventBus.on('ui:toggle-panels', () => {
        this.togglePanels();
      });

      eventBus.on('ui:toggle-left-panel', () => {
        this.toggle('left');
      });

      eventBus.on('ui:toggle-right-panel', () => {
        this.toggle('right');
      });

      eventBus.on('ui:toggle-bottom-panel', () => {
        this.toggle('bottom');
      });
    }
  }

  /**
   * Start resizing a panel
   */
  startResize(panel, direction, startPos) {
    this.resizing = {
      panel,
      direction,
      startPos,
      startSize: panel === 'bottom' ? this.panels[panel].height : this.panels[panel].width
    };

    document.body.style.cursor = direction === 'horizontal' ? 'col-resize' : 'row-resize';
    document.body.style.userSelect = 'none';
  }

  /**
   * Handle resize
   */
  handleResize(e) {
    if (!this.resizing) {
      return;
    }

    const { panel, direction, startPos, startSize } = this.resizing;
    const currentPos = direction === 'horizontal' ? e.clientX : e.clientY;
    const delta = currentPos - startPos;

    let newSize = startSize + delta;

    // Apply constraints
    if (direction === 'horizontal') {
      newSize = Math.max(200, Math.min(600, newSize));
      this.panels[panel].width = newSize;
      if (this.panels[panel].element) {
        this.panels[panel].element.style.width = `${newSize}px`;
      }
    } else {
      newSize = Math.max(100, Math.min(400, newSize));
      this.panels[panel].height = newSize;
      if (this.panels[panel].element) {
        this.panels[panel].element.style.height = `${newSize}px`;
      }
    }

    // Emit resize event
    if (typeof eventBus !== 'undefined') {
      eventBus.emit('panel:resized', { panel, size: newSize });
    }
  }

  /**
   * Stop resizing
   */
  stopResize() {
    if (!this.resizing) {
      return;
    }

    const { panel } = this.resizing;
    this.resizing = null;

    document.body.style.cursor = '';
    document.body.style.userSelect = '';

    // Save state
    this.saveState();

    // Emit resize complete event
    if (typeof eventBus !== 'undefined') {
      eventBus.emit('panel:resize-complete', { panel });
    }
  }

  /**
   * Toggle panel visibility
   */
  toggle(panel) {
    if (!this.panels[panel]) {
      return;
    }

    this.panels[panel].visible = !this.panels[panel].visible;
    this.applyState();
    this.saveState();

    if (typeof eventBus !== 'undefined') {
      eventBus.emit('panel:toggled', { panel, visible: this.panels[panel].visible });
    }
  }

  /**
   * Show panel
   */
  show(panel) {
    if (!this.panels[panel] || this.panels[panel].visible) {
      return;
    }

    this.panels[panel].visible = true;
    this.applyState();
    this.saveState();
  }

  /**
   * Hide panel
   */
  hide(panel) {
    if (!this.panels[panel] || !this.panels[panel].visible) {
      return;
    }

    this.panels[panel].visible = false;
    this.applyState();
    this.saveState();
  }

  /**
   * Toggle all panels
   */
  togglePanels() {
    const allVisible = this.panels.left.visible && 
                       this.panels.right.visible && 
                       this.panels.bottom.visible;

    this.panels.left.visible = !allVisible;
    this.panels.right.visible = !allVisible;
    this.panels.bottom.visible = false; // Keep bottom hidden by default

    this.applyState();
    this.saveState();
  }

  /**
   * Save panel state
   */
  saveState() {
    if (typeof stateManager !== 'undefined') {
      stateManager.set('panels', {
        left: {
          visible: this.panels.left.visible,
          width: this.panels.left.width
        },
        right: {
          visible: this.panels.right.visible,
          width: this.panels.right.width
        },
        bottom: {
          visible: this.panels.bottom.visible,
          height: this.panels.bottom.height
        }
      });
    }
  }

  /**
   * Get panel state
   */
  getState(panel) {
    return this.panels[panel] ? { ...this.panels[panel] } : null;
  }
}

// Create singleton instance
const panelManager = new PanelManager();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    panelManager.initialize();
  });
} else {
  panelManager.initialize();
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { PanelManager, panelManager };
}
