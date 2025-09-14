"""
Logging utilities for workers.
Provides standardized logging configuration and helpers.
"""

import logging
import sys
from typing import Optional, Dict, Any
from datetime import datetime


def setup_logging(level: str = "INFO", service_name: str = "worker") -> logging.Logger:
    """
    Setup standardized logging for workers.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        service_name: Name of the service for log identification
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    
    # Create formatter
    formatter = logging.Formatter(
        f'[%(asctime)s] {service_name.upper()}: %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger


def log_task_start(task_name: str, task_id: str, user_id: Optional[int] = None) -> None:
    """
    Log task start with standard format.
    
    Args:
        task_name: Name of the task
        task_id: Celery task ID
        user_id: User ID if applicable
    """
    logger = logging.getLogger(task_name.split('.')[0])
    log_data = {
        'task': task_name,
        'task_id': task_id,
        'status': 'started',
        'timestamp': datetime.now().isoformat()
    }
    
    if user_id:
        log_data['user_id'] = user_id
    
    logger.info(f"Task started: {log_data}")


def log_task_success(task_name: str, task_id: str, result: Dict[str, Any]) -> None:
    """
    Log task success with standard format.
    
    Args:
        task_name: Name of the task
        task_id: Celery task ID
        result: Task result data
    """
    logger = logging.getLogger(task_name.split('.')[0])
    log_data = {
        'task': task_name,
        'task_id': task_id,
        'status': 'completed',
        'result': result,
        'timestamp': datetime.now().isoformat()
    }
    
    logger.info(f"Task completed: {log_data}")


def log_task_error(task_name: str, task_id: str, error: str, retry_count: int = 0) -> None:
    """
    Log task error with standard format.
    
    Args:
        task_name: Name of the task
        task_id: Celery task ID
        error: Error message
        retry_count: Number of retries attempted
    """
    logger = logging.getLogger(task_name.split('.')[0])
    log_data = {
        'task': task_name,
        'task_id': task_id,
        'status': 'failed',
        'error': error,
        'retry_count': retry_count,
        'timestamp': datetime.now().isoformat()
    }
    
    logger.error(f"Task failed: {log_data}")


def log_email_sent(to_email: str, subject: str, task_name: str) -> None:
    """
    Log email sent with standard format.
    
    Args:
        to_email: Recipient email
        subject: Email subject
        task_name: Name of the email task
    """
    logger = logging.getLogger('email')
    log_data = {
        'action': 'email_sent',
        'to': to_email,
        'subject': subject,
        'task': task_name,
        'timestamp': datetime.now().isoformat()
    }
    
    logger.info(f"Email sent: {log_data}")


def log_email_failed(to_email: str, subject: str, error: str, task_name: str) -> None:
    """
    Log email failure with standard format.
    
    Args:
        to_email: Recipient email
        subject: Email subject
        error: Error message
        task_name: Name of the email task
    """
    logger = logging.getLogger('email')
    log_data = {
        'action': 'email_failed',
        'to': to_email,
        'subject': subject,
        'error': error,
        'task': task_name,
        'timestamp': datetime.now().isoformat()
    }
    
    logger.error(f"Email failed: {log_data}")


def log_database_query(query_type: str, user_id: Optional[int] = None, success: bool = True, 
                      error: Optional[str] = None) -> None:
    """
    Log database query with standard format.
    
    Args:
        query_type: Type of database query (e.g., 'get_user_email')
        user_id: User ID if applicable
        success: Whether query was successful
        error: Error message if query failed
    """
    logger = logging.getLogger('database')
    log_data = {
        'action': 'database_query',
        'query_type': query_type,
        'success': success,
        'timestamp': datetime.now().isoformat()
    }
    
    if user_id:
        log_data['user_id'] = user_id
    
    if error:
        log_data['error'] = error
    
    if success:
        logger.info(f"Database query: {log_data}")
    else:
        logger.error(f"Database query failed: {log_data}")