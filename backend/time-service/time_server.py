#!/usr/bin/env python3
"""
MindBotz Time Tracking Service
Handles time card purchases, balance management, and usage tracking with Stripe integration
"""

import os
import logging
import stripe
import sqlite3
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
import uvicorn
import jwt
import asyncio
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-this")
JWT_ALGORITHM = "HS256"
DATABASE_PATH = "mindbot_time_tracking.db"
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8000")

# Initialize Stripe
stripe.api_key = STRIPE_SECRET_KEY

# Pydantic models
class TimeCardPurchase(BaseModel):
    package_id: str
    payment_method_id: str
    save_payment_method: bool = False

class TimeCardActivation(BaseModel):
    activation_code: str

class TimeUsageStart(BaseModel):
    session_id: str
    room_name: str

class TimeUsageEnd(BaseModel):
    session_id: str
    duration_seconds: int

class PricingTier(BaseModel):
    id: str
    name: str
    hours: int
    price_cents: int
    bonus_minutes: int = 0
    description: str

class NotificationPreferences(BaseModel):
    low_balance_threshold_minutes: int = 30
    email_notifications: bool = True
    in_app_notifications: bool = True

@dataclass
class User:
    id: int
    email: str
    full_name: str
    
@dataclass
class TimeCard:
    id: int
    user_id: int
    activation_code: str
    total_minutes: int
    remaining_minutes: int
    activated_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    status: str  # 'pending', 'active', 'expired', 'used'

@dataclass
class TimeSession:
    id: int
    user_id: int
    session_id: str
    room_name: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    cost_minutes: Optional[int]
    status: str  # 'active', 'completed', 'error'

class DatabaseManager:
    """Handles all database operations for time tracking"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            # Time cards table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS time_cards (
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
                CREATE TABLE IF NOT EXISTS time_sessions (
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
                CREATE TABLE IF NOT EXISTS pricing_tiers (
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
                CREATE TABLE IF NOT EXISTS payment_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    stripe_payment_intent_id TEXT UNIQUE NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    currency TEXT DEFAULT 'usd',
                    status TEXT NOT NULL,
                    time_card_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (time_card_id) REFERENCES time_cards (id)
                )
            """)
            
            # User balance view (calculated from time cards)
            conn.execute("""
                CREATE VIEW IF NOT EXISTS user_balances AS
                SELECT 
                    user_id,
                    SUM(remaining_minutes) as total_minutes,
                    COUNT(*) as active_cards,
                    MIN(expires_at) as next_expiration
                FROM time_cards 
                WHERE status = 'active' AND (expires_at IS NULL OR expires_at > datetime('now'))
                GROUP BY user_id
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_time_cards_user_id ON time_cards(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_time_cards_code ON time_cards(activation_code)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON time_sessions(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON time_sessions(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_history_user_id ON payment_history(user_id)")
            
            # Insert default pricing tiers
            self.insert_default_pricing_tiers(conn)
            
            conn.commit()
            logger.info("Time tracking database initialized successfully")
    
    def insert_default_pricing_tiers(self, conn):
        """Insert default pricing tiers"""
        default_tiers = [
            ("starter_1h", "Starter Pack", 1, 999, 0, "Perfect for trying out MindBotz - 1 hour of AI conversation time"),
            ("basic_5h", "Basic Pack", 5, 4499, 30, "Great for regular users - 5 hours + 30 bonus minutes"),
            ("premium_10h", "Premium Pack", 10, 7999, 120, "Best value - 10 hours + 2 bonus hours"),
            ("pro_25h", "Pro Pack", 25, 17999, 300, "For power users - 25 hours + 5 bonus hours"),
            ("enterprise_50h", "Enterprise Pack", 50, 29999, 600, "Maximum value - 50 hours + 10 bonus hours")
        ]
        
        for tier_id, name, hours, price_cents, bonus_minutes, description in default_tiers:
            conn.execute("""
                INSERT OR IGNORE INTO pricing_tiers 
                (id, name, hours, price_cents, bonus_minutes, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tier_id, name, hours, price_cents, bonus_minutes, description))
    
    def generate_activation_code(self) -> str:
        """Generate unique activation code"""
        while True:
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12))
            # Format as XXXX-XXXX-XXXX
            formatted_code = f"{code[:4]}-{code[4:8]}-{code[8:]}"
            
            # Check if code already exists
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT id FROM time_cards WHERE activation_code = ?", (formatted_code,))
                if not cursor.fetchone():
                    return formatted_code
    
    def create_time_card(self, user_id: int, total_minutes: int, stripe_payment_intent_id: str = None) -> TimeCard:
        """Create a new time card"""
        activation_code = self.generate_activation_code()
        expires_at = datetime.utcnow() + timedelta(days=365)  # 1 year expiration
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO time_cards 
                (user_id, activation_code, total_minutes, remaining_minutes, expires_at, stripe_payment_intent_id, status)
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """, (user_id, activation_code, total_minutes, total_minutes, expires_at, stripe_payment_intent_id))
            
            time_card_id = cursor.lastrowid
            conn.commit()
            
            return self.get_time_card_by_id(time_card_id)
    
    def activate_time_card(self, activation_code: str, user_id: int) -> Optional[TimeCard]:
        """Activate a time card with activation code"""
        with sqlite3.connect(self.db_path) as conn:
            # Check if card exists and is pending
            cursor = conn.execute("""
                SELECT id FROM time_cards 
                WHERE activation_code = ? AND status = 'pending'
            """, (activation_code,))
            
            card_data = cursor.fetchone()
            if not card_data:
                return None
            
            # Activate the card
            activated_at = datetime.utcnow()
            conn.execute("""
                UPDATE time_cards 
                SET user_id = ?, activated_at = ?, status = 'active'
                WHERE activation_code = ?
            """, (user_id, activated_at, activation_code))
            
            conn.commit()
            return self.get_time_card_by_code(activation_code)
    
    def get_time_card_by_id(self, card_id: int) -> Optional[TimeCard]:
        """Get time card by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM time_cards WHERE id = ?", (card_id,))
            row = cursor.fetchone()
            
            if row:
                return TimeCard(
                    id=row['id'],
                    user_id=row['user_id'],
                    activation_code=row['activation_code'],
                    total_minutes=row['total_minutes'],
                    remaining_minutes=row['remaining_minutes'],
                    activated_at=datetime.fromisoformat(row['activated_at']) if row['activated_at'] else None,
                    expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                    created_at=datetime.fromisoformat(row['created_at']),
                    status=row['status']
                )
            return None
    
    def get_time_card_by_code(self, activation_code: str) -> Optional[TimeCard]:
        """Get time card by activation code"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM time_cards WHERE activation_code = ?", (activation_code,))
            row = cursor.fetchone()
            
            if row:
                return TimeCard(
                    id=row['id'],
                    user_id=row['user_id'],
                    activation_code=row['activation_code'],
                    total_minutes=row['total_minutes'],
                    remaining_minutes=row['remaining_minutes'],
                    activated_at=datetime.fromisoformat(row['activated_at']) if row['activated_at'] else None,
                    expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                    created_at=datetime.fromisoformat(row['created_at']),
                    status=row['status']
                )
            return None
    
    def get_user_balance(self, user_id: int) -> Dict[str, Any]:
        """Get user's total time balance"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT 
                    COALESCE(SUM(remaining_minutes), 0) as total_minutes,
                    COUNT(*) as active_cards,
                    MIN(expires_at) as next_expiration
                FROM time_cards 
                WHERE user_id = ? AND status = 'active' 
                AND (expires_at IS NULL OR expires_at > datetime('now'))
            """, (user_id,))
            
            row = cursor.fetchone()
            return {
                "total_minutes": row['total_minutes'],
                "total_hours": round(row['total_minutes'] / 60, 1),
                "active_cards": row['active_cards'],
                "next_expiration": row['next_expiration']
            }
    
    def get_user_time_cards(self, user_id: int) -> List[TimeCard]:
        """Get all time cards for a user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM time_cards 
                WHERE user_id = ? 
                ORDER BY created_at DESC
            """, (user_id,))
            
            cards = []
            for row in cursor.fetchall():
                cards.append(TimeCard(
                    id=row['id'],
                    user_id=row['user_id'],
                    activation_code=row['activation_code'],
                    total_minutes=row['total_minutes'],
                    remaining_minutes=row['remaining_minutes'],
                    activated_at=datetime.fromisoformat(row['activated_at']) if row['activated_at'] else None,
                    expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
                    created_at=datetime.fromisoformat(row['created_at']),
                    status=row['status']
                ))
            
            return cards
    
    def deduct_time(self, user_id: int, minutes: int) -> bool:
        """Deduct time from user's balance (FIFO - first expiring first)"""
        with sqlite3.connect(self.db_path) as conn:
            # Get active cards ordered by expiration date
            cursor = conn.execute("""
                SELECT id, remaining_minutes FROM time_cards 
                WHERE user_id = ? AND status = 'active' AND remaining_minutes > 0
                AND (expires_at IS NULL OR expires_at > datetime('now'))
                ORDER BY expires_at ASC, created_at ASC
            """, (user_id,))
            
            cards = cursor.fetchall()
            remaining_to_deduct = minutes
            
            for card_id, card_minutes in cards:
                if remaining_to_deduct <= 0:
                    break
                
                if card_minutes >= remaining_to_deduct:
                    # This card can cover the remaining time
                    new_balance = card_minutes - remaining_to_deduct
                    status = 'used' if new_balance == 0 else 'active'
                    
                    conn.execute("""
                        UPDATE time_cards 
                        SET remaining_minutes = ?, status = ?
                        WHERE id = ?
                    """, (new_balance, status, card_id))
                    
                    remaining_to_deduct = 0
                else:
                    # Use all remaining time from this card
                    conn.execute("""
                        UPDATE time_cards 
                        SET remaining_minutes = 0, status = 'used'
                        WHERE id = ?
                    """, (card_id,))
                    
                    remaining_to_deduct -= card_minutes
            
            conn.commit()
            return remaining_to_deduct == 0
    
    def start_time_session(self, user_id: int, session_id: str, room_name: str) -> TimeSession:
        """Start a new time tracking session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO time_sessions (user_id, session_id, room_name, status)
                VALUES (?, ?, ?, 'active')
            """, (user_id, session_id, room_name))
            
            session_db_id = cursor.lastrowid
            conn.commit()
            
            return TimeSession(
                id=session_db_id,
                user_id=user_id,
                session_id=session_id,
                room_name=room_name,
                start_time=datetime.utcnow(),
                end_time=None,
                duration_seconds=None,
                cost_minutes=None,
                status='active'
            )
    
    def end_time_session(self, session_id: str, duration_seconds: int) -> Optional[TimeSession]:
        """End a time tracking session"""
        cost_minutes = max(1, round(duration_seconds / 60))  # Minimum 1 minute billing
        
        with sqlite3.connect(self.db_path) as conn:
            # Get session info
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM time_sessions 
                WHERE session_id = ? AND status = 'active'
            """, (session_id,))
            
            session_row = cursor.fetchone()
            if not session_row:
                return None
            
            # Update session
            end_time = datetime.utcnow()
            conn.execute("""
                UPDATE time_sessions 
                SET end_time = ?, duration_seconds = ?, cost_minutes = ?, status = 'completed'
                WHERE session_id = ?
            """, (end_time, duration_seconds, cost_minutes, session_id))
            
            # Deduct time from user's balance
            success = self.deduct_time(session_row['user_id'], cost_minutes)
            if not success:
                # Mark session as error if insufficient balance
                conn.execute("""
                    UPDATE time_sessions SET status = 'error' WHERE session_id = ?
                """, (session_id,))
            
            conn.commit()
            
            return TimeSession(
                id=session_row['id'],
                user_id=session_row['user_id'],
                session_id=session_row['session_id'],
                room_name=session_row['room_name'],
                start_time=datetime.fromisoformat(session_row['start_time']),
                end_time=end_time,
                duration_seconds=duration_seconds,
                cost_minutes=cost_minutes,
                status='completed' if success else 'error'
            )
    
    def get_pricing_tiers(self) -> List[PricingTier]:
        """Get all active pricing tiers"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM pricing_tiers 
                WHERE active = TRUE 
                ORDER BY price_cents ASC
            """)
            
            tiers = []
            for row in cursor.fetchall():
                tiers.append(PricingTier(
                    id=row['id'],
                    name=row['name'],
                    hours=row['hours'],
                    price_cents=row['price_cents'],
                    bonus_minutes=row['bonus_minutes'] or 0,
                    description=row['description'] or ""
                ))
            
            return tiers

class StripeManager:
    """Handles Stripe payment processing"""
    
    def __init__(self):
        if not STRIPE_SECRET_KEY:
            raise ValueError("STRIPE_SECRET_KEY environment variable is required")
    
    async def create_payment_intent(self, user: User, package: PricingTier, save_payment_method: bool = False) -> Dict:
        """Create a Stripe payment intent for time card purchase"""
        try:
            intent_params = {
                'amount': package.price_cents,
                'currency': 'usd',
                'metadata': {
                    'user_id': str(user.id),
                    'user_email': user.email,
                    'package_id': package.id,
                    'package_name': package.name,
                    'hours': str(package.hours),
                    'bonus_minutes': str(package.bonus_minutes)
                },
                'description': f"MindBotz {package.name} - {package.hours} hours of AI conversation time"
            }
            
            if save_payment_method:
                intent_params['setup_future_usage'] = 'on_session'
                intent_params['customer'] = await self.get_or_create_customer(user)
            
            payment_intent = stripe.PaymentIntent.create(**intent_params)
            
            logger.info(f"Created payment intent {payment_intent.id} for user {user.id}")
            return payment_intent
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {e}")
            raise HTTPException(status_code=400, detail=f"Payment processing error: {str(e)}")
    
    async def get_or_create_customer(self, user: User) -> str:
        """Get or create a Stripe customer for the user"""
        try:
            # Search for existing customer
            customers = stripe.Customer.list(email=user.email, limit=1)
            
            if customers.data:
                return customers.data[0].id
            
            # Create new customer
            customer = stripe.Customer.create(
                email=user.email,
                name=user.full_name,
                metadata={'user_id': str(user.id)}
            )
            
            logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error managing customer: {e}")
            raise HTTPException(status_code=400, detail=f"Customer management error: {str(e)}")

class NotificationManager:
    """Handles user notifications for low balance, etc."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def check_low_balance_notifications(self, user_id: int, threshold_minutes: int = 30):
        """Check if user balance is low and send notification"""
        balance = self.db.get_user_balance(user_id)
        
        if balance['total_minutes'] <= threshold_minutes and balance['total_minutes'] > 0:
            await self.send_low_balance_notification(user_id, balance['total_minutes'])
    
    async def send_low_balance_notification(self, user_id: int, remaining_minutes: int):
        """Send low balance notification to user"""
        logger.info(f"Low balance notification for user {user_id}: {remaining_minutes} minutes remaining")
        
        # In a real implementation, you would:
        # 1. Send email notification
        # 2. Send in-app notification
        # 3. Possibly send SMS if configured
        
        # For now, just log it
        # You could integrate with services like:
        # - SendGrid for email
        # - Twilio for SMS
        # - WebSocket for real-time in-app notifications

# Initialize components
db_manager = DatabaseManager(DATABASE_PATH)
stripe_manager = StripeManager()
notification_manager = NotificationManager(db_manager)

# FastAPI app
app = FastAPI(
    title="MindBotz Time Tracking Service",
    description="Time card purchases, balance management, and usage tracking with Stripe integration",
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

async def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user"""
    payload = await verify_jwt_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Create user object from JWT payload
    return User(
        id=payload["user_id"],
        email=payload["email"],
        full_name=payload["full_name"]
    )

# API Endpoints

@app.get("/time/pricing")
async def get_pricing_tiers():
    """Get available time card pricing tiers"""
    tiers = db_manager.get_pricing_tiers()
    return {"pricing_tiers": [
        {
            "id": tier.id,
            "name": tier.name,
            "hours": tier.hours,
            "price_cents": tier.price_cents,
            "price_display": f"${tier.price_cents / 100:.2f}",
            "bonus_minutes": tier.bonus_minutes,
            "total_minutes": (tier.hours * 60) + tier.bonus_minutes,
            "description": tier.description
        } for tier in tiers
    ]}

@app.post("/time/purchase")
async def purchase_time_card(
    purchase_data: TimeCardPurchase,
    current_user: User = Depends(get_current_user)
):
    """Purchase a time card package"""
    # Get pricing tier
    tiers = db_manager.get_pricing_tiers()
    package = next((t for t in tiers if t.id == purchase_data.package_id), None)
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    try:
        # Create payment intent
        payment_intent = await stripe_manager.create_payment_intent(
            current_user, 
            package, 
            purchase_data.save_payment_method
        )
        
        # Create pending time card
        total_minutes = (package.hours * 60) + package.bonus_minutes
        time_card = db_manager.create_time_card(
            current_user.id, 
            total_minutes, 
            payment_intent.id
        )
        
        logger.info(f"Created time card purchase for user {current_user.id}: {package.name}")
        
        return {
            "payment_intent_id": payment_intent.id,
            "client_secret": payment_intent.client_secret,
            "time_card_id": time_card.id,
            "activation_code": time_card.activation_code,
            "package": {
                "name": package.name,
                "hours": package.hours,
                "bonus_minutes": package.bonus_minutes,
                "total_minutes": total_minutes
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing time card purchase: {e}")
        raise HTTPException(status_code=500, detail="Purchase processing failed")

@app.post("/time/activate")
async def activate_time_card(
    activation_data: TimeCardActivation,
    current_user: User = Depends(get_current_user)
):
    """Activate a time card with activation code"""
    time_card = db_manager.activate_time_card(activation_data.activation_code, current_user.id)
    
    if not time_card:
        raise HTTPException(status_code=404, detail="Invalid activation code or card already used")
    
    logger.info(f"Activated time card {time_card.id} for user {current_user.id}")
    
    return {
        "message": "Time card activated successfully",
        "time_card": {
            "id": time_card.id,
            "total_minutes": time_card.total_minutes,
            "remaining_minutes": time_card.remaining_minutes,
            "expires_at": time_card.expires_at.isoformat() if time_card.expires_at else None
        }
    }

@app.get("/time/balance")
async def get_time_balance(current_user: User = Depends(get_current_user)):
    """Get user's current time balance"""
    balance = db_manager.get_user_balance(current_user.id)
    time_cards = db_manager.get_user_time_cards(current_user.id)
    
    return {
        "balance": balance,
        "time_cards": [{
            "id": card.id,
            "activation_code": card.activation_code,
            "total_minutes": card.total_minutes,
            "remaining_minutes": card.remaining_minutes,
            "status": card.status,
            "activated_at": card.activated_at.isoformat() if card.activated_at else None,
            "expires_at": card.expires_at.isoformat() if card.expires_at else None,
            "created_at": card.created_at.isoformat()
        } for card in time_cards]
    }

@app.post("/time/session/start")
async def start_time_session(
    session_data: TimeUsageStart,
    current_user: User = Depends(get_current_user)
):
    """Start tracking time for a voice session"""
    # Check if user has sufficient balance
    balance = db_manager.get_user_balance(current_user.id)
    if balance['total_minutes'] <= 0:
        raise HTTPException(status_code=402, detail="Insufficient time balance")
    
    session = db_manager.start_time_session(
        current_user.id, 
        session_data.session_id, 
        session_data.room_name
    )
    
    logger.info(f"Started time session {session_data.session_id} for user {current_user.id}")
    
    return {
        "session_id": session.session_id,
        "start_time": session.start_time.isoformat(),
        "remaining_balance_minutes": balance['total_minutes']
    }

@app.post("/time/session/end")
async def end_time_session(
    session_data: TimeUsageEnd,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """End time tracking for a voice session"""
    session = db_manager.end_time_session(session_data.session_id, session_data.duration_seconds)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check for low balance notification
    background_tasks.add_task(
        notification_manager.check_low_balance_notifications,
        current_user.id
    )
    
    logger.info(f"Ended time session {session_data.session_id}: {session.cost_minutes} minutes charged")
    
    return {
        "session_id": session.session_id,
        "duration_seconds": session.duration_seconds,
        "cost_minutes": session.cost_minutes,
        "status": session.status,
        "remaining_balance": db_manager.get_user_balance(current_user.id)
    }

@app.get("/time/sessions")
async def get_time_sessions(
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """Get user's time session history"""
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM time_sessions 
            WHERE user_id = ? 
            ORDER BY start_time DESC 
            LIMIT ?
        """, (current_user.id, limit))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "id": row['id'],
                "session_id": row['session_id'],
                "room_name": row['room_name'],
                "start_time": row['start_time'],
                "end_time": row['end_time'],
                "duration_seconds": row['duration_seconds'],
                "cost_minutes": row['cost_minutes'],
                "status": row['status']
            })
    
    return {"sessions": sessions}

@app.post("/webhooks/stripe")
async def stripe_webhook(request):
    """Handle Stripe webhooks for payment confirmations"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle payment success
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        
        # Activate time card
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.execute("""
                UPDATE time_cards 
                SET status = 'active', activated_at = datetime('now')
                WHERE stripe_payment_intent_id = ?
            """, (payment_intent.id,))
            
            # Record payment history
            conn.execute("""
                INSERT INTO payment_history 
                (user_id, stripe_payment_intent_id, amount_cents, status)
                VALUES (?, ?, ?, 'succeeded')
            """, (
                int(payment_intent.metadata.get('user_id')),
                payment_intent.id,
                payment_intent.amount
            ))
            
            conn.commit()
        
        logger.info(f"Activated time card for payment intent {payment_intent.id}")
    
    return {"status": "success"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "mindbot-time-tracking",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MindBotz Time Tracking Service",
        "version": "1.0.0",
        "endpoints": {
            "pricing": "/time/pricing",
            "purchase": "/time/purchase",
            "activate": "/time/activate",
            "balance": "/time/balance",
            "sessions": "/time/sessions",
            "start_session": "/time/session/start",
            "end_session": "/time/session/end",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    # Validate environment variables
    required_env_vars = ["STRIPE_SECRET_KEY", "JWT_SECRET"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        exit(1)
    
    logger.info("Starting MindBotz Time Tracking Service...")
    logger.info(f"Stripe configured: {'Yes' if STRIPE_SECRET_KEY else 'No'}")
    
    uvicorn.run(
        "time_server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )