"""
Enhanced MindBot Creator API with preset persona management
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import logging

from persona_manager import PersonaManager, CreatePersonaRequest, PersonaResponse
from mindbot_factory import mindbot_factory
from supabase_client import supabase_client

logger = logging.getLogger(__name__)

app = FastAPI(
    title="MindBot Creator API - Enhanced",
    description="Create and manage custom AI voice assistants with preset personas",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize persona manager
persona_manager = PersonaManager(supabase_client)

@app.get("/personas", response_model=List[PersonaResponse])
async def list_available_personas(
    user_access_level: str = "free",
    category: Optional[str] = None
):
    """Get list of available personas for user"""
    try:
        personas = await persona_manager.get_available_personas(user_access_level)
        
        if category:
            personas = [p for p in personas if p['category'] == category]
        
        return personas
        
    except Exception as e:
        logger.error(f"Error listing personas: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving personas")

@app.get("/personas/{slug}")
async def get_persona_details(slug: str):
    """Get detailed information about a specific persona"""
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
            "daily_limit": persona.daily_usage_limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting persona details: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving persona")

@app.post("/personas/custom")
async def create_custom_persona(
    persona_request: CreatePersonaRequest,
    user_id: str,  # Would come from JWT token in real implementation
    background_tasks: BackgroundTasks
):
    """Create a custom persona from user specifications"""
    try:
        # Convert request to persona data
        persona_data = {
            "name": persona_request.name,
            "summary": persona_request.summary,
            "persona": persona_request.persona,
            "purpose": persona_request.purpose,
            "category": persona_request.category.value,
            "voice": persona_request.voice or {"tts": "openai_en_us_002", "style": "neutral"},
            "tools": persona_request.tools or ["check_time_balance"],
            "safety": persona_request.safety or "Follow platform safety guidelines.",
            "age_restriction": persona_request.age_restriction
        }
        
        # Use the AI to generate enhanced system prompt
        config, system_prompt = await mindbot_factory.create_mindbot_from_description(
            f"Create a {persona_request.name} personality that {persona_request.summary}. "
            f"Persona: {persona_request.persona}. Purpose: {persona_request.purpose}",
            user_id
        )
        
        # Override with user specifications
        persona_data["system_prompt"] = system_prompt
        
        # Create custom persona
        persona = await persona_manager.create_custom_persona(user_id, persona_data)
        
        logger.info(f"Created custom persona {persona.slug} for user {user_id}")
        
        return {
            "slug": persona.slug,
            "name": persona.name,
            "message": "Custom persona created successfully!",
            "system_prompt": system_prompt[:200] + "..." if len(system_prompt) > 200 else system_prompt
        }
        
    except Exception as e:
        logger.error(f"Error creating custom persona: {e}")
        raise HTTPException(status_code=500, detail="Error creating custom persona")

@app.post("/personas/{slug}/session")
async def start_persona_session(
    slug: str,
    user_id: str,  # Would come from JWT token
    room_name: Optional[str] = None
):
    """Start a voice session with a specific persona"""
    try:
        persona = await persona_manager.get_persona_by_slug(slug)
        
        if not persona:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        # Check user's time balance
        balance = await supabase_client.get_user_time_balance(user_id)
        
        if balance['total_minutes'] <= 0:
            raise HTTPException(
                status_code=402, 
                detail="Insufficient time balance. Please purchase time cards to continue."
            )
        
        # Check session limits
        if persona.session_time_limit and balance['total_minutes'] < persona.session_time_limit:
            logger.warning(f"User {user_id} may not have enough time for full session with {slug}")
        
        # Generate LiveKit token for this session
        from livekit import api
        import secrets
        
        if not room_name:
            room_name = f"persona_{slug}_{secrets.token_hex(8)}"
        
        # Create LiveKit token with persona-specific identity
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
        
        # Start time tracking session
        session_data = await supabase_client.start_voice_session(
            user_id=user_id,
            session_id=f"persona_{slug}_{int(datetime.utcnow().timestamp())}",
            room_name=room_name,
            agent_type=persona.slug
        )
        
        logger.info(f"Started persona session for user {user_id} with {persona.name}")
        
        return {
            "session_started": True,
            "room_name": room_name,
            "livekit_token": token,
            "livekit_url": os.getenv("LIVEKIT_URL"),
            "persona": {
                "name": persona.name,
                "slug": persona.slug,
                "summary": persona.summary,
                "cost_multiplier": persona.base_cost_multiplier
            },
            "session_id": session_data.session_id if session_data else None,
            "time_balance": balance,
            "estimated_cost_per_minute": persona.base_cost_multiplier
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting persona session: {e}")
        raise HTTPException(status_code=500, detail="Error starting session")

@app.get("/categories")
async def get_persona_categories():
    """Get available persona categories"""
    from persona_manager import PersonaCategory
    
    return {
        "categories": [
            {
                "value": category.value,
                "label": category.value.replace('_', ' ').title(),
                "description": _get_category_description(category)
            }
            for category in PersonaCategory
        ]
    }

def _get_category_description(category) -> str:
    """Get description for each category"""
    descriptions = {
        PersonaCategory.ENTERTAINMENT: "Fun, engaging personas for entertainment and leisure",
        PersonaCategory.EDUCATION: "Learning-focused personas for tutoring and skill development",
        PersonaCategory.WELLNESS: "Health and wellness personas for mental and physical wellbeing",
        PersonaCategory.BUSINESS: "Professional personas for business and career development",
        PersonaCategory.CREATIVE: "Artistic and creative personas for inspiration and collaboration",
        PersonaCategory.LIFESTYLE: "Lifestyle and hobby-focused personas",
        PersonaCategory.TECHNICAL: "Technical and programming-focused personas",
        PersonaCategory.GENERAL: "General-purpose personas for everyday assistance"
    }
    return descriptions.get(category, "Specialized AI assistant")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "mindbot-creator-enhanced",
        "available_personas": len(persona_manager.presets),
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)