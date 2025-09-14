# Evently Bookings Service

A high-consistency booking management microservice built with FastAPI, designed for mission-critical event booking systems with distributed locking and real-time availability tracking.

## 🚀 Key Features

### Core Booking Management
- **High-Consistency Bookings**: ACID transactions with optimistic locking for data integrity
- **Real-Time Availability**: Live capacity tracking with distributed locking mechanisms
- **Booking Lifecycle**: Complete booking management from creation to completion
- **Payment Integration**: Payment status tracking and processing workflows
- **Audit Trail**: Comprehensive audit logging for compliance and debugging

### Advanced Features
- **Waitlist Management**: Priority-based waitlist with automatic notifications
- **Distributed Locking**: Redis-based locking for concurrent booking prevention
- **Optimistic Concurrency**: Version-based conflict resolution for high performance
- **Event-Driven Architecture**: Real-time event publishing for service integration
- **Capacity Management**: Real-time capacity tracking with reservation system

### Performance & Reliability
- **High Throughput**: Optimized for concurrent booking operations
- **Data Consistency**: Strong consistency guarantees with ACID compliance
- **Fault Tolerance**: Graceful degradation and automatic recovery mechanisms
- **Scalability**: Horizontal scaling with stateless design

## 🏗️ Architecture Overview

### Service Structure
```
bookings_service/
├── app/
│   ├── api/           # API layer with versioned endpoints
│   ├── core/          # Configuration and core utilities
│   ├── db/            # Database and Redis connections
│   ├── models/        # SQLAlchemy data models
│   ├── schemas/       # Pydantic request/response models
│   └── services/      # Business logic and event services
├── tests/             # Comprehensive test suite
└── Dockerfile         # Container configuration
```

### Technology Stack
- **Framework**: FastAPI (async, high-performance web framework)
- **Database**: PostgreSQL with SQLAlchemy ORM and Alembic migrations
- **Caching**: Redis for distributed locking and session management
- **Authentication**: JWT with role-based access control
- **Event Processing**: Redis pub/sub for real-time event notifications
- **Secrets Management**: Zero SDK for secure configuration management
- **Containerization**: Docker with Python 3.11 slim base image
- **Testing**: Pytest with comprehensive test coverage

## 📡 API Endpoints

### Booking Endpoints (JWT Required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/bookings/` | Create new booking with availability check |
| `GET` | `/api/v1/bookings/` | List user bookings with pagination |
| `GET` | `/api/v1/bookings/{booking_id}` | Get booking details |
| `PUT` | `/api/v1/bookings/{booking_id}/cancel` | Cancel booking |
| `GET` | `/api/v1/bookings/{booking_id}/status` | Get booking status |

### Availability Endpoints (JWT Required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/availability/{event_id}` | Check event availability |
| `POST` | `/api/v1/availability/{event_id}/reserve` | Reserve capacity temporarily |
| `DELETE` | `/api/v1/availability/{event_id}/release` | Release reserved capacity |

### Waitlist Endpoints (JWT Required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/waitlist/` | Join event waitlist |
| `GET` | `/api/v1/waitlist/` | List user waitlist entries |
| `PUT` | `/api/v1/waitlist/{entry_id}/cancel` | Cancel waitlist entry |
| `POST` | `/api/v1/waitlist/{entry_id}/book` | Book from waitlist notification |

### Admin Endpoints (Admin JWT Required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/admin/bookings/` | List all bookings with filters |
| `GET` | `/api/v1/admin/bookings/{booking_id}` | Get booking details (admin) |
| `PUT` | `/api/v1/admin/bookings/{booking_id}/confirm` | Confirm booking manually |
| `PUT` | `/api/v1/admin/bookings/{booking_id}/refund` | Process booking refund |
| `GET` | `/api/v1/admin/availability/` | System-wide availability overview |
| `GET` | `/api/v1/admin/waitlist/` | Manage waitlist entries |

### System Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health check |
| `GET` | `/api/v1/health` | Detailed health check |
| `GET` | `/api/v1/info` | Service information and capabilities |
| `GET` | `/docs` | Interactive API documentation |

## ⚙️ Configuration & Setup

### Environment Variables
The service uses Zero SDK for secure secrets management. Set the following environment variable:

```bash
export ZERO_TOKEN="your-zero-token-here"
```

### Required Secrets (via Zero SDK)
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` - PostgreSQL database configuration
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_USE_TLS` - Redis configuration for locking and caching
- `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRY_MINUTES` - JWT token configuration
- `CORS_ORIGINS` - CORS allowed origins (comma-separated)
- `BOOKING_TIMEOUT_MINUTES` - Booking reservation timeout (default: 15 minutes)
- `WAITLIST_NOTIFICATION_TIMEOUT_HOURS` - Waitlist notification expiry (default: 24 hours)

### Quick Start

#### Development Setup
```bash
cd bookings_service

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
docker build -t bookings-service:latest .

# Run with environment file
docker run -p 8002:8002 \
  -e ZERO_TOKEN="your-token" \
  bookings-service:latest
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
- **Role-based Access**: User and Admin roles with granular permissions
- **Token Validation**: Real-time JWT verification with user status checks
- **Authentication Required**: All endpoints require valid JWT tokens

### Security Features
- **CORS Protection**: Configurable origin restrictions
- **Input Validation**: Comprehensive Pydantic schema validation
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **Distributed Locking**: Redis-based locking to prevent race conditions
- **Audit Trail**: Complete booking lifecycle tracking for compliance

## 📊 Performance & Monitoring

### High-Consistency Features
- **Distributed Locking**: Redis-based locks for concurrent booking prevention
- **Optimistic Concurrency**: Version-based conflict resolution with retry logic
- **ACID Transactions**: Full database transaction support for data integrity
- **Real-Time Availability**: Live capacity tracking with immediate updates
- **Event Publishing**: Real-time notifications for booking lifecycle events

### Monitoring & Observability
- **Health Checks**: `/health` endpoint with database and Redis connectivity checks
- **Structured Logging**: JSON-formatted logs with request correlation IDs
- **Error Tracking**: Comprehensive error logging with stack traces
- **Performance Metrics**: Request timing, database query metrics, and lock contention
- **Service Information**: `/info` endpoint with service capabilities and features

### Other Features
- **Connection Pooling**: Optimized database connection management with automatic failover
- **Graceful Degradation**: Service continues with reduced functionality during outages
- **Stateless Design**: Horizontal scaling support with load balancer integration
- **Event Publishing**: Redis pub/sub for real-time inter-service communication
- **Cache Resilience**: Automatic fallback to database when cache is unavailable
- **Circuit Breaker Pattern**: Automatic failure detection and recovery mechanisms
- **Health Monitoring**: Continuous health checks with automatic service recovery

## 🔄 Data Consistency & Reliability

### Database Design
- **ACID Compliance**: Full transaction support with SQLAlchemy ORM
- **Data Integrity**: Foreign key constraints, unique constraints, and validation
- **Migration Management**: Alembic for database schema versioning
- **Connection Pooling**: Optimized database connection management

### Booking Data Models

#### Booking Model
```python
class Booking:
    id: int                    # Primary key
    user_id: int               # User ID (foreign key)
    event_id: int              # Event ID (foreign key)
    booking_reference: str     # Unique booking reference (indexed)
    quantity: int              # Number of tickets
    total_amount: decimal      # Total booking amount
    currency: str              # Currency code (default: USD)
    status: BookingStatus      # pending/confirmed/cancelled/expired/refunded/completed
    payment_status: PaymentStatus  # pending/processing/completed/failed/refunded
    booking_date: datetime     # Booking creation timestamp
    expires_at: datetime       # Booking expiry for pending bookings
    confirmed_at: datetime     # Confirmation timestamp
    cancelled_at: datetime     # Cancellation timestamp
    payment_method: str        # Payment method used
    payment_reference: str     # Payment gateway reference
    version: int               # Optimistic locking version
    created_at: datetime       # Creation timestamp (auto-generated)
    updated_at: datetime       # Last update timestamp (auto-updated)
    
    # Computed Properties
    is_active: bool            # Check if booking is active
    is_expired: bool           # Check if booking has expired
```

#### Event Availability Model
```python
class EventAvailability:
    id: int                    # Primary key
    event_id: int              # Event ID (unique, indexed)
    event_name: str            # Event name for reference
    total_capacity: int        # Total event capacity
    available_capacity: int    # Currently available capacity
    reserved_capacity: int     # Temporarily reserved capacity
    confirmed_capacity: int    # Confirmed bookings capacity
    price: decimal             # Event price per ticket
    version: int               # Optimistic locking version
    last_updated: datetime     # Last update timestamp
    
    # Computed Properties
    is_available: bool         # Check if event has available capacity
    utilization_percentage: float  # Capacity utilization percentage
```

#### Waitlist Entry Model
```python
class WaitlistEntry:
    id: int                    # Primary key
    user_id: int               # User ID (foreign key)
    event_id: int              # Event ID (foreign key)
    quantity: int              # Number of tickets requested
    priority: int              # Waitlist priority (lower = higher priority)
    status: WaitlistStatus     # pending/notified/booked/expired/cancelled
    joined_at: datetime        # Waitlist join timestamp
    notified_at: datetime      # Notification timestamp
    expires_at: datetime       # Notification expiry timestamp
    booked_at: datetime        # Booking from waitlist timestamp
    version: int               # Optimistic locking version
    created_at: datetime       # Creation timestamp (auto-generated)
    updated_at: datetime       # Last update timestamp (auto-updated)
    
    # Computed Properties
    is_active: bool            # Check if waitlist entry is active
    is_notification_expired: bool  # Check if notification has expired
```

### Trading-Grade Consistency Guarantees
- **Strong Consistency**: ACID transactions ensure data integrity for critical operations
- **Distributed Locking**: Redis-based locks prevent race conditions in concurrent bookings
- **Optimistic Concurrency**: Version-based conflict resolution with automatic retry
- **Event Publishing**: Real-time notifications for inter-service consistency with guaranteed delivery
- **Write-through Caching**: Immediate cache updates on writes with rollback capabilities
- **Read-after-write Consistency**: Guaranteed data visibility across all service instances
- **Transaction Support**: Full ACID compliance with isolation levels for concurrent access
- **Eventual Consistency**: Distributed cache synchronization with conflict resolution
- **Data Validation**: Multi-layer validation ensuring data accuracy and completeness
- **Audit Trail**: Complete booking lifecycle tracking for compliance and debugging

## 🚀 Deployment & Scaling

### Container Configuration
- **Base Image**: Python 3.11 slim for optimal size and security
- **Optimized Build**: Minimal dependencies with security-focused packages
- **Health Checks**: Built-in health monitoring with dependency checks

### Enterprise-Grade Scaling Considerations
- **Horizontal Scaling**: Stateless design supports unlimited instances with auto-scaling
- **Database Scaling**: Connection pooling with read replicas and automatic failover
- **Cache Scaling**: Redis cluster for high availability and performance with data sharding
- **Load Balancing**: Advanced load balancing with health checks and traffic distribution
- **Event Publishing**: Redis pub/sub for real-time inter-service communication with message persistence
- **Cache Distribution**: Redis-based cache sharing across instances with consistency guarantees
- **Auto-scaling**: Dynamic scaling based on load metrics and performance thresholds
- **Geographic Distribution**: Multi-region deployment support for global availability

### Production Deployment
- **Docker Compose**: Multi-service orchestration with PostgreSQL and Redis clusters
- **Environment Management**: Zero SDK for secure configuration with secret rotation
- **Monitoring**: Comprehensive health checks and structured logging for observability