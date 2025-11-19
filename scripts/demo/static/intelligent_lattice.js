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
        
        this.init();
    }
    
    init() {
        console.log('🧠 Initializing Intelligent Lattice Generator...');
        this.initCytoscape();
        this.initEventHandlers();
        this.loadExampleRequirements();
        console.log('✅ Intelligent generator ready');
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
                                return '#fbbf24'; // Yellow for processing
                            }
                            
                            return baseColor;
                        },
                        'color': '#ffffff',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'font-size': '11px',
                        'font-weight': 'bold',
                        'border-width': function(ele) {
                            const state = ele.data('state');
                            return state === 'processing' ? 4 : 2;
                        },
                        'border-color': function(ele) {
                            const state = ele.data('state');
                            if (state === 'processing') return '#fbbf24';
                            return '#334155';
                        },
                        'text-wrap': 'wrap',
                        'text-max-width': '90px'
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
            // Call the actual LLM debug service
            console.log('📡 Calling LLM Debug Service...');
            const response = await fetch('http://localhost:8083/generate-lattice', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    requirements: requirementsText,
                    max_projects: 6 
                })
            });
            
            if (response.ok) {
                this.currentLattice = await response.json();
                
                // Fetch debug context to show LLM interaction
                const debugResponse = await fetch('http://localhost:8083/debug-context');
                if (debugResponse.ok) {
                    this.debugContext = await debugResponse.json();
                    this.showDebugContext();
                }
                
                this.updateAnalysisStatus('✅ Real LLM generation complete');
                console.log('✅ Used real LLM service');
            } else {
                throw new Error(`LLM service error: ${response.status}`);
            }
            
            // Display analysis results
            this.displayAnalysisResults();
            
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
            this.createLatticeVisualization();
            this.enableControls();
            this.updateAnalysisStatus('✅ Generated using probabilistic mock');
        } finally {
            document.getElementById('generateLatticeBtn').disabled = false;
        }
    }
    
    showDebugContext() {
        if (!this.debugContext) return;
        
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
        if (!node.length) return;
        
        const projectData = node.data('project_data');
        
        // Set to processing state
        node.data('state', 'processing');
        this.updateProjectState(projectName, 'processing', 'Analyzing requirements...');
        
        // Show detailed processing view
        this.showDetailedProcessing(projectData);
        
        // Simulate LLM processing with realistic timing
        await new Promise(resolve => setTimeout(resolve, 2000 + Math.random() * 2000));
        
        // Generate detailed LLM-like results
        const results = await this.generateDetailedResults(projectData);
        
        // Store results in data store
        this.dataStore.set(projectName, results);
        
        // Set to complete
        node.data('state', 'complete');
        this.updateProjectState(projectName, 'complete', 'Analysis complete');
        
        // Show detailed results
        this.displayDetailedResults(projectName, results);
        
        // Trigger downstream projects
        this.triggerDownstreamProjects(projectName, results);
    }
    
    showDetailedProcessing(projectData) {
        const statusDiv = document.getElementById('processingStatus');
        statusDiv.innerHTML = `
            <div style="font-weight: bold; color: var(--warning); margin-bottom: 8px;">
                🔍 Processing: ${projectData.name}
            </div>
            <div style="margin-bottom: 6px;"><strong>Purpose:</strong> ${projectData.purpose}</div>
            <div style="margin-bottom: 6px;"><strong>Processing Type:</strong> ${projectData.processing_type}</div>
            <div style="margin-bottom: 8px;"><strong>Expected Inputs:</strong> ${projectData.inputs.join(', ')}</div>
            <div style="font-size: 0.9rem; color: var(--text-light); font-style: italic;">
                LLM is analyzing requirements and generating ${projectData.processing_type} specific to ${projectData.domain}...
            </div>
        `;
        
        const dataDiv = document.getElementById('currentData');
        dataDiv.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 6px;">Input Data for ${projectData.name}:</div>
            <div style="font-size: 0.8rem; color: var(--text-light);">
                • Requirements document (${document.getElementById('requirementsInput').value.length} chars)
                <br>• Processing context: ${projectData.domain} domain
                <br>• Expected outputs: ${projectData.outputs.length} data types
            </div>
        `;
    }
    
    async generateDetailedResults(project) {
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
            p.parent_name === completedProject || 
            this.currentLattice.data_flows.some(flow => 
                flow.from_project === completedProject && flow.to_project === p.name
            )
        );
        
        // Animate data flow
        for (const downstreamProject of downstreamProjects) {
            this.animateDataFlow(completedProject, downstreamProject.name, results);
            
            // Start downstream processing after short delay
            setTimeout(() => {
                this.processProject(downstreamProject.name);
            }, 1000);
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
        
        const statusDiv = document.getElementById('processingStatus');
        const stateEntries = Array.from(this.processingStates.entries())
            .sort((a, b) => b[1].timestamp - a[1].timestamp);
        
        statusDiv.innerHTML = '';
        stateEntries.slice(0, 5).forEach(([name, info]) => {
            const stateDiv = document.createElement('div');
            stateDiv.className = 'processing-item';
            stateDiv.innerHTML = `
                <div style="font-weight: bold;">${name}</div>
                <div style="font-size: 0.8rem; color: var(--text-light);">${info.description}</div>
                <div style="font-size: 0.7rem; color: var(--text-light);">${info.state}</div>
            `;
            statusDiv.appendChild(stateDiv);
        });
    }
    
    displayDetailedResults(projectName, results) {
        const resultsDiv = document.getElementById('results');
        
        // Remove "no results" message
        const noResults = resultsDiv.querySelector('.no-results');
        if (noResults) noResults.remove();
        
        const resultDiv = document.createElement('div');
        resultDiv.className = 'result-item';
        resultDiv.style.cssText = 'border: 1px solid var(--border-dark); border-radius: 6px; padding: 12px; margin-bottom: 12px; background: var(--dark-3);';
        
        // Build detailed result display
        let content = `
            <div style="font-weight: bold; color: var(--success); margin-bottom: 8px; font-size: 1rem;">
                ✅ ${projectName} Complete
            </div>
        `;
        
        // Show LLM reasoning process
        if (results.llm_reasoning) {
            content += `
                <div style="margin-bottom: 8px;">
                    <div style="font-weight: bold; color: var(--primary); margin-bottom: 4px;">🧠 LLM Reasoning:</div>
                    <div style="font-size: 0.8rem; color: var(--text-light);">
                        ${results.llm_reasoning.map(reason => `• ${reason}`).join('<br>')}
                    </div>
                </div>
            `;
        }
        
        // Show extracted/developed data
        if (results.extracted_data) {
            content += `
                <div style="margin-bottom: 8px;">
                    <div style="font-weight: bold; color: var(--warning); margin-bottom: 4px;">📊 Extracted Data:</div>
                    <div style="font-size: 0.8rem;">
                        <strong>Capability Gaps:</strong> ${results.extracted_data.capability_gaps.length} identified<br>
                        <strong>Performance Req's:</strong> ${Object.keys(results.extracted_data.performance_requirements).length} parameters<br>
                        <strong>Constraints:</strong> ${results.extracted_data.technical_constraints.length} technical constraints
                    </div>
                </div>
            `;
        } else if (results.developed_scenarios) {
            content += `
                <div style="margin-bottom: 8px;">
                    <div style="font-weight: bold; color: var(--warning); margin-bottom: 4px;">🎯 Developed Scenarios:</div>
                    <div style="font-size: 0.8rem;">
                        ${Object.values(results.developed_scenarios).map(scenario => 
                            `<strong>${scenario.name}:</strong> ${scenario.description}`
                        ).join('<br>')}
                    </div>
                </div>
            `;
        } else if (results.performance_evaluation) {
            content += `
                <div style="margin-bottom: 8px;">
                    <div style="font-weight: bold; color: var(--warning); margin-bottom: 4px;">📈 Performance Evaluation:</div>
                    <div style="font-size: 0.8rem;">
                        ${results.performance_evaluation.evaluated_uavs.map(uav => 
                            `<strong>${uav.name}:</strong> Score ${Math.round(uav.performance_score * 100)}%`
                        ).join('<br>')}
                    </div>
                </div>
            `;
        } else if (results.final_recommendation) {
            content += `
                <div style="margin-bottom: 8px;">
                    <div style="font-weight: bold; color: var(--success); margin-bottom: 4px;">🎯 Final Recommendation:</div>
                    <div style="font-size: 0.9rem; font-weight: bold; color: var(--success);">
                        ${results.final_recommendation.selected_uav}
                    </div>
                    <div style="font-size: 0.8rem; margin-top: 4px;">
                        ${results.final_recommendation.justification}
                    </div>
                </div>
            `;
        }
        
        // Show confidence and next actions
        content += `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">
                <div style="font-size: 0.8rem;">
                    <span style="color: var(--text-light);">Confidence:</span>
                    <span style="color: var(--success); font-weight: bold;">${Math.round(results.confidence * 100)}%</span>
                </div>
                <div style="font-size: 0.7rem; color: var(--text-light);">
                    Ready: ${results.ready_for_downstream ? '✅' : '❌'}
                </div>
            </div>
        `;
        
        if (results.next_actions) {
            content += `
                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border-dark);">
                    <div style="font-size: 0.8rem; color: var(--primary);">
                        <strong>Next Actions:</strong><br>
                        ${results.next_actions.map(action => `• ${action}`).join('<br>')}
                    </div>
                </div>
            `;
        }
        
        resultDiv.innerHTML = content;
        resultsDiv.insertBefore(resultDiv, resultsDiv.firstChild);
        
        // Keep only last 2 detailed results
        const items = resultsDiv.querySelectorAll('.result-item');
        if (items.length > 2) {
            items[items.length - 1].remove();
        }
    }
    
    stepThroughProcessing() {
        // Manual step-through for demonstration
        if (!this.currentLattice) return;
        
        const inactiveNodes = this.cy.nodes('[state="inactive"]');
        if (inactiveNodes.length > 0) {
            const nextProject = inactiveNodes[0].data('project_data').name;
            this.processProject(nextProject);
        }
    }
    
    resetDemo() {
        this.currentLattice = null;
        this.processingStates.clear();
        this.dataStore.clear();
        
        this.cy.elements().remove();
        document.getElementById('requirementsInput').value = '';
        document.getElementById('analysisSummary').style.display = 'none';
        document.getElementById('projectList').innerHTML = '<div class="no-projects">No projects generated yet...</div>';
        document.getElementById('dataFlows').innerHTML = '<div class="no-flows">No data flows defined yet...</div>';
        document.getElementById('processingStatus').innerHTML = '<div class="no-processing">No processing active...</div>';
        document.getElementById('results').innerHTML = '<div class="no-results">No results yet...</div>';
        
        document.getElementById('activateProjectsBtn').disabled = true;
        document.getElementById('stepThroughBtn').disabled = true;
        
        this.updateAnalysisStatus('Reset complete');
    }
    
    updateAnalysisStatus(message) {
        document.getElementById('analysisStatus').textContent = message;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.intelligentLattice = new IntelligentLatticeGenerator();
});
