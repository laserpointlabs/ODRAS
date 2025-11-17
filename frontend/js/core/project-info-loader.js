/**
 * Project Info Loader Module
 * 
 * Loads and renders project information in the project workbench.
 */

import { apiClient } from './api-client.js';
import { getAppState } from './state-manager.js';
import { subscribeToEvent } from './event-bus.js';

const ApiClient = apiClient;

/**
 * Initialize project info loader
 */
export function initializeProjectInfoLoader() {
  console.log('📋 Initializing Project Info Loader...');

  // Load project info when project is selected
  subscribeToEvent('project:selected', async (projectId) => {
    await loadProjectInfo(projectId);
  });

  // Load project info when project workbench is activated
  subscribeToEvent('workbench:switched', async (workbenchId) => {
    if (workbenchId === 'project') {
      const state = getAppState();
      if (state.activeProject?.projectId) {
        await loadProjectInfo(state.activeProject.projectId);
      } else {
        showNoProjectMessage();
      }
    }
  });

  console.log('✅ Project Info Loader initialized');
}

/**
 * Load project information
 */
async function loadProjectInfo(projectId) {
  const projectInfoCard = document.getElementById('projectInfoCard');
  if (!projectInfoCard) {
    console.warn('⚠️ projectInfoCard element not found');
    return;
  }

  if (!projectId) {
    showNoProjectMessage();
    return;
  }

  try {
    projectInfoCard.innerHTML = `
      <div style="text-align: center; color: var(--muted);">
        <div>Loading project information...</div>
      </div>
    `;

    // Get project details with namespace info
    const response = await ApiClient.get(`/api/projects/${projectId}/namespace`);

    if (response.error) {
      projectInfoCard.innerHTML = `
        <div style="text-align: center; color: var(--err);">
          <h3>Error Loading Project</h3>
          <p>Could not load project information. Please try again.</p>
        </div>
      `;
      return;
    }

    const projectData = response;

    // Get additional project details from main API
    try {
      const projectsResponse = await ApiClient.get('/api/projects');
      const projects = projectsResponse.projects || [];
      const currentProject = projects.find(p => (p.id || p.project_id) === projectId);
      if (currentProject) {
        Object.assign(projectData, currentProject);
      }
    } catch (e) {
      console.warn('Could not load full project list:', e);
    }

    // Get parent and child project information (project lattice)
    let parentProject = null;
    let childProjects = [];
    
    try {
      // Get parent project
      const parentResponse = await ApiClient.get(`/api/projects/${projectId}/parent`);
      if (parentResponse.success && parentResponse.parent) {
        parentProject = parentResponse.parent;
      }
    } catch (e) {
      console.warn('Could not load parent project:', e);
    }
    
    try {
      // Get child projects
      const childrenResponse = await ApiClient.get(`/api/projects/${projectId}/children`);
      if (childrenResponse.success && childrenResponse.children) {
        childProjects = childrenResponse.children;
      }
    } catch (e) {
      console.warn('Could not load child projects:', e);
    }
    
    // Add hierarchy info to project data
    projectData.parentProject = parentProject;
    projectData.childProjects = childProjects;

    renderProjectInfo(projectData);
  } catch (error) {
    console.error('Error loading project info:', error);
    if (error.message && error.message.includes('403')) {
      projectInfoCard.innerHTML = `
        <div style="text-align: center; color: var(--warn);">
          <h3>Project Access Denied</h3>
          <p>The selected project is not accessible with your current permissions.</p>
          <p>Please select a different project from the dropdown.</p>
        </div>
      `;
    } else {
      projectInfoCard.innerHTML = `
        <div style="text-align: center; color: var(--err);">
          <h3>Error</h3>
          <p>Failed to load project information: ${error.message || 'Unknown error'}</p>
        </div>
      `;
    }
  }
}

/**
 * Render project information
 */
function renderProjectInfo(projectData) {
  const projectInfoCard = document.getElementById('projectInfoCard');
  if (!projectInfoCard) return;

  const createdDate = projectData.created_at ? new Date(projectData.created_at).toLocaleDateString() : 'Unknown';
  const updatedDate = projectData.updated_at ? new Date(projectData.updated_at).toLocaleDateString() : 'Unknown';
  const createdBy = projectData.created_by_username || projectData.created_by || 'Unknown';
  const projectId = projectData.project_id || projectData.id;
  const projectName = projectData.project_name || projectData.name || 'Project';
  const projectLevel = projectData.project_level;
  const publicationStatus = projectData.publication_status || 'draft';
  const parentProject = projectData.parentProject;
  const childProjects = projectData.childProjects || [];

  projectInfoCard.innerHTML = `
    <div style="margin-bottom: 32px;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
        <h2 style="margin: 0; color: var(--text); font-size: 1.75rem; font-weight: 600;">
          ${projectName}
          ${projectLevel !== null && projectLevel !== undefined ? ` <span style="color: var(--muted); font-size: 1.2rem; font-weight: 400;">L${projectLevel}</span>` : ''}
        </h2>
        <div style="display: flex; gap: 8px; align-items: center;">
          <span style="font-size: 14px; padding: 6px 12px; background: var(--accent); color: white; border-radius: 16px; font-weight: 500; text-transform: capitalize;">
            ${projectData.status || 'active'}
          </span>
          <span style="font-size: 12px; padding: 4px 8px; background: var(--panel-2); color: var(--text); border-radius: 12px; border: 1px solid var(--border); text-transform: capitalize;">
            ${publicationStatus}
          </span>
        </div>
      </div>
      ${projectData.description ? `
        <div style="background: var(--panel-2); padding: 16px; border-radius: 8px; border-left: 4px solid var(--accent);">
          <p style="color: var(--text); margin: 0; line-height: 1.5;">${projectData.description}</p>
        </div>
      ` : ''}
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 32px; margin-bottom: 32px;">
      <div style="background: var(--panel-2); padding: 20px; border-radius: 12px; border: 1px solid var(--border);">
        <h3 style="margin: 0 0 16px 0; color: var(--text); font-size: 1.1rem; font-weight: 600;">Organization</h3>
        <div style="display: grid; gap: 12px;">
          <div>
            <label style="display: block; font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Namespace</label>
            <div style="font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace; color: var(--accent); font-weight: 500; background: var(--panel); padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border);">
              ${projectData.namespace_path || 'No namespace assigned'}
            </div>
          </div>
          ${projectData.domain ? `
            <div>
              <label style="display: block; font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Domain</label>
              <div style="color: var(--text); font-weight: 500; background: var(--panel); padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border);">
                ${projectData.domain}
              </div>
            </div>
          ` : ''}
          <div>
            <label style="display: block; font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Project ID</label>
            <div style="font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace; color: var(--text); font-size: 14px; background: var(--panel); padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border); word-break: break-all;">
              ${projectId}
            </div>
          </div>
        </div>
      </div>

      <div style="background: var(--panel-2); padding: 20px; border-radius: 12px; border: 1px solid var(--border);">
        <h3 style="margin: 0 0 16px 0; color: var(--text); font-size: 1.1rem; font-weight: 600;">Details</h3>
        <div style="display: grid; gap: 12px;">
          <div>
            <label style="display: block; font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Created</label>
            <div style="color: var(--text); font-weight: 500;">${createdDate}</div>
          </div>
          <div>
            <label style="display: block; font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Last Updated</label>
            <div style="color: var(--text); font-weight: 500;">${updatedDate}</div>
          </div>
          <div>
            <label style="display: block; font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">Created By</label>
            <div style="color: var(--text); font-weight: 500; display: flex; align-items: center; gap: 8px;">
              <span style="width: 32px; height: 32px; background: var(--accent); color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 14px;">
                ${createdBy.charAt(0).toUpperCase()}
              </span>
              ${createdBy}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Project Hierarchy Section -->
    ${(parentProject || childProjects.length > 0) ? `
    <div style="margin-bottom: 32px;">
      <h3 style="margin: 0 0 16px 0; color: var(--text); font-size: 1.1rem; font-weight: 600;">Project Hierarchy</h3>
      <div style="display: grid; gap: 16px;">
        
        ${parentProject ? `
        <div style="background: var(--panel-2); padding: 16px; border-radius: 8px; border: 1px solid var(--border);">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
            <span style="color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">Parent Project</span>
            <span style="font-size: 10px; padding: 2px 6px; background: var(--accent); color: white; border-radius: 10px;">
              L${parentProject.project_level}
            </span>
          </div>
          <div style="color: var(--text); font-weight: 500; cursor: pointer;" onclick="selectProject('${parentProject.project_id}')" onmouseover="this.style.color='var(--accent)'" onmouseout="this.style.color='var(--text)'">
            ${parentProject.name}
          </div>
          <div style="color: var(--muted); font-size: 12px; margin-top: 4px;">
            Domain: ${parentProject.domain || 'Unknown'} • Status: ${parentProject.publication_status || 'draft'}
          </div>
        </div>
        ` : ''}
        
        ${childProjects.length > 0 ? `
        <div style="background: var(--panel-2); padding: 16px; border-radius: 8px; border: 1px solid var(--border);">
          <div style="color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px;">
            Child Projects (${childProjects.length})
          </div>
          <div style="display: grid; gap: 8px;">
            ${childProjects.map(child => `
              <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; background: var(--panel); border-radius: 6px; border: 1px solid var(--border);">
                <div style="cursor: pointer;" onclick="selectProject('${child.project_id}')" onmouseover="this.style.color='var(--accent)'" onmouseout="this.style.color='var(--text)'">
                  <div style="color: var(--text); font-weight: 500;">${child.name}</div>
                  <div style="color: var(--muted); font-size: 11px;">
                    Domain: ${child.domain || 'Unknown'}
                  </div>
                </div>
                <div style="display: flex; align-items: center; gap: 6px;">
                  <span style="font-size: 10px; padding: 2px 6px; background: var(--accent); color: white; border-radius: 10px;">
                    L${child.project_level}
                  </span>
                  <span style="font-size: 10px; padding: 2px 6px; background: var(--panel-2); color: var(--text); border-radius: 10px; border: 1px solid var(--border);">
                    ${child.publication_status || 'draft'}
                  </span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
        ` : ''}
        
      </div>
    </div>
    ` : ''}
  `;
}

/**
 * Get layer description for display
 */
function getLayerDescription(level) {
  const descriptions = {
    0: 'Abstract/Foundation',
    1: 'Strategic', 
    2: 'Tactical',
    3: 'Concrete'
  };
  return descriptions[level] || 'Unknown';
}

/**
 * Select a project (for hierarchy navigation)
 */
async function selectProject(projectId) {
  try {
    // Import project manager and select the project
    const { selectProject: selectProjectFn } = await import('./project-manager.js');
    await selectProjectFn(projectId);
  } catch (error) {
    console.error('Error selecting project:', error);
  }
}

/**
 * Show no project message
 */
function showNoProjectMessage() {
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

// Make loadProjectInfo available globally for compatibility
if (typeof window !== 'undefined') {
  window.loadProjectInfo = (projectId) => {
    const state = getAppState();
    const pid = projectId || state.activeProject?.projectId;
    if (pid) {
      loadProjectInfo(pid);
    } else {
      showNoProjectMessage();
    }
  };
}
