"""
Stripe payment manager for MindBot time card purchases
Handles payment intents, webhooks, and subscription management
"""

import os
import logging
from typing import Dict, Any, Optional
import json
import stripe
from datetime import datetime

from supabase_client import supabase_client, PricingTier

logger = logging.getLogger("mindbot.stripe")


class StripeManager:
    """Enhanced Stripe payment manager with time card integration"""
    
    def __init__(self):
        self.stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        
        if not self.stripe_secret_key:
            raise ValueError("STRIPE_SECRET_KEY environment variable is required")
        
        stripe.api_key = self.stripe_secret_key
        
        # Validate key type for environment
        environment = os.getenv("ENVIRONMENT", "development")
        if environment == "production" and not self.stripe_secret_key.startswith("sk_live_"):
            logger.warning("Using test Stripe key in production environment")
        elif environment != "production" and not self.stripe_secret_key.startswith("sk_test_"):
            logger.warning("Using live Stripe key in non-production environment")
        
        logger.info("Stripe manager initialized successfully")
    
    async def create_payment_intent(
        self, 
        user_id: str, 
        package_id: str, 
        user_email: str,
        save_payment_method: bool = False
    ) -> Dict[str, Any]:
        """
        Create Stripe payment intent for time card purchase
        
        Args:
            user_id: MindBot user ID
            package_id: Pricing tier ID
            user_email: User's email for customer creation
            save_payment_method: Whether to save payment method for future use
            
        Returns:
            Dictionary with payment intent details
        """
        try:
            # Get pricing tier
            tiers = await supabase_client.get_pricing_tiers()
            tier = next((t for t in tiers if t.id == package_id), None)
            
            if not tier:
                raise ValueError(f"Pricing tier {package_id} not found")
            
            # Get or create Stripe customer
            customer_id = await self._get_or_create_customer(user_id, user_email)
            
            # Calculate total minutes
            total_minutes = (tier.hours * 60) + tier.bonus_minutes
            
            # Create payment intent
            payment_intent_params = {
                'amount': tier.price_cents,
                'currency': 'usd',
                'customer': customer_id,
                'metadata': {
                    'user_id': user_id,
                    'user_email': user_email,
                    'package_id': package_id,
                    'package_name': tier.name,
                    'hours': str(tier.hours),
                    'bonus_minutes': str(tier.bonus_minutes),
                    'total_minutes': str(total_minutes),
                    'mindbot_service': 'time_card_purchase'
                },
                'description': f"MindBot {tier.name} - {tier.hours} hours of AI conversation time",
                'receipt_email': user_email
            }
            
            # Add setup for future payments if requested
            if save_payment_method:
                payment_intent_params['setup_future_usage'] = 'on_session'
            
            payment_intent = stripe.PaymentIntent.create(**payment_intent_params)
            
            # Create pending time card in database
            time_card = await supabase_client.create_time_card(
                user_id=user_id,
                package_id=package_id,
                stripe_payment_intent_id=payment_intent.id
            )
            
            if not time_card:
                # Cancel payment intent if card creation failed
                stripe.PaymentIntent.cancel(payment_intent.id)
                raise Exception("Failed to create time card record")
            
            logger.info(f"Created payment intent {payment_intent.id} for user {user_id}, package {package_id}")
            
            return {
                'payment_intent_id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'amount': payment_intent.amount,
                'currency': payment_intent.currency,
                'customer_id': customer_id,
                'time_card': {
                    'id': time_card.id,
                    'activation_code': time_card.activation_code,
                    'total_minutes': time_card.total_minutes,
                    'expires_at': time_card.expires_at.isoformat() if time_card.expires_at else None
                },
                'package': {
                    'id': tier.id,
                    'name': tier.name,
                    'hours': tier.hours,
                    'bonus_minutes': tier.bonus_minutes,
                    'description': tier.description
                }
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {e}")
            raise Exception(f"Payment processing error: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating payment intent: {e}")
            raise
    
    async def _get_or_create_customer(self, user_id: str, email: str) -> str:
        """Get existing Stripe customer or create new one"""
        try:
            # Search for existing customer by email
            customers = stripe.Customer.list(email=email, limit=1)
            
            if customers.data:
                customer = customers.data[0]
                
                # Update metadata with user_id if missing
                if customer.metadata.get('mindbot_user_id') != user_id:
                    stripe.Customer.modify(
                        customer.id,
                        metadata={'mindbot_user_id': user_id}
                    )
                
                return customer.id
            
            # Create new customer
            customer = stripe.Customer.create(
                email=email,
                metadata={
                    'mindbot_user_id': user_id,
                    'service': 'mindbot_voice_ai'
                },
                description=f"MindBot user - {email}"
            )
            
            logger.info(f"Created Stripe customer {customer.id} for user {user_id}")
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error managing customer: {e}")
            raise Exception(f"Customer management error: {str(e)}")
    
    async def handle_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """
        Handle Stripe webhook events
        
        Args:
            payload: Raw webhook payload
            sig_header: Stripe signature header
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            
            event_type = event['type']
            event_data = event['data']['object']
            
            logger.info(f"Processing Stripe webhook: {event_type}")
            
            result = {'event_type': event_type, 'processed': False, 'error': None}
            
            if event_type == 'payment_intent.succeeded':
                result = await self._handle_payment_success(event_data)
            elif event_type == 'payment_intent.payment_failed':
                result = await self._handle_payment_failed(event_data)
            elif event_type == 'customer.subscription.created':
                result = await self._handle_subscription_created(event_data)
            elif event_type == 'customer.subscription.deleted':
                result = await self._handle_subscription_cancelled(event_data)
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
                result['processed'] = True
            
            return result
            
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid webhook signature")
            raise Exception("Invalid webhook signature")
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            raise
    
    async def _handle_payment_success(self, payment_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful payment"""
        try:
            payment_intent_id = payment_intent['id']
            user_id = payment_intent['metadata'].get('user_id')
            amount_cents = payment_intent['amount']
            
            if not user_id:
                logger.error(f"No user_id in payment intent {payment_intent_id}")
                return {'processed': False, 'error': 'Missing user_id'}
            
            # Activate time card
            activated = await supabase_client.activate_time_card(payment_intent_id)
            
            if not activated:
                logger.error(f"Failed to activate time card for payment {payment_intent_id}")
                return {'processed': False, 'error': 'Time card activation failed'}
            
            # Record payment in history
            await supabase_client.record_payment(
                user_id=user_id,
                stripe_payment_intent_id=payment_intent_id,
                amount_cents=amount_cents,
                status='succeeded'
            )
            
            logger.info(f"Successfully processed payment {payment_intent_id} for user {user_id}")
            
            # TODO: Send confirmation email/notification
            await self._send_purchase_confirmation(user_id, payment_intent)
            
            return {'processed': True, 'payment_intent_id': payment_intent_id}
            
        except Exception as e:
            logger.error(f"Error handling payment success: {e}")
            return {'processed': False, 'error': str(e)}
    
    async def _handle_payment_failed(self, payment_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed payment"""
        try:
            payment_intent_id = payment_intent['id']
            user_id = payment_intent['metadata'].get('user_id')
            
            if user_id:
                # Record failed payment
                await supabase_client.record_payment(
                    user_id=user_id,
                    stripe_payment_intent_id=payment_intent_id,
                    amount_cents=payment_intent['amount'],
                    status='failed'
                )
                
                # TODO: Send failure notification
                await self._send_payment_failure_notification(user_id, payment_intent)
            
            logger.warning(f"Payment failed for {payment_intent_id}")
            return {'processed': True, 'payment_intent_id': payment_intent_id}
            
        except Exception as e:
            logger.error(f"Error handling payment failure: {e}")
            return {'processed': False, 'error': str(e)}
    
    async def _handle_subscription_created(self, subscription: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription creation (for future subscription features)"""
        try:
            customer_id = subscription['customer']
            subscription_id = subscription['id']
            
            # Get customer metadata to find user_id
            customer = stripe.Customer.retrieve(customer_id)
            user_id = customer.metadata.get('mindbot_user_id')
            
            if user_id:
                logger.info(f"Subscription {subscription_id} created for user {user_id}")
                # TODO: Handle subscription creation in database
            
            return {'processed': True, 'subscription_id': subscription_id}
            
        except Exception as e:
            logger.error(f"Error handling subscription creation: {e}")
            return {'processed': False, 'error': str(e)}
    
    async def _handle_subscription_cancelled(self, subscription: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription cancellation"""
        try:
            subscription_id = subscription['id']
            logger.info(f"Subscription {subscription_id} cancelled")
            # TODO: Handle subscription cancellation in database
            
            return {'processed': True, 'subscription_id': subscription_id}
            
        except Exception as e:
            logger.error(f"Error handling subscription cancellation: {e}")
            return {'processed': False, 'error': str(e)}
    
    async def _send_purchase_confirmation(self, user_id: str, payment_intent: Dict[str, Any]):
        """Send purchase confirmation (placeholder for email/notification service)"""
        try:
            package_name = payment_intent['metadata'].get('package_name', 'Time Card')
            amount = payment_intent['amount'] / 100
            
            logger.info(f"Purchase confirmation: User {user_id} bought {package_name} for ${amount:.2f}")
            
            # TODO: Integrate with email service (SendGrid, AWS SES, etc.)
            # TODO: Send in-app notification
            
        except Exception as e:
            logger.error(f"Error sending purchase confirmation: {e}")
    
    async def _send_payment_failure_notification(self, user_id: str, payment_intent: Dict[str, Any]):
        """Send payment failure notification"""
        try:
            logger.info(f"Payment failure notification for user {user_id}")
            
            # TODO: Send failure notification email
            # TODO: Log for customer support follow-up
            
        except Exception as e:
            logger.error(f"Error sending payment failure notification: {e}")
    
    async def create_refund(self, payment_intent_id: str, amount_cents: Optional[int] = None, reason: str = "requested_by_customer") -> Dict[str, Any]:
        """Create a refund for a payment"""
        try:
            refund_params = {
                'payment_intent': payment_intent_id,
                'reason': reason,
                'metadata': {
                    'refund_timestamp': datetime.utcnow().isoformat(),
                    'service': 'mindbot'
                }
            }
            
            if amount_cents:
                refund_params['amount'] = amount_cents
            
            refund = stripe.Refund.create(**refund_params)
            
            logger.info(f"Created refund {refund.id} for payment {payment_intent_id}")
            
            # TODO: Update time card status to refunded
            # TODO: Remove time from user's balance if already used
            
            return {
                'refund_id': refund.id,
                'amount': refund.amount,
                'status': refund.status,
                'payment_intent_id': payment_intent_id
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating refund: {e}")
            raise Exception(f"Refund error: {str(e)}")


# Global instance
stripe_manager = StripeManager()