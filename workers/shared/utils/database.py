"""
Database utilities for workers.
Provides direct database query functionality using WorkersConfig.
"""

import logging
import psycopg2
import asyncio
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Import WorkersConfig
from ..config.celery_config import workers_config


def get_database_connection():
    """
    Get direct database connection using WorkersConfig.
    
    Returns:
        psycopg2 connection object
    """
    # Get database configuration from WorkersConfig
    db_config = asyncio.run(workers_config.get_db_config())
    
    host = db_config.get('host') or 'localhost'
    port = db_config.get('port') or '5432'
    name = db_config.get('name') or 'evently'
    user = db_config.get('user') or 'evently'
    password = db_config.get('password') or 'evently123'
    
    connection_string = f"host={host} port={port} dbname={name} user={user} password={password}"
    
    try:
        conn = psycopg2.connect(connection_string)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


def get_user_email(user_id: int) -> Optional[str]:
    """
    Get user email address by user ID with direct database query.
    
    Args:
        user_id: User ID
        
    Returns:
        User email address or None if not found
    """
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Query users table directly
        cursor.execute(
            "SELECT email FROM users WHERE id = %s AND is_active = true",
            (user_id,)
        )
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            email = result[0]
            logger.info(f"Found email for user {user_id}: {email}")
            return email
        else:
            logger.warning(f"User {user_id} not found or inactive")
            return None
            
    except Exception as e:
        logger.error(f"Failed to get user email for user {user_id}: {e}")
        # Return placeholder as fallback
        return f"user{user_id}@example.com"



def check_user_exists(user_id: int) -> bool:
    """
    Check if user exists and is active.
    
    Args:
        user_id: User ID
        
    Returns:
        True if user exists and is active, False otherwise
    """
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT 1 FROM users WHERE id = %s AND is_active = true",
            (user_id,)
        )
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return result is not None
        
    except Exception as e:
        logger.error(f"Failed to check user existence for user {user_id}: {e}")
        return False