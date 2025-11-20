/**
 * ODRAS Living Project Lattice JavaScript
 * 
 * Provides real-time visualization of project lattice with:
 * - Proper grid layout (L0-L3 vertical, domains horizontal)
 * - Live event flow animations
 * - Project state transitions
 * - WebSocket integration for real-time updates
 */

class LatticeVisualizer {
    constructor() {
        this.cy = null;
        this.websocket = null;
        this.isConnected = false;
        this.projects = new Map();
        this.relationships = [];
        this.domains = new Set();
        this.layers = new Set([0, 1, 2, 3]);
        this.domainOrder = [];
        
        // Configuration
        this.websocketUrl = 'ws://localhost:8081';
        this.gridSpacing = {
            columnWidth: 180,  // Increased for better spacing
            rowHeight: 120,    // Increased for better spacing
            startX: 100,
            startY: 80
        };
        
        this.init();
    }
    
    init() {
        console.log('🔬 Initializing ODRAS Living Lattice Visualizer...');
        this.initCytoscape();
        this.initWebSocket();
        this.initEventHandlers();
        this.initMockSystems();
        console.log('✅ Lattice visualizer initialized');
    }
    
    initCytoscape() {
        const container = document.getElementById('cy');
        if (!container) {
            console.error('Cytoscape container not found');
            return;
        }
        
        this.cy = cytoscape({
            container: container,
            elements: [],
            style: [
                // Node styles
                {
                    selector: 'node',
                    style: {
                        'label': 'data(label)',
                        'width': 60,
                        'height': 60,
                        'shape': 'round-rectangle',
                        'background-color': function(ele) {
                            const level = ele.data('level');
                            const state = ele.data('state') || 'draft';
                            
                            // Base colors by level
                            let baseColor;
                            if (level === 0) baseColor = '#3b82f6';      // Blue
                            else if (level === 1) baseColor = '#10b981'; // Green
                            else if (level === 2) baseColor = '#f59e0b'; // Orange
                            else if (level === 3) baseColor = '#ef4444'; // Red
                            else baseColor = '#64748b';                  // Gray
                            
                            // For draft state, use rgba for transparency
                            if (state === 'draft') {
                                const r = parseInt(baseColor.substr(1, 2), 16);
                                const g = parseInt(baseColor.substr(3, 2), 16);
                                const b = parseInt(baseColor.substr(5, 2), 16);
                                return `rgba(${r}, ${g}, ${b}, 0.6)`;
                            }
                            
                            return baseColor; // Full opacity for other states
                        },
                        'color': '#ffffff',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'font-size': '10px',
                        'font-weight': 'bold',
                        'border-width': function(ele) {
                            const state = ele.data('state') || 'draft';
                            return state === 'processing' ? 4 : 2;
                        },
                        'border-color': function(ele) {
                            const state = ele.data('state') || 'draft';
                            if (state === 'processing') return '#fbbf24';  // Yellow for processing
                            else if (state === 'published') return '#10b981'; // Green for published
                            return '#334155';
                        },
                        'text-wrap': 'wrap',
                        'text-max-width': '50px'
                    }
                },
                // Processing animation
                {
                    selector: 'node[state="processing"]',
                    style: {
                        'border-width': 4,
                        'border-color': '#fbbf24',
                        'border-style': 'dashed'
                    }
                },
                // Parent-child edges (vertical)
                {
                    selector: 'edge[type="parent-child"]',
                    style: {
                        'width': 3,
                        'line-color': '#60a5fa',
                        'target-arrow-color': '#60a5fa',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'straight',
                        'arrow-scale': 1.2
                    }
                },
                // Cousin edges (horizontal)
                {
                    selector: 'edge[type="cousin"], edge[type="coordinates_with"]',
                    style: {
                        'width': 2,
                        'line-color': '#10b981',
                        'target-arrow-color': '#10b981',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'line-style': 'dashed',
                        'arrow-scale': 1.0
                    }
                },
                // Event flow animation
                {
                    selector: '.event-flow',
                    style: {
                        'width': 4,
                        'line-color': '#f59e0b',
                        'target-arrow-color': '#f59e0b',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'straight',
                        'arrow-scale': 1.5,
                        'opacity': 0.8
                    }
                }
            ],
            layout: {
                name: 'preset' // We'll position nodes manually in grid
            },
            minZoom: 0.3,
            maxZoom: 2.0,
            wheelSensitivity: 0.2
        });
        
        // Handle node selection
        this.cy.on('tap', 'node', (evt) => {
            const node = evt.target;
            const projectData = node.data();
            this.showProjectDetails(projectData);
        });
        
        // Handle node hover
        this.cy.on('mouseover', 'node', (evt) => {
            const node = evt.target;
            node.style('border-width', 4);
        });
        
        this.cy.on('mouseout', 'node', (evt) => {
            const node = evt.target;
            const state = node.data('state');
            node.style('border-width', state === 'processing' ? 4 : 2);
        });
    }
    
    initWebSocket() {
        console.log(`🔌 Connecting to WebSocket: ${this.websocketUrl}`);
        
        try {
            this.websocket = new WebSocket(this.websocketUrl);
            
            this.websocket.onopen = () => {
                console.log('✅ WebSocket connected');
                this.isConnected = true;
                this.updateConnectionStatus('connected', 'Connected');
                this.requestLatticeUpdate();
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (e) {
                    console.error('Error parsing WebSocket message:', e);
                }
            };
            
            this.websocket.onclose = () => {
                console.log('❌ WebSocket disconnected');
                this.isConnected = false;
                this.updateConnectionStatus('disconnected', 'Disconnected');
                
                // Attempt to reconnect after 3 seconds
                setTimeout(() => {
                    if (!this.isConnected) {
                        console.log('🔄 Attempting to reconnect...');
                        this.initWebSocket();
                    }
                }, 3000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                this.updateConnectionStatus('disconnected', 'Connection error');
            };
            
        } catch (e) {
            console.error('❌ Failed to create WebSocket:', e);
            this.updateConnectionStatus('disconnected', 'Connection failed');
        }
    }
    
    updateConnectionStatus(status, text) {
        const indicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        
        if (indicator) {
            indicator.className = `status-indicator ${status}`;
        }
        
        if (statusText) {
            statusText.textContent = text;
        }
    }
    
    requestLatticeUpdate() {
        if (this.websocket && this.isConnected) {
            this.websocket.send(JSON.stringify({
                type: 'request_lattice_update'
            }));
        }
    }
    
    handleWebSocketMessage(data) {
        const messageType = data.type;
        
        switch (messageType) {
            case 'initial_lattice':
            case 'lattice_update':
                this.updateLattice(data.data);
                break;
                
            case 'event':
            case 'simulated_event':
                this.handleLiveEvent(data);
                break;
                
            case 'project_state':
                this.updateProjectState(data.project_id, data.state);
                break;
                
            default:
                console.log('Unknown message type:', messageType);
        }
    }
    
    updateLattice(latticeData) {
        console.log('📊 Updating lattice visualization...');
        
        let projects = latticeData.projects || [];
        const relationships = latticeData.relationships || [];
        
        // ALWAYS infer project levels from names since API doesn't return them
        projects = projects.map(p => {
            const name = (p.name || '').toLowerCase();
            
            // Infer level from name patterns
            if (name.includes('foundation') || name.includes('ontology')) {
                p.project_level = 0;  // L0 Foundation
            } else if (name.includes('icd') || name.includes('mission-analysis') || name.includes('cost-strategy')) {
                p.project_level = 1;  // L1 Strategic
            } else if (name.includes('cdd') || name.includes('conops') || name.includes('affordability')) {
                p.project_level = 2;  // L2 Tactical
            } else if (name.includes('concept') || name.includes('trade-study')) {
                p.project_level = 3;  // L3 Concrete
            } else {
                // Default to 1 if we can't determine
                p.project_level = 1;
            }
            return p;
        });
        
        // Filter to only show the most recent lattice projects
        // Keep only the lattice project names we expect
        projects = projects.filter(p => {
            const name = (p.name || '').toLowerCase();
            const latticeNames = [
                'foundation-ontology', 'icd-development', 'mission-analysis', 'cost-strategy',
                'cdd-development', 'conops-development', 'affordability-analysis',
                'solution-concept-a', 'solution-concept-b', 'trade-study'
            ];
            return latticeNames.includes(name);
        });
        
        // If no lattice projects found, show the 10 most recent projects
        if (projects.length === 0) {
            console.log('No lattice projects found, showing 10 most recent...');
            projects = latticeData.projects.slice(0, 10);
            projects.forEach(p => {
                if (p.project_level === null || p.project_level === undefined) {
                    p.project_level = 1; // Default level for visualization
                }
            });
        }
        
        console.log(`Showing ${projects.length} projects (levels inferred if needed)`);
        
        // Debug: Log project details
        console.log('Project details:');
        projects.slice(0, 5).forEach(p => {
            console.log(`  ${p.name}: level=${p.project_level}, domain=${p.domain}`);
        });
        
        // Extract domains and organize projects
        this.domains.clear();
        this.projects.clear();
        
        projects.forEach(project => {
            const domain = project.domain || 'unknown';
            this.domains.add(domain);
            this.projects.set(project.project_id, project);
        });
        
        this.domainOrder = Array.from(this.domains).sort();
        this.relationships = relationships;
        
        // Update domain labels
        this.updateDomainLabels();
        
        // Create Cytoscape elements
        const elements = this.createCytoscapeElements(projects, relationships);
        
        // Update graph
        this.cy.elements().remove();
        this.cy.add(elements);
        
        // Apply grid layout
        this.applyGridLayout();
        
        // Update info display
        this.updateLatticeInfo(projects, relationships);
        
        console.log(`✅ Lattice updated: ${projects.length} projects, ${relationships.length} relationships`);
    }
    
    createCytoscapeElements(projects, relationships) {
        const elements = [];
        
        // Create nodes
        projects.forEach(project => {
            // Ensure project_level is a number
            const level = typeof project.project_level === 'number' ? project.project_level : 
                         project.project_level !== null && project.project_level !== undefined ? 
                         parseInt(project.project_level) : 0;
            
            const element = {
                data: {
                    id: project.project_id,
                    label: project.name || 'Project',
                    level: level,
                    domain: project.domain || 'unknown',
                    state: project.state || 'draft',
                    type: 'project'
                }
            };
            elements.push(element);
        });
        
        // Create edges for parent-child relationships
        projects.forEach(project => {
            if (project.parent_project_id) {
                elements.push({
                    data: {
                        id: `parent-${project.parent_project_id}-${project.project_id}`,
                        source: project.parent_project_id,
                        target: project.project_id,
                        type: 'parent-child'
                    }
                });
            }
        });
        
        // Create edges for cousin relationships
        relationships.forEach(rel => {
            elements.push({
                data: {
                    id: `cousin-${rel.source_project_id}-${rel.target_project_id}`,
                    source: rel.source_project_id,
                    target: rel.target_project_id,
                    type: rel.relationship_type || 'cousin'
                }
            });
        });
        
        return elements;
    }
    
    applyGridLayout() {
        const nodes = this.cy.nodes();
        
        // Group nodes by domain and layer to handle overlaps
        const gridCells = new Map();
        
        nodes.forEach(node => {
            const level = node.data('level') || 0;
            const domain = node.data('domain') || 'unknown';
            
            const key = `${domain}-${level}`;
            if (!gridCells.has(key)) {
                gridCells.set(key, []);
            }
            gridCells.get(key).push(node);
        });
        
        // Position nodes with offsets for multiple nodes in same cell
        gridCells.forEach((nodesInCell, key) => {
            const [domain, level] = key.split('-');
            const domainIndex = this.domainOrder.indexOf(domain);
            const layerIndex = parseInt(level) || 0;
            
            // Base position for this grid cell
            const baseX = this.gridSpacing.startX + (domainIndex * this.gridSpacing.columnWidth);
            const baseY = this.gridSpacing.startY + (layerIndex * this.gridSpacing.rowHeight);
            
            // If multiple nodes in same cell, offset them
            if (nodesInCell.length === 1) {
                nodesInCell[0].position({ x: baseX, y: baseY });
            } else {
                // Arrange multiple nodes in a small cluster
                const offsetRadius = 25;
                const angleStep = (2 * Math.PI) / nodesInCell.length;
                nodesInCell.forEach((node, index) => {
                    const angle = index * angleStep;
                    const offsetX = Math.cos(angle) * offsetRadius;
                    const offsetY = Math.sin(angle) * offsetRadius;
                    node.position({ 
                        x: baseX + offsetX, 
                        y: baseY + offsetY 
                    });
                });
            }
        });
        
        // Fit to view with padding
        this.cy.fit(this.cy.nodes(), 80);
    }
    
    updateDomainLabels() {
        const domainLabelsContainer = document.getElementById('domainLabels');
        if (!domainLabelsContainer) return;
        
        domainLabelsContainer.innerHTML = '';
        
        this.domainOrder.forEach(domain => {
            const label = document.createElement('div');
            label.className = 'domain-label';
            label.textContent = domain.toUpperCase();
            domainLabelsContainer.appendChild(label);
        });
    }
    
    updateLatticeInfo(projects, relationships) {
        document.getElementById('projectCount').textContent = projects.length;
        document.getElementById('relationshipCount').textContent = relationships.length;
        
        const activeProjects = projects.filter(p => p.state === 'published' || p.state === 'active');
        document.getElementById('activeProjectCount').textContent = activeProjects.length;
    }
    
    handleLiveEvent(eventData) {
        console.log('📡 Live event received:', eventData.event_type);
        
        // Add to event log
        this.addEventToLog(eventData);
        
        // Animate event flow
        this.animateEventFlow(eventData);
        
        // Update project states if necessary
        this.handleEventEffects(eventData);
    }
    
    addEventToLog(eventData) {
        const eventLog = document.getElementById('eventLog');
        if (!eventLog) return;
        
        // Rate limit: don't add duplicate events within 1 second
        const eventKey = `${eventData.event_type}-${eventData.source_project_id}`;
        const now = Date.now();
        if (!this.lastEventTimes) this.lastEventTimes = new Map();
        
        if (this.lastEventTimes.has(eventKey)) {
            const timeSince = now - this.lastEventTimes.get(eventKey);
            if (timeSince < 1000) { // Skip if less than 1 second since last
                return;
            }
        }
        this.lastEventTimes.set(eventKey, now);
        
        // Remove "no events" message
        const noEvents = eventLog.querySelector('.no-events');
        if (noEvents) noEvents.remove();
        
        const eventItem = document.createElement('div');
        eventItem.className = 'event-item';
        
        const time = new Date(eventData.timestamp || Date.now()).toLocaleTimeString();
        
        eventItem.innerHTML = `
            <div class="event-type">${eventData.event_type}</div>
            <div class="event-source">From: ${this.getProjectName(eventData.source_project_id)}</div>
            <div class="event-time">${time}</div>
        `;
        
        eventLog.insertBefore(eventItem, eventLog.firstChild);
        
        // Keep only last 10 events (reduced from 20)
        const events = eventLog.querySelectorAll('.event-item');
        if (events.length > 10) {
            events[events.length - 1].remove();
        }
    }
    
    animateEventFlow(eventData) {
        const sourceId = eventData.source_project_id;
        const sourceNode = this.cy.getElementById(sourceId);
        
        if (!sourceNode.length) return;
        
        // Flash source node
        this.flashNode(sourceNode);
        
        // Find subscribers and animate flow to them
        const subscribers = this.findEventSubscribers(eventData.event_type, sourceId);
        subscribers.forEach(targetId => {
            this.animateEventPath(sourceId, targetId);
        });
    }
    
    flashNode(node) {
        const originalColor = node.style('background-color');
        
        node.animate({
            style: { 'background-color': '#fbbf24' }
        }, {
            duration: 200,
            complete: () => {
                node.animate({
                    style: { 'background-color': originalColor }
                }, { duration: 200 });
            }
        });
    }
    
    animateEventPath(sourceId, targetId) {
        const sourceNode = this.cy.getElementById(sourceId);
        const targetNode = this.cy.getElementById(targetId);
        
        if (!sourceNode.length || !targetNode.length) return;
        
        // Create temporary edge for animation
        const tempEdgeId = `flow-${sourceId}-${targetId}-${Date.now()}`;
        const tempEdge = this.cy.add({
            data: {
                id: tempEdgeId,
                source: sourceId,
                target: targetId
            },
            classes: 'event-flow'
        });
        
        // Animate edge appearance
        tempEdge.style('opacity', 0);
        tempEdge.animate({
            style: { 'opacity': 1 }
        }, {
            duration: 500,
            complete: () => {
                // Flash target node
                this.flashNode(targetNode);
                
                // Remove temp edge after delay
                setTimeout(() => {
                    if (this.cy.getElementById(tempEdgeId).length) {
                        this.cy.remove(tempEdge);
                    }
                }, 1000);
            }
        });
    }
    
    findEventSubscribers(eventType, sourceId) {
        // Mock subscriber logic (in real implementation, would query ODRAS)
        const subscribers = [];
        
        // Simple rules for demo
        if (eventType.includes('requirements')) {
            // Requirements events go to analysis projects
            this.cy.nodes().forEach(node => {
                const domain = node.data('domain');
                const level = node.data('level');
                if (domain.includes('analysis') || (level > 1 && domain !== node.data('domain'))) {
                    subscribers.push(node.id());
                }
            });
        } else if (eventType.includes('scenarios')) {
            // Scenario events go to concept projects
            this.cy.nodes().forEach(node => {
                const level = node.data('level');
                if (level === 3) {
                    subscribers.push(node.id());
                }
            });
        }
        
        return subscribers;
    }
    
    handleEventEffects(eventData) {
        // Simulate project state changes in response to events
        const affectedProjects = this.findEventSubscribers(eventData.event_type, eventData.source_project_id);
        
        // Limit to prevent cascading loops - only process if not too many recent events
        const recentEventCount = this.getRecentEventCount(5000); // last 5 seconds
        if (recentEventCount > 10) {
            console.log('⚠️ Too many recent events, skipping cascade to prevent loop');
            return;
        }
        
        affectedProjects.forEach(projectId => {
            // Only process if project is not already processing
            const node = this.cy.getElementById(projectId);
            if (node.length && node.data('state') === 'processing') {
                return; // Skip if already processing
            }
            
            // Set project to processing state
            this.updateProjectState(projectId, 'processing');
            
            // After processing time, set to ready (but don't auto-publish)
            setTimeout(() => {
                this.updateProjectState(projectId, 'ready');
                // Removed automatic event publishing to prevent loops
            }, 2000 + Math.random() * 3000); // 2-5 second processing time
        });
    }
    
    updateProjectState(projectId, newState) {
        const node = this.cy.getElementById(projectId);
        if (node.length) {
            node.data('state', newState);
            
            // Update project in registry
            if (this.projects.has(projectId)) {
                const project = this.projects.get(projectId);
                project.state = newState;
                this.projects.set(projectId, project);
            }
        }
        
        console.log(`🔄 Project ${this.getProjectName(projectId)} state → ${newState}`);
    }
    
    simulateProcessingComplete(projectId) {
        // Simulate this project publishing an event after processing
        const project = this.projects.get(projectId);
        if (!project) return;
        
        const domain = project.domain || 'unknown';
        let eventType = 'analysis.complete';
        
        // Domain-specific event types
        if (domain.includes('systems-engineering')) eventType = 'requirements.approved';
        else if (domain.includes('mission')) eventType = 'scenarios.defined';
        else if (domain.includes('cost')) eventType = 'constraints.defined';
        else if (domain.includes('analysis')) eventType = 'analysis.complete';
        
        // Simulate publishing event
        this.simulateEvent(projectId, eventType, {
            project_name: project.name,
            completion_time: new Date().toISOString(),
            results: 'Processing complete'
        });
    }
    
    simulateEvent(sourceProjectId, eventType, eventData) {
        if (this.websocket && this.isConnected) {
            this.websocket.send(JSON.stringify({
                type: 'simulate_event',
                event_data: {
                    source_project_id: sourceProjectId,
                    event_type: eventType,
                    payload: eventData
                }
            }));
        }
    }
    
    getProjectName(projectId) {
        const project = this.projects.get(projectId);
        return project ? project.name : projectId;
    }
    
    showProjectDetails(projectData) {
        const detailsContainer = document.getElementById('projectDetails');
        if (!detailsContainer) return;
        
        const project = this.projects.get(projectData.id);
        if (!project) return;
        
        detailsContainer.innerHTML = `
            <div class="project-detail-item">
                <div class="project-detail-label">Name</div>
                <div class="project-detail-value">${project.name}</div>
            </div>
            <div class="project-detail-item">
                <div class="project-detail-label">Domain</div>
                <div class="project-detail-value">${project.domain}</div>
            </div>
            <div class="project-detail-item">
                <div class="project-detail-label">Layer</div>
                <div class="project-detail-value">L${project.project_level}</div>
            </div>
            <div class="project-detail-item">
                <div class="project-detail-label">State</div>
                <div class="project-detail-value">
                    <span class="project-state ${projectData.state || 'draft'}">${projectData.state || 'draft'}</span>
                </div>
            </div>
            <div class="project-detail-item">
                <div class="project-detail-label">Description</div>
                <div class="project-detail-value">${project.description || 'No description'}</div>
            </div>
        `;
    }
    
    initEventHandlers() {
        // Refresh button
        document.getElementById('refreshBtn')?.addEventListener('click', () => {
            this.requestLatticeUpdate();
        });
        
        // Simulate event button
        document.getElementById('simulateBtn')?.addEventListener('click', () => {
            this.showEventModal();
        });
        
        // Control buttons
        document.getElementById('activateProjectsBtn')?.addEventListener('click', () => {
            this.activateL1Projects();
        });
        
        document.getElementById('publishRequirementsBtn')?.addEventListener('click', () => {
            this.publishRequirementsEvent();
        });
        
        document.getElementById('changeRequirementBtn')?.addEventListener('click', () => {
            this.changeRequirementEvent();
        });
        
        // Modal handlers
        document.getElementById('cancelEventBtn')?.addEventListener('click', () => {
            this.hideEventModal();
        });
        
        document.getElementById('sendEventBtn')?.addEventListener('click', () => {
            this.sendSimulatedEvent();
        });
    }
    
    showEventModal() {
        const modal = document.getElementById('eventModal');
        const sourceSelect = document.getElementById('sourceProjectSelect');
        
        if (modal && sourceSelect) {
            // Populate project options
            sourceSelect.innerHTML = '<option value="">Select project...</option>';
            this.projects.forEach((project, id) => {
                const option = document.createElement('option');
                option.value = id;
                option.textContent = project.name;
                sourceSelect.appendChild(option);
            });
            
            modal.style.display = 'flex';
        }
    }
    
    hideEventModal() {
        const modal = document.getElementById('eventModal');
        if (modal) modal.style.display = 'none';
    }
    
    sendSimulatedEvent() {
        const sourceId = document.getElementById('sourceProjectSelect').value;
        const eventType = document.getElementById('eventTypeSelect').value;
        const eventDataText = document.getElementById('eventDataInput').value;
        
        if (!sourceId || !eventType) {
            alert('Please select source project and event type');
            return;
        }
        
        let eventData = {};
        if (eventDataText.trim()) {
            try {
                eventData = JSON.parse(eventDataText);
            } catch (e) {
                alert('Invalid JSON in event data');
                return;
            }
        }
        
        this.simulateEvent(sourceId, eventType, eventData);
        this.hideEventModal();
    }
    
    activateL1Projects() {
        this.cy.nodes().forEach(node => {
            if (node.data('level') === 1) {
                this.updateProjectState(node.id(), 'published');
            }
        });
        
        this.addDecisionToLog('Activated L1 strategic projects', 'User action: Projects ready for activation');
    }
    
    publishRequirementsEvent() {
        // Find requirements project and publish event
        const reqProject = Array.from(this.projects.values()).find(p => 
            p.name.includes('requirements') || p.name.includes('icd') || p.name.includes('cdd')
        );
        
        if (reqProject) {
            this.simulateEvent(reqProject.project_id, 'requirements.approved', {
                requirement_count: 15,
                approval_date: new Date().toISOString(),
                status: 'approved'
            });
            
            this.addDecisionToLog('Published requirements event', 'Requirements analysis complete');
        }
    }
    
    changeRequirementEvent() {
        // Simulate requirement change
        const reqProject = Array.from(this.projects.values()).find(p => 
            p.name.includes('requirements') || p.name.includes('icd') || p.name.includes('cdd')
        );
        
        if (reqProject) {
            this.simulateEvent(reqProject.project_id, 'requirement.changed', {
                changed_requirement: 'Surveillance range increased to 75 nautical miles',
                change_reason: 'Operational requirements update',
                impact: 'medium'
            });
            
            this.addDecisionToLog('Requirement changed', 'User modification: Surveillance range updated');
        }
    }
    
    addDecisionToLog(decision, justification) {
        const decisionLog = document.getElementById('decisionLog');
        if (!decisionLog) return;
        
        // Remove "no decisions" message
        const noDecisions = decisionLog.querySelector('.no-decisions');
        if (noDecisions) noDecisions.remove();
        
        const decisionItem = document.createElement('div');
        decisionItem.className = 'decision-item';
        
        decisionItem.innerHTML = `
            <div class="decision-text">${decision}</div>
            <div class="decision-justification">${justification}</div>
        `;
        
        decisionLog.insertBefore(decisionItem, decisionLog.firstChild);
        
        // Keep only last 10 decisions
        const decisions = decisionLog.querySelectorAll('.decision-item');
        if (decisions.length > 10) {
            decisions[decisions.length - 1].remove();
        }
    }
    
    initMockSystems() {
        // Start Gray System simulation
        this.startGraySystemSimulation();
        
        // Start X-layer simulation
        this.startXLayerSimulation();
    }
    
    startGraySystemSimulation() {
        setInterval(() => {
            // Simulate Gray System activity
            const status = document.getElementById('graySystemStatus');
            if (status) {
                const activities = ['Analyzing', 'Perturbing', 'Active', 'Evaluating'];
                status.textContent = activities[Math.floor(Math.random() * activities.length)];
            }
            
            // Randomly update project sensitivity (visual effect)
            this.cy.nodes().forEach(node => {
                if (Math.random() < 0.1) { // 10% chance per node
                    const sensitivity = Math.random();
                    if (sensitivity > 0.7) {
                        node.style('border-color', '#ef4444'); // High sensitivity
                    } else if (sensitivity > 0.4) {
                        node.style('border-color', '#f59e0b'); // Medium sensitivity
                    } else {
                        node.style('border-color', '#10b981'); // Low sensitivity
                    }
                    
                    // Reset after 3 seconds
                    setTimeout(() => {
                        const state = node.data('state');
                        if (state !== 'processing') {
                            node.style('border-color', '#334155');
                        }
                    }, 3000);
                }
            });
        }, 8000); // Update every 8 seconds
    }
    
    startXLayerSimulation() {
        setInterval(() => {
            // Simulate X-layer activity
            const status = document.getElementById('xLayerStatus');
            if (status) {
                const activities = ['Exploring', 'Generating', 'Evaluating', 'Optimizing'];
                status.textContent = activities[Math.floor(Math.random() * activities.length)];
            }
        }, 12000); // Update every 12 seconds
    }
    
    findEventSubscribers(eventType, sourceId) {
        // Mock subscription logic
        const subscribers = [];
        
        this.cy.nodes().forEach(node => {
            const nodeId = node.id();
            const level = node.data('level');
            const domain = node.data('domain');
            
            // Children of source project
            if (node.data('parent') === sourceId) {
                subscribers.push(nodeId);
            }
            
            // Cross-domain subscriptions based on event type
            if (eventType.includes('requirements') && level > 1) {
                subscribers.push(nodeId);
            } else if (eventType.includes('scenarios') && domain.includes('analysis')) {
                subscribers.push(nodeId);
            } else if (eventType.includes('constraints') && level === 3) {
                subscribers.push(nodeId);
            }
        });
        
        return subscribers;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.latticeVisualizer = new LatticeVisualizer();
});

// Global functions for debugging
window.requestUpdate = () => {
    if (window.latticeVisualizer) {
        window.latticeVisualizer.requestLatticeUpdate();
    }
};

window.simulateEvent = (sourceId, eventType, data) => {
    if (window.latticeVisualizer) {
        window.latticeVisualizer.simulateEvent(sourceId, eventType, data);
    }
};
