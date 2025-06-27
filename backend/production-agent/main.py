import asyncio
import logging
import uvicorn

from livekit.agents import cli, WorkerOptions

from .core.settings import get_config, AgentConfig
from .services.supabase_client import SupabaseClient
from .services.stripe_manager import StripeManager
from .agent.main import entrypoint as agent_entrypoint, prewarm_process as agent_prewarm_process
from .api.webhook import app as webhook_app, stripe_manager as webhook_stripe_manager, supabase_client as webhook_supabase_client, config as webhook_config
from .core.logging_config import configure_logging, get_logger

logger = get_logger("mindbot.main")

async def main():
    # Load configuration
    config: AgentConfig = get_config("agent")

    # Configure logging
    configure_logging(
        service_name="mindbot-main",
        log_level=config.log_level,
        enable_json=config.environment == "production"
    )

    logger.info("Starting MindBot System...")
    logger.info(f"Environment: {config.environment}")
    logger.info(f"Supabase URL: {config.supabase_url}")
    logger.info(f"LiveKit URL: {config.livekit_url}")

    # Initialize global instances for webhook app
    webhook_stripe_manager.set(StripeManager(config))
    webhook_supabase_client.set(SupabaseClient(config))
    webhook_config.set(config)

    # Start webhook server in a separate task
    webhook_server_task = asyncio.create_task(uvicorn.run(
        webhook_app,
        host="0.0.0.0",
        port=8003,
        log_level=config.log_level.lower(),
        reload=config.debug # Reload only in debug mode
    ))

    # Start LiveKit agent
    logger.info("Starting LiveKit Agent...")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=agent_entrypoint,
            prewarm_fnc=agent_prewarm_process,
            # Additional LiveKit worker options can go here
        )
    )

    # Wait for the webhook server to complete (it will run indefinitely)
    await webhook_server_task

if __name__ == "__main__":
    asyncio.run(main())