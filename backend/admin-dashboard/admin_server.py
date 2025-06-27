#!/usr/bin/env python3
"""
MindBotz Admin Dashboard
Administrative interface for time tracking, user management, and analytics
"""

import os
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import jwt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-this")
JWT_ALGORITHM = "HS256"
TIME_DB_PATH = os.getenv("TIME_DB_PATH", "../time-service/mindbot_time_tracking.db")
AUTH_DB_PATH = os.getenv("AUTH_DB_PATH", "../auth-service/mindbot_users.db")

# Admin credentials (in production, use proper admin user system)
ADMIN_USERS = ["admin@mindbot.ai", "support@mindbot.ai"]

# Pydantic models
class RefundRequest(BaseModel):
    payment_intent_id: str
    reason: str
    amount_cents: Optional[int] = None  # Partial refund amount

class PricingTierUpdate(BaseModel):
    id: str
    name: str
    hours: int
    price_cents: int
    bonus_minutes: int
    description: str
    active: bool

@dataclass
class UserAnalytics:
    user_id: int
    email: str
    full_name: str
    total_purchased_hours: float
    total_used_hours: float
    remaining_hours: float
    total_spent_cents: int
    session_count: int
    avg_session_minutes: float
    last_activity: Optional[datetime]

class AdminDatabaseManager:
    """Handles database queries for admin dashboard"""
    
    def __init__(self, time_db_path: str, auth_db_path: str):
        self.time_db_path = time_db_path
        self.auth_db_path = auth_db_path
    
    def get_revenue_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get revenue analytics for the specified period"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with sqlite3.connect(self.time_db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Total revenue
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_transactions,
                    SUM(amount_cents) as total_revenue_cents,
                    AVG(amount_cents) as avg_transaction_cents
                FROM payment_history 
                WHERE status = 'succeeded' AND created_at >= ?
            """, (cutoff_date.isoformat(),))
            
            revenue_data = cursor.fetchone()
            
            # Daily revenue trend
            cursor = conn.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as transactions,
                    SUM(amount_cents) as revenue_cents
                FROM payment_history 
                WHERE status = 'succeeded' AND created_at >= ?
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """, (cutoff_date.isoformat(),))
            
            daily_revenue = cursor.fetchall()
            
            # Package popularity
            cursor = conn.execute("""
                SELECT 
                    pt.name as package_name,
                    COUNT(*) as purchases,
                    SUM(ph.amount_cents) as revenue_cents
                FROM payment_history ph
                JOIN time_cards tc ON tc.stripe_payment_intent_id = ph.stripe_payment_intent_id
                JOIN pricing_tiers pt ON pt.id IN (
                    SELECT id FROM pricing_tiers 
                    WHERE (hours * 60 + bonus_minutes) = tc.total_minutes
                    LIMIT 1
                )
                WHERE ph.status = 'succeeded' AND ph.created_at >= ?
                GROUP BY pt.name
                ORDER BY purchases DESC
            """, (cutoff_date.isoformat(),))
            
            package_stats = cursor.fetchall()
        
        return {
            "period_days": days,
            "total_transactions": revenue_data['total_transactions'] or 0,
            "total_revenue_cents": revenue_data['total_revenue_cents'] or 0,
            "total_revenue_display": f"${(revenue_data['total_revenue_cents'] or 0) / 100:.2f}",
            "avg_transaction_cents": revenue_data['avg_transaction_cents'] or 0,
            "avg_transaction_display": f"${(revenue_data['avg_transaction_cents'] or 0) / 100:.2f}",
            "daily_revenue": [
                {
                    "date": row['date'],
                    "transactions": row['transactions'],
                    "revenue_cents": row['revenue_cents'],
                    "revenue_display": f"${row['revenue_cents'] / 100:.2f}"
                } for row in daily_revenue
            ],
            "package_stats": [
                {
                    "package_name": row['package_name'],
                    "purchases": row['purchases'],
                    "revenue_cents": row['revenue_cents'],
                    "revenue_display": f"${row['revenue_cents'] / 100:.2f}"
                } for row in package_stats
            ]
        }
    
    def get_usage_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get usage analytics for the specified period"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        with sqlite3.connect(self.time_db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Usage statistics
            cursor = conn.execute("""
                SELECT 
                    COUNT(DISTINCT user_id) as active_users,
                    COUNT(*) as total_sessions,
                    SUM(cost_minutes) as total_minutes_used,
                    AVG(cost_minutes) as avg_session_minutes,
                    AVG(duration_seconds) as avg_session_duration_seconds
                FROM time_sessions 
                WHERE status = 'completed' AND start_time >= ?
            """, (cutoff_date.isoformat(),))
            
            usage_data = cursor.fetchone()
            
            # Daily usage trend
            cursor = conn.execute("""
                SELECT 
                    DATE(start_time) as date,
                    COUNT(DISTINCT user_id) as active_users,
                    COUNT(*) as sessions,
                    SUM(cost_minutes) as minutes_used
                FROM time_sessions 
                WHERE status = 'completed' AND start_time >= ?
                GROUP BY DATE(start_time)
                ORDER BY date DESC
            """, (cutoff_date.isoformat(),))
            
            daily_usage = cursor.fetchall()
        
        return {
            "period_days": days,
            "active_users": usage_data['active_users'] or 0,
            "total_sessions": usage_data['total_sessions'] or 0,
            "total_minutes_used": usage_data['total_minutes_used'] or 0,
            "total_hours_used": round((usage_data['total_minutes_used'] or 0) / 60, 1),
            "avg_session_minutes": round(usage_data['avg_session_minutes'] or 0, 1),
            "avg_session_duration_seconds": usage_data['avg_session_duration_seconds'] or 0,
            "daily_usage": [
                {
                    "date": row['date'],
                    "active_users": row['active_users'],
                    "sessions": row['sessions'],
                    "minutes_used": row['minutes_used'],
                    "hours_used": round(row['minutes_used'] / 60, 1)
                } for row in daily_usage
            ]
        }
    
    def get_user_analytics(self, limit: int = 100) -> List[UserAnalytics]:
        """Get detailed user analytics"""
        with sqlite3.connect(self.time_db_path) as time_conn, \
             sqlite3.connect(self.auth_db_path) as auth_conn:
            
            time_conn.row_factory = sqlite3.Row
            auth_conn.row_factory = sqlite3.Row
            
            # Get user data with analytics
            cursor = time_conn.execute("""
                SELECT 
                    u.id,
                    u.email,
                    u.full_name,
                    COALESCE(SUM(tc.total_minutes), 0) as total_purchased_minutes,
                    COALESCE(SUM(tc.total_minutes - tc.remaining_minutes), 0) as total_used_minutes,
                    COALESCE(SUM(tc.remaining_minutes), 0) as remaining_minutes,
                    COALESCE(SUM(ph.amount_cents), 0) as total_spent_cents,
                    COUNT(DISTINCT ts.id) as session_count,
                    AVG(ts.cost_minutes) as avg_session_minutes,
                    MAX(ts.start_time) as last_activity
                FROM (
                    SELECT id, email, full_name FROM users
                ) u
                LEFT JOIN time_cards tc ON tc.user_id = u.id
                LEFT JOIN payment_history ph ON ph.user_id = u.id AND ph.status = 'succeeded'
                LEFT JOIN time_sessions ts ON ts.user_id = u.id AND ts.status = 'completed'
                GROUP BY u.id, u.email, u.full_name
                ORDER BY total_spent_cents DESC
                LIMIT ?
            """, (limit,))
            
            # This is a complex query that would need proper JOIN across databases
            # For now, let's simplify and get basic user data
            auth_cursor = auth_conn.execute("SELECT id, email, full_name FROM users LIMIT ?", (limit,))
            users = auth_cursor.fetchall()
            
            analytics = []
            for user in users:
                user_id = user['id']
                
                # Get time data for this user
                time_cursor = time_conn.execute("""
                    SELECT 
                        COALESCE(SUM(total_minutes), 0) as purchased_minutes,
                        COALESCE(SUM(total_minutes - remaining_minutes), 0) as used_minutes,
                        COALESCE(SUM(remaining_minutes), 0) as remaining_minutes
                    FROM time_cards WHERE user_id = ?
                """, (user_id,))
                time_data = time_cursor.fetchone()
                
                # Get payment data
                payment_cursor = time_conn.execute("""
                    SELECT COALESCE(SUM(amount_cents), 0) as total_spent
                    FROM payment_history WHERE user_id = ? AND status = 'succeeded'
                """, (user_id,))
                payment_data = payment_cursor.fetchone()
                
                # Get session data
                session_cursor = time_conn.execute("""
                    SELECT 
                        COUNT(*) as session_count,
                        AVG(cost_minutes) as avg_minutes,
                        MAX(start_time) as last_activity
                    FROM time_sessions WHERE user_id = ? AND status = 'completed'
                """, (user_id,))
                session_data = session_cursor.fetchone()
                
                analytics.append(UserAnalytics(
                    user_id=user_id,
                    email=user['email'],
                    full_name=user['full_name'],
                    total_purchased_hours=round((time_data['purchased_minutes'] or 0) / 60, 1),
                    total_used_hours=round((time_data['used_minutes'] or 0) / 60, 1),
                    remaining_hours=round((time_data['remaining_minutes'] or 0) / 60, 1),
                    total_spent_cents=payment_data['total_spent'] or 0,
                    session_count=session_data['session_count'] or 0,
                    avg_session_minutes=round(session_data['avg_minutes'] or 0, 1),
                    last_activity=datetime.fromisoformat(session_data['last_activity']) if session_data['last_activity'] else None
                ))
        
        return analytics
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status and health metrics"""
        with sqlite3.connect(self.time_db_path) as time_conn, \
             sqlite3.connect(self.auth_db_path) as auth_conn:
            
            time_conn.row_factory = sqlite3.Row
            auth_conn.row_factory = sqlite3.Row
            
            # User counts
            auth_cursor = auth_conn.execute("SELECT COUNT(*) as total_users FROM users")
            total_users = auth_cursor.fetchone()['total_users']
            
            # Active time cards
            time_cursor = time_conn.execute("""
                SELECT 
                    COUNT(*) as active_cards,
                    SUM(remaining_minutes) as total_remaining_minutes
                FROM time_cards 
                WHERE status = 'active' AND remaining_minutes > 0
            """)
            card_data = time_cursor.fetchone()
            
            # Recent activity (last 24 hours)
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            time_cursor = time_conn.execute("""
                SELECT COUNT(*) as recent_sessions
                FROM time_sessions 
                WHERE start_time >= ?
            """, (recent_cutoff.isoformat(),))
            recent_activity = time_cursor.fetchone()
            
            # Error sessions (insufficient balance)
            time_cursor = time_conn.execute("""
                SELECT COUNT(*) as error_sessions
                FROM time_sessions 
                WHERE status = 'error' AND start_time >= ?
            """, (recent_cutoff.isoformat(),))
            error_data = time_cursor.fetchone()
        
        return {
            "total_users": total_users,
            "active_time_cards": card_data['active_cards'] or 0,
            "total_remaining_minutes": card_data['total_remaining_minutes'] or 0,
            "total_remaining_hours": round((card_data['total_remaining_minutes'] or 0) / 60, 1),
            "recent_sessions_24h": recent_activity['recent_sessions'] or 0,
            "error_sessions_24h": error_data['error_sessions'] or 0,
            "system_health": "healthy" if (error_data['error_sessions'] or 0) < 10 else "warning"
        }

# Initialize components
admin_db = AdminDatabaseManager(TIME_DB_PATH, AUTH_DB_PATH)

# FastAPI app
app = FastAPI(
    title="MindBotz Admin Dashboard",
    description="Administrative interface for time tracking and user management",
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

async def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify admin JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Check if user is admin
        if payload.get("email") not in ADMIN_USERS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# API Endpoints

@app.get("/admin/dashboard")
async def get_dashboard_data(admin_user: Dict = Depends(verify_admin_token)):
    """Get comprehensive dashboard data"""
    return {
        "system_status": admin_db.get_system_status(),
        "revenue_analytics": admin_db.get_revenue_analytics(30),
        "usage_analytics": admin_db.get_usage_analytics(30),
        "recent_users": admin_db.get_user_analytics(20)
    }

@app.get("/admin/analytics/revenue")
async def get_revenue_analytics(
    days: int = 30,
    admin_user: Dict = Depends(verify_admin_token)
):
    """Get detailed revenue analytics"""
    return admin_db.get_revenue_analytics(days)

@app.get("/admin/analytics/usage")
async def get_usage_analytics(
    days: int = 30,
    admin_user: Dict = Depends(verify_admin_token)
):
    """Get detailed usage analytics"""
    return admin_db.get_usage_analytics(days)

@app.get("/admin/users")
async def get_user_analytics(
    limit: int = 100,
    admin_user: Dict = Depends(verify_admin_token)
):
    """Get user analytics and details"""
    users = admin_db.get_user_analytics(limit)
    
    return {
        "users": [
            {
                "user_id": user.user_id,
                "email": user.email,
                "full_name": user.full_name,
                "total_purchased_hours": user.total_purchased_hours,
                "total_used_hours": user.total_used_hours,
                "remaining_hours": user.remaining_hours,
                "total_spent_cents": user.total_spent_cents,
                "total_spent_display": f"${user.total_spent_cents / 100:.2f}",
                "session_count": user.session_count,
                "avg_session_minutes": user.avg_session_minutes,
                "last_activity": user.last_activity.isoformat() if user.last_activity else None
            } for user in users
        ]
    }

@app.get("/admin/pricing")
async def get_pricing_management(admin_user: Dict = Depends(verify_admin_token)):
    """Get pricing tiers for management"""
    with sqlite3.connect(TIME_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT *, 
                (SELECT COUNT(*) FROM time_cards tc 
                 WHERE (tc.total_minutes = (pt.hours * 60 + pt.bonus_minutes))) as usage_count
            FROM pricing_tiers pt
            ORDER BY price_cents ASC
        """)
        
        tiers = []
        for row in cursor.fetchall():
            tiers.append({
                "id": row['id'],
                "name": row['name'],
                "hours": row['hours'],
                "price_cents": row['price_cents'],
                "price_display": f"${row['price_cents'] / 100:.2f}",
                "bonus_minutes": row['bonus_minutes'] or 0,
                "total_minutes": (row['hours'] * 60) + (row['bonus_minutes'] or 0),
                "description": row['description'],
                "active": bool(row['active']),
                "usage_count": row['usage_count'] or 0,
                "created_at": row['created_at']
            })
    
    return {"pricing_tiers": tiers}

@app.put("/admin/pricing/{tier_id}")
async def update_pricing_tier(
    tier_id: str,
    tier_data: PricingTierUpdate,
    admin_user: Dict = Depends(verify_admin_token)
):
    """Update a pricing tier"""
    with sqlite3.connect(TIME_DB_PATH) as conn:
        conn.execute("""
            UPDATE pricing_tiers 
            SET name = ?, hours = ?, price_cents = ?, bonus_minutes = ?, 
                description = ?, active = ?
            WHERE id = ?
        """, (
            tier_data.name,
            tier_data.hours,
            tier_data.price_cents,
            tier_data.bonus_minutes,
            tier_data.description,
            tier_data.active,
            tier_id
        ))
        
        if conn.total_changes == 0:
            raise HTTPException(status_code=404, detail="Pricing tier not found")
        
        conn.commit()
    
    logger.info(f"Updated pricing tier {tier_id} by admin {admin_user['email']}")
    return {"message": "Pricing tier updated successfully"}

@app.get("/admin/reports/user/{user_id}")
async def get_user_report(
    user_id: int,
    admin_user: Dict = Depends(verify_admin_token)
):
    """Get detailed report for a specific user"""
    with sqlite3.connect(TIME_DB_PATH) as time_conn, \
         sqlite3.connect(AUTH_DB_PATH) as auth_conn:
        
        # Get user info
        auth_conn.row_factory = sqlite3.Row
        user_cursor = auth_conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_data = user_cursor.fetchone()
        
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        time_conn.row_factory = sqlite3.Row
        
        # Get time cards
        cards_cursor = time_conn.execute("""
            SELECT * FROM time_cards WHERE user_id = ? ORDER BY created_at DESC
        """, (user_id,))
        time_cards = cards_cursor.fetchall()
        
        # Get sessions
        sessions_cursor = time_conn.execute("""
            SELECT * FROM time_sessions WHERE user_id = ? ORDER BY start_time DESC LIMIT 50
        """, (user_id,))
        sessions = sessions_cursor.fetchall()
        
        # Get payments
        payments_cursor = time_conn.execute("""
            SELECT * FROM payment_history WHERE user_id = ? ORDER BY created_at DESC
        """, (user_id,))
        payments = payments_cursor.fetchall()
    
    return {
        "user": {
            "id": user_data['id'],
            "email": user_data['email'],
            "full_name": user_data['full_name'],
            "created_at": user_data['created_at'],
            "last_login": user_data['last_login']
        },
        "time_cards": [dict(card) for card in time_cards],
        "recent_sessions": [dict(session) for session in sessions],
        "payment_history": [dict(payment) for payment in payments]
    }

@app.get("/admin/system/status")
async def get_system_status(admin_user: Dict = Depends(verify_admin_token)):
    """Get system status and health metrics"""
    return admin_db.get_system_status()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "mindbot-admin-dashboard",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MindBotz Admin Dashboard",
        "version": "1.0.0",
        "endpoints": {
            "dashboard": "/admin/dashboard",
            "revenue_analytics": "/admin/analytics/revenue",
            "usage_analytics": "/admin/analytics/usage",
            "users": "/admin/users",
            "pricing": "/admin/pricing",
            "system_status": "/admin/system/status",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    # Validate environment variables
    if not os.path.exists(TIME_DB_PATH):
        logger.warning(f"Time database not found at {TIME_DB_PATH}")
    
    if not os.path.exists(AUTH_DB_PATH):
        logger.warning(f"Auth database not found at {AUTH_DB_PATH}")
    
    logger.info("Starting MindBotz Admin Dashboard...")
    logger.info(f"Admin users: {', '.join(ADMIN_USERS)}")
    
    uvicorn.run(
        "admin_server:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )