"""Typed application configuration.

All configuration flows through here so the rest of the codebase never touches
``os.environ`` directly. Settings fail fast at construction time if a required
value is missing for the selected environment.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    LOCAL = "local"
    DATABRICKS = "databricks"


class LLMProvider(str, Enum):
    GROQ = "groq"
    DATABRICKS = "databricks"
    FAKE = "fake"


class DatabricksSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DATABRICKS_", extra="ignore", populate_by_name=True
    )

    host: str = ""
    token: str = ""
    warehouse_id: str = Field(default="", alias="DATABRICKS_WAREHOUSE_ID")
    llm_endpoint: str = Field(default="databricks-claude-sonnet", alias="DATABRICKS_LLM_ENDPOINT")


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", populate_by_name=True)

    provider: LLMProvider = Field(default=LLMProvider.GROQ, alias="LLM_PROVIDER")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    groq_model_reasoning: str = Field(
        default="llama-3.3-70b-versatile", alias="GROQ_MODEL_REASONING"
    )


class Settings(BaseSettings):
    """Root settings object, composed of sub-settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True
    )

    environment: Environment = Field(default=Environment.LOCAL, alias="DE_AGENT_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=False, alias="LOG_JSON")

    require_approval: bool = Field(default=True, alias="REQUIRE_APPROVAL")
    target_catalog: str = Field(default="de_agent_dev", alias="TARGET_CATALOG")
    allow_create_catalog: bool = Field(default=False, alias="ALLOW_CREATE_CATALOG")
    max_retries: int = Field(default=3, alias="MAX_RETRIES")

    database_url: str = Field(default="", alias="DATABASE_URL")

    databricks: DatabricksSettings = Field(default_factory=DatabricksSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)

    @model_validator(mode="after")
    def _validate_environment(self) -> Settings:
        if self.environment is Environment.DATABRICKS:
            if not self.databricks.warehouse_id:
                raise ValueError("DATABRICKS_WAREHOUSE_ID is required in the databricks environment")
        if self.llm.provider is LLMProvider.GROQ and not self.llm.groq_api_key:
            # Not fatal locally — allow the app to boot and surface the error on first LLM use,
            # but warn loudly through validation when explicitly selected in databricks.
            if self.environment is Environment.DATABRICKS:
                raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq")
        return self

    @property
    def use_fakes(self) -> bool:
        """True when the app should wire in-memory fakes for external systems."""
        return self.environment is Environment.LOCAL and not self.databricks.host


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    return Settings()
