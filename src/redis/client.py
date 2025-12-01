"""Redis client configuration and connection management."""
import os
from typing import Optional
import redis.asyncio as redis


class RedisClient:
    """Async Redis client singleton."""
    
    _instance: Optional['RedisClient'] = None
    _redis: Optional[redis.Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self):
        """Initialize Redis connection."""
        if self._redis is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self._redis = await redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10
            )
            print(f"✅ Connected to Redis: {redis_url}")
    
    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None
            print("❌ Disconnected from Redis")
    
    @property
    def client(self) -> redis.Redis:
        """Get Redis client instance."""
        if self._redis is None:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._redis
    
    async def pubsub(self):
        """Get a new PubSub instance."""
        return self.client.pubsub()


# Global instance
redis_client = RedisClient()
