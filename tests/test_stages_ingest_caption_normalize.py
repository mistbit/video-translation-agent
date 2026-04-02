import json
import subprocess
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest

from video_translation_agent.adapters.media import MediaProbeAdapter
from video_translation_agent.adapters.asr import ASRSegment
from video_translation_agent.adapters.subtitles import SubtitleParser
from video_translation_agent.domain.config import (
    InputConfig,
    PipelineConfig,
    RuntimeConfig,
)
from video_translation_agent.domain.enums import JobStatus, StageName
from video_translation_agent.domain.models import JobSpec
from video_translation_agent.orchestrator import InProcessOrchestrator
from video_translation_agent.orchestrator import StageExecutionError
from video_translation_agent.pipeline.registry import StageRegistry
from video_translation_agent.stages.caption import build_caption_stage
from video_translation_agent.stages.ingest import build_ingest_stage
from video_translation_agent.stages.normalize import build_normalize_stage
from video_translation_agent.store import LocalMetadataStore
from video_translation_agent.workspace import JobWorkspace


def test_ingest_caption_normalize_pipeline_persists_artifacts_and_segments(
    tmp_path: Path,
) -> None:
    stage_order = cast(
        list[StageName],
        [StageName.INGEST, StageName.CAPTION, StageName.NORMALIZE],
    )
    job_id = UUID("00000000-0000-0000-0000-000000000099")
    artifact_root = tmp_path / "jobs"

    subtitle_path = tmp_path / "source.srt"
    subtitle_path.write_text(
        "1\n00:00:00,000 --> 00:00:01,200\nHello   hello\n\n"
        "2\n00:00:01,250 --> 00:00:02,800\n你好！！ 这是，测试。\n",
        encoding="utf-8",
    )

    def _ffprobe_runner(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout='{"streams":[{"codec_type":"video"},{"codec_type":"audio"}],"format":{"duration":"4.2","size":"5120","format_name":"mp4"}}',
            stderr="",
        )

    registry = StageRegistry(stage_order=stage_order)
    registry.register(
        StageName.INGEST,
        build_ingest_stage(MediaProbeAdapter(run_command=_ffprobe_runner)),
    )
    registry.register(StageName.CAPTION, build_caption_stage(SubtitleParser()))
    registry.register(StageName.NORMALIZE, build_normalize_stage())

    orchestrator = InProcessOrchestrator(registry=registry)
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
            video=str(tmp_path / "source.mp4"),
            subtitle=str(subtitle_path),
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

    job = orchestrator.run_job(spec)
    workspace = JobWorkspace(artifact_root=artifact_root, job_id=job_id)
    store = LocalMetadataStore(workspace)

    assert job.status == JobStatus.completed
    assert [run.stage_name for run in store.list_stage_runs()] == stage_order

    artifacts = store.list_artifacts()
    assert [artifact.stage_name for artifact in artifacts] == [
        StageName.INGEST,
        StageName.CAPTION,
        StageName.NORMALIZE,
        StageName.NORMALIZE,
    ]
    assert (workspace.stage_dir(StageName.INGEST) / "media_info.json").exists()
    assert (workspace.stage_dir(StageName.CAPTION) / "source_zh.raw.json").exists()
    assert (
        workspace.stage_dir(StageName.NORMALIZE) / "source_zh.cleaned.json"
    ).exists()
    assert (workspace.stage_dir(StageName.NORMALIZE) / "source_zh.srt").exists()

    latest = store.latest_segments()
    assert latest["seg_0001"].source_text == "Hello"
    assert latest["seg_0001"].start_ms == 0
    assert latest["seg_0001"].end_ms == 1200
    assert latest["seg_0002"].source_text == "你好! 这是,测试."

    history_entries = [
        json.loads(line)
        for line in workspace.segments_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(history_entries) == 4

    normalize_payload = json.loads(
        (workspace.stage_dir(StageName.NORMALIZE) / "source_zh.cleaned.json").read_text(
            encoding="utf-8"
        )
    )
    assert normalize_payload["segments"][0]["original_text"] == "Hello hello"
    assert normalize_payload["segments"][0]["normalized_text"] == "Hello"


def test_caption_stage_rejects_non_subtitle_strategy(tmp_path: Path) -> None:
    stage_order = cast(list[StageName], [StageName.CAPTION])
    job_id = UUID("00000000-0000-0000-0000-000000000100")
    artifact_root = tmp_path / "jobs"

    class FakeASRAdapter:
        def transcribe(self, *_args, **_kwargs):
            return [
                ASRSegment(start_ms=0, end_ms=1000, text="你好世界", confidence=0.5)
            ]

    registry = StageRegistry(stage_order=stage_order)
    registry.register(
        StageName.CAPTION,
        build_caption_stage(SubtitleParser(), FakeASRAdapter()),
    )
    orchestrator = InProcessOrchestrator(registry=registry)
    spec = JobSpec(
        id=job_id,
        status=cast(JobStatus, JobStatus.pending),
        current_stage=None,
        runtime=RuntimeConfig(),
        input=InputConfig(video=str(tmp_path / "source.mp4"), subtitle=None),
        pipeline=PipelineConfig(caption_strategy="asr", stage_order=stage_order),
        artifact_root=str(artifact_root),
    )

    job = orchestrator.run_job(spec)
    assert job.status == JobStatus.completed


def test_caption_stage_rejects_unknown_strategy(tmp_path: Path) -> None:
    stage_order = cast(list[StageName], [StageName.CAPTION])
    job_id = UUID("00000000-0000-0000-0000-000000000101")
    artifact_root = tmp_path / "jobs"

    registry = StageRegistry(stage_order=stage_order)
    registry.register(StageName.CAPTION, build_caption_stage(SubtitleParser()))
    orchestrator = InProcessOrchestrator(registry=registry)
    spec = JobSpec(
        id=job_id,
        status=cast(JobStatus, JobStatus.pending),
        current_stage=None,
        runtime=RuntimeConfig(),
        input=InputConfig(video=str(tmp_path / "source.mp4"), subtitle=None),
        pipeline=PipelineConfig(caption_strategy="unknown", stage_order=stage_order),
        artifact_root=str(artifact_root),
    )

    with pytest.raises(StageExecutionError, match="caption"):
        orchestrator.run_job(spec)
