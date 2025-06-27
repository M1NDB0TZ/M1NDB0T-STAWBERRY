"""
Monetization service for MindBot - Handles subscriptions, ads, and revenue optimization
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import asyncio

import stripe
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt

from supabase_client import supabase_client

# Configure logging
logger = logging.getLogger("mindbot.monetization")

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key")
JWT_ALGORITHM = "HS256"

# FastAPI app
app = FastAPI(
    title="MindBot Monetization Service",
    description="Handles subscriptions, ads, and revenue optimization for MindBot",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Pydantic models
class SubscriptionRequest(BaseModel):
    """Request to create a subscription"""
    plan_id: str
    payment_method_id: str
    coupon_code: Optional[str] = None

class TimeCardPurchaseRequest(BaseModel):
    """Request to purchase a time card"""
    package_id: str
    payment_method_id: str
    save_payment_method: bool = False
    coupon_code: Optional[str] = None

class AdViewRequest(BaseModel):
    """Request to record an ad view"""
    ad_id: str
    view_duration: int
    completion: bool = False
    interaction: bool = False

# Authentication functions
async def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify JWT token and return user info"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current authenticated user"""
    return await verify_jwt_token(credentials)

from core.settings import get_config

config = get_config('agent')
SUBSCRIPTION_PLANS = config.subscription_plans
TIME_CARD_PACKAGES = config.time_card_packages
COUPON_CODES = config.coupon_codes
AD_CONFIG = config.ad_config

# API Endpoints

@app.get("/plans", tags=["Subscriptions"])
async def get_subscription_plans():
    """Get available subscription plans"""
    return {
        "plans": [
            {
                "id": plan_id,
                "name": plan["name"],
                "price": plan["amount"] / 100,
                "price_display": f"${plan['amount'] / 100:.2f}/{plan['interval']}",
                "currency": plan["currency"],
                "interval": plan["interval"],
                "features": plan["features"]
            }
            for plan_id, plan in SUBSCRIPTION_PLANS.items()
        ]
    }

@app.post("/subscriptions", tags=["Subscriptions"])
async def create_subscription(
    subscription_request: SubscriptionRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Create a new subscription"""
    try:
        user_id = current_user.get("user_id", str(current_user.get("sub", "unknown")))
        user_email = current_user.get("email", "unknown@example.com")
        
        # Validate plan
        plan = SUBSCRIPTION_PLANS.get(subscription_request.plan_id)
        if not plan:
            raise HTTPException(status_code=400, detail="Invalid plan ID")
        
        # Get or create customer
        customer = await _get_or_create_customer(user_id, user_email)
        
        # Apply coupon if provided
        discount = None
        if subscription_request.coupon_code:
            coupon = COUPON_CODES.get(subscription_request.coupon_code.upper())
            if coupon and datetime.strptime(coupon["valid_until"], "%Y-%m-%d") > datetime.utcnow():
                # In production, create or retrieve actual Stripe coupon
                discount = {"coupon": subscription_request.coupon_code}
        
        # Create subscription
        subscription = stripe.Subscription.create(
            customer=customer,
            items=[
                {"price": plan["price_id"]}
            ],
            payment_behavior="default_incomplete",
            payment_settings={"save_default_payment_method": "on_subscription"},
            expand=["latest_invoice.payment_intent"],
            discounts=discount
        )
        
        # Return client secret for frontend to complete payment
        return {
            "subscription_id": subscription.id,
            "client_secret": subscription.latest_invoice.payment_intent.client_secret,
            "plan": plan["name"],
            "amount": plan["amount"] / 100,
            "currency": plan["currency"],
            "interval": plan["interval"]
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating subscription: {e}")
        raise HTTPException(status_code=400, detail=f"Payment processing error: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(status_code=500, detail="Error processing subscription")

@app.get("/subscriptions/current", tags=["Subscriptions"])
async def get_current_subscription(
    current_user: Dict = Depends(get_current_user)
):
    """Get user's current subscription"""
    try:
        user_id = current_user.get("user_id", str(current_user.get("sub", "unknown")))
        
        # In production, get from database
        # For now, return mock data
        subscription = {
            "status": "active",
            "plan": "premium_monthly",
            "plan_name": "Premium Monthly",
            "current_period_end": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "cancel_at_period_end": False,
            "amount": 19.99,
            "currency": "usd",
            "features": SUBSCRIPTION_PLANS["premium_monthly"]["features"]
        }
        
        return subscription
        
    except Exception as e:
        logger.error(f"Error getting subscription: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving subscription")

@app.post("/subscriptions/cancel", tags=["Subscriptions"])
async def cancel_subscription(
    current_user: Dict = Depends(get_current_user)
):
    """Cancel subscription at period end"""
    try:
        user_id = current_user.get("user_id", str(current_user.get("sub", "unknown")))
        
        # In production, get subscription ID from database
        subscription_id = "sub_mock_123"
        
        # Update subscription to cancel at period end
        # In production, use actual Stripe call
        # stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
        
        return {
            "cancelled": True,
            "message": "Your subscription will be cancelled at the end of the current billing period."
        }
        
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        raise HTTPException(status_code=500, detail="Error cancelling subscription")

@app.get("/packages", tags=["Time Cards"])
async def get_time_card_packages():
    """Get available time card packages"""
    return {
        "packages": [
            {
                "id": package_id,
                "name": package["name"],
                "hours": package["hours"],
                "price_cents": package["price_cents"],
                "price_display": f"${package['price_cents'] / 100:.2f}",
                "bonus_minutes": package["bonus_minutes"],
                "total_minutes": (package["hours"] * 60) + package["bonus_minutes"],
                "total_hours": round(((package["hours"] * 60) + package["bonus_minutes"]) / 60, 1),
                "description": package["description"]
            }
            for package_id, package in TIME_CARD_PACKAGES.items()
        ]
    }

@app.post("/time-cards/purchase", tags=["Time Cards"])
async def purchase_time_card(
    purchase_request: TimeCardPurchaseRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Purchase a time card package"""
    try:
        user_id = current_user.get("user_id", str(current_user.get("sub", "unknown")))
        user_email = current_user.get("email", "unknown@example.com")
        
        # Validate package
        package = TIME_CARD_PACKAGES.get(purchase_request.package_id)
        if not package:
            raise HTTPException(status_code=400, detail="Invalid package ID")
        
        # Apply coupon if provided
        discount_percent = 0
        if purchase_request.coupon_code:
            coupon = COUPON_CODES.get(purchase_request.coupon_code.upper())
            if coupon and datetime.strptime(coupon["valid_until"], "%Y-%m-%d") > datetime.utcnow():
                if "min_amount" in coupon and package["price_cents"] < coupon["min_amount"]:
                    raise HTTPException(status_code=400, detail=f"Coupon requires minimum purchase of ${coupon['min_amount']/100:.2f}")
                discount_percent = coupon["percent_off"]
        
        # Calculate final price
        final_price = package["price_cents"]
        if discount_percent > 0:
            final_price = int(final_price * (1 - discount_percent / 100))
        
        # Get or create customer
        customer = await _get_or_create_customer(user_id, user_email)
        
        # Create payment intent
        payment_intent_params = {
            'amount': final_price,
            'currency': 'usd',
            'customer': customer,
            'metadata': {
                'user_id': user_id,
                'user_email': user_email,
                'package_id': purchase_request.package_id,
                'package_name': package["name"],
                'hours': str(package["hours"]),
                'bonus_minutes': str(package["bonus_minutes"]),
                'discount_percent': str(discount_percent),
                'mindbot_service': 'time_card_purchase'
            },
            'description': f"MindBot {package['name']} - {package['hours']} hours of AI conversation time",
            'receipt_email': user_email
        }
        
        # Add setup for future payments if requested
        if purchase_request.save_payment_method:
            payment_intent_params['setup_future_usage'] = 'on_session'
        
        # In production, use actual Stripe call
        # payment_intent = stripe.PaymentIntent.create(**payment_intent_params)
        
        # Mock payment intent for testing
        payment_intent = type('MockPaymentIntent', (), {
            'id': f"pi_mock_{datetime.utcnow().timestamp()}",
            'client_secret': f"pi_mock_secret_{datetime.utcnow().timestamp()}",
            'amount': final_price
        })()
        
        # Create pending time card in database
        total_minutes = (package["hours"] * 60) + package["bonus_minutes"]
        
        try:
            time_card = await supabase_client.create_time_card(
                user_id=user_id,
                package_id=purchase_request.package_id,
                stripe_payment_intent_id=payment_intent.id
            )
        except:
            # Mock time card for testing
            import uuid
            time_card = type('MockTimeCard', (), {
                'id': str(uuid.uuid4()),
                'activation_code': f"TEST-CARD-{uuid.uuid4().hex[:8].upper()}",
                'total_minutes': total_minutes,
                'remaining_minutes': total_minutes,
                'expires_at': datetime.utcnow() + timedelta(days=365)
            })()
        
        logger.info(f"Created time card purchase for user {user_id}: {package['name']}")
        
        return {
            "payment_intent_id": payment_intent.id,
            "client_secret": payment_intent.client_secret,
            "amount": final_price,
            "amount_display": f"${final_price / 100:.2f}",
            "original_price": package["price_cents"],
            "original_price_display": f"${package['price_cents'] / 100:.2f}",
            "discount_percent": discount_percent,
            "discount_amount": package["price_cents"] - final_price,
            "discount_display": f"${(package['price_cents'] - final_price) / 100:.2f}",
            "package": {
                "name": package["name"],
                "hours": package["hours"],
                "bonus_minutes": package["bonus_minutes"],
                "total_minutes": total_minutes,
                "total_hours": round(total_minutes / 60, 1)
            },
            "time_card": {
                "id": time_card.id,
                "activation_code": time_card.activation_code,
                "total_minutes": time_card.total_minutes,
                "expires_at": time_card.expires_at.isoformat() if hasattr(time_card, 'expires_at') else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing time card purchase: {e}")
        raise HTTPException(status_code=500, detail="Error processing purchase")

@app.post("/webhooks/stripe", tags=["Webhooks"])
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Stripe webhook events"""
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        
        if not sig_header:
            raise HTTPException(status_code=400, detail="Missing Stripe signature")
        
        # Process webhook in background to return quickly
        background_tasks.add_task(_process_stripe_webhook, payload, sig_header)
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/ads/view", tags=["Ads"])
async def record_ad_view(
    ad_view: AdViewRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Record ad view and grant rewards"""
    try:
        user_id = current_user.get("user_id", str(current_user.get("sub", "unknown")))
        
        # Validate minimum viewing time for reward
        ad_type = ad_view.ad_id.split("_")[0] if "_" in ad_view.ad_id else "banner"
        ad_config = AD_CONFIG["ad_types"].get(ad_type, AD_CONFIG["ad_types"]["banner"])
        
        minimum_view_time = ad_config["display_time"] * 0.75  # 75% of required time
        
        rewards = {}
        
        if ad_view.view_duration >= minimum_view_time:
            # Calculate revenue
            revenue = ad_config["revenue_per_view"]
            
            if ad_view.completion and "revenue_per_completion" in ad_config:
                revenue += ad_config["revenue_per_completion"]
            
            if ad_view.interaction and "revenue_per_interaction" in ad_config:
                revenue += ad_config["revenue_per_interaction"]
            
            # Track revenue
            await _track_ad_revenue(user_id, ad_view.ad_id, revenue)
            
            # Grant rewards
            if ad_type == "video" and ad_view.completion:
                # Grant time reward
                time_reward = AD_CONFIG["reward_options"]["watch_ad_for_time"]["time_reward"]
                rewards["time_reward"] = time_reward
                rewards["message"] = f"You earned {time_reward} free minutes for watching the ad!"
            else:
                # Grant discount
                discount = AD_CONFIG["reward_options"]["watch_ad_for_discount"]["discount_percent"]
                rewards["discount_percent"] = discount
                rewards["message"] = f"You earned a {discount}% discount on your next session!"
            
            logger.info(f"User {user_id} earned rewards for watching ad {ad_view.ad_id}")
            
            return {
                "success": True,
                "rewards": rewards,
                "message": rewards["message"]
            }
        else:
            return {
                "success": False,
                "message": f"Please watch at least {minimum_view_time} seconds of the ad to earn rewards."
            }
            
    except Exception as e:
        logger.error(f"Error recording ad view: {e}")
        raise HTTPException(status_code=500, detail="Error processing ad view")

@app.get("/ads/config", tags=["Ads"])
async def get_ad_configuration(
    current_user: Dict = Depends(get_current_user)
):
    """Get ad configuration for user"""
    try:
        user_id = current_user.get("user_id", str(current_user.get("sub", "unknown")))
        
        # In production, check user's subscription status
        is_premium = False
        
        if is_premium:
            return {
                "ads_enabled": False,
                "message": "You're a premium user - enjoy an ad-free experience!"
            }
        
        return {
            "ads_enabled": True,
            "ad_types": list(AD_CONFIG["ad_types"].keys()),
            "reward_options": AD_CONFIG["reward_options"],
            "message": "Watch ads to earn free minutes or discounts!"
        }
        
    except Exception as e:
        logger.error(f"Error getting ad configuration: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving ad configuration")

@app.get("/coupons/validate/{code}", tags=["Coupons"])
async def validate_coupon(
    code: str,
    amount: Optional[int] = None,
    current_user: Dict = Depends(get_current_user)
):
    """Validate a coupon code"""
    try:
        coupon = COUPON_CODES.get(code.upper())
        
        if not coupon:
            return {
                "valid": False,
                "message": "Invalid coupon code"
            }
        
        # Check expiration
        if datetime.strptime(coupon["valid_until"], "%Y-%m-%d") <= datetime.utcnow():
            return {
                "valid": False,
                "message": "Coupon has expired"
            }
        
        # Check minimum amount if applicable
        if "min_amount" in coupon and amount and amount < coupon["min_amount"]:
            return {
                "valid": False,
                "message": f"Coupon requires minimum purchase of ${coupon['min_amount']/100:.2f}"
            }
        
        return {
            "valid": True,
            "percent_off": coupon["percent_off"],
            "description": coupon["description"],
            "valid_until": coupon["valid_until"],
            "message": f"Coupon applied: {coupon['percent_off']}% off!"
        }
        
    except Exception as e:
        logger.error(f"Error validating coupon: {e}")
        raise HTTPException(status_code=500, detail="Error validating coupon")

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "mindbot-monetization",
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "subscriptions": True,
            "time_cards": True,
            "ads": True,
            "coupons": True
        }
    }

# Helper functions

async def _get_or_create_customer(user_id: str, email: str) -> str:
    """Get existing Stripe customer or create new one"""
    try:
        # In production, check database for existing customer ID
        
        # Mock customer ID for testing
        return f"cus_mock_{user_id}"
        
    except Exception as e:
        logger.error(f"Error managing customer: {e}")
        raise Exception(f"Customer management error: {str(e)}")

async def _process_stripe_webhook(payload: bytes, sig_header: str):
    """Process Stripe webhook event"""
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        
        event_type = event['type']
        event_data = event['data']['object']
        
        logger.info(f"Processing Stripe webhook: {event_type}")
        
        if event_type == 'payment_intent.succeeded':
            await _handle_payment_success(event_data)
        elif event_type == 'payment_intent.payment_failed':
            await _handle_payment_failed(event_data)
        elif event_type == 'customer.subscription.created':
            await _handle_subscription_created(event_data)
        elif event_type == 'customer.subscription.updated':
            await _handle_subscription_updated(event_data)
        elif event_type == 'customer.subscription.deleted':
            await _handle_subscription_deleted(event_data)
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")
        
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid webhook signature")
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")

async def _handle_payment_success(payment_intent):
    """Handle successful payment"""
    try:
        payment_intent_id = payment_intent['id']
        user_id = payment_intent['metadata'].get('user_id')
        
        if not user_id:
            logger.error(f"No user_id in payment intent {payment_intent_id}")
            return
        
        # Check if this is a time card purchase
        if payment_intent['metadata'].get('mindbot_service') == 'time_card_purchase':
            # Activate time card
            try:
                activated = await supabase_client.activate_time_card(payment_intent_id)
                
                if not activated:
                    logger.error(f"Failed to activate time card for payment {payment_intent_id}")
                    return
                
                # Record payment in history
                await supabase_client.record_payment(
                    user_id=user_id,
                    stripe_payment_intent_id=payment_intent_id,
                    amount_cents=payment_intent['amount'],
                    status='succeeded'
                )
                
                logger.info(f"Successfully processed time card payment {payment_intent_id} for user {user_id}")
            except Exception as e:
                logger.error(f"Error activating time card: {e}")
        
    except Exception as e:
        logger.error(f"Error handling payment success: {e}")

async def _handle_payment_failed(payment_intent):
    """Handle failed payment"""
    try:
        payment_intent_id = payment_intent['id']
        user_id = payment_intent['metadata'].get('user_id')
        
        if user_id:
            # Record failed payment
            try:
                await supabase_client.record_payment(
                    user_id=user_id,
                    stripe_payment_intent_id=payment_intent_id,
                    amount_cents=payment_intent['amount'],
                    status='failed'
                )
            except Exception as e:
                logger.error(f"Error recording failed payment: {e}")
        
        logger.warning(f"Payment failed for {payment_intent_id}")
        
    except Exception as e:
        logger.error(f"Error handling payment failure: {e}")

async def _handle_subscription_created(subscription):
    """Handle subscription creation"""
    try:
        subscription_id = subscription['id']
        customer_id = subscription['customer']
        
        # In production, update user's subscription status in database
        logger.info(f"Subscription {subscription_id} created for customer {customer_id}")
        
    except Exception as e:
        logger.error(f"Error handling subscription creation: {e}")

async def _handle_subscription_updated(subscription):
    """Handle subscription update"""
    try:
        subscription_id = subscription['id']
        status = subscription['status']
        
        # In production, update user's subscription status in database
        logger.info(f"Subscription {subscription_id} updated: {status}")
        
    except Exception as e:
        logger.error(f"Error handling subscription update: {e}")

async def _handle_subscription_deleted(subscription):
    """Handle subscription cancellation"""
    try:
        subscription_id = subscription['id']
        
        # In production, update user's subscription status in database
        logger.info(f"Subscription {subscription_id} cancelled")
        
    except Exception as e:
        logger.error(f"Error handling subscription cancellation: {e}")

async def _track_ad_revenue(user_id: str, ad_id: str, amount: float):
    """Track ad revenue"""
    try:
        # In production, store in database
        logger.info(f"Ad revenue: ${amount:.2f} from user {user_id} for ad {ad_id}")
    except Exception as e:
        logger.error(f"Error tracking ad revenue: {e}")

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting MindBot Monetization Service...")
    
    uvicorn.run(
        "monetization_service:app",
        host="0.0.0.0",
        port=8005,
        reload=True,
        log_level="info"
    )