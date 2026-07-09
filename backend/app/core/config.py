from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Airflow Observer"
    demo_mode: bool = False
    database_url: str = "sqlite:///./airflow_observer.db"
    default_workspace_id: str = "demo-workspace"
    default_api_key: str | None = None
    cors_origins: str = ""
    slack_webhook_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_api_key(self) -> str:
        if self.default_api_key:
            return self.default_api_key
        if self.demo_mode:
            return "dev-observer-key"
        raise RuntimeError("DEFAULT_API_KEY must be set when DEMO_MODE=false.")

    def validate_runtime(self) -> None:
        if self.demo_mode:
            return
        missing = []
        if not self.database_url:
            missing.append("DATABASE_URL")
        if not self.default_api_key:
            missing.append("DEFAULT_API_KEY")
        if not self.cors_origin_list:
            missing.append("CORS_ORIGINS")
        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(f"Missing required self-hosted setting(s): {joined}.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
