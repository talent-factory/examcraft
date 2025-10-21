"""
Audit Logging Service für ExamCraft AI
Implementiert Security & GDPR Compliance Logging
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Request
import logging
import json
from datetime import datetime, timezone

from models.auth import AuditLog, User

logger = logging.getLogger(__name__)


class AuditService:
    """
    Audit Logging Service
    Logs all security-relevant actions for compliance and security monitoring
    """
    
    # Action Types
    ACTION_LOGIN = "login"
    ACTION_LOGOUT = "logout"
    ACTION_REGISTER = "register"
    ACTION_PASSWORD_CHANGE = "password_change"
    ACTION_PASSWORD_RESET = "password_reset"
    ACTION_TOKEN_REFRESH = "token_refresh"
    ACTION_OAUTH_LOGIN = "oauth_login"
    
    ACTION_CREATE_DOCUMENT = "create_document"
    ACTION_DELETE_DOCUMENT = "delete_document"
    ACTION_PROCESS_DOCUMENT = "process_document"
    
    ACTION_CREATE_QUESTION = "create_question"
    ACTION_APPROVE_QUESTION = "approve_question"
    ACTION_REJECT_QUESTION = "reject_question"
    ACTION_EDIT_QUESTION = "edit_question"
    ACTION_DELETE_QUESTION = "delete_question"
    
    ACTION_CREATE_USER = "create_user"
    ACTION_UPDATE_USER = "update_user"
    ACTION_DELETE_USER = "delete_user"
    ACTION_ASSIGN_ROLE = "assign_role"
    ACTION_REMOVE_ROLE = "remove_role"
    
    ACTION_API_ACCESS = "api_access"
    ACTION_PERMISSION_DENIED = "permission_denied"
    ACTION_RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    
    # Status Types
    STATUS_SUCCESS = "success"
    STATUS_FAILURE = "failure"
    STATUS_ERROR = "error"
    
    # Resource Types
    RESOURCE_USER = "user"
    RESOURCE_DOCUMENT = "document"
    RESOURCE_QUESTION = "question"
    RESOURCE_SESSION = "session"
    RESOURCE_ROLE = "role"
    RESOURCE_INSTITUTION = "institution"
    
    @staticmethod
    def log_action(
        db: Session,
        action: str,
        status: str = STATUS_SUCCESS,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        request: Optional[Request] = None
    ) -> AuditLog:
        """
        Log an audit action
        
        Args:
            db: Database session
            action: Action type (use ACTION_* constants)
            status: Action status (use STATUS_* constants)
            user_id: User ID who performed the action
            resource_type: Type of resource affected (use RESOURCE_* constants)
            resource_id: ID of affected resource
            ip_address: Client IP address
            user_agent: Client user agent
            additional_data: Additional data as dict (will be JSON serialized)
            error_message: Error message if status is failure/error
            request: FastAPI Request object (auto-extracts IP and user agent)
            
        Returns:
            Created AuditLog entry
        """
        try:
            # Extract IP and user agent from request if provided
            if request:
                if not ip_address:
                    ip_address = request.client.host if request.client else None
                if not user_agent:
                    user_agent = request.headers.get("user-agent")
            
            # Serialize additional data to JSON
            additional_data_json = None
            if additional_data:
                try:
                    additional_data_json = json.dumps(additional_data)
                except Exception as e:
                    logger.warning(f"Failed to serialize additional_data: {e}")
                    additional_data_json = json.dumps({"error": "Failed to serialize data"})
            
            # Create audit log entry
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else None,  # Truncate to 500 chars
                additional_data=additional_data_json,
                status=status,
                error_message=error_message
            )
            
            db.add(audit_log)
            db.commit()
            db.refresh(audit_log)
            
            logger.info(
                f"Audit log created: action={action}, status={status}, "
                f"user_id={user_id}, resource={resource_type}:{resource_id}"
            )
            
            return audit_log
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            db.rollback()
            # Don't raise exception - audit logging should not break application flow
            return None
    
    @staticmethod
    def log_login(
        db: Session,
        user_id: int,
        success: bool,
        request: Optional[Request] = None,
        error_message: Optional[str] = None,
        login_method: str = "password"
    ) -> AuditLog:
        """Log user login attempt"""
        return AuditService.log_action(
            db=db,
            action=AuditService.ACTION_LOGIN,
            status=AuditService.STATUS_SUCCESS if success else AuditService.STATUS_FAILURE,
            user_id=user_id if success else None,
            resource_type=AuditService.RESOURCE_USER,
            resource_id=str(user_id) if user_id else None,
            request=request,
            error_message=error_message,
            additional_data={"login_method": login_method}
        )
    
    @staticmethod
    def log_logout(
        db: Session,
        user_id: int,
        request: Optional[Request] = None
    ) -> AuditLog:
        """Log user logout"""
        return AuditService.log_action(
            db=db,
            action=AuditService.ACTION_LOGOUT,
            status=AuditService.STATUS_SUCCESS,
            user_id=user_id,
            resource_type=AuditService.RESOURCE_USER,
            resource_id=str(user_id),
            request=request
        )
    
    @staticmethod
    def log_register(
        db: Session,
        user_id: int,
        email: str,
        request: Optional[Request] = None
    ) -> AuditLog:
        """Log user registration"""
        return AuditService.log_action(
            db=db,
            action=AuditService.ACTION_REGISTER,
            status=AuditService.STATUS_SUCCESS,
            user_id=user_id,
            resource_type=AuditService.RESOURCE_USER,
            resource_id=str(user_id),
            request=request,
            additional_data={"email": email}
        )
    
    @staticmethod
    def log_password_change(
        db: Session,
        user_id: int,
        success: bool,
        request: Optional[Request] = None,
        error_message: Optional[str] = None
    ) -> AuditLog:
        """Log password change attempt"""
        return AuditService.log_action(
            db=db,
            action=AuditService.ACTION_PASSWORD_CHANGE,
            status=AuditService.STATUS_SUCCESS if success else AuditService.STATUS_FAILURE,
            user_id=user_id,
            resource_type=AuditService.RESOURCE_USER,
            resource_id=str(user_id),
            request=request,
            error_message=error_message
        )
    
    @staticmethod
    def log_document_action(
        db: Session,
        action: str,
        user_id: int,
        document_id: int,
        success: bool = True,
        request: Optional[Request] = None,
        error_message: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """Log document-related action"""
        return AuditService.log_action(
            db=db,
            action=action,
            status=AuditService.STATUS_SUCCESS if success else AuditService.STATUS_FAILURE,
            user_id=user_id,
            resource_type=AuditService.RESOURCE_DOCUMENT,
            resource_id=str(document_id),
            request=request,
            error_message=error_message,
            additional_data=additional_data
        )
    
    @staticmethod
    def log_question_action(
        db: Session,
        action: str,
        user_id: int,
        question_id: int,
        success: bool = True,
        request: Optional[Request] = None,
        error_message: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """Log question-related action"""
        return AuditService.log_action(
            db=db,
            action=action,
            status=AuditService.STATUS_SUCCESS if success else AuditService.STATUS_FAILURE,
            user_id=user_id,
            resource_type=AuditService.RESOURCE_QUESTION,
            resource_id=str(question_id),
            request=request,
            error_message=error_message,
            additional_data=additional_data
        )
    
    @staticmethod
    def log_permission_denied(
        db: Session,
        user_id: int,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        request: Optional[Request] = None,
        required_permission: Optional[str] = None
    ) -> AuditLog:
        """Log permission denied event"""
        return AuditService.log_action(
            db=db,
            action=AuditService.ACTION_PERMISSION_DENIED,
            status=AuditService.STATUS_FAILURE,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            request=request,
            additional_data={
                "attempted_action": action,
                "required_permission": required_permission
            }
        )
    
    @staticmethod
    def log_rate_limit_exceeded(
        db: Session,
        user_id: Optional[int] = None,
        request: Optional[Request] = None,
        limit_type: str = "ip"
    ) -> AuditLog:
        """Log rate limit exceeded event"""
        return AuditService.log_action(
            db=db,
            action=AuditService.ACTION_RATE_LIMIT_EXCEEDED,
            status=AuditService.STATUS_FAILURE,
            user_id=user_id,
            request=request,
            additional_data={"limit_type": limit_type}
        )

