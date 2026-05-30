from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="AI Code Review Backend", validation_alias="APP_NAME")
    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", validation_alias="API_V1_PREFIX")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    port: int = Field(default=8000, validation_alias="PORT")
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    github_token: str | None = Field(default=None, validation_alias="GITHUB_TOKEN")
    github_api_proxy: str | None = Field(default=None, validation_alias="GITHUB_API_PROXY")
    review_api_token: str | None = Field(
        default=None,
        validation_alias="REVIEW_API_TOKEN",
    )
    rate_limit_requests: int = Field(default=30, validation_alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(
        default=60,
        validation_alias="RATE_LIMIT_WINDOW_SECONDS",
    )
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, validation_alias="OPENAI_BASE_URL")
    openai_model: str | None = Field(default=None, validation_alias="OPENAI_MODEL")
    deep_model: str = Field(default="deepseek-v4-pro", validation_alias="DEEP_MODEL")
    fast_model: str = Field(default="deepseek-v4-flash", validation_alias="FAST_MODEL")

    database_url: str = Field(
        default="mysql+aiomysql://root:@localhost:3306/code_review",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
    )
    jwt_secret: str = Field(default="", validation_alias="JWT_SECRET")
    jwt_access_token_expire_minutes: int = Field(
        default=15,
        validation_alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    jwt_refresh_token_expire_days: int = Field(
        default=30,
        validation_alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS",
    )

    @field_validator("port", mode="before")
    @classmethod
    def default_port_when_empty(cls, value: object) -> object:
        return 8000 if value == "" or value is None else value

    @field_validator("rate_limit_requests", mode="before")
    @classmethod
    def default_rate_limit_requests_when_empty(cls, value: object) -> object:
        return 30 if value == "" or value is None else value

    @field_validator("rate_limit_window_seconds", mode="before")
    @classmethod
    def default_rate_limit_window_when_empty(cls, value: object) -> object:
        return 60 if value == "" or value is None else value

    @field_validator(
        "github_token",
        "github_api_proxy",
        "review_api_token",
        "log_level",
        "openai_api_key",
        "openai_base_url",
        "openai_model",
        "deep_model",
        "fast_model",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("jwt_secret", mode="after")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
