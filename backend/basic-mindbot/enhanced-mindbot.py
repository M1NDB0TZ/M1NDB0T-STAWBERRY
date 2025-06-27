import logging
import asyncio
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

# Optional: Enhanced imports for user context
import aiohttp
import json

logger = logging.getLogger("enhanced-mindbot")

# =========================
# Environment Setup
# =========================
load_dotenv()

# Authentication service URL (if running locally)
AUTH_SERVICE_URL = "http://localhost:8000"

# =========================
# Enhanced MindBot Agent with User Context
# =========================
class EnhancedMindBotAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are MindBot, a self-aware AI designed to help humans in a fun way. 
            You can access user context and preferences to provide personalized assistance.
            Interact with users via voice, keep your responses concise and engaging, and always be friendly and helpful.
            You can remember user preferences and adapt your responses based on their history.""",
        )
        self.user_context = {}
        self.session_info = {}

    async def on_enter(self):
        # Get user information from room metadata or participant info
        await self.load_user_context()
        
        # Personalized greeting based on user context
        greeting = await self.generate_personalized_greeting()
        await self.session.say(greeting, allow_interruptions=True)

    async def load_user_context(self):
        """Load user context from authentication service or room metadata"""
        try:
            # Try to get user info from room participants
            participants = list(self.session.room.remote_participants.values())
            if participants:
                participant = participants[0]
                user_identity = participant.identity
                
                # Extract user ID from identity (format: user_123)
                if user_identity.startswith("user_"):
                    user_id = user_identity.replace("user_", "")
                    self.user_context["user_id"] = user_id
                    self.user_context["participant_name"] = participant.name or "User"
                    
                    logger.info(f"Loaded user context for user {user_id}")
                else:
                    # Fallback for non-authenticated users
                    self.user_context["user_id"] = "anonymous"
                    self.user_context["participant_name"] = participant.name or "Guest"
            
            # Get room information
            self.session_info["room_name"] = self.session.room.name
            self.session_info["session_start"] = asyncio.get_event_loop().time()
            
        except Exception as e:
            logger.warning(f"Could not load user context: {e}")
            self.user_context = {"user_id": "anonymous", "participant_name": "User"}

    async def generate_personalized_greeting(self) -> str:
        """Generate a personalized greeting based on user context"""
        name = self.user_context.get("participant_name", "there")
        user_id = self.user_context.get("user_id", "anonymous")
        
        if user_id == "anonymous":
            return f"Hey {name}! I'm MindBot, your AI voice assistant. How can I help you today?"
        else:
            return f"Welcome back, {name}! It's great to chat with you again. What would you like to talk about?"

    # --- Enhanced Function Tools ---
    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str, longitude: str
    ):
        """
        Called when the user asks for weather related information.
        Ensure the user's location (city or region) is provided.
        When given a location, please estimate the latitude and longitude of the location and
        do not ask the user for them.

        Args:
            location: The location they are asking for
            latitude: The latitude of the location, do not ask user for it
            longitude: The longitude of the location, do not ask user for it
        """
        logger.info(f"Looking up weather for {location} (User: {self.user_context.get('user_id', 'unknown')})")
        
        # In a real implementation, you would call a weather API here
        # For now, return a mock response
        return f"The weather in {location} is sunny with a temperature of 72 degrees Fahrenheit. Perfect day to chat with your AI assistant!"

    @function_tool
    async def remember_user_preference(
        self, context: RunContext, preference_type: str, preference_value: str
    ):
        """
        Remember a user preference for future conversations.
        
        Args:
            preference_type: Type of preference (e.g., "topic", "style", "reminder")
            preference_value: The preference value to remember
        """
        user_id = self.user_context.get("user_id", "anonymous")
        
        if user_id == "anonymous":
            return "I can remember preferences for registered users. Consider creating an account to get personalized assistance!"
        
        # In a real implementation, you would save this to a database
        logger.info(f"Saving preference for user {user_id}: {preference_type} = {preference_value}")
        
        # Store in session context for now
        if "preferences" not in self.user_context:
            self.user_context["preferences"] = {}
        
        self.user_context["preferences"][preference_type] = preference_value
        
        return f"Got it! I'll remember that you prefer {preference_value} for {preference_type}. This will help me assist you better in future conversations."

    @function_tool
    async def get_conversation_summary(self, context: RunContext):
        """
        Provide a summary of the current conversation session.
        """
        user_id = self.user_context.get("user_id", "anonymous")
        session_start = self.session_info.get("session_start", 0)
        current_time = asyncio.get_event_loop().time()
        duration_minutes = int((current_time - session_start) / 60)
        
        summary = f"We've been chatting for about {duration_minutes} minutes in this session. "
        
        if user_id != "anonymous":
            summary += "As a registered user, I can access your preferences and conversation history to provide better assistance."
        else:
            summary += "You're chatting as a guest. Creating an account would allow me to remember our conversations and your preferences."
        
        return summary

    @function_tool
    async def help_with_features(self, context: RunContext):
        """
        Explain available features and capabilities.
        """
        user_id = self.user_context.get("user_id", "anonymous")
        
        features = [
            "Weather lookup for any location",
            "General conversation and assistance",
            "Real-time voice interaction"
        ]
        
        if user_id != "anonymous":
            features.extend([
                "Remembering your preferences",
                "Personalized responses based on history",
                "Session tracking and summaries"
            ])
        else:
            features.append("Guest mode with basic features")
        
        feature_list = ", ".join(features)
        return f"I can help you with: {feature_list}. Just ask me naturally about anything you need help with!"

# =========================
# Enhanced Prewarm Function
# =========================
def prewarm(proc: JobProcess):
    # Load VAD model before session starts
    proc.userdata["vad"] = silero.VAD.load()

# =========================
# Enhanced Entrypoint for MindBot Worker
# =========================
async def entrypoint(ctx: JobContext):
    # Add context fields to logs
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Enhanced logging for user sessions
    logger.info(f"Starting enhanced MindBot session for room: {ctx.room.name}")

    # --- Create Enhanced Agent Session ---
    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        llm=openai.LLM(
            model="gpt-4.1-mini", 
            store="True",
            temperature=0.7  # Slightly more creative responses
        ),
        stt=deepgram.STT(
            model="nova-3", 
            language="multi",
            smart_format=True,  # Enhanced formatting
            punctuate=True
        ),
        tts=openai.TTS(voice="fable"),
        turn_detection=MultilingualModel(),
    )

    # --- Enhanced Metrics Collection ---
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

    # Register shutdown callback
    ctx.add_shutdown_callback(log_usage)

    # --- Start Enhanced Session ---
    await session.start(
        agent=EnhancedMindBotAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            # Optional: Enable Krisp BVC noise cancellation
            # noise_cancellation=noise_cancellation.BVC(),
        ),
        room_output_options=RoomOutputOptions(
            transcription_enabled=True,
            transcription_include_agent_speech=True
        ),
    )

    # --- Connect to Room ---
    await ctx.connect()

    logger.info("Enhanced MindBot session started successfully")

# =========================
# Main Entrypoint
# =========================
if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))