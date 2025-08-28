from typing import Dict, Optional

from fastapi import Header, HTTPException


# Simple in-memory token store mapping tokens to user dicts
TOKENS: Dict[str, Dict] = {}


def get_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization.split(" ", 1)[1]
    user = TOKENS.get(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


def get_admin_user(authorization: Optional[str] = Header(None)):
    """Get user and verify admin permissions."""
    user = get_user(authorization)
    if not user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def is_user_admin(user: Dict) -> bool:
    """Check if user has admin privileges."""
    return user.get("is_admin", False)


