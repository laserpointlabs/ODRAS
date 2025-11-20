"""
Mock Gray System for Living Lattice Demonstration

Simulates the Gray System's continuous sensitivity analysis capabilities.
Shows how shadow cells perturb parameters and evaluate enterprise stability.
"""

import time
import random
import logging
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SensitivityResult:
    """Result from Gray System sensitivity analysis."""
    project_id: str
    project_name: str
    sensitivity_level: str  # "low", "medium", "high"
    sensitivity_score: float  # 0.0 to 1.0
    fragile_parameters: List[str]
    stability_indicators: Dict[str, float]
    recommendations: List[str]
    analysis_timestamp: datetime


@dataclass
class PerturbationTest:
    """Individual perturbation test."""
    parameter_name: str
    original_value: Any
    perturbed_value: Any
    impact_score: float
    cascade_effects: List[str]


class MockGraySystem:
    """
    Simulates the Gray System's continuous sensitivity analysis.
    
    The Gray System:
    - Continuously perturbs project parameters
    - Evaluates impact on dependent projects
    - Identifies fragile regions in the lattice
    - Provides proactive warnings before changes occur
    """
    
    def __init__(self):
        self.running = False
        self.analysis_thread = None
        self.project_sensitivity = {}
        self.enterprise_health = {}
        self.perturbation_history = []
        self.analysis_cycle_count = 0
        
    def start_continuous_analysis(self):
        """Start continuous sensitivity analysis."""
        if self.running:
            return
        
        self.running = True
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()
        logger.info("🌫️  Gray System started - continuous analysis active")
    
    def stop_continuous_analysis(self):
        """Stop continuous sensitivity analysis."""
        self.running = False
        if self.analysis_thread:
            self.analysis_thread.join()
        logger.info("🌫️  Gray System stopped")
    
    def _analysis_loop(self):
        """Main analysis loop for continuous sensitivity evaluation."""
        while self.running:
            try:
                self.analysis_cycle_count += 1
                
                # Perform sensitivity analysis cycle
                self._run_sensitivity_cycle()
                
                # Update enterprise health assessment
                self._assess_enterprise_health()
                
                # Sleep between cycles (simulate continuous but not overwhelming analysis)
                time.sleep(8 + random.uniform(-2, 3))  # 6-11 second cycles
                
            except Exception as e:
                logger.error(f"Error in Gray System analysis cycle: {e}")
                time.sleep(10)
    
    def _run_sensitivity_cycle(self):
        """Run a complete sensitivity analysis cycle."""
        logger.info(f"🌫️  Gray System: Analysis cycle #{self.analysis_cycle_count}")
        
        # Mock project parameters to perturb
        projects_to_analyze = [
            {"id": "icd-dev", "name": "ICD Development", "parameters": ["capability_gaps", "priority_weights"]},
            {"id": "mission", "name": "Mission Analysis", "parameters": ["scenario_complexity", "environmental_factors"]},
            {"id": "cost", "name": "Cost Strategy", "parameters": ["budget_constraints", "risk_factors"]},
            {"id": "cdd-dev", "name": "CDD Development", "parameters": ["requirement_count", "specification_detail"]},
            {"id": "conops", "name": "CONOPS", "parameters": ["operational_complexity", "crew_requirements"]},
            {"id": "concept-a", "name": "Solution Concept A", "parameters": ["technical_risk", "performance_margins"]},
        ]
        
        for project in projects_to_analyze:
            sensitivity = self._analyze_project_sensitivity(project)
            self.project_sensitivity[project["id"]] = sensitivity
    
    def _analyze_project_sensitivity(self, project: Dict[str, Any]) -> SensitivityResult:
        """Analyze sensitivity for a specific project."""
        project_id = project["id"]
        project_name = project["name"]
        parameters = project["parameters"]
        
        # Simulate perturbation tests
        perturbation_tests = []
        impact_scores = []
        
        for param in parameters:
            # Simulate parameter perturbation
            perturbation = self._simulate_perturbation(param)
            perturbation_tests.append(perturbation)
            impact_scores.append(perturbation.impact_score)
        
        # Calculate overall sensitivity
        avg_impact = sum(impact_scores) / len(impact_scores) if impact_scores else 0
        
        # Determine sensitivity level
        if avg_impact > 0.7:
            sensitivity_level = "high"
            sensitivity_score = avg_impact
        elif avg_impact > 0.4:
            sensitivity_level = "medium" 
            sensitivity_score = avg_impact
        else:
            sensitivity_level = "low"
            sensitivity_score = avg_impact
        
        # Identify fragile parameters
        fragile_params = [test.parameter_name for test in perturbation_tests if test.impact_score > 0.6]
        
        # Generate stability indicators
        stability_indicators = {
            "requirement_stability": random.uniform(0.7, 0.95),
            "cost_stability": random.uniform(0.6, 0.9),
            "schedule_stability": random.uniform(0.65, 0.88),
            "technical_stability": random.uniform(0.75, 0.92)
        }
        
        # Generate recommendations
        recommendations = self._generate_recommendations(sensitivity_level, fragile_params)
        
        return SensitivityResult(
            project_id=project_id,
            project_name=project_name,
            sensitivity_level=sensitivity_level,
            sensitivity_score=sensitivity_score,
            fragile_parameters=fragile_params,
            stability_indicators=stability_indicators,
            recommendations=recommendations,
            analysis_timestamp=datetime.now()
        )
    
    def _simulate_perturbation(self, parameter_name: str) -> PerturbationTest:
        """Simulate perturbing a specific parameter."""
        # Mock original and perturbed values
        if "cost" in parameter_name.lower():
            original = 2.5e6
            perturbed = original * (1 + random.uniform(-0.3, 0.3))  # ±30% variation
            impact = abs(perturbed - original) / original
        elif "time" in parameter_name.lower() or "duration" in parameter_name.lower():
            original = 48  # hours
            perturbed = original * (1 + random.uniform(-0.2, 0.2))  # ±20% variation  
            impact = abs(perturbed - original) / original
        elif "range" in parameter_name.lower():
            original = 50  # nautical miles
            perturbed = original * (1 + random.uniform(-0.25, 0.25))  # ±25% variation
            impact = abs(perturbed - original) / original * 1.5  # Range changes have higher impact
        else:
            # Generic parameter
            original = 1.0
            perturbed = random.uniform(0.5, 1.5)
            impact = abs(perturbed - original) / original
        
        # Simulate cascade effects
        cascade_effects = []
        if impact > 0.2:
            if "cost" in parameter_name.lower():
                cascade_effects = ["Budget constraints tightened", "Alternative concepts needed"]
            elif "range" in parameter_name.lower():
                cascade_effects = ["Mission scenarios affected", "Concept performance impacted"]
            elif "duration" in parameter_name.lower():
                cascade_effects = ["Power requirements increased", "Cost implications"]
        
        return PerturbationTest(
            parameter_name=parameter_name,
            original_value=original,
            perturbed_value=perturbed,
            impact_score=min(impact, 1.0),  # Cap at 1.0
            cascade_effects=cascade_effects
        )
    
    def _generate_recommendations(self, sensitivity_level: str, fragile_params: List[str]) -> List[str]:
        """Generate recommendations based on sensitivity analysis."""
        recommendations = []
        
        if sensitivity_level == "high":
            recommendations.append("⚠️  High sensitivity detected - review critical assumptions")
            recommendations.append("Consider additional analysis to reduce uncertainty")
        elif sensitivity_level == "medium":
            recommendations.append("🔍 Monitor project for parameter changes")
            recommendations.append("Validate key assumptions")
        else:
            recommendations.append("✅ Project appears stable under perturbation")
        
        # Parameter-specific recommendations
        for param in fragile_params:
            if "cost" in param.lower():
                recommendations.append(f"💰 Monitor {param} - high cost sensitivity")
            elif "requirement" in param.lower():
                recommendations.append(f"📋 Stabilize {param} - requirements volatility risk")
            else:
                recommendations.append(f"🎯 Review {param} - parameter sensitivity detected")
        
        return recommendations
    
    def _assess_enterprise_health(self):
        """Assess overall enterprise health."""
        if not self.project_sensitivity:
            return
        
        # Calculate enterprise-wide metrics
        high_sensitivity_count = sum(1 for result in self.project_sensitivity.values() 
                                   if result.sensitivity_level == "high")
        
        total_projects = len(self.project_sensitivity)
        high_sensitivity_ratio = high_sensitivity_count / total_projects if total_projects > 0 else 0
        
        # Overall stability score
        avg_stability = sum(
            sum(result.stability_indicators.values()) / len(result.stability_indicators)
            for result in self.project_sensitivity.values()
        ) / total_projects if total_projects > 0 else 0.8
        
        # Enterprise health assessment
        if high_sensitivity_ratio > 0.4 or avg_stability < 0.7:
            health_status = "fragile"
            health_score = 0.6
        elif high_sensitivity_ratio > 0.2 or avg_stability < 0.8:
            health_status = "moderate"
            health_score = 0.75
        else:
            health_status = "stable"
            health_score = 0.9
        
        self.enterprise_health = {
            "status": health_status,
            "score": health_score,
            "high_sensitivity_ratio": high_sensitivity_ratio,
            "average_stability": avg_stability,
            "total_projects": total_projects,
            "assessment_time": datetime.now()
        }
        
        logger.info(f"🌫️  Enterprise Health: {health_status} (score: {health_score:.2f})")
    
    def get_current_sensitivity(self, project_id: str) -> Optional[SensitivityResult]:
        """Get current sensitivity analysis for a project."""
        return self.project_sensitivity.get(project_id)
    
    def get_enterprise_health(self) -> Dict[str, Any]:
        """Get current enterprise health assessment."""
        return self.enterprise_health.copy() if self.enterprise_health else {}
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of current Gray System analysis."""
        if not self.project_sensitivity:
            return {"status": "initializing"}
        
        sensitivity_counts = {"low": 0, "medium": 0, "high": 0}
        for result in self.project_sensitivity.values():
            sensitivity_counts[result.sensitivity_level] += 1
        
        return {
            "analysis_cycles": self.analysis_cycle_count,
            "projects_analyzed": len(self.project_sensitivity),
            "sensitivity_distribution": sensitivity_counts,
            "enterprise_health": self.enterprise_health,
            "last_analysis": max(
                (result.analysis_timestamp for result in self.project_sensitivity.values()),
                default=datetime.now()
            ).isoformat()
        }


# Global Gray System instance
_gray_system = MockGraySystem()


def get_gray_system() -> MockGraySystem:
    """Get the global Gray System instance."""
    return _gray_system


def start_gray_system():
    """Start the Gray System."""
    _gray_system.start_continuous_analysis()


def stop_gray_system():
    """Stop the Gray System."""
    _gray_system.stop_continuous_analysis()


if __name__ == "__main__":
    # Test Gray System independently
    print("🧪 Testing Mock Gray System...")
    
    gray_system = MockGraySystem()
    gray_system.start_continuous_analysis()
    
    try:
        # Run for 30 seconds
        time.sleep(30)
        
        # Show results
        summary = gray_system.get_analysis_summary()
        print(f"\n📊 Analysis Summary:")
        print(f"   Cycles completed: {summary['analysis_cycles']}")
        print(f"   Projects analyzed: {summary['projects_analyzed']}")
        print(f"   Sensitivity distribution: {summary['sensitivity_distribution']}")
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
    finally:
        gray_system.stop_continuous_analysis()
        print("✅ Gray System test complete")
