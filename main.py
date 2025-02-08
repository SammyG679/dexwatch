import asyncio
import sys
from config import logger
from models.stats import PipelineStats
from db.connections import init_db_connections
from services.token_service import (
    fetch_token_profiles,
    fetch_latest_boosts,
    fetch_top_boosts,
)
from services.pair_service import process_solana_pairs
from services.analysis_service import analyze_pairs
from utils.config import Config
import time

config = Config()


async def run_pipeline(
    redis_url: str, arango_url: str, db_name: str, username: str, password: str
) -> None:
    start_time = time.time()
    logger.info("Starting DexScreener pipeline")

    stats = PipelineStats()
    redis_client, db = await init_db_connections(
        redis_url, arango_url, db_name, username, password
    )

    try:
        # Fetch and store latest boosts
        logger.info("=== Starting Latest Boosts Phase ===")
        await fetch_latest_boosts(redis_client, stats)
        await asyncio.sleep(1)

        # Fetch and store top boosts
        logger.info("=== Starting Top Boosts Phase ===")
        await fetch_top_boosts(redis_client, stats)

        # Add new token profiles phase
        logger.info("=== Starting Token Profiles Phase ===")
        await fetch_token_profiles(redis_client, stats)
        await asyncio.sleep(1)

        # Process pair data
        logger.info("=== Starting Pair Data Processing Phase ===")
        await process_solana_pairs(redis_client, db, stats)

        elapsed_time = time.time() - start_time
        logger.info(f"Pipeline completed in {elapsed_time:.2f} seconds")
        stats.log_summary()

    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        raise
    finally:
        await redis_client.aclose()
        logger.info("Pipeline shutdown complete")


async def main():
    try:
        await run_pipeline(
            redis_url="redis://localhost:6379",
            arango_url="http://localhost:8529",
            db_name="jeettech",
            username=f"{config.ARANGO_USER}",
            password=f"{config.ARANGO_PASS}",
        )
        logger.info("\n=== Analyzing Pair Data ===")
        await analyze_pairs()
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
