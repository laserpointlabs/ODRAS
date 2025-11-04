/**
 * Project Manager Module
 * 
 * Handles project loading, selection, and creation.
 */

import { apiClient } from './api-client.js';
import { updateAppState, getAppState } from './state-manager.js';
import { emitEvent, subscribeToEvent } from './event-bus.js';

const ApiClient = apiClient;

/**
 * Initialize project management functionality
 */
export async function initializeProjectManager() {
  console.log('📁 Initializing Project Manager...');

  // Wire up project creation button
  const addNodeBtn = document.getElementById('addNodeBtn');
  if (addNodeBtn) {
    addNodeBtn.addEventListener('click', () => {
      showCreateProjectModal();
    });
  }

  // Wire up project selector
  const projectSelect = document.getElementById('projectSelect2');
  if (projectSelect) {
    projectSelect.addEventListener('change', (e) => {
      const projectId = e.target.value;
      if (projectId) {
        selectProject(projectId);
      }
    });
  }

  // Load projects if user is authenticated
  const state = getAppState();
  if (state.token) {
    await loadProjects();
  }

  // Reload projects after login
  subscribeToEvent('auth:loggedIn', async () => {
    await loadProjects();
  });

  console.log('✅ Project Manager initialized');
}

/**
 * Load projects from API and populate dropdown
 */
export async function loadProjects() {
  try {
    console.log('📁 Loading projects...');
    const response = await ApiClient.get('/api/projects');
    const projects = response.projects || [];

    // Update project selector
    const projectSelect = document.getElementById('projectSelect2');
    if (projectSelect) {
      if (projects.length === 0) {
        projectSelect.innerHTML = '<option value="" disabled selected>Create Project...</option>';
        projectSelect.disabled = true;
      } else {
        projectSelect.innerHTML = projects.map(p => {
          const id = p.id || p.project_id || p.projectId;
          const name = p.name || p.project_name || 'Project';
          return `<option value="${id}">${name}</option>`;
        }).join('');
        projectSelect.disabled = false;

        // Select first project or previously selected
        const state = getAppState();
        if (state.activeProject?.projectId && projects.find(p => (p.id || p.project_id || p.projectId) === state.activeProject.projectId)) {
          projectSelect.value = state.activeProject.projectId;
          await selectProject(state.activeProject.projectId);
        } else if (projects.length > 0) {
          const firstProject = projects[0];
          const firstId = firstProject.id || firstProject.project_id || firstProject.projectId;
          projectSelect.value = firstId;
          await selectProject(firstId);
        }
      }
    }

    console.log(`✅ Loaded ${projects.length} projects`);
    emitEvent('projects:loaded', projects);
  } catch (error) {
    console.error('❌ Failed to load projects:', error);
    const projectSelect = document.getElementById('projectSelect2');
    if (projectSelect) {
      projectSelect.innerHTML = '<option value="" disabled selected>Error loading projects</option>';
      projectSelect.disabled = true;
    }
  }
}

/**
 * Select a project
 */
export async function selectProject(projectId) {
  console.log('📁 Selecting project:', projectId);
  
  try {
    const response = await ApiClient.get(`/api/projects/${projectId}`);
    const project = response.project || response;
    
    updateAppState({ 
      activeProject: {
        projectId: projectId,
        name: project.name || project.project_name || 'Project',
        ...project
      }
    }, true);

    emitEvent('project:selected', projectId);
    console.log('✅ Project selected:', project.name || projectId);
  } catch (error) {
    console.error('❌ Failed to load project details:', error);
  }
}

/**
 * Show create project modal (from app.html)
 */
function showCreateProjectModal() {
  // Prevent duplicate modals
  const existingModals = document.querySelectorAll('.modal');
  if (existingModals.length > 0) {
    console.log('🔧 Removing existing modals before creating new one');
    existingModals.forEach(modal => modal.remove());
  }

  const modal = document.createElement('div');
  modal.className = 'modal';
  modal.style.cssText = `
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(0,0,0,0.8); display: flex; align-items: center;
    justify-content: center; z-index: 10000;
  `;

  modal.innerHTML = `
    <div style="background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 24px; min-width: 400px; max-width: 600px; max-height: 90vh; overflow-y: auto;">
      <h3 style="margin: 0 0 16px 0; color: var(--text);">Create New Project</h3>

      <div style="margin-bottom: 16px;">
        <label style="display: block; margin-bottom: 6px; color: var(--text);">Project Name:</label>
        <input type="text" id="projectName" placeholder="e.g., f35-avionics" 
          style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px; background: var(--panel-2); color: var(--text); box-sizing: border-box;" />
        <div style="font-size: 0.85em; color: var(--muted); margin-top: 4px;">
          Alphanumeric characters, hyphens, and underscores only
        </div>
      </div>

      <div style="margin-bottom: 16px;">
        <label style="display: block; margin-bottom: 6px; color: var(--text);">Namespace:</label>
        <select id="projectNamespace" 
          style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px; background: var(--panel-2); color: var(--text); box-sizing: border-box;">
          <option value="">Loading namespaces...</option>
        </select>
        <div style="font-size: 0.85em; color: var(--muted); margin-top: 4px;">
          Select from available released namespaces
        </div>
      </div>

      <div style="margin-bottom: 16px;">
        <label style="display: block; margin-bottom: 6px; color: var(--text);">Domain:</label>
        <select id="projectDomain" 
          style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px; background: var(--panel-2); color: var(--text); box-sizing: border-box;">
          <option value="">Loading domains...</option>
        </select>
        <div style="font-size: 0.85em; color: var(--muted); margin-top: 4px;">
          Select the functional domain for this project
        </div>
      </div>

      <div style="margin-bottom: 16px;">
        <label style="display: block; margin-bottom: 6px; color: var(--text);">Description (optional):</label>
        <textarea id="projectDescription" placeholder="Brief description of the project..." 
          style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px; background: var(--panel-2); color: var(--text); height: 80px; resize: vertical; box-sizing: border-box; font-family: inherit;"></textarea>
      </div>

      <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
        <button class="btn" id="cancelProjectBtn" 
          style="background: var(--panel-2); color: var(--text); border-color: var(--border); padding: 8px 16px;">
          Cancel
        </button>
        <button class="btn" id="createProjectBtn" 
          style="background: var(--accent); color: white; border-color: var(--accent); padding: 8px 16px;">
          Create Project
        </button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // Load released namespaces and active domains
  loadReleasedNamespaces();
  loadActiveDomains();

  // Wire up cancel button
  const cancelBtn = modal.querySelector('#cancelProjectBtn');
  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      modal.remove();
    });
  }

  // Wire up create button
  const createBtn = modal.querySelector('#createProjectBtn');
  if (createBtn) {
    createBtn.addEventListener('click', async () => {
      await handleCreateProject(modal);
    });
  }

  // Close on backdrop click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.remove();
    }
  });

  // Close on Escape key
  const escapeHandler = (e) => {
    if (e.key === 'Escape') {
      modal.remove();
      document.removeEventListener('keydown', escapeHandler);
    }
  };
  document.addEventListener('keydown', escapeHandler);
}

/**
 * Load released namespaces for project creation
 */
async function loadReleasedNamespaces() {
  try {
    console.log('🔧 Loading released namespaces...');
    const response = await ApiClient.get('/api/namespaces/released');
    const namespaces = response.namespaces || response || [];

    const select = document.getElementById('projectNamespace');
    if (!select) return;

    if (namespaces.length === 0) {
      select.innerHTML = '<option value="">No released namespaces available</option>';
      return;
    }

    select.innerHTML = '<option value="">Select a namespace...</option>' +
      namespaces.map(ns => {
        const id = ns.id || ns.namespace_id;
        const path = ns.path || ns.namespace_path || '';
        const name = ns.name || ns.namespace_name || '';
        return `<option value="${id}">${path} - ${name}</option>`;
      }).join('');
  } catch (error) {
    console.error('Error loading released namespaces:', error);
    const select = document.getElementById('projectNamespace');
    if (select) {
      select.innerHTML = '<option value="">Error loading namespaces</option>';
    }
  }
}

/**
 * Load active domains for project creation
 */
async function loadActiveDomains() {
  try {
    console.log('🔧 Loading active domains...');
    const response = await ApiClient.get('/api/domains/active');
    const domains = response.domains || response || [];

    const select = document.getElementById('projectDomain');
    if (!select) return;

    if (domains.length === 0) {
      select.innerHTML = '<option value="">No domains available</option>';
      return;
    }

    select.innerHTML = '<option value="">Select a domain...</option>' +
      domains.map(domain => {
        const domainName = domain.domain || domain.domain_name || '';
        const description = domain.description || '';
        return `<option value="${domainName}">${domainName} - ${description}</option>`;
      }).join('');
  } catch (error) {
    console.error('Error loading active domains:', error);
    const select = document.getElementById('projectDomain');
    if (select) {
      select.innerHTML = '<option value="">Error loading domains</option>';
    }
  }
}

/**
 * Handle project creation from modal
 */
async function handleCreateProject(modal) {
  const createBtn = modal.querySelector('#createProjectBtn');
  const originalBtnText = createBtn ? createBtn.textContent : 'Create Project';

  try {
    const nameEl = document.getElementById('projectName');
    const namespaceEl = document.getElementById('projectNamespace');
    const domainEl = document.getElementById('projectDomain');
    const descriptionEl = document.getElementById('projectDescription');

    if (!nameEl || !namespaceEl) {
      alert('Project name and namespace are required');
      return;
    }

    const name = nameEl.value.trim();
    const namespaceId = namespaceEl.value;
    const domain = domainEl ? domainEl.value : '';
    const description = descriptionEl ? descriptionEl.value.trim() : '';

    if (!name || !namespaceId) {
      alert('Please fill in project name and select a namespace');
      return;
    }

    // Update button to show progress
    if (createBtn) {
      createBtn.disabled = true;
      createBtn.style.opacity = '0.8';
      let dots = 0;
      const ellipsisInterval = setInterval(() => {
        dots = (dots + 1) % 4;
        createBtn.textContent = 'Creating' + '.'.repeat(dots);
      }, 500);
      createBtn._ellipsisInterval = ellipsisInterval;
    }

    console.log('🔧 Creating project:', { name, namespaceId, domain, description });

    const requestData = {
      name,
      namespace_id: namespaceId,
      ...(domain && { domain }),
      ...(description && { description })
    };

    const response = await ApiClient.post('/api/projects', requestData);

    // Clear interval
    if (createBtn && createBtn._ellipsisInterval) {
      clearInterval(createBtn._ellipsisInterval);
    }

    // Close modal
    modal.remove();

    // Reload projects
    await loadProjects();

    // Select the new project
    const newProject = response.project || response;
    const projectId = newProject.id || newProject.project_id || newProject.projectId;
    if (projectId) {
      const projectSelect = document.getElementById('projectSelect2');
      if (projectSelect) {
        projectSelect.value = projectId;
        await selectProject(projectId);
      }
    }

    emitEvent('project:created', projectId);
    console.log('✅ Project created:', projectId);

  } catch (error) {
    console.error('❌ Failed to create project:', error);
    
    // Reset button
    if (createBtn) {
      if (createBtn._ellipsisInterval) {
        clearInterval(createBtn._ellipsisInterval);
      }
      createBtn.disabled = false;
      createBtn.style.opacity = '1';
      createBtn.textContent = originalBtnText;
    }

    alert(`Failed to create project: ${error.message || 'Unknown error'}`);
  }
}

/**
 * Create a new project (simple version for programmatic use)
 */
export async function createProject(projectName) {
  try {
    console.log('📁 Creating project:', projectName);

    const response = await ApiClient.post('/api/projects', {
      name: projectName
    });

    const newProject = response.project || response;
    const projectId = newProject.id || newProject.project_id || newProject.projectId;

    console.log('✅ Project created:', projectId);

    // Reload projects
    await loadProjects();

    // Select the new project
    if (projectId) {
      const projectSelect = document.getElementById('projectSelect2');
      if (projectSelect) {
        projectSelect.value = projectId;
        await selectProject(projectId);
      }
    }

    emitEvent('project:created', projectId);
    return projectId;
  } catch (error) {
    console.error('❌ Failed to create project:', error);
    alert(`Failed to create project: ${error.message || 'Unknown error'}`);
    throw error;
  }
}
