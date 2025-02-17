import json
import redis.asyncio as redis
from config import logger, REDIS_PREFIX


async def analyze_pairs():
    redis_client = redis.from_url("redis://localhost:6379")

    try:
        token_chains = {}
        boost_keys = [
            f"{REDIS_PREFIX}latest_boost_addresses",
            f"{REDIS_PREFIX}top_boost_addresses",
            f"{REDIS_PREFIX}token_profiles_addresses",
        ]

        for key in boost_keys:
            token_addresses = await redis_client.smembers(key)
            for token in token_addresses:
                token = token.decode()
                metadata_key = f"{key}:metadata:{token}"
                metadata = await redis_client.hgetall(metadata_key)
                if metadata and b"chain_id" in metadata:
                    chain_id = metadata[b"chain_id"].decode()
                    token_chains[token] = chain_id

        pattern = f"{REDIS_PREFIX}pairs:*:summary"
        all_tokens = await redis_client.keys(pattern)

        total_pairs = 0
        chain_counts = {}
        chain_liquidity = {}
        chain_volume = {}
        chain_dex_pairs = {}
        chain_active_tokens = {}

        for token_key in all_tokens:
            token_address = token_key.decode().split(":")[2]
            addresses_key = f"{REDIS_PREFIX}pairs:{token_address}:addresses"
            pair_addresses = await redis_client.smembers(addresses_key)

            for pair_address in pair_addresses:
                pair_address = pair_address.decode()
                data_key = (
                    f"{REDIS_PREFIX}pairs:{token_address}:pair:{pair_address}:data"
                )
                full_data = await redis_client.get(data_key)

                if full_data:
                    pair_data = json.loads(full_data)
                    chain_id = pair_data.get("chainId", "unknown")
                    dex_id = pair_data.get("dexId", "unknown")

                    chain_counts[chain_id] = chain_counts.get(chain_id, 0) + 1
                    chain_active_tokens[chain_id] = chain_active_tokens.get(
                        chain_id, set()
                    )
                    chain_active_tokens[chain_id].add(token_address)

                    liquidity = float(pair_data.get("liquidity", {}).get("usd", 0) or 0)
                    volume = float(pair_data.get("volume", {}).get("h24", 0) or 0)

                    chain_liquidity[chain_id] = (
                        chain_liquidity.get(chain_id, 0) + liquidity
                    )
                    chain_volume[chain_id] = chain_volume.get(chain_id, 0) + volume

                    chain_dex_pairs.setdefault(chain_id, {})
                    chain_dex_pairs[chain_id][dex_id] = (
                        chain_dex_pairs[chain_id].get(dex_id, 0) + 1
                    )

                    total_pairs += 1

        logger.info("\n=== Chain ID Pair Distribution ===")
        for chain_id, count in sorted(
            chain_counts.items(), key=lambda x: x[1], reverse=True
        ):
            active_tokens = len(chain_active_tokens.get(chain_id, set()))
            pair_percentage = (count / total_pairs) * 100 if total_pairs else 0

            logger.info(f"\nChain: {chain_id}")
            logger.info(f"  Active Tokens: {active_tokens}")
            logger.info(f"  Total Pairs: {count} ({pair_percentage:.1f}% of all pairs)")
            logger.info(f"  Total Liquidity: ${chain_liquidity.get(chain_id, 0):,.2f}")
            logger.info(f"  24h Volume: ${chain_volume.get(chain_id, 0):,.2f}")
            logger.info(f"  Avg Pairs per Token: {count/active_tokens:.1f}")

            if chain_id in chain_dex_pairs:
                logger.info("  DEX Distribution:")
                for dex_id, dex_count in sorted(
                    chain_dex_pairs[chain_id].items(), key=lambda x: x[1], reverse=True
                ):
                    percentage = (dex_count / count) * 100
                    logger.info(f"    {dex_id}: {dex_count} pairs ({percentage:.1f}%)")

    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        logger.error("Error details:", exc_info=True)
    finally:
        await redis_client.aclose()
