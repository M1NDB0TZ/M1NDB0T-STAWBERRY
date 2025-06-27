
import asyncio
import logging
from core.settings import get_config
from services.supabase_client import supabase_client
from services.stripe_manager import stripe_manager
from livekit.api import RoomServiceClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_supabase_connection():
    """Checks the connection to Supabase."""
    try:
        await supabase_client.from_("users").select("id").limit(1).execute()
        logger.info("Supabase connection successful.")
        return True
    except Exception as e:
        logger.error(f"Supabase connection failed: {e}")
        return False

async def check_stripe_connection():
    """Checks the connection to Stripe."""
    try:
        stripe_manager.api_key
        logger.info("Stripe connection successful.")
        return True
    except Exception as e:
        logger.error(f"Stripe connection failed: {e}")
        return False

async def check_livekit_connection():
    """Checks the connection to LiveKit."""
    try:
        config = get_config('agent')
        livekit_client = RoomServiceClient(config.livekit_url, config.livekit_api_key, config.livekit_api_secret)
        await livekit_client.list_rooms()
        logger.info("LiveKit connection successful.")
        return True
    except Exception as e:
        logger.error(f"LiveKit connection failed: {e}")
        return False

async def main():
    """Runs all health checks."""
    logger.info("Starting health checks...")
    results = {
        "supabase": await check_supabase_connection(),
        "stripe": await check_stripe_connection(),
        "livekit": await check_livekit_connection(),
    }
    logger.info("Health checks finished.")
    
    all_successful = all(results.values())
    if all_successful:
        logger.info("All services are healthy.")
    else:
        logger.error("Some services are not healthy.")
        for service, status in results.items():
            if not status:
                logger.error(f"- {service}: FAILED")

if __name__ == "__main__":
    asyncio.run(main())
