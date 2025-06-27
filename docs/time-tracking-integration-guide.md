# MindBotz Time Tracking System Integration Guide

This guide covers the complete integration of the time tracking system with Stripe payments, user authentication, and the MindBot voice AI backend.

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client Apps   │◄──►│   Auth Service   │◄──►│   User DB       │
│                 │    │   (Port 8000)    │    │   (SQLite)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        
         ▼                        ▼                        
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Time Service  │◄──►│   Stripe API     │    │   Time DB       │
│   (Port 8001)   │    │                  │    │   (SQLite)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                                              
         ▼                                              
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Admin Panel   │◄──►│   LiveKit        │◄──►│   MindBot       │
│   (Port 8002)   │    │   Server         │    │   Agent         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Complete Setup Guide

### 1. Prerequisites

- Python 3.11+
- Stripe account with API keys
- LiveKit Cloud account or self-hosted server
- OpenAI API key
- Deepgram API key

### 2. Service Setup Order

#### Step 1: Authentication Service
```bash
cd backend/auth-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp env.example .env
# Edit with your LiveKit and JWT credentials

# Start auth service
python auth_server.py  # Runs on port 8000
```

#### Step 2: Time Tracking Service
```bash
cd backend/time-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp env.example .env
# Edit with your Stripe keys and JWT secret

# Start time service
python time_server.py  # Runs on port 8001
```

#### Step 3: Admin Dashboard
```bash
cd backend/admin-dashboard
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp env.example .env
# Edit with database paths and JWT secret

# Start admin dashboard
python admin_server.py  # Runs on port 8002
```

#### Step 4: Time-Aware MindBot Agent
```bash
cd backend/basic-mindbot
# Use existing virtual environment or create new
pip install -r requirements.txt

# Start time-aware agent
python time_aware_mindbot.py start
```

### 3. Environment Configuration

Create `.env` files for each service:

#### Auth Service (.env)
```env
LIVEKIT_API_SECRET="your_livekit_api_secret"
LIVEKIT_API_KEY="your_livekit_api_key"
LIVEKIT_URL="wss://your-project.livekit.cloud"
JWT_SECRET="your-super-secret-jwt-key-change-this"
```

#### Time Service (.env)
```env
STRIPE_SECRET_KEY="sk_test_your_stripe_secret_key"
STRIPE_PUBLISHABLE_KEY="pk_test_your_stripe_publishable_key"
STRIPE_WEBHOOK_SECRET="whsec_your_webhook_secret"
JWT_SECRET="your-super-secret-jwt-key-change-this"
AUTH_SERVICE_URL="http://localhost:8000"
```

#### Admin Dashboard (.env)
```env
JWT_SECRET="your-super-secret-jwt-key-change-this"
TIME_DB_PATH="../time-service/mindbot_time_tracking.db"
AUTH_DB_PATH="../auth-service/mindbot_users.db"
```

## 💳 Stripe Integration Setup

### 1. Create Stripe Account and Get Keys

1. Sign up at [stripe.com](https://stripe.com)
2. Navigate to **Developers > API keys**
3. Copy your **Publishable key** and **Secret key**
4. For testing, use the test keys (start with `pk_test_` and `sk_test_`)

### 2. Set Up Webhook Endpoint

1. Go to **Developers > Webhooks** in Stripe Dashboard
2. Click **Add endpoint**
3. Set URL to: `https://your-domain.com/webhooks/stripe`
4. Select events: `payment_intent.succeeded`
5. Copy the **Signing secret** (starts with `whsec_`)

### 3. Test Stripe Integration

```bash
# Test with Stripe test cards
curl -X POST http://localhost:8001/time/purchase \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "package_id": "starter_1h",
    "payment_method_id": "pm_card_visa"
  }'
```

## 🔄 Complete User Flow

### 1. User Registration/Authentication
```bash
# Register new user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password",
    "full_name": "John Doe"
  }'

# Response includes JWT token for API access
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "livekit_token": "eyJhbGciOiJIUzI1NiIs...",
  "livekit_url": "wss://your-project.livekit.cloud"
}
```

### 2. Purchase Time Cards
```bash
# Get available packages
curl http://localhost:8001/time/pricing

# Purchase time card
curl -X POST http://localhost:8001/time/purchase \
  -H "Authorization: Bearer JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "package_id": "basic_5h",
    "payment_method_id": "pm_card_visa"
  }'
```

### 3. Voice Session with Time Tracking
```bash
# Get room-specific LiveKit token
curl -X POST http://localhost:8000/auth/token \
  -H "Authorization: Bearer JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "room_name": "voice_session_123",
    "participant_name": "John Doe"
  }'

# Client connects to LiveKit room with token
# Time-aware agent automatically:
# 1. Recognizes user from participant identity
# 2. Checks time balance
# 3. Starts time tracking
# 4. Provides personalized greeting with balance info
```

### 4. Admin Monitoring
```bash
# Admin login (must be in ADMIN_USERS list)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@mindbot.ai",
    "password": "admin_password"
  }'

# Access admin dashboard
curl -X GET http://localhost:8002/admin/dashboard \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

## 🤖 Agent Integration Features

### Time-Aware Responses

The time-aware agent provides intelligent responses based on user balance:

```python
# Low balance greeting
"Hi John! You have about 15 minutes left. Consider purchasing more time cards to continue our conversations!"

# Sufficient balance greeting  
"Welcome back, John! You have 2.5 hours of conversation time remaining. What would you like to talk about today?"

# Guest user greeting
"Hey there! I'm MindBot. Note that as a guest, your session time isn't tracked. Consider creating an account to purchase time cards!"
```

### Function Tools Available

1. **check_time_balance()**: Get current balance and usage info
2. **get_time_packages()**: List available time card packages with pricing
3. **estimate_session_cost()**: Show current session cost and remaining time
4. **lookup_weather()**: Standard weather lookup (example function)

### Automatic Time Management

- **Session Start**: Automatically begins time tracking when user joins
- **Session End**: Deducts time from balance when user leaves
- **Balance Checks**: Prevents sessions if insufficient balance
- **Low Balance Alerts**: Warns users when time is running low

## 📊 Analytics and Monitoring

### Revenue Analytics
```bash
# Get 30-day revenue report
curl -X GET http://localhost:8002/admin/analytics/revenue?days=30 \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"

# Response includes:
{
  "total_revenue_cents": 12599,
  "total_transactions": 15,
  "avg_transaction_cents": 839,
  "daily_revenue": [...],
  "package_stats": [...]
}
```

### Usage Analytics
```bash
# Get usage statistics
curl -X GET http://localhost:8002/admin/analytics/usage?days=30 \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"

# Response includes:
{
  "active_users": 25,
  "total_sessions": 142,
  "total_hours_used": 89.5,
  "avg_session_minutes": 18.2
}
```

### User Management
```bash
# Get user analytics
curl -X GET http://localhost:8002/admin/users?limit=50 \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"

# Get detailed user report
curl -X GET http://localhost:8002/admin/reports/user/123 \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

## 🛡️ Security Considerations

### Production Security Checklist

- [ ] Use production Stripe keys (live mode)
- [ ] Set strong, unique JWT secret (256+ bit entropy)
- [ ] Enable HTTPS for all endpoints
- [ ] Configure proper CORS policies
- [ ] Use environment variables for all secrets
- [ ] Enable database backups
- [ ] Set up monitoring and alerting
- [ ] Configure rate limiting on API endpoints
- [ ] Validate all input data
- [ ] Use least-privilege access controls

### Webhook Security

```python
# Verify Stripe webhook signatures
try:
    event = stripe.Webhook.construct_event(
        payload, sig_header, STRIPE_WEBHOOK_SECRET
    )
except stripe.error.SignatureVerificationError:
    raise HTTPException(status_code=400, detail="Invalid signature")
```

## 🚀 Production Deployment

### Docker Compose Setup

```yaml
version: '3.8'
services:
  auth-service:
    build: ./backend/auth-service
    ports:
      - "8000:8000"
    environment:
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_URL=${LIVEKIT_URL}
      - JWT_SECRET=${JWT_SECRET}
    volumes:
      - auth_data:/app/data

  time-service:
    build: ./backend/time-service
    ports:
      - "8001:8001"
    environment:
      - STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
      - STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET}
      - JWT_SECRET=${JWT_SECRET}
    volumes:
      - time_data:/app/data

  admin-dashboard:
    build: ./backend/admin-dashboard
    ports:
      - "8002:8002"
    environment:
      - JWT_SECRET=${JWT_SECRET}
    volumes:
      - auth_data:/app/auth_data
      - time_data:/app/time_data

volumes:
  auth_data:
  time_data:
```

### Load Balancer Configuration

```nginx
upstream auth_service {
    server auth-service:8000;
}

upstream time_service {
    server time-service:8001;
}

upstream admin_service {
    server admin-dashboard:8002;
}

server {
    listen 443 ssl;
    server_name api.mindbot.ai;

    location /auth/ {
        proxy_pass http://auth_service/;
    }

    location /time/ {
        proxy_pass http://time_service/;
    }

    location /admin/ {
        proxy_pass http://admin_service/;
    }
}
```

## 📈 Scaling Considerations

### Database Optimization

For production, consider migrating to PostgreSQL:

```python
# production_database.py
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://user:password@db_host/mindbot"
engine = create_async_engine(DATABASE_URL, echo=False)
```

### Caching Strategy

Implement Redis caching for frequently accessed data:

```python
# Add Redis for session caching
import redis
redis_client = redis.Redis(host='redis', port=6379, db=0)

# Cache user balances
def cache_user_balance(user_id: int, balance: dict):
    redis_client.setex(f"balance:{user_id}", 300, json.dumps(balance))
```

### Message Queue for Async Processing

Use Celery for background tasks:

```python
# tasks.py
from celery import Celery

app = Celery('mindbot')

@app.task
def send_low_balance_notification(user_id: int, remaining_minutes: int):
    # Send email notification
    # Update user preferences
    # Log notification event
```

## 🆘 Troubleshooting

### Common Issues

#### Stripe Webhook Not Working
```bash
# Test webhook locally with Stripe CLI
stripe listen --forward-to localhost:8001/webhooks/stripe
```

#### Time Not Deducting
```bash
# Check session status
curl -X GET http://localhost:8001/time/sessions \
  -H "Authorization: Bearer JWT_TOKEN"

# Verify user balance
curl -X GET http://localhost:8001/time/balance \
  -H "Authorization: Bearer JWT_TOKEN"
```

#### Authentication Issues
```bash
# Verify JWT token
python -c "
import jwt
token = 'YOUR_JWT_TOKEN'
try:
    payload = jwt.decode(token, 'YOUR_JWT_SECRET', algorithms=['HS256'])
    print('Token valid:', payload)
except Exception as e:
    print('Token error:', e)
"
```

### Health Checks

```bash
# Check all services
curl http://localhost:8000/health  # Auth service
curl http://localhost:8001/health  # Time service  
curl http://localhost:8002/health  # Admin dashboard
```

This integration guide provides everything needed to deploy a complete time tracking system for MindBotz with secure payments, user management, and comprehensive analytics.