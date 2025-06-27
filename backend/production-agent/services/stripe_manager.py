# services/stripe_manager.py

import logging
from typing import Dict, Any, Optional
import stripe
from datetime import datetime

from .supabase_client import SupabaseClient
from ..core.settings import AgentConfig

logger = logging.getLogger("mindbot.stripe")

class StripeManager:
    """
    Manages all Stripe-related operations, including payments, customers, and webhooks.
    """
    
    def __init__(self, config: AgentConfig, supabase_client: SupabaseClient):
        self.config = config
        self.supabase_client = supabase_client
        self.stripe_secret_key = config.stripe_secret_key
        self.webhook_secret = config.stripe_webhook_secret
        
        if not self.stripe_secret_key or not self.webhook_secret:
            raise ValueError("Stripe secret key and webhook secret are required.")
        
        stripe.api_key = self.stripe_secret_key
        logger.info("Stripe manager initialized successfully.")

    async def create_payment_intent(
        self, 
        user_id: str, 
        package_id: str, 
        user_email: str,
        save_payment_method: bool = False
    ) -> Dict[str, Any]:
        """
        Creates a Stripe Payment Intent for a time card purchase.
        It also creates a 'pending' time card in Supabase that will be activated upon successful payment.
        """
        try:
            tiers = await self.supabase_client.get_pricing_tiers()
            tier = next((t for t in tiers if t.id == package_id), None)
            if not tier:
                raise ValueError(f"Pricing tier '{package_id}' not found or is not active.")

            customer_id = await self._get_or_create_customer(user_id, user_email)
            
            payment_intent = stripe.PaymentIntent.create(
                amount=tier.price_cents,
                currency='usd',
                customer=customer_id,
                metadata={
                    'user_id': user_id,
                    'package_id': package_id,
                    'service': 'mindbot_time_card'
                },
                description=f"MindBot Time Card: {tier.name}",
                receipt_email=user_email,
                setup_future_usage='on_session' if save_payment_method else None
            )

            time_card = await self.supabase_client.create_time_card(
                user_id=user_id,
                package_id=package_id,
                stripe_payment_intent_id=payment_intent.id
            )
            if not time_card:
                stripe.PaymentIntent.cancel(payment_intent.id)
                raise Exception("Failed to create a pending time card record in the database.")

            logger.info(f"Created PaymentIntent {payment_intent.id} for user {user_id}.")
            return {
                'payment_intent_id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'time_card_id': time_card.id
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error during payment intent creation: {e}", exc_info=True)
            raise Exception("A payment processing error occurred with our provider.")
        except Exception as e:
            logger.error(f"Failed to create payment intent for user {user_id}: {e}", exc_info=True)
            raise

    async def _get_or_create_customer(self, user_id: str, email: str) -> str:
        """Retrieves an existing Stripe customer by email or creates a new one."""
        try:
            customers = stripe.Customer.list(email=email, limit=1)
            if customers.data:
                customer = customers.data[0]
                if customer.metadata.get('mindbot_user_id') != user_id:
                    stripe.Customer.modify(customer.id, metadata={'mindbot_user_id': user_id})
                return customer.id
            
            customer = stripe.Customer.create(
                email=email,
                metadata={'mindbot_user_id': user_id},
                description=f"MindBot User: {email}"
            )
            logger.info(f"Created new Stripe customer {customer.id} for user {user_id}.")
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error managing customer for user {user_id}: {e}", exc_info=True)
            raise Exception("Could not manage customer information with our payment provider.")

    async def handle_webhook(self, payload: bytes, sig_header: str):
        """
        Validates and processes incoming Stripe webhooks.
        Delegates to specific handler methods based on the event type.
        """
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, self.webhook_secret)
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.warning(f"Invalid Stripe webhook signature received: {e}")
            raise HTTPException(status_code=400, detail="Invalid webhook signature.")

        logger.info(f"Processing Stripe webhook event: {event.type}")
        handler = getattr(self, f"_handle_{event.type.replace('.', '_')}", self._handle_unhandled_event)
        await handler(event.data.object)

    async def _handle_payment_intent_succeeded(self, payment_intent: Dict[str, Any]):
        """Handles the 'payment_intent.succeeded' event."""
        pi_id = payment_intent['id']
        logger.info(f"Payment succeeded for intent: {pi_id}")
        if await self.supabase_client.activate_time_card(pi_id):
            await self.supabase_client.record_payment(
                user_id=payment_intent['metadata']['user_id'],
                stripe_payment_intent_id=pi_id,
                amount_cents=payment_intent['amount'],
                status='succeeded'
            )
            # Here you could trigger a confirmation email
        else:
            logger.error(f"Could not find a pending time card to activate for payment intent {pi_id}.")

    async def _handle_payment_intent_payment_failed(self, payment_intent: Dict[str, Any]):
        """Handles the 'payment_intent.payment_failed' event."""
        pi_id = payment_intent['id']
        logger.warning(f"Payment failed for intent: {pi_id}. Reason: {payment_intent.get('last_payment_error', {}).get('message')}")
        await self.supabase_client.record_payment(
            user_id=payment_intent['metadata']['user_id'],
            stripe_payment_intent_id=pi_id,
            amount_cents=payment_intent['amount'],
            status='failed'
        )
        # Here you could trigger a notification to the user

    async def _handle_unhandled_event(self, event_data: Dict[str, Any]):
        """Handles all other webhook events."""
        logger.debug(f"Received an unhandled event type.")


