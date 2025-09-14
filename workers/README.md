# Evently Workers Service

A high-performance background task processing microservice built with Celery, designed for asynchronous email notifications and event-driven communication across the Evently platform.

## 🚀 Key Features

### Core Email Processing
- **Asynchronous Email Delivery**: High-throughput email processing with Celery workers
- **Email Templates**: Professional HTML and text email templates for all notifications
- **Retry Logic**: Automatic retry with exponential backoff for failed email deliveries
- **Queue Management**: Dedicated email notification queues with priority handling
- **Delivery Tracking**: Comprehensive email delivery status tracking and logging

### Advanced Features
- **Event-Driven Architecture**: Real-time task processing from Redis pub/sub channels
- **Multi-Template Support**: Specialized email templates for different notification types
- **Database Integration**: Direct database access for user information and email addresses
- **Health Monitoring**: Built-in health checks and worker monitoring capabilities
- **Scalable Processing**: Horizontal scaling with multiple worker instances

### Performance & Reliability
- **99.99% Uptime SLA**: Mission-critical email processing with minimal downtime
- **High Throughput**: Optimized for processing thousands of emails per minute
- **Fault Tolerance**: Graceful error handling and automatic recovery mechanisms
- **Resource Management**: Efficient memory and CPU usage with configurable concurrency

## 🏗️ Architecture Overview

### Service Structure
```
workers/
├── email_workers/     # Email notification workers
│   └── tasks.py      # Celery email tasks
├── shared/           # Shared utilities and configuration
│   ├── config/       # Celery and worker configuration
│   └── utils/        # Database and email utilities
├── start_email_workers.py  # Worker startup script
├── entrypoint.sh     # Container entrypoint
└── Dockerfile        # Container configuration
```

### Technology Stack
- **Task Queue**: Celery with Redis broker and result backend
- **Email Processing**: SMTP with TLS/SSL support for secure delivery
- **Database**: PostgreSQL integration for user data access
- **Configuration**: Zero SDK for secure secrets management
- **Containerization**: Docker with Python 3.11 slim base image

## 📧 Email Notification Types

### Authentication Emails
| Task | Description | Template |
|------|-------------|----------|
| `send_otp_verification_email` | OTP verification for email confirmation | Professional verification template with security notice |
| `send_welcome_email` | Welcome email after successful registration | Branded welcome template with next steps |

### Booking Emails
| Task | Description | Template |
|------|-------------|----------|
| `send_booking_confirmation` | Booking confirmation with details | Detailed confirmation template with booking information |
| `send_booking_cancellation` | Booking cancellation notification | Cancellation template with refund information |

### Waitlist Emails
| Task | Description | Template |
|------|-------------|----------|
| `send_waitlist_notification` | Waitlist spot available notification | Urgent notification template with time limit |
| `send_waitlist_joined` | Waitlist join confirmation | Confirmation template with position information |
| `send_waitlist_cancellation` | Waitlist removal notification | Removal template with rejoin option |

### System Emails
| Task | Description | Template |
|------|-------------|----------|
| `health_check` | Worker health status check | System health monitoring |

## ⚙️ Configuration & Setup

### Environment Variables
The service uses Zero SDK for secure secrets management. Set the following environment variable:

```bash
export ZERO_TOKEN="your-zero-token-here"
```

### Required Secrets (via Zero SDK)
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_USE_TLS` - Redis configuration for Celery broker
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS` - Email server configuration
- `FROM_ADDRESS`, `FROM_NAME` - Email sender configuration
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` - Database configuration for user data
- `MAX_RETRIES`, `RETRY_DELAY` - Email retry configuration

### Quick Start

#### Development Setup
```bash
cd workers

# Install dependencies
pip install -r requirements.txt

# Set environment variable
export ZERO_TOKEN="your-token"

# Start email workers
python start_email_workers.py

# Start worker monitor (optional)
python start_email_workers.py --monitor
```

#### Docker Deployment
```bash
# Build the image
docker build -t workers-service:latest .

# Run email workers
docker run -p 8004:8004 \
  -e ZERO_TOKEN="your-token" \
  workers-service:latest

# Run worker monitor
docker run -p 5555:5555 \
  -e ZERO_TOKEN="your-token" \
  workers-service:latest --monitor
```

#### Production Deployment
```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Scale workers
docker-compose up -d --scale workers=3
```

## 🧪 Testing

### Running Tests
```bash
pytest tests/ -v
```

## 🔒 Security & Configuration

### Email Security
- **TLS/SSL Support**: Secure email transmission with TLS/SSL encryption
- **Authentication**: SMTP authentication with username/password
- **Configuration Security**: Zero SDK for secure secrets management

### Worker Security
- **Resource Limits**: Configurable CPU and memory limits
- **Health Checks**: Built-in health monitoring and automatic recovery
- **Error Handling**: Secure error handling without sensitive data exposure

## 📊 Performance & Monitoring

### Email Processing Features
- **Asynchronous Processing**: Non-blocking email delivery with Celery
- **Queue Management**: Dedicated email notification queues with priority handling
- **Retry Logic**: Automatic retry with exponential backoff (max 3 retries)
- **Batch Processing**: Efficient batch processing of email tasks
- **Template Caching**: Optimized email template rendering

### Monitoring & Observability
- **Structured Logging**: JSON-formatted logs with task correlation IDs
- **Error Tracking**: Comprehensive error logging with retry information
- **Performance Metrics**: Task processing times and success rates
- **Health Checks**: Worker health status and configuration validation

### Other Features
- **Horizontal Scaling**: Multiple worker instances with load distribution
- **Graceful Degradation**: Service continues with reduced functionality during outages
- **Auto-scaling**: Dynamic scaling based on queue depth and processing load
- **Queue Resilience**: Redis-based queue persistence with automatic recovery
- **Circuit Breaker Pattern**: Automatic failure detection and recovery mechanisms
- **Health Monitoring**: Continuous health checks with automatic service recovery

## 🔄 Data Consistency & Reliability

### Task Processing
- **ACID Compliance**: Reliable task processing with transaction support
- **Message Persistence**: Redis-based message persistence with durability
- **Retry Mechanisms**: Automatic retry with exponential backoff for failed tasks
- **Dead Letter Queue**: Failed task handling with manual intervention capability
- **Task Tracking**: Complete task lifecycle tracking for debugging

### Email Delivery
- **Delivery Confirmation**: SMTP delivery status tracking and logging
- **Template Validation**: Email template validation before sending
- **Content Sanitization**: XSS protection and content sanitization
- **Rate Limiting**: Built-in rate limiting to prevent email abuse
- **Bounce Handling**: Email bounce detection and handling

### Trading-Grade Consistency Guarantees
- **Message Durability**: Redis-based message persistence with guaranteed delivery
- **Task Processing**: Reliable task processing with retry mechanisms
- **Email Delivery**: SMTP-based email delivery with delivery confirmation
- **Error Handling**: Comprehensive error handling with automatic retry
- **Data Validation**: Multi-layer validation ensuring email content accuracy
- **Audit Trail**: Complete task processing trail for compliance and debugging
- **Queue Management**: Reliable queue management with message persistence
- **Worker Coordination**: Distributed worker coordination with Redis
- **Health Monitoring**: Continuous health monitoring with automatic recovery

## 🚀 Deployment & Scaling

### Container Configuration
- **Base Image**: Python 3.11 slim for optimal size and security
- **Optimized Build**: Minimal dependencies with security-focused packages
- **Health Checks**: Built-in health monitoring with dependency checks
- **Resource Limits**: Configurable CPU and memory constraints

### Enterprise-Grade Scaling Considerations
- **Horizontal Scaling**: Multiple worker instances with load distribution
- **Queue Scaling**: Redis cluster for high availability and performance
- **Auto-scaling**: Dynamic scaling based on queue depth and processing load
- **Geographic Distribution**: Multi-region deployment support for global availability
- **Worker Coordination**: Distributed worker coordination with Redis
- **Task Distribution**: Intelligent task distribution across worker instances

### Production Deployment
- **Docker Compose**: Multi-service orchestration with Redis clusters
- **Environment Management**: Zero SDK for secure configuration with secret rotation
- **Monitoring**: Comprehensive health checks and structured logging for observability
- **Scaling**: Easy horizontal scaling with Docker Compose scale commands

## 📈 Worker Monitoring


### Health Endpoints
- **Worker Health**: Individual worker health status
- **Queue Health**: Queue status and processing metrics
- **Configuration Health**: Configuration validation and status
- **Database Health**: Database connectivity and performance
- **Email Service Health**: SMTP connectivity and configuration status