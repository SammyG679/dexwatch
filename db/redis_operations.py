from typing import Dict, List, Optional
import json
from datetime import datetime, timezone
import redis.asyncio as redis
from config import logger, REDIS_PREFIX


async def store_token_addresses(
    redis_client: redis.Redis, key: str, data: List[Dict], source: str
) -> bool:
    """Store token addresses with full metadata in Redis"""
    try:
        await redis_client.delete(key)
        timestamp = datetime.now(timezone.utc).isoformat()
        stored_count = 0

        items = data if isinstance(data, list) else [data]

        for item in items:
            if isinstance(item, dict) and item.get("tokenAddress"):
                token_address = item["tokenAddress"]
                chain_id = item.get("chainId", "solana")

                metadata = {
                    "address": token_address,
                    "chain_id": chain_id,
                    "source": source,
                    "timestamp": timestamp,
                    "original_data": json.dumps(item),
                }

                await redis_client.hset(
                    f"{key}:metadata:{token_address}", mapping=metadata
                )
                await redis_client.sadd(key, token_address)
                stored_count += 1

        count = await redis_client.scard(key)
        logger.info(
            f"Stored {stored_count} token addresses in {key} from source {source}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to store token addresses: {str(e)}")
        return False


async def get_token_metadata(redis_client: redis.Redis, token_address: str) -> Dict:
    """Get complete metadata for a specific token address"""
    metadata = {}
    keys = [
        f"{REDIS_PREFIX}latest_boost_addresses",
        f"{REDIS_PREFIX}top_boost_addresses",
        f"{REDIS_PREFIX}token_profiles_addresses",
    ]

    for key in keys:
        metadata_key = f"{key}:metadata:{token_address}"
        token_data = await redis_client.hgetall(metadata_key)
        if token_data:
            source = token_data[b"source"].decode()
            metadata[source] = {
                "timestamp": token_data[b"timestamp"].decode(),
                "address": token_data[b"address"].decode(),
                "chain_id": token_data[b"chain_id"].decode(),
                "original_data": json.loads(token_data[b"original_data"].decode()),
            }

    return metadata


async def store_token_pairs_in_redis(
    token_address: str, pairs: List[Dict], redis_client: redis.Redis
) -> None:
    """Store token pairs data in Redis for analysis"""
    try:
        base_key = f"{REDIS_PREFIX}pairs:{token_address}"
        timestamp = datetime.now(timezone.utc).isoformat()

        # Store summary info
        summary = {
            "token_address": token_address,
            "total_pairs": str(len(pairs)),
            "dexes": json.dumps(
                [pair.get("dexId") for pair in pairs if pair.get("dexId")]
            ),
            "updated_at": timestamp,
        }

        summary_key = f"{base_key}:summary"
        await redis_client.hmset(summary_key, summary)

        # Store pair addresses
        addresses_key = f"{base_key}:addresses"
        pair_addresses = [
            pair.get("pairAddress") for pair in pairs if pair.get("pairAddress")
        ]
        if pair_addresses:
            await redis_client.sadd(addresses_key, *pair_addresses)

        # Store pair data
        for pair in pairs:
            pair_address = pair.get("pairAddress")
            if pair_address:
                metrics = {
                    "pair_address": pair_address,
                    "dex_id": pair.get("dexId", ""),
                    "price_usd": str(pair.get("priceUsd", "")),
                    "liquidity_usd": str(pair.get("liquidity", {}).get("usd", "")),
                    "volume_24h": str(pair.get("volume", {}).get("h24", "")),
                    "pair_created_at": str(pair.get("pairCreatedAt", "")),
                    "updated_at": timestamp,
                }

                metrics_key = f"{base_key}:pair:{pair_address}:metrics"
                await redis_client.hmset(metrics_key, metrics)

                full_key = f"{base_key}:pair:{pair_address}:data"
                await redis_client.set(full_key, json.dumps(pair))

    except Exception as e:
        logger.error(
            f"Failed to store pairs in Redis for token {token_address}: {str(e)}"
        )
        logger.error("Error details:", exc_info=True)
