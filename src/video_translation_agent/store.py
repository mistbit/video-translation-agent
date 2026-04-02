import json
from pathlib import Path
from typing import Any

from video_translation_agent.domain.enums import JobStatus, StageName
from video_translation_agent.domain import models as domain_models
from video_translation_agent.workspace import JobWorkspace


class LocalMetadataStore:
    def __init__(self, workspace: JobWorkspace):
        self.workspace = workspace

    def create_job(self, job_spec: domain_models.JobSpec) -> domain_models.JobManifest:
        now = domain_models.utc_now()
        job = domain_models.JobManifest(
            id=job_spec.id,
            status=job_spec.status,
            current_stage=job_spec.current_stage,
            runtime=job_spec.runtime,
            input=job_spec.input,
            pipeline=job_spec.pipeline,
            artifact_root=job_spec.artifact_root,
            created_at=now,
            updated_at=now,
        )
        self.workspace.create()
        self.save_job(job)
        return job

    def save_job(self, job: domain_models.JobManifest) -> None:
        job.updated_at = domain_models.utc_now()
        self._write_json(self.workspace.job_manifest_path, job.model_dump(mode="json"))

    def load_job(self) -> domain_models.JobManifest:
        payload = self._read_json(self.workspace.job_manifest_path)
        return domain_models.JobManifest.model_validate(payload)

    def update_job_status(
        self,
        *,
        status: JobStatus,
        current_stage: StageName | None,
        error_message: str | None = None,
    ) -> domain_models.JobManifest:
        job = self.load_job()
        job.status = status
        job.current_stage = current_stage
        job.error_message = error_message
        self.save_job(job)
        return job

    def append_stage_run(self, stage_run: domain_models.StageRunRecord) -> None:
        self._append_jsonl(
            self.workspace.stage_runs_path, stage_run.model_dump(mode="json")
        )

    def list_stage_runs(
        self, stage: StageName | None = None
    ) -> list[domain_models.StageRunRecord]:
        records = [
            domain_models.StageRunRecord.model_validate(item)
            for item in self._read_jsonl(self.workspace.stage_runs_path)
        ]
        if stage is None:
            return records
        return [record for record in records if record.stage_name == stage]

    def next_stage_attempt(self, stage: StageName) -> int:
        return len(self.list_stage_runs(stage)) + 1

    def append_artifact(self, artifact: domain_models.ArtifactRecord) -> None:
        self._append_jsonl(
            self.workspace.artifacts_path, artifact.model_dump(mode="json")
        )

    def list_artifacts(self) -> list[domain_models.ArtifactRecord]:
        return [
            domain_models.ArtifactRecord.model_validate(item)
            for item in self._read_jsonl(self.workspace.artifacts_path)
        ]

    def append_segment(
        self, segment: domain_models.SegmentRecord, event: str = "upsert"
    ) -> None:
        segment.updated_at = domain_models.utc_now()
        payload = {
            "event": event,
            "recorded_at": domain_models.utc_now().isoformat(),
            "segment": segment.model_dump(mode="json"),
        }
        self._append_jsonl(self.workspace.segments_path, payload)

    def latest_segments(self) -> dict[str, domain_models.SegmentRecord]:
        latest: dict[str, domain_models.SegmentRecord] = {}
        for entry in self._read_jsonl(self.workspace.segments_path):
            segment = domain_models.SegmentRecord.model_validate(entry["segment"])
            latest[segment.segment_key] = segment
        return latest

    def append_segment_rerun(self, rerun: domain_models.SegmentRerunRecord) -> None:
        self._append_jsonl(
            self.workspace.segment_reruns_path, rerun.model_dump(mode="json")
        )

    def list_segment_reruns(self) -> list[domain_models.SegmentRerunRecord]:
        return [
            domain_models.SegmentRerunRecord.model_validate(item)
            for item in self._read_jsonl(self.workspace.segment_reruns_path)
        ]

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file_obj:
            file_obj.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        items: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as file_obj:
            for line in file_obj:
                cleaned = line.strip()
                if not cleaned:
                    continue
                items.append(json.loads(cleaned))
        return items
