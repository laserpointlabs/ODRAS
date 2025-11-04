/**
 * Application Initialization Module
 * 
 * Handles application startup, configuration loading, and initialization sequence.
 */

import { apiClient } from './api-client.js';
import { getAppState, updateAppState, persistState } from './state-manager.js';
import { emitEvent, subscribeToEvent } from './event-bus.js';

// Use apiClient as ApiClient (following pattern from other modules)
const ApiClient = apiClient;

/**
 * Initializes the application by loading configurations and setting up global listeners.
 */
export async function initializeApplication() {
  console.log('🚀 Initializing ODRAS Frontend...');

  // Check authentication and show appropriate view
  await checkAuthenticationAndShowView();

  // Load installation configuration
  await loadInstallationConfig();

  // Load RAG and File Processing configurations (requires auth)
  await loadAdminConfigs();

  // Set up global event listeners
  setupGlobalEventListeners();

  // Apply initial URL state
  applyURLState();

  console.log('✅ ODRAS Frontend Initialized.');
  emitEvent('app:initialized');
}

/**
 * Checks authentication status and shows appropriate view (mainView or authView)
 */
async function checkAuthenticationAndShowView() {
  console.log('🔐 Checking authentication status...');
  const state = getAppState();
  const authView = document.getElementById('authView');
  const mainView = document.getElementById('mainView');
  const logoutBtn = document.getElementById('logoutBtn');

  if (!authView || !mainView) {
    console.warn('⚠️ Auth/main view elements not found', { authView: !!authView, mainView: !!mainView });
    return;
  }

  console.log('🔐 Auth check - token exists:', !!state.token);

  // Check if user has a token
  if (state.token) {
    try {
      // Verify token is valid by checking current user
      const user = await ApiClient.getCurrentUser();
      console.log('🔐 Auth check - user response:', user);
      if (user && user.user_id) {
        // User is authenticated - show main view
        updateAppState({ user: user }, false);
        authView.style.display = 'none';
        mainView.style.display = 'grid';
        if (logoutBtn) logoutBtn.style.display = 'block';
        console.log('✅ User authenticated - showing main view:', user.username);
        return;
      }
    } catch (error) {
      console.log('ℹ️ Token invalid or expired:', error.message);
      // Clear invalid token
      updateAppState({ token: null, user: null }, true);
    }
  }

  // User not authenticated - show auth view
  console.log('ℹ️ User not authenticated - showing login form');
  updateAppState({ token: null, user: null }, false);
  authView.style.display = 'grid';
  mainView.style.display = 'none';
  if (logoutBtn) logoutBtn.style.display = 'none';
  console.log('✅ Auth view shown, main view hidden');
}

/**
 * Loads installation configuration from the backend.
 */
async function loadInstallationConfig() {
  try {
    const config = await ApiClient.get('/api/installation/config');
    updateAppState({ installationConfig: { ...getAppState().installationConfig, ...config } }, false);
    console.log('🔧 Loaded installation config:', getAppState().installationConfig);
  } catch (error) {
    console.warn('⚠️ Failed to load installation config, using defaults:', error);
  }
}

/**
 * Loads RAG and File Processing configurations from the backend (admin endpoints).
 */
async function loadAdminConfigs() {
  try {
    const ragConfig = await ApiClient.get('/api/admin/rag-config');
    updateAppState({ ragConfig: ragConfig }, false);
    console.log('🔧 Loaded RAG config:', ragConfig);
  } catch (error) {
    console.warn('⚠️ Failed to load RAG config (admin access may be required):', error);
  }

  try {
    const fileProcessingConfig = await ApiClient.get('/api/admin/file-processing-config');
    updateAppState({ fileProcessingConfig: fileProcessingConfig }, false);
    console.log('🔧 Loaded File Processing config:', fileProcessingConfig);
  } catch (error) {
    console.warn('⚠️ Failed to load File Processing config (admin access may be required):', error);
  }

  // BPMN models endpoint doesn't exist yet - skip for now
  // try {
  //   const bpmnModels = await ApiClient.get('/api/admin/bpmn-models');
  //   updateAppState({ bpmnModels: bpmnModels }, false);
  //   console.log('🔧 Loaded BPMN Models:', bpmnModels);
  // } catch (error) {
  //   console.warn('⚠️ Failed to load BPMN Models (admin access may be required):', error);
  // }
  persistState(); // Persist all loaded configs
}

/**
 * Sets up global event listeners, e.g., for URL changes, beforeunload.
 */
function setupGlobalEventListeners() {
  // Persist state before unload
  window.addEventListener('beforeunload', () => {
    persistState();
  });

  // Listen for auth:unauthorized event to clear token and show login
  subscribeToEvent('auth:unauthorized', (detail) => {
    console.warn('Authentication unauthorized:', detail);
    updateAppState({ token: null, user: null }, true);
    showAuthView();
  });

  // Listen for auth:loggedIn event to show main view
  subscribeToEvent('auth:loggedIn', async (userData) => {
    console.log('✅ User logged in:', userData);
    showMainView();
    
    // Load projects after login
    const { initializeProjectManager } = await import('/static/js/core/project-manager.js');
    await initializeProjectManager();
  });

  // Listen for auth:loggedOut event to show auth view
  subscribeToEvent('auth:loggedOut', () => {
    console.log('ℹ️ User logged out');
    showAuthView();
  });

  // Listen for state changes to update URL
  subscribeToEvent('state:updated', (newState) => {
    updateURL(newState.activeProject?.projectId, newState.activeWorkbench);
  });
}

/**
 * Updates the browser's URL based on the current application state.
 * @param {string|null} projectId - The active project ID.
 * @param {string|null} workbench - The active workbench ID.
 */
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

/**
 * Applies the initial URL state to the application state.
 */
function applyURLState() {
  try {
    const url = new URL(window.location);
    const projectId = url.searchParams.get('project');
    const workbench = url.searchParams.get('wb');

    if (projectId) {
      // In a real app, you'd fetch project details here
      updateAppState({ activeProject: { projectId: projectId, name: `Project ${projectId}` } }, false);
    }
    if (workbench) {
      updateAppState({ activeWorkbench: workbench }, false);
    }
    persistState(); // Persist changes from URL
  } catch (error) {
    console.warn('Failed to apply URL state:', error);
  }
}

/**
 * Shows the main application view and hides the auth view
 */
function showMainView() {
  const authView = document.getElementById('authView');
  const mainView = document.getElementById('mainView');
  const logoutBtn = document.getElementById('logoutBtn');

  if (authView) authView.style.display = 'none';
  if (mainView) mainView.style.display = 'grid';
  if (logoutBtn) logoutBtn.style.display = 'block';
}

/**
 * Shows the authentication view and hides the main view
 */
function showAuthView() {
  const authView = document.getElementById('authView');
  const mainView = document.getElementById('mainView');
  const logoutBtn = document.getElementById('logoutBtn');

  if (authView) authView.style.display = 'grid';
  if (mainView) mainView.style.display = 'none';
  if (logoutBtn) logoutBtn.style.display = 'none';
}
