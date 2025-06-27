"""
MindBot Factory - Creates and manages custom MindBot instances
Integrates with the existing production system for modular AI creation
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, AsyncIterable
from dataclasses import dataclass
import asyncio
from datetime import datetime

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    llm,
    function_tool,
    RunContext,
    cli,
    WorkerOptions,
    ModelSettings,
)
from livekit.plugins import deepgram, openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from prompt_generator import MindBotConfig, MindBotPromptGenerator
from supabase_client import supabase_client

logger = logging.getLogger(__name__)

class CustomMindBotAgent(Agent):
    """Dynamically created MindBot agent based on user configuration"""
    
    def __init__(self, config: MindBotConfig, system_prompt: str):
        super().__init__(instructions=system_prompt)
        self.config = config
        self.user_context = {}
        self.session_info = {}
        self.conversation_count = 0
        
    async def on_enter(self):
        """Called when agent enters the session"""
        try:
            # Load user context
            await self._load_user_context()
            
            # Generate personalized greeting based on AI type
            greeting = await self._generate_custom_greeting()
            
            # Send initial greeting
            await self.session.generate_reply(
                instructions=f"Greet the user with this message: {greeting}",
                allow_interruptions=True
            )
            
            logger.info(f"Started {self.config.name} session for user {self.user_context.get('user_id', 'anonymous')}")
            
        except Exception as e:
            logger.error(f"Error in on_enter for {self.config.name}: {e}")
            await self.session.generate_reply(
                instructions=f"Greet the user warmly as {self.config.name} and let them know you're here to help with {self.config.primary_purpose}.",
                allow_interruptions=True
            )
    
    async def _load_user_context(self):
        """Load user context from LiveKit participant"""
        try:
            participants = list(self.session.room.remote_participants.values())
            if participants:
                participant = participants[0]
                user_identity = participant.identity
                
                if user_identity and user_identity != "anonymous":
                    self.user = await supabase_client.get_user_by_id(user_identity)
                    
                    if self.user:
                        self.user_context = {
                            "user_id": self.user.id,
                            "email": self.user.email,
                            "full_name": self.user.full_name,
                            "participant_name": participant.name or self.user.full_name,
                            "is_authenticated": True
                        }
                        
                        # Get time balance if this is a paid service
                        balance = await supabase_client.get_user_time_balance(self.user.id)
                        self.user_context["time_balance"] = balance
                    else:
                        self._set_anonymous_context(participant.name)
                else:
                    self._set_anonymous_context(participant.name)
            else:
                self._set_anonymous_context()
                
        except Exception as e:
            logger.error(f"Error loading user context: {e}")
            self._set_anonymous_context()
    
    def _set_anonymous_context(self, participant_name: str = "there"):
        """Set context for anonymous users"""
        self.user_context = {
            "user_id": "anonymous",
            "participant_name": participant_name,
            "is_authenticated": False
        }
    
    async def _generate_custom_greeting(self) -> str:
        """Generate greeting based on AI type and user context"""
        name = self.user_context.get("participant_name", "there")
        is_authenticated = self.user_context.get("is_authenticated", False)
        
        greetings = {
            "tutor": f"Hello {name}! I'm {self.config.name}, your {self.config.primary_purpose} tutor. I'm excited to help you learn and grow. What would you like to explore today?",
            
            "coach": f"Hi {name}! I'm {self.config.name}, and I'm here to coach you through {self.config.primary_purpose}. Together, we'll work on achieving your goals. What are you hoping to accomplish?",
            
            "consultant": f"Good day, {name}. I'm {self.config.name}, a specialist in {self.config.primary_purpose}. I'm here to provide expert guidance and solutions. How can I assist you today?",
            
            "therapist": f"Hello {name}, I'm {self.config.name}. I'm here to provide a supportive space for {self.config.primary_purpose}. Remember, I'm an AI companion, not a licensed therapist, but I'm here to listen and help. How are you feeling today?",
            
            "assistant": f"Hi {name}! I'm {self.config.name}, your personal assistant for {self.config.primary_purpose}. I'm here to help make your life easier and more organized. What can I help you with?",
            
            "entertainer": f"Hey there, {name}! I'm {self.config.name}, and I'm here to bring some fun to your day with {self.config.primary_purpose}. Ready for some entertainment?",
            
            "specialist": f"Hello {name}! I'm {self.config.name}, specializing in {self.config.primary_purpose}. I'm here to share my expertise and help you succeed. What questions do you have for me?"
        }
        
        base_greeting = greetings.get(self.config.personality_type, greetings["assistant"])
        
        # Add time balance info if authenticated
        if is_authenticated and self.config.personality_type != "therapist":
            balance = self.user_context.get("time_balance", {})
            if balance.get("total_minutes", 0) < 30:
                base_greeting += " By the way, you're running low on conversation time - consider purchasing more time cards to continue our sessions!"
        
        return base_greeting
    
    async def llm_node(
        self,
        chat_ctx: llm.ChatContext,
        tools: list[llm.FunctionTool],
        model_settings: ModelSettings,
    ) -> AsyncIterable[llm.ChatChunk]:
        """Override LLM node to add custom context and behavior"""
        
        # Add user context to the conversation
        await self._enrich_with_context(chat_ctx)
        
        # Track conversation metrics
        self.conversation_count += 1
        
        # Call default LLM node with enriched context
        async for chunk in Agent.default.llm_node(self, chat_ctx, tools, model_settings):
            yield chunk
    
    async def _enrich_with_context(self, chat_ctx: llm.ChatContext):
        """Add user context and AI-specific instructions to conversation"""
        try:
            if not chat_ctx.messages:
                return
            
            # Get user context information
            context_info = []
            
            if self.user_context.get("is_authenticated"):
                context_info.append(f"User: {self.user_context['participant_name']}")
                balance = self.user_context.get("time_balance", {})
                if balance:
                    context_info.append(f"Time remaining: {balance.get('total_minutes', 0)} minutes")
            
            context_info.append(f"Session conversation count: {self.conversation_count}")
            context_info.append(f"AI Type: {self.config.personality_type}")
            context_info.append(f"Primary Purpose: {self.config.primary_purpose}")
            
            if context_info:
                context_text = " | ".join(context_info)
                
                context_msg = llm.ChatMessage.create(
                    text=f"[Context: {context_text}]",
                    role="system",
                )
                
                # Insert context before the latest user message
                chat_ctx.messages.insert(-1, context_msg)
                
        except Exception as e:
            logger.error(f"Error enriching context: {e}")
    
    # Dynamic function tools based on AI type
    async def get_ai_info(self, context: RunContext) -> str:
        """Get information about this AI's capabilities and purpose"""
        info = f"""I'm {self.config.name}, a {self.config.personality_type} AI specialized in {self.config.primary_purpose}.

My expertise areas include: {', '.join(self.config.domain_expertise)}

I'm designed to be {self.config.tone} in tone and use a {self.config.interaction_style} interaction style.

My target audience is: {self.config.target_audience}

I can help you with specific tasks using these available functions: {', '.join(self.config.available_functions)}

Is there something specific you'd like to know about my capabilities?"""
        
        return info
    
    async def check_time_balance(self, context: RunContext) -> str:
        """Check user's time balance (inherited from base system)"""
        if not self.user_context.get("is_authenticated"):
            return f"Time tracking is only available for registered users. As {self.config.name}, I'm here to help you with {self.config.primary_purpose} whether you have an account or not!"
        
        balance = self.user_context.get("time_balance", {})
        if not balance:
            return "I'm having trouble accessing your time balance right now."
        
        total_minutes = balance.get("total_minutes", 0)
        
        if total_minutes <= 0:
            return f"Your conversation time has run out. You'll need to purchase more time cards to continue our {self.config.primary_purpose} sessions. I'll be here when you're ready!"
        
        return f"You have {total_minutes} minutes ({balance.get('total_hours', 0)} hours) remaining for our {self.config.primary_purpose} sessions."


class MindBotFactory:
    """Factory for creating and managing custom MindBot instances"""
    
    def __init__(self):
        self.prompt_generator = MindBotPromptGenerator()
        self.active_configs: Dict[str, MindBotConfig] = {}
        self.system_prompts: Dict[str, str] = {}
    
    async def create_mindbot_from_description(self, user_description: str, user_id: str = None) -> tuple[MindBotConfig, str]:
        """Create a custom MindBot from user description"""
        
        logger.info(f"Creating custom MindBot from description: {user_description}")
        
        # Generate configuration
        config = await self.prompt_generator.generate_custom_mindbot(user_description)
        
        # Generate system prompt
        system_prompt = await self.prompt_generator.generate_system_prompt(config)
        
        # Store configuration
        config_id = f"{config.name.lower().replace(' ', '_')}_{int(datetime.utcnow().timestamp())}"
        self.active_configs[config_id] = config
        self.system_prompts[config_id] = system_prompt
        
        # Save to database if user is authenticated
        if user_id:
            await self._save_mindbot_config(config_id, config, user_id)
        
        logger.info(f"Created MindBot: {config.name} ({config.personality_type})")
        
        return config, system_prompt
    
    async def create_mindbot_from_conversation(self, conversation_history: List[str], user_id: str = None) -> tuple[MindBotConfig, str]:
        """Create a custom MindBot based on conversation about requirements"""
        
        logger.info("Creating custom MindBot from conversation")
        
        # Generate configuration from conversation
        config = await self.prompt_generator.create_mindbot_from_conversation(conversation_history)
        
        # Generate system prompt
        system_prompt = await self.prompt_generator.generate_system_prompt(config)
        
        # Store configuration
        config_id = f"{config.name.lower().replace(' ', '_')}_{int(datetime.utcnow().timestamp())}"
        self.active_configs[config_id] = config
        self.system_prompts[config_id] = system_prompt
        
        # Save to database if user is authenticated
        if user_id:
            await self._save_mindbot_config(config_id, config, user_id)
        
        logger.info(f"Created MindBot from conversation: {config.name} ({config.personality_type})")
        
        return config, system_prompt
    
    async def get_mindbot_agent(self, config_id: str) -> CustomMindBotAgent:
        """Get a MindBot agent instance"""
        
        if config_id not in self.active_configs:
            raise ValueError(f"MindBot configuration {config_id} not found")
        
        config = self.active_configs[config_id]
        system_prompt = self.system_prompts[config_id]
        
        return CustomMindBotAgent(config, system_prompt)
    
    async def list_available_mindbot_types(self) -> Dict[str, str]:
        """List available MindBot types with descriptions"""
        return {
            "tutor": "Educational AI that helps with learning and skill development",
            "coach": "Motivational AI that helps achieve goals and personal growth",
            "consultant": "Expert AI that provides professional advice and solutions",
            "therapist": "Supportive AI companion for emotional wellbeing (not licensed therapy)",
            "assistant": "General-purpose AI that helps with tasks and organization",
            "entertainer": "Fun AI that provides entertainment and creative activities",
            "specialist": "Domain-specific AI expert in particular fields"
        }
    
    async def get_user_mindbot_configs(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all MindBot configurations created by a user"""
        try:
            # This would query your database for saved configurations
            # For now, return active configs
            user_configs = []
            for config_id, config in self.active_configs.items():
                user_configs.append({
                    "id": config_id,
                    "name": config.name,
                    "type": config.personality_type,
                    "purpose": config.primary_purpose,
                    "created_at": config.created_at.isoformat()
                })
            return user_configs
        except Exception as e:
            logger.error(f"Error getting user MindBot configs: {e}")
            return []
    
    async def _save_mindbot_config(self, config_id: str, config: MindBotConfig, user_id: str):
        """Save MindBot configuration to database"""
        try:
            # This would save to your Supabase database
            # Add a table for custom mindbot configurations
            logger.info(f"Saving MindBot config {config_id} for user {user_id}")
            # Implementation depends on your database schema
        except Exception as e:
            logger.error(f"Error saving MindBot config: {e}")


# Global factory instance
mindbot_factory = MindBotFactory()


# Example usage for creating custom agents
async def create_custom_agent_entrypoint(ctx: JobContext, user_description: str = None):
    """
    Entrypoint for custom MindBot creation
    This would be called with the user's description of what they want
    """
    
    try:
        # Connect to LiveKit room
        await ctx.connect()
        
        if user_description:
            # Create custom MindBot based on description
            config, system_prompt = await mindbot_factory.create_mindbot_from_description(user_description)
            logger.info(f"Created custom MindBot: {config.name}")
        else:
            # Use a default assistant configuration
            user_description = "A helpful general assistant for various tasks"
            config, system_prompt = await mindbot_factory.create_mindbot_from_description(user_description)
        
        # Create agent session
        session = AgentSession(
            stt=deepgram.STT(
                model="nova-3",
                language="multi",
                smart_format=True,
                punctuate=True
            ),
            llm=openai.LLM(
                model="gpt-4-1106-preview", 
                temperature=0.7
            ),
            tts=openai.TTS(voice="alloy"),
            vad=silero.VAD.load(),
            turn_detection=MultilingualModel(),
        )
        
        # Create custom agent
        agent = CustomMindBotAgent(config, system_prompt)
        
        # Start the session
        await session.start(
            room=ctx.room,
            agent=agent,
        )
        
        logger.info(f"Started custom MindBot session: {config.name}")
        
    except Exception as e:
        logger.error(f"Error in custom agent entrypoint: {e}")
        raise


if __name__ == "__main__":
    # Example: Create a math tutor
    user_request = "I want to create a patient math tutor for high school students who struggle with algebra. It should be encouraging and break down problems step by step."
    
    # This would normally be passed as a parameter to the entrypoint
    cli.run_app(WorkerOptions(
        entrypoint_fnc=lambda ctx: create_custom_agent_entrypoint(ctx, user_request)
    ))