import logging
import os

from livekit.agents import (
    JobContext,
    AgentSession,
    cli,
    WorkerOptions,
    metrics,
)
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins import deepgram, openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from .mindbot_agent import ProductionMindBotAgent
from ..core.settings import AgentConfig, get_config
from ..services.supabase_client import SupabaseClient
from ..services.stripe_manager import StripeManager

logger = logging.getLogger("mindbot.agent.main")

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
    
    agent_config: AgentConfig = get_config("agent")

    try:
        # Add context fields to logs
        ctx.log_context_fields = {
            "room": ctx.room.name,
            "environment": agent_config.environment,
        }
        
        logger.info(f"Starting production MindBot session for room: {ctx.room.name}")
        
        # Connect to LiveKit room
        await ctx.connect(auto_subscribe=True)
        
        # Create agent session with production configuration
        session = AgentSession(
            stt=deepgram.STT(
                model=agent_config.stt_model,
                language=agent_config.stt_language,
                smart_format=True,
                punctuate=True
            ),
            llm=openai.LLM(
                model=agent_config.llm_model,
                temperature=agent_config.llm_temperature,
                max_tokens=agent_config.llm_max_tokens
            ),
            tts=openai.TTS(
                voice=agent_config.tts_voice
            ),
            vad=ctx.proc.userdata.get("vad") or silero.VAD.load(),
            turn_detection=MultilingualModel(),
        )
        
        # Create production MindBot agent
        agent = ProductionMindBotAgent(config=agent_config)
        
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


