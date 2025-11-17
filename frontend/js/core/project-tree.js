/**
 * Project Tree Module
 * 
 * Handles the main sidebar tree view showing projects, requirements, documents, ontologies, etc.
 * Extracted from app.html renderTree function and related helpers.
 */

import { apiClient } from './api-client.js';
import { getAppState, updateAppState } from './state-manager.js';
import { emitEvent, subscribeToEvent } from './event-bus.js';

const ApiClient = apiClient;
const tokenKey = 'odras_token';

// Helper functions
function qs(selector) {
  return document.querySelector(selector);
}

function qsa(selector) {
  return Array.from(document.querySelectorAll(selector));
}

function slugify(str) {
  return String(str || '')
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function toast(msg, isError = false) {
  // Simple toast notification
  const toastEl = document.createElement('div');
  toastEl.style.cssText = `
    position: fixed; top: 20px; right: 20px; z-index: 10001;
    background: ${isError ? 'var(--err)' : 'var(--accent)'};
    color: white; padding: 12px 24px; border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    animation: slideIn 0.3s ease;
  `;
  toastEl.textContent = msg;
  document.body.appendChild(toastEl);
  setTimeout(() => {
    toastEl.style.animation = 'slideOut 0.3s ease';
    setTimeout(() => toastEl.remove(), 300);
  }, 3000);
}

// Tree navigation helpers
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
  if (idx < list.length - 1) (list[idx + 1].querySelector('.node-row') || list[idx + 1]).focus();
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

// Ontology label management
function loadOntologyLabelMap(project) {
  const state = getAppState();
  const pid = project?.id || project?.project_id || state.activeProject?.projectId || 'default';
  try { 
    return JSON.parse(localStorage.getItem(`onto_label_map__${pid}`) || '{}'); 
  } catch (_) { 
    return {}; 
  }
}

function saveOntologyLabel(graphIri, label) {
  const state = getAppState();
  const pid = state.activeProject?.projectId || 'default';
  try { 
    const m = loadOntologyLabelMap(state.activeProject); 
    m[graphIri] = label; 
    localStorage.setItem(`onto_label_map__${pid}`, JSON.stringify(m)); 
  } catch (_) { }
}

async function loadCurrentProjectNamespace(displayElement) {
  if (!displayElement) return;

  try {
    const state = getAppState();
    const currentProjectId = state.activeProject?.projectId || localStorage.getItem('active_project_id');
    if (!currentProjectId) {
      displayElement.textContent = 'No project selected - select a project first';
      displayElement.style.color = 'var(--warning)';
      return;
    }

    const token = localStorage.getItem(tokenKey);
    if (!token) {
      displayElement.textContent = 'Authentication required';
      displayElement.style.color = 'var(--err)';
      return;
    }

    const response = await fetch(`/api/projects/${currentProjectId}/namespace`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (response.ok) {
      const data = await response.json();
      if (data.namespace_path && data.namespace_path !== 'no namespace') {
        displayElement.textContent = `${data.namespace_path}/${data.name}`;
        displayElement.style.color = 'var(--text)';
        displayElement.title = `Project: ${data.name} in namespace: ${data.namespace_path}`;
      } else {
        displayElement.textContent = 'Project has no namespace - assign one first';
        displayElement.style.color = 'var(--warning)';
      }
    } else {
      displayElement.textContent = 'Error loading project namespace';
      displayElement.style.color = 'var(--err)';
    }
  } catch (error) {
    console.error('Error loading project namespace:', error);
    displayElement.textContent = 'Error loading namespace';
    displayElement.style.color = 'var(--err)';
  }
}

// Handle tree node selection
async function handleTreeSelection(li) {
  if (!li || !li.dataset) return;
  const type = li.dataset.nodeType || '';

  if (type === 'ontology') {
    const iri = li.dataset.iri;
    if (iri) {
      // Emit event for ontology workbench to handle
      emitEvent('ontology:selected', {
        iri: iri,
        label: li.dataset.label || iri.split('/').pop() || iri,
        projectId: getAppState().activeProject?.projectId
      });
    }
  } else if (type === 'class' || type === 'dataProperty' || type === 'note') {
    // Emit event for ontology workbench to handle element selection
    emitEvent('ontology:element:selected', {
      nodeId: li.dataset.nodeId,
      type: type
    });
  } else if (type === 'edge') {
    // Emit event for ontology workbench to handle edge selection
    emitEvent('ontology:edge:selected', {
      edgeId: li.dataset.edgeId
    });
  }
  // Other node types (requirements, documents, etc.) can be handled here
}

// Render the project tree
export async function renderTree(project) {
  const state = getAppState();
  const activeProject = project && project.id ? project : null;
  
  // Update app state with active project
  if (activeProject) {
    updateAppState({ 
      activeProject: {
        projectId: activeProject.id || activeProject.project_id,
        name: activeProject.name || activeProject.project_name || 'Project',
        ...activeProject
      }
    });
  }

  // Reset active ontology when switching context
  emitEvent('ontology:reset');

  const root = qs('#treeRoot');
  if (!root) {
    console.error('❌ Tree root element not found');
    return;
  }

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
        renameOntology(li.dataset.iri, name.trim(), li, row);
      }
    };

    const twist = document.createElement('span'); 
    twist.className = 'twist';
    if (hasChildren) {
      twist.onclick = (e) => { e.stopPropagation(); toggleNode(li); };
    }
    row.appendChild(twist);

    const icon = document.createElement('span'); 
    icon.className = 'node-icon ' + iconCls; 
    row.appendChild(icon);
    
    const text = document.createElement('span'); 
    text.className = 'node-label'; 
    text.textContent = label; 
    row.appendChild(text);
    
    li.appendChild(row);

    if (hasChildren) {
      const ul = document.createElement('ul'); 
      ul.setAttribute('role', 'group');
      children.forEach(ch => ul.appendChild(ch));
      li.appendChild(ul);
    }
    return li;
  };

  // Build tree items
  const reqItems = ((project && project.requirements) || []).map((r, idx) => {
    const rid = r.id || `SP-${String(idx + 1).padStart(3, '0')}`;
    const label = rid;
    return makeItem(rid, label, 'req');
  });

  const docReqItems = (project && project.documents && project.documents.requirements ? project.documents.requirements : []).map(d => 
    makeItem(d.id || d.name, d.name || d.id, 'docreq')
  );
  
  const docKnowItems = (project && project.documents && project.documents.knowledge ? project.documents.knowledge : []).map(d => 
    makeItem(d.id || d.name, d.name || d.id, 'docknow')
  );
  
  const outItems = ((project && (project.artifacts || project.outputs)) || []).map(o => 
    makeItem(o.id || o.name, o.name || o.id, 'out')
  );

  // Ontology tree: discover from Fuseki
  let ontologyNode = null;
  try {
    const pid = project && (project.id || project.project_id);
    const token = localStorage.getItem(tokenKey);
    const res = await fetch(`/api/ontologies${pid ? `?project=${encodeURIComponent(pid)}` : ''}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
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
          try { 
            ev.dataTransfer.setData('text/graph-iri', o.graphIri); 
            ev.dataTransfer.effectAllowed = 'copy'; 
          } catch (_) { }
        });

        // Add context menu for ontology nodes
        row.oncontextmenu = (ev) => {
          ev.preventDefault();
          showOntologyContextMenu(ev, o, li, row, project);
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
      ontologyNode = makeItem('ontology', 'Ontologies', 'folder', []);
    }
  } catch (error) {
    console.error('Error loading ontologies:', error);
    ontologyNode = makeItem('ontology', 'Ontologies', 'folder', [
      makeItem('onto-error', 'Discovery unavailable', 'onto')
    ]);
  }

  // Project info node
  const projectDisplay = (project && (project.name || project.id)) ? (project.name || project.id) : '';
  const projectInfo = makeItem('project-info', `Project: ${projectDisplay}`, 'folder');
  
  // Wire up project info click handler
  try {
    const row = projectInfo.querySelector('.node-row');
    if (row && project && (project.id || project.project_id)) {
      row.onclick = (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        // Import and use workbench manager to switch
        import('/static/js/core/workbench-manager.js').then(module => {
          if (module.switchWorkbench) {
            module.switchWorkbench('project');
          }
        }).catch(err => console.warn('Could not switch to project workbench:', err));
      };

      // Context menu for project
      row.oncontextmenu = (ev) => {
        ev.preventDefault();
        showProjectContextMenu(ev, project);
      };
    }
  } catch (_) { }

  // Build document nodes
  const docsReqNode = makeItem('documents-requirements', 'Requirements Documents', 'folder', docReqItems);
  const docsKnowNode = makeItem('documents-knowledge', 'Knowledge Documents', 'folder', docKnowItems);
  const docsChildren = [];
  if (docReqItems.length) docsChildren.push(docsReqNode);
  if (docKnowItems.length) docsChildren.push(docsKnowNode);
  const docsNode = makeItem('documents', 'Documents', 'folder', docsChildren);
  const reqNode = makeItem('requirements', 'Extracted Requirements', 'folder', reqItems);

  // Create new ODRAS-specific tree nodes
  const knowledgeNode = makeItem('knowledge', 'Knowledge', 'folder', []);
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

  // Fetch DAS Assumptions
  let assumptionsNode = null;
  try {
    const pid = project && (project.id || project.project_id);
    if (pid) {
      const token = localStorage.getItem('odras_token');
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

  if (!assumptionsNode) {
    assumptionsNode = makeItem('assumptions', 'Assumptions', 'folder', []);
  }

  // Fetch DAS Artifacts
  let dasArtifactItems = [];
  try {
    const pid = project && (project.id || project.project_id);
    if (pid) {
      const token = localStorage.getItem('odras_token');
      const filesRes = await fetch(`/api/files?project_id=${pid}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (filesRes.ok) {
        const filesData = await filesRes.json();
        const dasFiles = (filesData.files || []).filter(f =>
          f.tags && f.tags.generated_by === 'das'
        );
        dasArtifactItems = dasFiles.map(f => {
          const artifactItem = makeItem(f.file_id, f.filename, 'artifact', [], {
            fileId: f.file_id,
            artifactType: f.tags.artifact_type,
            createdAt: f.created_at
          });
          const nodeRow = artifactItem.querySelector('.node-row');
          if (nodeRow) {
            nodeRow.onclick = (e) => {
              e.preventDefault();
              e.stopPropagation();
              emitEvent('artifact:view', { fileId: f.file_id, filename: f.filename, type: f.tags.artifact_type });
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

  const allArtifactItems = [...dasArtifactItems, ...outItems];
  const outNode = makeItem('artifacts', 'Artifacts', 'folder', allArtifactItems);

  // Create horizontal separator
  const separator = document.createElement('li');
  separator.className = 'tree-separator';
  separator.innerHTML = '<div class="separator-line"></div>';

  // Clear and rebuild tree
  root.innerHTML = '';
  if (project && (project.id || project.project_id)) {
    [projectInfo, ontologyNode, knowledgeNode, analysisNode, eventsNode, assumptionsNode, separator, outNode]
      .filter(Boolean)
      .forEach(n => root.appendChild(n));
  }

  // Add plus button on Ontology section header
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
        if (!project || !(project.id || project.project_id)) { 
          alert('Create a project first'); 
          return; 
        }
        await showCreateOntologyModal(project);
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
      await deleteOntology(iri, project);
    }
  });
}

// Ontology creation modal
async function showCreateOntologyModal(project) {
  const token = localStorage.getItem(tokenKey);
  let isAdmin = false;
  try {
    const userRes = await fetch('/api/auth/me', { headers: { Authorization: 'Bearer ' + token } });
    if (userRes.ok) {
      const user = await userRes.json();
      isAdmin = user.is_admin || false;
    }
  } catch (err) {
    console.error('Failed to get user info:', err);
  }

  const overlay = document.createElement('div');
  overlay.style.cssText = `
    position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 9998;
  `;

  const panel = document.createElement('div');
  panel.style.cssText = `
    position: fixed; top: 30%; left: 50%; transform: translateX(-50%);
    background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
    padding: 20px; min-width: 400px; z-index: 9999;
  `;

  panel.innerHTML = `
    <div style="margin-bottom:16px;">
      <h3 style="margin:0 0 16px 0;">Create or Import Ontology</h3>
      <div style="margin-bottom:16px;">
        <div style="display:flex; gap:8px; margin-bottom:12px;">
          <button id="createMode" class="btn btn-primary" style="flex:1;">Create New</button>
          <button id="importMode" class="btn" style="flex:1;">Import from URL</button>
        </div>
      </div>
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
        </div>
        ` : ''}
      </div>
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

  // Mode toggle
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

  // Load namespace
  loadCurrentProjectNamespace(panel.querySelector('#ontoNamespaceDisplay'));

  // Create handler
  panel.querySelector('#createOnto').onclick = async () => {
    const labelInput = panel.querySelector('#ontoLabel');
    const disp = labelInput.value.trim();

    if (!disp) {
      alert('Please enter a label for the ontology');
      return;
    }

    const currentProjectId = getAppState().activeProject?.projectId || localStorage.getItem('active_project_id');
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

      // Select the created ontology
      if (created && created.graphIri) {
        const newRoot = qs('#treeRoot');
        const li = Array.from(newRoot.querySelectorAll('li[role="treeitem"]')).find(el => el.dataset && el.dataset.iri === created.graphIri);
        if (li) {
          const lbl = li.querySelector('.node-label'); 
          if (lbl) lbl.textContent = created.label || label;
          li.dataset.label = created.label || label;
          selectNode(li);
          await handleTreeSelection(li);
        }
      }
    } catch (err) {
      alert('Failed to create ontology: ' + err.message);
    }
  };

  // Import handler
  panel.querySelector('#importOnto').onclick = async () => {
    const urlInput = panel.querySelector('#importUrl');
    const nameInput = panel.querySelector('#importName');
    const labelInput = panel.querySelector('#importLabel');

    const url = urlInput.value.trim();
    const name = nameInput.value.trim();
    const label = labelInput.value.trim();

    if (!url || !name || !label) {
      alert('Please fill in all fields');
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
          project_id: project.id || project.project_id,
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

  setTimeout(() => {
    panel.querySelector('#ontoLabel').focus();
  }, 100);
}

// Context menu handlers
function showOntologyContextMenu(ev, ontology, li, row, project) {
  const menu = qs('#ontologyContextMenu');
  if (!menu) return;

  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const displayLabel = li.dataset.label || ontology.graphIri;

  menu.style.display = 'block';
  menu.style.left = ev.pageX + 'px';
  menu.style.top = ev.pageY + 'px';

  const hide = () => {
    menu.style.display = 'none';
    document.removeEventListener('click', hide, { capture: true });
  };
  setTimeout(() => { document.addEventListener('click', hide, { capture: true }); }, 0);

  const renameBtn = qs('#ontoRenameBtn');
  const toggleRefBtn = qs('#ontoToggleReferenceBtn');
  const deleteBtn = qs('#ontoDeleteBtn');

  if (renameBtn) {
    renameBtn.onclick = async () => {
      hide();
      const current = displayLabel;
      const name = prompt('Rename ontology label', current);
      if (!name || name.trim() === current) return;
      await renameOntology(ontology.graphIri, name.trim(), li, row);
    };
  }

  if (toggleRefBtn) {
    const currentRefStatus = ontology.is_reference || false;
    toggleRefBtn.textContent = currentRefStatus ? 'Remove Reference Status' : 'Mark as Reference';
    toggleRefBtn.onclick = async () => {
      hide();
      await toggleOntologyReference(ontology.graphIri, !currentRefStatus, project);
    };
  }

  if (deleteBtn) {
    deleteBtn.onclick = async () => {
      hide();
      await deleteOntology(ontology.graphIri, project);
    };
  }
}

function showProjectContextMenu(ev, project) {
  const menu = qs('#projectContextMenu');
  if (!menu) return;

  menu.style.display = 'block';
  menu.style.left = ev.pageX + 'px';
  menu.style.top = ev.pageY + 'px';

  const hide = () => {
    menu.style.display = 'none';
    document.removeEventListener('click', hide, { capture: true });
  };
  setTimeout(() => { document.addEventListener('click', hide, { capture: true }); }, 0);

  const pid = project.id || project.project_id;
  const token = localStorage.getItem(tokenKey);

  const renameBtn = qs('#projRenameBtn');
  const archiveBtn = qs('#projArchiveBtn');
  const deleteBtn = qs('#projDeleteBtn');
  const showArchivedBtn = qs('#projShowArchivedBtn');

  if (renameBtn) {
    renameBtn.onclick = async () => {
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
          emitEvent('project:reload');
        } else {
          const t = await res.text().catch(() => String(res.status));
          alert('Rename failed: ' + t);
        }
      } finally { hide(); }
    };
  }

  if (archiveBtn) {
    archiveBtn.onclick = async () => {
      try {
        const res = await fetch(`/api/projects/${encodeURIComponent(pid)}/archive`, { 
          method: 'POST', 
          headers: { Authorization: 'Bearer ' + token } 
        });
        if (res.ok) { 
          try { localStorage.removeItem('active_project_id'); } catch (_) { } 
          emitEvent('project:reload');
        } else { 
          const t = await res.text().catch(() => String(res.status)); 
          alert('Archive failed: ' + t); 
        }
      } finally { hide(); }
    };
  }

  if (deleteBtn) {
    deleteBtn.onclick = async () => {
      try {
        if (!confirm('Delete this project? This does not delete external artifacts.')) return;
        const res = await fetch(`/api/projects/${encodeURIComponent(pid)}`, { 
          method: 'DELETE', 
          headers: { Authorization: 'Bearer ' + token } 
        });
        if (res.ok) { 
          try { localStorage.removeItem('active_project_id'); } catch (_) { } 
          emitEvent('project:reload');
        } else { 
          const t = await res.text().catch(() => String(res.status)); 
          alert('Delete failed: ' + t); 
        }
      } finally { hide(); }
    };
  }

  if (showArchivedBtn) {
    showArchivedBtn.onclick = async () => {
      // Show archived projects modal
      hide();
    };
  }
}

// Ontology operations
async function renameOntology(graphIri, newLabel, li, row) {
  try {
    const payload = { graph: graphIri, label: newLabel.trim() };
    const token = localStorage.getItem(tokenKey);
    const res = await fetch('/api/ontologies/label', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      row.querySelector('.node-label').textContent = newLabel.trim();
      li.dataset.label = newLabel.trim();
      saveOntologyLabel(graphIri, newLabel.trim());
      emitEvent('ontology:renamed', { graphIri, label: newLabel.trim() });
      const state = getAppState();
      await renderTree(state.activeProject);
    } else {
      alert('Rename failed');
    }
  } catch (_) {
    alert('Rename failed');
  }
}

async function toggleOntologyReference(graphIri, isReference, project) {
  try {
    const payload = { graph: graphIri, is_reference: isReference };
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
}

async function deleteOntology(graphIri, project) {
  if (!confirm(`Delete ontology "${graphIri}"?`)) return;
  
  try {
    const token = localStorage.getItem(tokenKey);
    const res = await fetch(`/api/ontologies?graph=${encodeURIComponent(graphIri)}`, {
      method: 'DELETE',
      headers: { Authorization: 'Bearer ' + token }
    });
    if (res.ok) {
      // Clear local storage for this ontology
      try {
        const state = getAppState();
        const pid = state.activeProject?.projectId || 'default';
        localStorage.removeItem(`onto_graph__${pid}__${encodeURIComponent(graphIri)}`);
      } catch (e) {
        console.warn('Failed to clear local storage:', e);
      }

      await renderTree(project);
      emitEvent('ontology:deleted', { graphIri });
    } else {
      alert('Delete failed');
    }
  } catch (_) {
    alert('Delete failed');
  }
}

// Initialize project tree
export function initializeProjectTree() {
  console.log('🌳 Initializing Project Tree...');
  
  // Listen for project selection changes
  subscribeToEvent('project:selected', async (projectId) => {
    const state = getAppState();
    if (state.activeProject && state.activeProject.projectId === projectId) {
      await renderTree(state.activeProject);
    }
  });

  // Listen for project reload requests
  subscribeToEvent('project:reload', async () => {
    const state = getAppState();
    if (state.activeProject) {
      await renderTree(state.activeProject);
    }
  });

  console.log('✅ Project Tree initialized');
}
