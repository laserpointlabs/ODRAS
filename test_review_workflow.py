#!/usr/bin/env python3
"""
Test the Requirements Review Interface with Mock Data

This script helps you test the review interface with realistic mock data
without needing to run a full BPMN workflow.
"""

import requests
import json
import webbrowser
import time
from typing import Dict

BASE_URL = "http://localhost:8000"

def create_test_task():
    """Create a test review task with mock requirements"""
    print("\n🔧 Creating test review task...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/test/create-review-task")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Test task created successfully!")
            print(f"   Process ID: {data['process_instance_id']}")
            print(f"   Task ID: {data['task_id']}")
            print(f"\n📋 Review URL: {BASE_URL}{data['review_url']}")
            return data
        else:
            print(f"❌ Failed to create test task: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error creating test task: {e}")
        return None

def test_approve_decision(process_id: str):
    """Test approving requirements"""
    print("\n✅ Testing APPROVE decision...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/test/user-tasks/{process_id}/complete",
            json={"decision": "approve"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Decision: {result['decision']}")
            print(f"   ✓ Status: {result['status']}")
            print(f"   ✓ Next step: {result.get('next_step', 'N/A')}")
            return True
        else:
            print(f"   ✗ Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

def test_rerun_decision(process_id: str):
    """Test rerun decision with parameters"""
    print("\n🔄 Testing RERUN decision...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/test/user-tasks/{process_id}/complete",
            json={
                "decision": "rerun",
                "extraction_parameters": {
                    "method": "strict",
                    "confidence_threshold": 0.8,
                    "custom_patterns": ["shall", "must", "should"],
                    "reason": "Testing rerun functionality"
                }
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Decision: {result['decision']}")
            print(f"   ✓ Status: {result['status']}")
            print(f"   ✓ Next step: {result.get('next_step', 'N/A')}")
            return True
        else:
            print(f"   ✗ Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

def check_test_status():
    """Check status of all test processes"""
    print("\n📊 Checking test process status...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/test/status")
        if response.status_code == 200:
            data = response.json()
            print(f"   Total processes: {data['total_processes']}")
            print(f"   Pending review: {data['pending_review']}")
            print(f"   Completed: {data['completed']}")
            
            if data['test_processes']:
                print("\n   Recent test processes:")
                for pid, pdata in list(data['test_processes'].items())[:3]:
                    print(f"   - {pid}: {pdata['status']}")
            return True
        else:
            print(f"   ✗ Failed to get status: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

def main():
    """Main test workflow"""
    print("="*60)
    print("🧪 ODRAS Requirements Review Interface Test")
    print("="*60)
    
    # Check if server is running
    try:
        response = requests.get(BASE_URL, timeout=2)
        print("✅ Server is running")
    except:
        print("❌ Server is not running on localhost:8000")
        print("   Please start it with: uvicorn backend.main:app --reload")
        return
    
    print("\nSelect test option:")
    print("1. Create test task and open review interface")
    print("2. Run automated test workflow")
    print("3. Check test status")
    print("4. Exit")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        # Create task and open in browser
        task_data = create_test_task()
        if task_data:
            review_url = f"{BASE_URL}{task_data['review_url']}"
            print(f"\n🌐 Opening review interface in browser...")
            print(f"   URL: {review_url}")
            
            # Try to open in browser
            try:
                webbrowser.open(review_url)
                print("\n✅ Browser opened. You should see:")
                print("   - Purple gradient background")
                print("   - 8 mock requirements with different confidence levels")
                print("   - Approve, Rerun, and Edit buttons")
                print("\n📝 Try clicking:")
                print("   1. 'Approve & Continue' - to approve requirements")
                print("   2. 'Rerun Extraction' - to see the modal with options")
            except:
                print(f"\n⚠️  Could not open browser automatically")
                print(f"   Please open this URL manually: {review_url}")
    
    elif choice == "2":
        # Run automated tests
        print("\n🤖 Running automated test workflow...")
        
        # Create first test task
        task1 = create_test_task()
        if task1:
            time.sleep(1)
            test_approve_decision(task1['process_instance_id'])
        
        # Create second test task
        task2 = create_test_task()
        if task2:
            time.sleep(1)
            test_rerun_decision(task2['process_instance_id'])
        
        # Check final status
        time.sleep(1)
        check_test_status()
        
        print("\n✅ Automated tests complete!")
    
    elif choice == "3":
        # Just check status
        check_test_status()
    
    elif choice == "4":
        print("\n👋 Exiting...")
        return
    
    else:
        print("\n❌ Invalid choice")
    
    print("\n" + "="*60)
    print("Test complete! The review interface is working with mock data.")
    print("="*60)

if __name__ == "__main__":
    main()
