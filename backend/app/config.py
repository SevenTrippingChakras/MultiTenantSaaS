from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "dev-secret-change-me"
MIN_PROD_SECRET_LEN = 32


class Settings(BaseSettings):
    """Reads config from environment variables (or a local .env file).

    MONGODB_URI is required (no default) so a missing DB config fails loudly
    at startup. The rest have safe defaults until their phase needs them.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    mongodb_uri: str
    mongodb_db: str = "aichat"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_expire_min: int = 60
    log_level: str = "INFO"
    max_message_chars: int = 16000
    cors_origins: list[str] = ["http://localhost:5173"]
    rate_limit_enabled: bool = True
    default_rate_limit: str = "200/minute"
    auth_rate_limit: str = "10/minute"
    chat_rate_limit: str = "30/minute"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        """Accept a comma-separated env string (CORS_ORIGINS=a,b) as a list."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @model_validator(mode="after")
    def _guard_prod_secret(self) -> "Settings":
        """In prod, refuse to boot with the default or a too-short JWT secret."""
        if self.env == "prod":
            if self.jwt_secret == DEFAULT_JWT_SECRET:
                raise ValueError("JWT_SECRET must be set in prod (not the default)")
            if len(self.jwt_secret) < MIN_PROD_SECRET_LEN:
                raise ValueError(
                    f"JWT_SECRET must be at least {MIN_PROD_SECRET_LEN} chars in prod"
                )
        return self


settings = Settings()
