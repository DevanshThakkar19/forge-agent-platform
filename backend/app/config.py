"""Process settings. Environment variables use the FORGE_ prefix."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FORGE_",
        env_file=(".env", "../.env"),
        extra="ignore",
    )

    api_key: str = "dev-api-key"
    database_url: str = "postgresql://forge:forge@localhost:5432/forge"
    sandbox_root: Path = Path("var/sandbox")
    corpus_dir: Path = Path("corpus")
    tool_transport: Literal["stdio", "inprocess"] = "stdio"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    max_graph_steps: int = Field(default=5, ge=1, le=8)
    retrieve_limit: int = Field(default=4, ge=1, le=8)
    tool_timeout_s: float = Field(default=5.0, gt=0, le=60)
    baseline_path: Path = Path("evals/baselines/current.json")
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    planner: Literal["keyword", "local"] = "keyword"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "mistral"
    planner_timeout_s: float = Field(default=60.0, gt=0, le=120)

    @field_validator("api_key")
    @classmethod
    def api_key_must_be_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("FORGE_API_KEY must not be empty")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
