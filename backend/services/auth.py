import hashlib
import logging
from typing import Dict, Optional

from fastapi import Header, HTTPException

from .db import DatabaseService
from .config import Settings

logger = logging.getLogger(__name__)

# Keep in-memory cache for performance, but use DB as source of truth
TOKENS_CACHE: Dict[str, Dict] = {}


def _hash_token(token: str) -> str:
    """Create a secure hash of the token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def _get_db_service() -> DatabaseService:
    """Get database service instance."""
    settings = Settings()
    return DatabaseService(settings)


def _update_token_last_used(token_hash: str):
    """Update the last used timestamp for a token (background operation)."""
    try:
        db = _get_db_service()
        conn = db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE public.auth_tokens SET last_used_at = NOW() WHERE token_hash = %s",
                    (token_hash,),
                )
                conn.commit()
        finally:
            db._return(conn)
    except Exception as e:
        logger.warning(f"Failed to update token last used time: {e}")


def create_token(user_id: str, username: str, is_admin: bool, token: str) -> None:
    """Create a new authentication token in the database."""
    # Validate user_id is a valid UUID format
    import uuid

    try:
        uuid.UUID(user_id)
    except ValueError as e:
        raise ValueError(f"Invalid user_id format: {user_id!r}. Expected UUID format.") from e

    token_hash = _hash_token(token)
    db = _get_db_service()
    conn = db._conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.auth_tokens (token_hash, user_id, username, is_admin, expires_at)
                VALUES (%s, %s, %s, %s, NOW() + INTERVAL '24 hours')
                ON CONFLICT (token_hash) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    username = EXCLUDED.username,
                    is_admin = EXCLUDED.is_admin,
                    expires_at = EXCLUDED.expires_at,
                    is_active = TRUE,
                    last_used_at = NOW()
            """,
                (token_hash, user_id, username, is_admin),
            )
            conn.commit()

            # Cache the user info
            user = {"user_id": user_id, "username": username, "is_admin": is_admin}
            TOKENS_CACHE[token_hash] = user

    finally:
        db._return(conn)


def invalidate_token(token: str) -> None:
    """Invalidate a token by marking it as inactive."""
    token_hash = _hash_token(token)
    db = _get_db_service()
    conn = db._conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.auth_tokens SET is_active = FALSE WHERE token_hash = %s",
                (token_hash,),
            )
            conn.commit()

            # Remove from cache
            TOKENS_CACHE.pop(token_hash, None)

    finally:
        db._return(conn)


def cleanup_expired_tokens() -> None:
    """Clean up expired and inactive tokens."""
    db = _get_db_service()
    conn = db._conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.auth_tokens WHERE expires_at < NOW() OR is_active = FALSE"
            )
            deleted_count = cur.rowcount
            conn.commit()
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired/inactive tokens")

            # Clear cache of any tokens that might have been deleted
            TOKENS_CACHE.clear()

    finally:
        db._return(conn)


def get_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = authorization.split(" ", 1)[1]
    token_hash = _hash_token(token)

    # Check cache first for performance
    if token_hash in TOKENS_CACHE:
        user = TOKENS_CACHE[token_hash]
        # Update last used time in background
        _update_token_last_used(token_hash)
        return user

    # Check database
    db = _get_db_service()
    conn = db._conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, username, is_admin, expires_at, is_active
                FROM public.auth_tokens
                WHERE token_hash = %s AND is_active = TRUE
            """,
                (token_hash,),
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=401, detail="Invalid token")

            user_id, username, is_admin, expires_at, is_active = row

            # Check if token is expired
            if expires_at:
                cur.execute("SELECT NOW()")
                current_time = cur.fetchone()[0]
                if expires_at < current_time:
                    # Clean up expired token
                    cur.execute(
                        "UPDATE public.auth_tokens SET is_active = FALSE WHERE token_hash = %s",
                        (token_hash,),
                    )
                    conn.commit()
                    raise HTTPException(status_code=401, detail="Token expired")

            # Update last used time
            cur.execute(
                "UPDATE public.auth_tokens SET last_used_at = NOW() WHERE token_hash = %s",
                (token_hash,),
            )
            conn.commit()

            user = {
                "user_id": str(user_id),
                "username": username,
                "is_admin": bool(is_admin),
            }

            # Cache the result
            TOKENS_CACHE[token_hash] = user

            return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        raise HTTPException(status_code=401, detail="Authentication error")
    finally:
        db._return(conn)


def get_admin_user(authorization: Optional[str] = Header(None)):
    """Get user and verify admin permissions."""
    user = get_user(authorization)
    if not user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def is_user_admin(user: Dict) -> bool:
    """Check if user has admin privileges."""
    return user.get("is_admin", False)

