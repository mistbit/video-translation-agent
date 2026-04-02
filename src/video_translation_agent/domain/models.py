from datetime import UTC, datetime
from enum import Enum
from typing import Any, Generic, TypeVar, cast
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from video_translation_agent.domain.config import (
    InputConfig,
    PipelineConfig,
    RuntimeConfig,
)
from video_translation_agent.domain.enums import JobStatus, StageName

T = TypeVar("T")


class ApiEnvelope(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: T | None = None


class JobSpec(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    status: JobStatus = cast(JobStatus, "pending")
    current_stage: StageName | None = None
    runtime: RuntimeConfig = Field(
        default_factory=lambda: RuntimeConfig.model_validate({})
    )
    input: InputConfig
    pipeline: PipelineConfig = Field(
        default_factory=lambda: PipelineConfig.model_validate({})
    )
    artifact_root: str = "jobs"


def utc_now() -> datetime:
    return datetime.now(UTC)


class StageRunStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class SegmentStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class JobManifest(BaseModel):
    id: UUID
    status: JobStatus = cast(JobStatus, "pending")
    current_stage: StageName | None = None
    runtime: RuntimeConfig = Field(
        default_factory=lambda: RuntimeConfig.model_validate({})
    )
    input: InputConfig
    pipeline: PipelineConfig = Field(
        default_factory=lambda: PipelineConfig.model_validate({})
    )
    artifact_root: str = "jobs"
    error_message: str | None = None
    retry_count: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @classmethod
    def from_spec(cls, spec: JobSpec) -> "JobManifest":
        now = utc_now()
        return cls(
            id=spec.id,
            status=spec.status,
            current_stage=spec.current_stage,
            runtime=spec.runtime,
            input=spec.input,
            pipeline=spec.pipeline,
            artifact_root=spec.artifact_root,
            created_at=now,
            updated_at=now,
        )


class SegmentRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    segment_key: str
    segment_index: int
    status: SegmentStatus = SegmentStatus.pending
    start_ms: int
    end_ms: int
    source_text: str | None = None
    subtitle_text: str | None = None
    dubbing_text: str | None = None
    asr_confidence: float | None = None
    ocr_confidence: float | None = None
    translation_confidence: float | None = None
    tts_duration_ms: int | None = None
    tts_path: str | None = None
    qa_flags: list[str] = Field(default_factory=list)
    rerun_count: int = 0
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ArtifactRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    stage_name: StageName | None = None
    artifact_type: str
    path: str
    checksum: str | None = None
    size_bytes: int | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class StageRunRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    stage_name: StageName
    status: StageRunStatus
    attempt: int = 1
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    error_type: str | None = None
    error_message: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class SegmentRerunRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    segment_key: str
    stages: list[StageName] = Field(default_factory=list)
    reason: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    requested_at: datetime = Field(default_factory=utc_now)
