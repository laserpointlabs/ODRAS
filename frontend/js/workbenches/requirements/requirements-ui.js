/**
 * Requirements Workbench UI Module
 * 
 * Extracted from app.html - handles all requirements workbench functionality
 */

import { ApiClient } from '../../core/api-client.js';
import { getAppState, updateAppState } from '../../core/state-manager.js';
import { subscribeToEvent, emitEvent } from '../../core/event-bus.js';

// Requirements workbench state
const requirementsState = {
  initialized: false,
  requirements: [],
  currentPage: 1,
  pageSize: 50,
  totalItems: 0,
  filters: {
    search: '',
    requirement_type: '',
    state: '',
    priority: '',
    verification_status: ''
  },
  sorting: {
    sort_by: 'created_at',
    sort_order: 'desc'
  },
  selectedRequirement: null
};

// Simple inline markdown renderer for requirements text
function renderInlineMarkdown(text) {
  if (!text) return '';

  // Escape HTML first
  let rendered = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

  // Bold: **text** or __text__
  rendered = rendered.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  rendered = rendered.replace(/__(.+?)__/g, '<strong>$1</strong>');

  // Italic: *text* or _text_ (but not within underscores in words)
  rendered = rendered.replace(/\*(.+?)\*/g, '<em>$1</em>');
  rendered = rendered.replace(/(?<!\w)_(.+?)_(?!\w)/g, '<em>$1</em>');

  // Code: `text`
  rendered = rendered.replace(/`(.+?)`/g, '<code style="background:var(--panel-2);padding:2px 4px;border-radius:3px;font-family:monospace;font-size:0.9em;">$1</code>');

  // Links: [text](url)
  rendered = rendered.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" style="color:var(--primary);">$1</a>');

  return rendered;
}

// Initialize requirements workbench
export function initializeRequirementsWorkbench() {
  if (requirementsState.initialized) {
    loadRequirements();
    return;
  }

  requirementsState.initialized = true;

  console.log('📋 Initializing Requirements Workbench...');

  // Initialize event handlers
  initRequirementsEventHandlers();

  // Load requirements for current project
  loadRequirements();
}

// Initialize all event handlers for requirements workbench
function initRequirementsEventHandlers() {
  // Extract from document button
  const extractBtn = document.getElementById('reqExtractBtn');
  if (extractBtn) {
    extractBtn.onclick = () => showExtractRequirementsModal();
  }

  // Create new requirement button
  const createBtn = document.getElementById('reqCreateBtn');
  if (createBtn) {
    createBtn.onclick = () => showCreateRequirementModal();
  }

  // Import requirements button
  const importBtn = document.getElementById('reqImportBtn');
  if (importBtn) {
    importBtn.onclick = () => showImportRequirementsModal();
  }

  // Search input with debouncing
  const searchInput = document.getElementById('reqSearchInput');
  if (searchInput) {
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        requirementsState.filters.search = e.target.value;
        requirementsState.currentPage = 1; // Reset to first page
        loadRequirements();
      }, 500); // 500ms debounce
    });
  }

  // Filter dropdowns
  const typeFilter = document.getElementById('reqTypeFilter');
  if (typeFilter) {
    typeFilter.addEventListener('change', (e) => {
      requirementsState.filters.requirement_type = e.target.value;
      requirementsState.currentPage = 1;
      loadRequirements();
    });
  }

  const stateFilter = document.getElementById('reqStateFilter');
  if (stateFilter) {
    stateFilter.addEventListener('change', (e) => {
      requirementsState.filters.state = e.target.value;
      requirementsState.currentPage = 1;
      loadRequirements();
    });
  }

  const priorityFilter = document.getElementById('reqPriorityFilter');
  if (priorityFilter) {
    priorityFilter.addEventListener('change', (e) => {
      requirementsState.filters.priority = e.target.value;
      requirementsState.currentPage = 1;
      loadRequirements();
    });
  }

  // Clear filters button
  const clearFiltersBtn = document.getElementById('reqClearFilters');
  if (clearFiltersBtn) {
    clearFiltersBtn.onclick = () => {
      // Reset all filter values
      requirementsState.filters = {
        search: '',
        requirement_type: '',
        state: '',
        priority: '',
        verification_status: ''
      };

      // Reset UI elements
      if (searchInput) searchInput.value = '';
      if (typeFilter) typeFilter.value = '';
      if (stateFilter) stateFilter.value = '';
      if (priorityFilter) priorityFilter.value = '';

      // Reload data
      requirementsState.currentPage = 1;
      loadRequirements();
    };
  }

  // Refresh button
  const refreshBtn = document.getElementById('reqRefreshBtn');
  if (refreshBtn) {
    refreshBtn.onclick = () => loadRequirements();
  }

  // Details panel handlers
  const closeDetailsBtn = document.getElementById('reqCloseDetails');
  if (closeDetailsBtn) {
    closeDetailsBtn.onclick = () => hideRequirementDetails();
  }

  const dasReviewBtn = document.getElementById('reqDASReviewBtn');
  if (dasReviewBtn) {
    dasReviewBtn.onclick = () => startDASReview();
  }

  const editBtn = document.getElementById('reqEditBtn');
  if (editBtn) {
    editBtn.onclick = () => editSelectedRequirement();
  }

  const publishBtn = document.getElementById('reqPublishBtn');
  if (publishBtn) {
    publishBtn.onclick = () => {
      if (requirementsState.selectedRequirement) {
        publishRequirement(requirementsState.selectedRequirement.requirement_id);
      }
    };
  }

  const unpublishBtn = document.getElementById('reqUnpublishBtn');
  if (unpublishBtn) {
    unpublishBtn.onclick = () => {
      if (requirementsState.selectedRequirement) {
        const confirmed = confirm(`Are you sure you want to unpublish "${requirementsState.selectedRequirement.requirement_identifier}"?\n\nThis will revert the requirement to "approved" state.`);
        if (confirmed) {
          unpublishRequirement(requirementsState.selectedRequirement.requirement_id);
        }
      }
    };
  }

  const unimportBtn = document.getElementById('reqUnimportBtn');
  if (unimportBtn) {
    unimportBtn.onclick = () => {
      if (requirementsState.selectedRequirement) {
        const req = requirementsState.selectedRequirement;
        const sourceInfo = req.source_namespace_path ?
          `\n\nSource: ${req.source_namespace_path}` : '';

        const confirmed = confirm(
          `Are you sure you want to un-import "${req.requirement_identifier}"?` +
          sourceInfo +
          `\n\nThis will permanently remove the imported requirement from this project. The original requirement in the source project will remain unchanged.`
        );

        if (confirmed) {
          unimportRequirement(req.requirement_id);
        }
      }
    };
  }

  const batchPublishBtn = document.getElementById('reqBatchPublishBtn');
  if (batchPublishBtn) {
    batchPublishBtn.onclick = () => batchPublishRequirements();
  }
}

// Load requirements from API
export async function loadRequirements() {
  const state = getAppState();
  const projectId = state.activeProject?.projectId || localStorage.getItem('active_project_id');

  if (!projectId) {
    updateRequirementsTable([], 0);
    return;
  }

  // Show loading state
  const container = document.getElementById('requirementsTableContainer');

  if (container) {
    container.innerHTML = `
      <div style="text-align:center; padding:40px; color:var(--muted-color);">
        <div style="animation: spin 1s linear infinite; width:24px; height:24px; margin:0 auto 12px;">⚙️</div>
        Loading requirements...
      </div>
    `;
  }

  try {
    // Build query parameters
    const params = new URLSearchParams({
      page: requirementsState.currentPage.toString(),
      page_size: requirementsState.pageSize.toString(),
      sort_by: requirementsState.sorting.sort_by,
      sort_order: requirementsState.sorting.sort_order
    });

    // Add filters
    Object.entries(requirementsState.filters).forEach(([key, value]) => {
      if (value) {
        params.append(key, value);
      }
    });

    const result = await ApiClient.get(`/api/requirements/projects/${projectId}/requirements?${params}`);

    updateRequirementsTable(result.requirements, result.pagination.total_items, result.pagination);

  } catch (error) {
    console.error('Error loading requirements:', error);

    // Show error state
    if (container) {
      container.innerHTML = `
        <div style="text-align:center; padding:40px; color:var(--error-color);">
          <div style="margin-bottom:12px;">❌</div>
          Error loading requirements: ${error.message}
          <div style="margin-top:12px;">
            <button onclick="window.requirementsWorkbench.loadRequirements()" class="btn btn-sm">Retry</button>
          </div>
        </div>
      `;
    }
  }
}

// Placeholder functions - these will be implemented in subsequent commits
function updateRequirementsTable(requirements, totalItems, pagination) {
  console.log('updateRequirementsTable called', requirements.length, totalItems);
  // TODO: Implement full table rendering
}

function showExtractRequirementsModal() {
  console.log('showExtractRequirementsModal called');
  // TODO: Implement modal
}

function showCreateRequirementModal() {
  console.log('showCreateRequirementModal called');
  // TODO: Implement modal
}

function showImportRequirementsModal() {
  console.log('showImportRequirementsModal called');
  // TODO: Implement modal
}

function hideRequirementDetails() {
  console.log('hideRequirementDetails called');
  // TODO: Implement
}

function startDASReview() {
  console.log('startDASReview called');
  // TODO: Implement
}

function editSelectedRequirement() {
  console.log('editSelectedRequirement called');
  // TODO: Implement
}

function publishRequirement(requirementId) {
  console.log('publishRequirement called', requirementId);
  // TODO: Implement
}

function unpublishRequirement(requirementId) {
  console.log('unpublishRequirement called', requirementId);
  // TODO: Implement
}

function unimportRequirement(requirementId) {
  console.log('unimportRequirement called', requirementId);
  // TODO: Implement
}

function batchPublishRequirements() {
  console.log('batchPublishRequirements called');
  // TODO: Implement
}

// Export for use in app.html
export const requirementsWorkbench = {
  initializeRequirementsWorkbench,
  loadRequirements,
  state: requirementsState
};

// Make available globally for backwards compatibility during transition
window.requirementsWorkbench = requirementsWorkbench;
window.initializeRequirementsWorkbench = initializeRequirementsWorkbench;
window.loadRequirements = loadRequirements;

