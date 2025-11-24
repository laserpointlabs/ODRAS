/**
 * Intelligent Project Lattice Generator
 * 
 * Uses LLM to analyze requirements and generate intelligent project structures.
 * Shows real data flowing between projects, not just events.
 */

class IntelligentLatticeGenerator {
    constructor() {
        this.cy = null;
        this.currentLattice = null;
        this.processingStates = new Map();
        this.dataStore = new Map(); // Stores actual data flowing between projects
        this.workflowHistory = []; // Stores complete workflow history with inputs/outputs
        this.llmAuditTrail = []; // Stores complete LLM interaction audit trail
        this.processingQueue = new Set(); // Tracks projects currently being processed
        this.completedProjects = new Set(); // Tracks completed projects
        this.pendingProjects = new Map(); // Maps project name -> {projectData, retryCount}
        this.authToken = null;
        this.projectRegistry = {}; // Maps project names to created project IDs
        this.createdProjects = [];
        this.baseUrl = 'http://localhost:8000';
        this.materialSolutions = []; // Available material solutions for evaluation
        this.finalRecommendation = null; // Final LLM recommendation after processing
        
        this.init();
    }
    
    init() {
        console.log('🧠 Initializing Intelligent Lattice Generator...');
        this.initCytoscape();
        this.initEventHandlers();
        this.initSolutionsHandlers();
        this.loadExampleRequirements();
        this.renderSolutionsList();
        console.log('✅ Intelligent generator ready');
    }
    
    initSolutionsHandlers() {
        // Load sample solutions button
        document.getElementById('loadSampleSolutionsBtn')?.addEventListener('click', () => {
            this.loadSampleSolutions();
        });
        
        // Add custom solution button
        document.getElementById('addSolutionBtn')?.addEventListener('click', () => {
            this.showAddSolutionDialog();
        });
        
        // Clear all solutions button
        document.getElementById('clearSolutionsBtn')?.addEventListener('click', () => {
            this.materialSolutions = [];
            this.renderSolutionsList();
            this.updateSolutionSummary();
        });
    }
    
    loadSampleSolutions() {
        // Sample UAV solutions - these are just context for the LLM
        this.materialSolutions = [
            {
                id: 'solution-1',
                name: 'SkyEagle X500',
                type: 'Fixed-Wing UAV',
                manufacturer: 'AeroTech Systems',
                specifications: {
                    endurance: '8-10 hours',
                    range: '150 km',
                    payload: '3.5 kg',
                    max_speed: '120 km/h',
                    wind_tolerance: '30 knots',
                    setup_time: '20 minutes',
                    cost: '$1.2M'
                },
                capabilities: ['Long endurance', 'High payload capacity', 'All-weather operation', 'Real-time video'],
                limitations: ['Requires runway/launcher', 'Complex setup', 'Limited hover capability']
            },
            {
                id: 'solution-2',
                name: 'AeroMapper X8',
                type: 'Fixed-Wing UAV',
                manufacturer: 'Precision Aero',
                specifications: {
                    endurance: '12-14 hours',
                    range: '200 km',
                    payload: '5 kg',
                    max_speed: '100 km/h',
                    wind_tolerance: '35 knots',
                    setup_time: '25 minutes',
                    cost: '$1.7M'
                },
                capabilities: ['Extended endurance', 'Heavy payload', 'Multi-sensor integration', 'Extreme weather operation'],
                limitations: ['Pneumatic launcher required', 'Higher cost', 'Longer setup time']
            },
            {
                id: 'solution-3',
                name: 'Falcon VTOL-X',
                type: 'VTOL Hybrid UAV',
                manufacturer: 'VertiFlight Inc',
                specifications: {
                    endurance: '5-6 hours',
                    range: '80 km',
                    payload: '2.5 kg',
                    max_speed: '90 km/h',
                    wind_tolerance: '25 knots',
                    setup_time: '10 minutes',
                    cost: '$850K'
                },
                capabilities: ['VTOL capability', 'Rapid deployment', 'Hover for inspection', 'Compact transport'],
                limitations: ['Lower endurance', 'Moderate payload', 'Complex transition mechanics']
            },
            {
                id: 'solution-4',
                name: 'SwiftScout Pro',
                type: 'Quadcopter UAV',
                manufacturer: 'DroneWorks',
                specifications: {
                    endurance: '45 minutes',
                    range: '10 km',
                    payload: '1.5 kg',
                    max_speed: '70 km/h',
                    wind_tolerance: '20 knots',
                    setup_time: '5 minutes',
                    cost: '$150K'
                },
                capabilities: ['Ultra-fast deployment', 'Precise hovering', 'Low cost', 'Easy operation'],
                limitations: ['Very limited endurance', 'Short range', 'Weather sensitive']
            },
            {
                id: 'solution-5',
                name: 'Endurance One',
                type: 'Solar-Electric UAV',
                manufacturer: 'SolarWing Systems',
                specifications: {
                    endurance: '24+ hours',
                    range: '500 km',
                    payload: '2 kg',
                    max_speed: '60 km/h',
                    wind_tolerance: '20 knots',
                    setup_time: '45 minutes',
                    cost: '$2.5M'
                },
                capabilities: ['Extreme endurance', 'Persistent surveillance', 'Low operating cost', 'Quiet operation'],
                limitations: ['Weather dependent', 'Slow speed', 'Complex assembly', 'High acquisition cost']
            }
        ];
        
        this.renderSolutionsList();
        this.updateSolutionSummary();
        console.log(`✅ Loaded ${this.materialSolutions.length} sample solutions`);
    }
    
    renderSolutionsList() {
        const container = document.getElementById('solutionsList');
        if (!container) return;
        
        if (this.materialSolutions.length === 0) {
            container.innerHTML = '<div class="no-solutions">No solutions defined. Click "Load Sample Solutions" to add example UAVs.</div>';
            return;
        }
        
        container.innerHTML = this.materialSolutions.map(solution => `
            <div class="solution-card" data-solution-id="${solution.id}">
                <button class="solution-remove-btn" onclick="window.intelligentLattice.removeSolution('${solution.id}')" title="Remove">✕</button>
                <div class="solution-card-header">
                    <div class="solution-card-name">${solution.name}</div>
                    <div class="solution-card-type">${solution.type}</div>
                </div>
                <div class="solution-card-specs">
                    <strong>Endurance:</strong> ${solution.specifications.endurance}<br>
                    <strong>Range:</strong> ${solution.specifications.range}<br>
                    <strong>Payload:</strong> ${solution.specifications.payload}<br>
                    <strong>Setup:</strong> ${solution.specifications.setup_time}<br>
                    <strong>Cost:</strong> ${solution.specifications.cost}
                </div>
            </div>
        `).join('');
    }
    
    removeSolution(solutionId) {
        this.materialSolutions = this.materialSolutions.filter(s => s.id !== solutionId);
        this.renderSolutionsList();
        this.updateSolutionSummary();
    }
    
    updateSolutionSummary() {
        const summaryDiv = document.getElementById('solutionSummary');
        if (!summaryDiv) return;
        
        if (this.materialSolutions.length === 0) {
            summaryDiv.style.display = 'none';
            return;
        }
        
        summaryDiv.style.display = 'block';
        summaryDiv.innerHTML = `
            <strong>📊 ${this.materialSolutions.length} solutions available for evaluation</strong>
            <div style="font-size: 0.85rem; color: var(--text-light); margin-top: 4px;">
                Types: ${[...new Set(this.materialSolutions.map(s => s.type))].join(', ')}
            </div>
        `;
    }
    
    showAddSolutionDialog() {
        const name = prompt('Solution Name (e.g., "Custom UAV Model"):');
        if (!name) return;
        
        const type = prompt('Solution Type (e.g., "Fixed-Wing UAV", "VTOL", "Quadcopter"):') || 'UAV';
        const endurance = prompt('Endurance (e.g., "4 hours"):') || 'Unknown';
        const range = prompt('Range (e.g., "50 km"):') || 'Unknown';
        const payload = prompt('Payload capacity (e.g., "2 kg"):') || 'Unknown';
        const cost = prompt('Cost (e.g., "$500K"):') || 'Unknown';
        const capabilities = prompt('Capabilities (comma-separated):') || '';
        
        const newSolution = {
            id: `solution-custom-${Date.now()}`,
            name: name,
            type: type,
            manufacturer: 'Custom',
            specifications: {
                endurance: endurance,
                range: range,
                payload: payload,
                max_speed: 'Unknown',
                wind_tolerance: 'Unknown',
                setup_time: 'Unknown',
                cost: cost
            },
            capabilities: capabilities.split(',').map(c => c.trim()).filter(c => c),
            limitations: []
        };
        
        this.materialSolutions.push(newSolution);
        this.renderSolutionsList();
        this.updateSolutionSummary();
    }
    
    getSolutionsContext() {
        // Format solutions as context for the LLM
        if (this.materialSolutions.length === 0) {
            return null;
        }
        
        return this.materialSolutions.map(s => ({
            name: s.name,
            type: s.type,
            manufacturer: s.manufacturer,
            specifications: s.specifications,
            capabilities: s.capabilities,
            limitations: s.limitations
        }));
    }
    
    initCytoscape() {
        const container = document.getElementById('cy');
        
        this.cy = cytoscape({
            container: container,
            elements: [],
            style: [
                {
                    selector: 'node',
                    style: {
                        'label': 'data(label)',
                        'width': 100,
                        'height': 80,
                        'shape': 'round-rectangle',
                        'background-color': function(ele) {
                            const level = ele.data('level');
                            const state = ele.data('state') || 'inactive';
                            
                            let baseColor;
                            if (level === 0) baseColor = '#3b82f6';      // Blue
                            else if (level === 1) baseColor = '#10b981'; // Green  
                            else if (level === 2) baseColor = '#f59e0b'; // Orange
                            else if (level === 3) baseColor = '#ef4444'; // Red
                            else baseColor = '#64748b';                  // Gray
                            
                            if (state === 'inactive') {
                                const r = parseInt(baseColor.substr(1, 2), 16);
                                const g = parseInt(baseColor.substr(3, 2), 16);
                                const b = parseInt(baseColor.substr(5, 2), 16);
                                return `rgba(${r}, ${g}, ${b}, 0.3)`;
                            } else if (state === 'processing') {
                                return '#fbbf24'; // Bright yellow for processing
                            }
                            
                            return baseColor;
                        },
                        'color': '#ffffff',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'font-size': '11px',
                        'font-weight': 'bold',
                        'border-width': 2,
                        'border-color': '#334155',
                        'text-wrap': 'wrap',
                        'text-max-width': '90px',
                        'opacity': 1,
                        'z-index': 1
                    }
                },
                {
                    selector: 'node[state="processing"]',
                    style: {
                        'width': 140,
                        'height': 110,
                        'background-color': '#fbbf24',
                        'border-width': 6,
                        'border-color': '#f59e0b',
                        'font-size': '13px',
                        'font-weight': 'bold',
                        'opacity': 1,
                        'z-index': 10,
                        'overlay-opacity': 0.3,
                        'overlay-color': '#fbbf24',
                        'overlay-padding': '12px',
                        'transition-property': 'width, height, border-width, font-size, overlay-opacity',
                        'transition-duration': '0.3s',
                        'transition-timing-function': 'ease-in-out'
                    }
                },
                {
                    selector: 'node[state="complete"]',
                    style: {
                        'border-width': 3,
                        'border-color': '#10b981',
                        'opacity': 0.9
                    }
                },
                {
                    selector: 'node[state="error"]',
                    style: {
                        'background-color': '#ef4444',
                        'border-color': '#dc2626',
                        'border-width': 4
                    }
                },
                {
                    selector: 'node[state="waiting"]',
                    style: {
                        'background-color': '#64748b',
                        'border-color': '#f59e0b', // Orange/amber for visibility
                        'border-width': 5, // Thicker border
                        'opacity': 0.85, // More visible
                        'border-style': 'dashed',
                        'border-opacity': 1,
                        'overlay-opacity': 0.2,
                        'overlay-color': '#f59e0b',
                        'overlay-padding': '8px',
                        'z-index': 5
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 3,
                        'line-color': '#60a5fa',
                        'target-arrow-color': '#60a5fa', 
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'label': 'data(label)',
                        'font-size': '9px',
                        'color': '#cbd5e1',
                        'text-rotation': 'autorotate'
                    }
                },
                {
                    selector: '.data-flowing',
                    style: {
                        'line-color': '#fbbf24',
                        'target-arrow-color': '#fbbf24',
                        'width': 5
                    }
                }
            ],
            layout: { name: 'preset' },
            minZoom: 0.3,
            maxZoom: 2.0
        });
        
        // Handle node clicks
        this.cy.on('tap', 'node', (evt) => {
            const node = evt.target;
            this.showProjectDetails(node.data());
        });
    }
    
    initEventHandlers() {
        // File upload
        document.getElementById('requirementsFile')?.addEventListener('change', (e) => {
            this.handleFileUpload(e);
        });
        
        // Load example
        document.getElementById('loadExampleBtn')?.addEventListener('click', () => {
            this.loadExampleRequirements();
        });
        
        // Generate lattice
        document.getElementById('generateLatticeBtn')?.addEventListener('click', () => {
            this.generateLattice();
        });
        
        // Save results
        document.getElementById('saveResultsBtn')?.addEventListener('click', () => {
            this.saveResults();
        });
        
        // Controls
        document.getElementById('activateProjectsBtn')?.addEventListener('click', () => {
            this.startProcessing();
        });
        
        document.getElementById('stepThroughBtn')?.addEventListener('click', () => {
            this.stepThroughProcessing();
        });
        
        document.getElementById('resetBtn')?.addEventListener('click', () => {
            this.resetDemo();
        });
        
        // Debug panel control
        document.getElementById('showDebugBtn')?.addEventListener('click', () => {
            this.showDebugContext();
        });
    }
    
    loadExampleRequirements() {
        const exampleRequirements = `# UAV Mission Requirements for Disaster Response

## Operational Requirements

**MUST Requirements:**
- The system MUST provide the ability to survey 5-10 square kilometers within 2 hours
- The UAS MUST operate in winds up to 25 knots
- The system MUST provide 24/7 operational capability
- The UAS MUST be ready for flight within 15 minutes of arrival on scene
- The system MUST maintain operational costs below $500 per flight hour

**SHALL Requirements:** 
- The UAS SHALL maintain a minimum 50 km operational radius
- The UAS SHALL operate at variable altitudes from 100-3000 meters AGL
- The UAS SHALL provide a minimum 2 kg payload capacity
- The system SHALL include an IR camera with heat detection capabilities
- The UAS SHALL have an acquisition cost below $2M for complete system

**SHOULD Requirements:**
- The UAS SHOULD be able to revisit the same area multiple times per day
- The system SHOULD function in light to moderate rainfall conditions  
- The UAS SHOULD be able to swap payload packages in under 10 minutes

## Key Performance Parameters
- Area coverage rate ≥ 2.5 km²/hour
- Wind tolerance ≥ 25 knots
- Operational range ≥ 50 km  
- Flight endurance ≥ 3 hours
- Payload capacity ≥ 2 kg
- Camera resolution ≥ 4K

## Mission Context
Emergency response teams need rapid deployment UAV capability for disaster assessment and search operations in challenging environmental conditions.`;

        document.getElementById('requirementsInput').value = exampleRequirements;
        this.updateAnalysisStatus('Example requirements loaded');
    }
    
    async handleFileUpload(event) {
        const file = event.target.files[0];
        if (file) {
            try {
                const text = await file.text();
                document.getElementById('requirementsInput').value = text;
                this.updateAnalysisStatus(`Loaded: ${file.name}`);
            } catch (error) {
                this.updateAnalysisStatus(`Error loading file: ${error.message}`);
            }
        }
    }
    
    async generateLattice() {
        const requirementsText = document.getElementById('requirementsInput').value.trim();
        
        if (!requirementsText) {
            alert('Please enter or load requirements first');
            return;
        }
        
        this.updateAnalysisStatus('🧠 Analyzing requirements with LLM...');
        document.getElementById('generateLatticeBtn').disabled = true;
        
        try {
            // Call the actual LLM service with solutions context
            console.log('📡 Calling LLM Service...');
            const solutionsContext = this.getSolutionsContext();
            const requestBody = { 
                requirements: requirementsText,
                max_projects: 6
            };
            
            // Include solutions if available
            if (solutionsContext && solutionsContext.length > 0) {
                requestBody.available_solutions = solutionsContext;
                console.log(`📦 Including ${solutionsContext.length} material solutions in context`);
            }
            
            const response = await fetch('http://localhost:8083/generate-lattice', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
            
            if (response.ok) {
                this.currentLattice = await response.json();
                
                // Fetch debug context to show LLM interaction
                const debugResponse = await fetch('http://localhost:8083/debug-context');
                if (debugResponse.ok) {
                    this.debugContext = await debugResponse.json();
                    
                    // Store lattice generation audit trail
                    if (this.debugContext.last_generation) {
                        const lastGen = this.debugContext.last_generation;
                        this.llmAuditTrail.push({
                            step_type: 'lattice_generation',
                            step_number: 0,
                            timestamp: new Date().toISOString(),
                            project_name: 'Lattice Generation',
                            prompt: lastGen.prompt_sent || lastGen.prompt || 'N/A',
                            raw_response: lastGen.raw_response || 'N/A',
                            parsed_result: lastGen.parsed_lattice || this.currentLattice,
                            source: lastGen.source || 'unknown',
                            success: lastGen.success !== false
                        });
                    }
                    
                    this.showDebugContext();
                    
                    // Show debug button for reopening
                    document.getElementById('showDebugBtn').style.display = 'block';
                }
                
                this.updateAnalysisStatus('✅ Real LLM generation complete');
                console.log('✅ Used real LLM service');
                
                // Show audit trail button
                document.getElementById('showAuditTrailBtn').style.display = 'block';
                
                // Show save results button
                document.getElementById('saveResultsBtn').style.display = 'block';
            } else {
                throw new Error(`LLM service error: ${response.status}`);
            }
            
            // Display analysis results
            this.displayAnalysisResults();
            
            // Create projects in ODRAS
            await this.createProjectsInODRAS();
            
            // Create visualization  
            this.createLatticeVisualization();
            
            // Enable controls
            this.enableControls();
            
        } catch (error) {
            console.error('LLM service unavailable:', error);
            console.log('📋 Falling back to probabilistic mock...');
            
            // Use probabilistic mock that varies each time
            this.currentLattice = this.generateProbabilisticMock(requirementsText);
            this.displayAnalysisResults();
            
            // Create projects in ODRAS even for mock
            await this.createProjectsInODRAS();
            
            this.createLatticeVisualization();
            this.enableControls();
            this.updateAnalysisStatus('✅ Generated using probabilistic mock');
            
            // Show debug button even for mock
            document.getElementById('showDebugBtn').style.display = 'block';
            
            // Show save results button
            document.getElementById('saveResultsBtn').style.display = 'block';
        } finally {
            document.getElementById('generateLatticeBtn').disabled = false;
        }
    }
    
    showDebugContext() {
        if (!this.debugContext && !this.currentLattice) return;
        
        // If no debug context but have current lattice, show lattice info
        if (!this.debugContext) {
            this.showMockDebugInfo();
            return;
        }
        
        console.log('🔍 LLM Debug Context:', this.debugContext);
        
        // Add debug panel to show LLM interaction
        const debugPanel = document.createElement('div');
        debugPanel.id = 'debugPanel';
        debugPanel.style.cssText = `
            position: fixed; 
            top: 20px; 
            right: 20px; 
            width: 400px; 
            max-height: 80vh; 
            background: var(--dark-2); 
            border: 2px solid var(--primary); 
            border-radius: 8px; 
            padding: 16px; 
            z-index: 1000;
            overflow-y: auto;
            font-size: 0.8rem;
        `;
        
        const lastGen = this.debugContext.last_generation;
        if (lastGen) {
            debugPanel.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h4 style="color: var(--primary); margin: 0;">🔍 LLM Debug Context</h4>
                    <button onclick="this.parentElement.parentElement.remove()" style="background: var(--danger); color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer;">✕</button>
                </div>
                
                <div style="margin-bottom: 8px;">
                    <strong>Source:</strong> ${lastGen.source}<br>
                    <strong>Generation ID:</strong> ${lastGen.generation_id}<br>
                    <strong>Probabilistic:</strong> ${lastGen.probabilistic ? '✅' : '❌'}<br>
                    ${lastGen.fallback_reason ? `<strong style="color: var(--warning);">Fallback Reason:</strong> ${lastGen.fallback_reason}<br>` : ''}
                </div>
                
                <details style="margin-bottom: 8px;">
                    <summary style="cursor: pointer; font-weight: bold; color: var(--warning);">📝 Prompt Sent to LLM</summary>
                    <pre style="background: var(--dark-3); padding: 8px; border-radius: 4px; margin-top: 4px; white-space: pre-wrap; font-size: 0.7rem; max-height: 200px; overflow-y: auto;">${lastGen.prompt_sent}</pre>
                </details>
                
                <details style="margin-bottom: 8px;">
                    <summary style="cursor: pointer; font-weight: bold; color: var(--success);">🤖 Raw LLM Response</summary>
                    <pre style="background: var(--dark-3); padding: 8px; border-radius: 4px; margin-top: 4px; white-space: pre-wrap; font-size: 0.7rem; max-height: 200px; overflow-y: auto;">${lastGen.raw_response}</pre>
                </details>
                
                <div>
                    <strong style="color: var(--primary);">📊 Parsed Result:</strong><br>
                    <div style="font-size: 0.7rem;">
                        Projects: ${lastGen.parsed_lattice.projects?.length || 0}<br>
                        Data Flows: ${lastGen.parsed_lattice.data_flows?.length || 0}<br>
                        Confidence: ${Math.round((lastGen.parsed_lattice.confidence || 0) * 100)}%<br>
                        Type: ${lastGen.parsed_lattice.lattice_type || 'standard'}
                    </div>
                </div>
            `;
        } else {
            debugPanel.innerHTML = `
                <h4 style="color: var(--primary);">🔍 LLM Debug Context</h4>
                <div>No debug context available</div>
            `;
        }
        
        // Remove existing debug panel if any
        const existing = document.getElementById('debugPanel');
        if (existing) existing.remove();
        
        document.body.appendChild(debugPanel);
    }
    
    showMockDebugInfo() {
        // Show debug info for mock generation
        const debugPanel = document.createElement('div');
        debugPanel.id = 'debugPanel';
        debugPanel.style.cssText = `
            position: fixed; 
            top: 20px; 
            right: 20px; 
            width: 400px; 
            max-height: 80vh; 
            background: var(--dark-2); 
            border: 2px solid var(--warning); 
            border-radius: 8px; 
            padding: 16px; 
            z-index: 1000;
            overflow-y: auto;
            font-size: 0.8rem;
        `;
        
        debugPanel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h4 style="color: var(--warning); margin: 0;">🔍 Generation Context (Mock)</h4>
                <button onclick="this.parentElement.parentElement.remove()" style="background: var(--danger); color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer;">✕</button>
            </div>
            
            <div style="margin-bottom: 8px;">
                <strong>Source:</strong> Probabilistic Mock LLM<br>
                <strong>Type:</strong> ${this.currentLattice.lattice_type || 'mock_generation'}<br>
                <strong>Probabilistic:</strong> ✅ Yes<br>
            </div>
            
            <div style="margin-bottom: 8px; padding: 8px; background: var(--dark-3); border-radius: 4px;">
                <strong style="color: var(--warning);">📝 Mock Analysis Process:</strong><br>
                <div style="font-size: 0.75rem; margin-top: 4px;">
                    1. Analyzed requirements for key themes (disaster, performance, etc.)<br>
                    2. Probabilistically selected variant based on content<br>
                    3. Generated ${this.currentLattice.projects?.length || 0} projects with logical relationships<br>
                    4. Each run produces different structure (truly probabilistic)
                </div>
            </div>
            
            <div style="margin-bottom: 8px;">
                <strong style="color: var(--primary);">📊 Generated Structure:</strong><br>
                <div style="font-size: 0.75rem;">
                    Projects: ${this.currentLattice.projects?.length || 0}<br>
                    Data Flows: ${this.currentLattice.data_flows?.length || 0}<br>
                    Confidence: ${Math.round((this.currentLattice.confidence || 0) * 100)}%<br>
                    Domains: ${this.currentLattice.domains?.join(', ') || 'unknown'}
                </div>
            </div>
            
            <div style="background: var(--dark-3); padding: 8px; border-radius: 4px; font-size: 0.75rem;">
                <strong>Analysis Summary:</strong><br>
                ${this.currentLattice.analysis_summary || 'No summary available'}
            </div>
            
            <div style="margin-top: 8px; padding: 8px; background: rgba(16, 185, 129, 0.1); border-radius: 4px; font-size: 0.75rem;">
                <strong style="color: var(--success);">💡 To see real OpenAI context:</strong><br>
                Set OPENAI_API_KEY in .env file and restart the LLM service
            </div>
        `;
        
        // Remove existing debug panel
        const existing = document.getElementById('debugPanel');
        if (existing) existing.remove();
        
        document.body.appendChild(debugPanel);
    }
    
    generateProbabilisticMock(requirements) {
        // Generate different lattice structures based on content - TRULY PROBABILISTIC
        const reqLower = requirements.toLowerCase();
        const random = Math.random();
        
        // Add randomness to structure selection
        if (reqLower.includes('disaster') && reqLower.includes('emergency')) {
            if (random > 0.6) {
                return this.getDisasterResponseVariant();
            } else {
                return this.getEmergencyOptimizedVariant(); 
            }
        } else if (reqLower.includes('performance') || reqLower.includes('endurance')) {
            if (random > 0.5) {
                return this.getPerformanceVariant();
            } else {
                return this.getEnduranceOptimizedVariant();
            }
        } else {
            // Random selection of general variants
            const variants = [this.getGeneralVariantA(), this.getGeneralVariantB()];
            return variants[Math.floor(random * variants.length)];
        }
    }
    
    getDisasterResponseVariant() {
        return {
            analysis_summary: "VARIANT A: Emergency-focused lattice with rapid deployment emphasis. Probabilistic generation detected disaster response priority.",
            confidence: 0.89,
            lattice_type: "emergency_response_variant_a",
            projects: [
                {
                    name: "emergency-requirements", domain: "systems-engineering", layer: 1,
                    description: "Rapid requirements analysis for emergency response",
                    purpose: "Extract time-critical requirements for emergency UAV deployment",
                    inputs: ["emergency_specs", "deployment_timelines"],
                    outputs: ["critical_requirements", "emergency_constraints"],
                    processing_type: "analysis", publishes: ["emergency.analyzed"]
                },
                {
                    name: "rapid-deployment", domain: "mission-planning", layer: 2,
                    description: "Design rapid deployment procedures",
                    purpose: "Develop 15-minute deployment capability",
                    inputs: ["critical_requirements", "field_conditions"],
                    outputs: ["deployment_procedures", "setup_protocols"], 
                    processing_type: "analysis", parent_name: "emergency-requirements",
                    subscribes_to: ["emergency.analyzed"], publishes: ["deployment.ready"]
                },
                {
                    name: "resilience-assessment", domain: "analysis", layer: 2,
                    description: "Assess system resilience for emergency conditions",
                    purpose: "Evaluate UAV robustness for emergency operations",
                    inputs: ["emergency_constraints", "environmental_factors"],
                    outputs: ["resilience_metrics", "failure_modes"],
                    processing_type: "analysis", parent_name: "emergency-requirements",
                    subscribes_to: ["emergency.analyzed"], publishes: ["resilience.assessed"]
                },
                {
                    name: "emergency-optimized-selection", domain: "analysis", layer: 3,
                    description: "Select UAV optimized for emergency response",
                    purpose: "Choose UAV best suited for emergency deployment scenarios",
                    inputs: ["deployment_procedures", "resilience_metrics"],
                    outputs: ["emergency_recommendation", "risk_mitigation"],
                    processing_type: "evaluation", parent_name: "rapid-deployment",
                    subscribes_to: ["deployment.ready", "resilience.assessed"], publishes: ["solution.emergency_optimized"]
                }
            ],
            data_flows: [
                { from_project: "emergency-requirements", to_project: "rapid-deployment", data_type: "critical_requirements", description: "Critical reqs drive deployment design", trigger_event: "emergency.analyzed" },
                { from_project: "emergency-requirements", to_project: "resilience-assessment", data_type: "emergency_constraints", description: "Constraints inform resilience analysis", trigger_event: "emergency.analyzed" },
                { from_project: "rapid-deployment", to_project: "emergency-optimized-selection", data_type: "deployment_procedures", description: "Deployment procedures guide selection", trigger_event: "deployment.ready" },
                { from_project: "resilience-assessment", to_project: "emergency-optimized-selection", data_type: "resilience_metrics", description: "Resilience metrics ensure robust selection", trigger_event: "resilience.assessed" }
            ],
            domains: ["systems-engineering", "mission-planning", "analysis"]
        };
    }
    
    getEmergencyOptimizedVariant() { 
        return {
            analysis_summary: "VARIANT B: Emergency-optimized lattice emphasizing operational resilience. Alternative probabilistic structure.",
            confidence: 0.86,
            lattice_type: "emergency_response_variant_b",
            projects: [
                {
                    name: "emergency-needs-analysis", domain: "systems-engineering", layer: 1,
                    description: "Analyze emergency response needs and constraints",
                    purpose: "Understand emergency operational requirements",
                    inputs: ["response_scenarios", "operational_demands"],
                    outputs: ["emergency_needs", "operational_requirements"],
                    processing_type: "analysis", publishes: ["needs.analyzed"]
                },
                {
                    name: "operational-resilience", domain: "mission-planning", layer: 2,
                    description: "Design resilient operational concepts",
                    purpose: "Create robust operational concepts for emergency use",
                    inputs: ["emergency_needs", "resilience_criteria"],
                    outputs: ["resilient_operations", "contingency_plans"],
                    processing_type: "design", parent_name: "emergency-needs-analysis",
                    subscribes_to: ["needs.analyzed"], publishes: ["operations.designed"]
                },
                {
                    name: "capability-optimization", domain: "analysis", layer: 2,
                    description: "Optimize UAV capabilities for emergency scenarios",
                    purpose: "Match UAV capabilities to emergency needs",
                    inputs: ["operational_requirements", "uav_capabilities"],
                    outputs: ["optimized_capabilities", "performance_targets"],
                    processing_type: "analysis", parent_name: "emergency-needs-analysis", 
                    subscribes_to: ["needs.analyzed"], publishes: ["capabilities.optimized"]
                },
                {
                    name: "resilient-solution", domain: "analysis", layer: 3,
                    description: "Select most resilient UAV solution",
                    purpose: "Choose UAV with highest operational resilience",
                    inputs: ["resilient_operations", "optimized_capabilities"],
                    outputs: ["resilient_recommendation", "robustness_analysis"],
                    processing_type: "evaluation", parent_name: "operational-resilience",
                    subscribes_to: ["operations.designed", "capabilities.optimized"], publishes: ["solution.resilience_optimized"]
                }
            ],
            data_flows: [
                { from_project: "emergency-needs-analysis", to_project: "operational-resilience", data_type: "emergency_needs", description: "Emergency needs drive operational design", trigger_event: "needs.analyzed" },
                { from_project: "emergency-needs-analysis", to_project: "capability-optimization", data_type: "operational_requirements", description: "Requirements drive capability optimization", trigger_event: "needs.analyzed" },
                { from_project: "operational-resilience", to_project: "resilient-solution", data_type: "resilient_operations", description: "Resilient operations guide solution selection", trigger_event: "operations.designed" },
                { from_project: "capability-optimization", to_project: "resilient-solution", data_type: "optimized_capabilities", description: "Optimized capabilities ensure robust selection", trigger_event: "capabilities.optimized" }
            ],
            domains: ["systems-engineering", "mission-planning", "analysis"]
        };
    }
    
    getPerformanceVariant() {
        return {
            analysis_summary: "VARIANT A: Performance-centric lattice focusing on technical optimization. Generated probabilistically from performance keywords.",
            confidence: 0.84,
            lattice_type: "performance_variant_a",
            projects: [
                { name: "technical-requirements", domain: "systems-engineering", layer: 1, description: "Analyze technical performance requirements", purpose: "Extract performance specifications and constraints", inputs: ["performance_docs", "technical_specs"], outputs: ["performance_requirements", "technical_constraints"], processing_type: "analysis", publishes: ["technical.analyzed"] },
                { name: "performance-modeling", domain: "analysis", layer: 2, description: "Model UAV performance characteristics", purpose: "Create performance models for UAV evaluation", inputs: ["performance_requirements", "uav_specs"], outputs: ["performance_models", "capability_matrix"], processing_type: "analysis", parent_name: "technical-requirements", subscribes_to: ["technical.analyzed"], publishes: ["modeling.complete"] },
                { name: "optimization-analysis", domain: "analysis", layer: 2, description: "Optimize performance parameters", purpose: "Find optimal UAV configuration for performance", inputs: ["technical_constraints", "optimization_criteria"], outputs: ["optimization_results", "trade_recommendations"], processing_type: "analysis", parent_name: "technical-requirements", subscribes_to: ["technical.analyzed"], publishes: ["optimization.complete"] },
                { name: "performance-selection", domain: "analysis", layer: 3, description: "Select performance-optimized UAV", purpose: "Choose UAV with best performance characteristics", inputs: ["performance_models", "optimization_results"], outputs: ["performance_recommendation", "technical_justification"], processing_type: "evaluation", parent_name: "performance-modeling", subscribes_to: ["modeling.complete", "optimization.complete"], publishes: ["solution.performance_optimized"] }
            ],
            data_flows: [
                { from_project: "technical-requirements", to_project: "performance-modeling", data_type: "performance_requirements", description: "Performance requirements drive modeling", trigger_event: "technical.analyzed" },
                { from_project: "technical-requirements", to_project: "optimization-analysis", data_type: "technical_constraints", description: "Constraints guide optimization", trigger_event: "technical.analyzed" },
                { from_project: "performance-modeling", to_project: "performance-selection", data_type: "performance_models", description: "Models inform selection", trigger_event: "modeling.complete" },
                { from_project: "optimization-analysis", to_project: "performance-selection", data_type: "optimization_results", description: "Optimization results guide selection", trigger_event: "optimization.complete" }
            ],
            domains: ["systems-engineering", "analysis"]
        };
    }
    
    getEnduranceOptimizedVariant() {
        return {
            analysis_summary: "VARIANT B: Endurance-optimized lattice with extended operation focus. Alternative probabilistic generation.",
            confidence: 0.81,
            lattice_type: "performance_variant_b",
            projects: [
                { name: "endurance-requirements", domain: "systems-engineering", layer: 1, description: "Analyze endurance and operational requirements", purpose: "Focus on long-duration operational needs", inputs: ["endurance_specs", "operational_profiles"], outputs: ["endurance_requirements", "operational_constraints"], processing_type: "analysis", publishes: ["endurance.analyzed"] },
                { name: "mission-endurance", domain: "mission-planning", layer: 2, description: "Plan extended mission operations", purpose: "Design extended operation mission profiles", inputs: ["endurance_requirements", "mission_contexts"], outputs: ["extended_missions", "endurance_scenarios"], processing_type: "design", parent_name: "endurance-requirements", subscribes_to: ["endurance.analyzed"], publishes: ["missions.extended"] },
                { name: "endurance-evaluation", domain: "analysis", layer: 2, description: "Evaluate UAV endurance capabilities", purpose: "Assess UAV endurance against mission needs", inputs: ["operational_constraints", "uav_endurance_data"], outputs: ["endurance_assessment", "capability_gaps"], processing_type: "analysis", parent_name: "endurance-requirements", subscribes_to: ["endurance.analyzed"], publishes: ["endurance.evaluated"] },
                { name: "long-endurance-selection", domain: "analysis", layer: 3, description: "Select long-endurance UAV solution", purpose: "Choose UAV optimized for extended operations", inputs: ["extended_missions", "endurance_assessment"], outputs: ["endurance_recommendation", "operational_plan"], processing_type: "evaluation", parent_name: "mission-endurance", subscribes_to: ["missions.extended", "endurance.evaluated"], publishes: ["solution.endurance_optimized"] }
            ],
            data_flows: [
                { from_project: "endurance-requirements", to_project: "mission-endurance", data_type: "endurance_requirements", description: "Endurance needs drive mission design", trigger_event: "endurance.analyzed" },
                { from_project: "endurance-requirements", to_project: "endurance-evaluation", data_type: "operational_constraints", description: "Constraints guide endurance evaluation", trigger_event: "endurance.analyzed" },
                { from_project: "mission-endurance", to_project: "long-endurance-selection", data_type: "extended_missions", description: "Extended missions inform selection", trigger_event: "missions.extended" },
                { from_project: "endurance-evaluation", to_project: "long-endurance-selection", data_type: "endurance_assessment", description: "Endurance assessment guides selection", trigger_event: "endurance.evaluated" }
            ],
            domains: ["systems-engineering", "mission-planning", "analysis"]
        };
    }
    
    getGeneralVariantA() {
        return {
            analysis_summary: "VARIANT A: Comprehensive analysis lattice with balanced approach. Randomly selected structure.",
            confidence: 0.76,
            lattice_type: "general_variant_a",
            projects: [
                { name: "balanced-requirements", domain: "systems-engineering", layer: 1, description: "Balanced requirements analysis", purpose: "Comprehensive requirements decomposition", inputs: ["all_requirements"], outputs: ["requirement_hierarchy"], processing_type: "analysis", publishes: ["requirements.balanced"] },
                { name: "system-design", domain: "architecture", layer: 2, description: "System architecture design", purpose: "Design comprehensive system solution", inputs: ["requirement_hierarchy"], outputs: ["system_design"], processing_type: "design", parent_name: "balanced-requirements", subscribes_to: ["requirements.balanced"], publishes: ["design.complete"] },
                { name: "integrated-evaluation", domain: "analysis", layer: 3, description: "Integrated solution evaluation", purpose: "Evaluate complete system solution", inputs: ["system_design"], outputs: ["evaluation_results"], processing_type: "evaluation", parent_name: "system-design", subscribes_to: ["design.complete"], publishes: ["evaluation.complete"] }
            ],
            data_flows: [
                { from_project: "balanced-requirements", to_project: "system-design", data_type: "requirement_hierarchy", description: "Requirements drive system design", trigger_event: "requirements.balanced" },
                { from_project: "system-design", to_project: "integrated-evaluation", data_type: "system_design", description: "Design flows to evaluation", trigger_event: "design.complete" }
            ],
            domains: ["systems-engineering", "architecture", "analysis"]
        };
    }
    
    getGeneralVariantB() {
        return {
            analysis_summary: "VARIANT B: Alternative comprehensive lattice with different emphasis. Probabilistic variant selection.",
            confidence: 0.74, 
            lattice_type: "general_variant_b",
            projects: [
                { name: "comprehensive-analysis", domain: "systems-engineering", layer: 1, description: "Comprehensive UAV requirements analysis", purpose: "Thorough analysis of all UAV aspects", inputs: ["comprehensive_docs"], outputs: ["complete_analysis"], processing_type: "analysis", publishes: ["analysis.comprehensive"] },
                { name: "solution-development", domain: "architecture", layer: 2, description: "Develop UAV solutions", purpose: "Create multiple solution approaches", inputs: ["complete_analysis"], outputs: ["solution_options"], processing_type: "design", parent_name: "comprehensive-analysis", subscribes_to: ["analysis.comprehensive"], publishes: ["solutions.developed"] },
                { name: "final-selection", domain: "analysis", layer: 3, description: "Final UAV selection", purpose: "Select best overall UAV solution", inputs: ["solution_options"], outputs: ["final_recommendation"], processing_type: "evaluation", parent_name: "solution-development", subscribes_to: ["solutions.developed"], publishes: ["selection.final"] }
            ],
            data_flows: [
                { from_project: "comprehensive-analysis", to_project: "solution-development", data_type: "complete_analysis", description: "Analysis drives solution development", trigger_event: "analysis.comprehensive" },
                { from_project: "solution-development", to_project: "final-selection", data_type: "solution_options", description: "Solutions flow to final selection", trigger_event: "solutions.developed" }
            ],
            domains: ["systems-engineering", "architecture", "analysis"]
        };
    }
    
    mockLLMAnalysis(requirements) {
        // Mock intelligent analysis based on requirements content
        const hasPerformance = requirements.toLowerCase().includes('performance') || 
                              requirements.toLowerCase().includes('speed') ||
                              requirements.toLowerCase().includes('range');
        const hasMission = requirements.toLowerCase().includes('mission') ||
                          requirements.toLowerCase().includes('operational');
        const hasCost = requirements.toLowerCase().includes('cost') ||
                       requirements.toLowerCase().includes('budget');
        
        if (hasPerformance && hasMission) {
            return {
                analysis_summary: "Requirements emphasize operational performance and mission effectiveness. Generated lattice focuses on mission scenario development and performance analysis leading to solution evaluation.",
                confidence: 0.87,
                projects: [
                    {
                        name: "requirements-analysis",
                        domain: "systems-engineering",
                        layer: 1,
                        description: "Analyze UAV requirements and extract key performance parameters",
                        purpose: "Extract operational requirements and performance specifications",
                        inputs: ["requirements_documents", "performance_criteria"],
                        outputs: ["capability_gaps", "performance_requirements", "technical_constraints"],
                        processing_type: "analysis",
                        publishes: ["requirements.analyzed"]
                    },
                    {
                        name: "mission-analysis",
                        domain: "mission-planning", 
                        layer: 2,
                        description: "Develop mission scenarios and operational concepts",
                        purpose: "Define operational use cases and deployment scenarios",
                        inputs: ["capability_gaps", "operational_context"],
                        outputs: ["mission_scenarios", "operational_constraints", "deployment_concepts"],
                        processing_type: "analysis",
                        parent_name: "requirements-analysis",
                        publishes: ["scenarios.defined"]
                    },
                    {
                        name: "performance-analysis",
                        domain: "analysis",
                        layer: 2, 
                        description: "Analyze performance requirements vs UAV capabilities",
                        purpose: "Evaluate UAV performance against mission requirements",
                        inputs: ["performance_requirements", "uav_specifications"],
                        outputs: ["performance_assessment", "capability_matching"],
                        processing_type: "analysis",
                        parent_name: "requirements-analysis",
                        publishes: ["performance.analyzed"]
                    },
                    {
                        name: "solution-selection",
                        domain: "analysis",
                        layer: 3,
                        description: "Select optimal UAV solution",
                        purpose: "Recommend best UAV option based on mission and performance analysis",
                        inputs: ["mission_scenarios", "performance_assessment", "cost_constraints"],
                        outputs: ["recommended_solution", "justification", "implementation_plan"], 
                        processing_type: "evaluation",
                        parent_name: "performance-analysis",
                        publishes: ["solution.selected"]
                    }
                ],
                data_flows: [
                    {
                        from_project: "requirements-analysis",
                        to_project: "mission-analysis",
                        data_type: "capability_gaps",
                        description: "Capability gaps inform mission scenario development",
                        trigger_event: "requirements.analyzed"
                    },
                    {
                        from_project: "requirements-analysis", 
                        to_project: "performance-analysis",
                        data_type: "performance_requirements",
                        description: "Performance specifications guide technical analysis",
                        trigger_event: "requirements.analyzed"
                    },
                    {
                        from_project: "mission-analysis",
                        to_project: "solution-selection", 
                        data_type: "mission_scenarios",
                        description: "Mission scenarios inform solution selection criteria",
                        trigger_event: "scenarios.defined"
                    },
                    {
                        from_project: "performance-analysis",
                        to_project: "solution-selection",
                        data_type: "performance_assessment", 
                        description: "Performance analysis guides solution recommendation",
                        trigger_event: "performance.analyzed"
                    }
                ],
                domains: ["systems-engineering", "mission-planning", "analysis"]
            };
        } else {
            // Different lattice for different requirement types
            return {
                analysis_summary: "General requirements analysis leading to solution development.",
                confidence: 0.75,
                projects: [
                    {
                        name: "requirements-decomposition",
                        domain: "systems-engineering",
                        layer: 1,
                        description: "Decompose and analyze requirements",
                        purpose: "Break down requirements into manageable components",
                        inputs: ["requirements_documents"],
                        outputs: ["requirement_hierarchy", "constraints"],
                        processing_type: "analysis",
                        publishes: ["requirements.decomposed"]
                    },
                    {
                        name: "solution-design",
                        domain: "architecture", 
                        layer: 2,
                        description: "Design solution architecture",
                        purpose: "Develop system architecture to meet requirements",
                        inputs: ["requirement_hierarchy", "design_constraints"],
                        outputs: ["system_design", "architecture_specification"],
                        processing_type: "design",
                        parent_name: "requirements-decomposition",
                        publishes: ["design.complete"]
                    },
                    {
                        name: "evaluation",
                        domain: "analysis",
                        layer: 3,
                        description: "Evaluate proposed solution",
                        purpose: "Assess solution against requirements",
                        inputs: ["system_design", "evaluation_criteria"],
                        outputs: ["evaluation_results", "recommendations"],
                        processing_type: "evaluation", 
                        parent_name: "solution-design",
                        publishes: ["evaluation.complete"]
                    }
                ],
                data_flows: [
                    {
                        from_project: "requirements-decomposition",
                        to_project: "solution-design",
                        data_type: "requirement_hierarchy",
                        description: "Decomposed requirements guide solution design",
                        trigger_event: "requirements.decomposed"
                    },
                    {
                        from_project: "solution-design",
                        to_project: "evaluation", 
                        data_type: "system_design",
                        description: "System design flows to evaluation",
                        trigger_event: "design.complete"
                    }
                ],
                domains: ["systems-engineering", "architecture", "analysis"]
            };
        }
    }
    
    displayAnalysisResults() {
        if (!this.currentLattice) return;
        
        // Show analysis summary
        const summaryDiv = document.getElementById('analysisSummary');
        summaryDiv.style.display = 'block';
        summaryDiv.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>🧠 LLM Analysis:</strong> ${this.currentLattice.analysis_summary}
                </div>
                <div class="confidence-badge">${Math.round(this.currentLattice.confidence * 100)}% confidence</div>
            </div>
        `;
        
        // Show project list
        const projectList = document.getElementById('projectList');
        projectList.innerHTML = '';
        
        this.currentLattice.projects.forEach(project => {
            const projectDiv = document.createElement('div');
            projectDiv.className = 'project-item';
            projectDiv.innerHTML = `
                <div style="font-weight: bold; margin-bottom: 4px;">
                    ${project.name} (L${project.layer})
                </div>
                <div style="font-size: 0.8rem; color: var(--text-light); margin-bottom: 4px;">
                    ${project.purpose}
                </div>
                <div style="font-size: 0.7rem; color: var(--text-light);">
                    Inputs: ${project.inputs.slice(0, 2).join(', ')}${project.inputs.length > 2 ? '...' : ''}
                </div>
                <div style="font-size: 0.7rem; color: var(--text-light);">
                    Outputs: ${project.outputs.slice(0, 2).join(', ')}${project.outputs.length > 2 ? '...' : ''}
                </div>
            `;
            projectList.appendChild(projectDiv);
        });
        
        // Show data flows
        const dataFlows = document.getElementById('dataFlows');
        dataFlows.innerHTML = '';
        
        this.currentLattice.data_flows.forEach(flow => {
            const flowDiv = document.createElement('div');
            flowDiv.className = 'flow-item';
            flowDiv.innerHTML = `
                <div style="font-weight: bold; font-size: 0.9rem;">
                    ${flow.from_project} → ${flow.to_project}
                </div>
                <div style="font-size: 0.8rem; color: var(--primary);">
                    Data: ${flow.data_type}
                </div>
                <div style="font-size: 0.7rem; color: var(--text-light);">
                    ${flow.description}
                </div>
            `;
            dataFlows.appendChild(flowDiv);
        });
        
        // Update counts
        document.getElementById('projectCount').textContent = this.currentLattice.projects.length;
        document.getElementById('flowCount').textContent = this.currentLattice.data_flows.length;
    }
    
    createLatticeVisualization() {
        if (!this.currentLattice) return;
        
        // Clear existing elements
        this.cy.elements().remove();
        
        // Create nodes
        const elements = [];
        this.currentLattice.projects.forEach(project => {
            elements.push({
                data: {
                    id: project.name,
                    label: project.name.replace(/-/g, '\n'),
                    level: project.layer,
                    domain: project.domain,
                    state: 'inactive',
                    project_data: project
                }
            });
        });
        
        // Create edges for data flows
        this.currentLattice.data_flows.forEach(flow => {
            elements.push({
                data: {
                    id: `${flow.from_project}-${flow.to_project}`,
                    source: flow.from_project,
                    target: flow.to_project,
                    label: flow.data_type,
                    flow_data: flow
                }
            });
        });
        
        // Add elements to graph
        this.cy.add(elements);
        
        // Apply intelligent layout
        this.applyIntelligentLayout();
    }
    
    applyIntelligentLayout() {
        const nodes = this.cy.nodes();
        const domains = [...new Set(nodes.map(n => n.data('domain')))].sort();
        
        // Position nodes in grid layout
        nodes.forEach(node => {
            const level = node.data('level');
            const domain = node.data('domain');
            
            const domainIndex = domains.indexOf(domain);
            const x = 150 + (domainIndex * 200);
            const y = 100 + (level * 120);
            
            node.position({ x, y });
        });
        
        // Update domain labels
        this.updateDomainLabels(domains);
        
        // Fit to view
        this.cy.fit(this.cy.nodes(), 50);
    }
    
    updateDomainLabels(domains) {
        const container = document.getElementById('domainLabels');
        container.innerHTML = '';
        
        domains.forEach(domain => {
            const label = document.createElement('div');
            label.className = 'domain-label';
            label.textContent = domain.toUpperCase().replace('-', ' ');
            container.appendChild(label);
        });
    }
    
    showProjectDetails(projectData) {
        const details = projectData.project_data;
        if (!details) return;
        
        const statusDiv = document.getElementById('processingStatus');
        statusDiv.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 8px;">${details.name}</div>
            <div style="margin-bottom: 4px;"><strong>Purpose:</strong> ${details.purpose}</div>
            <div style="margin-bottom: 4px;"><strong>Type:</strong> ${details.processing_type}</div>
            <div style="margin-bottom: 4px;"><strong>Layer:</strong> L${details.layer} (${details.domain})</div>
            <div style="margin-bottom: 8px;"><strong>State:</strong> ${projectData.state}</div>
            <div style="font-size: 0.8rem;">
                <div><strong>Inputs:</strong> ${details.inputs.join(', ')}</div>
                <div><strong>Outputs:</strong> ${details.outputs.join(', ')}</div>
            </div>
        `;
    }
    
    enableControls() {
        document.getElementById('activateProjectsBtn').disabled = false;
        document.getElementById('stepThroughBtn').disabled = false;
    }
    
    async startProcessing() {
        if (!this.currentLattice) return;
        
        this.updateAnalysisStatus('🚀 Starting project processing...');
        
        // Start with L1 projects (requirements analysis)
        const l1Projects = this.currentLattice.projects.filter(p => p.layer === 1);
        
        for (const project of l1Projects) {
            await this.processProject(project.name);
        }
    }
    
    async processProject(projectName) {
        const node = this.cy.getElementById(projectName);
        if (!node.length) {
            console.warn(`⚠️ Node not found: ${projectName}`);
            return;
        }
        
        // Prevent duplicate processing
        if (this.processingQueue.has(projectName)) {
            console.log(`⏸️ ${projectName} already processing, skipping...`);
            return;
        }
        
        // Don't reprocess completed projects
        if (this.completedProjects.has(projectName)) {
            console.log(`✅ ${projectName} already completed, skipping...`);
            return;
        }
        
        const projectData = node.data('project_data');
        const currentState = node.data('state');
        
        // Get input data from upstream projects
        const inputCheck = this.getInputDataForProject(projectName, projectData);
        const inputData = inputCheck.inputs;
        
        // Check if all required inputs are available
        if (!inputCheck.allInputsReady) {
            console.log(`⏳ ${projectName} waiting for inputs: ${inputCheck.missingInputs.join(', ')}`);
            
            // Only update state if not already waiting (avoid visual flicker)
            if (currentState !== 'waiting') {
                node.data('state', 'waiting');
                node.style({
                    'background-color': '#64748b',
                    'border-color': '#f59e0b', // Orange/amber for visibility
                    'border-width': 5, // Thicker border
                    'opacity': 0.85, // More visible
                    'border-style': 'dashed',
                    'border-opacity': 1,
                    'overlay-opacity': 0.2,
                    'overlay-color': '#f59e0b',
                    'overlay-padding': '8px',
                    'z-index': 5
                });
                this.updateProjectState(projectName, 'waiting', `Waiting for: ${inputCheck.missingInputs.join(', ')}`);
            }
            
            // Store as pending for later retry
            this.pendingProjects.set(projectName, {
                projectData: projectData,
                missingInputs: inputCheck.missingInputs,
                retryCount: (this.pendingProjects.get(projectName)?.retryCount || 0) + 1
            });
            
            return; // Don't process yet - wait for all inputs
        }
        
        // Remove from pending if all inputs are now ready
        this.pendingProjects.delete(projectName);
        
        // Add to processing queue
        this.processingQueue.add(projectName);
        
        // Set to processing state
        node.data('state', 'processing');
        this.updateProjectState(projectName, 'processing', 'Analyzing requirements...');
        
        // Highlight and center on processing node
        this.highlightProcessingNode(node);
        
        // Show detailed processing view
        this.showDetailedProcessing(projectData, inputData);
        
        try {
            // Call REAL LLM service to process this project
            const requirements = document.getElementById('requirementsInput').value;
            
            console.log(`🧠 Calling LLM to process project: ${projectName}`);
            
            // Build the request payload with solutions context
            const solutionsContext = this.getSolutionsContext();
            
            // Determine if this is a terminal project (no downstream projects)
            const hasDownstreamProjects = this.currentLattice.projects.some(p => 
                p.parent_name === projectName || 
                this.currentLattice.data_flows.some(flow => 
                    flow.from_project === projectName && flow.to_project === p.name
                )
            );
            const isTerminalProject = !hasDownstreamProjects;
            
            if (isTerminalProject) {
                console.log(`🏁 ${projectName} is a TERMINAL project - will make final selection`);
            } else {
                console.log(`📋 ${projectName} has downstream projects - will NOT make final selection`);
            }
            
            const requestPayload = {
                project: projectData,
                requirements: requirements,
                upstream_data: inputData,
                is_terminal_project: isTerminalProject
            };
            
            // Include solutions if available
            if (solutionsContext && solutionsContext.length > 0) {
                requestPayload.available_solutions = solutionsContext;
            }
            
            const response = await fetch('http://localhost:8083/process-project', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestPayload)
            });
            
            if (!response.ok) {
                throw new Error(`LLM service error: ${response.status} - ${await response.text()}`);
            }
            
            // Get real LLM results (now includes llm_interaction details)
            const responseData = await response.json();
            const results = responseData.result || responseData;
            const llmInteraction = responseData.llm_interaction;
            
            // Store project processing audit trail
            this.llmAuditTrail.push({
                step_type: 'project_processing',
                step_number: this.workflowHistory.length + 1,
                timestamp: new Date().toISOString(),
                project_name: projectName,
                prompt: llmInteraction?.prompt_sent || JSON.stringify(requestPayload, null, 2),
                raw_response: llmInteraction?.raw_response || JSON.stringify(results, null, 2),
                parsed_result: results,
                source: llmInteraction?.source || 'openai_gpt4',
                success: llmInteraction?.success !== false,
                project_data: projectData,
                input_data: inputData
            });
            
            console.log(`✅ LLM processing complete for ${projectName}:`, results);
        
        // Store results in data store
        this.dataStore.set(projectName, results);
            
            // Add to workflow history
            this.addToWorkflowHistory(projectName, projectData, inputData, results);
        
        // Remove from processing queue
        this.processingQueue.delete(projectName);
        
        // Mark as completed
        this.completedProjects.add(projectName);
        
        // Set to complete
        node.data('state', 'complete');
        this.updateProjectState(projectName, 'complete', 'Analysis complete');
        
        // Remove processing highlight
        this.removeProcessingHighlight(node);
        
        // Show detailed results
        this.displayDetailedResults(projectName, results);
        
        // Trigger downstream projects (this will check if they're ready)
        await this.triggerDownstreamProjects(projectName, results);
            
        } catch (error) {
            console.error(`❌ LLM processing failed for ${projectName}:`, error);
            
            // Show error in UI
            this.updateProjectState(projectName, 'error', `LLM processing failed: ${error.message}`);
            
            // Remove from processing queue
            this.processingQueue.delete(projectName);
            
            // Remove processing highlight
            this.removeProcessingHighlight(node);
            
            // Mark as error state
            node.data('state', 'error');
            node.style({
                'background-color': '#ef4444',
                'border-color': '#dc2626',
                'border-width': 4
            });
            
            // Fallback to mock for now (but mark it clearly)
            const mockResults = await this.generateDetailedResults(projectData, inputData);
            mockResults.llm_error = error.message;
            mockResults.source = 'mock_fallback';
            
            this.dataStore.set(projectName, mockResults);
            this.addToWorkflowHistory(projectName, projectData, inputData, mockResults);
            
            // Mark as completed even on error (so we don't retry)
            this.completedProjects.add(projectName);
            node.data('state', 'complete');
            this.displayDetailedResults(projectName, mockResults);
            await this.triggerDownstreamProjects(projectName, mockResults);
        }
    }
    
    getInputDataForProject(projectName, projectData) {
        const inputs = {};
        const missingInputs = [];
        
        // Get data from parent project
        if (projectData.parent_name) {
            if (this.dataStore.has(projectData.parent_name)) {
                const parentResults = this.dataStore.get(projectData.parent_name);
                inputs.parent_data = parentResults;
            } else {
                missingInputs.push(`parent:${projectData.parent_name}`);
            }
        }
        
        // Get data from upstream projects via data flows
        const upstreamFlows = this.currentLattice.data_flows.filter(
            flow => flow.to_project === projectName
        );
        
        upstreamFlows.forEach(flow => {
            if (this.dataStore.has(flow.from_project)) {
                const upstreamResults = this.dataStore.get(flow.from_project);
                inputs[flow.data_type] = upstreamResults;
            } else {
                missingInputs.push(`flow:${flow.data_type} from ${flow.from_project}`);
            }
        });
        
        // Add original requirements if this is a top-level project
        if (projectData.layer === 1) {
            const requirements = document.getElementById('requirementsInput').value;
            if (requirements) {
                inputs.requirements = requirements;
            } else {
                missingInputs.push('requirements');
            }
        }
        
        return { inputs, missingInputs, allInputsReady: missingInputs.length === 0 };
    }
    
    addToWorkflowHistory(projectName, projectData, inputData, results) {
        const workflowStep = {
            step_number: this.workflowHistory.length + 1,
            project_name: projectName,
            project_data: projectData,
            timestamp: new Date().toISOString(),
            inputs: inputData,
            outputs: results,
            processing_type: projectData.processing_type,
            domain: projectData.domain,
            layer: projectData.layer
        };
        
        this.workflowHistory.push(workflowStep);
        this.updateWorkflowHistoryDisplay();
    }
    
    updateWorkflowHistoryDisplay() {
        const historyDiv = document.getElementById('workflowHistory');
        
        // Remove "no history" message
        const noHistory = historyDiv.querySelector('.no-history');
        if (noHistory) noHistory.remove();
        
        historyDiv.innerHTML = '';
        
        // Display workflow steps in reverse order (newest first)
        this.workflowHistory.slice().reverse().forEach((step, index) => {
            const stepDiv = document.createElement('div');
            stepDiv.className = 'workflow-step';
            stepDiv.style.cssText = `
                border: 1px solid var(--border-dark);
                border-radius: 6px;
                padding: 12px;
                margin-bottom: 12px;
                background: var(--dark-3);
                cursor: pointer;
            `;
            
            const isExpanded = index === 0; // Expand most recent by default
            
            stepDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-weight: bold; color: var(--primary);">
                        Step ${step.step_number}: ${step.project_name}
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-light);">
                        L${step.layer} • ${step.domain}
                    </div>
                </div>
                
                <div style="font-size: 0.8rem; margin-bottom: 8px; color: var(--text-light);">
                    ${step.project_data.purpose}
                </div>
                
                <div style="margin-bottom: 8px;">
                    <button class="view-full-btn" onclick="window.intelligentLattice.showFullWorkflowStep(${index})">
                        📋 View Full Details
                    </button>
                </div>
                
                <details ${isExpanded ? 'open' : ''} style="font-size: 0.85rem;">
                    <summary style="cursor: pointer; font-weight: bold; color: var(--warning); margin-bottom: 6px;">
                        🔍 View Details (Inputs → Outputs)
                    </summary>
                    
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border-dark);">
                        <!-- Inputs Section -->
                        <div style="margin-bottom: 12px;">
                            <div style="font-weight: bold; color: var(--primary); margin-bottom: 4px;">
                                📥 Inputs:
                            </div>
                            <div style="font-size: 0.75rem; color: var(--text-light); padding-left: 12px;">
                                ${this.formatInputsForDisplay(step.inputs, step.project_data)}
                            </div>
                        </div>
                        
                        <!-- LLM Reasoning Section -->
                        ${step.outputs.llm_reasoning ? `
                            <div style="margin-bottom: 12px;">
                                <div style="font-weight: bold; color: var(--primary); margin-bottom: 4px;">
                                    🧠 LLM Reasoning Process:
                                </div>
                                <div style="font-size: 0.75rem; color: var(--text-light); padding-left: 12px; background: var(--dark-2); padding: 8px; border-radius: 4px; max-height: 200px; overflow-y: auto;">
                                    ${step.outputs.llm_reasoning.map((reason, idx) => 
                                        `<div style="margin-bottom: 4px; padding: 4px; background: rgba(59, 130, 246, 0.1); border-left: 2px solid var(--primary); padding-left: 8px;">
                                            <span style="color: var(--primary); font-weight: bold;">Step ${idx + 1}:</span> ${reason}
                                        </div>`
                                    ).join('')}
                                </div>
                            </div>
                        ` : ''}
                        
                        <!-- LLM Prompt Context (if available) -->
                        ${step.outputs.llm_prompt ? `
                            <div style="margin-bottom: 12px;">
                                <details>
                                    <summary style="cursor: pointer; font-weight: bold; color: var(--warning); margin-bottom: 4px;">
                                        📝 View LLM Prompt
                                    </summary>
                                    <div style="font-size: 0.7rem; color: var(--text-light); padding: 8px; background: var(--dark-2); border-radius: 4px; margin-top: 4px; max-height: 150px; overflow-y: auto; font-family: monospace; white-space: pre-wrap;">
                                        ${step.outputs.llm_prompt.substring(0, 500)}${step.outputs.llm_prompt.length > 500 ? '...' : ''}
                                    </div>
                                </details>
                            </div>
                        ` : ''}
                        
                        <!-- Outputs Section -->
                        <div style="margin-bottom: 12px;">
                            <div style="font-weight: bold; color: var(--success); margin-bottom: 4px;">
                                📤 Outputs:
                            </div>
                            <div style="font-size: 0.75rem; color: var(--text-light); padding-left: 12px;">
                                ${this.formatOutputsForDisplay(step.outputs)}
                            </div>
                        </div>
                        
                        <!-- Data Flow Info -->
                        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border-dark); font-size: 0.7rem; color: var(--text-light);">
                            <strong>Expected Outputs:</strong> ${step.project_data.outputs.join(', ')}<br>
                            <strong>Publishes Events:</strong> ${step.project_data.publishes ? step.project_data.publishes.join(', ') : 'None'}
                        </div>
                    </div>
                </details>
            `;
            
            historyDiv.appendChild(stepDiv);
        });
    }
    
    formatInputsForDisplay(inputs, projectData) {
        const parts = [];
        
        if (inputs.requirements) {
            parts.push(`<div style="margin-bottom: 6px;"><strong>📄 Requirements Document:</strong><br>`);
            parts.push(`  <span style="font-size: 0.7rem;">${inputs.requirements.length} characters</span><br>`);
            parts.push(`  <details style="margin-top: 4px;"><summary style="cursor: pointer; font-size: 0.7rem;">View content</summary>`);
            parts.push(`  <div style="font-size: 0.65rem; max-height: 100px; overflow-y: auto; background: var(--dark-2); padding: 6px; border-radius: 4px; margin-top: 4px; white-space: pre-wrap; font-family: monospace;">${inputs.requirements.substring(0, 500)}${inputs.requirements.length > 500 ? '...' : ''}</div></details></div>`);
        }
        
        if (inputs.parent_data) {
            parts.push(`<div style="margin-bottom: 6px;"><strong>👆 Parent Project Data:</strong> From ${projectData.parent_name || 'parent project'}<br>`);
            if (inputs.parent_data.extracted_data) {
                parts.push(`  <span style="font-size: 0.7rem;">• Capability gaps: ${inputs.parent_data.extracted_data.capability_gaps?.length || 0}</span><br>`);
                parts.push(`  <span style="font-size: 0.7rem;">• Performance params: ${Object.keys(inputs.parent_data.extracted_data.performance_requirements || {}).length}</span><br>`);
                parts.push(`  <span style="font-size: 0.7rem;">• Technical constraints: ${inputs.parent_data.extracted_data.technical_constraints?.length || 0}</span>`);
            }
            if (inputs.parent_data.developed_scenarios) {
                parts.push(`  <span style="font-size: 0.7rem;">• Scenarios: ${Object.keys(inputs.parent_data.developed_scenarios).length}</span>`);
            }
            parts.push(`</div>`);
        }
        
        Object.keys(inputs).forEach(key => {
            if (key !== 'requirements' && key !== 'parent_data') {
                const data = inputs[key];
                parts.push(`<div style="margin-bottom: 6px;"><strong>📊 ${key}:</strong><br>`);
                if (data && typeof data === 'object') {
                    parts.push(`  <details><summary style="cursor: pointer; font-size: 0.7rem;">View data</summary>`);
                    parts.push(`  <div style="font-size: 0.65rem; max-height: 100px; overflow-y: auto; background: var(--dark-2); padding: 6px; border-radius: 4px; margin-top: 4px; white-space: pre-wrap; font-family: monospace;">${JSON.stringify(data, null, 2).substring(0, 300)}${JSON.stringify(data).length > 300 ? '...' : ''}</div></details></div>`);
                } else {
                    parts.push(`  <span style="font-size: 0.7rem;">${data}</span></div>`);
                }
            }
        });
        
        if (parts.length === 0) {
            parts.push(`<em style="font-size: 0.7rem;">No upstream data (starting project)</em>`);
        }
        
        return parts.join('');
    }
    
    showFullWorkflowStep(stepIndex) {
        // Get the step from workflow history (reverse order, so convert index)
        const reversedIndex = this.workflowHistory.length - 1 - stepIndex;
        const step = this.workflowHistory[reversedIndex];
        
        if (!step) return;
        
        const modal = document.getElementById('workflowModal');
        const modalTitle = document.getElementById('modalTitle');
        const modalContent = document.getElementById('modalContent');
        
        modalTitle.textContent = `Step ${step.step_number}: ${step.project_name}`;
        
        let html = `
            <div class="modal-section">
                <h3>📋 Project Information</h3>
                <div class="modal-section-content">
                    <strong>Name:</strong> ${step.project_name}<br>
                    <strong>Domain:</strong> ${step.domain}<br>
                    <strong>Layer:</strong> L${step.layer}<br>
                    <strong>Processing Type:</strong> ${step.processing_type}<br>
                    <strong>Purpose:</strong> ${step.project_data.purpose}<br>
                    <strong>Description:</strong> ${step.project_data.description}<br>
                    <strong>Timestamp:</strong> ${new Date(step.timestamp).toLocaleString()}
                </div>
            </div>
            
            <div class="modal-section">
                <h3>📥 Inputs</h3>
                <div class="modal-section-content">
                    <div class="modal-json">${JSON.stringify(step.inputs, null, 2)}</div>
                </div>
            </div>
            
            <div class="modal-section">
                <h3>📤 Outputs</h3>
                <div class="modal-section-content">
                    <div class="modal-json">${JSON.stringify(step.outputs, null, 2)}</div>
                </div>
            </div>
        `;
        
        // Add LLM reasoning if available
        if (step.outputs.llm_reasoning && step.outputs.llm_reasoning.length > 0) {
            html += `
                <div class="modal-section">
                    <h3>🧠 LLM Reasoning Process</h3>
                    <div class="modal-section-content">
                        ${step.outputs.llm_reasoning.map((reason, idx) => 
                            `<div style="margin-bottom: 8px; padding: 8px; background: rgba(59, 130, 246, 0.1); border-left: 3px solid var(--primary);">
                                <strong style="color: var(--primary);">Step ${idx + 1}:</strong> ${reason}
                            </div>`
                        ).join('')}
                    </div>
                </div>
            `;
        }
        
        // Add project data details
        html += `
            <div class="modal-section">
                <h3>⚙️ Project Configuration</h3>
                <div class="modal-section-content">
                    <div class="modal-json">${JSON.stringify(step.project_data, null, 2)}</div>
                </div>
            </div>
        `;
        
        modalContent.innerHTML = html;
        modal.classList.add('active');
    }
    
    showAuditTrailModal() {
        const modal = document.getElementById('auditTrailModal');
        const modalContent = document.getElementById('auditTrailModalContent');
        
        if (this.llmAuditTrail.length === 0) {
            modalContent.innerHTML = '<div class="no-history" style="text-align: center; padding: 40px; color: var(--text-light);">No LLM interactions yet...</div>';
            modal.classList.add('active');
            return;
        }
        
        let html = '';
        
        // Display audit entries in chronological order
        this.llmAuditTrail.forEach((entry, index) => {
            const timestamp = new Date(entry.timestamp).toLocaleString();
            const badgeClass = entry.success ? 'success' : 'error';
            const badgeText = entry.success ? '✓ Success' : '✗ Error';
            
            html += `
                <div class="audit-entry-modal">
                    <div class="audit-entry-header-modal">
                        <div>
                            <span class="audit-entry-title-modal">
                                ${entry.step_type === 'lattice_generation' ? '🏗️ Lattice Generation' : `📊 Step ${entry.step_number}: ${entry.project_name}`}
                            </span>
                            <span class="audit-badge ${badgeClass}">${badgeText}</span>
                        </div>
                        <div class="audit-entry-meta-modal">
                            ${timestamp} • ${entry.source || 'unknown'}
                        </div>
                    </div>
            `;
            
            // Prompt Section
            html += `
                <div class="audit-section-modal">
                    <div class="audit-section-title-modal">📝 Prompt Sent to LLM</div>
                    <div class="audit-code-block">${this.escapeHtml(entry.prompt)}</div>
                </div>
            `;
            
            // Raw Response Section
            html += `
                <div class="audit-section-modal">
                    <div class="audit-section-title-modal">📥 Raw LLM Response</div>
                    <div class="audit-code-block">${this.escapeHtml(entry.raw_response)}</div>
                </div>
            `;
            
            // Parsed Result Section
            html += `
                <div class="audit-section-modal">
                    <div class="audit-section-title-modal">✅ Parsed Result</div>
                    <div class="audit-code-block">${this.escapeHtml(JSON.stringify(entry.parsed_result, null, 2))}</div>
                </div>
            `;
            
            // Additional context for project processing
            if (entry.step_type === 'project_processing' && entry.project_data) {
                html += `
                    <div class="audit-section-modal">
                        <div class="audit-section-title-modal">⚙️ Project Context</div>
                        <div class="audit-code-block">${this.escapeHtml(JSON.stringify({
                            project_name: entry.project_data.name,
                            domain: entry.project_data.domain,
                            layer: entry.project_data.layer,
                            processing_type: entry.project_data.processing_type,
                            purpose: entry.project_data.purpose,
                            inputs: entry.project_data.inputs,
                            outputs: entry.project_data.outputs
                        }, null, 2))}</div>
                    </div>
                `;
            }
            
            html += `</div>`;
        });
        
        modalContent.innerHTML = html;
        modal.classList.add('active');
    }
    
    highlightProcessingNode(node) {
        // Add pulsing animation class
        node.addClass('processing-active');
        
        // Center and zoom to the processing node
        this.cy.animate({
            center: { eles: node },
            zoom: Math.min(this.cy.zoom() * 1.4, 2.0), // Zoom in but cap at 2x
            duration: 500
        });
        
        // Create pulsing animation effect
        const pulseAnimation = () => {
            if (node.data('state') === 'processing') {
                node.animate({
                    style: {
                        'overlay-opacity': 0.5,
                        'overlay-padding': '15px'
                    }
                }, {
                    duration: 800,
                    easing: 'ease-in-out',
                    complete: () => {
                        if (node.data('state') === 'processing') {
                            node.animate({
                                style: {
                                    'overlay-opacity': 0.2,
                                    'overlay-padding': '10px'
                                }
                            }, {
                                duration: 800,
                                easing: 'ease-in-out',
                                complete: () => {
                                    if (node.data('state') === 'processing') {
                                        pulseAnimation();
                                    }
                                }
                            });
                        }
                    }
                });
            }
        };
        
        // Start pulsing
        pulseAnimation();
        
        // Store animation reference for cleanup
        node.data('pulse-animation', pulseAnimation);
    }
    
    removeProcessingHighlight(node) {
        // Remove processing class
        node.removeClass('processing-active');
        
        // Stop pulsing animation
        node.data('pulse-animation', null);
        
        // Remove overlay with smooth transition
        node.animate({
            style: {
                'overlay-opacity': 0,
                'overlay-padding': '0px'
            }
        }, {
            duration: 300,
            easing: 'ease-out'
        });
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    formatOutputsForDisplay(outputs) {
        const parts = [];
        
        if (outputs.extracted_data) {
            parts.push(`<div style="margin-bottom: 8px;"><strong>📊 Extracted Data:</strong><br>`);
            if (outputs.extracted_data.capability_gaps) {
                parts.push(`  <div style="margin-top: 4px;"><strong style="font-size: 0.7rem;">Capability Gaps (${outputs.extracted_data.capability_gaps.length}):</strong>`);
                parts.push(`  <ul style="margin: 4px 0; padding-left: 16px; font-size: 0.7rem;">`);
                outputs.extracted_data.capability_gaps.forEach(gap => {
                    parts.push(`    <li>${gap}</li>`);
                });
                parts.push(`  </ul></div>`);
            }
            if (outputs.extracted_data.performance_requirements) {
                parts.push(`  <div style="margin-top: 4px;"><strong style="font-size: 0.7rem;">Performance Requirements:</strong>`);
                parts.push(`  <ul style="margin: 4px 0; padding-left: 16px; font-size: 0.7rem;">`);
                Object.entries(outputs.extracted_data.performance_requirements).forEach(([key, value]) => {
                    parts.push(`    <li><strong>${key}:</strong> ${value}</li>`);
                });
                parts.push(`  </ul></div>`);
            }
            if (outputs.extracted_data.technical_constraints) {
                parts.push(`  <div style="margin-top: 4px;"><strong style="font-size: 0.7rem;">Technical Constraints (${outputs.extracted_data.technical_constraints.length}):</strong>`);
                parts.push(`  <ul style="margin: 4px 0; padding-left: 16px; font-size: 0.7rem;">`);
                outputs.extracted_data.technical_constraints.forEach(constraint => {
                    parts.push(`    <li>${constraint}</li>`);
                });
                parts.push(`  </ul></div>`);
            }
            parts.push(`</div>`);
        }
        
        if (outputs.developed_scenarios) {
            parts.push(`<div style="margin-bottom: 8px;"><strong>🎯 Developed Scenarios (${Object.keys(outputs.developed_scenarios).length}):</strong>`);
            Object.entries(outputs.developed_scenarios).forEach(([name, scenario]) => {
                parts.push(`  <div style="margin-top: 4px; padding: 6px; background: var(--dark-2); border-radius: 4px; font-size: 0.7rem;">`);
                parts.push(`    <strong>${name}:</strong> ${scenario.description}<br>`);
                if (scenario.duration) parts.push(`    Duration: ${scenario.duration}<br>`);
                if (scenario.coverage) parts.push(`    Coverage: ${scenario.coverage}<br>`);
                if (scenario.critical_factors) {
                    parts.push(`    Critical Factors: ${scenario.critical_factors.join(', ')}`);
                }
                parts.push(`  </div>`);
            });
            parts.push(`</div>`);
        }
        
        if (outputs.performance_evaluation) {
            parts.push(`<div style="margin-bottom: 8px;"><strong>📈 Performance Evaluation:</strong>`);
            outputs.performance_evaluation.evaluated_uavs?.forEach(uav => {
                parts.push(`  <div style="margin-top: 4px; padding: 6px; background: var(--dark-2); border-radius: 4px; font-size: 0.7rem;">`);
                parts.push(`    <strong>${uav.name}:</strong> ${Math.round(uav.performance_score * 100)}%<br>`);
                if (uav.strengths) {
                    parts.push(`    <span style="color: var(--success);">Strengths:</span> ${uav.strengths.join('; ')}<br>`);
                }
                if (uav.weaknesses) {
                    parts.push(`    <span style="color: var(--warning);">Weaknesses:</span> ${uav.weaknesses.join('; ')}`);
                }
                parts.push(`  </div>`);
            });
            parts.push(`</div>`);
        }
        
        if (outputs.final_recommendation) {
            parts.push(`<div style="margin-bottom: 8px; padding: 8px; background: rgba(16, 185, 129, 0.1); border: 1px solid var(--success); border-radius: 4px;">`);
            parts.push(`  <strong style="color: var(--success);">🎯 Final Recommendation:</strong><br>`);
            parts.push(`  <div style="font-size: 0.9rem; font-weight: bold; color: var(--success); margin: 4px 0;">${outputs.final_recommendation.selected_uav}</div>`);
            parts.push(`  <div style="font-size: 0.75rem; margin-top: 4px;">${outputs.final_recommendation.justification}</div>`);
            if (outputs.final_recommendation.risk_factors) {
                parts.push(`  <div style="margin-top: 6px; font-size: 0.7rem;"><strong>Risk Factors:</strong>`);
                parts.push(`  <ul style="margin: 4px 0; padding-left: 16px;">`);
                outputs.final_recommendation.risk_factors.forEach(risk => {
                    parts.push(`    <li>${risk}</li>`);
                });
                parts.push(`  </ul></div>`);
            }
            parts.push(`</div>`);
        }
        
        if (parts.length === 0) {
            parts.push(`<em style="font-size: 0.7rem;">Processing complete</em>`);
        }
        
        return parts.join('');
    }
    
    showDetailedProcessing(projectData, inputData) {
        const statusDiv = document.getElementById('processingStatus');
        statusDiv.innerHTML = `
            <div style="font-weight: bold; color: var(--warning); margin-bottom: 4px;">
                🔍 ${projectData.name}
            </div>
            <div style="font-size: 0.75rem; color: var(--text-light);">
                ${projectData.processing_type} • ${projectData.domain}
            </div>
        `;
        
        const dataDiv = document.getElementById('currentData');
        let inputDetails = '';
        
        if (inputData.requirements) {
            inputDetails += `<div style="margin-bottom: 4px;"><strong>Requirements:</strong> ${inputData.requirements.length} chars</div>`;
        }
        
        if (inputData.parent_data) {
            inputDetails += `<div style="margin-bottom: 4px;"><strong>Parent:</strong> ${projectData.parent_name || 'parent'}</div>`;
            if (inputData.parent_data.extracted_data) {
                inputDetails += `<div style="font-size: 0.7rem;">• ${inputData.parent_data.extracted_data.capability_gaps?.length || 0} gaps</div>`;
            }
        }
        
        Object.keys(inputData).forEach(key => {
            if (key !== 'requirements' && key !== 'parent_data') {
                inputDetails += `<div style="margin-bottom: 4px;"><strong>${key}:</strong> Received</div>`;
            }
        });
        
        if (!inputDetails) {
            inputDetails = '<div style="font-size: 0.75rem; font-style: italic;">Starting project</div>';
        }
        
        dataDiv.innerHTML = inputDetails;
    }
    
    async generateDetailedResults(project, inputData) {
        const requirements = document.getElementById('requirementsInput').value;
        
        // Generate detailed LLM-style analysis
        if (project.processing_type === 'analysis' && project.name === 'requirements-analysis') {
            return {
                project_name: project.name,
                analysis_type: 'requirements_decomposition',
                llm_reasoning: [
                    "📋 Analyzing UAV requirements document...",
                    "🎯 Identified key mission: Disaster response with rapid deployment",
                    "📏 Extracted performance parameters: 50km range, 3+ hour endurance, 2kg payload",
                    "🌤️ Environmental constraints: 25 knot winds, operational altitudes 100-3000m",
                    "💰 Cost constraints: $2M acquisition, $500/hour operational",
                    "⚡ Critical requirement: 15-minute deployment time"
                ],
                extracted_data: {
                    capability_gaps: [
                        "Rapid deployment capability (≤15 min setup)",
                        "Extended endurance operations (≥3 hours)", 
                        "All-weather operation capability",
                        "Multi-sensor payload integration"
                    ],
                    performance_requirements: {
                        range: "≥50 km operational radius",
                        endurance: "≥3 hours flight time",
                        payload: "≥2 kg capacity",
                        altitude: "100-3000 meters AGL",
                        wind_tolerance: "≥25 knots"
                    },
                    technical_constraints: [
                        "IR camera with heat detection required",
                        "Real-time data transmission capability",
                        "Field-ruggedized design required"
                    ]
                },
                confidence: 0.91,
                processing_time: 3.2,
                ready_for_downstream: true,
                next_actions: [
                    "Send capability_gaps to mission-analysis project",
                    "Send performance_requirements to performance-analysis project"
                ]
            };
        } else if (project.processing_type === 'analysis' && project.name === 'mission-analysis') {
            const reqData = this.dataStore.get('requirements-analysis');
            const capabilityGaps = reqData?.extracted_data?.capability_gaps || [];
            
            return {
                project_name: project.name,
                analysis_type: 'mission_scenario_development',
                llm_reasoning: [
                    "🎯 Receiving capability gaps from requirements analysis...",
                    "📍 Primary mission: Disaster response in challenging environments",
                    "🚁 Analyzing deployment scenarios for emergency response",
                    "⏱️ Critical factor: 15-minute rapid deployment requirement",
                    "🌍 Operating environment: Variable terrain, potentially hazardous conditions",
                    "👥 User profile: Emergency response teams with minimal UAV training"
                ],
                developed_scenarios: {
                    scenario_1: {
                        name: "Rapid Assessment Mission",
                        description: "Quick area survey immediately after disaster",
                        duration: "2-3 hours",
                        coverage: "5-10 sq km systematic grid",
                        critical_factors: ["15-min deployment", "IR capability", "weather tolerance"]
                    },
                    scenario_2: {
                        name: "Extended Monitoring Mission", 
                        description: "Continuous area monitoring over extended period",
                        duration: "6+ hours",
                        coverage: "Targeted areas with repeat visits",
                        critical_factors: ["Endurance", "Payload flexibility", "Real-time feed"]
                    },
                    scenario_3: {
                        name: "Search and Rescue Support",
                        description: "Support SAR operations with thermal detection",
                        duration: "4+ hours",
                        coverage: "Focused search areas",
                        critical_factors: ["Thermal imaging", "Low altitude operation", "Weather tolerance"]
                    }
                },
                operational_constraints: [
                    "Must operate in 25+ knot winds",
                    "Required 2+ kg payload for sensor packages",
                    "15-minute maximum setup time",
                    "2-person operation team maximum"
                ],
                confidence: 0.88,
                ready_for_downstream: true,
                next_actions: [
                    "Send mission_scenarios to solution-selection project"
                ]
            };
        } else if (project.processing_type === 'analysis' && project.name === 'performance-analysis') {
            const reqData = this.dataStore.get('requirements-analysis');
            const perfRequirements = reqData?.extracted_data?.performance_requirements || {};
            
            return {
                project_name: project.name,
                analysis_type: 'performance_evaluation',
                llm_reasoning: [
                    "⚡ Receiving performance requirements from requirements analysis...",
                    "📊 Evaluating UAV options against performance criteria",
                    "🔍 Analyzing available UAV specifications against requirements",
                    "⚖️ Performing trade-off analysis: performance vs cost vs mission fit",
                    "🎯 Identifying UAV candidates that meet minimum requirements",
                    "📈 Ranking solutions by performance match score"
                ],
                performance_evaluation: {
                    evaluated_uavs: [
                        {
                            name: "SkyEagle X500",
                            performance_score: 0.94,
                            strengths: ["8-10hr endurance exceeds requirement", "150km range exceeds requirement", "3.5kg payload exceeds requirement"],
                            weaknesses: ["Higher cost at $1.2M", "Complex setup may challenge 15-min requirement"]
                        },
                        {
                            name: "AeroMapper X8", 
                            performance_score: 0.89,
                            strengths: ["12-14hr endurance well above requirement", "High weather tolerance", "5kg payload capacity"],
                            weaknesses: ["$1.7M cost approaching limit", "Complex pneumatic launcher"]
                        },
                        {
                            name: "Falcon VTOL-X",
                            performance_score: 0.82, 
                            strengths: ["VTOL capability simplifies deployment", "Good endurance at 5-6 hours", "Moderate cost at $850K"],
                            weaknesses: ["Lower payload at 2.5kg", "Complex transition mechanics"]
                        }
                    ],
                    performance_gap_analysis: [
                        "All candidates meet minimum endurance requirement (≥3 hours)",
                        "SkyEagle X500 and AeroMapper X8 significantly exceed range requirements",
                        "Deployment time may be challenging for complex launcher systems",
                        "Weather tolerance varies - AeroMapper X8 has best all-weather capability"
                    ]
                },
                confidence: 0.86,
                ready_for_downstream: true,
                next_actions: [
                    "Send performance_assessment to solution-selection project"
                ]
            };
        } else if (project.processing_type === 'evaluation' && project.name === 'solution-selection') {
            const missionData = this.dataStore.get('mission-analysis');
            const perfData = this.dataStore.get('performance-analysis');
            
            return {
                project_name: project.name,
                analysis_type: 'solution_recommendation',
                llm_reasoning: [
                    "🔍 Integrating mission scenarios and performance analysis...",
                    "⚖️ Weighing mission requirements against UAV capabilities",
                    "💡 Scenario 1 (Rapid Assessment) favors quick-deploy UAVs",
                    "💡 Scenario 2 (Extended Monitoring) favors high-endurance UAVs", 
                    "💡 Scenario 3 (SAR Support) requires thermal and weather capability",
                    "🎯 Finding optimal solution that covers all scenarios effectively",
                    "💰 Considering cost-effectiveness and lifecycle costs"
                ],
                evaluation_matrix: {
                    criteria: {
                        mission_fit: 0.35,
                        performance: 0.25,
                        cost_effectiveness: 0.20,
                        deployment_ease: 0.20
                    },
                    final_scores: [
                        { name: "SkyEagle X500", total_score: 0.89, recommendation_rank: 1 },
                        { name: "AeroMapper X8", total_score: 0.84, recommendation_rank: 2 },
                        { name: "Falcon VTOL-X", total_score: 0.76, recommendation_rank: 3 }
                    ]
                },
                final_recommendation: {
                    selected_uav: "SkyEagle X500",
                    justification: "Best balance of performance, mission capability, and operational requirements. 8-10 hour endurance provides significant operational margin. 150km range exceeds requirements by 3x. Payload capacity supports multiple sensor configurations for disaster response scenarios.",
                    risk_factors: [
                        "Setup time may challenge 15-minute requirement - recommend training focus",
                        "Higher acquisition cost requires budget justification"
                    ],
                    implementation_notes: [
                        "Prioritize rapid deployment training for operators",
                        "Consider pre-positioned equipment to reduce setup time",
                        "Recommend procurement of 2 units for redundancy"
                    ]
                },
                confidence: 0.91,
                ready_for_downstream: true
            };
        }
        
        // Default for other project types
        return {
            project_name: project.name,
            results: [`Completed ${project.processing_type} for ${project.description}`],
            confidence: 0.75,
            ready_for_downstream: true
        };
    }
    
    async triggerDownstreamProjects(completedProject, results) {
        // Find projects that should receive this data
        const downstreamProjects = this.currentLattice.projects.filter(p => 
            (p.parent_name === completedProject || 
            this.currentLattice.data_flows.some(flow => 
                flow.from_project === completedProject && flow.to_project === p.name
            )) &&
            !this.completedProjects.has(p.name) && // Not already completed
            !this.processingQueue.has(p.name)     // Not currently processing
        );
        
        console.log(`📊 ${completedProject} completed. Checking ${downstreamProjects.length} downstream projects...`);
        
        // Animate data flow and check if downstream projects are ready
        for (const downstreamProject of downstreamProjects) {
            this.animateDataFlow(completedProject, downstreamProject.name, results);
            
            // Check if this downstream project now has all inputs ready
            const downstreamNode = this.cy.getElementById(downstreamProject.name);
            if (!downstreamNode.length) continue;
            
            const downstreamProjectData = downstreamNode.data('project_data');
            const inputCheck = this.getInputDataForProject(downstreamProject.name, downstreamProjectData);
            
            // Only process if all inputs are now ready AND not already processing/completed
            if (inputCheck.allInputsReady && 
                !this.processingQueue.has(downstreamProject.name) &&
                !this.completedProjects.has(downstreamProject.name)) {
                
                // Update waiting state if it was waiting
                if (downstreamNode.data('state') === 'waiting') {
                    downstreamNode.data('state', 'ready');
                    const level = downstreamProjectData.level;
                    let baseColor = '#64748b';
                    if (level === 0) baseColor = '#3b82f6';
                    else if (level === 1) baseColor = '#10b981';
                    else if (level === 2) baseColor = '#f59e0b';
                    else if (level === 3) baseColor = '#ef4444';
                    
                    downstreamNode.style({
                        'opacity': 1,
                        'background-color': baseColor,
                        'border-color': '#334155',
                        'border-width': 2
                    });
                }
                
                // Start downstream processing after short delay
                console.log(`✅ ${downstreamProject.name} has all inputs ready, starting processing...`);
                setTimeout(async () => {
                    await this.processProject(downstreamProject.name);
                }, 1000);
            } else {
                const reason = this.processingQueue.has(downstreamProject.name) ? 'already processing' :
                              this.completedProjects.has(downstreamProject.name) ? 'already completed' :
                              `waiting for: ${inputCheck.missingInputs.join(', ')}`;
                console.log(`⏳ ${downstreamProject.name} ${reason}`);
            }
        }
        
        // Check pending projects to see if any are now ready
        await this.checkPendingProjects();
    }
    
    async checkPendingProjects() {
        // Check all pending projects to see if inputs are now available
        for (const [projectName, pendingInfo] of this.pendingProjects.entries()) {
            const node = this.cy.getElementById(projectName);
            if (!node.length) continue;
            
            // Skip if already processing or completed
            if (this.processingQueue.has(projectName) || this.completedProjects.has(projectName)) {
                this.pendingProjects.delete(projectName);
                continue;
            }
            
            const inputCheck = this.getInputDataForProject(projectName, pendingInfo.projectData);
            
            if (inputCheck.allInputsReady) {
                console.log(`✅ ${projectName} inputs now ready, starting processing...`);
                this.pendingProjects.delete(projectName);
                await this.processProject(projectName);
            }
        }
    }
    
    animateDataFlow(fromProject, toProject, data) {
        const fromNode = this.cy.getElementById(fromProject);
        const toNode = this.cy.getElementById(toProject);
        
        if (fromNode.length && toNode.length) {
            // Find the edge
            const edge = this.cy.edges(`[source="${fromProject}"][target="${toProject}"]`);
            if (edge.length) {
                edge.addClass('data-flowing');
                
                setTimeout(() => {
                    edge.removeClass('data-flowing');
                }, 2000);
            }
            
            console.log(`📊 Data flowing: ${fromProject} → ${toProject}`);
        }
    }
    
    updateProjectState(projectName, state, description) {
        this.processingStates.set(projectName, { state, description, timestamp: Date.now() });
        
        // Update is now handled by showDetailedProcessing
        // This function kept for compatibility but simplified
    }
    
    displayDetailedResults(projectName, results) {
        const resultsDiv = document.getElementById('results');
        
        // Remove "no results" message
        const noResults = resultsDiv.querySelector('.no-results');
        if (noResults) noResults.remove();
        
        let content = `<div style="font-weight: bold; color: var(--success); margin-bottom: 4px;">✅ ${projectName}</div>`;
        
        // Show summary based on result type
        if (results.extracted_data) {
            content += `<div style="font-size: 0.75rem; color: var(--text-light);">${results.extracted_data.capability_gaps?.length || 0} gaps, ${Object.keys(results.extracted_data.performance_requirements || {}).length} params</div>`;
        } else if (results.developed_scenarios) {
            content += `<div style="font-size: 0.75rem; color: var(--text-light);">${Object.keys(results.developed_scenarios).length} scenarios</div>`;
        } else if (results.performance_evaluation) {
            const topUav = results.performance_evaluation.evaluated_uavs?.[0];
            content += `<div style="font-size: 0.75rem; color: var(--text-light);">${topUav?.name || 'Evaluated'}: ${Math.round((topUav?.performance_score || 0) * 100)}%</div>`;
        } else {
            content += `<div style="font-size: 0.75rem; color: var(--text-light);">Complete</div>`;
        }
        
        resultsDiv.innerHTML = content;
        
        // Check if this result contains a final recommendation/selection
        this.checkForFinalRecommendation(projectName, results);
    }
    
    checkForFinalRecommendation(projectName, results) {
        // Only check for recommendation from terminal projects (those with no downstream projects)
        // This ensures the recommendation uses ALL workflow analysis data
        
        if (!this.currentLattice) return;
        
        // Check if this project has any downstream projects
        const hasDownstreamProjects = this.currentLattice.projects.some(p => 
            p.parent_name === projectName || 
            this.currentLattice.data_flows.some(flow => 
                flow.from_project === projectName && flow.to_project === p.name
            )
        );
        
        // Only process recommendation from terminal projects (no downstream)
        if (hasDownstreamProjects) {
            console.log(`📋 ${projectName} has downstream projects - waiting for full workflow completion before recommendation`);
            return;
        }
        
        console.log(`🏁 ${projectName} is a terminal project - checking for final recommendation`);
        
        // Look for any recommendation-like output from the LLM
        const recommendation = results.final_recommendation || 
                               results.selected_solution ||
                               results.recommendation ||
                               results.solution_selection;
        
        if (recommendation) {
            // Extract confidence from recommendation or results
            const selectionConfidence = recommendation.selection_confidence || 
                                        recommendation.confidence || 
                                        results.confidence || 
                                        0.8;
            
            this.finalRecommendation = {
                projectName: projectName,
                recommendation: recommendation,
                confidence: selectionConfidence,
                timestamp: new Date().toISOString(),
                solutionEvaluation: results.solution_evaluation || null,
                workflowComplete: true
            };
            
            console.log(`🎯 Workflow complete - displaying final recommendation from ${projectName}`);
            this.displayFinalRecommendation();
        } else {
            console.log(`⚠️ Terminal project ${projectName} completed but no explicit recommendation found in output`);
        }
    }
    
    displayFinalRecommendation() {
        if (!this.finalRecommendation) return;
        
        const rec = this.finalRecommendation.recommendation;
        const selectedName = rec.selected_solution || rec.selected_uav || rec.name || rec.selection || 'No Selection Made';
        const rationale = rec.rationale || rec.justification || rec.reasoning || rec.explanation || '';
        const confidence = Math.round((this.finalRecommendation.confidence || 0.8) * 100);
        const keyFactors = rec.key_deciding_factors || [];
        const comparisonToAlternatives = rec.comparison_to_alternatives || '';
        
        // Create or update the recommendation panel
        let panel = document.getElementById('finalRecommendationPanel');
        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'finalRecommendationPanel';
            panel.className = 'final-recommendation-panel';
            
            // Insert into the content-wrapper after the solutions panel
            const solutionsPanel = document.getElementById('solutionsPanel');
            if (solutionsPanel && solutionsPanel.parentNode) {
                solutionsPanel.parentNode.insertBefore(panel, solutionsPanel.nextSibling);
            } else {
                // Fallback - insert into the content wrapper
                const contentWrapper = document.querySelector('.content-wrapper');
                if (contentWrapper) {
                    const bottomSection = contentWrapper.querySelector('.bottom-section');
                    if (bottomSection) {
                        contentWrapper.insertBefore(panel, bottomSection);
                    } else {
                        contentWrapper.appendChild(panel);
                    }
                } else {
                    // Last resort
                    document.body.appendChild(panel);
                }
            }
        }
        
        // Ensure panel is visible
        panel.style.display = 'block';
        
        // Build the solution evaluation section if available
        let evaluationHtml = '';
        if (this.finalRecommendation.solutionEvaluation && this.finalRecommendation.solutionEvaluation.evaluated_solutions) {
            const evalSolutions = this.finalRecommendation.solutionEvaluation.evaluated_solutions;
            evaluationHtml = `
                <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border-dark);">
                    <h4 style="color: var(--primary); margin-bottom: 12px;">📊 Solution Comparison</h4>
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px;">
                        ${evalSolutions.map(sol => `
                            <div style="background: ${sol.name === selectedName ? 'rgba(16, 185, 129, 0.2)' : 'var(--dark-3)'}; 
                                        padding: 12px; border-radius: 8px; 
                                        border: 2px solid ${sol.name === selectedName ? 'var(--success)' : 'var(--border-dark)'};">
                                <div style="font-weight: bold; color: ${sol.name === selectedName ? 'var(--success)' : 'var(--light)'}; margin-bottom: 4px;">
                                    ${sol.name === selectedName ? '✅ ' : ''}${sol.name}
                                </div>
                                <div style="font-size: 0.85rem; color: var(--text-light);">
                                    Score: ${Math.round((sol.score || 0) * 100)}%
                                </div>
                                ${sol.meets_requirements !== undefined ? `
                                    <div style="font-size: 0.8rem; color: ${sol.meets_requirements ? 'var(--success)' : 'var(--danger)'};">
                                        ${sol.meets_requirements ? '✓ Meets requirements' : '✗ Does not meet requirements'}
                                    </div>
                                ` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        panel.innerHTML = `
            <div class="final-recommendation-header" onclick="toggleRecommendationPanel()">
                <div class="final-recommendation-header-left">
                    <div class="final-recommendation-title">🎯 LLM Solution Selection</div>
                    <div class="final-recommendation-confidence">${confidence}% confidence</div>
                    <span style="color: var(--light); font-size: 0.9rem;">→ ${selectedName}</span>
                </div>
                <span class="final-recommendation-collapse-icon">▼</span>
            </div>
            <div class="final-recommendation-content">
                <div class="selected-solution-name">${selectedName}</div>
                
                <div class="recommendation-rationale">
                    <h4>📝 Rationale</h4>
                    <p style="margin: 0; line-height: 1.6;">${rationale || 'The LLM selected this solution based on the analysis of requirements and available options.'}</p>
                </div>
                
                ${keyFactors.length > 0 ? `
                    <div style="margin-top: 16px;">
                        <h4 style="color: var(--success); margin-bottom: 8px;">✓ Key Deciding Factors</h4>
                        <ul style="margin: 0; padding-left: 20px; font-size: 0.9rem;">
                            ${keyFactors.map(f => `<li>${f}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                
                ${comparisonToAlternatives ? `
                    <div style="margin-top: 16px;">
                        <h4 style="color: var(--warning); margin-bottom: 8px;">🔄 Comparison to Alternatives</h4>
                        <p style="margin: 0; font-size: 0.9rem; color: var(--text-light);">${comparisonToAlternatives}</p>
                    </div>
                ` : ''}
                
                ${rec.risk_factors && rec.risk_factors.length > 0 ? `
                    <div style="margin-top: 16px;">
                        <h4 style="color: var(--danger); margin-bottom: 8px;">⚠️ Risk Factors</h4>
                        <ul style="margin: 0; padding-left: 20px; font-size: 0.9rem;">
                            ${rec.risk_factors.map(r => `<li>${r}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                
                ${rec.implementation_notes && rec.implementation_notes.length > 0 ? `
                    <div style="margin-top: 16px;">
                        <h4 style="color: var(--primary); margin-bottom: 8px;">📋 Implementation Notes</h4>
                        <ul style="margin: 0; padding-left: 20px; font-size: 0.9rem;">
                            ${rec.implementation_notes.map(n => `<li>${n}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                
                ${evaluationHtml}
            </div>
        `;
        
        console.log('🎯 Final recommendation displayed:', selectedName, `(${confidence}% confidence)`);
    }
    
    async stepThroughProcessing() {
        // Manual step-through for demonstration
        if (!this.currentLattice) return;
        
        const inactiveNodes = this.cy.nodes('[state="inactive"]');
        if (inactiveNodes.length > 0) {
            const nextProject = inactiveNodes[0].data('project_data').name;
            await this.processProject(nextProject);
        }
    }
    
    resetDemo() {
        this.currentLattice = null;
        this.processingStates.clear();
        this.dataStore.clear();
        this.workflowHistory = [];
        this.llmAuditTrail = [];
        this.processingQueue.clear();
        this.completedProjects.clear();
        this.pendingProjects.clear();
        this.projectRegistry = {};
        this.createdProjects = [];
        this.finalRecommendation = null;
        
        // Remove final recommendation panel if exists
        const recPanel = document.getElementById('finalRecommendationPanel');
        if (recPanel) recPanel.remove();
        
        this.cy.elements().remove();
        document.getElementById('requirementsInput').value = '';
        document.getElementById('analysisSummary').style.display = 'none';
        document.getElementById('projectList').innerHTML = '<div class="no-projects">No projects generated yet...</div>';
        document.getElementById('dataFlows').innerHTML = '<div class="no-flows">No data flows defined yet...</div>';
        document.getElementById('processingStatus').innerHTML = '<div class="no-processing">No processing active...</div>';
        document.getElementById('results').innerHTML = '<div class="no-results">No results yet...</div>';
        document.getElementById('workflowHistory').innerHTML = '<div class="no-history">No workflow steps yet...</div>';
        document.getElementById('showAuditTrailBtn').style.display = 'none';
        document.getElementById('saveResultsBtn').style.display = 'none';
        document.getElementById('currentData').innerHTML = '<div class="no-data">No data flowing yet...</div>';
        
        document.getElementById('activateProjectsBtn').disabled = true;
        document.getElementById('stepThroughBtn').disabled = true;
        
        this.updateAnalysisStatus('Reset complete');
    }
    
    updateAnalysisStatus(message) {
        document.getElementById('analysisStatus').textContent = message;
    }
    
    async authenticate() {
        if (this.authToken) return true;
        
        try {
            this.updateAnalysisStatus('🔐 Authenticating with ODRAS...');
            const response = await fetch(`${this.baseUrl}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: 'das_service',
                    password: 'das_service_2024!'
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.authToken = data.token || data.access_token;
                if (this.authToken) {
                    console.log('✅ Authenticated with ODRAS');
                    return true;
                }
            }
            console.error('❌ Authentication failed:', response.status);
            return false;
        } catch (error) {
            console.error('❌ Authentication error:', error);
            return false;
        }
    }
    
    async getDefaultNamespace() {
        try {
            const response = await fetch(`${this.baseUrl}/api/namespaces/released`, {
                headers: {
                    'Authorization': `Bearer ${this.authToken}`
                }
            });
            
            if (response.ok) {
                const namespaces = await response.json();
                if (Array.isArray(namespaces) && namespaces.length > 0) {
                    return namespaces[0].id;
                }
            }
            return null;
        } catch (error) {
            console.error('❌ Error getting namespace:', error);
            return null;
        }
    }
    
    async createProjectsInODRAS() {
        if (!this.currentLattice || !this.currentLattice.projects) {
            console.warn('No lattice to create');
            return;
        }
        
        // Authenticate first
        if (!await this.authenticate()) {
            alert('Failed to authenticate with ODRAS. Projects will not be created.');
            return;
        }
        
        // Get namespace
        const namespaceId = await this.getDefaultNamespace();
        if (!namespaceId) {
            alert('Failed to get namespace. Projects will not be created.');
            return;
        }
        
        this.updateAnalysisStatus('📁 Creating projects in ODRAS...');
        this.projectRegistry = {};
        this.createdProjects = [];
        
        // Sort projects by level (parents first) to ensure parent projects exist before children
        const sortedProjects = [...this.currentLattice.projects].sort((a, b) => a.layer - b.layer);
        
        // Create projects in order
        for (const project of sortedProjects) {
            try {
                const projectData = {
                    name: project.name,
                    namespace_id: namespaceId,
                    domain: project.domain,
                    project_level: project.layer,
                    description: project.description || project.purpose
                };
                
                // Add parent if specified
                if (project.parent_name && this.projectRegistry[project.parent_name]) {
                    projectData.parent_project_id = this.projectRegistry[project.parent_name].project_id;
                }
                
                const response = await fetch(`${this.baseUrl}/api/projects`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${this.authToken}`
                    },
                    body: JSON.stringify(projectData)
                });
                
                if (response.ok) {
                    const result = await response.json();
                    const createdProject = result.project || result;
                    this.projectRegistry[project.name] = createdProject;
                    this.createdProjects.push(createdProject.project_id);
                    console.log(`✅ Created project: ${project.name} (L${project.layer})`);
                } else {
                    const errorText = await response.text();
                    console.error(`❌ Failed to create ${project.name}:`, response.status, errorText);
                }
            } catch (error) {
                console.error(`❌ Error creating ${project.name}:`, error);
            }
        }
        
        // Create cousin relationships if specified in data flows
        if (this.currentLattice.data_flows) {
            this.updateAnalysisStatus('🔗 Creating relationships...');
            for (const flow of this.currentLattice.data_flows) {
                // Check if this is a cousin relationship (different domains, same level)
                const fromProject = this.currentLattice.projects.find(p => p.name === flow.from_project);
                const toProject = this.currentLattice.projects.find(p => p.name === flow.to_project);
                
                if (fromProject && toProject && 
                    fromProject.domain !== toProject.domain && 
                    fromProject.layer === toProject.layer &&
                    this.projectRegistry[flow.from_project] && 
                    this.projectRegistry[flow.to_project]) {
                    
                    try {
                        const sourceId = this.projectRegistry[flow.from_project].project_id;
                        const targetId = this.projectRegistry[flow.to_project].project_id;
                        
                        const response = await fetch(`${this.baseUrl}/api/projects/${sourceId}/relationships`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'Authorization': `Bearer ${this.authToken}`
                            },
                            body: JSON.stringify({
                                target_project_id: targetId,
                                relationship_type: 'coordinates_with',
                                description: flow.description || `${flow.from_project} coordinates with ${flow.to_project}`
                            })
                        });
                        
                        if (response.ok) {
                            console.log(`✅ Created relationship: ${flow.from_project} → ${flow.to_project}`);
                        }
                    } catch (error) {
                        console.error(`❌ Error creating relationship:`, error);
                    }
                }
            }
        }
        
        this.updateAnalysisStatus(`✅ Created ${this.createdProjects.length} projects in ODRAS`);
        console.log(`✅ Created ${this.createdProjects.length} projects in ODRAS`);
    }
    
    saveResults() {
        if (!this.currentLattice) {
            alert('No lattice generated yet. Please generate a lattice first.');
            return;
        }
        
        const data = {
            lattice: this.currentLattice,
            projects: this.createdProjects || [],
            registry: this.projectRegistry || {},
            workflowHistory: this.workflowHistory || [],
            llmAuditTrail: this.llmAuditTrail || []
        };
        
        // Check if vscode API is available (when embedded directly in VS Code webview)
        if (typeof vscode !== 'undefined' && vscode) {
            // Direct call to extension host - no iframe needed!
            vscode.postMessage({
                command: 'saveLattice',
                data: data
            });
            
            this.updateAnalysisStatus('💾 Saving to .odras/demo/...');
            return;
        }
        
        // Fallback: Try iframe communication (for backward compatibility)
        if (window.parent && window.parent !== window) {
            // We're in an iframe - send message to parent (desktop webview)
            window.parent.postMessage({
                source: 'lattice-demo-iframe',
                command: 'saveLattice',
                data: data
            }, '*');
            
            this.updateAnalysisStatus('💾 Saving to .odras/demo/...');
            return;
        }
        
        // Fallback: browser downloads if not in VS Code extension
        const files = [
            { name: 'lattice.json', data: data.lattice },
            { name: 'projects.json', data: data.projects },
            { name: 'registry.json', data: data.registry },
            { name: 'workflow-history.json', data: data.workflowHistory },
            { name: 'llm-audit-trail.json', data: data.llmAuditTrail }
        ];
        
        let savedCount = 0;
        files.forEach((file, index) => {
            if (file.data !== undefined && file.data !== null) {
                const jsonStr = JSON.stringify(file.data, null, 2);
                const blob = new Blob([jsonStr], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = file.name;
                document.body.appendChild(a);
                // Stagger downloads slightly to avoid browser blocking
                setTimeout(() => {
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    savedCount++;
                    if (savedCount === files.filter(f => f.data !== undefined && f.data !== null).length) {
                        this.updateAnalysisStatus(`✅ Saved ${savedCount} files. Save them to .odras/demo/ folder.`);
                    }
                }, index * 100);
            }
        });
        
        if (savedCount === 0) {
            alert('No data to save. Please generate a lattice first.');
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.intelligentLattice = new IntelligentLatticeGenerator();
    
    // Auto-load sample solutions on page load
    window.intelligentLattice.loadSampleSolutions();
});
