"""
Pydantic schemas for Bookings Service.
Handles request/response validation and serialization.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum

from app.models.booking import BookingStatus, PaymentStatus


# Enums for API
class BookingStatusEnum(str, Enum):
    """Booking status enumeration for API."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REFUNDED = "refunded"
    COMPLETED = "completed"


class PaymentStatusEnum(str, Enum):
    """Payment status enumeration for API."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


# Base schemas
class BaseBookingSchema(BaseModel):
    """Base booking schema with common fields."""
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


# Request schemas
class BookingItemCreate(BaseModel):
    """Schema for creating booking items."""
    
    price_per_item: Decimal = Field(..., gt=0, description="Price per individual ticket")
    quantity: int = Field(..., gt=0, le=10, description="Number of tickets (max 10)")
    
    @field_validator('price_per_item')
    @classmethod
    def validate_price(cls, v):
        """Validate price has at most 2 decimal places."""
        if v.as_tuple().exponent < -2:
            raise ValueError('Price cannot have more than 2 decimal places')
        return v
    
    @model_validator(mode='after')
    def validate_total_price(self):
        """Calculate and validate total price."""
        if hasattr(self, 'price_per_item') and hasattr(self, 'quantity'):
            self.total_price = self.price_per_item * self.quantity
        return self


class BookingCreate(BaseModel):
    """Schema for creating a new booking."""
    
    event_id: int = Field(..., gt=0, description="ID of the event to book")
    quantity: int = Field(..., gt=0, le=10, description="Total number of tickets to book")
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes for the booking")
    
    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v):
        """Validate booking quantity."""
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        if v > 10:
            raise ValueError('Maximum 10 tickets per booking')
        return v


class BookingUpdate(BaseModel):
    """Schema for updating an existing booking."""
    
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes for the booking")


class BookingCancel(BaseModel):
    """Schema for cancelling a booking."""
    
    reason: Optional[str] = Field(None, max_length=500, description="Reason for cancellation")




# Response schemas
class BookingItemResponse(BaseModel):
    """Schema for booking item response."""
    
    id: int
    price_per_item: float
    quantity: int
    total_price: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class BookingResponse(BaseModel):
    """Schema for booking response."""
    
    id: int
    user_id: int
    event_id: int
    booking_reference: str
    quantity: int
    total_amount: float
    currency: str
    status: BookingStatusEnum
    payment_status: PaymentStatusEnum
    booking_date: datetime
    expires_at: Optional[datetime]
    confirmed_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    payment_method: Optional[str]
    payment_reference: Optional[str]
    payment_processed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    version: int
    notes: Optional[str]
    booking_items: List[BookingItemResponse] = []
    
    class Config:
        from_attributes = True


class BookingSummaryResponse(BaseModel):
    """Schema for booking summary (list view)."""
    
    id: int
    booking_reference: str
    event_id: int
    quantity: int
    total_amount: float
    status: BookingStatusEnum
    payment_status: PaymentStatusEnum
    booking_date: datetime
    expires_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class EventAvailabilityResponse(BaseModel):
    """Schema for event availability response."""
    
    event_id: int = Field(gt=0, description="Event ID must be positive")
    total_capacity: int = Field(ge=0, description="Total capacity must be non-negative")
    available_capacity: int = Field(ge=0, description="Available capacity must be non-negative")
    utilization_percentage: float = Field(ge=0.0, le=100.0, description="Utilization percentage must be between 0 and 100")
    last_updated: datetime
    
    class Config:
        from_attributes = True


class BookingAuditLogResponse(BaseModel):
    """Schema for booking audit log response."""
    
    id: int
    action: str
    field_name: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    changed_by: Optional[int]
    changed_at: datetime
    reason: Optional[str]
    
    class Config:
        from_attributes = True


# Query schemas
class BookingQueryParams(BaseModel):
    """Schema for booking query parameters."""
    
    status: Optional[BookingStatusEnum] = Field(None, description="Filter by booking status")
    payment_status: Optional[PaymentStatusEnum] = Field(None, description="Filter by payment status")
    event_id: Optional[int] = Field(None, gt=0, description="Filter by event ID")
    user_id: Optional[int] = Field(None, gt=0, description="Filter by user ID")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Number of items per page")
    sort_by: str = Field("booking_date", description="Sort field")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


class AvailabilityQueryParams(BaseModel):
    """Schema for availability query parameters."""
    
    event_id: int = Field(..., gt=0, description="Event ID to check availability for")
    include_reserved: bool = Field(False, description="Include reserved capacity in response")


# Error schemas
class BookingErrorResponse(BaseModel):
    """Schema for booking error responses."""
    
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


class ValidationErrorResponse(BaseModel):
    """Schema for validation error responses."""
    
    error_code: str = "VALIDATION_ERROR"
    error_message: str = "Validation failed"
    validation_errors: List[Dict[str, Any]] = Field(..., description="List of validation errors")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


# Success schemas
class BookingSuccessResponse(BaseModel):
    """Schema for successful booking operations."""
    
    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class BookingCreateResponse(BaseModel):
    """Schema for booking creation response."""
    
    success: bool = Field(True, description="Booking creation success")
    message: str = Field("Booking created successfully", description="Success message")
    booking: BookingResponse = Field(..., description="Created booking details")
    expires_at: datetime = Field(..., description="Booking expiry time")


class BookingCancelResponse(BaseModel):
    """Schema for booking cancellation response."""
    
    success: bool = Field(True, description="Cancellation success")
    message: str = Field("Booking cancelled successfully", description="Success message")
    booking: BookingResponse = Field(..., description="Cancelled booking details")


# Pagination schemas
class PaginatedResponse(BaseModel):
    """Schema for paginated responses."""
    
    items: List[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class BookingListResponse(PaginatedResponse):
    """Schema for paginated booking list response."""
    
    items: List[BookingSummaryResponse] = Field(..., description="List of bookings")


# Health check schemas
class HealthCheckResponse(BaseModel):
    """Schema for health check response."""
    
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Health check timestamp")
    version: str = Field(..., description="Service version")
    database: str = Field(..., description="Database connection status")
    redis: str = Field(..., description="Redis connection status")
    uptime: float = Field(..., description="Service uptime in seconds")


# Statistics schemas
class BookingStatsResponse(BaseModel):
    """Schema for booking statistics response."""
    
    total_bookings: int = Field(..., description="Total number of bookings")
    confirmed_bookings: int = Field(..., description="Number of confirmed bookings")
    pending_bookings: int = Field(..., description="Number of pending bookings")
    cancelled_bookings: int = Field(..., description="Number of cancelled bookings")
    total_revenue: float = Field(..., description="Total revenue from confirmed bookings")
    average_booking_value: float = Field(..., description="Average booking value")
    conversion_rate: float = Field(..., description="Booking conversion rate")
    period_start: datetime = Field(..., description="Statistics period start")
    period_end: datetime = Field(..., description="Statistics period end")