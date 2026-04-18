from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url_sync: str = Field(
        default="postgresql+psycopg2://cgd:cgd_dev_change_me@127.0.0.1:5432/cgd",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://127.0.0.1:6379/0", validation_alias="REDIS_URL")
    celery_broker_url: str = Field(
        default="redis://127.0.0.1:6379/0",
        validation_alias="CELERY_BROKER_URL",
    )
    celery_result_backend: str = Field(
        default="redis://127.0.0.1:6379/0",
        validation_alias="CELERY_RESULT_BACKEND",
    )

    semantics_version: int = Field(default=1, validation_alias="SEMANTICS_VERSION")
    matrix_version: int = Field(default=1, validation_alias="MATRIX_VERSION")
    shadow_mode: bool = Field(default=True, validation_alias="SHADOW_MODE")

    #: Consecutive evaluations without a matching candidate before auto-resolve (gap lifecycle).
    auto_resolve_miss_threshold: int = Field(default=2, validation_alias="AUTO_RESOLVE_MISS_THRESHOLD")

    telegram_bot_token: str = Field(default="", validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", validation_alias="TELEGRAM_CHAT_ID")

    defillama_base_url: str = "https://api.llama.fi"
    http_timeout_s: float = 30.0
    http_max_retries: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
