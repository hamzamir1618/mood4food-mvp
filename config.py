from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str
    REDIS_URL: str = "redis://localhost:6379/0"
    INTENT_EXTRACTOR: str = "keyword"
    FRONTEND_ORIGIN: str = "http://localhost:8000"
    DEPLOY_MODE: str = "full"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
