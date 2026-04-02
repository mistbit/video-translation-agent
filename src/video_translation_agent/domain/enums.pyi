from enum import Enum

class JobStatus(str, Enum):
    pending: JobStatus
    running: JobStatus
    paused: JobStatus
    completed: JobStatus
    failed: JobStatus
    cancelled: JobStatus

class StageName(str, Enum):
    INGEST: StageName
    CAPTION: StageName
    NORMALIZE: StageName
    TRANSLATE: StageName
    TTS: StageName
    RENDER: StageName
    QA: StageName
