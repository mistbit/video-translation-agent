from typing import cast

from video_translation_agent.domain.enums import StageName
from video_translation_agent.pipeline.bootstrap import build_default_stage_registry
from video_translation_agent.pipeline.context import (
    StageExecutionContext,
    StageExecutionResult,
)
from video_translation_agent.pipeline.registry import StageRegistry

STAGE_SEQUENCE: tuple[StageName, ...] = cast(
    tuple[StageName, ...],
    (
        StageName.INGEST,
        StageName.CAPTION,
        StageName.NORMALIZE,
        StageName.TRANSLATE,
        StageName.TTS,
        StageName.RENDER,
        StageName.QA,
    ),
)

__all__ = [
    "STAGE_SEQUENCE",
    "StageExecutionContext",
    "StageExecutionResult",
    "StageRegistry",
    "build_default_stage_registry",
]
