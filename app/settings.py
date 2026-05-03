from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ENV_AGENT_", extra="ignore")

    db_path: Path = Path("data/env_agent.db")
    upload_dir: Path = Path("uploads")


settings = Settings()
