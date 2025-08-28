#!/usr/bin/env python3
"""
Test script to verify default user setup after database cleaning.
"""
import requests
import json
import psycopg2
import sys

def test_database_users():
    """Test that default users exist in the database"""
    try:
        conn = psycopg2.connect(
            host="localhost", database="odras", user="postgres", 
            password="password", port=5432
        )
        cur = conn.cursor()
        
        # Check users table
        cur.execute("SELECT username, display_name, is_admin FROM users ORDER BY username")
        users = cur.fetchall()
        
        print("👥 Users in database:")
        expected_users = {'admin': True, 'jdehart': False}
        found_users = {}
        
        for username, display_name, is_admin in users:
            admin_flag = "👑 Admin" if is_admin else "👤 User"
            print(f"  • {username:8} | {display_name:15} | {admin_flag}")
            found_users[username] = is_admin
        
        # Verify expected users
        success = True
        for username, should_be_admin in expected_users.items():
            if username not in found_users:
                print(f"❌ Missing user: {username}")
                success = False
            elif found_users[username] != should_be_admin:
                print(f"❌ Wrong admin status for {username}: expected {should_be_admin}, got {found_users[username]}")
                success = False
            else:
                print(f"✅ User {username} correctly configured")
        
        # Check project membership
        cur.execute("""
            SELECT u.username, p.name, pm.role 
            FROM project_members pm
            JOIN users u ON pm.user_id = u.user_id  
            JOIN projects p ON pm.project_id = p.project_id
            ORDER BY u.username
        """)
        memberships = cur.fetchall()
        
        print("\n🏢 Project memberships:")
        for username, project_name, role in memberships:
            print(f"  • {username:8} | {project_name:15} | {role}")
        
        cur.close()
        conn.close()
        
        return success and len(users) >= 2 and len(memberships) >= 2
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

def test_login_endpoints():
    """Test that users can login via API"""
    print("\n🔐 Testing login endpoints:")
    
    test_credentials = [
        ("admin", "admin", True),
        ("jdehart", "jdehart", False)
    ]
    
    success_count = 0
    
    for username, password, should_be_admin in test_credentials:
        try:
            response = requests.post(
                "http://localhost:8000/api/auth/login",
                json={"username": username, "password": password},
                timeout=5
            )
            
            if response.status_code == 200:
                token_data = response.json()
                token = token_data.get("token")
                
                if token:
                    # Test the token by getting user info
                    me_response = requests.get(
                        "http://localhost:8000/api/auth/me",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=5
                    )
                    
                    if me_response.status_code == 200:
                        user_info = me_response.json()
                        is_admin = user_info.get("is_admin", False)
                        
                        admin_indicator = "👑" if is_admin else "👤"
                        print(f"  ✅ {username:8} | Login successful | {admin_indicator} {user_info.get('display_name', '')}")
                        
                        if is_admin == should_be_admin:
                            success_count += 1
                        else:
                            print(f"    ⚠️  Admin status mismatch: expected {should_be_admin}, got {is_admin}")
                    else:
                        print(f"  ❌ {username:8} | Token validation failed: {me_response.status_code}")
                else:
                    print(f"  ❌ {username:8} | No token received")
            else:
                print(f"  ❌ {username:8} | Login failed: {response.status_code}")
                try:
                    error = response.json()
                    print(f"    Error: {error}")
                except:
                    print(f"    Raw response: {response.text}")
                    
        except Exception as e:
            print(f"  ❌ {username:8} | Connection error: {e}")
    
    return success_count == len(test_credentials)

def main():
    """Test complete user setup"""
    print("🧪 Testing ODRAS User Setup After Database Cleaning")
    print("=" * 60)
    
    # Test database users
    db_success = test_database_users()
    
    # Test API login
    api_success = test_login_endpoints()
    
    print(f"\n📊 Test Results:")
    print("-" * 30)
    print(f"Database Users:  {'✅ Pass' if db_success else '❌ Fail'}")
    print(f"API Login:       {'✅ Pass' if api_success else '❌ Fail'}")
    
    if db_success and api_success:
        print("\n🎉 All user setup tests passed!")
        print("💡 Ready for testing with clean data and working login")
        return 0
    else:
        print("\n⚠️  Some user setup tests failed")
        print("💡 Try running: ./odras.sh clean && ./odras.sh restart")
        return 1

if __name__ == "__main__":
    sys.exit(main())


