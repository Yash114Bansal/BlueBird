# Evently Auth Service for BlueBird


## 🚀 Key Features

### Core Functionality
- **User Authentication**: Complete registration, login, and session management
- **JWT Token Management**: Secure token generation, validation, and refresh
- **Role-Based Access Control**: User and Admin role management with granular permissions
- **Session Management**: Redis-powered session tracking and security
- **High Availability**: Designed for 99.9% uptime with graceful degradation

### Security & Performance
- **Password Security**: Bcrypt hashing with salt rounds
- **Rate Limiting**: Configurable rate limits for authentication endpoints
- **Session Security**: IP tracking, user agent validation, and session invalidation
- **Error Handling**: Comprehensive error handling with detailed logging
- **Health Monitoring**: Built-in health checks and service monitoring

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
- **Framework**: FastAPI (async, high-performance)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis for session and token caching
- **Authentication**: JWT with bcrypt password hashing
- **Secrets Management**: Zero SDK for secure configuration
- **Containerization**: Docker with optimized builds

## 📡 API Endpoints

### Authentication Endpoints (Public)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | User registration |
| `POST` | `/api/v1/auth/login` | User login |
| `POST` | `/api/v1/auth/refresh` | Refresh JWT token |
| `POST` | `/api/v1/auth/logout` | User logout |
| `POST` | `/api/v1/auth/change-password` | Change user password |
| `POST` | `/api/v1/auth/forgot-password` | Request password reset |
| `POST` | `/api/v1/auth/reset-password` | Reset password with token |

### User Profile Endpoints (JWT Required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/auth/me` | Get current user profile |
| `PUT` | `/api/v1/auth/me` | Update user profile |
| `GET` | `/api/v1/auth/sessions` | Get user active sessions |
| `DELETE` | `/api/v1/auth/sessions/{session_id}` | Terminate specific session |

### Admin Endpoints (Admin JWT Required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/admin/users` | List all users |
| `GET` | `/api/v1/admin/users/{user_id}` | Get user by ID |
| `PUT` | `/api/v1/admin/users/{user_id}` | Update user |
| `DELETE` | `/api/v1/admin/users/{user_id}` | Delete user |
| `PUT` | `/api/v1/admin/users/{user_id}/verify` | Verify user account |
| `PUT` | `/api/v1/admin/users/{user_id}/activate` | Activate/deactivate user |

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
- `REFRESH_TOKEN_EXPIRY_DAYS` - Refresh token expiry
- `PASSWORD_RESET_EXPIRY_HOURS` - Password reset token expiry
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` - Email configuration
- `CORS_ORIGINS` - CORS allowed origins
- `RATE_LIMIT_LOGIN`, `RATE_LIMIT_REGISTER`, `RATE_LIMIT_WINDOW` - Rate limiting

### Quick Start

#### Development Setup
```bash
cd auth_service

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

## 🔒 Security & Authentication

### JWT Implementation
- **Algorithm**: HS256 (configurable)
- **Expiry**: 30 minutes (configurable)
- **Refresh Tokens**: 7-day expiry with automatic renewal
- **Role-based Access**: User and Admin roles
- **Token Validation**: Comprehensive token verification

### Security Features
- **Password Hashing**: Bcrypt with configurable salt rounds
- **Rate Limiting**: Per-endpoint rate limiting with Redis
- **Session Management**: IP tracking and user agent validation
- **CORS Protection**: Configurable origin restrictions
- **Input Validation**: Pydantic schema validation
- **SQL Injection Protection**: SQLAlchemy ORM protection

## 📊 Performance & Monitoring

### Session Management
- **Redis Caching**: Session data cached for fast access
- **Session Invalidation**: Automatic cleanup of expired sessions
- **Concurrent Sessions**: Support for multiple active sessions per user
- **Session Security**: IP and user agent tracking

### Monitoring & Observability
- **Health Checks**: `/health` endpoint for load balancer integration
- **Structured Logging**: JSON-formatted logs for easy parsing
- **Error Tracking**: Comprehensive error logging and reporting
- **Performance Metrics**: Request timing and database query metrics

## 🔄 Data Consistency & Reliability

### Database Design
- **ACID Compliance**: Full transaction support
- **Data Integrity**: Foreign key constraints and validation


### User Model
```python
class User:
    id: int                    # Primary key
    email: str                 # Unique email address
    username: str              # Unique username
    hashed_password: str       # Bcrypt hashed password
    full_name: str             # User's full name
    is_active: bool            # Account status
    is_verified: bool          # Email verification status
    role: UserRole             # user/admin role
    created_at: datetime       # Creation timestamp
    updated_at: datetime       # Last update timestamp
    last_login: datetime       # Last login timestamp
```

### Session Model
```python
class UserSession:
    id: int                    # Primary key
    user_id: int               # Foreign key to user
    session_token: str         # Unique session token
    refresh_token: str         # Refresh token
    is_active: bool            # Session status
    expires_at: datetime       # Session expiry
    created_at: datetime       # Creation timestamp
    last_accessed: datetime    # Last access timestamp
    ip_address: str            # Client IP address
    user_agent: str            # Client user agent
```

### Consistency Guarantees
- **Session Consistency**: Redis and database synchronization
- **Token Validation**: Real-time token verification
- **Password Security**: Secure password storage and verification

## 🚀 Deployment & Scaling

### Container Configuration
- **Base Image**: Python 3.11 slim for optimal size
- **Optimized Build**: Minimal dependencies for security
- **Health Checks**: Container health monitoring
- **Resource Limits**: CPU and memory constraints

### Scaling Considerations
- **Horizontal Scaling**: Stateless design supports multiple instances
- **Database Scaling**: Read replicas for query distribution
- **Cache Scaling**: Redis cluster for high availability
- **Load Balancing**: Round-robin or least-connections strategies
