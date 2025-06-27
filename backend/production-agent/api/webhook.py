# api/webhook.py

import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from contextvars import ContextVar

from ..services.stripe_manager import StripeManager
from ..services.supabase_client import SupabaseClient
from ..core.settings import AgentConfig

logger = logging.getLogger("mindbot.webhook")

# Define ContextVars to act as proxies for the global instances
stripe_manager: ContextVar[StripeManager] = ContextVar("stripe_manager")
supabase_client: ContextVar[SupabaseClient] = ContextVar("supabase_client")
config: ContextVar[AgentConfig] = ContextVar("config")

class CreatePaymentIntentRequest(BaseModel):
    """Request model for creating a payment intent."""
    user_id: str = Field(..., description="Unique identifier for the user")
    package_id: str = Field(..., description="ID of the time card package to purchase")
    user_email: EmailStr = Field(..., description="User's email address for Stripe customer creation")
    save_payment_method: bool = Field(False, description="Whether to save the payment method for future use")

app = FastAPI(
    title="MindBot API Server",
    description="Handles Stripe webhooks, payments, and other API requests for MindBot.",
    version="1.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/v1/openapi.json"
)

@app.on_event("startup")
async def startup_event():
    """
    FastAPI startup event.
    Initializes CORS middleware based on the configuration.
    """
    app_config = config.get()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_config.cors_origins,
        allow_credentials=app_config.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("Webhook server startup complete with CORS configured.")

# Dependency to get the StripeManager instance
def get_stripe_manager() -> StripeManager:
    return stripe_manager.get()

# Dependency to get the SupabaseClient instance
def get_supabase_client() -> SupabaseClient:
    return supabase_client.get()

@app.post("/webhooks/stripe", summary="Handle Stripe Webhooks", tags=["Webhooks"])
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    stripe: StripeManager = Depends(get_stripe_manager)
):
    """
    Endpoint to receive and process Stripe webhooks.
    It validates the webhook signature and processes the event in the background.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        logger.warning("Stripe webhook received without signature.")
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    # Offload the actual processing to a background task to respond quickly
    background_tasks.add_task(stripe.handle_webhook, payload, sig_header)
    
    return {"status": "pending"}

@app.get("/pricing", summary="Get Pricing Tiers", tags=["Payments"])
async def get_pricing_tiers(supabase: SupabaseClient = Depends(get_supabase_client)):
    """
    Retrieves the available pricing tiers for time card packages.
    This is used by the frontend to display purchase options.
    """
    try:
        tiers = await supabase.get_pricing_tiers()
        return {
            "pricing_tiers": [tier.dict() for tier in tiers]
        }
    except Exception as e:
        logger.error(f"Failed to retrieve pricing tiers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve pricing information.")

@app.post("/create-payment-intent", summary="Create Payment Intent", tags=["Payments"])
async def create_payment_intent(
    request: CreatePaymentIntentRequest,
    stripe: StripeManager = Depends(get_stripe_manager)
):
    """
    Creates a Stripe Payment Intent for purchasing a time card package.
    This is the first step in the checkout process.
    """
    try:
        payment_data = await stripe.create_payment_intent(
            user_id=request.user_id,
            package_id=request.package_id,
            user_email=request.user_email,
            save_payment_method=request.save_payment_method
        )
        return payment_data
    except ValueError as e:
        logger.warning(f"Invalid request for payment intent: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create payment intent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not process payment.")

@app.get("/user/{user_id}/balance", summary="Get User Time Balance", tags=["User"])
async def get_user_balance(user_id: str, supabase: SupabaseClient = Depends(get_supabase_client)):
    """
    Retrieves the current time balance for a specific user.
    """
    try:
        balance = await supabase.get_user_time_balance(user_id)
        return balance
    except Exception as e:
        logger.error(f"Failed to get balance for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve user balance.")

@app.get("/user/{user_id}/analytics", summary="Get User Analytics", tags=["User"])
async def get_user_analytics(user_id: str, supabase: SupabaseClient = Depends(get_supabase_client)):
    """
    Retrieves comprehensive analytics for a specific user.
    """
    try:
        analytics = await supabase.get_user_analytics(user_id)
        if not analytics:
            raise HTTPException(status_code=404, detail="User not found.")
        return analytics
    except Exception as e:
        logger.error(f"Failed to get analytics for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve user analytics.")

@app.get("/health", summary="Health Check", tags=["System"])
async def health_check():
    """
    A simple health check endpoint to verify that the API server is running.
    """
    return {
        "status": "healthy",
        "service": "mindbot-api-server",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/", summary="API Root", tags=["System"])
async def root():
    """
    Root endpoint providing basic information about the API.
    """
    return {
        "message": "Welcome to the MindBot API Server",
        "version": app.version,
        "docs": app.docs_url,
        "redoc": app.redoc_url
    }
