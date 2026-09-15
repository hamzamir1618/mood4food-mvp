from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Dev-only placeholders. Startup warns loudly if either is still in use.
DEV_SESSION_SECRET = "dev-insecure-session-secret-change-me"
DEV_AUTH_SECRET = "dev-insecure-auth-secret-change-me"


class Settings(BaseSettings):
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str
    REDIS_URL: str = "redis://localhost:6379/0"
    GROQ_API_KEY: Optional[str] = None
    DEPLOY_MODE: str = "full"
    INTENT_EXTRACTOR: Optional[str] = None
    FRONTEND_ORIGIN: str = "http://localhost:8000,http://localhost:5173"
    SESSION_SECRET: str = DEV_SESSION_SECRET
    AUTH_SECRET: str = DEV_AUTH_SECRET
    AUTH_TOKEN_DAYS: int = 7
    AUTH_COOKIE_SECURE: bool = False
    # Sized for AuraDB Free's lower published limits; see docs/ACCOUNTS.md.
    GRAPH_NODE_LIMIT: int = 50_000
    GRAPH_RELATIONSHIP_LIMIT: int = 175_000
    GRAPH_HEADROOM: float = 0.9
    EVENTS_PER_USER: int = 200

    @model_validator(mode="after")
    def set_intent_extractor_default(self):
        if self.INTENT_EXTRACTOR is None:
            if self.DEPLOY_MODE in ("lite", "test"):
                self.INTENT_EXTRACTOR = "keyword"
            else:
                self.INTENT_EXTRACTOR = "groq"
        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
