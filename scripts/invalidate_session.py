#!/usr/bin/env python3
"""
Script to invalidate the current user session for testing authentication.
This simulates what happens when a session expires naturally.
"""

import psycopg2
import sys
from datetime import datetime, timedelta


def invalidate_session():
    """Invalidate the current user session by clearing tokens."""

    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host="localhost", database="odras", user="postgres", password="password"
        )
        cur = conn.cursor()

        print("🔐 Invalidating user sessions...")

        # Clear all user tokens (this will force re-authentication)
        cur.execute(
            """
            UPDATE public.users 
            SET token = NULL, token_expires = NULL 
            WHERE token IS NOT NULL
        """
        )

        affected_rows = cur.rowcount
        conn.commit()

        print(f"✅ Invalidated {affected_rows} user session(s)")
        print("🔄 All users will need to log in again")
        print("\n📝 Test Instructions:")
        print("1. Try to interact with the application (click buttons, save ontologies, etc.)")
        print("2. You should see a 'Session expired' toast notification")
        print("3. You should be automatically redirected to the login page")
        print("4. After logging in again, everything should work normally")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error invalidating session: {e}")
        sys.exit(1)


if __name__ == "__main__":
    invalidate_session()
