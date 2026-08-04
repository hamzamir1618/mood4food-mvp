import json
from typing import Any, Optional, Union

import redis
from pydantic import BaseModel

from config import settings
from tier_1.contracts.schemas import CandidateEvaluation, DecisionBlueprint, GroundedIntent

_redis_client = None


def get_redis() -> redis.Redis:
    """Returns a singleton Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def save_contract(
    session_id: str,
    contract_name: str,
    data: Union[BaseModel, dict, list, Any],
    ttl_seconds: int = 900,
) -> None:
    """
    Saves a contract to Redis under the key '{session_id}:{contract_name}'.
    TTL defaults to 15 minutes (900 seconds).
    """
    client = get_redis()
    key = f"{session_id}:{contract_name}"

    if isinstance(data, BaseModel):
        json_str = data.model_dump_json()
    else:
        # Fallback to json.dumps if passing a raw dict during tests
        json_str = json.dumps(data)

    client.set(key, json_str, ex=ttl_seconds)


def load_contract(session_id: str, contract_name: str) -> Optional[Union[BaseModel, dict, Any]]:
    """
    Loads and deserializes a contract from Redis into a Pydantic model.
    Returns None if the contract does not exist or expired.
    """
    client = get_redis()
    key = f"{session_id}:{contract_name}"
    raw = client.get(key)

    if not raw:
        return None

    if contract_name == "grounded_intent":
        return GroundedIntent.model_validate_json(raw)
    elif contract_name == "candidate_evaluation":
        return CandidateEvaluation.model_validate_json(raw)
    elif contract_name == "decision_blueprint":
        return DecisionBlueprint.model_validate_json(raw)

    return json.loads(raw)
