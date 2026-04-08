"""
Authentication Routes
Provides user registration, login, and token refresh endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import UserRegister, UserLogin, TokenResponse, UserResponse
from backend.services.auth import AuthService
from backend.middleware.auth import get_current_user
from backend.models.user import User

router = APIRouter(
    prefix="/api/auth",
    tags=["authentication"],
    responses={404: {"description": "Not found"}},
)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    
    - **email**: User email address (must be unique)
    - **password**: User password (min 8 characters)
    - **full_name**: User full name
    - **phone**: User phone number
    - **role**: User role (customer, driver, admin, company) - defaults to 'customer'
    
    Returns access token and refresh token on successful registration.
    """
    # Register user (register_user handles duplicate check)
    user = AuthService.register_user(
        db=db,
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        phone=request.phone,
        role=request.role or "customer"
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create tokens
    tokens = AuthService.create_tokens(user)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens.get("token_type", "bearer"),
        expires_in=86400  # 24 hours in seconds
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLogin,
    db: Session = Depends(get_db)
):
    """
    User login endpoint
    
    - **email**: User email address
    - **password**: User password
    
    Returns access token and refresh token on successful authentication.
    """
    # Authenticate user
    user = AuthService.authenticate_user(
        db=db,
        email=request.email,
        password=request.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    tokens = AuthService.create_tokens(user)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=86400  # 24 hours in seconds
    )


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Refresh authentication token
    
    Request body should contain:
    - **refresh_token**: Valid refresh token
    
    Returns new access token and refresh token.
    """
    refresh_token_str = request.get("refresh_token")
    
    if not refresh_token_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="refresh_token is required"
        )
    
    # Verify refresh token
    payload = AuthService.verify_token(refresh_token_str)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Create new tokens
    tokens = AuthService.create_tokens(user)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=86400  # 24 hours in seconds
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user profile."""
    return current_user
