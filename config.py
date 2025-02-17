import logging
from utils.config import config

# API Configuration
DEXSCREENER_BASE_URL = "https://api.dexscreener.com"
REDIS_PREFIX = "dexscreener:"

# Logging Configuration
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - [%(funcName)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
