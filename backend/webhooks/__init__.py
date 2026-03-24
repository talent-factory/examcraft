"""
Webhook Handlers für ExamCraft AI

Handles incoming webhooks from email providers:
- Resend (transactional email events)
- Kit (marketing automation events) - Future
"""

from .resend_webhooks import router as resend_router

__all__ = ["resend_router"]
