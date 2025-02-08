# 🔍 DexWatch

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

DexWatch is a high-performance DEX analytics pipeline that tracks token performance, liquidity pairs, and market movements across multiple chains. Built with asyncio, and rotating proxies to bypass rate limiting and deliver high-resolution time-series data, it's designed for reliability and scale.

## ✨ Features

- 🚀 Asynchronous data collection from DexScreener API
- 🔄 Smart proxy rotation with geo-distributed endpoints
- 📊 Real-time token and pair analytics
- 💾 Persistent storage with Redis and ArangoDB
- 📈 Comprehensive chain and DEX statistics
- 🛡️ Built-in rate limiting and error handling
- 📝 Detailed logging and performance metrics

## 🏗️ Architecture

```
src/
├── __init__.py
├── config.py                 # Configuration and constants
├── db/                      # Database operations
├── api/                     # API clients
├── models/                  # Data models
├── services/                # Business logic
└── main.py                  # Entry point
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Redis
- ArangoDB
- Virtual environment (recommended)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/dexwatch.git
cd dexwatch
```

2. Create and activate virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # Unix
# or
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure your environment:

```python
# config.py

# Database Settings
REDIS_URL = "redis://localhost:6379"
ARANGO_URL = "http://localhost:8529"
DB_NAME = "dexwatch"

# Proxy Configuration
PROXY_USERNAME = "your_username" # (optional)
PROXY_PASSWORD = "your_password" # (optional)

# Performance Tuning
CONCURRENCY_LIMIT = 50
BATCH_SIZE = 30
```

### Usage

Run the pipeline:

```bash
python main.py
```

Monitor the analysis:

```bash
tail -f dexwatch.log
```

## 📊 Sample Output

```json
{
  "chain": "ethereum",
  "metrics": {
    "active_tokens": 156,
    "total_pairs": 892,
    "total_liquidity_usd": 25892156.42,
    "volume_24h_usd": 12456789.23,
    "avg_pairs_per_token": 5.7
  },
  "dex_distribution": {
    "uniswap_v2": { "pairs": 456, "share": 51.1 },
    "sushiswap": { "pairs": 234, "share": 26.2 }
  }
}
```

### Performance Tips

- Increase `max_concurrent` if using more proxies
- Adjust `batch_size` based on API rate limits
- Monitor proxy response times in logs
- Scale batch size with available memory

## 🕒 Scheduling

### Cron Setup

1. Create a wrapper script `run_dexwatch.sh`:

```bash
#!/bin/bash
cd /path/to/dexwatch
source venv/bin/activate
python main.py >> /var/log/dexwatch/pipeline.log 2>&1
```

2. Make executable:

```bash
chmod +x run_dexwatch.sh
```

3. Add cron job:

```bash
# Every 1 minute
*/1 * * * * /path/to/dexwatch/run_dexwatch.sh
```

## 🤝 Contributing

Contributions welcome! Check out our [Contributing Guide](CONTRIBUTING.md) to get started.

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a pull request

## 📝 License

MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Support

Join the Telegram: [t.me/IYKYKLabs](https://t.me/IYKYKLabs)
Follow Me on X: [x.com/eth_moon\_](https://x.com/eth_moon_)

## 🙏 Acknowledgments

- DexScreener API team for their excellent documentation
- And most of all our community. If you know, you know.

---

🌟 If this project helps you, please consider giving it a star!
