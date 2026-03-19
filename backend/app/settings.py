from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Email LLM API"
    app_env: str = Field(default="development")
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-5.4-mini")

    smtp_host: str = Field(default="")
    smtp_port: int = Field(default=587)
    smtp_username: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_use_tls: bool = Field(default=True)
    smtp_from_email: str = Field(default="")
    smtp_from_name: str = Field(default="")

    allow_origins: str = Field(default="*")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        if self.allow_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
