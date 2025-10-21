"""
Redis Service für ExamCraft AI
Session Management, Token Blacklist, Rate Limiting
"""

import redis
import json
import os
from typing import Optional, Dict, Any
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_DB_SESSIONS = 0  # Database 0 for sessions
REDIS_DB_BLACKLIST = 1  # Database 1 for token blacklist
REDIS_DB_RATELIMIT = 2  # Database 2 for rate limiting


class RedisService:
    """Redis Service für Session Management und Caching"""
    
    _session_client: Optional[redis.Redis] = None
    _blacklist_client: Optional[redis.Redis] = None
    _ratelimit_client: Optional[redis.Redis] = None
    
    @classmethod
    def get_session_client(cls) -> redis.Redis:
        """Get Redis client for session storage"""
        if cls._session_client is None:
            cls._session_client = redis.from_url(
                REDIS_URL,
                db=REDIS_DB_SESSIONS,
                decode_responses=True
            )
            logger.info("Redis session client initialized")
        return cls._session_client
    
    @classmethod
    def get_blacklist_client(cls) -> redis.Redis:
        """Get Redis client for token blacklist"""
        if cls._blacklist_client is None:
            cls._blacklist_client = redis.from_url(
                REDIS_URL,
                db=REDIS_DB_BLACKLIST,
                decode_responses=True
            )
            logger.info("Redis blacklist client initialized")
        return cls._blacklist_client
    
    @classmethod
    def get_ratelimit_client(cls) -> redis.Redis:
        """Get Redis client for rate limiting"""
        if cls._ratelimit_client is None:
            cls._ratelimit_client = redis.from_url(
                REDIS_URL,
                db=REDIS_DB_RATELIMIT,
                decode_responses=True
            )
            logger.info("Redis rate limit client initialized")
        return cls._ratelimit_client
    
    @classmethod
    def close_all(cls):
        """Close all Redis connections"""
        if cls._session_client:
            cls._session_client.close()
            cls._session_client = None
        if cls._blacklist_client:
            cls._blacklist_client.close()
            cls._blacklist_client = None
        if cls._ratelimit_client:
            cls._ratelimit_client.close()
            cls._ratelimit_client = None
        logger.info("All Redis clients closed")


class SessionStore:
    """Redis-based Session Store"""
    
    def __init__(self):
        self.client = RedisService.get_session_client()
    
    def create_session(
        self,
        session_id: str,
        user_id: int,
        data: Dict[str, Any],
        ttl_seconds: int = 604800  # 7 days default
    ) -> bool:
        """
        Create a new session in Redis
        
        Args:
            session_id: Unique session identifier (e.g., refresh token JTI)
            user_id: User ID
            data: Session data (ip_address, user_agent, etc.)
            ttl_seconds: Time to live in seconds (default: 7 days)
            
        Returns:
            True if session created successfully
        """
        try:
            session_key = f"session:{session_id}"
            session_data = {
                "user_id": user_id,
                **data
            }
            
            # Store session with expiration
            self.client.setex(
                session_key,
                ttl_seconds,
                json.dumps(session_data)
            )
            
            # Add to user's session set
            user_sessions_key = f"user_sessions:{user_id}"
            self.client.sadd(user_sessions_key, session_id)
            self.client.expire(user_sessions_key, ttl_seconds)
            
            logger.info(f"Session created: {session_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {str(e)}")
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data from Redis
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data or None if not found
        """
        try:
            session_key = f"session:{session_id}"
            session_data = self.client.get(session_key)
            
            if session_data:
                return json.loads(session_data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {str(e)}")
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from Redis
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session deleted successfully
        """
        try:
            session_key = f"session:{session_id}"
            
            # Get user_id before deleting
            session_data = self.get_session(session_id)
            if session_data:
                user_id = session_data.get("user_id")
                
                # Remove from user's session set
                if user_id:
                    user_sessions_key = f"user_sessions:{user_id}"
                    self.client.srem(user_sessions_key, session_id)
            
            # Delete session
            self.client.delete(session_key)
            logger.info(f"Session deleted: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {str(e)}")
            return False
    
    def delete_user_sessions(self, user_id: int) -> int:
        """
        Delete all sessions for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Number of sessions deleted
        """
        try:
            user_sessions_key = f"user_sessions:{user_id}"
            session_ids = self.client.smembers(user_sessions_key)
            
            count = 0
            for session_id in session_ids:
                if self.delete_session(session_id):
                    count += 1
            
            # Delete user sessions set
            self.client.delete(user_sessions_key)
            
            logger.info(f"Deleted {count} sessions for user {user_id}")
            return count
            
        except Exception as e:
            logger.error(f"Failed to delete user sessions for {user_id}: {str(e)}")
            return 0
    
    def get_user_sessions(self, user_id: int) -> list[str]:
        """
        Get all session IDs for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of session IDs
        """
        try:
            user_sessions_key = f"user_sessions:{user_id}"
            return list(self.client.smembers(user_sessions_key))
        except Exception as e:
            logger.error(f"Failed to get user sessions for {user_id}: {str(e)}")
            return []
    
    def extend_session(self, session_id: str, ttl_seconds: int = 604800) -> bool:
        """
        Extend session expiration time
        
        Args:
            session_id: Session identifier
            ttl_seconds: New time to live in seconds
            
        Returns:
            True if session extended successfully
        """
        try:
            session_key = f"session:{session_id}"
            return self.client.expire(session_key, ttl_seconds)
        except Exception as e:
            logger.error(f"Failed to extend session {session_id}: {str(e)}")
            return False


class TokenBlacklist:
    """Redis-based Token Blacklist for revoked tokens"""
    
    def __init__(self):
        self.client = RedisService.get_blacklist_client()
    
    def add_token(self, token_jti: str, ttl_seconds: int) -> bool:
        """
        Add a token to the blacklist
        
        Args:
            token_jti: JWT Token ID (JTI claim)
            ttl_seconds: Time until token expires naturally
            
        Returns:
            True if token added successfully
        """
        try:
            blacklist_key = f"blacklist:{token_jti}"
            self.client.setex(blacklist_key, ttl_seconds, "1")
            logger.info(f"Token added to blacklist: {token_jti}")
            return True
        except Exception as e:
            logger.error(f"Failed to blacklist token {token_jti}: {str(e)}")
            return False
    
    def is_token_blacklisted(self, token_jti: str) -> bool:
        """
        Check if a token is blacklisted
        
        Args:
            token_jti: JWT Token ID (JTI claim)
            
        Returns:
            True if token is blacklisted
        """
        try:
            blacklist_key = f"blacklist:{token_jti}"
            return self.client.exists(blacklist_key) > 0
        except Exception as e:
            logger.error(f"Failed to check blacklist for {token_jti}: {str(e)}")
            return False

