# MindBot Authentication Service

A comprehensive authentication service for the MindBot voice AI backend that handles user management, JWT authentication, and LiveKit token generation.

## Features

- **User Registration & Login**: Secure user authentication with bcrypt password hashing
- **JWT Token Management**: Generate and validate JWT tokens for API access
- **LiveKit Integration**: Generate LiveKit access tokens for voice sessions
- **Session Tracking**: Track user sessions and room participation
- **RESTful API**: Clean API endpoints for authentication operations
- **SQLite Database**: Lightweight user and session storage

## Quick Start

### 1. Setup Environment

```bash
cd backend/auth-service
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp env.example .env
# Edit .env with your credentials
```

Required environment variables:
```env
LIVEKIT_API_SECRET="your_livekit_api_secret"
LIVEKIT_API_KEY="your_livekit_api_key"
LIVEKIT_URL="wss://your-project.livekit.cloud"
JWT_SECRET="your-super-secret-jwt-key-change-this-in-production"
```

### 3. Start the Service

```bash
python auth_server.py
```

The service will start on `http://localhost:8000`

## API Endpoints

### Authentication

#### Register User
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
    "access_token": "jwt_token_here",
    "token_type": "bearer",
    "livekit_token": "livekit_token_here",
    "livekit_url": "wss://your-project.livekit.cloud"
}
```

#### Login User
```http
POST /auth/login
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "secure_password"
}
```

**Response:** Same as register

#### Get Room Token
```http
POST /auth/token
Authorization: Bearer your_jwt_token
Content-Type: application/json

{
    "room_name": "voice_session_room",
    "participant_name": "John Doe"
}
```

**Response:**
```json
{
    "livekit_token": "room_specific_token",
    "livekit_url": "wss://your-project.livekit.cloud",
    "room_name": "voice_session_room",
    "session_id": 123
}
```

#### Get User Info
```http
GET /auth/me
Authorization: Bearer your_jwt_token
```

### Utility Endpoints

#### Health Check
```http
GET /health
```

#### Service Info
```http
GET /
```

## Database Schema

### Users Table
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

## Integration with MindBot Agent

### 1. Update Agent for User Context

Add user information to your agent sessions:

```python
# In your agent code
@function_tool
async def get_user_context(context: RunContext, user_id: str):
    """Get user context for personalized responses"""
    # Fetch user data from auth service
    # Return user preferences, history, etc.
    pass
```

### 2. Room Management

Create user-specific rooms:

```python
# Generate room names based on user and session
room_name = f"user_{user_id}_session_{session_id}"
```

### 3. Session Tracking

Update session records when users join/leave:

```python
# When user joins
session_id = db_manager.create_session(user_id, room_name)

# When user leaves (add to your agent cleanup)
# Update session end time and duration
```

## Testing the Service

### Using curl

```bash
# Register a new user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword",
    "full_name": "Test User"
  }'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword"
  }'

# Get room token (replace JWT_TOKEN)
curl -X POST http://localhost:8000/auth/token \
  -H "Authorization: Bearer JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "room_name": "test_room",
    "participant_name": "Test User"
  }'
```

### Using Python requests

```python
import requests

# Register
response = requests.post('http://localhost:8000/auth/register', json={
    'email': 'test@example.com',
    'password': 'testpassword',
    'full_name': 'Test User'
})
auth_data = response.json()

# Get room token
headers = {'Authorization': f'Bearer {auth_data["access_token"]}'}
response = requests.post('http://localhost:8000/auth/token', 
    headers=headers,
    json={'room_name': 'my_room'}
)
room_data = response.json()
```

## Security Features

- **Password Hashing**: bcrypt with salt for secure password storage
- **JWT Tokens**: Stateless authentication with expiration
- **LiveKit Integration**: Secure room access with proper grants
- **Input Validation**: Pydantic models for request validation
- **CORS Configuration**: Configurable cross-origin requests

## Production Considerations

1. **Change JWT Secret**: Use a strong, random JWT secret in production
2. **Database**: Consider PostgreSQL for production instead of SQLite
3. **HTTPS**: Always use HTTPS in production
4. **Rate Limiting**: Add rate limiting for auth endpoints
5. **Logging**: Configure proper logging levels
6. **Monitoring**: Add health checks and metrics

## Integration Flow

1. **User Registration/Login** → Get JWT token + default LiveKit token
2. **Start Voice Session** → Request room-specific LiveKit token
3. **Join LiveKit Room** → Use LiveKit token to connect
4. **Agent Processing** → Agent can access user context via session info
5. **Session Tracking** → Record session data for analytics

This authentication service provides a solid foundation for user management in your MindBot voice AI system while maintaining security and scalability.