/**
 * UI Helpers
 *
 * DOM utility functions and UI-related helpers.
 * These functions have minimal dependencies (only DOM APIs).
 */

/**
 * Query selector - get single element
 * @param {string} selector - CSS selector
 * @param {Element} root - Root element to search from (default: document)
 * @returns {Element|null} Found element or null
 */
export function qs(selector, root = document) {
  return root.querySelector(selector);
}

/**
 * Query selector all - get all matching elements
 * @param {string} selector - CSS selector
 * @param {Element} root - Root element to search from (default: document)
 * @returns {Array<Element>} Array of found elements
 */
export function qsa(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

/**
 * Debounce function - delays execution until after wait time has passed
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Get display name for element type
 * @param {string} type - Element type ('class', 'objectProperty', 'dataProperty', 'note', 'model')
 * @returns {string} Display name
 */
export function getTypeDisplayName(type) {
  const typeMap = {
    'class': 'Class',
    'objectProperty': 'Object Property',
    'dataProperty': 'Data Property',
    'note': 'Note',
    'model': 'Model'
  };
  return typeMap[type] || 'Class';
}

/**
 * Get style configuration for note type
 * @param {string} noteType - Note type ('Note', 'Warning', 'Issue', 'Todo', 'Info', 'Success', 'Question')
 * @returns {Object} Style configuration with backgroundColor, borderColor, textColor, symbol
 */
export function getNoteTypeStyle(noteType) {
  const styles = {
    'Note': { backgroundColor: '#2a1f0a', borderColor: '#8b5a1e', textColor: '#f5e6cc', symbol: '📝' },
    'Warning': { backgroundColor: '#2d1b0f', borderColor: '#d97706', textColor: '#fbbf24', symbol: '⚠️' },
    'Issue': { backgroundColor: '#2d0f0f', borderColor: '#dc2626', textColor: '#fca5a5', symbol: '❗' },
    'Todo': { backgroundColor: '#1e1b2d', borderColor: '#7c3aed', textColor: '#c4b5fd', symbol: '✅' },
    'Info': { backgroundColor: '#0f1a2d', borderColor: '#2563eb', textColor: '#93c5fd', symbol: 'ℹ️' },
    'Success': { backgroundColor: '#0f2d1a', borderColor: '#16a34a', textColor: '#86efac', symbol: '✨' },
    'Question': { backgroundColor: '#2d1a0f', borderColor: '#ea580c', textColor: '#fdba74', symbol: '❓' }
  };
  return styles[noteType] || styles['Note'];
}

/**
 * Snap position to grid
 * @param {Object} position - Position object with x and y
 * @param {boolean} snapToGrid - Whether to snap to grid
 * @param {number} gridSize - Grid size in pixels
 * @returns {Object} Snapped position object
 */
export function snapToGrid(position, snapToGrid = true, gridSize = 20) {
  if (!snapToGrid) return position;
  return {
    x: Math.round(position.x / gridSize) * gridSize,
    y: Math.round(position.y / gridSize) * gridSize
  };
}

/**
 * Show temporary message (stub - to be implemented with UI framework)
 * @param {string} msg - Message text
 * @param {number} duration - Duration in milliseconds
 */
export function showTemporaryMessage(msg, duration = 2000) {
  console.log('💬', msg);
  // TODO: Implement with proper UI notification system
}
