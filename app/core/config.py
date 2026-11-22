from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AutoTestReport Hub"
    app_env: Literal["development", "test", "production"] = "development"
    secret_key: SecretStr = Field(min_length=32)
    database_url: str = "sqlite:///./data/autotestreport.db"
    access_token_expire_minutes: int = Field(default=30, gt=0, le=1440)


@lru_cache
def get_settings() -> Settings:
    return Settings()
