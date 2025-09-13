"""
Event Subscriber Service for Bookings Service.
Subscribes to Redis events from Events Service and syncs availability data.
"""

import asyncio
import json
import logging
from typing import Dict, Any
from ..db.redis_client import redis_manager
from ..db.database import db_manager
from ..models.booking import EventAvailability
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class EventSubscriber:
    """
    Subscribes to Redis events from Events Service and maintains availability sync.
    """
    
    def __init__(self):
        self.channel_prefix = "evently:events"
        self.running = False
        self.pubsub = None
    
    async def start(self):
        """Start the event subscriber."""
        if self.running:
            return
        
        try:
            await redis_manager.initialize()
            self.pubsub = redis_manager.redis_client.pubsub()
            
            # Subscribe to all event channels
            channels = [
                f"{self.channel_prefix}:created",
                f"{self.channel_prefix}:updated", 
                f"{self.channel_prefix}:deleted"
            ]
            
            await self.pubsub.subscribe(*channels)
            self.running = True
            
            logger.info("Event subscriber started, listening for events...")
            
            # Start listening for messages
            asyncio.create_task(self._listen_for_messages())
            
        except Exception as e:
            logger.error(f"Failed to start event subscriber: {e}")
            raise
    
    async def stop(self):
        """Stop the event subscriber."""
        if not self.running:
            return
        
        self.running = False
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        
        logger.info("Event subscriber stopped")
    
    async def _listen_for_messages(self):
        """Listen for messages from Redis pub/sub."""
        try:
            while self.running:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                
                if message and message['type'] == 'message':
                    await self._handle_message(message)
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in message listener: {e}")
            self.running = False
    
    async def _handle_message(self, message):
        """Handle incoming Redis message."""
        try:
            data = json.loads(message['data'])
            event_type = data.get('type')
            event_id = data.get('event_id')
            
            logger.info(f"Received event: {event_type} for event {event_id}")
            
            if event_type == 'EventCreated':
                await self._handle_event_created(data)
            elif event_type == 'EventUpdated':
                await self._handle_event_updated(data)
            elif event_type == 'EventDeleted':
                await self._handle_event_deleted(event_id)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _handle_event_created(self, data: Dict[str, Any]):
        """Handle event created notification."""
        try:
            event_data = data.get('event_data', {})
            event_id = event_data.get('id')
            capacity = event_data.get('capacity', 0)
            
            if not event_id:
                logger.error("Event ID missing in EventCreated data")
                return
            
            # Create EventAvailability record
            with db_manager.get_session() as session:
                # Check if availability already exists
                existing = session.query(EventAvailability).filter(
                    EventAvailability.event_id == event_id
                ).first()
                
                if existing:
                    logger.info(f"EventAvailability already exists for event {event_id}")
                    return
                
                # Create new availability record
                availability = EventAvailability(
                    event_id=event_id,
                    total_capacity=capacity,
                    available_capacity=capacity,
                    reserved_capacity=0,
                    confirmed_capacity=0,
                    version=1,
                    last_updated=datetime.now(timezone.utc)
                )
                
                session.add(availability)
                session.commit()
                
                logger.info(f"Created EventAvailability for event {event_id} with capacity {capacity}")
                
        except Exception as e:
            logger.error(f"Error handling EventCreated: {e}")
    
    async def _handle_event_updated(self, data: Dict[str, Any]):
        """Handle event updated notification."""
        try:
            event_data = data.get('event_data', {})
            event_id = event_data.get('id')
            new_capacity = event_data.get('capacity')
            
            if not event_id or new_capacity is None:
                logger.error("Event ID or capacity missing in EventUpdated data")
                return
            
            # Update EventAvailability record
            with db_manager.get_session() as session:
                availability = session.query(EventAvailability).filter(
                    EventAvailability.event_id == event_id
                ).first()
                
                if not availability:
                    logger.warning(f"EventAvailability not found for event {event_id}, creating new one")
                    # Create new availability record
                    availability = EventAvailability(
                        event_id=event_id,
                        total_capacity=new_capacity,
                        available_capacity=new_capacity,
                        reserved_capacity=0,
                        confirmed_capacity=0,
                        version=1,
                        last_updated=datetime.now(timezone.utc)
                    )
                    session.add(availability)
                else:
                    # Update existing record
                    old_capacity = availability.total_capacity
                    capacity_diff = new_capacity - old_capacity
                    
                    availability.total_capacity = new_capacity
                    availability.available_capacity = max(0, availability.available_capacity + capacity_diff)
                    availability.version += 1
                    availability.last_updated = datetime.now(timezone.utc)
                
                session.commit()
                logger.info(f"Updated EventAvailability for event {event_id} to capacity {new_capacity}")
                
        except Exception as e:
            logger.error(f"Error handling EventUpdated: {e}")
    
    async def _handle_event_deleted(self, event_id: int):
        """Handle event deleted notification."""
        try:
            # Delete EventAvailability record
            with db_manager.get_session() as session:
                availability = session.query(EventAvailability).filter(
                    EventAvailability.event_id == event_id
                ).first()
                
                if availability:
                    session.delete(availability)
                    session.commit()
                    logger.info(f"Deleted EventAvailability for event {event_id}")
                else:
                    logger.info(f"EventAvailability not found for deleted event {event_id}")
                    
        except Exception as e:
            logger.error(f"Error handling EventDeleted: {e}")


# Global subscriber instance
event_subscriber = EventSubscriber()