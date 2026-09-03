"""
Webhook Handlers für ExamCraft AI

Handles incoming webhooks from:
- SubscribeFlow (transactional email delivery-status events)
"""

from .subscribeflow_webhooks import router as subscribeflow_router

__all__ = ["subscribeflow_router"]
