from datetime import datetime
import time
from typing import Any, Dict, Optional


def safe_float(value: Any) -> Optional[float]:
    """Safely convert value to float"""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def safe_int(value: Any) -> Optional[int]:
    """Safely convert value to int"""
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None

def days_forward_from_today(date_str: str) -> int:
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    today = datetime.today().date()
    delta = (target_date - today).days
    
    return delta

class LocationCache:
    """Simple in-memory cache for location data"""
    
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def _is_expired(self, timestamp: float) -> bool:
        return time.time() - timestamp > self.ttl_seconds
    
    def get(self, location: str) -> Optional[str]:
        """Get normalized location from cache"""
        cache_entry = self._cache.get(location.lower())
        if cache_entry and not self._is_expired(cache_entry['timestamp']):
            return cache_entry['normalized_location']
        return None
    
    def set(self, original_location: str, normalized_location: str):
        """Cache normalized location"""
        self._cache[original_location.lower()] = {
            'normalized_location': normalized_location,
            'timestamp': time.time()
        }
    
    def clear_expired(self):
        """Clear expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, value in self._cache.items()
            if current_time - value['timestamp'] > self.ttl_seconds
        ]
        for key in expired_keys:
            del self._cache[key]