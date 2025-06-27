"""
Enhanced voice agent that can dynamically load different personas
"""

import logging
import asyncio
from typing import Optional, Dict, Any

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

from supabase_client import supabase_client
from persona_manager import PersonaManager

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

# Enhanced entrypoint that accepts persona parameter
async def persona_entrypoint(ctx: JobContext, persona_slug: str = "mindbot"):
    """
    Entrypoint for persona-specific voice agent
    """
    try:
        # Connect to LiveKit room
        await ctx.connect()
        
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
            tts=openai.TTS(voice="alloy"),  # Default voice, persona can override
            vad=silero.VAD.load(),
            turn_detection=MultilingualModel(),
        )
        
        # Create persona agent
        agent = PersonaVoiceAgent(persona_slug)
        
        # Start the session
        await session.start(
            room=ctx.room,
            agent=agent,
        )
        
        logger.info(f"Started persona session: {persona_slug}")
        
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