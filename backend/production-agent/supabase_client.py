"""
Supabase client and database operations for MindBot
Handles user management, time cards, sessions, and payments
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

from supabase import create_client, Client
import asyncpg
from postgrest import APIError

logger = logging.getLogger("mindbot.supabase")


@dataclass
class User:
    id: str
    email: str
    full_name: str
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    email_verified: bool = False


@dataclass
class TimeCard:
    id: str
    user_id: str
    activation_code: str
    total_minutes: int
    remaining_minutes: int
    activated_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    status: str
    stripe_payment_intent_id: Optional[str] = None


@dataclass
class VoiceSession:
    id: str
    user_id: str
    session_id: str
    room_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    cost_minutes: Optional[int] = None
    status: str = 'active'
    agent_type: str = 'production'
    quality_rating: Optional[int] = None


@dataclass
class PricingTier:
    id: str
    name: str
    hours: int
    price_cents: int
    bonus_minutes: int
    description: str
    active: bool = True


class SupabaseClient:
    """Enhanced Supabase client for MindBot operations"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not all([self.supabase_url, self.supabase_key]):
            raise ValueError("Missing required Supabase environment variables")
        
        # Create service role client for admin operations
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Create anon client for user operations
        self.supabase_anon: Client = create_client(self.supabase_url, self.supabase_anon_key)
        
        logger.info("Supabase client initialized successfully")
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            response = self.supabase.table('users').select('*').eq('id', user_id).execute()
            
            if response.data:
                user_data = response.data[0]
                return User(
                    id=user_data['id'],
                    email=user_data['email'],
                    full_name=user_data['full_name'],
                    created_at=datetime.fromisoformat(user_data['created_at'].replace('Z', '+00:00')),
                    last_login=datetime.fromisoformat(user_data['last_login'].replace('Z', '+00:00')) if user_data.get('last_login') else None,
                    is_active=user_data.get('is_active', True),
                    email_verified=user_data.get('email_verified', False)
                )
            return None
            
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            response = self.supabase.table('users').select('*').eq('email', email).execute()
            
            if response.data:
                user_data = response.data[0]
                return User(
                    id=user_data['id'],
                    email=user_data['email'],
                    full_name=user_data['full_name'],
                    created_at=datetime.fromisoformat(user_data['created_at'].replace('Z', '+00:00')),
                    last_login=datetime.fromisoformat(user_data['last_login'].replace('Z', '+00:00')) if user_data.get('last_login') else None,
                    is_active=user_data.get('is_active', True),
                    email_verified=user_data.get('email_verified', False)
                )
            return None
            
        except Exception as e:
            logger.error(f"Error fetching user by email {email}: {e}")
            return None
    
    async def get_user_time_balance(self, user_id: str) -> Dict[str, Any]:
        """Get user's current time balance from active time cards"""
        try:
            # Get active time cards with remaining minutes
            response = self.supabase.table('time_cards')\
                .select('remaining_minutes, expires_at')\
                .eq('user_id', user_id)\
                .eq('status', 'active')\
                .gt('remaining_minutes', 0)\
                .execute()
            
            total_minutes = 0
            active_cards = len(response.data) if response.data else 0
            next_expiration = None
            
            if response.data:
                for card in response.data:
                    total_minutes += card['remaining_minutes']
                    
                    # Find earliest expiration
                    if card['expires_at']:
                        exp_date = datetime.fromisoformat(card['expires_at'].replace('Z', '+00:00'))
                        if not next_expiration or exp_date < next_expiration:
                            next_expiration = exp_date
            
            return {
                'total_minutes': total_minutes,
                'total_hours': round(total_minutes / 60, 1),
                'active_cards': active_cards,
                'next_expiration': next_expiration.isoformat() if next_expiration else None
            }
            
        except Exception as e:
            logger.error(f"Error fetching time balance for user {user_id}: {e}")
            return {'total_minutes': 0, 'total_hours': 0, 'active_cards': 0, 'next_expiration': None}
    
    async def create_time_card(self, user_id: str, package_id: str, stripe_payment_intent_id: str) -> Optional[TimeCard]:
        """Create a new time card for purchase"""
        try:
            # Get pricing tier
            tier_response = self.supabase.table('pricing_tiers')\
                .select('*')\
                .eq('id', package_id)\
                .eq('active', True)\
                .execute()
            
            if not tier_response.data:
                logger.error(f"Pricing tier {package_id} not found")
                return None
            
            tier = tier_response.data[0]
            total_minutes = (tier['hours'] * 60) + tier.get('bonus_minutes', 0)
            
            # Generate activation code
            import secrets
            import string
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12))
            activation_code = f"{code[:4]}-{code[4:8]}-{code[8:]}"
            
            # Create time card
            expires_at = datetime.utcnow() + timedelta(days=365)
            
            card_data = {
                'user_id': user_id,
                'activation_code': activation_code,
                'total_minutes': total_minutes,
                'remaining_minutes': total_minutes,
                'expires_at': expires_at.isoformat(),
                'status': 'pending',
                'stripe_payment_intent_id': stripe_payment_intent_id
            }
            
            response = self.supabase.table('time_cards').insert(card_data).execute()
            
            if response.data:
                card = response.data[0]
                logger.info(f"Created time card {card['id']} for user {user_id}")
                
                return TimeCard(
                    id=card['id'],
                    user_id=card['user_id'],
                    activation_code=card['activation_code'],
                    total_minutes=card['total_minutes'],
                    remaining_minutes=card['remaining_minutes'],
                    activated_at=None,
                    expires_at=datetime.fromisoformat(card['expires_at'].replace('Z', '+00:00')),
                    created_at=datetime.fromisoformat(card['created_at'].replace('Z', '+00:00')),
                    status=card['status'],
                    stripe_payment_intent_id=card['stripe_payment_intent_id']
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating time card: {e}")
            return None
    
    async def activate_time_card(self, stripe_payment_intent_id: str) -> bool:
        """Activate time card after successful payment"""
        try:
            # Update time card status to active
            response = self.supabase.table('time_cards')\
                .update({
                    'status': 'active',
                    'activated_at': datetime.utcnow().isoformat()
                })\
                .eq('stripe_payment_intent_id', stripe_payment_intent_id)\
                .execute()
            
            if response.data:
                logger.info(f"Activated time card for payment intent {stripe_payment_intent_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error activating time card: {e}")
            return False
    
    async def deduct_time(self, user_id: str, minutes: int) -> bool:
        """Deduct time from user's balance (FIFO - first expiring first)"""
        try:
            # Get active cards ordered by expiration date
            response = self.supabase.table('time_cards')\
                .select('id, remaining_minutes')\
                .eq('user_id', user_id)\
                .eq('status', 'active')\
                .gt('remaining_minutes', 0)\
                .order('expires_at')\
                .execute()
            
            if not response.data:
                return False
            
            remaining_to_deduct = minutes
            
            for card in response.data:
                if remaining_to_deduct <= 0:
                    break
                
                card_id = card['id']
                card_minutes = card['remaining_minutes']
                
                if card_minutes >= remaining_to_deduct:
                    # This card can cover the remaining time
                    new_balance = card_minutes - remaining_to_deduct
                    status = 'used' if new_balance == 0 else 'active'
                    
                    self.supabase.table('time_cards')\
                        .update({
                            'remaining_minutes': new_balance,
                            'status': status
                        })\
                        .eq('id', card_id)\
                        .execute()
                    
                    remaining_to_deduct = 0
                else:
                    # Use all remaining time from this card
                    self.supabase.table('time_cards')\
                        .update({
                            'remaining_minutes': 0,
                            'status': 'used'
                        })\
                        .eq('id', card_id)\
                        .execute()
                    
                    remaining_to_deduct -= card_minutes
            
            return remaining_to_deduct == 0
            
        except Exception as e:
            logger.error(f"Error deducting time: {e}")
            return False
    
    async def start_voice_session(self, user_id: str, session_id: str, room_name: str) -> Optional[VoiceSession]:
        """Start a new voice session"""
        try:
            session_data = {
                'user_id': user_id,
                'session_id': session_id,
                'room_name': room_name,
                'status': 'active',
                'agent_type': 'production'
            }
            
            response = self.supabase.table('voice_sessions').insert(session_data).execute()
            
            if response.data:
                session = response.data[0]
                logger.info(f"Started voice session {session_id} for user {user_id}")
                
                return VoiceSession(
                    id=session['id'],
                    user_id=session['user_id'],
                    session_id=session['session_id'],
                    room_name=session['room_name'],
                    start_time=datetime.fromisoformat(session['start_time'].replace('Z', '+00:00')),
                    status=session['status'],
                    agent_type=session['agent_type']
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error starting voice session: {e}")
            return None
    
    async def end_voice_session(self, session_id: str, duration_seconds: int) -> bool:
        """End voice session and deduct time"""
        try:
            # Calculate cost (minimum 1 minute billing)
            cost_minutes = max(1, round(duration_seconds / 60))
            
            # Get session info
            response = self.supabase.table('voice_sessions')\
                .select('user_id')\
                .eq('session_id', session_id)\
                .eq('status', 'active')\
                .execute()
            
            if not response.data:
                logger.warning(f"Active session {session_id} not found")
                return False
            
            user_id = response.data[0]['user_id']
            
            # Deduct time from user's balance
            time_deducted = await self.deduct_time(user_id, cost_minutes)
            
            # Update session record
            end_time = datetime.utcnow()
            session_status = 'completed' if time_deducted else 'error'
            
            self.supabase.table('voice_sessions')\
                .update({
                    'end_time': end_time.isoformat(),
                    'duration_seconds': duration_seconds,
                    'cost_minutes': cost_minutes,
                    'status': session_status
                })\
                .eq('session_id', session_id)\
                .execute()
            
            logger.info(f"Ended voice session {session_id}: {cost_minutes} minutes, success: {time_deducted}")
            return time_deducted
            
        except Exception as e:
            logger.error(f"Error ending voice session: {e}")
            return False
    
    async def get_pricing_tiers(self) -> List[PricingTier]:
        """Get all active pricing tiers"""
        try:
            response = self.supabase.table('pricing_tiers')\
                .select('*')\
                .eq('active', True)\
                .order('price_cents')\
                .execute()
            
            tiers = []
            if response.data:
                for tier_data in response.data:
                    tiers.append(PricingTier(
                        id=tier_data['id'],
                        name=tier_data['name'],
                        hours=tier_data['hours'],
                        price_cents=tier_data['price_cents'],
                        bonus_minutes=tier_data.get('bonus_minutes', 0),
                        description=tier_data['description'],
                        active=tier_data['active']
                    ))
            
            return tiers
            
        except Exception as e:
            logger.error(f"Error fetching pricing tiers: {e}")
            return []
    
    async def record_payment(self, user_id: str, stripe_payment_intent_id: str, amount_cents: int, status: str) -> bool:
        """Record payment in payment history"""
        try:
            payment_data = {
                'user_id': user_id,
                'stripe_payment_intent_id': stripe_payment_intent_id,
                'amount_cents': amount_cents,
                'currency': 'usd',
                'status': status
            }
            
            response = self.supabase.table('payment_history').insert(payment_data).execute()
            
            if response.data:
                logger.info(f"Recorded payment {stripe_payment_intent_id} for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error recording payment: {e}")
            return False
    
    async def update_user_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp"""
        try:
            response = self.supabase.table('users')\
                .update({'last_login': datetime.utcnow().isoformat()})\
                .eq('id', user_id)\
                .execute()
            
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"Error updating last login for user {user_id}: {e}")
            return False
    
    async def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive analytics for a user"""
        try:
            # Get user info
            user = await self.get_user_by_id(user_id)
            if not user:
                return {}
            
            # Get time balance
            balance = await self.get_user_time_balance(user_id)
            
            # Get session statistics
            session_response = self.supabase.table('voice_sessions')\
                .select('duration_seconds, cost_minutes, status')\
                .eq('user_id', user_id)\
                .execute()
            
            total_sessions = len(session_response.data) if session_response.data else 0
            total_minutes_used = sum(s.get('cost_minutes', 0) for s in session_response.data if s.get('cost_minutes'))
            completed_sessions = len([s for s in session_response.data if s.get('status') == 'completed'])
            
            # Get payment statistics
            payment_response = self.supabase.table('payment_history')\
                .select('amount_cents, status')\
                .eq('user_id', user_id)\
                .execute()
            
            total_spent_cents = sum(p.get('amount_cents', 0) for p in payment_response.data if p.get('status') == 'succeeded')
            
            return {
                'user_id': user_id,
                'email': user.email,
                'full_name': user.full_name,
                'created_at': user.created_at.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'balance': balance,
                'usage': {
                    'total_sessions': total_sessions,
                    'completed_sessions': completed_sessions,
                    'total_minutes_used': total_minutes_used,
                    'total_hours_used': round(total_minutes_used / 60, 1)
                },
                'payments': {
                    'total_spent_cents': total_spent_cents,
                    'total_spent_display': f"${total_spent_cents / 100:.2f}",
                    'transaction_count': len(payment_response.data) if payment_response.data else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting user analytics: {e}")
            return {}


# Global instance
supabase_client = SupabaseClient()