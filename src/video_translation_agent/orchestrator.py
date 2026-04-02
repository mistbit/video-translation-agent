from datetime import UTC
from pathlib import Path
from typing import cast
from uuid import UUID

from video_translation_agent.domain.enums import JobStatus, StageName
from video_translation_agent.domain import models as domain_models
from video_translation_agent.pipeline.context import (
    StageExecutionContext,
    StageExecutionResult,
)
from video_translation_agent.pipeline.registry import StageRegistry
from video_translation_agent.store import LocalMetadataStore
from video_translation_agent.workspace import JobWorkspace


class StageExecutionError(RuntimeError):
    pass


class InProcessOrchestrator:
    def __init__(self, registry: StageRegistry):
        self.registry = registry

    def run_job(self, job_spec: domain_models.JobSpec) -> domain_models.JobManifest:
        workspace = JobWorkspace(
            artifact_root=Path(job_spec.artifact_root), job_id=job_spec.id
        )
        store = LocalMetadataStore(workspace)
        job = store.create_job(job_spec)
        return self._run_stages(
            job=job, store=store, workspace=workspace, stages=job.pipeline.stage_order
        )

    def rerun_stage(
        self, job_id: UUID, artifact_root: str, stage: StageName
    ) -> domain_models.JobManifest:
        workspace = JobWorkspace(artifact_root=Path(artifact_root), job_id=job_id)
        store = LocalMetadataStore(workspace)
        job = store.load_job()
        return self._run_stages(
            job=job,
            store=store,
            workspace=workspace,
            stages=[stage],
            trigger="stage_rerun",
        )

    def rerun_segment(
        self,
        *,
        job_id: UUID,
        artifact_root: str,
        segment_key: str,
        stages: list[StageName] | None = None,
        reason: str | None = None,
        execute_stages: bool = False,
    ) -> domain_models.JobManifest:
        workspace = JobWorkspace(artifact_root=Path(artifact_root), job_id=job_id)
        store = LocalMetadataStore(workspace)
        job = store.load_job()
        rerun_stages = cast(
            list[StageName], stages or [StageName.TRANSLATE, StageName.TTS]
        )

        rerun_record = domain_models.SegmentRerunRecord(
            job_id=job.id,
            segment_key=segment_key,
            stages=rerun_stages,
            reason=reason,
            meta={"execute_stages": execute_stages},
            requested_at=domain_models.utc_now(),
        )
        store.append_segment_rerun(rerun_record)

        segments = store.latest_segments()
        existing = segments.get(segment_key)
        if existing is None:
            existing = domain_models.SegmentRecord(
                job_id=job.id,
                segment_key=segment_key,
                segment_index=-1,
                status=domain_models.SegmentStatus.pending,
                start_ms=0,
                end_ms=0,
            )

        existing.rerun_count += 1
        existing.meta = {
            **existing.meta,
            "last_rerun_reason": reason,
            "last_rerun_stages": [item.value for item in rerun_stages],
            "last_rerun_at": rerun_record.requested_at.astimezone(UTC).isoformat(),
        }
        store.append_segment(existing, event="rerun")

        if execute_stages:
            return self._run_stages(
                job=job,
                store=store,
                workspace=workspace,
                stages=rerun_stages,
                trigger="segment_rerun",
                trigger_meta={"segment_key": segment_key},
            )

        return job

    def _run_stages(
        self,
        *,
        job: domain_models.JobManifest,
        store: LocalMetadataStore,
        workspace: JobWorkspace,
        stages: list[StageName],
        trigger: str = "pipeline",
        trigger_meta: dict[str, str] | None = None,
    ) -> domain_models.JobManifest:
        store.update_job_status(
            status=cast(JobStatus, JobStatus.running),
            current_stage=job.current_stage,
        )
        for stage in stages:
            job = self._execute_stage(
                job=store.load_job(),
                stage=stage,
                store=store,
                workspace=workspace,
                trigger=trigger,
                trigger_meta=trigger_meta or {},
            )

        final_job = store.load_job()
        if final_job.status == cast(JobStatus, JobStatus.running):
            final_job.status = cast(JobStatus, JobStatus.completed)
            final_job.current_stage = None
            store.save_job(final_job)
        return final_job

    def _execute_stage(
        self,
        *,
        job: domain_models.JobManifest,
        stage: StageName,
        store: LocalMetadataStore,
        workspace: JobWorkspace,
        trigger: str,
        trigger_meta: dict[str, str],
    ) -> domain_models.JobManifest:
        handler = self.registry.get(stage)
        attempt = store.next_stage_attempt(stage)
        started_at = domain_models.utc_now()
        store.update_job_status(
            status=cast(JobStatus, JobStatus.running),
            current_stage=stage,
        )

        try:
            context = StageExecutionContext(
                job=store.load_job(),
                stage=stage,
                attempt=attempt,
                workspace=workspace,
                store=store,
                trigger=trigger,
                trigger_meta=trigger_meta,
            )
            result = handler(context) or StageExecutionResult()
            for artifact in result.artifacts:
                store.append_artifact(artifact)
            for segment in result.segments:
                store.append_segment(segment)

            stage_run = domain_models.StageRunRecord(
                job_id=job.id,
                stage_name=stage,
                status=domain_models.StageRunStatus.completed,
                attempt=attempt,
                started_at=started_at,
                finished_at=store.load_job().updated_at,
                duration_ms=self._duration_ms(started_at, store.load_job().updated_at),
                meta={"trigger": trigger, **trigger_meta, **(result.meta or {})},
            )
            store.append_stage_run(stage_run)
            return store.load_job()
        except Exception as exc:
            failed_job = store.update_job_status(
                status=cast(JobStatus, JobStatus.failed),
                current_stage=stage,
                error_message=str(exc),
            )
            failed_stage_run = domain_models.StageRunRecord(
                job_id=job.id,
                stage_name=stage,
                status=domain_models.StageRunStatus.failed,
                attempt=attempt,
                started_at=started_at,
                finished_at=failed_job.updated_at,
                duration_ms=self._duration_ms(started_at, failed_job.updated_at),
                error_type=type(exc).__name__,
                error_message=str(exc),
                meta={"trigger": trigger, **trigger_meta},
            )
            store.append_stage_run(failed_stage_run)
            raise StageExecutionError(f"Stage '{stage.value}' failed") from exc

    @staticmethod
    def _duration_ms(started_at, finished_at) -> int:
        return int((finished_at - started_at).total_seconds() * 1000)
