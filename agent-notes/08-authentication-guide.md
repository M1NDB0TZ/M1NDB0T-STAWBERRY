# MindBot Authentication System Guide

This guide covers the comprehensive authentication system for MindBot, including user management, JWT tokens, and LiveKit integration.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client App    │◄──►│   Auth Service   │◄──►│   Database      │
│                 │    │   (FastAPI)      │    │   (SQLite)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        
         ▼                        ▼                        
┌─────────────────┐    ┌──────────────────┐    
│   LiveKit       │◄──►│   Enhanced       │    
│   Server        │    │   MindBot Agent  │    
└─────────────────┘    └──────────────────┘    
```

## 🚀 Quick Setup

### 1. Start Authentication Service

```bash
cd backend/auth-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp env.example .env
# Edit .env with your LiveKit credentials

# Start service
python auth_server.py
```

The auth service will run on `http://localhost:8000`

### 2. Start Enhanced Agent

```bash
cd backend/basic-mindbot
# Use existing virtual environment
pip install -r requirements.txt

# Start enhanced agent with user context
python enhanced-mindbot.py start
```

### 3. Test Integration

```bash
cd backend/test-auth
pip install -r requirements.txt

# Run comprehensive tests
python test_auth_integration.py

# Or quick test
python test_auth_integration.py simple
```

## 🔐 Authentication Flow

### Registration Flow
```mermaid
sequenceDiagram
    Client->>Auth Service: POST /auth/register
    Auth Service->>Database: Create user record
    Auth Service->>Auth Service: Generate JWT token
    Auth Service->>LiveKit: Generate default room token
    Auth Service->>Client: Return JWT + LiveKit tokens
```

### Session Flow
```mermaid
sequenceDiagram
    Client->>Auth Service: POST /auth/token (with JWT)
    Auth Service->>Auth Service: Validate JWT
    Auth Service->>LiveKit: Generate room token
    Auth Service->>Database: Create session record
    Auth Service->>Client: Return LiveKit token
    Client->>LiveKit: Connect with token
    LiveKit->>Agent: User joined with identity
    Agent->>Agent: Load user context
```

## 📋 API Reference

### Authentication Endpoints

#### Register User
Creates a new user account and returns authentication tokens.

```http
POST /auth/register
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "secure_password",
    "full_name": "John Doe"
}
```

**Response:**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "livekit_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "livekit_url": "wss://your-project.livekit.cloud"
}
```

#### Login User
Authenticates existing user and returns tokens.

```http
POST /auth/login
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "secure_password"
}
```

#### Get Room Token
Generates LiveKit token for specific room access.

```http
POST /auth/token
Authorization: Bearer your_jwt_token
Content-Type: application/json

{
    "room_name": "voice_session_123",
    "participant_name": "John Doe"
}
```

**Response:**
```json
{
    "livekit_token": "eyJhbGciOiJIUzI1NiIs...",
    "livekit_url": "wss://your-project.livekit.cloud",
    "room_name": "voice_session_123",
    "session_id": 42
}
```

#### Get User Info
Returns current user information.

```http
GET /auth/me
Authorization: Bearer your_jwt_token
```

### Utility Endpoints

#### Health Check
```http
GET /health
```

#### Service Information  
```http
GET /
```

## 🗄️ Database Schema

### Users Table
Stores user account information with secure password hashing.

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

### User Sessions Table
Tracks user voice sessions for analytics and billing.

```sql
CREATE TABLE user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    room_name TEXT NOT NULL,
    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_end TIMESTAMP,
    duration_seconds INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

## 🤖 Enhanced Agent Features

The enhanced MindBot agent includes user context awareness:

### User Context Loading
- Extracts user ID from LiveKit participant identity
- Loads user preferences and history
- Provides personalized responses

### Enhanced Function Tools
- **User Preferences**: Remember and apply user preferences
- **Session Tracking**: Track conversation duration and topics
- **Personalized Greetings**: Welcome users based on their history
- **Context-Aware Responses**: Adapt responses to user context

### Example Usage in Agent
```python
@function_tool
async def remember_user_preference(
    self, context: RunContext, preference_type: str, preference_value: str
):
    """Remember user preference for future conversations"""
    user_id = self.user_context.get("user_id", "anonymous")
    
    if user_id == "anonymous":
        return "I can remember preferences for registered users. Consider creating an account!"
    
    # Save preference to database
    await self.save_user_preference(user_id, preference_type, preference_value)
    return f"Got it! I'll remember that you prefer {preference_value} for {preference_type}."
```

## 🔧 Client Integration

### JavaScript/TypeScript Example
```javascript
// Register or login user
const authResponse = await fetch('http://localhost:8000/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        email: 'user@example.com',
        password: 'password'
    })
});

const { access_token, livekit_token, livekit_url } = await authResponse.json();

// Connect to LiveKit with token
import { Room } from 'livekit-client';

const room = new Room();
await room.connect(livekit_url, livekit_token);

// Get room-specific token when needed
const roomTokenResponse = await fetch('http://localhost:8000/auth/token', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${access_token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        room_name: 'custom_room_name',
        participant_name: 'User Name'
    })
});
```

### Python Client Example
```python
import aiohttp
from livekit import Room

async def connect_authenticated_user():
    # Login user
    async with aiohttp.ClientSession() as session:
        async with session.post('http://localhost:8000/auth/login', json={
            'email': 'user@example.com',
            'password': 'password'
        }) as response:
            auth_data = await response.json()
        
        # Get room token
        headers = {'Authorization': f'Bearer {auth_data["access_token"]}'}
        async with session.post('http://localhost:8000/auth/token', 
            headers=headers,
            json={'room_name': 'my_room'}
        ) as response:
            room_data = await response.json()
    
    # Connect to LiveKit room
    room = Room()
    await room.connect(room_data['livekit_url'], room_data['livekit_token'])
```

## 🛡️ Security Features

### Password Security
- **bcrypt hashing**: Strong password hashing with salt
- **Minimum requirements**: Configurable password policies
- **Hash validation**: Secure password verification

### JWT Security
- **HS256 algorithm**: Secure token signing
- **Expiration**: Configurable token lifetime (default: 24 hours)
- **Claims validation**: User ID, email, and expiration validation

### LiveKit Token Security
- **Scoped access**: Room-specific permissions
- **Time-limited**: 6-hour default expiration
- **Identity mapping**: User ID to participant identity
- **Permission grants**: Granular publish/subscribe controls

### API Security
- **Bearer token authentication**: JWT-based API access
- **CORS configuration**: Configurable cross-origin policies
- **Input validation**: Pydantic model validation
- **SQL injection protection**: Parameterized queries

## 🚀 Production Deployment

### Environment Configuration
```env
# Production environment variables
LIVEKIT_API_SECRET="your_production_secret"
LIVEKIT_API_KEY="your_production_key"
LIVEKIT_URL="wss://your-production.livekit.cloud"
JWT_SECRET="your-super-secure-production-jwt-secret"
DATABASE_PATH="/app/data/mindbot_users.db"
```

### Docker Deployment
```dockerfile
# Auth service Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "auth_server.py"]
```

### Database Migration for Production
For production, consider migrating to PostgreSQL:

```python
# production_db.py
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://user:password@localhost/mindbot"
engine = create_async_engine(DATABASE_URL)
```

## 📊 Monitoring & Analytics

### Session Analytics
Track user engagement and usage patterns:

```python
# In your analytics code
def analyze_user_sessions():
    """Analyze user session patterns"""
    # Average session duration
    # Most active users
    # Popular conversation topics
    # Usage patterns by time of day
```

### Security Monitoring
Monitor authentication events:

```python
# Security event logging
logger.info(f"User login: {user.email} from {request.client.host}")
logger.warning(f"Failed login attempt: {email} from {request.client.host}")
logger.error(f"Invalid token access attempt from {request.client.host}")
```

## 🔍 Testing & Validation

### Unit Tests
```python
import pytest
from auth_server import AuthManager, DatabaseManager

@pytest.fixture
def auth_manager():
    db = DatabaseManager(":memory:")  # In-memory SQLite for testing
    return AuthManager(db)

def test_password_hashing(auth_manager):
    password = "test_password"
    hashed = auth_manager.hash_password(password)
    assert auth_manager.verify_password(password, hashed)

def test_jwt_token_generation(auth_manager):
    user = User(id=1, email="test@example.com", full_name="Test User", password_hash="hash")
    token = auth_manager.create_jwt_token(user)
    payload = auth_manager.verify_jwt_token(token)
    assert payload["user_id"] == 1
```

### Integration Tests
Use the provided test script:
```bash
cd backend/test-auth
python test_auth_integration.py
```

## 🚨 Troubleshooting

### Common Issues

#### Auth Service Won't Start
```bash
# Check environment variables
python -c "import os; print('LIVEKIT_API_KEY:', bool(os.getenv('LIVEKIT_API_KEY')))"

# Check database permissions
ls -la mindbot_users.db

# Check port availability
lsof -i :8000
```

#### JWT Token Issues
```python
# Debug JWT tokens
import jwt
try:
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    print("Token valid:", payload)
except jwt.ExpiredSignatureError:
    print("Token expired")
except jwt.InvalidTokenError:
    print("Invalid token")
```

#### LiveKit Connection Issues
```python
# Validate LiveKit token
from livekit import api
try:
    token = api.AccessToken.from_jwt(livekit_token)
    print("LiveKit token valid")
    print("Identity:", token.identity)
    print("Room:", token.grants.room)
except Exception as e:
    print("LiveKit token error:", e)
```

### Debug Mode
Start services with debug logging:
```bash
# Auth service debug
python auth_server.py --log-level DEBUG

# Agent debug
python enhanced-mindbot.py start --log-level DEBUG
```

## 🔄 Future Enhancements

### Planned Features
1. **OAuth Integration**: Google, GitHub, Microsoft sign-in
2. **Multi-tenant Support**: Organization and team management
3. **Role-based Access Control**: Admin, user, guest roles
4. **Session Analytics Dashboard**: Web interface for usage metrics
5. **API Rate Limiting**: Prevent abuse and manage costs
6. **Audit Logging**: Comprehensive security event logging
7. **Password Reset**: Email-based password recovery
8. **User Preferences API**: Advanced preference management
9. **Conversation History**: Store and retrieve past conversations
10. **Billing Integration**: Usage-based billing system

### Integration Opportunities
- **CRM Systems**: Salesforce, HubSpot integration
- **Identity Providers**: LDAP, Active Directory
- **Analytics Platforms**: Google Analytics, Mixpanel
- **Communication Tools**: Slack, Discord, Teams
- **Database Options**: PostgreSQL, MongoDB, Redis

This authentication system provides a solid foundation for secure, scalable user management in your MindBot voice AI platform.