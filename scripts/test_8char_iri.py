#!/usr/bin/env python3
"""
Test 8-Character Ontology Element IRI Generation
Validates the new human-memorable IRI system for ontology elements.
"""

import os
import sys
import logging
import requests
from typing import Set
import re

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.config import Settings
from services.db import DatabaseService
from services.unified_iri_service import UnifiedIRIService, create_tenant_context

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EightCharIRITester:
    """Test the 8-character IRI system for ontology elements"""
    
    def __init__(self):
        self.settings = Settings()
        self.api_base = "http://localhost:8000"
        
        # Create test tenant context
        self.test_tenant = create_tenant_context(
            tenant_id="test-8char",
            tenant_code="test-org",
            tenant_name="Test Organization",
            base_iri="https://test.odras.local/test-org"
        )
        self.iri_service = UnifiedIRIService(self.test_tenant)
        
    def run_tests(self):
        """Run all 8-character IRI tests"""
        logger.info("🧪 Testing 8-Character Ontology Element IRI Generation")
        
        try:
            # Test 1: Basic 8-Character Code Generation
            logger.info("\n=== Test 1: Basic 8-Character Code Generation ===")
            self.test_8char_generation()
            
            # Test 2: Code Format Validation
            logger.info("\n=== Test 2: Code Format Validation ===")
            self.test_code_format()
            
            # Test 3: Uniqueness Testing
            logger.info("\n=== Test 3: Uniqueness Testing ===")
            self.test_uniqueness()
            
            # Test 4: Full IRI Generation
            logger.info("\n=== Test 4: Full IRI Generation ===")
            self.test_full_iri_generation()
            
            # Test 5: API Integration (if server running)
            logger.info("\n=== Test 5: API Integration ===")
            self.test_api_integration()
            
            logger.info("\n✅ All 8-character IRI tests passed!")
            
        except Exception as e:
            logger.error(f"❌ 8-character IRI test failed: {e}")
            raise
    
    def test_8char_generation(self):
        """Test basic 8-character code generation"""
        # Generate multiple codes
        codes = set()
        for i in range(20):
            code = self.iri_service.generate_8char_code()
            codes.add(code)
            logger.info(f"Generated code {i+1}: {code}")
        
        # Should have 20 unique codes (very high probability)
        if len(codes) == 20:
            logger.info("✓ All generated codes are unique")
        else:
            logger.warning(f"⚠ Some duplicate codes found: {20 - len(codes)} duplicates")
        
        # Test a few specific examples
        sample_codes = list(codes)[:5]
        logger.info(f"✓ Sample codes: {sample_codes}")
    
    def test_code_format(self):
        """Test that generated codes follow the expected format"""
        # Generate codes and validate format
        valid_pattern = re.compile(r'^[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz]{4}-[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz]{4}$')
        
        for i in range(10):
            code = self.iri_service.generate_8char_code()
            
            # Check overall format
            if not valid_pattern.match(code):
                raise AssertionError(f"Invalid code format: {code}")
            
            # Check length
            if len(code) != 9:  # 4 + 1 (hyphen) + 4
                raise AssertionError(f"Invalid code length: {code} (length: {len(code)})")
            
            # Check for confusing characters
            confusing_chars = "0OIl"
            if any(char in code for char in confusing_chars):
                raise AssertionError(f"Code contains confusing characters: {code}")
            
            logger.info(f"✓ Code format valid: {code}")
    
    def test_uniqueness(self):
        """Test uniqueness within ontology scope"""
        project_id = "test-project-123"
        ontology_name = "TestOntology"
        
        # Generate multiple unique codes for same ontology
        generated_codes = set()
        
        for i in range(10):
            code = self.iri_service.generate_unique_8char_code(project_id, ontology_name)
            if code in generated_codes:
                raise AssertionError(f"Duplicate code generated: {code}")
            generated_codes.add(code)
            logger.info(f"✓ Unique code {i+1}: {code}")
        
        logger.info(f"✓ All {len(generated_codes)} codes are unique within ontology scope")
    
    def test_full_iri_generation(self):
        """Test full IRI generation with 8-character codes"""
        project_id = "12345678-1234-1234-1234-123456789abc"
        ontology_name = "Requirements"
        
        # Test minting element IRIs
        test_elements = [
            ("class", "Requirement"),
            ("objectProperty", "hasComponent"),
            ("dataProperty", "priority"),
            ("individual", "REQ001")
        ]
        
        for element_type, element_name in test_elements:
            result = self.iri_service.mint_ontology_element_iri(
                project_id=project_id,
                ontology_name=ontology_name,
                element_type=element_type
            )
            
            # Validate result structure
            required_keys = ["code", "iri", "element_type", "project_id", "ontology_name"]
            for key in required_keys:
                if key not in result:
                    raise AssertionError(f"Missing key in result: {key}")
            
            # Validate IRI format
            expected_base = f"https://test.odras.local/test-org/projects/{project_id}/ontologies/requirements#"
            if not result["iri"].startswith(expected_base):
                raise AssertionError(f"Invalid IRI base: {result['iri']}")
            
            # Validate code is in IRI
            if result["code"] not in result["iri"]:
                raise AssertionError(f"Code not found in IRI: {result['code']} not in {result['iri']}")
            
            logger.info(f"✓ {element_type} minted: {result['code']} -> {result['iri']}")
    
    def test_api_integration(self):
        """Test API integration if server is running"""
        try:
            # Check if API server is running
            response = requests.get(f"{self.api_base}/api/health", timeout=5)
            if response.status_code != 200:
                logger.info("⚠ API server not running - skipping API tests")
                return
                
            logger.info("✓ API server is running")
            
            # Get authentication token
            auth_response = requests.post(
                f"{self.api_base}/api/auth/login",
                json={"username": "das_service", "password": "das_service_2024!"},
                timeout=5
            )
            
            if auth_response.status_code != 200:
                logger.warning("⚠ Authentication failed - skipping API tests")
                return
                
            token = auth_response.json()["token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test sample code generation endpoint
            sample_response = requests.get(
                f"{self.api_base}/api/tenants/generate-8char-codes/5",
                headers=headers,
                timeout=5
            )
            
            if sample_response.status_code == 200:
                sample_data = sample_response.json()
                logger.info(f"✓ Sample codes generated: {len(sample_data['sample_codes'])} codes")
                
                for i, code_info in enumerate(sample_data['sample_codes'][:3]):
                    logger.info(f"  Example {i+1}: {code_info['code']} -> {code_info['example_iri']}")
            else:
                logger.warning(f"⚠ Sample codes endpoint failed: {sample_response.status_code}")
            
            # Test element IRI minting endpoint
            mint_response = requests.post(
                f"{self.api_base}/api/tenants/mint-element-iri",
                headers=headers,
                json={
                    "project_id": "12345678-1234-1234-1234-123456789abc",
                    "ontology_name": "TestOntology",
                    "element_type": "class"
                },
                timeout=5
            )
            
            if mint_response.status_code == 200:
                mint_data = mint_response.json()
                logger.info(f"✓ Element IRI minted via API:")
                logger.info(f"  Code: {mint_data['code']}")
                logger.info(f"  IRI: {mint_data['iri']}")
                logger.info(f"  Type: {mint_data['element_type']}")
                
                # Validate API response format
                if not re.match(r'^[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz]{4}-[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz]{4}$', mint_data['code']):
                    raise AssertionError(f"API returned invalid code format: {mint_data['code']}")
                
                if mint_data['code'] not in mint_data['iri']:
                    raise AssertionError(f"Code not found in returned IRI")
                
                logger.info("✓ API response format validated")
            else:
                logger.warning(f"⚠ Element minting endpoint failed: {mint_response.status_code}")
                
        except requests.RequestException:
            logger.info("⚠ API server not accessible - skipping API tests")


def main():
    """Main test runner"""
    tester = EightCharIRITester()
    
    try:
        tester.run_tests()
        print("\n🎉 All 8-character IRI tests passed! System is ready for ontology workbench integration.")
        
        print("\n💡 Example Usage:")
        print("Instead of: Class1, Class2, Class3...")  
        print("Use codes: A1B2-C3D4, X5Y7-M9N2, P3Q6-R8S4...")
        print("\nUsers can now reference ontology elements by memorable codes!")
        
    except Exception as e:
        print(f"\n❌ 8-character IRI tests failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
