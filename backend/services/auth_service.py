"""
Authentication Service für ExamCraft AI
JWT Token Generation, Validation, Refresh Token Logic
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session
import secrets
import logging

from models.auth import User, UserSession, UserStatus
from services.redis_service import SessionStore, TokenBlacklist

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


class AuthService:
    """
    Authentication Service für JWT Token Management
    """
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against a hashed password

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database

        Returns:
            True if password matches, False otherwise
        """
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password
        )

    @staticmethod
    def get_password_hash(password: str) -> str:
        """
        Hash a password using bcrypt

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token
        
        Args:
            data: Data to encode in token (user_id, email, etc.)
            expires_delta: Optional custom expiration time
            
        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        # Add standard JWT claims
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": secrets.token_urlsafe(32)  # JWT ID for token revocation
        })
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT refresh token
        
        Args:
            data: Data to encode in token (user_id, email, etc.)
            expires_delta: Optional custom expiration time
            
        Returns:
            Encoded JWT refresh token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        # Add standard JWT claims
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": secrets.token_urlsafe(32),  # JWT ID for token revocation
            "type": "refresh"  # Mark as refresh token
        })
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate a JWT token
        
        Args:
            token: JWT token to decode
            
        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            return None
    
    @staticmethod
    def create_tokens_for_user(
        user: User,
        db: Session,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Create access and refresh tokens for a user and store session
        
        Args:
            user: User object
            db: Database session
            user_agent: User agent string
            ip_address: IP address
            
        Returns:
            Dictionary with access_token and refresh_token
        """
        # Create token data
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "institution_id": user.institution_id,
            "roles": [role.name for role in user.roles]
        }
        
        # Create tokens
        access_token = AuthService.create_access_token(token_data)
        refresh_token = AuthService.create_refresh_token(token_data)
        
        # Decode tokens to get JTI
        access_payload = AuthService.decode_token(access_token)
        refresh_payload = AuthService.decode_token(refresh_token)
        
        if not access_payload or not refresh_payload:
            raise ValueError("Failed to decode tokens")
        
        # Create session record in database
        session = UserSession(
            user_id=user.id,
            token_jti=access_payload["jti"],
            refresh_token_jti=refresh_payload["jti"],
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=datetime.fromtimestamp(refresh_payload["exp"]),
            is_active=True
        )

        db.add(session)
        db.commit()

        # Also store session in Redis for fast lookup
        try:
            session_store = SessionStore()
            ttl_seconds = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
            session_store.create_session(
                session_id=refresh_payload["jti"],
                user_id=user.id,
                data={
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "access_token_jti": access_payload["jti"]
                },
                ttl_seconds=ttl_seconds
            )
        except Exception as e:
            logger.warning(f"Failed to create Redis session: {str(e)}")

        logger.info(f"Created tokens for user {user.email} (ID: {user.id})")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    @staticmethod
    def refresh_access_token(
        refresh_token: str,
        db: Session,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """
        Refresh an access token using a refresh token
        
        Args:
            refresh_token: Refresh token
            db: Database session
            user_agent: User agent string
            ip_address: IP address
            
        Returns:
            Dictionary with new access_token or None if invalid
        """
        # Decode refresh token
        payload = AuthService.decode_token(refresh_token)
        
        if not payload:
            logger.warning("Invalid refresh token")
            return None
        
        # Check if it's a refresh token
        if payload.get("type") != "refresh":
            logger.warning("Token is not a refresh token")
            return None
        
        # Check if session exists and is active
        session = db.query(UserSession).filter(
            UserSession.refresh_token_jti == payload["jti"],
            UserSession.is_active == True
        ).first()
        
        if not session:
            logger.warning(f"Session not found or inactive for JTI: {payload['jti']}")
            return None
        
        # Check if session is expired
        if session.expires_at < datetime.now(timezone.utc):
            logger.warning(f"Session expired for user {session.user_id}")
            session.is_active = False
            db.commit()
            return None
        
        # Get user
        user = db.query(User).filter(User.id == session.user_id).first()
        
        if not user or user.status != UserStatus.ACTIVE.value:
            logger.warning(f"User not found or inactive: {session.user_id}")
            return None
        
        # Create new access token
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "institution_id": user.institution_id,
            "roles": [role.name for role in user.roles]
        }
        
        access_token = AuthService.create_access_token(token_data)
        access_payload = AuthService.decode_token(access_token)
        
        if not access_payload:
            raise ValueError("Failed to decode new access token")
        
        # Update session with new access token JTI
        session.token_jti = access_payload["jti"]
        session.last_activity_at = datetime.now(timezone.utc)
        db.commit()
        
        logger.info(f"Refreshed access token for user {user.email} (ID: {user.id})")
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    
    @staticmethod
    def revoke_token(token_jti: str, db: Session, ttl_seconds: int = 1800) -> bool:
        """
        Revoke a token by marking its session as inactive

        Args:
            token_jti: JWT ID of token to revoke
            db: Database session
            ttl_seconds: Time until token expires naturally (for Redis blacklist)

        Returns:
            True if token was revoked, False otherwise
        """
        session = db.query(UserSession).filter(
            UserSession.token_jti == token_jti
        ).first()

        if session:
            session.is_active = False
            session.revoked_at = datetime.now(timezone.utc)
            db.commit()

            # Add to Redis blacklist for fast lookup
            try:
                blacklist = TokenBlacklist()
                blacklist.add_token(token_jti, ttl_seconds)
            except Exception as e:
                logger.warning(f"Failed to add token to Redis blacklist: {str(e)}")

            logger.info(f"Revoked token JTI: {token_jti}")
            return True

        logger.warning(f"Token JTI not found: {token_jti}")
        return False
    
    @staticmethod
    def revoke_all_user_sessions(user_id: int, db: Session) -> int:
        """
        Revoke all active sessions for a user (logout from all devices)

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Number of sessions revoked
        """
        sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        ).all()

        count = 0
        for session in sessions:
            session.is_active = False
            session.revoked_at = datetime.now(timezone.utc)

            # Add tokens to Redis blacklist
            try:
                blacklist = TokenBlacklist()
                # Calculate remaining TTL
                remaining_seconds = int((session.expires_at - datetime.now(timezone.utc)).total_seconds())
                if remaining_seconds > 0:
                    blacklist.add_token(session.token_jti, remaining_seconds)
                    if session.refresh_token_jti:
                        blacklist.add_token(session.refresh_token_jti, remaining_seconds)
            except Exception as e:
                logger.warning(f"Failed to add tokens to Redis blacklist: {str(e)}")

            count += 1

        db.commit()

        # Also delete Redis sessions
        try:
            session_store = SessionStore()
            session_store.delete_user_sessions(user_id)
        except Exception as e:
            logger.warning(f"Failed to delete Redis sessions: {str(e)}")

        logger.info(f"Revoked {count} sessions for user {user_id}")

        return count
    
    @staticmethod
    def is_token_revoked(token_jti: str, db: Session) -> bool:
        """
        Check if a token has been revoked

        Args:
            token_jti: JWT ID to check
            db: Database session

        Returns:
            True if token is revoked, False otherwise
        """
        # Fast check: Redis blacklist (cache layer)
        try:
            blacklist = TokenBlacklist()
            if blacklist.is_token_blacklisted(token_jti):
                return True
        except Exception as e:
            logger.warning(f"Redis blacklist check failed: {str(e)}")

        # Fallback: Database check
        session = db.query(UserSession).filter(
            UserSession.token_jti == token_jti
        ).first()

        if not session:
            return True  # Token not found = revoked

        return not session.is_active

