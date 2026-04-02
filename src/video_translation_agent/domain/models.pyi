from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

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
    id: UUID
    status: JobStatus
    current_stage: StageName | None = None
    runtime: RuntimeConfig
    input: InputConfig
    pipeline: PipelineConfig
    artifact_root: str = "jobs"

class StageRunStatus(str, Enum):
    pending: StageRunStatus
    running: StageRunStatus
    completed: StageRunStatus
    failed: StageRunStatus
    cancelled: StageRunStatus

class SegmentStatus(str, Enum):
    pending: SegmentStatus
    running: SegmentStatus
    completed: SegmentStatus
    failed: SegmentStatus

class JobManifest(BaseModel):
    id: UUID
    status: JobStatus
    current_stage: StageName | None = None
    runtime: RuntimeConfig
    input: InputConfig
    pipeline: PipelineConfig
    artifact_root: str = "jobs"
    error_message: str | None = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_spec(cls, spec: JobSpec) -> "JobManifest": ...

class SegmentRecord(BaseModel):
    id: UUID | None = None
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
    qa_flags: list[str] = []
    rerun_count: int = 0
    meta: dict[str, Any] = {}
    created_at: datetime | None = None
    updated_at: datetime | None = None

class ArtifactRecord(BaseModel):
    id: UUID | None = None
    job_id: UUID
    stage_name: StageName | None = None
    artifact_type: str
    path: str
    checksum: str | None = None
    size_bytes: int | None = None
    meta: dict[str, Any] = {}
    created_at: datetime | None = None

class StageRunRecord(BaseModel):
    id: UUID | None = None
    job_id: UUID
    stage_name: StageName
    status: StageRunStatus
    attempt: int = 1
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    error_type: str | None = None
    error_message: str | None = None
    meta: dict[str, Any] = {}

class SegmentRerunRecord(BaseModel):
    id: UUID | None = None
    job_id: UUID
    segment_key: str
    stages: list[StageName]
    reason: str | None = None
    meta: dict[str, Any] = {}
    requested_at: datetime

def utc_now() -> datetime: ...
