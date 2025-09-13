"""
Analytics API endpoints for admin dashboard.
Provides comprehensive analytics data with admin-only access.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from ..dependencies import (
    get_analytics_service,
    get_event_subscriber,
    get_current_admin,
    rate_limit_check,
    AnalyticsService,
    EventSubscriber
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=Dict[str, Any])
async def get_system_overview(
    request: Request,
    admin: dict = Depends(get_current_admin),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    _: bool = Depends(rate_limit_check)
):
    """
    Get system-wide analytics overview.
    
    Returns:
        System metrics, recent trends, and performance data
    """
    try:
        overview = await analytics_service.get_system_overview()
        return {
            "success": True,
            "data": overview,
            "admin": admin["username"]
        }
    except Exception as e:
        logger.error(f"Error getting system overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system overview"
        )


@router.get("/top-events", response_model=Dict[str, Any])
async def get_top_events(
    limit: int = Query(10, ge=1, le=50, description="Number of events to return"),
    sort_by: str = Query("bookings", regex="^(bookings|revenue|utilization)$", description="Sort criteria"),
    admin: dict = Depends(get_current_admin),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    _: bool = Depends(rate_limit_check)
):
    """
    Get top performing events.
    
    Args:
        limit: Number of events to return (1-50)
        sort_by: Sort criteria (bookings, revenue, utilization)
        
    Returns:
        List of top performing events
    """
    try:
        top_events = await analytics_service.get_top_events(limit=limit, sort_by=sort_by)
        return {
            "success": True,
            "data": {
                "events": top_events,
                "total": len(top_events),
                "sort_by": sort_by
            },
            "admin": admin["username"]
        }
    except Exception as e:
        logger.error(f"Error getting top events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve top events"
        )


@router.get("/daily", response_model=Dict[str, Any])
async def get_daily_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    admin: dict = Depends(get_current_admin),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    _: bool = Depends(rate_limit_check)
):
    """
    Get daily analytics for the specified period.
    
    Args:
        days: Number of days to analyze (1-365)
        
    Returns:
        Daily analytics data
    """
    try:
        daily_data = await analytics_service.get_daily_analytics(days=days)
        return {
            "success": True,
            "data": {
                "daily_stats": daily_data,
                "period_days": days,
                "total_days": len(daily_data)
            },
            "admin": admin["username"]
        }
    except Exception as e:
        logger.error(f"Error getting daily analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve daily analytics"
        )


@router.get("/events", response_model=Dict[str, Any])
async def get_event_analytics(
    event_id: Optional[int] = Query(None, description="Specific event ID to analyze"),
    admin: dict = Depends(get_current_admin),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    _: bool = Depends(rate_limit_check)
):
    """
    Get detailed event analytics.
    
    Args:
        event_id: Optional specific event ID to analyze
        
    Returns:
        Event analytics data
    """
    try:
        event_data = await analytics_service.get_event_analytics(event_id=event_id)
        return {
            "success": True,
            "data": event_data,
            "admin": admin["username"]
        }
    except Exception as e:
        logger.error(f"Error getting event analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve event analytics"
        )


@router.get("/booking-trends", response_model=Dict[str, Any])
async def get_booking_trends(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    admin: dict = Depends(get_current_admin),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    _: bool = Depends(rate_limit_check)
):
    """
    Get booking trends and patterns.
    
    Args:
        days: Number of days to analyze (1-365)
        
    Returns:
        Booking trends and growth data
    """
    try:
        trends = await analytics_service.get_booking_trends(days=days)
        return {
            "success": True,
            "data": trends,
            "admin": admin["username"]
        }
    except Exception as e:
        logger.error(f"Error getting booking trends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve booking trends"
        )


@router.get("/capacity-utilization", response_model=Dict[str, Any])
async def get_capacity_utilization(
    admin: dict = Depends(get_current_admin),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    _: bool = Depends(rate_limit_check)
):
    """
    Get capacity utilization analytics.
    
    Returns:
        Capacity utilization data and underutilized events
    """
    try:
        utilization = await analytics_service.get_capacity_utilization()
        return {
            "success": True,
            "data": utilization,
            "admin": admin["username"]
        }
    except Exception as e:
        logger.error(f"Error getting capacity utilization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve capacity utilization data"
        )


@router.get("/revenue", response_model=Dict[str, Any])
async def get_revenue_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    admin: dict = Depends(get_current_admin),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    _: bool = Depends(rate_limit_check)
):
    """
    Get revenue analytics and trends.
    
    Args:
        days: Number of days to analyze (1-365)
        
    Returns:
        Revenue analytics and top revenue events
    """
    try:
        revenue = await analytics_service.get_revenue_analytics(days=days)
        return {
            "success": True,
            "data": revenue,
            "admin": admin["username"]
        }
    except Exception as e:
        logger.error(f"Error getting revenue analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve revenue analytics"
        )


@router.post("/events/process", response_model=Dict[str, Any])
async def process_event(
    event_type: str,
    event_data: Dict[str, Any],
    admin: dict = Depends(get_current_admin),
    event_subscriber: EventSubscriber = Depends(get_event_subscriber),
    _: bool = Depends(rate_limit_check)
):
    """
    Process an event for analytics (for testing or manual processing).
    
    Args:
        event_type: Type of event (BookingCreated, EventCreated, etc.)
        event_data: Event payload data
        
    Returns:
        Processing result
    """
    try:
        success = await event_subscriber.process_event(event_type, event_data)
        
        if success:
            return {
                "success": True,
                "message": f"Event {event_type} processed successfully",
                "admin": admin["username"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process event {event_type}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process event"
        )


@router.post("/cache/clear", response_model=Dict[str, Any])
async def clear_analytics_cache(
    pattern: str = Query("*", description="Cache pattern to clear"),
    admin: dict = Depends(get_current_admin),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    _: bool = Depends(rate_limit_check)
):
    """
    Clear analytics cache.
    
    Args:
        pattern: Cache pattern to clear (default: all)
        
    Returns:
        Cache clear result
    """
    try:
        success = await analytics_service.clear_cache(pattern=pattern)
        
        if success:
            return {
                "success": True,
                "message": f"Cache cleared for pattern: {pattern}",
                "admin": admin["username"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to clear cache"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_data(
    admin: dict = Depends(get_current_admin),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    _: bool = Depends(rate_limit_check)
):
    """
    Get comprehensive dashboard data (all key metrics).
    
    Returns:
        Complete dashboard data for admin interface
    """
    try:
        # Get all key metrics in parallel
        import asyncio
        
        overview_task = analytics_service.get_system_overview()
        top_events_task = analytics_service.get_top_events(limit=10, sort_by="bookings")
        daily_task = analytics_service.get_daily_analytics(days=30)
        trends_task = analytics_service.get_booking_trends(days=30)
        utilization_task = analytics_service.get_capacity_utilization()
        revenue_task = analytics_service.get_revenue_analytics(days=30)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(
            overview_task,
            top_events_task,
            daily_task,
            trends_task,
            utilization_task,
            revenue_task,
            return_exceptions=True
        )
        
        # Check for exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error in dashboard data task {i}: {result}")
                results[i] = {}
        
        dashboard_data = {
            "overview": results[0],
            "top_events": results[1],
            "daily_analytics": results[2],
            "booking_trends": results[3],
            "capacity_utilization": results[4],
            "revenue_analytics": results[5],
            "generated_at": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "data": dashboard_data,
            "admin": admin["username"]
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard data"
        )