from loguru import logger

class RateLimiter:
    def __init__(self):
        self.remaining = None
        self.used = None
        
    def update_from_headers(self, headers: dict):
        """Update rate limit status from API headers"""
        if not headers:
            return
            
        # The Odds API headers
        if 'x-requests-remaining' in headers:
            try:
                self.remaining = int(headers['x-requests-remaining'])
                logger.debug(f"API Quota: {self.remaining} requests remaining")
            except (ValueError, TypeError):
                pass
                
        if 'x-requests-used' in headers:
            try:
                self.used = int(headers['x-requests-used'])
            except (ValueError, TypeError):
                pass

    @property
    def is_quota_exhausted(self) -> bool:
        """Check if we should stop scanning due to quota limits"""
        if self.remaining is not None and self.remaining <= 0:
            return True
        return False