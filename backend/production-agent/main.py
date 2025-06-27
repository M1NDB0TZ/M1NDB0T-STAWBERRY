# main.py

import asyncio
import logging
import uvicorn
from contextvars import ContextVar

from livekit.agents import cli, WorkerOptions

from .core.settings import get_config, AgentConfig
from .services.supabase_client import SupabaseClient
from .services.stripe_manager import StripeManager
from .agent.main import entrypoint as agent_entrypoint, prewarm_process as agent_prewarm_process
from .api.webhook import app as webhook_app
from .core.logging_config import configure_logging, get_logger

# Use ContextVar for global instances to ensure they are context-safe
webhook_stripe_manager: ContextVar[StripeManager] = ContextVar("webhook_stripe_manager")
webhook_supabase_client: ContextVar[SupabaseClient] = ContextVar("webhook_supabase_client")
webhook_config: ContextVar[AgentConfig] = ContextVar("webhook_config")

# Assign the context variables to the webhook module
from .api import webhook
webhook.stripe_manager = webhook_stripe_manager
webhook.supabase_client = webhook_supabase_client
webhook.config = webhook_config

logger = get_logger("mindbot.main")

async def main():
    """
    Main entry point for the MindBot system.
    This function initializes all services and starts the LiveKit agent and the webhook server.
    """
    # Load configuration
    config: AgentConfig = get_config("agent")

    # Configure logging for the entire application
    configure_logging(
        service_name="mindbot",
        log_level=config.log_level,
        enable_json=config.environment == "production"
    )

    logger.info("Initializing MindBot System...")
    logger.info(f"Environment: {config.environment}")
    logger.info(f"Log Level: {config.log_level}")
    logger.info(f"Debug Mode: {config.debug_mode}")

    # Initialize services and set them in context variables
    try:
        supabase_client = SupabaseClient(config)
        stripe_manager = StripeManager(config)
        webhook_supabase_client.set(supabase_client)
        webhook_stripe_manager.set(stripe_manager)
        webhook_config.set(config)
        logger.info("Supabase and Stripe clients initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        return

    # Configure the Uvicorn server for the webhook app
    uvicorn_config = uvicorn.Config(
        webhook_app,
        host="0.0.0.0",
        port=8003,
        log_level=config.log_level.lower(),
        reload=config.debug_mode
    )
    webhook_server = uvicorn.Server(uvicorn_config)

    # Start the webhook server in a separate asyncio task
    webhook_task = asyncio.create_task(webhook_server.serve())
    logger.info("Webhook server started at http://0.0.0.0:8003")

    # Start the LiveKit agent worker
    try:
        logger.info("Starting LiveKit Agent Worker...")
        worker_options = WorkerOptions(
            entrypoint_fnc=agent_entrypoint,
            prewarm_fnc=agent_prewarm_process,
            log_level=config.log_level,
            num_workers=config.max_concurrent_sessions
        )
        cli.run_app(worker_options)
    except Exception as e:
        logger.error(f"LiveKit Agent Worker failed to start: {e}")
    finally:
        # Ensure the webhook server is properly shut down
        if not webhook_task.done():
            webhook_task.cancel()
        logger.info("MindBot System has been shut down.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down MindBot System...")
    except Exception as e:
        logger.critical(f"An unhandled exception occurred: {e}", exc_info=True)
