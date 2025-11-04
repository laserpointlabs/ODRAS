/**
 * Requirements Workbench UI Module
 * 
 * Complete requirements workbench functionality extracted from app.html
 * Handles requirements CRUD, extraction, import, publishing, and constraints management
 */

import { apiClient } from '../../core/api-client.js';
import { getAppState, updateAppState } from '../../core/state-manager.js';
import { subscribeToEvent, emitEvent } from '../../core/event-bus.js';
import { parseMarkdown, showToast, getCurrentProjectId } from '../../core/utils.js';

// Use apiClient as ApiClient
const ApiClient = apiClient;

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

// Global constraints state for modals
let modalConstraints = [];
let selectedRequirements = new Set();

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
  const projectId = getCurrentProjectId();

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

// Update requirements table with data
function updateRequirementsTable(requirements, totalItems, pagination = null) {
  requirementsState.requirements = requirements;
  requirementsState.totalItems = totalItems;

  // Update statistics
  const statsEl = document.getElementById('reqTableStats');
  if (statsEl) {
    if (pagination) {
      statsEl.textContent = `${totalItems} requirements (page ${pagination.page} of ${pagination.total_pages})`;
    } else {
      statsEl.textContent = `${requirements.length} requirements`;
    }
  }

  // Generate table HTML
  const container = document.getElementById('requirementsTableContainer');
  if (!container) return;

  if (requirements.length === 0) {
    // Check if we have active filters
    const hasActiveFilters = requirementsState.filters.search ||
      requirementsState.filters.requirement_type ||
      requirementsState.filters.state ||
      requirementsState.filters.priority ||
      requirementsState.filters.verification_status;

    if (hasActiveFilters) {
      // No results due to filters
      container.innerHTML = `
        <div style="text-align:center; padding:40px; color:var(--muted-color);">
          <div style="margin-bottom:12px;">🔍</div>
          <div style="font-weight:600; margin-bottom:8px;">No matching requirements</div>
          <div style="font-size:12px; margin-bottom:16px;">Try adjusting your filters or search criteria</div>
          <button onclick="document.getElementById('reqClearFilters').click()" class="btn btn-sm">Clear Filters</button>
        </div>
      `;
    } else {
      // No requirements exist at all
      container.innerHTML = `
        <div style="text-align:center; padding:40px; color:var(--muted-color);">
          <div style="margin-bottom:12px;">📋</div>
          No requirements found.
          <div style="margin-top:12px;">
            <button onclick="document.getElementById('reqExtractBtn').click()" class="btn btn-sm">Extract from Document</button>
            <button onclick="document.getElementById('reqCreateBtn').click()" class="btn btn-sm">Create Manually</button>
          </div>
        </div>
      `;
    }
    return;
  }

  // Build sortable table
  const tableHtml = `
    <table style="width:100%; border-collapse:separate; border-spacing:0 4px;">
      <thead>
        <tr style="background:var(--panel-2);">
          <th style="padding:8px; text-align:center; width:40px; border-radius:6px 0 0 6px;">
            <input type="checkbox" id="selectAllRequirements" onchange="window.requirementsWorkbench.toggleSelectAllRequirements()" 
                   title="Select all requirements" />
          </th>
          <th style="padding:8px; text-align:left; cursor:pointer;" 
              onclick="window.requirementsWorkbench.sortRequirements('requirement_identifier')">
            ID ${getSortIndicator('requirement_identifier')}
          </th>
          <th style="padding:8px; text-align:left; cursor:pointer;" 
              onclick="window.requirementsWorkbench.sortRequirements('requirement_title')">
            Title ${getSortIndicator('requirement_title')}
          </th>
          <th style="padding:8px; text-align:left; cursor:pointer;" 
              onclick="window.requirementsWorkbench.sortRequirements('requirement_type')">
            Type ${getSortIndicator('requirement_type')}
          </th>
          <th style="padding:8px; text-align:left; cursor:pointer;" 
              onclick="window.requirementsWorkbench.sortRequirements('priority')">
            Priority ${getSortIndicator('priority')}
          </th>
          <th style="padding:8px; text-align:left; cursor:pointer;" 
              onclick="window.requirementsWorkbench.sortRequirements('state')">
            Status ${getSortIndicator('state')}
          </th>
          <th style="padding:8px; text-align:left; cursor:pointer;" 
              onclick="window.requirementsWorkbench.sortRequirements('verification_status')">
            Verification ${getSortIndicator('verification_status')}
          </th>
          <th style="padding:8px; text-align:center;">Confidence</th>
          <th style="padding:8px; text-align:right; border-radius:0 6px 6px 0;">Actions</th>
        </tr>
      </thead>
      <tbody>
        ${requirements.map(req => generateRequirementRow(req)).join('')}
      </tbody>
    </table>
  `;

  container.innerHTML = tableHtml;

  // Add pagination if needed
  if (pagination && pagination.total_pages > 1) {
    container.innerHTML += generatePaginationControls(pagination);
  }
}

// Generate HTML for a single requirement row
function generateRequirementRow(req) {
  const priorityColors = {
    critical: '#ef4444',
    high: '#f97316',
    medium: '#eab308',
    low: '#22c55e'
  };

  const stateColors = {
    draft: '#6b7280',
    review: '#3b82f6',
    approved: '#10b981',
    published: '#8b5cf6',
    imported: '#06b6d4',
    deprecated: '#ef4444',
    cancelled: '#9ca3af'
  };

  const typeColors = {
    functional: '#3b82f6',
    performance: '#f97316',
    safety: '#ef4444',
    security: '#dc2626',
    interface: '#8b5cf6',
    non_functional: '#6b7280'
  };

  const confidenceColor = req.extraction_confidence >= 0.8 ? '#10b981' :
    req.extraction_confidence >= 0.6 ? '#eab308' : '#ef4444';

  return `
    <tr style="background:${(req.state === 'imported' || req.is_immutable) ? '#2a2f3a' : 'var(--panel)'}; border:1px solid var(--border); border-radius:6px; cursor:pointer;"
        onclick="window.requirementsWorkbench.selectRequirement('${req.requirement_id}')"
        onmouseover="this.style.background='${(req.state === 'imported' || req.is_immutable) ? '#323946' : 'var(--panel-2)'}'"
        onmouseout="this.style.background='${(req.state === 'imported' || req.is_immutable) ? '#2a2f3a' : 'var(--panel)'}'">
      <td style="padding:8px; text-align:center;">
        <input type="checkbox" class="requirement-checkbox" value="${req.requirement_id}" 
               data-state="${req.state}" onchange="window.requirementsWorkbench.updateSelectedCount(); event.stopPropagation();" />
      </td>
      <td style="padding:8px; font-weight:600; color:var(--accent);">
        ${req.state === 'imported' ? '<span style="color:#06b6d4; margin-right:4px;" title="Imported Requirement"><svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clip-rule="evenodd"/></svg></span>' : ''}
        ${req.requirement_identifier}
        ${req.is_immutable ? '<span style="color:#6b7280; margin-left:4px;" title="Read-only"><svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd"/></svg></span>' : ''}
      </td>
      <td style="padding:8px; max-width:300px;">
        <div style="font-weight:500; margin-bottom:4px;">
          ${renderInlineMarkdown(req.requirement_title || req.requirement_text.substring(0, 80) + '...')}
        </div>
        <div style="font-size:11px; color:var(--muted-color); max-width:300px; overflow:hidden; text-overflow:ellipsis;">
          ${renderInlineMarkdown(req.requirement_text.substring(0, 120))}...
        </div>
      </td>
      <td style="padding:8px;">
        <span style="background:${typeColors[req.requirement_type] || '#6b7280'}; 
                     color:white; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:500;">
          ${req.requirement_type}
        </span>
      </td>
      <td style="padding:8px;">
        <span style="background:${priorityColors[req.priority] || '#6b7280'}; 
                     color:white; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:500;">
          ${req.priority}
        </span>
      </td>
      <td style="padding:8px;">
        <span style="background:${stateColors[req.state] || '#6b7280'}; 
                     color:white; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:500;">
          ${req.state}
        </span>
      </td>
      <td style="padding:8px;">
        <span style="color:${req.verification_status === 'passed' ? '#10b981' :
          req.verification_status === 'failed' ? '#ef4444' :
            req.verification_status === 'in_progress' ? '#3b82f6' : '#6b7280'}; 
                     font-size:11px; font-weight:500;">
          ${req.verification_status?.replace('_', ' ') || 'not started'}
        </span>
      </td>
      <td style="padding:8px; text-align:center;">
        ${req.extraction_confidence ?
          `<span style="color:${confidenceColor}; font-size:11px; font-weight:600;">
             ${Math.round(req.extraction_confidence * 100)}%
           </span>` :
          `<span style="color:var(--muted-color); font-size:11px;">manual</span>`
        }
      </td>
      <td style="padding:8px; text-align:right;">
        ${req.state === 'imported' || req.is_immutable ?
          `<span style="color:var(--muted-color); font-size:10px; font-style:italic;">Read-only</span>` :
          `<button onclick="event.stopPropagation(); window.requirementsWorkbench.editRequirement('${req.requirement_id}')" 
                  class="btn btn-sm" style="font-size:10px; padding:4px 8px;">
            Edit
          </button>
          <button onclick="event.stopPropagation(); window.requirementsWorkbench.requestDASReview('${req.requirement_id}')" 
                  class="btn btn-primary btn-sm" style="font-size:10px; padding:4px 8px; margin-left:4px;">
            DAS Review
          </button>`
        }
      </td>
    </tr>
  `;
}

// Generate pagination controls
function generatePaginationControls(pagination) {
  const { page, total_pages, total_items } = pagination;

  if (total_pages <= 1) return '';

  let paginationHtml = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:12px; padding:12px; background:var(--panel-2); border-radius:6px;">
      <div style="font-size:12px; color:var(--muted-color);">
        Page ${page} of ${total_pages} (${total_items} total)
      </div>
      <div style="display:flex; gap:4px;">
  `;

  // Previous button
  if (page > 1) {
    paginationHtml += `<button onclick="window.requirementsWorkbench.goToPage(${page - 1})" class="btn btn-sm">Previous</button>`;
  }

  // Page numbers (show current page and a few around it)
  const startPage = Math.max(1, page - 2);
  const endPage = Math.min(total_pages, page + 2);

  for (let p = startPage; p <= endPage; p++) {
    if (p === page) {
      paginationHtml += `<button class="btn btn-sm btn-primary" disabled>${p}</button>`;
    } else {
      paginationHtml += `<button onclick="window.requirementsWorkbench.goToPage(${p})" class="btn btn-sm">${p}</button>`;
    }
  }

  // Next button
  if (page < total_pages) {
    paginationHtml += `<button onclick="window.requirementsWorkbench.goToPage(${page + 1})" class="btn btn-sm">Next</button>`;
  }

  paginationHtml += `
      </div>
    </div>
  `;

  return paginationHtml;
}

// Get sort indicator for column headers
function getSortIndicator(column) {
  if (requirementsState.sorting.sort_by !== column) {
    return '<span style="color:var(--muted-color);">⇅</span>';
  }
  return requirementsState.sorting.sort_order === 'asc' ?
    '<span style="color:var(--accent);">↑</span>' :
    '<span style="color:var(--accent);">↓</span>';
}

// Sort requirements by column
export function sortRequirements(column) {
  if (requirementsState.sorting.sort_by === column) {
    // Toggle sort direction
    requirementsState.sorting.sort_order =
      requirementsState.sorting.sort_order === 'asc' ? 'desc' : 'asc';
  } else {
    // New column, default to ascending
    requirementsState.sorting.sort_by = column;
    requirementsState.sorting.sort_order = 'asc';
  }

  requirementsState.currentPage = 1; // Reset to first page
  loadRequirements();
}

// Go to specific page
export function goToPage(pageNum) {
  requirementsState.currentPage = pageNum;
  loadRequirements();
}

// Select a requirement and show details
export function selectRequirement(requirementId) {
  const requirement = requirementsState.requirements.find(r => r.requirement_id === requirementId);
  if (!requirement) return;

  requirementsState.selectedRequirement = requirement;
  showRequirementDetails(requirement);
}

// Show requirement details panel
function showRequirementDetails(requirement) {
  const panel = document.getElementById('requirementDetailsPanel');
  const content = document.getElementById('requirementDetailsContent');

  if (!panel || !content) return;

  // Generate details HTML
  const detailsHtml = `
    <div style="display:grid; gap:16px;">
      <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px;">
        <div>
          <div style="font-size:11px; color:var(--muted-color); font-weight:600; margin-bottom:4px;">IDENTIFIER</div>
          <div style="font-weight:600; color:var(--accent);">${requirement.requirement_identifier}</div>
        </div>
        <div>
          <div style="font-size:11px; color:var(--muted-color); font-weight:600; margin-bottom:4px;">TYPE</div>
          <div>${requirement.requirement_type}</div>
        </div>
        <div>
          <div style="font-size:11px; color:var(--muted-color); font-weight:600; margin-bottom:4px;">PRIORITY</div>
          <div>${requirement.priority}</div>
        </div>
        <div>
          <div style="font-size:11px; color:var(--muted-color); font-weight:600; margin-bottom:4px;">STATUS</div>
          <div>${requirement.state}</div>
        </div>
      </div>

      <div>
        <div style="font-size:11px; color:var(--muted-color); font-weight:600; margin-bottom:8px;">REQUIREMENT TEXT</div>
        <div style="padding:12px; background:var(--panel-2); border:1px solid var(--border); border-radius:6px; line-height:1.5;" class="das-markdown">
          ${parseMarkdown(requirement.requirement_text || '')}
        </div>
      </div>

      ${requirement.requirement_rationale ? `
        <div>
          <div style="font-size:11px; color:var(--muted-color); font-weight:600; margin-bottom:8px;">RATIONALE</div>
          <div style="padding:12px; background:var(--panel-2); border:1px solid var(--border); border-radius:6px; line-height:1.5;" class="das-markdown">
            ${parseMarkdown(requirement.requirement_rationale)}
          </div>
        </div>
      ` : ''}

      ${requirement.verification_criteria ? `
        <div>
          <div style="font-size:11px; color:var(--muted-color); font-weight:600; margin-bottom:8px;">VERIFICATION CRITERIA</div>
          <div style="padding:12px; background:var(--panel-2); border:1px solid var(--border); border-radius:6px; line-height:1.5;" class="das-markdown">
            ${parseMarkdown(requirement.verification_criteria)}
          </div>
        </div>
      ` : ''}

      <div id="requirementConstraints-${requirement.requirement_id}">
        <!-- Constraints will be loaded here -->
      </div>

      <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; font-size:12px; color:var(--muted-color);">
        <div>
          Created: ${new Date(requirement.created_at).toLocaleString()}<br/>
          ${requirement.state === 'imported' ?
          `<span style="color:#06b6d4;"><svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor" style="margin-right:4px;"><path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clip-rule="evenodd"/></svg>Imported from source project</span>` :
            (requirement.extraction_confidence ? `Extraction Confidence: ${Math.round(requirement.extraction_confidence * 100)}%` : 'Manual Entry')
          }
        </div>
        <div>
          Updated: ${new Date(requirement.updated_at).toLocaleString()}<br/>
          Version: ${requirement.version || 1}
          ${requirement.is_immutable ? '<br/><span style="color:#f59e0b;"><svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor" style="margin-right:4px;"><path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd"/></svg>Read-only (Imported)</span>' : ''}
        </div>
      </div>

      ${requirement.state === 'imported' && (requirement.source_namespace_path || requirement.source_project_iri) ? `
        <div style="margin-top:16px; padding:12px; background:var(--panel-2); border:1px solid var(--border); border-radius:6px; border-left:3px solid #06b6d4;">
          <div style="font-size:11px; color:var(--accent); font-weight:600; margin-bottom:8px; display:flex; align-items:center; gap:4px;">
            <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clip-rule="evenodd"/></svg>SOURCE PROJECT TRACEABILITY
          </div>
          <div style="font-size:12px; color:var(--text); line-height:1.4;">
            ${requirement.source_namespace_path ? `<strong>Namespace:</strong> ${requirement.source_namespace_path}<br/>` : ''}
            ${requirement.source_project_iri ? `<strong>Project IRI:</strong> <code style="background:var(--bg); padding:2px 4px; border-radius:3px; font-family:monospace; font-size:11px;">${requirement.source_project_iri}</code><br/>` : ''}
            <strong>Source Requirement ID:</strong> ${requirement.source_requirement_id || requirement.requirement_id}<br/>
            ${requirement.source_namespace_prefix ? `<strong>Namespace Prefix:</strong> ${requirement.source_namespace_prefix}` : ''}
          </div>
          <div style="margin-top:6px; font-size:11px; color:var(--muted-color); font-style:italic;">
            This requirement was imported and cannot be modified. Changes must be made in the source project.
          </div>
        </div>
      ` : ''}
    </div>
  `;

  content.innerHTML = detailsHtml;
  panel.style.display = 'block';

  // Load constraints for this requirement
  loadRequirementConstraintsForDetails(requirement.requirement_id);

  // Load notes for this requirement
  loadRequirementNotes(requirement.requirement_id);

  // Update publish button visibility based on requirement state
  updatePublishButtonVisibility(requirement);
}

// Hide requirement details panel
function hideRequirementDetails() {
  const panel = document.getElementById('requirementDetailsPanel');
  if (panel) {
    panel.style.display = 'none';
  }
  requirementsState.selectedRequirement = null;
}

// Load notes for a requirement
async function loadRequirementNotes(requirementId) {
  const projectId = getCurrentProjectId();
  if (!projectId) return;

  try {
    const notes = await ApiClient.get(`/api/requirements/projects/${projectId}/requirements/${requirementId}/notes`);

    // Add notes section to details panel if notes exist
    if (notes.length > 0) {
      const content = document.getElementById('requirementDetailsContent');
      if (content) {
        const notesHtml = `
          <div style="margin-top:16px; padding-top:16px; border-top:1px solid var(--border);">
            <div style="font-size:11px; color:var(--muted-color); font-weight:600; margin-bottom:8px;">
              COLLABORATIVE NOTES (${notes.length})
            </div>
            ${notes.map(note => `
              <div style="margin-bottom:12px; padding:8px; background:var(--panel-2); border-radius:4px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                  <span style="font-size:11px; color:var(--accent); font-weight:600;">${note.note_type}</span>
                  <span style="font-size:11px; color:var(--muted-color);">
                    ${new Date(note.created_at).toLocaleString()} by ${note.created_by_name || 'Unknown'}
                  </span>
                </div>
                <div style="font-size:12px; line-height:1.4;">${note.note_text}</div>
              </div>
            `).join('')}
          </div>
        `;
        content.innerHTML += notesHtml;
      }
    }

  } catch (error) {
    console.error('Error loading requirement notes:', error);
  }
}

// Start DAS review for selected requirement
async function startDASReview() {
  const requirement = requirementsState.selectedRequirement;
  if (!requirement) {
    alert('No requirement selected');
    return;
  }

  const projectId = getCurrentProjectId();
  if (!projectId) return;

  // Show loading state
  const dasBtn = document.getElementById('reqDASReviewBtn');
  if (dasBtn) {
    dasBtn.disabled = true;
    dasBtn.innerHTML = `
      <div style="animation: spin 1s linear infinite; width:14px; height:14px; margin-right:4px;">⚙️</div>
      Reviewing...
    `;
  }

  try {
    const reviewResult = await ApiClient.post(
      `/api/requirements/projects/${projectId}/requirements/${requirement.requirement_id}/das-review`,
      {
        review_type: 'improvement',
        include_context: true,
        focus_areas: ['clarity', 'testability', 'completeness']
      }
    );

    // Show DAS review in a modal
    showDASReviewModal(reviewResult);

  } catch (error) {
    console.error('Error requesting DAS review:', error);
    showToast(`DAS review failed: ${error.message}`, true);
  } finally {
    // Restore button
    if (dasBtn) {
      dasBtn.disabled = false;
      dasBtn.innerHTML = `
        <svg style="width:14px; height:14px; margin-right:4px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9 11l3 3L22 4"/>
          <path d="M21 12c-.12 2.51-.61 4.92-1.44 7.08"/>
          <path d="M16 19.35l-.35.35c-1.96 1.96-5.14 1.96-7.1 0l-.35-.35"/>
        </svg>
        DAS Review
      `;
    }
  }
}

// Show DAS review results in a modal
function showDASReviewModal(reviewResult) {
  // Create modal overlay
  const modal = document.createElement('div');
  modal.style.cssText = `
    position: fixed; top: 0; left: 0; right: 0; bottom: 0; 
    background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 10000;
  `;

  const modalContent = document.createElement('div');
  modalContent.style.cssText = `
    background: var(--panel); border: 1px solid var(--border); border-radius: 8px; 
    width: 90%; max-width: 800px; max-height: 80vh; overflow: auto; padding: 20px;
  `;

  modalContent.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
      <h3 style="margin:0;">DAS Requirement Review</h3>
      <button onclick="this.closest('.das-modal').remove()" class="btn" style="padding:4px 8px;">
        <svg style="width:16px; height:16px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6L6 18M6 6l12 12"/>
        </svg>
      </button>
    </div>

    <div style="margin-bottom:16px;">
      <div style="font-size:11px; color:var(--muted-color); font-weight:600; margin-bottom:8px;">ORIGINAL REQUIREMENT</div>
      <div style="padding:12px; background:var(--panel-2); border:1px solid var(--border); border-radius:6px;" class="das-markdown">
        ${parseMarkdown(requirementsState.selectedRequirement.requirement_text)}
      </div>
    </div>

    <div style="margin-bottom:16px;">
      <div style="font-size:11px; color:var(--muted-color); font-weight:600; margin-bottom:8px;">DAS ANALYSIS & SUGGESTIONS</div>
      <div style="padding:12px; background:var(--panel-2); border:1px solid var(--border); border-radius:6px; line-height:1.5;" class="das-markdown">
        ${parseMarkdown(reviewResult.das_response || '')}
      </div>
    </div>

    ${reviewResult.suggestions && reviewResult.suggestions.length > 0 ? `
      <div style="margin-bottom:16px;">
        <div style="font-size:11px; color:var(--muted-color); font-weight:600; margin-bottom:8px;">KEY SUGGESTIONS</div>
        ${reviewResult.suggestions.map(suggestion => `
          <div style="padding:8px; margin-bottom:8px; background:var(--success-bg); border:1px solid var(--success); border-radius:4px; font-size:12px;">
            ${renderInlineMarkdown(suggestion)}
          </div>
        `).join('')}
      </div>
    ` : ''}

    <div style="display:flex; gap:8px; justify-content:flex-end;">
      <button onclick="this.closest('.das-modal').remove()" class="btn">Close</button>
      <button onclick="window.requirementsWorkbench.acceptDASReview('${reviewResult.review_id}')" class="btn btn-primary">Apply Suggestions</button>
    </div>
  `;

  modal.className = 'das-modal';
  modal.appendChild(modalContent);
  document.body.appendChild(modal);

  // Close modal on outside click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.remove();
    }
  });
}

// Accept DAS review suggestions
export async function acceptDASReview(reviewId) {
  // For demo purposes, just show a success message
  showToast('DAS suggestions accepted! (Implementation in progress)');

  // Close modal
  const modal = document.querySelector('.das-modal');
  if (modal) modal.remove();

  // Reload requirement details
  if (requirementsState.selectedRequirement) {
    showRequirementDetails(requirementsState.selectedRequirement);
  }
}

// Show extract requirements modal
function showExtractRequirementsModal() {
  const projectId = getCurrentProjectId();
  if (!projectId) {
    alert('Please select a project first');
    return;
  }

  // Create modal for document selection and extraction configuration
  const modal = document.createElement('div');
  modal.style.cssText = `
    position: fixed; top: 0; left: 0; right: 0; bottom: 0; 
    background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 10000;
  `;

  const modalContent = document.createElement('div');
  modalContent.style.cssText = `
    background: var(--panel); border: 1px solid var(--border); border-radius: 8px; 
    width: 90%; max-width: 600px; padding: 20px;
  `;

  modalContent.innerHTML = `
    <div style="margin-bottom:16px;">
      <h3>Extract Requirements from Document</h3>
      <div class="muted">Select a document and configure extraction settings</div>
    </div>

    <div style="margin-bottom:16px;">
      <label style="display:block; font-weight:600; margin-bottom:8px;">Select Document:</label>
      <select id="extractDocumentSelect" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px;">
        <option value="">Loading documents...</option>
      </select>
    </div>

    <div style="margin-bottom:16px;">
      <label style="display:block; font-weight:600; margin-bottom:8px;">Job Name:</label>
      <input type="text" id="extractJobName" value="Requirements Extraction ${new Date().toISOString().slice(0, 16)}" 
             style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px;" />
    </div>

    <div style="margin-bottom:16px;">
      <label style="display:block; font-weight:600; margin-bottom:8px;">Minimum Confidence:</label>
      <input type="range" id="extractMinConfidence" min="0.5" max="1.0" step="0.05" value="0.7" 
             style="width:100%;" />
      <div style="display:flex; justify-content:space-between; font-size:12px; color:var(--muted-color);">
        <span>50%</span>
        <span id="confidenceDisplay">70%</span>
        <span>100%</span>
      </div>
    </div>

    <div style="margin-bottom:16px;">
      <label style="display:flex; align-items:center; gap:8px;">
        <input type="checkbox" id="extractConstraints" checked />
        Extract constraints (thresholds, objectives, KPCs, KPPs)
      </label>
    </div>

    <div style="display:flex; gap:8px; justify-content:flex-end;">
      <button onclick="this.closest('.extract-modal').remove()" class="btn">Cancel</button>
      <button onclick="window.requirementsWorkbench.startExtractionJob()" class="btn btn-primary">Start Extraction</button>
    </div>
  `;

  modal.className = 'extract-modal';
  modal.appendChild(modalContent);
  document.body.appendChild(modal);

  // Load available documents
  loadDocumentsForExtraction();

  // Update confidence display
  const confidenceSlider = document.getElementById('extractMinConfidence');
  const confidenceDisplay = document.getElementById('confidenceDisplay');
  if (confidenceSlider && confidenceDisplay) {
    confidenceSlider.addEventListener('input', (e) => {
      confidenceDisplay.textContent = `${Math.round(e.target.value * 100)}%`;
    });
  }
}

// Load documents available for extraction
async function loadDocumentsForExtraction() {
  const projectId = getCurrentProjectId();
  if (!projectId) return;

  try {
    const result = await ApiClient.get(`/api/files?project_id=${projectId}`);
    const files = result.files || [];

    const select = document.getElementById('extractDocumentSelect');
    if (select) {
      if (files.length === 0) {
        select.innerHTML = '<option value="">No documents available</option>';
      } else {
        select.innerHTML = [
          '<option value="">Select a document...</option>',
          ...files.map(file => `<option value="${file.file_id}">${file.filename} (${file.content_type || 'unknown type'})</option>`)
        ].join('');
      }
    }
  } catch (error) {
    console.error('Error loading documents:', error);
    const select = document.getElementById('extractDocumentSelect');
    if (select) {
      select.innerHTML = '<option value="">Error loading documents</option>';
    }
  }
}

// Start extraction job
export async function startExtractionJob() {
  const documentId = document.getElementById('extractDocumentSelect').value;
  const jobName = document.getElementById('extractJobName').value;
  const minConfidence = parseFloat(document.getElementById('extractMinConfidence').value);
  const extractConstraints = document.getElementById('extractConstraints').checked;

  if (!documentId) {
    alert('Please select a document');
    return;
  }

  if (!jobName.trim()) {
    alert('Please enter a job name');
    return;
  }

  const projectId = getCurrentProjectId();
  if (!projectId) return;

  try {
    // Show progress
    const startBtn = document.querySelector('.extract-modal button[onclick*="startExtractionJob"]');
    if (startBtn) {
      startBtn.disabled = true;
      startBtn.textContent = 'Extracting...';
    }

    const result = await ApiClient.post(`/api/requirements/projects/${projectId}/extract`, {
      job_name: jobName,
      source_document_id: documentId,
      min_confidence: minConfidence,
      extract_constraints: extractConstraints
    });

    // Close modal
    const modal = document.querySelector('.extract-modal');
    if (modal) modal.remove();

    // Show success message
    showToast(`Extraction completed! Created ${result.requirements_created} requirements and ${result.constraints_created} constraints.`);

    // Reload requirements table
    loadRequirements();

  } catch (error) {
    console.error('Error starting extraction job:', error);
    showToast(`Extraction failed: ${error.message}`, true);

    // Restore button
    const startBtn = document.querySelector('.extract-modal button[onclick*="startExtractionJob"]');
    if (startBtn) {
      startBtn.disabled = false;
      startBtn.textContent = 'Start Extraction';
    }
  }
}

// Show create requirement modal
function showCreateRequirementModal() {
  const projectId = getCurrentProjectId();
  if (!projectId) {
    alert('Please select a project first');
    return;
  }

  const modal = document.createElement('div');
  modal.style.cssText = `
    position: fixed; top: 0; left: 0; right: 0; bottom: 0; 
    background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 10000;
  `;

  const modalContent = document.createElement('div');
  modalContent.style.cssText = `
    background: var(--panel); border: 1px solid var(--border); border-radius: 8px; 
    width: 90%; max-width: 700px; max-height: 90vh; overflow: auto; padding: 20px;
  `;

  modalContent.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
      <h3 style="margin:0; color:var(--accent);">Create New Requirement</h3>
      <button onclick="this.closest('.create-req-modal').remove()" class="btn" style="padding:4px 8px;">
        <svg style="width:16px; height:16px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6L6 18M6 6l12 12"/>
        </svg>
      </button>
    </div>

    <form id="createRequirementForm" style="display:grid; gap:16px;">
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
        <div>
          <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">TITLE *</label>
          <input type="text" id="newReqTitle" value="" 
                 style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2); color:var(--text);" 
                 maxlength="500" placeholder="Enter a clear, concise title..." required>
        </div>
        
        <div>
          <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">TYPE *</label>
          <select id="newReqType" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2); color:var(--text);" required>
            <option value="">Select type...</option>
            <option value="functional" selected>Functional</option>
            <option value="non_functional">Non-Functional</option>
            <option value="performance">Performance</option>
            <option value="safety">Safety</option>
            <option value="security">Security</option>
            <option value="interface">Interface</option>
            <option value="operational">Operational</option>
            <option value="design">Design</option>
            <option value="implementation">Implementation</option>
          </select>
        </div>
      </div>

      <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px;">
        <div>
          <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">PRIORITY</label>
          <select id="newReqPriority" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2); color:var(--text);">
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium" selected>Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
        
        <div>
          <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">STATUS</label>
          <select id="newReqState" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2); color:var(--text);">
            <option value="draft" selected>Draft</option>
            <option value="review">Review</option>
            <option value="approved">Approved</option>
          </select>
        </div>
        
        <div>
          <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">VERIFICATION METHOD</label>
          <select id="newReqVerificationMethod" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2); color:var(--text);">
            <option value="">Not specified</option>
            <option value="test">Test</option>
            <option value="analysis">Analysis</option>
            <option value="inspection">Inspection</option>
            <option value="demonstration">Demonstration</option>
            <option value="review">Review</option>
          </select>
        </div>
      </div>

      <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
        <div>
          <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">CATEGORY</label>
          <input type="text" id="newReqCategory" value="" 
                 style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2); color:var(--text);" 
                 placeholder="e.g. User Interface, Data Management">
        </div>
        
        <div>
          <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">SUBCATEGORY</label>
          <input type="text" id="newReqSubcategory" value="" 
                 style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2); color:var(--text);" 
                 placeholder="e.g. Login, Database Access">
        </div>
      </div>

      <div>
        <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">REQUIREMENT TEXT *</label>
        <textarea id="newReqText" rows="4" 
                  style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2); color:var(--text); resize:vertical;" 
                  placeholder="The system SHALL... (use clear language with modal verbs)" required></textarea>
        <div style="font-size:11px; color:var(--muted-color); margin-top:4px;">
          💡 Tip: Use modal verbs like SHALL, MUST, WILL for mandatory requirements, SHOULD for recommended features
        </div>
      </div>

      <div>
        <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">RATIONALE</label>
        <textarea id="newReqRationale" rows="3" 
                  style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2); color:var(--text); resize:vertical;" 
                  placeholder="Why is this requirement necessary? What business need does it address?"></textarea>
      </div>

      <div>
        <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">VERIFICATION CRITERIA</label>
        <textarea id="newReqVerificationCriteria" rows="2" 
                  style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2); color:var(--text); resize:vertical;" 
                  placeholder="How will this requirement be verified or tested?"></textarea>
      </div>

      <div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <label style="font-weight:600; font-size:12px; color:var(--muted-color);">CONSTRAINTS</label>
          <div style="display:flex; gap:8px;">
            <button type="button" onclick="window.requirementsWorkbench.addNewConstraint()" class="btn btn-sm" style="font-size:11px; padding:4px 8px;">
              <svg style="width:12px; height:12px; margin-right:4px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 5v14M5 12h14"/>
              </svg>
              Add Constraint
            </button>
            <button type="button" onclick="window.requirementsWorkbench.askDASForConstraints('create')" class="btn btn-sm" style="font-size:11px; padding:4px 8px; background:var(--primary); color:white; opacity:0.6;" disabled title="Coming soon!">
              <svg style="width:12px; height:12px; margin-right:4px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 11l3 3L22 4"/>
                <path d="M21 12c-.12 2.51-.61 4.92-1.44 7.08"/>
              </svg>
              Ask DAS
            </button>
          </div>
        </div>
        <div id="newReqConstraintsContainer" style="min-height:40px; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2);">
          <div style="text-align:center; color:var(--muted-color); font-size:11px; padding:16px;">
            No constraints defined. Click "Add Constraint" to add manual constraints or "Ask DAS" to auto-extract from requirement text.
          </div>
        </div>
      </div>

      <div style="display:flex; gap:8px; justify-content:flex-end; padding-top:12px; border-top:1px solid var(--border);">
        <button type="button" onclick="this.closest('.create-req-modal').remove()" class="btn">Cancel</button>
        <button type="submit" class="btn btn-primary">Create Requirement</button>
      </div>
    </form>
  `;

  modal.className = 'create-req-modal';
  modal.appendChild(modalContent);
  document.body.appendChild(modal);

  // Initialize constraints for create modal
  modalConstraints = [];
  const constraintsContainer = document.getElementById('newReqConstraintsContainer');
  renderConstraints(constraintsContainer, 'create');

  // Handle form submission
  const form = document.getElementById('createRequirementForm');
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    saveNewRequirement();
  });

  // Focus on title field
  setTimeout(() => {
    document.getElementById('newReqTitle').focus();
  }, 100);
}

// Save new requirement
async function saveNewRequirement() {
  const projectId = getCurrentProjectId();
  if (!projectId) {
    alert('No project selected');
    return;
  }

  // Get form values
  const formData = {
    requirement_title: document.getElementById('newReqTitle').value.trim(),
    requirement_text: document.getElementById('newReqText').value.trim(),
    requirement_rationale: document.getElementById('newReqRationale').value.trim() || null,
    requirement_type: document.getElementById('newReqType').value,
    category: document.getElementById('newReqCategory').value.trim() || null,
    subcategory: document.getElementById('newReqSubcategory').value.trim() || null,
    priority: document.getElementById('newReqPriority').value,
    verification_method: document.getElementById('newReqVerificationMethod').value || null,
    verification_criteria: document.getElementById('newReqVerificationCriteria').value.trim() || null
  };

  // Validate required fields
  if (!formData.requirement_title) {
    alert('Title is required');
    document.getElementById('newReqTitle').focus();
    return;
  }
  if (!formData.requirement_text) {
    alert('Requirement text is required');
    document.getElementById('newReqText').focus();
    return;
  }
  if (formData.requirement_text.length < 10) {
    alert('Requirement text must be at least 10 characters');
    document.getElementById('newReqText').focus();
    return;
  }
  if (!formData.requirement_type) {
    alert('Requirement type is required');
    document.getElementById('newReqType').focus();
    return;
  }

  // Show saving state
  const saveBtn = document.querySelector('.create-req-modal .btn-primary');
  const originalText = saveBtn.textContent;
  saveBtn.disabled = true;
  saveBtn.textContent = 'Creating...';

  try {
    const newRequirement = await ApiClient.post(`/api/requirements/projects/${projectId}/requirements`, formData);

    // Close modal
    document.querySelector('.create-req-modal').remove();

    // Save any constraints that were added
    if (modalConstraints && modalConstraints.length > 0) {
      await saveConstraintsForRequirement(newRequirement.requirement_id, modalConstraints);
    }

    // Show success message
    showToast('Requirement created successfully', false);

    // Refresh the table
    await loadRequirements();

    // Optionally select the new requirement
    requirementsState.selectedRequirement = newRequirement;
    showRequirementDetails(newRequirement);

  } catch (error) {
    console.error('Error creating requirement:', error);
    alert(`Failed to create requirement: ${error.message}`);
  } finally {
    // Restore button state
    saveBtn.disabled = false;
    saveBtn.textContent = originalText;
  }
}

// =====================================
// CONSTRAINTS MANAGEMENT
// =====================================

// Add constraint to create modal
export function addNewConstraint() {
  const container = document.getElementById('newReqConstraintsContainer');
  const constraintId = 'constraint_' + Date.now();

  const constraint = {
    id: constraintId,
    name: '',
    description: '',
    constraint_type: 'threshold',
    value_type: 'text',
    text_value: ''
  };

  modalConstraints.push(constraint);
  renderConstraints(container, 'create');
}

// Add constraint to edit modal
export function addEditConstraint() {
  const container = document.getElementById('reqConstraintsContainer');
  const constraintId = 'constraint_' + Date.now();

  const constraint = {
    id: constraintId,
    name: '',
    description: '',
    constraint_type: 'threshold',
    value_type: 'text',
    text_value: ''
  };

  modalConstraints.push(constraint);
  renderConstraints(container, 'edit');
}

// Placeholder for future DAS integration
export function askDASForConstraints(modalType) {
  alert('DAS constraint extraction coming in future release!\n\nThis will analyze your requirement text and automatically suggest relevant constraints like thresholds, objectives, and performance parameters.');
}

// Render constraints in container
function renderConstraints(container, modalType) {
  if (!container) return;

  if (modalConstraints.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; color:var(--muted-color); font-size:11px; padding:16px;">
        No constraints defined. Click "Add Constraint" to add manual constraints or "Ask DAS" to auto-extract from requirement text.
      </div>
    `;
    return;
  }

  const constraintsHtml = modalConstraints.map(constraint => `
    <div style="display:grid; grid-template-columns:1fr 1fr auto; gap:8px; align-items:end; margin-bottom:8px; padding:8px; background:var(--panel); border:1px solid var(--border); border-radius:4px;">
      <div>
        <label style="display:block; font-size:10px; color:var(--muted-color); margin-bottom:2px;">TYPE</label>
        <select onchange="window.requirementsWorkbench.updateConstraint('${constraint.id}', 'constraint_type', this.value)" 
                style="width:100%; padding:4px; border:1px solid var(--border); border-radius:3px; background:var(--panel-2); font-size:11px;">
          <option value="threshold" ${constraint.constraint_type === 'threshold' ? 'selected' : ''}>Threshold</option>
          <option value="objective" ${constraint.constraint_type === 'objective' ? 'selected' : ''}>Objective</option>
          <option value="kpc" ${constraint.constraint_type === 'kpc' ? 'selected' : ''}>KPC</option>
          <option value="kpp" ${constraint.constraint_type === 'kpp' ? 'selected' : ''}>KPP</option>
          <option value="design" ${constraint.constraint_type === 'design' ? 'selected' : ''}>Design</option>
          <option value="interface" ${constraint.constraint_type === 'interface' ? 'selected' : ''}>Interface</option>
          <option value="environmental" ${constraint.constraint_type === 'environmental' ? 'selected' : ''}>Environmental</option>
          <option value="equation" ${constraint.constraint_type === 'equation' ? 'selected' : ''}>Equation</option>
        </select>
      </div>
      <div>
        <label style="display:block; font-size:10px; color:var(--muted-color); margin-bottom:2px;">NAME & VALUE</label>
        <input type="text" value="${(constraint.name || '').replace(/"/g, '&quot;')}" 
               onchange="window.requirementsWorkbench.updateConstraint('${constraint.id}', 'name', this.value)"
               placeholder="e.g. Maximum range, Response time"
               style="width:100%; padding:4px; border:1px solid var(--border); border-radius:3px; background:var(--panel-2); font-size:11px;">
      </div>
      <div>
        <button onclick="window.requirementsWorkbench.removeConstraint('${constraint.id}', '${modalType}')" 
                class="btn" style="padding:4px 6px; background:var(--error); color:white; font-size:10px;" 
                title="Remove constraint">
          <svg style="width:10px; height:10px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6L6 18M6 6l12 12"/>
          </svg>
        </button>
      </div>
      <div style="grid-column:1/-1;">
        ${constraint.constraint_type === 'equation' ? `
          <div style="display:grid; grid-template-columns:1fr auto; gap:8px; align-items:center;">
            <div>
              <label style="display:block; font-size:10px; color:var(--muted-color); margin-bottom:2px;">EQUATION EXPRESSION</label>
              <input type="text" value="${(constraint.equation_expression || '').replace(/"/g, '&quot;')}" 
                     onchange="window.requirementsWorkbench.updateConstraint('${constraint.id}', 'equation_expression', this.value)"
                     placeholder="e.g. ResponseTime <= 30, Velocity = Distance / Time"
                     style="width:100%; padding:4px; border:1px solid var(--border); border-radius:3px; background:var(--panel-2); font-size:11px; font-family:monospace;">
            </div>
            <button onclick="window.requirementsWorkbench.openParameterPicker('${constraint.id}')" class="btn btn-sm" style="font-size:10px; padding:4px 8px; opacity:0.6;" disabled title="SysMLv2-lite Parameter Picker - Coming Soon!">
              <svg style="width:12px; height:12px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                <polyline points="3.27,6.96 12,12.01 20.73,6.96"/>
                <line x1="12" y1="22.08" x2="12" y2="12"/>
              </svg>
              Ontology
            </button>
          </div>
          <div style="margin-top:4px;">
            <input type="text" value="${(constraint.text_value || '').replace(/"/g, '&quot;')}" 
                   onchange="window.requirementsWorkbench.updateConstraint('${constraint.id}', 'text_value', this.value)"
                   placeholder="Description (e.g. 'System response time must not exceed target threshold')"
                   style="width:100%; padding:4px; border:1px solid var(--border); border-radius:3px; background:var(--panel-2); font-size:11px;">
          </div>
        ` : `
          <input type="text" value="${(constraint.text_value || '').replace(/"/g, '&quot;')}" 
                 onchange="window.requirementsWorkbench.updateConstraint('${constraint.id}', 'text_value', this.value)"
                 placeholder="Constraint description/value (e.g. '50 km maximum', 'Less than 2 hours', 'Encrypted transmission')"
                 style="width:100%; padding:4px; border:1px solid var(--border); border-radius:3px; background:var(--panel-2); font-size:11px;">
        `}
      </div>
    </div>
  `).join('');

  container.innerHTML = constraintsHtml;
}

// Update constraint value
export function updateConstraint(constraintId, field, value) {
  const constraint = modalConstraints.find(c => c.id === constraintId);
  if (constraint) {
    constraint[field] = value;

    // When constraint type changes, update value_type accordingly
    if (field === 'constraint_type') {
      if (value === 'equation') {
        constraint.value_type = 'equation';
        constraint.equation_expression = constraint.equation_expression || '';
      } else {
        constraint.value_type = 'text';
      }

      // Re-render to show/hide equation fields
      const modalType = document.querySelector('.create-req-modal') ? 'create' : 'edit';
      const containerName = modalType === 'create' ? 'newReqConstraintsContainer' : 'reqConstraintsContainer';
      const container = document.getElementById(containerName);
      if (container) renderConstraints(container, modalType);
    }
  }
}

// Placeholder for future SysMLv2-lite parameter picker
export function openParameterPicker(constraintId) {
  alert('SysMLv2-lite Parameter Picker Coming Soon!\n\nThis will allow you to:\n• Browse ontology-defined parameters\n• Select data properties with proper units\n• Build semantically validated equations\n• Ensure mathematical consistency across requirements\n\nExample: Select "ResponseTime" from ontology → Auto-suggests units and valid operations');
}

// Remove constraint
export function removeConstraint(constraintId, modalType) {
  const constraint = modalConstraints.find(c => c.id === constraintId);

  // Mark existing constraints for deletion
  if (constraint && constraint.existing) {
    constraint.deleted = true;
  }

  // Remove from UI array
  modalConstraints = modalConstraints.filter(c => c.id !== constraintId);

  const containerName = modalType === 'create' ? 'newReqConstraintsContainer' : 'reqConstraintsContainer';
  const container = document.getElementById(containerName);
  if (container) renderConstraints(container, modalType);
}

// Load existing constraints for edit modal
async function loadConstraintsForEdit(requirementId) {
  try {
    const projectId = getCurrentProjectId();
    const constraints = await ApiClient.get(`/api/requirements/projects/${projectId}/requirements/${requirementId}/constraints`);

    modalConstraints = constraints.map(c => ({
      id: c.constraint_id,
      name: c.constraint_name,
      description: c.constraint_description,
      constraint_type: c.constraint_type,
      value_type: c.value_type,
      text_value: c.text_value || `${c.numeric_value || ''}${c.numeric_unit ? ' ' + c.numeric_unit : ''}`,
      equation_expression: c.equation_expression,
      equation_parameters: c.equation_parameters,
      existing: true  // Mark as existing for updates
    }));
  } catch (error) {
    console.error('Error loading constraints:', error);
    modalConstraints = [];
  }
}

// Save constraints for a requirement
async function saveConstraintsForRequirement(requirementId, constraints) {
  if (!constraints || constraints.length === 0) return;

  const projectId = getCurrentProjectId();
  const validConstraints = constraints.filter(c => c.name && (c.text_value || c.numeric_value || c.equation_expression));

  try {
    for (const constraint of validConstraints) {
      const constraintData = {
        constraint_type: constraint.constraint_type,
        constraint_name: constraint.name,
        constraint_description: constraint.text_value || constraint.equation_expression || constraint.name,
        value_type: constraint.value_type,
        text_value: constraint.text_value,
        numeric_value: constraint.numeric_value,
        numeric_unit: constraint.numeric_unit,
        priority: constraint.priority || 'medium'
      };

      // Add equation fields if this is an equation constraint
      if (constraint.constraint_type === 'equation') {
        constraintData.equation_expression = constraint.equation_expression;
        constraintData.equation_parameters = constraint.equation_parameters || null;
      }

      if (constraint.existing && constraint.id && constraint.id.includes('-')) {
        // Update existing constraint
        await ApiClient.put(
          `/api/requirements/projects/${projectId}/requirements/${requirementId}/constraints/${constraint.id}`,
          constraintData
        );
      } else {
        // Create new constraint
        await ApiClient.post(
          `/api/requirements/projects/${projectId}/requirements/${requirementId}/constraints`,
          constraintData
        );
      }
    }
  } catch (error) {
    console.error('Error saving constraints:', error);
    // Don't fail the whole operation for constraint errors
  }
}

// Show import requirements modal (placeholder - full implementation to follow)
function showImportRequirementsModal() {
  const projectId = getCurrentProjectId();
  if (!projectId) {
    alert('Please select a project first');
    return;
  }

  showToast('Import requirements modal - full implementation coming in next commit', false);
  console.log('Import requirements modal - to be implemented');
}

// Edit requirement
export function editRequirement(requirementId) {
  const requirement = requirementsState.requirements.find(r => r.requirement_id === requirementId);
  if (!requirement) {
    alert('Requirement not found');
    return;
  }
  showEditRequirementModal(requirement);
}

// Edit selected requirement
function editSelectedRequirement() {
  if (requirementsState.selectedRequirement) {
    showEditRequirementModal(requirementsState.selectedRequirement);
  }
}

// Show edit requirement modal
function showEditRequirementModal(requirement) {
  const modal = document.createElement('div');
  modal.style.cssText = `
    position: fixed; top: 0; left: 0; right: 0; bottom: 0; 
    background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 10000;
  `;

  const modalContent = document.createElement('div');
  modalContent.style.cssText = `
    background: var(--panel); border: 1px solid var(--border); border-radius: 8px; 
    width: 90%; max-width: 700px; max-height: 90vh; overflow: auto; padding: 20px;
  `;

  modalContent.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
      <h3 style="margin:0; color:var(--accent);">Edit Requirement: ${requirement.requirement_identifier}</h3>
      <button onclick="this.closest('.edit-req-modal').remove()" class="btn" style="padding:4px 8px;">
        <svg style="width:16px; height:16px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6L6 18M6 6l12 12"/>
        </svg>
      </button>
    </div>

    <form id="editRequirementForm" style="display:grid; gap:16px;">
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
        <div>
          <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">TITLE</label>
          <input type="text" id="reqTitle" value="${(requirement.requirement_title || '').replace(/"/g, '&quot;')}" 
                 style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2);" 
                 maxlength="500">
        </div>
        
        <div>
          <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">TYPE</label>
          <select id="reqType" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2);">
            <option value="functional" ${requirement.requirement_type === 'functional' ? 'selected' : ''}>Functional</option>
            <option value="non_functional" ${requirement.requirement_type === 'non_functional' ? 'selected' : ''}>Non-Functional</option>
            <option value="performance" ${requirement.requirement_type === 'performance' ? 'selected' : ''}>Performance</option>
            <option value="safety" ${requirement.requirement_type === 'safety' ? 'selected' : ''}>Safety</option>
            <option value="security" ${requirement.requirement_type === 'security' ? 'selected' : ''}>Security</option>
            <option value="interface" ${requirement.requirement_type === 'interface' ? 'selected' : ''}>Interface</option>
            <option value="operational" ${requirement.requirement_type === 'operational' ? 'selected' : ''}>Operational</option>
            <option value="design" ${requirement.requirement_type === 'design' ? 'selected' : ''}>Design</option>
            <option value="implementation" ${requirement.requirement_type === 'implementation' ? 'selected' : ''}>Implementation</option>
          </select>
        </div>
      </div>

      <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px;">
        <div>
          <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">PRIORITY</label>
          <select id="reqPriority" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2);">
            <option value="critical" ${requirement.priority === 'critical' ? 'selected' : ''}>Critical</option>
            <option value="high" ${requirement.priority === 'high' ? 'selected' : ''}>High</option>
            <option value="medium" ${requirement.priority === 'medium' ? 'selected' : ''}>Medium</option>
            <option value="low" ${requirement.priority === 'low' ? 'selected' : ''}>Low</option>
          </select>
        </div>
        
        <div>
          <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">STATUS</label>
          <select id="reqState" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2);">
            <option value="draft" ${requirement.state === 'draft' ? 'selected' : ''}>Draft</option>
            <option value="review" ${requirement.state === 'review' ? 'selected' : ''}>Review</option>
            <option value="approved" ${requirement.state === 'approved' ? 'selected' : ''}>Approved</option>
            ${requirement.state === 'published' ? '<option value="published" selected disabled>Published (Use Publish Button)</option>' : ''}
            <option value="deprecated" ${requirement.state === 'deprecated' ? 'selected' : ''}>Deprecated</option>
            <option value="cancelled" ${requirement.state === 'cancelled' ? 'selected' : ''}>Cancelled</option>
          </select>
        </div>
        
        <div>
          <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">VERIFICATION METHOD</label>
          <select id="reqVerificationMethod" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2);">
            <option value="">Not specified</option>
            <option value="test" ${requirement.verification_method === 'test' ? 'selected' : ''}>Test</option>
            <option value="analysis" ${requirement.verification_method === 'analysis' ? 'selected' : ''}>Analysis</option>
            <option value="inspection" ${requirement.verification_method === 'inspection' ? 'selected' : ''}>Inspection</option>
            <option value="demonstration" ${requirement.verification_method === 'demonstration' ? 'selected' : ''}>Demonstration</option>
            <option value="review" ${requirement.verification_method === 'review' ? 'selected' : ''}>Review</option>
          </select>
        </div>
      </div>

      <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
        <div>
          <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">CATEGORY</label>
          <input type="text" id="reqCategory" value="${(requirement.category || '').replace(/"/g, '&quot;')}" 
                 style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2);" 
                 placeholder="e.g. User Interface, Data Management">
        </div>
        
        <div>
          <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">SUBCATEGORY</label>
          <input type="text" id="reqSubcategory" value="${(requirement.subcategory || '').replace(/"/g, '&quot;')}" 
                 style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2);" 
                 placeholder="e.g. Login, Database Access">
        </div>
      </div>

      <div>
        <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">REQUIREMENT TEXT *</label>
        <textarea id="reqText" rows="4" 
                  style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2); color:var(--text); resize:vertical;" 
                  placeholder="Enter the full requirement text..." required>${(requirement.requirement_text || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</textarea>
      </div>

      <div>
        <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">RATIONALE</label>
        <textarea id="reqRationale" rows="3" 
                  style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2); color:var(--text); resize:vertical;" 
                  placeholder="Why is this requirement necessary?">${(requirement.requirement_rationale || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</textarea>
      </div>

      <div>
        <label style="display:block; font-weight:600; margin-bottom:4px; font-size:12px; color:var(--muted-color);">VERIFICATION CRITERIA</label>
        <textarea id="reqVerificationCriteria" rows="2" 
                  style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2); color:var(--text); resize:vertical;" 
                  placeholder="How will this requirement be verified/tested?">${(requirement.verification_criteria || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</textarea>
      </div>

      <div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <label style="font-weight:600; font-size:12px; color:var(--muted-color);">CONSTRAINTS</label>
          <div style="display:flex; gap:8px;">
            <button type="button" onclick="window.requirementsWorkbench.addEditConstraint()" class="btn btn-sm" style="font-size:11px; padding:4px 8px;">
              <svg style="width:12px; height:12px; margin-right:4px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 5v14M5 12h14"/>
              </svg>
              Add Constraint
            </button>
            <button type="button" onclick="window.requirementsWorkbench.askDASForConstraints('edit')" class="btn btn-sm" style="font-size:11px; padding:4px 8px; background:var(--primary); color:white; opacity:0.6;" disabled title="Coming soon!">
              <svg style="width:12px; height:12px; margin-right:4px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 11l3 3L22 4"/>
                <path d="M21 12c-.12 2.51-.61 4.92-1.44 7.08"/>
              </svg>
              Ask DAS
            </button>
          </div>
        </div>
        <div id="reqConstraintsContainer" style="min-height:40px; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2);">
          <!-- Constraints will be loaded here -->
        </div>
      </div>

      <div style="display:flex; gap:8px; justify-content:flex-end; padding-top:12px; border-top:1px solid var(--border);">
        <button type="button" onclick="this.closest('.edit-req-modal').remove()" class="btn">Cancel</button>
        <button type="submit" class="btn btn-primary">Save Changes</button>
      </div>
    </form>
  `;

  modal.className = 'edit-req-modal';
  modal.appendChild(modalContent);
  document.body.appendChild(modal);

  // Load existing constraints for edit modal
  loadConstraintsForEdit(requirement.requirement_id).then(() => {
    const constraintsContainer = document.getElementById('reqConstraintsContainer');
    renderConstraints(constraintsContainer, 'edit');
  });

  // Handle form submission
  const form = document.getElementById('editRequirementForm');
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    saveRequirementEdit(requirement.requirement_id);
  });

  // Focus on title field
  setTimeout(() => {
    document.getElementById('reqTitle').focus();
  }, 100);
}

// Save requirement edit
async function saveRequirementEdit(requirementId) {
  const projectId = getCurrentProjectId();
  if (!projectId) {
    alert('No project selected');
    return;
  }

  // Get form values
  const formData = {
    requirement_title: document.getElementById('reqTitle').value.trim(),
    requirement_text: document.getElementById('reqText').value.trim(),
    requirement_rationale: document.getElementById('reqRationale').value.trim() || null,
    requirement_type: document.getElementById('reqType').value,
    category: document.getElementById('reqCategory').value.trim() || null,
    subcategory: document.getElementById('reqSubcategory').value.trim() || null,
    priority: document.getElementById('reqPriority').value,
    state: document.getElementById('reqState').value,
    verification_method: document.getElementById('reqVerificationMethod').value || null,
    verification_criteria: document.getElementById('reqVerificationCriteria').value.trim() || null
  };

  // Validate required fields
  if (!formData.requirement_text) {
    alert('Requirement text is required');
    return;
  }

  // Show saving state
  const saveBtn = document.querySelector('.edit-req-modal .btn-primary');
  const originalText = saveBtn.textContent;
  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving...';

  try {
    const updatedRequirement = await ApiClient.put(
      `/api/requirements/projects/${projectId}/requirements/${requirementId}`,
      formData
    );

    // Update local state
    const reqIndex = requirementsState.requirements.findIndex(r => r.requirement_id === requirementId);
    if (reqIndex !== -1) {
      requirementsState.requirements[reqIndex] = { ...requirementsState.requirements[reqIndex], ...updatedRequirement };
    }

    // Update selected requirement if it's the one we edited
    if (requirementsState.selectedRequirement && requirementsState.selectedRequirement.requirement_id === requirementId) {
      requirementsState.selectedRequirement = { ...requirementsState.selectedRequirement, ...updatedRequirement };
    }

    // Save any constraint changes
    if (modalConstraints && modalConstraints.length > 0) {
      await saveConstraintsForRequirement(requirementId, modalConstraints);
    }

    // Close modal
    document.querySelector('.edit-req-modal').remove();

    // Show success message
    showToast('Requirement updated successfully', false);

    // Refresh the table and details panel
    await loadRequirements();

    if (requirementsState.selectedRequirement) {
      showRequirementDetails(requirementsState.selectedRequirement);
    }

  } catch (error) {
    console.error('Error updating requirement:', error);
    alert(`Failed to update requirement: ${error.message}`);
  } finally {
    // Restore button state
    saveBtn.disabled = false;
    saveBtn.textContent = originalText;
  }
}

// Request DAS review for specific requirement
export function requestDASReview(requirementId) {
  const requirement = requirementsState.requirements.find(r => r.requirement_id === requirementId);
  if (!requirement) return;

  requirementsState.selectedRequirement = requirement;
  startDASReview();
}

// Update selected count
export function updateSelectedCount() {
  const checkboxes = document.querySelectorAll('.requirement-checkbox:checked');
  selectedRequirements.clear();
  checkboxes.forEach(cb => selectedRequirements.add(cb.value));

  const count = selectedRequirements.size;
  const countEl = document.getElementById('selectedCount');
  const batchBtn = document.getElementById('reqBatchPublishBtn');

  if (countEl) countEl.textContent = count;
  if (batchBtn) batchBtn.style.display = count > 0 ? 'inline-flex' : 'none';

  // Update select all checkbox state
  const selectAllCb = document.getElementById('selectAllRequirements');
  const allCheckboxes = document.querySelectorAll('.requirement-checkbox');
  if (selectAllCb && allCheckboxes.length > 0) {
    selectAllCb.indeterminate = count > 0 && count < allCheckboxes.length;
    selectAllCb.checked = count === allCheckboxes.length;
  }
}

// Toggle select all requirements
export function toggleSelectAllRequirements() {
  const selectAllCb = document.getElementById('selectAllRequirements');
  const checkboxes = document.querySelectorAll('.requirement-checkbox');

  checkboxes.forEach(cb => {
    cb.checked = selectAllCb.checked;
  });

  updateSelectedCount();
}

// Publish requirement
export async function publishRequirement(requirementId, force = false) {
  if (!requirementId) return;

  try {
    const projectId = getCurrentProjectId();
    if (!projectId) {
      showToast('No active project selected', true);
      return;
    }

    const result = await ApiClient.post(
      `/api/requirements/projects/${projectId}/requirements/${requirementId}/publish`,
      { force: force }
    );

    showToast(`✅ ${result.message}`);

    // Refresh the requirements list to show updated state
    await loadRequirements();

    // Update selected requirement if it's showing in details
    if (requirementsState.selectedRequirement?.requirement_id === requirementId) {
      const updatedReq = requirementsState.requirements.find(r => r.requirement_id === requirementId);
      if (updatedReq) {
        requirementsState.selectedRequirement = updatedReq;
        showRequirementDetails(updatedReq);
      }
    }

  } catch (error) {
    console.error('Error publishing requirement:', error);
    showToast(`Failed to publish requirement: ${error.message}`, true);
  }
}

// Unpublish requirement
export async function unpublishRequirement(requirementId) {
  if (!requirementId) return;

  try {
    const projectId = getCurrentProjectId();
    if (!projectId) {
      showToast('No active project selected', true);
      return;
    }

    const result = await ApiClient.post(
      `/api/requirements/projects/${projectId}/requirements/${requirementId}/unpublish`,
      {}
    );

    showToast(`✅ ${result.message}`);

    // Refresh the requirements list
    await loadRequirements();

    // Update selected requirement if showing in details
    if (requirementsState.selectedRequirement?.requirement_id === requirementId) {
      const updatedReq = requirementsState.requirements.find(r => r.requirement_id === requirementId);
      if (updatedReq) {
        requirementsState.selectedRequirement = updatedReq;
        showRequirementDetails(updatedReq);
      }
    }

  } catch (error) {
    console.error('Error unpublishing requirement:', error);
    showToast(`Failed to unpublish requirement: ${error.message}`, true);
  }
}

// Unimport requirement
export async function unimportRequirement(requirementId) {
  if (!requirementId) return;

  try {
    const projectId = getCurrentProjectId();
    if (!projectId) {
      showToast('No active project selected', true);
      return;
    }

    const result = await ApiClient.delete(
      `/api/requirements/projects/${projectId}/requirements/${requirementId}/import`
    );

    showToast(`✅ ${result.message}`);

    // Close details panel and refresh requirements list
    hideRequirementDetails();
    await loadRequirements();

  } catch (error) {
    console.error('Error un-importing requirement:', error);
    showToast(`Failed to un-import requirement: ${error.message}`, true);
  }
}

// Batch publish requirements
export async function batchPublishRequirements(force = false) {
  const selectedIds = Array.from(selectedRequirements);
  if (selectedIds.length === 0) {
    showToast('No requirements selected', true);
    return;
  }

  try {
    const projectId = getCurrentProjectId();
    if (!projectId) {
      showToast('No active project selected', true);
      return;
    }

    const result = await ApiClient.post(
      `/api/requirements/projects/${projectId}/requirements/batch-publish`,
      {
        requirement_ids: selectedIds,
        force: force
      }
    );

    // Show detailed results
    const publishedCount = result.summary.published_count;
    const skippedCount = result.summary.skipped_count;

    if (publishedCount > 0) {
      showToast(`✅ Published ${publishedCount} requirements successfully`);
    }

    if (skippedCount > 0) {
      const skippedReasons = result.skipped.map(s => `${s.requirement_identifier || s.requirement_id}: ${s.reason}`).join('\n');
      console.warn('Skipped requirements:', skippedReasons);

      if (publishedCount === 0) {
        // If nothing was published, offer to force publish
        const hasUnforceable = result.skipped.some(s => s.reason.includes('approved'));
        if (hasUnforceable && !force) {
          const forcePublish = confirm(`No requirements were published:\n\n${skippedReasons}\n\nWould you like to force publish the eligible requirements anyway?`);
          if (forcePublish) {
            return await batchPublishRequirements(true);
          }
        } else {
          showToast(`No requirements published: ${skippedCount} skipped`, true);
        }
      } else {
        showToast(`⚠️ Published ${publishedCount}, skipped ${skippedCount} requirements`);
      }
    }

    // Clear selections and refresh
    selectedRequirements.clear();
    document.querySelectorAll('.requirement-checkbox').forEach(cb => cb.checked = false);
    updateSelectedCount();
    await loadRequirements();

  } catch (error) {
    console.error('Error batch publishing requirements:', error);
    showToast(`Failed to batch publish: ${error.message}`, true);
  }
}

// Update publish button visibility
function updatePublishButtonVisibility(requirement) {
  const publishBtn = document.getElementById('reqPublishBtn');
  const unpublishBtn = document.getElementById('reqUnpublishBtn');
  const unimportBtn = document.getElementById('reqUnimportBtn');
  const editBtn = document.getElementById('reqEditBtn');

  if (!publishBtn || !unpublishBtn) return;

  // Handle imported/immutable requirements - show un-import button
  const isImported = requirement.state === 'imported' || requirement.is_immutable;

  if (isImported) {
    publishBtn.style.display = 'none';
    unpublishBtn.style.display = 'none';
    if (editBtn) editBtn.style.display = 'none';
    if (unimportBtn) unimportBtn.style.display = 'inline-flex';
    return;
  }

  // Hide un-import button for non-imported requirements
  if (unimportBtn) unimportBtn.style.display = 'none';

  // Show appropriate buttons for regular requirements
  const canPublish = requirement.state === 'approved' ||
    (requirement.state === 'draft' || requirement.state === 'review');
  const isPublished = requirement.state === 'published';

  publishBtn.style.display = !isPublished && canPublish ? 'inline-flex' : 'none';
  unpublishBtn.style.display = isPublished ? 'inline-flex' : 'none';
  if (editBtn) editBtn.style.display = 'inline-flex';
}

// Load and display constraints in requirement details panel
async function loadRequirementConstraintsForDetails(requirementId) {
  try {
    const projectId = getCurrentProjectId();
    const constraints = await ApiClient.get(`/api/requirements/projects/${projectId}/requirements/${requirementId}/constraints`);

    const container = document.getElementById(`requirementConstraints-${requirementId}`);
    if (!container) return;

    if (constraints.length === 0) {
      container.innerHTML = '';
      return;
    }

    const constraintsHtml = `
      <div style="margin-bottom:16px;">
        <div style="font-size:11px; color:var(--muted-color); font-weight:600; margin-bottom:8px;">CONSTRAINTS (${constraints.length})</div>
        <div style="display:grid; gap:6px;">
          ${constraints.map(c => {
    const typeColors = {
      threshold: '#ef4444', objective: '#3b82f6', kpc: '#8b5cf6', kpp: '#06b6d4',
      design: '#6b7280', interface: '#10b981', environmental: '#f59e0b', equation: '#7c3aed'
    };
    const color = typeColors[c.constraint_type] || '#6b7280';

    let displayValue = '';
    if (c.constraint_type === 'equation' && c.equation_expression) {
      displayValue = `📐 ${c.equation_expression}`;
    } else {
      displayValue = c.text_value || `${c.numeric_value || ''}${c.numeric_unit ? ' ' + c.numeric_unit : ''}`;
    }

    return `
            <div style="display:flex; align-items:center; gap:8px; padding:6px 8px; background:var(--panel-2); border:1px solid var(--border); border-radius:4px; font-size:12px;">
              <span style="background:${color}; color:white; padding:2px 6px; border-radius:3px; font-size:10px; font-weight:500; min-width:70px; text-align:center;">
                ${c.constraint_type.toUpperCase()}
              </span>
              <span style="font-weight:500;">${c.constraint_name}</span>
              ${displayValue ? `<span style="color:var(--muted-color); font-family:${c.constraint_type === 'equation' ? 'monospace' : 'inherit'};">→ ${displayValue}</span>` : ''}
            </div>
          `;
  }).join('')}
        </div>
      </div>
    `;

    container.innerHTML = constraintsHtml;
  } catch (error) {
    console.error('Error loading requirement constraints:', error);
    const container = document.getElementById(`requirementConstraints-${requirementId}`);
    if (container) container.innerHTML = '';
  }
}

// Export for use in app.html
export const requirementsWorkbench = {
  initializeRequirementsWorkbench,
  loadRequirements,
  sortRequirements,
  goToPage,
  selectRequirement,
  editRequirement,
  requestDASReview,
  updateSelectedCount,
  toggleSelectAllRequirements,
  publishRequirement,
  unpublishRequirement,
  unimportRequirement,
  batchPublishRequirements,
  startExtractionJob,
  acceptDASReview,
  state: requirementsState
};

// Make available globally for backwards compatibility during transition
window.requirementsWorkbench = requirementsWorkbench;
window.initializeRequirementsWorkbench = initializeRequirementsWorkbench;
window.loadRequirements = loadRequirements;
window.sortRequirements = sortRequirements;
window.goToPage = goToPage;
window.selectRequirement = selectRequirement;
window.editRequirement = editRequirement;
window.requestDASReview = requestDASReview;
window.updateSelectedCount = updateSelectedCount;
window.toggleSelectAllRequirements = toggleSelectAllRequirements;
window.publishRequirement = publishRequirement;
window.unpublishRequirement = unpublishRequirement;
window.unimportRequirement = unimportRequirement;
window.batchPublishRequirements = batchPublishRequirements;
window.startExtractionJob = startExtractionJob;
window.acceptDASReview = acceptDASReview;
window.addNewConstraint = addNewConstraint;
window.addEditConstraint = addEditConstraint;
window.updateConstraint = updateConstraint;
window.removeConstraint = removeConstraint;
window.askDASForConstraints = askDASForConstraints;
window.openParameterPicker = openParameterPicker;
