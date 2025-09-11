"""
Admin API routes.
Defines admin-only endpoints for user management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from ..dependencies import (
    get_user_repository,
    get_session_repository,
    get_current_admin_user,
    get_auth_service
)
from ...schemas.auth import (
    UserResponse,
    UserUpdate,
    MessageResponse
)
from ...models.user import User

# Create router
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    user_repo = Depends(get_user_repository)
):
    """
    Get all users (admin only).
    
    Args:
        skip: Number of users to skip
        limit: Maximum number of users to return
        current_user: Current admin user
        user_repo: User repository
        
    Returns:
        List of users
    """
    users = user_repo.get_all(skip=skip, limit=limit)
    return [UserResponse.from_orm(user) for user in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    user_repo = Depends(get_user_repository)
):
    """
    Get user by ID (admin only).
    
    Args:
        user_id: User ID
        current_user: Current admin user
        user_repo: User repository
        
    Returns:
        User data
        
    Raises:
        HTTPException: If user not found
    """
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserResponse.from_orm(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    user_repo = Depends(get_user_repository),
    auth_service = Depends(get_auth_service)
):
    """
    Update any user (admin only).
    
    Args:
        user_id: User ID to update
        user_update: User update data
        current_user: Current admin user
        user_repo: User repository
        auth_service: Authentication service
        
    Returns:
        Updated user data
        
    Raises:
        HTTPException: If update fails
    """
    try:
        update_data = user_update.dict(exclude_unset=True)
        updated_user = await auth_service.update_user_profile(
            user_id, update_data, user_repo, is_admin=True
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse.from_orm(updated_user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during user update"
        )


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    user_repo = Depends(get_user_repository)
):
    """
    Delete a user (admin only).
    
    Args:
        user_id: User ID to delete
        current_user: Current admin user
        user_repo: User repository
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If deletion fails
    """
    try:
        # Prevent admin from deleting themselves
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        success = user_repo.delete(user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return MessageResponse(message="User deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during user deletion"
        )


@router.post("/users/{user_id}/deactivate", response_model=MessageResponse)
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    user_repo = Depends(get_user_repository)
):
    """
    Deactivate a user account (admin only).
    
    Args:
        user_id: User ID to deactivate
        current_user: Current admin user
        user_repo: User repository
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If deactivation fails
    """
    try:
        # Prevent admin from deactivating themselves
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account"
            )
        
        updated_user = user_repo.update(user_id, is_active=False)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return MessageResponse(message="User deactivated successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during user deactivation"
        )


@router.post("/users/{user_id}/activate", response_model=MessageResponse)
async def activate_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    user_repo = Depends(get_user_repository)
):
    """
    Activate a user account (admin only).
    
    Args:
        user_id: User ID to activate
        current_user: Current admin user
        user_repo: User repository
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If activation fails
    """
    try:
        updated_user = user_repo.update(user_id, is_active=True)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return MessageResponse(message="User activated successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during user activation"
        )


@router.get("/users/{user_id}/sessions", response_model=List[dict])
async def get_user_sessions(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    session_repo = Depends(get_session_repository)
):
    """
    Get all sessions for a specific user (admin only).
    
    Args:
        user_id: User ID
        current_user: Current admin user
        session_repo: Session repository
        
    Returns:
        List of user sessions
    """
    sessions = session_repo.get_user_sessions(user_id)
    return [session.to_dict() for session in sessions]


@router.delete("/users/{user_id}/sessions", response_model=MessageResponse)
async def revoke_all_user_sessions(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    session_repo = Depends(get_session_repository)
):
    """
    Revoke all sessions for a specific user (admin only).
    
    Args:
        user_id: User ID
        current_user: Current admin user
        session_repo: Session repository
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If revocation fails
    """
    try:
        session_repo.deactivate_user_sessions(user_id)
        return MessageResponse(message="All user sessions revoked successfully")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during session revocation"
        )


@router.post("/cleanup-sessions", response_model=MessageResponse)
async def cleanup_expired_sessions(
    current_user: User = Depends(get_current_admin_user),
    session_repo = Depends(get_session_repository)
):
    """
    Clean up expired sessions (admin only).
    
    Args:
        current_user: Current admin user
        session_repo: Session repository
        
    Returns:
        Success message with count of cleaned sessions
    """
    try:
        cleaned_count = session_repo.cleanup_expired_sessions()
        return MessageResponse(
            message=f"Cleaned up {cleaned_count} expired sessions"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during session cleanup"
        )