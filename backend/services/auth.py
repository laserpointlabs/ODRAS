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


