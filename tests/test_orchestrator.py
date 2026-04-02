from collections.abc import Callable
from pathlib import Path
from typing import cast
from uuid import UUID

from video_translation_agent.domain.config import (
    InputConfig,
    PipelineConfig,
    RuntimeConfig,
)
from video_translation_agent.domain.enums import JobStatus, StageName
from video_translation_agent.domain.models import ArtifactRecord, JobSpec, SegmentRecord
from video_translation_agent.orchestrator import InProcessOrchestrator
from video_translation_agent.pipeline.context import (
    StageExecutionContext,
    StageExecutionResult,
)
from video_translation_agent.pipeline.registry import StageRegistry
from video_translation_agent.store import LocalMetadataStore
from video_translation_agent.workspace import JobWorkspace


def _build_registry(
    stage_order: list[StageName],
    calls: list[StageName],
) -> StageRegistry:
    registry = StageRegistry(stage_order=stage_order)

    def _handler_for(
        stage: StageName,
    ) -> Callable[[StageExecutionContext], StageExecutionResult]:
        def _handler(context: StageExecutionContext) -> StageExecutionResult:
            calls.append(context.stage)
            result = StageExecutionResult(
                artifacts=[
                    ArtifactRecord(
                        job_id=context.job.id,
                        stage_name=stage,
                        artifact_type=f"{stage.value}_output",
                        path=str(context.workspace.stage_dir(stage) / "output.txt"),
                    )
                ],
                meta={"attempt": context.attempt},
            )
            if stage == StageName.CAPTION:
                result.segments.append(
                    SegmentRecord(
                        job_id=context.job.id,
                        segment_key="seg_0001",
                        segment_index=0,
                        start_ms=0,
                        end_ms=1000,
                        source_text="原文",
                    )
                )
            return result

        return _handler

    for stage in stage_order:
        registry.register(stage, _handler_for(stage))

    return registry


def test_orchestrator_runs_registered_stages_in_order(tmp_path: Path) -> None:
    stage_order = cast(
        list[StageName],
        [
            StageName.INGEST,
            StageName.CAPTION,
            StageName.NORMALIZE,
            StageName.TRANSLATE,
            StageName.TTS,
            StageName.RENDER,
            StageName.QA,
        ],
    )
    calls: list[StageName] = []
    registry = _build_registry(stage_order=stage_order, calls=calls)
    orchestrator = InProcessOrchestrator(registry=registry)

    job_id = UUID("00000000-0000-0000-0000-000000000010")
    spec = JobSpec(
        id=job_id,
        status=cast(JobStatus, JobStatus.pending),
        current_stage=None,
        runtime=RuntimeConfig(
            profile="standalone",
            metadata_backend="sqlite",
            queue_backend="inline",
        ),
        input=InputConfig(
            video="/tmp/source.mp4",
            subtitle=None,
            source_lang="zh",
            target_lang="en",
        ),
        pipeline=PipelineConfig(
            mode="auto",
            caption_strategy="subtitle",
            translation_model="qwen2.5-14b-instruct",
            tts_model="melotts",
            voice_profile="en_female_neutral_01",
            mix_mode="duck",
            burn_subtitles=True,
            stage_order=stage_order,
        ),
        artifact_root=str(tmp_path / "jobs"),
    )

    job = orchestrator.run_job(spec)
    workspace = JobWorkspace(artifact_root=tmp_path / "jobs", job_id=job_id)
    store = LocalMetadataStore(workspace)
    stage_runs = store.list_stage_runs()

    assert calls == stage_order
    assert job.status == JobStatus.completed
    assert job.current_stage is None
    assert [run.stage_name for run in stage_runs] == stage_order
    assert [run.attempt for run in stage_runs] == [1, 1, 1, 1, 1, 1, 1]
    assert len(store.list_artifacts()) == len(stage_order)


def test_stage_rerun_creates_new_stage_run_attempt(tmp_path: Path) -> None:
    stage_order = cast(
        list[StageName],
        [StageName.INGEST, StageName.CAPTION, StageName.TRANSLATE],
    )
    calls: list[StageName] = []
    registry = _build_registry(stage_order=stage_order, calls=calls)
    orchestrator = InProcessOrchestrator(registry=registry)

    job_id = UUID("00000000-0000-0000-0000-000000000011")
    artifact_root = tmp_path / "jobs"
    spec = JobSpec(
        id=job_id,
        status=cast(JobStatus, JobStatus.pending),
        current_stage=None,
        runtime=RuntimeConfig(
            profile="standalone",
            metadata_backend="sqlite",
            queue_backend="inline",
        ),
        input=InputConfig(
            video="/tmp/source.mp4",
            subtitle=None,
            source_lang="zh",
            target_lang="en",
        ),
        pipeline=PipelineConfig(
            mode="auto",
            caption_strategy="subtitle",
            translation_model="qwen2.5-14b-instruct",
            tts_model="melotts",
            voice_profile="en_female_neutral_01",
            mix_mode="duck",
            burn_subtitles=True,
            stage_order=stage_order,
        ),
        artifact_root=str(artifact_root),
    )

    orchestrator.run_job(spec)
    rerun_job = orchestrator.rerun_stage(
        job_id=job_id,
        artifact_root=str(artifact_root),
        stage=cast(StageName, StageName.TRANSLATE),
    )

    store = LocalMetadataStore(JobWorkspace(artifact_root=artifact_root, job_id=job_id))
    rerun_runs = store.list_stage_runs(stage=cast(StageName, StageName.TRANSLATE))

    assert rerun_job.status == JobStatus.completed
    assert [run.attempt for run in rerun_runs] == [1, 2]
    assert calls == [
        StageName.INGEST,
        StageName.CAPTION,
        StageName.TRANSLATE,
        StageName.TRANSLATE,
    ]


def test_segment_rerun_records_history_without_overwrite(tmp_path: Path) -> None:
    stage_order = cast(
        list[StageName],
        [StageName.CAPTION, StageName.TRANSLATE, StageName.TTS],
    )
    calls: list[StageName] = []
    registry = _build_registry(stage_order=stage_order, calls=calls)
    orchestrator = InProcessOrchestrator(registry=registry)

    job_id = UUID("00000000-0000-0000-0000-000000000012")
    artifact_root = tmp_path / "jobs"
    spec = JobSpec(
        id=job_id,
        status=cast(JobStatus, JobStatus.pending),
        current_stage=None,
        runtime=RuntimeConfig(
            profile="standalone",
            metadata_backend="sqlite",
            queue_backend="inline",
        ),
        input=InputConfig(
            video="/tmp/source.mp4",
            subtitle=None,
            source_lang="zh",
            target_lang="en",
        ),
        pipeline=PipelineConfig(
            mode="auto",
            caption_strategy="subtitle",
            translation_model="qwen2.5-14b-instruct",
            tts_model="melotts",
            voice_profile="en_female_neutral_01",
            mix_mode="duck",
            burn_subtitles=True,
            stage_order=stage_order,
        ),
        artifact_root=str(artifact_root),
    )

    orchestrator.run_job(spec)
    orchestrator.rerun_segment(
        job_id=job_id,
        artifact_root=str(artifact_root),
        segment_key="seg_0001",
        reason="manual review",
        execute_stages=False,
    )

    store = LocalMetadataStore(JobWorkspace(artifact_root=artifact_root, job_id=job_id))
    rerun_history = store.list_segment_reruns()
    latest_segments = store.latest_segments()

    assert len(rerun_history) == 1
    assert rerun_history[0].segment_key == "seg_0001"
    assert [stage.value for stage in rerun_history[0].stages] == ["translate", "tts"]
    assert latest_segments["seg_0001"].rerun_count == 1
    assert latest_segments["seg_0001"].meta["last_rerun_reason"] == "manual review"
