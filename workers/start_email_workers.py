#!/usr/bin/env python3
"""
Start email workers for Evently platform.
This script starts Celery workers to process email notification tasks.
"""

import os
import sys
import subprocess
import logging

# Add workers directory to Python path
workers_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, workers_dir)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def start_email_workers():
    """Start email notification workers."""
    try:
        logger.info("Starting email notification workers...")
        
        # Check if ZERO_TOKEN is set
        if not os.getenv('ZERO_TOKEN'):
            logger.error("ZERO_TOKEN environment variable is required")
            return False
        
        # Start Celery worker for email notifications
        cmd = [
            'celery',
            '-A', 'email_workers.tasks',
            'worker',
            '--loglevel=info',
            '--queues=email_notifications',
            '--concurrency=4',
            '--hostname=email-worker@%h'
        ]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        subprocess.run(cmd, cwd=workers_dir)
        
        return True
        
    except KeyboardInterrupt:
        logger.info("Stopping email workers...")
        return True
    except Exception as e:
        logger.error(f"Failed to start email workers: {e}")
        return False


def start_worker_monitor():
    """Start Celery flower for monitoring workers."""
    try:
        logger.info("Starting worker monitor (Flower)...")
        
        cmd = [
            'celery',
            '-A', 'email_workers.tasks',
            'flower',
            '--port=5555',
            '--broker=redis://localhost:6379/0'
        ]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        subprocess.run(cmd, cwd=workers_dir)
        
        return True
        
    except KeyboardInterrupt:
        logger.info("Stopping worker monitor...")
        return True
    except Exception as e:
        logger.error(f"Failed to start worker monitor: {e}")
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Start Evently email workers')
    parser.add_argument('--monitor', action='store_true', help='Start worker monitor (Flower)')
    
    args = parser.parse_args()
    
    if args.monitor:
        start_worker_monitor()
    else:
        start_email_workers()