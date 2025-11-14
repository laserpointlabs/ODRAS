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

  // Initialize default workbench after a short delay to ensure DOM is ready
  setTimeout(() => {
    initializeDefaultWorkbench();
  }, 100);

  console.log('✅ Workbench Manager initialized');
}

/**
 * Initialize the default workbench on page load
 */
function initializeDefaultWorkbench() {
  // Check URL for workbench parameter
  const urlParams = new URLSearchParams(window.location.search);
  const urlWorkbench = urlParams.get('wb');
  
  // Check localStorage for saved workbench
  const savedWorkbench = localStorage.getItem('active_workbench');
  
  // Check for workbench with active class in HTML
  const activeWorkbenchEl = document.querySelector('.workbench.active');
  const htmlWorkbench = activeWorkbenchEl ? activeWorkbenchEl.id.replace('wb-', '') : null;
  
  // Priority: URL > localStorage > HTML > default
  const defaultWorkbench = urlWorkbench || savedWorkbench || htmlWorkbench || 'ontology';
  
  console.log('🔷 Initializing default workbench:', defaultWorkbench);
  switchWorkbench(defaultWorkbench);
}

/**
 * Switch to a specific workbench
 * 
 * This is the central function for showing/hiding workbenches.
 * All workbench visibility is controlled through this function.
 * 
 * @param {string} workbenchId - The ID of the workbench to activate (e.g., 'ontology', 'requirements')
 */
export function switchWorkbench(workbenchId) {
  if (!workbenchId) {
    console.warn('⚠️ switchWorkbench called with no workbenchId');
    return;
  }

  console.log('🔄 Switching to workbench:', workbenchId);

  // Step 1: Update active icon in iconbar
  document.querySelectorAll('.iconbar .icon').forEach(icon => {
    icon.classList.remove('active');
  });
  const activeIcon = document.querySelector(`.iconbar .icon[data-wb="${workbenchId}"]`);
  if (activeIcon) {
    activeIcon.classList.add('active');
  } else {
    console.warn(`⚠️ Icon not found for workbench: ${workbenchId}`);
  }

  // Step 2: Hide all workbench sections (CSS: .workbench { display: none })
  document.querySelectorAll('.workbench').forEach(wb => {
    wb.classList.remove('active');
  });

  // Step 3: Show selected workbench (CSS: .workbench.active { display: flex })
  const targetWorkbench = document.getElementById(`wb-${workbenchId}`);
  if (targetWorkbench) {
    targetWorkbench.classList.add('active');
    console.log(`✅ Workbench ${workbenchId} is now visible`);
    
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
      // Initialize ontology workbench
      import('/static/js/workbenches/ontology/ontology-ui.js')
        .then(module => {
          if (module.initializeOntologyWorkbench) {
            module.initializeOntologyWorkbench();
          } else if (typeof window.ensureOntologyInitialized === 'function') {
            // Fallback to legacy function
            window.ensureOntologyInitialized();
          }
          // Resize cytoscape if available
          if (window.ontoState && window.ontoState.cy) {
            setTimeout(() => window.ontoState.cy.resize(), 100);
          }
        })
        .catch(err => {
          console.warn('Could not load ontology workbench:', err);
          // Fallback to legacy function
          if (typeof window.ensureOntologyInitialized === 'function') {
            window.ensureOntologyInitialized();
          }
        });
    } else if (workbenchId === 'project') {
      // Load project info - use event system
      const state = getAppState();
      if (state.activeProject?.projectId) {
        emitEvent('project:selected', state.activeProject.projectId);
      } else {
        // Show no project message
        const projectInfoCard = document.getElementById('projectInfoCard');
        if (projectInfoCard) {
          projectInfoCard.innerHTML = `
            <div style="text-align: center; color: var(--muted);">
              <h3>No Project Selected</h3>
              <p>Select a project from the dropdown or create a new one to view project information.</p>
            </div>
          `;
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
