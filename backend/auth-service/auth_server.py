#!/usr/bin/env python3
"""
MindBot Authentication Service
Handles user authentication and LiveKit token generation
"""

import os
import jwt
import bcrypt
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from livekit import api
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configuration
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET") 
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-this")
JWT_ALGORITHM = "HS256"
DATABASE_PATH = "mindbot_users.db"

# Pydantic models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenRequest(BaseModel):
    room_name: str
    participant_name: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    livekit_token: str
    livekit_url: str

@dataclass
class User:
    id: int
    email: str
    full_name: str
    password_hash: str
    created_at: datetime
    last_login: Optional[datetime] = None

class DatabaseManager:
    """Handles all database operations"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    room_name TEXT NOT NULL,
                    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_end TIMESTAMP,
                    duration_seconds INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id);
            """)
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    def create_user(self, email: str, full_name: str, password: str) -> Optional[User]:
        """Create a new user"""
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "INSERT INTO users (email, full_name, password_hash) VALUES (?, ?, ?)",
                    (email, full_name, password_hash)
                )
                user_id = cursor.lastrowid
                conn.commit()
                
                return self.get_user_by_id(user_id)
        except sqlite3.IntegrityError:
            return None  # User already exists
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            )
            row = cursor.fetchone()
            
            if row:
                return User(
                    id=row['id'],
                    email=row['email'],
                    full_name=row['full_name'],
                    password_hash=row['password_hash'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None
                )
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return User(
                    id=row['id'],
                    email=row['email'],
                    full_name=row['full_name'],
                    password_hash=row['password_hash'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None
                )
            return None
    
    def update_last_login(self, user_id: int):
        """Update user's last login timestamp"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (user_id,)
            )
            conn.commit()
    
    def create_session(self, user_id: int, room_name: str) -> int:
        """Create a new session record"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO user_sessions (user_id, room_name) VALUES (?, ?)",
                (user_id, room_name)
            )
            session_id = cursor.lastrowid
            conn.commit()
            return session_id

class AuthManager:
    """Handles authentication logic"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def create_jwt_token(self, user: User) -> str:
        """Create a JWT token for the user"""
        payload = {
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def generate_livekit_token(self, user: User, room_name: str, participant_name: Optional[str] = None) -> str:
        """Generate a LiveKit access token"""
        if not participant_name:
            participant_name = user.full_name
        
        # Create LiveKit token
        token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
            .with_identity(f"user_{user.id}") \
            .with_name(participant_name) \
            .with_grants(api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
                can_update_own_metadata=True
            )) \
            .with_ttl(timedelta(hours=6))
        
        return token.to_jwt()

# Initialize components
db_manager = DatabaseManager(DATABASE_PATH)
auth_manager = AuthManager(db_manager)

# FastAPI app
app = FastAPI(
    title="MindBot Authentication Service",
    description="Authentication service for MindBot voice AI backend",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user"""
    payload = auth_manager.verify_jwt_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user = db_manager.get_user_by_id(payload["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

# API Endpoints
@app.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """Register a new user"""
    user = db_manager.create_user(
        email=user_data.email,
        full_name=user_data.full_name,
        password=user_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Generate tokens
    jwt_token = auth_manager.create_jwt_token(user)
    livekit_token = auth_manager.generate_livekit_token(user, f"user_{user.id}_default")
    
    logger.info(f"New user registered: {user.email}")
    
    return TokenResponse(
        access_token=jwt_token,
        livekit_token=livekit_token,
        livekit_url=LIVEKIT_URL
    )

@app.post("/auth/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    """Login user"""
    user = db_manager.get_user_by_email(login_data.email)
    
    if not user or not auth_manager.verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Update last login
    db_manager.update_last_login(user.id)
    
    # Generate tokens
    jwt_token = auth_manager.create_jwt_token(user)
    livekit_token = auth_manager.generate_livekit_token(user, f"user_{user.id}_default")
    
    logger.info(f"User logged in: {user.email}")
    
    return TokenResponse(
        access_token=jwt_token,
        livekit_token=livekit_token,
        livekit_url=LIVEKIT_URL
    )

@app.post("/auth/token", response_model=dict)
async def get_room_token(
    token_request: TokenRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate LiveKit token for specific room"""
    livekit_token = auth_manager.generate_livekit_token(
        current_user, 
        token_request.room_name,
        token_request.participant_name
    )
    
    # Create session record
    session_id = db_manager.create_session(current_user.id, token_request.room_name)
    
    logger.info(f"Generated room token for user {current_user.email}, room: {token_request.room_name}")
    
    return {
        "livekit_token": livekit_token,
        "livekit_url": LIVEKIT_URL,
        "room_name": token_request.room_name,
        "session_id": session_id
    }

@app.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "created_at": current_user.created_at.isoformat(),
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "mindbot-auth",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MindBot Authentication Service",
        "version": "1.0.0",
        "endpoints": {
            "register": "/auth/register",
            "login": "/auth/login", 
            "token": "/auth/token",
            "me": "/auth/me",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    # Validate environment variables
    required_env_vars = ["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "LIVEKIT_URL"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        exit(1)
    
    logger.info("Starting MindBot Authentication Service...")
    logger.info(f"LiveKit URL: {LIVEKIT_URL}")
    
    uvicorn.run(
        "auth_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )