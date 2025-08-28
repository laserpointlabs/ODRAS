#!/usr/bin/env python3
"""
Test the complete database cleaning workflow.
"""
import subprocess
import sys
import time

def run_command(cmd, input_text=None):
    """Run a shell command and return result"""
    try:
        if input_text:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, input=input_text, timeout=60
            )
        else:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=60
            )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"

def test_clean_workflow():
    """Test the complete clean workflow"""
    print("🧪 Testing Database Clean Workflow")
    print("=" * 50)
    
    print("📊 Step 1: Check initial state")
    retcode, stdout, stderr = run_command("python test_user_setup.py")
    initial_users_exist = retcode == 0
    print(f"  Initial users exist: {'✅' if initial_users_exist else '❌'}")
    
    print("\n🧹 Step 2: Clean databases (with auto 'y' confirmation)")
    retcode, stdout, stderr = run_command("./odras.sh clean", input_text="y\n")
    clean_success = retcode == 0 and "Database cleaning completed" in stdout
    print(f"  Clean command success: {'✅' if clean_success else '❌'}")
    if not clean_success:
        print(f"    Error: {stderr}")
        return False
    
    # Check if users were recreated automatically
    users_recreated = "Created default users" in stdout and "admin/admin" in stdout
    print(f"  Users auto-recreated: {'✅' if users_recreated else '❌'}")
    
    print("\n⏳ Step 3: Wait a moment for database operations to complete")
    time.sleep(2)
    
    print("\n🔍 Step 4: Verify users work after cleaning")
    retcode, stdout, stderr = run_command("python test_user_setup.py")
    final_users_work = retcode == 0
    print(f"  Final users functional: {'✅' if final_users_work else '❌'}")
    
    if not final_users_work:
        print("    User test output:")
        print("   ", stdout.replace('\n', '\n    '))
        if stderr:
            print("    Errors:")
            print("   ", stderr.replace('\n', '\n    '))
    
    print(f"\n📊 Workflow Test Results:")
    print("-" * 30)
    success = clean_success and users_recreated and final_users_work
    print(f"Overall Result: {'🎉 SUCCESS' if success else '❌ FAILED'}")
    
    if success:
        print("\n✅ Database cleaning workflow is working perfectly!")
        print("💡 Users can now run './odras.sh clean' and login immediately")
    else:
        print("\n⚠️  Database cleaning workflow needs attention")
    
    return success

if __name__ == "__main__":
    success = test_clean_workflow()
    sys.exit(0 if success else 1)

