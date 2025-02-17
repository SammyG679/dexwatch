from typing import Tuple
import redis.asyncio as redis
from arango import ArangoClient
from config import logger


async def init_db_connections(
    redis_url: str, arango_url: str, db_name: str, username: str, password: str
) -> Tuple[redis.Redis, ArangoClient]:
    """Initialize database connections"""
    logger.info(
        f"Initializing database connections - Redis: {redis_url}, ArangoDB: {arango_url}"
    )

    redis_client = redis.from_url(redis_url)
    arango_client = ArangoClient(hosts=arango_url)
    db = arango_client.db(db_name, username=username, password=password)

    try:
        await redis_client.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.error(f"Redis connection failed: {str(e)}")
        raise

    if not db.has_collection("pair_data"):
        logger.info("Creating pair_data collection in ArangoDB")
        db.create_collection("pair_data")

    logger.info("Database connections initialized successfully")
    return redis_client, db
