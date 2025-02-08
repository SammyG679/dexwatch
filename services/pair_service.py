import asyncio
import redis.asyncio as redis
from arango import ArangoClient
from typing import List, Dict
from config import logger
from models.stats import PipelineStats
from api.dexscreener import fetch_token_pairs, fetch_pairs_batch
from db.redis_operations import store_token_pairs_in_redis
from db.arango_operations import store_pair_data
from services.token_service import aggregate_solana_tokens


async def process_pair_batch(
    batch: List[Dict], redis_client: redis.Redis, db: ArangoClient, stats: PipelineStats
) -> None:
    # Process each token in the batch concurrently
    pair_tasks = []
    for token in batch:
        address = token["address"]
        metadata = token["metadata"]
        source_data = next(iter(metadata.values()))
        chain_id = source_data.get("chain_id", "solana")

        task = asyncio.create_task(
            fetch_token_pairs(address, chain_id, stats, redis_client)
        )
        pair_tasks.append((token, task))

    # Store results concurrently
    store_tasks = []
    for token, task in pair_tasks:
        try:
            pairs = await task
            if pairs:
                address = token["address"]
                metadata = token["metadata"]
                chain_id = next(iter(metadata.values())).get("chain_id", "solana")

                store_tasks.extend(
                    [
                        store_token_pairs_in_redis(address, pairs, redis_client),
                        store_pair_data(db, address, chain_id, pairs, metadata),
                    ]
                )
                stats.tokens_processed += 1
        except Exception as e:
            logger.error(f"Error processing token {token['address']}: {str(e)}")

    if store_tasks:
        await asyncio.gather(*store_tasks)


async def process_solana_pairs(
    redis_client: redis.Redis, db: ArangoClient, stats: PipelineStats
) -> None:
    tokens = await aggregate_solana_tokens(redis_client)
    total_tokens = len(tokens)
    batch_size = 30  # Increased batch size for parallel processing
    total_batches = (total_tokens + batch_size - 1) // batch_size

    for i in range(0, total_tokens, batch_size):
        batch = tokens[i : i + batch_size]
        await process_pair_batch(batch, redis_client, db, stats)

        current_batch = i // batch_size + 1
        progress = (current_batch / total_batches) * 100
        logger.info(
            f"Processed batch {current_batch}/{total_batches} ({progress:.1f}%)"
        )

        # Small delay between batches to prevent overwhelming
        await asyncio.sleep(0.1)


# Bulk processing function for maximum throughput
async def bulk_process_pairs(
    redis_client: redis.Redis,
    db: ArangoClient,
    stats: PipelineStats,
    concurrency_limit: int = 50,
) -> None:
    tokens = await aggregate_solana_tokens(redis_client)
    semaphore = asyncio.Semaphore(concurrency_limit)

    async def process_with_semaphore(token):
        async with semaphore:
            address = token["address"]
            metadata = token["metadata"]
            chain_id = next(iter(metadata.values())).get("chain_id", "solana")

            try:
                pairs = await fetch_token_pairs(address, chain_id, stats, redis_client)
                if pairs:
                    await asyncio.gather(
                        store_token_pairs_in_redis(address, pairs, redis_client),
                        store_pair_data(db, address, chain_id, pairs, metadata),
                    )
                    stats.tokens_processed += 1
            except Exception as e:
                logger.error(f"Failed to process token {address}: {str(e)}")

    tasks = [process_with_semaphore(token) for token in tokens]
    await asyncio.gather(*tasks)
