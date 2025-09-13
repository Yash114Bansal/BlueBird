"""
Event subscriber service for Analytics Service.
Handles events from bookings and events services.
"""

import asyncio
import json
import logging
from datetime import datetime, date
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from ..models.analytics import EventStats, DailyStats, TopEvents, SystemMetrics, EventLog
from ..db.database import DatabaseManager
from ..db.redis_client import RedisManager

logger = logging.getLogger(__name__)


class EventSubscriber:
    """
    Event subscriber for analytics data aggregation.
    Processes events from other services and updates analytics tables.
    """
    
    def __init__(self, db_manager: DatabaseManager, redis_manager: RedisManager):
        self.db_manager = db_manager
        self.redis_manager = redis_manager
        self.running = False
        self.pubsub = None
        
        # Channel prefixes for different services
        self.events_channel_prefix = "evently:events"
        self.bookings_channel_prefix = "evently:bookings"
    
    async def process_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        Process incoming event and update analytics.
        
        Args:
            event_type: Type of event (BookingCreated, EventCreated, etc.)
            event_data: Event payload data
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            # Log the event
            await self._log_event(event_type, event_data)
            
            # Process based on event type
            if event_type == "BookingCreated":
                await self._handle_booking_created(event_data)
            elif event_type == "BookingCancelled":
                await self._handle_booking_cancelled(event_data)
            elif event_type == "BookingConfirmed":
                await self._handle_booking_confirmed(event_data)
            elif event_type == "EventCreated":
                await self._handle_event_created(event_data)
            elif event_type == "EventUpdated":
                await self._handle_event_updated(event_data)
            elif event_type == "EventDeleted":
                await self._handle_event_deleted(event_data)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return False
            
            # Update top events rankings after processing any event
            await self.update_top_events_rankings()
            
            # Clear relevant cache entries
            await self._clear_analytics_cache()
            
            logger.info(f"Successfully processed event: {event_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing event {event_type}: {e}")
            return False
    
    async def start(self):
        """Start the event subscriber."""
        if self.running:
            return
        
        try:
            await self.redis_manager.initialize()
            self.pubsub = self.redis_manager.redis_client.pubsub()
            
            # Subscribe to all event channels
            channels = [
                # Events service channels
                f"{self.events_channel_prefix}:created",
                f"{self.events_channel_prefix}:updated", 
                f"{self.events_channel_prefix}:deleted",
                # Bookings service channels
                f"{self.bookings_channel_prefix}:created",
                f"{self.bookings_channel_prefix}:confirmed",
                f"{self.bookings_channel_prefix}:cancelled"
            ]
            
            await self.pubsub.subscribe(*channels)
            self.running = True
            
            logger.info("Analytics event subscriber started, listening for events...")
            logger.info(f"Subscribed to channels: {channels}")
            
            # Start listening for messages
            asyncio.create_task(self._listen_for_messages())
            
        except Exception as e:
            logger.error(f"Failed to start analytics event subscriber: {e}")
            raise
    
    async def stop(self):
        """Stop the event subscriber."""
        if not self.running:
            return
        
        self.running = False
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        
        logger.info("Analytics event subscriber stopped")
    
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
            logger.error(f"Error in analytics message listener: {e}")
            self.running = False
    
    async def _handle_message(self, message):
        """Handle incoming Redis message."""
        try:
            data = json.loads(message['data'])
            event_type = data.get('type')
            
            logger.info(f"📊 Analytics Service: Received event: {event_type}")
            logger.info(f"📊 Event data: {data}")
            
            # Process the event
            success = await self.process_event(event_type, data)
            if success:
                logger.info(f"✅ Successfully processed {event_type} event")
            else:
                logger.warning(f"⚠️ Failed to process {event_type} event")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _log_event(self, event_type: str, event_data: Dict[str, Any]):
        """Log event to database for audit trail."""
        session = self.db_manager.SessionLocal()
        try:
            event_log = EventLog(
                event_type=event_type,
                event_id=event_data.get("id") or event_data.get("event_id"),
                event_data=json.dumps(event_data),
                processed=True
            )
            session.add(event_log)
            session.commit()
        except Exception as e:
            logger.error(f"Error logging event: {e}")
            session.rollback()
        finally:
            session.close()
    
    async def _handle_booking_created(self, event_data: Dict[str, Any]):
        """Handle booking created event."""
        session = self.db_manager.SessionLocal()
        try:
            event_id = event_data.get("event_id")
            booking_data = event_data.get("booking_data", {})
            quantity = booking_data.get("quantity", 1)  # Default to 1 if not specified
            booking_value = booking_data.get("total_amount", 0)
            booking_date = datetime.now().date()
            
            # Update event stats
            await self._update_event_stats(session, event_id, {
                "total_bookings": quantity,
                "total_revenue": booking_value,
                "last_booking": datetime.now()
            })
            
            # Update daily stats
            await self._update_daily_stats(session, booking_date, {
                "new_bookings": quantity,
                "total_revenue": booking_value
            })
            
            # Update system metrics
            await self._update_system_metrics(session, {
                "total_bookings": quantity,
                "total_revenue": booking_value,
                "recent_bookings": quantity,
                "recent_revenue": booking_value
            })
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Error handling booking created: {e}")
            session.rollback()
        finally:
            session.close()
    
    async def _handle_booking_cancelled(self, event_data: Dict[str, Any]):
        """Handle booking cancelled event."""
        session = self.db_manager.SessionLocal()
        try:
            event_id = event_data.get("event_id")
            booking_data = event_data.get("booking_data", {})
            quantity = booking_data.get("quantity", 1)  # Default to 1 if not specified
            booking_value = booking_data.get("total_amount", 0)
            booking_date = datetime.now().date()
            
            # Update event stats
            await self._update_event_stats(session, event_id, {
                "cancelled_bookings": quantity,
                "total_revenue": -booking_value,  # Subtract revenue
                "last_booking": datetime.now()
            })
            
            # Update daily stats
            await self._update_daily_stats(session, booking_date, {
                "cancelled_bookings": quantity,
                "total_revenue": -booking_value
            })
            
            # Update system metrics
            await self._update_system_metrics(session, {
                "total_bookings": -quantity,  # Subtract from total
                "total_revenue": -booking_value,
                "recent_bookings": -quantity,
                "recent_revenue": -booking_value
            })
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Error handling booking cancelled: {e}")
            session.rollback()
        finally:
            session.close()
    
    async def _handle_booking_confirmed(self, event_data: Dict[str, Any]):
        """Handle booking confirmed event."""
        session = self.db_manager.SessionLocal()
        try:
            event_id = event_data.get("event_id")
            booking_data = event_data.get("booking_data", {})
            quantity = booking_data.get("quantity", 1)  # Default to 1 if not specified
            
            # Update event stats
            await self._update_event_stats(session, event_id, {
                "confirmed_bookings": quantity,
                "last_booking": datetime.now()
            })
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Error handling booking confirmed: {e}")
            session.rollback()
        finally:
            session.close()
    
    async def _handle_event_created(self, event_data: Dict[str, Any]):
        """Handle event created event."""
        session = self.db_manager.SessionLocal()
        try:
            # Handle both direct event data and nested event_data
            if "event_data" in event_data:
                event_info = event_data["event_data"]
                event_id = event_info.get("id")
                event_name = event_info.get("name") or event_info.get("title", "Unknown Event")
                category = event_info.get("category")
                capacity = event_info.get("capacity", 0)
            else:
                event_id = event_data.get("id") or event_data.get("event_id")
                event_name = event_data.get("name") or event_data.get("title", "Unknown Event")
                category = event_data.get("category")
                capacity = event_data.get("capacity", 0)
            
            # Create new event stats entry
            event_stats = EventStats(
                event_id=event_id,
                event_name=event_name,
                category=category,
                total_capacity=capacity
            )
            session.add(event_stats)
            
            # Update system metrics
            await self._update_system_metrics(session, {
                "total_events": 1,
                "recent_events": 1
            })
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Error handling event created: {e}")
            session.rollback()
        finally:
            session.close()
    
    async def _handle_event_updated(self, event_data: Dict[str, Any]):
        """Handle event updated event."""
        session = self.db_manager.SessionLocal()
        try:
            # Handle both direct event data and nested event_data
            if "event_data" in event_data:
                event_info = event_data["event_data"]
                event_id = event_info.get("id")
                event_name = event_info.get("name") or event_info.get("title")
                category = event_info.get("category")
                capacity = event_info.get("capacity")
            else:
                event_id = event_data.get("id") or event_data.get("event_id")
                event_name = event_data.get("name") or event_data.get("title")
                category = event_data.get("category")
                capacity = event_data.get("capacity")
            
            # Update event stats if exists, create if not
            event_stats = session.query(EventStats).filter(EventStats.event_id == event_id).first()
            if event_stats:
                if event_name:
                    event_stats.event_name = event_name
                if category:
                    event_stats.category = category
                if capacity is not None:
                    event_stats.total_capacity = capacity
            else:
                # Create new entry if doesn't exist
                event_stats = EventStats(
                    event_id=event_id,
                    event_name=event_name or "Unknown Event",
                    category=category,
                    total_capacity=capacity or 0
                )
                session.add(event_stats)
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Error handling event updated: {e}")
            session.rollback()
        finally:
            session.close()
    
    async def _handle_event_deleted(self, event_data: Dict[str, Any]):
        """Handle event deleted event."""
        session = self.db_manager.SessionLocal()
        try:
            event_id = event_data.get("event_id") or event_data.get("id")
            
            if not event_id:
                logger.warning("Event deletion event missing event_id")
                return
            
            # Remove event stats
            event_stats = session.query(EventStats).filter(EventStats.event_id == event_id).first()
            if event_stats:
                session.delete(event_stats)
            
            # Remove from top events
            top_event = session.query(TopEvents).filter(TopEvents.event_id == event_id).first()
            if top_event:
                session.delete(top_event)
            
            # Update system metrics
            await self._update_system_metrics(session, {
                "total_events": -1,
                "recent_events": -1
            })
            
            session.commit()
            logger.info(f"Removed analytics data for deleted event {event_id}")
            
        except Exception as e:
            logger.error(f"Error handling event deleted: {e}")
            session.rollback()
        finally:
            session.close()
    
    async def _update_event_stats(self, session: Session, event_id: int, updates: Dict[str, Any]):
        """Update event statistics."""
        if not event_id:
            logger.warning("Cannot update event stats: missing event_id")
            return
            
        event_stats = session.query(EventStats).filter(EventStats.event_id == event_id).first()
        
        if event_stats:
            # Update existing stats
            for key, value in updates.items():
                if key == "total_bookings":
                    event_stats.total_bookings += value
                elif key == "cancelled_bookings":
                    event_stats.cancelled_bookings += value
                elif key == "confirmed_bookings":
                    event_stats.confirmed_bookings += value
                elif key == "total_revenue":
                    event_stats.total_revenue += value
                elif key == "last_booking":
                    event_stats.last_booking = value
            
            # Recalculate derived metrics
            if event_stats.total_bookings > 0:
                event_stats.cancellation_rate = (event_stats.cancelled_bookings / event_stats.total_bookings) * 100
                event_stats.avg_booking_value = event_stats.total_revenue / event_stats.total_bookings
                if event_stats.total_capacity > 0:
                    # Use total_bookings for capacity utilization, not just confirmed
                    event_stats.capacity_utilization = (event_stats.total_bookings / event_stats.total_capacity) * 100
                else:
                    event_stats.capacity_utilization = 0
            else:
                event_stats.cancellation_rate = 0
                event_stats.avg_booking_value = 0
                event_stats.capacity_utilization = 0
        else:
            # Create new event stats entry
            event_stats = EventStats(
                event_id=event_id,
                event_name="Unknown Event",
                **updates
            )
            session.add(event_stats)
    
    async def _update_daily_stats(self, session: Session, stat_date: date, updates: Dict[str, Any]):
        """Update daily statistics."""
        if not stat_date:
            logger.warning("Cannot update daily stats: missing date")
            return
            
        daily_stats = session.query(DailyStats).filter(DailyStats.date == stat_date).first()
        
        if daily_stats:
            # Update existing daily stats
            for key, value in updates.items():
                if key == "new_bookings":
                    daily_stats.new_bookings += value
                elif key == "cancelled_bookings":
                    daily_stats.cancelled_bookings += value
                elif key == "total_revenue":
                    daily_stats.total_revenue += value
            
            # Recalculate derived metrics
            if daily_stats.new_bookings > 0:
                daily_stats.avg_booking_value = daily_stats.total_revenue / daily_stats.new_bookings
            else:
                daily_stats.avg_booking_value = 0
        else:
            # Create new daily stats entry
            daily_stats = DailyStats(
                date=stat_date,
                **updates
            )
            # Calculate initial avg_booking_value
            if daily_stats.new_bookings > 0:
                daily_stats.avg_booking_value = daily_stats.total_revenue / daily_stats.new_bookings
            else:
                daily_stats.avg_booking_value = 0
            session.add(daily_stats)
    
    async def _update_system_metrics(self, session: Session, updates: Dict[str, Any]):
        """Update system-wide metrics."""
        system_metrics = session.query(SystemMetrics).filter(SystemMetrics.id == 1).first()
        
        if system_metrics:
            # Update existing metrics
            for key, value in updates.items():
                if key == "total_events":
                    system_metrics.total_events += value
                elif key == "total_bookings":
                    system_metrics.total_bookings += value
                elif key == "total_revenue":
                    system_metrics.total_revenue += value
                elif key == "recent_events":
                    system_metrics.recent_events += value
                elif key == "recent_bookings":
                    system_metrics.recent_bookings += value
                elif key == "recent_revenue":
                    system_metrics.recent_revenue += value
            
            # Ensure non-negative values
            system_metrics.total_events = max(0, system_metrics.total_events)
            system_metrics.total_bookings = max(0, system_metrics.total_bookings)
            system_metrics.recent_events = max(0, system_metrics.recent_events)
            system_metrics.recent_bookings = max(0, system_metrics.recent_bookings)
        else:
            # Create new system metrics entry
            system_metrics = SystemMetrics(**updates)
            session.add(system_metrics)
    
    async def update_top_events_rankings(self):
        """Update top events rankings based on current data."""
        session = self.db_manager.SessionLocal()
        try:
            # Get all event stats ordered by different metrics
            events_by_bookings = session.query(EventStats).order_by(EventStats.total_bookings.desc()).all()
            events_by_revenue = session.query(EventStats).order_by(EventStats.total_revenue.desc()).all()
            events_by_utilization = session.query(EventStats).order_by(EventStats.capacity_utilization.desc()).all()
            
            # Update rankings
            for i, event in enumerate(events_by_bookings, 1):
                top_event = session.query(TopEvents).filter(TopEvents.event_id == event.event_id).first()
                if top_event:
                    top_event.booking_rank = i
                    top_event.total_bookings = event.total_bookings
                    top_event.total_revenue = event.total_revenue
                    top_event.capacity_utilization = event.capacity_utilization
                else:
                    top_event = TopEvents(
                        event_id=event.event_id,
                        event_name=event.event_name,
                        category=event.category,
                        total_bookings=event.total_bookings,
                        total_revenue=event.total_revenue,
                        capacity_utilization=event.capacity_utilization,
                        booking_rank=i
                    )
                    session.add(top_event)
            
            for i, event in enumerate(events_by_revenue, 1):
                top_event = session.query(TopEvents).filter(TopEvents.event_id == event.event_id).first()
                if top_event:
                    top_event.revenue_rank = i
                else:
                    top_event = TopEvents(
                        event_id=event.event_id,
                        event_name=event.event_name,
                        category=event.category,
                        total_bookings=event.total_bookings,
                        total_revenue=event.total_revenue,
                        capacity_utilization=event.capacity_utilization,
                        revenue_rank=i
                    )
                    session.add(top_event)
            
            for i, event in enumerate(events_by_utilization, 1):
                top_event = session.query(TopEvents).filter(TopEvents.event_id == event.event_id).first()
                if top_event:
                    top_event.utilization_rank = i
                else:
                    top_event = TopEvents(
                        event_id=event.event_id,
                        event_name=event.event_name,
                        category=event.category,
                        total_bookings=event.total_bookings,
                        total_revenue=event.total_revenue,
                        capacity_utilization=event.capacity_utilization,
                        utilization_rank=i
                    )
                    session.add(top_event)
            
            session.commit()
            logger.info("Top events rankings updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating top events rankings: {e}")
            session.rollback()
        finally:
            session.close()
    
    async def _clear_analytics_cache(self):
        """Clear analytics cache after data updates."""
        try:
            # Clear main analytics cache patterns
            cache_patterns = [
                "analytics:system_overview",
                "analytics:top_events:*",
                "analytics:daily:*",
                "analytics:event:*",
                "analytics:all_events",
                "analytics:booking_trends:*",
                "analytics:capacity_utilization",
                "analytics:revenue:*"
            ]
            
            for pattern in cache_patterns:
                await self.redis_manager.delete(pattern)
                
            logger.debug("Analytics cache cleared after event processing")
        except Exception as e:
            logger.error(f"Error clearing analytics cache: {e}")