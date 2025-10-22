"""
Avatar Service für ExamCraft AI
Proxy für OAuth Avatar URLs mit Redis Caching
"""

import httpx
import logging
from typing import Optional
from services.redis_service import RedisService

logger = logging.getLogger(__name__)

# Avatar Cache Configuration
AVATAR_CACHE_TTL = 86400  # 24 hours in seconds
AVATAR_DOWNLOAD_TIMEOUT = 10  # 10 seconds timeout


class AvatarService:
    """Service für Avatar Download und Caching"""

    def __init__(self):
        self.redis_client = RedisService.get_session_client()

    def get_avatar(self, user_id: int, avatar_url: str) -> Optional[bytes]:
        """
        Get avatar image with caching

        Args:
            user_id: User ID for cache key
            avatar_url: Original avatar URL (e.g., Google OAuth URL)

        Returns:
            Image bytes or None if download fails
        """
        # Check cache first
        cache_key = f"avatar:{user_id}"
        cached_avatar = self._get_cached_avatar(cache_key)

        if cached_avatar:
            logger.info(f"Avatar cache hit for user {user_id}")
            return cached_avatar

        # Download avatar from original URL
        logger.info(f"Avatar cache miss for user {user_id}, downloading from {avatar_url[:50]}...")
        avatar_bytes = self._download_avatar(avatar_url)

        if avatar_bytes:
            # Cache the avatar
            self._cache_avatar(cache_key, avatar_bytes)
            logger.info(f"Avatar cached for user {user_id}")
            return avatar_bytes

        logger.warning(f"Failed to download avatar for user {user_id}")
        return None

    def _get_cached_avatar(self, cache_key: str) -> Optional[bytes]:
        """
        Get avatar from Redis cache

        Args:
            cache_key: Redis cache key

        Returns:
            Image bytes or None if not cached
        """
        try:
            # Redis with decode_responses=False for binary data
            redis_binary = RedisService.get_session_client()
            redis_binary.connection_pool.connection_kwargs["decode_responses"] = False

            cached_data = redis_binary.get(cache_key)
            return cached_data if cached_data else None

        except Exception as e:
            logger.error(f"Failed to get cached avatar {cache_key}: {str(e)}")
            return None

    def _cache_avatar(self, cache_key: str, avatar_bytes: bytes) -> bool:
        """
        Cache avatar in Redis

        Args:
            cache_key: Redis cache key
            avatar_bytes: Image bytes to cache

        Returns:
            True if cached successfully
        """
        try:
            # Redis with decode_responses=False for binary data
            redis_binary = RedisService.get_session_client()
            redis_binary.connection_pool.connection_kwargs["decode_responses"] = False

            redis_binary.setex(cache_key, AVATAR_CACHE_TTL, avatar_bytes)
            return True

        except Exception as e:
            logger.error(f"Failed to cache avatar {cache_key}: {str(e)}")
            return False

    def _download_avatar(self, avatar_url: str) -> Optional[bytes]:
        """
        Download avatar from URL

        Args:
            avatar_url: Avatar URL to download

        Returns:
            Image bytes or None if download fails
        """
        try:
            with httpx.Client(timeout=AVATAR_DOWNLOAD_TIMEOUT) as client:
                response = client.get(avatar_url)
                response.raise_for_status()

                # Validate content type
                content_type = response.headers.get("content-type", "")
                if not content_type.startswith("image/"):
                    logger.warning(f"Invalid content type for avatar: {content_type}")
                    return None

                return response.content

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading avatar: {e.response.status_code}")
            return None
        except httpx.TimeoutException:
            logger.error(f"Timeout downloading avatar from {avatar_url[:50]}")
            return None
        except Exception as e:
            logger.error(f"Failed to download avatar: {str(e)}")
            return None

    def invalidate_cache(self, user_id: int) -> bool:
        """
        Invalidate cached avatar for a user

        Args:
            user_id: User ID

        Returns:
            True if cache invalidated successfully
        """
        try:
            cache_key = f"avatar:{user_id}"
            self.redis_client.delete(cache_key)
            logger.info(f"Avatar cache invalidated for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to invalidate avatar cache for user {user_id}: {str(e)}")
            return False

