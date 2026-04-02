from pydantic import BaseModel, Field

from video_translation_agent.domain.enums import StageName


class RuntimeConfig(BaseModel):
    profile: str = "standalone"
    metadata_backend: str = "sqlite"
    queue_backend: str = "inline"


class InputConfig(BaseModel):
    video: str
    subtitle: str | None = None
    source_lang: str = "zh"
    target_lang: str = "en"


class PipelineConfig(BaseModel):
    mode: str = "auto"
    caption_strategy: str = "auto"
    asr_model: str = "tiny"
    translation_model: str = "qwen2.5-14b-instruct"
    tts_model: str = "melotts"
    voice_profile: str = "en_female_neutral_01"
    mix_mode: str = "duck"
    burn_subtitles: bool = True
    stage_order: list[StageName] = Field(
        default_factory=lambda: [
            StageName.INGEST,
            StageName.CAPTION,
            StageName.NORMALIZE,
            StageName.TRANSLATE,
            StageName.TTS,
            StageName.RENDER,
            StageName.QA,
        ]
    )
