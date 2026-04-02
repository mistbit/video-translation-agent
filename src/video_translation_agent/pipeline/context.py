from typing import Any

from pydantic import BaseModel, Field

from video_translation_agent.domain.enums import StageName
from video_translation_agent.domain import models as domain_models
from video_translation_agent.store import LocalMetadataStore
from video_translation_agent.workspace import JobWorkspace


class StageExecutionResult(BaseModel):
    artifacts: list[domain_models.ArtifactRecord] = Field(default_factory=list)
    segments: list[domain_models.SegmentRecord] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class StageExecutionContext(BaseModel):
    job: domain_models.JobManifest
    stage: StageName
    attempt: int
    workspace: JobWorkspace
    store: LocalMetadataStore
    trigger: str = "pipeline"
    trigger_meta: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}
