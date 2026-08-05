from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
def health_check():
    """Health check endpoint: pings Neo4j and Redis."""
    from neo4j import GraphDatabase

    from config import settings
    from tier_1.contracts.session_store import get_redis

    health_status = {"neo4j": "ok", "redis": "ok"}
    status_code = 200

    # Ping Neo4j
    try:
        with GraphDatabase.driver(
            settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        ) as driver:
            driver.verify_connectivity()
    except Exception:
        health_status["neo4j"] = "unreachable"
        status_code = 503

    # Ping Redis
    try:
        redis_client = get_redis()
        redis_client.ping()
    except Exception:
        health_status["redis"] = "unreachable"
        status_code = 503

    if status_code == 200:
        return {"status": "ok", **health_status}
    else:
        return JSONResponse(status_code=503, content={"status": "error", **health_status})
