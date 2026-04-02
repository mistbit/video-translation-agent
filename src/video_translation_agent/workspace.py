from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from video_translation_agent.domain.enums import StageName


@dataclass(frozen=True)
class JobWorkspace:
    artifact_root: Path
    job_id: UUID

    @property
    def root(self) -> Path:
        return self.artifact_root / str(self.job_id)

    @property
    def input_dir(self) -> Path:
        return self.root / "input"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def job_manifest_path(self) -> Path:
        return self.root / "job.json"

    @property
    def stage_runs_path(self) -> Path:
        return self.root / "stage_runs.jsonl"

    @property
    def artifacts_path(self) -> Path:
        return self.root / "artifacts.jsonl"

    @property
    def segments_path(self) -> Path:
        return self.root / "segments.jsonl"

    @property
    def segment_reruns_path(self) -> Path:
        return self.root / "segment_reruns.jsonl"

    def stage_dir(self, stage: StageName) -> Path:
        return self.root / stage.value

    def create(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        for stage in StageName:
            self.stage_dir(stage).mkdir(parents=True, exist_ok=True)
