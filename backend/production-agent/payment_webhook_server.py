"""
FastAPI server for handling Stripe webhooks and payment management
Runs alongside the voice agent to process payments and activate time cards
"""

import os
import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from stripe_manager import stripe_manager
from supabase_client import supabase_client

# Configure logging
logger = logging.getLogger("mindbot.webhook")

# FastAPI app
app = FastAPI(
    title="MindBot Payment Webhook Server",
    description="Handles Stripe webhooks and payment processing for MindBot",
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


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Stripe webhook events"""
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        
        if not sig_header:
            raise HTTPException(status_code=400, detail="Missing Stripe signature")
        
        # Process webhook in background to return quickly
        background_tasks.add_task(process_stripe_webhook, payload, sig_header)
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))


async def process_stripe_webhook(payload: bytes, sig_header: str):
    """Process Stripe webhook in background"""
    try:
        result = await stripe_manager.handle_webhook(payload, sig_header)
        logger.info(f"Webhook processed: {result}")
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")


@app.get("/pricing")
async def get_pricing_tiers():
    """Get available pricing tiers for frontend"""
    try:
        tiers = await supabase_client.get_pricing_tiers()
        
        return {
            "pricing_tiers": [
                {
                    "id": tier.id,
                    "name": tier.name,
                    "hours": tier.hours,
                    "price_cents": tier.price_cents,
                    "price_display": f"${tier.price_cents / 100:.2f}",
                    "bonus_minutes": tier.bonus_minutes,
                    "total_minutes": (tier.hours * 60) + tier.bonus_minutes,
                    "total_hours": round(((tier.hours * 60) + tier.bonus_minutes) / 60, 1),
                    "description": tier.description
                } for tier in tiers
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting pricing tiers: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving pricing")


@app.post("/create-payment-intent")
async def create_payment_intent(request: Request):
    """Create Stripe payment intent for time card purchase"""
    try:
        data = await request.json()
        
        user_id = data.get("user_id")
        package_id = data.get("package_id")
        user_email = data.get("user_email")
        save_payment_method = data.get("save_payment_method", False)
        
        if not all([user_id, package_id, user_email]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Create payment intent
        payment_data = await stripe_manager.create_payment_intent(
            user_id=user_id,
            package_id=package_id,
            user_email=user_email,
            save_payment_method=save_payment_method
        )
        
        return payment_data
        
    except Exception as e:
        logger.error(f"Error creating payment intent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/user/{user_id}/balance")
async def get_user_balance(user_id: str):
    """Get user's time balance"""
    try:
        balance = await supabase_client.get_user_time_balance(user_id)
        return balance
        
    except Exception as e:
        logger.error(f"Error getting user balance: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving balance")


@app.get("/user/{user_id}/analytics")
async def get_user_analytics(user_id: str):
    """Get user analytics"""
    try:
        analytics = await supabase_client.get_user_analytics(user_id)
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting user analytics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving analytics")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "mindbot-payment-webhook",
        "timestamp": "2024-01-01T00:00:00Z"
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MindBot Payment Webhook Server",
        "version": "1.0.0",
        "endpoints": {
            "stripe_webhook": "/webhooks/stripe",
            "pricing": "/pricing",
            "create_payment": "/create-payment-intent",
            "user_balance": "/user/{user_id}/balance",
            "user_analytics": "/user/{user_id}/analytics",
            "health": "/health"
        }
    }


if __name__ == "__main__":
    logger.info("Starting MindBot Payment Webhook Server...")
    
    # Validate required environment variables
    required_vars = ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "SUPABASE_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        exit(1)
    
    uvicorn.run(
        "payment_webhook_server:app",
        host="0.0.0.0",
        port=8003,
        reload=False,  # Set to False in production
        log_level="info"
    )