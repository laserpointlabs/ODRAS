"""
User Management API endpoints for ODRAS
Provides secure user creation, authentication, and management.
"""

from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import logging

from ..services.auth_service import AuthService
from ..services.db import DatabaseService
from ..services.config import Settings
from ..services.auth import get_user, get_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


# Pydantic models for request/response validation
class UserCreate(BaseModel):
    username: str = Field(
        ..., min_length=3, max_length=50, description="Username (3-50 characters)"
    )
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    display_name: Optional[str] = Field(None, max_length=100, description="Display name")
    is_admin: bool = Field(False, description="Admin privileges")


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100, description="Display name")
    is_admin: Optional[bool] = Field(None, description="Admin privileges")
    is_active: Optional[bool] = Field(None, description="Account status")


class PasswordChange(BaseModel):
    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")


class UserResponse(BaseModel):
    user_id: str
    username: str
    display_name: str
    is_admin: bool
    is_active: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_user_dict(cls, user_dict: Dict[str, any]) -> "UserResponse":
        """Convert user dictionary to UserResponse, handling datetime conversion."""
        return cls(
            user_id=str(user_dict["user_id"]),
            username=user_dict["username"],
            display_name=user_dict["display_name"],
            is_admin=bool(user_dict["is_admin"]),
            is_active=bool(user_dict["is_active"]),
            created_at=(user_dict["created_at"].isoformat() if user_dict.get("created_at") else ""),
            updated_at=(user_dict["updated_at"].isoformat() if user_dict.get("updated_at") else ""),
        )


# Dependency to get auth service
def get_auth_service() -> AuthService:
    db = DatabaseService(Settings())
    return AuthService(db)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
    admin_user: Dict = Depends(get_admin_user),
):
    """Create a new user (admin only)."""
    try:
        user = auth_service.create_user(
            username=user_data.username,
            password=user_data.password,
            display_name=user_data.display_name,
            is_admin=user_data.is_admin,
        )

        logger.info(f"User created: {user_data.username} by admin {admin_user['username']}")
        return UserResponse.from_user_dict(user)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user")


@router.get("/", response_model=List[UserResponse])
def list_users(
    include_inactive: bool = False,
    auth_service: AuthService = Depends(get_auth_service),
    admin_user: Dict = Depends(get_admin_user),
):
    """List all users (admin only)."""
    try:
        users = auth_service.list_users(include_inactive=include_inactive)
        return [UserResponse.from_user_dict(user) for user in users]
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail="Failed to list users")


@router.get("/me", response_model=UserResponse)
def get_current_user(current_user: Dict = Depends(get_user)):
    """Get current user information."""
    return UserResponse(
        user_id=current_user["user_id"],
        username=current_user["username"],
        display_name=current_user.get("display_name", current_user["username"]),
        is_admin=current_user.get("is_admin", False),
        is_active=True,  # If they're authenticated, they're active
        created_at="",  # We'd need to fetch this from DB
        updated_at="",
    )


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    password_data: PasswordChange,
    auth_service: AuthService = Depends(get_auth_service),
    current_user: Dict = Depends(get_user),
):
    """Change current user's password."""
    try:
        success = auth_service.update_user_password(
            user_id=current_user["user_id"],
            old_password=password_data.old_password,
            new_password=password_data.new_password,
        )

        if not success:
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        logger.info(f"Password changed for user: {current_user['username']}")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        raise HTTPException(status_code=500, detail="Failed to change password")


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    user_data: UserUpdate,
    auth_service: AuthService = Depends(get_auth_service),
    admin_user: Dict = Depends(get_admin_user),
):
    """Update user information (admin only)."""
    try:
        # Get current user
        current_user = auth_service.get_user_by_username(user_id)
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update fields
        conn = auth_service.db._conn()
        try:
            with conn.cursor() as cur:
                update_fields = []
                update_values = []

                if user_data.display_name is not None:
                    update_fields.append("display_name = %s")
                    update_values.append(user_data.display_name)

                if user_data.is_admin is not None:
                    update_fields.append("is_admin = %s")
                    update_values.append(user_data.is_admin)

                if user_data.is_active is not None:
                    update_fields.append("is_active = %s")
                    update_values.append(user_data.is_active)

                if not update_fields:
                    raise HTTPException(status_code=400, detail="No fields to update")

                update_fields.append("updated_at = NOW()")
                update_values.append(user_id)

                cur.execute(
                    f"""
                    UPDATE public.users
                    SET {', '.join(update_fields)}
                    WHERE user_id = %s
                    RETURNING user_id, username, display_name, is_admin, is_active, created_at, updated_at
                    """,
                    update_values,
                )

                result = cur.fetchone()
                conn.commit()

                if not result:
                    raise HTTPException(status_code=404, detail="User not found")

                return UserResponse.from_user_dict(
                    {
                        "user_id": str(result[0]),
                        "username": result[1],
                        "display_name": result[2],
                        "is_admin": bool(result[3]),
                        "is_active": bool(result[4]),
                        "created_at": result[5],
                        "updated_at": result[6],
                    }
                )
        finally:
            auth_service.db._return(conn)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user")


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: str,
    auth_service: AuthService = Depends(get_auth_service),
    admin_user: Dict = Depends(get_admin_user),
):
    """Deactivate a user account (admin only)."""
    try:
        success = auth_service.deactivate_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")

        logger.info(f"User deactivated: {user_id} by admin {admin_user['username']}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating user: {e}")
        raise HTTPException(status_code=500, detail="Failed to deactivate user")


@router.post("/{user_id}/activate", status_code=status.HTTP_204_NO_CONTENT)
def activate_user(
    user_id: str,
    auth_service: AuthService = Depends(get_auth_service),
    admin_user: Dict = Depends(get_admin_user),
):
    """Activate a user account (admin only)."""
    try:
        success = auth_service.activate_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")

        logger.info(f"User activated: {user_id} by admin {admin_user['username']}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating user: {e}")
        raise HTTPException(status_code=500, detail="Failed to activate user")

