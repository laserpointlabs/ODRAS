/**
 * Utility Functions Module
 * 
 * Shared utilities for ODRAS frontend modules
 */

// Markdown parser - uses marked if available, otherwise falls back to simple renderer
export function parseMarkdown(text) {
  if (!text) return '';
  
  // Use marked library if available (loaded from CDN in app.html)
  if (typeof marked !== 'undefined' && marked.parse) {
    try {
      return marked.parse(text);
    } catch (e) {
      console.warn('Markdown parsing failed, using fallback:', e);
    }
  }
  
  // Fallback simple markdown renderer
  let rendered = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

  rendered = rendered.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  rendered = rendered.replace(/__(.+?)__/g, '<strong>$1</strong>');
  rendered = rendered.replace(/\*(.+?)\*/g, '<em>$1</em>');
  rendered = rendered.replace(/(?<!\w)_(.+?)_(?!\w)/g, '<em>$1</em>');
  rendered = rendered.replace(/`(.+?)`/g, '<code style="background:var(--panel-2);padding:2px 4px;border-radius:3px;font-family:monospace;font-size:0.9em;">$1</code>');
  rendered = rendered.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" style="color:var(--primary);">$1</a>');

  return rendered;
}

// Toast notification system
export function showToast(message, isError = false) {
  // Emit event for other modules to listen
  if (typeof window !== 'undefined' && window.dispatchEvent) {
    window.dispatchEvent(new CustomEvent('toast', { 
      detail: { message, isError } 
    }));
  }

  // Create toast element if window.toast doesn't exist
  if (typeof window.toast === 'undefined') {
    const toast = document.createElement('div');
    toast.style.cssText = `
      position: fixed; bottom: 20px; right: 20px; z-index: 10001;
      background: ${isError ? '#ef4444' : '#10b981'}; color: white;
      padding: 12px 16px; border-radius: 6px; font-size: 14px; font-weight: 500;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      animation: slideInRight 0.3s ease-out;
    `;
    toast.textContent = message;

    // Ensure CSS animations exist
    if (!document.getElementById('toast-animations')) {
      const style = document.createElement('style');
      style.id = 'toast-animations';
      style.textContent = `
        @keyframes slideInRight {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOutRight {
          from { transform: translateX(0); opacity: 1; }
          to { transform: translateX(100%); opacity: 0; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `;
      document.head.appendChild(style);
    }

    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = 'slideOutRight 0.3s ease-in forwards';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  } else {
    // Use existing toast function
    window.toast(message, isError);
  }
}

// Get current project ID from state or localStorage
export function getCurrentProjectId() {
  // Try to get from state manager if available (import dynamically)
  if (typeof window !== 'undefined' && window.getAppState) {
    try {
      const state = window.getAppState();
      if (state?.currentProject?.project_id) {
        return state.currentProject.project_id;
      }
      // Also check activeProject for compatibility
      if (state?.activeProject?.projectId) {
        return state.activeProject.projectId;
      }
    } catch (e) {
      // Fall through to localStorage
    }
  }
  
  // Fallback to localStorage (backwards compatible)
  return localStorage.getItem('active_project_id') || null;
}

// Make available globally for backwards compatibility
if (typeof window !== 'undefined') {
  window.getCurrentProjectId = getCurrentProjectId;
  window.parseMarkdown = parseMarkdown;
  window.showToast = showToast;
}
