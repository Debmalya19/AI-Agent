"""
Session management utilities for unified authentication system.
Provides utilities for session creation, validation, cleanup, and management.
"""

import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .database import get_db
from .unified_models import UnifiedUser, UnifiedUserSession
from .unified_auth import auth_service, AuthenticatedUser

logger = logging.getLogger(__name__)

class SessionUtils:
    """Utilities for managing user sessions across the unified system"""
    
    @staticmethod
    def get_active_sessions_count(user_id: int, db: Session) -> int:
        """Get count of active sessions for a user"""
        try:
            return db.query(UnifiedUserSession).filter(
                UnifiedUserSession.user_id == user_id,
                UnifiedUserSession.is_active == True,
                UnifiedUserSession.expires_at > datetime.now(timezone.utc)
            ).count()
        except Exception as e:
            logger.error(f"Error getting active sessions count: {e}")
            return 0
    
    @staticmethod
    def get_user_sessions(user_id: int, db: Session, 
                         include_expired: bool = False) -> List[UnifiedUserSession]:
        """Get all sessions for a user"""
        try:
            query = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.user_id == user_id
            )
            
            if not include_expired:
                query = query.filter(
                    UnifiedUserSession.is_active == True,
                    UnifiedUserSession.expires_at > datetime.now(timezone.utc)
                )
            
            return query.order_by(UnifiedUserSession.last_accessed.desc()).all()
            
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []
    
    @staticmethod
    def cleanup_expired_sessions(db: Session) -> int:
        """Clean up expired sessions"""
        try:
            expired_count = db.query(UnifiedUserSession).filter(
                or_(
                    UnifiedUserSession.expires_at < datetime.now(timezone.utc),
                    UnifiedUserSession.is_active == False
                )
            ).count()
            
            # Mark expired sessions as inactive
            db.query(UnifiedUserSession).filter(
                UnifiedUserSession.expires_at < datetime.now(timezone.utc)
            ).update({"is_active": False})
            
            db.commit()
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired sessions")
            
            return expired_count
            
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")
            db.rollback()
            return 0
    
    @staticmethod
    def cleanup_old_sessions(db: Session, days_old: int = 30) -> int:
        """Remove old inactive sessions from database"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            
            old_sessions = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.is_active == False,
                UnifiedUserSession.created_at < cutoff_date
            )
            
            count = old_sessions.count()
            old_sessions.delete()
            db.commit()
            
            if count > 0:
                logger.info(f"Removed {count} old sessions")
            
            return count
            
        except Exception as e:
            logger.error(f"Old session cleanup error: {e}")
            db.rollback()
            return 0
    
    @staticmethod
    def extend_session(session_token: str, db: Session, 
                      extend_hours: int = 24) -> bool:
        """Extend session expiration time"""
        try:
            session = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.session_id == session_token,
                UnifiedUserSession.is_active == True
            ).first()
            
            if not session:
                return False
            
            # Extend expiration
            session.expires_at = datetime.now(timezone.utc) + timedelta(hours=extend_hours)
            session.last_accessed = datetime.now(timezone.utc)
            
            db.commit()
            
            logger.debug(f"Extended session {session_token[:8]}... by {extend_hours} hours")
            return True
            
        except Exception as e:
            logger.error(f"Session extension error: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def get_session_info(session_token: str, db: Session) -> Optional[Dict[str, Any]]:
        """Get detailed session information"""
        try:
            session = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.session_id == session_token
            ).first()
            
            if not session:
                return None
            
            user = db.query(UnifiedUser).filter(
                UnifiedUser.id == session.user_id
            ).first()
            
            return {
                "session_id": session.session_id,
                "user_id": user.user_id if user else None,
                "username": user.username if user else None,
                "created_at": session.created_at,
                "expires_at": session.expires_at,
                "last_accessed": session.last_accessed,
                "is_active": session.is_active,
                "is_expired": session.expires_at < datetime.now(timezone.utc),
                "time_remaining": (session.expires_at - datetime.now(timezone.utc)).total_seconds() if session.expires_at > datetime.now(timezone.utc) else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return None
    
    @staticmethod
    def invalidate_user_sessions_except(user_id: int, keep_session_token: str, 
                                      db: Session) -> int:
        """Invalidate all user sessions except the specified one"""
        try:
            count = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.user_id == user_id,
                UnifiedUserSession.session_id != keep_session_token,
                UnifiedUserSession.is_active == True
            ).update({"is_active": False})
            
            db.commit()
            
            if count > 0:
                logger.info(f"Invalidated {count} sessions for user {user_id}")
            
            return count
            
        except Exception as e:
            logger.error(f"Session invalidation error: {e}")
            db.rollback()
            return 0
    
    @staticmethod
    def get_concurrent_sessions_limit() -> int:
        """Get maximum concurrent sessions per user"""
        # This could be configurable per user role or system-wide
        return 5
    
    @staticmethod
    def enforce_session_limit(user_id: int, db: Session) -> bool:
        """Enforce concurrent session limit for user"""
        try:
            limit = SessionUtils.get_concurrent_sessions_limit()
            active_sessions = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.user_id == user_id,
                UnifiedUserSession.is_active == True,
                UnifiedUserSession.expires_at > datetime.now(timezone.utc)
            ).order_by(UnifiedUserSession.last_accessed.desc()).all()
            
            if len(active_sessions) > limit:
                # Invalidate oldest sessions
                sessions_to_invalidate = active_sessions[limit:]
                for session in sessions_to_invalidate:
                    session.is_active = False
                
                db.commit()
                
                logger.info(f"Invalidated {len(sessions_to_invalidate)} excess sessions for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Session limit enforcement error: {e}")
            db.rollback()
            return False

class SessionMonitor:
    """Monitor and manage session health across the system"""
    
    def __init__(self):
        self.cleanup_interval = 3600  # 1 hour
        self.is_running = False
    
    async def start_monitoring(self):
        """Start background session monitoring"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("Starting session monitoring")
        
        while self.is_running:
            try:
                await self._cleanup_cycle()
                await asyncio.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Session monitoring error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def stop_monitoring(self):
        """Stop background session monitoring"""
        self.is_running = False
        logger.info("Stopping session monitoring")
    
    async def _cleanup_cycle(self):
        """Perform cleanup cycle"""
        db = next(get_db())
        try:
            # Clean up expired sessions
            expired_count = SessionUtils.cleanup_expired_sessions(db)
            
            # Clean up old sessions (older than 30 days)
            old_count = SessionUtils.cleanup_old_sessions(db, days_old=30)
            
            # Get session statistics
            total_sessions = db.query(UnifiedUserSession).count()
            active_sessions = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.is_active == True,
                UnifiedUserSession.expires_at > datetime.now(timezone.utc)
            ).count()
            
            logger.debug(
                f"Session cleanup: {expired_count} expired, {old_count} old removed. "
                f"Active: {active_sessions}, Total: {total_sessions}"
            )
            
        except Exception as e:
            logger.error(f"Cleanup cycle error: {e}")
        finally:
            db.close()

class SessionSecurity:
    """Security utilities for session management"""
    
    @staticmethod
    def detect_suspicious_activity(user_id: int, db: Session) -> List[Dict[str, Any]]:
        """Detect suspicious session activity"""
        suspicious_activities = []
        
        try:
            # Get recent sessions
            recent_sessions = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.user_id == user_id,
                UnifiedUserSession.created_at > datetime.now(timezone.utc) - timedelta(hours=24)
            ).all()
            
            # Check for too many sessions created
            if len(recent_sessions) > 10:
                suspicious_activities.append({
                    "type": "excessive_sessions",
                    "description": f"User created {len(recent_sessions)} sessions in 24 hours",
                    "severity": "medium"
                })
            
            # Check for concurrent sessions from different locations (if we had IP tracking)
            active_sessions = [s for s in recent_sessions if s.is_active]
            if len(active_sessions) > 5:
                suspicious_activities.append({
                    "type": "concurrent_sessions",
                    "description": f"User has {len(active_sessions)} concurrent active sessions",
                    "severity": "low"
                })
            
            return suspicious_activities
            
        except Exception as e:
            logger.error(f"Suspicious activity detection error: {e}")
            return []
    
    @staticmethod
    def force_user_logout(user_id: int, reason: str, db: Session) -> bool:
        """Force logout all user sessions with reason"""
        try:
            count = db.query(UnifiedUserSession).filter(
                UnifiedUserSession.user_id == user_id,
                UnifiedUserSession.is_active == True
            ).update({"is_active": False})
            
            db.commit()
            
            logger.warning(f"Force logged out user {user_id}: {reason}. {count} sessions invalidated.")
            return True
            
        except Exception as e:
            logger.error(f"Force logout error: {e}")
            db.rollback()
            return False

# Global session monitor instance
session_monitor = SessionMonitor()

# Utility functions for FastAPI integration
def get_session_from_request(request) -> Optional[str]:
    """Extract session token from request"""
    # Try cookie first
    session_token = request.cookies.get("session_token")
    if session_token:
        return session_token
    
    # Try header
    session_header = request.headers.get("X-Session-Token")
    if session_header:
        return session_header
    
    return None

def validate_session_security(session_token: str, db: Session) -> Dict[str, Any]:
    """Validate session security and return security info"""
    session_info = SessionUtils.get_session_info(session_token, db)
    
    if not session_info:
        return {"valid": False, "reason": "Session not found"}
    
    if not session_info["is_active"]:
        return {"valid": False, "reason": "Session inactive"}
    
    if session_info["is_expired"]:
        return {"valid": False, "reason": "Session expired"}
    
    # Check if session is about to expire (within 1 hour)
    time_remaining = session_info["time_remaining"]
    warning_threshold = 3600  # 1 hour
    
    return {
        "valid": True,
        "expires_soon": time_remaining < warning_threshold,
        "time_remaining": time_remaining,
        "session_info": session_info
    }

# Background task for session cleanup
async def periodic_session_cleanup():
    """Periodic session cleanup task"""
    await session_monitor.start_monitoring()