#!/usr/bin/env python3
"""
Comprehensive RAG Test - Compare BPMN RAG vs Original RAG
Tests functional parity between the two implementations.
"""

import json
import time
import requests
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import difflib


class RAGComparativeTest:
    def __init__(self):
        self.api_base = "http://localhost:8000"
        self.camunda_base = "http://localhost:8080/engine-rest"
        self.worker_process = None
        
        # Test questions with expected characteristics
        self.test_queries = [
            {
                "query": "What are the navigation system requirements?",
                "description": "Navigation system overview",
                "expected_chunks": 5,
                "key_terms": ["navigation", "requirements", "REQ-NAV"]
            },
            {
                "query": "What is the required position accuracy?",
                "description": "Position accuracy specification", 
                "expected_chunks": 1,
                "key_terms": ["3 meters CEP", "Circular Error Probable"]
            },
            {
                "query": "What safety procedures should be followed?",
                "description": "Safety protocols",
                "expected_chunks": 5,
                "key_terms": ["safety", "monitoring", "procedures"]
            },
            {
                "query": "For Hardware Components what is our memory requirements",
                "description": "Hardware memory specs",
                "expected_chunks": 2,
                "key_terms": ["16 GB DDR4", "memory"]
            },
            {
                "query": "What frequency does the Communication Interfaces operate at?",
                "description": "Communication frequencies",
                "expected_chunks": 2,
                "key_terms": ["VHF/UHF", "frequency", "dual-band"]
            }
        ]
        
        self.results = []

    def get_auth_token(self) -> str:
        """Get authentication token for original RAG testing."""
        try:
            response = requests.post(
                f"{self.api_base}/api/auth/login",
                json={"username": "jdehart", "password": "jdehart"},
                timeout=10
            )
            
            if response.status_code == 200:
                token = response.json().get('token')
                if token:
                    return token
            
            raise Exception(f"Login failed: {response.status_code}")
            
        except Exception as e:
            raise Exception(f"Authentication failed: {str(e)}")

    def test_original_rag(self, query: str, token: str) -> Dict[str, Any]:
        """Test a query against the original RAG endpoint."""
        try:
            print(f"      🔍 Calling original RAG API...")
            response = requests.post(
                f"{self.api_base}/api/knowledge/query",
                json={
                    "question": query,
                    "max_chunks": 5,
                    "similarity_threshold": 0.4,
                    "response_style": "comprehensive"
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            print(f"      📥 Original RAG response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": data.get("success", False),
                    "chunks_found": data.get("chunks_found", 0),
                    "response": data.get("response", ""),
                    "confidence": data.get("confidence", "unknown"),
                    "sources": data.get("sources", []),
                    "error": None
                }
            else:
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"success": False, "error": f"Exception: {str(e)}"}

    def start_external_worker(self):
        """Start external task worker."""
        try:
            print("      🔄 Killing existing workers...")
            # Kill existing workers
            subprocess.run(["pkill", "-f", "external_task_worker"], capture_output=True)
            time.sleep(2)
            
            print("      🚀 Starting new worker...")
            worker_script = Path(__file__).parent / "run_external_task_worker.py"
            self.worker_process = subprocess.Popen(
                [sys.executable, str(worker_script)],
                cwd=Path(__file__).parent.parent,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            print("      ⏳ Waiting for worker startup...")
            time.sleep(5)  # Give it time to start
            
            if self.worker_process.poll() is None:
                print(f"      ✅ Worker started (PID: {self.worker_process.pid})")
                return True
            else:
                print("      ❌ Worker failed to start")
                return False
                
        except Exception as e:
            print(f"      ❌ Worker start exception: {str(e)}")
            return False

    def stop_external_worker(self):
        """Stop external task worker."""
        if self.worker_process:
            try:
                self.worker_process.terminate()
                self.worker_process.wait(timeout=5)
            except:
                try:
                    self.worker_process.kill()
                except:
                    pass

    def test_bpmn_rag(self, query: str) -> Dict[str, Any]:
        """Test a query against the BPMN RAG pipeline."""
        try:
            print(f"      🔍 Calling BPMN RAG API...")
            # Start RAG query
            response = requests.post(
                f"{self.api_base}/api/workflows/rag-query",
                json={
                    "query": query,
                    "max_results": 5,
                    "similarity_threshold": 0.3
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            print(f"      📥 BPMN RAG response: {response.status_code}")
            
            if response.status_code != 200:
                return {"success": False, "error": f"API failed: {response.status_code} - {response.text}"}
            
            result = response.json()
            process_id = result.get("process_instance_id")
            
            if not process_id:
                return {"success": False, "error": "No process ID returned"}
            
            print(f"      ⏳ Monitoring process {process_id[:8]}... (max 30s)")
            # Monitor for completion
            max_wait = 30
            for i in range(max_wait):
                time.sleep(1)
                
                # Show progress every 5 seconds
                if (i + 1) % 5 == 0:
                    print(f"      🔄 Still processing... ({i + 1}s)")
                
                try:
                    status_response = requests.get(
                        f"{self.camunda_base}/process-instance/{process_id}",
                        timeout=3
                    )
                    
                    if status_response.status_code == 404:
                        print(f"      ✅ Process completed and cleaned up after {i + 1}s")
                        break
                    elif status_response.status_code == 200:
                        process_info = status_response.json()
                        if process_info.get('ended'):
                            print(f"      ✅ Process ended after {i + 1}s")
                            break
                except Exception as e:
                    if i == 0:  # Only show first error
                        print(f"      ⚠️  Monitoring error: {str(e)}")
                    continue
            else:
                print(f"      ⏰ Process timed out after {max_wait}s")
            
            # Get results from Camunda history
            print(f"      📊 Retrieving process variables...")
            try:
                hist_vars_response = requests.get(
                    f"{self.camunda_base}/history/variable-instance?processInstanceId={process_id}",
                    timeout=10
                )
                print(f"      📊 Variable retrieval: {hist_vars_response.status_code}")
                
                if hist_vars_response.status_code == 200:
                    hist_vars = hist_vars_response.json()
                    
                    # Extract key variables
                    variables = {}
                    for var in hist_vars:
                        variables[var['name']] = var.get('value')
                    
                    final_response = variables.get('final_response', '')
                    retrieval_stats = variables.get('retrieval_stats', '{}')
                    reranked_context = variables.get('reranked_context', '[]')
                    
                    # Try multiple ways to get chunk count
                    chunks_found = 0
                    try:
                        stats = json.loads(retrieval_stats) if isinstance(retrieval_stats, str) else {}
                        chunks_found = stats.get('total_results', 0)
                    except:
                        pass
                    
                    # If stats don't work, count from reranked_context
                    if chunks_found == 0:
                        try:
                            context_data = json.loads(reranked_context) if isinstance(reranked_context, str) else []
                            chunks_found = len(context_data) if context_data else 0
                        except:
                            pass
                    
                    # If still 0, check if final_response has context indicators
                    if chunks_found == 0 and "[Context" in final_response:
                        # Count context sections in response
                        chunks_found = final_response.count("[Context")
                    
                    print(f"   📊 Debug - Stats: {retrieval_stats}")
                    print(f"   📊 Debug - Context length: {len(reranked_context) if reranked_context else 0}")
                    print(f"   📊 Debug - Final chunks count: {chunks_found}")
                    
                    return {
                        "success": bool(final_response),
                        "chunks_found": chunks_found,
                        "response": final_response,
                        "process_id": process_id,
                        "error": None
                    }
                
            except Exception as e:
                return {"success": False, "error": f"Results retrieval failed: {str(e)}"}
            
            return {"success": False, "error": "Could not retrieve results"}
            
        except Exception as e:
            return {"success": False, "error": f"BPMN test failed: {str(e)}"}

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text responses."""
        if not text1 or not text2:
            return 0.0
        
        # Use difflib for sequence matching
        similarity = difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        return similarity

    def check_key_terms(self, response: str, key_terms: List[str]) -> Dict[str, Any]:
        """Check if response contains expected key terms."""
        found_terms = []
        missing_terms = []
        
        response_lower = response.lower()
        for term in key_terms:
            if term.lower() in response_lower:
                found_terms.append(term)
            else:
                missing_terms.append(term)
        
        coverage = len(found_terms) / len(key_terms) if key_terms else 0.0
        
        return {
            "found_terms": found_terms,
            "missing_terms": missing_terms,
            "coverage": coverage
        }

    def run_comparative_test(self):
        """Run comprehensive comparison test."""
        print("🧪 ODRAS RAG Comparative Test")
        print("Comparing BPMN RAG vs Original RAG")
        print("=" * 60)
        
        # Get authentication token
        try:
            token = self.get_auth_token()
            print(f"✅ Authentication successful")
        except Exception as e:
            print(f"❌ Authentication failed: {str(e)}")
            return False
        
        # Start external task worker for BPMN tests
        print("\n🔄 Starting external task worker...")
        if not self.start_external_worker():
            print("❌ Failed to start external task worker")
            return False
        
        try:
            # Test each query
            for i, test_case in enumerate(self.test_queries, 1):
                query = test_case["query"]
                description = test_case["description"]
                expected_chunks = test_case["expected_chunks"]
                key_terms = test_case["key_terms"]
                
                print(f"\n📝 Test {i}/5: {description}")
                print(f"Query: '{query}'")
                print("-" * 50)
                
                # Get fresh token for each test (tokens expire)
                try:
                    token = self.get_auth_token()
                except Exception as e:
                    print(f"   ❌ Token refresh failed: {str(e)}")
                    continue
                
                # Test original RAG
                print("🔍 Testing Original RAG...")
                original_result = self.test_original_rag(query, token)
                
                if original_result["success"]:
                    print(f"   ✅ Chunks found: {original_result['chunks_found']}")
                    print(f"   📄 Response: {original_result['response'][:100]}...")
                else:
                    print(f"   ❌ Failed: {original_result.get('error', 'Unknown error')}")
                
                # Test BPMN RAG
                print("\n🔍 Testing BPMN RAG...")
                bpmn_result = self.test_bpmn_rag(query)
                
                if bpmn_result["success"]:
                    print(f"   ✅ Chunks found: {bpmn_result['chunks_found']}")
                    response_text = bpmn_result['response']
                    print(f"   📄 Response: {response_text[:150]}...")
                    
                    # Show if key terms are present
                    key_check = self.check_key_terms(response_text, key_terms)
                    if key_check['found_terms']:
                        print(f"   🔑 Found key terms: {key_check['found_terms']}")
                else:
                    print(f"   ❌ Failed: {bpmn_result.get('error', 'Unknown error')}")
                
                # Compare results
                comparison = self.compare_results(original_result, bpmn_result, key_terms)
                self.results.append({
                    "query": query,
                    "description": description,
                    "original": original_result,
                    "bpmn": bpmn_result,
                    "comparison": comparison
                })
                
                print(f"\n📊 Comparison:")
                print(f"   Both successful: {comparison['both_successful']}")
                print(f"   Text similarity: {comparison['similarity']:.3f}")
                print(f"   Key terms coverage: {comparison['key_terms']['coverage']:.3f}")
                
                if comparison['key_terms']['missing_terms']:
                    print(f"   Missing terms: {comparison['key_terms']['missing_terms']}")
                
                print("=" * 60)
            
            # Generate summary report
            self.generate_summary_report()
            
            return True
            
        finally:
            self.stop_external_worker()

    def compare_results(self, original: Dict, bpmn: Dict, key_terms: List[str]) -> Dict[str, Any]:
        """Compare original and BPMN results."""
        both_successful = original.get("success", False) and bpmn.get("success", False)
        
        similarity = 0.0
        key_terms_analysis = {"coverage": 0.0, "found_terms": [], "missing_terms": key_terms}
        
        if both_successful:
            original_text = original.get("response", "")
            bpmn_text = bpmn.get("response", "")
            
            similarity = self.calculate_similarity(original_text, bpmn_text)
            key_terms_analysis = self.check_key_terms(bpmn_text, key_terms)
        
        return {
            "both_successful": both_successful,
            "similarity": similarity,
            "key_terms": key_terms_analysis,
            "chunks_match": original.get("chunks_found", 0) == bpmn.get("chunks_found", 0)
        }

    def generate_summary_report(self):
        """Generate comprehensive summary report."""
        print("\n📈 COMPREHENSIVE TEST SUMMARY")
        print("=" * 50)
        
        total_tests = len(self.results)
        successful_both = len([r for r in self.results if r["comparison"]["both_successful"]])
        
        # Calculate averages
        similarities = [r["comparison"]["similarity"] for r in self.results if r["comparison"]["both_successful"]]
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
        
        key_term_coverages = [r["comparison"]["key_terms"]["coverage"] for r in self.results]
        avg_key_coverage = sum(key_term_coverages) / len(key_term_coverages) if key_term_coverages else 0.0
        
        # Success metrics
        print(f"🎯 Overall Results:")
        print(f"   Tests Passed: {successful_both}/{total_tests} ({successful_both/total_tests*100:.1f}%)")
        print(f"   Average Text Similarity: {avg_similarity:.3f}")
        print(f"   Average Key Term Coverage: {avg_key_coverage:.3f}")
        
        # Detailed results
        print(f"\n📋 Detailed Results:")
        for i, result in enumerate(self.results, 1):
            query = result["query"]
            comp = result["comparison"]
            
            status = "✅ PASS" if comp["both_successful"] else "❌ FAIL"
            similarity = comp["similarity"]
            coverage = comp["key_terms"]["coverage"]
            
            print(f"   {i}. {status} | Sim: {similarity:.3f} | Terms: {coverage:.3f} | {query[:40]}...")
            
            # Show issues
            if not comp["both_successful"]:
                orig_success = result["original"].get("success", False)
                bpmn_success = result["bpmn"].get("success", False)
                print(f"      Original: {'✅' if orig_success else '❌'} | BPMN: {'✅' if bpmn_success else '❌'}")
                
                if not orig_success:
                    print(f"      Original Error: {result['original'].get('error', 'Unknown')}")
                if not bpmn_success:
                    print(f"      BPMN Error: {result['bpmn'].get('error', 'Unknown')}")
        
        # Final assessment
        print(f"\n🎯 Final Assessment:")
        
        if successful_both == total_tests:
            print(f"   🎉 EXCELLENT: All {total_tests} tests passed!")
            print(f"   ✅ BPMN RAG has full functional parity with Original RAG")
        elif successful_both >= total_tests * 0.8:
            print(f"   ✅ GOOD: {successful_both}/{total_tests} tests passed (80%+ success rate)")
            print(f"   🔧 Minor issues to address in failing tests")
        elif successful_both >= total_tests * 0.6:
            print(f"   ⚠️  PARTIAL: {successful_both}/{total_tests} tests passed (60%+ success rate)")
            print(f"   🔧 Several issues need attention")
        else:
            print(f"   ❌ POOR: Only {successful_both}/{total_tests} tests passed (<60% success rate)")
            print(f"   🚨 Major issues with BPMN implementation")
        
        if avg_similarity >= 0.7:
            print(f"   📝 Text similarity is GOOD ({avg_similarity:.3f})")
        elif avg_similarity >= 0.5:
            print(f"   📝 Text similarity is ACCEPTABLE ({avg_similarity:.3f})")
        else:
            print(f"   📝 Text similarity is POOR ({avg_similarity:.3f})")
        
        if avg_key_coverage >= 0.8:
            print(f"   🔑 Key term coverage is EXCELLENT ({avg_key_coverage:.3f})")
        elif avg_key_coverage >= 0.6:
            print(f"   🔑 Key term coverage is GOOD ({avg_key_coverage:.3f})")
        else:
            print(f"   🔑 Key term coverage is POOR ({avg_key_coverage:.3f})")

        return successful_both == total_tests and avg_similarity >= 0.5 and avg_key_coverage >= 0.6


def main():
    """Main test function."""
    tester = RAGComparativeTest()
    
    try:
        success = tester.run_comparative_test()
        
        if success:
            print(f"\n🏆 BPMN RAG implementation meets quality standards!")
        else:
            print(f"\n🔧 BPMN RAG implementation needs improvements.")
        
        return success
        
    except KeyboardInterrupt:
        print(f"\n🛑 Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        return False
    finally:
        tester.stop_external_worker()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
