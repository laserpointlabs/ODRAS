/**
 * Ontology Workbench UI Structure
 * 
 * Creates the HTML structure for the ontology workbench dynamically
 * This keeps index.html minimal and makes the workbench truly pluggable
 */

export function createOntologyWorkbenchHTML() {
  return `
    <div class="ontology-header">
      <!-- Graph Info and Title -->
      <div class="header-left">
        <h2 class="workbench-title">Ontology Workbench</h2>
        <span id="ontoGraphLabel" class="graph-label">No graph selected</span>
      </div>

      <!-- Menu Bar -->
      <div class="header-menu">
        <div class="menu-group">
          <button class="menu-btn" id="ontoLayoutMenuBtn">
            <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round"
              stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="9" y1="9" x2="15" y2="9" />
              <line x1="9" y1="15" x2="15" y2="15" />
            </svg>
            Layout
          </button>
          <div class="menu-dropdown" id="ontoLayoutMenu">
            <div class="menu-section">
              <div class="menu-label">Layout Algorithm</div>
              <select id="ontoLayoutSelector" class="menu-select">
                <option value="cose">Force-Directed (CoSE)</option>
                <option value="dagre">Hierarchical (Dagre)</option>
                <option value="concentric">Concentric</option>
                <option value="breadthfirst">Breadthfirst</option>
                <option value="circle">Circle</option>
                <option value="grid">Grid</option>
                <option value="cola">Constraint-Based</option>
                <option value="spread">Spread</option>
              </select>
              <button class="menu-item" id="ontoLayoutBtn">Apply Layout</button>
            </div>
            <div class="menu-divider"></div>
            <div class="menu-section">
              <button class="menu-item" id="ontoQuickCoseBtn">Quick CoSE</button>
              <button class="menu-item" id="ontoQuickDagreBtn">Quick Dagre</button>
            </div>
          </div>
        </div>

        <div class="menu-group">
          <button class="menu-btn" id="ontoViewMenuBtn">
            <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round"
              stroke-linejoin="round">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
            View
          </button>
          <div class="menu-dropdown" id="ontoViewMenu">
            <button class="menu-item" id="ontoFitBtn">Fit to View</button>
            <button class="menu-item" id="ontoFullscreenBtn">Fullscreen</button>
            <button class="menu-item" id="ontoForceRefreshBtn">Refresh</button>
            <div class="menu-divider"></div>
            <button class="menu-item" id="ontoClearCacheBtn">Clear Cache</button>
          </div>
        </div>

        <!-- CAD Tools Menu -->
        <div class="menu-group">
          <button class="menu-btn" id="cadToolsMenuBtn">
            <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round"
              stroke-linejoin="round">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
            </svg>
            Tools
          </button>
          <div class="menu-dropdown" id="cadToolsMenu">
            <div class="menu-section">
              <div class="menu-label">Grid Settings</div>
              <button class="menu-item" id="snapGridBtn">
                <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <path d="M9 9h.01M15 9h.01M9 15h.01M15 15h.01" />
                </svg>
                <span id="snapGridStatus">Grid Snap: ON</span>
              </button>
              <div style="display: flex; align-items: center; gap: 8px; padding: 4px 12px;">
                <label style="font-size: 11px; color: var(--muted); min-width: 60px;">Grid Size:</label>
                <select id="gridSizeSelector"
                  style="flex: 1; font-size: 11px; background: var(--panel); color: var(--text); border: 1px solid var(--border); border-radius: 3px; padding: 2px;">
                  <option value="10">Fine (10px)</option>
                  <option value="20" selected>Normal (20px)</option>
                  <option value="40">Coarse (40px)</option>
                  <option value="80">Large (80px)</option>
                  <option value="custom">Custom...</option>
                </select>
              </div>
            </div>
            <div class="menu-divider"></div>
            <div class="menu-section">
              <div class="menu-label">Align</div>
              <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px;">
                <button class="btn btn-sm" title="Align Left (Ctrl+L)">⇤</button>
                <button class="btn btn-sm" title="Center (Ctrl+M)">⬌</button>
                <button class="btn btn-sm" title="Align Right (Ctrl+R)">⇥</button>
                <button class="btn btn-sm" title="Align Top (Ctrl+T)">⇈</button>
                <button class="btn btn-sm" title="Distribute V">⬍</button>
                <button class="btn btn-sm" title="Align Bottom (Ctrl+B)">⇊</button>
              </div>
              <button class="menu-item" title="Distribute Horizontal (Ctrl+Shift+H)">
                <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6">
                  <rect x="4" y="6" width="3" height="12" />
                  <rect x="10" y="6" width="4" height="12" />
                  <rect x="17" y="6" width="3" height="12" />
                </svg>
                Distribute Horizontal
              </button>
            </div>
            <div class="menu-divider"></div>
            <div class="menu-section">
              <div class="menu-label">Edit</div>
              <button class="menu-item" title="Copy (Ctrl+C)">
                <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
                Copy Selected
              </button>
              <button class="menu-item" title="Paste (Ctrl+V)">
                <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6">
                  <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
                  <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
                </svg>
                Paste
              </button>
              <button class="menu-item" title="Undo (Ctrl+Z)">
                <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6">
                  <path d="M3 7v6h6" />
                  <path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13" />
                </svg>
                Undo
              </button>
              <button class="menu-item" title="Redo (Ctrl+Y)">
                <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6">
                  <path d="M21 7v6h-6" />
                  <path d="M3 17a9 9 0 0 1 9-9 9 9 0 0 1 6 2.3l3 2.7" />
                </svg>
                Redo
              </button>
            </div>
            <div class="menu-divider"></div>
            <div class="menu-section">
              <div class="menu-label">View</div>
              <button class="menu-item" title="Zoom to Selection (Ctrl+F)">
                <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6">
                  <circle cx="11" cy="11" r="8" />
                  <path d="M21 21l-4.35-4.35" />
                  <rect x="8" y="8" width="6" height="6" />
                </svg>
                Zoom to Selection
              </button>
              <button class="menu-item" title="Fit All (F)">
                <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6">
                  <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
                </svg>
                Fit All
              </button>
              <button class="menu-item" title="100% Zoom (Ctrl+1)">
                <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6">
                  <circle cx="12" cy="12" r="8" />
                  <text x="12" y="16" text-anchor="middle" font-size="8" fill="currentColor">1:1</text>
                </svg>
                100% Zoom
              </button>
            </div>
          </div>
        </div>

        <div class="menu-group">
          <button class="menu-btn" id="ontoEditMenuBtn">
            <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round"
              stroke-linejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
            Edit
          </button>
          <div class="menu-dropdown" id="ontoEditMenu">
            <button class="menu-item" id="ontoDeleteBtn">Delete Selected</button>
            <button class="menu-item" id="ontoLinkIdenticalBtn">Link Identical Classes</button>
          </div>
        </div>

        <div class="menu-group">
          <button class="menu-btn" id="ontoFileMenuBtn">
            <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round"
              stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14,2 14,8 20,8" />
            </svg>
            File
          </button>
          <div class="menu-dropdown" id="ontoFileMenu">
            <button class="menu-item" id="ontoSaveBtn">Save Ontology</button>
            <div class="menu-divider"></div>
            <button class="menu-item" id="ontoImportBtn">Import JSON</button>
            <button class="menu-item" id="ontoExportBtn">Export JSON</button>
            <input type="file" id="ontoImportFile" accept="application/json" style="display:none" />
          </div>
        </div>
      </div>
    </div>

    <!-- Workbench Tabs -->
    <div class="workbench-tabs">
      <button class="workbench-tab active" id="ontologyTab">
        <svg viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="6" cy="6" r="2" />
          <circle cx="18" cy="6" r="2" />
          <circle cx="6" cy="18" r="2" />
          <circle cx="18" cy="18" r="2" />
          <line x1="8" y1="6" x2="16" y2="6" />
          <line x1="6" y1="8" x2="6" y2="16" />
          <line x1="18" y1="8" x2="18" y2="16" />
          <line x1="8" y1="18" x2="16" y2="18" />
        </svg>
        Ontologies
      </button>
      <button class="workbench-tab" id="individualsTab">
        <svg viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
          <line x1="7" y1="9" x2="17" y2="9" />
          <line x1="7" y1="13" x2="17" y2="13" />
          <line x1="7" y1="17" x2="13" y2="17" />
        </svg>
        Individuals
      </button>
      <button class="workbench-tab" id="cqmtTab">
        <svg viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="9" />
          <path d="M9 12l2 2 4-4" />
          <path d="M8 14s1.5 2 4 2 4-2 4-2" />
        </svg>
        CQ/MT
      </button>
    </div>

    <div id="ontoEmpty" class="card onto-empty-state">
      Create or Select an Ontology to begin
    </div>
    
    <div class="onto-layout" id="ontoLayoutSection">
      <aside class="onto-tree" aria-label="Ontology Tree">
        <div class="onto-tree-header" id="ontoTreeHeader">
          <div class="muted">Ontology</div>
          <div class="onto-tree-controls">
            <button class="iconbtn" id="ontoTreeToggle" title="Collapse">
              <svg id="ontoTreeToggleIcon" viewBox="0 0 24 24" fill="none" stroke-width="1.6"
                stroke-linecap="round" stroke-linejoin="round">
                <path d="M15 6l-6 6 6 6" />
              </svg>
            </button>
          </div>
        </div>
        <div class="onto-tree-scroll">
          <nav class="onto-treeview" aria-label="Ontology">
            <ul role="tree" id="ontoTreeRoot" aria-label="Ontology tree"></ul>
          </nav>
        </div>
      </aside>
      
      <div class="onto-resizer" id="ontoResizer" aria-hidden="true"></div>
      
      <aside class="onto-iconbar" aria-label="Ontology Tools">
        <div class="onto-icon" draggable="true" data-onto-type="class" title="Class">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <rect x="6" y="6" width="12" height="12" rx="2" />
          </svg>
        </div>
        <div class="onto-icon" draggable="true" data-onto-type="dataProperty" title="Data Property">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="7" cy="12" r="3" />
            <rect x="14" y="9" width="6" height="6" rx="1" />
          </svg>
        </div>
        <div class="onto-icon" draggable="true" data-onto-type="note" title="Note">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 4h12l4 4v12H4z" />
            <path d="M16 4v4h4" />
          </svg>
        </div>
      </aside>
      
      <div id="cy" role="application" aria-label="Ontology Graph Canvas"></div>
      
      <div class="onto-resizer" id="ontoPropsResizer" aria-hidden="true"></div>
      
      <aside class="onto-props" aria-label="Properties Panel">
        <div class="onto-props-header" id="ontoPropsHeader">
          <div class="muted">Properties</div>
          <button class="iconbtn" id="ontoPropsToggle" title="Collapse">
            <svg id="ontoPropsToggleIcon" viewBox="0 0 24 24" fill="none" stroke-width="1.6"
              stroke-linecap="round" stroke-linejoin="round">
              <path d="M9 6l6 6-6 6" />
            </svg>
          </button>
        </div>
        <div class="onto-props-scroll">
          <form id="ontoPropsForm" class="props-form">
            <!-- Properties form content -->
            <div class="props-section">
              <h4 class="props-section-title">Basic Properties</h4>
              <div class="form-group">
                <label class="form-label" for="propName">Name</label>
                <input id="propName" type="text" class="form-input" placeholder="Enter name..." />
              </div>
              <div class="form-group">
                <label class="form-label" for="propType">Type</label>
                <div id="propType" class="form-text-display">
                  <span id="propTypeValue">Class</span>
                </div>
              </div>
            </div>
          </form>
        </div>
      </aside>
    </div>

    <!-- Context Menus and Overlays -->
    <input id="ontoInlineEdit" type="text" />
    
    <div id="ontoContextMenu" class="onto-menu" style="display: none;">
      <div class="menu-section">
        <button id="menuAddRel" class="menu-item">
          <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round"
            stroke-linejoin="round">
            <circle cx="7" cy="12" r="3" />
            <circle cx="17" cy="12" r="3" />
            <path d="M10 12h4" />
          </svg>
          Add Relationship
        </button>
        <button id="menuAddDataProp" class="menu-item">
          <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round"
            stroke-linejoin="round">
            <circle cx="7" cy="12" r="3" />
            <rect x="14" y="9" width="6" height="6" rx="1" />
          </svg>
          Add Data Property
        </button>
      </div>
      <div class="menu-divider"></div>
      <div class="menu-section">
        <button id="menuCancel" class="menu-item menu-item-secondary">Cancel</button>
      </div>
    </div>

    <div id="edgeContextMenu" class="onto-menu" style="display: none;">
      <div class="menu-header" style="padding: 8px 12px; background: var(--panel-1); font-weight: 600; border-bottom: 1px solid var(--border); border-radius: 8px 8px 0 0; margin: -4px 0 4px;">
        <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round"
          stroke-linejoin="round" style="display: inline; vertical-align: middle; margin-right: 6px;">
          <path d="M3 12h18M12 3v18" />
        </svg>
        Multiplicity Constraint
      </div>
      <div class="menu-section">
        <button data-action="mult-none" class="menu-item">No constraint</button>
        <button data-action="mult-1" class="menu-item">Exactly one (1)</button>
        <button data-action="mult-0-1" class="menu-item">Zero or one (0..1)</button>
        <button data-action="mult-0-*" class="menu-item">Zero or more (0..*)</button>
        <button data-action="mult-1-*" class="menu-item">One or more (1..*)</button>
        <button data-action="mult-custom" class="menu-item">Custom range...</button>
      </div>
      <div class="menu-divider"></div>
      <div class="menu-section">
        <button data-action="edit-edge" class="menu-item">Edit relationship</button>
        <button id="edgeMenuCancel" class="menu-item menu-item-secondary">Cancel</button>
      </div>
    </div>

    <!-- Individual Tables Content Area -->
    <div id="individualsContent" class="individuals-content">
      <div class="individuals-tabs-nav">
        <div id="individualsTabList" class="individuals-tab-list">
          <div style="padding: 20px; text-align: center; color: var(--muted);">Loading...</div>
        </div>
      </div>
      <div class="individuals-table-area">
        <div id="individualsTableContent">
          <div style="padding: 40px; text-align: center; color: var(--muted);">
            <h3>Individual Tables</h3>
            <p>Select a class from the ontology to view and edit individuals</p>
          </div>
        </div>
      </div>
    </div>

    <!-- CQ/MT Content Area -->
    <div id="cqmtContent" class="cqmt-content">
      <div style="padding: 40px; text-align: center; color: var(--muted);">
        <h3>Competency Questions & Mapping Tables</h3>
        <p>Define competency questions and create mapping tables for data transformation</p>
      </div>
    </div>
  `;
}
