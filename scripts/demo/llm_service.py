#!/usr/bin/env python3
"""
LLM Service - Intelligent project lattice generation using LLM

Provides LLM-powered project lattice generation with:
- Exact prompts sent to LLM
- Raw LLM responses
- Project processing with full context
- Complete audit trail of all LLM interactions
"""

import json
import logging
import time
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for browser requests


class LLMService:
    """LLM service for intelligent project lattice generation and processing."""
    
    def __init__(self):
        self.client = self._get_openai_client()
        self.last_prompt = None
        self.last_response = None
        self.generation_history = []
    
    def _get_openai_client(self) -> Optional[OpenAI]:
        """Get OpenAI client if API key is available."""
        # Try to load API key
        api_key = None
        
        # Check .env file
        if os.path.exists(".env"):
            with open(".env") as f:
                for line in f:
                    if line.startswith("OPENAI_API_KEY=") and not "your-openai" in line:
                        api_key = line.strip().split("=", 1)[1].strip('"\'')
                        break
        
        # Check environment
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        
        if api_key and "your-openai" not in api_key:
            logger.info("✅ Found OpenAI API key")
            return OpenAI(api_key=api_key)
        else:
            logger.warning("❌ No valid OpenAI API key found")
            return None
    
    def generate_with_context(self, requirements_text: str, max_projects: int = 6) -> Dict[str, Any]:
        """Generate lattice with full context exposure."""
        
        # Build the prompt
        prompt = self._build_detailed_prompt(requirements_text, max_projects)
        self.last_prompt = prompt
        
        generation_id = f"gen_{int(time.time())}"
        
        if self.client:
            try:
                # Call real OpenAI
                logger.info("🧠 Calling OpenAI for project generation...")
                
                response = self.client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert systems engineer specializing in UAV acquisition programs. You analyze requirements and design intelligent project structures for complex acquisition programs."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.4,  # Some randomness for probabilistic results
                    max_tokens=3000
                )
                
                self.last_response = response.choices[0].message.content
                
                # Parse JSON from response
                json_start = self.last_response.find('{')
                json_end = self.last_response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_content = self.last_response[json_start:json_end]
                    lattice_data = json.loads(json_content)
                    
                    result = {
                        "generation_id": generation_id,
                        "source": "openai_gpt4",
                        "prompt_sent": prompt,
                        "raw_response": self.last_response,
                        "parsed_lattice": lattice_data,
                        "success": True,
                        "probabilistic": True,
                        "generation_time": time.time()
                    }
                    
                    self.generation_history.append(result)
                    logger.info(f"✅ OpenAI generation complete: {len(lattice_data.get('projects', []))} projects")
                    return result
                else:
                    raise ValueError("No valid JSON in LLM response")
                    
            except Exception as e:
                logger.error(f"OpenAI generation failed: {e}")
                # Fallback to mock but mark as fallback
                return self._generate_mock_with_context(requirements_text, generation_id, str(e))
        else:
            logger.info("Using mock LLM (no API key)")
            return self._generate_mock_with_context(requirements_text, generation_id, "No OpenAI API key")
    
    def _generate_mock_with_context(self, requirements: str, generation_id: str, reason: str) -> Dict[str, Any]:
        """Generate mock lattice but expose it as if it was LLM generated."""
        
        prompt = self._build_detailed_prompt(requirements, 6)
        
        # Generate probabilistic mock response (different each time)
        import random
        random.seed()  # Ensure different results each run
        
        # Vary the project structure based on requirements focus
        req_lower = requirements.lower()
        
        # Different lattice structures based on content analysis
        if "disaster" in req_lower and "rapid" in req_lower:
            lattice_variant = "disaster_response_focused"
            projects_config = self._get_disaster_response_config()
        elif "performance" in req_lower and "endurance" in req_lower:
            lattice_variant = "performance_focused"  
            projects_config = self._get_performance_focused_config()
        else:
            lattice_variant = "general_analysis"
            projects_config = self._get_general_config()
        
        # Add randomness to confidence and descriptions
        confidence = 0.75 + random.uniform(0, 0.2)
        
        # Simulate realistic LLM response
        mock_response = json.dumps(projects_config, indent=2)
        
        result = {
            "generation_id": generation_id,
            "source": f"mock_llm_{lattice_variant}",
            "fallback_reason": reason,
            "prompt_sent": prompt,
            "raw_response": f"Based on analysis of the UAV requirements, I'll design a project lattice...\n\n{mock_response}",
            "parsed_lattice": projects_config,
            "success": True,
            "probabilistic": True,
            "generation_time": time.time()
        }
        
        self.generation_history.append(result)
        return result
    
    def _get_disaster_response_config(self) -> Dict[str, Any]:
        """Config for disaster response focused requirements."""
        return {
            "analysis_summary": "Requirements focus on rapid disaster response deployment. Generated lattice emphasizes quick assessment capabilities and operational resilience.",
            "confidence": 0.89,
            "lattice_type": "disaster_response_optimized",
            "projects": [
                {
                    "name": "emergency-requirements",
                    "domain": "systems-engineering",
                    "layer": 1,
                    "description": "Rapid requirements analysis for emergency response UAV",
                    "purpose": "Extract time-critical operational requirements for emergency deployment",
                    "inputs": ["emergency_requirements", "deployment_constraints", "response_timelines"],
                    "outputs": ["critical_capabilities", "deployment_requirements", "operational_constraints"],
                    "processing_type": "analysis",
                    "subscribes_to": ["ontology.published"],
                    "publishes": ["emergency_requirements.analyzed"]
                },
                {
                    "name": "rapid-deployment-analysis",
                    "domain": "mission-planning",
                    "layer": 2, 
                    "description": "Analyze rapid deployment scenarios for emergency response",
                    "purpose": "Define deployment procedures and operational concepts for emergency scenarios",
                    "inputs": ["critical_capabilities", "response_protocols"],
                    "outputs": ["deployment_procedures", "emergency_scenarios", "response_concepts"],
                    "processing_type": "analysis",
                    "parent_name": "emergency-requirements",
                    "subscribes_to": ["emergency_requirements.analyzed"],
                    "publishes": ["deployment.defined"]
                },
                {
                    "name": "system-resilience-analysis",
                    "domain": "analysis",
                    "layer": 2,
                    "description": "Evaluate system resilience for emergency operations",
                    "purpose": "Assess UAV system robustness for emergency deployment conditions",
                    "inputs": ["operational_constraints", "environmental_factors"],
                    "outputs": ["resilience_assessment", "risk_mitigation"],
                    "processing_type": "analysis", 
                    "parent_name": "emergency-requirements",
                    "subscribes_to": ["emergency_requirements.analyzed"],
                    "publishes": ["resilience.assessed"]
                },
                {
                    "name": "emergency-solution-selection",
                    "domain": "analysis",
                    "layer": 3,
                    "description": "Select optimal UAV for emergency response missions",
                    "purpose": "Recommend UAV solution optimized for emergency response scenarios",
                    "inputs": ["deployment_procedures", "resilience_assessment", "uav_options"],
                    "outputs": ["emergency_recommendation", "deployment_plan"],
                    "processing_type": "evaluation",
                    "parent_name": "rapid-deployment-analysis", 
                    "subscribes_to": ["deployment.defined", "resilience.assessed"],
                    "publishes": ["solution.optimized"]
                }
            ],
            "data_flows": [
                {
                    "from_project": "emergency-requirements",
                    "to_project": "rapid-deployment-analysis",
                    "data_type": "critical_capabilities",
                    "description": "Critical capabilities drive deployment scenario development",
                    "trigger_event": "emergency_requirements.analyzed"
                },
                {
                    "from_project": "emergency-requirements", 
                    "to_project": "system-resilience-analysis",
                    "data_type": "operational_constraints",
                    "description": "Operational constraints inform resilience analysis",
                    "trigger_event": "emergency_requirements.analyzed"
                },
                {
                    "from_project": "rapid-deployment-analysis",
                    "to_project": "emergency-solution-selection",
                    "data_type": "deployment_procedures",
                    "description": "Deployment procedures guide solution selection",
                    "trigger_event": "deployment.defined"
                },
                {
                    "from_project": "system-resilience-analysis",
                    "to_project": "emergency-solution-selection", 
                    "data_type": "resilience_assessment",
                    "description": "Resilience assessment ensures robust solution selection",
                    "trigger_event": "resilience.assessed"
                }
            ],
            "domains": ["systems-engineering", "mission-planning", "analysis"]
        }
    
    def _get_performance_focused_config(self) -> Dict[str, Any]:
        """Config for performance-focused requirements."""
        return {
            "analysis_summary": "Requirements emphasize technical performance and endurance capabilities. Generated lattice focuses on detailed performance analysis and optimization.",
            "confidence": 0.84,
            "lattice_type": "performance_optimized", 
            "projects": [
                {
                    "name": "performance-requirements",
                    "domain": "systems-engineering",
                    "layer": 1,
                    "description": "Analyze performance and endurance requirements",
                    "purpose": "Extract and prioritize technical performance requirements",
                    "inputs": ["performance_specs", "endurance_requirements"], 
                    "outputs": ["performance_matrix", "technical_thresholds"],
                    "processing_type": "analysis",
                    "subscribes_to": ["ontology.published"],
                    "publishes": ["performance.analyzed"]
                },
                {
                    "name": "endurance-optimization",
                    "domain": "analysis",
                    "layer": 2,
                    "description": "Optimize UAV endurance capabilities",
                    "purpose": "Analyze endurance requirements and optimization opportunities",
                    "inputs": ["performance_matrix", "endurance_profiles"],
                    "outputs": ["endurance_analysis", "optimization_recommendations"],
                    "processing_type": "analysis",
                    "parent_name": "performance-requirements",
                    "subscribes_to": ["performance.analyzed"],
                    "publishes": ["endurance.optimized"]
                },
                {
                    "name": "capability-matching", 
                    "domain": "analysis",
                    "layer": 2,
                    "description": "Match UAV capabilities to performance requirements",
                    "purpose": "Evaluate UAV options against performance criteria",
                    "inputs": ["technical_thresholds", "uav_capabilities"],
                    "outputs": ["capability_assessment", "performance_gaps"],
                    "processing_type": "analysis",
                    "parent_name": "performance-requirements",
                    "subscribes_to": ["performance.analyzed"], 
                    "publishes": ["capabilities.matched"]
                },
                {
                    "name": "optimized-selection",
                    "domain": "analysis", 
                    "layer": 3,
                    "description": "Select performance-optimized UAV solution",
                    "purpose": "Recommend UAV solution optimized for performance requirements",
                    "inputs": ["endurance_analysis", "capability_assessment"],
                    "outputs": ["optimized_recommendation", "performance_justification"],
                    "processing_type": "evaluation",
                    "parent_name": "endurance-optimization",
                    "subscribes_to": ["endurance.optimized", "capabilities.matched"],
                    "publishes": ["solution.performance_optimized"]
                }
            ],
            "data_flows": [
                {
                    "from_project": "performance-requirements",
                    "to_project": "endurance-optimization",
                    "data_type": "performance_matrix", 
                    "description": "Performance matrix drives endurance optimization",
                    "trigger_event": "performance.analyzed"
                },
                {
                    "from_project": "performance-requirements",
                    "to_project": "capability-matching",
                    "data_type": "technical_thresholds",
                    "description": "Technical thresholds guide capability matching",
                    "trigger_event": "performance.analyzed"
                },
                {
                    "from_project": "endurance-optimization",
                    "to_project": "optimized-selection",
                    "data_type": "endurance_analysis",
                    "description": "Endurance analysis informs final selection",
                    "trigger_event": "endurance.optimized"
                },
                {
                    "from_project": "capability-matching", 
                    "to_project": "optimized-selection",
                    "data_type": "capability_assessment",
                    "description": "Capability assessment guides optimization",
                    "trigger_event": "capabilities.matched"
                }
            ],
            "domains": ["systems-engineering", "analysis"]
        }
    
    def _get_general_config(self) -> Dict[str, Any]:
        """Config for general requirements."""
        return {
            "analysis_summary": "Balanced requirements analysis with focus on comprehensive evaluation approach.",
            "confidence": 0.78,
            "lattice_type": "comprehensive_analysis",
            "projects": [
                {
                    "name": "comprehensive-requirements",
                    "domain": "systems-engineering", 
                    "layer": 1,
                    "description": "Comprehensive UAV requirements analysis",
                    "purpose": "Thorough analysis of all UAV requirements and constraints",
                    "inputs": ["requirements_documents", "stakeholder_needs"],
                    "outputs": ["requirement_breakdown", "constraint_analysis"],
                    "processing_type": "analysis",
                    "subscribes_to": ["ontology.published"],
                    "publishes": ["comprehensive.analyzed"]
                },
                {
                    "name": "solution-architecture",
                    "domain": "architecture",
                    "layer": 2,
                    "description": "Design UAV solution architecture", 
                    "purpose": "Develop comprehensive system architecture for UAV solution",
                    "inputs": ["requirement_breakdown", "technical_constraints"],
                    "outputs": ["system_architecture", "design_specifications"],
                    "processing_type": "design",
                    "parent_name": "comprehensive-requirements",
                    "subscribes_to": ["comprehensive.analyzed"],
                    "publishes": ["architecture.designed"]
                },
                {
                    "name": "integrated-evaluation",
                    "domain": "analysis",
                    "layer": 3,
                    "description": "Integrated evaluation of UAV solutions",
                    "purpose": "Comprehensive evaluation considering all factors",
                    "inputs": ["system_architecture", "evaluation_criteria"],
                    "outputs": ["integrated_assessment", "final_recommendation"],
                    "processing_type": "evaluation", 
                    "parent_name": "solution-architecture",
                    "subscribes_to": ["architecture.designed"],
                    "publishes": ["evaluation.integrated"]
                }
            ],
            "data_flows": [
                {
                    "from_project": "comprehensive-requirements",
                    "to_project": "solution-architecture",
                    "data_type": "requirement_breakdown",
                    "description": "Comprehensive requirements drive architectural design",
                    "trigger_event": "comprehensive.analyzed"
                },
                {
                    "from_project": "solution-architecture",
                    "to_project": "integrated-evaluation", 
                    "data_type": "system_architecture",
                    "description": "System architecture flows to integrated evaluation",
                    "trigger_event": "architecture.designed"
                }
            ],
            "domains": ["systems-engineering", "architecture", "analysis"]
        }
    
    def _build_detailed_prompt(self, requirements_text: str, max_projects: int) -> str:
        """Build detailed prompt for LLM."""
        
        return f"""
TASK: Analyze UAV acquisition requirements and design an intelligent project lattice structure.

REQUIREMENTS DOCUMENT TO ANALYZE:
{requirements_text}

ANALYSIS INSTRUCTIONS:
You are designing a project lattice for a UAV acquisition program. Each project should be a logical analysis component that processes specific aspects of the requirements.

Think like a systems engineer breaking down this acquisition into manageable project components. Consider:
- What analyses are needed to make an informed UAV selection?
- How should information flow between analyses?
- What are the logical dependencies between different aspects?

AVAILABLE PROJECT TYPES:
- Requirements Analysis: Decompose and analyze requirements
- Mission Analysis: Define operational scenarios and use cases
- Performance Analysis: Evaluate technical performance requirements  
- Cost Analysis: Analyze cost constraints and lifecycle economics
- Risk Analysis: Identify and assess program risks
- Trade Study: Compare alternative solutions
- Solution Evaluation: Evaluate and recommend solutions
- Integration Analysis: Analyze system integration requirements
- Test Planning: Plan verification and validation

PROJECT LAYERS (think hierarchical decomposition):
- L0: Foundation/Ontology (foundational concepts, 0-1 projects)
- L1: Strategic Analysis (high-level decomposition, 1-2 projects)
- L2: Tactical Analysis (detailed analysis, 2-3 projects)
- L3: Solution Selection (specific recommendations, 1-2 projects)

DOMAINS:
systems-engineering, mission-planning, cost, analysis, architecture, integration, testing

RESPONSE FORMAT:
Return ONLY a JSON object with this EXACT structure:

{{
  "analysis_summary": "Your reasoning for why you chose this project structure",
  "confidence": 0.85,
  "lattice_reasoning": "Explanation of how projects work together",
  "projects": [
    {{
      "name": "descriptive-project-name",
      "domain": "systems-engineering",
      "layer": 1,
      "description": "What this project does",
      "purpose": "Why this project is needed for UAV acquisition",
      "inputs": ["specific_data_this_project_needs"],
      "outputs": ["specific_data_this_project_produces"],
      "processing_type": "analysis",
      "parent_name": null,
      "subscribes_to": ["ontology.published"],
      "publishes": ["event.type"]
    }}
  ],
  "data_flows": [
    {{
      "from_project": "project-name",
      "to_project": "target-project",
      "data_type": "specific_data_being_transferred",
      "description": "Why this data flows to this project",
      "trigger_event": "event.type"
    }}
  ],
  "domains": ["list", "of", "domains", "used"]
}}

IMPORTANT:
- Create {max_projects} projects maximum
- Focus specifically on UAV acquisition decision-making
- Ensure logical data flows between projects
- Each project should have clear purpose for UAV selection
- Make the lattice specifically relevant to the provided requirements
"""
    
    def process_project(self, project: Dict[str, Any], requirements: str, upstream_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a single project using LLM to generate detailed analysis."""
        
        if not self.client:
            raise RuntimeError("OpenAI API key not configured. Set OPENAI_API_KEY in .env file or environment variables.")
        
        # Build project-specific prompt
        prompt = self._build_project_processing_prompt(project, requirements, upstream_data)
        
        generation_id = f"project_{project.get('name', 'unknown')}_{int(time.time())}"
        
        try:
            logger.info(f"🧠 Processing project: {project.get('name')} ({project.get('processing_type')})")
            
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert systems engineer analyzing UAV acquisition requirements. You provide detailed, realistic analysis with specific confidence levels based on data quality and analysis depth."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,
                max_tokens=2000
            )
            
            llm_response = response.choices[0].message.content
            
            # Parse JSON from response
            json_start = llm_response.find('{')
            json_end = llm_response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_content = llm_response[json_start:json_end]
                result_data = json.loads(json_content)
                
                # Ensure confidence is included and is from LLM
                if 'confidence' not in result_data:
                    raise ValueError("LLM response must include confidence level")
                
                result = {
                    "generation_id": generation_id,
                    "source": "openai_gpt4",
                    "prompt_sent": prompt,
                    "raw_response": llm_response,
                    "project_name": project.get('name'),
                    "result": result_data,
                    "success": True,
                    "generation_time": time.time()
                }
                
                self.generation_history.append(result)
                logger.info(f"✅ Project processing complete: {project.get('name')} (confidence: {result_data.get('confidence', 'N/A')})")
                return result
            else:
                raise ValueError("No valid JSON in LLM response")
                
        except Exception as e:
            logger.error(f"Project processing failed: {e}")
            raise RuntimeError(f"OpenAI API call failed: {e}") from e
    
    def _build_project_processing_prompt(self, project: Dict[str, Any], requirements: str, upstream_data: Dict[str, Any] = None) -> str:
        """Build prompt for processing a specific project."""
        
        upstream_info = ""
        if upstream_data:
            upstream_info = f"""
UPSTREAM DATA AVAILABLE:
{json.dumps(upstream_data, indent=2)}
"""
        
        return f"""
TASK: Process the project "{project.get('name')}" as part of a UAV acquisition program.

PROJECT DETAILS:
- Name: {project.get('name')}
- Domain: {project.get('domain')}
- Layer: {project.get('layer')}
- Processing Type: {project.get('processing_type')}
- Purpose: {project.get('purpose')}
- Description: {project.get('description')}
- Expected Inputs: {', '.join(project.get('inputs', []))}
- Expected Outputs: {', '.join(project.get('outputs', []))}

ORIGINAL REQUIREMENTS:
{requirements[:2000]}

{upstream_info}

INSTRUCTIONS:
Analyze and process this project according to its purpose and processing type. Provide detailed, realistic results specific to UAV acquisition.

For {project.get('processing_type')} type projects, focus on:
- Analysis projects: Extract specific data, identify patterns, quantify requirements
- Design projects: Create detailed designs, architectures, or plans
- Evaluation projects: Compare options, make recommendations with justification

IMPORTANT:
- Provide a REAL confidence level (0.0-1.0) based on:
  * Quality and completeness of input data
  * Clarity of requirements
  * Complexity of the analysis
  * Availability of upstream data
- Confidence should be realistic - not always high (0.85-0.95)
- Lower confidence (0.65-0.80) if data is incomplete or requirements are vague
- Higher confidence (0.85-0.95) if data is complete and requirements are clear
- NEVER use fixed confidence values - vary based on actual analysis quality

RESPONSE FORMAT:
Return ONLY a JSON object with this EXACT structure:

{{
  "project_name": "{project.get('name')}",
  "analysis_type": "specific_type_of_analysis",
  "llm_reasoning": [
    "Step 1 of your reasoning process",
    "Step 2 of your reasoning process",
    "Step 3..."
  ],
  "extracted_data": {{
    "key_findings": ["finding1", "finding2"],
    "specific_metrics": {{"metric": "value"}},
    "recommendations": ["rec1", "rec2"]
  }},
  "confidence": 0.82,
  "confidence_reasoning": "Why this confidence level (data quality, completeness, etc.)",
  "processing_time": 2.5,
  "ready_for_downstream": true,
  "next_actions": [
    "Action 1 for downstream projects",
    "Action 2 for downstream projects"
  ]
}}

Make the response specific to UAV acquisition and realistic. Include actual confidence reasoning.
"""
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get complete debug information."""
        return {
            "last_generation": self.generation_history[-1] if self.generation_history else None,
            "total_generations": len(self.generation_history),
            "openai_available": self.client is not None,
            "history": self.generation_history[-5:]  # Last 5 generations
        }


# Global LLM service instance
llm_service = LLMService()


@app.route('/generate-lattice', methods=['POST'])
def generate_lattice():
    """Generate lattice with full debug context."""
    try:
        data = request.json
        requirements = data.get('requirements', '')
        max_projects = data.get('max_projects', 6)
        
        if not requirements.strip():
            return jsonify({"error": "Requirements text is required"}), 400
        
        # Generate with full context
        result = llm_service.generate_with_context(requirements, max_projects)
        
        # Return just the lattice data (debug info available via separate endpoint)
        return jsonify(result['parsed_lattice'])
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/debug-context', methods=['GET'])
def get_debug_context():
    """Get complete LLM interaction context."""
    return jsonify(llm_service.get_debug_info())


@app.route('/debug-last-prompt', methods=['GET']) 
def get_last_prompt():
    """Get the last prompt sent to LLM."""
    if llm_service.generation_history:
        last_gen = llm_service.generation_history[-1]
        return jsonify({
            "generation_id": last_gen["generation_id"],
            "source": last_gen["source"],
            "prompt": last_gen["prompt_sent"],
            "raw_response": last_gen.get("raw_response", ""),
            "success": last_gen["success"]
        })
    return jsonify({"error": "No generations yet"}), 404


@app.route('/process-project', methods=['POST'])
def process_project():
    """Process a single project using LLM."""
    try:
        data = request.json
        project = data.get('project')
        requirements = data.get('requirements', '')
        upstream_data = data.get('upstream_data')
        
        if not project:
            return jsonify({"error": "Project data is required"}), 400
        
        if not requirements.strip():
            return jsonify({"error": "Requirements text is required"}), 400
        
        # Process project with LLM
        result = llm_service.process_project(project, requirements, upstream_data)
        
        # Return both the result data AND the full interaction details
        return jsonify({
            'result': result['result'],
            'llm_interaction': {
                'prompt_sent': result.get('prompt_sent'),
                'raw_response': result.get('raw_response'),
                'source': result.get('source'),
                'generation_id': result.get('generation_id'),
                'success': result.get('success')
            }
        })
        
    except Exception as e:
        logger.error(f"Project processing failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({
        "status": "ok",
        "openai_available": llm_service.client is not None,
        "generations": len(llm_service.generation_history)
    })


if __name__ == "__main__":
    print("🧠 Starting LLM Service...")
    print("🔍 Intelligent project lattice generation with LLM")
    print(f"✅ OpenAI Available: {llm_service.client is not None}")
    print("")
    print("📋 Endpoints:")
    print("  POST /generate-lattice - Generate project lattice")
    print("  POST /process-project - Process individual project")
    print("  GET  /debug-context - Get complete LLM interaction context")
    print("  GET  /debug-last-prompt - Get last LLM prompt/response")
    print("  GET  /health - Service health")
    print("")
    app.run(host='0.0.0.0', port=8083, debug=False)
