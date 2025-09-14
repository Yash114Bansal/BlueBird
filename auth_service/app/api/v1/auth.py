"""
Authentication API routes.
Defines all authentication endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List
import logging

logger = logging.getLogger(__name__)

from ..dependencies import (
    get_database_session,
    get_user_repository,
    get_session_repository,
    get_auth_service,
    get_current_user,
    get_current_active_user,
    get_current_admin_user,
    get_client_ip,
    get_user_agent,
    login_rate_limit,
    register_rate_limit,
    password_reset_rate_limit,
    otp_verification_rate_limit,
    resend_otp_rate_limit,
    security
)
from ...schemas.auth import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    Token,
    PasswordChange,
    PasswordReset,
    PasswordResetConfirm,
    RefreshToken,
    SessionResponse,
    MessageResponse,
    ErrorResponse,
    OTPVerificationRequest,
    OTPVerificationResponse,
    ResendOTPRequest,
    ResendOTPResponse
)
from ...models.user import User

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    user_repo = Depends(get_user_repository),
    auth_service = Depends(get_auth_service),
    rate_limit: bool = Depends(register_rate_limit)
):
    """
    Register a new user and send OTP verification email.
    
    Args:
        user_data: User registration data
        request: FastAPI request object
        user_repo: User repository
        auth_service: Authentication service
        rate_limit: Rate limiting dependency
        
    Returns:
        Created user data
        
    Raises:
        HTTPException: If registration fails
    """
    try:
        user = await auth_service.register_user(user_data, user_repo)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed. Email or username may already exist."
            )
        
        # Send OTP verification email
        try:
            from ...services.otp_service import otp_service
            from ...services.celery_service import celery_service
            
            # Generate and store OTP
            otp = otp_service.generate_otp()
            await otp_service.store_otp(user.email, otp)
            
            # Send OTP email via Celery workers
            await celery_service.send_otp_email(
                user.email,
                otp,
                {
                    'username': user.username,
                    'full_name': user.full_name or user.username,
                    'email': user.email
                }
            )
            
            logger.info(f"OTP verification email sent to {user.email}")
            
        except Exception as e:
            logger.error(f"Failed to send OTP email to {user.email}: {e}")
            # Don't fail registration if email sending fails
        
        return UserResponse.from_orm(user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )


@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,
    request: Request,
    user_repo = Depends(get_user_repository),
    session_repo = Depends(get_session_repository),
    auth_service = Depends(get_auth_service),
    rate_limit: bool = Depends(login_rate_limit)
):
    """
    Authenticate user and return tokens.
    
    Args:
        login_data: User login credentials
        request: FastAPI request object
        user_repo: User repository
        session_repo: Session repository
        auth_service: Authentication service
        rate_limit: Rate limiting dependency
        
    Returns:
        Access and refresh tokens
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Authenticate user
        user = await auth_service.authenticate_user(login_data, user_repo)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create session
        client_ip = get_client_ip(request)
        user_agent = get_user_agent(request)
        
        session = await auth_service.create_user_session(
            user, session_repo, client_ip, user_agent
        )
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create session"
            )
        
        return Token(
            access_token=session.session_token,
            refresh_token=session.refresh_token,
            token_type="bearer",
            expires_in=await auth_service.get_token_expiry()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshToken,
    session_repo = Depends(get_session_repository),
    auth_service = Depends(get_auth_service)
):
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_data: Refresh token data
        session_repo: Session repository
        auth_service: Authentication service
        
    Returns:
        New access and refresh tokens
        
    Raises:
        HTTPException: If token refresh fails
    """
    try:
        tokens = await auth_service.refresh_access_token(
            refresh_data.refresh_token, session_repo
        )
        
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        return Token(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
            expires_in=await auth_service.get_token_expiry()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during token refresh"
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session_repo = Depends(get_session_repository),
    auth_service = Depends(get_auth_service)
):
    """
    Logout user by invalidating session.
    
    Args:
        credentials: HTTP authorization credentials
        session_repo: Session repository
        auth_service: Authentication service
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If logout fails
    """
    try:
        success = await auth_service.logout_user(
            credentials.credentials, session_repo
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Logout failed"
            )
        
        return MessageResponse(message="Successfully logged out")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during logout"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user data
    """
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    user_repo = Depends(get_user_repository),
    auth_service = Depends(get_auth_service)
):
    """
    Update current user information.
    
    Args:
        user_update: User update data
        current_user: Current authenticated user
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
            current_user.id, update_data, user_repo, is_admin=False
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


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    user_repo = Depends(get_user_repository),
    auth_service = Depends(get_auth_service)
):
    """
    Change user password.
    
    Args:
        password_data: Password change data
        current_user: Current authenticated user
        user_repo: User repository
        auth_service: Authentication service
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If password change fails
    """
    try:
        success = await auth_service.change_password(
            current_user.id, password_data, user_repo
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid current password"
            )
        
        return MessageResponse(message="Password changed successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during password change"
        )


@router.get("/sessions", response_model=List[SessionResponse])
async def get_user_sessions(
    current_user: User = Depends(get_current_active_user),
    session_repo = Depends(get_session_repository)
):
    """
    Get current user's active sessions.
    
    Args:
        current_user: Current authenticated user
        session_repo: Session repository
        
    Returns:
        List of user sessions
    """
    sessions = session_repo.get_user_sessions(current_user.id)
    return [SessionResponse.from_orm(session) for session in sessions]


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    session_repo = Depends(get_session_repository)
):
    """
    Revoke a specific user session.
    
    Args:
        session_id: Session ID to revoke
        current_user: Current authenticated user
        session_repo: Session repository
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If session revocation fails
    """
    try:
        session = session_repo.get_by_id(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to revoke this session"
            )
        
        session.is_active = False
        session_repo.session.commit()
        
        return MessageResponse(message="Session revoked successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during session revocation"
        )


@router.post("/verify-email", response_model=OTPVerificationResponse)
async def verify_email(
    verification_data: OTPVerificationRequest,
    request: Request,
    user_repo = Depends(get_user_repository),
    auth_service = Depends(get_auth_service),
    rate_limit: bool = Depends(otp_verification_rate_limit)
):
    """
    Verify user email with OTP.
    
    Args:
        verification_data: OTP verification data
        user_repo: User repository
        auth_service: Authentication service
        
    Returns:
        Verification result
        
    Raises:
        HTTPException: If verification fails
    """
    try:
        # Import OTP service
        from ...services.otp_service import otp_service
        
        # Find user by email
        user = user_repo.get_by_email(verification_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user is already verified
        if user.is_verified:
            return OTPVerificationResponse(
                success=True,
                message="Email already verified",
                verified=True
            )
        
        # Validate OTP
        validation_result = await otp_service.validate_otp(
            verification_data.email, 
            verification_data.otp
        )
        
        if not validation_result["valid"]:
            # Get remaining attempts
            otp_info = await otp_service.get_otp_info(verification_data.email)
            remaining_attempts = otp_info.get("remaining_attempts", 0)
            
            if validation_result["reason"] == "MAX_ATTEMPTS_EXCEEDED":
                return OTPVerificationResponse(
                    success=False,
                    message=validation_result["message"],
                    verified=False,
                    remaining_attempts=0
                )
            elif validation_result["reason"] == "OTP_NOT_FOUND":
                return OTPVerificationResponse(
                    success=False,
                    message="OTP expired or not found. Please request a new one.",
                    verified=False,
                    remaining_attempts=0
                )
            else:
                return OTPVerificationResponse(
                    success=False,
                    message=validation_result["message"],
                    verified=False,
                    remaining_attempts=remaining_attempts
                )
        
        # Mark user as verified
        user.is_verified = True
        user_repo.session.commit()
        
        # Send welcome email
        from ...services.celery_service import celery_service
        await celery_service.send_welcome_email(
            user.email,
            {
                'username': user.username,
                'full_name': user.full_name or user.username,
                'email': user.email
            }
        )
        
        logger.info(f"Email verified successfully for user {user.email}")
        
        return OTPVerificationResponse(
            success=True,
            message="Email verified successfully",
            verified=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during email verification"
        )


@router.post("/resend-otp", response_model=ResendOTPResponse)
async def resend_otp(
    resend_data: ResendOTPRequest,
    request: Request,
    user_repo = Depends(get_user_repository),
    auth_service = Depends(get_auth_service),
    rate_limit: bool = Depends(resend_otp_rate_limit)
):
    """
    Resend OTP verification email.
    
    Args:
        resend_data: Resend OTP data
        user_repo: User repository
        auth_service: Authentication service
        
    Returns:
        Resend result
        
    Raises:
        HTTPException: If resend fails
    """
    try:
        # Import services
        from ...services.otp_service import otp_service
        from ...services.celery_service import celery_service
        
        # Find user by email
        user = user_repo.get_by_email(resend_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user is already verified
        if user.is_verified:
            return ResendOTPResponse(
                success=True,
                message="Email already verified",
                otp_sent=False
            )
        
        # Check if there's already an active OTP
        otp_info = await otp_service.get_otp_info(resend_data.email)
        if not otp_info["is_expired"]:
            return ResendOTPResponse(
                success=True,
                message="OTP already sent. Please check your email or wait for it to expire.",
                otp_sent=False,
                remaining_attempts=otp_info["remaining_attempts"]
            )
        
        # Generate new OTP
        otp = otp_service.generate_otp()
        
        # Store OTP in cache
        stored = await otp_service.store_otp(resend_data.email, otp)
        if not stored:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate OTP"
            )
        
        # Send OTP email via Celery workers
        email_sent = await celery_service.send_otp_email(
            resend_data.email,
            otp,
            {
                'username': user.username,
                'full_name': user.full_name or user.username,
                'email': user.email
            }
        )
        
        if not email_sent:
            # Clean up stored OTP if email sending failed
            await otp_service.clear_otp(resend_data.email)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email"
            )
        
        logger.info(f"OTP resent successfully to {resend_data.email}")
        
        return ResendOTPResponse(
            success=True,
            message="Verification email sent successfully",
            otp_sent=True,
            remaining_attempts=otp_info["max_attempts"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resend OTP failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during OTP resend"
        )