import asyncio
import csv
from datetime import datetime
import redis.asyncio as redis
from arango import ArangoClient
from config import logger, REDIS_PREFIX
import json


async def export_data_to_csv():
    # Initialize connections
    redis_client = redis.from_url("redis://localhost:6379")
    arango_client = ArangoClient(hosts="http://localhost:8529")
    db = arango_client.db("jeettech", username="jeettech", password="jeettech_password")

    try:
        # Get current timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export pair data
        pair_filename = f"pair_data_{timestamp}.csv"
        pairs_cursor = db.collection("pair_data").all()
        
        with open(pair_filename, 'w', newline='') as csvfile:
            # First pair to get fields
            first_pair = next(pairs_cursor, None)
            if first_pair:
                # Get all fields from the first document
                fieldnames = ['timestamp', 'chain_id', 'token_address', 'pair_address', 
                            'dex_id', 'price_usd', 'liquidity_usd', 'volume_24h', 
                            'pair_created_at']
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # Write the first pair
                row = {
                    'timestamp': first_pair['timestamp'],
                    'chain_id': first_pair['chain_id'],
                    'token_address': first_pair['token_address'],
                    'pair_address': first_pair['pair_address'],
                    'dex_id': first_pair['dex_id'],
                    'price_usd': first_pair['metrics']['price_usd'],
                    'liquidity_usd': first_pair['metrics']['liquidity_usd'],
                    'volume_24h': first_pair['metrics']['volume_24h'],
                    'pair_created_at': first_pair['metrics']['pair_created_at']
                }
                writer.writerow(row)
                
                # Write the rest of the pairs
                for pair in pairs_cursor:
                    row = {
                        'timestamp': pair['timestamp'],
                        'chain_id': pair['chain_id'],
                        'token_address': pair['token_address'],
                        'pair_address': pair['pair_address'],
                        'dex_id': pair['dex_id'],
                        'price_usd': pair['metrics']['price_usd'],
                        'liquidity_usd': pair['metrics']['liquidity_usd'],
                        'volume_24h': pair['metrics']['volume_24h'],
                        'pair_created_at': pair['metrics']['pair_created_at']
                    }
                    writer.writerow(row)
        
        logger.info(f"Pair data exported to {pair_filename}")
        
        # Export token metadata
        token_filename = f"token_metadata_{timestamp}.csv"
        pattern = f"{REDIS_PREFIX}*:metadata:*"
        keys = await redis_client.keys(pattern)
        
        with open(token_filename, 'w', newline='') as csvfile:
            fieldnames = ['token_address', 'chain_id', 'source', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for key in keys:
                metadata = await redis_client.hgetall(key)
                if metadata:
                    row = {
                        'token_address': metadata[b'address'].decode(),
                        'chain_id': metadata[b'chain_id'].decode(),
                        'source': metadata[b'source'].decode(),
                        'timestamp': metadata[b'timestamp'].decode()
                    }
                    writer.writerow(row)
        
        logger.info(f"Token metadata exported to {token_filename}")

    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        raise
    finally:
        await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(export_data_to_csv())
