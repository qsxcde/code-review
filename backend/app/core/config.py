from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="AI Code Review Backend", validation_alias="APP_NAME")
    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", validation_alias="API_V1_PREFIX")

    port: int = Field(default=8000, validation_alias="PORT")
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    github_token: str | None = Field(default=None, validation_alias="GITHUB_TOKEN")
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, validation_alias="OPENAI_BASE_URL")
    openai_model: str | None = Field(default=None, validation_alias="OPENAI_MODEL")

    @field_validator("port", mode="before")
    @classmethod
    def default_port_when_empty(cls, value: object) -> object:
        return 8000 if value == "" or value is None else value

    @field_validator(
        "github_token",
        "openai_api_key",
        "openai_base_url",
        "openai_model",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        return None if value == "" else value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
