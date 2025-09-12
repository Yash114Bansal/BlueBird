"""
Event Publisher Service for Events Service.
Publishes events to Redis for inter-service communication.
"""

import json
import logging
from typing import Dict, Any
from ..db.redis_client import CacheManager

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Publishes events to Redis channels for inter-service communication.
    """
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.channel_prefix = "evently:events"
    
    async def publish_event_created(self, event):
        """
        Publish event created notification.
        
        Args:
            event: Event object to publish
        """
        try:
            channel = f"{self.channel_prefix}:created"
            message = {
                "type": "event.created",
                "event_id": event.id,
                "event_data": {
                    "id": event.id,
                    "title": event.title,
                    "capacity": event.capacity,
                    "price": float(event.price) if event.price else 0.0,
                    "event_date": event.event_date.isoformat() if event.event_date else None,
                    "created_at": event.created_at.isoformat() if event.created_at else None
                }
            }
            
            await self.cache_manager.redis.publish(channel, json.dumps(message))
            logger.info(f"Published event.created for event {event.id}")
            
        except Exception as e:
            logger.error(f"Failed to publish event.created: {e}")
    
    async def publish_event_updated(self, event):
        """
        Publish event updated notification.
        
        Args:
            event: Event object to publish
        """
        try:
            channel = f"{self.channel_prefix}:updated"
            message = {
                "type": "event.updated",
                "event_id": event.id,
                "event_data": {
                    "id": event.id,
                    "title": event.title,
                    "capacity": event.capacity,
                    "price": float(event.price) if event.price else 0.0,
                    "event_date": event.event_date.isoformat() if event.event_date else None,
                    "updated_at": event.updated_at.isoformat() if event.updated_at else None
                }
            }
            
            await self.cache_manager.redis.publish(channel, json.dumps(message))
            logger.info(f"Published event.updated for event {event.id}")
            
        except Exception as e:
            logger.error(f"Failed to publish event.updated: {e}")
    
    async def publish_event_deleted(self, event_id: int):
        """
        Publish event deleted notification.
        
        Args:
            event_id: ID of the deleted event
        """
        try:
            channel = f"{self.channel_prefix}:deleted"
            message = {
                "type": "event.deleted",
                "event_id": event_id
            }
            
            await self.cache_manager.redis.publish(channel, json.dumps(message))
            logger.info(f"Published event.deleted for event {event_id}")
            
        except Exception as e:
            logger.error(f"Failed to publish event.deleted: {e}")