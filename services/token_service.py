import asyncio
import redis.asyncio as redis
from typing import List, Dict
from config import logger, REDIS_PREFIX
from api.dexscreener import make_request, make_concurrent_requests
from db.redis_operations import store_token_addresses, get_token_metadata
from models.stats import PipelineStats


async def fetch_all_token_data(redis_client: redis.Redis, stats: PipelineStats) -> None:
    endpoints = [
        "/token-profiles/latest/v1",
        "/token-boosts/latest/v1",
        "/token-boosts/top/v1",
    ]

    results = await make_concurrent_requests(
        endpoints, stats, redis_client, batch_size=3
    )

    store_tasks = []
    for endpoint, data in zip(endpoints, results):
        if data:
            key_suffix = "_".join(endpoint.split("/")[-2:])
            store_tasks.append(
                store_token_addresses(
                    redis_client,
                    f"{REDIS_PREFIX}{key_suffix}_addresses",
                    data,
                    key_suffix,
                )
            )

    if store_tasks:
        await asyncio.gather(*store_tasks)


# Keep these for backwards compatibility
async def fetch_token_profiles(redis_client: redis.Redis, stats: PipelineStats) -> None:
    data = await make_request("/token-profiles/latest/v1", stats, redis_client)
    if data:
        await store_token_addresses(
            redis_client,
            f"{REDIS_PREFIX}token_profiles_addresses",
            data,
            "token_profiles",
        )


async def fetch_latest_boosts(redis_client: redis.Redis, stats: PipelineStats) -> None:
    data = await make_request("/token-boosts/latest/v1", stats, redis_client)
    if data:
        await store_token_addresses(
            redis_client, f"{REDIS_PREFIX}latest_boost_addresses", data, "latest_boosts"
        )


async def fetch_top_boosts(redis_client: redis.Redis, stats: PipelineStats) -> None:
    data = await make_request("/token-boosts/top/v1", stats, redis_client)
    if data:
        await store_token_addresses(
            redis_client, f"{REDIS_PREFIX}top_boost_addresses", data, "top_boosts"
        )


async def aggregate_solana_tokens(redis_client: redis.Redis) -> List[Dict]:
    keys = [
        f"{REDIS_PREFIX}latest_boost_addresses",
        f"{REDIS_PREFIX}top_boost_addresses",
        f"{REDIS_PREFIX}token_profiles_addresses",
    ]

    # Gather all addresses concurrently
    address_tasks = [redis_client.smembers(key) for key in keys]
    all_addresses_lists = await asyncio.gather(*address_tasks)
    all_addresses = set()
    for addresses in all_addresses_lists:
        all_addresses.update(
            addr.decode() if isinstance(addr, bytes) else addr for addr in addresses
        )

    # Fetch metadata concurrently
    metadata_tasks = [
        get_token_metadata(redis_client, address) for address in all_addresses
    ]
    metadata_results = await asyncio.gather(*metadata_tasks)

    tokens_with_metadata = [
        {"address": addr, "metadata": meta}
        for addr, meta in zip(all_addresses, metadata_results)
    ]

    logger.info(
        f"Found {len(tokens_with_metadata)} unique token addresses with metadata"
    )
    return tokens_with_metadata
