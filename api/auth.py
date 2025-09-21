"""
Authentication and Authorization for Product Feedback Miner API.

This module provides JWT-based authentication, API key authentication,
and role-based access control for the API endpoints.
"""

import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from functools import wraps
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from api.models import LoginRequest, LoginResponse, TokenResponse

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# Configuration
JWT_SECRET_KEY = "your-secret-key-change-in-production"  # Should be from environment
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# API Key storage (in production, use Redis or database)
API_KEYS = {
    "admin": "admin-key-12345",
    "readonly": "readonly-key-67890",
    "analyst": "analyst-key-11111"
}

# User roles and permissions
ROLES = {
    "admin": {
        "permissions": ["read", "write", "delete", "admin"],
        "description": "Full system access"
    },
    "analyst": {
        "permissions": ["read", "write"],
        "description": "Read and write access to data"
    },
    "readonly": {
        "permissions": ["read"],
        "description": "Read-only access"
    }
}

# User storage (in production, use database)
USERS = {
    "admin": {
        "username": "admin",
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "admin",
        "active": True,
        "created_at": datetime.utcnow()
    },
    "analyst": {
        "username": "analyst",
        "password_hash": hashlib.sha256("analyst123".encode()).hexdigest(),
        "role": "analyst",
        "active": True,
        "created_at": datetime.utcnow()
    },
    "readonly": {
        "username": "readonly",
        "password_hash": hashlib.sha256("readonly123".encode()).hexdigest(),
        "role": "readonly",
        "active": True,
        "created_at": datetime.utcnow()
    }
}

class AuthenticationError(Exception):
    """Authentication error."""
    pass

class AuthorizationError(Exception):
    """Authorization error."""
    pass

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(password) == hashed

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.JWTError:
        raise AuthenticationError("Invalid token")

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate a user with username and password."""
    user = USERS.get(username)
    if not user or not user.get("active"):
        return None
    
    if not verify_password(password, user["password_hash"]):
        return None
    
    return {
        "username": user["username"],
        "role": user["role"],
        "permissions": ROLES[user["role"]]["permissions"]
    }

def authenticate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Authenticate using API key."""
    for role, key in API_KEYS.items():
        if key == api_key:
            return {
                "api_key": api_key,
                "role": role,
                "permissions": ROLES[role]["permissions"]
            }
    return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user from JWT token or API key."""
    try:
        token = credentials.credentials
        
        # Try JWT token first
        try:
            payload = verify_token(token)
            return payload
        except AuthenticationError:
            pass
        
        # Try API key
        user = authenticate_api_key(token)
        if user:
            return user
        
        raise AuthenticationError("Invalid authentication credentials")
    
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def require_permission(permission: str):
    """Decorator to require specific permission."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs or dependencies
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            user_permissions = current_user.get("permissions", [])
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(role: str):
    """Decorator to require specific role."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            user_role = current_user.get("role")
            if user_role != role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{role}' required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict[str, Any]]:
    """Get current user if authenticated, otherwise return None."""
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        
        # Try JWT token first
        try:
            payload = verify_token(token)
            return payload
        except AuthenticationError:
            pass
        
        # Try API key
        user = authenticate_api_key(token)
        if user:
            return user
        
        return None
    
    except Exception:
        return None

# Authentication endpoints
async def login(login_request: LoginRequest) -> LoginResponse:
    """Authenticate user and return JWT token."""
    user = authenticate_user(login_request.username, login_request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION_HOURS * 3600,
        user=user
    )

async def verify_token_endpoint(token: str) -> TokenResponse:
    """Verify a JWT token."""
    try:
        payload = verify_token(token)
        return TokenResponse(
            valid=True,
            user=payload,
            expires_at=datetime.fromtimestamp(payload["exp"])
        )
    except AuthenticationError as e:
        return TokenResponse(
            valid=False,
            user=None,
            expires_at=None
        )

async def refresh_token(current_user: Dict[str, Any] = Depends(get_current_user)) -> LoginResponse:
    """Refresh JWT token."""
    access_token = create_access_token(data={"sub": current_user["username"], "role": current_user["role"]})
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION_HOURS * 3600,
        user=current_user
    )

# Permission checkers
def has_permission(user: Dict[str, Any], permission: str) -> bool:
    """Check if user has specific permission."""
    user_permissions = user.get("permissions", [])
    return permission in user_permissions

def has_role(user: Dict[str, Any], role: str) -> bool:
    """Check if user has specific role."""
    return user.get("role") == role

def has_any_permission(user: Dict[str, Any], permissions: List[str]) -> bool:
    """Check if user has any of the specified permissions."""
    user_permissions = user.get("permissions", [])
    return any(permission in user_permissions for permission in permissions)

def has_any_role(user: Dict[str, Any], roles: List[str]) -> bool:
    """Check if user has any of the specified roles."""
    user_role = user.get("role")
    return user_role in roles

# API Key management
def generate_api_key() -> str:
    """Generate a new API key."""
    return secrets.token_urlsafe(32)

def add_api_key(role: str, api_key: str) -> bool:
    """Add a new API key."""
    if role not in ROLES:
        return False
    
    API_KEYS[role] = api_key
    return True

def revoke_api_key(api_key: str) -> bool:
    """Revoke an API key."""
    for role, key in list(API_KEYS.items()):
        if key == api_key:
            del API_KEYS[role]
            return True
    return False

def list_api_keys() -> Dict[str, str]:
    """List all API keys (without revealing the actual keys)."""
    return {role: f"{key[:8]}..." for role, key in API_KEYS.items()}

# User management
def create_user(username: str, password: str, role: str) -> bool:
    """Create a new user."""
    if username in USERS or role not in ROLES:
        return False
    
    USERS[username] = {
        "username": username,
        "password_hash": hash_password(password),
        "role": role,
        "active": True,
        "created_at": datetime.utcnow()
    }
    return True

def update_user_role(username: str, new_role: str) -> bool:
    """Update user role."""
    if username not in USERS or new_role not in ROLES:
        return False
    
    USERS[username]["role"] = new_role
    USERS[username]["permissions"] = ROLES[new_role]["permissions"]
    return True

def deactivate_user(username: str) -> bool:
    """Deactivate a user."""
    if username not in USERS:
        return False
    
    USERS[username]["active"] = False
    return True

def get_user_info(username: str) -> Optional[Dict[str, Any]]:
    """Get user information."""
    user = USERS.get(username)
    if not user:
        return None
    
    return {
        "username": user["username"],
        "role": user["role"],
        "permissions": ROLES[user["role"]]["permissions"],
        "active": user["active"],
        "created_at": user["created_at"]
    }

def list_users() -> List[Dict[str, Any]]:
    """List all users."""
    return [get_user_info(username) for username in USERS.keys()]

# Rate limiting (simple in-memory implementation)
from collections import defaultdict
import time

RATE_LIMITS = defaultdict(list)

def check_rate_limit(identifier: str, limit: int, window: int) -> bool:
    """Check if request is within rate limit."""
    now = time.time()
    window_start = now - window
    
    # Clean old entries
    RATE_LIMITS[identifier] = [timestamp for timestamp in RATE_LIMITS[identifier] if timestamp > window_start]
    
    # Check if under limit
    if len(RATE_LIMITS[identifier]) < limit:
        RATE_LIMITS[identifier].append(now)
        return True
    
    return False

def get_rate_limit_info(identifier: str, limit: int, window: int) -> Dict[str, Any]:
    """Get rate limit information."""
    now = time.time()
    window_start = now - window
    
    # Clean old entries
    RATE_LIMITS[identifier] = [timestamp for timestamp in RATE_LIMITS[identifier] if timestamp > window_start]
    
    return {
        "limit": limit,
        "remaining": max(0, limit - len(RATE_LIMITS[identifier])),
        "reset_time": window_start + window,
        "current_requests": len(RATE_LIMITS[identifier])
    }

