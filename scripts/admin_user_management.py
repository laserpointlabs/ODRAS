#!/usr/bin/env python3
"""
Simple CLI tool for user management in ODRAS
Provides basic user operations without needing the full web interface.
"""

import os
import sys
import getpass
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from services.auth_service import AuthService
from services.db import DatabaseService
from services.config import Settings


def get_auth_service():
    """Get authentication service instance."""
    db = DatabaseService(Settings())
    return AuthService(db)


def list_users():
    """List all users."""
    auth_service = get_auth_service()
    users = auth_service.list_users(include_inactive=True)

    if not users:
        print("No users found.")
        return

    print("\n👥 Users:")
    print("-" * 80)
    print(f"{'Username':<20} {'Display Name':<20} {'Admin':<8} {'Active':<8} {'Created'}")
    print("-" * 80)

    for user in users:
        status = "✅" if user["is_active"] else "❌"
        admin = "✅" if user["is_admin"] else "❌"
        created = user["created_at"].strftime("%Y-%m-%d") if user["created_at"] else "Unknown"
        print(f"{user['username']:<20} {user['display_name']:<20} {admin:<8} {status:<8} {created}")


def create_user():
    """Create a new user."""
    print("\n👤 Create New User")
    print("-" * 30)

    username = input("Username: ").strip()
    if not username:
        print("❌ Username required")
        return

    password = getpass.getpass("Password: ")
    if len(password) < 8:
        print("❌ Password must be at least 8 characters")
        return

    display_name = input("Display name (optional): ").strip() or username

    is_admin = input("Admin user? (y/N): ").strip().lower() == "y"

    try:
        auth_service = get_auth_service()
        user = auth_service.create_user(
            username=username,
            password=password,
            display_name=display_name,
            is_admin=is_admin,
        )
        print(f"✅ User created successfully: {user['username']}")
    except ValueError as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def change_password():
    """Change a user's password."""
    print("\n🔐 Change User Password")
    print("-" * 30)

    username = input("Username: ").strip()
    if not username:
        print("❌ Username required")
        return

    # Get user info
    auth_service = get_auth_service()
    user = auth_service.get_user_by_username(username)
    if not user:
        print(f"❌ User not found: {username}")
        return

    new_password = getpass.getpass("New password: ")
    if len(new_password) < 8:
        print("❌ Password must be at least 8 characters")
        return

    confirm_password = getpass.getpass("Confirm password: ")
    if new_password != confirm_password:
        print("❌ Passwords don't match")
        return

    # For admin changing another user's password, we need to update directly
    # This is a simplified approach - in production, you'd want proper admin verification
    try:
        import hashlib
        import secrets

        salt = secrets.token_hex(32)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256", new_password.encode("utf-8"), salt.encode("utf-8"), 100000
        ).hex()

        db = DatabaseService(Settings())
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE public.users
                    SET password_hash = %s, salt = %s, updated_at = NOW()
                    WHERE username = %s
                    """,
                    (password_hash, salt, username),
                )
                conn.commit()
                print(f"✅ Password changed for user: {username}")
        finally:
            db._return(conn)
    except Exception as e:
        print(f"❌ Error changing password: {e}")


def toggle_user_status():
    """Activate or deactivate a user."""
    print("\n🔄 Toggle User Status")
    print("-" * 30)

    username = input("Username: ").strip()
    if not username:
        print("❌ Username required")
        return

    auth_service = get_auth_service()
    user = auth_service.get_user_by_username(username)
    if not user:
        print(f"❌ User not found: {username}")
        return

    current_status = "active" if user["is_active"] else "inactive"
    new_status = "inactive" if user["is_active"] else "active"

    confirm = (
        input(f"Change {username} from {current_status} to {new_status}? (y/N): ").strip().lower()
    )
    if confirm != "y":
        print("Cancelled.")
        return

    try:
        if new_status == "active":
            success = auth_service.activate_user(user["user_id"])
        else:
            success = auth_service.deactivate_user(user["user_id"])

        if success:
            print(f"✅ User {username} is now {new_status}")
        else:
            print(f"❌ Failed to change user status")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main menu."""
    while True:
        print("\n🔐 ODRAS User Management")
        print("=" * 30)
        print("1. List users")
        print("2. Create user")
        print("3. Change password")
        print("4. Toggle user status")
        print("5. Exit")

        choice = input("\nSelect option (1-5): ").strip()

        if choice == "1":
            list_users()
        elif choice == "2":
            create_user()
        elif choice == "3":
            change_password()
        elif choice == "4":
            toggle_user_status()
        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print("❌ Invalid option")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

