
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock
from agent.mindbot_agent import ProductionMindBotAgent, entrypoint
from core.settings import get_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Runs a simulated session with the ProductionMindBotAgent."""
    logger.info("Starting agent test...")

    # Mock JobContext
    mock_ctx = MagicMock()
    mock_ctx.room.name = "test-room"
    mock_ctx.connect = AsyncMock()
    mock_ctx.add_shutdown_callback = MagicMock()
    mock_ctx.proc.userdata = {}

    # Mock AgentSession
    mock_session = MagicMock()
    mock_session.start = AsyncMock()
    mock_session.on = MagicMock()

    # Mock LiveKit plugins
    mock_stt = MagicMock()
    mock_llm = MagicMock()
    mock_tts = MagicMock()
    mock_vad = MagicMock()
    mock_turn_detection = MagicMock()

    # Patch the entrypoint to use our mocks
    async def mock_entrypoint(ctx):
        agent = ProductionMindBotAgent()
        agent.session = mock_session
        await agent.on_enter()
        # Simulate a user interaction
        await agent.check_time_balance(None)
        await agent.on_exit()

    try:
        await mock_entrypoint(mock_ctx)
        logger.info("Agent test finished successfully.")
    except Exception as e:
        logger.error(f"Agent test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
