"""
Mock LLM Generator (for when OpenAI key isn't available)

Provides intelligent-looking project generation without requiring OpenAI API.
Shows what the real LLM system would produce.
"""

import json
import random
from typing import Dict, List, Any
from llm_project_generator import ProjectSpec, DataFlow, LatticeStructure


class MockLLMGenerator:
    """Mock LLM that generates realistic project lattices."""
    
    def generate_lattice(self, requirements_text: str, max_projects: int = 6) -> LatticeStructure:
        """Generate realistic project lattice based on requirements analysis."""
        
        # Analyze requirements to determine focus areas
        requirements_lower = requirements_text.lower()
        
        # Determine primary focus areas
        has_performance_focus = any(word in requirements_lower for word in 
            ["speed", "range", "endurance", "performance", "capability"])
        has_cost_focus = any(word in requirements_lower for word in 
            ["cost", "budget", "affordable", "price"])
        has_mission_focus = any(word in requirements_lower for word in 
            ["mission", "operational", "scenario", "deployment"])
        has_technical_focus = any(word in requirements_lower for word in 
            ["technical", "sensor", "payload", "system"])
        
        # Generate intelligent project structure based on analysis
        if has_mission_focus and has_technical_focus:
            return self._generate_mission_technical_lattice(requirements_text)
        elif has_performance_focus and has_cost_focus:
            return self._generate_performance_cost_lattice(requirements_text)
        else:
            return self._generate_general_analysis_lattice(requirements_text)
    
    def _generate_mission_technical_lattice(self, requirements: str) -> LatticeStructure:
        """Generate lattice focused on mission and technical analysis."""
        
        projects = [
            ProjectSpec(
                name="requirements-analysis",
                domain="systems-engineering",
                layer=1,
                description="Analyze and decompose UAV requirements for disaster response",
                purpose="Extract operational requirements and technical specifications",
                inputs=["requirements_documents", "stakeholder_input"],
                outputs=["capability_gaps", "technical_requirements", "performance_specifications"],
                processing_type="analysis",
                subscribes_to=["ontology.published"],
                publishes=["requirements.analyzed", "specifications.defined"]
            ),
            ProjectSpec(
                name="mission-scenario-analysis", 
                domain="mission-planning",
                layer=2,
                description="Develop operational scenarios and use cases",
                purpose="Define how UAV will be used in disaster response operations",
                inputs=["capability_gaps", "operational_requirements"],
                outputs=["mission_scenarios", "operational_constraints", "deployment_concepts"],
                processing_type="analysis",
                parent_name="requirements-analysis",
                subscribes_to=["requirements.analyzed"],
                publishes=["scenarios.defined", "constraints.identified"]
            ),
            ProjectSpec(
                name="technical-analysis",
                domain="analysis", 
                layer=2,
                description="Analyze technical performance requirements",
                purpose="Evaluate technical feasibility and constraints",
                inputs=["technical_requirements", "performance_specifications"],
                outputs=["technical_assessment", "feasibility_analysis", "risk_factors"],
                processing_type="analysis", 
                parent_name="requirements-analysis",
                subscribes_to=["requirements.analyzed"], 
                publishes=["technical.assessed", "risks.identified"]
            ),
            ProjectSpec(
                name="solution-evaluation",
                domain="analysis",
                layer=3, 
                description="Evaluate UAV solutions against requirements",
                purpose="Compare available UAV systems against mission and technical requirements",
                inputs=["mission_scenarios", "technical_assessment", "uav_specifications"],
                outputs=["solution_comparison", "recommendation", "trade_analysis"],
                processing_type="evaluation",
                parent_name="technical-analysis",
                subscribes_to=["scenarios.defined", "technical.assessed"],
                publishes=["solution.evaluated", "recommendation.ready"]
            )
        ]
        
        data_flows = [
            DataFlow(
                from_project="requirements-analysis",
                to_project="mission-scenario-analysis", 
                data_type="capability_gaps",
                description="Identified capability gaps flow to mission planning for scenario development",
                trigger_event="requirements.analyzed"
            ),
            DataFlow(
                from_project="requirements-analysis",
                to_project="technical-analysis",
                data_type="technical_requirements", 
                description="Technical specifications flow to technical analysis for feasibility assessment",
                trigger_event="requirements.analyzed"
            ),
            DataFlow(
                from_project="mission-scenario-analysis",
                to_project="solution-evaluation",
                data_type="mission_scenarios",
                description="Mission scenarios flow to solution evaluation for requirements matching",
                trigger_event="scenarios.defined"
            ),
            DataFlow(
                from_project="technical-analysis", 
                to_project="solution-evaluation",
                data_type="technical_assessment",
                description="Technical assessment flows to solution evaluation for capability matching",
                trigger_event="technical.assessed"
            )
        ]
        
        return LatticeStructure(
            projects=projects,
            data_flows=data_flows,
            domains=["systems-engineering", "mission-planning", "analysis"],
            analysis_summary="Requirements show strong focus on mission operations and technical capabilities. Generated lattice emphasizes operational scenario development and technical feasibility analysis leading to solution evaluation.",
            confidence=0.87
        )
    
    def _generate_performance_cost_lattice(self, requirements: str) -> LatticeStructure:
        """Generate lattice focused on performance and cost analysis."""
        
        projects = [
            ProjectSpec(
                name="requirements-analysis",
                domain="systems-engineering",
                layer=1,
                description="Analyze UAV acquisition requirements",
                purpose="Extract performance requirements and cost constraints",
                inputs=["requirements_documents"],
                outputs=["performance_requirements", "cost_constraints", "capability_matrix"],
                processing_type="analysis",
                subscribes_to=["ontology.published"],
                publishes=["requirements.analyzed"]
            ),
            ProjectSpec(
                name="performance-analysis",
                domain="analysis",
                layer=2, 
                description="Analyze UAV performance requirements",
                purpose="Evaluate performance specifications against mission needs",
                inputs=["performance_requirements", "mission_profiles"],
                outputs=["performance_assessment", "capability_gaps"],
                processing_type="analysis",
                parent_name="requirements-analysis",
                subscribes_to=["requirements.analyzed"],
                publishes=["performance.analyzed"]
            ),
            ProjectSpec(
                name="cost-analysis", 
                domain="cost",
                layer=2,
                description="Analyze cost constraints and lifecycle costs",
                purpose="Evaluate acquisition and operational cost factors",
                inputs=["cost_constraints", "operational_profiles"],
                outputs=["cost_model", "affordability_assessment"],
                processing_type="analysis",
                parent_name="requirements-analysis", 
                subscribes_to=["requirements.analyzed"],
                publishes=["costs.analyzed"]
            ),
            ProjectSpec(
                name="trade-study",
                domain="analysis",
                layer=3,
                description="Comparative analysis of UAV options",
                purpose="Trade-off analysis between performance, cost, and mission suitability", 
                inputs=["performance_assessment", "cost_model", "uav_options"],
                outputs=["trade_analysis", "recommendation"],
                processing_type="evaluation",
                parent_name="performance-analysis",
                subscribes_to=["performance.analyzed", "costs.analyzed"],
                publishes=["trade.complete"]
            )
        ]
        
        data_flows = [
            DataFlow("requirements-analysis", "performance-analysis", "performance_requirements", 
                    "Performance specs flow for detailed analysis", "requirements.analyzed"),
            DataFlow("requirements-analysis", "cost-analysis", "cost_constraints",
                    "Cost constraints flow for financial analysis", "requirements.analyzed"),
            DataFlow("performance-analysis", "trade-study", "performance_assessment", 
                    "Performance assessment flows to trade study", "performance.analyzed"),
            DataFlow("cost-analysis", "trade-study", "cost_model",
                    "Cost model flows to trade study for comparison", "costs.analyzed")
        ]
        
        return LatticeStructure(
            projects=projects,
            data_flows=data_flows, 
            domains=["systems-engineering", "analysis", "cost"],
            analysis_summary="Requirements emphasize performance capabilities and cost effectiveness. Generated lattice focuses on detailed performance analysis and cost modeling leading to trade study evaluation.",
            confidence=0.82
        )
    
    def _generate_general_analysis_lattice(self, requirements: str) -> LatticeStructure:
        """Generate general analysis lattice."""
        
        projects = [
            ProjectSpec(
                name="requirements-analysis",
                domain="systems-engineering", 
                layer=1,
                description="Comprehensive requirements analysis",
                purpose="Analyze all UAV requirements and extract key factors",
                inputs=["requirements_documents"],
                outputs=["analyzed_requirements", "priority_matrix"],
                processing_type="analysis",
                subscribes_to=["ontology.published"],
                publishes=["requirements.complete"]
            ),
            ProjectSpec(
                name="solution-development",
                domain="architecture",
                layer=2,
                description="Develop UAV solution architecture", 
                purpose="Design system approach to meet requirements",
                inputs=["analyzed_requirements", "technical_constraints"],
                outputs=["system_architecture", "solution_concept"],
                processing_type="design",
                parent_name="requirements-analysis",
                subscribes_to=["requirements.complete"],
                publishes=["solution.designed"]
            ),
            ProjectSpec(
                name="evaluation",
                domain="analysis",
                layer=3,
                description="Evaluate proposed solutions",
                purpose="Assess solutions against requirements and constraints",
                inputs=["system_architecture", "evaluation_criteria"],
                outputs=["evaluation_results", "recommendations"], 
                processing_type="evaluation",
                parent_name="solution-development",
                subscribes_to=["solution.designed"],
                publishes=["evaluation.complete"]
            )
        ]
        
        data_flows = [
            DataFlow("requirements-analysis", "solution-development", "analyzed_requirements",
                    "Requirements analysis flows to solution development", "requirements.complete"),
            DataFlow("solution-development", "evaluation", "system_architecture", 
                    "Solution concepts flow to evaluation", "solution.designed")
        ]
        
        return LatticeStructure(
            projects=projects,
            data_flows=data_flows,
            domains=["systems-engineering", "architecture", "analysis"],
            analysis_summary="General requirements analysis leading to solution development and evaluation.",
            confidence=0.75
        )


if __name__ == "__main__":
    # Test with mock LLM
    print("🧪 Testing Mock LLM Project Generator...")
    
    generator = MockLLMGenerator()
    
    # Use disaster response requirements for test
    with open("data/uas_spec_docs/disaster_response_requirements.md") as f:
        test_requirements = f.read()
    
    print("📋 Analyzing requirements with Mock LLM...")
    try:
        lattice = generator.generate_lattice(test_requirements[:1500], max_projects=4)
        
        print(f"\n✅ Mock LLM Analysis Complete!")
        print(f"📊 Confidence: {lattice.confidence}")
        print(f"📄 Summary: {lattice.analysis_summary}")
        print(f"\n🏗️ Generated Projects:")
        for project in lattice.projects:
            print(f"  - {project.name} (L{project.layer}, {project.domain})")
            print(f"    Purpose: {project.purpose}")
            print(f"    Inputs: {', '.join(project.inputs[:2])}...")
            print(f"    Outputs: {', '.join(project.outputs[:2])}...")
        
        print(f"\n🔄 Data Flows:")
        for flow in lattice.data_flows:
            print(f"  {flow.from_project} → {flow.to_project}")
            print(f"    Data: {flow.data_type}")
        
        print("\n🎯 This shows intelligent project generation!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
