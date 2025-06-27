# services/supabase_client.py

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from supabase import create_client, Client
from postgrest import APIError

from ..core.settings import AgentConfig

logger = logging.getLogger("mindbot.supabase")

# Pydantic models for data validation and structure
class User(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    email_verified: bool = False

class TimeCard(BaseModel):
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

class VoiceSession(BaseModel):
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

class PricingTier(BaseModel):
    id: str
    name: str
    hours: int
    price_cents: int
    bonus_minutes: int
    description: str
    active: bool = True

class SupabaseClient:
    """
    A client for interacting with the Supabase database.
    This class provides methods for all database operations required by MindBot.
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.supabase_url = config.supabase_url
        self.supabase_key = config.supabase_service_role_key
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase URL and service role key are required.")
        
        try:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info("Supabase client initialized successfully.")
        except Exception as e:
            logger.critical(f"Failed to initialize Supabase client: {e}", exc_info=True)
            raise

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Retrieves a user by their unique ID."""
        try:
            response = await self.client.table('users').select('*').eq('id', user_id).single().execute()
            return User(**response.data) if response.data else None
        except APIError as e:
            logger.error(f"API error fetching user {user_id}: {e.message}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching user {user_id}: {e}", exc_info=True)
            return None

    async def get_user_time_balance(self, user_id: str) -> Dict[str, Any]:
        """Calculates a user's total time balance from all active time cards."""
        try:
            response = await self.client.table('time_cards').select('remaining_minutes, expires_at') \
                .eq('user_id', user_id) \
                .eq('status', 'active') \
                .gt('remaining_minutes', 0) \
                .execute()

            if not response.data:
                return {'total_minutes': 0, 'total_hours': 0, 'active_cards': 0, 'next_expiration': None}

            total_minutes = sum(card['remaining_minutes'] for card in response.data)
            exp_dates = [datetime.fromisoformat(c['expires_at']) for c in response.data if c.get('expires_at')]
            next_expiration = min(exp_dates) if exp_dates else None

            return {
                'total_minutes': total_minutes,
                'total_hours': round(total_minutes / 60, 2),
                'active_cards': len(response.data),
                'next_expiration': next_expiration.isoformat() if next_expiration else None
            }
        except Exception as e:
            logger.error(f"Error fetching time balance for user {user_id}: {e}", exc_info=True)
            return {'total_minutes': 0, 'total_hours': 0, 'active_cards': 0, 'next_expiration': None}

    async def create_time_card(self, user_id: str, package_id: str, stripe_payment_intent_id: str) -> Optional[TimeCard]:
        """Creates a new time card record in a 'pending' state before payment."""
        try:
            tiers = await self.get_pricing_tiers()
            tier = next((t for t in tiers if t.id == package_id), None)
            if not tier:
                raise ValueError(f"Pricing tier '{package_id}' not found or is not active.")

            total_minutes = (tier.hours * 60) + tier.bonus_minutes
            activation_code = self._generate_activation_code()
            expires_at = datetime.utcnow() + timedelta(days=self.config.time_card_expiry_days)

            card_data = {
                'user_id': user_id,
                'activation_code': activation_code,
                'total_minutes': total_minutes,
                'remaining_minutes': total_minutes,
                'expires_at': expires_at.isoformat(),
                'status': 'pending',
                'stripe_payment_intent_id': stripe_payment_intent_id,
                'package_id': package_id
            }
            
            response = await self.client.table('time_cards').insert(card_data).execute()
            logger.info(f"Created pending time card for user {user_id} with payment intent {stripe_payment_intent_id}.")
            return TimeCard(**response.data[0]) if response.data else None
        except Exception as e:
            logger.error(f"Error creating time card for user {user_id}: {e}", exc_info=True)
            return None

    async def activate_time_card(self, stripe_payment_intent_id: str) -> bool:
        """Activates a 'pending' time card after successful payment."""
        try:
            response = await self.client.table('time_cards').update({
                'status': 'active',
                'activated_at': datetime.utcnow().isoformat()
            }).eq('stripe_payment_intent_id', stripe_payment_intent_id).eq('status', 'pending').execute()
            
            if response.data:
                logger.info(f"Activated time card for payment intent {stripe_payment_intent_id}.")
                return True
            else:
                logger.warning(f"No pending time card found to activate for payment intent {stripe_payment_intent_id}.")
                return False
        except Exception as e:
            logger.error(f"Error activating time card for payment {stripe_payment_intent_id}: {e}", exc_info=True)
            return False

    async def deduct_time(self, user_id: str, minutes_to_deduct: int) -> bool:
        """Deducts time from a user's active time cards, using the one that expires soonest first (FIFO)."""
        # This operation should be atomic. Using a database function is recommended.
        try:
            rpc_params = {'p_user_id': user_id, 'p_minutes_to_deduct': minutes_to_deduct}
            response = await self.client.rpc('deduct_user_time', rpc_params).execute()
            
            if response.data:
                logger.info(f"Successfully deducted {minutes_to_deduct} minutes for user {user_id}.")
                return True
            else:
                logger.warning(f"Failed to deduct {minutes_to_deduct} minutes for user {user_id}. Not enough balance?")
                return False
        except Exception as e:
            logger.error(f"Error deducting time for user {user_id}: {e}", exc_info=True)
            return False

    async def start_voice_session(self, user_id: str, session_id: str, room_name: str, agent_type: str) -> Optional[VoiceSession]:
        """Records the start of a new voice session."""
        try:
            session_data = {
                'user_id': user_id,
                'session_id': session_id,
                'room_name': room_name,
                'status': 'active',
                'agent_type': agent_type
            }
            response = await self.client.table('voice_sessions').insert(session_data).execute()
            logger.info(f"Started voice session {session_id} for user {user_id}.")
            return VoiceSession(**response.data[0]) if response.data else None
        except Exception as e:
            logger.error(f"Error starting voice session for user {user_id}: {e}", exc_info=True)
            return None

    async def end_voice_session(self, session_id: str, duration_seconds: int) -> bool:
        """Records the end of a voice session and deducts the time cost."""
        cost_minutes = max(self.config.minimum_session_minutes, round(duration_seconds / 60))
        
        try:
            session_response = await self.client.table('voice_sessions').select('user_id').eq('session_id', session_id).single().execute()
            if not session_response.data:
                logger.warning(f"Could not find active session {session_id} to end.")
                return False

            user_id = session_response.data['user_id']
            time_deducted = await self.deduct_time(user_id, cost_minutes)
            
            update_data = {
                'end_time': datetime.utcnow().isoformat(),
                'duration_seconds': duration_seconds,
                'cost_minutes': cost_minutes,
                'status': 'completed' if time_deducted else 'completed_no_charge'
            }
            await self.client.table('voice_sessions').update(update_data).eq('session_id', session_id).execute()
            
            logger.info(f"Ended voice session {session_id}. Cost: {cost_minutes} mins. Deducted: {time_deducted}.")
            return time_deducted
        except Exception as e:
            logger.error(f"Error ending voice session {session_id}: {e}", exc_info=True)
            return False

    async def get_pricing_tiers(self) -> List[PricingTier]:
        """Retrieves all active pricing tiers, ordered by price."""
        try:
            response = await self.client.table('pricing_tiers').select('*').eq('active', True).order('price_cents').execute()
            return [PricingTier(**tier) for tier in response.data] if response.data else []
        except Exception as e:
            logger.error(f"Error fetching pricing tiers: {e}", exc_info=True)
            return []

    async def record_payment(self, user_id: str, stripe_payment_intent_id: str, amount_cents: int, status: str, currency: str = 'usd') -> bool:
        """Records a payment transaction in the payment history."""
        try:
            payment_data = {
                'user_id': user_id,
                'stripe_payment_intent_id': stripe_payment_intent_id,
                'amount_cents': amount_cents,
                'currency': currency,
                'status': status
            }
            await self.client.table('payment_history').insert(payment_data).execute()
            logger.info(f"Recorded {status} payment {stripe_payment_intent_id} for user {user_id}.")
            return True
        except Exception as e:
            logger.error(f"Error recording payment for user {user_id}: {e}", exc_info=True)
            return False

    def _generate_activation_code(self) -> str:
        """Generates a unique, human-readable activation code."""
        import secrets
        import string
        code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12))
        return f"{code[:4]}-{code[4:8]}-{code[8:]}"


