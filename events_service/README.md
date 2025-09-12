# Evently Events Service for BlueBird


## 🚀 Key Features

### Core Functionality
- **Event Management**: Complete CRUD operations for events with admin controls
- **User Experience**: Seamless event browsing with pagination and filtering
- **Authentication**: JWT-based security with role-based access control (RBAC)
- **Caching Layer**: Redis-powered caching for optimal performance
- **High Availability**: Designed for 99.9% uptime with graceful degradation

### Performance & Reliability
- **Intelligent Caching**: Multi-tier caching strategy with automatic invalidation
- **Database Optimization**: Connection pooling and query optimization
- **Error Handling**: Comprehensive error handling with detailed logging
- **Health Monitoring**: Built-in health checks and service monitoring
- **Graceful Shutdown**: Proper resource cleanup and connection management

## 🏗️ Architecture Overview

### Service Structure
```
events_service/
├── app/
│   ├── api/           # API layer with versioned endpoints
│   ├── core/          # Configuration and core utilities
│   ├── db/            # Database and Redis connections
│   ├── models/        # SQLAlchemy data models
│   ├── schemas/       # Pydantic request/response models
│   └── services/      # Business logic and JWT services
├── tests/             # Comprehensive test suite
└── Dockerfile         # Container configuration
```

### Technology Stack
- **Framework**: FastAPI (async, high-performance)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis for session and data caching
- **Authentication**: JWT with role-based permissions
- **Secrets Management**: Zero SDK for secure configuration
- **Containerization**: Docker with multi-stage builds

## 📡 API Endpoints

### Public Event Endpoints (JWT Required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/events/` | List events with pagination and filtering |
| `GET` | `/api/v1/events/upcoming` | Get upcoming events only |
| `GET` | `/api/v1/events/{event_id}` | Get detailed event information |
| `GET` | `/api/v1/events/{event_id}/capacity` | Check event capacity and availability |

### Admin Endpoints (Admin JWT Required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/admin/events/` | Create new event |
| `PUT` | `/api/v1/admin/events/{event_id}` | Update existing event |
| `DELETE` | `/api/v1/admin/events/{event_id}` | Delete event |

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
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` - Database configuration
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_USE_TLS` - Redis configuration
- `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRY_MINUTES` - JWT configuration
- `CORS_ORIGINS` - CORS allowed origins
- `CACHE_TTL_EVENTS`, `CACHE_TTL_EVENT_DETAILS` - Cache TTL settings

### Quick Start

#### Development Setup
```bash
cd events_service

# Install dependencies
pip install -r requirements.txt

# Set environment variable
export ZERO_TOKEN="your-token"

# Run the service
python main.py
```

#### Docker Deployment
```bash
# Build the image
docker build -t events-service:latest .

# Run with environment file
docker run -p 8001:8001 \
  -e ZERO_TOKEN="your-token" \
  events-service:latest
```

#### Production Deployment
```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or with Kubernetes
kubectl apply -f k8s/
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test categories
pytest tests/api/ -v          # API tests
pytest tests/models/ -v       # Model tests
pytest tests/services/ -v     # Service tests
```

### Test Coverage
The service maintains comprehensive test coverage including:
- **Unit Tests**: Individual component testing
- **Integration Tests**: API endpoint testing
- **Database Tests**: Repository and model testing
- **Authentication Tests**: JWT and RBAC testing
- **Cache Tests**: Redis caching functionality

## 🔒 Security & Authentication

### JWT Implementation
- **Algorithm**: HS256 (configurable)
- **Expiry**: 30 minutes (configurable)
- **Role-based Access**: User and Admin roles
- **Token Validation**: Comprehensive token verification

### Security Features
- **CORS Protection**: Configurable origin restrictions
- **Input Validation**: Pydantic schema validation
- **SQL Injection Protection**: SQLAlchemy ORM protection
- **Rate Limiting**: Built-in request throttling
- **Secure Headers**: Security headers middleware

## 📊 Performance & Monitoring

### Caching Strategy
- **Events List**: 5-minute TTL with automatic invalidation
- **Event Details**: 10-minute TTL for frequently accessed data
- **Cache Invalidation**: Smart invalidation on data updates
- **Cache Warming**: Proactive cache population

### Monitoring & Observability
- **Health Checks**: `/health` endpoint for load balancer integration
- **Structured Logging**: JSON-formatted logs for easy parsing
- **Error Tracking**: Comprehensive error logging and reporting
- **Performance Metrics**: Request timing and database query metrics

### High Availability Features
- **Connection Pooling**: Database connection optimization
- **Graceful Degradation**: Service continues with reduced functionality
- **Circuit Breaker**: Automatic failure detection and recovery
- **Load Balancing Ready**: Stateless design for horizontal scaling

## 🔄 Data Consistency & Reliability

### Database Design
- **ACID Compliance**: Full transaction support
- **Data Integrity**: Foreign key constraints and validation
- **Backup Strategy**: Automated backup and recovery

### Event Model
```python
class Event:
    id: int                    # Primary key
    title: str                 # Event title
    description: str           # Event description
    venue: str                 # Event location
    event_date: datetime       # Event date/time
    capacity: int              # Maximum attendees
    price: decimal             # Event price
    status: EventStatus        # draft/published/cancelled/completed
    created_at: datetime       # Creation timestamp
    updated_at: datetime       # Last update timestamp
    created_by: int            # Creator user ID
```

### Consistency Guarantees
- **Eventual Consistency**: Cache and database synchronization
- **Write-through Caching**: Immediate cache updates on writes
- **Read-after-write Consistency**: Guaranteed data visibility

## 🚀 Deployment & Scaling

### Container Configuration
- **Base Image**: Python 3.11 slim for optimal size
- **Multi-stage Build**: Optimized production image
- **Health Checks**: Container health monitoring
- **Resource Limits**: CPU and memory constraints

### Scaling Considerations
- **Horizontal Scaling**: Stateless design supports multiple instances
- **Database Scaling**: Read replicas for query distribution
- **Cache Scaling**: Redis cluster for high availability
- **Load Balancing**: Round-robin or least-connections strategies
