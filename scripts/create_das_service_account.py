#!/usr/bin/env python3
"""
Create a dedicated DAS service account with limited privileges for autonomous operations.
This account will have restricted permissions to prevent admin-level operations.
"""

import os
import sys
import hashlib
import secrets
import psycopg2
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from services.config import Settings


def hash_password(password: str, salt: str) -> str:
    """Hash a password using PBKDF2 with the given salt."""
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
    )
    return password_hash.hex()


def get_connection():
    """Get database connection."""
    settings = Settings()
    return psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_database,
        user=settings.postgres_user,
        password=settings.postgres_password,
    )


def create_das_service_account():
    """Create a dedicated DAS service account with limited privileges."""
    print("🤖 Creating DAS service account...")

    # DAS service account credentials
    das_username = "das_service"
    das_password = "das_service_2024!"  # Should be changed in production
    das_display_name = "DAS Service Account"

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Check if DAS service account already exists
            cur.execute("SELECT user_id FROM users WHERE username = %s", (das_username,))
            existing_user = cur.fetchone()
            
            if existing_user:
                print(f"✅ DAS service account '{das_username}' already exists")
                return existing_user[0]

            # Create the DAS service user
            print(f"Creating DAS service user: {das_username}")
            
            # Generate salt and hash password
            salt = secrets.token_hex(32)
            password_hash = hash_password(das_password, salt)
            
            # Insert user record with password
            cur.execute(
                """
                INSERT INTO users (username, display_name, is_admin, is_active, password_hash, salt) 
                VALUES (%s, %s, %s, %s, %s, %s) 
                RETURNING user_id
                """,
                (das_username, das_display_name, False, True, password_hash, salt)
            )
            user_id = cur.fetchone()[0]
            
            # Add to default project as a member (not admin)
            cur.execute(
                """
                INSERT INTO project_members (user_id, project_id, role)
                SELECT %s, p.project_id, 'das_service'
                FROM projects p 
                WHERE p.name = 'Default Project'
                ON CONFLICT (user_id, project_id) DO UPDATE SET role = EXCLUDED.role
                """,
                (user_id,)
            )
            
            conn.commit()
            
            print(f"✅ Created DAS service account:")
            print(f"   Username: {das_username}")
            print(f"   Password: {das_password}")
            print(f"   Role: Service Account (Limited Privileges)")
            print(f"   User ID: {user_id}")
            print(f"")
            print(f"⚠️  SECURITY NOTE: This account has limited privileges for DAS autonomous operations.")
            print(f"   It cannot perform admin operations like user management or system configuration.")
            
            return user_id
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Error creating DAS service account: {e}")
        raise
    finally:
        conn.close()


def create_das_permissions_table():
    """Create a permissions table specifically for DAS operations."""
    print("🔐 Setting up DAS permissions system...")
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Create DAS permissions table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS das_permissions (
                    permission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(user_id),
                    permission_type VARCHAR(50) NOT NULL,
                    resource_pattern VARCHAR(255) NOT NULL,
                    allowed BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(user_id, permission_type, resource_pattern)
                )
            """)
            
            # Get DAS service user ID
            cur.execute("SELECT user_id FROM users WHERE username = 'das_service'")
            das_user = cur.fetchone()
            if not das_user:
                print("❌ DAS service account not found. Create it first.")
                return
                
            das_user_id = das_user[0]
            
            # Define allowed operations for DAS service account
            das_permissions = [
                # Ontology operations (read/create classes, not delete)
                ("api_call", "GET:/api/ontologies*", True),
                ("api_call", "POST:/api/ontologies/*/classes", True),
                ("api_call", "POST:/api/ontologies/*/relationships", True),
                ("api_call", "PUT:/api/ontologies/*/classes/*", True),
                
                # Knowledge operations (read/search only)
                ("api_call", "GET:/api/knowledge/assets*", True),
                ("api_call", "POST:/api/knowledge/search", True),
                ("api_call", "GET:/api/knowledge/assets/*", True),
                
                # File operations (limited)
                ("api_call", "GET:/api/files*", True),
                ("api_call", "POST:/api/files/upload", True),
                
                # Analysis workflows
                ("api_call", "POST:/api/workflows/requirements_analysis", True),
                ("api_call", "GET:/api/workflows/status/*", True),
                
                # Project operations (read only)
                ("api_call", "GET:/api/projects*", True),
                
                # BLOCKED operations
                ("api_call", "DELETE:*", False),  # No delete operations
                ("api_call", "*:/api/auth/*", False),  # No auth management
                ("api_call", "*:/api/admin/*", False),  # No admin operations
                ("api_call", "POST:/api/users*", False),  # No user creation
                ("api_call", "PUT:/api/users*", False),  # No user modification
            ]
            
            # Insert permissions
            for perm_type, resource, allowed in das_permissions:
                cur.execute("""
                    INSERT INTO das_permissions (user_id, permission_type, resource_pattern, allowed)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, permission_type, resource_pattern) 
                    DO UPDATE SET allowed = EXCLUDED.allowed, updated_at = NOW()
                """, (das_user_id, perm_type, resource, allowed))
            
            conn.commit()
            print(f"✅ Set up DAS permissions for service account")
            print(f"   Allowed operations: {len([p for p in das_permissions if p[2]])} permissions")
            print(f"   Blocked operations: {len([p for p in das_permissions if not p[2]])} restrictions")
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Error setting up DAS permissions: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        # Create DAS service account
        das_user_id = create_das_service_account()
        
        # Set up permissions system
        create_das_permissions_table()
        
        print(f"")
        print(f"🎉 DAS service account setup complete!")
        print(f"")
        print(f"Next steps:")
        print(f"1. Update DAS API client to use 'das_service' account")
        print(f"2. Implement permission checking in DAS API client")
        print(f"3. Test DAS operations with limited privileges")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)
