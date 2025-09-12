"""
Availability Service for high consistency capacity management.
Handles real-time availability tracking and capacity operations.
"""

import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, update, and_, or_
import logging

from app.core.config import config
from app.db.database import db_manager
from app.db.redis_client import redis_manager, get_distributed_lock
from app.models.booking import EventAvailability

logger = logging.getLogger(__name__)


class AvailabilityService:
    """
    High consistency availability service for capacity management.
    Implements distributed locking and real-time capacity tracking.
    """
    
    def __init__(self):
        self.consistency_config = None
        self.cache_config = None
    
    async def _get_configs(self):
        """Get configuration settings."""
        if not self.consistency_config:
            self.consistency_config = await config.get_consistency_config()
        if not self.cache_config:
            self.cache_config = await config.get_cache_config()
    
    async def get_event_availability(
        self, 
        event_id: int, 
        use_cache: bool = True
    ) -> Optional[EventAvailability]:
        """
        Get current availability for an event.
        
        Args:
            event_id: ID of the event
            use_cache: Whether to use Redis cache
            
        Returns:
            EventAvailability object or None if not found
        """
        await self._get_configs()
        
        # Try cache first if enabled
        if use_cache:
            cache_key = f"availability:event:{event_id}"
            cached_data = await redis_manager.get_json(cache_key)
            
            if cached_data:
                # Convert cached data back to EventAvailability object
                availability = EventAvailability()
                availability.event_id = cached_data["event_id"]
                availability.total_capacity = cached_data["total_capacity"]
                availability.available_capacity = cached_data["available_capacity"]
                availability.reserved_capacity = cached_data["reserved_capacity"]
                availability.confirmed_capacity = cached_data["confirmed_capacity"]
                availability.version = cached_data["version"]
                availability.last_updated = datetime.fromisoformat(cached_data["last_updated"])
                return availability
        
        # Get from database
        with db_manager.get_session() as session:
            availability = session.query(EventAvailability).filter(
                EventAvailability.event_id == event_id
            ).first()
            
            # Cache the result
            if availability and use_cache:
                await self._cache_availability(event_id, availability)
            
            return availability
    
    async def _cache_availability(self, event_id: int, availability: EventAvailability):
        """Cache availability data in Redis."""
        cache_key = f"availability:event:{event_id}"
        cache_data = availability.to_dict()
        
        await redis_manager.set_json(
            cache_key, 
            cache_data, 
            ttl=self.cache_config["availability_ttl"]
        )
    
    async def check_availability(
        self, 
        event_id: int, 
        quantity: int
    ) -> Tuple[bool, Optional[EventAvailability]]:
        """
        Check if requested quantity is available for an event.
        
        Args:
            event_id: ID of the event
            quantity: Quantity to check
            
        Returns:
            Tuple of (is_available, availability_object)
        """
        availability = await self.get_event_availability(event_id)
        
        if not availability:
            return False, None
        
        is_available = availability.available_capacity >= quantity
        return is_available, availability
    
    async def reserve_capacity(
        self, 
        event_id: int, 
        quantity: int,
        timeout_seconds: int = 30
    ) -> Tuple[bool, Optional[EventAvailability]]:
        """
        Reserve capacity for an event with distributed locking.
        
        Args:
            event_id: ID of the event
            quantity: Quantity to reserve
            timeout_seconds: Lock timeout in seconds
            
        Returns:
            Tuple of (success, updated_availability)
        """
        await self._get_configs()
        
        lock_key = f"availability:reserve:{event_id}"
        
        async with get_distributed_lock(lock_key, timeout=timeout_seconds) as lock:
            try:
                with db_manager.get_transaction_session() as session:
                    # Get current availability with optimistic locking
                    availability = session.query(EventAvailability).filter(
                        EventAvailability.event_id == event_id
                    ).first()
                    
                    if not availability:
                        logger.warning(f"Availability record not found for event {event_id}")
                        return False, None
                    
                    # Check if enough capacity is available
                    if availability.available_capacity < quantity:
                        return False, availability
                    
                    # Reserve capacity with optimistic locking
                    result = session.query(EventAvailability).filter(
                        and_(
                            EventAvailability.event_id == event_id,
                            EventAvailability.version == availability.version,
                            EventAvailability.available_capacity >= quantity
                        )
                    ).update({
                        EventAvailability.available_capacity: EventAvailability.available_capacity - quantity,
                        EventAvailability.reserved_capacity: EventAvailability.reserved_capacity + quantity,
                        EventAvailability.version: EventAvailability.version + 1
                    })
                    
                    if result > 0:
                        # Get updated availability
                        updated_availability = session.query(EventAvailability).filter(
                            EventAvailability.event_id == event_id
                        ).first()
                        
                        # Invalidate cache
                        await self._invalidate_availability_cache(event_id)
                        
                        logger.info(f"Reserved {quantity} capacity for event {event_id}")
                        return True, updated_availability
                    else:
                        logger.warning(f"Failed to reserve capacity for event {event_id} - optimistic lock failed")
                        return False, availability
                        
            except Exception as e:
                logger.error(f"Failed to reserve capacity for event {event_id}: {e}")
                return False, None
    
    async def confirm_capacity(
        self, 
        event_id: int, 
        quantity: int
    ) -> Tuple[bool, Optional[EventAvailability]]:
        """
        Confirm reserved capacity (move from reserved to confirmed).
        
        Args:
            event_id: ID of the event
            quantity: Quantity to confirm
            
        Returns:
            Tuple of (success, updated_availability)
        """
        await self._get_configs()
        
        lock_key = f"availability:confirm:{event_id}"
        
        async with get_distributed_lock(lock_key, timeout=self.consistency_config["lock_timeout_seconds"]) as lock:
            try:
                with db_manager.get_transaction_session() as session:
                    # Get current availability
                    availability = session.query(EventAvailability).filter(
                        EventAvailability.event_id == event_id
                    ).first()
                    
                    if not availability:
                        return False, None
                    
                    # Check if enough reserved capacity exists
                    if availability.reserved_capacity < quantity:
                        return False, availability
                    
                    # Move from reserved to confirmed
                    result = session.query(EventAvailability).filter(
                        and_(
                            EventAvailability.event_id == event_id,
                            EventAvailability.version == availability.version,
                            EventAvailability.reserved_capacity >= quantity
                        )
                    ).update({
                        EventAvailability.reserved_capacity: EventAvailability.reserved_capacity - quantity,
                        EventAvailability.confirmed_capacity: EventAvailability.confirmed_capacity + quantity,
                        EventAvailability.version: EventAvailability.version + 1
                    })
                    
                    if result > 0:
                        # Get updated availability
                        updated_availability = session.query(EventAvailability).filter(
                            EventAvailability.event_id == event_id
                        ).first()
                        
                        # Invalidate cache
                        await self._invalidate_availability_cache(event_id)
                        
                        logger.info(f"Confirmed {quantity} capacity for event {event_id}")
                        return True, updated_availability
                    else:
                        return False, availability
                        
            except Exception as e:
                logger.error(f"Failed to confirm capacity for event {event_id}: {e}")
                return False, None
    
    async def release_capacity(
        self, 
        event_id: int, 
        quantity: int,
        capacity_type: str = "reserved"
    ) -> Tuple[bool, Optional[EventAvailability]]:
        """
        Release capacity back to available.
        
        Args:
            event_id: ID of the event
            quantity: Quantity to release
            capacity_type: Type of capacity to release ("reserved" or "confirmed")
            
        Returns:
            Tuple of (success, updated_availability)
        """
        await self._get_configs()
        
        lock_key = f"availability:release:{event_id}"
        
        async with get_distributed_lock(lock_key, timeout=self.consistency_config["lock_timeout_seconds"]) as lock:
            try:
                with db_manager.get_transaction_session() as session:
                    # Get current availability
                    availability = session.query(EventAvailability).filter(
                        EventAvailability.event_id == event_id
                    ).first()
                    
                    if not availability:
                        return False, None
                    
                    # Prepare update based on capacity type
                    update_data = {
                        EventAvailability.available_capacity: EventAvailability.available_capacity + quantity,
                        EventAvailability.version: EventAvailability.version + 1
                    }
                    
                    if capacity_type == "reserved":
                        if availability.reserved_capacity < quantity:
                            return False, availability
                        update_data[EventAvailability.reserved_capacity] = EventAvailability.reserved_capacity - quantity
                    elif capacity_type == "confirmed":
                        if availability.confirmed_capacity < quantity:
                            return False, availability
                        update_data[EventAvailability.confirmed_capacity] = EventAvailability.confirmed_capacity - quantity
                    else:
                        raise ValueError(f"Invalid capacity type: {capacity_type}")
                    
                    # Release capacity
                    result = session.query(EventAvailability).filter(
                        and_(
                            EventAvailability.event_id == event_id,
                            EventAvailability.version == availability.version
                        )
                    ).update(update_data)
                    
                    if result > 0:
                        # Get updated availability
                        updated_availability = session.query(EventAvailability).filter(
                            EventAvailability.event_id == event_id
                        ).first()
                        
                        # Invalidate cache
                        await self._invalidate_availability_cache(event_id)
                        
                        logger.info(f"Released {quantity} {capacity_type} capacity for event {event_id}")
                        return True, updated_availability
                    else:
                        return False, availability
                        
            except Exception as e:
                logger.error(f"Failed to release capacity for event {event_id}: {e}")
                return False, None
    
    async def _invalidate_availability_cache(self, event_id: int):
        """Invalidate availability cache for an event."""
        cache_key = f"availability:event:{event_id}"
        await redis_manager.delete(cache_key)
    
    async def create_event_availability(
        self, 
        event_id: int, 
        total_capacity: int
    ) -> EventAvailability:
        """
        Create availability record for a new event.
        
        Args:
            event_id: ID of the event
            total_capacity: Total capacity for the event
            
        Returns:
            Created EventAvailability object
        """
        await self._get_configs()
        
        lock_key = f"availability:create:{event_id}"
        
        async with get_distributed_lock(lock_key, timeout=self.consistency_config["lock_timeout_seconds"]) as lock:
            try:
                with db_manager.get_transaction_session() as session:
                    # Check if availability record already exists
                    existing = session.query(EventAvailability).filter(
                        EventAvailability.event_id == event_id
                    ).first()
                    
                    if existing:
                        raise Exception(f"Availability record already exists for event {event_id}")
                    
                    # Create new availability record
                    availability = EventAvailability(
                        event_id=event_id,
                        total_capacity=total_capacity,
                        available_capacity=total_capacity,
                        reserved_capacity=0,
                        confirmed_capacity=0,
                        version=1
                    )
                    
                    session.add(availability)
                    session.commit()
                    
                    # Cache the new availability
                    await self._cache_availability(event_id, availability)
                    
                    logger.info(f"Created availability record for event {event_id} with capacity {total_capacity}")
                    return availability
                    
            except Exception as e:
                logger.error(f"Failed to create availability for event {event_id}: {e}")
                raise
    
    async def update_event_capacity(
        self, 
        event_id: int, 
        new_total_capacity: int
    ) -> Tuple[bool, Optional[EventAvailability]]:
        """
        Update total capacity for an event.
        
        Args:
            event_id: ID of the event
            new_total_capacity: New total capacity
            
        Returns:
            Tuple of (success, updated_availability)
        """
        await self._get_configs()
        
        lock_key = f"availability:update:{event_id}"
        
        async with get_distributed_lock(lock_key, timeout=self.consistency_config["lock_timeout_seconds"]) as lock:
            try:
                with db_manager.get_transaction_session() as session:
                    # Get current availability
                    availability = session.query(EventAvailability).filter(
                        EventAvailability.event_id == event_id
                    ).first()
                    
                    if not availability:
                        return False, None
                    
                    # Calculate new available capacity
                    current_used = availability.reserved_capacity + availability.confirmed_capacity
                    new_available = max(0, new_total_capacity - current_used)
                    
                    # Update capacity
                    result = session.query(EventAvailability).filter(
                        and_(
                            EventAvailability.event_id == event_id,
                            EventAvailability.version == availability.version
                        )
                    ).update({
                        EventAvailability.total_capacity: new_total_capacity,
                        EventAvailability.available_capacity: new_available,
                        EventAvailability.version: EventAvailability.version + 1
                    })
                    
                    if result > 0:
                        # Get updated availability
                        updated_availability = session.query(EventAvailability).filter(
                            EventAvailability.event_id == event_id
                        ).first()
                        
                        # Invalidate cache
                        await self._invalidate_availability_cache(event_id)
                        
                        logger.info(f"Updated capacity for event {event_id} to {new_total_capacity}")
                        return True, updated_availability
                    else:
                        return False, availability
                        
            except Exception as e:
                logger.error(f"Failed to update capacity for event {event_id}: {e}")
                return False, None
    
    async def get_availability_stats(self) -> Dict[str, Any]:
        """
        Get overall availability statistics.
        
        Returns:
            Dictionary with availability statistics
        """
        with db_manager.get_session() as session:
            # Get total events with availability records
            total_events = session.query(EventAvailability).count()
            
            # Get events with available capacity
            available_events = session.query(EventAvailability).filter(
                EventAvailability.available_capacity > 0
            ).count()
            
            # Get events that are sold out
            sold_out_events = session.query(EventAvailability).filter(
                EventAvailability.available_capacity == 0
            ).count()
            
            # Get total capacity across all events
            total_capacity = session.query(EventAvailability).with_entities(
                EventAvailability.total_capacity
            ).all()
            total_capacity = sum(row[0] for row in total_capacity)
            
            # Get total available capacity
            total_available = session.query(EventAvailability).with_entities(
                EventAvailability.available_capacity
            ).all()
            total_available = sum(row[0] for row in total_available)
            
            # Get total reserved capacity
            total_reserved = session.query(EventAvailability).with_entities(
                EventAvailability.reserved_capacity
            ).all()
            total_reserved = sum(row[0] for row in total_reserved)
            
            # Get total confirmed capacity
            total_confirmed = session.query(EventAvailability).with_entities(
                EventAvailability.confirmed_capacity
            ).all()
            total_confirmed = sum(row[0] for row in total_confirmed)
            
            return {
                "total_events": total_events,
                "available_events": available_events,
                "sold_out_events": sold_out_events,
                "total_capacity": total_capacity,
                "total_available": total_available,
                "total_reserved": total_reserved,
                "total_confirmed": total_confirmed,
                "overall_utilization_percentage": (
                    (total_reserved + total_confirmed) / total_capacity * 100
                    if total_capacity > 0 else 0
                )
            }


# Global service instance
availability_service = AvailabilityService()