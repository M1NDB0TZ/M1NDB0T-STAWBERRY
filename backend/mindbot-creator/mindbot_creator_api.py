"""
MindBot Creator API - REST API for creating and managing custom MindBots
Integrates with the main payment system and Supabase
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

from mindbot_factory import mindbot_factory, MindBotConfig
from supabase_client import supabase_client
import jwt

logger = logging.getLogger(__name__)

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-jwt-secret")
JWT_ALGORITHM = "HS256"

# Pydantic models for API
class MindBotCreationRequest(BaseModel):
    description: str = Field(..., description="Description of the desired AI assistant")
    name: Optional[str] = Field(None, description="Optional custom name for the AI")
    save_config: bool = Field(True, description="Whether to save this configuration")

class MindBotCreationResponse(BaseModel):
    config_id: str
    name: str
    personality_type: str
    primary_purpose: str
    system_prompt: str
    creation_successful: bool
    message: str

class ConversationCreationRequest(BaseModel):
    conversation_history: List[str] = Field(..., description="Conversation about AI requirements")
    save_config: bool = Field(True, description="Whether to save this configuration")

class MindBotListResponse(BaseModel):
    mindbot_configs: List[Dict[str, Any]]
    total_count: int

class MindBotTypeResponse(BaseModel):
    types: Dict[str, str]

# FastAPI app
app = FastAPI(
    title="MindBot Creator API",
    description="Create and manage custom AI voice assistants",
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

async def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify JWT token and return user info"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# API Endpoints

@app.post("/mindbot/create", response_model=MindBotCreationResponse)
async def create_mindbot(
    request: MindBotCreationRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(verify_jwt_token)
):
    """Create a custom MindBot from description"""
    
    try:
        user_id = current_user.get("user_id")
        
        logger.info(f"Creating MindBot for user {user_id}: {request.description}")
        
        # Create the MindBot configuration
        config, system_prompt = await mindbot_factory.create_mindbot_from_description(
            request.description,
            user_id if request.save_config else None
        )
        
        # Override name if provided
        if request.name:
            config.name = request.name
        
        # Generate config ID
        config_id = f"{config.name.lower().replace(' ', '_')}_{int(datetime.utcnow().timestamp())}"
        
        # Store in factory
        mindbot_factory.active_configs[config_id] = config
        mindbot_factory.system_prompts[config_id] = system_prompt
        
        # Save to database if requested
        if request.save_config:
            background_tasks.add_task(
                save_mindbot_to_database,
                config_id,
                config,
                system_prompt,
                user_id
            )
        
        logger.info(f"Successfully created MindBot: {config.name} ({config.personality_type})")
        
        return MindBotCreationResponse(
            config_id=config_id,
            name=config.name,
            personality_type=config.personality_type,
            primary_purpose=config.primary_purpose,
            system_prompt=system_prompt,
            creation_successful=True,
            message=f"Successfully created {config.name}! Your AI is ready to use."
        )
        
    except Exception as e:
        logger.error(f"Error creating MindBot: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating MindBot: {str(e)}")

@app.post("/mindbot/create-from-conversation", response_model=MindBotCreationResponse)
async def create_mindbot_from_conversation(
    request: ConversationCreationRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(verify_jwt_token)
):
    """Create a custom MindBot from a conversation about requirements"""
    
    try:
        user_id = current_user.get("user_id")
        
        logger.info(f"Creating MindBot from conversation for user {user_id}")
        
        # Create the MindBot configuration
        config, system_prompt = await mindbot_factory.create_mindbot_from_conversation(
            request.conversation_history,
            user_id if request.save_config else None
        )
        
        # Generate config ID
        config_id = f"{config.name.lower().replace(' ', '_')}_{int(datetime.utcnow().timestamp())}"
        
        # Store in factory
        mindbot_factory.active_configs[config_id] = config
        mindbot_factory.system_prompts[config_id] = system_prompt
        
        # Save to database if requested
        if request.save_config:
            background_tasks.add_task(
                save_mindbot_to_database,
                config_id,
                config,
                system_prompt,
                user_id
            )
        
        logger.info(f"Successfully created MindBot from conversation: {config.name}")
        
        return MindBotCreationResponse(
            config_id=config_id,
            name=config.name,
            personality_type=config.personality_type,
            primary_purpose=config.primary_purpose,
            system_prompt=system_prompt,
            creation_successful=True,
            message=f"Successfully created {config.name} based on your conversation! Your AI is ready to use."
        )
        
    except Exception as e:
        logger.error(f"Error creating MindBot from conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating MindBot: {str(e)}")

@app.get("/mindbot/types", response_model=MindBotTypeResponse)
async def get_mindbot_types():
    """Get available MindBot types and their descriptions"""
    
    try:
        types = await mindbot_factory.list_available_mindbot_types()
        
        return MindBotTypeResponse(types=types)
        
    except Exception as e:
        logger.error(f"Error getting MindBot types: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving MindBot types")

@app.get("/mindbot/my-configs", response_model=MindBotListResponse)
async def get_user_mindbot_configs(
    current_user: Dict = Depends(verify_jwt_token)
):
    """Get all MindBot configurations created by the current user"""
    
    try:
        user_id = current_user.get("user_id")
        
        # Get user's configurations
        configs = await mindbot_factory.get_user_mindbot_configs(user_id)
        
        return MindBotListResponse(
            mindbot_configs=configs,
            total_count=len(configs)
        )
        
    except Exception as e:
        logger.error(f"Error getting user MindBot configs: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving configurations")

@app.get("/mindbot/config/{config_id}")
async def get_mindbot_config(
    config_id: str,
    current_user: Dict = Depends(verify_jwt_token)
):
    """Get a specific MindBot configuration"""
    
    try:
        if config_id not in mindbot_factory.active_configs:
            raise HTTPException(status_code=404, detail="MindBot configuration not found")
        
        config = mindbot_factory.active_configs[config_id]
        system_prompt = mindbot_factory.system_prompts.get(config_id, "")
        
        return {
            "config_id": config_id,
            "config": config.to_dict(),
            "system_prompt": system_prompt
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting MindBot config: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving configuration")

@app.delete("/mindbot/config/{config_id}")
async def delete_mindbot_config(
    config_id: str,
    current_user: Dict = Depends(verify_jwt_token)
):
    """Delete a MindBot configuration"""
    
    try:
        user_id = current_user.get("user_id")
        
        if config_id not in mindbot_factory.active_configs:
            raise HTTPException(status_code=404, detail="MindBot configuration not found")
        
        # Remove from factory
        del mindbot_factory.active_configs[config_id]
        if config_id in mindbot_factory.system_prompts:
            del mindbot_factory.system_prompts[config_id]
        
        # Remove from database
        await delete_mindbot_from_database(config_id, user_id)
        
        logger.info(f"Deleted MindBot config {config_id} for user {user_id}")
        
        return {"message": "MindBot configuration deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting MindBot config: {e}")
        raise HTTPException(status_code=500, detail="Error deleting configuration")

@app.post("/mindbot/start-session/{config_id}")
async def start_mindbot_session(
    config_id: str,
    current_user: Dict = Depends(verify_jwt_token)
):
    """Start a voice session with a specific MindBot"""
    
    try:
        user_id = current_user.get("user_id")
        
        if config_id not in mindbot_factory.active_configs:
            raise HTTPException(status_code=404, detail="MindBot configuration not found")
        
        # Check user's time balance
        balance = await supabase_client.get_user_time_balance(user_id)
        
        if balance['total_minutes'] <= 0:
            raise HTTPException(
                status_code=402, 
                detail="Insufficient time balance. Please purchase time cards to continue."
            )
        
        config = mindbot_factory.active_configs[config_id]
        
        # Generate LiveKit token for this session
        from livekit import api
        import secrets
        
        room_name = f"mindbot_{config_id}_{secrets.token_hex(8)}"
        participant_name = current_user.get("full_name", "User")
        
        token = api.AccessToken(
            os.getenv("LIVEKIT_API_KEY"),
            os.getenv("LIVEKIT_API_SECRET")
        ).with_identity(user_id).with_name(participant_name).with_grants(
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
            session_id=f"mindbot_{config_id}_{int(datetime.utcnow().timestamp())}",
            room_name=room_name,
            agent_type=config.personality_type
        )
        
        logger.info(f"Started MindBot session for user {user_id} with {config.name}")
        
        return {
            "session_started": True,
            "room_name": room_name,
            "livekit_token": token,
            "livekit_url": os.getenv("LIVEKIT_URL"),
            "mindbot_name": config.name,
            "mindbot_type": config.personality_type,
            "session_id": session_data.session_id if session_data else None,
            "time_balance": balance
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting MindBot session: {e}")
        raise HTTPException(status_code=500, detail="Error starting session")

# Background tasks

async def save_mindbot_to_database(config_id: str, config: MindBotConfig, system_prompt: str, user_id: str):
    """Save MindBot configuration to database"""
    try:
        # This would save to a custom_mindbot_configs table in Supabase
        logger.info(f"Saving MindBot config {config_id} to database for user {user_id}")
        
        # Implementation would depend on your database schema
        # For now, just log the save operation
        
    except Exception as e:
        logger.error(f"Error saving MindBot to database: {e}")

async def delete_mindbot_from_database(config_id: str, user_id: str):
    """Delete MindBot configuration from database"""
    try:
        logger.info(f"Deleting MindBot config {config_id} from database for user {user_id}")
        
        # Implementation would depend on your database schema
        
    except Exception as e:
        logger.error(f"Error deleting MindBot from database: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "mindbot-creator-api",
        "timestamp": datetime.utcnow().isoformat(),
        "active_configs": len(mindbot_factory.active_configs)
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MindBot Creator API",
        "version": "1.0.0",
        "endpoints": {
            "create_mindbot": "/mindbot/create",
            "create_from_conversation": "/mindbot/create-from-conversation",
            "get_types": "/mindbot/types",
            "my_configs": "/mindbot/my-configs",
            "start_session": "/mindbot/start-session/{config_id}",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    logger.info("Starting MindBot Creator API...")
    
    uvicorn.run(
        "mindbot_creator_api:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
        log_level="info"
    )