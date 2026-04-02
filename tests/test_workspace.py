from pathlib import Path
from typing import cast
from uuid import UUID

from video_translation_agent.domain.config import (
    InputConfig,
    PipelineConfig,
    RuntimeConfig,
)
from video_translation_agent.domain.enums import JobStatus, StageName
from video_translation_agent.domain.models import JobSpec
from video_translation_agent.store import LocalMetadataStore
from video_translation_agent.workspace import JobWorkspace


def test_workspace_creates_expected_layout(tmp_path: Path) -> None:
    job_id = UUID("00000000-0000-0000-0000-000000000001")
    workspace = JobWorkspace(artifact_root=tmp_path / "jobs", job_id=job_id)

    workspace.create()

    assert workspace.root.exists()
    assert workspace.input_dir.exists()
    assert workspace.logs_dir.exists()
    for stage in StageName:
        assert workspace.stage_dir(stage).exists()


def test_workspace_persists_job_manifest(tmp_path: Path) -> None:
    job_id = UUID("00000000-0000-0000-0000-000000000002")
    workspace = JobWorkspace(artifact_root=tmp_path / "jobs", job_id=job_id)
    store = LocalMetadataStore(workspace)
    stage_order = cast(list[StageName], [StageName.INGEST, StageName.CAPTION])
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

    created = store.create_job(spec)
    loaded = store.load_job()

    assert workspace.job_manifest_path.exists()
    assert created.id == loaded.id
    assert loaded.pipeline.stage_order == [StageName.INGEST, StageName.CAPTION]
    assert loaded.artifact_root == str(tmp_path / "jobs")
