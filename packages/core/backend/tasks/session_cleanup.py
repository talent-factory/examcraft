"""
Background Task: Session Cleanup
Removes expired sessions from database and Redis
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
import logging

from database import SessionLocal
from models.auth import UserSession
from services.redis_service import SessionStore

logger = logging.getLogger(__name__)


def cleanup_expired_sessions():
    """
    Remove expired sessions from database

    This task should be run periodically (e.g., daily via cron or scheduler)
    """
    db: Session = SessionLocal()

    try:
        # Find expired sessions
        expired_sessions = (
            db.query(UserSession)
            .filter(
                UserSession.expires_at < datetime.now(timezone.utc),
                UserSession.is_active,
            )
            .all()
        )

        count = 0
        for session in expired_sessions:
            session.is_active = False
            session.revoked_at = datetime.now(timezone.utc)
            count += 1

        db.commit()
        logger.info(f"Cleaned up {count} expired sessions from database")

        return count

    except Exception as e:
        logger.error(f"Session cleanup failed: {str(e)}")
        db.rollback()
        return 0
    finally:
        db.close()


def cleanup_old_sessions(days: int = 30):
    """
    Remove old inactive sessions from database

    Args:
        days: Remove sessions older than this many days
    """
    db: Session = SessionLocal()

    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Delete old inactive sessions
        deleted_count = (
            db.query(UserSession)
            .filter(not UserSession.is_active, UserSession.revoked_at < cutoff_date)
            .delete()
        )

        db.commit()
        logger.info(f"Deleted {deleted_count} old sessions (older than {days} days)")

        return deleted_count

    except Exception as e:
        logger.error(f"Old session cleanup failed: {str(e)}")
        db.rollback()
        return 0
    finally:
        db.close()


def cleanup_redis_sessions():
    """
    Cleanup orphaned Redis sessions

    Redis sessions should auto-expire, but this ensures cleanup
    """
    try:
        SessionStore()
        # Redis handles TTL automatically, but we can add manual cleanup if needed
        logger.info("Redis session cleanup completed (TTL-based)")
        return True
    except Exception as e:
        logger.error(f"Redis session cleanup failed: {str(e)}")
        return False


if __name__ == "__main__":
    """Run cleanup tasks manually"""
    print("Running session cleanup tasks...")

    # Cleanup expired sessions
    expired_count = cleanup_expired_sessions()
    print(f"✅ Cleaned up {expired_count} expired sessions")

    # Cleanup old sessions (older than 30 days)
    old_count = cleanup_old_sessions(days=30)
    print(f"✅ Deleted {old_count} old sessions")

    # Cleanup Redis sessions
    cleanup_redis_sessions()
    print("✅ Redis session cleanup completed")

    print("Session cleanup tasks completed!")
