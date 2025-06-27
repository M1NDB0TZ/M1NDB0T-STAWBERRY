"""
Enhanced voice agent that can dynamically load different personas
"""

import logging
import asyncio
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    function_tool,
    cli,
    WorkerOptions,
)
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins import deepgram, openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Load environment variables
load_dotenv()

# Try to import supabase client, use mock if not available
try:
    from supabase_client import supabase_client
except ImportError:
    # Create mock for testing
    class MockSupabaseClient:
        async def get_user_by_id(self, user_id):
            return type('User', (), {'id': user_id, 'email': 'test@example.com', 'full_name': 'Test User'})
        
        async def get_user_time_balance(self, user_id):
            return {"total_minutes": 60, "total_hours": 1.0, "active_cards": 1}
        
        async def start_voice_session(self, user_id, session_id, room_name, agent_type):
            return type('Session', (), {'session_id': session_id})
    
    supabase_client = MockSupabaseClient()

# Import or create mock persona manager
try:
    from persona_manager import PersonaManager
except ImportError:
    # Create mock for testing
    class MockPersonaConfig:
        def __init__(self, slug, name, summary, system_prompt):
            self.slug = slug
            self.name = name
            self.summary = summary
            self.system_prompt = system_prompt
            self.voice = {"tts": "alloy", "style": "neutral"}
            self.tools = ["check_time_balance"]
            self.age_restriction = None
            self.base_cost_multiplier = 1.0
            self.session_time_limit = None
            self.daily_usage_limit = None
            self.ad_supported = False
            self.premium_features = []
    
    class MockPersonaManager:
        def __init__(self, supabase_client):
            self.presets = {
                "mindbot": MockPersonaConfig(
                    "mindbot", 
                    "MindBot", 
                    "General assistant",
                    "You are MindBot, a helpful AI assistant."
                ),
                "blaze": MockPersonaConfig(
                    "blaze", 
                    "Blaze", 
                    "Cannabis guru",
                    "You are Blaze, a laid-back cannabis guru."
                ),
                "sizzle": MockPersonaConfig(
                    "sizzle", 
                    "SizzleBot", 
                    "DJ hype-man",
                    "You are SizzleBot, an energetic DJ hype-man."
                )
            }
        
        async def get_persona_by_slug(self, slug):
            return self.presets.get(slug)
    
    PersonaManager = MockPersonaManager

logger = logging.getLogger("mindbot.persona-agent")

class PersonaVoiceAgent(Agent):
    """Enhanced voice agent that adapts to different personas"""
    
    def __init__(self, persona_slug: str = "mindbot"):
        # Load persona configuration
        self.persona_manager = PersonaManager(supabase_client)
        self.persona = None
        self.persona_slug = persona_slug
        self.user_context = {}
        self.session_info = {}
        self.session_start_time = None
        
        # Initialize with default instructions (will be overridden)
        super().__init__(
            instructions="Loading persona..."
        )
    
    async def on_enter(self):
        """Called when agent enters the session"""
        try:
            # Load persona configuration
            await self._load_persona()
            
            # Load user context
            await self._load_user_context()
            
            # Update agent instructions with persona system prompt
            if self.persona:
                self.instructions = self.persona.system_prompt
            
            # Generate persona-specific greeting
            greeting = await self._generate_persona_greeting()
            
            # Send initial greeting
            await self.session.generate_reply(
                instructions=f"Greet the user with this message: {greeting}",
                allow_interruptions=True
            )
            
            logger.info(f"Started {self.persona_slug} session for user {self.user_context.get('user_id', 'anonymous')}")
            
        except Exception as e:
            logger.error(f"Error in on_enter for persona {self.persona_slug}: {e}")
            await self.session.generate_reply(
                instructions="Greet the user warmly and let them know you're here to help.",
                allow_interruptions=True
            )
    
    async def _load_persona(self):
        """Load the specific persona configuration"""
        try:
            self.persona = await self.persona_manager.get_persona_by_slug(self.persona_slug)
            
            if not self.persona:
                logger.error(f"Persona {self.persona_slug} not found, falling back to default")
                self.persona = await self.persona_manager.get_persona_by_slug("mindbot")
                self.persona_slug = "mindbot"
            
            logger.info(f"Loaded persona: {self.persona.name}")
            
        except Exception as e:
            logger.error(f"Error loading persona {self.persona_slug}: {e}")
            self.persona = None
    
    async def _load_user_context(self):
        """Load user context from LiveKit participant"""
        try:
            participants = list(self.session.room.remote_participants.values())
            if participants:
                participant = participants[0]
                user_identity = participant.identity
                
                if user_identity and user_identity != "anonymous":
                    user = await supabase_client.get_user_by_id(user_identity)
                    
                    if user:
                        self.user_context = {
                            "user_id": user.id,
                            "email": user.email,
                            "full_name": user.full_name,
                            "participant_name": participant.name or user.full_name,
                            "is_authenticated": True
                        }
                        
                        # Get time balance
                        balance = await supabase_client.get_user_time_balance(user.id)
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
    
    async def _generate_persona_greeting(self) -> str:
        """Generate greeting based on persona and user context"""
        name = self.user_context.get("participant_name", "there")
        is_authenticated = self.user_context.get("is_authenticated", False)
        
        if not self.persona:
            return f"Hello {name}! I'm MindBot, your AI assistant. How can I help you today?"
        
        # Use persona-specific greeting logic
        if self.persona.slug == "blaze":
            if is_authenticated:
                return f"Yo {name}! Blaze here, ready to share some chill wisdom and good vibes. What's on your mind today, dude?"
            else:
                return f"Hey there! I'm Blaze, your laid-back guide to all things zen. Ready to explore some mellow topics?"
        
        elif self.persona.slug == "sizzle":
            return f"YO YO YO {name}! SizzleBot in the house! *air horn* Ready to get this party STARTED? What we spinning today?!"
        
        elif self.persona.slug == "neon":
            balance = self.user_context.get("time_balance", {})
            if balance.get("total_minutes", 0) < 30 and is_authenticated:
                return f"Hello beautiful soul {name}! It's Neon here. I see your energy is running a bit low - maybe it's time to recharge with some time cards? What brings you to the festival today?"
            return f"Welcome to the light, {name}! I'm Neon, your rave guardian. How are your vibes feeling today?"
        
        elif self.persona.slug == "pixel":
            return f"OMG {name}! Pixel here! ✨ Ready to create some absolute BANGERS today? What kind of musical magic are we making?!"
        
        elif self.persona.slug == "professor_oak":
            return f"Good day, {name}! I'm Professor Oak. I'm here to help you learn and grow. What subject shall we explore together today?"
        
        elif self.persona.slug == "zen_master":
            return f"Welcome, {name}. I am here to guide you toward inner peace. Take a deep breath with me... How may we cultivate mindfulness together today?"
        
        # Default greeting for other personas
        balance = self.user_context.get("time_balance", {})
        if is_authenticated:
            if balance.get("total_minutes", 0) < 30:
                return f"Hello {name}! I'm {self.persona.name}. I notice you're running low on conversation time - consider getting some time cards to keep our sessions going. How can I help you today?"
            else:
                return f"Welcome back, {name}! I'm {self.persona.name}. You have {balance.get('total_hours', 0)} hours remaining. Ready to dive in?"
        else:
            return f"Hello {name}! I'm {self.persona.name}. {self.persona.summary} How can I assist you today?"
    
    # Universal function tools (available to all personas)
    
    @function_tool
    async def check_time_balance(self, context: RunContext) -> str:
        """Check user's current time balance"""
        if not self.user_context.get("is_authenticated"):
            return "Time balance tracking is only available for registered users. Create an account to purchase time cards and track your usage!"
        
        balance = await supabase_client.get_user_time_balance(self.user_context["user_id"])
        
        if not balance:
            return "I'm having trouble accessing your time balance right now."
        
        total_minutes = balance.get("total_minutes", 0)
        total_hours = balance.get("total_hours", 0)
        
        if total_hours >= 1:
            return f"You have {total_hours:.1f} hours ({total_minutes} minutes) remaining across {balance.get('active_cards', 0)} active time cards."
        elif total_minutes > 0:
            return f"You have {total_minutes} minutes remaining. Consider purchasing additional time cards to continue our conversations."
        else:
            return "Your time balance is empty. You'll need to purchase time cards to continue using MindBot."
    
    @function_tool
    async def switch_persona(self, context: RunContext, persona_name: str) -> str:
        """Switch to a different persona (if available)"""
        try:
            # Get available personas for user
            personas = await self.persona_manager.get_available_personas("premium")  # Assume premium for now
            
            # Find matching persona
            matching_persona = None
            for p in personas:
                if p["name"].lower() == persona_name.lower() or p["slug"] == persona_name.lower():
                    matching_persona = p
                    break
            
            if not matching_persona:
                available_names = [p["name"] for p in personas]
                return f"I couldn't find a persona named '{persona_name}'. Available personas: {', '.join(available_names)}"
            
            return f"To switch to {matching_persona['name']}, you'll need to start a new session. Would you like me to help you set that up?"
            
        except Exception as e:
            logger.error(f"Error switching persona: {e}")
            return "I'm having trouble switching personas right now. Please try again later."
    
    @function_tool
    async def get_persona_info(self, context: RunContext) -> str:
        """Get information about the current persona"""
        if not self.persona:
            return "I'm the default MindBot assistant, here to help with general questions and guide you to specialized personas."
        
        info = f"I'm {self.persona.name}! {self.persona.summary}\n\n"
        info += f"My purpose: {self.persona.purpose}\n\n"
        
        if self.persona.tools:
            info += f"I can help you with: {', '.join(self.persona.tools)}\n\n"
        
        if self.persona.age_restriction:
            info += f"Note: This persona is designed for users {self.persona.age_restriction}+ years old.\n\n"
        
        info += "What would you like to explore together?"
        
        return info
    
    @function_tool
    async def list_pricing_tiers(self, context: RunContext) -> str:
        """List available time card pricing tiers"""
        try:
            # In production, get from database
            tiers = [
                {"name": "Starter Pack", "hours": 1, "price": "$9.99", "bonus": "0 min"},
                {"name": "Basic Pack", "hours": 5, "price": "$44.99", "bonus": "30 min"},
                {"name": "Premium Pack", "hours": 10, "price": "$79.99", "bonus": "2 hours"},
                {"name": "Pro Pack", "hours": 25, "price": "$179.99", "bonus": "5 hours"},
                {"name": "Enterprise Pack", "hours": 50, "price": "$299.99", "bonus": "10 hours"}
            ]
            
            response = "Here are our current time card packages:\n\n"
            
            for tier in tiers:
                response += f"• {tier['name']} - {tier['price']}\n"
                response += f"  {tier['hours']} hours"
                
                if tier['bonus'] != "0 min":
                    response += f" + {tier['bonus']} bonus time"
                
                response += "\n"
            
            response += "\nAll time cards are valid for one year from activation. You can purchase them through our website or mobile app."
            
            return response
            
        except Exception as e:
            logger.error(f"Error listing pricing tiers: {e}")
            return "I'm having trouble retrieving our pricing information right now. Please check our website for current packages and pricing."
    
    @function_tool
    async def estimate_session_cost(self, context: RunContext) -> str:
        """Estimate the cost of the current session"""
        try:
            if not self.session_start_time:
                self.session_start_time = datetime.utcnow().timestamp()
            
            elapsed_seconds = datetime.utcnow().timestamp() - self.session_start_time
            elapsed_minutes = max(1, round(elapsed_seconds / 60))
            
            if not self.user_context.get("is_authenticated"):
                return f"This guest session has been running for about {elapsed_minutes} minute{'s' if elapsed_minutes != 1 else ''}. Time isn't deducted for guest sessions, but creating an account gives you access to time tracking and premium features."
            
            # Get cost multiplier based on persona
            cost_multiplier = 1.0
            if self.persona:
                cost_multiplier = getattr(self.persona, "base_cost_multiplier", 1.0)
            
            # Calculate cost
            cost_minutes = round(elapsed_minutes * cost_multiplier)
            
            # Get balance
            balance = self.user_context.get("time_balance", {"total_minutes": 0})
            remaining_minutes = balance.get("total_minutes", 0)
            
            # Calculate remaining time after this session
            remaining_after = max(0, remaining_minutes - cost_minutes)
            
            response = f"This session has been running for {elapsed_minutes} minute{'s' if elapsed_minutes != 1 else ''}, "
            
            if cost_multiplier != 1.0:
                response += f"with a cost multiplier of {cost_multiplier}x for this persona, "
            
            response += f"which will use approximately {cost_minutes} minute{'s' if cost_minutes != 1 else ''} from your balance."
            
            if remaining_after > 0:
                response += f" You'll have about {remaining_after} minutes remaining after this session."
            else:
                response += " This session will use up your remaining time balance. Consider purchasing more time cards to continue our conversations."
            
            return response
            
        except Exception as e:
            logger.error(f"Error estimating session cost: {e}")
            return "I'm having trouble calculating your session cost right now."

# Enhanced prewarm function
def prewarm(proc: JobProcess):
    """Preload components to speed up session start"""
    try:
        # Preload VAD model
        proc.userdata["vad"] = silero.VAD.load()
        
        # Preload other models if needed
        logger.info("Prewarming completed successfully")
        
    except Exception as e:
        logger.error(f"Error during prewarm: {e}")

# Enhanced entrypoint that accepts persona parameter
async def persona_entrypoint(ctx: JobContext, persona_slug: str = "mindbot"):
    """
    Entrypoint for persona-specific voice agent
    """
    try:
        # Add context fields to logs
        ctx.log_context_fields = {
            "room": ctx.room.name,
            "persona": persona_slug
        }
        
        logger.info(f"Starting persona session: {persona_slug} in room: {ctx.room.name}")
        
        # Connect to LiveKit room
        await ctx.connect()
        
        # Get voice configuration for persona
        voice = "alloy"  # Default voice
        try:
            # In production, get from persona config
            persona_voices = {
                "blaze": "onyx",
                "sizzle": "echo",
                "neon": "nova",
                "pixel": "shimmer",
                "professor_oak": "onyx",
                "zen_master": "alloy"
            }
            voice = persona_voices.get(persona_slug, "alloy")
        except Exception as e:
            logger.warning(f"Error getting voice for persona {persona_slug}: {e}")
        
        # Create agent session with persona
        session = AgentSession(
            stt=deepgram.STT(
                model="nova-3",
                language="multi",
                smart_format=True,
                punctuate=True
            ),
            llm=openai.LLM(
                model="gpt-4.1-mini", 
                temperature=0.7
            ),
            tts=openai.TTS(voice=voice),
            vad=ctx.proc.userdata.get("vad") or silero.VAD.load(),
            turn_detection=MultilingualModel(),
        )
        
        # Set up metrics collection
        usage_collector = session.metrics.UsageCollector()
        
        @session.on("metrics_collected")
        def _on_metrics_collected(ev: MetricsCollectedEvent):
            session.metrics.log_metrics(ev.metrics)
            usage_collector.collect(ev.metrics)
        
        @session.on("user_speech_committed")
        def _on_user_speech(msg):
            logger.debug(f"User said: {msg.transcript}")
        
        @session.on("agent_speech_committed")
        def _on_agent_speech(msg):
            logger.debug(f"Agent said: {msg.transcript}")
        
        # Log usage summary on shutdown
        async def log_usage():
            try:
                summary = usage_collector.get_summary()
                logger.info(f"Session usage summary: {summary}")
            except Exception as e:
                logger.error(f"Error logging usage: {e}")
        
        ctx.add_shutdown_callback(log_usage)
        
        # Create persona agent
        agent = PersonaVoiceAgent(persona_slug)
        
        # Start the session
        await session.start(
            room=ctx.room,
            agent=agent,
        )
        
        logger.info(f"Persona session started successfully: {persona_slug}")
        
    except Exception as e:
        logger.error(f"Error in persona entrypoint: {e}")
        raise

if __name__ == "__main__":
    import sys
    
    # Allow specifying persona via command line
    persona = sys.argv[1] if len(sys.argv) > 1 else "mindbot"
    
    cli.run_app(WorkerOptions(
        entrypoint_fnc=lambda ctx: persona_entrypoint(ctx, persona)
    ))