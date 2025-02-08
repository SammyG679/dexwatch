import aiohttp
import asyncio
from aiohttp import BasicAuth
from typing import Dict, Optional, List
import json
from config import logger, DEXSCREENER_BASE_URL, PROXY_USERNAME, PROXY_PASSWORD
from models.stats import PipelineStats


# These are whitelisted by IP so replace these with you own
# I use 10: https://oxylabs.io/products/private-proxies but add more if you need higher frequency checks.


proxy_list = [
    {"port": 8001, "country": "NL", "assigned_ip": "158.115.253.96"},
    {"port": 8002, "country": "NL", "assigned_ip": "158.115.253.97"},
    {"port": 8003, "country": "NL", "assigned_ip": "158.115.253.98"},
    {"port": 8004, "country": "NL", "assigned_ip": "158.115.253.99"},
    {"port": 8005, "country": "DE", "assigned_ip": "109.207.132.182"},
    {"port": 8006, "country": "DE", "assigned_ip": "109.207.132.183"},
    {"port": 8007, "country": "DE", "assigned_ip": "109.207.132.192"},
    {"port": 8008, "country": "FR", "assigned_ip": "154.17.190.199"},
    {"port": 8009, "country": "FR", "assigned_ip": "154.17.190.20"},
    {"port": 8010, "country": "FR", "assigned_ip": "154.17.190.200"},
]


async def get_next_proxy(redis_client) -> Dict:
    counter = await redis_client.incr("dexscreener_proxy_counter")
    index = (counter - 1) % len(proxy_list)
    proxy = proxy_list[index]
    logger.debug(f"Selected proxy {proxy['assigned_ip']} (counter: {counter})")
    return proxy


async def make_request(
    endpoint: str, stats: PipelineStats, redis_client, retries=3
) -> Optional[Dict]:
    stats.requests_made += 1
    headers = {"Accept": "application/json", "User-Agent": "curl/7.68.0"}
    use_proxy = bool(PROXY_USERNAME and PROXY_PASSWORD)

    for attempt in range(retries):
        proxy_url = None
        proxy_auth = None
        proxy_info = None

        if use_proxy:
            proxy_info = await get_next_proxy(redis_client)
            proxy_url = f"socks5h://ddc.oxylabs.io:{proxy_info['port']}"
            proxy_auth = BasicAuth(f"user-{PROXY_USERNAME}", PROXY_PASSWORD)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{DEXSCREENER_BASE_URL}{endpoint}",
                    headers=headers,
                    proxy=proxy_url,
                    proxy_auth=proxy_auth,
                    timeout=10,
                ) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        stats.successful_requests += 1
                        return json.loads(response_text)
                    elif response.status == 429:
                        msg = (
                            f"Rate limited on proxy {proxy_info['assigned_ip']}"
                            if use_proxy
                            else "Rate limited on direct request"
                        )
                        logger.warning(f"{msg}, attempt {attempt + 1}")
                        await asyncio.sleep(1)
                    else:
                        msg = (
                            f"Status {response.status} on proxy {proxy_info['assigned_ip']}"
                            if use_proxy
                            else f"Status {response.status} on direct request"
                        )
                        logger.error(msg)
                        await asyncio.sleep(0.5)
        except Exception as e:
            msg = (
                f"Request failed on proxy {proxy_info['assigned_ip']}"
                if use_proxy
                else "Request failed on direct request"
            )
            logger.error(f"{msg}: {str(e)}")
            await asyncio.sleep(0.5)

    return None


async def old_make_request(
    endpoint: str, stats: PipelineStats, redis_client, retries=3
) -> Optional[Dict]:
    stats.requests_made += 1
    headers = {"Accept": "application/json", "User-Agent": "curl/7.68.0"}

    for attempt in range(retries):
        proxy_info = await get_next_proxy(redis_client)
        proxy_url = f"socks5h://ddc.oxylabs.io:{proxy_info['port']}"
        proxy_auth = BasicAuth(f"user-{PROXY_USERNAME}", PROXY_PASSWORD)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{DEXSCREENER_BASE_URL}{endpoint}",
                    headers=headers,
                    proxy=proxy_url,
                    proxy_auth=proxy_auth,
                    timeout=10,
                ) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        stats.successful_requests += 1
                        return json.loads(response_text)
                    elif response.status == 429:
                        logger.warning(
                            f"Rate limited on proxy {proxy_info['assigned_ip']}, attempt {attempt + 1}"
                        )
                        await asyncio.sleep(1)
                    else:
                        logger.error(
                            f"Status {response.status} on proxy {proxy_info['assigned_ip']}"
                        )
                        await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(
                f"Request failed on proxy {proxy_info['assigned_ip']}: {str(e)}"
            )
            await asyncio.sleep(0.5)

    return None


async def make_concurrent_requests(
    endpoints: List[str], stats: PipelineStats, redis_client, batch_size=10
) -> List[Dict]:
    results = []
    for i in range(0, len(endpoints), batch_size):
        batch = endpoints[i : i + batch_size]
        batch_tasks = [
            make_request(endpoint, stats, redis_client) for endpoint in batch
        ]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        results.extend([r for r in batch_results if not isinstance(r, Exception) and r])
        await asyncio.sleep(0.2)
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
    tokens: List[Dict], stats: PipelineStats, redis_client, batch_size=30
) -> List[Dict]:
    pair_tasks = []
    for token in tokens:
        chain_id = next(iter(token["metadata"].values())).get("chain_id", "solana")
        pair_tasks.append(
            fetch_token_pairs(token["address"], chain_id, stats, redis_client)
        )

    all_pairs = await asyncio.gather(*pair_tasks)
    return [p for p in all_pairs if p]
