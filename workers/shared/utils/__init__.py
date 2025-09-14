"""
Shared utilities for workers.
Provides common functionality across all worker types.
"""

from .database import get_user_email
from .email import EmailService, email_service
from .logging import (
    setup_logging, 
    log_task_start, 
    log_task_success, 
    log_task_error,
    log_email_sent,
    log_email_failed,
    log_database_query
)

__all__ = [
    # Database utilities
    'get_user_email',
    'setup_logging',
    'log_task_start',
    'log_task_success', 
    'log_task_error',
    'log_email_sent',
    'log_email_failed',
    'log_database_query'
]