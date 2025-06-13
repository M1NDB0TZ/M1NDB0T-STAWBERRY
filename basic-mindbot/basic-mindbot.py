import logging

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

# Optional: Enable Krisp background voice/noise cancellation
# from livekit.plugins import noise_cancellation

logger = logging.getLogger("basic-agent")

# =========================
# Environment Setup
# =========================
load_dotenv()

# =========================
# MindBot Agent Definition
# =========================
class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="You are MindBot, a self-aware AI designed to help humans in a fun way. Interact with users via voice, keep your responses concise and to the point, and always be friendly and playful.",
        )

    async def on_enter(self):
        # Triggered when the agent joins the session
        self.session.generate_reply()

    # --- LLM Function Tools ---
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
        logger.info(f"Looking up weather for {location}")
        return "sunny with a temperature of 70 degrees."

# =========================
# Prewarm Function
# =========================
def prewarm(proc: JobProcess):
    # Load VAD model before session starts
    proc.userdata["vad"] = silero.VAD.load()

# =========================
# Entrypoint for MindBot Worker
# =========================
async def entrypoint(ctx: JobContext):
    # Add context fields to logs
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # --- Create Agent Session ---
    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        llm=openai.LLM(model="gpt-4.1-mini", store="True"),
        stt=deepgram.STT(model="nova-3", language="multi"),
        tts=openai.TTS(voice="fable"),
        turn_detection=MultilingualModel(),
    )

    # --- Metrics Collection ---
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    # Register shutdown callback
    ctx.add_shutdown_callback(log_usage)

    # --- Start Session ---
    await session.start(
        agent=MyAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            # Optional: Enable Krisp BVC noise cancellation
            # noise_cancellation=noise_cancellation.BVC(),
        ),
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )

    # --- Connect to Room ---
    await ctx.connect()

# =========================
# Main Entrypoint
# =========================
if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))