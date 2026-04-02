from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VTA_", extra="ignore")

    app_name: str = "video-translation-agent"
    env: str = "local"
    api_prefix: str = "/api/v1"
    artifact_root: str = "jobs"
    default_source_lang: str = "zh"
    default_target_lang: str = "en"
    log_level: str = Field(default="INFO")


settings = AppSettings()
