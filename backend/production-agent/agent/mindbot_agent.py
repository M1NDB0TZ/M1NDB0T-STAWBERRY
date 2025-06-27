
Production MindBot Voice Agent with Supabase & Stripe Integration
Follows the Mem0 LiveKit pattern with time tracking and payment features


import asyncio
import logging
import time
from typing import AsyncIterable, Any, Dict, Optional
from datetime import datetime, timedelta

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    llm,
    function_tool,
    RunContext,
    ModelSettings,
    metrics,
)
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins import deepgram, openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Import our custom modules
from ..services.supabase_client import supabase_client, User, VoiceSession
from ..core.settings import AgentConfig, get_config

# Configure logging
logger = logging.getLogger("mindbot.production")


class ProductionMindBotAgent(Agent):
    """
    Production MindBot Agent with time tracking, payment integration, and user context
    Follows the Mem0 pattern for session management and external service integration
    """
    def __init__(self):
        super().__init__(
            instructions="""
            You are MindBot, a professional AI voice assistant that helps users with various tasks.
            You have access to the user's time balance and can help them manage their conversation time.
            
            Key capabilities:
            - Check user's remaining conversation time
            - Help with time card purchases
            - Provide information about pricing packages
            - Offer helpful assistance across various topics
            - Track usage and provide session summaries
            
            Guidelines:
            - Be concise and helpful in your responses
            - Keep track of the user's time balance
            - Warn users when their balance is getting low
            - Suggest purchasing more time when appropriate
            - Always be professional and friendly
            
            You can remember context within the session and provide personalized assistance.
            """
        )
        
        self.user_context: Dict[str, Any] = {}
        self.session_info: Dict[str, Any] = {}
        self.session_start_time: Optional[float] = None
        self.voice_session: Optional[VoiceSession] = None
        self.user: Optional[User] = None
        config = get_config('agent')
        self.low_balance_threshold = config.low_balance_threshold_minutes
        self.max_session_minutes = config.session_timeout_minutes
    
    async def on_enter(self):
        """Called when agent enters the session"""
        try:
            self.session_start_time = time.time()
            
            # Load user context from LiveKit participant
            await self._load_user_context()
            
            # Start time tracking if user is authenticated
            if self.user:
                await self._start_time_tracking()
            
            # Generate personalized greeting
            greeting = await self._generate_personalized_greeting()
            
            # Send initial greeting
            await self.session.generate_reply(
                instructions=f"Greet the user with this message: {greeting}",
                allow_interruptions=True
            )
            
            logger.info(f"Session started for user {self.user_context.get('user_id', 'anonymous')}")
            
        except Exception as e:
            logger.error(f"Error in on_enter: {e}")
            await self.session.generate_reply(
                instructions="Greet the user warmly and let them know you're here to help.",
                allow_interruptions=True
            )
    
    async def on_exit(self):
        """Called when agent exits the session"""
        try:
            if self.session_start_time and self.user:
                # Calculate session duration
                duration_seconds = int(time.time() - self.session_start_time)
                
                # End time tracking
                if self.voice_session:
                    await supabase_client.end_voice_session(
                        self.voice_session.session_id,
                        duration_seconds
                    )
                
                logger.info(f"Session ended for user {self.user.id}, duration: {duration_seconds}s")
            
        except Exception as e:
            logger.error(f"Error in on_exit: {e}")
    
    async def llm_node(
        self,
        chat_ctx: llm.ChatContext,
        tools: list[llm.FunctionTool],
        model_settings: ModelSettings,
    ) -> AsyncIterable[llm.ChatChunk]:
        """Override LLM node to add user context and time awareness"""
        
        # Add user context to the conversation
        await self._enrich_with_user_context(chat_ctx)
        
        # Call default LLM node with enriched context
        async for chunk in Agent.default.llm_node(self, chat_ctx, tools, model_settings):
            yield chunk
    
    async def _load_user_context(self):
        """Load user context from LiveKit participant information"""
        try:
            # Get participants from the room
            participants = list(self.session.room.remote_participants.values())
            
            if participants:
                participant = participants[0]
                user_identity = participant.identity
                
                # Extract user ID from identity (format: user_uuid or anonymous)
                if user_identity and user_identity != "anonymous":
                    # Try to get user from database
                    self.user = await supabase_client.get_user_by_id(user_identity)
                    
                    if self.user:
                        self.user_context = {
                            "user_id": self.user.id,
                            "email": self.user.email,
                            "full_name": self.user.full_name,
                            "participant_name": participant.name or self.user.full_name,
                            "is_authenticated": True
                        }
                        
                        # Update last login
                        await supabase_client.update_user_last_login(self.user.id)
                        
                        logger.info(f"Loaded user context for {self.user.email}")
                    else:
                        logger.warning(f"User {user_identity} not found in database")
                        self._set_anonymous_context(participant.name)
                else:
                    self._set_anonymous_context(participant.name)
            else:
                self._set_anonymous_context()
                
        except Exception as e:
            logger.error(f"Error loading user context: {e}")
            self._set_anonymous_context()
    
    def _set_anonymous_context(self, participant_name: str = "Guest"):
        """Set context for anonymous users"""
        self.user_context = {
            "user_id": "anonymous",
            "participant_name": participant_name,
            "is_authenticated": False
        }
    
    async def _start_time_tracking(self):
        """Start time tracking for authenticated users"""
        try:
            if not self.user:
                return
            
            # Generate unique session ID
            import uuid
            session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            room_name = self.session.room.name or "default_room"
            
            # Start voice session in database
            self.voice_session = await supabase_client.start_voice_session(
                user_id=self.user.id,
                session_id=session_id,
                room_name=room_name
            )
            
            if self.voice_session:
                logger.info(f"Started time tracking session {session_id}")
            else:
                logger.error("Failed to start time tracking session")
                
        except Exception as e:
            logger.error(f"Error starting time tracking: {e}")
    
    async def _generate_personalized_greeting(self) -> str:
        """Generate personalized greeting based on user context and balance"""
        try:
            if not self.user_context.get("is_authenticated"):
                return f"Hello {self.user_context.get('participant_name', 'there')}! I'm MindBot, your AI voice assistant. As a guest, your conversation time isn't tracked. Consider creating an account to access our full features with time card packages!"
            
            # Get user's time balance
            balance = await supabase_client.get_user_time_balance(self.user.id)
            total_minutes = balance['total_minutes']
            total_hours = balance['total_hours']
            
            name = self.user_context.get('participant_name', 'there')
            
            if total_minutes <= 0:
                return f"Hello {name}! I'm MindBot. I notice you don't have any conversation time remaining. You'll need to purchase time cards to continue using my services. Would you like me to help you with that?"
            elif total_minutes <= self.low_balance_threshold:
                return f"Hi {name}! Welcome back to MindBot. You have {total_minutes} minutes of conversation time remaining. Consider purchasing more time cards soon to avoid interruption. How can I help you today?"
            elif total_hours >= 5:
                return f"Welcome back, {name}! You have plenty of conversation time with {total_hours} hours remaining. What would you like to explore today?"
            else:
                return f"Hello {name}! You have {total_hours} hours of conversation time remaining. How can I assist you today?"
                
        except Exception as e:
            logger.error(f"Error generating greeting: {e}")
            return f"Hello! I'm MindBot, your AI voice assistant. How can I help you today?"
    
    async def _enrich_with_user_context(self, chat_ctx: llm.ChatContext):
        """Add user context and balance information to the conversation"""
        try:
            if not chat_ctx.messages or not self.user_context.get("is_authenticated"):
                return
            
            # Get latest user message
            user_msg = chat_ctx.messages[-1]
            if user_msg.role != "user":
                return
            
            # Get current time balance
            balance = await supabase_client.get_user_time_balance(self.user.id)
            
            # Calculate session time so far
            session_minutes = 0
            if self.session_start_time:
                session_minutes = int((time.time() - self.session_start_time) / 60)
            
            # Create context message
            context_text = f"""
User Context:
- Name: {self.user_context['participant_name']}
- Remaining Time: {balance['total_minutes']} minutes ({balance['total_hours']} hours)
- Active Time Cards: {balance['active_cards']}
- Current Session: {session_minutes} minutes elapsed
- Low Balance Warning: {'Yes' if balance['total_minutes'] <= self.low_balance_threshold else 'No'}
"""
            
            context_msg = llm.ChatMessage.create(
                text=f"User Context Information: {context_text}",
                role="assistant",
            )
            
            # Insert context before user message
            chat_ctx.messages.insert(-1, context_msg)
            
        except Exception as e:
            logger.error(f"Error enriching with user context: {e}")
    
    # Function tools for time management and purchases
    
    @function_tool
    async def check_time_balance(self, context: RunContext) -> str:
        """Check the user's current time balance and provide detailed information"""
        try:
            if not self.user_context.get("is_authenticated"):
                return "Time balance tracking is only available for registered users. Create an account to purchase time cards and track your usage!"
            
            balance = await supabase_client.get_user_time_balance(self.user.id)
            total_minutes = balance['total_minutes']
            total_hours = balance['total_hours']
            active_cards = balance['active_cards']
            
            if total_minutes <= 0:
                return "Your conversation time balance is empty. You'll need to purchase time cards to continue using MindBot. Would you like to hear about our available packages?"
            
            session_minutes = 0
            if self.session_start_time:
                session_minutes = int((time.time() - self.session_start_time) / 60)
            
            response = f"You have {total_minutes} minutes ({total_hours} hours) of conversation time remaining across {active_cards} active time cards."
            
            if session_minutes > 0:
                response += f" This current session has been running for {session_minutes} minutes."
            
            if total_minutes <= self.low_balance_threshold:
                response += " Your balance is getting low - consider purchasing additional time cards to avoid interruption."
            
            return response
            
        except Exception as e:
            logger.error(f"Error checking time balance: {e}")
            return "I'm having trouble accessing your time balance right now. Please try again in a moment."
    
    @function_tool
    async def get_pricing_packages(self, context: RunContext) -> str:
        """Get information about available time card packages and pricing"""
        try:
            tiers = await supabase_client.get_pricing_tiers()
            
            if not tiers:
                return "I'm having trouble retrieving pricing information right now. Please try again later."
            
            packages_info = "Here are our current time card packages:\n\n"
            
            for tier in tiers:
                total_minutes = (tier.hours * 60) + tier.bonus_minutes
                total_hours = round(total_minutes / 60, 1)
                price_display = f"${tier.price_cents / 100:.2f}"
                
                packages_info += f"• {tier.name} - {price_display}\n"
                packages_info += f"  {tier.hours} hours"
                
                if tier.bonus_minutes > 0:
                    bonus_hours = round(tier.bonus_minutes / 60, 1)
                    packages_info += f" + {bonus_hours} bonus hours"
                
                packages_info += f" (Total: {total_hours} hours)\n"
                packages_info += f"  {tier.description}\n\n"
            
            packages_info += "All time cards are valid for one year from activation. You can purchase them through our website or mobile app."
            
            return packages_info
            
        except Exception as e:
            logger.error(f"Error getting pricing packages: {e}")
            return "I'm having trouble retrieving pricing information right now. Please visit our website for current packages and pricing."
    
    @function_tool
    async def estimate_session_cost(self, context: RunContext) -> str:
        """Estimate the cost of the current session and remaining time"""
        try:
            if not self.session_start_time:
                return "I don't have session timing information available right now."
            
            elapsed_seconds = time.time() - self.session_start_time
            elapsed_minutes = max(1, round(elapsed_seconds / 60))  # Minimum 1 minute billing
            
            if not self.user_context.get("is_authenticated"):
                return f"This guest session has been running for about {elapsed_minutes} minute{'s' if elapsed_minutes != 1 else ''}. Time isn't deducted for guest sessions, but creating an account gives you access to time tracking and premium features."
            
            balance = await supabase_client.get_user_time_balance(self.user.id)
            remaining_minutes = balance['total_minutes']
            estimated_remaining = max(0, remaining_minutes - elapsed_minutes)
            
            response = f"This session has been running for {elapsed_minutes} minute{'s' if elapsed_minutes != 1 else ''}, which will be deducted from your balance when we finish."
            
            if estimated_remaining > 0:
                estimated_hours = round(estimated_remaining / 60, 1)
                response += f" You'd have approximately {estimated_remaining} minutes ({estimated_hours} hours) remaining after this session."
            else:
                response += " This session will use up your remaining time balance. Consider purchasing more time cards to continue our conversations."
            
            return response
            
        except Exception as e:
            logger.error(f"Error estimating session cost: {e}")
            return "I'm having trouble calculating your session cost right now."
    
    @function_tool
    async def start_purchase_process(self, context: RunContext, package_id: str) -> str:
        """Help user start the process to purchase a time card package"""
        try:
            if not self.user_context.get("is_authenticated"):
                return "To purchase time cards, you'll need to create an account first. Please visit our website or mobile app to register and then purchase time cards."
            
            # Validate package
            tiers = await supabase_client.get_pricing_tiers()
            tier = next((t for t in tiers if t.id == package_id), None)
            
            if not tier:
                available_packages = ", ".join([t.id for t in tiers])
                return f"Package '{package_id}' not found. Available packages are: {available_packages}"
            
            price_display = f"${tier.price_cents / 100:.2f}"
            total_hours = round(((tier.hours * 60) + tier.bonus_minutes) / 60, 1)
            
            response = f"To purchase the {tier.name} package ({total_hours} hours for {price_display}), "
            response += "please visit our website or mobile app where you can securely complete your payment. "
            response += "Once your payment is processed, your time will be automatically added to your account. "
            response += "You can then continue our conversation with your new time balance!"
            
            return response
            
        except Exception as e:
            logger.error(f"Error starting purchase process: {e}")
            return "I'm having trouble with the purchase process right now. Please visit our website to purchase time cards directly."
    
    @function_tool 
    async def get_session_summary(self, context: RunContext) -> str:
        """Provide a summary of the current session"""
        try:
            if not self.session_start_time:
                return "I don't have session information available right now."
            
            elapsed_seconds = time.time() - self.session_start_time
            elapsed_minutes = round(elapsed_seconds / 60, 1)
            
            summary = f"Session Summary:\n"
            summary += f"• Duration: {elapsed_minutes} minutes\n"
            
            if self.user_context.get("is_authenticated"):
                summary += f"• User: {self.user_context['participant_name']}\n"
                
                balance = await supabase_client.get_user_time_balance(self.user.id)
                summary += f"• Time Remaining: {balance['total_minutes']} minutes ({balance['total_hours']} hours)\n"
                
                cost_minutes = max(1, round(elapsed_seconds / 60))
                summary += f"• Estimated Cost: {cost_minutes} minutes\n"
                
                if balance['total_minutes'] <= self.low_balance_threshold:
                    summary += "• Note: Your balance is running low - consider purchasing more time cards\n"
            else:
                summary += "• Guest Session: No time tracking\n"
                summary += "• Tip: Create an account for time tracking and premium features\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating session summary: {e}")
            return "I'm having trouble generating your session summary right now."

    @function_tool
    async def get_agent_state(self, context: RunContext) -> str:
        """Get a snapshot of the agent's current state (for debugging)."""
        if not self.config.debug_mode:
            return "Debug mode is not enabled."

        state = {
            "user_context": self.user_context,
            "session_info": self.session_info,
            "session_start_time": self.session_start_time,
            "voice_session": self.voice_session.dict() if self.voice_session else None,
            "user": self.user.dict() if self.user else None,
            "config": self.config.dict(),
        }
        return str(state)


def prewarm_process(proc):
    """Preload components to speed up session start"""
    try:
        # Preload VAD model
        proc.userdata["vad"] = silero.VAD.load()
        
        # Preload other models if needed
        logger.info("Prewarming completed successfully")
        
    except Exception as e:
        logger.error(f"Error during prewarm: {e}")


async def entrypoint(ctx: JobContext):
    """
    Main entrypoint for the production MindBot agent
    Follows the Mem0 pattern with async initialization and proper error handling
    """
    
    try:
        config = get_config('agent')
        # Add context fields to logs
        ctx.log_context_fields = {
            "room": ctx.room.name,
            "environment": config.environment,
        }
        
        logger.info(f"Starting production MindBot session for room: {ctx.room.name}")
        
        # Connect to LiveKit room
        await ctx.connect(auto_subscribe=True)
        
        # Create agent session with production configuration
        session = AgentSession(
            stt=deepgram.STT(
                model=config.stt_model,
                language=config.stt_language,
                smart_format=True,
                punctuate=True
            ),
            llm=openai.LLM(
                model=config.llm_model,
                temperature=config.llm_temperature,
                max_tokens=config.llm_max_tokens
            ),
            tts=openai.TTS(
                voice=config.tts_voice
            ),
            vad=ctx.proc.userdata.get("vad") or silero.VAD.load(),
            turn_detection=MultilingualModel(),
        )
        
        # Create production MindBot agent
        agent = ProductionMindBotAgent()
        
        # Set up metrics collection
        usage_collector = metrics.UsageCollector()
        
        @session.on("metrics_collected")
        def _on_metrics_collected(ev: MetricsCollectedEvent):
            metrics.log_metrics(ev.metrics)
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
        
        # Start the session
        await session.start(
            room=ctx.room,
            agent=agent,
        )
        
        logger.info("Production MindBot session started successfully")
        
    except Exception as e:
        logger.error(f"Error in entrypoint: {e}")
        raise
