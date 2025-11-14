/**
 * Ontology Workbench UI Module
 * 
 * Complete ontology workbench functionality extracted from app.html
 * This is the full, complete implementation with all features.
 */

import { apiClient } from '../../core/api-client.js';
import { getAppState, updateAppState } from '../../core/state-manager.js';
import { subscribeToEvent, emitEvent } from '../../core/event-bus.js';

// Use apiClient as ApiClient
const ApiClient = apiClient;

// Helper functions (if not already imported)
function qs(selector) {
  return document.querySelector(selector);
}

function qsa(selector) {
  return Array.from(document.querySelectorAll(selector));
}

function debounce(func, wait) {
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

// Authenticated fetch helper
async function authenticatedFetch(url, options = {}) {
  const token = localStorage.getItem('odras_token');
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return fetch(url, { ...options, headers });
}

// Ontology workbench state
const ontoState = {
  cy: null,
  eh: null,
  connectMode: false,
  clickConnectFrom: null,
  nextId: 1,
  currentPredicateType: 'objectProperty',
  isCanvasActive: false,
  suspendAutosave: false,
  autosaveBound: false,
  layoutRunning: false,     // Flag to prevent saves during layout algorithms
  // CAD-like features
  snapToGrid: true,         // Snap to grid enabled by default
  gridSize: 20,             // Grid size (matches CSS background)
  undoStack: [],            // Undo history
  redoStack: [],            // Redo history
  maxUndoLevels: 50,        // Maximum undo levels
  clipboard: null,          // Copy/paste clipboard
  visibilityState: {
    classes: true,
    dataProperties: true,
    notes: true,
    edges: true,
    imported: true
  },
  collapsedImports: new Set(), // Track which imports are collapsed
  elementVisibility: {}, // Track individual element visibility {elementId: true/false}
  activeNamedView: null, // Track currently active named view
  beforeViewState: null // Track state before applying any named view
};
let activeProject = null;
let suppressWorkbenchSwitch = false;
let activeOntologyIri = null;

// URL state management
function updateURL(projectId = null, workbench = null) {
  try {
    const url = new URL(window.location);
    if (projectId) {
      url.searchParams.set('project', projectId);
    } else {
      url.searchParams.delete('project');
    }
    if (workbench) {
      url.searchParams.set('wb', workbench);
    } else {
      url.searchParams.delete('wb');
    }
    window.history.replaceState({}, '', url);
  } catch (error) {
    console.warn('Failed to update URL:', error);
  }
}

function getURLState() {
  try {
    const url = new URL(window.location);
    return {
      projectId: url.searchParams.get('project'),
      workbench: url.searchParams.get('wb')
    };
  } catch (error) {
    console.warn('Failed to read URL state:', error);
    return { projectId: null, workbench: null };
  }
}

function updateOntoGraphLabel() {
  const el = qs('#ontoGraphLabel');
  if (!el) return;
  if (activeOntologyIri) {
    el.textContent = 'Graph: ' + activeOntologyIri;
    el.title = activeOntologyIri;
  } else {
    el.textContent = 'No graph selected';
    el.title = '';
  }

  // Also update element IRI display when graph changes
  updateElementIriDisplay();

  // Toggle empty-state hint
  const empty = qs('#ontoEmpty');
  const layout = qs('#ontoLayoutSection');
  if (empty && layout) {
    const showEmpty = !activeOntologyIri;
    empty.style.display = showEmpty ? 'block' : 'none';
    layout.style.display = showEmpty ? 'none' : 'grid';
  }
}

function slugify(str) {
  try {
    return String(str || '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'ontology';
  } catch (_) { return 'ontology'; }
}

// Installation configuration - loaded from API
let INSTALLATION_CONFIG = {
  organization: "ODRAS Development",
  baseUri: "http://odras.local",  // Will be loaded from API
  prefix: "odras",
  type: "development"  // navy, airforce, army, industry, research, etc.
};

// Load installation configuration from API
async function loadInstallationConfig() {
  try {
    const response = await fetch('/api/installation/config');
    if (response.ok) {
      const config = await response.json();
      INSTALLATION_CONFIG = { ...INSTALLATION_CONFIG, ...config };
      console.log('🔧 Loaded installation config:', INSTALLATION_CONFIG);
      updateInstallationConfigDisplay();
    }
  } catch (error) {
    console.warn('⚠️ Failed to load installation config, using defaults:', error);
    updateInstallationConfigDisplay();
  }
}

// Load config on page load
loadInstallationConfig().then(() => {
  loadRagConfig();
  loadFileProcessingConfig(); // Load file processing config alongside RAG config
});

// Update installation config display
function updateInstallationConfigDisplay() {
  // Update admin panel display
  document.getElementById('configOrganization').textContent = INSTALLATION_CONFIG.organization;
  document.getElementById('configBaseUri').textContent = INSTALLATION_CONFIG.baseUri;
  document.getElementById('configType').textContent = INSTALLATION_CONFIG.type;

  // Update topbar display
  const installOrg = document.getElementById('installOrg');
  const installType = document.getElementById('installType');
  const installOffice = document.getElementById('installOffice');

  if (installOrg) installOrg.textContent = INSTALLATION_CONFIG.organization || 'ODRAS';
  if (installType) installType.textContent = INSTALLATION_CONFIG.type || 'development';
  if (installOffice) installOffice.textContent = INSTALLATION_CONFIG.programOffice || '';
  document.getElementById('configProgramOffice').textContent = INSTALLATION_CONFIG.programOffice || 'N/A';
}

// RAG Configuration Management
let CURRENT_RAG_CONFIG = null;
let AVAILABLE_BPMN_MODELS = {};

// Load RAG configuration from API
async function loadRagConfig() {
  try {
    const token = localStorage.getItem('odras_token');
    if (!token) {
      console.warn('⚠️ No authentication token found - RAG config requires admin access');
      document.getElementById('currentRagImplementation').textContent = 'Login required';
      return;
    }

    const response = await fetch('/api/admin/rag-config', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (response.ok) {
      const config = await response.json();
      CURRENT_RAG_CONFIG = config;
      console.log('🔧 Loaded RAG config:', CURRENT_RAG_CONFIG);
      await loadBpmnModels(); // Load BPMN models after config
      updateRagConfigDisplay();
    } else {
      console.error('Failed to load RAG config:', response.status, response.statusText);
      if (response.status === 401 || response.status === 403) {
        document.getElementById('currentRagImplementation').textContent = 'Admin access required';
      } else {
        document.getElementById('currentRagImplementation').textContent = 'Error loading configuration';
      }
    }
  } catch (error) {
    console.warn('⚠️ Failed to load RAG config:', error);
    document.getElementById('currentRagImplementation').textContent = 'Error loading configuration';
  }
}

// ===== EVENT MANAGER FUNCTIONALITY =====

// Event Manager global variables
let EVENT_MONITOR_ACTIVE = false;
let EVENT_MONITOR_INTERVAL = null;
let EVENT_STATISTICS = null;
let LAST_EVENT_TIMESTAMP = null;

// Initialize Event Manager when workbench becomes active
async function initializeEventManager() {
  try {
    console.log('📊 Initializing Event Manager...');

    // Check if required elements exist
    const eventCount24h = document.getElementById('eventCount24h');
    const totalEvents24h = document.getElementById('totalEvents24h');
    const eventSystemStatus = document.getElementById('eventSystemStatus');

    console.log('🔍 Event Manager elements check:');
    console.log('   eventCount24h:', !!eventCount24h);
    console.log('   totalEvents24h:', !!totalEvents24h);
    console.log('   eventSystemStatus:', !!eventSystemStatus);

    // Set loading states
    if (eventCount24h) eventCount24h.textContent = 'Loading...';
    if (eventSystemStatus) eventSystemStatus.textContent = 'Loading...';

    // Load initial data with error handling
    console.log('📊 Loading Event Manager data...');

    try {
      await loadEventStatistics();
      console.log('✅ Event statistics loaded');
    } catch (error) {
      console.error('❌ Event statistics failed:', error);
    }

    try {
      await loadEventTypes();
      console.log('✅ Event types loaded');
    } catch (error) {
      console.error('❌ Event types failed:', error);
    }

    try {
      await loadEventHealth();
      console.log('✅ Event health loaded');
    } catch (error) {
      console.error('❌ Event health failed:', error);
    }

    console.log('✅ Event Manager initialization complete');
  } catch (error) {
    console.error('❌ Event Manager initialization failed:', error);

    // Set error states
    const eventCount24h = document.getElementById('eventCount24h');
    const eventSystemStatus = document.getElementById('eventSystemStatus');
    if (eventCount24h) eventCount24h.textContent = 'Error';
    if (eventSystemStatus) eventSystemStatus.textContent = 'Error';
  }
}

// Load event statistics for dashboard
async function loadEventStatistics() {
  try {
    console.log('📊 Loading event statistics...');
    const token = localStorage.getItem('odras_token');
    if (!token) {
      console.warn('⚠️ No auth token for event statistics');
      document.getElementById('eventCount24h').textContent = 'No Auth';
      return;
    }

    console.log('🔑 Auth token available, calling API...');
    const response = await fetch('/api/events/statistics', {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    console.log('📊 Event statistics response:', response.status);

    if (response.ok) {
      EVENT_STATISTICS = await response.json();
      console.log('📊 Event statistics data received:', EVENT_STATISTICS);
      updateEventStatisticsDisplay();
      console.log('✅ Event statistics display updated');
    } else {
      console.error('Failed to load event statistics:', response.status, await response.text());
      document.getElementById('eventCount24h').textContent = `Error ${response.status}`;
    }
  } catch (error) {
    console.error('Error loading event statistics:', error);
    document.getElementById('eventCount24h').textContent = 'Error';
  }
}

// Update statistics display
function updateEventStatisticsDisplay() {
  if (!EVENT_STATISTICS) {
    console.warn('⚠️ No event statistics data to display');
    return;
  }

  console.log('🔄 Updating Event Manager display with data:', EVENT_STATISTICS);

  // Update health status counts (with null checks)
  const elements = {
    'eventCount24h': EVENT_STATISTICS.total_events_24h || 0,
    'totalEvents24h': EVENT_STATISTICS.total_events_24h || 0,
    'totalEvents7d': EVENT_STATISTICS.total_events_7d || 0,
    'activeProjects24h': EVENT_STATISTICS.active_projects_24h || 0
  };

  for (const [elementId, value] of Object.entries(elements)) {
    const element = document.getElementById(elementId);
    if (element) {
      element.textContent = value;
      console.log(`✅ Updated ${elementId}: ${value}`);
    } else {
      console.warn(`⚠️ Element not found: ${elementId}`);
    }
  }

  // Update system status with color
  const statusElement = document.getElementById('eventSystemStatus');
  if (statusElement && EVENT_STATISTICS.system_health) {
    const health = EVENT_STATISTICS.system_health;
    statusElement.textContent = health.charAt(0).toUpperCase() + health.slice(1);
    statusElement.style.color = health === 'healthy' ? 'var(--ok)' :
      health === 'warning' ? 'var(--warn)' : 'var(--err)';
    console.log(`✅ Updated system status: ${health}`);
  }

  // Update top event types
  const topEventTypesEl = document.getElementById('topEventTypes');
  if (topEventTypesEl) {
    if (EVENT_STATISTICS.top_event_types && EVENT_STATISTICS.top_event_types.length > 0) {
      topEventTypesEl.innerHTML = EVENT_STATISTICS.top_event_types
        .map(et => `
          <div style="display: flex; justify-content: space-between; padding: 8px 12px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px;">
            <span style="color: var(--text);">${et.event_type.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase())}</span>
            <span style="color: var(--muted);">${et.count} events</span>
          </div>
        `).join('');
      console.log(`✅ Updated top event types: ${EVENT_STATISTICS.top_event_types.length} types`);
    } else {
      topEventTypesEl.innerHTML = '<div style="color: var(--muted); padding: 8px;">No events in last 24 hours</div>';
      console.log('ℹ️ No event types to display');
    }
  }

  // Update most active project
  const mostActiveEl = document.getElementById('mostActiveProject');
  if (mostActiveEl) {
    if (EVENT_STATISTICS.most_active_project) {
      const project = EVENT_STATISTICS.most_active_project;
      mostActiveEl.innerHTML = `
        <div style="font-weight: 600; color: var(--text);">${project.project_name}</div>
        <div style="font-size: 12px; color: var(--muted); margin-top: 4px;">
          ${project.event_count} events • Project ID: ${project.project_id.substring(0, 8)}...
        </div>
      `;
      console.log(`✅ Updated most active project: ${project.project_name}`);
    } else {
      mostActiveEl.innerHTML = '<div style="color: var(--muted);">No active projects in last 24 hours</div>';
      console.log('ℹ️ No active project to display');
    }
  }

  console.log('✅ Event statistics display update complete');
}

// Toggle live event monitor
function toggleEventMonitor() {
  const button = document.getElementById('toggleEventMonitor');

  if (EVENT_MONITOR_ACTIVE) {
    // Stop monitoring
    EVENT_MONITOR_ACTIVE = false;
    if (EVENT_MONITOR_INTERVAL) {
      clearInterval(EVENT_MONITOR_INTERVAL);
      EVENT_MONITOR_INTERVAL = null;
    }
    button.innerHTML = '▶ Start Monitor';
    button.style.background = 'var(--ok)';

    const feed = document.getElementById('eventFeed');
    feed.innerHTML += '<div style="color: var(--muted); text-align: center; padding: 10px; border-top: 1px solid var(--border); margin-top: 10px;">--- Event monitoring stopped ---</div>';

    console.log('📊 Event monitor stopped');
  } else {
    // Start monitoring
    EVENT_MONITOR_ACTIVE = true;
    button.innerHTML = '⏸ Stop Monitor';
    button.style.background = 'var(--err)';

    const feed = document.getElementById('eventFeed');
    feed.innerHTML = '<div style="color: var(--ok); text-align: center; padding: 10px;">--- Live event monitoring started ---</div>';

    // Start polling for new events
    EVENT_MONITOR_INTERVAL = setInterval(pollForNewEvents, 3000); // Poll every 3 seconds

    console.log('📊 Event monitor started - polling every 3 seconds');
  }
}

// Poll for new events
async function pollForNewEvents() {
  if (!EVENT_MONITOR_ACTIVE) return;

  try {
    const token = localStorage.getItem('odras_token');
    if (!token) return;

    const eventTypeFilter = document.getElementById('eventTypeFilter').value;
    let url = '/api/events/recent?limit=10';
    if (eventTypeFilter) {
      url += `&event_type=${eventTypeFilter}`;
    }

    const response = await fetch(url, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.ok) {
      const events = await response.json();
      displayNewEvents(events);
    } else {
      console.error('Failed to poll events:', response.status);
    }
  } catch (error) {
    console.error('Error polling for events:', error);
  }
}

// Display new events in feed
function displayNewEvents(events) {
  const feed = document.getElementById('eventFeed');
  const countEl = document.getElementById('eventFeedCount');
  const autoScroll = document.getElementById('autoScrollEvents').checked;

  if (!events || events.length === 0) return;

  // Filter events newer than last displayed timestamp
  const newEvents = LAST_EVENT_TIMESTAMP ?
    events.filter(e => new Date(e.created_at) > new Date(LAST_EVENT_TIMESTAMP)) : events;

  if (newEvents.length === 0) return;

  // Add new events to feed
  const eventHtml = newEvents.map(event => {
    const timestamp = new Date(event.created_at).toLocaleTimeString();
    const eventTypeColor = getEventTypeColor(event.event_type);

    return `
      <div style="margin-bottom: 8px; padding: 8px; border-left: 3px solid ${eventTypeColor}; background: var(--panel-2);">
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 4px;">
          <span style="font-weight: 600; color: var(--text); font-size: 11px;">${event.event_type.toUpperCase()}</span>
          <span style="color: var(--muted); font-size: 10px;">${timestamp}</span>
        </div>
        <div style="color: var(--text); margin-bottom: 4px; font-size: 11px;">${event.semantic_summary}</div>
        <div style="display: flex; gap: 12px; font-size: 10px; color: var(--muted);">
          ${event.project_name ? `<span>📁 ${event.project_name.substring(0, 25)}${event.project_name.length > 25 ? '...' : ''}</span>` : ''}
          <span>👤 ${event.user_id.substring(0, 8)}...</span>
        </div>
      </div>
    `;
  }).join('');

  // Update feed
  feed.innerHTML += eventHtml;

  // Update count
  const currentCount = parseInt(countEl.textContent) || 0;
  countEl.textContent = currentCount + newEvents.length;

  // Auto-scroll to bottom if enabled
  if (autoScroll) {
    feed.scrollTop = feed.scrollHeight;
  }

  // Update last timestamp
  LAST_EVENT_TIMESTAMP = Math.max(...newEvents.map(e => new Date(e.created_at).getTime()));
}

// Get color for event type
function getEventTypeColor(eventType) {
  if (eventType.includes('project')) return 'var(--primary)';
  if (eventType.includes('ontology') || eventType.includes('class')) return 'var(--warn)';
  if (eventType.includes('file')) return 'var(--ok)';
  if (eventType.includes('das')) return '#9333ea';
  if (eventType.includes('knowledge')) return '#0891b2';
  if (eventType.includes('error')) return 'var(--err)';
  return 'var(--muted)';
}

// Clear event feed
function clearEventFeed() {
  const feed = document.getElementById('eventFeed');
  const countEl = document.getElementById('eventFeedCount');

  feed.innerHTML = '<div style="color: var(--muted); text-align: center; padding: 20px;">Event feed cleared. New events will appear here.</div>';
  countEl.textContent = '0';
  LAST_EVENT_TIMESTAMP = new Date().getTime();

  console.log('📊 Event feed cleared');
}

// Filter event feed
function filterEventFeed() {
  if (EVENT_MONITOR_ACTIVE) {
    // Restart monitoring with new filter
    clearEventFeed();
  }
}

// Clear old events (maintenance)
async function clearOldEvents() {
  if (!confirm('Clear events older than 30 days? This cannot be undone.')) return;

  try {
    const token = localStorage.getItem('odras_token');
    if (!token) return;

    const response = await fetch('/api/events/clear?days_old=30', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.ok) {
      const result = await response.json();
      alert(`✅ Cleared ${result.events_cleared} old events`);
      await loadEventStatistics(); // Refresh stats
    } else {
      alert('❌ Failed to clear old events');
    }
  } catch (error) {
    console.error('Error clearing old events:', error);
    alert('❌ Error clearing old events');
  }
}

// Refresh event statistics
async function refreshEventStats() {
  try {
    await loadEventStatistics();
    await loadEventHealth();
    console.log('📊 Event statistics refreshed');
  } catch (error) {
    console.error('Error refreshing event stats:', error);
  }
}

// Force load Event Manager data (simple approach)
async function forceLoadEventManager() {
  console.log('🔄 FORCE LOADING EVENT MANAGER DATA');

  try {
    const token = localStorage.getItem('odras_token');
    if (!token) {
      alert('❌ No authentication token - please login first');
      return;
    }

    // Direct API call and immediate UI update
    const response = await fetch('/api/events/statistics', {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.ok) {
      const data = await response.json();
      console.log('📊 Event data loaded:', data);

      // Immediately update all UI elements
      document.getElementById('eventCount24h').textContent = data.total_events_24h || 0;
      document.getElementById('totalEvents24h').textContent = data.total_events_24h || 0;
      document.getElementById('totalEvents7d').textContent = data.total_events_7d || 0;
      document.getElementById('activeProjects24h').textContent = data.active_projects_24h || 0;

      const statusEl = document.getElementById('eventSystemStatus');
      statusEl.textContent = (data.system_health || 'Unknown').charAt(0).toUpperCase() + (data.system_health || 'unknown').slice(1);
      statusEl.style.color = data.system_health === 'healthy' ? 'var(--ok)' : 'var(--warn)';

      document.getElementById('eventSqlFirstStatus').textContent = 'Active';
      document.getElementById('eventSqlFirstStatus').style.color = 'var(--ok)';

      // Update most active project
      if (data.most_active_project) {
        const project = data.most_active_project;
        document.getElementById('mostActiveProject').innerHTML = `
          <div style='font-weight: 600; color: var(--text);'>${project.project_name}</div>
          <div style='font-size: 12px; color: var(--muted); margin-top: 4px;'>
            ${project.event_count} events • Project ID: ${project.project_id.substring(0, 8)}...
          </div>
        `;
      } else {
        document.getElementById('mostActiveProject').innerHTML = '<div style=\"color: var(--muted);\">No active projects in last 24 hours</div>';
      }

      // Update top event types
      if (data.top_event_types && data.top_event_types.length > 0) {
        document.getElementById('topEventTypes').innerHTML = data.top_event_types
          .map(et => `
            <div style=\"display: flex; justify-content: space-between; padding: 8px 12px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px;\">
              <span style=\"color: var(--text);\">${et.event_type.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase())}</span>
              <span style=\"color: var(--muted);\">${et.count} events</span>
            </div>
          `).join('');
      }

      alert(`✅ Event Manager loaded! ${data.total_events_24h} events (24h), System: ${data.system_health}`);

    } else {
      alert(`❌ API failed: ${response.status}`);
    }

  } catch (error) {
    console.error('Force load error:', error);
    alert('❌ Load failed: ' + error.message);
  }
}

// Manual test function for debugging (clickable from UI)
async function testEventManagerLoad() {
  console.log('🧪 MANUAL EVENT MANAGER LOAD TEST');

  // Check elements
  const elements = ['eventCount24h', 'totalEvents24h', 'eventSystemStatus', 'mostActiveProject'];
  elements.forEach(id => {
    const el = document.getElementById(id);
    console.log(`${id}:`, !!el);
  });

  // Check auth
  const token = localStorage.getItem('odras_token');
  console.log('Auth token:', !!token);

  if (token) {
    try {
      // Manual API test
      const response = await fetch('/api/events/statistics', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      console.log('Manual API response:', response.status);

      if (response.ok) {
        const data = await response.json();
        console.log('Manual API data:', data);

        // Force update elements
        const eventCount24h = document.getElementById('eventCount24h');
        const totalEvents24h = document.getElementById('totalEvents24h');
        const eventSystemStatus = document.getElementById('eventSystemStatus');
        const mostActiveProject = document.getElementById('mostActiveProject');

        if (eventCount24h) {
          eventCount24h.textContent = data.total_events_24h || 0;
          eventCount24h.style.color = 'var(--ok)';
          console.log('✅ Manually updated eventCount24h');
        }

        if (totalEvents24h) {
          totalEvents24h.textContent = data.total_events_24h || 0;
          console.log('✅ Manually updated totalEvents24h');
        }

        if (eventSystemStatus) {
          eventSystemStatus.textContent = (data.system_health || 'unknown').charAt(0).toUpperCase() + (data.system_health || 'unknown').slice(1);
          eventSystemStatus.style.color = data.system_health === 'healthy' ? 'var(--ok)' : 'var(--warn)';
          console.log('✅ Manually updated eventSystemStatus');
        }

        if (mostActiveProject && data.most_active_project) {
          const project = data.most_active_project;
          mostActiveProject.innerHTML = `
            <div style='font-weight: 600; color: var(--text);'>${project.project_name}</div>
            <div style='font-size: 12px; color: var(--muted); margin-top: 4px;'>
              ${project.event_count} events • Project ID: ${project.project_id.substring(0, 8)}...
            </div>
          `;
          console.log('✅ Manually updated mostActiveProject');
        }

        alert('✅ Event Manager data manually loaded! Check the updated values.');

      } else {
        console.error('Manual API failed:', response.status);
        alert('❌ API call failed: ' + response.status);
      }

    } catch (error) {
      console.error('Manual test error:', error);
      alert('❌ Manual test failed: ' + error.message);
    }
  } else {
    alert('❌ No authentication token found');
  }
}

// Load event types configuration
async function loadEventTypes() {
  try {
    const token = localStorage.getItem('odras_token');
    if (!token) return;

    const response = await fetch('/api/events/types', {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.ok) {
      const eventTypes = await response.json();
      updateEventTypesDisplay(eventTypes);
    } else {
      console.error('Failed to load event types:', response.status);
    }
  } catch (error) {
    console.error('Error loading event types:', error);
  }
}

// Update event types display
function updateEventTypesDisplay(eventTypes) {
  const eventTypesEl = document.getElementById('eventTypesList');
  if (!eventTypesEl || !eventTypes) return;

  const typesByCategory = {
    'Project': eventTypes.filter(et => et.event_type.startsWith('project_')),
    'Ontology': eventTypes.filter(et => et.event_type.includes('ontology') || et.event_type.includes('class')),
    'Files': eventTypes.filter(et => et.event_type.startsWith('file_')),
    'Knowledge': eventTypes.filter(et => et.event_type.includes('knowledge')),
    'DAS': eventTypes.filter(et => et.event_type.startsWith('das_')),
    'System': eventTypes.filter(et => et.event_type.includes('user_') || et.event_type.includes('system_'))
  };

  eventTypesEl.innerHTML = Object.entries(typesByCategory)
    .filter(([category, types]) => types.length > 0)
    .map(([category, types]) => `
      <div style="margin-bottom: 16px;">
        <h5 style="margin: 0 0 8px 0; color: var(--text); font-size: 13px; font-weight: 600;">${category}</h5>
        <div style="display: grid; gap: 6px; padding-left: 12px;">
          ${types.map(et => `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; background: var(--bg); border: 1px solid var(--border); border-radius: 4px; font-size: 12px;">
              <span style="color: var(--text);">${et.description}</span>
              <div style="display: flex; gap: 8px; align-items: center;">
                <span style="color: var(--muted);">${et.count_24h}</span>
                <span style="width: 8px; height: 8px; border-radius: 50%; background: ${et.enabled ? 'var(--ok)' : 'var(--muted)'};"></span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `).join('') || '<div style="color: var(--muted); padding: 8px;">No event types found</div>';
}

// Load event system health
async function loadEventHealth() {
  try {
    console.log('🏥 Loading event health...');
    const token = localStorage.getItem('odras_token');
    if (!token) {
      console.warn('⚠️ No auth token for event health');
      return;
    }

    const response = await fetch('/api/events/health', {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    console.log('🏥 Event health response:', response.status);

    if (response.ok) {
      const health = await response.json();
      console.log('🏥 Event health data received:', health);
      updateEventHealthDisplay(health);
      console.log('✅ Event health display updated');
    } else {
      console.error('Failed to load event health:', response.status);
      const statusEl = document.getElementById('eventSystemStatus');
      if (statusEl) statusEl.textContent = `Error ${response.status}`;
    }
  } catch (error) {
    console.error('Error loading event health:', error);
    const statusEl = document.getElementById('eventSystemStatus');
    if (statusEl) statusEl.textContent = 'Error';
  }
}

// Update event health display
function updateEventHealthDisplay(health) {
  const statusEl = document.getElementById('eventSystemStatus');
  const sqlFirstEl = document.getElementById('eventSqlFirstStatus');

  if (statusEl) {
    statusEl.textContent = health.status.charAt(0).toUpperCase() + health.status.slice(1);
    statusEl.style.color = health.status === 'healthy' ? 'var(--ok)' :
      health.status === 'warning' ? 'var(--warn)' : 'var(--err)';
  }

  if (sqlFirstEl) {
    sqlFirstEl.textContent = health.sql_first_active ? 'Active' : 'Inactive';
    sqlFirstEl.style.color = health.sql_first_active ? 'var(--ok)' : 'var(--err)';
  }
}

// Load file processing configuration from API
async function loadFileProcessingConfig() {
  try {
    const token = localStorage.getItem('odras_token');
    if (!token) {
      console.warn('⚠️ No authentication token found - File processing config requires admin access');
      document.getElementById('currentFileProcessingImplementation').textContent = 'Login required';
      return;
    }

    const response = await fetch('/api/admin/file-processing-config', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (response.ok) {
      const config = await response.json();
      console.log('🔧 Loaded file processing config:', config);

      const implementation = config.file_processing_implementation;
      const displayText = implementation === 'hardcoded'
        ? 'Hardcoded Processing (SQL-first)'
        : 'BPMN Workflow Processing';

      document.getElementById('currentFileProcessingImplementation').textContent = displayText;
      document.getElementById('fileProcessingImplementationSelect').value = implementation;
    } else {
      console.error('Failed to load file processing config:', response.status, response.statusText);
      if (response.status === 401 || response.status === 403) {
        document.getElementById('currentFileProcessingImplementation').textContent = 'Admin access required';
      } else {
        document.getElementById('currentFileProcessingImplementation').textContent = 'Error loading configuration';
      }
    }
  } catch (error) {
    console.warn('⚠️ Failed to load file processing config:', error);
    document.getElementById('currentFileProcessingImplementation').textContent = 'Error loading configuration';
  }
}

// Load RAG configuration for DAS (public endpoint, no admin required)
async function loadRagConfigForDAS() {
  try {
    const response = await fetch('/api/rag-config', {
      headers: {
        ...authHeader(),
        'Content-Type': 'application/json'
      }
    });

    if (response.ok) {
      const config = await response.json();
      CURRENT_RAG_CONFIG = config;
      console.log('🔧 DAS loaded RAG config:', CURRENT_RAG_CONFIG);
      console.log('🔧 DAS RAG implementation:', CURRENT_RAG_CONFIG?.rag_implementation);
      console.log('🔧 DAS will use workflow:', CURRENT_RAG_CONFIG?.rag_implementation === 'bpmn');
    } else {
      console.error('🔧 DAS failed to load RAG config:', response.status);
      // Fallback to hardcoded if API fails
      CURRENT_RAG_CONFIG = {
        success: true,
        rag_implementation: 'hardcoded',
        rag_bpmn_model: null,
        rag_model_version: null
      };
    }
  } catch (error) {
    console.error('🔧 DAS error loading RAG config:', error);
    // Fallback to hardcoded if API fails
    CURRENT_RAG_CONFIG = {
      success: true,
      rag_implementation: 'hardcoded',
      rag_bpmn_model: null,
      rag_model_version: null
    };
  }
}

// Load BPMN models from Camunda
async function loadBpmnModels() {
  try {
    const token = localStorage.getItem('odras_token');
    if (!token) return;

    const response = await fetch('/api/admin/bpmn-models', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (response.ok) {
      const data = await response.json();
      AVAILABLE_BPMN_MODELS = {};
      data.models.forEach(model => {
        AVAILABLE_BPMN_MODELS[model.key] = model;
      });
      console.log('🔧 Loaded BPMN models:', AVAILABLE_BPMN_MODELS);
      populateBpmnModelOptions();
    } else {
      console.error('Failed to load BPMN models:', response.status, response.statusText);
    }
  } catch (error) {
    console.warn('⚠️ Failed to load BPMN models:', error);
  }
}

// Populate BPMN model options
function populateBpmnModelOptions() {
  const modelSelect = document.getElementById('ragBpmnModelSelect');
  modelSelect.innerHTML = '<option value="">Select Model...</option>';

  for (const [key, model] of Object.entries(AVAILABLE_BPMN_MODELS)) {
    const option = document.createElement('option');
    option.value = key;
    option.textContent = model.name;
    modelSelect.appendChild(option);
  }
}

// Update RAG configuration display
function updateRagConfigDisplay() {
  if (CURRENT_RAG_CONFIG) {
    const implementation = CURRENT_RAG_CONFIG.rag_implementation;
    const bpmnModel = CURRENT_RAG_CONFIG.rag_bpmn_model;
    const modelVersion = CURRENT_RAG_CONFIG.rag_model_version;

    // Update current display
    const displayText = implementation === 'hardcoded' ? 'Hardcoded RAG (Direct Service)' : 'BPMN RAG (Workflow-based)';
    document.getElementById('currentRagImplementation').textContent = displayText;

    // Show/hide BPMN model info
    const bpmnModelDisplay = document.getElementById('currentBpmnModelDisplay');
    const versionDisplay = document.getElementById('currentModelVersionDisplay');

    if (implementation === 'bpmn') {
      bpmnModelDisplay.style.display = 'block';
      versionDisplay.style.display = 'block';
      const modelInfo = AVAILABLE_BPMN_MODELS[bpmnModel];
      document.getElementById('currentRagBpmnModel').textContent = modelInfo ? modelInfo.name : bpmnModel;
      document.getElementById('currentRagModelVersion').textContent = modelVersion;
    } else {
      bpmnModelDisplay.style.display = 'none';
      versionDisplay.style.display = 'none';
    }

    // Update form controls
    document.getElementById('ragImplementationSelect').value = implementation;
    document.getElementById('ragBpmnModelSelect').value = bpmnModel;
    updateModelVersions(); // This will set the version dropdown
    toggleBpmnOptions(); // This will show/hide BPMN options
  }
}

// Toggle BPMN options visibility
function toggleBpmnOptions() {
  const implementation = document.getElementById('ragImplementationSelect').value;
  const bpmnModelDiv = document.getElementById('bpmnModelSelect');
  const versionDiv = document.getElementById('modelVersionSelect');
  const descriptionDiv = document.getElementById('modelDescription');

  if (implementation === 'bpmn') {
    bpmnModelDiv.style.display = 'block';
    versionDiv.style.display = 'block';
    updateModelVersions();
  } else {
    bpmnModelDiv.style.display = 'none';
    versionDiv.style.display = 'none';
    descriptionDiv.style.display = 'none';
  }
}

// Update model versions based on selected model
function updateModelVersions() {
  const selectedModel = document.getElementById('ragBpmnModelSelect').value;
  const versionSelect = document.getElementById('ragModelVersionSelect');
  const descriptionDiv = document.getElementById('modelDescription');
  const descriptionText = document.getElementById('modelDescriptionText');

  versionSelect.innerHTML = '<option value="">Select Version...</option>';

  if (selectedModel && AVAILABLE_BPMN_MODELS[selectedModel]) {
    const model = AVAILABLE_BPMN_MODELS[selectedModel];

    // Populate versions
    model.versions.forEach(version => {
      const option = document.createElement('option');
      option.value = version;
      option.textContent = `v${version}`;
      versionSelect.appendChild(option);
    });

    // Set current version if available
    if (CURRENT_RAG_CONFIG && CURRENT_RAG_CONFIG.rag_bpmn_model === selectedModel) {
      versionSelect.value = CURRENT_RAG_CONFIG.rag_model_version;
    }

    // Show description
    descriptionText.textContent = model.description;
    descriptionDiv.style.display = 'block';
  } else {
    descriptionDiv.style.display = 'none';
  }
}

// Update file processing implementation
async function updateFileProcessingImplementation() {
  const selectedImplementation = document.getElementById('fileProcessingImplementationSelect').value;
  const updateButton = document.querySelector('button[onclick="updateFileProcessingImplementation()"]');

  if (!selectedImplementation) {
    showNotification('Please select an implementation type', 'warning');
    return;
  }

  const token = localStorage.getItem('odras_token');
  if (!token) {
    showNotification('Authentication required to update configuration', 'error');
    return;
  }

  // Update button state
  const originalText = updateButton.textContent;
  updateButton.textContent = 'Updating...';
  updateButton.disabled = true;

  try {
    const requestBody = {
      file_processing_implementation: selectedImplementation
    };

    const response = await fetch('/api/admin/file-processing-config', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(requestBody)
    });

    if (response.ok) {
      const result = await response.json();
      showNotification(`File processing configuration updated successfully! ${result.message}`, 'success');
      console.log('✅ File processing configuration updated:', result);
      await loadFileProcessingConfig(); // Refresh the display
    } else {
      const error = await response.json();
      if (response.status === 401 || response.status === 403) {
        showNotification('Admin access required to update file processing configuration', 'error');
      } else {
        showNotification(`Failed to update file processing configuration: ${error.detail || 'Unknown error'}`, 'error');
      }
      console.error('Failed to update file processing config:', response.status, error);
    }
  } catch (error) {
    console.error('Error updating file processing config:', error);
    showNotification('Error updating file processing configuration. Check console for details.', 'error');
  } finally {
    // Restore button state
    updateButton.textContent = originalText;
    updateButton.disabled = false;
  }
}

// Update RAG implementation
async function updateRagImplementation() {
  const selectedImplementation = document.getElementById('ragImplementationSelect').value;
  const updateButton = document.querySelector('button[onclick="updateRagImplementation()"]');

  if (!selectedImplementation) {
    showNotification('Please select an implementation type', 'warning');
    return;
  }

  // Validate BPMN-specific fields when BPMN is selected
  let selectedModel = null;
  let selectedVersion = null;

  if (selectedImplementation === 'bpmn') {
    selectedModel = document.getElementById('ragBpmnModelSelect').value;
    selectedVersion = document.getElementById('ragModelVersionSelect').value;

    if (!selectedModel) {
      showNotification('Please select a BPMN model', 'warning');
      return;
    }
    if (!selectedVersion) {
      showNotification('Please select a model version', 'warning');
      return;
    }
  }

  const token = localStorage.getItem('odras_token');
  if (!token) {
    showNotification('Authentication required - please login as admin', 'error');
    return;
  }

  // Show loading state
  const originalText = updateButton.textContent;
  updateButton.textContent = 'Updating...';
  updateButton.disabled = true;

  try {
    const requestBody = {
      rag_implementation: selectedImplementation
    };

    // Add BPMN-specific parameters when using BPMN
    if (selectedImplementation === 'bpmn') {
      requestBody.rag_bpmn_model = selectedModel;
      requestBody.rag_model_version = selectedVersion;
    }

    const response = await fetch('/api/admin/rag-config', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(requestBody)
    });

    if (response.ok) {
      const result = await response.json();
      showNotification(`RAG configuration updated successfully! ${result.message}`, 'success');
      console.log('✅ RAG configuration updated:', result);
      await loadRagConfig(); // Refresh the display
    } else {
      const error = await response.json();
      if (response.status === 401 || response.status === 403) {
        showNotification('Admin access required to update RAG configuration', 'error');
      } else {
        showNotification(`Failed to update RAG configuration: ${error.detail || 'Unknown error'}`, 'error');
      }
      console.error('Failed to update RAG config:', response.status, error);
    }
  } catch (error) {
    console.error('Error updating RAG config:', error);
    showNotification('Error updating RAG configuration. Check console for details.', 'error');
  } finally {
    // Restore button state
    updateButton.textContent = originalText;
    updateButton.disabled = false;
  }
}

// Show notification (simple implementation)
function showNotification(message, type = 'info') {
  // Create notification element
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 12px 16px;
    border-radius: 6px;
    color: white;
    font-size: 14px;
    font-weight: 500;
    z-index: 10000;
    max-width: 400px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    transition: all 0.3s ease;
  `;

  // Set color based on type
  switch (type) {
    case 'success':
      notification.style.background = '#10b981';
      break;
    case 'warning':
      notification.style.background = '#f59e0b';
      break;
    case 'error':
      notification.style.background = '#ef4444';
      break;
    default:
      notification.style.background = '#3b82f6';
  }

  notification.textContent = message;
  document.body.appendChild(notification);

  // Auto remove after 4 seconds
  setTimeout(() => {
    notification.style.opacity = '0';
    notification.style.transform = 'translateX(100%)';
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 300);
  }, 4000);
}

// Load namespaces for project ontology creation
async function loadNamespacesForProject(selectElement) {
  try {
    const response = await fetch('/api/admin/namespaces/available/namespaces');
    if (response.ok) {
      const namespaces = await response.json();

      selectElement.innerHTML = '<option value="">Select a namespace...</option>' +
        namespaces.map(ns => `<option value="${ns.id}">${ns.name} (${ns.type}) - ${ns.description || 'No description'}</option>`).join('');
    } else {
      console.error('Failed to load namespaces:', response.status, response.statusText);
      selectElement.innerHTML = '<option value="">Error loading namespaces</option>';
    }
  } catch (error) {
    console.error('Error loading namespaces:', error);
    selectElement.innerHTML = '<option value="">Error loading namespaces</option>';
  }
}

// View ontologies in a namespace
async function viewNamespaceOntologies(namespaceId, namespaceName) {
  try {
    // For now, show a simple modal with placeholder content
    // In a full implementation, this would fetch actual ontologies from the namespace
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
      <div>
        <h3>Ontologies in ${namespaceName}</h3>
        <div style="margin: 20px 0; padding: 16px; background: var(--panel-2); border-radius: 6px; border: 1px solid var(--border);">
          <div style="text-align: center; color: var(--muted);">
            <p>This feature will show all ontologies created using the "${namespaceName}" namespace.</p>
            <p>Currently, this is a placeholder. In a full implementation, this would:</p>
            <ul style="text-align: left; margin: 16px 0;">
              <li>Query the database for ontologies using this namespace</li>
              <li>Show ontology details, creation dates, and owners</li>
              <li>Allow viewing and editing of individual ontologies</li>
              <li>Show URI structure and namespace usage</li>
            </ul>
          </div>
        </div>
        <div class="button-group">
          <button onclick="this.closest('.modal').remove()" class="btn" style="background: var(--muted);">Close</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  } catch (error) {
    console.error('Error viewing namespace ontologies:', error);
    alert(`Error viewing namespace ontologies: ${error.message}`);
  }
}

// Delete a namespace
async function deleteNamespace(namespaceId, namespaceName) {
  try {
    // Confirm deletion
    if (!confirm(`Are you sure you want to delete the namespace "${namespaceName}"?\n\nThis action cannot be undone.`)) {
      return;
    }

    const token = localStorage.getItem('odras_token');
    const response = await fetch(`/api/admin/namespaces/${namespaceId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (response.ok) {
      const result = await response.json();
      alert(`Namespace "${namespaceName}" deleted successfully.`);
      // Refresh the namespace list
      loadNamespaces();
    } else {
      const error = await response.json();
      alert(`Error deleting namespace: ${error.detail || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Error deleting namespace:', error);
    alert('Error deleting namespace: ' + error.message);
  }
}

// Auto-generate namespace name and path based on prefix and type
function updateNamespaceFields() {
  const typeSelect = document.getElementById('nsType');
  const nameInput = document.getElementById('nsName');
  const pathInput = document.getElementById('nsPath');

  if (!typeSelect || !nameInput || !pathInput) return;

  // Use the ordered prefixes
  const selectedPrefixes = selectedPrefixOrder;
  const type = typeSelect.value;

  if (selectedPrefixes.length === 0) {
    nameInput.value = '';
    pathInput.value = '';
    return;
  }

  // Generate name as prefix1-prefix2-type (or just prefix-type if single)
  const prefixString = selectedPrefixes.join('-');
  const name = `${prefixString}-${type}`;
  nameInput.value = name;

  // Generate path based on type and selected prefixes
  let path = '';
  const prefixPath = selectedPrefixes.join('/');

  // Simplified, consistent logic: type always comes after the prefix path
  switch (type) {
    case 'core':
      path = `${prefixPath}/core`;
      break;
    case 'service':
      path = `${prefixPath}/service`;
      break;
    case 'domain':
      path = `${prefixPath}/domain`;
      break;
    case 'program':
      path = `${prefixPath}/program`;
      break;
    case 'project':
      path = `${prefixPath}/project`;
      break;
    case 'industry':
      path = `${prefixPath}/industry`;
      break;
    case 'vocab':
      path = `${prefixPath}/vocab`;
      break;
    case 'shapes':
      path = `${prefixPath}/shapes`;
      break;
    case 'align':
      path = `${prefixPath}/align`;
      break;
    default:
      path = `${prefixPath}/${type}`;
  }

  pathInput.value = path;
}

// Simplified ontology creation - inherits project namespace
async function showCreateOntologyModal() {
  const modal = document.createElement('div');
  modal.className = 'modal';
  modal.innerHTML = `
    <div>
      <h3>Create New Ontology</h3>

      <div style="margin-bottom: 16px;">
        <label>Current Project Namespace:</label>
        <div id="modalNamespaceDisplay" style="padding: 8px; background: var(--panel-2); border: 1px solid var(--border); border-radius: 4px; font-family: monospace; color: var(--muted);">
          Loading project namespace...
        </div>
        <div style="font-size: 0.8em; color: var(--muted); margin-top: 4px;">
          Ontologies inherit their project's namespace automatically
        </div>
      </div>

      <div style="margin-bottom: 16px;">
        <label>Ontology Name:</label>
        <input type="text" id="simpleOntologyName" placeholder="e.g., flight-control" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 4px; background: var(--panel); color: var(--text);" />
      </div>

      <div style="margin-bottom: 16px;">
        <label>Title:</label>
        <input type="text" id="simpleOntologyTitle" placeholder="e.g., Flight Control System Ontology" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 4px; background: var(--panel); color: var(--text);" />
      </div>

      <div style="margin-bottom: 16px;">
        <label>Description:</label>
        <textarea id="simpleOntologyDescription" placeholder="Brief description of the ontology" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 4px; background: var(--panel); color: var(--text); height: 80px; resize: vertical;"></textarea>
      </div>

      <div class="button-group">
        <button onclick="this.closest('.modal').remove()" class="btn" style="background: var(--muted);">Cancel</button>
        <button onclick="createSimpleOntology()" class="btn" style="background: var(--accent); color: white; border-color: var(--accent);">Create Ontology</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);

  // Load current project's namespace for display
  loadCurrentProjectNamespace(document.getElementById('modalNamespaceDisplay'));
}

async function createSimpleOntology() {
  try {
    const name = document.getElementById('simpleOntologyName').value.trim();
    const title = document.getElementById('simpleOntologyTitle').value.trim();
    const description = document.getElementById('simpleOntologyDescription').value.trim();

    if (!name) {
      alert('Please enter an ontology name');
      return;
    }

    const currentProjectId = localStorage.getItem('active_project_id');
    if (!currentProjectId) {
      alert('No project selected - select a project first');
      return;
    }

    const token = localStorage.getItem('odras_token');
    if (!token) {
      alert('No auth token found');
      return;
    }

    console.log('🔧 Creating ontology with inherited namespace:', {
      name, title, description, project: currentProjectId
    });

    const response = await fetch('/api/ontologies', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        project: currentProjectId,
        name: name,
        label: title || name,
        description: description || null
        // No namespace_id - will be inherited from project
      })
    });

    if (response.ok) {
      const newOntology = await response.json();
      console.log('🔧 Created ontology:', newOntology);
      document.querySelector('.modal').remove();

      // Refresh ontology list or switch to new ontology
      // This will depend on your existing ontology management code
      alert('Ontology created successfully!');

      // Reload the current project to show the new ontology
      window.location.reload();
    } else {
      const error = await response.json();
      console.error('🔧 Error creating ontology:', error);
      alert(`Error creating ontology: ${error.detail || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Error creating ontology:', error);
    alert('Error creating ontology: ' + error.message);
  }
}

function updateOntoUriPreview() {
  const type = document.getElementById('ontologyNamespaceType').value;
  const name = document.getElementById('ontologyName').value || 'ontology';

  let uri = INSTALLATION_CONFIG.baseUri;

  if (type === 'core') {
    uri += `/core/${name}`;
  } else if (type === 'domain') {
    const domain = document.getElementById('ontologyDomain').value || 'domain';
    uri += `/${domain}/${name}`;
  } else if (type === 'program') {
    const program = document.getElementById('ontologyProgram').value || 'program';
    uri += `/${program}/core/${name}`;
  } else if (type === 'project') {
    const program = document.getElementById('ontologyProgram').value || 'program';
    const project = document.getElementById('ontologyProject').value || 'project';
    uri += `/${program}/${project}/${name}`;
  } else if (type === 'se') {
    const seDomain = document.getElementById('ontologySeDomain').value || 'se-domain';
    uri += `/se/${seDomain}/${name}`;
  } else if (type === 'mission') {
    const missionType = document.getElementById('ontologyMissionType').value || 'mission-type';
    uri += `/mission/${missionType}/${name}`;
  } else if (type === 'platform') {
    const platformType = document.getElementById('ontologyPlatformType').value || 'platform-type';
    uri += `/platform/${platformType}/${name}`;
  } else {
    uri += `/${name}`;
  }

  document.getElementById('ontologyUriPreview').textContent = uri;
}

async function createOntology() {
  try {
    const type = document.getElementById('ontologyNamespaceType').value;
    const name = document.getElementById('ontologyName').value;
    const title = document.getElementById('ontologyTitle').value || name;
    const description = document.getElementById('ontologyDescription').value;

    if (!name) {
      alert('Please enter an ontology name');
      return;
    }

    // Generate the URI
    let uri = INSTALLATION_CONFIG.baseUri;
    let projectId = 'core';

    if (type === 'core') {
      uri += `/core/${name}`;
      projectId = 'core';
    } else if (type === 'domain') {
      const domain = document.getElementById('ontologyDomain').value || 'domain';
      uri += `/${domain}/${name}`;
      projectId = `domain-${domain}`;
    } else if (type === 'program') {
      const program = document.getElementById('ontologyProgram').value || 'program';
      uri += `/${program}/core/${name}`;
      projectId = `program-${program}`;
    } else if (type === 'project') {
      const program = document.getElementById('ontologyProgram').value || 'program';
      const project = document.getElementById('ontologyProject').value || 'project';
      uri += `/${program}/${project}/${name}`;
      projectId = `project-${program}-${project}`;
    } else if (type === 'se') {
      const seDomain = document.getElementById('ontologySeDomain').value || 'se-domain';
      uri += `/se/${seDomain}/${name}`;
      projectId = `se-${seDomain}`;
    } else if (type === 'mission') {
      const missionType = document.getElementById('ontologyMissionType').value || 'mission-type';
      uri += `/mission/${missionType}/${name}`;
      projectId = `mission-${missionType}`;
    } else if (type === 'platform') {
      const platformType = document.getElementById('ontologyPlatformType').value || 'platform-type';
      uri += `/platform/${platformType}/${name}`;
      projectId = `platform-${platformType}`;
    } else {
      uri += `/${name}`;
      projectId = 'general';
    }

    // Create the ontology
    const response = await authenticatedFetch('/api/ontology', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project: projectId,
        name: name,
        label: title,
        description: description,
        is_reference: true  // These are reference ontologies
      })
    });

    if (response.ok) {
      const result = await response.json();
      console.log('✅ Ontology created:', result);
      document.querySelector('.modal').remove();
      await loadNamespaces();
      alert('Ontology created successfully!');
    } else {
      const error = await response.text();
      throw new Error(`HTTP ${response.status}: ${error}`);
    }
  } catch (error) {
    console.error('Error creating ontology:', error);
    alert(`Error creating ontology: ${error.message}`);
  }
}

function computeOntologyIri(projectId, name, version) {
  // This function generates project-scoped ontology URIs following the namespace design
  // Pattern: {base_uri}/{namespace_path}/{project_uuid}/ontologies/{name}
  console.log('⚠️ computeOntologyIri called - this may be generating old-format URIs');
  console.log('Project ID:', projectId, 'Name:', name, 'Version:', version);

  // For now, return a simple placeholder - the backend ResourceURIService should handle proper URI generation
  const pid = encodeURIComponent(projectId || 'project');
  const n = slugify(name || 'ontology');
  const ver = version ? ('/v' + encodeURIComponent(version)) : '';

  // Note: This is a legacy pattern - proper URIs should come from backend ResourceURIService
  const uri = `${INSTALLATION_CONFIG.baseUri}/legacy/${pid}/${n}${ver}`;
  console.log('⚠️ Generated legacy URI:', uri, '(should be replaced by backend service)');
  return uri;
}

async function handleTreeSelection(li) {
  if (!li || !li.dataset) return;
  const type = li.dataset.nodeType || '';

  if (type === 'ontology') {
    const iri = li.dataset.iri;
    if (iri) {
      // Save previous active ontology canvas before switching
      const prevIri = activeOntologyIri;
      ensureOntologyInitialized();
      if (ontoState.cy && prevIri) {
        saveGraphToLocal(prevIri);
      }
      // Switch active ontology
      activeOntologyIri = iri;
      try {
        const pid = (activeProject && (activeProject.id || activeProject.project_id)) ? (activeProject.id || activeProject.project_id) : 'default';
        localStorage.setItem(`onto_active_iri__${pid}`, iri);
        // Set model name for properties panel based on discovered label or IRI tail
        const friendly = (li.dataset.label && li.dataset.label.trim()) || iri.split('/').pop() || iri;
        // FIXED: Use ontology-specific localStorage keys consistently  
        const ontologyKey = iri ? iri.split('/').pop() : 'default';
        const modelNameKey = `onto_model_name__${pid}__${ontologyKey}`;
        const modelAttrsKey = `onto_model_attrs__${pid}__${ontologyKey}`;

        localStorage.setItem(modelNameKey, friendly);
        // Also store display label, graph, and namespace in model attributes
        let attrs = {};

        try { attrs = JSON.parse(localStorage.getItem(modelAttrsKey) || '{}'); } catch (_) { attrs = {}; }
        attrs.displayLabel = friendly;
        attrs.graphIri = iri;
        // Set namespace based on installation configuration
        attrs.namespace = iri;  // Use the actual graph IRI as namespace
        localStorage.setItem(modelAttrsKey, JSON.stringify(attrs));
        // Keep project-scoped label map in sync so the top node reflects selection
        try { saveOntologyLabel(iri, friendly); } catch (_) { }

        // Load collapsed imports state for this ontology
        ontoState.collapsedImports = loadCollapsedImports(iri);

        // Load visibility state for this ontology
        ontoState.visibilityState = loadVisibilityState(iri);

        // Load individual element visibility for this ontology
        ontoState.elementVisibility = loadElementVisibility(iri);
      } catch (_) { }
      updateOntoGraphLabel();
      // Load new graph from local storage if present, otherwise fetch from API
      if (ontoState.cy) {
        // Avoid racing autosave during restore
        ontoState.suspendAutosave = true;
        try { ontoState.cy.elements().remove(); } catch (_) { }
        await loadGraphFromLocalOrAPI(iri);
        // Refresh overlay imports to restore visible imported ontologies
        await overlayImportsRefresh();
        // Apply saved visibility states after overlay refresh
        updateCanvasVisibility();
        setTimeout(() => { ontoState.suspendAutosave = false; }, 50);
      }
      // Show model-level props when nothing selected
      updatePropertiesPanelFromSelection();
      // Rebuild ontology tree (top node label and contents)
      try { refreshOntologyTree(); } catch (_) { }
      // Switch to Ontology workbench view unless suppressed during restore
      if (!suppressWorkbenchSwitch) {
        const ico = document.querySelector('.icon[data-wb="ontology"]');
        if (ico && !document.querySelector('#wb-ontology.workbench.active')) {
          ico.click();
        }
      }
      // Reflect in hash for deep-linking (preserve current workbench)
      try {
        const params = new URLSearchParams(location.hash.replace(/^#/, ''));
        const wb = localStorage.getItem('active_workbench') || 'ontology';
        params.set('wb', wb);
        params.set('graph', encodeURIComponent(iri));
        location.hash = params.toString();
      } catch (_) { }
    }
  } else if (type === 'class' || type === 'dataProperty' || type === 'note') {
    // Handle individual element selection
    const nodeId = li.dataset.nodeId;
    if (nodeId && ontoState.cy) {
      // Clear current selection
      ontoState.cy.$(':selected').unselect();

      // Find and select the corresponding node in the canvas (escape special characters in ID)
      const node = ontoState.cy.$(`#${CSS.escape(nodeId)}`);
      if (node.length > 0) {
        node.select();

        // Center the view on the selected node
        ontoState.cy.animate({
          center: { eles: node },
          zoom: Math.max(ontoState.cy.zoom(), 0.8) // Ensure minimum zoom level
        }, {
          duration: 300
        });

        // Update properties panel with selected element data
        updatePropertiesPanelFromSelection();
      } else {
        console.log('🔍 Could not find node with ID:', nodeId);
      }
    }
  } else if (type === 'namedView') {
    // Handle named view selection with toggle functionality
    const viewId = li.dataset.viewId;
    if (viewId) {
      const views = await loadNamedViews(activeOntologyIri);
      const view = views.find(v => v.id === viewId);
      if (view) {
        if (ontoState.activeNamedView === viewId) {
          // Toggle off - restore original state before any named views
          console.log('🔍 Toggling off named view:', view.name, 'returning to original state');
          if (ontoState.beforeViewState) {
            restoreOriginalState();
          } else {
            ontoState.activeNamedView = null;
            refreshOntologyTree();
          }
        } else {
          // Capture current state as "before state" if this is the first named view applied
          if (!ontoState.activeNamedView && !ontoState.beforeViewState) {
            console.log('🔍 Capturing current state before applying first named view');
            ontoState.beforeViewState = captureCurrentView('__original_state__');
          }

          // Apply the view
          console.log('🔍 Applying named view:', view.name, 'with visible imports:', view.visibleImports);
          restoreView(view);
        }
      }
    }
  } else if (type === 'edge') {
    // Handle edge selection
    const edgeId = li.dataset.edgeId;
    if (edgeId && ontoState.cy) {
      // Clear current selection
      ontoState.cy.$(':selected').unselect();

      // Find and select the corresponding edge in the canvas (escape special characters in ID)
      const edge = ontoState.cy.$(`#${CSS.escape(edgeId)}`);
      if (edge.length > 0) {
        edge.select();

        // Center the view on the selected edge
        ontoState.cy.animate({
          center: { eles: edge },
          zoom: Math.max(ontoState.cy.zoom(), 0.8)
        }, {
          duration: 300
        });

        // Update properties panel with selected element data
        updatePropertiesPanelFromSelection();
      } else {
        console.log('🔍 Could not find edge with ID:', edgeId);
      }
    }
  }
}
function ensureOntologyInitialized() {
  if (ontoState.cy) return;
  const container = qs('#cy');
  if (!container) return;
  // Make canvas focusable for keyboard events (Delete)
  try { container.setAttribute('tabindex', '0'); container.style.outline = 'none'; } catch (_) { }
  try {
    if (window.cytoscape && (window.cytoscapeEdgehandles || window.edgehandles)) {
      const plugin = window.cytoscapeEdgehandles || window.edgehandles;
      if (plugin && typeof plugin === 'function') window.cytoscape.use(plugin);
    }
  } catch (_) { }
  ontoState.cy = cytoscape({
    container,
    layout: {
      name: 'breadthfirst',
      directed: true,           // Treat as directed graph for hierarchy
      spacingFactor: 2.0,       // More spacing between nodes
      avoidOverlap: true,       // Prevent node overlap
      nodeDimensionsIncludeLabels: true, // Account for label size
      animate: true,            // Smooth animation
      animationDuration: 500,   // Animation duration
      fit: true,                // Fit to container
      padding: 50               // Padding around graph
    },
    wheelSensitivity: 0.15,  // Much more gentle mouse wheel zoom (default: 1)
    minZoom: 0.1,
    maxZoom: 3,
    // CAD-like features
    boxSelectionEnabled: true,  // Enable selection box like SolidWorks
    selectionType: 'single',   // Single selection by default, Ctrl+click for multi-select
    style: [
      {
        selector: 'node', style: {
          'shape': 'round-rectangle',
          'background-color': '#1b2a45',
          'border-color': '#2a3b5f',
          'border-width': 1,
          'label': 'data(label)',
          'color': '#e5e7eb',
          'font-size': 12,
          'text-wrap': 'wrap',
          'text-max-width': 180,
          'text-valign': 'center',
          'text-halign': 'center'
        }
      },
      { selector: 'node[type = "class"]', style: { 'width': 180, 'height': 56 } },
      {
        selector: 'node[type = "dataProperty"]', style: {
          'width': 160,
          'height': 48,
          'background-color': '#154e5a',
          'border-color': '#2ea3b0'
        }
      },
      {
        selector: 'edge', style: {
          'curve-style': 'bezier',
          'width': 2,
          'line-color': '#3b4a6b',
          'target-arrow-shape': 'triangle',
          'target-arrow-color': '#3b4a6b',
          'arrow-scale': 1,
          'label': 'data(predicate)',
          'color': '#e5e7eb',
          'font-size': 10,
          'text-rotation': 'autorotate',
          'text-background-color': '#0b1220',
          'text-background-opacity': 0.6,
          'text-background-padding': 2,
          // Multiplicity label at target (arrow tip) - only for edges with multiplicity
          'target-label': 'data(multiplicityDisplay)',
          'target-text-offset': 15,  // Distance from arrow tip
          'target-text-rotation': 0,  // Keep horizontal
          'target-text-color': '#60a5fa',  // Accent color for visibility
          'target-text-background-color': '#0b1220',
          'target-text-background-opacity': 0.8,
          'target-text-background-padding': 3,
          'target-text-border-width': 1,
          'target-text-border-color': '#60a5fa',
          'target-text-border-opacity': 0.5
        }
      },
      {
        selector: 'edge[type = "note"], edge[predicate = "note_for"]', style: {
          'target-arrow-shape': 'circle',
          'target-arrow-color': '#9ca3af',
          'arrow-scale': 0.8,
          'source-arrow-shape': 'none'
        }
      },
      {
        selector: '.imported', style: {
          'opacity': 0.55
        }
      },
      { selector: 'edge.imported', style: { 'line-style': 'dashed' } },
      {
        selector: 'edge.imported-equivalence', style: {
          'line-style': 'dotted',
          'width': 1.5,
          'line-color': '#60a5fa',
          'label': '≡',
          'color': '#9ca3af',
          'font-size': 9,
          'text-background-opacity': 0
        }
      },
      {
        selector: 'node[type = "note"], .note', style: {
          'shape': 'rectangle',
          'background-color': function (ele) {
            const noteType = ele.data('attrs') && ele.data('attrs').noteType;
            return getNoteTypeStyle(noteType || 'Note').backgroundColor;
          },
          'border-color': function (ele) {
            const noteType = ele.data('attrs') && ele.data('attrs').noteType;
            return getNoteTypeStyle(noteType || 'Note').borderColor;
          },
          'border-style': 'solid',
          'border-width': 1,
          'label': function (ele) {
            const noteType = ele.data('attrs') && ele.data('attrs').noteType;
            const symbol = getNoteTypeStyle(noteType || 'Note').symbol;
            const content = ele.data('attrs') && ele.data('attrs').content;
            const text = content || ele.data('label') || 'Note';
            return symbol + ' ' + text;
          },
          'color': function (ele) {
            const noteType = ele.data('attrs') && ele.data('attrs').noteType;
            return getNoteTypeStyle(noteType || 'Note').textColor;
          },
          'font-size': 12,
          'text-wrap': 'wrap',
          'text-max-width': 220,
          'text-valign': 'center',
          'text-halign': 'center',
          'width': 220, 'height': 80
        }
      },
      {
        selector: ':selected', style: {
          'border-color': '#60a5fa',
          'border-width': 2,
          'line-color': '#60a5fa',
          'target-arrow-color': '#60a5fa'
        }
      }
    ],
    elements: []
  });
  window._cy = ontoState.cy;
  ontoState.nextId = 1;
  // Focus canvas on interaction so Delete works reliably
  ontoState.cy.on('tap', () => { try { container.focus(); } catch (_) { } });
  ontoState.cy.on('select', () => { try { container.focus(); } catch (_) { } });
  try { container.addEventListener('keydown', handleDeleteKey); } catch (_) { }

  // Mark canvas active on any interaction
  ontoState.cy.on('tap', () => { ontoState.isCanvasActive = true; });

  if (typeof ontoState.cy.edgehandles === 'function') {
    ontoState.eh = ontoState.cy.edgehandles({
      handleSize: 8,
      handleNodes: 'node[type = "class"], node[type = "note"]',
      handleColor: '#60a5fa',
      handleOutlineColor: '#0b1220',
      handleOutlineWidth: 2,
      toggleOffOnLeave: true,
      enabled: true,
      edgeParams: () => ({ data: { predicate: 'relatedTo', type: 'objectProperty' } })
    });
    ontoState.cy.on('ehcomplete', (event, sourceNode, targetNode, addedEdge) => {
      try {
        const srcType = (sourceNode.data('type') || 'class');
        const tgtType = (targetNode.data('type') || 'class');
        const edgeType = (addedEdge && addedEdge.data('type')) || ontoState.currentPredicateType || 'objectProperty';
        let invalid = false;
        // Allow note -> class as 'note_for' (reverse if class->note used)
        if ((srcType === 'note' && (tgtType === 'class' || tgtType === 'dataProperty')) || ((srcType === 'class' || srcType === 'dataProperty') && tgtType === 'note')) {
          // Ensure direction note -> class
          if ((srcType === 'class' || srcType === 'dataProperty') && tgtType === 'note') {
            addedEdge.data('source', targetNode.id());
            addedEdge.data('target', sourceNode.id());
          }
          addedEdge.data('predicate', 'note_for');
          addedEdge.data('type', 'note');
        } else {
          // For object properties, only allow class→class
          if (edgeType === 'objectProperty' && (srcType !== 'class' || tgtType !== 'class')) invalid = true;
          // Disallow any other note edges
          if (srcType === 'note' || tgtType === 'note') invalid = true;
          if (invalid && addedEdge) { addedEdge.remove(); return; }
        }
      } catch (_) { }
      requestAnimationFrame(() => { refreshOntologyTree(); persistOntologyToLocalStorage(); });
    });
    ontoState.cy.on('select unselect add remove data free', () => {
      updatePropertiesPanelFromSelection();
      persistOntologyToLocalStorage();

      // Highlight corresponding tree item when canvas selection changes
      const selected = ontoState.cy.$(':selected');
      if (selected.length === 1) {
        const element = selected[0];
        if (element.isNode()) {
          highlightTreeItem(element.id(), 'node');
        } else if (element.isEdge()) {
          highlightTreeItem(element.id(), 'edge');
        }
      } else {
        // Clear tree selection when nothing is selected on canvas
        qsa('.node-row').forEach(r => r.classList.remove('selected'));
      }
    });
    // Persist overlay positions when moved
    ontoState.cy.on('free', 'node.imported', (ev) => {
      try {
        const n = ev.target; const imp = n.data('importSource');
        if (!imp || !activeOntologyIri) return;
        const curr = loadOverlayPositions(activeOntologyIri, imp);
        curr[n.id()] = n.position();
        console.log('🔍 Saving position for', n.id(), ':', n.position(), 'in import', imp);
        saveOverlayPositions(activeOntologyIri, imp, curr);
      } catch (_) { }
    });
    // Persist overlay positions when moved
    ontoState.cy.on('free', 'node.imported', (ev) => {
      try {
        const n = ev.target; const imp = n.data('importSource');
        if (!imp || !activeOntologyIri) return;
        const curr = loadOverlayPositions(activeOntologyIri, imp);
        curr[n.id()] = n.position();
        console.log('🔍 Saving position for', n.id(), ':', n.position(), 'in import', imp);
        saveOverlayPositions(activeOntologyIri, imp, curr);
      } catch (_) { }
    });
  } else {
    ontoState.cy.on('tap', 'node', (ev) => {
      if (!ontoState.connectMode) return;
      const node = ev.target;
      if (!ontoState.clickConnectFrom) {
        ontoState.clickConnectFrom = node.id();
      } else {
        const from = ontoState.clickConnectFrom;
        const to = node.id();
        if (from !== to) {
          const src = ontoState.cy.$(`#${from}`)[0];
          const tgt = ontoState.cy.$(`#${to}`)[0];
          const srcType = (src && (src.data('type') || 'class')) || 'class';
          const tgtType = (tgt && (tgt.data('type') || 'class')) || 'class';
          if (srcType !== 'note' && tgtType !== 'note' && srcType === 'class' && tgtType === 'class') {
            const edgeAttrs = addCreationMetadata({});
            ontoState.cy.add({ group: 'edges', data: { id: `e${Date.now()}`, source: from, target: to, predicate: 'relatedTo', type: 'objectProperty', attrs: edgeAttrs } });
            refreshOntologyTree();
            persistOntologyToLocalStorage();
          }
        }
        ontoState.clickConnectFrom = null;
      }
    });
    ontoState.cy.on('select unselect add remove data free', () => {
      updatePropertiesPanelFromSelection();
      persistOntologyToLocalStorage();

      // Highlight corresponding tree item when canvas selection changes
      const selected = ontoState.cy.$(':selected');
      if (selected.length === 1) {
        const element = selected[0];
        if (element.isNode()) {
          highlightTreeItem(element.id(), 'node');
        } else if (element.isEdge()) {
          highlightTreeItem(element.id(), 'edge');
        }
      } else {
        // Clear tree selection when nothing is selected on canvas
        qsa('.node-row').forEach(r => r.classList.remove('selected'));
      }
    });
  }

  // Background click clears selection and shows model-level props
  ontoState.cy.on('tap', (ev) => {
    if (ev.target === ontoState.cy) {
      ontoState.cy.$(':selected').unselect();
      updatePropertiesPanelFromSelection();
      hideMenu();
      hideEdgeMenu();
      clearConnectState();
    }
  });

  // Inline label editor on F2 or Enter when focused
  ontoState.cy.on('cxttap', 'node', (ev) => {
    const n = ev.target; const t = (n.data('type') || 'class');
    const rect = qs('#cy').getBoundingClientRect();
    const rp = ev.renderedPosition || n.renderedPosition();
    // Configure menu per node type
    const menu = qs('#ontoContextMenu');
    if (!menu) return;
    const btnRel = qs('#menuAddRel');
    const btnDP = qs('#menuAddDataProp');
    if (t === 'note') {
      if (btnRel) {
        btnRel.innerHTML = `
          <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="7" cy="12" r="3"/><circle cx="17" cy="12" r="3"/><path d="M10 12h4"/>
          </svg>
          Link to Class/Property
        `;
      }
      if (btnDP) btnDP.style.display = 'none';
    } else {
      if (btnRel) {
        btnRel.innerHTML = `
          <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="7" cy="12" r="3"/><circle cx="17" cy="12" r="3"/><path d="M10 12h4"/>
          </svg>
          Add Relationship
        `;
      }
      if (btnDP) btnDP.style.display = 'block';
    }
    showMenuAt(rect.left + rp.x + 6, rect.top + rp.y + 6);
    menu.dataset.nodeId = n.id();
    menu.dataset.nodeType = t;
  });

  // Edge right-click context menu for multiplicity constraints
  ontoState.cy.on('cxttap', 'edge', (ev) => {
    const edge = ev.target;
    const edgeData = edge.data();

    // Only show context menu for object properties (relationships)
    if (edgeData.type !== 'objectProperty') return;

    // Don't allow editing of imported elements
    if (edge.hasClass('imported')) {
      console.log('🔍 Cannot edit imported edge:', edge.data('predicate'));
      return;
    }

    const rect = qs('#cy').getBoundingClientRect();
    const rp = ev.renderedPosition || edge.renderedMidpoint();

    showEdgeMenuAt(rect.left + rp.x + 6, rect.top + rp.y + 6);
    const edgeMenu = qs('#edgeContextMenu');
    if (edgeMenu) {
      edgeMenu.dataset.edgeId = edge.id();
    }
  });
  function showInlineEditor(target) {
    // Don't allow editing of imported elements
    if (target.hasClass('imported')) {
      console.log('🔍 Cannot edit imported element:', target.data('label'));
      return;
    }

    const input = qs('#ontoInlineEdit'); if (!input) return;
    const pos = target.renderedPosition();
    const rect = qs('#cy').getBoundingClientRect();

    let current = '';
    if (target.isNode()) {
      const nodeType = target.data('type') || 'class';
      if (nodeType === 'note') {
        // For notes, show the current rdfs:comment from attributes  
        const attrs = target.data('attrs') || {};
        current = attrs.content || '';  // Use 'content' to match the template mapping
      } else {
        // For other nodes, show the label as before
        current = target.data('label') || '';
      }
    } else {
      // For edges, show predicate
      current = target.data('predicate') || '';
    }

    input.value = current;
    input.style.left = (rect.left + pos.x - Math.min(100, rect.width * 0.2)) + 'px';
    input.style.top = (rect.top + pos.y - 12) + 'px';
    input.style.display = 'block';
    input.focus();
    input.select();
    function commit(save) {
      if (save) {
        const v = input.value.trim();
        if (target.isNode()) {
          const nodeType = target.data('type') || 'class';

          if (nodeType === 'note') {
            // For notes, update the rdfs:comment in attributes, not the label
            const currentAttrs = target.data('attrs') || {};
            currentAttrs.content = v || current;  // Use 'content' to match the template mapping
            const updatedAttrs = updateModificationMetadata(currentAttrs);
            target.data('attrs', updatedAttrs);
          } else {
            // For other nodes (classes, etc.), update the label as before
            target.data('label', v || current);
            // Update modification metadata for inline label changes
            const currentAttrs = target.data('attrs') || {};
            const updatedAttrs = updateModificationMetadata(currentAttrs);
            target.data('attrs', updatedAttrs);
          }
        } else {
          target.data('predicate', v || current);
          // Update modification metadata for inline predicate changes
          const currentAttrs = target.data('attrs') || {};
          const updatedAttrs = updateModificationMetadata(currentAttrs);
          target.data('attrs', updatedAttrs);
        }
        refreshOntologyTree();
        persistOntologyToLocalStorage();
      }
      input.style.display = 'none';
      input.onkeydown = null; input.onblur = null;
    }
    input.onkeydown = (e) => {
      if (e.key === 'Enter') commit(true);
      else if (e.key === 'Escape') commit(false);
    };
    input.onblur = () => commit(true);
  }
  ontoState.cy.on('keydown', 'node,edge', (ev) => {
    if (ev.originalEvent && ev.originalEvent.key === 'F2') showInlineEditor(ev.target);
  });
  // Double-click to edit
  ontoState.cy.on('dblclick', 'node,edge', (ev) => showInlineEditor(ev.target));

  // CAD-like snap-to-grid (only on drag end for smooth experience)
  ontoState.cy.on('dragfree', 'node', (ev) => {
    const node = ev.target;
    if (ontoState.snapToGrid && !node.hasClass('imported')) {
      const snappedPos = snapToGrid(node.position());
      node.position(snappedPos);
      showTemporaryMessage(`Snapped to grid (${snappedPos.x}, ${snappedPos.y})`, 800);
    }
  });

  // Add to undo stack on significant changes
  ontoState.cy.on('add remove', (ev) => {
    const actionType = ev.type;
    const elementType = ev.target.isNode() ? 'node' : 'edge';
    addToUndoStack(actionType, { elementType, count: 1 });
  });

  // Update position inputs when nodes are moved (CAD-like coordinate display)
  ontoState.cy.on('position', 'node', (ev) => {
    // Only update if this node is currently selected
    const node = ev.target;
    if (node.selected()) {
      updatePositionInputs();
    }
  });

  // Context menu actions
  document.addEventListener('click', (e) => {
    const menu = qs('#ontoContextMenu');
    if (!menu) return;
    if (e.target === qs('#menuCancel')) { hideMenu(); return; }
    if (e.target === qs('#menuAddRel')) {
      hideMenu();
      const id = menu.dataset.nodeId; if (!id) return;
      const node = ontoState.cy.$('#' + id)[0]; if (!node) return;
      const t = menu.dataset.nodeType || 'class';
      clearConnectState(); startConnectFrom(node); cmState.sourceType = t;
      return;
    }
    if (e.target === qs('#menuAddDataProp')) {
      hideMenu();
      const id = menu.dataset.nodeId; if (!id) return;
      const node = ontoState.cy.$('#' + id)[0]; if (!node) return;
      // Add a default data property node near the class
      const pos = node.position();
      const pid = `DP${Date.now()}`;
      const label = `Data Property ${Date.now() % 1000}`;
      const dpAttrs = addCreationMetadata({});
      ontoState.cy.add({ group: 'nodes', data: { id: pid, label, type: 'dataProperty', attrs: dpAttrs }, position: { x: pos.x + 120, y: pos.y } });
      // Use objectProperty for the visual connector edge
      const edgeAttrs = addCreationMetadata({});
      ontoState.cy.add({ group: 'edges', data: { id: `edp${Date.now()}`, source: id, target: pid, predicate: label, type: 'objectProperty', attrs: edgeAttrs } });
      refreshOntologyTree(); persistOntologyToLocalStorage();
      return;
    }
  });

  // Edge context menu actions for multiplicity constraints
  document.addEventListener('click', (e) => {
    const edgeMenu = qs('#edgeContextMenu');
    if (!edgeMenu || edgeMenu.style.display === 'none') return;

    const action = e.target.dataset.action;
    if (!action && e.target.id !== 'edgeMenuCancel') return;

    if (e.target.id === 'edgeMenuCancel') {
      hideEdgeMenu();
      return;
    }

    const edgeId = edgeMenu.dataset.edgeId;
    const edge = edgeId ? ontoState.cy.$('#' + edgeId)[0] : null;

    if (!edge) {
      hideEdgeMenu();
      return;
    }

    let minCount = null, maxCount = null;

    switch (action) {
      case 'mult-none':
        minCount = null; maxCount = null;
        break;
      case 'mult-1':
        minCount = 1; maxCount = 1;
        break;
      case 'mult-0-1':
        minCount = 0; maxCount = 1;
        break;
      case 'mult-0-*':
        minCount = 0; maxCount = null;
        break;
      case 'mult-1-*':
        minCount = 1; maxCount = null;
        break;
      case 'mult-custom':
        hideEdgeMenu();
        showCustomMultiplicityDialog(edge);
        return;
      case 'edit-edge':
        hideEdgeMenu();
        showInlineEditor(edge);
        return;
      default:
        return;
    }

    // Update edge multiplicity
    updateEdgeMultiplicity(edge, minCount, maxCount);
    hideEdgeMenu();
  });
  // Clicking a target after 'Add relationship' completes the edge
  ontoState.cy.on('tap', 'node', (ev) => {
    const target = ev.target; if (!cmState.sourceId) return;
    const tgtType = (target.data('type') || 'class');
    const source = ontoState.cy.$('#' + cmState.sourceId)[0]; if (!source) { clearConnectState(); return; }
    const srcType = cmState.sourceType || (source.data('type') || 'class');
    if (source.id() !== target.id()) {
      if (srcType === 'note' && (tgtType === 'class' || tgtType === 'dataProperty')) {
        const edgeAttrs = addCreationMetadata({});
        ontoState.cy.add({ group: 'edges', data: { id: `enote${Date.now()}`, source: source.id(), target: target.id(), predicate: 'note_for', type: 'note', attrs: edgeAttrs } });
        refreshOntologyTree(); persistOntologyToLocalStorage();
      } else if (srcType === 'class' && tgtType === 'class') {
        const edgeAttrs = addCreationMetadata({});
        ontoState.cy.add({ group: 'edges', data: { id: `e${Date.now()}`, source: source.id(), target: target.id(), predicate: 'relatedTo', type: 'objectProperty', attrs: edgeAttrs } });
        refreshOntologyTree(); persistOntologyToLocalStorage();
      }
    }
    source.removeClass('connect-source');
    clearConnectState();
  });

  // Drag-and-drop from tool icons
  const icons = Array.from(document.querySelectorAll('.onto-icon'));
  icons.forEach(icon => {
    icon.addEventListener('dragstart', (ev) => {
      ev.dataTransfer.setData('text/onto-type', icon.getAttribute('data-onto-type') || 'class');
      try { ev.dataTransfer.effectAllowed = 'copy'; } catch (_) { }
    });
  });

  container.addEventListener('dragenter', (ev) => { ev.preventDefault(); });
  container.addEventListener('dragover', (ev) => { ev.preventDefault(); ontoState.isCanvasActive = true; try { ev.dataTransfer.dropEffect = 'copy'; } catch (_) { } });
  container.addEventListener('drop', async (ev) => {
    ev.preventDefault();
    ontoState.isCanvasActive = true;
    const ontoType = ev.dataTransfer.getData('text/onto-type') || 'class';
    const rect = container.getBoundingClientRect();
    const renderedPos = { x: ev.clientX - rect.left, y: ev.clientY - rect.top };
    const pan = ontoState.cy.pan();
    const zoom = ontoState.cy.zoom();
    const pos = { x: (renderedPos.x - pan.x) / zoom, y: (renderedPos.y - pan.y) / zoom };
    if (ontoType === 'class') {
      const label = `Class ${ontoState.nextId}`;
      const id = await addClassNodeAt(label, pos);
      if (id) { ontoState.cy.$('#' + id).select(); }
    } else if (ontoType === 'objectProperty') {
      ontoState.currentPredicateType = 'objectProperty';
      setConnectMode(true);
      // With edgehandles enabled, user can drag handle from a class to another class
    } else if (ontoType === 'dataProperty') {
      const sel = ontoState.cy.nodes(':selected').filter(n => (n.data('type') || 'class') === 'class');
      if (sel.length !== 1) { return; }
      const prop = `Data Property ${Date.now() % 1000}`;
      const pid = `DP${Date.now()}`;
      const dpAttrs = addCreationMetadata({});
      ontoState.cy.add({ group: 'nodes', data: { id: pid, label: prop, type: 'dataProperty', attrs: dpAttrs }, position: pos });
      // Link edge is a visual connector; keep it as objectProperty for consistency
      const edgeAttrs = addCreationMetadata({});
      ontoState.cy.add({ group: 'edges', data: { id: `edp${Date.now()}`, source: sel[0].id(), target: pid, predicate: prop, type: 'objectProperty', attrs: edgeAttrs } });
      refreshOntologyTree();
    } else if (ontoType === 'note') {
      const nid = `Note${Date.now()}`;
      const text = `Note ${nid.slice(-4)}`;

      // Add note with proper metadata
      const attrs = addCreationMetadata({
        noteType: 'Note',
        author: getCurrentUsername() // Keep legacy field for backward compatibility
      });

      ontoState.cy.add({
        group: 'nodes',
        data: {
          id: nid,
          label: text,
          type: 'note',
          attrs
        },
        position: pos,
        classes: 'note'
      });
      // If exactly one class is selected, auto-link note -> class
      const sel = ontoState.cy.nodes(':selected').filter(n => (n.data('type') || 'class') === 'class');
      if (sel && sel.length === 1) {
        const edgeAttrs = addCreationMetadata({});
        ontoState.cy.add({ group: 'edges', data: { id: `enote${Date.now()}`, source: nid, target: sel[0].id(), predicate: 'note_for', type: 'note', attrs: edgeAttrs } });
      }
      refreshOntologyTree(); persistOntologyToLocalStorage();
    }
    persistOntologyToLocalStorage();
  });
  // Bind autosave on edits (add/remove/data) - NOT position changes
  try {
    const autosave = debounce(() => { try { if (activeOntologyIri) persistOntologyToLocalStorage(); } catch (_) { } }, 250);
    ontoState.cy.on('add remove data', autosave);  // Removed 'position' event

    // Create a separate debounced save for layout changes with longer delay
    const layoutSave = debounce(() => {
      try {
        if (activeOntologyIri && !ontoState.layoutRunning) {
          console.log('🔄 Layout save triggered after 5 second delay');
          const nodes = ontoState.cy.nodes().filter(n => !n.hasClass('imported')).map(n => ({ data: n.data(), position: n.position() }));
          const edges = ontoState.cy.edges().filter(e => !e.hasClass('imported')).map(e => ({ data: e.data() }));
          saveLayoutToServer(activeOntologyIri, nodes, edges);
        } else if (ontoState.layoutRunning) {
          console.log('⏸️ Layout save skipped - layout algorithm is running');
        }
      } catch (_) { }
    }, 5000); // 5 second delay for layout saves

    // Create a fast debounced save for localStorage (100ms) to prevent excessive writes
    const localStorageSave = debounce(() => {
      try {
        if (activeOntologyIri && !ontoState.layoutRunning) {
          persistOntologyToLocalStorage();

          // Also save layout to localStorage for quick recovery
          const pan = ontoState.cy.pan();
          const zoom = ontoState.cy.zoom();
          const nodes = ontoState.cy.nodes().filter(n => !n.hasClass('imported')).map(n => ({
            iri: n.data('id'),
            x: n.position('x'),
            y: n.position('y')
          }));

          const layoutData = {
            nodes: nodes,
            zoom: zoom,
            pan: pan,
            timestamp: Date.now()
          };

          const localLayoutKey = `onto_layout_${encodeURIComponent(activeOntologyIri)}`;
          localStorage.setItem(localLayoutKey, JSON.stringify(layoutData));
          console.log('💾 Layout saved to localStorage');
        }
      } catch (_) { }
    }, 100); // Very short delay - just to batch rapid movements

    ontoState.cy.on('position', layoutSave);
    ontoState.cy.on('position', localStorageSave); // Also save to localStorage quickly
    ontoState.autosaveBound = true;

    // Update modification metadata when elements are moved
    ontoState.cy.on('position', 'node', (evt) => {
      try {
        const node = evt.target;
        if (!node.hasClass('imported')) { // Don't update metadata for imported elements
          const currentAttrs = node.data('attrs') || {};
          const updatedAttrs = updateModificationMetadata(currentAttrs);
          node.data('attrs', updatedAttrs);
        }
      } catch (_) { }
    });
  } catch (_) { }

  // Initialize element IRI display
  updateElementIriDisplay();
}

async function addClassNode(label) {
  ensureOntologyInitialized();
  const id = `Class${ontoState.nextId++}`;
  const x = 100 + Math.random() * 400;
  const y = 100 + Math.random() * 300;

  // Add to Cytoscape graph first with metadata
  const attrs = addCreationMetadata({});
  ontoState.cy.add({ group: 'nodes', data: { id, label, type: 'class', attrs }, position: { x, y } });

  // Call backend API to persist to Fuseki with correct graph context
  try {
    const graphUri = activeOntologyIri;
    const url = graphUri ? `/api/ontology/classes?graph=${encodeURIComponent(graphUri)}` : '/api/ontology/classes';

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('odras_token')}`
      },
      body: JSON.stringify({
        name: id,
        label: label,
        comment: ''
      })
    });

    if (response.ok) {
      console.log('✅ Class created in Fuseki:', label);
    } else {
      console.error('❌ Failed to create class in Fuseki:', response.status, response.statusText);
    }
  } catch (error) {
    console.error('❌ Error creating class in Fuseki:', error);
  }

  refreshOntologyTree();
  persistOntologyToLocalStorage();
}

async function addClassNodeAt(label, position) {
  ensureOntologyInitialized();
  const id = `Class${ontoState.nextId++}`;

  // Add to Cytoscape graph first with metadata
  const attrs = addCreationMetadata({});
  ontoState.cy.add({ group: 'nodes', data: { id, label, type: 'class', attrs }, position });

  // Call backend API to persist to Fuseki with correct graph context
  try {
    const graphUri = activeOntologyIri;
    const url = graphUri ? `/api/ontology/classes?graph=${encodeURIComponent(graphUri)}` : '/api/ontology/classes';

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('odras_token')}`
      },
      body: JSON.stringify({
        name: id,
        label: label,
        comment: ''
      })
    });

    if (response.ok) {
      console.log('✅ Class created in Fuseki:', label);
    } else {
      console.error('❌ Failed to create class in Fuseki:', response.status, response.statusText);
    }
  } catch (error) {
    console.error('❌ Error creating class in Fuseki:', error);
  }

  refreshOntologyTree();
  persistOntologyToLocalStorage();
  return id;
}

function runAutoLayout() {
  // Legacy function - now uses advanced layout
  runAdvancedLayout('cose');
}

function runAdvancedLayout(layoutType) {
  ensureOntologyInitialized();
  if (!ontoState.cy) return;

  // Check if a layout is already running
  if (ontoState.layoutRunning) {
    console.log('⏭️ Layout already in progress, skipping...');
    return;
  }

  // Suspend layout saves during layout algorithm execution
  ontoState.layoutRunning = true;
  console.log('🔄 Layout algorithm starting, suspending position saves...');

  let layoutOptions = {
    animate: true,
    animationDuration: 800,
    animationEasing: 'ease-out'
  };

  switch (layoutType) {
    case 'grid':
      layoutOptions = {
        ...layoutOptions,
        name: 'grid',
        cols: Math.ceil(Math.sqrt(ontoState.cy.nodes().length)),
        rows: Math.ceil(ontoState.cy.nodes().length / Math.ceil(Math.sqrt(ontoState.cy.nodes().length))),
        spacingFactor: 1.5
      };
      break;

    case 'circle':
      layoutOptions = {
        ...layoutOptions,
        name: 'circle',
        radius: Math.max(200, ontoState.cy.nodes().length * 30),
        spacingFactor: 1.2
      };
      break;

    case 'concentric':
      layoutOptions = {
        ...layoutOptions,
        name: 'concentric',
        concentric: (node) => {
          // Use node degree as concentric level
          return node.degree();
        },
        levelWidth: (nodes) => {
          return Math.max(100, nodes.length * 20);
        },
        spacingFactor: 1.5
      };
      break;

    case 'breadthfirst':
      layoutOptions = {
        ...layoutOptions,
        name: 'breadthfirst',
        directed: true,
        spacingFactor: 1.5,
        avoidOverlap: true,
        nodeDimensionsIncludeLabels: true
      };
      break;

    case 'cose':
      layoutOptions = {
        ...layoutOptions,
        name: 'cose',
        idealEdgeLength: 150,
        nodeOverlap: 20,
        refresh: 20,
        fit: true,
        padding: 30,
        randomize: false,
        componentSpacing: 100,
        nodeRepulsion: 400000,
        edgeElasticity: 100,
        nestingFactor: 5,
        gravity: 80,
        numIter: 1000,
        initialTemp: 200,
        coolingFactor: 0.95,
        minTemp: 1.0
      };
      break;

    case 'dagre':
      layoutOptions = {
        ...layoutOptions,
        name: 'dagre',
        rankDir: 'TB', // Top to Bottom
        rankSep: 100,
        nodeSep: 50,
        edgeSep: 10,
        ranker: 'tight-tree'
      };
      break;

    case 'cola':
      layoutOptions = {
        ...layoutOptions,
        name: 'cola',
        animate: true,
        refresh: 1,
        maxSimulationTime: 4000,
        ungrabifyWhileSimulating: false,
        fit: true,
        padding: 30,
        randomize: false,
        avoidOverlap: true,
        handleDisconnected: true,
        convergenceThreshold: 0.01,
        nodeSpacing: 20,
        flow: { axis: 'y', minSeparation: 30 },
        alignment: undefined,
        gapInequalities: undefined,
        centerGraph: true
      };
      break;

    case 'spread':
      layoutOptions = {
        ...layoutOptions,
        name: 'spread',
        minDist: 100,
        expandingFactor: -1.0,
        maxExpandingIterations: 4,
        maxContractingIterations: 4,
        initialTemp: 200,
        finalTemp: 0.1,
        coolingFactor: 0.99
      };
      break;

    default:
      console.warn('Unknown layout type:', layoutType);
      layoutOptions.name = 'cose';
  }

  try {
    const layout = ontoState.cy.layout(layoutOptions);

    // Reset flag when layout completes
    layout.on('layoutstop', () => {
      console.log('✅ Layout algorithm completed');
      ontoState.layoutRunning = false;

      // Update modification metadata for all moved nodes
      ontoState.cy.nodes().forEach(node => {
        if (!node.hasClass('imported')) {
          const currentAttrs = node.data('attrs') || {};
          const updatedAttrs = updateModificationMetadata(currentAttrs);
          node.data('attrs', updatedAttrs);
        }
      });

      // Directly save to localStorage and trigger server save
      if (activeOntologyIri) {
        console.log('💾 Saving layout after algorithm completion...');

        // Save to localStorage immediately
        persistOntologyToLocalStorage();

        // Save layout to localStorage for quick recovery
        const pan = ontoState.cy.pan();
        const zoom = ontoState.cy.zoom();
        const nodes = ontoState.cy.nodes().filter(n => !n.hasClass('imported')).map(n => ({
          iri: n.data('id'),
          x: n.position('x'),
          y: n.position('y')
        }));

        const layoutData = {
          nodes: nodes,
          zoom: zoom,
          pan: pan,
          timestamp: Date.now()
        };

        const localLayoutKey = `onto_layout_${encodeURIComponent(activeOntologyIri)}`;
        localStorage.setItem(localLayoutKey, JSON.stringify(layoutData));
        console.log('💾 Layout saved to localStorage');

        // Trigger server save after 5 seconds
        setTimeout(() => {
          if (activeOntologyIri) {
            const nodes = ontoState.cy.nodes().filter(n => !n.hasClass('imported')).map(n => ({ data: n.data(), position: n.position() }));
            const edges = ontoState.cy.edges().filter(e => !e.hasClass('imported')).map(e => ({ data: e.data() }));
            saveLayoutToServer(activeOntologyIri, nodes, edges);
          }
        }, 5000);
      }

      console.log(`📍 Layout complete - updated metadata for ${ontoState.cy.nodes().filter(n => !n.hasClass('imported')).length} nodes`);
    });

    layout.run();

    // Fit the graph after layout completes
    setTimeout(() => {
      ontoState.cy.fit(undefined, 20);
    }, layoutOptions.animationDuration + 100);

  } catch (error) {
    console.error('Layout error:', error);
    ontoState.layoutRunning = false; // Reset flag on error
    // Fallback to basic cose layout
    const fallbackLayout = ontoState.cy.layout({
      name: 'cose',
      animate: true,
      animationDuration: 500
    });
    fallbackLayout.on('layoutstop', () => {
      ontoState.layoutRunning = false;
      // Update modification metadata for all moved nodes
      ontoState.cy.nodes().forEach(node => {
        if (!node.hasClass('imported')) {
          const currentAttrs = node.data('attrs') || {};
          const updatedAttrs = updateModificationMetadata(currentAttrs);
          node.data('attrs', updatedAttrs);
        }
      });

      // Directly save layout (same as main layout handler)
      if (activeOntologyIri) {
        console.log('💾 Saving layout after fallback algorithm completion...');
        persistOntologyToLocalStorage();

        const pan = ontoState.cy.pan();
        const zoom = ontoState.cy.zoom();
        const nodes = ontoState.cy.nodes().filter(n => !n.hasClass('imported')).map(n => ({
          iri: n.data('id'),
          x: n.position('x'),
          y: n.position('y')
        }));

        const layoutData = {
          nodes: nodes,
          zoom: zoom,
          pan: pan,
          timestamp: Date.now()
        };

        const localLayoutKey = `onto_layout_${encodeURIComponent(activeOntologyIri)}`;
        localStorage.setItem(localLayoutKey, JSON.stringify(layoutData));
        console.log('💾 Layout saved to localStorage (fallback)');

        setTimeout(() => {
          if (activeOntologyIri) {
            const nodes = ontoState.cy.nodes().filter(n => !n.hasClass('imported')).map(n => ({ data: n.data(), position: n.position() }));
            const edges = ontoState.cy.edges().filter(e => !e.hasClass('imported')).map(e => ({ data: e.data() }));
            saveLayoutToServer(activeOntologyIri, nodes, edges);
          }
        }, 5000);
      }

      console.log(`📍 Layout complete (fallback) - updated metadata for ${ontoState.cy.nodes().filter(n => !n.hasClass('imported')).length} nodes`);
    });
    fallbackLayout.run();
  }
}

function setConnectMode(enabled) {
  ensureOntologyInitialized();
  ontoState.connectMode = !!enabled;
  const btn = qs('#ontoConnectBtn');
  if (btn) btn.style.borderColor = enabled ? '#60a5fa' : 'var(--border)';
  if (ontoState.eh) {
    if (enabled) ontoState.eh.enableDrawMode(); else ontoState.eh.disableDrawMode();
  } else {
    if (!enabled) ontoState.clickConnectFrom = null;
  }
}

function ensureAttributesExist() {
  // Ensure all nodes have an attrs property
  ontoState.cy.nodes().forEach(n => {
    if (!n.data('attrs')) {
      n.data('attrs', {});
    }
  });

  // Ensure all edges have an attrs property
  ontoState.cy.edges().forEach(e => {
    if (!e.data('attrs')) {
      e.data('attrs', {});
    }
  });
}

// Ontology loading progress indicator functions
function showOntologyLoadingIndicator() {
  // Remove any existing indicator
  hideOntologyLoadingIndicator();

  // Create loading overlay
  const overlay = document.createElement('div');
  overlay.id = 'ontology-loading-overlay';
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 10000;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  `;

  const container = document.createElement('div');
  container.style.cssText = `
    background: white;
    border-radius: 12px;
    padding: 30px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
    text-align: center;
    min-width: 300px;
    max-width: 500px;
  `;

  const title = document.createElement('h3');
  title.textContent = 'Loading Ontology';
  title.style.cssText = `
    margin: 0 0 20px 0;
    color: #333;
    font-size: 18px;
    font-weight: 600;
  `;

  const progressBar = document.createElement('div');
  progressBar.style.cssText = `
    width: 100%;
    height: 8px;
    background: #e0e0e0;
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 15px;
  `;

  const progressFill = document.createElement('div');
  progressFill.id = 'ontology-progress-fill';
  progressFill.style.cssText = `
    height: 100%;
    background: linear-gradient(90deg, #4CAF50, #45a049);
    width: 0%;
    transition: width 0.3s ease;
    border-radius: 4px;
  `;

  const statusText = document.createElement('div');
  statusText.id = 'ontology-status-text';
  statusText.textContent = 'Initializing...';
  statusText.style.cssText = `
    color: #666;
    font-size: 14px;
    margin-bottom: 10px;
  `;

  const progressText = document.createElement('div');
  progressText.id = 'ontology-progress-text';
  progressText.textContent = '0%';
  progressText.style.cssText = `
    color: #999;
    font-size: 12px;
  `;

  progressBar.appendChild(progressFill);
  container.appendChild(title);
  container.appendChild(progressBar);
  container.appendChild(statusText);
  container.appendChild(progressText);
  overlay.appendChild(container);
  document.body.appendChild(overlay);
}

function updateOntologyLoadingProgress(status, percentage) {
  const statusText = document.getElementById('ontology-status-text');
  const progressText = document.getElementById('ontology-progress-text');
  const progressFill = document.getElementById('ontology-progress-fill');

  if (statusText) statusText.textContent = status;
  if (progressText) progressText.textContent = `${percentage}%`;
  if (progressFill) progressFill.style.width = `${percentage}%`;
}

function hideOntologyLoadingIndicator() {
  const overlay = document.getElementById('ontology-loading-overlay');
  if (overlay) {
    overlay.remove();
  }
}

// Lazy load additional metadata when user clicks on elements
async function loadAdditionalMetadataForElement(elementId, graphIri) {
  try {
    // Check if we already have rich metadata for this element
    const element = ontoState.cy.getElementById(elementId);
    if (!element || element.data('attrs')?.definition) {
      return; // Already loaded or element doesn't exist
    }

    // Fetch additional metadata for this specific element
    const query = `
      PREFIX owl: <http://www.w3.org/2002/07/owl#>
      PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
      PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
      PREFIX dc11: <http://purl.org/dc/elements/1.1/>
      SELECT ?label ?comment ?definition ?example ?identifier WHERE {
        GRAPH <${graphIri}> {
          <${elementId}> rdfs:label ?label .
          OPTIONAL { <${elementId}> rdfs:comment ?comment }
          OPTIONAL { <${elementId}> skos:definition ?definition }
          OPTIONAL { <${elementId}> skos:example ?example }
          OPTIONAL { <${elementId}> dc11:identifier ?identifier }
        }
      }`;

    const response = await authenticatedFetch('/api/ontology/sparql', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });

    if (response.ok) {
      const result = await response.json();
      if (result.results?.bindings?.length > 0) {
        const binding = result.results.bindings[0];
        const attrs = element.data('attrs') || {};

        // Add the additional metadata
        if (binding.definition) attrs.definition = binding.definition.value;
        if (binding.example) attrs.example = binding.example.value;
        if (binding.identifier) attrs.identifier = binding.identifier.value;
        if (binding.comment) attrs.comment = binding.comment.value;

        element.data('attrs', attrs);

        // Update the properties panel if this element is selected
        if (ontoState.selectedElement && ontoState.selectedElement.id() === elementId) {
          updatePropertiesPanelFromSelection();
        }
      }
    }
  } catch (error) {
    console.error('Error loading additional metadata:', error);
  }
}

async function exportOntologyJSON() {
  ensureOntologyInitialized();
  ensureAttributesExist(); // Make sure all elements have attrs property

  // Get ontology name for filename
  const modelNameField = document.querySelector('#propName');
  const ontologyName = modelNameField?.value || 'Ontology Model';
  const safeFilename = ontologyName.toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-+/g, '-');

  // Capture graph data
  const nodes = ontoState.cy.nodes().map(n => ({ data: n.data(), position: n.position() }));
  const edges = ontoState.cy.edges().map(e => ({ data: e.data() }));

  // Get model metadata from properties panel
  const modelMetadata = {};
  if (activeOntologyIri) {
    const pid = (activeProject && (activeProject.id || activeProject.project_id)) ? (activeProject.id || activeProject.project_id) : 'default';
    const ontologyKey = activeOntologyIri ? activeOntologyIri.split('/').pop() : 'default';
    const modelNameKey = `onto_model_name__${pid}__${ontologyKey}`;
    const modelAttrsKey = `onto_model_attrs__${pid}__${ontologyKey}`;

    modelMetadata.name = localStorage.getItem(modelNameKey) || ontologyName;
    modelMetadata.type = 'Model';

    try {
      const attrs = JSON.parse(localStorage.getItem(modelAttrsKey) || '{}');
      modelMetadata.comment = attrs.comment || '';
      modelMetadata.definition = attrs.definition || '';
      modelMetadata.version = attrs.version || '';
      modelMetadata.namespace = attrs.namespace || activeOntologyIri;
      modelMetadata.imports = attrs.imports || '';
    } catch (_) {
      modelMetadata.comment = '';
      modelMetadata.definition = '';
      modelMetadata.version = '';
      modelMetadata.namespace = activeOntologyIri;
      modelMetadata.imports = '';
    }
  }

  // Get named views
  let namedViews = [];
  try {
    namedViews = await loadNamedViews(activeOntologyIri);
  } catch (error) {
    console.warn('Could not load named views for export:', error);
    namedViews = [];
  }

  // Create complete export payload
  const payload = {
    metadata: {
      exportedBy: getCurrentUsername(),
      exportedDate: getCurrentDate(),
      exportedTimestamp: getCurrentTimestamp(),
      ontologyIri: activeOntologyIri,
      exportVersion: '1.0'
    },
    model: modelMetadata,
    nodes: nodes,
    edges: edges,
    namedViews: namedViews
  };

  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${safeFilename}.json`;
  document.body.appendChild(a);
  a.click();
  URL.revokeObjectURL(a.href);
  a.remove();

  console.log(`📋 Exported ontology as: ${safeFilename}.json`);
  console.log('📋 Export includes:', Object.keys(payload));
}

function slugId(text) {
  return String(text || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}

function iriMapKey(graphIri) { return 'onto_iri_map__' + encodeURIComponent(graphIri); }
function loadIriMap(graphIri) { try { return JSON.parse(localStorage.getItem(iriMapKey(graphIri)) || '{}'); } catch (_) { return {}; } }
function saveIriMap(graphIri, map) {
  try { localStorage.setItem(iriMapKey(graphIri), JSON.stringify(map || {})); } catch (_) { }
}

/**
 * Extract RDF property URI from attribute template label
 * Example: 'Comment (rdfs:comment)' → 'rdfs:comment'
 */
function extractRdfPropertyFromLabel(label) {
  const match = label.match(/\(([^)]+)\)$/);
  return match ? match[1] : null;
}

/**
 * Create flexible mapping from UI attributes to RDF properties
 * Uses the attributeTemplates to automatically map UI fields to RDF predicates
 */
function getAttributeToRdfMapping(objectType) {
  const template = attributeTemplates[objectType] || {};
  const mapping = {};

  Object.entries(template).forEach(([attrKey, config]) => {
    const rdfProperty = extractRdfPropertyFromLabel(config.label || attrKey);
    if (rdfProperty) {
      mapping[attrKey] = rdfProperty;
    }
  });

  return mapping;
}

/**
 * Generate RDF triples for element attributes
 * Converts UI attributes to proper RDF annotation properties
 */
function generateAttributeTriples(elementIri, attrs, objectType) {
  const mapping = getAttributeToRdfMapping(objectType);
  const triples = [];

  Object.entries(attrs).forEach(([attrKey, value]) => {
    const rdfProperty = mapping[attrKey];

    // Skip if no RDF mapping or empty value
    if (!rdfProperty || !value) return;

    // Skip readonly metadata fields that shouldn't be saved as RDF
    if (attrKey.includes('_timestamp') || attrKey.includes('readonly')) return;

    // CRITICAL FIX: Handle inheritance array and comma-separated strings for subclass_of
    if (attrKey === 'subclass_of') {
      let parentUris = [];

      if (Array.isArray(value)) {
        parentUris = value;
      } else if (typeof value === 'string' && value.includes(',')) {
        // Handle comma-separated parent URIs
        parentUris = value.split(',').map(uri => uri.trim());
      } else if (typeof value === 'string' && value.trim()) {
        // Handle single parent URI
        parentUris = [value.trim()];
      }

      // Convert each parent URI to a separate rdfs:subClassOf triple
      parentUris.forEach(parentUri => {
        if (parentUri && parentUri.trim()) {
          triples.push(`<${elementIri}> ${rdfProperty} <${parentUri}> .`);
          console.log(`🔍 Adding inheritance triple: ${elementIri} subClassOf ${parentUri}`);
        }
      });
      return;
    }

    // Handle different data types
    if (typeof value === 'boolean') {
      triples.push(`<${elementIri}> ${rdfProperty} ${value} .`);
    } else if (typeof value === 'string') {
      // Check if this is a URI reference (for properties like subclassOf, equivalentClass)
      if (attrKey === 'subclassOf' || attrKey === 'equivalentClass' || attrKey === 'disjointWith') {
        // Don't quote URIs
        if (value.trim()) {
          triples.push(`<${elementIri}> ${rdfProperty} <${value}> .`);
        }
      } else {
        // Escape quotes and backslashes for RDF literals
        const escapedValue = value.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
        triples.push(`<${elementIri}> ${rdfProperty} "${escapedValue}" .`);
      }
    }
  });

  return triples;
}

function toTurtle(graphIri, linkedPairsOpt) {
  // Build per-graph stable id→IRI map
  const iriMap = loadIriMap(graphIri);
  const lines = [
    '@prefix owl: <http://www.w3.org/2002/07/owl#> .',
    '@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .',
    '@prefix skos: <http://www.w3.org/2004/02/skos/core#> .',
    '@prefix dc: <http://purl.org/dc/elements/1.1/> .',
    '@prefix dcterms: <http://purl.org/dc/terms/> .',
    '@prefix odras: <http://odras.system/ontology#> .',
    '@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .',
    (() => {
      try {
        const labels = loadOntologyLabelMap(activeProject);
        const pid = (activeProject && (activeProject.id || activeProject.project_id)) ? (activeProject.id || activeProject.project_id) : 'default';

        // FIXED: Use ontology-specific localStorage keys
        const ontologyKey = graphIri ? graphIri.split('/').pop() : 'default';
        const modelNameKey = `onto_model_name__${pid}__${ontologyKey}`;
        const modelAttrsKey = `onto_model_attrs__${pid}__${ontologyKey}`;

        const scopedName = localStorage.getItem(modelNameKey) || '';
        const mapLabel = labels[graphIri] || '';
        const tail = (graphIri.split('/').pop() || graphIri);
        // Prefer the actively edited model name, then label map, then IRI tail
        const chosen = ((activeOntologyIri === graphIri && scopedName.trim()) || mapLabel || tail);
        const lbl = String(chosen || '');

        // Get ontology metadata attributes from localStorage using ontology-specific key
        let ontologyAttrs = {};
        try {
          ontologyAttrs = JSON.parse(localStorage.getItem(modelAttrsKey) || '{}');
        } catch (_) {
          ontologyAttrs = {};
        }

        // Build ontology declaration with all metadata
        let ontologyDecl = `\n<${graphIri}> a owl:Ontology ;\n`;
        ontologyDecl += `    rdfs:label "${String(lbl || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;

        // Add comment if present
        if (ontologyAttrs.comment && ontologyAttrs.comment.trim()) {
          ontologyDecl += ` ;\n    rdfs:comment "${String(ontologyAttrs.comment).replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
        }

        // Add definition if present
        if (ontologyAttrs.definition && ontologyAttrs.definition.trim()) {
          ontologyDecl += ` ;\n    skos:definition "${String(ontologyAttrs.definition).replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
        }

        // Add version if present
        if (ontologyAttrs.version && ontologyAttrs.version.trim()) {
          ontologyDecl += ` ;\n    owl:versionInfo "${String(ontologyAttrs.version).replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
        }

        ontologyDecl += ' .\n';
        return ontologyDecl;
      } catch (_) { return `\n<${graphIri}> a owl:Ontology .\n`; }
    })()
  ];
  // Include owl:imports from local storage
  try {
    const imports = JSON.parse(localStorage.getItem('onto_imports__' + encodeURIComponent(graphIri)) || '[]');
    imports.forEach(imp => { lines.push(`<${graphIri}> <http://www.w3.org/2002/07/owl#imports> <${imp}> .`); });
  } catch (_) { }
  const nodes = ontoState.cy.nodes();
  const edges = ontoState.cy.edges();
  function nodeIri(n) {
    const id = n.id();
    if (iriMap[id]) return iriMap[id];
    const explicit = n.data('iri');
    if (explicit) { iriMap[id] = explicit; return explicit; }

    // Use model namespace instead of graph IRI for element IRIs
    const modelNamespace = getModelNamespace();
    const base = slugId(n.data('label') || id) || id;
    const iri = `${modelNamespace}#${base}`;
    iriMap[id] = iri;
    return iri;
  }
  // Classes and data properties (exclude imported overlays)
  nodes.forEach(n => {
    if (n.hasClass && n.hasClass('imported')) return;
    const t = n.data('type') || 'class';
    const iri = nodeIri(n);
    const label = (n.data('label') || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
    if (t === 'class') {
      lines.push(`<${iri}> a owl:Class ; rdfs:label "${label}" .`);

      // Add attributes as RDF annotation properties
      const attrs = n.data('attrs') || {};
      console.log(`🔍 TURTLE DEBUG: Processing class ${n.data('label')} (${n.id()})`);
      console.log(`🔍 TURTLE DEBUG: Node attributes:`, attrs);
      console.log(`🔍 TURTLE DEBUG: subclass_of present:`, !!attrs.subclass_of);
      console.log(`🔍 TURTLE DEBUG: subclass_of value:`, attrs.subclass_of);

      const attributeTriples = generateAttributeTriples(iri, attrs, 'class');
      console.log(`🔍 TURTLE DEBUG: Generated ${attributeTriples.length} triples for ${n.data('label')}`);
      lines.push(...attributeTriples);
    } else if (t === 'dataProperty') {
      lines.push(`<${iri}> a owl:DatatypeProperty ; rdfs:label "${label}" .`);
      const incoming = n.incomers('edge');
      if (incoming && incoming.length) {
        const src = incoming[0].source();
        const srcIri = nodeIri(src);
        lines.push(`<${iri}> rdfs:domain <${srcIri}> .`);
        lines.push(`<${iri}> rdfs:range <http://www.w3.org/2001/XMLSchema#string> .`);
      }

      // Add attributes as RDF annotation properties
      const attrs = n.data('attrs') || {};
      const attributeTriples = generateAttributeTriples(iri, attrs, 'dataProperty');
      lines.push(...attributeTriples);
    } else if (t === 'note') {
      lines.push(`<${iri}> a skos:Note ; rdfs:label "${label}" .`);

      // Add attributes as RDF annotation properties
      const attrs = n.data('attrs') || {};
      const attributeTriples = generateAttributeTriples(iri, attrs, 'note');
      lines.push(...attributeTriples);
    }
  });
  // Object properties from edges
  const existingEquiv = new Set();
  edges.forEach(e => {
    if (e.hasClass && (e.hasClass('imported') || e.hasClass('imported-equivalence'))) return;
    const s = e.source(); const t = e.target();
    const pred = (e.data('predicate') || 'relatedTo').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
    const modelNamespace = getModelNamespace();
    const propIri = `${modelNamespace}#${slugId(pred)}`;
    const sIri = nodeIri(s); const tIri = nodeIri(t);
    const isData = (e.data('type') || 'objectProperty') === 'dataProperty';
    const sType = (s.data('type') || 'class'); const tType = (t.data('type') || 'class');
    if (!isData) {
      if (sType === 'class' && tType === 'class') {
        // Treat special case for equivalence edges represented in UI as predicate 'equivalentClass'
        if (pred === 'equivalentClass' || pred === 'linked_by') {
          const key = `${sIri}|${tIri}`;
          if (!existingEquiv.has(key)) {
            existingEquiv.add(key);
            lines.push(`<${sIri}> owl:equivalentClass <${tIri}> .`);
          }
        } else {
          lines.push(`<${propIri}> a owl:ObjectProperty ; rdfs:label "${pred}" ; rdfs:domain <${sIri}> ; rdfs:range <${tIri}> .`);

          // Add attributes as RDF annotation properties for object properties
          const attrs = e.data('attrs') || {};
          const attributeTriples = generateAttributeTriples(propIri, attrs, 'objectProperty');
          lines.push(...attributeTriples);
        }
      } else if (sType === 'note' && (tType === 'class' || tType === 'dataProperty') && pred === 'note_for') {
        // Emit skos:note_for relationship to connect note to target element
        lines.push(`<${sIri}> skos:note_for <${tIri}> .`);
      }
    }
  });
  // Add auto-computed equivalence pairs (no UI edges) if provided
  if (Array.isArray(linkedPairsOpt)) {
    linkedPairsOpt.forEach(p => {
      try {
        const n = p.baseNode; const targetIri = p.importIri;
        const sIri = nodeIri(n);
        const key = `${sIri}|${targetIri}`;
        if (!existingEquiv.has(key)) {
          existingEquiv.add(key);
          lines.push(`<${sIri}> owl:equivalentClass <${targetIri}> .`);
        }
      } catch (_) { }
    });
  }
  saveIriMap(graphIri, iriMap);
  return lines.join('\n');
}

// Compute linked_by pairs between base classes and imported graphs by label/local name
async function computeLinkedByPairs(graphIri) {
  try {
    const imports = JSON.parse(localStorage.getItem('onto_imports__' + encodeURIComponent(graphIri)) || '[]');
    if (!imports || !imports.length || !ontoState.cy) return [];
    const baseClasses = ontoState.cy.nodes().filter(n => (n.data('type') || 'class') === 'class' && !n.hasClass('imported'));
    const norm = (s) => String(s || '').trim().toLowerCase();
    const baseByLabel = new Map();
    baseClasses.forEach(n => { baseByLabel.set(norm(n.data('label') || n.id()), n); });
    const pairs = [];
    for (const imp of imports) {
      const q = `PREFIX owl: <http://www.w3.org/2002/07/owl#>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\nSELECT ?c ?label WHERE { GRAPH <${imp}> { ?c a owl:Class . OPTIONAL { ?c rdfs:label ?label } } }`;
      const res = await fetch('/api/ontology/sparql', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: q }) });
      if (!res.ok) continue;
      const json = await res.json();
      const rows = (json && json.results && json.results.bindings) ? json.results.bindings : [];
      rows.forEach(b => {
        const iri = b.c && b.c.value; const label = b.label && b.label.value;
        const local = iri ? (iri.includes('#') ? iri.split('#').pop() : iri.split('/').pop()) : '';
        const key = norm(label || local);
        const base = baseByLabel.get(key);
        if (base && iri) pairs.push({ baseNode: base, importIri: iri });
      });
    }
    // Deduplicate pairs by base id + target iri
    const out = [];
    const seen = new Set();
    pairs.forEach(p => { const k = p.baseNode.id() + '|' + p.importIri; if (!seen.has(k)) { seen.add(k); out.push(p); } });
    return out;
  } catch (_) { return []; }
}

// Imported overlay visibility persistence
function visibleImportsKey(graphIri) { return 'onto_imports_visible__' + encodeURIComponent(graphIri || ''); }
function loadVisibleImports(graphIri) { try { return new Set(JSON.parse(localStorage.getItem(visibleImportsKey(graphIri)) || '[]')); } catch (_) { return new Set(); } }
function saveVisibleImports(graphIri, set) { try { localStorage.setItem(visibleImportsKey(graphIri), JSON.stringify(Array.from(set || []))); } catch (_) { } }

// Reference ontology selector
async function showReferenceOntologySelector() {
  try {
    const token = localStorage.getItem(tokenKey);
    const res = await fetch('/api/ontologies/reference', {
      headers: { Authorization: 'Bearer ' + token }
    });

    if (!res.ok) {
      throw new Error('Failed to fetch reference ontologies');
    }

    const json = await res.json();
    const referenceOntologies = json.reference_ontologies || [];

    // Create overlay
    const overlay = document.createElement('div');
    overlay.style.position = 'fixed';
    overlay.style.inset = '0';
    overlay.style.background = 'rgba(0,0,0,0.4)';
    overlay.style.zIndex = '9998';

    const panel = document.createElement('div');
    panel.style.position = 'fixed';
    panel.style.top = '10%';
    panel.style.left = '50%';
    panel.style.transform = 'translateX(-50%)';
    panel.style.background = 'var(--panel)';
    panel.style.border = '1px solid var(--border)';
    panel.style.borderRadius = '12px';
    panel.style.padding = '20px';
    panel.style.minWidth = '600px';
    panel.style.maxWidth = '80vw';
    panel.style.maxHeight = '80vh';
    panel.style.overflow = 'auto';
    panel.style.zIndex = '9999';

    panel.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
        <h3 style="margin:0;">Import Reference Ontology</h3>
        <button id="refOntClose" class="btn" style="background: var(--muted);">Close</button>
      </div>


      <!-- Existing Reference Ontologies Section -->
      <div>
        <h4 style="margin:0 0 12px 0;">📚 Existing Reference Ontologies</h4>
        <div id="refOntList" style="max-height:300px; overflow-y:auto;">
          ${referenceOntologies.length === 0 ?
        '<div style="text-align:center; color:var(--muted); padding:20px;">No reference ontologies available</div>' :
        referenceOntologies.map(onto => `
              <div style="display:flex; justify-content:space-between; align-items:center; border:1px solid var(--border); border-radius:8px; padding:12px; margin-bottom:8px; cursor:pointer;"
                   data-graph-iri="${onto.graph_iri}" class="ref-onto-item">
                <div>
                  <div style="font-weight:500;">${onto.label || onto.graph_iri.split('/').pop()}</div>
                  <div style="font-size:0.9em; color:var(--muted);">${onto.project_name} • ${onto.graph_iri}</div>
                </div>
                <button class="btn" data-graph-iri="${onto.graph_iri}">Import</button>
              </div>
            `).join('')
      }
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
    document.body.appendChild(panel);

    const close = () => {
      try {
        document.body.removeChild(panel);
        document.body.removeChild(overlay);
      } catch (_) { }
    };

    panel.querySelector('#refOntClose').onclick = close;
    overlay.onclick = close;


    // Add hover effects for existing ontologies
    panel.querySelectorAll('.ref-onto-item').forEach(item => {
      item.onmouseover = () => item.style.background = 'var(--hover)';
      item.onmouseout = () => item.style.background = 'transparent';
    });

    // Handle import clicks for existing ontologies
    const listEl = panel.querySelector('#refOntList');
    listEl.addEventListener('click', async (e) => {
      const btn = e.target.closest('button[data-graph-iri]');
      if (!btn) return;

      const graphIri = btn.getAttribute('data-graph-iri');
      const importsKey = 'onto_imports__' + encodeURIComponent(activeOntologyIri || '');

      try {
        const curr = new Set(JSON.parse(localStorage.getItem(importsKey) || '[]'));
        console.log('🔍 Current imports:', Array.from(curr));
        console.log('🔍 Adding import:', graphIri);
        if (!curr.has(graphIri)) {
          curr.add(graphIri);
          localStorage.setItem(importsKey, JSON.stringify(Array.from(curr)));
          console.log('🔍 Import added, refreshing tree...');
          refreshOntologyTree();
          toast('Reference ontology imported successfully');
        } else {
          console.log('🔍 Import already exists');
          toast('Reference ontology already imported', true);
        }
        close();
      } catch (err) {
        console.error('🔍 Error importing reference ontology:', err);
        toast('Failed to import reference ontology', true);
      }
    });

  } catch (err) {
    toast('Failed to load reference ontologies', true);
  }
}

// Persist per-import overlay node positions
function overlayPositionsKey(baseIri, importIri) { return 'onto_import_positions__' + encodeURIComponent(baseIri || '') + '__' + encodeURIComponent(importIri || ''); }
function loadOverlayPositions(baseIri, importIri) { try { return JSON.parse(localStorage.getItem(overlayPositionsKey(baseIri, importIri)) || '{}'); } catch (_) { return {}; } }
function saveOverlayPositions(baseIri, importIri, obj) { try { localStorage.setItem(overlayPositionsKey(baseIri, importIri), JSON.stringify(obj || {})); } catch (_) { } }

// Collapsed imports persistence
function collapsedImportsKey(baseIri) { return 'onto_collapsed_imports__' + encodeURIComponent(baseIri || ''); }
function loadCollapsedImports(baseIri) {
  try {
    const data = localStorage.getItem(collapsedImportsKey(baseIri));
    return data ? new Set(JSON.parse(data)) : new Set();
  } catch (_) {
    return new Set();
  }
}
function saveCollapsedImports(baseIri, collapsedSet) {
  try {
    localStorage.setItem(collapsedImportsKey(baseIri), JSON.stringify(Array.from(collapsedSet)));
  } catch (_) { }
}

// Pseudo-node positions persistence
function pseudoNodePositionsKey(baseIri) { return 'onto_pseudo_positions__' + encodeURIComponent(baseIri || ''); }
function loadPseudoNodePositions(baseIri) {
  try {
    return JSON.parse(localStorage.getItem(pseudoNodePositionsKey(baseIri)) || '{}');
  } catch (_) {
    return {};
  }
}
function savePseudoNodePositions(baseIri, positions) {
  try {
    localStorage.setItem(pseudoNodePositionsKey(baseIri), JSON.stringify(positions || {}));
  } catch (_) { }
}

// Visibility state persistence
function visibilityStateKey(baseIri) { return 'onto_visibility_state__' + encodeURIComponent(baseIri || ''); }
function loadVisibilityState(baseIri) {
  try {
    const saved = JSON.parse(localStorage.getItem(visibilityStateKey(baseIri)) || '{}');
    return {
      classes: saved.classes !== undefined ? saved.classes : true,
      dataProperties: saved.dataProperties !== undefined ? saved.dataProperties : true,
      notes: saved.notes !== undefined ? saved.notes : true,
      edges: saved.edges !== undefined ? saved.edges : true,
      imported: saved.imported !== undefined ? saved.imported : true
    };
  } catch (_) {
    return {
      classes: true,
      dataProperties: true,
      notes: true,
      edges: true,
      imported: true
    };
  }
}
function saveVisibilityState(baseIri, state) {
  try {
    localStorage.setItem(visibilityStateKey(baseIri), JSON.stringify(state || {}));
  } catch (_) { }
}

// Individual element visibility persistence
function elementVisibilityKey(baseIri) { return 'onto_element_visibility__' + encodeURIComponent(baseIri || ''); }
function loadElementVisibility(baseIri) {
  try {
    return JSON.parse(localStorage.getItem(elementVisibilityKey(baseIri)) || '{}');
  } catch (_) {
    return {};
  }
}
function saveElementVisibility(baseIri, visibility) {
  try {
    localStorage.setItem(elementVisibilityKey(baseIri), JSON.stringify(visibility || {}));
  } catch (_) { }
}

async function fetchImportGraphSnapshot(importIri) {
  try {
    // First try to get data from local storage (consistent with importEquivCount)
    const pid = (activeProject && (activeProject.id || activeProject.project_id)) ? (activeProject.id || activeProject.project_id) : 'default';
    const importKey = `onto_graph__${pid}__` + encodeURIComponent(importIri);
    let importData = localStorage.getItem(importKey);

    if (!importData) {
      console.log('🔍 No local storage data found for import snapshot, attempting to load from API:', importIri);
      try {
        // Try to load the imported ontology data from API
        const token = localStorage.getItem(tokenKey);
        const apiUrl = `/api/ontology/?graph=${encodeURIComponent(importIri)}`;
        const response = await fetch(apiUrl, {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });

        if (response.ok) {
          const ontologyData = await response.json();
          console.log('🔍 Loaded imported ontology from API for snapshot:', ontologyData);
          console.log('🔍 Snapshot API response structure - classes:', ontologyData.classes);
          console.log('🔍 Snapshot API response structure - object_properties:', ontologyData.object_properties);

          // Convert to Cytoscape format and save to local storage
          // Use a simpler conversion since we don't have rich metadata
          // The API response has the data nested in a 'data' property
          const actualOntologyData = ontologyData.data || ontologyData;
          const cytoscapeData = convertOntologyToCytoscape(actualOntologyData);
          console.log('🔍 Snapshot converted cytoscape data:', cytoscapeData);
          const storageData = {
            nodes: cytoscapeData.nodes || [],
            edges: cytoscapeData.edges || [],
            timestamp: Date.now(),
            source: 'api'
          };

          localStorage.setItem(importKey, JSON.stringify(storageData));
          importData = JSON.stringify(storageData);
          console.log('🔍 Saved imported ontology data to local storage for snapshot');
        } else {
          console.log('🔍 Failed to load imported ontology from API for snapshot:', response.status);
          // Fall through to SPARQL fallback
        }
      } catch (err) {
        console.error('🔍 Error loading imported ontology for snapshot:', err);
        // Fall through to SPARQL fallback
      }
    }

    // Check if cached data is empty and force reload
    if (importData) {
      const cachedData = JSON.parse(importData);
      if (cachedData.nodes && cachedData.nodes.length === 0 && cachedData.edges && cachedData.edges.length === 0) {
        console.log('🔍 Snapshot cached data is empty, forcing reload from API:', importIri);
        try {
          const token = localStorage.getItem(tokenKey);
          const apiUrl = `/api/ontology/?graph=${encodeURIComponent(importIri)}`;
          const response = await fetch(apiUrl, {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
          });

          if (response.ok) {
            const ontologyData = await response.json();
            console.log('🔍 Snapshot reloaded imported ontology from API:', ontologyData);
            console.log('🔍 Snapshot reload API response structure - classes:', ontologyData.classes);
            console.log('🔍 Snapshot reload API response structure - object_properties:', ontologyData.object_properties);

            // Convert to Cytoscape format and save to local storage
            // The API response has the data nested in a 'data' property
            const actualOntologyData = ontologyData.data || ontologyData;
            console.log('🔍 Snapshot reload actual ontology data being passed to convertOntologyToCytoscape:', actualOntologyData);
            console.log('🔍 Snapshot reload actualOntologyData.classes:', actualOntologyData.classes);
            const cytoscapeData = convertOntologyToCytoscape(actualOntologyData);
            console.log('🔍 Snapshot reload converted cytoscape data:', cytoscapeData);
            const storageData = {
              nodes: cytoscapeData.nodes || [],
              edges: cytoscapeData.edges || [],
              timestamp: Date.now(),
              source: 'api'
            };

            localStorage.setItem(importKey, JSON.stringify(storageData));
            importData = JSON.stringify(storageData);
            console.log('🔍 Snapshot reloaded and saved imported ontology data to local storage');
          } else {
            console.log('🔍 Failed to reload imported ontology from API for snapshot:', response.status);
          }
        } catch (err) {
          console.error('🔍 Error reloading imported ontology for snapshot:', err);
        }
      }
    }

    if (importData) {
      console.log('🔍 Using local storage data for import snapshot:', importIri);
      const importOntology = JSON.parse(importData);
      console.log('🔍 Import ontology data:', importOntology);
      const importNodes = importOntology.nodes || [];
      const importEdges = importOntology.edges || [];
      console.log('🔍 Import nodes count:', importNodes.length);
      console.log('🔍 Import edges count:', importEdges.length);

      // Convert Cytoscape nodes to snapshot format
      const classes = importNodes
        .filter(node => (node.data && node.data.type === 'class') || !node.data?.type)
        .map(node => {
          console.log('🔍 Import node data:', node);
          return {
            iri: node.data?.iri || node.id,
            label: node.data?.label || node.data?.id || node.id,
            comment: node.data?.comment || '',
            attrs: node.data?.attrs || {}
          };
        });

      // Convert Cytoscape edges to snapshot format
      const edges = importEdges
        .filter(edge => edge.data && edge.data.source && edge.data.target)
        .map(edge => ({
          sourceIri: edge.data.source,
          targetIri: edge.data.target,
          label: edge.data.predicate || 'relatedTo',
          attrs: edge.data.attrs || {}
        }));

      console.log('🔍 Processed edges count:', edges.length);

      console.log('🔍 Final import classes:', classes);
      classes.forEach((cls, i) => {
        console.log(`🔍 Class ${i}:`, cls);
      });
      return { classes, edges, importNodes };
    }

    // Fallback to SPARQL if no local storage data
    console.log('🔍 No local storage data, using SPARQL for import snapshot:', importIri);
    const qClasses = `
      PREFIX owl: <http://www.w3.org/2002/07/owl#>
      PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
      PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
      PREFIX dc11: <http://purl.org/dc/elements/1.1/>
      PREFIX dcterms: <http://purl.org/dc/terms/>
      PREFIX obo: <http://purl.obolibrary.org/obo/>
      SELECT ?c ?label ?comment ?definition ?example ?identifier ?subclassOf ?equivalentClass WHERE {
        GRAPH <${importIri}> {
          ?c a owl:Class .
          OPTIONAL { ?c rdfs:label ?label }
          OPTIONAL { ?c rdfs:comment ?comment }
          OPTIONAL { ?c skos:definition ?definition }
          OPTIONAL { ?c skos:example ?example }
          OPTIONAL { ?c dc11:identifier ?identifier }
          OPTIONAL { ?c rdfs:subClassOf ?subclassOf }
          OPTIONAL { ?c owl:equivalentClass ?equivalentClass }
        }
      }`;

    const qProps = `
      PREFIX owl: <http://www.w3.org/2002/07/owl#>
      PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
      PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
      PREFIX dc11: <http://purl.org/dc/elements/1.1/>
      PREFIX dcterms: <http://purl.org/dc/terms/>
      SELECT ?p ?label ?comment ?definition ?example ?identifier ?domain ?range ?inverseOf ?subPropertyOf ?equivalentProperty ?propertyType WHERE {
        GRAPH <${importIri}> {
          ?p a owl:ObjectProperty .
          OPTIONAL { ?p rdfs:label ?label }
          OPTIONAL { ?p rdfs:comment ?comment }
          OPTIONAL { ?p skos:definition ?definition }
          OPTIONAL { ?p skos:example ?example }
          OPTIONAL { ?p dc11:identifier ?identifier }
          OPTIONAL { ?p rdfs:domain ?domain }
          OPTIONAL { ?p rdfs:range ?range }
          OPTIONAL { ?p owl:inverseOf ?inverseOf }
          OPTIONAL { ?p rdfs:subPropertyOf ?subPropertyOf }
          OPTIONAL { ?p owl:equivalentProperty ?equivalentProperty }
          OPTIONAL { ?p a ?propertyType }
        }
      }`;

    const classesRes = await authenticatedFetch('/api/ontology/sparql', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: qClasses }) });
    const propsRes = await authenticatedFetch('/api/ontology/sparql', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: qProps }) });
    const classesJson = classesRes.ok ? await classesRes.json() : { results: { bindings: [] } };
    const propsJson = propsRes.ok ? await propsRes.json() : { results: { bindings: [] } };

    // Enhanced class processing with rich metadata
    const cls = (classesJson.results?.bindings || []).map(b => {
      const iri = b.c.value;
      const label = (b.label && b.label.value) || (iri.includes('#') ? iri.split('#').pop() : iri.split('/').pop());
      const attrs = {};

      // Store all available metadata
      if (b.comment && b.comment.value) attrs.comment = b.comment.value;
      if (b.definition && b.definition.value) attrs.definition = b.definition.value;
      if (b.example && b.example.value) attrs.example = b.example.value;
      if (b.identifier && b.identifier.value) attrs.identifier = b.identifier.value;
      if (b.subclassOf && b.subclassOf.value) attrs.subclassOf = b.subclassOf.value;
      if (b.equivalentClass && b.equivalentClass.value) attrs.equivalentClass = b.equivalentClass.value;

      return { iri, label, attrs };
    });

    // Enhanced property processing with rich metadata
    const edges = [];
    (propsJson.results?.bindings || []).forEach(b => {
      const p = b.p.value;
      const label = (b.label && b.label.value) || (p.includes('#') ? p.split('#').pop() : p.split('/').pop());
      const attrs = {};

      // Store all available metadata
      if (b.comment && b.comment.value) attrs.comment = b.comment.value;
      if (b.definition && b.definition.value) attrs.definition = b.definition.value;
      if (b.example && b.example.value) attrs.example = b.example.value;
      if (b.identifier && b.identifier.value) attrs.identifier = b.identifier.value;
      if (b.domain && b.domain.value) attrs.domain = b.domain.value;
      if (b.range && b.range.value) attrs.range = b.range.value;
      if (b.inverseOf && b.inverseOf.value) attrs.inverseOf = b.inverseOf.value;
      if (b.subPropertyOf && b.subPropertyOf.value) attrs.subPropertyOf = b.subPropertyOf.value;
      if (b.equivalentProperty && b.equivalentProperty.value) attrs.equivalentProperty = b.equivalentProperty.value;
      if (b.propertyType && b.propertyType.value) attrs.propertyType = b.propertyType.value;

      // Create edges for domain-range relationships
      if (b.domain && b.range) {
        edges.push({
          sourceIri: b.domain.value,
          targetIri: b.range.value,
          label,
          predicate: p,
          attrs
        });
      }
    });

    return { classes: cls, edges };
  } catch (_) { return { classes: [], edges: [] }; }
}

async function overlayImportsRefresh() {
  try {
    if (!ontoState.cy || !activeOntologyIri) {
      console.log('🔍 overlayImportsRefresh: No cytoscape instance or active ontology');
      return;
    }

    const visible = loadVisibleImports(activeOntologyIri);
    const visibleList = Array.from(visible);
    console.log('🔍 overlayImportsRefresh: Visible imports:', visibleList);

    // Before removing overlays, snapshot positions for imports being hidden
    try {
      ontoState.cy.nodes('.imported').forEach(n => {
        const imp = n.data('importSource') || '';
        if (!visible.has(imp)) {
          const curr = loadOverlayPositions(activeOntologyIri, imp);
          curr[n.id()] = n.position();
          saveOverlayPositions(activeOntologyIri, imp, curr);
        }
      });
    } catch (err) {
      console.error('🔍 Error saving overlay positions:', err);
    }

    // Remove overlays for imports no longer visible
    try {
      const elementsToRemove = ontoState.cy.elements('.imported, .imported-equivalence').filter(el => {
        const importSource = el.data('importSource') || '';
        return !visible.has(importSource);
      });
      console.log('🔍 overlayImportsRefresh: Removing', elementsToRemove.length, 'elements');
      elementsToRemove.remove();
    } catch (err) {
      console.error('🔍 Error removing overlay elements:', err);
    }
    // Add overlays for newly visible imports
    for (const imp of visibleList) {
      const existing = ontoState.cy.elements('.imported').filter(e => (e.data('importSource') || '') === imp);
      if (existing && existing.length) continue;
      const snap = await fetchImportGraphSnapshot(imp);
      const added = [];
      // Compute a simple cluster origin to the right of the base graph to avoid overlap (notes included)
      const baseBBox = ontoState.cy.nodes().filter(n => !n.hasClass('imported')).boundingBox();
      const orderIndex = Math.max(0, visibleList.indexOf(imp));
      const padX = 200, padY = 40, jitterX = orderIndex * 100, jitterY = orderIndex * 60;
      const safe = (n, f) => (Number.isFinite(n) ? n : f);
      const originX = safe(baseBBox.x2, 0) + padX + jitterX;
      const originY = safe(baseBBox.y1, 0) + jitterY;
      const total = Math.max(1, snap.classes.length);
      const cols = Math.ceil(Math.sqrt(total));
      const spacing = 160;
      let nextIdx = 0;
      function nextPos() {
        const col = nextIdx % cols; const row = Math.floor(nextIdx / cols); nextIdx += 1;
        return { x: originX + col * spacing, y: originY + row * spacing };
      }
      // Add class nodes in a simple grid within the cluster; apply saved positions if available
      const savedPos = loadOverlayPositions(activeOntologyIri, imp);
      console.log('🔍 Loading saved positions for import:', imp, savedPos);
      const isCollapsed = ontoState.collapsedImports.has(imp);

      if (isCollapsed) {
        // Create pseudo-node for collapsed import
        const importData = JSON.parse(localStorage.getItem('onto_imports__' + encodeURIComponent(activeOntologyIri || '')) || '[]').find(importData => importData.iri === imp);
        const importName = importData?.label || imp.split('/').pop() || imp;

        // Check if pseudo-node already exists
        const pseudoNodeId = `pseudo-import-${CSS.escape(imp)}`;
        const existingPseudoNode = ontoState.cy.$(`#${CSS.escape(pseudoNodeId)}`);

        if (existingPseudoNode.length === 0) {
          // Load saved position for pseudo-node
          const pseudoPositions = loadPseudoNodePositions(activeOntologyIri);
          let position = pseudoPositions[pseudoNodeId];

          if (!position) {
            // Calculate center position for pseudo-node if no saved position
            const baseBBox = ontoState.cy.nodes().filter(n => !n.hasClass('imported')).boundingBox();
            const orderIndex = Math.max(0, visibleList.indexOf(imp));
            const padX = 200, jitterX = orderIndex * 100, jitterY = orderIndex * 60;
            const safe = (n, f) => (Number.isFinite(n) ? n : f);
            position = {
              x: safe(baseBBox.x2, 0) + padX + jitterX,
              y: safe(baseBBox.y1, 0) + jitterY
            };
          }

          const pseudoNode = ontoState.cy.add({
            group: 'nodes',
            data: {
              id: pseudoNodeId,
              label: importName,
              type: 'import',
              importSource: imp,
              isPseudo: true,
              attrs: {}
            },
            position: position,
            classes: 'imported pseudo-import'
          });
          added.push(pseudoNode);
        }
      } else {
        // Create all imported nodes normally
        snap.classes.forEach((c, index) => {
          // Use the original node ID from the local storage data if available, otherwise generate one
          const originalId = snap.importNodes?.[index]?.data?.id || `Class${index + 1}`;
          const id = `imp:${imp}#${originalId}`;
          console.log('🔍 Creating imported node with ID:', id, 'originalId:', originalId, 'from snapNode:', snap.importNodes?.[index]);
          if (ontoState.cy.$(`#${CSS.escape(id)}`).length) return;
          const pos = savedPos[id] ? savedPos[id] : nextPos();
          console.log('🔍 Position for', id, ':', pos, 'saved:', !!savedPos[id], 'savedPos keys:', Object.keys(savedPos));
          // Generate proper IRI for imported element using import source namespace
          const elementIri = c.iri || `${imp}#${slugId(c.label) || originalId}`;
          console.log('🔍 Creating imported node:', c.label, 'with IRI:', elementIri, 'from data:', c);
          const node = ontoState.cy.add({ group: 'nodes', data: { id, iri: elementIri, label: c.label, type: 'class', importSource: imp, attrs: c.attrs || {} }, position: pos, classes: 'imported' });
          added.push(node);
        });
      }
      if (isCollapsed) {
        // For collapsed imports, create equivalence edges from pseudo-node to base classes
        const pseudoNodeId = `pseudo-import-${CSS.escape(imp)}`;
        const pseudoNode = ontoState.cy.$(`#${CSS.escape(pseudoNodeId)}`);

        if (pseudoNode.length > 0) {
          // Find equivalence relationships by matching imported class labels with base class labels
          const baseClasses = ontoState.cy.nodes().filter(n => (n.data('type') || 'class') === 'class' && !n.hasClass('imported'));
          const byKey = (s) => String(s || '').trim().toLowerCase();
          const baseMap = new Map();
          baseClasses.forEach(n => baseMap.set(byKey(n.data('label') || n.id()), n));

          // Create equivalence edges for each imported class that matches a base class
          snap.classes.forEach(c => {
            const key = byKey(c.label);
            const baseNode = baseMap.get(key);
            if (baseNode) {
              const equivEdgeId = `pseudo-equiv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
              const equivEdge = ontoState.cy.add({
                group: 'edges',
                data: {
                  id: equivEdgeId,
                  source: pseudoNodeId,
                  target: baseNode.id(),
                  predicate: 'equivalentClass',
                  type: 'objectProperty',
                  importSource: imp,
                  isPseudo: true,
                  attrs: {}
                },
                classes: 'imported imported-equivalence pseudo-equivalence'
              });
              added.push(equivEdge);
            }
          });
        }
      } else {
        // Add edges where both endpoints available; create missing nodes on demand
        let idx = 0;
        snap.edges.forEach(e => {
          const sid = `imp:${imp}#${e.sourceIri}`;
          const tid = `imp:${imp}#${e.targetIri}`;
          if (!ontoState.cy.$(`#${CSS.escape(sid)}`).length) {
            const label = e.sourceIri.includes('#') ? e.sourceIri.split('#').pop() : e.sourceIri.split('/').pop();
            const pos = savedPos[sid] ? savedPos[sid] : nextPos();
            // Use the actual sourceIri as the element IRI
            added.push(ontoState.cy.add({ group: 'nodes', data: { id: sid, iri: e.sourceIri, label, type: 'class', importSource: imp, attrs: e.attrs || {} }, position: pos, classes: 'imported' }));
          }
          if (!ontoState.cy.$(`#${CSS.escape(tid)}`).length) {
            const label = e.targetIri.includes('#') ? e.targetIri.split('#').pop() : e.targetIri.split('/').pop();
            const pos = savedPos[tid] ? savedPos[tid] : nextPos();
            // Use the actual targetIri as the element IRI
            added.push(ontoState.cy.add({ group: 'nodes', data: { id: tid, iri: e.targetIri, label, type: 'class', importSource: imp, attrs: e.attrs || {} }, position: pos, classes: 'imported' }));
          }
          const edge = ontoState.cy.add({ group: 'edges', data: { id: `impE${Date.now()}_${idx++}`, source: sid, target: tid, predicate: e.label, type: 'objectProperty', importSource: imp, attrs: e.attrs || {} }, classes: 'imported' });
          added.push(edge);
        });
      }
      // Make overlays semi-interactive for positioning: allow drag, but don't select or edit
      added.forEach(el => {
        try {
          if (el.isNode && el.isNode()) {
            el.selectable(true); el.grabbable(true); el.locked(false); // Allow selection for imported elements
          } else {
            el.selectable(false); el.grabbable(false); el.locked(true);
          }
        } catch (_) { }
      });

      // Add position saving for pseudo-nodes
      added.filter(el => el.data('isPseudo')).forEach(el => {
        el.on('free', () => {
          const pseudoPositions = loadPseudoNodePositions(activeOntologyIri);
          pseudoPositions[el.id()] = { x: el.position('x'), y: el.position('y') };
          savePseudoNodePositions(activeOntologyIri, pseudoPositions);
        });
      });

      // Add position saving for imported nodes
      added.filter(el => el.isNode && el.isNode() && el.hasClass('imported') && !el.data('isPseudo')).forEach(el => {
        el.on('free', () => {
          const imp = el.data('importSource');
          if (!imp || !activeOntologyIri) return;
          const curr = loadOverlayPositions(activeOntologyIri, imp);
          curr[el.id()] = el.position();
          console.log('🔍 Saving position for imported element', el.id(), ':', el.position(), 'in import', imp);
          saveOverlayPositions(activeOntologyIri, imp, curr);
        });
      });

      // Add owl:equivalentClass visual links between base and imported nodes (by label/local name)
      // Only create equivalence edges for expanded imports
      if (!isCollapsed) {
        try {
          const baseClasses = ontoState.cy.nodes().filter(n => (n.data('type') || 'class') === 'class' && !n.hasClass('imported'));
          const imported = ontoState.cy.nodes().filter(n => (n.data('type') || 'class') === 'class' && n.hasClass('imported') && (n.data('importSource') || '') === imp);
          const byKey = (s) => String(s || '').trim().toLowerCase();
          const baseMap = new Map(); baseClasses.forEach(n => baseMap.set(byKey(n.data('label') || n.id()), n));
          let idx2 = 0;
          imported.forEach(n => {
            const key = byKey(n.data('label') || n.id());
            const base = baseMap.get(key);
            if (base) {
              const eid = `impEq${Date.now()}_${idx2++}`;
              const equivEdge = ontoState.cy.add({ group: 'edges', data: { id: eid, source: base.id(), target: n.id(), predicate: 'equivalentClass', type: 'objectProperty', importSource: imp, attrs: {} }, classes: 'imported imported-equivalence' });
              added.push(equivEdge);
            }
          });
        } catch (_) { }
      }
    }
    // Do not persist imported overlays to base local storage
    refreshOntologyTree();
  } catch (err) {
    console.error('🔍 Error in overlayImportsRefresh:', err);
    // Don't let the error crash the app
  }
}

// Context menu helpers
let cmState = { visible: false, sourceId: null };
function showMenuAt(x, y) {
  const m = qs('#ontoContextMenu'); if (!m) return;
  m.style.left = x + 'px'; m.style.top = y + 'px'; m.style.display = 'block'; cmState.visible = true;
}
function hideMenu() { const m = qs('#ontoContextMenu'); if (!m) return; m.style.display = 'none'; cmState.visible = false; }

// Edge context menu helpers for multiplicity constraints
function showEdgeMenuAt(x, y) {
  const m = qs('#edgeContextMenu'); if (!m) return;
  m.style.left = x + 'px'; m.style.top = y + 'px'; m.style.display = 'block';
  // Hide node context menu if visible
  hideMenu();

  // Auto-hide on outside click
  setTimeout(() => {
    const hideOnOutsideClick = (e) => {
      if (!m.contains(e.target)) {
        hideEdgeMenu();
        document.removeEventListener('click', hideOnOutsideClick);
      }
    };
    document.addEventListener('click', hideOnOutsideClick);
  }, 0);
}
function hideEdgeMenu() { const m = qs('#edgeContextMenu'); if (!m) return; m.style.display = 'none'; }

// Update edge label with multiplicity information
function updateEdgeLabel(edge) {
  const minCount = edge.data('minCount');
  const maxCount = edge.data('maxCount');
  const basePredicate = edge.data('predicate') || 'relatedTo';

  let multiplicity = '';
  if (minCount !== null && minCount !== undefined || maxCount !== null && maxCount !== undefined) {
    if (minCount === 1 && maxCount === 1) multiplicity = ' (1)';
    else if (minCount === 0 && (maxCount === null || maxCount === undefined)) multiplicity = ' (0..*)';
    else if (minCount === 1 && (maxCount === null || maxCount === undefined)) multiplicity = ' (1..*)';
    else if (minCount === 0 && maxCount === 1) multiplicity = ' (0..1)';
    else if (minCount !== null && minCount !== undefined && maxCount !== null && maxCount !== undefined && minCount === maxCount)
      multiplicity = ` (${minCount})`;
    else if (minCount !== null && minCount !== undefined && maxCount !== null && maxCount !== undefined)
      multiplicity = ` (${minCount}..${maxCount})`;
    else if (minCount !== null && minCount !== undefined) multiplicity = ` (${minCount}..*)`;
    else if (maxCount !== null && maxCount !== undefined) multiplicity = ` (0..${maxCount})`;
  }

  // Store multiplicity display  
  edge.data('multiplicityDisplay', multiplicity.trim());
  edge.data('predicate', basePredicate);  // Keep relationship name clean

  // FORCE CYTOSCAPE VISUAL REFRESH
  if (ontoState.cy) {
    ontoState.cy.style().update();
    // Small delay then force redraw
    setTimeout(() => {
      ontoState.cy.forceRender();
    }, 10);
  }

  console.log(`🎯 Updated edge: "${basePredicate}" with multiplicity at arrow tip: "${multiplicity.trim()}"`);

  // Trigger refresh
  refreshOntologyTree();
  persistOntologyToLocalStorage();
}

// Apply multiplicity constraint to edge
function updateEdgeMultiplicity(edge, minCount, maxCount) {
  // Store multiplicity in edge data
  edge.data('minCount', minCount);
  edge.data('maxCount', maxCount);

  // Update modification metadata
  const currentAttrs = edge.data('attrs') || {};
  const updatedAttrs = updateModificationMetadata(currentAttrs);
  edge.data('attrs', updatedAttrs);

  // Update visual display
  updateEdgeLabel(edge);

  // PERSIST TO BACKEND: Save all SHACL constraint changes to RDF store
  saveShaclConstraintsToBackend(edge);
}

// Save all SHACL constraints to backend RDF store
async function saveShaclConstraintsToBackend(edge) {
  const minCount = edge.data('minCount');
  const maxCount = edge.data('maxCount');
  const datatypeConstraint = edge.data('datatypeConstraint');
  const enumerationValues = edge.data('enumerationValues');
  try {
    if (!activeOntologyIri) {
      console.log('❌ No active ontology IRI for saving multiplicity');
      return;
    }

    const propertyName = edge.data('predicate');
    const edgeType = edge.data('type');

    if (edgeType !== 'objectProperty') {
      console.log('⚠️ Skipping multiplicity save for non-object property');
      return;
    }

    console.log(`💾 Saving SHACL constraints to backend for: ${propertyName}`);
    console.log(`   - Multiplicity: min=${minCount} max=${maxCount}`);
    console.log(`   - Datatype: ${datatypeConstraint || 'none'}`);
    console.log(`   - Enumeration: ${enumerationValues ? enumerationValues.join(', ') : 'none'}`);
    console.log(`🔍 Active ontology IRI: ${activeOntologyIri}`);

    // Build SPARQL UPDATE to add/update all SHACL constraints
    const propertyUri = `${activeOntologyIri}#${propertyName}`;
    console.log(`🔍 Property URI: ${propertyUri}`);

    let sparqlUpdate = `
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX odras: <http://odras.ai/ontology/>
    
    DELETE {
      GRAPH <${activeOntologyIri}> {
        <${propertyUri}> odras:minCount ?oldMin .
        <${propertyUri}> odras:maxCount ?oldMax .
        <${propertyUri}> odras:datatypeConstraint ?oldDatatype .
        <${propertyUri}> odras:enumerationValues ?oldEnum .
      }
    }
    WHERE {
      GRAPH <${activeOntologyIri}> {
        OPTIONAL { <${propertyUri}> odras:minCount ?oldMin }
        OPTIONAL { <${propertyUri}> odras:maxCount ?oldMax }
        OPTIONAL { <${propertyUri}> odras:datatypeConstraint ?oldDatatype }
        OPTIONAL { <${propertyUri}> odras:enumerationValues ?oldEnum }
      }
    }
    `;

    // Add new constraints (if any exist)
    if (minCount !== null || maxCount !== null || datatypeConstraint || enumerationValues) {
      sparqlUpdate += `;
      
      INSERT {
        GRAPH <${activeOntologyIri}> {
      `;

      // Multiplicity constraints
      if (minCount !== null) {
        sparqlUpdate += `    <${propertyUri}> odras:minCount ${minCount} .
`;
      }
      if (maxCount !== null) {
        sparqlUpdate += `    <${propertyUri}> odras:maxCount ${maxCount} .
`;
      }

      // Datatype constraint
      if (datatypeConstraint) {
        sparqlUpdate += `    <${propertyUri}> odras:datatypeConstraint "${datatypeConstraint}" .
`;
      }

      // Enumeration constraint (as JSON string)
      if (enumerationValues && enumerationValues.length > 0) {
        const enumJson = JSON.stringify(enumerationValues).replace(/\"/g, '\\\\"');
        sparqlUpdate += `    <${propertyUri}> odras:enumerationValues "${enumJson}" .
`;
      }

      sparqlUpdate += `  }
    } WHERE {}`;
    }

    console.log('🔍 SPARQL Update:');
    console.log(sparqlUpdate);

    // Execute SPARQL update directly to Fuseki update endpoint
    const fusekiUpdateUrl = 'http://localhost:3030/odras/update';
    console.log(`🔍 Sending UPDATE to: ${fusekiUpdateUrl}`);

    try {
      const response = await fetch(fusekiUpdateUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/sparql-update'
        },
        body: sparqlUpdate
      });

      console.log(`🔍 Response status: ${response.status}`);
      console.log(`🔍 Response ok: ${response.ok}`);

      if (response.ok) {
        console.log(`✅ SHACL constraints saved to RDF store for ${propertyName}`);
      } else {
        const errorText = await response.text();
        console.log(`❌ Failed to save SHACL constraints: ${response.status}`);
        console.log(`❌ Error response: ${errorText}`);
      }

    } catch (fetchError) {
      console.log(`❌ Network error saving SHACL constraints: ${fetchError}`);
      console.log(`❌ Error details: ${JSON.stringify(fetchError)}`);
    }

  } catch (error) {
    console.error('❌ Error saving SHACL constraints to backend:', error);
  }
}

// Save class inheritance data to backend RDF store
async function saveClassInheritanceToBackend(className, attrs) {
  if (!activeOntologyIri) {
    console.error('No active ontology IRI for saving class data');
    return;
  }

  try {
    console.log(`💾 Saving class inheritance data for: ${className}`);
    console.log(`📋 Class attributes:`, attrs);

    // Prepare class data for backend API
    const classData = {
      name: className,
      label: attrs.label || className,
      comment: attrs.comment || '',
      subclass_of: attrs.subclass_of || [],
      is_abstract: !!attrs.is_abstract
    };

    console.log(`💾 Sending class data to backend:`, classData);

    // Use the classes API endpoint to update the class
    const response = await authenticatedFetch(`/api/ontology/classes/${encodeURIComponent(className)}?graph=${encodeURIComponent(activeOntologyIri)}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(classData)
    });

    if (response.ok) {
      const result = await response.json();
      console.log('✅ Class inheritance data saved to backend:', result.message);
    } else {
      const errorText = await response.text();
      console.error('❌ Failed to save class inheritance data:', response.status, errorText);

      // Show error in UI
      const st = qs('#propSaveStatus');
      if (st) {
        st.textContent = 'Backend Save Failed';
        setTimeout(() => { const s = qs('#propSaveStatus'); if (s) s.textContent = ''; }, 3000);
      }
    }
  } catch (error) {
    console.error('❌ Error saving class inheritance data to backend:', error);

    // Show error in UI
    const st = qs('#propSaveStatus');
    if (st) {
      st.textContent = 'Save Error';
      setTimeout(() => { const s = qs('#propSaveStatus'); if (s) s.textContent = ''; }, 3000);
    }
  }
}

// Save model-level metadata to backend RDF store
async function saveModelMetadataToBackend(ontologyIri, modelName, attrs) {
  try {
    console.log(`💾 Saving model metadata for: ${modelName}`);
    console.log(`🔍 Ontology IRI: ${ontologyIri}`);
    console.log(`📋 Attributes:`, attrs);

    // Build SPARQL UPDATE for ontology metadata
    const ontologyUri = ontologyIri;  // The ontology IRI itself is the subject

    let sparqlUpdate = `
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    
    DELETE {
      GRAPH <${ontologyIri}> {
        <${ontologyUri}> rdfs:label ?oldLabel .
        <${ontologyUri}> rdfs:comment ?oldComment .
        <${ontologyUri}> skos:definition ?oldDefinition .
        <${ontologyUri}> owl:versionInfo ?oldVersion .
        <${ontologyUri}> dcterms:description ?oldDescription .
      }
    }
    WHERE {
      GRAPH <${ontologyIri}> {
        OPTIONAL { <${ontologyUri}> rdfs:label ?oldLabel }
        OPTIONAL { <${ontologyUri}> rdfs:comment ?oldComment }
        OPTIONAL { <${ontologyUri}> skos:definition ?oldDefinition }
        OPTIONAL { <${ontologyUri}> owl:versionInfo ?oldVersion }
        OPTIONAL { <${ontologyUri}> dcterms:description ?oldDescription }
      }
    }
    `;

    // Add new metadata if exists
    let hasInserts = false;
    let insertParts = [];

    // Add label (model name)
    if (modelName && modelName.trim()) {
      const escapedName = modelName.replace(/\\\\/g, '\\\\\\\\').replace(/"/g, '\\\\"').replace(/\\n/g, '\\\\n').replace(/\\r/g, '\\\\r');
      insertParts.push(`    <${ontologyUri}> rdfs:label "${escapedName}" .`);
      hasInserts = true;
    }

    // Add comment  
    if (attrs.comment && attrs.comment.trim()) {
      const escapedComment = attrs.comment.replace(/\\\\/g, '\\\\\\\\').replace(/"/g, '\\\\"').replace(/\\n/g, '\\\\n').replace(/\\r/g, '\\\\r');
      insertParts.push(`    <${ontologyUri}> rdfs:comment "${escapedComment}" .`);
      hasInserts = true;
    }

    // Add definition
    if (attrs.definition && attrs.definition.trim()) {
      const escapedDefinition = attrs.definition.replace(/\\\\/g, '\\\\\\\\').replace(/"/g, '\\\\"').replace(/\\n/g, '\\\\n').replace(/\\r/g, '\\\\r');
      insertParts.push(`    <${ontologyUri}> skos:definition "${escapedDefinition}" .`);
      hasInserts = true;
    }

    // Add version info
    if (attrs.versionInfo && attrs.versionInfo.trim()) {
      const escapedVersion = attrs.versionInfo.replace(/\\\\/g, '\\\\\\\\').replace(/"/g, '\\\\"').replace(/\\n/g, '\\\\n').replace(/\\r/g, '\\\\r');
      insertParts.push(`    <${ontologyUri}> owl:versionInfo "${escapedVersion}" .`);
      hasInserts = true;
    }

    // Add description
    if (attrs.description && attrs.description.trim()) {
      const escapedDescription = attrs.description.replace(/\\\\/g, '\\\\\\\\').replace(/"/g, '\\\\"').replace(/\\n/g, '\\\\n').replace(/\\r/g, '\\\\r');
      insertParts.push(`    <${ontologyUri}> dcterms:description "${escapedDescription}" .`);
      hasInserts = true;
    }

    if (hasInserts) {
      sparqlUpdate += `;
      
      INSERT {
        GRAPH <${ontologyIri}> {
${insertParts.join('\\n')}
        }
      } WHERE {}`;
    }

    console.log('🔍 Model metadata SPARQL Update:');
    console.log(sparqlUpdate);

    // Execute SPARQL update
    const fusekiUpdateUrl = 'http://localhost:3030/odras/update';
    console.log(`🔍 Sending model metadata UPDATE to: ${fusekiUpdateUrl}`);

    try {
      const response = await fetch(fusekiUpdateUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/sparql-update'
        },
        body: sparqlUpdate
      });

      console.log(`🔍 Model metadata response status: ${response.status}`);
      console.log(`🔍 Model metadata response ok: ${response.ok}`);

      if (response.ok) {
        console.log(`✅ Model metadata saved to RDF store for ${modelName}`);
      } else {
        const errorText = await response.text();
        console.log(`❌ Failed to save model metadata: ${response.status}`);
        console.log(`❌ Error response: ${errorText}`);
      }

    } catch (fetchError) {
      console.log(`❌ Network error saving model metadata: ${fetchError}`);
    }

  } catch (error) {
    console.error('❌ Error saving model metadata to backend:', error);
  }
}

// ========== CAD-LIKE FEATURES ==========

// Snap position to grid
function snapToGrid(position) {
  if (!ontoState.snapToGrid) return position;

  const gridSize = ontoState.gridSize;
  return {
    x: Math.round(position.x / gridSize) * gridSize,
    y: Math.round(position.y / gridSize) * gridSize
  };
}

// Toggle snap-to-grid with visual feedback
function toggleSnapToGrid() {
  ontoState.snapToGrid = !ontoState.snapToGrid;
  const status = ontoState.snapToGrid ? 'ON' : 'OFF';
  console.log(`🔧 Snap-to-grid: ${status} (Grid size: ${ontoState.gridSize}px)`);

  // Update UI status text
  const statusEl = document.querySelector('#snapGridStatus');
  if (statusEl) {
    statusEl.textContent = `Grid Snap: ${status}`;
  }

  // Show temporary visual feedback
  showTemporaryMessage(`Grid Snap: ${status}`, 1500);
}

// Update grid size
function updateGridSize(newSize) {
  if (newSize === 'custom') {
    const customSize = prompt('Enter custom grid size in pixels:', ontoState.gridSize);
    if (customSize && !isNaN(customSize) && customSize > 0) {
      ontoState.gridSize = parseInt(customSize);
    } else {
      // Reset dropdown to current value
      const selector = document.querySelector('#gridSizeSelector');
      if (selector) selector.value = ontoState.gridSize;
      return;
    }
  } else {
    ontoState.gridSize = parseInt(newSize);
  }

  // Update CSS grid background to match
  const canvasEl = document.querySelector('#cy');
  if (canvasEl) {
    canvasEl.style.backgroundSize = `${ontoState.gridSize}px ${ontoState.gridSize}px`;
  }

  console.log(`🔧 Grid size updated to: ${ontoState.gridSize}px`);
  showTemporaryMessage(`Grid: ${ontoState.gridSize}px`, 1000);
}

// Show temporary message overlay (like CAD status messages)
function showTemporaryMessage(message, duration = 2000) {
  // Remove existing message
  const existing = document.querySelector('#cadStatusMessage');
  if (existing) existing.remove();

  const msgDiv = document.createElement('div');
  msgDiv.id = 'cadStatusMessage';
  msgDiv.style.cssText = `
    position: fixed;
    top: 80px;
    right: 20px;
    background: var(--panel-2);
    color: var(--accent);
    border: 1px solid var(--accent);
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 600;
    z-index: 10000;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    transition: opacity 0.3s ease;
  `;
  msgDiv.textContent = message;
  document.body.appendChild(msgDiv);

  setTimeout(() => {
    if (msgDiv) {
      msgDiv.style.opacity = '0';
      setTimeout(() => msgDiv.remove(), 300);
    }
  }, duration);
}

// Align selected elements
function alignElements(direction) {
  if (!ontoState.cy) return;

  const selected = ontoState.cy.$(':selected').nodes();
  if (selected.length < 2) {
    showTemporaryMessage('Select 2+ elements to align');
    return;
  }

  const positions = selected.map(node => ({ node, pos: node.position() }));
  let referenceValue;

  switch (direction) {
    case 'left':
      referenceValue = Math.min(...positions.map(p => p.pos.x));
      positions.forEach(({ node }) => {
        const newPos = { x: referenceValue, y: node.position().y };
        node.position(snapToGrid(newPos));
      });
      break;
    case 'right':
      referenceValue = Math.max(...positions.map(p => p.pos.x));
      positions.forEach(({ node }) => {
        const newPos = { x: referenceValue, y: node.position().y };
        node.position(snapToGrid(newPos));
      });
      break;
    case 'center':
      const centerX = (Math.min(...positions.map(p => p.pos.x)) + Math.max(...positions.map(p => p.pos.x))) / 2;
      positions.forEach(({ node }) => {
        const newPos = { x: centerX, y: node.position().y };
        node.position(snapToGrid(newPos));
      });
      break;
    case 'top':
      referenceValue = Math.min(...positions.map(p => p.pos.y));
      positions.forEach(({ node }) => {
        const newPos = { x: node.position().x, y: referenceValue };
        node.position(snapToGrid(newPos));
      });
      break;
    case 'bottom':
      referenceValue = Math.max(...positions.map(p => p.pos.y));
      positions.forEach(({ node }) => {
        const newPos = { x: node.position().x, y: referenceValue };
        node.position(snapToGrid(newPos));
      });
      break;
    case 'distribute-horizontal':
      if (selected.length < 3) {
        showTemporaryMessage('Need 3+ elements to distribute');
        return;
      }
      positions.sort((a, b) => a.pos.x - b.pos.x);
      const minX = positions[0].pos.x;
      const maxX = positions[positions.length - 1].pos.x;
      const spacingX = (maxX - minX) / (positions.length - 1);
      positions.forEach(({ node }, index) => {
        const newPos = { x: minX + (index * spacingX), y: node.position().y };
        node.position(snapToGrid(newPos));
      });
      break;
    case 'distribute-vertical':
      if (selected.length < 3) {
        showTemporaryMessage('Need 3+ elements to distribute');
        return;
      }
      positions.sort((a, b) => a.pos.y - b.pos.y);
      const minY = positions[0].pos.y;
      const maxY = positions[positions.length - 1].pos.y;
      const spacingY = (maxY - minY) / (positions.length - 1);
      positions.forEach(({ node }, index) => {
        const newPos = { x: node.position().x, y: minY + (index * spacingY) };
        node.position(snapToGrid(newPos));
      });
      break;
  }

  showTemporaryMessage(`Aligned: ${direction}`);
  addToUndoStack('align', { direction, elements: selected.length });
  persistOntologyToLocalStorage();
}

// Undo/Redo system
function addToUndoStack(action, data) {
  if (!ontoState.cy) return;

  const state = {
    action,
    data,
    timestamp: Date.now(),
    snapshot: ontoState.cy.json() // Full canvas state
  };

  ontoState.undoStack.push(state);
  if (ontoState.undoStack.length > ontoState.maxUndoLevels) {
    ontoState.undoStack.shift(); // Remove oldest
  }

  // Clear redo stack when new action is performed
  ontoState.redoStack = [];
}

function performUndo() {
  if (!ontoState.cy || ontoState.undoStack.length === 0) {
    showTemporaryMessage('Nothing to undo');
    return;
  }

  // Save current state to redo stack
  const currentState = {
    action: 'undo_point',
    data: {},
    timestamp: Date.now(),
    snapshot: ontoState.cy.json()
  };
  ontoState.redoStack.push(currentState);

  // Restore previous state
  const previousState = ontoState.undoStack.pop();
  ontoState.cy.json(previousState.snapshot);

  showTemporaryMessage(`Undid: ${previousState.action}`);
  persistOntologyToLocalStorage();
}

function performRedo() {
  if (!ontoState.cy || ontoState.redoStack.length === 0) {
    showTemporaryMessage('Nothing to redo');
    return;
  }

  // Save current state to undo stack
  addToUndoStack('redo_point', {});
  ontoState.undoStack.pop(); // Remove the redo_point we just added

  // Restore redo state
  const redoState = ontoState.redoStack.pop();
  ontoState.cy.json(redoState.snapshot);

  showTemporaryMessage('Redid action');
  persistOntologyToLocalStorage();
}

// Copy selected elements
function copySelectedElements() {
  if (!ontoState.cy) return;

  const selected = ontoState.cy.$(':selected');
  if (selected.length === 0) {
    showTemporaryMessage('No elements selected to copy');
    return;
  }

  ontoState.clipboard = {
    nodes: selected.nodes().map(n => ({ data: n.data(), position: n.position() })),
    edges: selected.edges().map(e => ({ data: e.data() })),
    timestamp: Date.now()
  };

  showTemporaryMessage(`Copied ${selected.length} elements`);
}

// Paste elements with smart offset
function pasteElements() {
  if (!ontoState.cy || !ontoState.clipboard) {
    showTemporaryMessage('Nothing to paste');
    return;
  }

  const offset = 40; // Offset like CAD copy operations
  const newElements = [];
  const idMapping = {}; // Map old IDs to new IDs for edges

  // Create new nodes with offset positions
  ontoState.clipboard.nodes.forEach(nodeData => {
    const oldId = nodeData.data.id;
    const newId = `${oldId}_copy_${Date.now()}_${Math.floor(Math.random() * 1000)}`;

    const newPos = {
      x: nodeData.position.x + offset,
      y: nodeData.position.y + offset
    };

    const newNodeData = {
      group: 'nodes',
      data: { ...nodeData.data, id: newId },
      position: snapToGrid(newPos)
    };

    idMapping[oldId] = newId;
    newElements.push(newNodeData);
  });

  // Create new edges with updated source/target IDs
  ontoState.clipboard.edges.forEach(edgeData => {
    const newSource = idMapping[edgeData.data.source];
    const newTarget = idMapping[edgeData.data.target];

    // Only create edge if both nodes were copied
    if (newSource && newTarget) {
      const newId = `edge_copy_${Date.now()}_${Math.floor(Math.random() * 1000)}`;

      const newEdgeData = {
        group: 'edges',
        data: {
          ...edgeData.data,
          id: newId,
          source: newSource,
          target: newTarget
        }
      };

      newElements.push(newEdgeData);
    }
  });

  // Add to canvas and select
  ontoState.cy.add(newElements);
  ontoState.cy.$(':selected').unselect();
  newElements.forEach(el => {
    if (el.group === 'nodes') {
      ontoState.cy.$(`#${el.data.id}`).select();
    }
  });

  showTemporaryMessage(`Pasted ${newElements.length} elements`);
  addToUndoStack('paste', { count: newElements.length });
  persistOntologyToLocalStorage();
}

// Snap selected node to grid
function snapNodeToGrid() {
  if (!ontoState.cy) return;

  const selected = ontoState.cy.$(':selected').nodes();
  if (selected.length === 0) {
    showTemporaryMessage('No node selected');
    return;
  }

  selected.forEach(node => {
    const snappedPos = snapToGrid(node.position());
    node.position(snappedPos);
  });

  // Update position inputs if visible
  updatePositionInputs();
  showTemporaryMessage(`Snapped ${selected.length} node(s) to grid`);
  addToUndoStack('snap', { count: selected.length });
  persistOntologyToLocalStorage();
}

// Center selected node in view  
function centerNodeInView() {
  if (!ontoState.cy) return;

  const selected = ontoState.cy.$(':selected').nodes();
  if (selected.length === 0) {
    showTemporaryMessage('No node selected');
    return;
  }

  ontoState.cy.animate({
    center: { eles: selected },
    zoom: Math.max(ontoState.cy.zoom(), 0.8)
  }, {
    duration: 300
  });

  showTemporaryMessage('Centered in view');
}

// Update position input fields
function updatePositionInputs() {
  const posXInput = qs('#propPosX');
  const posYInput = qs('#propPosY');

  if (!posXInput || !posYInput || !ontoState.cy) return;

  const selected = ontoState.cy.$(':selected').nodes();
  if (selected.length === 1) {
    const pos = selected[0].position();
    posXInput.value = Math.round(pos.x);
    posYInput.value = Math.round(pos.y);
  } else if (selected.length > 1) {
    posXInput.placeholder = 'Multiple selected';
    posYInput.placeholder = 'Multiple selected';
    posXInput.value = '';
    posYInput.value = '';
  } else {
    posXInput.value = '';
    posYInput.value = '';
  }
}

// Apply position from input fields
function applyPositionFromInputs() {
  const posXInput = qs('#propPosX');
  const posYInput = qs('#propPosY');

  if (!posXInput || !posYInput || !ontoState.cy) return;

  const selected = ontoState.cy.$(':selected').nodes();
  if (selected.length === 0) return;

  const x = parseFloat(posXInput.value);
  const y = parseFloat(posYInput.value);

  if (isNaN(x) || isNaN(y)) return;

  const newPos = { x, y };
  const snappedPos = snapToGrid(newPos);

  selected.forEach(node => {
    node.position(snappedPos);
  });

  showTemporaryMessage(`Moved to (${snappedPos.x}, ${snappedPos.y})`);
  addToUndoStack('position', { x: snappedPos.x, y: snappedPos.y });
  persistOntologyToLocalStorage();
}

// Enhanced zoom controls (like CAD view controls)
function zoomToSelection() {
  if (!ontoState.cy) return;

  const selected = ontoState.cy.$(':selected');
  if (selected.length === 0) {
    showTemporaryMessage('No elements selected to zoom to');
    return;
  }

  ontoState.cy.animate({
    fit: { eles: selected, padding: 50 }
  }, {
    duration: 300
  });

  showTemporaryMessage('Zoomed to selection');
}

function zoomTo100Percent() {
  if (!ontoState.cy) return;

  ontoState.cy.animate({
    zoom: 1.0,
    center: { eles: ontoState.cy.elements() }
  }, {
    duration: 300
  });

  showTemporaryMessage('Zoom: 100%');
}

function zoomToFitAll() {
  if (!ontoState.cy) return;

  ontoState.cy.animate({
    fit: { eles: ontoState.cy.elements(), padding: 30 }
  }, {
    duration: 300
  });

  showTemporaryMessage('Fit all elements');
}

// Show custom multiplicity dialog
function showCustomMultiplicityDialog(edge) {
  const currentMin = edge.data('minCount');
  const currentMax = edge.data('maxCount');

  const dialog = document.createElement('div');
  dialog.style.cssText = `
    position: fixed; top: 50%; left: 50%; 
    transform: translate(-50%, -50%);
    background: var(--panel-2); border: 1px solid var(--border);
    border-radius: 6px; padding: 20px; z-index: 10000;
    min-width: 280px; box-shadow: 0 8px 24px rgba(0, 0, 0, .4);
  `;

  dialog.innerHTML = `
    <h3 style="margin-top: 0; color: var(--text); font-size: 16px;">Custom Multiplicity</h3>
    <div style="margin: 15px 0;">
      <label style="display: block; margin-bottom: 4px; color: var(--text); font-size: 13px;">Minimum count:</label>
      <input type="number" id="minCountInput" value="${currentMin || ''}" min="0" 
             style="width: 100%; padding: 6px; background: var(--panel); border: 1px solid var(--border); border-radius: 4px; color: var(--text);">
    </div>
    <div style="margin: 15px 0;">
      <label style="display: block; margin-bottom: 4px; color: var(--text); font-size: 13px;">Maximum count:</label>
      <input type="number" id="maxCountInput" value="${currentMax || ''}" min="0"
             style="width: 100%; padding: 6px; background: var(--panel); border: 1px solid var(--border); border-radius: 4px; color: var(--text);">
      <small style="display: block; margin-top: 4px; color: var(--muted); font-size: 11px;">
        Leave empty for unlimited
      </small>
    </div>
    <div style="margin-top: 20px; text-align: right;">
      <button id="cancelBtn" style="margin-right: 8px; padding: 6px 12px; background: transparent; border: 1px solid var(--border); border-radius: 4px; color: var(--text); cursor: pointer;">Cancel</button>
      <button id="applyBtn" style="padding: 6px 12px; background: var(--accent); border: none; border-radius: 4px; color: white; cursor: pointer;">Apply</button>
    </div>
  `;

  document.body.appendChild(dialog);

  // Focus first input
  setTimeout(() => {
    const input = dialog.querySelector('#minCountInput');
    if (input) input.focus();
  }, 100);

  dialog.querySelector('#cancelBtn').onclick = () => dialog.remove();
  dialog.querySelector('#applyBtn').onclick = () => {
    const minVal = dialog.querySelector('#minCountInput').value;
    const maxVal = dialog.querySelector('#maxCountInput').value;

    const minCount = minVal ? parseInt(minVal, 10) : null;
    const maxCount = maxVal ? parseInt(maxVal, 10) : null;

    updateEdgeMultiplicity(edge, minCount, maxCount);
    dialog.remove();
  };
}
function startConnectFrom(node) {
  cmState.sourceId = node.id();
  node.addClass('connect-source');
}
function clearConnectState() {
  if (cmState.sourceId && ontoState.cy) {
    const n = ontoState.cy.$('#' + cmState.sourceId);
    if (n) n.removeClass('connect-source');
  }
  cmState.sourceId = null;
}

// Ensure new class IDs do not collide with existing nodes after imports/loads
function recomputeNextId() {
  try {
    if (!ontoState || !ontoState.cy) return;
    let maxNum = 0;
    ontoState.cy.nodes().forEach(n => {
      try {
        const nid = (n && typeof n.id === 'function') ? n.id() : '';
        const m = /^Class(\d+)$/.exec(String(nid || ''));
        if (m) {
          const num = parseInt(m[1], 10);
          if (!isNaN(num)) maxNum = Math.max(maxNum, num);
        }
      } catch (_) { }
    });
    ontoState.nextId = Math.max(1, maxNum + 1);
  } catch (_) { }
}

async function importOntologyJSON(obj) {
  ensureOntologyInitialized();

  // Handle enhanced export format (with metadata, model, namedViews) or legacy format (just nodes/edges)
  let nodes, edges, modelMetadata, namedViews;

  if (obj.metadata && obj.model) {
    // Enhanced format from our new export
    nodes = obj.nodes || [];
    edges = obj.edges || [];
    modelMetadata = obj.model;
    namedViews = obj.namedViews || [];
    console.log('📋 Importing enhanced format with model metadata and named views');
  } else if (Array.isArray(obj.nodes) && Array.isArray(obj.edges)) {
    // Legacy format (just nodes/edges)
    nodes = obj.nodes;
    edges = obj.edges;
    modelMetadata = null;
    namedViews = [];
    console.log('📋 Importing legacy format (nodes/edges only)');
  } else {
    console.error('Invalid import format');
    return;
  }

  // Clear only base elements, keep imported overlays intact
  ontoState.cy.elements().filter(el => !el.hasClass('imported') && !el.hasClass('imported-equivalence')).remove();

  // Migration guard: filter out any overlays accidentally saved to JSON
  const isOverlayNode = (n) => {
    try {
      const d = (n && n.data) ? n.data : {};
      const id = String(d.id || '');
      const cls = String(n.classes || d.classes || '');
      return !!d.importSource || id.startsWith('imp:') || cls.includes('imported');
    } catch (_) { return false; }
  };

  const baseNodes = (nodes || []).filter(n => !isOverlayNode(n));
  const baseNodeIds = new Set(baseNodes.map(n => (n.data && n.data.id) || ''));
  const baseEdges = (edges || []).filter(e => {
    try {
      const d = (e && e.data) ? e.data : {};
      const cls = String(e.classes || d.classes || '');
      if (d.importSource || cls.includes('imported')) return false;
      if (String(d.predicate || '').toLowerCase() === 'equivalentclass') return false;
      return baseNodeIds.has(d.source) && baseNodeIds.has(d.target);
    } catch (_) { return false; }
  });

  // Add back base nodes and edges
  ontoState.cy.add(baseNodes.map(n => ({ group: 'nodes', data: n.data, position: n.position })));
  ontoState.cy.add(baseEdges.map(e => ({ group: 'edges', data: e.data })));
  ontoState.cy.fit();

  // Import model metadata if available
  if (modelMetadata && activeOntologyIri) {
    const pid = (activeProject && (activeProject.id || activeProject.project_id)) ? (activeProject.id || activeProject.project_id) : 'default';
    const ontologyKey = activeOntologyIri ? activeOntologyIri.split('/').pop() : 'default';
    const modelNameKey = `onto_model_name__${pid}__${ontologyKey}`;
    const modelAttrsKey = `onto_model_attrs__${pid}__${ontologyKey}`;

    // Save model name and attributes
    localStorage.setItem(modelNameKey, modelMetadata.name || 'Imported Ontology');
    const attrs = {
      comment: modelMetadata.comment || '',
      definition: modelMetadata.definition || '',
      version: modelMetadata.version || '',
      namespace: modelMetadata.namespace || activeOntologyIri,
      imports: modelMetadata.imports || ''
    };
    localStorage.setItem(modelAttrsKey, JSON.stringify(attrs));

    console.log('📋 Restored model metadata:', modelMetadata.name);
  }

  // Import named views if available
  if (namedViews && namedViews.length > 0 && activeOntologyIri) {
    try {
      console.log(`📋 Importing ${namedViews.length} named views:`, namedViews.map(v => v.name));
      await saveNamedViews(activeOntologyIri, namedViews);
      console.log('✅ Named views saved to backend successfully');
    } catch (error) {
      console.error('❌ Failed to import named views:', error);
    }
  }

  // Wait for named views to be saved before refreshing tree
  setTimeout(async () => {
    await refreshOntologyTree();
    persistOntologyToLocalStorage();

    // Update ID counter so new classes get unique IDs
    recomputeNextId();

    // Update properties panel to show imported model metadata
    updatePropertiesPanelFromSelection();

    console.log('✅ Import complete including tree refresh');
  }, 200);
}

// Auth/UI gating
const tokenKey = 'odras_token';
const userKey = 'odras_user';
function showAuth(show) {
  qs('#authView').style.display = show ? 'grid' : 'none';
  qs('#mainView').style.display = show ? 'none' : 'grid';
  // Hide/show logout button based on auth state
  qs('#logoutBtn').style.display = show ? 'none' : 'block';

  // Only close DAS when logging out - let DAS manage its own visibility when logging in
  if (show) {
    // When logging out: close and clean DAS
    if (typeof window.closeDASAndClean === 'function') {
      window.closeDASAndClean();
    }
  }
  // Don't manually override DAS panel display - let DAS state management handle it
}

// Global authentication state
let isAuthenticated = false;
let authCheckInProgress = false;

// Enhanced fetch wrapper that handles authentication
async function authenticatedFetch(url, options = {}) {
  const token = localStorage.getItem(tokenKey);

  // Add authorization header if token exists
  if (token) {
    options.headers = {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    };
  }

  try {
    const response = await fetch(url, options);

    // Check for 401 Unauthorized
    if (response.status === 401) {
      console.warn('Authentication failed (401), redirecting to login...');
      handleAuthFailure();
      throw new Error('Authentication required');
    }

    return response;
  } catch (error) {
    // Re-throw the error for the caller to handle
    throw error;
  }
}

// Handle authentication failure
function handleAuthFailure() {
  if (authCheckInProgress) return; // Prevent multiple simultaneous auth checks

  authCheckInProgress = true;
  isAuthenticated = false;

  // Close and clean DAS dock when session expires
  if (typeof window.closeDASAndClean === 'function') {
    window.closeDASAndClean();
  }

  // Clear stored auth data
  localStorage.removeItem(tokenKey);
  localStorage.removeItem(userKey);
  localStorage.removeItem('user'); // Clear full user object

  // Clear UI state
  qs('#userMenu').textContent = '';
  activeOntologyIri = null;
  updateOntoGraphLabel();

  // Hide admin UI elements since user is no longer authenticated
  updateAdminUIVisibility(false);

  // Show login screen
  showAuth(true);

  // Show notification
  if (window.toast) {
    window.toast('Session expired. Please log in again.', true);
  }

  authCheckInProgress = false;
}

// Periodic authentication check
let authCheckInterval = null;
function startAuthMonitoring() {
  // Check auth status every 30 seconds
  authCheckInterval = setInterval(async () => {
    if (!isAuthenticated) return;

    try {
      const token = localStorage.getItem(tokenKey);
      if (!token) {
        handleAuthFailure();
        return;
      }

      const response = await fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        handleAuthFailure();
      }
    } catch (error) {
      console.warn('Auth check failed:', error);
      handleAuthFailure();
    }
  }, 30000); // Check every 30 seconds
}

function stopAuthMonitoring() {
  if (authCheckInterval) {
    clearInterval(authCheckInterval);
    authCheckInterval = null;
  }
}
async function initAuth() {
  const token = localStorage.getItem(tokenKey);
  if (!token) {
    showAuth(true);
    isAuthenticated = false;
    stopAuthMonitoring();
    // Clear any stale user data
    localStorage.removeItem(userKey);
    localStorage.removeItem('user'); // Clear full user object
    qs('#userMenu').textContent = '';
    return;
  }

  try {
    const response = await authenticatedFetch('/api/auth/me');

    const me = await response.json();
    if (!me || me.error || !me.username) {
      // Invalid response, clear auth and show login
      handleAuthFailure();
      return;
    }

    // Success - user is authenticated
    isAuthenticated = true;
    localStorage.setItem(userKey, me.username);
    localStorage.setItem('user', JSON.stringify(me)); // Store full user object for context menu
    qs('#userMenu').textContent = me.username + (me.is_admin ? ' (admin)' : '');
    showAuth(false);

    // Update admin UI elements visibility
    updateAdminUIVisibility(me.is_admin);

    // Load knowledge assets if knowledge workbench is active
    const knowledgeWorkbench = document.getElementById('wb-knowledge');
    if (knowledgeWorkbench && knowledgeWorkbench.style.display !== 'none') {
      console.log('🧠 User authenticated, loading knowledge assets...');
      loadKnowledgeAssets();
    }

    // Start monitoring authentication status
    startAuthMonitoring();
  } catch (error) {
    // Network or other error, clear auth and show login
    console.error('Auth check failed:', error);
    handleAuthFailure();
    return;
  }
  // Restore last active workbench before loading projects
  try {
    const urlState = getURLState();
    const hashWB = (() => { try { const p = new URLSearchParams(location.hash.replace(/^#/, '')); return p.get('wb') || ''; } catch (_) { return ''; } })();
    const wb = urlState.workbench || hashWB || localStorage.getItem('active_workbench') || 'ontology';
    // Activate matching icon and section
    const icon = qs(`.icon[data-wb="${wb}"]`);
    if (icon) {
      // Instead of manually setting classes, trigger a click to run initialization
      icon.click();
    }
    // If no workbench got activated (e.g., missing section), default to ontology
    if (!document.querySelector('.workbench.active')) {
      const fallback = qs('.icon[data-wb="ontology"]');
      if (fallback) fallback.click();
    }

    // Update admin UI visibility based on current user
    try {
      const userData = JSON.parse(localStorage.getItem('user') || '{}');
      updateAdminUIVisibility(userData.is_admin || false);
    } catch (e) {
      console.error('Failed to parse user data for admin UI visibility:', e);
      updateAdminUIVisibility(false);
    }

    // Load admin data if admin workbench is active
    if (wb === 'admin') {
      loadPrefixes();
      loadDomains();
      loadUsers(); // Load user management data
      loadRagConfig(); // Load RAG configuration
      loadFileProcessingConfig(); // Load file processing configuration
      // Only load namespaces if user is authenticated
      const token = localStorage.getItem('odras_token');
      if (token) {
        loadNamespaces();
      }
    }
  } catch (_) { }
  // Initialize Cytoscape BEFORE loading projects so restore can occur during renderTree
  ensureOntologyInitialized();
  // If Files workbench is already active from restore, initialize its handlers now
  try { if (document.querySelector('#wb-files.workbench.active')) { ensureFilesInitialized(); } } catch (_) { }
  await loadProjects();
  // Load project info if project workbench is active (this is now handled in loadProjects)
  // but we'll keep this as a fallback
  try { if (document.querySelector('#wb-project.workbench.active')) { loadProjectInfo(); } } catch (_) { }
  refreshOntologyTree();
  // Bind Files workbench handlers proactively so Choose Files works immediately
  try { ensureFilesInitialized(); } catch (_) { }
  // Restore ontology tree collapsed state
  try {
    // Restore left project tree width
    const uiMainTreeW = parseInt(localStorage.getItem('ui_main_tree_w') || '0', 10);
    if (uiMainTreeW) document.documentElement.style.setProperty('--tree-w', uiMainTreeW + 'px');

    // Restore main tree collapsed state
    const mainTreeCollapsed = localStorage.getItem('main_tree_collapsed') === '1';
    if (mainTreeCollapsed) {
      const treePanel = qs('#treePanel');
      if (treePanel && !treePanel.classList.contains('tree-dock-collapsed')) {
        treePanel.classList.add('tree-dock-collapsed');
      }
    }

    // Restore ontology left tree width
    const ontoTreeW = parseInt(localStorage.getItem('onto_tree_w') || '0', 10);
    if (ontoTreeW) document.documentElement.style.setProperty('--onto-tree-w', ontoTreeW + 'px');
    const treeCollapsed = localStorage.getItem('onto_tree_collapsed') === '1';
    if (treeCollapsed) {
      const sec = qs('#wb-ontology');
      if (sec && !sec.classList.contains('onto-tree-collapsed')) sec.classList.add('onto-tree-collapsed');
      // CSS rotation handles chevron direction automatically
    }
    const propsCollapsed = localStorage.getItem('onto_props_collapsed') === '1';
    if (propsCollapsed) {
      const sec = qs('#wb-ontology');
      if (sec && !sec.classList.contains('onto-props-collapsed')) sec.classList.add('onto-props-collapsed');
      // CSS rotation handles chevron direction automatically
    }
    // CSS rotation handles chevron directions automatically for both panels
    const savedW = parseInt(localStorage.getItem('onto_props_w') || '0', 10);
    if (savedW) document.documentElement.style.setProperty('--onto-props-w', savedW + 'px');
    // Do not load any graph here; renderTree handles per-project restore safely
    requestAnimationFrame(() => { if (ontoState.cy) ontoState.cy.resize(); });
  } catch (_) { }
}
qs('#loginBtn').onclick = async () => {
  const username = qs('#u').value.trim();
  const password = qs('#p').value;
  qs('#loginMsg').textContent = 'Signing in...';

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const json = await res.json();

    if (res.ok && json.token) {
      localStorage.setItem(tokenKey, json.token);
      localStorage.setItem(userKey, username);
      qs('#loginMsg').textContent = '';
      await initAuth();
    } else {
      qs('#loginMsg').textContent = json.error || 'Login failed';
    }
  } catch (error) {
    console.error('Login error:', error);
    qs('#loginMsg').textContent = 'Login failed: ' + error.message;
  }
};
qs('#logoutBtn').onclick = async () => {
  // Call backend logout endpoint to invalidate token
  const token = localStorage.getItem(tokenKey);
  if (token) {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
    } catch (error) {
      console.warn('Logout API call failed:', error);
      // Continue with local logout even if API call fails
    }
  }

  // Close and clean DAS dock
  if (typeof window.closeDASAndClean === 'function') {
    window.closeDASAndClean();
  }

  // Clear user-specific data from localStorage but preserve URL state
  try {
    // Don't clear active_project_id - let URL state handle it
    localStorage.removeItem('active_ontology_iri');
    localStorage.removeItem('onto_state');
  } catch (error) {
    console.warn('Failed to clear localStorage:', error);
  }

  isAuthenticated = false;
  stopAuthMonitoring();
  localStorage.removeItem(tokenKey);
  localStorage.removeItem(userKey);
  localStorage.removeItem('user'); // Clear full user object
  activeOntologyIri = null;
  updateOntoGraphLabel();
  try { if (ontoState.cy) ontoState.cy.elements().remove(); } catch (_) { }
  qs('#userMenu').textContent = '';  // Clear user display
  showAuth(true);
};

// Initialize settings workbench
function initializeSettings() {
  console.log('⚙️ Initializing Settings workbench...');

  // Load saved settings from localStorage
  const savedTheme = localStorage.getItem('odras_theme') || 'dark';
  const savedTreeWidth = localStorage.getItem('ui_main_tree_w') || '300';

  // Set theme selector
  const themeSelect = document.getElementById('themeSelect');
  if (themeSelect) {
    themeSelect.value = savedTheme;
    themeSelect.addEventListener('change', (e) => {
      localStorage.setItem('odras_theme', e.target.value);
      console.log('Theme changed to:', e.target.value);
    });
  }

  // Set tree width slider
  const treeWidthSlider = document.getElementById('treeWidthSlider');
  const treeWidthValue = document.getElementById('treeWidthValue');
  if (treeWidthSlider && treeWidthValue) {
    treeWidthSlider.value = savedTreeWidth;
    treeWidthValue.textContent = savedTreeWidth + 'px';

    treeWidthSlider.addEventListener('input', (e) => {
      const width = e.target.value;
      treeWidthValue.textContent = width + 'px';
      localStorage.setItem('ui_main_tree_w', width);

      // Apply the width change immediately
      const tree = document.querySelector('.tree');
      if (tree) {
        tree.style.width = width + 'px';
      }
    });
  }
}

// Initialize analysis lab workbench
function initializeAnalysisLab() {
  console.log('📊 Initializing Analysis Lab workbench...');

  // Check if Jupyter Lab is already running
  const jupyterStatus = localStorage.getItem('jupyter_lab_status') || 'stopped';
  updateJupyterStatus(jupyterStatus);
}

// Jupyter Lab functions
function startJupyterLab() {
  console.log('🚀 Starting Jupyter Lab...');

  // Update status to starting
  updateJupyterStatus('starting');

  // Simulate Jupyter Lab startup (in real implementation, this would make API calls)
  setTimeout(() => {
    // For demo purposes, show a placeholder
    const content = document.getElementById('jupyterLabContent');
    const iframe = document.getElementById('jupyterLabFrame');

    if (content && iframe) {
      content.style.display = 'none';
      iframe.style.display = 'block';

      // Set a placeholder URL (in real implementation, this would be the actual Jupyter Lab URL)
      iframe.src = 'data:text/html,<div style="display:flex;align-items:center;justify-content:center;height:100%;background:#f8f9fa;color:#666;font-family:monospace;"><div style="text-align:center;"><h3>Jupyter Lab</h3><p>Jupyter Lab would be running here</p><p style="font-size:12px;color:#999;">This is a placeholder for demonstration</p></div></div>';

      updateJupyterStatus('running');
    }
  }, 2000);
}

function showJupyterInfo() {
  alert('Jupyter Lab Integration:\\n\\n• Interactive data analysis environment\\n• Support for Python, R, Julia, and more\\n• Rich visualizations and plots\\n• Collaborative notebooks\\n• Integration with ODRAS data sources\\n\\nThis is a scaffolded interface for future Jupyter Lab integration.');
}

function updateJupyterStatus(status) {
  localStorage.setItem('jupyter_lab_status', status);

  const buttons = document.querySelectorAll('#jupyterLabContainer button');
  buttons.forEach(btn => {
    if (btn.textContent.includes('Launch Jupyter Lab')) {
      if (status === 'starting') {
        btn.textContent = 'Starting...';
        btn.disabled = true;
      } else if (status === 'running') {
        btn.textContent = 'Stop Lab';
        btn.disabled = false;
        btn.onclick = stopJupyterLab;
      } else {
        btn.textContent = 'Launch Jupyter Lab';
        btn.disabled = false;
        btn.onclick = startJupyterLab;
      }
    }
  });
}

function stopJupyterLab() {
  console.log('🛑 Stopping Jupyter Lab...');

  const content = document.getElementById('jupyterLabContent');
  const iframe = document.getElementById('jupyterLabFrame');

  if (content && iframe) {
    content.style.display = 'flex';
    iframe.style.display = 'none';
    iframe.src = 'about:blank';

    updateJupyterStatus('stopped');
  }
}

// Enhanced Jupyter Lab Toolbar Functions
function createNewNotebook() {
  console.log('📓 Creating new notebook...');
  alert('New notebook creation would be implemented here. This would create a new Jupyter notebook for analysis.');
}

function openFile() {
  console.log('📁 Opening file...');
  alert('File browser would be implemented here. This would open the Jupyter Lab file browser.');
}

function saveNotebook() {
  console.log('💾 Saving notebook...');
  alert('Notebook save functionality would be implemented here.');
}

function runCell() {
  console.log('▶️ Running cell...');
  alert('Cell execution would be implemented here. This would run the current cell in Jupyter Lab.');
}

function stopExecution() {
  console.log('⏸️ Stopping execution...');
  alert('Execution stop functionality would be implemented here.');
}

function restartKernel() {
  console.log('🔄 Restarting kernel...');
  alert('Kernel restart functionality would be implemented here.');
}

function loadOdrasData() {
  console.log('📊 Loading ODRAS data...');
  alert('ODRAS data loading would be implemented here. This would provide access to project data from PostgreSQL, Neo4j, and Qdrant.');
}

function saveToArtifacts() {
  console.log('💾 Saving to artifacts...');
  alert('Save to artifacts functionality would be implemented here. This would save notebook outputs to the artifacts section.');
}

function exportReport() {
  console.log('📋 Exporting report...');
  alert('Report export functionality would be implemented here. This would generate reports from notebook outputs.');
}

function linkToProject() {
  console.log('🔗 Linking to project...');
  alert('Project linking functionality would be implemented here. This would associate the notebook with the current ODRAS project.');
}

function quickPlot() {
  console.log('📈 Quick plot...');
  alert('Quick plotting functionality would be implemented here. This would provide quick access to plotting tools.');
}

function openMLTemplates() {
  console.log('🤖 Opening ML templates...');
  alert('ML templates would be implemented here. This would provide pre-built machine learning workflow templates.');
}

function openSimulation() {
  console.log('🎲 Opening simulation...');
  alert('Simulation functionality would be implemented here. This would provide simulation workflow templates and tools.');
}

function shareNotebook() {
  console.log('👥 Sharing notebook...');
  alert('Notebook sharing functionality would be implemented here. This would allow sharing notebooks with team members.');
}

function openTemplates() {
  console.log('📚 Opening templates...');
  alert('Template library would be implemented here. This would provide ODRAS-specific notebook templates.');
}

function showJupyterHelp() {
  alert('Jupyter Lab Help:\\n\\n• Use Ctrl+Enter to run cells\\n• Use Shift+Enter to run and advance\\n• Use A/B to add cells above/below\\n• Use DD to delete cells\\n• Use M/Y to switch between Markdown/Code\\n\\nODRAS Integration:\\n• Load project data directly\\n• Save results to artifacts\\n• Export reports and visualizations\\n• Collaborate with team members');
}

// Projects
async function loadProjects() {
  const res = await authenticatedFetch('/api/projects');
  const json = await res.json();
  const raw = json.projects || [];
  // Normalize backend shape to { id, name }
  const list = raw.map(p => ({
    id: p.id || p.project_id || p.projectId,
    name: p.name || p.project_name || 'Project'
  })).filter(p => !!p.id);
  const selects = [qs('#projectSelect2')];
  if (list.length) {
    // Check URL state first, then localStorage, then default to first project
    const urlState = getURLState();
    const savedPid = (localStorage.getItem('active_project_id') || '').trim();
    const urlProjectId = urlState.projectId;

    let selected = list[0];
    let projectIdToUse = null;

    // Priority: URL state > localStorage > first available project
    if (urlProjectId) {
      const found = list.find(p => p.id === urlProjectId);
      if (found) {
        selected = found;
        projectIdToUse = urlProjectId;
        console.log('Using project from URL:', urlProjectId);
      } else {
        console.warn('URL project ID not accessible, falling back to localStorage');
      }
    }

    if (!projectIdToUse && savedPid) {
      const found = list.find(p => p.id === savedPid);
      if (found) {
        selected = found;
        projectIdToUse = savedPid;
        console.log('Using project from localStorage:', savedPid);
      } else {
        // Saved project ID not found in accessible projects - clear it
        console.warn('Saved project ID not accessible, clearing selection');
        try {
          localStorage.removeItem('active_project_id');
        } catch (error) {
          console.warn('Failed to clear project selection:', error);
        }
      }
    }

    // Update localStorage and URL to match selected project
    // Use selected.id if projectIdToUse wasn't set (fallback)
    const finalProjectId = projectIdToUse || selected.id;
    if (finalProjectId) {
      try {
        localStorage.setItem('active_project_id', finalProjectId);
        updateURL(finalProjectId);
      } catch (error) {
        console.warn('Failed to update project state:', error);
      }
    }

    // Update namespace display for initial project
    if (selected) {
      updateNamespaceDisplay(selected.id);
    }
    selects.forEach(sel => { if (sel) { sel.innerHTML = list.map(p => `<option value="${p.id}">${p.name}</option>`).join(''); sel.disabled = false; sel.value = selected.id; } });
    await renderTree(selected);

    // Load project info if project workbench is active
    if (document.querySelector('#wb-project.workbench.active')) {
      // Small delay to ensure project selection is fully established
      setTimeout(() => {
        loadProjectInfo();
      }, 100);
    }
  } else {
    // No projects: clear tree and show empty state
    console.warn('No accessible projects found, clearing project selection');
    try {
      localStorage.removeItem('active_project_id');
    } catch (error) {
      console.warn('Failed to clear project selection:', error);
    }
    selects.forEach(sel => { if (sel) { sel.innerHTML = '<option value="" disabled selected>Create Project...</option>'; sel.disabled = true; } });
    await renderTree({ id: null, name: '' });
  }
}
// Reusable progress indicator system for project operations
function createProjectProgressIndicator(message, type = 'info') {
  console.log('🔧 createProjectProgressIndicator called:', message, type);

  // Remove any existing progress indicator
  const existing = document.getElementById('project-operation-progress');
  if (existing) {
    console.log('🔧 Removing existing progress indicator');
    existing.remove();
  }

  const progressDiv = document.createElement('div');
  progressDiv.id = 'project-operation-progress';
  console.log('🔧 Created progress div element');

  const colors = {
    info: '#2196F3',
    success: '#4CAF50',
    error: '#f44336',
    warning: '#FF9800'
  };

  progressDiv.style.cssText = `
    position: fixed; top: 50px; right: 50px;
    background: ${colors[type]}; color: white;
    padding: 20px 30px; border-radius: 12px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    z-index: 99999; font-weight: bold; font-size: 16px;
    animation: pulse 1.5s infinite;
    max-width: 400px; text-align: center;
    transition: all 0.3s ease;
    border: 3px solid white;
  `;
  progressDiv.innerHTML = message;
  console.log('🔧 Appending progress div to body');
  document.body.appendChild(progressDiv);
  console.log('🔧 Progress indicator should now be visible');
  return progressDiv;
}

function updateProjectProgress(message, type = 'info') {
  console.log('🔧 updateProjectProgress called:', message, type);
  const progressDiv = document.getElementById('project-operation-progress');
  if (progressDiv) {
    console.log('🔧 Found progress div, updating...');
    progressDiv.innerHTML = message;
    const colors = {
      info: '#2196F3',
      success: '#4CAF50',
      error: '#f44336',
      warning: '#FF9800'
    };
    progressDiv.style.background = colors[type];
    console.log('🔧 Progress updated successfully');
  } else {
    console.warn('🔧 Progress div not found for update');
  }
}

function removeProjectProgress(delay = 0) {
  setTimeout(() => {
    const progressDiv = document.getElementById('project-operation-progress');
    if (progressDiv) {
      progressDiv.style.animation = 'fadeOut 0.3s ease';
      setTimeout(() => progressDiv.remove(), 300);
    }
  }, delay);
}

// Add CSS for animations
if (!document.getElementById('project-progress-styles')) {
  const style = document.createElement('style');
  style.id = 'project-progress-styles';
  style.textContent = `
    @keyframes pulse {
      0% { transform: scale(1); opacity: 1; }
      50% { transform: scale(1.05); opacity: 0.8; }
      100% { transform: scale(1); opacity: 1; }
    }
    @keyframes fadeOut {
      from { opacity: 1; transform: translateY(0); }
      to { opacity: 0; transform: translateY(-20px); }
    }
  `;
  document.head.appendChild(style);
}

// Enhanced project deletion with progress indicator
async function deleteProjectWithProgress(projectId, projectName) {
  if (!projectId) {
    alert('No project selected for deletion');
    return false;
  }

  // Confirm deletion
  if (!confirm(`Are you sure you want to delete project "${projectName}"?\n\nThis will permanently delete:\n• Project data and settings\n• All uploaded files\n• All knowledge assets\n• All project threads and history\n\nThis action cannot be undone.`)) {
    return false;
  }

  const progressDiv = createProjectProgressIndicator('🗑️ Preparing to delete project...', 'warning');

  try {
    const token = localStorage.getItem('odras_token');
    if (!token) {
      throw new Error('Authentication required');
    }

    console.log(`🗑️ Deleting project "${projectName}" (${projectId})...`);

    // Step 1: Delete from database
    updateProjectProgress('🗄️ Removing project from database...', 'warning');

    const res = await fetch(`/api/projects/${projectId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`Failed to delete project: ${res.status} ${errorText}`);
    }

    // Step 2: Clean up UI
    updateProjectProgress('🔄 Updating project list...', 'info');

    // Reload projects
    const pr = await fetch('/api/projects', {
      headers: { Authorization: 'Bearer ' + token }
    }).then(r => r.json()).catch(() => ({ projects: [] }));

    const raw = pr.projects || [];
    const list = raw.map(p => ({ id: p.id || p.project_id || p.projectId, name: p.name || p.project_name || 'Project' })).filter(p => !!p.id);

    // Update project selector
    const sel = qs('#projectSelect2');
    if (sel) {
      sel.innerHTML = list.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
      if (list.length) {
        sel.value = list[0].id;
        sel.disabled = false;
      } else {
        sel.innerHTML = '<option value="" disabled selected>No projects</option>';
        sel.disabled = true;
      }
    }

    // Render tree with new selection
    const selected = list[0] || { id: null, name: '' };
    updateProjectProgress('🎨 Updating interface...', 'info');
    await renderTree(selected);

    // Success
    updateProjectProgress(`✅ Project "${projectName}" deleted successfully`, 'success');
    removeProjectProgress(2000);

    console.log(`✅ Project "${projectName}" deleted successfully`);
    return true;

  } catch (error) {
    console.error('❌ Error during project deletion:', error);
    updateProjectProgress('❌ Project deletion failed', 'error');
    removeProjectProgress(3000);
    alert(`Error deleting project: ${error.message}`);
    return false;
  }
}

// Global functions for project operations
window.createProjectProgressIndicator = createProjectProgressIndicator;
window.updateProjectProgress = updateProjectProgress;
window.removeProjectProgress = removeProjectProgress;
window.deleteProjectWithProgress = deleteProjectWithProgress;

(function () {
  const npb = qs('#newProjectBtn');
  if (!npb) return;
  npb.onclick = async () => {
    // Prevent multiple clicks during project creation
    if (npb.disabled) {
      console.log('🚫 Project creation already in progress...');
      return;
    }

    const name = prompt('Project name');
    if (!name) return;

    // Disable button and show loading state
    const originalText = npb.textContent;
    npb.disabled = true;
    npb.innerHTML = '🔄 Creating...';
    npb.style.opacity = '0.7';
    npb.style.cursor = 'not-allowed';

    // Add progress indicator using reusable system
    console.log('🔧 Creating progress indicator...');
    let progressDiv;
    try {
      progressDiv = createProjectProgressIndicator('🏗️ Creating project...');
      console.log('🔧 Progress indicator created:', progressDiv);
    } catch (progressError) {
      console.error('🔧 Progress indicator failed:', progressError);
      // Fallback: just log to console
      console.log('🏗️ Creating project (progress indicator failed)...');
    }

    try {
      const token = localStorage.getItem(tokenKey);
      console.log(`🏗️ Creating project "${name}"...`);

      // Update progress
      updateProjectProgress('📝 Submitting project data...');

      const res = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token },
        body: JSON.stringify({ name })
      });

      // Update progress
      updateProjectProgress('⚙️ Processing project creation...');

      let pid = '';
      let pname = name;
      if (res.ok) {
        const js = await res.json().catch(() => ({}));
        const proj = js.project || js;
        pid = (proj && (proj.id || proj.project_id || proj.projectId)) || '';
        pname = (proj && proj.name) || name;
        if (pid) {
          try {
            localStorage.setItem('active_project_id', pid);
            updateURL(pid); // Update URL with new project
            updateNamespaceDisplay(pid); // Update namespace display
          } catch (_) { }
          console.log(`✅ Project "${pname}" created successfully (ID: ${pid})`);
        }
      } else {
        console.error(`❌ Failed to create project: ${res.status} ${res.statusText}`);
        alert(`Failed to create project: ${res.status} ${res.statusText}`);
      }

      // Reload projects, select the created one, and render it
      console.log('🔄 Reloading projects...');
      updateProjectProgress('🔄 Refreshing project list...');

      const pr = await fetch('/api/projects', { headers: { Authorization: 'Bearer ' + token } }).then(r => r.json()).catch(() => ({ projects: [] }));
      const raw = pr.projects || [];
      const list = raw.map(p => ({ id: p.id || p.project_id || p.projectId, name: p.name || p.project_name || 'Project' })).filter(p => !!p.id);
      const sel = qs('#projectSelect2');
      if (sel) {
        sel.innerHTML = list.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
        if (pid && list.find(p => p.id === pid)) sel.value = pid; else if (list.length) sel.value = list[0].id;
        sel.disabled = !list.length;
      }
      const selected = pid ? { id: pid, name: pname } : (list[0] || { id: null, name: '' });
      updateProjectProgress('🎨 Setting up project interface...');

      // Set active project in localStorage and update URL if we have a new project
      if (pid) {
        try {
          localStorage.setItem('active_project_id', pid);
          updateURL(pid);
          updateNamespaceDisplay(pid);

          // Trigger the dropdown change event to properly initialize the new project
          const selDropdown = qs('#projectSelect2');
          if (selDropdown && selDropdown.value === pid) {
            // Dispatch change event to trigger the dropdown's change handler
            selDropdown.dispatchEvent(new Event('change', { bubbles: true }));
          }
        } catch (_) { }
      }

      await renderTree(selected);

      // Success indicator
      updateProjectProgress('✅ Project created successfully!', 'success');
      removeProjectProgress(2000);

      console.log('✅ Project creation and setup completed');

    } catch (error) {
      console.error('❌ Error during project creation:', error);

      // Error indicator
      updateProjectProgress('❌ Project creation failed', 'error');
      removeProjectProgress(3000);

      alert(`Error creating project: ${error.message}`);
    } finally {
      // Re-enable button and restore original state
      npb.disabled = false;
      npb.innerHTML = originalText;
      npb.style.opacity = '1';
      npb.style.cursor = 'pointer';
      console.log('🔓 Project creation button re-enabled');

      // Ensure progress indicator is removed
      removeProjectProgress(100);
    }
  };
})();
['#projectSelect2'].forEach(id => {
  const sel = qs(id); if (!sel) return;
  sel.addEventListener('change', async (e) => {
    const pid = e.target.value;
    try {
      localStorage.setItem('active_project_id', pid);
      updateURL(pid); // Update URL with new project

      // Update Thread Manager with new project
      if (window.updateThreadManagerProject) {
        window.updateThreadManagerProject(pid);
      }
    } catch (_) { }
    const token = localStorage.getItem(tokenKey);
    // Save current ontology canvas before switching projects
    try { if (ontoState && ontoState.cy && activeOntologyIri) saveGraphToLocal(activeOntologyIri); } catch (_) { }
    const res = await fetch('/api/projects', { headers: { Authorization: 'Bearer ' + token } });
    const json = await res.json();
    const raw = json.projects || [];
    const list = raw.map(p => ({ id: p.id || p.project_id || p.projectId, name: p.name || p.project_name || 'Project' }));
    const proj = list.find(p => p.id === pid);
    if (proj) {
      activeOntologyIri = null;
      updateOntoGraphLabel();
      await renderTree(proj);
      updateNamespaceDisplay(pid);
      // Update project info page if it's active
      if (document.querySelector('#wb-project.workbench.active')) {
        loadProjectInfo();
      }

      // Always reset requirements state when project changes
      if (window.requirementsState) {
        window.requirementsState.currentPage = 1;
        window.requirementsState.filters = {
          search: '',
          requirement_type: '',
          state: '',
          priority: '',
          verification_status: ''
        };
        // Clear filters in UI
        const searchInput = document.getElementById('reqSearchInput');
        if (searchInput) searchInput.value = '';
        const selects = ['reqTypeFilter', 'reqStatusFilter', 'reqPriorityFilter'];
        selects.forEach(id => {
          const el = document.getElementById(id);
          if (el) el.value = '';
        });
      }

      // Update requirements workbench if it's active
      if (document.querySelector('#wb-requirements.workbench.active')) {
        if (window.loadRequirements) {
          window.loadRequirements();
        }
      }

      // Reinitialize DAS dock for new project if dock is open
      console.log('🔄 Project dropdown changed to:', pid);

      if (typeof window.reinitializeDASForProject === 'function') {
        try {
          await window.reinitializeDASForProject(pid);
        } catch (error) {
          console.error('🔄 Error during DAS reinitialize:', error);
        }
      } else {
        console.warn('🔄 reinitializeDASForProject function not available - DAS dock will not update');
      }
    }
  });
});

// Plus button near project selector creates a new project
(function () {
  const btn = qs('#addNodeBtn');
  if (!btn) return;
  btn.addEventListener('click', () => {
    showCreateProjectModal();
  });
})();

// Workbench switching
qsa('.icon').forEach(el => el.onclick = () => {
  // Get the previous workbench
  const previousWb = document.querySelector('.workbench.active')?.id?.replace('wb-', '');

  qsa('.icon').forEach(i => i.classList.remove('active')); el.classList.add('active');
  const wb = el.getAttribute('data-wb');
  qsa('.workbench').forEach(w => w.classList.remove('active'));
  qs('#wb-' + wb).classList.add('active');

  // Load data when switching to specific workbenches
  if (wb === 'settings') {
    initializeSettings();
  } else if (wb === 'analysis') {
    initializeAnalysisLab();
  } else if (wb === 'admin') {
    loadPrefixes();
    loadDomains();
    // Only load namespaces if user is authenticated
    const token = localStorage.getItem('odras_token');
    if (token) {
      loadNamespaces();
    }
  } else if (wb === 'project') {
    // For project workbench, load project info if we have a project selected
    const currentProjectId = localStorage.getItem('active_project_id');
    if (currentProjectId) {
      loadProjectInfo();
    }
  } else if (wb === 'thread') {
    // Initialize Thread Manager workbench
    console.log('🧵 Activating Thread Manager workbench');
    const currentProjectId = localStorage.getItem('active_project_id');
    if (currentProjectId) {
      updateThreadManagerProject(currentProjectId);
    }
    onThreadWorkbenchActivated();
  } else if (wb === 'events') {
    // Initialize Event Manager workbench
    console.log('📊 Activating Event Manager workbench');
    initializeEventManager();
  } else if (wb === 'conceptualizer') {
    // Initialize Conceptualizer workbench
    console.log('🎯 Activating Conceptualizer workbench');
    initializeConceptualizer();
  }

  // Persist selected workbench and update URL
  try {
    localStorage.setItem('active_workbench', wb);
    const currentProjectId = localStorage.getItem('active_project_id');
    updateURL(currentProjectId, wb); // Update URL with workbench
  } catch (_) { }
  // Reflect in hash
  try {
    const params = new URLSearchParams(location.hash.replace(/^#/, ''));
    params.set('wb', wb);
    location.hash = params.toString();
  } catch (_) { }
  if (wb === 'graph') refreshGraphSummary();
  if (wb === 'ontology') { ensureOntologyInitialized(); if (ontoState.cy) ontoState.cy.resize(); }
  if (wb === 'files') {
    ensureFilesInitialized();
    // Load library when files workbench becomes active
    try {
      if (window.loadLibraryFromApi) {
        setTimeout(() => window.loadLibraryFromApi(), 100); // Small delay to ensure auth/project context is ready
      }
    } catch (_) { }
  } else if (wb === 'requirements') {
    // Initialize Requirements Workbench
    console.log('📋 Activating Requirements Workbench');
    if (typeof initializeRequirementsWorkbench === 'function') {
      initializeRequirementsWorkbench();
    } else {
      console.error('❌ initializeRequirementsWorkbench is not defined!');
      console.log('📋 Available functions:', Object.keys(window).filter(k => k.includes('equirement')));
    }
  }
});

// Tree collapsible sections
qsa('.section > button').forEach(btn => {
  btn.onclick = (e) => {
    const sec = e.currentTarget.parentElement;
    const expanded = sec.getAttribute('aria-expanded') !== 'false';
    sec.setAttribute('aria-expanded', expanded ? 'false' : 'true');
  };
});

// Admin section toggle function
function toggleSection(header) {
  console.log('🔄 Toggling section...', header);
  const section = header.closest('.section');
  console.log('Section found:', section);
  if (!section) {
    console.error('❌ Section not found');
    return;
  }

  const content = section.querySelector('.section-content');
  console.log('Content found:', content);
  if (!content) {
    console.error('❌ Content not found');
    return;
  }

  const isCollapsed = section.classList.contains('collapsed');
  console.log('Currently collapsed:', isCollapsed);

  // Toggle the collapsed class
  section.classList.toggle('collapsed');

  // Toggle display style based on collapsed state
  if (section.classList.contains('collapsed')) {
    content.style.display = 'none';
  } else {
    content.style.display = 'block';
  }

  // Update the toggle icon
  const icon = header.querySelector('.section-toggle');
  console.log('Icon found:', icon);
  if (icon) {
    const newIcon = section.classList.contains('collapsed') ? '▶' : '▼';
    icon.textContent = newIcon;
    console.log('✅ Section toggled, icon updated to:', newIcon);
  } else {
    console.error('❌ Icon not found');
  }
}

// Resizer
(function () {
  const res = qs('#resizer');
  const panel = qs('#treePanel');
  let dragging = false;
  res.addEventListener('mousedown', () => dragging = true);
  window.addEventListener('mouseup', () => {
    dragging = false;
    requestAnimationFrame(() => { if (ontoState.cy) ontoState.cy.resize(); });
  });
  window.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    const min = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--tree-w-min'));
    const max = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--tree-w-max'));
    let w = e.clientX - parseInt(getComputedStyle(document.documentElement).getPropertyValue('--iconbar-w'));
    w = Math.max(min, Math.min(max, w));
    document.documentElement.style.setProperty('--tree-w', w + 'px');
    try { localStorage.setItem('ui_main_tree_w', String(w)); } catch (_) { }
    if (ontoState.cy) ontoState.cy.resize();
  });
})();

// Ontology panel resizer
(function () {
  const res = qs('#ontoResizer');
  const panelWidthProp = '--onto-tree-w';
  let dragging = false;
  if (!res) return;
  res.addEventListener('mousedown', () => dragging = true);
  window.addEventListener('mouseup', () => {
    dragging = false;
    requestAnimationFrame(() => { if (ontoState.cy) ontoState.cy.resize(); });
  });
  window.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    const layout = qs('#wb-ontology .onto-layout'); if (!layout) return;
    const layoutRect = layout.getBoundingClientRect();
    // Grid columns: [tree][divider][iconbar][canvas][divider][props]
    // If tree is collapsed, divider width is 0; math still uses layout left
    let w = e.clientX - layoutRect.left;
    const min = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--onto-tree-w-min'));
    const max = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--onto-tree-w-max'));
    w = Math.max(min, Math.min(max, w));
    document.documentElement.style.setProperty(panelWidthProp, w + 'px');
    try { localStorage.setItem('onto_tree_w', String(w)); } catch (_) { }
    if (ontoState.cy) ontoState.cy.resize();
  });
})();

// Properties panel resizer
(function () {
  const res = qs('#ontoPropsResizer');
  let dragging = false;
  if (!res) return;
  res.addEventListener('mousedown', () => dragging = true);
  window.addEventListener('mouseup', () => dragging = false);
  window.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    const layoutRect = qs('#wb-ontology .onto-layout')?.getBoundingClientRect();
    if (!layoutRect) return;
    let w = layoutRect.right - e.clientX;
    const min = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--onto-props-w-min'));
    const max = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--onto-props-w-max'));
    w = Math.max(min, Math.min(max, w));
    document.documentElement.style.setProperty('--onto-props-w', w + 'px');
    try { localStorage.setItem('onto_props_w', String(w)); } catch (_) { }
    if (ontoState.cy) ontoState.cy.resize();
  });
})();

async function renderTree(project) {
  activeProject = project && project.id ? project : null;
  // Reset active ontology when switching context or when no project
  activeOntologyIri = null;
  updateOntoGraphLabel();
  try { if (ontoState.cy) ontoState.cy.elements().remove(); } catch (_) { }
  // Restore per-project active ontology selection (label only)
  try {
    const pid = project && (project.id || project.project_id);
    const savedIri = localStorage.getItem(`onto_active_iri__${pid}`);
    if (savedIri) {
      activeOntologyIri = savedIri;
      updateOntoGraphLabel();
      // Ensure properties panel model name reflects the saved active ontology
      try {
        const labels = loadOntologyLabelMap(project);
        const pid2 = (project && (project.id || project.project_id)) ? (project.id || project.project_id) : 'default';
        const friendly = (labels[savedIri] && String(labels[savedIri]).trim()) || (savedIri.split('/').pop() || savedIri);
        // FIXED: Use ontology-specific localStorage keys consistently
        const ontologyKey = savedIri ? savedIri.split('/').pop() : 'default';
        const modelNameKey = `onto_model_name__${pid2}__${ontologyKey}`;
        const modelAttrsKey = `onto_model_attrs__${pid2}__${ontologyKey}`;

        localStorage.setItem(modelNameKey, friendly);
        let attrs = {};

        try { attrs = JSON.parse(localStorage.getItem(modelAttrsKey) || '{}'); } catch (_) { attrs = {}; }
        attrs.displayLabel = friendly;
        attrs.graphIri = savedIri;
        // Set namespace based on installation configuration
        attrs.namespace = iri;  // Use the actual graph IRI as namespace
        localStorage.setItem(modelAttrsKey, JSON.stringify(attrs));
        updatePropertiesPanelFromSelection();
      } catch (_) { }
      // Attempt to load saved canvas for this active IRI
      try {
        if (ontoState.cy) {
          ontoState.suspendAutosave = true;
          ontoState.cy.elements().remove();
          loadGraphFromLocal(savedIri);
          setTimeout(() => { ontoState.suspendAutosave = false; }, 50);
        }
      } catch (_) { }
    }
  } catch (_) { }
  const root = qs('#treeRoot');
  const makeItem = (id, label, iconCls, children = [], dataAttrs = {}) => {
    const hasChildren = children && children.length > 0;
    const li = document.createElement('li');
    li.setAttribute('role', 'treeitem');
    if (hasChildren) li.setAttribute('aria-expanded', 'true');
    li.dataset.nodeId = id;
    Object.keys(dataAttrs || {}).forEach(k => { li.dataset[k] = dataAttrs[k]; });

    const row = document.createElement('div');
    row.className = 'node-row';
    row.tabIndex = 0;
    row.onclick = async (e) => { selectNode(li); await handleTreeSelection(li); };
    row.onkeydown = (e) => handleKey(e, li);
    // Inline rename on double-click for ontology nodes
    row.ondblclick = (e) => {
      if (li.dataset.nodeType === 'ontology') {
        const current = (li.dataset.label || row.querySelector('.node-label')?.textContent || '').trim();
        const name = prompt('Rename ontology label', current);
        if (!name || name.trim() === current) return;
        try {
          const payload = { graph: li.dataset.iri, label: name.trim() };
          const token = localStorage.getItem(tokenKey);
          fetch('/api/ontologies/label', { method: 'PUT', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token }, body: JSON.stringify(payload) })
            .then(async (res) => {
              if (!res.ok) throw new Error('rename failed');
              const newLabel = name.trim();
              row.querySelector('.node-label').textContent = newLabel; li.dataset.label = newLabel; saveOntologyLabel(li.dataset.iri, newLabel);
              if (activeOntologyIri === li.dataset.iri) {
                const pid = project.id || project.project_id || 'default';
                // FIXED: Use ontology-specific localStorage keys consistently
                const ontologyKey = (li.dataset.iri || activeOntologyIri) ? (li.dataset.iri || activeOntologyIri).split('/').pop() : 'default';
                const modelNameKey = `onto_model_name__${pid}__${ontologyKey}`;
                const modelAttrsKey = `onto_model_attrs__${pid}__${ontologyKey}`;

                localStorage.setItem(modelNameKey, newLabel);
                try {
                  let attrs = {};

                  try { attrs = JSON.parse(localStorage.getItem(modelAttrsKey) || '{}'); } catch (_) { attrs = {}; }
                  attrs.displayLabel = newLabel;
                  // Ensure namespace matches the graph IRI
                  if (!attrs.namespace || attrs.namespace.endsWith('/ontology')) {
                    attrs.namespace = li.dataset.iri || activeOntologyIri;
                  }
                  localStorage.setItem(modelAttrsKey, JSON.stringify(attrs));
                } catch (_) { }
                updateOntoGraphLabel();
                // Immediately update properties panel model name
                try { updatePropertiesPanelFromSelection(); } catch (_) { }
                // Immediately reflect in Ontology tree view without a full tree reload
                try { refreshOntologyTree(); } catch (_) { }
              }
              // Avoid immediate server re-fetch that could race and overwrite the fresh label
            })
            .catch(() => { alert('Rename failed'); });
        } catch (_) { }
      }
    };

    const twist = document.createElement('span'); twist.className = 'twist';
    if (hasChildren) {
      twist.onclick = (e) => { e.stopPropagation(); toggleNode(li); };
    }
    row.appendChild(twist);

    const icon = document.createElement('span'); icon.className = 'node-icon ' + iconCls; row.appendChild(icon);
    const text = document.createElement('span'); text.className = 'node-label'; text.textContent = label; row.appendChild(text);
    li.appendChild(row);

    if (hasChildren) {
      const ul = document.createElement('ul'); ul.setAttribute('role', 'group');
      children.forEach(ch => ul.appendChild(ch));
      li.appendChild(ul);
    }
    return li;
  };

  const reqItems = ((project && project.requirements) || []).map((r, idx) => {
    const rid = r.id || `SP-${String(idx + 1).padStart(3, '0')}`;
    const label = rid; // ID only
    return makeItem(rid, label, 'req');
  });
  const docReqItems = (project && project.documents && project.documents.requirements ? project.documents.requirements : []).map(d => makeItem(d.id || d.name, d.name || d.id, 'docreq'));
  const docKnowItems = (project && project.documents && project.documents.knowledge ? project.documents.knowledge : []).map(d => makeItem(d.id || d.name, d.name || d.id, 'docknow'));
  const outItems = ((project && (project.artifacts || project.outputs)) || []).map(o => makeItem(o.id || o.name, o.name || o.id, 'out'));

  // Ontology tree: discover from Fuseki
  let ontologyNode = null;
  try {
    const pid = project && (project.id || project.project_id);
    const res = await fetch(`/api/ontologies${pid ? `?project=${encodeURIComponent(pid)}` : ''}`);
    const json = await res.json();
    const onts = Array.isArray(json.ontologies) ? json.ontologies : [];
    const labelsMap = loadOntologyLabelMap(project);
    const ontoItems = onts.map((o, idx) => {
      const serverLabel = (o.label && String(o.label).trim()) || '';
      const mapLabel = (labelsMap[o.graphIri] && String(labelsMap[o.graphIri]).trim()) || '';
      const displayLabel = mapLabel || serverLabel || o.graphIri;
      const isReference = o.is_reference || false;
      const referenceIndicator = isReference ? ' 📚' : '';
      const li = makeItem(
        `ontology-${idx}-${o.graphIri}`,
        displayLabel + referenceIndicator,
        'onto',
        [],
        { nodeType: 'ontology', iri: o.graphIri, label: displayLabel, isReference: isReference }
      );
      // Enable dragging this ontology into the Imports node
      const row = li.querySelector('.node-row');
      if (row) {
        row.setAttribute('draggable', 'true');
        row.addEventListener('dragstart', (ev) => {
          try { ev.dataTransfer.setData('text/graph-iri', o.graphIri); ev.dataTransfer.effectAllowed = 'copy'; } catch (_) { }
        });

        // Add context menu for ontology nodes (admin only)
        row.oncontextmenu = (ev) => {
          ev.preventDefault();
          console.log('🔍 Right-click detected on ontology node:', o.graphIri);

          const menu = qs('#ontologyContextMenu');
          if (!menu) {
            console.log('❌ Ontology context menu not found');
            return;
          }

          // Check if user is admin
          const user = JSON.parse(localStorage.getItem('user') || '{}');
          console.log('👤 Current user:', user);
          console.log('🔍 User is_admin:', user.is_admin);

          // Temporarily allow all users to test the context menu
          // if (!user.is_admin) {
          //   console.log('❌ User is not admin, context menu disabled');
          //   return;
          // }

          console.log('✅ Showing context menu (admin check temporarily disabled)');

          menu.style.display = 'block';
          menu.style.left = ev.pageX + 'px';
          menu.style.top = ev.pageY + 'px';

          const hide = () => {
            menu.style.display = 'none';
            document.removeEventListener('click', hide, { capture: true });
          };
          setTimeout(() => { document.addEventListener('click', hide, { capture: true }); }, 0);

          // Set up context menu actions
          const renameBtn = qs('#ontoRenameBtn');
          const toggleRefBtn = qs('#ontoToggleReferenceBtn');
          const deleteBtn = qs('#ontoDeleteBtn');

          if (renameBtn) {
            renameBtn.onclick = async () => {
              hide();
              const current = displayLabel;
              const name = prompt('Rename ontology label', current);
              if (!name || name.trim() === current) return;
              try {
                const payload = { graph: o.graphIri, label: name.trim() };
                const token = localStorage.getItem(tokenKey);
                const res = await fetch('/api/ontologies/label', {
                  method: 'PUT',
                  headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token },
                  body: JSON.stringify(payload)
                });
                if (res.ok) {
                  row.querySelector('.node-label').textContent = name.trim() + referenceIndicator;
                  li.dataset.label = name.trim();
                  saveOntologyLabel(o.graphIri, name.trim());
                  await renderTree(project);
                } else {
                  alert('Rename failed');
                }
              } catch (_) {
                alert('Rename failed');
              }
            };
          }

          if (toggleRefBtn) {
            const currentRefStatus = isReference;
            toggleRefBtn.textContent = currentRefStatus ? 'Remove Reference Status' : 'Mark as Reference';
            toggleRefBtn.onclick = async () => {
              hide();
              try {
                const payload = { graph: o.graphIri, is_reference: !currentRefStatus };
                const token = localStorage.getItem(tokenKey);
                const res = await fetch('/api/ontologies/reference', {
                  method: 'PUT',
                  headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token },
                  body: JSON.stringify(payload)
                });
                if (res.ok) {
                  await renderTree(project);
                } else {
                  alert('Failed to update reference status');
                }
              } catch (_) {
                alert('Failed to update reference status');
              }
            };
          }


          if (deleteBtn) {
            deleteBtn.onclick = async () => {
              hide();
              if (confirm(`Delete ontology "${displayLabel}"?`)) {
                try {
                  const token = localStorage.getItem(tokenKey);
                  const res = await fetch(`/api/ontologies?graph=${encodeURIComponent(o.graphIri)}`, {
                    method: 'DELETE',
                    headers: { Authorization: 'Bearer ' + token }
                  });
                  if (res.ok) {
                    // Clear local storage for this ontology
                    try {
                      localStorage.removeItem(storageKeyForGraph(o.graphIri));
                      console.log('🗑️ Cleared local storage for deleted ontology:', o.graphIri);
                    } catch (e) {
                      console.warn('Failed to clear local storage:', e);
                    }

                    await renderTree(project);
                    if (activeOntologyIri === o.graphIri) {
                      activeOntologyIri = null;
                      updateOntoGraphLabel();
                      ensureOntologyInitialized();
                      ontoState.cy?.elements().remove();
                      refreshOntologyTree();
                    }
                  } else {
                    alert('Delete failed');
                  }
                } catch (_) {
                  alert('Delete failed');
                }
              }
            };
          }
        };
      }
      // Initialize label map from server only if missing
      if (!mapLabel && serverLabel) {
        try { saveOntologyLabel(o.graphIri, serverLabel); } catch (_) { }
      }
      return li;
    });
    if (ontoItems.length) {
      ontologyNode = makeItem('ontology', 'Ontologies', 'folder', ontoItems);
    } else {
      // No ontologies: ensure empty state is shown
      activeOntologyIri = null;
      updateOntoGraphLabel();
      ontologyNode = makeItem('ontology', 'Ontologies', 'folder', []);
    }
  } catch (_) {
    // Network/SPARQL error: show a placeholder item
    ontologyNode = makeItem('ontology', 'Ontologies', 'folder', [
      makeItem('onto-error', 'Discovery unavailable', 'onto')
    ]);
  }

  const projectDisplay = (project && (project.name || project.id)) ? (project.name || project.id) : '';
  const projectInfo = makeItem('project-info', `Project: ${projectDisplay}`, 'folder');
  // Enable delete on main tree top node when project is selected
  try {
    const row = projectInfo.querySelector('.node-row');
    if (row && project && (project.id || project.project_id)) {
      // Click handler to open project information page
      row.onclick = (ev) => {
        ev.preventDefault();
        ev.stopPropagation();

        // Switch to project workbench
        const projectIcon = qs('#wb-project');
        if (projectIcon) {
          // Remove active class from all workbenches
          qsa('.workbench').forEach(wb => wb.classList.remove('active'));
          qsa('.icon').forEach(icon => icon.classList.remove('active'));

          // Add active class to project workbench
          projectIcon.classList.add('active');
          qs('#wb-project').classList.add('active');

          // Update localStorage and URL
          try {
            localStorage.setItem('active_workbench', 'project');
            const currentProjectId = localStorage.getItem('active_project_id');
            updateURL(currentProjectId, 'project');
          } catch (_) { }

          // Load project information
          loadProjectInfo();
        }
      };

      // Context menu binding
      row.oncontextmenu = (ev) => {
        ev.preventDefault();
        const menu = qs('#projectContextMenu'); if (!menu) return;
        menu.style.display = 'block';
        menu.style.left = ev.pageX + 'px';
        menu.style.top = ev.pageY + 'px';
        const hide = () => { menu.style.display = 'none'; document.removeEventListener('click', hide, { capture: true }); };
        setTimeout(() => { document.addEventListener('click', hide, { capture: true }); }, 0);
        const pid = project.id || project.project_id;
        const token = localStorage.getItem(tokenKey);
        const archiveBtn = qs('#projArchiveBtn');
        const deleteBtn = qs('#projDeleteBtn');
        const showArchivedBtn = qs('#projShowArchivedBtn');
        const renameBtn = qs('#projRenameBtn');
        if (renameBtn) renameBtn.onclick = async () => {
          try {
            const currentName = (project && (project.name || '')) || '';
            const newName = prompt('Rename project', currentName);
            if (!newName || newName.trim() === currentName) return;
            const res = await fetch(`/api/projects/${encodeURIComponent(pid)}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token },
              body: JSON.stringify({ name: newName.trim() })
            });
            if (res.ok) {
              // Verify via API that the rename persisted
              try {
                const vr = await fetch(`/api/projects/${encodeURIComponent(pid)}`, { headers: { Authorization: 'Bearer ' + token } });
                if (vr.ok) {
                  const vj = await vr.json();
                  const vproj = vj.project || vj;
                  const serverName = (vproj.name || vproj.project_name || '').trim();
                  if (serverName !== newName.trim()) {
                    alert('Rename saved but verification failed: expected "' + newName.trim() + '", got "' + serverName + '". UI will refresh.');
                  }
                } else {
                  const t = await vr.text().catch(() => String(vr.status));
                  alert('Rename saved, but verification request failed: ' + t);
                }
              } catch (_) {
                // Non-fatal verification error
              }
              await loadProjects();
            } else {
              const t = await res.text().catch(() => String(res.status));
              alert('Rename failed: ' + t);
            }
          } finally { hide(); }
        };
        if (archiveBtn) archiveBtn.onclick = async () => {
          try {
            const res = await fetch(`/api/projects/${encodeURIComponent(pid)}/archive`, { method: 'POST', headers: { Authorization: 'Bearer ' + token } });
            if (res.ok) { try { localStorage.removeItem('active_project_id'); } catch (_) { } await loadProjects(); }
            else { const t = await res.text().catch(() => String(res.status)); alert('Archive failed: ' + t); }
          } finally { hide(); }
        };
        if (deleteBtn) deleteBtn.onclick = async () => {
          try {
            if (!confirm('Delete this project? This does not delete external artifacts.')) return;
            const res = await fetch(`/api/projects/${encodeURIComponent(pid)}`, { method: 'DELETE', headers: { Authorization: 'Bearer ' + token } });
            if (res.ok) { try { localStorage.removeItem('active_project_id'); } catch (_) { } await loadProjects(); }
            else { const t = await res.text().catch(() => String(res.status)); alert('Delete failed: ' + t); }
          } finally { hide(); }
        };
        if (showArchivedBtn) showArchivedBtn.onclick = async () => {
          try {
            const res = await fetch('/api/projects?state=archived', { headers: { Authorization: 'Bearer ' + token } });
            const json = await res.json();
            const rows = (json.projects || []).map(p => ({ id: p.project_id || p.id, name: p.name || 'Project' })).filter(p => p.id);
            const overlay = document.createElement('div');
            overlay.style.position = 'fixed'; overlay.style.inset = '0'; overlay.style.background = 'rgba(0,0,0,0.4)'; overlay.style.zIndex = '9998';
            const panel = document.createElement('div'); panel.style.position = 'fixed'; panel.style.top = '20%'; panel.style.left = '50%'; panel.style.transform = 'translateX(-50%)'; panel.style.background = 'var(--panel)'; panel.style.border = '1px solid var(--border)'; panel.style.borderRadius = '12px'; panel.style.padding = '12px'; panel.style.minWidth = '420px'; panel.style.zIndex = '9999';
            panel.innerHTML = `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;"><strong>Archived Projects</strong><button id="archClose" class="btn">Close</button></div><div id="archList"></div>`;
            document.body.appendChild(overlay); document.body.appendChild(panel);
            const close = () => { try { document.body.removeChild(panel); document.body.removeChild(overlay); } catch (_) { } };
            panel.querySelector('#archClose').onclick = close; overlay.onclick = close;
            const listEl = panel.querySelector('#archList');
            if (!rows.length) { listEl.innerHTML = '<div class="muted">No archived projects.</div>'; return; }
            listEl.innerHTML = rows.map(r => `<div style="display:flex; justify-content:space-between; align-items:center; border:1px solid var(--border); border-radius:8px; padding:8px; margin-bottom:6px;"><span>${r.name}</span><div><button class="btn" data-restore="${r.id}">Restore</button></div></div>`).join('');
            listEl.addEventListener('click', async (e) => {
              const btn = e.target.closest('button[data-restore]'); if (!btn) return;
              const rid = btn.getAttribute('data-restore');
              const rr = await fetch(`/api/projects/${encodeURIComponent(rid)}/restore`, { method: 'POST', headers: { Authorization: 'Bearer ' + token } });
              if (rr.ok) {
                try { localStorage.setItem('active_project_id', rid); } catch (_) { }
                close();
                await loadProjects();
              } else {
                const t = await rr.text().catch(() => String(rr.status)); alert('Restore failed: ' + t);
              }
            });
          } finally { hide(); }
        };
      };
      row.onkeydown = async (e) => {
        if (e.key === 'Delete' || e.key === 'Backspace') {
          e.preventDefault();
          const pid = project.id || project.project_id;
          const token = localStorage.getItem(tokenKey);
          if (!confirm('Delete this project? This does not delete external artifacts.')) return;
          const res = await fetch(`/api/projects/${encodeURIComponent(pid)}`, { method: 'DELETE', headers: { Authorization: 'Bearer ' + token } });
          if (res.ok) {
            try { localStorage.removeItem('active_project_id'); } catch (_) { }
            await loadProjects();
          } else {
            const t = await res.text().catch(() => String(res.status));
            alert('Delete failed: ' + t);
          }
        }
      };
    }
  } catch (_) { }
  const docsReqNode = makeItem('documents-requirements', 'Requirements Documents', 'folder', docReqItems);
  const docsKnowNode = makeItem('documents-knowledge', 'Knowledge Documents', 'folder', docKnowItems);
  const docsChildren = [];
  if (docReqItems.length) docsChildren.push(docsReqNode);
  if (docKnowItems.length) docsChildren.push(docsKnowNode);
  const docsNode = makeItem('documents', 'Documents', 'folder', docsChildren);
  const reqNode = makeItem('requirements', 'Extracted Requirements', 'folder', reqItems);

  // Create new ODRAS-specific tree nodes
  const knowledgeNode = makeItem('knowledge', 'Knowledge', 'folder', []);

  // Analysis node with nested structure for Test → Validate → Release workflow
  const analysisDataNode = makeItem('analysis-data', 'Data', 'folder', []);
  const analysisModelsNode = makeItem('analysis-models', 'Models', 'folder', []);
  const analysisSimulationsNode = makeItem('analysis-simulations', 'Simulations', 'folder', []);
  const analysisNotebooksNode = makeItem('analysis-notebooks', 'Notebooks', 'folder', []);
  const analysisResultsNode = makeItem('analysis-results', 'Results', 'folder', []);
  const analysisTemplatesNode = makeItem('analysis-templates', 'Templates', 'folder', []);

  const analysisNode = makeItem('analysis', 'Analysis', 'folder', [
    analysisDataNode,
    analysisModelsNode,
    analysisSimulationsNode,
    analysisNotebooksNode,
    analysisResultsNode,
    analysisTemplatesNode
  ]);

  const eventsNode = makeItem('events', 'Events', 'folder', []);

  // Fetch DAS Actions - Assumptions
  let assumptionsNode = null;
  try {
    const pid = project && (project.id || project.project_id);
    if (pid) {
      const token = localStorage.getItem('authToken');

      const assumptionsRes = await fetch(`/api/das/project/${pid}/assumptions`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      if (assumptionsRes.ok) {
        const assumptionsData = await assumptionsRes.json();
        const assumptionItems = (assumptionsData.assumptions || []).map(a => {
          const truncated = a.content.length > 60 ? a.content.substring(0, 57) + '...' : a.content;
          return makeItem(a.id, truncated, 'assumption', [], {
            fullContent: a.content,
            status: a.status,
            createdAt: a.created_at
          });
        });
        assumptionsNode = makeItem('assumptions', 'Assumptions', 'folder', assumptionItems);
      } else {
        assumptionsNode = makeItem('assumptions', 'Assumptions', 'folder', []);
      }
    } else {
      assumptionsNode = makeItem('assumptions', 'Assumptions', 'folder', []);
    }
  } catch (e) {
    console.error('Could not load assumptions:', e);
    assumptionsNode = makeItem('assumptions', 'Assumptions', 'folder', []);
  }

  // Ensure we always have an assumptions node
  if (!assumptionsNode) {
    assumptionsNode = makeItem('assumptions', 'Assumptions', 'folder', []);
  }

  // Fetch DAS Actions - Artifacts (white papers, diagrams)
  let dasArtifactItems = [];
  try {
    const pid = project && (project.id || project.project_id);
    if (pid) {
      // Get files tagged as DAS artifacts
      const token = localStorage.getItem('authToken');

      const filesRes = await fetch(`/api/files?project_id=${pid}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (filesRes.ok) {
        const filesData = await filesRes.json();
        // Filter for DAS-generated artifacts
        const dasFiles = (filesData.files || []).filter(f =>
          f.tags && f.tags.generated_by === 'das'
        );
        dasArtifactItems = dasFiles.map(f => {
          const artifactItem = makeItem(f.file_id, f.filename, 'artifact', [], {
            fileId: f.file_id,
            artifactType: f.tags.artifact_type,
            createdAt: f.created_at
          });

          // Add click handler for viewing artifact
          const nodeRow = artifactItem.querySelector('.node-row');
          if (nodeRow) {
            nodeRow.onclick = (e) => {
              e.preventDefault();
              e.stopPropagation();
              showArtifactModal(f.file_id, f.filename, f.tags.artifact_type);
            };
            nodeRow.style.cursor = 'pointer';
            nodeRow.title = `Click to view ${f.tags.artifact_type}`;
          }

          return artifactItem;
        });
      }
    }
  } catch (e) {
    console.error('Could not load DAS artifacts:', e);
  }

  // Combine with existing artifacts for backward compatibility
  const allArtifactItems = [...dasArtifactItems, ...outItems];
  const outNode = makeItem('artifacts', 'Artifacts', 'folder', allArtifactItems);

  // Create horizontal separator
  const separator = document.createElement('li');
  separator.className = 'tree-separator';
  separator.innerHTML = '<div class="separator-line"></div>';

  root.innerHTML = '';
  // If no project, show minimal empty tree
  root.innerHTML = '';
  if (project && (project.id || project.project_id)) {
    // Show new ODRAS tree structure with nested Analysis, Assumptions, and separator before artifacts
    [projectInfo, ontologyNode, knowledgeNode, analysisNode, eventsNode, assumptionsNode, separator, outNode].filter(Boolean).forEach(n => root.appendChild(n));
  }

  // Auto-restore previously selected ontology for this project, if available
  try {
    const pid = project && (project.id || project.project_id);
    const savedIri = pid ? localStorage.getItem(`onto_active_iri__${pid}`) : null;
    const treeEl = qs('#treeRoot');
    if (savedIri && treeEl) {
      const li = Array.from(treeEl.querySelectorAll('li[role="treeitem"]')).find(el => el.dataset && el.dataset.iri === savedIri);
      if (li) {
        // Restore canvas first (if we have saved content), then select the ontology to sync panels
        try {
          if (ontoState.cy) {
            ontoState.suspendAutosave = true;
            ontoState.cy.elements().remove();
            loadGraphFromLocal(savedIri);
            setTimeout(() => { ontoState.suspendAutosave = false; }, 50);
          }
        } catch (_) { }
        selectNode(li);
        // Prevent workbench switching when restoring selection on load
        suppressWorkbenchSwitch = true;
        try { await handleTreeSelection(li); } finally { suppressWorkbenchSwitch = false; }
      } else {
        // Saved IRI no longer present; reset to empty state
        activeOntologyIri = null;
        updateOntoGraphLabel();
        try { if (ontoState.cy) ontoState.cy.elements().remove(); } catch (_) { }
        refreshOntologyTree();
      }
    } else {
      // No saved selection for this project
      activeOntologyIri = null;
      updateOntoGraphLabel();
      try { if (ontoState.cy) ontoState.cy.elements().remove(); } catch (_) { }
      refreshOntologyTree();
    }
  } catch (_) { }

  // Add plus button on Ontology section header (right side)
  try {
    const ontoSection = Array.from(root.children).find(li => li.querySelector('.node-label')?.textContent === 'Ontologies');
    const headerRow = ontoSection ? ontoSection.querySelector('.node-row') : null;
    if (headerRow && !headerRow.querySelector('.tree-add-btn')) {
      const addBtn = document.createElement('button');
      addBtn.className = 'btn tree-add-btn';
      addBtn.title = 'New Ontology';
      addBtn.textContent = '+';
      addBtn.style.marginLeft = '8px';
      addBtn.onclick = async (e) => {
        e.stopPropagation();
        if (!project || !(project.id || project.project_id)) { alert('Create a project first'); return; }

        // Check if user is admin
        const token = localStorage.getItem(tokenKey);
        let isAdmin = false;
        try {
          const userRes = await fetch('/api/auth/me', { headers: { Authorization: 'Bearer ' + token } });
          if (userRes.ok) {
            const user = await userRes.json();
            isAdmin = user.is_admin || false;
            console.log('User admin status:', isAdmin, user);
          }
        } catch (err) {
          console.error('Failed to get user info:', err);
        }

        // Create dialog for ontology creation
        const overlay = document.createElement('div');
        overlay.style.position = 'fixed';
        overlay.style.inset = '0';
        overlay.style.background = 'rgba(0,0,0,0.4)';
        overlay.style.zIndex = '9998';

        const panel = document.createElement('div');
        panel.style.position = 'fixed';
        panel.style.top = '30%';
        panel.style.left = '50%';
        panel.style.transform = 'translateX(-50%)';
        panel.style.background = 'var(--panel)';
        panel.style.border = '1px solid var(--border)';
        panel.style.borderRadius = '12px';
        panel.style.padding = '20px';
        panel.style.minWidth = '400px';
        panel.style.zIndex = '9999';

        panel.innerHTML = `
          <div style="margin-bottom:16px;">
            <h3 style="margin:0 0 16px 0;">Create or Import Ontology</h3>

            <!-- Creation/Import Mode Toggle -->
            <div style="margin-bottom:16px;">
              <div style="display:flex; gap:8px; margin-bottom:12px;">
                <button id="createMode" class="btn btn-primary" style="flex:1;">Create New</button>
                <button id="importMode" class="btn" style="flex:1;">Import from URL</button>
              </div>
            </div>

            <!-- Create New Ontology Section -->
            <div id="createSection">
              <div style="margin-bottom:12px;">
                <label style="display:block; margin-bottom:4px; font-weight:500;">Display Label:</label>
                <input type="text" id="ontoLabel" placeholder="Enter ontology label" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--input-bg); color:var(--text);" />
              </div>

              <div style="margin-bottom:12px;">
                <label style="display:block; margin-bottom:4px; font-weight:500;">Namespace (inherited from project):</label>
                <div id="ontoNamespaceDisplay" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--panel-2); color:var(--muted); font-family: monospace;">
                  Loading project namespace...
                </div>
                <div style="font-size:0.9em; color:var(--muted); margin-top:4px;">
                  Ontologies automatically inherit their project's namespace
                </div>
              </div>
              ${isAdmin ? `
              <div style="margin-bottom:16px;">
                <label style="display:flex; align-items:center; cursor:pointer;">
                  <input type="checkbox" id="isReference" style="margin-right:8px;" />
                  <span>Mark as Reference Ontology (Admin only)</span>
                </label>
                <div style="font-size:0.9em; color:var(--muted); margin-top:4px;">
                  Reference ontologies can be imported by other projects
                </div>
              </div>
              ` : ''}
            </div>

            <!-- Import from URL Section -->
            <div id="importSection" style="display:none;">
              <div style="margin-bottom:12px;">
                <label style="display:block; margin-bottom:4px; font-weight:500;">Ontology URL:</label>
                <input type="url" id="importUrl" placeholder="https://example.com/ontology.owl" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--input-bg); color:var(--text);" />
              </div>
              <div style="margin-bottom:12px;">
                <label style="display:block; margin-bottom:4px; font-weight:500;">Display Name:</label>
                <input type="text" id="importName" placeholder="Enter display name" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--input-bg); color:var(--text);" />
              </div>
              <div style="margin-bottom:12px;">
                <label style="display:block; margin-bottom:4px; font-weight:500;">Display Label:</label>
                <input type="text" id="importLabel" placeholder="Enter display label" style="width:100%; padding:8px; border:1px solid var(--border); border-radius:4px; background:var(--input-bg); color:var(--text);" />
              </div>
              ${isAdmin ? `
              <div style="margin-bottom:16px;">
                <label style="display:flex; align-items:center; cursor:pointer;">
                  <input type="checkbox" id="importIsReference" style="margin-right:8px;" />
                  <span>Mark as Reference Ontology (Admin only)</span>
                </label>
                <div style="font-size:0.9em; color:var(--muted); margin-top:4px;">
                  Reference ontologies can be imported by other projects
                </div>
              </div>
              ` : ''}
            </div>

            <div style="display:flex; justify-content:flex-end; gap:8px;">
              <button id="cancelOnto" class="btn" style="background: var(--muted);">Cancel</button>
              <button id="createOnto" class="btn btn-primary">Create</button>
              <button id="importOnto" class="btn btn-primary" style="display:none;">Import</button>
            </div>
          </div>
        `;

        document.body.appendChild(overlay);
        document.body.appendChild(panel);

        const close = () => {
          try {
            document.body.removeChild(panel);
            document.body.removeChild(overlay);
          } catch (_) { }
        };

        panel.querySelector('#cancelOnto').onclick = close;
        overlay.onclick = close;

        // Mode toggle handlers
        panel.querySelector('#createMode').onclick = () => {
          panel.querySelector('#createMode').className = 'btn btn-primary';
          panel.querySelector('#importMode').className = 'btn';
          panel.querySelector('#createSection').style.display = 'block';
          panel.querySelector('#importSection').style.display = 'none';
          panel.querySelector('#createOnto').style.display = 'inline-block';
          panel.querySelector('#importOnto').style.display = 'none';
        };

        panel.querySelector('#importMode').onclick = () => {
          panel.querySelector('#importMode').className = 'btn btn-primary';
          panel.querySelector('#createMode').className = 'btn';
          panel.querySelector('#createSection').style.display = 'none';
          panel.querySelector('#importSection').style.display = 'block';
          panel.querySelector('#createOnto').style.display = 'none';
          panel.querySelector('#importOnto').style.display = 'inline-block';
        };

        // Load current project's namespace
        loadCurrentProjectNamespace(panel.querySelector('#ontoNamespaceDisplay'));

        panel.querySelector('#createOnto').onclick = async () => {
          const labelInput = panel.querySelector('#ontoLabel');
          const disp = labelInput.value.trim();

          if (!disp) {
            alert('Please enter a label for the ontology');
            return;
          }

          // Check if project has a namespace
          const currentProjectId = localStorage.getItem('active_project_id');
          if (!currentProjectId) {
            alert('No project selected - select a project first');
            return;
          }

          const isReference = isAdmin && panel.querySelector('#isReference').checked;
          const base = slugify(disp) || `ontology-${Date.now()}`;
          const label = disp;

          try {
            const pid2 = project.id || project.project_id;
            const body = {
              project: pid2,
              name: base,
              label
            };
            if (isReference) {
              body.is_reference = true;
            }

            console.log('🔧 Creating ontology with project namespace inheritance:', body);
            console.log('🔧 Frontend sending project ID:', pid2, 'from project object:', project);

            const res = await fetch('/api/ontologies', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token },
              body: JSON.stringify(body)
            });

            if (!res.ok) {
              const msg = await res.text().catch(() => String(res.status));
              alert('Create ontology failed: ' + msg);
              return;
            }

            const created = await res.json();
            if (created && created.graphIri) {
              try { saveOntologyLabel(created.graphIri, created.label || label); } catch (_) { }
            }

            close();
            await renderTree(project);

            // Ensure label is shown and select the created ontology (guard for valid response)
            if (created && created.graphIri) {
              const newRoot = qs('#treeRoot');
              const li = Array.from(newRoot.querySelectorAll('li[role="treeitem"]')).find(el => el.dataset && el.dataset.iri === created.graphIri);
              // Update top node label immediately
              try {
                const ontoTop = qs('#ontoTreeRoot .onto-node-label');
                if (ontoTop) ontoTop.textContent = created.label || label;
              } catch (_) { }
              if (li) {
                const lbl = li.querySelector('.node-label'); if (lbl) lbl.textContent = created.label || label;
                li.dataset.label = created.label || label;
                selectNode(li);
                await handleTreeSelection(li);
              } else {
                // Fallback: set selection and force refresh display
                activeOntologyIri = created.graphIri;
                updateOntoGraphLabel();
                refreshOntologyTree();
              }
            }
          } catch (err) {
            alert('Failed to create ontology: ' + err.message);
          }
        };

        // Import from URL handler
        panel.querySelector('#importOnto').onclick = async () => {
          const urlInput = panel.querySelector('#importUrl');
          const nameInput = panel.querySelector('#importName');
          const labelInput = panel.querySelector('#importLabel');

          const url = urlInput.value.trim();
          const name = nameInput.value.trim();
          const label = labelInput.value.trim();

          if (!url) {
            alert('Please enter an ontology URL');
            return;
          }

          if (!name) {
            alert('Please enter a display name');
            return;
          }

          if (!label) {
            alert('Please enter a display label');
            return;
          }

          const isReference = isAdmin && panel.querySelector('#importIsReference').checked;

          try {
            const response = await fetch('/api/ontologies/import-url', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
              },
              body: JSON.stringify({
                url: url,
                project_id: (activeProject && (activeProject.id || activeProject.project_id)) ? (activeProject.id || activeProject.project_id) : 'default',
                name: name,
                label: label,
                is_reference: isReference
              })
            });

            if (!response.ok) {
              const error = await response.text();
              throw new Error(error);
            }

            const result = await response.json();
            toast(`Successfully imported ontology: ${result.label}`);
            close();
            await renderTree(project);

            // Select the imported ontology
            if (result.graph_iri) {
              const newRoot = qs('#treeRoot');
              const li = Array.from(newRoot.querySelectorAll('li[role="treeitem"]')).find(el => el.dataset && el.dataset.iri === result.graph_iri);
              if (li) {
                const lbl = li.querySelector('.node-label');
                if (lbl) lbl.textContent = result.label || label;
                li.dataset.label = result.label || label;
                selectNode(li);
                await handleTreeSelection(li);
              }
            }

          } catch (error) {
            console.error('URL import error:', error);

            // Check if it's a duplicate ontology error
            if (error.message && (
              error.message.includes('duplicate key value violates unique constraint') ||
              error.message.includes('ontologies_registry_graph_iri_key') ||
              error.message.includes('already exists')
            )) {
              toast('This ontology has already been imported. Each ontology can only be imported once per project.', true);
            } else {
              toast(`Failed to import ontology: ${error.message}`, true);
            }
          }
        };

        // Focus the input
        setTimeout(() => {
          panel.querySelector('#ontoLabel').focus();
        }, 100);
      };
      headerRow.appendChild(addBtn);
    }
  } catch (_) { }

  // Handle Delete key for ontology deletion
  root.addEventListener('keydown', async (e) => {
    if (e.key === 'Delete' || e.keyCode === 46) {
      const sel = root.querySelector('.node-row.selected');
      if (!sel) return;
      const li = sel.closest('li[role="treeitem"]');
      if (!li || li.dataset.nodeType !== 'ontology') return;
      const iri = li.dataset.iri;
      if (!iri) return;
      try {
        const url = `/api/ontologies?graph=${encodeURIComponent(iri)}`;
        const token = localStorage.getItem(tokenKey);
        const res = await fetch(url, { method: 'DELETE', headers: { Authorization: 'Bearer ' + token } });
        if (res.ok) {
          await renderTree(project);
          if (activeOntologyIri === iri) { activeOntologyIri = null; updateOntoGraphLabel(); ensureOntologyInitialized(); ontoState.cy?.elements().remove(); refreshOntologyTree(); }
        }
      } catch (_) { }
    }
  });
}

async function refreshGraphSummary() {
  const el = qs('#graphSummary'); if (!el) return;
  el.textContent = 'Loading summary...';
  try {
    const res = await fetch('/api/ontology/summary');
    const json = await res.json();
    if (json.rows) {
      el.innerHTML = json.rows.map(r => `<div class="row"><span class="muted">${r.type}</span> — ${r.count}</div>`).join('') || '<div class="muted">No data</div>';
    } else {
      el.textContent = json.error || 'No data';
    }
  } catch (e) { el.textContent = 'Error loading summary'; }
}
(function () {
  const btnS = () => qs('#btnRefreshSummary');
  const btnQ = () => qs('#btnRunSparql');
  document.addEventListener('click', async (e) => {
    if (e.target === btnS()) {
      refreshGraphSummary();
    } else if (e.target === btnQ()) {
      const q = (qs('#sparqlInput')?.value) || '';
      const st = qs('#sparqlStatus'); const out = qs('#sparqlResult');
      st.textContent = 'Running...'; out.textContent = '';
      try {
        const res = await fetch('/api/ontology/sparql', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: q }) });
        const json = await res.json();
        if (res.ok) { out.textContent = JSON.stringify(json, null, 2); st.textContent = 'OK'; }
        else { out.textContent = JSON.stringify(json, null, 2); st.textContent = 'Error'; }
      } catch (err) { out.textContent = String(err); st.textContent = 'Error'; }
    }
  });
})();

async function refreshOntologyTree() {
  const root = qs('#ontoTreeRoot');
  if (!root || !ontoState.cy) return;

  // Filter nodes based on visibility settings
  const classes = ontoState.cy.nodes().filter(n => {
    const nodeType = n.data('type') || 'class';
    const isImported = n.hasClass('imported');

    // Always show classes in tree regardless of visibility state - visibility only affects canvas
    return !isImported && nodeType === 'class';
  });

  const dataProperties = ontoState.cy.nodes().filter(n => {
    const nodeType = n.data('type') || 'class';
    const isImported = n.hasClass('imported');

    // Always show data properties in tree regardless of visibility state
    return !isImported && nodeType === 'dataProperty';
  });

  const importedClasses = ontoState.cy.nodes().filter(n => {
    const nodeType = n.data('type') || 'class';
    const isImported = n.hasClass('imported');

    // Always show imported classes in tree regardless of visibility state
    return isImported && nodeType === 'class';
  });

  const notes = ontoState.cy.nodes().filter(n => {
    const nodeType = n.data('type') || '';
    const isImported = n.hasClass('imported');

    // Always show notes in tree regardless of visibility state - don't check isVisible
    return !isImported && nodeType === 'note';
  });
  // Simple grouping: Classes as top-level; edges shown under a "Relationships" group per class
  root.innerHTML = '';
  const makeItem = (label, expanded = true, children = []) => {
    const li = document.createElement('li');
    li.setAttribute('role', 'treeitem');
    if (children.length) li.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    const row = document.createElement('div'); row.className = 'onto-node-row';
    row.tabIndex = 0;
    const twist = document.createElement('span'); twist.className = 'onto-twist'; if (children.length) twist.onclick = (e) => { e.stopPropagation(); li.setAttribute('aria-expanded', li.getAttribute('aria-expanded') === 'true' ? 'false' : 'true'); };
    const text = document.createElement('span'); text.className = 'onto-node-label'; text.textContent = label;
    row.appendChild(twist); row.appendChild(text); li.appendChild(row);

    // Add click handler for tree item selection
    row.onclick = async (e) => {
      // Don't trigger if clicking on a button (like visibility toggle)
      if (e.target.tagName === 'BUTTON') return;
      console.log('🔍 Tree item clicked:', li.dataset.nodeType, li.dataset.nodeId);
      selectNode(li);
      await handleTreeSelection(li);
    };
    row.onkeydown = (e) => {
      const ENTER = 13, SPACE = 32;
      if (e.keyCode === ENTER || e.keyCode === SPACE) {
        selectNode(li);
        handleTreeSelection(li).catch(console.error);
        e.preventDefault();
      }
    };

    if (children.length) {
      const ul = document.createElement('ul'); ul.setAttribute('role', 'group');
      children.forEach(c => ul.appendChild(c));
      li.appendChild(ul);
    }
    return li;
  };
  const items = [];
  classes.forEach(cls => {
    const label = cls.data('label') || cls.id();
    const outEdges = cls.outgoers('edge').filter(e => {
      // Always show edges in tree regardless of visibility state
      return true;
    });
    const rels = outEdges.map(e => {
      const other = e.target();
      const pred = e.data('predicate') || 'relatedTo';
      const type = e.data('type') || 'objectProperty';
      const item = makeItem(`${pred} → ${(other.data('label') || other.id())} (${type})`, false, []);
      // Set edge data attributes for tree selection
      item.dataset.edgeId = e.id();
      item.dataset.nodeType = 'edge';
      return item;
    });
    const classItem = makeItem(label, false, rels);
    // Set node data attributes for tree selection
    classItem.dataset.nodeId = cls.id();
    classItem.dataset.nodeType = 'class';

    // Add visibility toggle for individual classes
    const row = classItem.querySelector('.onto-node-row');
    if (row) {
      const visibilityBtn = document.createElement('button');
      visibilityBtn.className = 'class-visibility-toggle';
      visibilityBtn.title = 'Toggle visibility';
      visibilityBtn.innerHTML = '👁';
      visibilityBtn.style.cssText = `
        background: none;
        border: none;
        color: var(--muted);
        cursor: pointer;
        padding: 2px 4px;
        margin-left: 4px;
        border-radius: 3px;
        font-size: 12px;
      `;

      // Set initial visibility state based on saved element visibility or global state
      const nodeId = cls.id();
      let isVisible = cls.visible();
      if (ontoState.elementVisibility.hasOwnProperty(nodeId)) {
        isVisible = ontoState.elementVisibility[nodeId];
      }
      visibilityBtn.style.opacity = isVisible ? '1' : '0.3';

      visibilityBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const node = ontoState.cy.$(`#${cls.id()}`);
        if (node.length > 0) {
          if (node.visible()) {
            node.hide();
            visibilityBtn.style.opacity = '0.3';
            // Save individual element visibility
            if (activeOntologyIri) {
              ontoState.elementVisibility[cls.id()] = false;
              saveElementVisibility(activeOntologyIri, ontoState.elementVisibility);
            }
          } else {
            node.show();
            visibilityBtn.style.opacity = '1';
            // Save individual element visibility
            if (activeOntologyIri) {
              ontoState.elementVisibility[cls.id()] = true;
              saveElementVisibility(activeOntologyIri, ontoState.elementVisibility);
            }
          }
          // Update properties panel if this node was selected
          updatePropertiesPanelFromSelection();
        }
      });

      row.appendChild(visibilityBtn);
    }

    items.push(classItem);
  });

  // Add data properties
  if (dataProperties.length) {
    const dataPropertyChildren = dataProperties.map(dp => {
      const item = makeItem(dp.data('label') || dp.id(), false, []);
      item.dataset.nodeId = dp.id();
      item.dataset.nodeType = 'dataProperty';

      // Add visibility toggle for data properties
      const row = item.querySelector('.onto-node-row');
      if (row) {
        const visibilityBtn = document.createElement('button');
        visibilityBtn.className = 'class-visibility-toggle';
        visibilityBtn.title = 'Toggle visibility';
        visibilityBtn.innerHTML = '👁';
        visibilityBtn.style.cssText = `
          background: none;
          border: none;
          color: var(--muted);
          cursor: pointer;
          padding: 2px 4px;
          margin-left: 4px;
          border-radius: 3px;
          font-size: 12px;
        `;

        // Set initial visibility state based on saved element visibility or global state
        const nodeId = dp.id();
        let isVisible = dp.visible();
        if (ontoState.elementVisibility.hasOwnProperty(nodeId)) {
          isVisible = ontoState.elementVisibility[nodeId];
        }
        visibilityBtn.style.opacity = isVisible ? '1' : '0.3';

        visibilityBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          const node = ontoState.cy.$(`#${dp.id()}`);
          if (node.length > 0) {
            if (node.visible()) {
              node.hide();
              visibilityBtn.style.opacity = '0.3';
              // Save individual element visibility
              if (activeOntologyIri) {
                ontoState.elementVisibility[dp.id()] = false;
                saveElementVisibility(activeOntologyIri, ontoState.elementVisibility);
              }
            } else {
              node.show();
              visibilityBtn.style.opacity = '1';
              // Save individual element visibility
              if (activeOntologyIri) {
                ontoState.elementVisibility[dp.id()] = true;
                saveElementVisibility(activeOntologyIri, ontoState.elementVisibility);
              }
            }
            // Update properties panel if this node was selected
            updatePropertiesPanelFromSelection();
          }
        });

        row.appendChild(visibilityBtn);
      }

      return item;
    });
    items.push(makeItem('Data Properties', true, dataPropertyChildren));
  }

  if (importedClasses.length) {
    const importedChildren = importedClasses.map(cls => {
      const item = makeItem((cls.data('label') || cls.id()) + ' (imported)', false, []);
      item.dataset.nodeId = cls.id();
      item.dataset.nodeType = 'class';

      // Add visibility toggle for imported classes
      const row = item.querySelector('.onto-node-row');
      if (row) {
        const visibilityBtn = document.createElement('button');
        visibilityBtn.className = 'class-visibility-toggle';
        visibilityBtn.title = 'Toggle visibility';
        visibilityBtn.innerHTML = '👁';
        visibilityBtn.style.cssText = `
          background: none;
          border: none;
          color: var(--muted);
          cursor: pointer;
          padding: 2px 4px;
          margin-left: 4px;
          border-radius: 3px;
          font-size: 12px;
        `;

        // Set initial visibility state based on saved element visibility or global state
        const nodeId = cls.id();
        let isVisible = cls.visible();
        if (ontoState.elementVisibility.hasOwnProperty(nodeId)) {
          isVisible = ontoState.elementVisibility[nodeId];
        }
        visibilityBtn.style.opacity = isVisible ? '1' : '0.3';

        visibilityBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          const node = ontoState.cy.$(`#${CSS.escape(cls.id())}`);
          if (node.length > 0) {
            if (node.visible()) {
              node.hide();
              visibilityBtn.style.opacity = '0.3';
              // Save individual element visibility
              if (activeOntologyIri) {
                ontoState.elementVisibility[cls.id()] = false;
                saveElementVisibility(activeOntologyIri, ontoState.elementVisibility);
              }
            } else {
              node.show();
              visibilityBtn.style.opacity = '1';
              // Save individual element visibility
              if (activeOntologyIri) {
                ontoState.elementVisibility[cls.id()] = true;
                saveElementVisibility(activeOntologyIri, ontoState.elementVisibility);
              }
            }
            // Update properties panel if this node was selected
            updatePropertiesPanelFromSelection();
          }
        });

        row.appendChild(visibilityBtn);
      }

      return item;
    });
    items.push(makeItem('Imported Classes', true, importedChildren));
  }
  if (notes.length) {
    const noteChildren = notes.map(n => {
      const item = makeItem(n.data('label') || n.id(), false, []);
      item.dataset.nodeId = n.id();
      item.dataset.nodeType = 'note';

      // Add visibility toggle for notes
      const row = item.querySelector('.onto-node-row');
      if (row) {
        const visibilityBtn = document.createElement('button');
        visibilityBtn.className = 'class-visibility-toggle';
        visibilityBtn.title = 'Toggle visibility';
        visibilityBtn.innerHTML = '👁';
        visibilityBtn.style.cssText = `
          background: none;
          border: none;
          color: var(--muted);
          cursor: pointer;
          padding: 2px 4px;
          margin-left: 4px;
          border-radius: 3px;
          font-size: 12px;
        `;

        // Set initial visibility state based on saved element visibility or global state
        const nodeId = n.id();
        let isVisible = n.visible();
        if (ontoState.elementVisibility.hasOwnProperty(nodeId)) {
          isVisible = ontoState.elementVisibility[nodeId];
        }
        visibilityBtn.style.opacity = isVisible ? '1' : '0.3';

        visibilityBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          const node = ontoState.cy.$(`#${n.id()}`);
          if (node.length > 0) {
            if (node.visible()) {
              node.hide();
              visibilityBtn.style.opacity = '0.3';
              // Save individual element visibility
              if (activeOntologyIri) {
                ontoState.elementVisibility[n.id()] = false;
                saveElementVisibility(activeOntologyIri, ontoState.elementVisibility);
              }
            } else {
              node.show();
              visibilityBtn.style.opacity = '1';
              // Save individual element visibility
              if (activeOntologyIri) {
                ontoState.elementVisibility[n.id()] = true;
                saveElementVisibility(activeOntologyIri, ontoState.elementVisibility);
              }
            }
            // Update properties panel if this node was selected
            updatePropertiesPanelFromSelection();
          }
        });

        row.appendChild(visibilityBtn);
      }

      return item;
    });
    items.push(makeItem('Notes', true, noteChildren));
  }

  // Add Named Views section
  const namedViews = await loadNamedViews(activeOntologyIri);
  if (namedViews.length > 0 || true) { // Always show section even if empty
    const viewChildren = namedViews.map(view => {
      const isActive = ontoState.activeNamedView === view.id;
      const displayName = isActive ? `● ${view.name}` : view.name;
      const item = makeItem(displayName, false, []);
      item.dataset.viewId = view.id;
      item.dataset.nodeType = 'namedView';

      // Style active view differently
      if (isActive) {
        const label = item.querySelector('.onto-node-label');
        if (label) {
          label.style.color = '#60a5fa';
          label.style.fontWeight = 'bold';
        }
      }

      // Add view management buttons with SVG icons
      const row = item.querySelector('.onto-node-row');
      if (row) {
        // Add rename button with edit SVG icon
        const renameBtn = document.createElement('button');
        renameBtn.className = 'class-visibility-toggle';
        renameBtn.title = 'Rename view';
        renameBtn.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="width: 12px; height: 12px;">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
        `;
        renameBtn.style.cssText = `
          background: none;
          border: none;
          color: var(--muted);
          cursor: pointer;
          padding: 2px 4px;
          margin-left: 4px;
          border-radius: 3px;
        `;

        renameBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          renameNamedView(view.id);
        });

        // Add delete button with trash SVG icon
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'class-visibility-toggle';
        deleteBtn.title = 'Delete view';
        deleteBtn.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="width: 12px; height: 12px;">
            <polyline points="3,6 5,6 21,6"/>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            <line x1="10" y1="11" x2="10" y2="17"/>
            <line x1="14" y1="11" x2="14" y2="17"/>
          </svg>
        `;
        deleteBtn.style.cssText = `
          background: none;
          border: none;
          color: var(--danger);
          cursor: pointer;
          padding: 2px 4px;
          margin-left: 4px;
          border-radius: 3px;
        `;

        deleteBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          deleteNamedView(view.id);
        });

        row.appendChild(renameBtn);
        row.appendChild(deleteBtn);
      }

      return item;
    });

    // Add the Named Views section with buttons
    const viewsSection = makeItem('Named Views', true, viewChildren);
    const viewsRow = viewsSection.querySelector('.onto-node-row');
    if (viewsRow) {
      // Add Return button (only visible when a view is active)
      if (ontoState.activeNamedView) {
        const returnBtn = document.createElement('button');
        returnBtn.className = 'btn tree-add-btn';
        returnBtn.title = 'Return to Original View';
        returnBtn.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="width: 12px; height: 12px;">
            <polyline points="9,14 4,9 9,4"/>
            <path d="M20,20v-7a4,4 0 0,0-4-4H4"/>
          </svg>
        `;
        returnBtn.style.marginLeft = '8px';
        returnBtn.style.fontSize = '12px';
        returnBtn.style.padding = '2px 6px';
        returnBtn.style.minWidth = '20px';
        returnBtn.style.height = '20px';
        returnBtn.style.color = '#60a5fa';
        returnBtn.onclick = (e) => {
          e.stopPropagation();
          restoreOriginalState();
        };

        viewsRow.appendChild(returnBtn);
      }

      // Add + button for creating new views
      const addViewBtn = document.createElement('button');
      addViewBtn.className = 'btn tree-add-btn';
      addViewBtn.title = 'Save Current View';
      addViewBtn.textContent = '+';
      addViewBtn.style.marginLeft = '8px';
      addViewBtn.style.fontSize = '12px';
      addViewBtn.style.padding = '2px 6px';
      addViewBtn.style.minWidth = '20px';
      addViewBtn.style.height = '20px';
      addViewBtn.onclick = (e) => {
        e.stopPropagation();
        createNamedView();
      };

      viewsRow.appendChild(addViewBtn);
    }

    items.push(viewsSection);
  }

  const ul = document.createElement('ul'); ul.setAttribute('role', 'group');
  items.forEach(i => ul.appendChild(i));
  // Root level
  const rootItem = document.createElement('li'); rootItem.setAttribute('role', 'treeitem'); rootItem.setAttribute('aria-expanded', 'true');
  const row = document.createElement('div'); row.className = 'onto-node-row';
  const twist = document.createElement('span'); twist.className = 'onto-twist'; twist.onclick = (e) => { e.stopPropagation(); rootItem.setAttribute('aria-expanded', rootItem.getAttribute('aria-expanded') === 'true' ? 'false' : 'true'); };
  const text = document.createElement('span'); text.className = 'onto-node-label';
  (function () {
    try {
      const labels = loadOntologyLabelMap(activeProject);
      let modelName = 'Ontology';
      const pid = (activeProject && (activeProject.id || activeProject.project_id)) ? (activeProject.id || activeProject.project_id) : 'default';
      const scopedName = localStorage.getItem(`onto_model_name__${pid}`) || '';
      if (scopedName.trim()) modelName = scopedName.trim();
      else if (activeOntologyIri) {
        modelName = (labels[activeOntologyIri] && String(labels[activeOntologyIri]).trim()) || (activeOntologyIri.split('/').pop() || 'Ontology');
      }
      text.textContent = modelName;
    } catch (_) { text.textContent = 'Ontology'; }
  })();
  // Add visibility toggle button to the ontology root node
  const visibilityBtn = document.createElement('button');
  visibilityBtn.className = 'iconbtn';
  visibilityBtn.id = 'ontoVisibilityToggle';
  visibilityBtn.title = 'Toggle Visibility';
  visibilityBtn.style.marginLeft = 'auto';
  visibilityBtn.innerHTML = `
    <svg viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  `;

  // Add click event listener for visibility toggle
  visibilityBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    showVisibilityMenu();
  });

  row.appendChild(twist); row.appendChild(text); row.appendChild(visibilityBtn); rootItem.appendChild(row); rootItem.appendChild(ul);
  // (Do not delete projects here; project deletion is handled in the main tree top node in renderTree)
  root.innerHTML = '';
  root.appendChild(rootItem);

  // Imports node specific to current ontology
  try {
    const importsKey = 'onto_imports__' + encodeURIComponent(activeOntologyIri || '');
    const imports = JSON.parse(localStorage.getItem(importsKey) || '[]');
    const importsRoot = document.createElement('li'); importsRoot.setAttribute('role', 'treeitem'); importsRoot.setAttribute('aria-expanded', 'true');
    const row = document.createElement('div'); row.className = 'onto-node-row';
    const tw = document.createElement('span'); tw.className = 'onto-twist';
    const lbl = document.createElement('span'); lbl.className = 'onto-node-label'; lbl.textContent = 'Imports';

    // Add + button for adding reference ontologies
    const addBtn = document.createElement('button');
    addBtn.className = 'btn tree-add-btn';
    addBtn.title = 'Add Reference Ontology';
    addBtn.textContent = '+';
    addBtn.style.marginLeft = '8px';
    addBtn.style.fontSize = '12px';
    addBtn.style.padding = '2px 6px';
    addBtn.style.minWidth = '20px';
    addBtn.style.height = '20px';
    addBtn.onclick = async (e) => {
      e.stopPropagation();
      console.log('➕ Add Reference Ontology button clicked');
      await showReferenceOntologySelector();
    };

    // Add collapse/expand all button (hidden for now)
    const collapseBtn = document.createElement('button');
    collapseBtn.className = 'btn tree-add-btn';
    collapseBtn.title = 'Collapse/Expand All Imports';
    collapseBtn.textContent = '⊞';
    collapseBtn.style.marginLeft = '4px';
    collapseBtn.style.fontSize = '12px';
    collapseBtn.style.padding = '2px 6px';
    collapseBtn.style.minWidth = '20px';
    collapseBtn.style.height = '20px';
    collapseBtn.style.display = 'none'; // Hidden for now
    collapseBtn.onclick = (e) => {
      e.stopPropagation();
      toggleAllImportsCollapse();
    };

    row.appendChild(tw);
    row.appendChild(lbl);
    row.appendChild(addBtn);
    row.appendChild(collapseBtn);
    importsRoot.appendChild(row);

    const ul = document.createElement('ul'); ul.setAttribute('role', 'group');
    function removeImport(iri) {
      try {
        console.log('🔍 Removing import:', iri);
        const key = 'onto_imports__' + encodeURIComponent(activeOntologyIri || '');
        const curr = new Set(JSON.parse(localStorage.getItem(key) || '[]'));
        if (curr.has(iri)) {
          curr.delete(iri);
          localStorage.setItem(key, JSON.stringify(Array.from(curr)));
          console.log('🔍 Import removed, refreshing tree');
          refreshOntologyTree();
        }
      } catch (err) {
        console.error('🔍 Error removing import:', err);
      }
    }
    async function friendlyImportName(iri) {
      try {
        const q = `PREFIX owl: <http://www.w3.org/2002/07/owl#>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\nSELECT ?label WHERE { GRAPH <${iri}> { <${iri}> a owl:Ontology . OPTIONAL { <${iri}> rdfs:label ?label } } }`;
        const res = await fetch('/api/ontology/sparql', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: q }) });
        if (!res.ok) throw new Error('sparql');
        const json = await res.json();
        const b = json.results && json.results.bindings && json.results.bindings[0];
        const lbl = b && b.label && b.label.value;
        return (lbl && lbl.trim()) || (iri.split('/').pop() || iri);
      } catch (_) { return iri.split('/').pop() || iri; }
    }
    async function importEquivCount(importIri) {
      try {
        if (!ontoState.cy) {
          console.log('🔍 No cytoscape instance for equivalence counting');
          return 0;
        }
        const norm = s => String(s || '').trim().toLowerCase();

        // Get base classes from current Cytoscape graph (local storage)
        const baseClasses = ontoState.cy.nodes().filter(n => (n.data('type') || 'class') === 'class' && !n.hasClass('imported'));
        console.log('🔍 Base classes found:', baseClasses.length);
        const baseByLabel = new Map();
        baseClasses.forEach(n => {
          const label = n.data('label') || n.id();
          const normalized = norm(label);
          baseByLabel.set(normalized, n);
          console.log('🔍 Base class details - ID:', n.id(), 'Label:', label, 'Normalized:', normalized);
        });
        console.log('🔍 Base classes by label:', Array.from(baseByLabel.keys()));

        // Get imported classes from local storage for the imported ontology
        const pid = (activeProject && (activeProject.id || activeProject.project_id)) ? (activeProject.id || activeProject.project_id) : 'default';
        const importKey = `onto_graph__${pid}__` + encodeURIComponent(importIri);
        let importData = localStorage.getItem(importKey);

        // TEMPORARY: Clear cached data with generic labels to force fresh reload
        if (importData) {
          const cachedData = JSON.parse(importData);
          const hasGenericLabels = cachedData.nodes && cachedData.nodes.some(node =>
            node.data && node.data.label && node.data.label.match(/^Class \d+$/)
          );
          if (hasGenericLabels) {
            console.log('🔍 Clearing cached data with generic labels to force fresh reload');
            localStorage.removeItem(importKey);
            importData = null;
          }
        }

        if (!importData) {
          console.log('🔍 No local storage data found for import, attempting to load from API:', importIri);
          try {
            // Try to load the imported ontology data from API
            const token = localStorage.getItem(tokenKey);
            const apiUrl = `/api/ontology/?graph=${encodeURIComponent(importIri)}`;
            const response = await fetch(apiUrl, {
              headers: token ? { 'Authorization': `Bearer ${token}` } : {}
            });

            if (response.ok) {
              const ontologyData = await response.json();
              console.log('🔍 Loaded imported ontology from API:', ontologyData);
              console.log('🔍 API response structure - classes:', ontologyData.classes);
              console.log('🔍 API response structure - object_properties:', ontologyData.object_properties);
              console.log('🔍 API response data property:', ontologyData.data);
              if (ontologyData.data) {
                console.log('🔍 Data.classes:', ontologyData.data.classes);
                console.log('🔍 Data.object_properties:', ontologyData.data.object_properties);
                console.log('🔍 Full data structure:', JSON.stringify(ontologyData.data, null, 2));
              }

              // Convert to Cytoscape format and save to local storage
              // Use a simpler conversion since we don't have rich metadata
              // The API response has the data nested in a 'data' property
              const actualOntologyData = ontologyData.data || ontologyData;
              console.log('🔍 Actual ontology data being passed to convertOntologyToCytoscape:', actualOntologyData);
              console.log('🔍 actualOntologyData.classes:', actualOntologyData.classes);
              const cytoscapeData = convertOntologyToCytoscape(actualOntologyData);
              console.log('🔍 Converted cytoscape data:', cytoscapeData);
              const storageData = {
                nodes: cytoscapeData.nodes || [],
                edges: cytoscapeData.edges || [],
                timestamp: Date.now(),
                source: 'api'
              };

              localStorage.setItem(importKey, JSON.stringify(storageData));
              importData = JSON.stringify(storageData);
              console.log('🔍 Saved imported ontology data to local storage');
            } else {
              console.log('🔍 Failed to load imported ontology from API:', response.status);
              return 0;
            }
          } catch (err) {
            console.error('🔍 Error loading imported ontology:', err);
            return 0;
          }
        } else {
          // Check if cached data is empty and force reload
          const cachedData = JSON.parse(importData);
          if (cachedData.nodes && cachedData.nodes.length === 0 && cachedData.edges && cachedData.edges.length === 0) {
            console.log('🔍 Cached data is empty, forcing reload from API:', importIri);
            try {
              const token = localStorage.getItem(tokenKey);
              const apiUrl = `/api/ontology/?graph=${encodeURIComponent(importIri)}`;
              const response = await fetch(apiUrl, {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {}
              });

              if (response.ok) {
                const ontologyData = await response.json();
                console.log('🔍 Reloaded imported ontology from API:', ontologyData);
                console.log('🔍 Reload API response structure - classes:', ontologyData.classes);
                console.log('🔍 Reload API response structure - object_properties:', ontologyData.object_properties);

                // Convert to Cytoscape format and save to local storage
                // The API response has the data nested in a 'data' property
                const actualOntologyData = ontologyData.data || ontologyData;
                console.log('🔍 Reload actual ontology data being passed to convertOntologyToCytoscape:', actualOntologyData);
                console.log('🔍 Reload actualOntologyData.classes:', actualOntologyData.classes);
                const cytoscapeData = convertOntologyToCytoscape(actualOntologyData);
                console.log('🔍 Reload converted cytoscape data:', cytoscapeData);
                const storageData = {
                  nodes: cytoscapeData.nodes || [],
                  edges: cytoscapeData.edges || [],
                  timestamp: Date.now(),
                  source: 'api'
                };

                localStorage.setItem(importKey, JSON.stringify(storageData));
                importData = JSON.stringify(storageData);
                console.log('🔍 Reloaded and saved imported ontology data to local storage');
              } else {
                console.log('🔍 Failed to reload imported ontology from API:', response.status);
              }
            } catch (err) {
              console.error('🔍 Error reloading imported ontology:', err);
            }
          }
        }

        const importOntology = JSON.parse(importData);
        const importNodes = importOntology.nodes || [];
        const importClasses = importNodes.filter(node => (node.data && node.data.type === 'class') || !node.data?.type);
        console.log('🔍 Import classes found in local storage:', importClasses.length);

        const matched = new Set();
        importClasses.forEach(node => {
          const label = node.data?.label || node.data?.id || node.id;
          const key = norm(label);
          console.log('🔍 Checking match:', key, 'in base classes:', baseByLabel.has(key));
          console.log('🔍 Import class details - ID:', node.data?.id || node.id, 'Label:', label, 'Key:', key);
          if (baseByLabel.has(key)) {
            matched.add(node.data?.id || node.id);
            console.log('🔍 ✅ MATCH FOUND for:', key);
          } else {
            console.log('🔍 ❌ No match for:', key, 'Available base classes:', Array.from(baseByLabel.keys()));
          }
        });
        console.log('🔍 Matched classes:', matched.size);
        return matched.size;
      } catch (err) {
        console.error('🔍 Error in importEquivCount:', err);
        return 0;
      }
    }
    const visibleSet = loadVisibleImports(activeOntologyIri);
    imports.forEach(async g => {
      const li = document.createElement('li'); li.setAttribute('role', 'treeitem'); li.dataset.importIri = g;
      const r = document.createElement('div'); r.className = 'onto-node-row'; r.tabIndex = 0;
      const cb = document.createElement('input'); cb.type = 'checkbox'; cb.style.marginRight = '6px'; cb.checked = visibleSet.has(g);
      const t = document.createElement('span'); t.className = 'onto-twist';
      const l = document.createElement('span'); l.className = 'onto-node-label';
      const name = await friendlyImportName(g);
      const cnt = await importEquivCount(g);
      l.textContent = `${name}${cnt ? ` (${cnt})` : ''}`;
      cb.addEventListener('change', async () => {
        try {
          console.log('🔍 Checkbox changed for import:', g, 'checked:', cb.checked);
          const vis = loadVisibleImports(activeOntologyIri);
          if (cb.checked) vis.add(g); else vis.delete(g);
          saveVisibleImports(activeOntologyIri, vis);
          console.log('🔍 Visible imports updated:', Array.from(vis));
          await overlayImportsRefresh();
        } catch (err) {
          console.error('🔍 Error handling import checkbox change:', err);
          // Revert the checkbox state if there was an error
          cb.checked = !cb.checked;
        }
      });
      // Add collapse/expand button (hidden for now)
      const collapseBtn = document.createElement('button');
      collapseBtn.className = 'btn tree-add-btn';
      collapseBtn.title = 'Collapse/Expand Import';
      collapseBtn.textContent = ontoState.collapsedImports.has(g) ? '⊞' : '⊟';
      collapseBtn.style.marginLeft = '8px';
      collapseBtn.style.fontSize = '12px';
      collapseBtn.style.padding = '2px 6px';
      collapseBtn.style.minWidth = '20px';
      collapseBtn.style.height = '20px';
      collapseBtn.style.display = 'none'; // Hidden for now
      collapseBtn.onclick = (e) => {
        e.stopPropagation();
        toggleImportCollapse(g);
        // Update button text
        collapseBtn.textContent = ontoState.collapsedImports.has(g) ? '⊞' : '⊟';
      };

      r.onclick = (e) => { Array.from(ul.querySelectorAll('.onto-node-row')).forEach(n => n.classList.remove('selected')); r.classList.add('selected'); };
      r.onkeydown = (e) => { const key = e.key || e.code; if (key === 'Delete' || key === 'Backspace') { e.preventDefault(); removeImport(g); } };
      r.appendChild(cb); r.appendChild(t); r.appendChild(l); r.appendChild(collapseBtn);
      li.appendChild(r); ul.appendChild(li);
    });
    importsRoot.appendChild(ul);
    root.appendChild(importsRoot);
    // Enable drop to import
    row.addEventListener('dragover', (e) => { e.preventDefault(); });
    row.addEventListener('drop', async (e) => {
      e.preventDefault();
      const draggedIri = e.dataTransfer.getData('text/graph-iri');
      if (!draggedIri) return;
      const list = new Set(imports);
      if (!list.has(draggedIri)) { list.add(draggedIri); localStorage.setItem(importsKey, JSON.stringify(Array.from(list))); refreshOntologyTree(); }
      // Overlay imported classes (placeholder: we only list; loading remote triples is OW-2)
    });
  } catch (_) { }
}

// (empty-state banner removed)

// Attribute templates for different object types
const attributeTemplates = {
  class: {
    // Standard ontological properties
    comment: { type: 'textarea', label: 'Comment (rdfs:comment)', placeholder: 'Description of the class' },
    definition: { type: 'textarea', label: 'Definition (skos:definition)', placeholder: 'Formal definition of the class' },
    example: { type: 'textarea', label: 'Example (skos:example)', placeholder: 'Usage example' },
    identifier: { type: 'text', label: 'Identifier (dc:identifier)', placeholder: 'Unique identifier' },
    subclassOf: { type: 'text', label: 'Subclass of (rdfs:subClassOf)', placeholder: 'Parent class IRI' },
    subclass_of: { type: 'text', label: 'Subclass of (rdfs:subClassOf)', placeholder: 'Parent class IRI' },
    equivalentClass: { type: 'text', label: 'Equivalent Class (owl:equivalentClass)', placeholder: 'Equivalent class IRI' },
    disjointWith: { type: 'text', label: 'Disjoint With (owl:disjointWith)', placeholder: 'Disjoint class IRI' },
    // Metadata properties
    creator: { type: 'text', label: 'Creator (dc:creator)', placeholder: 'Created by', readonly: true },
    created_date: { type: 'date', label: 'Created Date (dc:created)', placeholder: 'Creation date', readonly: true },
    created_timestamp: { type: 'text', label: 'Created Timestamp', placeholder: 'ISO timestamp', readonly: true },
    last_modified_by: { type: 'text', label: 'Last Modified By (dc:contributor)', placeholder: 'Modified by', readonly: true },
    last_modified_date: { type: 'date', label: 'Last Modified Date (dcterms:modified)', placeholder: 'Modification date', readonly: true },
    last_modified_timestamp: { type: 'text', label: 'Last Modified Timestamp', placeholder: 'ISO timestamp', readonly: true },
    // Custom properties
    priority: { type: 'select', label: 'Priority (odras:priority)', options: ['High', 'Medium', 'Low'], placeholder: 'Select priority' },
    status: { type: 'select', label: 'Status (odras:status)', options: ['Draft', 'Review', 'Approved', 'Deprecated'], placeholder: 'Select status' }
  },
  objectProperty: {
    // Standard ontological properties
    comment: { type: 'textarea', label: 'Comment (rdfs:comment)', placeholder: 'Description of the property' },
    definition: { type: 'textarea', label: 'Definition (skos:definition)', placeholder: 'Formal definition of the property' },
    example: { type: 'textarea', label: 'Example (skos:example)', placeholder: 'Usage example' },
    identifier: { type: 'text', label: 'Identifier (dc:identifier)', placeholder: 'Unique identifier' },
    domain: { type: 'text', label: 'Domain (rdfs:domain)', placeholder: 'Source class IRI' },
    range: { type: 'text', label: 'Range (rdfs:range)', placeholder: 'Target class IRI' },
    inverseOf: { type: 'text', label: 'Inverse Of (owl:inverseOf)', placeholder: 'Inverse property IRI' },
    subPropertyOf: { type: 'text', label: 'Sub Property Of (rdfs:subPropertyOf)', placeholder: 'Parent property IRI' },
    equivalentProperty: { type: 'text', label: 'Equivalent Property (owl:equivalentProperty)', placeholder: 'Equivalent property IRI' },
    propertyType: { type: 'text', label: 'Property Type (rdf:type)', placeholder: 'Property characteristics (e.g., TransitiveProperty)' },
    // Metadata properties
    creator: { type: 'text', label: 'Creator (dc:creator)', placeholder: 'Created by', readonly: true },
    created_date: { type: 'date', label: 'Created Date (dc:created)', placeholder: 'Creation date', readonly: true },
    created_timestamp: { type: 'text', label: 'Created Timestamp', placeholder: 'ISO timestamp', readonly: true },
    last_modified_by: { type: 'text', label: 'Last Modified By (dc:contributor)', placeholder: 'Modified by', readonly: true },
    last_modified_date: { type: 'date', label: 'Last Modified Date (dcterms:modified)', placeholder: 'Modification date', readonly: true },
    last_modified_timestamp: { type: 'text', label: 'Last Modified Timestamp', placeholder: 'ISO timestamp', readonly: true },
    // Custom properties
    functional: { type: 'checkbox', label: 'Functional', placeholder: 'Is this a functional property?' },
    inverse_functional: { type: 'checkbox', label: 'Inverse Functional', placeholder: 'Is this inverse functional?' }
  },
  dataProperty: {
    // Standard ontological properties
    comment: { type: 'textarea', label: 'Comment (rdfs:comment)', placeholder: 'Description of the property' },
    definition: { type: 'textarea', label: 'Definition (skos:definition)', placeholder: 'Formal definition of the property' },
    example: { type: 'textarea', label: 'Example (skos:example)', placeholder: 'Usage example' },
    identifier: { type: 'text', label: 'Identifier (dc:identifier)', placeholder: 'Unique identifier' },
    domain: { type: 'text', label: 'Domain (rdfs:domain)', placeholder: 'Source class IRI' },
    range: { type: 'select', label: 'Range (rdfs:range)', options: ['xsd:string', 'xsd:integer', 'xsd:float', 'xsd:boolean', 'xsd:dateTime'], placeholder: 'Data type' },
    subPropertyOf: { type: 'text', label: 'Sub Property Of (rdfs:subPropertyOf)', placeholder: 'Parent property IRI' },
    equivalentProperty: { type: 'text', label: 'Equivalent Property (owl:equivalentProperty)', placeholder: 'Equivalent property IRI' },
    // Metadata properties
    creator: { type: 'text', label: 'Creator (dc:creator)', placeholder: 'Created by', readonly: true },
    created_date: { type: 'date', label: 'Created Date (dc:created)', placeholder: 'Creation date', readonly: true },
    created_timestamp: { type: 'text', label: 'Created Timestamp', placeholder: 'ISO timestamp', readonly: true },
    last_modified_by: { type: 'text', label: 'Last Modified By (dc:contributor)', placeholder: 'Modified by', readonly: true },
    last_modified_date: { type: 'date', label: 'Last Modified Date (dcterms:modified)', placeholder: 'Modification date', readonly: true },
    last_modified_timestamp: { type: 'text', label: 'Last Modified Timestamp', placeholder: 'ISO timestamp', readonly: true },
    // Custom properties
    functional: { type: 'checkbox', label: 'Functional', placeholder: 'Is this a functional property?' }
  },
  note: {
    noteType: { type: 'select', label: 'Note Type (dc:type)', options: ['Note', 'Warning', 'Issue', 'Todo', 'Info', 'Success', 'Question'], placeholder: 'Select note type' },
    content: { type: 'textarea', label: 'Content (rdfs:comment)', placeholder: 'Note content' },
    // Metadata properties
    creator: { type: 'text', label: 'Creator (dc:creator)', placeholder: 'Created by', readonly: true },
    created_date: { type: 'date', label: 'Created Date (dc:created)', placeholder: 'Creation date', readonly: true },
    created_timestamp: { type: 'text', label: 'Created Timestamp', placeholder: 'ISO timestamp', readonly: true },
    last_modified_by: { type: 'text', label: 'Last Modified By (dc:contributor)', placeholder: 'Modified by', readonly: true },
    last_modified_date: { type: 'date', label: 'Last Modified Date (dcterms:modified)', placeholder: 'Modification date', readonly: true },
    last_modified_timestamp: { type: 'text', label: 'Last Modified Timestamp', placeholder: 'ISO timestamp', readonly: true },
    // Legacy fields for backward compatibility
    author: { type: 'text', label: 'Author', placeholder: 'Note author', readonly: true }
  },
  model: {
    // Standard ontological properties
    comment: { type: 'textarea', label: 'Comment (rdfs:comment)', placeholder: 'Description of the ontology' },
    definition: { type: 'textarea', label: 'Definition (skos:definition)', placeholder: 'Formal definition of the ontology' },
    version: { type: 'text', label: 'Version (owl:versionInfo)', placeholder: 'Ontology version' },
    namespace: { type: 'text', label: 'Namespace', placeholder: 'Base namespace URI' },
    imports: { type: 'textarea', label: 'Imports (owl:imports)', placeholder: 'Enter ontology URIs (one per line):\nhttps://example.com/ontology1\nhttps://example.com/ontology2', rows: 4 }
  }
};

// Get current username synchronously for metadata
function getCurrentUsername() {
  try {
    // First try the simple username storage (most reliable)
    const username = localStorage.getItem('odras_user');
    if (username && typeof username === 'string' && username.trim() !== '') {
      return username.trim();
    }

    // Try the full user object
    const userObj = localStorage.getItem('user');
    if (userObj) {
      const user = JSON.parse(userObj);
      if (user.username && typeof user.username === 'string') {
        return user.username;
      }
    }

    // Fallback to parsing the userMenu text
    const userMenu = document.querySelector('#userMenu');
    if (userMenu && userMenu.textContent) {
      const menuText = userMenu.textContent.trim();
      // Remove " (admin)" suffix if present
      const cleanUsername = menuText.replace(/\s*\(admin\)\s*$/, '').trim();
      if (cleanUsername && cleanUsername !== '') {
        return cleanUsername;
      }
    }

    return 'system';
  } catch (e) {
    console.error('Error getting current username:', e);
    return 'system';
  }
}

// Ontology metadata management functions
function getCurrentTimestamp() {
  return new Date().toISOString();
}

function getCurrentDate() {
  return new Date().toISOString().split('T')[0]; // YYYY-MM-DD format
}

function addCreationMetadata(attrs = {}) {
  const currentUser = getCurrentUsername();
  const timestamp = getCurrentTimestamp();

  return {
    ...attrs,
    creator: currentUser,
    created_date: getCurrentDate(),
    created_timestamp: timestamp,
    last_modified_by: currentUser,
    last_modified_date: getCurrentDate(),
    last_modified_timestamp: timestamp
  };
}

function updateModificationMetadata(attrs = {}) {
  const currentUser = getCurrentUsername();
  const timestamp = getCurrentTimestamp();

  return {
    ...attrs,
    last_modified_by: currentUser,
    last_modified_date: getCurrentDate(),
    last_modified_timestamp: timestamp
  };
}

// Named views persistence
// Load named views from backend API instead of localStorage
async function loadNamedViews(baseIri) {
  if (!baseIri) return [];

  try {
    const response = await authenticatedFetch(`/api/ontology/named-views?graph=${encodeURIComponent(baseIri)}`);
    if (response.ok) {
      const result = await response.json();
      return result.data || [];
    } else {
      console.warn('Failed to load named views from backend, falling back to empty array');
      return [];
    }
  } catch (error) {
    console.warn('Error loading named views from backend:', error);
    return [];
  }
}

// Save named views to backend API instead of localStorage  
async function saveNamedViews(baseIri, views) {
  if (!baseIri) return;

  try {
    const response = await authenticatedFetch(`/api/ontology/named-views?graph=${encodeURIComponent(baseIri)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(views || [])
    });

    if (response.ok) {
      const result = await response.json();
      console.log('✅ Named views saved to backend:', result.message);
    } else {
      console.error('Failed to save named views to backend:', response.status, response.statusText);
    }
  } catch (error) {
    console.error('Error saving named views to backend:', error);
  }
}

// Named view data structure functions
function captureCurrentView(name) {
  if (!ontoState.cy || !activeOntologyIri) return null;

  const currentUser = getCurrentUsername();
  const timestamp = getCurrentTimestamp();

  // Capture individual node positions for complete layout snapshot
  const nodePositions = {};
  ontoState.cy.nodes().forEach(node => {
    nodePositions[node.id()] = {
      x: node.position().x,
      y: node.position().y
    };
  });

  return {
    id: `view_${Date.now()}`,
    name: name,
    creator: currentUser,
    created_date: getCurrentDate(),
    created_timestamp: timestamp,
    // Complete canvas state (layout snapshot)
    zoom: ontoState.cy.zoom(),
    pan: ontoState.cy.pan(),
    nodePositions: nodePositions, // Individual node positions for true snapshot
    // Visibility state
    visibilityState: { ...ontoState.visibilityState },
    elementVisibility: { ...ontoState.elementVisibility },
    collapsedImports: Array.from(ontoState.collapsedImports),
    // Import visibility state - which imports are visible (checked in tree)
    visibleImports: Array.from(loadVisibleImports(activeOntologyIri))
  };
}

function restoreView(view) {
  if (!ontoState.cy || !view) return;

  // Restore visibility states
  ontoState.visibilityState = { ...view.visibilityState };
  ontoState.elementVisibility = { ...view.elementVisibility };
  ontoState.collapsedImports = new Set(view.collapsedImports || []);

  // Restore import visibility - set which imports should be visible
  if (view.visibleImports && activeOntologyIri) {
    const visibleImportsSet = new Set(view.visibleImports);
    saveVisibleImports(activeOntologyIri, visibleImportsSet);
  }

  // Apply visibility to canvas
  updateCanvasVisibility();

  // Refresh imports overlay to apply import visibility changes
  overlayImportsRefresh().then(() => {
    // Restore individual node positions for complete layout snapshot
    if (view.nodePositions) {
      ontoState.cy.nodes().forEach(node => {
        const savedPosition = view.nodePositions[node.id()];
        if (savedPosition) {
          node.position({
            x: savedPosition.x,
            y: savedPosition.y
          });
        }
      });
      console.log('🔍 Restored node positions from named view');
    }

    // After positions are restored, restore canvas position and zoom
    ontoState.cy.animate({
      zoom: view.zoom || 1,
      pan: view.pan || { x: 0, y: 0 }
    }, {
      duration: 500
    });
  });

  // Refresh tree to reflect all visibility changes
  refreshOntologyTree();

  // Save current states to localStorage
  if (activeOntologyIri) {
    saveVisibilityState(activeOntologyIri, ontoState.visibilityState);
    saveElementVisibility(activeOntologyIri, ontoState.elementVisibility);
    saveCollapsedImports(activeOntologyIri, ontoState.collapsedImports);
  }

  // Mark this view as active and refresh tree to show indicator
  ontoState.activeNamedView = view.id;
  refreshOntologyTree();
}

function restoreOriginalState() {
  if (!ontoState.beforeViewState) return;

  // Restore the state from before any named view was applied
  const beforeState = ontoState.beforeViewState;

  // Restore visibility states
  ontoState.visibilityState = { ...beforeState.visibilityState };
  ontoState.elementVisibility = { ...beforeState.elementVisibility };
  ontoState.collapsedImports = new Set(beforeState.collapsedImports || []);

  // Restore import visibility
  if (beforeState.visibleImports && activeOntologyIri) {
    const visibleImportsSet = new Set(beforeState.visibleImports);
    saveVisibleImports(activeOntologyIri, visibleImportsSet);
  }

  // Apply visibility to canvas
  updateCanvasVisibility();

  // Refresh imports overlay
  overlayImportsRefresh().then(() => {
    // Restore individual node positions for original state
    if (beforeState.nodePositions) {
      ontoState.cy.nodes().forEach(node => {
        const savedPosition = beforeState.nodePositions[node.id()];
        if (savedPosition) {
          node.position({
            x: savedPosition.x,
            y: savedPosition.y
          });
        }
      });
      console.log('🔍 Restored original node positions');
    }

    // Restore canvas position and zoom
    ontoState.cy.animate({
      zoom: beforeState.zoom || 1,
      pan: beforeState.pan || { x: 0, y: 0 }
    }, {
      duration: 500
    });
  });

  // Refresh tree
  refreshOntologyTree();

  // Save restored states to localStorage
  if (activeOntologyIri) {
    saveVisibilityState(activeOntologyIri, ontoState.visibilityState);
    saveElementVisibility(activeOntologyIri, ontoState.elementVisibility);
    saveCollapsedImports(activeOntologyIri, ontoState.collapsedImports);
  }

  // Clear the active view state
  ontoState.activeNamedView = null;
  ontoState.beforeViewState = null;
}

// Named view management functions
async function createNamedView() {
  if (!activeOntologyIri) return;

  const name = prompt('Enter a name for this view:');
  if (!name || name.trim() === '') return;

  const view = captureCurrentView(name.trim());
  if (!view) return;

  const views = await loadNamedViews(activeOntologyIri);
  views.push(view);
  await saveNamedViews(activeOntologyIri, views);

  refreshOntologyTree();
  console.log('🔍 Created named view:', name, 'with visible imports:', view.visibleImports);
}

async function renameNamedView(viewId) {
  if (!activeOntologyIri) return;

  const views = await loadNamedViews(activeOntologyIri);
  const view = views.find(v => v.id === viewId);
  if (!view) return;

  const newName = prompt('Enter new name for view:', view.name);
  if (!newName || newName.trim() === '' || newName.trim() === view.name) return;

  view.name = newName.trim();
  await saveNamedViews(activeOntologyIri, views);

  await refreshOntologyTree();
  console.log('🔍 Renamed view to:', newName);
}

async function deleteNamedView(viewId) {
  if (!activeOntologyIri) return;

  const views = await loadNamedViews(activeOntologyIri);
  const view = views.find(v => v.id === viewId);
  if (!view) return;

  if (!confirm(`Delete view "${view.name}"?`)) return;

  const updatedViews = views.filter(v => v.id !== viewId);
  await saveNamedViews(activeOntologyIri, updatedViews);

  await refreshOntologyTree();
  console.log('🔍 Deleted view:', view.name);
}

// Note type styling configuration
function getNoteTypeStyle(noteType) {
  const styles = {
    'Note': {
      backgroundColor: '#2a1f0a',
      borderColor: '#8b5a1e',
      textColor: '#f5e6cc',
      symbol: '📝'
    },
    'Warning': {
      backgroundColor: '#2d1b0f',
      borderColor: '#d97706',
      textColor: '#fbbf24',
      symbol: '⚠️'
    },
    'Issue': {
      backgroundColor: '#2d0f0f',
      borderColor: '#dc2626',
      textColor: '#fca5a5',
      symbol: '❗'
    },
    'Todo': {
      backgroundColor: '#1e1b2d',
      borderColor: '#7c3aed',
      textColor: '#c4b5fd',
      symbol: '✅'
    },
    'Info': {
      backgroundColor: '#0f1a2d',
      borderColor: '#2563eb',
      textColor: '#93c5fd',
      symbol: 'ℹ️'
    },
    'Success': {
      backgroundColor: '#0f2d1a',
      borderColor: '#16a34a',
      textColor: '#86efac',
      symbol: '✨'
    },
    'Question': {
      backgroundColor: '#2d1a0f',
      borderColor: '#ea580c',
      textColor: '#fdba74',
      symbol: '❓'
    }
  };

  return styles[noteType] || styles['Note'];
}

function getTypeDisplayName(type) {
  const typeMap = {
    'class': 'Class',
    'objectProperty': 'Object Property',
    'dataProperty': 'Data Property',
    'note': 'Note',
    'model': 'Model'
  };
  return typeMap[type] || 'Class';
}

function updatePropertiesPanelFromSelection() {
  const form = qs('#ontoPropsForm'); if (!form || !ontoState.cy) return;
  const sel = ontoState.cy.$(':selected');
  const nameEl = qs('#propName');
  const typeValueEl = qs('#propTypeValue');

  let currentAttrs = {};
  let objectType = 'class';

  if (sel.length === 1 && sel[0].isNode()) {
    const n = sel[0];
    const isImported = n.hasClass('imported');
    nameEl.value = n.data('label') || n.id();
    nameEl.disabled = isImported; // Disable name editing for imported elements
    const nodeType = n.data('type') || 'class';
    typeValueEl.textContent = getTypeDisplayName(nodeType) + (isImported ? ' (Imported)' : '');
    currentAttrs = n.data('attrs') || {};
    objectType = nodeType;

    // Show positioning section for nodes
    const positioningSection = qs('#positioningSection');
    if (positioningSection) {
      positioningSection.style.display = 'block';
      updatePositionInputs(); // Populate current position
    }

    // Show inheritance fields for class nodes
    const parentClassesGroup = qs('#parentClassesGroup');
    const abstractGroup = qs('#abstractGroup');
    if (nodeType === 'class') {
      // Show parent classes selection
      if (parentClassesGroup) {
        parentClassesGroup.style.display = 'block';
        populateParentClasses().catch(console.error);

        // Populate current parent selections if any
        const currentParents = currentAttrs.subclass_of || [];
        const parentSelect = qs('#propParentClasses');
        if (parentSelect && Array.isArray(currentParents)) {
          setTimeout(() => {
            Array.from(parentSelect.options).forEach(option => {
              option.selected = currentParents.includes(option.value);
            });
          }, 100); // Small delay to allow population
        }
      }

      // Show abstract class checkbox
      if (abstractGroup) {
        abstractGroup.style.display = 'block';
        const abstractCheckbox = qs('#propIsAbstract');
        if (abstractCheckbox) {
          abstractCheckbox.checked = !!currentAttrs.is_abstract;
        }
      }
    } else {
      // Hide inheritance fields for non-class nodes
      if (parentClassesGroup) parentClassesGroup.style.display = 'none';
      if (abstractGroup) abstractGroup.style.display = 'none';
    }

    // Lazy load additional metadata for imported ontologies
    if (activeOntologyIri && activeOntologyIri.includes('/onto/') && !currentAttrs.definition) {
      loadAdditionalMetadataForElement(n.id(), activeOntologyIri);
    }
  } else if (sel.length === 1 && sel[0].isEdge()) {
    const e = sel[0];
    nameEl.value = e.data('predicate') || e.id();
    const edgeType = e.data('type') || 'objectProperty';
    typeValueEl.textContent = getTypeDisplayName(edgeType);
    currentAttrs = e.data('attrs') || {};

    // Show/hide SHACL constraints section based on edge type
    const shaclSection = qs('#shaclConstraintsSection');
    if (shaclSection) {
      if (edgeType === 'objectProperty' || edgeType === 'dataProperty') {
        shaclSection.style.display = 'block';

        // Show/hide appropriate subsections
        const multiplicitySubsection = qs('#multiplicitySubsection');
        const datatypeSubsection = qs('#datatypeSubsection');
        const enumerationSubsection = qs('#enumerationSubsection');

        if (edgeType === 'objectProperty') {
          // Object properties: show multiplicity and enumeration, hide datatype
          if (multiplicitySubsection) multiplicitySubsection.style.display = 'block';
          if (datatypeSubsection) datatypeSubsection.style.display = 'none';
          if (enumerationSubsection) enumerationSubsection.style.display = 'block';
          updateMultiplicityFields(e);
          updateEnumerationFields(e);
        } else if (edgeType === 'dataProperty') {
          // Datatype properties: show datatype and enumeration, hide multiplicity
          if (multiplicitySubsection) multiplicitySubsection.style.display = 'none';
          if (datatypeSubsection) datatypeSubsection.style.display = 'block';
          if (enumerationSubsection) enumerationSubsection.style.display = 'block';
          updateDatatypeFields(e);
          updateEnumerationFields(e);
        }

        // Always update constraint summary
        updateAllConstraintsDisplay(e);
      } else {
        shaclSection.style.display = 'none';
      }
    }

    // Hide positioning section for edges
    const positioningSection = qs('#positioningSection');
    if (positioningSection) {
      positioningSection.style.display = 'none';
    }

    // Hide inheritance fields for edges
    const parentClassesGroup = qs('#parentClassesGroup');
    const abstractGroup = qs('#abstractGroup');
    if (parentClassesGroup) parentClassesGroup.style.display = 'none';
    if (abstractGroup) abstractGroup.style.display = 'none';

    // Lazy load additional metadata for imported ontologies
    if (activeOntologyIri && activeOntologyIri.includes('/onto/') && !currentAttrs.definition) {
      loadAdditionalMetadataForElement(e.id(), activeOntologyIri);
    }
    objectType = edgeType;
  } else {
    // Hide SHACL constraints section when no edge is selected
    const shaclSection = qs('#shaclConstraintsSection');
    if (shaclSection) {
      shaclSection.style.display = 'none';
    }

    // Hide positioning section when no node is selected
    const positioningSection = qs('#positioningSection');
    if (positioningSection) {
      positioningSection.style.display = 'none';
    }

    // Hide inheritance fields when no selection
    const parentClassesGroup = qs('#parentClassesGroup');
    const abstractGroup = qs('#abstractGroup');
    if (parentClassesGroup) parentClassesGroup.style.display = 'none';
    if (abstractGroup) abstractGroup.style.display = 'none';

    const pid = (activeProject && (activeProject.id || activeProject.project_id)) ? (activeProject.id || activeProject.project_id) : 'default';
    // FIXED: Make model metadata ontology-specific, not just project-specific
    const ontologyKey = activeOntologyIri ? activeOntologyIri.split('/').pop() : 'default';
    const modelNameKey = `onto_model_name__${pid}__${ontologyKey}`;
    const modelAttrsKey = `onto_model_attrs__${pid}__${ontologyKey}`;

    nameEl.value = localStorage.getItem(modelNameKey) || 'Ontology Model';
    typeValueEl.textContent = getTypeDisplayName('model');
    objectType = 'model';
    try {
      currentAttrs = JSON.parse(localStorage.getItem(modelAttrsKey) || '{}');

      // POPULATE IMPORTS: Read current imports from localStorage and add to attributes
      if (activeOntologyIri) {
        const importsKey = 'onto_imports__' + encodeURIComponent(activeOntologyIri);
        try {
          const imports = JSON.parse(localStorage.getItem(importsKey) || '[]');
          if (imports && imports.length > 0) {
            // Clean up imports and format properly (one per line)
            const cleanImports = imports.map(imp => {
              // Remove any Turtle syntax artifacts
              let cleanImp = String(imp).trim();
              if (cleanImp.startsWith('@')) cleanImp = cleanImp.substring(1);
              if (cleanImp.startsWith('<')) cleanImp = cleanImp.slice(1, -1);
              return cleanImp;
            }).filter(imp => imp.length > 0);

            currentAttrs.imports = cleanImports.join('\n');
            console.log(`📋 Loaded ${cleanImports.length} clean imports:`, cleanImports);
          } else {
            currentAttrs.imports = '';
          }
        } catch (_) {
          currentAttrs.imports = '';
        }
      }
    } catch (_) { currentAttrs = {}; }
  }

  // Update attribute editor
  const isImportedElement = (sel.length === 1 && sel[0].hasClass('imported'));
  updateAttributeEditor(objectType, currentAttrs, isImportedElement);

  // Update element IRI display
  updateElementIriDisplay();
}

// Update multiplicity fields in properties panel
function updateMultiplicityFields(edge) {
  const minCountInput = qs('#propMinCount');
  const maxCountInput = qs('#propMaxCount');
  const displayEl = qs('#multiplicityDisplay');

  if (!minCountInput || !maxCountInput || !displayEl) return;

  // Get multiplicity data from edge
  const minCount = edge.data('minCount');
  const maxCount = edge.data('maxCount');

  // Populate input fields
  minCountInput.value = minCount !== null && minCount !== undefined ? minCount : '';
  maxCountInput.value = maxCount !== null && maxCount !== undefined ? maxCount : '';

  // Update display
  updateMultiplicityDisplay();
}

// Update multiplicity display based on current input values
function updateMultiplicityDisplay() {
  const minCountInput = qs('#propMinCount');
  const maxCountInput = qs('#propMaxCount');
  const displayEl = qs('#multiplicityDisplay');

  if (!minCountInput || !maxCountInput || !displayEl) return;

  const minVal = minCountInput.value ? parseInt(minCountInput.value) : null;
  const maxVal = maxCountInput.value ? parseInt(maxCountInput.value) : null;

  let display = 'No constraints';

  if (minVal !== null || maxVal !== null) {
    if (minVal === 1 && maxVal === 1) display = '(1)';
    else if (minVal === 0 && maxVal === null) display = '(0..*)';
    else if (minVal === 1 && maxVal === null) display = '(1..*)';
    else if (minVal === 0 && maxVal === 1) display = '(0..1)';
    else if (minVal !== null && maxVal !== null && minVal === maxVal) display = `(${minVal})`;
    else if (minVal !== null && maxVal !== null) display = `(${minVal}..${maxVal})`;
    else if (minVal !== null) display = `(${minVal}..*)`;
    else if (maxVal !== null) display = `(0..${maxVal})`;
  }

  displayEl.textContent = display;
}

// Update datatype constraint fields in properties panel
function updateDatatypeFields(edge) {
  const datatypeSelect = qs('#propDatatypeConstraint');
  const displayEl = qs('#datatypeDisplay');

  if (!datatypeSelect || !displayEl) return;

  // Get datatype constraint from edge data
  const datatypeConstraint = edge.data('datatypeConstraint');

  // Populate select field
  datatypeSelect.value = datatypeConstraint || '';

  // Update display
  updateDatatypeDisplay();
}

// Update datatype display based on current selection
function updateDatatypeDisplay() {
  const datatypeSelect = qs('#propDatatypeConstraint');
  const displayEl = qs('#datatypeDisplay');

  if (!datatypeSelect || !displayEl) return;

  const selectedType = datatypeSelect.value;

  if (selectedType) {
    displayEl.textContent = `Datatype: ${selectedType}`;
    displayEl.style.color = 'var(--accent)';
  } else {
    displayEl.textContent = 'No datatype constraint';
    displayEl.style.color = 'var(--muted)';
  }
}

// Update enumeration fields in properties panel
function updateEnumerationFields(edge) {
  const enumerationTextarea = qs('#propEnumerationValues');
  const displayEl = qs('#enumerationDisplay');

  if (!enumerationTextarea || !displayEl) return;

  // Get enumeration values from edge data
  const enumerationValues = edge.data('enumerationValues');

  // Populate textarea (one value per line)
  if (enumerationValues && Array.isArray(enumerationValues)) {
    enumerationTextarea.value = enumerationValues.join('\\n');
  } else {
    enumerationTextarea.value = '';
  }

  // Update display
  updateEnumerationDisplay();
}

// Update enumeration display based on current values
function updateEnumerationDisplay() {
  const enumerationTextarea = qs('#propEnumerationValues');
  const displayEl = qs('#enumerationDisplay');

  if (!enumerationTextarea || !displayEl) return;

  const values = enumerationTextarea.value.split('\\n').filter(v => v.trim()).map(v => v.trim());

  if (values.length > 0) {
    displayEl.textContent = `Values: {${values.join(', ')}}`;
    displayEl.style.color = 'var(--accent)';
  } else {
    displayEl.textContent = 'No enumeration constraint';
    displayEl.style.color = 'var(--muted)';
  }
}

// Update all constraints summary display
function updateAllConstraintsDisplay(edge) {
  const displayEl = qs('#allConstraintsDisplay');
  if (!displayEl) return;

  const constraints = [];

  // Multiplicity
  const minCount = edge.data('minCount');
  const maxCount = edge.data('maxCount');
  if (minCount !== null && minCount !== undefined || maxCount !== null && maxCount !== undefined) {
    let multiplicity = '';
    if (minCount === 1 && maxCount === 1) multiplicity = '(1)';
    else if (minCount === 0 && !maxCount) multiplicity = '(0..*)';
    else if (minCount === 1 && !maxCount) multiplicity = '(1..*)';
    else if (minCount === 0 && maxCount === 1) multiplicity = '(0..1)';
    else if (minCount !== null && maxCount !== null && minCount === maxCount) multiplicity = `(${minCount})`;
    else if (minCount !== null && maxCount !== null) multiplicity = `(${minCount}..${maxCount})`;
    else if (minCount !== null) multiplicity = `(${minCount}..*)`;
    else if (maxCount !== null) multiplicity = `(0..${maxCount})`;

    if (multiplicity) constraints.push(`Multiplicity: ${multiplicity}`);
  }

  // Datatype
  const datatypeConstraint = edge.data('datatypeConstraint');
  if (datatypeConstraint) {
    constraints.push(`Datatype: ${datatypeConstraint}`);
  }

  // Enumeration
  const enumerationValues = edge.data('enumerationValues');
  if (enumerationValues && Array.isArray(enumerationValues) && enumerationValues.length > 0) {
    const valuesList = enumerationValues.slice(0, 3).join(', ');
    const suffix = enumerationValues.length > 3 ? `... (+${enumerationValues.length - 3} more)` : '';
    constraints.push(`Enumeration: {${valuesList}${suffix}}`);
  }

  if (constraints.length > 0) {
    displayEl.innerHTML = constraints.join('<br>');
    displayEl.style.color = 'var(--text)';
  } else {
    displayEl.textContent = 'No constraints defined';
    displayEl.style.color = 'var(--muted)';
  }
}

// Apply multiplicity preset
function applyMultiplicityPreset(preset) {
  const minCountInput = qs('#propMinCount');
  const maxCountInput = qs('#propMaxCount');

  if (!minCountInput || !maxCountInput) return;

  switch (preset) {
    case 'none':
      minCountInput.value = '';
      maxCountInput.value = '';
      break;
    case '1':
      minCountInput.value = '1';
      maxCountInput.value = '1';
      break;
    case '0..1':
      minCountInput.value = '0';
      maxCountInput.value = '1';
      break;
    case '0..*':
      minCountInput.value = '0';
      maxCountInput.value = '';
      break;
    case '1..*':
      minCountInput.value = '1';
      maxCountInput.value = '';
      break;
  }

  updateMultiplicityDisplay();
  applyMultiplicityToEdge();
}

// Apply enumeration preset
function applyEnumerationPreset(preset) {
  const enumerationTextarea = qs('#propEnumerationValues');

  if (!enumerationTextarea) return;

  let values = '';
  switch (preset) {
    case 'requirement-status':
      values = 'Draft\\nReviewed\\nApproved\\nImplemented';
      break;
    case 'criticality':
      values = 'Low\\nMedium\\nHigh\\nCritical';
      break;
    case 'risk-level':
      values = 'Negligible\\nLow\\nMedium\\nHigh\\nCatastrophic';
      break;
    case 'priority':
      values = 'Low\\nMedium\\nHigh\\nUrgent';
      break;
    case 'custom':
      const customValues = prompt('Enter enumeration values (one per line):', 'Value1\\nValue2\\nValue3');
      if (customValues) {
        values = customValues;
      }
      break;
  }

  if (values) {
    enumerationTextarea.value = values;
    updateEnumerationDisplay();
    applyEnumerationToEdge();
  }
}

// Apply datatype constraint to edge
function applyDatatypeToEdge() {
  if (!ontoState.cy) return;

  const sel = ontoState.cy.$(':selected');
  if (sel.length !== 1 || !sel[0].isEdge()) return;

  const edge = sel[0];
  const datatypeSelect = qs('#propDatatypeConstraint');

  if (!datatypeSelect) return;

  const datatypeConstraint = datatypeSelect.value || null;

  console.log(`🎯 Applying datatype constraint: ${datatypeConstraint}`);

  // Update edge data
  edge.data('datatypeConstraint', datatypeConstraint);

  // Update modification metadata
  const currentAttrs = edge.data('attrs') || {};
  const updatedAttrs = updateModificationMetadata(currentAttrs);
  edge.data('attrs', updatedAttrs);

  // Save to backend
  saveShaclConstraintsToBackend(edge);

  // Update displays
  updateAllConstraintsDisplay(edge);
  persistOntologyToLocalStorage();
}

// Apply enumeration constraint to edge
function applyEnumerationToEdge() {
  if (!ontoState.cy) return;

  const sel = ontoState.cy.$(':selected');
  if (sel.length !== 1 || !sel[0].isEdge()) return;

  const edge = sel[0];
  const enumerationTextarea = qs('#propEnumerationValues');

  if (!enumerationTextarea) return;

  const values = enumerationTextarea.value.split('\\n').filter(v => v.trim()).map(v => v.trim());
  const enumerationValues = values.length > 0 ? values : null;

  console.log(`🎯 Applying enumeration constraint:`, enumerationValues);

  // Update edge data
  edge.data('enumerationValues', enumerationValues);

  // Update modification metadata
  const currentAttrs = edge.data('attrs') || {};
  const updatedAttrs = updateModificationMetadata(currentAttrs);
  edge.data('attrs', updatedAttrs);

  // Save to backend
  saveShaclConstraintsToBackend(edge);

  // Update displays
  updateAllConstraintsDisplay(edge);
  persistOntologyToLocalStorage();
}

// Apply multiplicity changes to the selected edge
function applyMultiplicityToEdge() {
  if (!ontoState.cy) {
    console.log('❌ No Cytoscape instance available');
    return;
  }

  const sel = ontoState.cy.$(':selected');
  if (sel.length !== 1 || !sel[0].isEdge()) {
    console.log('❌ No edge selected or multiple items selected');
    return;
  }

  const edge = sel[0];
  const minCountInput = qs('#propMinCount');
  const maxCountInput = qs('#propMaxCount');

  if (!minCountInput || !maxCountInput) {
    console.log('❌ Multiplicity input fields not found');
    return;
  }

  const minCount = minCountInput.value ? parseInt(minCountInput.value) : null;
  const maxCount = maxCountInput.value ? parseInt(maxCountInput.value) : null;

  console.log(`🎯 Applying multiplicity to edge: min=${minCount}, max=${maxCount}`);

  // Update edge multiplicity using our existing function
  updateEdgeMultiplicity(edge, minCount, maxCount);
}

function updateAttributeEditor(objectType, currentAttrs, isReadOnly = false) {
  const container = qs('#propAttrsContainer');
  if (!container) return;

  container.innerHTML = '';

  if (isReadOnly) {
    // Show read-only message for imported elements
    const readOnlyMsg = document.createElement('div');
    readOnlyMsg.style.cssText = `
      padding: 12px;
      background: var(--panel-2);
      border: 1px solid var(--border);
      border-radius: 6px;
      text-align: center;
      color: var(--muted);
      font-style: italic;
      margin-bottom: 8px;
    `;
    readOnlyMsg.innerHTML = '🔒 Imported elements are read-only<br><small>Properties cannot be modified</small>';
    container.appendChild(readOnlyMsg);
  }

  const template = attributeTemplates[objectType] || {};

  // Add template attributes
  Object.entries(template).forEach(([key, config]) => {
    const attrDiv = createAttributeField(key, config, currentAttrs[key] || '', isReadOnly);
    container.appendChild(attrDiv);
  });

  // Add any custom attributes not in template
  Object.entries(currentAttrs).forEach(([key, value]) => {
    if (!template[key]) {
      const attrDiv = createAttributeField(key, { type: 'text', label: key }, value, isReadOnly);
      container.appendChild(attrDiv);
    }
  });

  // Disable save button for imported elements
  const saveBtn = qs('#propSaveBtn');
  if (saveBtn) {
    saveBtn.disabled = isReadOnly;
    saveBtn.style.opacity = isReadOnly ? '0.5' : '1';
    saveBtn.title = isReadOnly ? 'Cannot save changes to imported elements' : 'Save changes';
  }

  // Disable add and reset buttons for imported elements
  const addBtn = qs('#addAttrBtn');
  const resetBtn = qs('#resetAttrsBtn');
  if (addBtn) {
    addBtn.disabled = isReadOnly;
    addBtn.style.opacity = isReadOnly ? '0.5' : '1';
    addBtn.title = isReadOnly ? 'Cannot add attributes to imported elements' : 'Add custom attribute';
  }
  if (resetBtn) {
    resetBtn.disabled = isReadOnly;
    resetBtn.style.opacity = isReadOnly ? '0.5' : '1';
    resetBtn.title = isReadOnly ? 'Cannot reset attributes of imported elements' : 'Reset to template';
  }
}

function createAttributeField(key, config, value, isReadOnly = false) {
  const div = document.createElement('div');
  div.style.display = 'grid';
  div.style.gridTemplateColumns = '1fr auto';
  div.style.gap = '8px';
  div.style.alignItems = 'center';

  const label = document.createElement('label');
  label.textContent = config.label || key;
  label.style.fontSize = '12px';
  label.style.color = '#9ca3af';

  const inputContainer = document.createElement('div');
  inputContainer.style.display = 'flex';
  inputContainer.style.gap = '4px';

  let input;
  if (config.type === 'select') {
    input = document.createElement('select');
    input.style.width = '100%';
    input.style.background = '#0b1220';
    input.style.color = '#e5e7eb';
    input.style.border = '1px solid var(--border)';
    input.style.borderRadius = '4px';
    input.style.padding = '4px';
    input.style.fontSize = '12px';

    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = config.placeholder || 'Select...';
    input.appendChild(defaultOption);

    if (config.options) {
      config.options.forEach(option => {
        const opt = document.createElement('option');
        opt.value = option;
        opt.textContent = option;
        if (value === option) opt.selected = true;
        input.appendChild(opt);
      });
    }
  } else if (config.type === 'checkbox') {
    input = document.createElement('input');
    input.type = 'checkbox';
    input.checked = value === true || value === 'true';
  } else if (config.type === 'textarea') {
    input = document.createElement('textarea');
    input.rows = config.rows || 3;

    // Special handling for imports field to ensure clean display
    let displayValue = value || '';
    if (key === 'imports') {
      // Clean up any Turtle syntax that might have leaked in
      displayValue = displayValue.replace(/^@/, '').replace(/\\\\n/g, '\n');
    }

    input.value = displayValue;
    input.style.width = '100%';
    input.style.background = '#0b1220';
    input.style.color = '#e5e7eb';
    input.style.border = '1px solid var(--border)';
    input.style.borderRadius = '4px';
    input.style.padding = '4px';
    input.style.fontSize = '12px';
    input.style.resize = 'vertical';
  } else if (config.type === 'date') {
    input = document.createElement('input');
    input.type = 'date';
    input.value = value || '';
  } else {
    input = document.createElement('input');
    input.type = config.type || 'text';
    input.value = value || '';
    input.placeholder = config.placeholder || '';
  }

  if (input.type !== 'checkbox' && input.type !== 'textarea') {
    input.style.width = '100%';
    input.style.background = '#0b1220';
    input.style.color = '#e5e7eb';
    input.style.border = '1px solid var(--border)';
    input.style.borderRadius = '4px';
    input.style.padding = '4px';
    input.style.fontSize = '12px';
  }

  // Make input read-only for imported elements or readonly fields
  if (isReadOnly || config.readonly) {
    input.disabled = true;
    input.style.opacity = '0.6';
    input.style.cursor = 'not-allowed';
    input.title = config.readonly ? 'This field is read-only metadata' : 'This field cannot be edited for imported elements';
  }

  input.dataset.attrKey = key;
  input.dataset.attrType = config.type || 'text';

  const deleteBtn = document.createElement('button');
  deleteBtn.type = 'button';
  deleteBtn.textContent = '×';
  deleteBtn.style.background = '#dc2626';
  deleteBtn.style.color = 'white';
  deleteBtn.style.border = 'none';
  deleteBtn.style.borderRadius = '4px';
  deleteBtn.style.width = '24px';
  deleteBtn.style.height = '24px';
  deleteBtn.style.fontSize = '14px';
  deleteBtn.style.cursor = 'pointer';
  deleteBtn.title = 'Remove attribute';

  // Only show delete button for custom attributes (not in template)
  let objectType = 'class';
  if (ontoState.cy) {
    const sel = ontoState.cy.$(':selected');
    if (sel.length === 1) {
      objectType = sel[0].data('type') || 'class';
    } else {
      objectType = 'model';
    }
  }
  const template = attributeTemplates[objectType] || {};
  if (template[key]) {
    deleteBtn.style.display = 'none';
  }

  deleteBtn.onclick = () => {
    if (!isReadOnly) {
      div.remove();
    }
  };

  // Disable delete button for read-only fields
  if (isReadOnly) {
    deleteBtn.disabled = true;
    deleteBtn.style.opacity = '0.3';
    deleteBtn.style.cursor = 'not-allowed';
    deleteBtn.title = 'Cannot delete attributes of imported elements';
  }

  inputContainer.appendChild(input);
  inputContainer.appendChild(deleteBtn);

  div.appendChild(label);
  div.appendChild(inputContainer);

  return div;
}

function getCurrentAttributes() {
  const container = qs('#propAttrsContainer');
  if (!container) return {};

  const attrs = {};
  const inputs = container.querySelectorAll('input, select, textarea');

  inputs.forEach(input => {
    const key = input.dataset.attrKey;
    const type = input.dataset.attrType;

    if (key) {
      let value;
      if (type === 'checkbox') {
        value = input.checked;
      } else if (type === 'select' && input.value === '') {
        value = null; // Don't include empty selects
      } else {
        value = input.value.trim();
        if (value === '') value = null; // Don't include empty strings
      }

      if (value !== null) {
        attrs[key] = value;
      }
    }
  });

  return attrs;
}

function getModelNamespace() {
  // Get model namespace from active ontology IRI (proper project-scoped URI)
  if (activeOntologyIri) {
    return activeOntologyIri;
  }

  // Try to get from stored attributes using ontology-specific keys
  const pid = (activeProject && (activeProject.id || activeProject.project_id)) ? (activeProject.id || activeProject.project_id) : 'default';

  // FIXED: Use ontology-specific localStorage keys consistently
  const ontologyKey = activeOntologyIri ? activeOntologyIri.split('/').pop() : 'default';
  const modelAttrsKey = `onto_model_attrs__${pid}__${ontologyKey}`;

  try {
    const modelAttrs = JSON.parse(localStorage.getItem(modelAttrsKey) || '{}');
    if (modelAttrs.namespace && !modelAttrs.namespace.endsWith('/ontology')) {
      console.log('🔧 getModelNamespace using stored namespace:', modelAttrs.namespace);
      return modelAttrs.namespace;
    }
    // If the stored namespace is the old hardcoded one, update it
    if (modelAttrs.graphIri) {
      console.log('🔧 getModelNamespace updating stored namespace to use graphIri:', modelAttrs.graphIri);
      modelAttrs.namespace = modelAttrs.graphIri;
      localStorage.setItem(modelAttrsKey, JSON.stringify(modelAttrs));
      return modelAttrs.graphIri;
    }
  } catch (_) { }

  // Use installation configuration as fallback (but this is wrong for project-scoped ontologies)
  const fallback = INSTALLATION_CONFIG.baseUri + '/ontology';
  console.log('⚠️ getModelNamespace using hardcoded fallback (this should not happen):', fallback);
  return fallback;
}

function updateElementIriDisplay() {
  const iriEl = qs('#ontoElementIri');
  const container = qs('#ontoElementIriContainer');
  const copyBtn = qs('#ontoCopyIriBtn');
  if (!iriEl || !container) return;

  // Only show container if we have a canvas
  if (!ontoState.cy) {
    container.style.display = 'none';
    return;
  }

  container.style.display = 'block';

  const sel = ontoState.cy.$(':selected');
  if (sel.length === 1) {
    const element = sel[0];
    const elementId = element.id();
    const elementType = element.data('type') || (element.isNode() ? 'class' : 'objectProperty');
    const isImported = element.hasClass('imported');
    const importSource = element.data('importSource');

    let iri = '';
    let namespace = '';

    if (isImported && importSource) {
      // For imported elements, use their original IRI and show the import source
      const originalIri = element.data('iri');
      console.log('🔍 Imported element selected:', {
        elementId,
        elementLabel: element.data('label'),
        originalIri,
        importSource,
        elementData: element.data()
      });

      if (originalIri && originalIri !== elementId && !originalIri.includes('Class')) {
        iri = originalIri;
        namespace = importSource;
      } else {
        // Fallback: construct IRI using import source as namespace
        const elementLabel = element.data('label') || elementId;
        const sluggedLabel = slugId(elementLabel) || elementId;
        iri = `${importSource}#${sluggedLabel}`;
        namespace = importSource;
      }

      iriEl.textContent = iri;
      iriEl.title = `IRI: ${iri}\nType: ${elementType}\nImported from: ${importSource}\nClick to copy`;
      iriEl.style.color = '#fbbf24'; // Different color for imported elements
      iriEl.style.opacity = '1';
    } else {
      // For local elements, use model namespace as before
      const modelNamespace = getModelNamespace();
      const elementLabel = element.data('label') || elementId;
      const sluggedLabel = slugId(elementLabel) || elementId;

      iri = `${modelNamespace}#${sluggedLabel}`;
      namespace = modelNamespace;

      iriEl.textContent = iri;
      iriEl.title = `IRI: ${iri}\nType: ${elementType}\nModel Namespace: ${namespace}\nClick to copy`;
      iriEl.style.color = '#60a5fa';
      iriEl.style.opacity = '1';
    }

    // Show copy button
    if (copyBtn) {
      copyBtn.style.display = 'inline-block';
      copyBtn.onclick = () => copyIriToClipboard(iri);
    }

    // Add click handler to IRI text
    iriEl.onclick = () => copyIriToClipboard(iri);
  } else {
    // Show current namespace when no element is selected, but only if there's an active ontology
    if (activeOntologyIri) {
      const modelNamespace = getModelNamespace();
      iriEl.textContent = modelNamespace;
      iriEl.title = `Current Model Namespace: ${modelNamespace}\nClick to copy namespace`;
      iriEl.style.color = '#60a5fa';
      iriEl.style.opacity = '1';
      iriEl.onclick = () => copyIriToClipboard(modelNamespace);

      // Show copy button for namespace
      if (copyBtn) {
        copyBtn.style.display = 'inline-block';
        copyBtn.onclick = () => copyIriToClipboard(modelNamespace);
      }
    } else {
      // No active ontology - show "No element selected"
      iriEl.textContent = 'No element selected';
      iriEl.title = 'No element selected';
      iriEl.style.color = '#9aa4b2';
      iriEl.style.opacity = '0.7';
      iriEl.onclick = null;

      // Hide copy button when no element is selected
      if (copyBtn) {
        copyBtn.style.display = 'none';
      }
    }
  }
}

// General clipboard copy function
function copyToClipboard(text, showToast = true) {
  try {
    navigator.clipboard.writeText(text).then(() => {
      if (showToast && typeof toast === 'function') {
        toast(`Copied: ${text.length > 50 ? text.substring(0, 50) + '...' : text}`);
      }
    }).catch(err => {
      console.error('Failed to copy to clipboard:', err);
      if (showToast && typeof toast === 'function') {
        toast('Failed to copy to clipboard', true);
      }
    });
  } catch (err) {
    console.error('Clipboard not available:', err);
    if (showToast && typeof toast === 'function') {
      toast('Clipboard not available', true);
    }
  }
}

function copyIriToClipboard(iri) {
  try {
    navigator.clipboard.writeText(iri).then(() => {
      // Show temporary feedback
      const copyBtn = qs('#ontoCopyIriBtn');
      if (copyBtn) {
        const originalText = copyBtn.textContent;
        copyBtn.textContent = 'Copied!';
        copyBtn.style.background = '#10b981';
        setTimeout(() => {
          copyBtn.textContent = originalText;
          copyBtn.style.background = '';
        }, 1000);
      }
    }).catch(() => {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = iri;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);

      const copyBtn = qs('#ontoCopyIriBtn');
      if (copyBtn) {
        const originalText = copyBtn.textContent;
        copyBtn.textContent = 'Copied!';
        copyBtn.style.background = '#10b981';
        setTimeout(() => {
          copyBtn.textContent = originalText;
          copyBtn.style.background = '';
        }, 1000);
      }
    });
  } catch (error) {
    console.warn('Failed to copy IRI to clipboard:', error);
  }
}

function persistOntologyToLocalStorage() {
  if (!ontoState.cy) return;
  if (ontoState.suspendAutosave) return;
  try {
    const nodes = ontoState.cy.nodes().filter(n => !n.hasClass('imported')).map(n => ({ data: n.data(), position: n.position() }));
    const edges = ontoState.cy.edges().filter(e => !e.hasClass('imported')).map(e => ({ data: e.data() }));
    if (activeOntologyIri) {
      const storageData = {
        nodes,
        edges,
        timestamp: Date.now(),
        source: 'local' // Mark that this data was saved locally
      };
      localStorage.setItem(storageKeyForGraph(activeOntologyIri), JSON.stringify(storageData));

      // Layout is now saved separately with its own debounced handler
      // No longer automatically saving layout here to prevent excessive server calls
    }
  } catch (_) { }
}

async function saveLayoutToServer(graphIri, nodes, edges) {
  try {
    console.log('💾 Saving layout to server for:', graphIri);

    const pan = ontoState.cy.pan();
    const zoom = ontoState.cy.zoom();

    const layoutData = {
      nodes: nodes.map(n => ({
        iri: n.data.id,
        x: n.position.x,
        y: n.position.y
      })),
      edges: edges.map(e => ({
        iri: e.data.id
      })),
      zoom: zoom,
      pan: { x: pan.x, y: pan.y }
    };

    console.log('💾 Layout data:', {
      nodeCount: layoutData.nodes.length,
      edgeCount: layoutData.edges.length,
      zoom: layoutData.zoom,
      pan: layoutData.pan
    });

    const response = await authenticatedFetch(`/api/ontology/layout?graph=${encodeURIComponent(graphIri)}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(layoutData)
    });

    console.log('💾 Layout save response status:', response.status);
    console.log('💾 Layout save response ok:', response.ok);

    if (!response.ok) {
      console.warn('❌ Failed to save layout to server:', response.status);
    } else {
      console.log('✅ Layout saved to server successfully!');
    }
  } catch (error) {
    console.warn('Error saving layout to server:', error);
  }
}

async function loadLayoutFromServer(graphIri) {
  try {
    // First check if we have a recent layout in localStorage
    const localLayoutKey = `onto_layout_${encodeURIComponent(graphIri)}`;
    const localLayout = localStorage.getItem(localLayoutKey);

    if (localLayout) {
      try {
        const layoutData = JSON.parse(localLayout);
        // Check if local layout is recent (within last 30 seconds)
        if (layoutData.timestamp && (Date.now() - layoutData.timestamp) < 30000) {
          console.log('📍 Using recent layout from localStorage (saved within last 30 seconds)');

          // Apply node positions from local storage
          if (layoutData.nodes) {
            layoutData.nodes.forEach(nodeLayout => {
              const node = ontoState.cy.$(`#${nodeLayout.iri}`);
              if (node.length > 0) {
                node.position({ x: nodeLayout.x, y: nodeLayout.y });
              }
            });
          }

          // Apply zoom and pan
          if (layoutData.zoom && layoutData.pan) {
            ontoState.cy.zoom(layoutData.zoom);
            ontoState.cy.pan(layoutData.pan);
          }

          return true;
        }
      } catch (e) {
        console.warn('Error parsing local layout:', e);
      }
    }

    // If no recent local layout, load from server
    const response = await authenticatedFetch(`/api/ontology/layout?graph=${encodeURIComponent(graphIri)}`);

    if (response.ok) {
      const result = await response.json();
      const layoutData = result.data;

      if (layoutData && layoutData.nodes && layoutData.nodes.length > 0) {
        // Apply node positions
        layoutData.nodes.forEach(nodeLayout => {
          const node = ontoState.cy.$(`#${nodeLayout.iri}`);
          if (node.length > 0) {
            node.position({ x: nodeLayout.x, y: nodeLayout.y });
          }
        });

        // Apply zoom and pan
        if (layoutData.zoom && layoutData.pan) {
          ontoState.cy.zoom(layoutData.zoom);
          ontoState.cy.pan(layoutData.pan);
        }

        console.log('Layout loaded from server');
        return true;
      }
    } else if (response.status !== 404) {
      console.warn('Failed to load layout from server:', response.status);
    }
  } catch (error) {
    console.warn('Error loading layout from server:', error);
  }
  return false;
}

// graphKeyForActive not used; per-project keys are used via storageKeyForGraph
function attrsFromModel() {
  const pid = (activeProject && (activeProject.id || activeProject.project_id)) ? (activeProject.id || activeProject.project_id) : 'default';

  // FIXED: Use ontology-specific localStorage keys consistently
  const ontologyKey = activeOntologyIri ? activeOntologyIri.split('/').pop() : 'default';
  const modelAttrsKey = `onto_model_attrs__${pid}__${ontologyKey}`;

  try { return JSON.parse(localStorage.getItem(modelAttrsKey) || '{}'); } catch (_) { return {}; }
}
function loadOntologyLabelMap(project) {
  const pid = project?.id || project?.project_id || (activeProject && (activeProject.id || activeProject.project_id)) || 'default';
  try { return JSON.parse(localStorage.getItem(`onto_label_map__${pid}`) || '{}'); } catch (_) { return {}; }
}
function saveOntologyLabel(graphIri, label) {
  const pid = (activeProject && (activeProject.id || activeProject.project_id)) ? (activeProject.id || activeProject.project_id) : 'default';
  try { const m = loadOntologyLabelMap(activeProject); m[graphIri] = label; localStorage.setItem(`onto_label_map__${pid}`, JSON.stringify(m)); } catch (_) { }
}
function storageKeyForGraph(iri) {
  const pid = (activeProject && (activeProject.id || activeProject.project_id)) ? (activeProject.id || activeProject.project_id) : 'default';
  return `onto_graph__${pid}__` + encodeURIComponent(iri);
}
function saveGraphToLocal(graphIri) {
  try {
    const nodes = ontoState.cy ? ontoState.cy.nodes().jsons() : [];
    const edges = ontoState.cy ? ontoState.cy.edges().jsons() : [];
    const storageData = {
      nodes,
      edges,
      timestamp: Date.now(),
      source: 'local' // Mark that this data was saved locally
    };
    localStorage.setItem(storageKeyForGraph(graphIri), JSON.stringify(storageData));
  } catch (_) { }
}
function loadGraphFromLocal(graphIri) {
  try {
    const json = localStorage.getItem(storageKeyForGraph(graphIri));
    if (!json) return;
    const data = JSON.parse(json);
    if (!ontoState.cy) return;
    ontoState.cy.elements().remove();
    ontoState.cy.add(data.nodes || []);
    ontoState.cy.add(data.edges || []);
    // Ensure all loaded elements have attrs property
    ensureAttributesExist();
    // After loading, ensure nextId is advanced beyond existing ClassNNN
    recomputeNextId();
    requestAnimationFrame(() => { ontoState.cy.fit(); });
  } catch (_) { }
}

async function fetchRichMetadata(graphIri) {
  try {
    console.log('🔍 fetchRichMetadata called for:', graphIri);

    // Optimized SPARQL queries - fetch only essential metadata first
    // We'll fetch labels and basic info first, then load other metadata on demand
    const qClasses = `
      PREFIX owl: <http://www.w3.org/2002/07/owl#>
      PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
      PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
      PREFIX dc11: <http://purl.org/dc/elements/1.1/>
      PREFIX dcterms: <http://purl.org/dc/terms/>
      PREFIX obo: <http://purl.obolibrary.org/obo/>
      SELECT ?c ?label ?comment ?definition ?example ?identifier ?subclassOf ?equivalentClass WHERE {
        GRAPH <${graphIri}> {
          ?c a owl:Class .
          OPTIONAL { ?c rdfs:label ?label }
          OPTIONAL { ?c rdfs:comment ?comment }
          OPTIONAL { ?c skos:definition ?definition }
          OPTIONAL { ?c skos:example ?example }
          OPTIONAL { ?c dc11:identifier ?identifier }
          OPTIONAL { ?c rdfs:subClassOf ?subclassOf }
          OPTIONAL { ?c owl:equivalentClass ?equivalentClass }
        }
      }`;

    const qProps = `
      PREFIX owl: <http://www.w3.org/2002/07/owl#>
      PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
      PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
      PREFIX dc11: <http://purl.org/dc/elements/1.1/>
      PREFIX dcterms: <http://purl.org/dc/terms/>
      SELECT ?p ?label ?comment ?definition ?example ?identifier ?domain ?range ?inverseOf ?subPropertyOf ?equivalentProperty ?propertyType WHERE {
        GRAPH <${graphIri}> {
          ?p a owl:ObjectProperty .
          OPTIONAL { ?p rdfs:label ?label }
          OPTIONAL { ?p rdfs:comment ?comment }
          OPTIONAL { ?p skos:definition ?definition }
          OPTIONAL { ?p skos:example ?example }
          OPTIONAL { ?p dc11:identifier ?identifier }
          OPTIONAL { ?p rdfs:domain ?domain }
          OPTIONAL { ?p rdfs:range ?range }
          OPTIONAL { ?p owl:inverseOf ?inverseOf }
          OPTIONAL { ?p rdfs:subPropertyOf ?subPropertyOf }
          OPTIONAL { ?p owl:equivalentProperty ?equivalentProperty }
          OPTIONAL { ?p a ?propertyType }
        }
      }`;

    const classesRes = await authenticatedFetch('/api/ontology/sparql', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: qClasses }) });
    const propsRes = await authenticatedFetch('/api/ontology/sparql', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: qProps }) });
    const classesJson = classesRes.ok ? await classesRes.json() : { results: { bindings: [] } };
    const propsJson = propsRes.ok ? await propsRes.json() : { results: { bindings: [] } };

    // Enhanced class processing with rich metadata
    const classes = (classesJson.results?.bindings || []).map(b => {
      const iri = b.c.value;
      const label = (b.label && b.label.value) || (iri.includes('#') ? iri.split('#').pop() : iri.split('/').pop());
      const attrs = {};

      // Store all available metadata
      if (b.comment && b.comment.value) attrs.comment = b.comment.value;
      if (b.definition && b.definition.value) attrs.definition = b.definition.value;
      if (b.example && b.example.value) attrs.example = b.example.value;
      if (b.identifier && b.identifier.value) attrs.identifier = b.identifier.value;
      if (b.subclassOf && b.subclassOf.value) attrs.subclassOf = b.subclassOf.value;
      if (b.equivalentClass && b.equivalentClass.value) attrs.equivalentClass = b.equivalentClass.value;

      return { iri, label, attrs };
    });

    // Enhanced property processing with rich metadata
    const properties = [];
    (propsJson.results?.bindings || []).forEach(b => {
      const p = b.p.value;
      const label = (b.label && b.label.value) || (p.includes('#') ? p.split('#').pop() : p.split('/').pop());
      const attrs = {};

      // Store all available metadata
      if (b.comment && b.comment.value) attrs.comment = b.comment.value;
      if (b.definition && b.definition.value) attrs.definition = b.definition.value;
      if (b.example && b.example.value) attrs.example = b.example.value;
      if (b.identifier && b.identifier.value) attrs.identifier = b.identifier.value;
      if (b.domain && b.domain.value) attrs.domain = b.domain.value;
      if (b.range && b.range.value) attrs.range = b.range.value;
      if (b.inverseOf && b.inverseOf.value) attrs.inverseOf = b.inverseOf.value;
      if (b.subPropertyOf && b.subPropertyOf.value) attrs.subPropertyOf = b.subPropertyOf.value;
      if (b.equivalentProperty && b.equivalentProperty.value) attrs.equivalentProperty = b.equivalentProperty.value;
      if (b.propertyType && b.propertyType.value) attrs.propertyType = b.propertyType.value;

      properties.push({ iri: p, label, attrs });
    });

    return { classes, properties };
  } catch (error) {
    console.error('Failed to fetch rich metadata:', error);
    return { classes: [], properties: [] };
  }
}

function convertOntologyToCytoscape(ontologyData) {
  // Convert API ontology format to Cytoscape format
  const nodes = [];
  const edges = [];

  // Create nodes for classes
  const classes = ontologyData.classes || [];
  const classNameToId = {}; // Map class names to IDs

  classes.forEach((cls, index) => {
    // Use the original URI as ID if available, otherwise fall back to simple ID
    const classId = cls.iri || `Class${index + 1}`;
    classNameToId[cls.name] = classId;

    // Arrange in a grid layout
    const row = Math.floor(index / 4);
    const col = index % 4;

    const node = {
      data: {
        id: classId,
        iri: cls.iri || classId, // Preserve original URI
        label: cls.label || cls.name,
        type: 'class'
      },
      position: {
        x: 150 + (col * 200),
        y: 100 + (row * 150)
      }
    };
    nodes.push(node);
  });

  // Create edges for object properties
  let edgeId = 1;
  const objectProps = ontologyData.object_properties || [];
  objectProps.forEach(prop => {
    if (prop.domain && prop.range && classNameToId[prop.domain] && classNameToId[prop.range]) {
      // Format multiplicity constraints for display  
      const minCount = prop.min_count;
      const maxCount = prop.max_count;
      let multiplicity = '';
      if (minCount !== null && minCount !== undefined || maxCount !== null && maxCount !== undefined) {
        if (minCount === 1 && maxCount === 1) multiplicity = ' (1)';
        else if (minCount === 0 && (maxCount === null || maxCount === undefined)) multiplicity = ' (0..*)';
        else if (minCount === 1 && (maxCount === null || maxCount === undefined)) multiplicity = ' (1..*)';
        else if (minCount === 0 && maxCount === 1) multiplicity = ' (0..1)';
        else if (minCount !== null && minCount !== undefined && maxCount !== null && maxCount !== undefined && minCount === maxCount)
          multiplicity = ` (${minCount})`;
        else if (minCount !== null && minCount !== undefined && maxCount !== null && maxCount !== undefined)
          multiplicity = ` (${minCount}..${maxCount})`;
        else if (minCount !== null && minCount !== undefined) multiplicity = ` (${minCount}..*)`;
        else if (maxCount !== null && maxCount !== undefined) multiplicity = ` (0..${maxCount})`;
      }

      const displayLabel = prop.label || prop.name;

      const edge = {
        data: {
          id: `e${edgeId}`,
          source: classNameToId[prop.domain],
          target: classNameToId[prop.range],
          predicate: prop.name,
          label: displayLabel,  // Clean relationship name in middle
          type: 'objectProperty',
          minCount: minCount,       // Store multiplicity data
          maxCount: maxCount,
          multiplicityDisplay: multiplicity.trim(),  // Store formatted multiplicity
          attrs: {}
        }
      };
      edges.push(edge);
      edgeId++;
    }
  });

  // Create data property nodes and connect them to their domain classes
  let dpId = 1;
  const dataProps = ontologyData.datatype_properties || [];
  dataProps.forEach(prop => {
    if (prop.domain && classNameToId[prop.domain]) {
      const dataPropertyId = `DP${dpId}`;

      // Create data property node
      const domainClassId = classNameToId[prop.domain];
      const domainNode = nodes.find(n => n.data.id === domainClassId);
      let dpX = 150, dpY = 100; // fallback position

      if (domainNode) {
        // Position data property near its domain class
        dpX = domainNode.position.x + 180;
        dpY = domainNode.position.y + (dpId % 3 - 1) * 60; // stagger vertically
      }

      const dpNode = {
        data: {
          id: dataPropertyId,
          label: prop.label || prop.name,
          type: 'dataProperty'
        },
        position: {
          x: dpX,
          y: dpY
        }
      };
      nodes.push(dpNode);

      // Create edge connecting class to data property
      const dpEdge = {
        data: {
          id: `edp${dpId}`,
          source: domainClassId,
          target: dataPropertyId,
          predicate: prop.name,
          type: 'objectProperty', // UI uses objectProperty type for visual connection
          attrs: {}
        }
      };
      edges.push(dpEdge);

      dpId++;
    }
  });

  return { nodes, edges };
}

function convertOntologyToCytoscapeWithMetadata(ontologyData, richMetadata) {
  // Convert API ontology format to Cytoscape format with rich metadata
  const nodes = [];
  const edges = [];

  // Create a map of URI to rich metadata
  const classMetadataMap = {};
  richMetadata.classes.forEach(cls => {
    classMetadataMap[cls.iri] = cls;
  });

  const propertyMetadataMap = {};
  richMetadata.properties.forEach(prop => {
    propertyMetadataMap[prop.iri] = prop;
  });

  // Create nodes for classes
  const classes = ontologyData.classes || [];
  const classNameToId = {}; // Map class names to simple IDs

  classes.forEach((cls, index) => {
    // Use the original URI as ID if available, otherwise fall back to simple ID
    const classId = cls.iri || `Class${index + 1}`;
    classNameToId[cls.name] = classId;

    // Get rich metadata for this class
    const richClass = classMetadataMap[cls.uri] || {};
    const displayLabel = richClass.label || cls.label || cls.name;

    // Arrange in a circular layout for better initial positioning
    const totalClasses = classes.length;
    const angle = (2 * Math.PI * index) / totalClasses;
    const radius = Math.max(200, totalClasses * 25);
    const centerX = 400;
    const centerY = 300;

    const node = {
      data: {
        id: classId,
        iri: cls.iri || classId, // Preserve original URI
        label: displayLabel,
        type: 'class',
        attrs: richClass.attrs || {}
      },
      position: {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle)
      }
    };
    nodes.push(node);
  });

  // Create edges for object properties
  let edgeId = 1;
  const objectProps = ontologyData.object_properties || [];
  objectProps.forEach(prop => {
    if (prop.domain && prop.range && classNameToId[prop.domain] && classNameToId[prop.range]) {
      // Get rich metadata for this property
      const richProp = propertyMetadataMap[prop.uri] || {};
      const displayLabel = richProp.label || prop.label || prop.name;

      // Format multiplicity constraints for display
      const minCount = prop.min_count;
      const maxCount = prop.max_count;
      let multiplicity = '';
      if (minCount !== null && minCount !== undefined || maxCount !== null && maxCount !== undefined) {
        if (minCount === 1 && maxCount === 1) multiplicity = ' (1)';
        else if (minCount === 0 && (maxCount === null || maxCount === undefined)) multiplicity = ' (0..*)';
        else if (minCount === 1 && (maxCount === null || maxCount === undefined)) multiplicity = ' (1..*)';
        else if (minCount === 0 && maxCount === 1) multiplicity = ' (0..1)';
        else if (minCount !== null && minCount !== undefined && maxCount !== null && maxCount !== undefined && minCount === maxCount)
          multiplicity = ` (${minCount})`;
        else if (minCount !== null && minCount !== undefined && maxCount !== null && maxCount !== undefined)
          multiplicity = ` (${minCount}..${maxCount})`;
        else if (minCount !== null && minCount !== undefined) multiplicity = ` (${minCount}..*)`;
        else if (maxCount !== null && maxCount !== undefined) multiplicity = ` (0..${maxCount})`;
      }

      const edge = {
        data: {
          id: `e${edgeId}`,
          source: classNameToId[prop.domain],
          target: classNameToId[prop.range],
          predicate: displayLabel,  // Base predicate name
          label: displayLabel,      // Clean relationship name in middle
          type: 'objectProperty',
          minCount: minCount,       // Store multiplicity data
          maxCount: maxCount,
          multiplicityDisplay: multiplicity.trim(),  // Store formatted multiplicity
          attrs: richProp.attrs || {}
        }
      };
      edges.push(edge);
      edgeId++;
    }
  });

  // Create data property nodes and connect them to their domain classes
  let dpId = 1;
  const dataProps = ontologyData.datatype_properties || [];
  dataProps.forEach(prop => {
    if (prop.domain && classNameToId[prop.domain]) {
      const dataPropertyId = `DP${dpId}`;

      // Get rich metadata for this property
      const richProp = propertyMetadataMap[prop.uri] || {};
      const displayLabel = richProp.label || prop.label || prop.name;

      // Create data property node
      const domainClassId = classNameToId[prop.domain];
      const domainNode = nodes.find(n => n.data.id === domainClassId);
      let dpX = 150, dpY = 100; // fallback position

      if (domainNode) {
        // Position data property near its domain class
        dpX = domainNode.position.x + 180;
        dpY = domainNode.position.y + (dpId % 3 - 1) * 60; // stagger vertically
      }

      const dpNode = {
        data: {
          id: dataPropertyId,
          label: displayLabel,
          type: 'dataProperty',
          attrs: richProp.attrs || {}
        },
        position: {
          x: dpX,
          y: dpY
        }
      };
      nodes.push(dpNode);

      // Create edge connecting class to data property
      const dpEdge = {
        data: {
          id: `edp${dpId}`,
          source: domainClassId,
          target: dataPropertyId,
          predicate: prop.name,
          type: 'objectProperty', // UI uses objectProperty type for visual connection
          attrs: {}
        }
      };
      edges.push(dpEdge);

      dpId++;
    }
  });

  return { nodes, edges };
}

function convertCytoscapeToOntology() {
  // Convert current Cytoscape canvas to ontology JSON format
  if (!ontoState.cy) return null;

  const ontologyData = {
    metadata: {
      name: "Ontology from Canvas",
      namespace: activeOntologyIri || `${INSTALLATION_CONFIG.baseUri}/default`,
      created: new Date().toISOString()
    },
    classes: [],
    object_properties: [],
    datatype_properties: []
  };

  // Process nodes
  ontoState.cy.nodes().forEach(node => {
    const data = node.data();
    const type = data.type || 'class';

    if (type === 'class') {
      const attrs = data.attrs || {};

      // Build comprehensive class data with all attributes
      const classData = {
        name: data.id,
        label: data.label || data.id,
        comment: attrs.comment || data.comment || '',
        // Standard ontological properties
        definition: attrs.definition || '',
        example: attrs.example || '',
        identifier: attrs.identifier || '',
        subclassOf: attrs.subclassOf || '',
        equivalentClass: attrs.equivalentClass || '',
        disjointWith: attrs.disjointWith || '',
        // Inheritance system properties - CRITICAL FIX
        subclass_of: attrs.subclass_of || attrs.subclassOf || [],
        is_abstract: attrs.is_abstract || false,
        // Metadata properties
        creator: attrs.creator || '',
        created_date: attrs.created_date || '',
        last_modified_by: attrs.last_modified_by || '',
        last_modified_date: attrs.last_modified_date || '',
        // Custom properties
        priority: attrs.priority || '',
        status: attrs.status || ''
      };

      // CRITICAL FIX: Convert inheritance array to proper format for backend
      if (Array.isArray(classData.subclass_of) && classData.subclass_of.length > 0) {
        // Convert full URIs to class names for backend processing
        classData.subclass_of = classData.subclass_of.map(parentUri => {
          // Extract class name from URI (e.g., "...#PhysicalObject" -> "PhysicalObject")
          return parentUri.split('#').pop() || parentUri;
        });
        console.log(`🔍 Class ${data.id} inherits from:`, classData.subclass_of);
      } else if (classData.subclass_of && !Array.isArray(classData.subclass_of)) {
        // Handle legacy single parent format
        classData.subclass_of = [classData.subclass_of];
      }

      // Remove empty attributes to keep JSON clean (but preserve boolean false values)
      Object.keys(classData).forEach(key => {
        if (classData[key] === '' || classData[key] === null || classData[key] === undefined) {
          // Don't delete boolean false values (like is_abstract: false)
          if (typeof classData[key] !== 'boolean') {
            delete classData[key];
          }
        }
      });

      ontologyData.classes.push(classData);
    } else if (type === 'dataProperty') {
      const attrs = data.attrs || {};

      // Build comprehensive data property data with all attributes
      const propData = {
        name: data.id,
        label: data.label || data.id,
        comment: attrs.comment || data.comment || '',
        domain: data.domain || '',
        range: data.range || 'string',
        // Standard ontological properties
        definition: attrs.definition || '',
        example: attrs.example || '',
        identifier: attrs.identifier || '',
        subPropertyOf: attrs.subPropertyOf || '',
        equivalentProperty: attrs.equivalentProperty || '',
        // Metadata properties
        creator: attrs.creator || '',
        created_date: attrs.created_date || '',
        last_modified_by: attrs.last_modified_by || '',
        last_modified_date: attrs.last_modified_date || '',
        // Custom properties
        functional: attrs.functional || false
      };

      // Remove empty attributes to keep JSON clean
      Object.keys(propData).forEach(key => {
        if (propData[key] === '' || propData[key] === null || propData[key] === undefined || propData[key] === false) {
          delete propData[key];
        }
      });

      ontologyData.datatype_properties.push(propData);
    }
  });

  // Process edges
  ontoState.cy.edges().forEach(edge => {
    const data = edge.data();
    const sourceType = ontoState.cy.$(`#${data.source}`).data('type') || 'class';
    const targetType = ontoState.cy.$(`#${data.target}`).data('type') || 'class';

    if (sourceType === 'class' && targetType === 'class') {
      const attrs = data.attrs || {};

      // Build comprehensive object property data with all attributes
      const propData = {
        name: data.id,
        label: data.predicate || data.id,
        comment: attrs.comment || data.comment || '',
        domain: data.source,
        range: data.target,
        // Standard ontological properties
        definition: attrs.definition || '',
        example: attrs.example || '',
        identifier: attrs.identifier || '',
        inverseOf: attrs.inverseOf || '',
        subPropertyOf: attrs.subPropertyOf || '',
        equivalentProperty: attrs.equivalentProperty || '',
        propertyType: attrs.propertyType || '',
        // Metadata properties
        creator: attrs.creator || '',
        created_date: attrs.created_date || '',
        last_modified_by: attrs.last_modified_by || '',
        last_modified_date: attrs.last_modified_date || '',
        // Custom properties
        functional: attrs.functional || false,
        inverse_functional: attrs.inverse_functional || false
      };

      // Remove empty attributes to keep JSON clean
      Object.keys(propData).forEach(key => {
        if (propData[key] === '' || propData[key] === null || propData[key] === undefined || propData[key] === false) {
          delete propData[key];
        }
      });

      ontologyData.object_properties.push(propData);
    } else if (sourceType === 'note' && (targetType === 'class' || targetType === 'dataProperty') && data.predicate === 'note_for') {
      // Handle note annotations - add note content as comment on target element
      const noteNode = ontoState.cy.$(`#${data.source}`);
      const targetNode = ontoState.cy.$(`#${data.target}`);

      if (noteNode.length && targetNode.length) {
        // Get ALL note attributes for rich context
        const noteAttrs = noteNode.data('attrs') || {};
        let noteText = noteNode.data('label') || '';

        // Use content from attributes if available (richer than just label)
        if (noteAttrs.content) {
          noteText = noteAttrs.content;
        }

        // Build comprehensive note annotation with all metadata
        const noteType = noteAttrs.noteType || 'Note';
        const creator = noteAttrs.creator || 'Unknown';
        const createdDate = noteAttrs.created_date || '';

        // Create rich note annotation
        let fullNoteText = noteType !== 'Note' ? `[${noteType}] ${noteText}` : noteText;

        // Add metadata for DAS context
        const noteMetadata = [];
        if (creator) noteMetadata.push(`by ${creator}`);
        if (createdDate) noteMetadata.push(`on ${createdDate}`);

        if (noteMetadata.length > 0) {
          fullNoteText += ` (${noteMetadata.join(', ')})`;
        }

        const targetId = data.target;

        // Find the target class/property in our ontology data and add the note as a rich annotation
        if (targetType === 'class') {
          const targetClass = ontologyData.classes.find(cls => cls.name === targetId);
          if (targetClass) {
            // Add as structured note data for DAS to understand note context
            if (!targetClass.notes) targetClass.notes = [];
            targetClass.notes.push({
              type: noteType,
              content: noteText,
              creator: creator,
              created_date: createdDate,
              full_text: fullNoteText
            });

            // Also append to comment for backward compatibility
            const existingComment = targetClass.comment || '';
            targetClass.comment = existingComment ? `${existingComment}\nNote: ${fullNoteText}` : fullNoteText;
          }
        } else if (targetType === 'dataProperty') {
          const targetProp = ontologyData.datatype_properties.find(prop => prop.name === targetId);
          if (targetProp) {
            // Add as structured note data for DAS to understand note context
            if (!targetProp.notes) targetProp.notes = [];
            targetProp.notes.push({
              type: noteType,
              content: noteText,
              creator: creator,
              created_date: createdDate,
              full_text: fullNoteText
            });

            // Also append to comment for backward compatibility
            const existingComment = targetProp.comment || '';
            targetProp.comment = existingComment ? `${existingComment}\nNote: ${fullNoteText}` : fullNoteText;
          }
        }
      }
    }
  });

  return ontologyData;
}

async function loadGraphFromLocalOrAPI(graphIri) {
  try {
    console.log('🔍 loadGraphFromLocalOrAPI called for:', graphIri);

    // Load collapsed imports state for this ontology
    ontoState.collapsedImports = loadCollapsedImports(graphIri);

    // Load visibility state for this ontology
    ontoState.visibilityState = loadVisibilityState(graphIri);

    // Load individual element visibility for this ontology
    ontoState.elementVisibility = loadElementVisibility(graphIri);

    // Check if this is an imported ontology by looking for the pattern in the graph IRI
    const isImportedOntology = graphIri.includes('/onto/') && !graphIri.includes('#layout');

    // First, try to load from local storage for ALL ontologies (including imported ones)
    const json = localStorage.getItem(storageKeyForGraph(graphIri));
    if (json) {
      console.log('🔍 Loading from local storage:', json.substring(0, 200) + '...');
      const data = JSON.parse(json);
      if (data && (data.nodes || data.edges) && data.nodes?.length > 0) {
        if (!ontoState.cy) return;
        ontoState.cy.elements().remove();
        ontoState.cy.add(data.nodes || []);
        ontoState.cy.add(data.edges || []);
        // Ensure all loaded elements have attrs property
        ensureAttributesExist();
        recomputeNextId();

        // Try to load layout from server
        await loadLayoutFromServer(graphIri);

        // Apply saved visibility states
        updateCanvasVisibility();

        console.log('✅ Graph loaded from local storage, preserving current state');
        console.log('📊 Data source:', data.source || 'unknown', 'Timestamp:', data.timestamp ? new Date(data.timestamp).toLocaleString() : 'unknown');
        return;
      }
    }

    // Only fetch from API if local storage is empty or invalid
    if (isImportedOntology) {
      console.log('🔍 No local storage found for imported ontology, fetching from API for rich metadata');
      // Show loading indicator for imported ontologies
      showOntologyLoadingIndicator();
    } else {
      console.log('🔍 No local storage found, fetching from API');
    }

    // If local storage is empty, fetch from API
    console.log('Loading ontology from API:', graphIri);

    // Update progress: Fetching basic ontology data
    if (isImportedOntology) {
      updateOntologyLoadingProgress('Fetching ontology data...', 20);
    }

    const token = localStorage.getItem(tokenKey);
    const apiUrl = `/api/ontology/?graph=${encodeURIComponent(graphIri)}`;
    const response = await fetch(apiUrl, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });

    if (response.ok) {
      const result = await response.json();
      const ontologyData = result.data;

      if (ontologyData) {
        console.log('🔍 Loading ontology data from API:', ontologyData);

        // Update progress: Fetching rich metadata
        if (isImportedOntology) {
          updateOntologyLoadingProgress('Fetching rich metadata...', 40);
        }

        // Fetch rich metadata using the same queries as fetchImportGraphSnapshot
        const richMetadata = await fetchRichMetadata(graphIri);
        console.log('🔍 Rich metadata fetched:', richMetadata);

        // Update progress: Converting to graph format
        if (isImportedOntology) {
          updateOntologyLoadingProgress('Converting to graph format...', 60);
        }

        // Convert ontology JSON to Cytoscape format with rich metadata
        const cytoscapeData = convertOntologyToCytoscapeWithMetadata(ontologyData, richMetadata);
        console.log('🔍 Cytoscape data with metadata:', cytoscapeData);

        // Update progress: Loading graph
        if (isImportedOntology) {
          updateOntologyLoadingProgress('Loading graph...', 80);
        }

        if (!ontoState.cy) return;
        ontoState.cy.elements().remove();
        ontoState.cy.add(cytoscapeData.nodes || []);
        ontoState.cy.add(cytoscapeData.edges || []);
        recomputeNextId();

        // Save to local storage for future use with timestamp
        const storageData = {
          nodes: cytoscapeData.nodes || [],
          edges: cytoscapeData.edges || [],
          timestamp: Date.now(),
          source: 'api' // Mark that this data came from API with rich metadata
        };
        localStorage.setItem(storageKeyForGraph(graphIri), JSON.stringify(storageData));

        // Update progress: Loading layout
        if (isImportedOntology) {
          updateOntologyLoadingProgress('Loading layout...', 90);
        }

        // Try to load layout from server, fallback to fit if no layout
        const layoutLoaded = await loadLayoutFromServer(graphIri);
        if (!layoutLoaded) {
          requestAnimationFrame(() => { ontoState.cy.fit(); });
        }

        // Apply saved visibility states
        updateCanvasVisibility();

        // Complete loading
        if (isImportedOntology) {
          updateOntologyLoadingProgress('Complete!', 100);
          setTimeout(() => {
            hideOntologyLoadingIndicator();
            // Apply a nice layout after loading
            setTimeout(() => {
              runAdvancedLayout('cose'); // Use force-directed layout for imported ontologies
            }, 200);
          }, 500);
        }

        console.log('Ontology loaded from API with', cytoscapeData.nodes?.length || 0, 'nodes and', cytoscapeData.edges?.length || 0, 'edges');
      }
    } else {
      console.error('Failed to load ontology from API:', response.status, response.statusText);
      if (isImportedOntology) {
        hideOntologyLoadingIndicator();
      }
    }

    // Refresh overlay imports to restore visible imported ontologies
    await overlayImportsRefresh();

    // Apply saved visibility states
    updateCanvasVisibility();

  } catch (err) {
    console.error('Error loading ontology:', err);
    // Hide loading indicator on error
    hideOntologyLoadingIndicator();
  }
}

// Ontology toolbar events and import handling
(function () {
  document.addEventListener('click', async (e) => {
    if (e.target === qs('#ontoLayoutBtn')) {
      const selectedLayout = qs('#ontoLayoutSelector').value;
      runAdvancedLayout(selectedLayout);
    } else if (e.target === qs('#ontoQuickCoseBtn')) {
      runAdvancedLayout('cose');
    } else if (e.target === qs('#ontoQuickDagreBtn')) {
      runAdvancedLayout('dagre');
    } else if (e.target === qs('#ontoForceRefreshBtn')) {
      if (activeOntologyIri) {
        // Clear local storage and force reload from API
        localStorage.removeItem(storageKeyForGraph(activeOntologyIri));
        loadGraphFromLocalOrAPI(activeOntologyIri);
      }
    } else if (e.target === qs('#ontoClearCacheBtn')) {
      // Clear all ontology localStorage and reload page
      if (confirm('Clear all cached ontology data? This will reload the page and fetch everything fresh from the server.')) {
        console.log('🧹 Clearing ontology localStorage cache...');

        // Clear all ontology-related localStorage
        Object.keys(localStorage).forEach(key => {
          if (key.includes('onto_')) {
            localStorage.removeItem(key);
            console.log('🧹 Removed:', key);
          }
        });

        console.log('🧹 Cache cleared, reloading page...');
        location.reload();
      }
    } else if (e.target === qs('#ontoFitBtn')) {
      try { if (ontoState.cy) ontoState.cy.fit(undefined, 20); } catch (_) { }
    } else if (e.target === qs('#ontoFullscreenBtn')) {
      try {
        // Use browser fullscreen instead of element fullscreen
        // Auto-hide main tree view for more screen real estate
        const treePanel = qs('#treePanel');
        const wasTreeCollapsed = treePanel?.classList.contains('tree-dock-collapsed');

        if (!document.fullscreenElement) {
          // Entering fullscreen - hide tree if not already collapsed
          if (treePanel && !wasTreeCollapsed) {
            treePanel.classList.add('tree-dock-collapsed');
            // Store that we auto-collapsed it
            treePanel.setAttribute('data-auto-collapsed', 'true');
          }
          document.documentElement.requestFullscreen?.();
        } else {
          // Exiting fullscreen - restore tree if we auto-collapsed it
          if (treePanel && treePanel.getAttribute('data-auto-collapsed') === 'true') {
            treePanel.classList.remove('tree-dock-collapsed');
            treePanel.removeAttribute('data-auto-collapsed');
          }
          document.exitFullscreen?.();
        }
      } catch (_) { }
    } else if (e.target === qs('#ontoSaveBtn')) {
      try {
        if (!activeOntologyIri) { alert('Select an ontology to save.'); return; }
        if (!ontoState.cy) { alert('No ontology data to save.'); return; }

        console.log('💾 Starting ontology save operation...');
        console.log('💾 Active ontology IRI:', activeOntologyIri);

        // Convert current canvas to ontology JSON format
        const ontologyData = convertCytoscapeToOntology();
        console.log('💾 Converted ontology data:', ontologyData);
        console.log('💾 Number of nodes:', ontologyData.nodes?.length || 0);
        console.log('💾 Number of edges:', ontologyData.edges?.length || 0);

        // Save ontology data to server
        console.log('💾 Sending ontology data to server...');
        console.warn('🔥 USING DEPRECATED API: PUT /api/ontology/ - Consider migrating to Turtle save. See docs/architecture/MULTI_ENDPOINT_ONTOLOGY_ISSUE.md');
        const response = await authenticatedFetch(`/api/ontology/?graph=${encodeURIComponent(activeOntologyIri)}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(ontologyData)
        });

        console.log('💾 Server response status:', response.status);
        console.log('💾 Server response ok:', response.ok);

        if (response.ok) {
          console.log('✅ Ontology data saved successfully!');

          // Also save layout data
          console.log('💾 Saving layout data...');
          const nodes = ontoState.cy.nodes().filter(n => !n.hasClass('imported')).map(n => ({ data: n.data(), position: n.position() }));
          const edges = ontoState.cy.edges().filter(e => !e.hasClass('imported')).map(e => ({ data: e.data() }));
          console.log('💾 Layout nodes:', nodes.length);
          console.log('💾 Layout edges:', edges.length);

          await saveLayoutToServer(activeOntologyIri, nodes, edges);
          console.log('✅ Layout data saved successfully!');
          console.log('🎉 Complete save operation successful!');

          alert('Ontology and layout saved successfully!');
        } else {
          const errorData = await response.json().catch(() => ({}));
          console.error('❌ Save failed:', errorData);
          console.error('❌ Response status:', response.status);
          console.error('❌ Response text:', await response.text().catch(() => 'Could not read response text'));
          alert('Save failed: ' + (errorData.detail || response.status));
        }
      } catch (err) {
        console.error('❌ Save error:', err);
        alert('Save error: ' + err.message);
      }
    } else if (e.target.closest && e.target.closest('#ontoLinkIdenticalBtn')) {
      // Preview: count equivalent class links that will be saved (no UI edges yet)
      try {
        if (!activeOntologyIri || !ontoState.cy) return;
        const pairs = await computeLinkedByPairs(activeOntologyIri);
        if (pairs.length) alert(`Will save ${pairs.length} owl:equivalentClass links on Save.`);
        else alert('No identical classes found');
      } catch (err) { console.error(err); alert('Link check failed'); }
    } else if (e.target === qs('#ontoExportBtn')) {
      await exportOntologyJSON();
    } else if (e.target === qs('#ontoImportBtn')) {
      const inp = qs('#ontoImportFile'); if (inp) inp.click();
    } else if (e.target === qs('#treeToggle') || e.target.closest('#treeToggle')) {
      // Main tree dock toggle
      const treePanel = qs('#treePanel');
      if (!treePanel) return;
      const collapsed = treePanel.classList.toggle('tree-dock-collapsed');
      try { localStorage.setItem('main_tree_collapsed', collapsed ? '1' : '0'); } catch (_) { }
    } else if (e.target === qs('#ontoTreeToggle') || e.target === qs('#ontoTreeToggleIcon')) {
      const sec = qs('#wb-ontology');
      if (!sec) return;
      const collapsed = sec.classList.toggle('onto-tree-collapsed');
      // CSS rotation handles the chevron direction automatically
      try { localStorage.setItem('onto_tree_collapsed', collapsed ? '1' : '0'); } catch (_) { }
      requestAnimationFrame(() => { if (ontoState.cy) ontoState.cy.resize(); });
    } else if (e.target === qs('#ontoPropsToggle') || e.target.closest('#ontoPropsToggle')) {
      const sec = qs('#wb-ontology');
      if (!sec) return;
      const collapsed = sec.classList.toggle('onto-props-collapsed');
      // CSS rotation handles the chevron direction automatically
      try { localStorage.setItem('onto_props_collapsed', collapsed ? '1' : '0'); } catch (_) { }
      // Wait for reflow before resizing Cytoscape so it fits the new grid
      requestAnimationFrame(() => { if (ontoState.cy) ontoState.cy.resize(); });
    } else if (e.target === qs('#propSaveBtn')) {
      // Save properties
      try {
        if (!ontoState.cy) return;
        const sel = ontoState.cy.$(':selected');
        const nameEl = qs('#propName');
        const attrs = getCurrentAttributes();

        if (sel.length === 1 && sel[0].isNode()) {
          const n = sel[0];
          n.data('label', nameEl.value.trim() || n.data('label'));
          // Type is read-only, don't change it

          // Capture inheritance data for classes
          if (n.data('type') === 'class') {
            const parentSelect = qs('#propParentClasses');
            const abstractCheckbox = qs('#propIsAbstract');

            console.log('🔍 Capturing inheritance data for class:', n.data('label') || n.id());
            console.log('🔍 Parent select element:', parentSelect);
            console.log('🔍 Abstract checkbox element:', abstractCheckbox);

            // Get selected parent classes
            if (parentSelect) {
              const selectedParents = Array.from(parentSelect.selectedOptions).map(opt => opt.value);
              console.log('🔍 Selected parents:', selectedParents);
              if (selectedParents.length > 0) {
                attrs.subclass_of = selectedParents;
              } else {
                attrs.subclass_of = []; // Keep as empty array instead of deleting
              }
            }

            // Get abstract flag - fix checkbox reading issue
            const directAbstractCheckbox = document.getElementById('propIsAbstract');
            if (directAbstractCheckbox) {
              const isChecked = directAbstractCheckbox.checked;
              console.log('🔍 Abstract checkbox checked (direct DOM read):', isChecked);
              console.log('🔍 Abstract checkbox DOM element:', directAbstractCheckbox);
              attrs.is_abstract = isChecked;
            } else {
              console.log('🔍 Abstract checkbox element not found in DOM');
              attrs.is_abstract = false;
            }

            console.log('🔍 Final attrs with inheritance data:', attrs);
          }

          // Add modification metadata to attributes
          const updatedAttrs = updateModificationMetadata(attrs);
          n.data('attrs', updatedAttrs);

          // Update visual styling for abstract classes
          if (n.data('type') === 'class') {
            if (updatedAttrs.is_abstract) {
              n.data('is_abstract', true);
              n.addClass('abstract-class');
            } else {
              n.removeData('is_abstract');
              n.removeClass('abstract-class');
            }

            // CRITICAL FIX: Save class inheritance data to backend
            if (activeOntologyIri && (updatedAttrs.subclass_of || updatedAttrs.is_abstract !== undefined)) {
              console.log('💾 Saving class inheritance data to backend...');
              saveClassInheritanceToBackend(n.data('label') || n.id(), updatedAttrs).catch(error => {
                console.error('❌ Failed to save inheritance data:', error);
              });
            }
          }

          // Force canvas refresh for notes to update styling
          if (n.data('type') === 'note') {
            n.style('background-color', getNoteTypeStyle(attrs.noteType || 'Note').backgroundColor);
            n.style('border-color', getNoteTypeStyle(attrs.noteType || 'Note').borderColor);
            n.style('color', getNoteTypeStyle(attrs.noteType || 'Note').textColor);
          }
        } else if (sel.length === 1 && sel[0].isEdge()) {
          const ed = sel[0];
          ed.data('predicate', nameEl.value.trim() || ed.data('predicate'));
          // Type is read-only, don't change it

          // Add modification metadata to attributes
          const updatedAttrs = updateModificationMetadata(attrs);
          ed.data('attrs', updatedAttrs);
        } else {
          // Model-level metadata save
          const pid = (activeProject && (activeProject.id || activeProject.project_id)) ? (activeProject.id || activeProject.project_id) : 'default';
          const modelName = nameEl.value.trim() || 'Ontology Model';

          // FIXED: Make model metadata ontology-specific, not just project-specific
          const ontologyKey = activeOntologyIri ? activeOntologyIri.split('/').pop() : 'default';
          const modelNameKey = `onto_model_name__${pid}__${ontologyKey}`;
          const modelAttrsKey = `onto_model_attrs__${pid}__${ontologyKey}`;

          // HANDLE IMPORTS: Save imports field to separate localStorage key
          if (attrs.imports !== undefined && activeOntologyIri) {
            const importsKey = 'onto_imports__' + encodeURIComponent(activeOntologyIri);
            try {
              // Parse imports from textarea (one per line, filter empty lines and clean syntax)
              const rawImports = attrs.imports || '';
              const importLines = rawImports.split(/[\n\r]+/)
                .map(line => {
                  let clean = line.trim();
                  // Remove Turtle syntax artifacts
                  if (clean.startsWith('@')) clean = clean.substring(1);
                  if (clean.startsWith('<') && clean.endsWith('>')) clean = clean.slice(1, -1);
                  return clean;
                })
                .filter(line => line.length > 0 && line.startsWith('http'));

              // Save imports to their specific localStorage key
              localStorage.setItem(importsKey, JSON.stringify(importLines));
              console.log(`📋 Updated imports for ${activeOntologyIri}:`, importLines);

              // Remove imports from attrs since it's stored separately
              delete attrs.imports;
            } catch (_) {
              console.log('⚠️ Error processing imports field');
            }
          }

          // Save to localStorage with ontology-specific keys
          localStorage.setItem(modelNameKey, modelName);
          localStorage.setItem(modelAttrsKey, JSON.stringify(attrs));

          // SAVE TO BACKEND RDF STORE
          if (activeOntologyIri) {
            console.log('💾 Saving model-level metadata to RDF store...');
            saveModelMetadataToBackend(activeOntologyIri, modelName, attrs);
          } else {
            console.log('⚠️ No active ontology IRI for saving model metadata');
          }
        }
        refreshOntologyTree();
        persistOntologyToLocalStorage();
        const st = qs('#propSaveStatus'); if (st) { st.textContent = 'Saved'; setTimeout(() => { const s = qs('#propSaveStatus'); if (s) s.textContent = ''; }, 1000); }
      } catch (_) {
        const st = qs('#propSaveStatus'); if (st) { st.textContent = 'Error'; setTimeout(() => { const s = qs('#propSaveStatus'); if (s) s.textContent = ''; }, 1200); }
      }
    } else if (e.target === qs('#addAttrBtn')) {
      // Add custom attribute
      const key = prompt('Enter attribute name:');
      if (key && key.trim()) {
        const container = qs('#propAttrsContainer');
        if (container) {
          const attrDiv = createAttributeField(key.trim(), { type: 'text', label: key.trim() }, '');
          container.appendChild(attrDiv);
        }
      }
    } else if (e.target === qs('#resetAttrsBtn')) {
      // Reset to template
      let objectType = 'class';
      if (ontoState.cy) {
        const sel = ontoState.cy.$(':selected');
        if (sel.length === 1) {
          objectType = sel[0].data('type') || 'class';
        } else {
          objectType = 'model';
        }
      }
    } else if (e.target.hasAttribute('data-multiplicity')) {
      // Handle multiplicity preset buttons
      const preset = e.target.getAttribute('data-multiplicity');
      applyMultiplicityPreset(preset);
    } else if (e.target.hasAttribute('data-enumeration')) {
      // Handle enumeration preset buttons
      const preset = e.target.getAttribute('data-enumeration');
      applyEnumerationPreset(preset);
      updateAttributeEditor(objectType, {});
    }
  });
  // Add input event listeners for all constraint fields
  const minCountInput = qs('#propMinCount');
  const maxCountInput = qs('#propMaxCount');
  const datatypeSelect = qs('#propDatatypeConstraint');
  const enumerationTextarea = qs('#propEnumerationValues');

  if (minCountInput) {
    minCountInput.addEventListener('input', () => {
      updateMultiplicityDisplay();
      applyMultiplicityToEdge();
    });
  }
  if (maxCountInput) {
    maxCountInput.addEventListener('input', () => {
      updateMultiplicityDisplay();
      applyMultiplicityToEdge();
    });
  }
  if (datatypeSelect) {
    datatypeSelect.addEventListener('change', () => {
      updateDatatypeDisplay();
      applyDatatypeToEdge();
    });
  }
  if (enumerationTextarea) {
    enumerationTextarea.addEventListener('input', () => {
      updateEnumerationDisplay();
      applyEnumerationToEdge();
    });
  }

  // Add input event listeners for precise positioning
  const posXInput = qs('#propPosX');
  const posYInput = qs('#propPosY');
  if (posXInput) {
    posXInput.addEventListener('input', applyPositionFromInputs);
    posXInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        applyPositionFromInputs();
        posXInput.blur();
      }
    });
  }
  if (posYInput) {
    posYInput.addEventListener('input', applyPositionFromInputs);
    posYInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        applyPositionFromInputs();
        posYInput.blur();
      }
    });
  }

  // CAD-like keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    // Only handle shortcuts when ontology workbench is active
    const isOntologyActive = document.querySelector('#wb-ontology.workbench.active');
    if (!isOntologyActive || !ontoState.cy) return;

    // Prevent shortcuts when typing in inputs
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    const isCtrl = e.ctrlKey || e.metaKey;
    const isShift = e.shiftKey;

    switch (e.key.toLowerCase()) {
      case 's':
        if (isCtrl) {
          // Ctrl+S already handled by existing save
        } else if (!isCtrl) {
          // S alone = toggle snap-to-grid (like CAD tools)
          e.preventDefault();
          toggleSnapToGrid();
        }
        break;

      case 'z':
        if (isCtrl && !isShift) {
          // Ctrl+Z = Undo
          e.preventDefault();
          performUndo();
        } else if (isCtrl && isShift) {
          // Ctrl+Shift+Z = Redo (alternative)
          e.preventDefault();
          performRedo();
        }
        break;

      case 'y':
        if (isCtrl) {
          // Ctrl+Y = Redo
          e.preventDefault();
          performRedo();
        }
        break;

      case 'c':
        if (isCtrl) {
          // Ctrl+C = Copy
          e.preventDefault();
          copySelectedElements();
        }
        break;

      case 'v':
        if (isCtrl) {
          // Ctrl+V = Paste
          e.preventDefault();
          pasteElements();
        }
        break;

      case 'a':
        if (isCtrl) {
          // Ctrl+A = Select all
          e.preventDefault();
          if (ontoState.cy) {
            ontoState.cy.elements().select();
            showTemporaryMessage(`Selected all elements`);
          }
        }
        break;

      case 'escape':
        // Escape = Clear selection (like CAD)
        if (ontoState.cy) {
          ontoState.cy.$(':selected').unselect();
          showTemporaryMessage('Selection cleared');
        }
        break;

      case 'f':
        if (isCtrl) {
          // Ctrl+F = Zoom to fit selected elements (like CAD zoom to selection)
          e.preventDefault();
          zoomToSelection();
        } else {
          // F = Fit to view (like CAD fit all)
          ontoState.cy.fit(undefined, 20);
          showTemporaryMessage('Fit to view');
        }
        break;

      case '1':
        if (isCtrl) {
          // Ctrl+1 = 1:1 zoom (100%)
          e.preventDefault();
          zoomTo100Percent();
        }
        break;

      // Alignment shortcuts (like CAD align tools)
      case 'l':
        if (isCtrl) {
          e.preventDefault();
          alignElements('left');
        }
        break;
      case 'r':
        if (isCtrl) {
          e.preventDefault();
          alignElements('right');
        }
        break;
      case 'm':
        if (isCtrl) {
          e.preventDefault();
          alignElements('center');
        }
        break;
      case 't':
        if (isCtrl) {
          e.preventDefault();
          alignElements('top');
        }
        break;
      case 'b':
        if (isCtrl) {
          e.preventDefault();
          alignElements('bottom');
        }
        break;
      case 'h':
        if (isCtrl && isShift) {
          e.preventDefault();
          alignElements('distribute-horizontal');
        }
        break;
      case 'v':
        if (isCtrl && isShift) {
          e.preventDefault();
          alignElements('distribute-vertical');
        }
        break;
    }
  });

  // Keep Cytoscape sized correctly in fullscreen and update button title
  document.addEventListener('fullscreenchange', () => {
    const btn = qs('#ontoFullscreenBtn');
    if (btn) btn.title = document.fullscreenElement ? 'Exit fullscreen' : 'Enter fullscreen';

    // Handle auto-collapsed tree restoration when exiting fullscreen via F11 or other methods
    if (!document.fullscreenElement) {
      const treePanel = qs('#treePanel');
      if (treePanel && treePanel.getAttribute('data-auto-collapsed') === 'true') {
        treePanel.classList.remove('tree-dock-collapsed');
        treePanel.removeAttribute('data-auto-collapsed');
      }
    }

    requestAnimationFrame(() => { if (ontoState.cy) ontoState.cy.resize(); });
  });
  const header = qs('#ontoTreeHeader');
  if (header) header.addEventListener('dblclick', (e) => {
    const toggleBtn = qs('#ontoTreeToggle');
    if (toggleBtn) toggleBtn.click();
  });
  const propsHeader = qs('#ontoPropsHeader');
  if (propsHeader) propsHeader.addEventListener('dblclick', (e) => {
    const toggleBtn = qs('#ontoPropsToggle');
    if (toggleBtn) toggleBtn.click();
  });

  // Visibility toggle button (now handled in renderOntologyTree where button is created)

  // Type is now read-only, no event listener needed
  const fileInput = () => qs('#ontoImportFile');
  document.addEventListener('change', async (e) => {
    if (e.target === fileInput()) {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      try {
        const text = await file.text();
        const json = JSON.parse(text);
        await importOntologyJSON(json);
      } catch (_) {
        alert('Invalid ontology JSON');
      } finally {
        e.target.value = '';
      }
    }
  });
})();

window.addEventListener('resize', () => { if (ontoState.cy) ontoState.cy.resize(); });

function getSampleProject() {
  return {
    id: 'demo',
    name: 'Sample Project',
    ontology: {
      base: { id: 'BASE-ONTO', name: 'Base Ontology', versions: ['1.0', '1.1'] },
      systems: {
        base: { id: 'SYS-BASE', name: 'Systems Ontology', versions: ['0.1', '0.2'] },
        imports: [
          { id: 'GEO', name: 'Geo Ontology', versions: ['2023-09', '2024-02'] },
          { id: 'RELY', name: 'Reliability Ontology', versions: ['1.0'] },
          { id: 'ORG', name: 'Organization Ontology', versions: ['0.9'] }
        ]
      }
    },
    requirements: [
      { id: 'R-001', title: 'The system shall ingest documents and extract requirements.' },
      { id: 'R-002', title: 'The system should support ontology-based tagging of entities.' },
      { id: 'R-003', title: 'The system must store outputs in RDF, GraphDB, and Vector Store.' }
    ],
    documents: {
      requirements: [
        { id: 'RD-01', name: 'Concept of Operations.pdf' },
        { id: 'RD-02', name: 'Capabilities Development Document.docx' }
      ],
      knowledge: [
        { id: 'KD-01', name: 'Requirements Development Instructions.md' },
        { id: 'KD-02', name: 'Industry Spec MIL-STD-961E.pdf' }
      ]
    },
    artifacts: [
      { id: 'ART-01', name: 'White Paper - Initial Draft.md' },
      { id: 'ART-02', name: 'System Architecture Diagram.png' }
    ]
  };
}

function toggleNode(li) {
  const exp = li.getAttribute('aria-expanded');
  if (exp === null) return;
  li.setAttribute('aria-expanded', exp === 'true' ? 'false' : 'true');
}

function selectNode(li) {
  qsa('.node-row').forEach(r => r.classList.remove('selected'));
  const row = li.querySelector('.node-row');
  if (row) row.classList.add('selected');
}

function highlightTreeItem(elementId, elementType) {
  // Clear current tree selection
  qsa('.node-row').forEach(r => r.classList.remove('selected'));

  // Find the corresponding tree item
  let treeItem = null;
  if (elementType === 'node') {
    treeItem = qs(`li[data-node-id="${elementId}"]`);
  } else if (elementType === 'edge') {
    treeItem = qs(`li[data-edge-id="${elementId}"]`);
  }

  if (treeItem) {
    const row = treeItem.querySelector('.node-row');
    if (row) {
      row.classList.add('selected');
      // Scroll the tree item into view
      row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }
}

function toggleVisibility(type) {
  if (ontoState.visibilityState.hasOwnProperty(type)) {
    ontoState.visibilityState[type] = !ontoState.visibilityState[type];

    // Save visibility state
    if (activeOntologyIri) {
      saveVisibilityState(activeOntologyIri, ontoState.visibilityState);
    }

    updateCanvasVisibility();
    refreshOntologyTree();
  }
}

function updateCanvasVisibility() {
  if (!ontoState.cy) return;

  console.log('🔍 Updating canvas visibility:', ontoState.visibilityState);

  // Update node visibility based on type and visibility state
  ontoState.cy.nodes().forEach(node => {
    const nodeType = node.data('type') || 'class';
    const isImported = node.hasClass('imported');
    const nodeId = node.id();

    let shouldShow = true;

    if (isImported) {
      shouldShow = ontoState.visibilityState.imported;
    } else if (nodeType === 'class') {
      shouldShow = ontoState.visibilityState.classes;
    } else if (nodeType === 'dataProperty') {
      shouldShow = ontoState.visibilityState.dataProperties;
    } else if (nodeType === 'note') {
      shouldShow = ontoState.visibilityState.notes;
    }

    // If global visibility is enabled, check individual element visibility
    // If global visibility is disabled, hide all elements of this type regardless of individual settings
    if (shouldShow && ontoState.elementVisibility.hasOwnProperty(nodeId)) {
      shouldShow = ontoState.elementVisibility[nodeId];
    }

    if (shouldShow) {
      node.show();
    } else {
      node.hide();
    }
  });

  // Update edge visibility
  ontoState.cy.edges().forEach(edge => {
    const shouldShow = ontoState.visibilityState.edges;
    if (shouldShow) {
      edge.show();
    } else {
      edge.hide();
    }
  });
}

function showVisibilityMenu() {
  const menu = document.createElement('div');
  menu.className = 'visibility-menu';
  menu.style.cssText = `
    position: fixed;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px;
    z-index: 10000;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    min-width: 200px;
  `;

  const types = [
    { key: 'classes', label: 'Classes' },
    { key: 'dataProperties', label: 'Data Properties' },
    { key: 'notes', label: 'Notes' },
    { key: 'edges', label: 'Relationships' },
    { key: 'imported', label: 'Imported Elements' }
  ];

  // Add Show All / Hide All buttons
  const showAllBtn = document.createElement('div');
  showAllBtn.style.cssText = `
    display: flex;
    align-items: center;
    padding: 6px 8px;
    cursor: pointer;
    border-radius: 4px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 4px;
  `;
  showAllBtn.innerHTML = '<span style="color: var(--text); font-weight: bold;">Show All Classes</span>';
  showAllBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    if (!ontoState.cy) return;
    ontoState.cy.nodes().forEach(node => {
      if (node.data('type') === 'class' || node.data('type') === 'note') {
        node.show();
      }
    });
    refreshOntologyTree();
  });
  menu.appendChild(showAllBtn);

  const hideAllBtn = document.createElement('div');
  hideAllBtn.style.cssText = `
    display: flex;
    align-items: center;
    padding: 6px 8px;
    cursor: pointer;
    border-radius: 4px;
    margin-bottom: 4px;
  `;
  hideAllBtn.innerHTML = '<span style="color: var(--text); font-weight: bold;">Hide All Classes</span>';
  hideAllBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    if (!ontoState.cy) return;
    ontoState.cy.nodes().forEach(node => {
      if (node.data('type') === 'class' || node.data('type') === 'note') {
        node.hide();
      }
    });
    refreshOntologyTree();
  });
  menu.appendChild(hideAllBtn);

  types.forEach(type => {
    const item = document.createElement('div');
    item.style.cssText = `
      display: flex;
      align-items: center;
      padding: 6px 8px;
      cursor: pointer;
      border-radius: 4px;
    `;

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = ontoState.visibilityState[type.key];
    checkbox.style.marginRight = '8px';

    const label = document.createElement('span');
    label.textContent = type.label;
    label.style.color = 'var(--text)';

    item.appendChild(checkbox);
    item.appendChild(label);

    item.addEventListener('click', (e) => {
      e.stopPropagation();
      checkbox.checked = !checkbox.checked;
      toggleVisibility(type.key);
    });

    menu.appendChild(item);
  });

  // Position menu near the button
  const button = qs('#ontoVisibilityToggle');
  const rect = button.getBoundingClientRect();
  menu.style.left = (rect.left - 200) + 'px';
  menu.style.top = (rect.bottom + 4) + 'px';

  document.body.appendChild(menu);

  // Close menu when clicking outside
  const closeMenu = (e) => {
    if (!menu.contains(e.target) && e.target !== button) {
      document.body.removeChild(menu);
      document.removeEventListener('click', closeMenu);
    }
  };

  setTimeout(() => {
    document.addEventListener('click', closeMenu);
  }, 100);
}

function toggleImportCollapse(importIri) {
  if (!ontoState.cy || !activeOntologyIri) return;

  const isCollapsed = ontoState.collapsedImports.has(importIri);

  if (isCollapsed) {
    // Expand: show all imported nodes and their edges, remove pseudo-node
    ontoState.collapsedImports.delete(importIri);
    const importedNodes = ontoState.cy.nodes(`[importSource="${importIri}"]`).filter(n => !n.data('isPseudo'));
    const importedEdges = ontoState.cy.edges(`[importSource="${importIri}"]`).filter(e => !e.data('isPseudo'));
    const pseudoNode = ontoState.cy.nodes(`#pseudo-import-${CSS.escape(importIri)}`);
    const pseudoEdges = ontoState.cy.edges(`[importSource="${importIri}"][isPseudo="true"]`);

    // Remove pseudo-node and its pseudo-edges
    pseudoNode.remove();
    pseudoEdges.remove();

    // Show all original imported nodes and edges
    importedNodes.show();
    importedEdges.show();
    console.log('🔍 Expanded import:', importIri, importedNodes.length, 'nodes,', importedEdges.length, 'edges');
  } else {
    // Collapse: create pseudo-node and hide all imported nodes, but maintain equivalence edges
    ontoState.collapsedImports.add(importIri);
    const importedNodes = ontoState.cy.nodes(`[importSource="${importIri}"]`).filter(n => !n.data('isPseudo'));
    const importedEdges = ontoState.cy.edges(`[importSource="${importIri}"]`).filter(e => !e.data('isPseudo'));

    if (importedNodes.length > 0) {
      // Get import name from localStorage or use IRI tail
      const imports = JSON.parse(localStorage.getItem('onto_imports__' + encodeURIComponent(activeOntologyIri || '')) || '[]');
      const importData = imports.find(imp => imp.iri === importIri);
      const importName = importData?.label || importIri.split('/').pop() || importIri;

      // Calculate center position of imported nodes
      const bbox = importedNodes.boundingBox();
      const centerX = bbox.x1 + (bbox.w / 2);
      const centerY = bbox.y1 + (bbox.h / 2);

      // Create pseudo-node representing the entire import
      const pseudoNodeId = `pseudo-import-${CSS.escape(importIri)}`;
      const pseudoNode = ontoState.cy.add({
        group: 'nodes',
        data: {
          id: pseudoNodeId,
          label: importName,
          type: 'import',
          importSource: importIri,
          isPseudo: true,
          attrs: {}
        },
        position: { x: centerX, y: centerY },
        classes: 'imported pseudo-import'
      });

      // Add position saving for pseudo-node
      pseudoNode.on('free', () => {
        const pseudoPositions = loadPseudoNodePositions(activeOntologyIri);
        pseudoPositions[pseudoNodeId] = { x: pseudoNode.position('x'), y: pseudoNode.position('y') };
        savePseudoNodePositions(activeOntologyIri, pseudoPositions);
      });

      // Hide all imported nodes
      importedNodes.hide();

      // Create equivalence edges from pseudo-node to base ontology classes
      const equivalenceEdges = importedEdges.filter(edge => {
        const source = edge.source();
        const target = edge.target();
        const isEquivalence = edge.data('predicate') === 'equivalentClass';
        const connectsToBase = !source.hasClass('imported') || !target.hasClass('imported');
        return isEquivalence && connectsToBase;
      });

      // Create new equivalence edges from pseudo-node to base classes
      equivalenceEdges.forEach(edge => {
        const baseNode = edge.source().hasClass('imported') ? edge.target() : edge.source();
        const equivEdgeId = `pseudo-equiv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

        ontoState.cy.add({
          group: 'edges',
          data: {
            id: equivEdgeId,
            source: pseudoNodeId,
            target: baseNode.id(),
            predicate: 'equivalentClass',
            type: 'objectProperty',
            importSource: importIri,
            isPseudo: true,
            attrs: {}
          },
          classes: 'imported imported-equivalence pseudo-equivalence'
        });
      });

      // Hide original edges
      importedEdges.hide();

      console.log('🔍 Collapsed import:', importIri, 'created pseudo-node with', equivalenceEdges.length, 'equivalence edges');
    }
  }

  // Save the collapsed state
  saveCollapsedImports(activeOntologyIri, ontoState.collapsedImports);

  // Update the tree to reflect the change
  refreshOntologyTree();
}

function toggleAllImportsCollapse() {
  if (!ontoState.cy || !activeOntologyIri) return;

  const imports = JSON.parse(localStorage.getItem('onto_imports__' + encodeURIComponent(activeOntologyIri || '')) || '[]');
  const allCollapsed = imports.every(imp => ontoState.collapsedImports.has(imp));

  if (allCollapsed) {
    // Expand all
    imports.forEach(imp => {
      ontoState.collapsedImports.delete(imp);
      const importedNodes = ontoState.cy.nodes(`[importSource="${imp}"]`).filter(n => !n.data('isPseudo'));
      const importedEdges = ontoState.cy.edges(`[importSource="${imp}"]`).filter(e => !e.data('isPseudo'));
      const pseudoNode = ontoState.cy.nodes(`#pseudo-import-${CSS.escape(imp)}`);
      const pseudoEdges = ontoState.cy.edges(`[importSource="${imp}"][isPseudo="true"]`);

      // Remove pseudo-node and its pseudo-edges
      pseudoNode.remove();
      pseudoEdges.remove();

      // Show all original imported nodes and edges
      importedNodes.show();
      importedEdges.show();
    });
    console.log('🔍 Expanded all imports');
  } else {
    // Collapse all
    imports.forEach(imp => {
      ontoState.collapsedImports.add(imp);
      const importedNodes = ontoState.cy.nodes(`[importSource="${imp}"]`).filter(n => !n.data('isPseudo'));
      const importedEdges = ontoState.cy.edges(`[importSource="${imp}"]`).filter(e => !e.data('isPseudo'));

      if (importedNodes.length > 0) {
        // Get import name from localStorage or use IRI tail
        const importData = imports.find(importData => importData.iri === imp);
        const importName = importData?.label || imp.split('/').pop() || imp;

        // Calculate center position of imported nodes
        const bbox = importedNodes.boundingBox();
        const centerX = bbox.x1 + (bbox.w / 2);
        const centerY = bbox.y1 + (bbox.h / 2);

        // Create pseudo-node representing the entire import
        const pseudoNodeId = `pseudo-import-${CSS.escape(imp)}`;
        const pseudoNode = ontoState.cy.add({
          group: 'nodes',
          data: {
            id: pseudoNodeId,
            label: importName,
            type: 'import',
            importSource: imp,
            isPseudo: true,
            attrs: {}
          },
          position: { x: centerX, y: centerY },
          classes: 'imported pseudo-import'
        });

        // Add position saving for pseudo-node
        pseudoNode.on('free', () => {
          const pseudoPositions = loadPseudoNodePositions(activeOntologyIri);
          pseudoPositions[pseudoNodeId] = { x: pseudoNode.position('x'), y: pseudoNode.position('y') };
          savePseudoNodePositions(activeOntologyIri, pseudoPositions);
        });

        // Hide all imported nodes
        importedNodes.hide();

        // Create equivalence edges from pseudo-node to base ontology classes
        const equivalenceEdges = importedEdges.filter(edge => {
          const source = edge.source();
          const target = edge.target();
          const isEquivalence = edge.data('predicate') === 'equivalentClass';
          const connectsToBase = !source.hasClass('imported') || !target.hasClass('imported');
          return isEquivalence && connectsToBase;
        });

        // Create new equivalence edges from pseudo-node to base classes
        equivalenceEdges.forEach(edge => {
          const baseNode = edge.source().hasClass('imported') ? edge.target() : edge.source();
          const equivEdgeId = `pseudo-equiv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

          ontoState.cy.add({
            group: 'edges',
            data: {
              id: equivEdgeId,
              source: pseudoNodeId,
              target: baseNode.id(),
              predicate: 'equivalentClass',
              type: 'objectProperty',
              importSource: imp,
              isPseudo: true,
              attrs: {}
            },
            classes: 'imported imported-equivalence pseudo-equivalence'
          });
        });

        // Hide original edges
        importedEdges.hide();
      }
    });
    console.log('🔍 Collapsed all imports');
  }

  // Save the collapsed state
  saveCollapsedImports(activeOntologyIri, ontoState.collapsedImports);

  // Update the tree to reflect the change
  refreshOntologyTree();
}

function handleKey(e, li) {
  const LEFT = 37, UP = 38, RIGHT = 39, DOWN = 40, ENTER = 13, SPACE = 32;
  const exp = li.getAttribute('aria-expanded');
  switch (e.keyCode) {
    case LEFT:
      if (exp === 'true') { toggleNode(li); } else { focusParent(li); }
      e.preventDefault(); break;
    case RIGHT:
      if (exp === 'false') { toggleNode(li); } else { focusFirstChild(li); }
      e.preventDefault(); break;
    case UP:
      focusPrev(li); e.preventDefault(); break;
    case DOWN:
      focusNext(li); e.preventDefault(); break;
    case ENTER:
    case SPACE:
      selectNode(li); handleTreeSelection(li).catch(console.error); e.preventDefault(); break;
  }
}

function focusParent(li) {
  const parentLi = li.parentElement.closest('li[role="treeitem"]');
  if (parentLi) (parentLi.querySelector('.node-row') || parentLi).focus();
}
function focusFirstChild(li) {
  const child = li.querySelector('ul[role="group"] > li[role="treeitem"] .node-row');
  if (child) child.focus();
}
function visibleTreeItems() {
  const acc = [];
  function addVisible(container) {
    const items = Array.from(container.children).filter(n => n.matches('li[role="treeitem"]'));
    items.forEach(li => {
      acc.push(li);
      const exp = li.getAttribute('aria-expanded');
      if (exp === 'true') {
        const group = li.querySelector('ul[role="group"]');
        if (group) addVisible(group);
      }
    });
  }
  addVisible(qs('#treeRoot'));
  return acc;
}
function focusPrev(li) {
  const list = visibleTreeItems();
  const idx = list.indexOf(li);
  if (idx > 0) (list[idx - 1].querySelector('.node-row') || list[idx - 1]).focus();
}
function focusNext(li) {
  const list = visibleTreeItems();
  const idx = list.indexOf(li);
  if (idx >= 0 && idx < list.length - 1) (list[idx + 1].querySelector('.node-row') || list[idx + 1]).focus();
}

// Boot
initAuth();

// Global error handler for unhandled authentication errors
window.addEventListener('unhandledrejection', (event) => {
  if (event.reason && event.reason.message === 'Authentication required') {
    console.warn('Unhandled authentication error, redirecting to login...');
    handleAuthFailure();
    event.preventDefault(); // Prevent the error from being logged to console
  }
});

// Add toast notification system if it doesn't exist
if (!window.toast) {
  window.toast = function (message, isError = false) {
    // Create a simple toast notification
    const toast = document.createElement('div');
    toast.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: ${isError ? 'var(--err)' : 'var(--ok)'};
      color: white;
      padding: 12px 16px;
      border-radius: 6px;
      z-index: 10000;
      font-size: 14px;
      max-width: 300px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;
    toast.textContent = message;
    document.body.appendChild(toast);

    // Auto-remove after 3 seconds
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 3000);
  };
}

// Per-project restore happens inside renderTree; avoid global restore that can clobber state
// Save shortcut Ctrl/Cmd+S
document.addEventListener('keydown', async (e) => {
  const isSave = (e.key === 's' || e.key === 'S') && (e.ctrlKey || e.metaKey);
  if (!isSave) return;
  e.preventDefault();
  try {
    if (!activeOntologyIri) { alert('Select an ontology to save.'); return; }

    console.log('💾 Starting keyboard shortcut save (Ctrl+S)...');
    console.log('💾 Active ontology IRI:', activeOntologyIri);

    const ttl = toTurtle(activeOntologyIri);
    console.log('💾 Generated Turtle data length:', ttl.length);
    console.log('💾 Turtle data preview:', ttl.substring(0, 200) + '...');

    console.log('💾 Sending Turtle data to Fuseki...');
    const res = await fetch(`/api/ontology/save?graph=${encodeURIComponent(activeOntologyIri)}`, { method: 'POST', headers: { 'Content-Type': 'text/turtle' }, body: ttl });

    console.log('💾 Fuseki response status:', res.status);
    console.log('💾 Fuseki response ok:', res.ok);

    const json = await res.json().catch(() => ({}));
    if (res.ok) {
      console.log('✅ Ontology saved to Fuseki successfully!');

      // Also save layout data when using Ctrl+S
      if (ontoState.cy) {
        console.log('💾 Saving layout data...');
        const nodes = ontoState.cy.nodes().filter(n => !n.hasClass('imported')).map(n => ({ data: n.data(), position: n.position() }));
        const edges = ontoState.cy.edges().filter(e => !e.hasClass('imported')).map(e => ({ data: e.data() }));

        console.log('💾 Layout nodes:', nodes.length);
        console.log('💾 Layout edges:', edges.length);

        await saveLayoutToServer(activeOntologyIri, nodes, edges);
        console.log('✅ Layout data saved successfully!');
      }

      console.log('🎉 Complete save operation successful!');

      // Check for changes notification
      if (json.changes && json.changes.total > 0) {
        console.log('🔔 Changes detected:', json.changes);
        showChangeNotification(json.changes, activeOntologyIri);
      } else {
        alert('Ontology and layout saved successfully!');
      }
    } else {
      console.error('❌ Fuseki save failed:', json);
      console.error('❌ Response status:', res.status);
      alert('Save failed: ' + (json.detail || res.status));
    }
  } catch (err) {
    console.error('❌ Keyboard shortcut save error:', err);
    alert('Save error: ' + err.message);
  }
}, false);

// Delete selected canvas entities (nodes/edges) for current ontology only
function performDelete() {
  if (!(qs('#wb-ontology') && qs('#wb-ontology').classList.contains('active'))) return false;
  if (!ontoState.cy) return false;
  const sel = ontoState.cy.$(':selected');
  if (!sel || sel.length === 0) return false;
  ontoState.cy.remove(sel);
  refreshOntologyTree();
  persistOntologyToLocalStorage();
  return true;
}
function handleDeleteKey(e) {
  const key = e.key || e.code;
  const tgt = e.target;
  const isTyping = tgt && (tgt.tagName === 'INPUT' || tgt.tagName === 'TEXTAREA' || tgt.isContentEditable);
  const inline = qs('#ontoInlineEdit');
  const inlineVisible = inline ? (getComputedStyle(inline).display !== 'none') : false;
  if (isTyping || inlineVisible) return;
  if ((key === 'Delete' || key === 'Backspace') && ontoState.cy) {
    const ok = performDelete();
    if (ok) { e.preventDefault(); e.stopPropagation(); }
  }
}
document.addEventListener('keydown', handleDeleteKey, false);
window.addEventListener('keydown', handleDeleteKey, true);
// Keyup fallback in case keydown is intercepted by browser/OS
document.addEventListener('keyup', handleDeleteKey, false);
// Toolbar delete
document.addEventListener('click', (e) => {
  if (e.target === qs('#ontoDeleteBtn')) {
    performDelete();
  }
});

// Files workbench state + helpers

// Export main initialization function
export function initializeOntologyWorkbench() {
  console.log('🔷 Initializing Ontology Workbench (complete version)...');
  ensureOntologyInitialized();
  setupOntologyEventListeners();
  
  // Load initial ontology if project is active
  const state = getAppState();
  if (state.activeProject?.projectId) {
    loadProjectOntologies(state.activeProject.projectId);
  }
  
  console.log('✅ Ontology Workbench initialized');
}

// Export state for debugging
export { ontoState, activeOntologyIri, activeProject };

// Make available globally for compatibility
window.ensureOntologyInitialized = ensureOntologyInitialized;
window.ontoState = ontoState;
window.refreshOntologyTree = refreshOntologyTree;
window.updatePropertiesPanelFromSelection = updatePropertiesPanelFromSelection;
