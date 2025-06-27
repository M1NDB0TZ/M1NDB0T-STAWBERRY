import logging
import asyncio
import aiohttp
from typing import Optional

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    RoomOutputOptions,
    RunContext,
    WorkerOptions,
    cli,
    metrics,
)
from livekit.agents.llm import function_tool
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins import deepgram, openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("time-aware-mindbot")

# =========================
# Environment Setup
# =========================
load_dotenv()

# Service URLs
TIME_SERVICE_URL = "http://localhost:8001"
AUTH_SERVICE_URL = "http://localhost:8000"

# =========================
# Time-Aware MindBot Agent
# =========================
class TimeAwareMindBotAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are MindBot, a self-aware AI designed to help humans. 
            You track conversation time and can inform users about their remaining balance.
            Keep responses concise and helpful. If a user's balance is low, gently remind them
            and suggest purchasing more time. Always be friendly and engaging.""",
        )
        self.user_context = {}
        self.session_info = {}
        self.time_session_id = None
        self.session_start_time = None

    async def on_enter(self):
        # Get user information and start time tracking
        await self.load_user_context()
        await self.start_time_tracking()
        
        # Personalized greeting with time balance
        greeting = await self.generate_greeting_with_balance()
        await self.session.say(greeting, allow_interruptions=True)

    async def on_exit(self):
        # End time tracking when session ends
        if self.time_session_id:
            await self.end_time_tracking()

    async def load_user_context(self):
        """Load user context and time balance"""
        try:
            participants = list(self.session.room.remote_participants.values())
            if participants:
                participant = participants[0]
                user_identity = participant.identity
                
                if user_identity.startswith("user_"):
                    user_id = user_identity.replace("user_", "")
                    self.user_context["user_id"] = user_id
                    self.user_context["participant_name"] = participant.name or "User"
                    self.user_context["is_authenticated"] = True
                    
                    # Get time balance
                    await self.fetch_time_balance()
                else:
                    self.user_context["user_id"] = "anonymous"
                    self.user_context["participant_name"] = participant.name or "Guest"
                    self.user_context["is_authenticated"] = False
            
            self.session_info["room_name"] = self.session.room.name
            
        except Exception as e:
            logger.warning(f"Could not load user context: {e}")
            self.user_context = {
                "user_id": "anonymous", 
                "participant_name": "User",
                "is_authenticated": False
            }

    async def fetch_time_balance(self):
        """Fetch user's time balance from time service"""
        if not self.user_context.get("is_authenticated"):
            return
        
        try:
            # This would require the JWT token to be passed somehow
            # For now, we'll simulate the balance check
            # In a real implementation, you'd need to pass the JWT token
            # through room metadata or another mechanism
            
            # Simulated balance for demo
            self.user_context["time_balance"] = {
                "total_minutes": 120,  # 2 hours
                "total_hours": 2.0,
                "active_cards": 1
            }
            
            logger.info(f"User {self.user_context['user_id']} has {self.user_context['time_balance']['total_minutes']} minutes remaining")
            
        except Exception as e:
            logger.error(f"Failed to fetch time balance: {e}")
            self.user_context["time_balance"] = None

    async def start_time_tracking(self):
        """Start time tracking session"""
        if not self.user_context.get("is_authenticated"):
            return
        
        try:
            self.time_session_id = f"{self.session_info['room_name']}_{asyncio.get_event_loop().time()}"
            self.session_start_time = asyncio.get_event_loop().time()
            
            # In a real implementation, you would call the time service API
            # For now, we'll just log the session start
            logger.info(f"Started time tracking session {self.time_session_id}")
            
        except Exception as e:
            logger.error(f"Failed to start time tracking: {e}")

    async def end_time_tracking(self):
        """End time tracking session"""
        if not self.time_session_id or not self.session_start_time:
            return
        
        try:
            current_time = asyncio.get_event_loop().time()
            duration_seconds = int(current_time - self.session_start_time)
            
            # In a real implementation, you would call the time service API
            # For now, we'll just log the session end
            logger.info(f"Ended time tracking session {self.time_session_id}: {duration_seconds} seconds")
            
            # Update user's balance in memory (for demo)
            if self.user_context.get("time_balance"):
                cost_minutes = max(1, round(duration_seconds / 60))
                remaining = self.user_context["time_balance"]["total_minutes"] - cost_minutes
                self.user_context["time_balance"]["total_minutes"] = max(0, remaining)
                
        except Exception as e:
            logger.error(f"Failed to end time tracking: {e}")

    async def generate_greeting_with_balance(self) -> str:
        """Generate greeting that includes time balance information"""
        name = self.user_context.get("participant_name", "there")
        is_authenticated = self.user_context.get("is_authenticated", False)
        
        if not is_authenticated:
            return f"Hey {name}! I'm MindBot. Note that as a guest, your session time isn't tracked. Consider creating an account to purchase time cards and get the full MindBot experience!"
        
        balance = self.user_context.get("time_balance")
        if balance:
            hours = balance.get("total_hours", 0)
            if hours > 1:
                return f"Welcome back, {name}! You have {hours} hours of conversation time remaining. What would you like to talk about today?"
            elif hours > 0.5:
                return f"Hi {name}! You have about {int(balance['total_minutes'])} minutes left. What can I help you with?"
            else:
                return f"Hello {name}! You're running low on time with only {int(balance['total_minutes'])} minutes left. Consider purchasing more time cards to continue our conversations!"
        else:
            return f"Welcome back, {name}! I'm having trouble checking your time balance right now, but let's chat anyway!"

    # --- Enhanced Function Tools ---
    @function_tool
    async def check_time_balance(self, context: RunContext):
        """
        Check the user's current time balance and provide information about usage.
        """
        if not self.user_context.get("is_authenticated"):
            return "Time balance tracking is only available for registered users. Consider creating an account to purchase time cards and track your usage!"
        
        balance = self.user_context.get("time_balance")
        if not balance:
            return "I'm having trouble accessing your time balance right now. Please try again in a moment."
        
        total_minutes = balance.get("total_minutes", 0)
        total_hours = balance.get("total_hours", 0)
        
        if total_hours >= 1:
            return f"You have {total_hours:.1f} hours ({total_minutes} minutes) of conversation time remaining across {balance.get('active_cards', 0)} active time cards."
        elif total_minutes > 0:
            return f"You have {total_minutes} minutes of conversation time remaining. Consider purchasing additional time cards to continue our conversations."
        else:
            return "Your time balance is empty. You'll need to purchase time cards to continue using MindBot. Would you like information about our time card packages?"

    @function_tool
    async def get_time_packages(self, context: RunContext):
        """
        Provide information about available time card packages and pricing.
        """
        return """Here are our current time card packages:

• Starter Pack (1 hour) - $9.99 - Perfect for trying out MindBot
• Basic Pack (5 hours + 30 bonus minutes) - $44.99 - Great for regular users  
• Premium Pack (10 hours + 2 bonus hours) - $79.99 - Best value option
• Pro Pack (25 hours + 5 bonus hours) - $179.99 - For power users
• Enterprise Pack (50 hours + 10 bonus hours) - $299.99 - Maximum value

All time cards are valid for one year from activation. You can purchase them through our website or mobile app. Would you like help with anything else?"""

    @function_tool
    async def estimate_session_cost(self, context: RunContext):
        """
        Provide an estimate of the current session cost and remaining time.
        """
        if not self.session_start_time:
            return "I don't have session timing information available right now."
        
        current_time = asyncio.get_event_loop().time()
        elapsed_seconds = current_time - self.session_start_time
        elapsed_minutes = max(1, round(elapsed_seconds / 60))
        
        if self.user_context.get("is_authenticated"):
            balance = self.user_context.get("time_balance", {})
            remaining_minutes = balance.get("total_minutes", 0)
            estimated_remaining_time = remaining_minutes - elapsed_minutes
            
            return f"This session has been running for about {elapsed_minutes} minute{'s' if elapsed_minutes != 1 else ''}, which will be deducted from your balance when we finish. You'd have approximately {max(0, estimated_remaining_time)} minutes remaining after this session."
        else:
            return f"This guest session has been running for about {elapsed_minutes} minute{'s' if elapsed_minutes != 1 else ''}. Time isn't deducted for guest sessions, but creating an account gives you access to time tracking and premium features."

    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str, longitude: str
    ):
        """
        Called when the user asks for weather related information.
        """
        logger.info(f"Looking up weather for {location} (User: {self.user_context.get('user_id', 'unknown')})")
        return f"The weather in {location} is sunny with a temperature of 72 degrees Fahrenheit. Perfect weather for chatting with your AI assistant!"

# =========================
# Prewarm Function
# =========================
def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

# =========================
# Enhanced Entrypoint
# =========================
async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    logger.info(f"Starting time-aware MindBot session for room: {ctx.room.name}")

    # --- Create Time-Aware Agent Session ---
    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        llm=openai.LLM(
            model="gpt-4.1-mini", 
            store="True",
            temperature=0.7
        ),
        stt=deepgram.STT(
            model="nova-3", 
            language="multi",
            smart_format=True,
            punctuate=True
        ),
        tts=openai.TTS(voice="fable"),
        turn_detection=MultilingualModel(),
    )

    # --- Metrics Collection ---
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    @session.on("user_speech_committed")
    def _on_user_speech(msg):
        logger.info(f"User said: {msg.transcript}")

    @session.on("agent_speech_committed")
    def _on_agent_speech(msg):
        logger.info(f"Agent said: {msg.transcript}")

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Session usage summary: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # --- Start Time-Aware Session ---
    await session.start(
        agent=TimeAwareMindBotAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(),
        room_output_options=RoomOutputOptions(
            transcription_enabled=True,
            transcription_include_agent_speech=True
        ),
    )

    await ctx.connect()
    logger.info("Time-aware MindBot session started successfully")

# =========================
# Main Entrypoint
# =========================
if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))