/**
 * Modal Dialog Manager Module
 * 
 * Manages modal dialogs for the ODRAS application.
 */

class ModalManager {
  constructor() {
    this.modals = new Map();
    this.activeModal = null;
    this.initialized = false;
  }

  /**
   * Initialize modal manager
   */
  initialize() {
    if (this.initialized) {
      return;
    }

    this.setupEventListeners();
    this.initialized = true;
    console.log('✅ Modal manager initialized');
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // Close modal on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.activeModal) {
        this.close(this.activeModal);
      }
    });

    // Close modal on overlay click
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('modal-overlay') && this.activeModal) {
        this.close(this.activeModal);
      }
    });
  }

  /**
   * Create a modal
   */
  create(id, options = {}) {
    const {
      title = '',
      content = '',
      buttons = [],
      closable = true,
      className = '',
      size = 'medium' // 'small', 'medium', 'large', 'fullscreen'
    } = options;

    // Remove existing modal if present
    if (this.modals.has(id)) {
      this.remove(id);
    }

    // Create modal HTML
    const modalHTML = `
      <div class="modal-overlay" data-modal-id="${id}">
        <div class="modal ${className} modal-${size}">
          ${title ? `
            <div class="modal-header">
              <h3>${title}</h3>
              ${closable ? '<button class="modal-close" data-action="close">&times;</button>' : ''}
            </div>
          ` : ''}
          <div class="modal-body">
            ${content}
          </div>
          ${buttons.length > 0 ? `
            <div class="modal-footer">
              ${buttons.map(btn => `
                <button class="btn ${btn.className || ''}" data-action="${btn.action || 'none'}">
                  ${btn.label || 'Button'}
                </button>
              `).join('')}
            </div>
          ` : ''}
        </div>
      </div>
    `;

    // Create modal element
    const temp = document.createElement('div');
    temp.innerHTML = modalHTML;
    const modal = temp.firstElementChild;

    // Add to document
    document.body.appendChild(modal);
    this.modals.set(id, modal);

    // Setup button handlers
    modal.querySelectorAll('[data-action]').forEach(button => {
      button.addEventListener('click', (e) => {
        const action = button.getAttribute('data-action');
        if (action === 'close') {
          this.close(id);
        } else {
          if (typeof eventBus !== 'undefined') {
            eventBus.emit(`modal:${id}:action`, { action, button });
          }
        }
      });
    });

    return modal;
  }

  /**
   * Show a modal
   */
  show(id, options = {}) {
    let modal = this.modals.get(id);

    // Create modal if it doesn't exist
    if (!modal && options.title !== undefined) {
      modal = this.create(id, options);
    }

    if (!modal) {
      console.error(`Modal ${id} not found`);
      return;
    }

    // Hide previous modal
    if (this.activeModal && this.activeModal !== modal) {
      this.hide(this.activeModal);
    }

    // Show modal
    modal.style.display = 'flex';
    modal.classList.add('active');
    this.activeModal = modal;

    // Prevent body scroll
    document.body.style.overflow = 'hidden';

    // Emit event
    if (typeof eventBus !== 'undefined') {
      eventBus.emit('modal:opened', { id });
    }

    // Focus first input or button
    const firstInput = modal.querySelector('input, textarea, select, button');
    if (firstInput && firstInput.tagName !== 'BUTTON') {
      firstInput.focus();
    }
  }

  /**
   * Hide a modal
   */
  hide(id) {
    const modal = typeof id === 'string' ? this.modals.get(id) : id;
    if (!modal) {
      return;
    }

    modal.style.display = 'none';
    modal.classList.remove('active');

    if (this.activeModal === modal) {
      this.activeModal = null;
      document.body.style.overflow = '';
    }

    // Emit event
    if (typeof eventBus !== 'undefined') {
      const modalId = typeof id === 'string' ? id : modal.getAttribute('data-modal-id');
      eventBus.emit('modal:closed', { id: modalId });
    }
  }

  /**
   * Close a modal (alias for hide)
   */
  close(id) {
    this.hide(id);
  }

  /**
   * Remove a modal
   */
  remove(id) {
    const modal = this.modals.get(id);
    if (modal) {
      if (this.activeModal === modal) {
        this.hide(modal);
      }
      modal.remove();
      this.modals.delete(id);
    }
  }

  /**
   * Update modal content
   */
  updateContent(id, content) {
    const modal = this.modals.get(id);
    if (modal) {
      const body = modal.querySelector('.modal-body');
      if (body) {
        body.innerHTML = content;
      }
    }
  }

  /**
   * Show confirmation dialog
   */
  async confirm(message, title = 'Confirm') {
    return new Promise((resolve) => {
      const modalId = `confirm-${Date.now()}`;
      const modal = this.create(modalId, {
        title,
        content: `<p>${message}</p>`,
        buttons: [
          {
            label: 'Cancel',
            action: 'cancel',
            className: 'btn-secondary'
          },
          {
            label: 'Confirm',
            action: 'confirm',
            className: 'btn-primary'
          }
        ]
      });

      const handler = (data) => {
        if (data.action === 'confirm') {
          resolve(true);
        } else {
          resolve(false);
        }
        this.remove(modalId);
        if (typeof eventBus !== 'undefined') {
          eventBus.off(`modal:${modalId}:action`, handler);
        }
      };

      if (typeof eventBus !== 'undefined') {
        eventBus.once(`modal:${modalId}:action`, handler);
      }

      this.show(modalId);
    });
  }

  /**
   * Show alert dialog
   */
  async alert(message, title = 'Alert') {
    return new Promise((resolve) => {
      const modalId = `alert-${Date.now()}`;
      this.create(modalId, {
        title,
        content: `<p>${message}</p>`,
        buttons: [
          {
            label: 'OK',
            action: 'ok',
            className: 'btn-primary'
          }
        ]
      });

      const handler = () => {
        resolve();
        this.remove(modalId);
        if (typeof eventBus !== 'undefined') {
          eventBus.off(`modal:${modalId}:action`, handler);
        }
      };

      if (typeof eventBus !== 'undefined') {
        eventBus.once(`modal:${modalId}:action`, handler);
      }

      this.show(modalId);
    });
  }

  /**
   * Show prompt dialog
   */
  async prompt(message, defaultValue = '', title = 'Prompt') {
    return new Promise((resolve) => {
      const modalId = `prompt-${Date.now()}`;
      const inputId = `prompt-input-${Date.now()}`;
      this.create(modalId, {
        title,
        content: `
          <p>${message}</p>
          <input type="text" id="${inputId}" value="${defaultValue}" style="width: 100%; margin-top: 8px;">
        `,
        buttons: [
          {
            label: 'Cancel',
            action: 'cancel',
            className: 'btn-secondary'
          },
          {
            label: 'OK',
            action: 'ok',
            className: 'btn-primary'
          }
        ]
      });

      const handler = (data) => {
        if (data.action === 'ok') {
          const input = document.getElementById(inputId);
          resolve(input?.value || defaultValue);
        } else {
          resolve(null);
        }
        this.remove(modalId);
        if (typeof eventBus !== 'undefined') {
          eventBus.off(`modal:${modalId}:action`, handler);
        }
      };

      if (typeof eventBus !== 'undefined') {
        eventBus.once(`modal:${modalId}:action`, handler);
      }

      this.show(modalId);
    });
  }
}

// Create singleton instance
const modalManager = new ModalManager();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    modalManager.initialize();
  });
} else {
  modalManager.initialize();
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { ModalManager, modalManager };
}
