"""
Pytest configuration and shared fixtures for MindBot tests
Provides common test setup, database fixtures, and mock objects
"""

import os
import pytest
import asyncio
import tempfile
import sqlite3
from typing import Generator, Dict, Any
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

# FastAPI and HTTP testing
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Database
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# MindBot imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "true"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-testing-only-min-32-chars"


# Test database fixtures
@pytest.fixture(scope="session")
def test_auth_db():
    """Create temporary auth database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    # Create test database with schema
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """)
    
    conn.execute("""
        CREATE TABLE user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            room_name TEXT NOT NULL,
            session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            session_end TIMESTAMP,
            duration_seconds INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    os.unlink(db_path)


@pytest.fixture(scope="session")
def test_time_db():
    """Create temporary time tracking database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    # Create test database with schema
    conn = sqlite3.connect(db_path)
    
    # Time cards table
    conn.execute("""
        CREATE TABLE time_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            activation_code TEXT UNIQUE NOT NULL,
            total_minutes INTEGER NOT NULL,
            remaining_minutes INTEGER NOT NULL,
            activated_at TIMESTAMP,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            stripe_payment_intent_id TEXT
        )
    """)
    
    # Time sessions table
    conn.execute("""
        CREATE TABLE time_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            room_name TEXT NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            duration_seconds INTEGER,
            cost_minutes INTEGER,
            status TEXT DEFAULT 'active'
        )
    """)
    
    # Pricing tiers table
    conn.execute("""
        CREATE TABLE pricing_tiers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            hours INTEGER NOT NULL,
            price_cents INTEGER NOT NULL,
            bonus_minutes INTEGER DEFAULT 0,
            description TEXT,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Payment history table
    conn.execute("""
        CREATE TABLE payment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stripe_payment_intent_id TEXT UNIQUE NOT NULL,
            amount_cents INTEGER NOT NULL,
            currency TEXT DEFAULT 'usd',
            status TEXT NOT NULL,
            time_card_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert test pricing tiers
    test_tiers = [
        ("test_1h", "Test 1 Hour", 1, 999, 0, "Test package"),
        ("test_5h", "Test 5 Hours", 5, 4999, 30, "Test package with bonus"),
    ]
    
    for tier in test_tiers:
        conn.execute("""
            INSERT INTO pricing_tiers (id, name, hours, price_cents, bonus_minutes, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, tier)
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    os.unlink(db_path)


# Application fixtures
@pytest.fixture
def auth_app(test_auth_db):
    """FastAPI auth service app for testing"""
    # Mock environment variables
    with patch.dict(os.environ, {
        'DATABASE_PATH': test_auth_db,
        'LIVEKIT_API_KEY': 'test_key',
        'LIVEKIT_API_SECRET': 'test_secret',
        'LIVEKIT_URL': 'wss://test.livekit.cloud'
    }):
        from auth_service.auth_server import app
        yield app


@pytest.fixture
def time_app(test_time_db):
    """FastAPI time service app for testing"""
    with patch.dict(os.environ, {
        'DATABASE_PATH': test_time_db,
        'STRIPE_SECRET_KEY': 'sk_test_123',
        'STRIPE_WEBHOOK_SECRET': 'whsec_test_123'
    }):
        from time_service.time_server import app
        yield app


@pytest.fixture
def admin_app(test_auth_db, test_time_db):
    """FastAPI admin service app for testing"""
    with patch.dict(os.environ, {
        'AUTH_DB_PATH': test_auth_db,
        'TIME_DB_PATH': test_time_db,
        'ADMIN_USERS': 'admin@test.com'
    }):
        from admin_dashboard.admin_server import app
        yield app


# HTTP client fixtures
@pytest.fixture
def auth_client(auth_app):
    """Test client for auth service"""
    return TestClient(auth_app)


@pytest.fixture
def time_client(time_app):
    """Test client for time service"""
    return TestClient(time_app)


@pytest.fixture
def admin_client(admin_app):
    """Test client for admin service"""
    return TestClient(admin_app)


@pytest.fixture
async def async_auth_client(auth_app):
    """Async test client for auth service"""
    async with AsyncClient(app=auth_app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def async_time_client(time_app):
    """Async test client for time service"""
    async with AsyncClient(app=time_app, base_url="http://test") as client:
        yield client


# Test data fixtures
@pytest.fixture
def test_user_data():
    """Test user registration data"""
    return {
        "email": "test@mindbot.ai",
        "password": "TestPassword123!",
        "full_name": "Test User",
        "confirm_password": "TestPassword123!",
        "terms_accepted": True
    }


@pytest.fixture
def test_admin_data():
    """Test admin user data"""
    return {
        "email": "admin@test.com",
        "password": "AdminPassword123!",
        "full_name": "Test Admin"
    }


@pytest.fixture
def test_time_card_data():
    """Test time card data"""
    return {
        "package_id": "test_1h",
        "payment_method_id": "pm_card_visa",
        "save_payment_method": False
    }


@pytest.fixture
def test_session_data():
    """Test voice session data"""
    return {
        "session_id": "test_session_123",
        "room_name": "test_room",
        "duration_seconds": 300
    }


# Authentication fixtures
@pytest.fixture
def jwt_token(auth_client, test_user_data):
    """Create test user and return JWT token"""
    # Register user
    response = auth_client.post("/auth/register", json=test_user_data)
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def admin_jwt_token(auth_client, test_admin_data):
    """Create admin user and return JWT token"""
    # Register admin user
    response = auth_client.post("/auth/register", json=test_admin_data)
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(jwt_token):
    """Authorization headers with JWT token"""
    return {"Authorization": f"Bearer {jwt_token}"}


@pytest.fixture
def admin_headers(admin_jwt_token):
    """Admin authorization headers"""
    return {"Authorization": f"Bearer {admin_jwt_token}"}


# Mock fixtures
@pytest.fixture
def mock_stripe():
    """Mock Stripe objects"""
    with patch('stripe.PaymentIntent') as mock_pi, \
         patch('stripe.Customer') as mock_customer, \
         patch('stripe.Webhook') as mock_webhook:
        
        # Mock PaymentIntent
        mock_pi.create.return_value.id = "pi_test_123456"
        mock_pi.create.return_value.client_secret = "pi_test_123456_secret"
        mock_pi.create.return_value.amount = 999
        mock_pi.create.return_value.status = "requires_payment_method"
        
        # Mock Customer
        mock_customer.create.return_value.id = "cus_test_123456"
        mock_customer.list.return_value.data = []
        
        # Mock Webhook
        mock_webhook.construct_event.return_value = {
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_test_123456',
                    'amount': 999,
                    'metadata': {'user_id': '1'}
                }
            }
        }
        
        yield {
            'PaymentIntent': mock_pi,
            'Customer': mock_customer,
            'Webhook': mock_webhook
        }


@pytest.fixture
def mock_livekit():
    """Mock LiveKit objects"""
    with patch('livekit.api.AccessToken') as mock_token:
        mock_instance = Mock()
        mock_instance.with_identity.return_value = mock_instance
        mock_instance.with_name.return_value = mock_instance
        mock_instance.with_grants.return_value = mock_instance
        mock_instance.with_ttl.return_value = mock_instance
        mock_instance.to_jwt.return_value = "mock_livekit_token"
        
        mock_token.return_value = mock_instance
        yield mock_token


@pytest.fixture
def mock_openai():
    """Mock OpenAI API calls"""
    with patch('openai.ChatCompletion') as mock_chat, \
         patch('openai.Audio') as mock_audio:
        
        # Mock chat completion
        mock_chat.create.return_value = {
            'choices': [{
                'message': {
                    'content': 'Test response from AI'
                }
            }]
        }
        
        # Mock audio transcription
        mock_audio.transcribe.return_value = {
            'text': 'Test transcription'
        }
        
        yield {
            'ChatCompletion': mock_chat,
            'Audio': mock_audio
        }


@pytest.fixture
def mock_deepgram():
    """Mock Deepgram API calls"""
    mock_response = {
        'results': {
            'channels': [{
                'alternatives': [{
                    'transcript': 'Test transcription from Deepgram'
                }]
            }]
        }
    }
    
    with patch('deepgram.Deepgram') as mock_dg:
        mock_instance = Mock()
        mock_instance.transcription.sync_prerecorded.return_value = mock_response
        mock_dg.return_value = mock_instance
        yield mock_dg


# Database helpers
@pytest.fixture
def db_with_test_user(test_auth_db, test_user_data):
    """Database with a test user already created"""
    import bcrypt
    
    conn = sqlite3.connect(test_auth_db)
    password_hash = bcrypt.hashpw(
        test_user_data["password"].encode('utf-8'), 
        bcrypt.gensalt()
    ).decode('utf-8')
    
    conn.execute("""
        INSERT INTO users (email, full_name, password_hash)
        VALUES (?, ?, ?)
    """, (test_user_data["email"], test_user_data["full_name"], password_hash))
    
    conn.commit()
    user_id = conn.lastrowid
    conn.close()
    
    yield {"user_id": user_id, "db_path": test_auth_db}


@pytest.fixture
def db_with_time_card(test_time_db):
    """Database with a test time card"""
    conn = sqlite3.connect(test_time_db)
    
    conn.execute("""
        INSERT INTO time_cards (user_id, activation_code, total_minutes, remaining_minutes, status)
        VALUES (1, 'TEST-CARD-123', 60, 60, 'active')
    """)
    
    conn.commit()
    card_id = conn.lastrowid
    conn.close()
    
    yield {"card_id": card_id, "activation_code": "TEST-CARD-123"}


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Temporary file fixtures
@pytest.fixture
def temp_log_file():
    """Temporary log file for testing"""
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.log', delete=False) as tmp_file:
        yield tmp_file.name
    os.unlink(tmp_file.name)


@pytest.fixture
def temp_config_file():
    """Temporary config file for testing"""
    config_content = """
[DEFAULT]
environment = test
debug = true
log_level = DEBUG

[auth]
jwt_secret = test-jwt-secret-for-testing-only
database_path = test_auth.db

[time]
stripe_secret_key = sk_test_123
database_path = test_time.db
"""
    
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.ini', delete=False) as tmp_file:
        tmp_file.write(config_content)
        tmp_file.flush()
        yield tmp_file.name
    os.unlink(tmp_file.name)


# Performance testing fixtures
@pytest.fixture
def performance_timer():
    """Timer for performance testing"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


# Load testing fixtures
@pytest.fixture
def load_test_users():
    """Generate multiple test users for load testing"""
    users = []
    for i in range(10):
        users.append({
            "email": f"loadtest{i}@mindbot.ai",
            "password": f"LoadTest{i}Password123!",
            "full_name": f"Load Test User {i}"
        })
    return users


# Configuration fixtures
@pytest.fixture
def test_config():
    """Test configuration dictionary"""
    return {
        "environment": "test",
        "debug": True,
        "log_level": "DEBUG",
        "jwt_secret": "test-jwt-secret-for-testing-only-min-32-chars",
        "database_url": "sqlite:///:memory:",
        "stripe_secret_key": "sk_test_123",
        "livekit_url": "wss://test.livekit.cloud",
        "openai_api_key": "sk-test123",
        "deepgram_api_key": "test123"
    }


# Cleanup fixture
@pytest.fixture(autouse=True)
def cleanup_environment():
    """Cleanup environment after each test"""
    yield
    
    # Reset any global state
    # Clear caches
    # Reset singletons
    pass


# Pytest hooks
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers"""
    for item in items:
        # Mark integration tests
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # Mark slow tests
        if "load" in item.nodeid or "performance" in item.nodeid:
            item.add_marker(pytest.mark.slow)
        
        # Mark external service tests
        if any(keyword in item.nodeid for keyword in ["stripe", "livekit", "openai", "deepgram"]):
            item.add_marker(pytest.mark.external)


# Example usage in tests:
"""
def test_user_registration(auth_client, test_user_data):
    response = auth_client.post("/auth/register", json=test_user_data)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_async_endpoint(async_auth_client, test_user_data):
    response = await async_auth_client.post("/auth/register", json=test_user_data)
    assert response.status_code == 200

@pytest.mark.integration
def test_full_payment_flow(time_client, auth_headers, mock_stripe):
    # Integration test with mocked Stripe
    pass

@pytest.mark.slow
def test_load_performance(load_test_users, performance_timer):
    # Load testing
    pass
"""