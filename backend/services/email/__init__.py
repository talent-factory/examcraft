"""
Email Services Module für ExamCraft AI

Hybrid Email Strategy:
- Resend: Transactional Emails (Verification, Password Reset, Notifications)
- Kit: Marketing Automation (Welcome Series, Nurture Campaigns) - Future

Aktuell implementiert: Resend Transactional Service
"""

from .base import (
    EmailAddress,
    EmailTemplate,
    TransactionalEmail,
    EmailProvider,
    TransactionalProvider,
)
from .resend_service import ResendService
from .email_service import EmailService, email_service

__all__ = [
    # Base classes
    "EmailAddress",
    "EmailTemplate",
    "TransactionalEmail",
    "EmailProvider",
    "TransactionalProvider",
    # Services
    "ResendService",
    "EmailService",
    "email_service",
]
