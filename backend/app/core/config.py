from functools import lru_cache
from pathlib import Path
from secrets import token_urlsafe

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Extra Book Word API"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./app.db"
    storage_root: str = "storage"
    jwt_secret_key: str = token_urlsafe(32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7

    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    @property
    def books_storage_dir(self) -> Path:
        return Path(self.storage_root) / "books"

    @property
    def results_storage_dir(self) -> Path:
        return Path(self.storage_root) / "results"

    @property
    def backend_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def ecdict_path(self) -> Path:
        return self.repo_root / "ecdict.csv"

    @property
    def coca_words_path(self) -> Path:
        return self.repo_root / "词根词缀记单词.csv"


@lru_cache
def get_settings() -> Settings:
    return Settings()
