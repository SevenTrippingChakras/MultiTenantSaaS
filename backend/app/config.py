from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Reads config from environment variables (or a local .env file).

    MONGODB_URI is required (no default) so a missing DB config fails loudly
    at startup. The rest have safe defaults until their phase needs them.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongodb_uri: str
    mongodb_db: str = "aichat"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    jwt_secret: str = "dev-secret-change-me"
    jwt_expire_min: int = 60


settings = Settings()
