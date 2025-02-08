import uuid
from datetime import datetime, timezone
from typing import Dict, List
from arango import ArangoClient
from config import logger


async def store_pair_data(
    db: ArangoClient,
    token_address: str,
    chain_id: str,
    pairs: List[Dict],
    token_metadata: Dict,
) -> None:
    """Store pair data in ArangoDB"""
    timestamp = datetime.now(timezone.utc).isoformat()

    for pair in pairs:
        document = {
            "_key": str(uuid.uuid4()),
            "timestamp": timestamp,
            "chain_id": chain_id,
            "token_address": token_address,
            "token_metadata": token_metadata,
            "pair_address": pair["pairAddress"],
            "dex_id": pair.get("dexId"),
            "pair_data": pair,
            "metrics": {
                "price_usd": pair.get("priceUsd"),
                "liquidity_usd": pair.get("liquidity", {}).get("usd"),
                "volume_24h": pair.get("volume", {}).get("h24"),
                "pair_created_at": pair.get("pairCreatedAt"),
            },
        }

        try:
            logger.info(f"Storing pair data for {pair['pairAddress']}")
            db.collection("pair_data").insert(document)
        except Exception as e:
            logger.error(f"Failed to store pair data: {str(e)}")
