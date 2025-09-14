# Evently Auth Service

A comprehensive authentication and authorization microservice built with FastAPI, designed for high-performance app.

## 🚀 Key Features

### Core Authentication
- **User Registration & Login**: Complete user lifecycle management with email verification
- **JWT Token Management**: Secure access tokens (30 min) and refresh tokens (7 days)
- **OTP Email Verification**: 6-digit OTP system with Redis caching and rate limiting
- **Password Security**: Bcrypt hashing with configurable salt rounds
- **Session Management**: Redis-powered session tracking with IP and user agent validation

### Authorization & Security
- **Role-Based Access Control**: User and Admin roles with granular permissions
- **Rate Limiting**: Per-endpoint rate limiting with Redis backend using Sliding Window
- **Session Security**: Multi-device session management with revocation capabilities
- **Input Validation**: Comprehensive Pydantic schema validation
- **CORS Protection**: Configurable origin restrictions

### Email & Notifications
- **Asynchronous Email**: Celery-powered email workers for OTP and welcome emails
- **Email Templates**: Professional email templates for verification and notifications
- **Retry Logic**: Robust email delivery with retry mechanisms
- **Queue Management**: Dedicated email notification queues

### Performance & Reliability
- **High Availability**: Stateless design supporting horizontal scaling
- **Health Monitoring**: Comprehensive health checks for database and Redis
- **Error Handling**: Detailed error responses with proper HTTP status codes
- **Structured Logging**: JSON-formatted logs for easy parsing and monitoring

## 🏗️ Architecture Overview

### Service Structure
```
auth_service/
├── app/
│   ├── api/           # API layer with versioned endpoints
│   ├── core/          # Configuration and core utilities
│   ├── db/            # Database and Redis connections
│   ├── models/        # SQLAlchemy data models
│   ├── schemas/       # Pydantic request/response models
│   └── services/      # Business logic and authentication services
├── tests/             # Comprehensive test suite
└── Dockerfile         # Container configuration
```

### Technology Stack
- **Framework**: FastAPI (async, high-performance web framework)
- **Database**: PostgreSQL with SQLAlchemy ORM and Alembic migrations
- **Caching**: Redis for session management, OTP storage, and rate limiting
- **Authentication**: JWT with bcrypt password hashing
- **Email**: Celery workers with Redis broker for asynchronous email delivery
- **Secrets Management**: Zero SDK for secure configuration management
- **Containerization**: Docker with Python 3.11 slim base image
- **Testing**: Pytest with comprehensive test coverage

## 📡 API Endpoints

### Authentication Endpoints (Public)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | User registration with OTP email |
| `POST` | `/api/v1/auth/login` | User authentication |
| `POST` | `/api/v1/auth/refresh` | Refresh JWT access token |
| `POST` | `/api/v1/auth/logout` | User logout (invalidate session) |
| `POST` | `/api/v1/auth/verify-email` | Verify email with OTP |
| `POST` | `/api/v1/auth/resend-otp` | Resend OTP verification email |

### User Profile Endpoints (JWT Required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/auth/me` | Get current user profile |
| `PUT` | `/api/v1/auth/me` | Update user profile |
| `POST` | `/api/v1/auth/change-password` | Change user password |
| `GET` | `/api/v1/auth/sessions` | Get user active sessions |
| `DELETE` | `/api/v1/auth/sessions/{session_id}` | Terminate specific session |

### Admin Endpoints (Admin JWT Required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/admin/users` | List all users with pagination |
| `GET` | `/api/v1/admin/users/{user_id}` | Get user by ID |
| `PUT` | `/api/v1/admin/users/{user_id}` | Update user profile |
| `DELETE` | `/api/v1/admin/users/{user_id}` | Delete user account |
| `POST` | `/api/v1/admin/users/{user_id}/activate` | Activate user account |
| `POST` | `/api/v1/admin/users/{user_id}/deactivate` | Deactivate user account |
| `GET` | `/api/v1/admin/users/{user_id}/sessions` | Get user sessions |
| `DELETE` | `/api/v1/admin/users/{user_id}/sessions` | Revoke all user sessions |
| `POST` | `/api/v1/admin/cleanup-sessions` | Cleanup expired sessions |

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
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_USE_TLS` - Redis configuration for sessions and OTP
- `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRY_MINUTES` - JWT token configuration
- `REFRESH_TOKEN_EXPIRY_DAYS` - Refresh token expiry (default: 7 days)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS` - Email configuration
- `CORS_ORIGINS` - CORS allowed origins (comma-separated)
- `RATE_LIMIT_LOGIN`, `RATE_LIMIT_REGISTER`, `RATE_LIMIT_WINDOW` - Rate limiting configuration

### Quick Start

#### Development Setup
```bash
cd auth_service

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
docker build -t auth-service:latest .

# Run with environment file
docker run -p 8000:8000 \
  -e ZERO_TOKEN="your-token" \
  auth-service:latest
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
- **Access Token Expiry**: 30 minutes (configurable)
- **Refresh Token Expiry**: 7 days (configurable)
- **Token Rotation**: Automatic refresh token rotation on use
- **Role-based Access**: User and Admin roles with granular permissions
- **Token Validation**: Comprehensive token verification with user status checks

### Security Features
- **Password Security**: Bcrypt hashing with configurable salt rounds
- **Rate Limiting**: Per-endpoint rate limiting with Redis backend
- **Session Security**: IP tracking, user agent validation, and multi-device support
- **OTP Security**: 6-digit OTP with 3 attempts and 10-minute expiry
- **CORS Protection**: Configurable origin restrictions
- **Input Validation**: Comprehensive Pydantic schema validation
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **Email Verification**: Mandatory email verification before login

## 📊 Performance & Monitoring

### Session Management
- **Redis Caching**: Session data cached for fast access and scalability
- **Session Invalidation**: Automatic cleanup of expired sessions
- **Concurrent Sessions**: Support for multiple active sessions per user
- **Session Security**: IP and user agent tracking with session revocation
- **Session Cleanup**: Admin endpoint for manual session cleanup

### Monitoring & Observability
- **Health Checks**: `/health` endpoint with database and Redis connectivity checks
- **Structured Logging**: JSON-formatted logs with request correlation IDs
- **Error Tracking**: Comprehensive error logging with stack traces
- **Performance Metrics**: Request timing, database query metrics, and Redis operations
- **Service Information**: `/info` endpoint with service capabilities and features

## 🔄 Data Consistency & Reliability

### Database Design
- **ACID Compliance**: Full transaction support with SQLAlchemy ORM
- **Data Integrity**: Foreign key constraints, unique constraints, and validation
- **Migration Management**: Alembic for database schema versioning
- **Connection Pooling**: Optimized database connection management

### Data Models

#### User Model
```python
class User:
    id: int                    # Primary key
    email: str                 # Unique email address (indexed)
    username: str              # Unique username (indexed)
    hashed_password: str       # Bcrypt hashed password
    full_name: str             # User's full name (optional)
    is_active: bool            # Account status (default: True)
    is_verified: bool          # Email verification status (default: False)
    role: UserRole             # user/admin role (default: user)
    created_at: datetime       # Creation timestamp (auto-generated)
    updated_at: datetime       # Last update timestamp (auto-updated)
    last_login: datetime       # Last login timestamp (nullable)
```

#### Session Model
```python
class UserSession:
    id: int                    # Primary key
    user_id: int               # Foreign key to user (indexed)
    session_token: str         # Unique session token (indexed)
    refresh_token: str         # Refresh token (indexed, nullable)
    is_active: bool            # Session status (default: True)
    expires_at: datetime       # Session expiry timestamp
    created_at: datetime       # Creation timestamp (auto-generated)
    last_accessed: datetime    # Last access timestamp (auto-updated)
    ip_address: str            # Client IP address (nullable)
    user_agent: str            # Client user agent (nullable)
```

### Consistency Guarantees
- **Session Consistency**: Redis and database synchronization with automatic cleanup
- **Token Validation**: Real-time token verification with user status checks
- **Password Security**: Secure password storage with bcrypt hashing
- **OTP Management**: Redis-based OTP storage with automatic expiry
- **Email Verification**: Mandatory verification before account activation

## 🚀 Deployment & Scaling

### Container Configuration
- **Base Image**: Python 3.11 slim for optimal size and security
- **Optimized Build**: Minimal dependencies with security-focused packages
- **Health Checks**: Built-in health monitoring with dependency checks
- **Resource Limits**: Configurable CPU and memory constraints

### Scaling Considerations
- **Horizontal Scaling**: Stateless design supports multiple instances
- **Database Scaling**: Connection pooling with read replicas support
- **Cache Scaling**: Redis cluster for high availability and performance
- **Load Balancing**: Round-robin or least-connections strategies
- **Email Workers**: Separate Celery workers for email processing
- **Session Distribution**: Redis-based session sharing across instances

### Production Deployment
- **Docker Compose**: Multi-service orchestration with PostgreSQL and Redis
- **Environment Management**: Zero SDK for secure configuration
- **Monitoring**: Health checks and structured logging for observability
- **Backup Strategy**: Database backups and Redis persistence
