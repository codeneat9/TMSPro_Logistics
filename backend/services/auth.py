"""
Authentication Service
Handles user registration, login, password hashing, and JWT token management
"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from backend.models.user import User
from backend.config import get_settings

# Password hashing configuration.
# pbkdf2_sha256 avoids bcrypt backend incompatibilities on Python 3.14.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

settings = get_settings()


def _jwt_secret() -> str:
    """Return a JWT signing secret that meets HS256 minimum length guidance."""
    raw = settings.JWT_SECRET or ""
    return raw if len(raw) >= 32 else raw.ljust(32, "_")


class AuthService:
    """Service for authentication operations"""

    @staticmethod
    def normalize_india_phone(phone: str) -> str:
        """Normalize user phone to India E.164 format: +91XXXXXXXXXX."""
        raw = ''.join(ch for ch in str(phone or '').strip() if ch.isdigit() or ch == '+')
        digits = ''.join(ch for ch in raw if ch.isdigit())

        if len(digits) == 12 and digits.startswith('91'):
            local = digits[2:]
        elif len(digits) == 10:
            local = digits
        else:
            raise ValueError('Phone must be a valid India mobile number (10 digits).')

        if not local[0] in {'6', '7', '8', '9'}:
            raise ValueError('India mobile number must start with 6/7/8/9.')

        return f'+91{local}'
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token
        
        Args:
            data: Dictionary containing token claims (e.g., {"sub": user_id})
            expires_delta: Custom expiration time (optional)
            
        Returns:
            JWT token string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
        
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode,
            _jwt_secret(),
            algorithm="HS256"
        )
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """
        Create a JWT refresh token
        
        Args:
            data: Dictionary containing token claims
            
        Returns:
            JWT refresh token string
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(
            to_encode,
            _jwt_secret(),
            algorithm="HS256"
        )
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a JWT token and return its payload
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload dictionary if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                _jwt_secret(),
                algorithms=["HS256"]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def register_user(
        db: Session,
        email: str,
        password: str,
        full_name: str,
        phone: str,
        role: str = "customer"
    ) -> Optional[User]:
        """
        Register a new user
        
        Args:
            db: Database session
            email: User email
            password: Plain text password
            full_name: User full name
            phone: User phone number
            role: User role (customer, driver, admin, company)
            
        Returns:
            Created User object if successful, None if email already exists
        """
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            return None
        
        normalized_phone = AuthService.normalize_india_phone(phone)

        # Hash password and create user
        hashed_password = AuthService.hash_password(password)
        new_user = User(
            email=email,
            password_hash=hashed_password,
            full_name=full_name,
            phone=normalized_phone,
            role=role,
            is_active=True,
            is_verified=False  # Email verification required
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user
    
    @staticmethod
    def authenticate_user(
        db: Session,
        email: str,
        password: str
    ) -> Optional[User]:
        """
        Authenticate a user by email and password
        
        Args:
            db: Database session
            email: User email
            password: Plain text password
            
        Returns:
            User object if credentials are valid, None otherwise
        """
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            return None
        
        if not AuthService.verify_password(password, user.password_hash):
            return None
        
        if not user.is_active:
            return None
        
        return user
    
    @staticmethod
    def create_tokens(user: User) -> Dict[str, str]:
        """
        Create access and refresh tokens for a user
        
        Args:
            user: User object
            
        Returns:
            Dictionary with access_token and refresh_token
        """
        access_token = AuthService.create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            },
            expires_delta=timedelta(hours=settings.JWT_EXPIRATION_HOURS)
        )
        
        refresh_token = AuthService.create_refresh_token(
            data={"sub": str(user.id)}
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
