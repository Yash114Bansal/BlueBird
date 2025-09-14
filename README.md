# Evently - Enterprise Event Management Platform

A scalable, high-availability microservices-based backend system for event management, built with FastAPI and designed for trading-grade consistency and 99.99% uptime.

## 🏗️ Architecture Overview

Evently implements a modern microservices architecture with 5 core services, each designed for specific business domains while maintaining loose coupling and high cohesion.

<img width="7807" height="4649" alt="image" src="https://github.com/user-attachments/assets/a9a49e16-dd29-4749-8680-a82aca227ed4" />


### Core Services

| Service | Purpose | Key Features |
|---------|---------|--------------|
| **Auth Service** | Authentication & Authorization | JWT tokens, RBAC, OTP verification, session management |
| **Events Service** | Event Management | CRUD operations, caching, pub/sub notifications |
| **Bookings Service** | Booking & Availability | High-consistency bookings, waitlist, optimistic locking |
| **Analytics Service** | Analytics & Reporting | Real-time metrics, event-driven aggregation |
| **Email Workers** | Asynchronous Processing | Celery-based email notifications, background tasks |

### Technology Stack

- **Framework**: FastAPI (async, high-performance)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache**: Redis (caching, sessions, pub/sub, distributed locking)
- **Message Queue**: Celery with Redis broker
- **Authentication**: JWT with role-based access control
- **Secrets Management**: Zero SDK
- **Containerization**: Docker with health checks
- **Monitoring**: Structured logging, health endpoints

## 🔗 Service Communication

### Inter-Service Communication Patterns

1. **Asynchronous Pub/Sub**: Redis channels for event notifications
2. **Background Processing**: Celery tasks for non-blocking operations

### Communication Flow

```
Client → Auth Service (JWT validation)
Client → Events Service (browse events)
Client → Bookings Service (create booking)
Events Service - Bookings Service (add published events)
Events Service → Analytics Service (event metrics)
Bookings Service → Analytics Service (booking metrics)
Bookings Service → Email Workers (send notifications)
Auth Service -> Email Workers (send emails)
```

## 📊 Database Design

<img width="2948" height="2341" alt="image" src="https://github.com/user-attachments/assets/4bc72f99-7795-48a3-bec1-6843803e8c94" />


### Service-Specific Databases

Each service maintains its own PostgreSQL database with domain-specific models:

#### Auth Service
- **Users**: User accounts, roles, verification status
- **UserSessions**: Active sessions, security tracking

#### Events Service  
- **Events**: Event details, capacity, pricing, status

#### Bookings Service
- **Bookings**: Booking records with optimistic locking
- **BookingItems**: Individual booking line items
- **EventAvailability**: Real-time capacity tracking
- **WaitlistEntry**: Waitlist management
- **AuditLogs**: Complete audit trail

#### Analytics Service
- **EventStats**: Per-event aggregated metrics
- **DailyStats**: Time-series daily aggregates
- **TopEvents**: Pre-computed leaderboards
- **SystemMetrics**: System-wide KPIs
- **EventLog**: Event processing audit

## 🎯 Major Design Decisions & Trade-offs

### 1. Microservices vs Monolith

**Decision**: Microservices architecture
**Trade-offs**:
- ✅ **Pros**: Independent scaling, technology diversity, fault isolation, team autonomy
- ❌ **Cons**: Increased complexity, network latency, distributed data management
- **Rationale**: Event management has distinct domains (auth, events, bookings, analytics) that benefit from independent evolution

### 2. Database Per Service

**Decision**: Each service owns its database
**Trade-offs**:
- ✅ **Pros**: Data isolation, independent schema evolution, service autonomy
- ❌ **Cons**: Cross-service queries require API calls, eventual consistency challenges
- **Rationale**: Strong domain boundaries enable independent scaling and reduce coupling

### 3. Event-Driven Architecture

**Decision**: Redis pub/sub for inter-service communication
**Trade-offs**:
- ✅ **Pros**: Loose coupling, real-time updates, scalability
- ❌ **Cons**: Eventual consistency, message ordering challenges
- **Rationale**: Analytics and notifications can tolerate eventual consistency for better performance

### 4. Optimistic Locking for Bookings

**Decision**: Version-based optimistic locking in bookings
**Trade-offs**:
- ✅ **Pros**: High concurrency, better performance than pessimistic locking
- ❌ **Cons**: Retry logic required, potential for conflicts
- **Rationale**: Booking conflicts are rare, optimistic locking provides better user experience

### 5. Redis for Multiple Use Cases

**Decision**: Redis for caching, sessions, pub/sub, and distributed locking
**Trade-offs**:
- ✅ **Pros**: Single technology, high performance, rich data structures
- ❌ **Cons**: Single point of failure, memory limitations
- **Rationale**: Redis provides excellent performance for all use cases

## 🚀 Scalability & Fault Tolerance

### Horizontal Scaling Strategy

1. **Stateless Services**: All services are stateless, enabling easy horizontal scaling
2. **Load Balancing**: Docker Compose with multiple replicas
3. **Database Scaling**: Read replicas and connection pooling
4. **Cache Scaling**: Redis clustering for high availability

### Fault Tolerance Mechanisms

1. **Circuit Breaker Pattern**: Automatic service degradation
2. **Health Checks**: Built-in health endpoints with dependency checks
3. **Graceful Degradation**: Services continue with reduced functionality
4. **Retry Logic**: Exponential backoff for transient failures
5. **Distributed Locking**: Redis-based locks prevent race conditions

### High Availability Features

- **99.99% Uptime SLA**: Designed for mission-critical operations
- **Automatic Failover**: Service restart policies and health monitoring
- **Data Redundancy**: Database backups and replication
- **Zero-Downtime Deployments**: Rolling updates with health checks

## 🔒 Security Architecture

### Authentication & Authorization
- **JWT Tokens**: Stateless authentication with access/refresh token rotation
- **Role-Based Access Control**: User and Admin roles with granular permissions
- **Session Management**: Redis-based session tracking with security features

### Data Protection
- **Zero SDK**: Secure secrets management
- **Input Validation**: Pydantic schemas for all API inputs
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **Rate Limiting**: Redis-based rate limiting on authentication endpoints

### Network Security
- **CORS Protection**: Configurable origin restrictions
- **HTTPS Enforcement**: TLS termination at load balancer
- **Internal Network**: Isolated Docker network for service communication

## 📈 Performance Optimizations

### Caching Strategy
- **Multi-Level Caching**: Application-level and Redis caching
- **Smart Cache Invalidation**: Event-driven cache updates
- **TTL Management**: Configurable cache expiration

### Database Optimizations
- **Connection Pooling**: Optimized database connections
- **Indexing Strategy**: Strategic indexes for query performance
- **Query Optimization**: Efficient SQLAlchemy queries

### Async Processing
- **Non-Blocking Operations**: FastAPI async/await throughout
- **Background Tasks**: Celery for email processing
- **Event-Driven Updates**: Real-time notifications via pub/sub

## 🛠️ Creative Features & Optimizations

### 1. Event-Driven Analytics
- **Real-time Aggregation**: Analytics updated via Redis pub/sub events
- **Pre-computed Metrics**: Optimized dashboard queries
- **Time-series Optimization**: Efficient daily/weekly/monthly aggregates

### 2. Smart Waitlist Management
- **Priority-based Queue**: FIFO with admin override capabilities
- **Automatic Notifications**: Real-time waitlist position updates
- **Capacity Release**: Automatic booking when capacity becomes available

### 3. Optimistic Concurrency Control
- **Version-based Locking**: Prevents booking conflicts without blocking
- **Retry Mechanisms**: Automatic retry with exponential backoff
- **Audit Trail**: Complete history of all booking changes

### 4. Zero-Configuration Secrets
- **Zero SDK Integration**: Secure secrets management without hardcoded values
- **Environment Flexibility**: Seamless local/production configuration
- **Security by Default**: No secrets in code or environment files

## 📚 Service Documentation

### Core Services
- [**Auth Service**](./auth_service/README.md) - Authentication, JWT, RBAC, OTP verification
- [**Events Service**](./events_service/README.md) - Event CRUD, caching, pub/sub notifications  
- [**Bookings Service**](./bookings_service/README.md) - High-consistency bookings, waitlist, availability
- [**Analytics Service**](./analytics_service/README.md) - Real-time analytics, metrics, reporting
- [**Email Workers**](./workers/README.md) - Asynchronous email processing, notifications

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Zero SDK token for secrets management

### Local Development
```bash
# Clone repository
git clone <repository-url>
cd evently

# Set up environment
export ZERO_TOKEN="your-zero-token"

# Start all services
docker-compose up -d

# Check service health
curl http://localhost:35000/health  # Auth Service
curl http://localhost:35001/health  # Events Service  
curl http://localhost:35002/health  # Bookings Service
curl http://localhost:35003/health  # Analytics Service
```

### Service Ports
- Auth Service: http://localhost:35000
- Events Service: http://localhost:35001
- Bookings Service: http://localhost:35002
- Analytics Service: http://localhost:35003

## 🧪 Testing

### Running Tests
```bash
# Run all service tests
pytest auth_service/tests/ -v
pytest events_service/tests/ -v
pytest bookings_service/tests/ -v
pytest analytics_service/tests/ -v
```

### Test Coverage
- **Unit Tests**: Service logic and business rules
- **Integration Tests**: API endpoints and database operations
- **Concurrency Tests**: Booking conflicts and race conditions
- **Performance Tests**: Load testing and optimization validation

## 📊 Monitoring & Observability

### Health Monitoring
- **Health Endpoints**: `/health` on all services with dependency checks
- **Service Information**: `/info` endpoints with service capabilities
- **Structured Logging**: JSON-formatted logs with correlation IDs

### Performance Metrics
- **Request Timing**: Response time tracking
- **Database Metrics**: Query performance and connection pooling
- **Cache Metrics**: Hit rates and performance
- **Error Tracking**: Comprehensive error logging and alerting

## 🔄 Data Consistency Models

### Strong Consistency (ACID)
- **User Authentication**: Immediate consistency for security
- **Booking Operations**: ACID transactions for financial accuracy
- **Payment Processing**: Strong consistency for monetary operations

### Eventual Consistency
- **Analytics Updates**: Event-driven updates with eventual consistency
- **Cache Invalidation**: Eventual consistency for performance
- **Cross-Service Queries**: Eventual consistency for scalability

## 🏢 Enterprise Features

### Compliance & Audit
- **Complete Audit Trail**: All operations logged with timestamps
- **Data Retention**: Configurable retention policies
- **Security Logging**: Authentication and authorization events

### Multi-Tenancy Ready
- **Service Isolation**: Independent service scaling
- **Data Isolation**: Service-specific databases
- **Configuration Management**: Zero SDK for tenant-specific configs

### Disaster Recovery
- **Database Backups**: Automated backup strategies
- **Service Redundancy**: Multiple service instances
- **Geographic Distribution**: Multi-region deployment support

---

