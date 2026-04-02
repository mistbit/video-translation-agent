from enum import Enum


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class StageName(str, Enum):
    INGEST = "ingest"
    CAPTION = "caption"
    NORMALIZE = "normalize"
    TRANSLATE = "translate"
    TTS = "tts"
    RENDER = "render"
    QA = "qa"
