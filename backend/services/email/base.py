"""
Email Base Classes & Interfaces für ExamCraft AI

Definiert die abstrakten Basisklassen und Datenmodelle für den
Hybrid Email Service.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field


class EmailAddress(BaseModel):
    """Email address with optional display name"""

    email: EmailStr
    name: Optional[str] = None

    def __str__(self) -> str:
        """Format as 'Name <email>' or just 'email'"""
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email


class EmailTemplate(BaseModel):
    """Base email template"""

    subject: str
    html: Optional[str] = None
    text: Optional[str] = None


class TransactionalEmail(BaseModel):
    """Transactional email request"""

    to: EmailAddress
    from_address: EmailAddress = Field(alias="from_")
    subject: str
    template: EmailTemplate
    variables: dict[str, Any] = Field(default_factory=dict)
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    reply_to: Optional[EmailAddress] = None
    tags: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class EmailProvider(ABC):
    """Abstract email provider interface"""

    @abstractmethod
    async def send(self, email: Any) -> dict[str, Any]:
        """Send email"""
        pass

    @abstractmethod
    async def get_status(self, email_id: str) -> dict[str, Any]:
        """Get email delivery status"""
        pass


class TransactionalProvider(EmailProvider):
    """Interface for transactional email providers (e.g., Resend)"""

    @abstractmethod
    async def send_transactional(self, email: TransactionalEmail) -> str:
        """
        Send transactional email.

        Args:
            email: TransactionalEmail object with all email details

        Returns:
            str: Email ID from the provider
        """
        pass

    @abstractmethod
    async def send_verification_email(
        self, user_email: str, user_name: str, verification_url: str
    ) -> str:
        """Send account verification email"""
        pass

    @abstractmethod
    async def send_password_reset_email(
        self, user_email: str, user_name: str, reset_url: str
    ) -> str:
        """Send password reset email"""
        pass

    @abstractmethod
    async def send_payment_confirmation(
        self, user_email: str, user_name: str, payment_details: dict[str, Any]
    ) -> str:
        """Send payment confirmation email"""
        pass
