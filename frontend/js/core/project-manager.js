/**
 * Project Manager Module
 * 
 * Handles project loading, selection, and creation.
 */

import { apiClient } from './api-client.js';
import { updateAppState, getAppState } from './state-manager.js';
import { emitEvent, subscribeToEvent } from './event-bus.js';
import { renderTree, initializeProjectTree } from './project-tree.js';

const ApiClient = apiClient;

/**
 * Initialize project management functionality
 */
export async function initializeProjectManager() {
  console.log('📁 Initializing Project Manager...');

  // Initialize project tree
  initializeProjectTree();

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

    // Update localStorage
    try {
      localStorage.setItem('active_project_id', projectId);
    } catch (_) { }

    // Render tree with selected project
    await renderTree(project);

    emitEvent('project:selected', projectId);
    console.log('✅ Project selected:', project.name || projectId);
  } catch (error) {
    console.error('❌ Failed to load project details:', error);
  }
}

/**
 * Show create project modal (from app.html)
 * Exported for programmatic access
 */
export function showCreateProjectModal() {
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

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
        <div>
          <label style="display: block; margin-bottom: 6px; color: var(--text);">Layer (optional):</label>
          <select id="projectLevel" 
            style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px; background: var(--panel-2); color: var(--text); box-sizing: border-box;">
            <option value="">Select layer...</option>
            <option value="0">L0 - Abstract/Foundation</option>
            <option value="1">L1 - Strategic</option>
            <option value="2">L2 - Tactical</option>
            <option value="3">L3 - Concrete</option>
          </select>
          <div style="font-size: 0.85em; color: var(--muted); margin-top: 4px;">
            Layer defines abstraction level
          </div>
        </div>
        
        <div>
          <label style="display: block; margin-bottom: 6px; color: var(--text);">Parent Project (optional):</label>
          <select id="parentProject" 
            style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px; background: var(--panel-2); color: var(--text); box-sizing: border-box;">
            <option value="">No parent</option>
            <option value="">Loading projects...</option>
          </select>
          <div style="font-size: 0.85em; color: var(--muted); margin-top: 4px;">
            Parent for workflow coordination
          </div>
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

  // Load released namespaces, active domains, and available parent projects
  // Pass modal reference to ensure we update the correct select element
  requestAnimationFrame(() => {
    setTimeout(() => {
      loadReleasedNamespaces(modal);
      loadActiveDomains(modal);
      loadAvailableParentProjects(modal);
    }, 100);
  });

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
 * @param {HTMLElement} modalElement - Optional modal element to search within
 */
async function loadReleasedNamespaces(modalElement = null) {
  try {
    console.log('🔧 Loading released namespaces...');
    console.log('🔧 ApiClient available:', typeof ApiClient !== 'undefined');
    console.log('🔧 ApiClient.get available:', typeof ApiClient?.get === 'function');
    console.log('🔧 Making API call to /api/namespaces/released...');

    let response;
    const startTime = Date.now();
    try {
      response = await ApiClient.get('/api/namespaces/released');
      const duration = Date.now() - startTime;
      console.log(`✅ API call completed in ${duration}ms`);
      console.log('📦 Namespace API response:', response);
      console.log('📦 Response type:', typeof response, 'Is array:', Array.isArray(response));
    } catch (apiError) {
      const duration = Date.now() - startTime;
      console.error(`❌ API call failed after ${duration}ms:`, apiError);
      console.error('❌ API error details:', {
        message: apiError.message,
        stack: apiError.stack,
        name: apiError.name
      });
      throw apiError;
    }

    // Handle both array response and wrapped response
    let namespaces = [];
    if (Array.isArray(response)) {
      namespaces = response;
      console.log('✅ Response is array, using directly');
    } else if (response && response.namespaces && Array.isArray(response.namespaces)) {
      namespaces = response.namespaces;
      console.log('✅ Response has namespaces property');
    } else if (response && typeof response === 'object') {
      // Try to extract array from object
      console.warn('⚠️ Unexpected response format, attempting to extract namespaces');
      namespaces = Object.values(response).find(v => Array.isArray(v)) || [];
    } else {
      console.error('❌ Unexpected response format:', typeof response, response);
    }

    console.log(`📦 Extracted ${namespaces.length} namespaces`);

    // Find select element - use provided modal or find it
    const modal = modalElement || document.querySelector('.modal');
    const select = modal ? modal.querySelector('#projectNamespace') : document.getElementById('projectNamespace');
    if (!select) {
      console.error('❌ projectNamespace select element not found');
      console.error('❌ Modal exists:', !!modal);
      console.error('❌ All selects:', Array.from(document.querySelectorAll('select')).map(s => s.id));
      return;
    }
    console.log('✅ Found select element in modal');

    if (!namespaces || namespaces.length === 0) {
      console.warn('⚠️ No namespaces returned from API');
      select.innerHTML = '<option value="">No released namespaces available</option>';
      return;
    }

    console.log(`✅ Loading ${namespaces.length} namespaces into dropdown`);
    console.log('📦 First namespace:', namespaces[0]);

    const optionsHTML = '<option value="">Select a namespace...</option>' +
      namespaces.map(ns => {
        const id = ns.id || ns.namespace_id || '';
        const path = ns.path || ns.namespace_path || '';
        const name = ns.name || ns.namespace_name || '';
        const displayText = path && name ? `${path} - ${name}` : (name || path || id || 'Unnamed namespace');
        console.log(`  → Adding namespace: ${id} = ${displayText}`);
        return `<option value="${id}">${displayText}</option>`;
      }).join('');

    // Clear and set options
    select.innerHTML = optionsHTML;

    // Verify it was set - if not, find select again and retry
    if (select.innerHTML.length < 50) {
      console.warn('⚠️ Select innerHTML was not set correctly, finding select again...');
      const retrySelect = modal ? modal.querySelector('#projectNamespace') : document.getElementById('projectNamespace');
      if (retrySelect && retrySelect !== select) {
        console.log('✅ Found different select element, updating it');
        retrySelect.innerHTML = optionsHTML;
      } else if (retrySelect) {
        retrySelect.innerHTML = optionsHTML;
      }
    }

    console.log('✅ Namespaces loaded successfully');
    console.log('📦 Select element innerHTML length:', select.innerHTML.length);
    console.log('📦 Select element innerHTML preview:', select.innerHTML.substring(0, 150));
    // Check options count safely (options may not be immediately available after innerHTML change)
    try {
      const optionsCount = select.options?.length;
      console.log('📦 Select element options count:', optionsCount || 'N/A');
    } catch (e) {
      console.log('📦 Select element options count: N/A (not available yet)');
    }
    // Success - return early to avoid error handler overwriting the success
    return;
  } catch (error) {
    console.error('❌ Error loading released namespaces:', error);
    console.error('❌ Error type:', error?.constructor?.name);
    console.error('❌ Error message:', error?.message);
    console.error('❌ Error stack:', error?.stack);
    const select = document.getElementById('projectNamespace');
    if (select) {
      // Only set error message if select is empty or still showing loading message
      const currentText = select.options[0]?.text || '';
      if (!currentText || currentText.includes('Loading') || currentText.includes('Error')) {
        select.innerHTML = `<option value="">Error loading namespaces: ${error.message || 'Unknown error'}</option>`;
      } else {
        console.warn('⚠️ Error occurred but namespaces were already loaded, keeping existing options');
      }
    }
  }
}

/**
 * Load active domains for project creation
 * @param {HTMLElement} modalElement - Optional modal element to search within
 */
async function loadActiveDomains(modalElement = null) {
  try {
    console.log('🔧 Loading active domains...');
    const response = await ApiClient.get('/api/domains/active');
    console.log('📦 Domain API response:', response);

    // Handle both array response and wrapped response
    const domains = Array.isArray(response) ? response : (response.domains || []);

    // Find select element - use provided modal or find it
    const modal = modalElement || document.querySelector('.modal');
    const select = modal ? modal.querySelector('#projectDomain') : document.getElementById('projectDomain');
    if (!select) {
      console.error('❌ projectDomain select element not found');
      return;
    }

    if (!domains || domains.length === 0) {
      console.warn('⚠️ No domains returned from API');
      select.innerHTML = '<option value="">No domains available</option>';
      return;
    }

    console.log(`✅ Loading ${domains.length} domains into dropdown`);
    select.innerHTML = '<option value="">Select a domain...</option>' +
      domains.map(domain => {
        const domainName = domain.domain || domain.domain_name || '';
        const description = domain.description || '';
        const displayText = domainName && description ? `${domainName} - ${description}` : (domainName || 'Unnamed domain');
        return `<option value="${domainName}">${displayText}</option>`;
      }).join('');

    console.log('✅ Domains loaded successfully');
  } catch (error) {
    console.error('❌ Error loading active domains:', error);
    const select = document.getElementById('projectDomain');
    if (select) {
      select.innerHTML = `<option value="">Error loading domains: ${error.message || 'Unknown error'}</option>`;
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
    // Find elements within the modal
    const nameEl = modal.querySelector('#projectName');
    const namespaceEl = modal.querySelector('#projectNamespace');
    const domainEl = modal.querySelector('#projectDomain');
    const descriptionEl = modal.querySelector('#projectDescription');
    const levelEl = modal.querySelector('#projectLevel');
    const parentEl = modal.querySelector('#parentProject');

    console.log('🔧 Creating project with:', {
      name: nameEl?.value,
      namespace: namespaceEl?.value,
      domain: domainEl?.value,
      description: descriptionEl?.value,
      level: levelEl?.value,
      parent: parentEl?.value
    });

    if (!nameEl || !namespaceEl) {
      console.error('❌ Required elements not found in modal');
      alert('Project name and namespace are required');
      return;
    }

    const name = nameEl.value.trim();
    const namespaceId = namespaceEl.value;
    const domain = domainEl ? domainEl.value : '';
    const description = descriptionEl ? descriptionEl.value.trim() : '';
    const level = levelEl && levelEl.value ? parseInt(levelEl.value) : null;
    const parentId = parentEl && parentEl.value ? parentEl.value : null;

    console.log('🔧 Validating:', { name, namespaceId, domain, description, level, parentId });

    if (!name || !namespaceId) {
      console.error('❌ Validation failed:', { name: !!name, namespaceId: !!namespaceId });
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
      ...(description && { description }),
      ...(level !== null && { project_level: level }),
      ...(parentId && { parent_project_id: parentId })
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

/**
 * Load available parent projects for project creation modal
 */
async function loadAvailableParentProjects(modalElement = null) {
  try {
    const response = await ApiClient.get('/api/projects');
    const projects = response?.projects || [];

    const selector = modalElement ?
      modalElement.querySelector('#parentProject') :
      document.getElementById('parentProject');

    if (selector) {
      // Keep the "No parent" option
      selector.innerHTML = '<option value="">No parent</option>';

      if (projects.length === 0) {
        selector.innerHTML += '<option value="" disabled>No projects available</option>';
      } else {
        // Group by domain and level for better organization
        const groupedProjects = {};
        projects.forEach(project => {
          const domain = project.domain || 'Unknown';
          const level = project.project_level !== undefined ? `L${project.project_level}` : 'No Level';
          const key = `${domain} (${level})`;

          if (!groupedProjects[key]) {
            groupedProjects[key] = [];
          }
          groupedProjects[key].push(project);
        });

        // Add organized options
        Object.keys(groupedProjects).sort().forEach(groupKey => {
          const optgroup = document.createElement('optgroup');
          optgroup.label = groupKey;

          groupedProjects[groupKey].forEach(project => {
            const option = document.createElement('option');
            option.value = project.project_id;
            option.textContent = project.name;
            optgroup.appendChild(option);
          });

          selector.appendChild(optgroup);
        });
      }
    }
  } catch (error) {
    console.error('❌ Failed to load parent projects:', error);
  }
}
