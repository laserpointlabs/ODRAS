/**
 * Workbench Manager Module
 * 
 * Handles workbench switching and initialization.
 */

import { updateAppState, getAppState } from './state-manager.js';
import { emitEvent, subscribeToEvent } from './event-bus.js';

/**
 * Initialize workbench switching functionality
 */
export function initializeWorkbenchManager() {
  console.log('🔄 Initializing Workbench Manager...');

  // Wire up iconbar workbench switching
  const iconbar = document.querySelector('.iconbar');
  if (iconbar) {
    iconbar.addEventListener('click', (e) => {
      const icon = e.target.closest('.icon[data-wb]');
      if (icon) {
        const workbenchId = icon.getAttribute('data-wb');
        switchWorkbench(workbenchId);
      }
    });
  }

  // Subscribe to workbench switch events
  subscribeToEvent('workbench:switch', (data) => {
    if (data.workbench) {
      switchWorkbench(data.workbench);
    }
  });

  console.log('✅ Workbench Manager initialized');
}

/**
 * Switch to a specific workbench
 */
function switchWorkbench(workbenchId) {
  console.log('🔄 Switching to workbench:', workbenchId);

  // Update active icon in iconbar
  document.querySelectorAll('.iconbar .icon').forEach(icon => {
    icon.classList.remove('active');
  });
  const activeIcon = document.querySelector(`.iconbar .icon[data-wb="${workbenchId}"]`);
  if (activeIcon) {
    activeIcon.classList.add('active');
  }

  // Hide all workbench sections
  document.querySelectorAll('.workbench').forEach(wb => {
    wb.classList.remove('active');
  });

  // Show selected workbench
  const targetWorkbench = document.getElementById(`wb-${workbenchId}`);
  if (targetWorkbench) {
    targetWorkbench.classList.add('active');
    
    // Initialize workbench-specific functionality
    if (workbenchId === 'requirements') {
      // Initialize Requirements Workbench
      console.log('📋 Activating Requirements Workbench');
      if (typeof window.initializeRequirementsWorkbench === 'function') {
        window.initializeRequirementsWorkbench();
      } else {
        // Dynamic import if available
        import('/static/js/workbenches/requirements/requirements-ui.js')
          .then(module => {
            if (module.initializeRequirementsWorkbench) {
              module.initializeRequirementsWorkbench();
            }
          })
          .catch(err => console.warn('Could not load requirements workbench:', err));
      }
    } else if (workbenchId === 'ontology') {
      // Ensure ontology is initialized
      if (typeof window.ensureOntologyInitialized === 'function') {
        window.ensureOntologyInitialized();
      }
      // Resize cytoscape if available
      if (window.ontoState && window.ontoState.cy) {
        setTimeout(() => window.ontoState.cy.resize(), 100);
      }
    } else if (workbenchId === 'project') {
      // Load project info if available
      if (typeof window.loadProjectInfo === 'function') {
        const state = getAppState();
        if (state.activeProject?.projectId) {
          window.loadProjectInfo();
        }
      }
    } else if (workbenchId === 'admin') {
      // Load admin data if available
      if (typeof window.loadPrefixes === 'function') window.loadPrefixes();
      if (typeof window.loadDomains === 'function') window.loadDomains();
      const state = getAppState();
      if (state.token && typeof window.loadNamespaces === 'function') {
        window.loadNamespaces();
      }
    }
  } else {
    console.warn(`⚠️ Workbench section not found: wb-${workbenchId}`);
  }

  // Update app state and persist
  updateAppState({ activeWorkbench: workbenchId }, true);
  
  // Persist to localStorage (like old app.html)
  try {
    localStorage.setItem('active_workbench', workbenchId);
  } catch (e) {
    console.warn('Failed to persist workbench state:', e);
  }

  // Update URL
  const state = getAppState();
  const url = new URL(window.location);
  if (workbenchId) {
    url.searchParams.set('wb', workbenchId);
  } else {
    url.searchParams.delete('wb');
  }
  if (state.activeProject?.projectId) {
    url.searchParams.set('project', state.activeProject.projectId);
  }
  window.history.replaceState({}, '', url);

  // Emit event for other modules
  emitEvent('workbench:switched', workbenchId);
}
