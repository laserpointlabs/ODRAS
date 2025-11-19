#!/usr/bin/env python3
"""
Comprehensive IRI Testing for ODRAS
Tests all IRI patterns, parsing, and validation across different tenant contexts.
"""

import os
import sys
import logging
from typing import Dict, List

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.config import Settings
from services.db import DatabaseService
from services.unified_iri_service import UnifiedIRIService, create_tenant_context

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IRIComprehensiveTester:
    """Comprehensive IRI testing across all patterns and tenant contexts"""
    
    def __init__(self):
        self.settings = Settings()
        self.db_service = DatabaseService(self.settings)
        self.test_cases = []
        self.failures = []
        
    def run_tests(self):
        """Run all comprehensive IRI tests"""
        logger.info("🧪 Starting Comprehensive IRI Testing")
        
        try:
            # Test 1: System Tenant IRIs
            logger.info("\n=== Test 1: System Tenant IRI Patterns ===")
            self.test_system_tenant_iris()
            
            # Test 2: Custom Tenant IRIs  
            logger.info("\n=== Test 2: Custom Tenant IRI Patterns ===")
            self.test_custom_tenant_iris()
            
            # Test 3: IRI Parsing and Component Extraction
            logger.info("\n=== Test 3: IRI Parsing and Component Extraction ===")
            self.test_iri_parsing()
            
            # Test 4: IRI Validation and Compliance
            logger.info("\n=== Test 4: IRI Validation and Compliance ===")
            self.test_iri_validation()
            
            # Test 5: Edge Cases and Error Handling
            logger.info("\n=== Test 5: Edge Cases and Error Handling ===")
            self.test_iri_edge_cases()
            
            # Test 6: Cross-Resource IRI Consistency
            logger.info("\n=== Test 6: Cross-Resource IRI Consistency ===")
            self.test_cross_resource_consistency()
            
            # Report results
            self.report_results()
            
        except Exception as e:
            logger.error(f"❌ IRI test failed: {e}")
            raise
    
    def test_system_tenant_iris(self):
        """Test IRI patterns for system tenant"""
        # System tenant context
        system_tenant = create_tenant_context(
            tenant_id="00000000-0000-0000-0000-000000000000",
            tenant_code="system",
            tenant_name="System Resources",
            base_iri="https://system.odras.local"
        )
        
        iri_service = UnifiedIRIService(system_tenant)
        
        # Test all resource types
        project_id = "abc-123-def-456"
        
        test_cases = [
            ("Project IRI", iri_service.generate_project_iri(project_id), 
             "https://system.odras.local/projects/abc-123-def-456/"),
            
            ("Ontology IRI", iri_service.generate_ontology_iri(project_id, "Requirements"),
             "https://system.odras.local/projects/abc-123-def-456/ontologies/requirements"),
             
            ("Knowledge IRI", iri_service.generate_knowledge_iri(project_id, "asset-789"),
             "https://system.odras.local/projects/abc-123-def-456/knowledge/asset-789"),
             
            ("File IRI", iri_service.generate_file_iri(project_id, "doc-123"),
             "https://system.odras.local/projects/abc-123-def-456/files/doc-123"),
             
            ("User IRI", iri_service.generate_user_iri("jdehart"),
             "https://system.odras.local/users/jdehart"),
             
            ("Requirement IRI", iri_service.generate_requirement_iri(project_id, "req-456"),
             "https://system.odras.local/projects/abc-123-def-456/requirements/req-456"),
             
            ("DAS IRI", iri_service.generate_das_iri("personas", "analyst-1"),
             "https://system.odras.local/das/personas/analyst-1"),
             
            ("Ontology Entity IRI", iri_service.generate_ontology_entity_iri(project_id, "Requirements", "Requirement"),
             "https://system.odras.local/projects/abc-123-def-456/ontologies/requirements#requirement")
        ]
        
        for test_name, actual, expected in test_cases:
            if actual == expected:
                logger.info(f"✓ {test_name}: {actual}")
                self.test_cases.append((test_name, "PASS", actual))
            else:
                logger.error(f"❌ {test_name}: Expected {expected}, got {actual}")
                self.failures.append((test_name, expected, actual))
    
    def test_custom_tenant_iris(self):
        """Test IRI patterns for custom tenants"""
        # Navy tenant context
        navy_tenant = create_tenant_context(
            tenant_id="navy-tenant-uuid",
            tenant_code="usn-adt",
            tenant_name="USN ADT",
            base_iri="https://odras.navy.mil/usn-adt"
        )
        
        iri_service = UnifiedIRIService(navy_tenant)
        project_id = "se-analysis-project"
        
        test_cases = [
            ("Navy Project IRI", iri_service.generate_project_iri(project_id),
             "https://odras.navy.mil/usn-adt/projects/se-analysis-project/"),
             
            ("Navy Ontology IRI", iri_service.generate_ontology_iri(project_id, "Systems Engineering"),
             "https://odras.navy.mil/usn-adt/projects/se-analysis-project/ontologies/systems-engineering"),
             
            ("Navy User IRI", iri_service.generate_user_iri("captain.smith"),
             "https://odras.navy.mil/usn-adt/users/captainsmith"),  # Dots removed by sanitization
             
            ("Navy Knowledge IRI", iri_service.generate_knowledge_iri(project_id, "requirement-doc-v2"),
             "https://odras.navy.mil/usn-adt/projects/se-analysis-project/knowledge/requirement-doc-v2")
        ]
        
        # Air Force tenant context
        usaf_tenant = create_tenant_context(
            tenant_id="usaf-tenant-uuid",
            tenant_code="afit-research", 
            tenant_name="AFIT Research",
            base_iri="https://research.afit.edu/afit-research"
        )
        
        iri_service_usaf = UnifiedIRIService(usaf_tenant)
        
        test_cases.extend([
            ("USAF Project IRI", iri_service_usaf.generate_project_iri(project_id),
             "https://research.afit.edu/afit-research/projects/se-analysis-project/"),
             
            ("USAF User IRI", iri_service_usaf.generate_user_iri("dr.researcher"),
             "https://research.afit.edu/afit-research/users/drresearcher")  # Dots removed by sanitization
        ])
        
        for test_name, actual, expected in test_cases:
            if actual == expected:
                logger.info(f"✓ {test_name}: {actual}")
                self.test_cases.append((test_name, "PASS", actual))
            else:
                logger.error(f"❌ {test_name}: Expected {expected}, got {actual}")
                self.failures.append((test_name, expected, actual))
    
    def test_iri_parsing(self):
        """Test IRI parsing and component extraction"""
        # Test different tenant contexts
        tenants = [
            create_tenant_context("sys", "system", "System", "https://system.odras.local"),
            create_tenant_context("navy", "usn-adt", "USN ADT", "https://odras.navy.mil/usn-adt"),
            create_tenant_context("usaf", "afit-research", "AFIT", "https://research.afit.edu/afit-research")
        ]
        
        for tenant_context in tenants:
            iri_service = UnifiedIRIService(tenant_context)
            
            # Generate IRIs to test parsing
            project_id = "test-project-123"
            project_iri = iri_service.generate_project_iri(project_id)
            ontology_iri = iri_service.generate_ontology_iri(project_id, "Test Ontology")
            user_iri = iri_service.generate_user_iri("test.user")
            
            # Test project IRI parsing
            components = iri_service.parse_iri_components(project_iri)
            if components.get("tenant_code") == tenant_context.tenant_code:
                logger.info(f"✓ {tenant_context.tenant_code} project IRI parsing works")
                self.test_cases.append((f"{tenant_context.tenant_code} Project Parsing", "PASS", project_iri))
            else:
                logger.error(f"❌ {tenant_context.tenant_code} project IRI parsing failed: {components}")
                self.failures.append((f"{tenant_context.tenant_code} Project Parsing", tenant_context.tenant_code, components.get("tenant_code")))
            
            # Test ontology IRI parsing
            ont_components = iri_service.parse_iri_components(ontology_iri)
            if ont_components.get("resource_type") == "ontologies":
                logger.info(f"✓ {tenant_context.tenant_code} ontology IRI parsing works")
                self.test_cases.append((f"{tenant_context.tenant_code} Ontology Parsing", "PASS", ontology_iri))
            else:
                logger.error(f"❌ {tenant_context.tenant_code} ontology IRI parsing failed")
                self.failures.append((f"{tenant_context.tenant_code} Ontology Parsing", "ontologies", ont_components.get("resource_type")))
            
            # Test user IRI parsing  
            user_components = iri_service.parse_iri_components(user_iri)
            if user_components.get("resource_type") == "user":
                logger.info(f"✓ {tenant_context.tenant_code} user IRI parsing works")
                self.test_cases.append((f"{tenant_context.tenant_code} User Parsing", "PASS", user_iri))
            else:
                logger.error(f"❌ {tenant_context.tenant_code} user IRI parsing failed")
                self.failures.append((f"{tenant_context.tenant_code} User Parsing", "user", user_components.get("resource_type")))
    
    def test_iri_validation(self):
        """Test IRI validation and compliance checking"""
        # Valid tenant contexts
        valid_contexts = [
            create_tenant_context("valid1", "navy-test", "Navy Test", "https://test.navy.mil/navy-test"),
            create_tenant_context("valid2", "usaf-research", "USAF Research", "https://research.usaf.mil/usaf-research"),
            create_tenant_context("valid3", "industry-partner", "Industry Partner", "https://partner.example.com/industry-partner")
        ]
        
        for context in valid_contexts:
            iri_service = UnifiedIRIService(context)
            issues = iri_service.validate_tenant_iri_compliance()
            
            if len(issues) == 0:
                logger.info(f"✓ {context.tenant_code} IRI validation passes")
                self.test_cases.append((f"{context.tenant_code} Validation", "PASS", "No issues"))
            else:
                logger.warning(f"⚠ {context.tenant_code} validation issues: {issues}")
                # Not necessarily a failure, might be expected warnings
        
        # Invalid tenant contexts (should have validation issues)
        invalid_contexts = [
            create_tenant_context("inv1", "invalid_code", "Invalid", "http://insecure.example.com/invalid_code"),  # HTTP not HTTPS
            create_tenant_context("inv2", "a", "Short", "https://test.com/a"),  # Too short
            create_tenant_context("inv3", "system", "Reserved", "https://test.com/system")  # Reserved word
        ]
        
        for context in invalid_contexts:
            iri_service = UnifiedIRIService(context)
            issues = iri_service.validate_tenant_iri_compliance()
            
            if len(issues) > 0:
                logger.info(f"✓ {context.tenant_code} correctly flagged validation issues: {len(issues)}")
                self.test_cases.append((f"{context.tenant_code} Invalid Detection", "PASS", f"{len(issues)} issues"))
            else:
                logger.error(f"❌ {context.tenant_code} should have validation issues but passed")
                self.failures.append((f"{context.tenant_code} Invalid Detection", "> 0 issues", "0 issues"))
    
    def test_iri_edge_cases(self):
        """Test edge cases in IRI generation"""
        tenant_context = create_tenant_context(
            "edge", "edge-test", "Edge Test", "https://edge.test.com/edge-test"
        )
        iri_service = UnifiedIRIService(tenant_context)
        
        edge_cases = [
            # Special characters in names
            ("Special chars in ontology", "Test Ontology with Spaces & Symbols!@#", "test-ontology-with-spaces-symbols"),
            ("Underscores in name", "Test_Ontology_With_Underscores", "test-ontology-with-underscores"),
            ("Empty name", "", "unnamed"),
            ("Numbers in name", "Ontology123Test", "ontology123test"),
            ("Multiple spaces", "Test   Multiple    Spaces", "test-multiple-spaces"),
            ("Leading/trailing spaces", "  Test Ontology  ", "test-ontology"),
            ("Only special chars", "!@#$%^&*()", "unnamed"),
            ("Mixed case", "TestOntologyMixedCase", "testontologymixedcase")
        ]
        
        for test_name, input_name, expected_sanitized in edge_cases:
            # Test with ontology IRI generation
            ontology_iri = iri_service.generate_ontology_iri("test-project", input_name)
            expected_iri = f"https://edge.test.com/edge-test/projects/test-project/ontologies/{expected_sanitized}"
            
            if ontology_iri == expected_iri:
                logger.info(f"✓ {test_name}: '{input_name}' → {expected_sanitized}")
                self.test_cases.append((test_name, "PASS", expected_sanitized))
            else:
                logger.error(f"❌ {test_name}: '{input_name}' → Expected {expected_iri}, got {ontology_iri}")
                self.failures.append((test_name, expected_iri, ontology_iri))
    
    def test_cross_resource_consistency(self):
        """Test that IRIs are consistent across different resource types for same project"""
        tenant_context = create_tenant_context(
            "consistency", "test-org", "Test Org", "https://test.example.com/test-org"
        )
        iri_service = UnifiedIRIService(tenant_context)
        
        project_id = "consistency-test-project"
        base_expected = f"https://test.example.com/test-org/projects/{project_id}/"
        
        # Generate IRIs for different resource types
        project_iri = iri_service.generate_project_iri(project_id)
        ontology_iri = iri_service.generate_ontology_iri(project_id, "TestOntology")
        knowledge_iri = iri_service.generate_knowledge_iri(project_id, "knowledge-asset")
        file_iri = iri_service.generate_file_iri(project_id, "test-file")
        requirement_iri = iri_service.generate_requirement_iri(project_id, "req-001")
        
        # All should have the same project base
        iris_to_check = [
            ("Project", project_iri, base_expected),
            ("Ontology", ontology_iri, f"{base_expected}ontologies/testontology"),
            ("Knowledge", knowledge_iri, f"{base_expected}knowledge/knowledge-asset"),
            ("File", file_iri, f"{base_expected}files/test-file"),
            ("Requirement", requirement_iri, f"{base_expected}requirements/req-001")
        ]
        
        all_consistent = True
        for resource_type, actual_iri, expected_iri in iris_to_check:
            if actual_iri == expected_iri:
                logger.info(f"✓ {resource_type} IRI consistent: {actual_iri}")
                self.test_cases.append((f"Consistency {resource_type}", "PASS", actual_iri))
            else:
                logger.error(f"❌ {resource_type} IRI inconsistent: {actual_iri} vs {expected_iri}")
                self.failures.append((f"Consistency {resource_type}", expected_iri, actual_iri))
                all_consistent = False
        
        # Test that all project-based IRIs start with the same project base
        project_base = project_iri
        for resource_type, actual_iri, _ in iris_to_check[1:]:  # Skip project itself
            if actual_iri.startswith(project_base):
                logger.info(f"✓ {resource_type} IRI uses correct project base")
            else:
                logger.error(f"❌ {resource_type} IRI doesn't use project base: {actual_iri}")
                all_consistent = False
        
        if all_consistent:
            self.test_cases.append(("Cross-Resource Consistency", "PASS", "All IRIs consistent"))
        else:
            self.failures.append(("Cross-Resource Consistency", "All consistent", "Some inconsistent"))
    
    def test_iri_parsing(self):
        """Test parsing IRIs back into components"""
        tenant_context = create_tenant_context(
            "parsing", "parse-test", "Parse Test", "https://parse.test.com/parse-test"
        )
        iri_service = UnifiedIRIService(tenant_context)
        
        # Generate test IRIs (use proper UUID format)
        project_id = "12345678-1234-1234-1234-123456789abc"
        test_iris = {
            "project": iri_service.generate_project_iri(project_id),
            "ontology": iri_service.generate_ontology_iri(project_id, "TestOntology"),
            "knowledge": iri_service.generate_knowledge_iri(project_id, "test-knowledge"),
            "file": iri_service.generate_file_iri(project_id, "test-file"),
            "user": iri_service.generate_user_iri("test-user"),
            "das": iri_service.generate_das_iri("tools", "test-tool")
        }
        
        for resource_type, test_iri in test_iris.items():
            components = iri_service.parse_iri_components(test_iri)
            
            # Verify tenant extraction
            if components.get("tenant_code") == "parse-test":
                logger.info(f"✓ {resource_type} IRI tenant parsing: {test_iri}")
                self.test_cases.append((f"Parse {resource_type} Tenant", "PASS", "parse-test"))
            else:
                logger.error(f"❌ {resource_type} IRI tenant parsing failed: {components}")
                self.failures.append((f"Parse {resource_type} Tenant", "parse-test", components.get("tenant_code")))
            
            # Verify project extraction (where applicable)
            if resource_type in ["project", "ontology", "knowledge", "file"]:
                if components.get("project_id"):
                    logger.info(f"✓ {resource_type} IRI project extraction")
                    self.test_cases.append((f"Parse {resource_type} Project", "PASS", components.get("project_id")))
                else:
                    logger.error(f"❌ {resource_type} IRI project extraction failed: {components}")
                    self.failures.append((f"Parse {resource_type} Project", project_id, components.get("project_id")))
    
    def test_iri_validation(self):
        """Test IRI format validation"""
        # Test various tenant configurations
        test_configs = [
            # Valid configurations
            ("valid-https", "test-valid", "Valid Test", "https://valid.example.com/test-valid", 0),
            ("valid-gov", "gov-test", "Gov Test", "https://test.gov/gov-test", 0),
            ("valid-mil", "mil-test", "Mil Test", "https://test.mil/mil-test", 0),
            
            # Invalid configurations (should have issues)
            ("invalid-http", "http-test", "HTTP Test", "http://insecure.example.com/http-test", 1),  # HTTP not HTTPS
            ("invalid-short", "ab", "Short", "https://test.com/ab", 1),  # Too short
            ("invalid-long", "a" * 60, "Long", f"https://test.com/{'a' * 60}", 1),  # Too long
            ("invalid-reserved", "admin", "Admin", "https://test.com/admin", 1),  # Reserved word
        ]
        
        for test_name, tenant_code, tenant_name, base_iri, expected_issue_count in test_configs:
            try:
                tenant_context = create_tenant_context("test", tenant_code, tenant_name, base_iri)
                iri_service = UnifiedIRIService(tenant_context)
                issues = iri_service.validate_tenant_iri_compliance()
                
                if len(issues) == expected_issue_count:
                    logger.info(f"✓ {test_name} validation correct: {len(issues)} issues")
                    self.test_cases.append((f"Validation {test_name}", "PASS", f"{len(issues)} issues"))
                else:
                    logger.error(f"❌ {test_name} validation: Expected {expected_issue_count} issues, got {len(issues)}")
                    self.failures.append((f"Validation {test_name}", f"{expected_issue_count} issues", f"{len(issues)} issues"))
                    
            except ValueError as e:
                # Some validation happens at creation time
                if expected_issue_count > 0:
                    logger.info(f"✓ {test_name} correctly rejected at creation: {e}")
                    self.test_cases.append((f"Creation Validation {test_name}", "PASS", "Rejected"))
                else:
                    logger.error(f"❌ {test_name} incorrectly rejected: {e}")
                    self.failures.append((f"Creation Validation {test_name}", "Accepted", "Rejected"))
    
    def report_results(self):
        """Report comprehensive test results"""
        total_tests = len(self.test_cases) + len(self.failures)
        passed_tests = len(self.test_cases)
        failed_tests = len(self.failures)
        
        logger.info(f"\n📊 IRI TESTING SUMMARY:")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        
        if failed_tests > 0:
            logger.error(f"\n❌ FAILURES ({failed_tests}):")
            for test_name, expected, actual in self.failures:
                logger.error(f"  {test_name}: Expected '{expected}', got '{actual}'")
            raise AssertionError(f"{failed_tests} IRI tests failed")
        else:
            logger.info(f"\n✅ ALL {passed_tests} IRI TESTS PASSED!")


def main():
    """Main test runner"""
    tester = IRIComprehensiveTester()
    
    try:
        tester.run_tests()
        print("\n🎉 All IRI tests passed! IRI implementation is working correctly.")
        
    except Exception as e:
        print(f"\n❌ IRI tests failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
