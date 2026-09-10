from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    supabase_url: str
    supabase_anon_key: str
    supabase_storage_bucket: str = "workspace-files"
    github_token: str | None = None
    cors_origins: str = "http://localhost:5173"
    max_file_size_mib: int = 20
    github_sync_cooldown_seconds: int = 30

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @property
    def cors_list(self) -> list[str]:
        return [x.strip().rstrip("/") for x in self.cors_origins.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
