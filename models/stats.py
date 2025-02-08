import time
from config import logger


class PipelineStats:
    def __init__(self):
        self.requests_made = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.tokens_processed = 0
        self.start_time = time.time()

    def log_summary(self):
        elapsed_time = time.time() - self.start_time
        logger.info(f"""
Pipeline Summary:
----------------
Total Runtime: {elapsed_time:.2f} seconds
Total Requests: {self.requests_made}
Successful Requests: {self.successful_requests}
Failed Requests: {self.failed_requests}
Tokens Processed: {self.tokens_processed}
Success Rate: {(self.successful_requests/self.requests_made*100 if self.requests_made else 0):.2f}%
""")
