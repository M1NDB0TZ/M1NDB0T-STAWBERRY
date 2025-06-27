# MindBotz Voice Agent Payment System - Launch Preparation Plan

## 📋 Current System Analysis

Based on the existing codebase, you have a sophisticated system with:
- ✅ Authentication service with JWT/LiveKit integration
- ✅ Time tracking service with Stripe payments  
- ✅ Admin dashboard for monitoring
- ✅ Multiple voice agents (basic, enhanced, RAG-enabled)
- ✅ Comprehensive documentation
- ✅ Database schemas and API endpoints

## 🎯 Phase 1: Code Review and Organization

### 1.1 Code Quality Improvements

#### Backend Services Code Review
```bash
# Create code review checklist
backend/
├── auth-service/
│   ├── auth_server.py ✅ (Well structured)
│   ├── requirements.txt ✅
│   └── env.example ✅
├── time-service/
│   ├── time_server.py ✅ (Comprehensive)
│   ├── requirements.txt ✅
│   └── env.example ✅
├── admin-dashboard/
│   ├── admin_server.py ✅ (Feature complete)
│   ├── requirements.txt ✅
│   └── env.example ✅
└── basic-mindbot/
    ├── basic-mindbot.py ✅
    ├── enhanced-mindbot.py ✅
    ├── time_aware_mindbot.py ✅
    └── requirements.txt ✅
```

#### Immediate Code Improvements Needed

1. **Add Type Hints and Docstrings**
```python
# Example for auth_server.py functions
async def create_user(
    self, 
    email: str, 
    full_name: str, 
    password: str
) -> Optional[User]:
    """
    Create a new user with secure password hashing.
    
    Args:
        email: User's email address (must be unique)
        full_name: User's display name
        password: Plain text password (will be hashed)
        
    Returns:
        User object if successful, None if email already exists
        
    Raises:
        sqlite3.IntegrityError: If email constraint is violated
    """
```

2. **Enhanced Error Handling**
```python
# Add to each service
import structlog
logger = structlog.get_logger()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", 
                error=str(exc), 
                path=request.url.path,
                method=request.method)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

3. **Input Validation Enhancement**
```python
# Add to Pydantic models
from pydantic import validator, Field

class UserRegister(BaseModel):
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    full_name: str = Field(..., min_length=2, max_length=100)
    
    @validator('password')
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        return v
```

### 1.2 File Organization Improvements

```
backend/
├── shared/                    # NEW: Shared utilities
│   ├── __init__.py
│   ├── database.py           # Common DB utilities
│   ├── auth.py              # Shared auth functions
│   ├── logging_config.py    # Centralized logging
│   └── validators.py        # Common validation
├── config/                   # NEW: Configuration management
│   ├── __init__.py
│   ├── settings.py          # Centralized settings
│   └── environment.py       # Environment validation
└── tests/                    # NEW: Comprehensive testing
    ├── unit/
    ├── integration/
    └── load/
```

## 🎯 Phase 2: Environment and Configuration

### 2.1 Enhanced Environment Management

#### Create Centralized Configuration
```python
# backend/config/settings.py
from pydantic import BaseSettings, validator
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    auth_db_path: str = "mindbot_users.db"
    time_db_path: str = "mindbot_time_tracking.db"
    
    # Authentication
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # LiveKit
    livekit_api_key: str
    livekit_api_secret: str
    livekit_url: str
    
    # Stripe
    stripe_secret_key: str
    stripe_publishable_key: str
    stripe_webhook_secret: str
    
    # AI Services
    openai_api_key: str
    deepgram_api_key: str
    
    # Service URLs
    auth_service_url: str = "http://localhost:8000"
    time_service_url: str = "http://localhost:8001"
    admin_service_url: str = "http://localhost:8002"
    
    # Admin Users
    admin_users: list[str] = ["admin@mindbot.ai"]
    
    # Application
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    
    @validator('jwt_secret')
    def jwt_secret_must_be_strong(cls, v):
        if len(v) < 32:
            raise ValueError('JWT secret must be at least 32 characters')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

#### Master Environment Template
```bash
# backend/.env.example
# ===============================================
# MindBotz Voice Agent System Configuration
# ===============================================

# Environment
ENVIRONMENT=development
DEBUG=false
LOG_LEVEL=INFO

# Authentication & Security
JWT_SECRET=your-super-secure-jwt-secret-min-32-chars-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Database Paths
AUTH_DB_PATH=mindbot_users.db
TIME_DB_PATH=mindbot_time_tracking.db

# LiveKit Configuration
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
LIVEKIT_URL=wss://your-project.livekit.cloud

# Stripe Payment Processing
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# AI Service API Keys
OPENAI_API_KEY=sk-your_openai_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key

# Service URLs (for multi-service communication)
AUTH_SERVICE_URL=http://localhost:8000
TIME_SERVICE_URL=http://localhost:8001
ADMIN_SERVICE_URL=http://localhost:8002

# Admin Configuration
ADMIN_USERS=admin@mindbot.ai,support@mindbot.ai

# Optional: Advanced Configuration
MAX_CONCURRENT_SESSIONS=100
SESSION_TIMEOUT_MINUTES=30
LOW_BALANCE_THRESHOLD_MINUTES=30
WEBHOOK_RETRY_ATTEMPTS=3
```

### 2.2 Environment Validation Script

```python
# backend/scripts/validate_environment.py
#!/usr/bin/env python3
"""
Environment validation script for MindBotz system
Run before starting any services to ensure all required variables are set
"""

import os
import sys
from pathlib import Path
import requests
import stripe
from livekit import api

def validate_environment():
    """Validate all environment variables and external service connectivity"""
    
    print("🔍 Validating MindBotz Environment Configuration...")
    
    errors = []
    warnings = []
    
    # Required environment variables
    required_vars = {
        'JWT_SECRET': 'Authentication secret key',
        'LIVEKIT_API_KEY': 'LiveKit API key',
        'LIVEKIT_API_SECRET': 'LiveKit API secret',
        'LIVEKIT_URL': 'LiveKit server URL',
        'OPENAI_API_KEY': 'OpenAI API key',
        'DEEPGRAM_API_KEY': 'Deepgram API key',
        'STRIPE_SECRET_KEY': 'Stripe secret key',
        'STRIPE_WEBHOOK_SECRET': 'Stripe webhook secret'
    }
    
    # Check required variables
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            errors.append(f"❌ {var} is required ({description})")
        elif var == 'JWT_SECRET' and len(value) < 32:
            errors.append(f"❌ JWT_SECRET must be at least 32 characters")
        else:
            print(f"✅ {var} is set")
    
    # Test external service connectivity
    print("\n🌐 Testing External Service Connectivity...")
    
    # Test LiveKit
    try:
        lk_token = api.AccessToken(
            os.getenv('LIVEKIT_API_KEY'),
            os.getenv('LIVEKIT_API_SECRET')
        ).with_identity("test").to_jwt()
        print("✅ LiveKit credentials valid")
    except Exception as e:
        errors.append(f"❌ LiveKit connection failed: {e}")
    
    # Test Stripe
    try:
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        stripe.Account.retrieve()
        print("✅ Stripe credentials valid")
    except Exception as e:
        errors.append(f"❌ Stripe connection failed: {e}")
    
    # Test OpenAI (simple API call)
    try:
        import openai
        openai.api_key = os.getenv('OPENAI_API_KEY')
        # Just test key format, don't make actual API call
        if os.getenv('OPENAI_API_KEY', '').startswith('sk-'):
            print("✅ OpenAI API key format valid")
        else:
            warnings.append("⚠️ OpenAI API key format may be invalid")
    except Exception as e:
        warnings.append(f"⚠️ OpenAI validation warning: {e}")
    
    # Check database permissions
    try:
        db_path = Path(os.getenv('AUTH_DB_PATH', 'mindbot_users.db'))
        db_path.parent.mkdir(exist_ok=True)
        print("✅ Database directory accessible")
    except Exception as e:
        errors.append(f"❌ Database path issue: {e}")
    
    # Print results
    print(f"\n📊 Validation Results:")
    print(f"✅ Checks passed: {len(required_vars) - len(errors)}")
    print(f"❌ Errors: {len(errors)}")
    print(f"⚠️ Warnings: {len(warnings)}")
    
    if errors:
        print("\n❌ ERRORS FOUND:")
        for error in errors:
            print(f"  {error}")
        return False
    
    if warnings:
        print("\n⚠️ WARNINGS:")
        for warning in warnings:
            print(f"  {warning}")
    
    print("\n🎉 Environment validation successful!")
    return True

if __name__ == "__main__":
    if not validate_environment():
        sys.exit(1)
```

## 🎯 Phase 3: Supabase Integration (Future Enhancement)

### 3.1 Database Migration to Supabase

```sql
-- migrations/001_initial_schema.sql
-- User authentication tables
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE
);

-- Time cards and billing
CREATE TABLE IF NOT EXISTS time_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activation_code TEXT UNIQUE NOT NULL,
    total_minutes INTEGER NOT NULL,
    remaining_minutes INTEGER NOT NULL,
    activated_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'expired', 'used')),
    stripe_payment_intent_id TEXT
);

-- Voice sessions
CREATE TABLE IF NOT EXISTS voice_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    room_name TEXT NOT NULL,
    start_time TIMESTAMPTZ DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    duration_seconds INTEGER,
    cost_minutes INTEGER,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'error')),
    agent_type TEXT DEFAULT 'basic',
    quality_rating INTEGER CHECK (quality_rating BETWEEN 1 AND 5)
);

-- Payment history
CREATE TABLE IF NOT EXISTS payment_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stripe_payment_intent_id TEXT UNIQUE NOT NULL,
    amount_cents INTEGER NOT NULL,
    currency TEXT DEFAULT 'usd',
    status TEXT NOT NULL,
    time_card_id UUID REFERENCES time_cards(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

-- Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE time_cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_history ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can read own data" ON users
    FOR SELECT TO authenticated
    USING (auth.uid() = id);

CREATE POLICY "Users can read own time cards" ON time_cards
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Users can read own sessions" ON voice_sessions
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

-- Indexes for performance
CREATE INDEX idx_time_cards_user_id ON time_cards(user_id);
CREATE INDEX idx_voice_sessions_user_id ON voice_sessions(user_id);
CREATE INDEX idx_payment_history_user_id ON payment_history(user_id);
CREATE INDEX idx_voice_sessions_status ON voice_sessions(status);
```

## 🎯 Phase 4: Voice Agent System Enhancement

### 4.1 Agent State Management

```python
# backend/shared/agent_state.py
from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime
import json

@dataclass
class AgentSession:
    """Comprehensive agent session state management"""
    
    user_id: str
    session_id: str
    room_name: str
    agent_type: str  # 'basic', 'enhanced', 'rag'
    start_time: datetime
    
    # User context
    user_preferences: Dict[str, Any]
    conversation_history: list
    
    # Time tracking
    time_balance_minutes: int
    session_cost_minutes: int
    low_balance_warned: bool = False
    
    # Agent state
    current_mood: str = "helpful"
    interruption_count: int = 0
    function_calls_made: int = 0
    
    # Quality metrics
    response_times: list = None
    user_satisfaction: Optional[int] = None
    
    def __post_init__(self):
        if self.response_times is None:
            self.response_times = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'user_id': self.user_id,
            'session_id': self.session_id,
            'room_name': self.room_name,
            'agent_type': self.agent_type,
            'start_time': self.start_time.isoformat(),
            'user_preferences': self.user_preferences,
            'conversation_history': self.conversation_history[-10:],  # Keep last 10
            'time_balance_minutes': self.time_balance_minutes,
            'session_cost_minutes': self.session_cost_minutes,
            'low_balance_warned': self.low_balance_warned,
            'current_mood': self.current_mood,
            'interruption_count': self.interruption_count,
            'function_calls_made': self.function_calls_made,
            'avg_response_time': sum(self.response_times) / len(self.response_times) if self.response_times else 0,
            'user_satisfaction': self.user_satisfaction
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentSession':
        """Create from dictionary"""
        return cls(
            user_id=data['user_id'],
            session_id=data['session_id'],
            room_name=data['room_name'],
            agent_type=data['agent_type'],
            start_time=datetime.fromisoformat(data['start_time']),
            user_preferences=data.get('user_preferences', {}),
            conversation_history=data.get('conversation_history', []),
            time_balance_minutes=data.get('time_balance_minutes', 0),
            session_cost_minutes=data.get('session_cost_minutes', 0),
            low_balance_warned=data.get('low_balance_warned', False),
            current_mood=data.get('current_mood', 'helpful'),
            interruption_count=data.get('interruption_count', 0),
            function_calls_made=data.get('function_calls_made', 0),
            user_satisfaction=data.get('user_satisfaction')
        )
```

### 4.2 Enhanced Error Recovery

```python
# backend/shared/error_recovery.py
import asyncio
import logging
from typing import Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)

def with_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for retrying failed operations with exponential backoff"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts",
                            exc_info=True
                        )
                        raise last_exception
                    
                    wait_time = delay * (backoff ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}, "
                        f"retrying in {wait_time:.1f}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
            
            raise last_exception
        
        return wrapper
    return decorator

class CircuitBreaker:
    """Circuit breaker pattern for external service calls"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time and
            asyncio.get_event_loop().time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = asyncio.get_event_loop().time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
```

## 🎯 Phase 5: Testing and Quality Assurance

### 5.1 Comprehensive Test Suite

```python
# backend/tests/conftest.py
import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def test_db():
    """Create test database"""
    engine = create_engine("sqlite:///test_mindbot.db")
    # Setup test schema
    yield engine
    # Cleanup

@pytest.fixture
def auth_client():
    """Test client for auth service"""
    from backend.auth_service.auth_server import app
    return TestClient(app)

@pytest.fixture
def time_client():
    """Test client for time service"""
    from backend.time_service.time_server import app
    return TestClient(app)

@pytest.fixture
def test_user():
    """Create test user data"""
    return {
        "email": "test@mindbot.ai",
        "password": "TestPassword123!",
        "full_name": "Test User"
    }
```

```python
# backend/tests/integration/test_payment_flow.py
import pytest
import stripe
from unittest.mock import patch

class TestPaymentFlow:
    """Test complete payment and time card flow"""
    
    @pytest.mark.asyncio
    async def test_complete_purchase_flow(self, auth_client, time_client, test_user):
        """Test: Register → Login → Purchase → Activate → Use Time"""
        
        # 1. Register user
        register_response = auth_client.post("/auth/register", json=test_user)
        assert register_response.status_code == 200
        jwt_token = register_response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {jwt_token}"}
        
        # 2. Check initial balance (should be 0)
        balance_response = time_client.get("/time/balance", headers=headers)
        assert balance_response.json()["balance"]["total_minutes"] == 0
        
        # 3. Mock Stripe payment
        with patch('stripe.PaymentIntent.create') as mock_stripe:
            mock_stripe.return_value.id = "pi_test_123"
            mock_stripe.return_value.client_secret = "pi_test_123_secret"
            
            # Purchase time card
            purchase_response = time_client.post(
                "/time/purchase",
                headers=headers,
                json={
                    "package_id": "starter_1h",
                    "payment_method_id": "pm_card_visa"
                }
            )
            assert purchase_response.status_code == 200
            activation_code = purchase_response.json()["activation_code"]
        
        # 4. Simulate webhook (payment success)
        with patch('stripe.Webhook.construct_event') as mock_webhook:
            mock_webhook.return_value = {
                'type': 'payment_intent.succeeded',
                'data': {
                    'object': {
                        'id': 'pi_test_123',
                        'amount': 999,
                        'metadata': {'user_id': '1'}
                    }
                }
            }
            
            webhook_response = time_client.post("/webhooks/stripe")
            assert webhook_response.status_code == 200
        
        # 5. Check balance after activation
        balance_response = time_client.get("/time/balance", headers=headers)
        assert balance_response.json()["balance"]["total_minutes"] == 60
    
    @pytest.mark.asyncio
    async def test_time_usage_flow(self, time_client, authenticated_headers):
        """Test time usage during voice session"""
        
        # Start session
        start_response = time_client.post(
            "/time/session/start",
            headers=authenticated_headers,
            json={
                "session_id": "test_session_123",
                "room_name": "test_room"
            }
        )
        assert start_response.status_code == 200
        
        # End session (5 minutes)
        end_response = time_client.post(
            "/time/session/end",
            headers=authenticated_headers,
            json={
                "session_id": "test_session_123",
                "duration_seconds": 300
            }
        )
        assert end_response.status_code == 200
        assert end_response.json()["cost_minutes"] == 5
```

### 5.2 Load Testing Configuration

```python
# backend/tests/load/locustfile.py
from locust import HttpUser, task, between
import json
import random

class MindBotUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Setup: Register and login user"""
        user_data = {
            "email": f"loadtest{random.randint(1, 10000)}@mindbot.ai",
            "password": "LoadTest123!",
            "full_name": "Load Test User"
        }
        
        # Register
        response = self.client.post("/auth/register", json=user_data)
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def check_balance(self):
        """Frequently check balance"""
        self.client.get("/time/balance", headers=self.headers)
    
    @task(1)
    def start_session(self):
        """Start voice session"""
        self.client.post(
            "/time/session/start",
            headers=self.headers,
            json={
                "session_id": f"load_test_{random.randint(1, 1000)}",
                "room_name": "load_test_room"
            }
        )
    
    @task(1)
    def get_pricing(self):
        """Check pricing tiers"""
        self.client.get("/time/pricing")

# Run with: locust -f locustfile.py --host=http://localhost:8001
```

## 🎯 Phase 6: Launch Preparation

### 6.1 Production Deployment Checklist

```yaml
# backend/docker-compose.prod.yml
version: '3.8'

services:
  auth-service:
    build:
      context: ./auth-service
      dockerfile: Dockerfile.prod
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - LOG_LEVEL=INFO
    env_file: .env.prod
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  time-service:
    build:
      context: ./time-service
      dockerfile: Dockerfile.prod
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    env_file: .env.prod
    ports:
      - "8001:8001"
    depends_on:
      - auth-service
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  admin-dashboard:
    build:
      context: ./admin-dashboard
      dockerfile: Dockerfile.prod
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    env_file: .env.prod
    ports:
      - "8002:8002"
    depends_on:
      - auth-service
      - time-service
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - auth-service
      - time-service
      - admin-dashboard
    restart: unless-stopped

volumes:
  db_data:
```

### 6.2 Monitoring and Alerting

```python
# backend/monitoring/prometheus_metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time
import functools

# Metrics
REQUEST_COUNT = Counter('mindbot_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('mindbot_request_duration_seconds', 'Request duration')
ACTIVE_SESSIONS = Gauge('mindbot_active_sessions', 'Active voice sessions')
USER_BALANCE_TOTAL = Gauge('mindbot_user_balance_minutes_total', 'Total user balance in minutes')
STRIPE_PAYMENTS = Counter('mindbot_stripe_payments_total', 'Stripe payments', ['status'])

def track_metrics(func):
    """Decorator to track API metrics"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            REQUEST_COUNT.labels(method='POST', endpoint=func.__name__, status='success').inc()
            return result
        except Exception as e:
            REQUEST_COUNT.labels(method='POST', endpoint=func.__name__, status='error').inc()
            raise
        finally:
            REQUEST_DURATION.observe(time.time() - start_time)
    
    return wrapper

# Start metrics server
if __name__ == "__main__":
    start_http_server(8080)
    print("Prometheus metrics server started on port 8080")
```

### 6.3 CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy MindBot System

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_mindbot
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r backend/requirements-dev.txt
    
    - name: Run tests
      run: |
        cd backend
        python -m pytest tests/ -v --cov=. --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml

  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Run security scan
      run: |
        pip install bandit safety
        bandit -r backend/ -f json -o security-report.json
        safety check --json --output security-deps.json
    
    - name: Upload security reports
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: |
          security-report.json
          security-deps.json

  deploy:
    needs: [test, security-scan]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to production
      run: |
        # Deploy using your preferred method
        # (Railway, Docker, Kubernetes, etc.)
        echo "Deploying to production..."
```

### 6.4 Documentation Generation

```bash
#!/bin/bash
# scripts/generate_docs.sh

echo "🚀 Generating MindBot System Documentation..."

# Create docs directory
mkdir -p docs/api docs/guides docs/architecture

# Generate API documentation
echo "📝 Generating API documentation..."
python -m pdoc backend/auth_service --html --output-dir docs/api/auth
python -m pdoc backend/time_service --html --output-dir docs/api/time
python -m pdoc backend/admin_dashboard --html --output-dir docs/api/admin

# Generate OpenAPI specs
echo "📋 Generating OpenAPI specifications..."
python -c "
from backend.auth_service.auth_server import app as auth_app
from backend.time_service.time_server import app as time_app
import json

with open('docs/api/auth_openapi.json', 'w') as f:
    json.dump(auth_app.openapi(), f, indent=2)

with open('docs/api/time_openapi.json', 'w') as f:
    json.dump(time_app.openapi(), f, indent=2)
"

# Generate database schema documentation
echo "🗄️ Generating database documentation..."
python -c "
import sqlite3
import json

# Document auth database
conn = sqlite3.connect('backend/auth-service/mindbot_users.db')
cursor = conn.execute('SELECT sql FROM sqlite_master WHERE type=\"table\"')
auth_schema = [row[0] for row in cursor.fetchall()]

# Document time database  
conn = sqlite3.connect('backend/time-service/mindbot_time_tracking.db')
cursor = conn.execute('SELECT sql FROM sqlite_master WHERE type=\"table\"')
time_schema = [row[0] for row in cursor.fetchall()]

with open('docs/database_schema.json', 'w') as f:
    json.dump({
        'auth_database': auth_schema,
        'time_database': time_schema
    }, f, indent=2)
"

echo "✅ Documentation generated successfully!"
echo "📁 Check the docs/ directory for all generated documentation"
```

## 📊 Success Metrics and KPIs

### Technical Metrics
- ✅ 99.9% uptime for all services
- ✅ <500ms average API response time
- ✅ <100ms voice agent response latency
- ✅ 100% test coverage for critical paths
- ✅ 0 security vulnerabilities
- ✅ <1% error rate

### Business Metrics
- 💰 Revenue tracking and reporting
- 👥 User acquisition and retention
- ⏱️ Average session duration
- 🎯 Time card utilization rates
- 📈 Customer satisfaction scores
- 🔄 Payment success rates

## 🎯 Next Steps

1. **Week 1**: Code review and organization (Phase 1)
2. **Week 2**: Environment setup and validation (Phase 2)
3. **Week 3**: Testing implementation (Phase 5)
4. **Week 4**: Production deployment preparation (Phase 6)
5. **Week 5**: Launch and monitoring

## 📞 Support and Maintenance

- 📧 Technical support: tech@mindbot.ai
- 🔧 Maintenance schedule: Weekly during low-traffic hours
- 📊 Performance monitoring: 24/7 automated alerts
- 🛡️ Security updates: Monthly security reviews
- 📈 Feature updates: Quarterly releases