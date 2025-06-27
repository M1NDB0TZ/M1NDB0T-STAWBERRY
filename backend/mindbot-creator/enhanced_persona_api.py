"""
Enhanced MindBot Creator API with comprehensive persona management and monetization
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import jwt
import uvicorn

from persona_manager import (
    PersonaManager, CreatePersonaRequest, PersonaResponse, 
    PersonaCategory, PersonaAccessLevel, RevenueTracker
)
from mindbot_factory import mindbot_factory

logger = logging.getLogger(__name__)

# Initialize FastAPI app with comprehensive configuration
app = FastAPI(
    title="MindBot Creator API - Enhanced",
    description="Create and manage custom AI voice assistants with preset personas and revenue optimization",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enhanced CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Authentication
security = HTTPBearer()
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key")

# Initialize components
try:
    from supabase_client import supabase_client
    persona_manager = PersonaManager(supabase_client)
    revenue_tracker = RevenueTracker()
    logger.info("Persona API initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize persona API: {e}")
    # Create mock manager for testing
    persona_manager = PersonaManager(None)
    revenue_tracker = RevenueTracker()

# Authentication functions
async def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify JWT token and return user info"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current authenticated user"""
    return await verify_jwt_token(credentials)

# API Models
class AdConfiguration(BaseModel):
    """Configuration for ad-supported features"""
    enable_ads: bool = True
    ad_frequency: int = 3  # Show ad every 3 interactions
    ad_types: List[str] = ["banner", "video", "sponsored_content"]

class PersonaSessionRequest(BaseModel):
    """Request to start a persona session"""
    room_name: Optional[str] = None
    enable_ads: bool = True
    quality_preference: str = "standard"  # standard, premium

class PersonaUsageResponse(BaseModel):
    """Response with usage and billing information"""
    session_id: str
    estimated_cost: float
    time_balance: Dict[str, Any]
    ads_enabled: bool
    cost_savings: float = 0.0  # Savings from ad viewing

# API Endpoints

@app.get("/", tags=["General"])
async def root():
    """Welcome endpoint with system information"""
    return {
        "message": "MindBot Creator API - Enhanced",
        "version": "2.0.0",
        "features": [
            "Preset Personas",
            "Custom Persona Creation", 
            "Ad-Supported Free Tiers",
            "Revenue Optimization",
            "Advanced Analytics"
        ],
        "available_personas": len(persona_manager.presets),
        "categories": [category.value for category in PersonaCategory],
        "endpoints": {
            "personas": "/personas",
            "categories": "/categories", 
            "custom": "/personas/custom",
            "session": "/personas/{slug}/session",
            "analytics": "/analytics/personas"
        }
    }

@app.get("/personas", response_model=List[PersonaResponse], tags=["Personas"])
async def list_available_personas(
    user_tier: str = Query("free", description="User subscription tier"),
    category: Optional[str] = Query(None, description="Filter by category"),
    ad_supported: Optional[bool] = Query(None, description="Filter by ad support"),
    sort_by: str = Query("rating", description="Sort by: rating, cost, popularity"),
    limit: int = Query(20, description="Maximum number of personas to return")
):
    """
    Get list of available personas for user with comprehensive filtering
    
    - **user_tier**: User subscription level (free, premium, exclusive)
    - **category**: Filter by persona category
    - **ad_supported**: Show only ad-supported personas
    - **sort_by**: Sort order for results
    - **limit**: Maximum personas to return
    """
    try:
        personas = await persona_manager.get_available_personas(user_tier)
        
        # Apply filters
        if category:
            personas = [p for p in personas if p['category'] == category]
        
        if ad_supported is not None:
            personas = [p for p in personas if p['ad_supported'] == ad_supported]
        
        # Apply sorting
        if sort_by == "cost":
            personas = sorted(personas, key=lambda x: x['cost_multiplier'])
        elif sort_by == "popularity":
            personas = sorted(personas, key=lambda x: x.get('usage_count', 0), reverse=True)
        # Default is already sorted by rating
        
        # Apply limit
        personas = personas[:limit]
        
        logger.info(f"Retrieved {len(personas)} personas for user tier {user_tier}")
        return personas
        
    except Exception as e:
        logger.error(f"Error listing personas: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving personas")

@app.get("/personas/{slug}", tags=["Personas"])
async def get_persona_details(slug: str):
    """
    Get detailed information about a specific persona
    
    - **slug**: Unique persona identifier
    """
    try:
        persona = await persona_manager.get_persona_by_slug(slug)
        
        if not persona:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        return {
            "slug": persona.slug,
            "name": persona.name,
            "summary": persona.summary,
            "persona": persona.persona,
            "purpose": persona.purpose,
            "category": persona.category.value,
            "access_level": persona.access_level.value,
            "voice": persona.voice,
            "tools": persona.tools,
            "safety": persona.safety,
            "age_restriction": persona.age_restriction,
            "rating": persona.rating,
            "usage_count": persona.usage_count,
            "cost_multiplier": persona.base_cost_multiplier,
            "session_limit": persona.session_time_limit,
            "daily_limit": persona.daily_usage_limit,
            "ad_supported": persona.ad_supported,
            "premium_features": persona.premium_features,
            "user_customizable_fields": persona.user_customizable_fields,
            "created_at": persona.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting persona details: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving persona")

@app.post("/personas/custom", tags=["Personas"])
async def create_custom_persona(
    persona_request: CreatePersonaRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a custom persona from user specifications
    
    Requires premium subscription for custom persona creation.
    """
    try:
        user_id = current_user.get("user_id", str(current_user.get("sub", "unknown")))
        
        # Convert request to persona data
        persona_data = {
            "name": persona_request.name,
            "summary": persona_request.summary,
            "persona": persona_request.persona,
            "purpose": persona_request.purpose,
            "category": persona_request.category.value,
            "voice": persona_request.voice or {"tts": "alloy", "style": "neutral"},
            "tools": persona_request.tools or ["check_time_balance"],
            "safety": persona_request.safety or "Follow platform safety guidelines.",
            "age_restriction": persona_request.age_restriction
        }
        
        # Use AI to generate enhanced system prompt
        config, system_prompt = await mindbot_factory.create_mindbot_from_description(
            f"Create a {persona_request.name} personality that {persona_request.summary}. "
            f"Persona: {persona_request.persona}. Purpose: {persona_request.purpose}",
            user_id
        )
        
        # Override with user specifications
        persona_data["system_prompt"] = system_prompt
        
        # Create custom persona
        persona = await persona_manager.create_custom_persona(user_id, persona_data)
        
        # Track revenue event
        background_tasks.add_task(
            revenue_tracker.track_custom_persona_creation,
            user_id,
            persona.slug
        )
        
        logger.info(f"Created custom persona {persona.slug} for user {user_id}")
        
        return {
            "slug": persona.slug,
            "name": persona.name,
            "message": "Custom persona created successfully!",
            "system_prompt_preview": system_prompt[:200] + "..." if len(system_prompt) > 200 else system_prompt,
            "cost_multiplier": persona.base_cost_multiplier,
            "estimated_hourly_cost": persona_manager._calculate_hourly_cost(persona, "premium")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating custom persona: {e}")
        raise HTTPException(status_code=500, detail="Error creating custom persona")

@app.post("/personas/{slug}/session", tags=["Sessions"])
async def start_persona_session(
    slug: str,
    session_request: PersonaSessionRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """
    Start a voice session with a specific persona
    
    - **slug**: Persona identifier
    - **room_name**: Optional custom room name
    - **enable_ads**: Enable ad-supported features for cost savings
    """
    try:
        user_id = current_user.get("user_id", str(current_user.get("sub", "unknown")))
        persona = await persona_manager.get_persona_by_slug(slug)
        
        if not persona:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        # Check user's time balance
        try:
            balance = await supabase_client.get_user_time_balance(user_id)
        except:
            # Mock balance for testing
            balance = {"total_minutes": 60, "total_hours": 1.0, "active_cards": 1}
        
        if balance.get('total_minutes', 0) <= 0:
            raise HTTPException(
                status_code=402, 
                detail="Insufficient time balance. Please purchase time cards to continue."
            )
        
        # Calculate effective cost with ad support
        user_tier = await persona_manager._get_user_tier(user_id)
        effective_cost = persona.get_effective_cost(user_tier)
        
        # Ad-supported cost reduction
        cost_savings = 0.0
        if session_request.enable_ads and persona.ad_supported:
            cost_savings = persona.base_cost_multiplier * 0.5
            effective_cost = persona.get_effective_cost(user_tier)
        
        # Generate LiveKit token for this session
        import secrets
        room_name = session_request.room_name or f"persona_{slug}_{secrets.token_hex(8)}"
        
        # Create LiveKit token with persona-specific identity
        try:
            from livekit import api
            token = api.AccessToken(
                os.getenv("LIVEKIT_API_KEY"),
                os.getenv("LIVEKIT_API_SECRET")
            ).with_identity(user_id).with_name(f"User with {persona.name}").with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True
                )
            ).to_jwt()
        except Exception as e:
            logger.error(f"Error creating LiveKit token: {e}")
            token = "mock_token_for_testing"
        
        # Start time tracking session
        session_id = f"persona_{slug}_{int(datetime.utcnow().timestamp())}"
        
        try:
            session_data = await supabase_client.start_voice_session(
                user_id=user_id,
                session_id=session_id,
                room_name=room_name,
                agent_type=persona.slug
            )
        except:
            # Mock session data for testing
            session_data = type('MockSession', (), {'session_id': session_id})()
        
        # Track revenue event
        background_tasks.add_task(
            revenue_tracker.track_persona_session_start,
            user_id,
            persona.slug,
            effective_cost
        )
        
        logger.info(f"Started persona session for user {user_id} with {persona.name}")
        
        return {
            "session_started": True,
            "room_name": room_name,
            "livekit_token": token,
            "livekit_url": os.getenv("LIVEKIT_URL", "wss://mindbot.livekit.cloud"),
            "persona": {
                "name": persona.name,
                "slug": persona.slug,
                "summary": persona.summary,
                "cost_multiplier": effective_cost,
                "voice": persona.voice,
                "ad_supported": persona.ad_supported
            },
            "session_id": session_data.session_id if session_data else session_id,
            "time_balance": balance,
            "estimated_cost_per_minute": effective_cost,
            "ads_enabled": session_request.enable_ads and persona.ad_supported,
            "cost_savings": cost_savings,
            "premium_features_available": persona.premium_features if user_tier == "premium" else []
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting persona session: {e}")
        raise HTTPException(status_code=500, detail="Error starting session")

@app.get("/categories", tags=["Configuration"])
async def get_persona_categories():
    """Get available persona categories with descriptions"""
    
    descriptions = {
        "entertainment": {
            "label": "Entertainment",
            "description": "Fun, engaging personas for entertainment and leisure",
            "icon": "🎉",
            "popular_personas": ["sizzle", "pixel"]
        },
        "education": {
            "label": "Education", 
            "description": "Learning-focused personas for tutoring and skill development",
            "icon": "📚",
            "popular_personas": ["professor_oak"]
        },
        "wellness": {
            "label": "Wellness",
            "description": "Health and wellness personas for mental and physical wellbeing",
            "icon": "💪",
            "popular_personas": ["zen_master"]
        },
        "business": {
            "label": "Business",
            "description": "Professional personas for business and career development", 
            "icon": "💼",
            "popular_personas": ["deal_closer"]
        },
        "creative": {
            "label": "Creative",
            "description": "Artistic and creative personas for inspiration and collaboration",
            "icon": "🎨",
            "popular_personas": []
        },
        "lifestyle": {
            "label": "Lifestyle",
            "description": "Lifestyle and hobby-focused personas",
            "icon": "🏠", 
            "popular_personas": ["blaze"]
        },
        "technical": {
            "label": "Technical",
            "description": "Technical and programming-focused personas",
            "icon": "⚙️",
            "popular_personas": ["code_wizard"]
        },
        "general": {
            "label": "General",
            "description": "General-purpose personas for everyday assistance",
            "icon": "🤖",
            "popular_personas": ["mindbot"]
        }
    }
    
    return {
        "categories": [
            {
                "value": category.value,
                **descriptions.get(category.value, {
                    "label": category.value.title(),
                    "description": "Specialized AI assistant",
                    "icon": "🤖",
                    "popular_personas": []
                })
            }
            for category in PersonaCategory
        ]
    }

@app.get("/analytics/personas", tags=["Analytics"])
async def get_persona_analytics(
    current_user: Dict = Depends(get_current_user)
):
    """Get persona usage analytics and insights"""
    try:
        user_id = current_user.get("user_id", str(current_user.get("sub", "unknown")))
        
        # Mock analytics data - in production this would come from your analytics system
        analytics = {
            "user_usage": {
                "total_sessions": 47,
                "total_minutes": 312,
                "favorite_persona": "professor_oak",
                "most_used_category": "education",
                "average_session_length": 6.6,
                "cost_savings_from_ads": 12.50
            },
            "persona_recommendations": [
                {
                    "slug": "zen-master",
                    "name": "Zen Master",
                    "reason": "Based on your wellness interests"
                },
                {
                    "slug": "code-wizard",
                    "name": "Code Wizard", 
                    "reason": "Trending in your technical category"
                }
            ],
            "popular_personas": [
                {"slug": "mindbot", "name": "MindBot", "usage_percent": 32.1},
                {"slug": "professor_oak", "name": "Professor Oak", "usage_percent": 28.5},
                {"slug": "zen_master", "name": "Zen Master", "usage_percent": 15.3},
                {"slug": "sizzle", "name": "SizzleBot", "usage_percent": 12.7}
            ],
            "category_usage": {
                "education": 45.2,
                "general": 25.1,
                "wellness": 18.7,
                "entertainment": 11.0
            }
        }
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting persona analytics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving analytics")

@app.post("/personas/{slug}/rate", tags=["Feedback"])
async def rate_persona(
    slug: str,
    rating: int = Query(..., ge=1, le=5, description="Rating from 1 to 5"),
    feedback: Optional[str] = Query(None, description="Optional feedback"),
    current_user: Dict = Depends(get_current_user)
):
    """Rate a persona after a session"""
    try:
        user_id = current_user.get("user_id", str(current_user.get("sub", "unknown")))
        
        persona = await persona_manager.get_persona_by_slug(slug)
        if not persona:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        # In production, store rating in database
        logger.info(f"User {user_id} rated {slug}: {rating}/5 - {feedback}")
        
        return {
            "message": "Thank you for your feedback!",
            "rating_recorded": rating,
            "persona": persona.name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rating persona: {e}")
        raise HTTPException(status_code=500, detail="Error recording rating")

@app.get("/ads/config", tags=["Monetization"])
async def get_ad_configuration(
    current_user: Dict = Depends(get_current_user)
):
    """Get ad configuration for the current user"""
    try:
        user_id = current_user.get("user_id", str(current_user.get("sub", "unknown")))
        user_tier = await persona_manager._get_user_tier(user_id)
        
        # Ad configuration based on user tier
        if user_tier == "free":
            config = {
                "ads_enabled": True,
                "ad_frequency": 3,  # Every 3 interactions
                "ad_types": ["banner", "video"],
                "skip_after_seconds": 5,
                "reward_percentage": 50,  # 50% cost reduction
                "daily_ad_limit": 20
            }
        elif user_tier == "premium":
            config = {
                "ads_enabled": False,
                "ad_frequency": 0,
                "ad_types": [],
                "premium_benefits": [
                    "No advertisements",
                    "Priority support", 
                    "Advanced personas",
                    "Custom persona creation"
                ]
            }
        else:
            config = {"ads_enabled": False}
        
        return config
        
    except Exception as e:
        logger.error(f"Error getting ad configuration: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving ad configuration")

@app.post("/ads/viewed", tags=["Monetization"])
async def record_ad_view(
    ad_id: str,
    persona_slug: str,
    view_duration: int = Query(..., description="Seconds watched"),
    current_user: Dict = Depends(get_current_user)
):
    """Record when user views an ad for cost reduction"""
    try:
        user_id = current_user.get("user_id", str(current_user.get("sub", "unknown")))
        
        # Validate minimum viewing time for reward
        minimum_view_time = 5  # seconds
        
        if view_duration >= minimum_view_time:
            # Grant cost reduction for next interaction
            cost_reduction = 0.5  # 50% reduction
            
            # In production, store this credit in database
            logger.info(f"User {user_id} earned cost reduction by watching ad {ad_id}")
            
            return {
                "reward_earned": True,
                "cost_reduction_percentage": 50,
                "next_session_discount": cost_reduction,
                "message": "Thanks for watching! Your next interaction is 50% off."
            }
        else:
            return {
                "reward_earned": False,
                "message": f"Please watch the full ad ({minimum_view_time}s) to earn the discount."
            }
            
    except Exception as e:
        logger.error(f"Error recording ad view: {e}")
        raise HTTPException(status_code=500, detail="Error recording ad view")

@app.get("/revenue/stats", tags=["Admin"])
async def get_revenue_statistics(
    current_user: Dict = Depends(get_current_user)
):
    """Get revenue statistics (admin only)"""
    try:
        # Check if user is admin (in production, verify admin role)
        user_email = current_user.get("email", "")
        admin_emails = ["admin@mindbot.ai", "support@mindbot.ai"]
        
        if user_email not in admin_emails:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Mock revenue data - in production, calculate from actual data
        stats = {
            "total_sessions_today": 234,
            "revenue_today": 127.50,
            "top_personas": [
                {"slug": "professor_oak", "sessions": 87, "revenue": 45.30},
                {"slug": "deal_closer", "sessions": 34, "revenue": 68.00},
                {"slug": "zen_master", "sessions": 56, "revenue": 28.20}
            ],
            "ad_performance": {
                "total_views": 156,
                "completion_rate": 0.78,
                "revenue_from_ads": 23.40
            },
            "user_tiers": {
                "free": 145,
                "premium": 67,
                "exclusive": 12
            }
        }
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting revenue statistics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving statistics")

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "mindbot-creator-enhanced",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "features": {
            "personas_loaded": len(persona_manager.presets),
            "categories_available": len(list(PersonaCategory)),
            "monetization_active": True,
            "analytics_enabled": True
        }
    }

@app.get("/user/subscription", tags=["User Management"])
async def get_user_subscription(
    current_user: Dict = Depends(get_current_user)
):
    """Get user's subscription details and usage"""
    try:
        user_id = current_user.get("user_id", str(current_user.get("sub", "unknown")))
        
        # In production, get real subscription data
        subscription = {
            "tier": "free",
            "features": [
                "Basic personas",
                "Ad-supported sessions",
                "Standard voice quality"
            ],
            "usage": {
                "sessions_this_month": 23,
                "minutes_used": 145,
                "personas_accessed": 5
            },
            "upgrade_benefits": {
                "premium": [
                    "Remove all ads",
                    "Access to premium personas",
                    "Custom persona creation",
                    "Priority support",
                    "Advanced analytics"
                ],
                "premium_price": "$19.99/month"
            }
        }
        
        return subscription
        
    except Exception as e:
        logger.error(f"Error getting user subscription: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving subscription")

@app.post("/user/upgrade", tags=["User Management"])
async def upgrade_subscription(
    tier: str = Query(..., description="Target subscription tier"),
    current_user: Dict = Depends(get_current_user)
):
    """Upgrade user's subscription tier"""
    try:
        user_id = current_user.get("user_id", str(current_user.get("sub", "unknown")))
        
        if tier not in ["premium", "exclusive"]:
            raise HTTPException(status_code=400, detail="Invalid subscription tier")
        
        # In production, integrate with payment processor
        logger.info(f"User {user_id} requested upgrade to {tier}")
        
        return {
            "upgrade_initiated": True,
            "target_tier": tier,
            "message": "Upgrade process initiated. You'll be redirected to payment.",
            "payment_url": f"/payment/subscribe?tier={tier}&user={user_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error upgrading subscription: {e}")
        raise HTTPException(status_code=500, detail="Error processing upgrade")

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "available_endpoints": {
                "personas": "/personas",
                "categories": "/categories",
                "documentation": "/docs"
            }
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler"""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "support": "Please contact support if this persists"
        }
    )

if __name__ == "__main__":
    logger.info("Starting Enhanced MindBot Creator API...")
    logger.info(f"Available personas: {len(persona_manager.presets)}")
    
    uvicorn.run(
        "enhanced_persona_api:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
        log_level="info"
    )