"""
Analytics service for data aggregation and querying.
Provides analytics data for admin dashboard.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func

from ..models.analytics import EventStats, DailyStats, TopEvents, SystemMetrics
from ..db.database import DatabaseManager
from ..db.redis_client import RedisManager

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Main analytics service for data aggregation and querying.
    Provides cached analytics data for admin dashboard.
    """
    
    def __init__(self, db_manager: DatabaseManager, redis_manager: RedisManager):
        self.db_manager = db_manager
        self.redis_manager = redis_manager
        self.cache_ttl = 300  # 5 minutes default
    
    async def get_system_overview(self) -> Dict[str, Any]:
        """Get system-wide analytics overview."""
        cache_key = "analytics:system_overview"
        
        # Try cache first
        cached_data = await self.redis_manager.get_json(cache_key)
        if cached_data:
            return cached_data
        
        session = self.db_manager.SessionLocal()
        try:
            # Get system metrics
            system_metrics = session.query(SystemMetrics).filter(SystemMetrics.id == 1).first()
            
            if not system_metrics:
                # Initialize with default values
                system_metrics = SystemMetrics()
                session.add(system_metrics)
                session.commit()
            
            # Get recent trends (last 7 days)
            week_ago = date.today() - timedelta(days=7)
            recent_stats = session.query(DailyStats).filter(
                DailyStats.date >= week_ago
            ).order_by(desc(DailyStats.date)).all()
            
            # Calculate trends
            total_recent_bookings = sum(stat.new_bookings for stat in recent_stats)
            total_recent_revenue = sum(stat.total_revenue for stat in recent_stats)
            
            # Calculate growth rates
            if len(recent_stats) >= 2:
                first_half = recent_stats[:len(recent_stats)//2]
                second_half = recent_stats[len(recent_stats)//2:]
                
                first_half_bookings = sum(stat.new_bookings for stat in first_half)
                second_half_bookings = sum(stat.new_bookings for stat in second_half)
                
                if first_half_bookings > 0:
                    booking_growth = ((second_half_bookings - first_half_bookings) / first_half_bookings) * 100
                else:
                    booking_growth = 0
            else:
                booking_growth = 0
            
            overview = {
                "system_metrics": system_metrics.to_dict(),
                "recent_trends": {
                    "last_7_days": {
                        "total_bookings": total_recent_bookings,
                        "total_revenue": round(total_recent_revenue, 2),
                        "daily_average": round(total_recent_bookings / 7, 1) if recent_stats else 0,
                        "booking_growth_rate": round(booking_growth, 2)
                    }
                },
                "performance": {
                    "avg_capacity_utilization": system_metrics.avg_capacity_utilization,
                    "avg_cancellation_rate": system_metrics.avg_cancellation_rate,
                    "system_uptime": system_metrics.system_uptime
                }
            }
            
            # Cache the result
            await self.redis_manager.set_json(cache_key, overview, self.cache_ttl)
            
            return overview
            
        except Exception as e:
            logger.error(f"Error getting system overview: {e}")
            return {}
        finally:
            session.close()
    
    async def get_top_events(self, limit: int = 10, sort_by: str = "bookings") -> List[Dict[str, Any]]:
        """Get top performing events."""
        cache_key = f"analytics:top_events:{sort_by}:{limit}"
        
        # Try cache first
        cached_data = await self.redis_manager.get_json(cache_key)
        if cached_data:
            return cached_data
        
        session = self.db_manager.SessionLocal()
        try:
            if sort_by == "bookings":
                events = session.query(TopEvents).order_by(asc(TopEvents.booking_rank)).limit(limit).all()
            elif sort_by == "revenue":
                events = session.query(TopEvents).order_by(asc(TopEvents.revenue_rank)).limit(limit).all()
            elif sort_by == "utilization":
                events = session.query(TopEvents).order_by(asc(TopEvents.utilization_rank)).limit(limit).all()
            else:
                events = session.query(TopEvents).order_by(asc(TopEvents.booking_rank)).limit(limit).all()
            
            result = [event.to_dict() for event in events]
            
            # Cache the result
            await self.redis_manager.set_json(cache_key, result, self.cache_ttl)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting top events: {e}")
            return []
        finally:
            session.close()
    
    async def get_daily_analytics(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily analytics for the specified number of days."""
        cache_key = f"analytics:daily:{days}"
        
        # Try cache first
        cached_data = await self.redis_manager.get_json(cache_key)
        if cached_data:
            return cached_data
        
        session = self.db_manager.SessionLocal()
        try:
            start_date = date.today() - timedelta(days=days)
            daily_stats = session.query(DailyStats).filter(
                DailyStats.date >= start_date
            ).order_by(asc(DailyStats.date)).all()
            
            result = [stat.to_dict() for stat in daily_stats]
            
            # Cache the result
            await self.redis_manager.set_json(cache_key, result, self.cache_ttl)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting daily analytics: {e}")
            return []
        finally:
            session.close()
    
    async def get_event_analytics(self, event_id: Optional[int] = None) -> Dict[str, Any]:
        """Get detailed analytics for a specific event or all events."""
        if event_id:
            cache_key = f"analytics:event:{event_id}"
        else:
            cache_key = "analytics:all_events"
        
        # Try cache first
        cached_data = await self.redis_manager.get_json(cache_key)
        if cached_data:
            return cached_data
        
        session = self.db_manager.SessionLocal()
        try:
            if event_id:
                event_stats = session.query(EventStats).filter(EventStats.event_id == event_id).first()
                if not event_stats:
                    return {}
                result = event_stats.to_dict()
            else:
                # Get all events with summary
                all_events = session.query(EventStats).all()
                result = {
                    "total_events": len(all_events),
                    "events": [event.to_dict() for event in all_events],
                    "summary": {
                        "total_bookings": sum(event.total_bookings for event in all_events),
                        "total_revenue": round(sum(event.total_revenue for event in all_events), 2),
                        "avg_capacity_utilization": round(
                            sum(event.capacity_utilization for event in all_events) / len(all_events), 2
                        ) if all_events else 0,
                        "avg_cancellation_rate": round(
                            sum(event.cancellation_rate for event in all_events) / len(all_events), 2
                        ) if all_events else 0
                    }
                }
            
            # Cache the result
            await self.redis_manager.set_json(cache_key, result, self.cache_ttl)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting event analytics: {e}")
            return {}
        finally:
            session.close()
    
    async def get_booking_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get booking trends and patterns."""
        cache_key = f"analytics:booking_trends:{days}"
        
        # Try cache first
        cached_data = await self.redis_manager.get_json(cache_key)
        if cached_data:
            return cached_data
        
        session = self.db_manager.SessionLocal()
        try:
            start_date = date.today() - timedelta(days=days)
            daily_stats = session.query(DailyStats).filter(
                DailyStats.date >= start_date
            ).order_by(asc(DailyStats.date)).all()
            
            # Calculate trends
            total_bookings = sum(stat.new_bookings for stat in daily_stats)
            total_cancelled = sum(stat.cancelled_bookings for stat in daily_stats)
            total_revenue = sum(stat.total_revenue for stat in daily_stats)
            
            # Calculate growth rate (compare first half vs second half)
            if len(daily_stats) >= 2:
                mid_point = len(daily_stats) // 2
                first_half_bookings = sum(stat.new_bookings for stat in daily_stats[:mid_point])
                second_half_bookings = sum(stat.new_bookings for stat in daily_stats[mid_point:])
                
                growth_rate = 0
                if first_half_bookings > 0:
                    growth_rate = ((second_half_bookings - first_half_bookings) / first_half_bookings) * 100
            else:
                growth_rate = 0
            
            result = {
                "period": f"Last {days} days",
                "total_bookings": total_bookings,
                "total_cancelled": total_cancelled,
                "total_revenue": round(total_revenue, 2),
                "cancellation_rate": round((total_cancelled / total_bookings) * 100, 2) if total_bookings > 0 else 0,
                "growth_rate": round(growth_rate, 2),
                "daily_average": round(total_bookings / days, 1),
                "daily_breakdown": [stat.to_dict() for stat in daily_stats]
            }
            
            # Cache the result
            await self.redis_manager.set_json(cache_key, result, self.cache_ttl)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting booking trends: {e}")
            return {}
        finally:
            session.close()
    
    async def get_capacity_utilization(self) -> Dict[str, Any]:
        """Get capacity utilization analytics."""
        cache_key = "analytics:capacity_utilization"
        
        # Try cache first
        cached_data = await self.redis_manager.get_json(cache_key)
        if cached_data:
            return cached_data
        
        session = self.db_manager.SessionLocal()
        try:
            # Get all event stats
            event_stats = session.query(EventStats).all()
            
            if not event_stats:
                return {"average_utilization": 0, "events": []}
            
            # Calculate utilization metrics
            total_utilization = sum(event.capacity_utilization for event in event_stats)
            avg_utilization = total_utilization / len(event_stats)
            
            # Categorize by utilization levels
            high_utilization = [e for e in event_stats if e.capacity_utilization >= 80]
            medium_utilization = [e for e in event_stats if 50 <= e.capacity_utilization < 80]
            low_utilization = [e for e in event_stats if e.capacity_utilization < 50]
            
            result = {
                "average_utilization": round(avg_utilization, 2),
                "total_events": len(event_stats),
                "utilization_distribution": {
                    "high": len(high_utilization),
                    "medium": len(medium_utilization),
                    "low": len(low_utilization)
                },
                "top_utilized_events": [
                    {
                        "event_id": event.event_id,
                        "event_name": event.event_name,
                        "utilization": round(event.capacity_utilization, 2)
                    }
                    for event in sorted(event_stats, key=lambda x: x.capacity_utilization, reverse=True)[:10]
                ],
                "underutilized_events": [
                    {
                        "event_id": event.event_id,
                        "event_name": event.event_name,
                        "utilization": round(event.capacity_utilization, 2)
                    }
                    for event in sorted(event_stats, key=lambda x: x.capacity_utilization)[:10]
                    if event.capacity_utilization < 50
                ]
            }
            
            # Cache the result
            await self.redis_manager.set_json(cache_key, result, self.cache_ttl)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting capacity utilization: {e}")
            return {}
        finally:
            session.close()
    
    async def get_revenue_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get revenue analytics and trends."""
        cache_key = f"analytics:revenue:{days}"
        
        # Try cache first
        cached_data = await self.redis_manager.get_json(cache_key)
        if cached_data:
            return cached_data
        
        session = self.db_manager.SessionLocal()
        try:
            # Get daily revenue data
            start_date = date.today() - timedelta(days=days)
            daily_stats = session.query(DailyStats).filter(
                DailyStats.date >= start_date
            ).order_by(asc(DailyStats.date)).all()
            
            # Get event revenue data
            event_stats = session.query(EventStats).order_by(desc(EventStats.total_revenue)).all()
            
            total_revenue = sum(stat.total_revenue for stat in daily_stats)
            avg_daily_revenue = total_revenue / days if days > 0 else 0
            
            # Calculate revenue growth
            if len(daily_stats) >= 2:
                mid_point = len(daily_stats) // 2
                first_half_revenue = sum(stat.total_revenue for stat in daily_stats[:mid_point])
                second_half_revenue = sum(stat.total_revenue for stat in daily_stats[mid_point:])
                
                revenue_growth = 0
                if first_half_revenue > 0:
                    revenue_growth = ((second_half_revenue - first_half_revenue) / first_half_revenue) * 100
            else:
                revenue_growth = 0
            
            result = {
                "period": f"Last {days} days",
                "total_revenue": round(total_revenue, 2),
                "average_daily_revenue": round(avg_daily_revenue, 2),
                "revenue_growth_rate": round(revenue_growth, 2),
                "top_revenue_events": [
                    {
                        "event_id": event.event_id,
                        "event_name": event.event_name,
                        "revenue": round(event.total_revenue, 2),
                        "avg_booking_value": round(event.avg_booking_value, 2)
                    }
                    for event in event_stats[:10]
                ],
                "daily_revenue_breakdown": [
                    {
                        "date": stat.date.isoformat(),
                        "revenue": round(stat.total_revenue, 2),
                        "bookings": stat.new_bookings
                    }
                    for stat in daily_stats
                ]
            }
            
            # Cache the result
            await self.redis_manager.set_json(cache_key, result, self.cache_ttl)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting revenue analytics: {e}")
            return {}
        finally:
            session.close()
    
    async def clear_cache(self, pattern: str = "*") -> bool:
        """Clear analytics cache."""
        try:
            # This is a simplified cache clear - in production you'd want more sophisticated cache invalidation
            await self.redis_manager.delete("analytics:*")
            logger.info(f"Analytics cache cleared for pattern: {pattern}")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False