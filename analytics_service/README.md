# Evently Analytics Service

A high-performance analytics and reporting microservice built with FastAPI, designed for real-time event-driven data aggregation and comprehensive business intelligence dashboards.

## 🚀 Key Features

### Core Analytics
- **Real-Time Analytics**: Event-driven data aggregation with instant dashboard updates
- **Performance Metrics**: Comprehensive event performance tracking and analysis
- **Revenue Analytics**: Detailed revenue tracking with growth rate calculations
- **Capacity Utilization**: Real-time capacity utilization monitoring and reporting
- **Booking Trends**: Advanced booking pattern analysis and trend identification

### Advanced Features
- **Event-Driven Architecture**: Real-time event subscription and data processing
- **Pre-computed Aggregates**: Optimized analytics tables for fast dashboard queries
- **Time-Series Analytics**: Daily, weekly, and monthly trend analysis
- **Top Events Ranking**: Dynamic leaderboards for booking and revenue performance
- **System Metrics**: Comprehensive system-wide performance monitoring

### Performance & Reliability
- **99.99% Uptime SLA**: Mission-critical analytics system with minimal downtime
- **High Throughput**: Optimized for real-time data processing and aggregation
- **Data Consistency**: Eventual consistency with real-time updates
- **Fault Tolerance**: Graceful degradation and automatic recovery mechanisms
- **Scalability**: Horizontal scaling with stateless design

## 🏗️ Architecture Overview

### Service Structure
```
analytics_service/
├── app/
│   ├── api/           # API layer with versioned endpoints
│   ├── core/          # Configuration and core utilities
│   ├── db/            # Database and Redis connections
│   ├── models/        # SQLAlchemy analytics models
│   ├── schemas/       # Pydantic request/response models
│   └── services/      # Business logic and event processing
├── tests/             # Comprehensive test suite
└── Dockerfile         # Container configuration
```

### Technology Stack
- **Framework**: FastAPI (async, high-performance web framework)
- **Database**: PostgreSQL with SQLAlchemy ORM and Alembic migrations
- **Caching**: Redis for performance optimization and event processing
- **Authentication**: JWT with role-based access control
- **Event Processing**: Redis pub/sub for real-time event subscription
- **Secrets Management**: Zero SDK for secure configuration management
- **Containerization**: Docker with Python 3.11 slim base image
- **Testing**: Pytest with comprehensive test coverage

## 📡 API Endpoints

### Analytics Endpoints (Admin JWT Required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/analytics/dashboard` | Get comprehensive analytics dashboard |
| `GET` | `/api/v1/analytics/events` | Get event performance analytics |
| `GET` | `/api/v1/analytics/events/{event_id}` | Get specific event analytics |
| `GET` | `/api/v1/analytics/daily` | Get daily analytics trends |
| `GET` | `/api/v1/analytics/revenue` | Get revenue analytics and trends |
| `GET` | `/api/v1/analytics/capacity` | Get capacity utilization analytics |
| `GET` | `/api/v1/analytics/top-events` | Get top performing events |
| `GET` | `/api/v1/analytics/system` | Get system-wide metrics |

### System Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health check |
| `GET` | `/info` | Service information and capabilities |
| `GET` | `/docs` | Interactive API documentation |

## ⚙️ Configuration & Setup

### Environment Variables
The service uses Zero SDK for secure secrets management. Set the following environment variable:

```bash
export ZERO_TOKEN="your-zero-token-here"
```

### Required Secrets (via Zero SDK)
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` - PostgreSQL database configuration
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_USE_TLS` - Redis configuration for event processing
- `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRY_MINUTES` - JWT token configuration
- `CORS_ORIGINS` - CORS allowed origins (comma-separated)
- `ANALYTICS_CACHE_TTL` - Analytics data cache TTL (default: 300 seconds)
- `EVENT_PROCESSING_BATCH_SIZE` - Event processing batch size (default: 100)

### Quick Start

#### Development Setup
```bash
cd analytics_service

# Install dependencies
pip install -r requirements.txt

# Set environment variable
export ZERO_TOKEN="your-token"

# Run database migrations
python migrate.py upgrade

# Run the service
python main.py
```

#### Docker Deployment
```bash
# Build the image
docker build -t analytics-service:latest .

# Run with environment file
docker run -p 8003:8003 \
  -e ZERO_TOKEN="your-token" \
  analytics-service:latest
```

#### Production Deployment
```bash
# Using Docker Compose (recommended)
docker-compose up -d
```

## 🧪 Testing

### Running Tests
```bash
pytest tests/ -v
```

## 🔒 Security & Authentication

### JWT Implementation
- **Algorithm**: HS256 (configurable via Zero SDK)
- **Token Expiry**: 30 minutes (configurable)
- **Role-based Access**: Admin-only access for analytics endpoints
- **Token Validation**: Real-time JWT verification with user status checks
- **Authentication Required**: All endpoints require valid admin JWT tokens

### Security Features
- **CORS Protection**: Configurable origin restrictions
- **Input Validation**: Comprehensive Pydantic schema validation
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **Rate Limiting**: Built-in rate limiting for analytics endpoints
- **Data Privacy**: Secure handling of sensitive analytics data

## 📊 Performance & Monitoring

### Analytics Features
- **Real-Time Processing**: Event-driven data aggregation with instant updates
- **Pre-computed Aggregates**: Optimized analytics tables for fast dashboard queries
- **Caching Strategy**: Redis caching for frequently accessed analytics data
- **Batch Processing**: Efficient batch processing of analytics events
- **Time-Series Optimization**: Optimized queries for time-series analytics

### Monitoring & Observability
- **Health Checks**: `/health` endpoint with database and Redis connectivity checks
- **Structured Logging**: JSON-formatted logs with request correlation IDs
- **Error Tracking**: Comprehensive error logging with stack traces
- **Performance Metrics**: Request timing, database query metrics, and processing rates
- **Service Information**: `/info` endpoint with service capabilities and features

### Very High Availability Features
- **99.99% Uptime SLA**: Designed for mission-critical analytics systems with minimal downtime
- **Connection Pooling**: Optimized database connection management with automatic failover
- **Graceful Degradation**: Service continues with reduced functionality during outages
- **Stateless Design**: Horizontal scaling support with load balancer integration
- **Event Processing**: Redis pub/sub for real-time event subscription and processing
- **Cache Resilience**: Automatic fallback to database when cache is unavailable
- **Circuit Breaker Pattern**: Automatic failure detection and recovery mechanisms
- **Health Monitoring**: Continuous health checks with automatic service recovery

## 🔄 Data Consistency & Reliability

### Database Design
- **ACID Compliance**: Full transaction support with SQLAlchemy ORM
- **Data Integrity**: Foreign key constraints, unique constraints, and validation
- **Migration Management**: Alembic for database schema versioning
- **Connection Pooling**: Optimized database connection management

### Analytics Data Models

#### Event Statistics Model
```python
class EventStats:
    event_id: int              # Primary key
    event_name: str            # Event name (indexed)
    category: str              # Event category (indexed)
    total_capacity: int        # Total event capacity
    total_bookings: int        # Total bookings count
    confirmed_bookings: int    # Confirmed bookings count
    cancelled_bookings: int    # Cancelled bookings count
    capacity_utilization: float  # Capacity utilization percentage
    total_revenue: float       # Total revenue generated
    cancellation_rate: float   # Cancellation rate percentage
    avg_booking_value: float   # Average booking value
    first_booking: datetime    # First booking timestamp
    last_booking: datetime     # Last booking timestamp
    updated_at: datetime       # Last update timestamp
```

#### Daily Statistics Model
```python
class DailyStats:
    date: date                 # Primary key (date)
    total_bookings: int        # Total bookings for the day
    new_bookings: int          # New bookings for the day
    cancelled_bookings: int    # Cancelled bookings for the day
    confirmed_bookings: int    # Confirmed bookings for the day
    total_revenue: float       # Total revenue for the day
    avg_booking_value: float   # Average booking value for the day
    active_events: int         # Number of active events
    new_users: int             # Number of new users
    system_uptime: float       # System uptime percentage
    updated_at: datetime       # Last update timestamp
```

#### Top Events Model
```python
class TopEvents:
    id: int                    # Primary key
    event_id: int              # Event ID (unique, indexed)
    event_name: str            # Event name
    category: str              # Event category
    total_bookings: int        # Total bookings count
    total_revenue: float       # Total revenue generated
    capacity_utilization: float  # Capacity utilization percentage
    booking_rank: int          # Ranking by bookings
    revenue_rank: int          # Ranking by revenue
    utilization_rank: int      # Ranking by utilization
    updated_at: datetime       # Last update timestamp
```

#### System Metrics Model
```python
class SystemMetrics:
    id: int                    # Primary key (single row)
    total_events: int          # Total events in system
    total_bookings: int        # Total bookings in system
    total_users: int           # Total users in system
    total_revenue: float       # Total system revenue
    recent_bookings: int       # Bookings in last 30 days
    recent_revenue: float      # Revenue in last 30 days
    recent_events: int         # Events in last 30 days
    avg_capacity_utilization: float  # Average capacity utilization
    avg_cancellation_rate: float     # Average cancellation rate
    system_uptime: float       # System uptime percentage
    booking_growth_rate: float # Booking growth rate
    revenue_growth_rate: float # Revenue growth rate
    updated_at: datetime       # Last update timestamp
```

#### Event Log Model
```python
class EventLog:
    id: int                    # Primary key
    event_type: str            # Event type (indexed)
    event_id: int              # Related event ID (indexed)
    event_data: str            # JSON event payload
    processed: bool            # Processing status (indexed)
    created_at: datetime       # Event received timestamp (indexed)
```

### Trading-Grade Consistency Guarantees
- **Eventual Consistency**: Real-time event processing with eventual consistency guarantees
- **Event Processing**: Reliable event subscription and processing with retry mechanisms
- **Data Aggregation**: Consistent data aggregation with transaction support
- **Cache Synchronization**: Redis cache synchronization with automatic invalidation
- **Write-through Caching**: Immediate cache updates on data changes with rollback capabilities
- **Read-after-write Consistency**: Guaranteed data visibility across all service instances
- **Transaction Support**: Full ACID compliance with isolation levels for concurrent access
- **Eventual Consistency**: Distributed cache synchronization with conflict resolution
- **Data Validation**: Multi-layer validation ensuring data accuracy and completeness
- **Audit Trail**: Complete event processing trail for compliance and debugging

## 🚀 Deployment & Scaling

### Container Configuration
- **Base Image**: Python 3.11 slim for optimal size and security
- **Optimized Build**: Minimal dependencies with security-focused packages
- **Health Checks**: Built-in health monitoring with dependency checks
- **Resource Limits**: Configurable CPU and memory constraints

### Enterprise-Grade Scaling Considerations
- **Horizontal Scaling**: Stateless design supports unlimited instances with auto-scaling
- **Database Scaling**: Connection pooling with read replicas and automatic failover
- **Cache Scaling**: Redis cluster for high availability and performance with data sharding
- **Load Balancing**: Advanced load balancing with health checks and traffic distribution
- **Event Processing**: Redis pub/sub for real-time event subscription and processing with message persistence
- **Cache Distribution**: Redis-based cache sharing across instances with consistency guarantees
- **Auto-scaling**: Dynamic scaling based on load metrics and performance thresholds
- **Geographic Distribution**: Multi-region deployment support for global availability

### Production Deployment
- **Docker Compose**: Multi-service orchestration with PostgreSQL and Redis clusters
- **Environment Management**: Zero SDK for secure configuration with secret rotation
- **Monitoring**: Comprehensive health checks and structured logging for observability