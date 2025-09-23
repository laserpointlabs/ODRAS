"""
Enhanced Authentication Service for ODRAS
Implements secure password hashing, user management, and role-based access control.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from .db import DatabaseService
from .config import Settings

logger = logging.getLogger(__name__)


class AuthService:
    """Enhanced authentication service with proper password handling and user management."""

    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        self.settings = Settings()

    def hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hash a password using PBKDF2 with a random salt."""
        if salt is None:
            salt = secrets.token_hex(32)

        # Use PBKDF2 with 100,000 iterations (OWASP recommended minimum)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
        )
        return password_hash.hex(), salt

    def verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """Verify a password against its stored hash and salt."""
        try:
            password_hash, _ = self.hash_password(password, salt)
            return password_hash == stored_hash
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def create_user(
        self,
        username: str,
        password: str,
        display_name: Optional[str] = None,
        is_admin: bool = False,
        is_active: bool = True,
    ) -> Dict[str, any]:
        """Create a new user with hashed password."""
        if not username or not password:
            raise ValueError("Username and password are required")

        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Check if user already exists
        existing = self.get_user_by_username(username)
        if existing:
            raise ValueError("Username already exists")

        # Hash the password
        password_hash, salt = self.hash_password(password)

        # Create user in database
        conn = self.db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.users (username, display_name, password_hash, salt, is_admin, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING user_id, username, display_name, is_admin, is_active, created_at
                    """,
                    (
                        username,
                        display_name or username,
                        password_hash,
                        salt,
                        is_admin,
                        is_active,
                    ),
                )
                result = cur.fetchone()
                conn.commit()

                if not result:
                    raise ValueError("Failed to create user")

                return {
                    "user_id": str(result[0]),
                    "username": result[1],
                    "display_name": result[2],
                    "is_admin": bool(result[3]),
                    "is_active": bool(result[4]),
                    "created_at": result[5],
                }
        finally:
            self.db._return(conn)

    def get_user_by_username(self, username: str) -> Optional[Dict[str, any]]:
        """Get user by username."""
        conn = self.db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT user_id, username, display_name, password_hash, salt, is_admin, is_active, created_at, updated_at
                    FROM public.users WHERE username = %s
                    """,
                    (username,),
                )
                result = cur.fetchone()

                if not result:
                    return None

                return {
                    "user_id": str(result[0]),
                    "username": result[1],
                    "display_name": result[2],
                    "password_hash": result[3],
                    "salt": result[4],
                    "is_admin": bool(result[5]),
                    "is_active": bool(result[6]),
                    "created_at": result[7],
                    "updated_at": result[8],
                }
        finally:
            self.db._return(conn)

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, any]]:
        """Authenticate a user with username and password."""
        user = self.get_user_by_username(username)
        if not user:
            return None

        if not user["is_active"]:
            logger.warning(f"Login attempt for inactive user: {username}")
            return None

        if not self.verify_password(password, user["password_hash"], user["salt"]):
            logger.warning(f"Failed login attempt for user: {username}")
            return None

        # Return user info without sensitive data
        return {
            "user_id": user["user_id"],
            "username": user["username"],
            "display_name": user["display_name"],
            "is_admin": user["is_admin"],
            "is_active": user["is_active"],
        }

    def update_user_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """Update user password with old password verification."""
        if len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters long")

        conn = self.db._conn()
        try:
            with conn.cursor() as cur:
                # Get current user data
                cur.execute(
                    "SELECT password_hash, salt FROM public.users WHERE user_id = %s",
                    (user_id,),
                )
                result = cur.fetchone()
                if not result:
                    return False

                stored_hash, salt = result

                # Verify old password
                if not self.verify_password(old_password, stored_hash, salt):
                    return False

                # Hash new password
                new_hash, new_salt = self.hash_password(new_password)

                # Update password
                cur.execute(
                    """
                    UPDATE public.users
                    SET password_hash = %s, salt = %s, updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (new_hash, new_salt, user_id),
                )
                conn.commit()
                return True
        finally:
            self.db._return(conn)

    def list_users(self, include_inactive: bool = False) -> List[Dict[str, any]]:
        """List all users."""
        conn = self.db._conn()
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT user_id, username, display_name, is_admin, is_active, created_at, updated_at
                    FROM public.users
                """
                if not include_inactive:
                    query += " WHERE is_active = TRUE"
                query += " ORDER BY created_at DESC"

                cur.execute(query)
                results = cur.fetchall()

                return [
                    {
                        "user_id": str(row[0]),
                        "username": row[1],
                        "display_name": row[2],
                        "is_admin": bool(row[3]),
                        "is_active": bool(row[4]),
                        "created_at": row[5],
                        "updated_at": row[6],
                    }
                    for row in results
                ]
        finally:
            self.db._return(conn)

    def update_user_role(self, user_id: str, is_admin: bool) -> bool:
        """Update user admin status."""
        conn = self.db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE public.users
                    SET is_admin = %s, updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (is_admin, user_id),
                )
                conn.commit()
                return cur.rowcount > 0
        finally:
            self.db._return(conn)

    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account."""
        conn = self.db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE public.users
                    SET is_active = FALSE, updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
                conn.commit()
                return cur.rowcount > 0
        finally:
            self.db._return(conn)

    def activate_user(self, user_id: str) -> bool:
        """Activate a user account."""
        conn = self.db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE public.users
                    SET is_active = TRUE, updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
                conn.commit()
                return cur.rowcount > 0
        finally:
            self.db._return(conn)

