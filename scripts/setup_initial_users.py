#!/usr/bin/env python3
"""
Setup initial users with proper passwords for ODRAS
This script migrates from the old allowlist system to proper password authentication.
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


def setup_initial_users():
    """Set up initial users with passwords."""
    print("🔐 Setting up initial users with password authentication...")

    # Default passwords (should be changed after first login)
    default_passwords = {"admin": "admin123!", "jdehart": "jdehart123!"}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Check if password fields exist
            cur.execute(
                """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'password_hash'
            """
            )

            if not cur.fetchone():
                print("❌ Password fields not found. Please run the migration script first:")
                print("   psql -U postgres -d odras -f scripts/migrate_auth_system.sql")
                return False

            # Update existing users with passwords
            for username, password in default_passwords.items():
                # Check if user exists
                cur.execute("SELECT user_id FROM public.users WHERE username = %s", (username,))
                if not cur.fetchone():
                    print(f"⚠️  User {username} not found, skipping...")
                    continue

                # Generate salt and hash password
                salt = secrets.token_hex(32)
                password_hash = hash_password(password, salt)

                # Update user with password
                cur.execute(
                    """
                    UPDATE public.users 
                    SET password_hash = %s, salt = %s, is_active = TRUE, updated_at = NOW()
                    WHERE username = %s
                """,
                    (password_hash, salt, username),
                )

                print(f"✅ Set password for user: {username}")

            conn.commit()
            print("\n🎉 Initial users setup complete!")
            print("\n📋 Default credentials:")
            print("   admin / admin123!")
            print("   jdehart / jdehart123!")
            print("\n⚠️  IMPORTANT: Change these passwords after first login!")

            return True

    except Exception as e:
        print(f"❌ Error setting up users: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def create_admin_user():
    """Create a new admin user if needed."""
    print("\n👤 Create a new admin user")
    username = input("Username: ").strip()
    if not username:
        print("❌ Username required")
        return False

    password = input("Password (min 8 chars): ").strip()
    if len(password) < 8:
        print("❌ Password must be at least 8 characters")
        return False

    display_name = input("Display name (optional): ").strip() or username

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Check if user exists
            cur.execute("SELECT user_id FROM public.users WHERE username = %s", (username,))
            if cur.fetchone():
                print(f"❌ User {username} already exists")
                return False

            # Generate salt and hash password
            salt = secrets.token_hex(32)
            password_hash = hash_password(password, salt)

            # Create user
            cur.execute(
                """
                INSERT INTO public.users (username, display_name, password_hash, salt, is_admin, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            """,
                (username, display_name, password_hash, salt, True, True),
            )

            conn.commit()
            print(f"✅ Created admin user: {username}")
            return True

    except Exception as e:
        print(f"❌ Error creating user: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def main():
    """Main function."""
    print("🚀 ODRAS User Setup Script")
    print("=" * 40)

    # Check for CI mode
    ci_mode = "--ci" in sys.argv

    if ci_mode:
        print("Running in CI mode (non-interactive)")
        # Setup initial users without prompting
        if not setup_initial_users():
            return 1
    else:
        # Check if we should create a new admin
        create_new = input("Create a new admin user? (y/N): ").strip().lower()
        if create_new == "y":
            if not create_admin_user():
                return 1

        # Setup initial users
        if not setup_initial_users():
            return 1

    print("\n✅ Setup complete! You can now use proper password authentication.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
