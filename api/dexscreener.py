import aiohttp
import asyncio
from aiohttp import BasicAuth
from typing import Dict, Optional, List
import json
from config import logger, DEXSCREENER_BASE_URL
from models.stats import PipelineStats


async def make_request(
    endpoint: str, stats: PipelineStats, redis_client, retries=3
) -> Optional[Dict]:
    stats.requests_made += 1
    headers = {
        "Accept": "application/json",
        "User-Agent": "curl/7.68.0"
    }

    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{DEXSCREENER_BASE_URL}{endpoint}",
                    headers=headers,
                    timeout=10,
                ) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        stats.successful_requests += 1
                        return json.loads(response_text)
                    elif response.status == 429:
                        logger.warning(f"Rate limited, attempt {attempt + 1}")
                        # Exponential backoff for rate limits
                        await asyncio.sleep(2 ** attempt)
                    else:
                        logger.error(f"Request failed with status {response.status}")
                        await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            await asyncio.sleep(1)

    return None


async def make_concurrent_requests(
    endpoints: List[str], stats: PipelineStats, redis_client, batch_size=5
) -> List[Dict]:
    results = []
    for i in range(0, len(endpoints), batch_size):
        batch = endpoints[i : i + batch_size]
        batch_tasks = [
            make_request(endpoint, stats, redis_client) for endpoint in batch
        ]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        results.extend([r for r in batch_results if not isinstance(r, Exception) and r])
        # Increased delay between batches to avoid rate limiting
        await asyncio.sleep(1)
    return results


async def fetch_token_pairs(
    token_address: str, chain_id: str, stats: PipelineStats, redis_client
) -> List[Dict]:
    endpoint = f"/token-pairs/v1/{chain_id}/{token_address}"
    data = await make_request(endpoint, stats, redis_client)

    pairs = []
    if data and isinstance(data, list):
        pairs = [
            pair for pair in data if isinstance(pair, dict) and pair.get("pairAddress")
        ]
        logger.info(f"Found {len(pairs)} pairs for {token_address}")

    return pairs


async def fetch_pairs_batch(
    tokens: List[Dict], stats: PipelineStats, redis_client, batch_size=10
) -> List[Dict]:
    pair_tasks = []
    for token in tokens:
        chain_id = next(iter(token["metadata"].values())).get("chain_id", "solana")
        pair_tasks.append(
            fetch_token_pairs(token["address"], chain_id, stats, redis_client)
        )

    all_pairs = await asyncio.gather(*pair_tasks)
    return [p for p in all_pairs if p]

