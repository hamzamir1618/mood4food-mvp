import json
from typing import Optional

import redis

from config import settings

_redis_client = None


def get_redis() -> redis.Redis:
    """Returns a singleton Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def save_contract(session_id: str, contract_name: str, data: dict, ttl_seconds: int = 900) -> None:
    """
    Saves a JSON-serializable contract dict to Redis under the key '{session_id}:{contract_name}'.
    TTL defaults to 15 minutes (900 seconds).
    """
    client = get_redis()
    key = f"{session_id}:{contract_name}"
    client.set(key, json.dumps(data), ex=ttl_seconds)


def load_contract(session_id: str, contract_name: str) -> Optional[dict]:
    """
    Loads and deserializes a contract from Redis.
    Returns None if the contract does not exist or expired.
    """
    client = get_redis()
    key = f"{session_id}:{contract_name}"
    raw = client.get(key)
    if raw:
        return json.loads(raw)
    return None
