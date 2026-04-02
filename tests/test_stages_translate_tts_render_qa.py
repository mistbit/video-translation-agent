import json
import subprocess
from pathlib import Path
from typing import cast
from uuid import UUID

from video_translation_agent.adapters.media import MediaProbeAdapter
from video_translation_agent.adapters.qa import QAAdapter
from video_translation_agent.adapters.render import LocalRenderAdapter
from video_translation_agent.adapters.subtitles import SubtitleParser
from video_translation_agent.adapters.tts import LocalTTSAdapter, TTSClip
from video_translation_agent.adapters.translation import (
    LocalTranslationAdapter,
    MediaTranslationSegment,
    TranslationResult,
)
from video_translation_agent.domain.config import (
    InputConfig,
    PipelineConfig,
    RuntimeConfig,
)
from video_translation_agent.domain.enums import JobStatus, StageName
from video_translation_agent.domain.models import JobSpec
from video_translation_agent.orchestrator import InProcessOrchestrator
from video_translation_agent.pipeline.bootstrap import build_default_stage_registry
from video_translation_agent.pipeline.registry import StageRegistry
from video_translation_agent.stages.caption import build_caption_stage
from video_translation_agent.stages.normalize import build_normalize_stage
from video_translation_agent.stages.qa import build_qa_stage
from video_translation_agent.stages.render import build_render_stage
from video_translation_agent.stages.translate import build_translate_stage
from video_translation_agent.stages.tts import build_tts_stage
from video_translation_agent.store import LocalMetadataStore
from video_translation_agent.workspace import JobWorkspace


def test_translate_stage_persists_dual_track_outputs(tmp_path: Path) -> None:
    class FakeMediaTranslation(LocalTranslationAdapter):
        def translate_media(self, media_path, *, source_lang="zh"):
            return [
                MediaTranslationSegment(
                    start_ms=0,
                    end_ms=2000,
                    text="Hello world.",
                    confidence=0.9,
                ),
                MediaTranslationSegment(
                    start_ms=2000,
                    end_ms=4000,
                    text="Hello team.",
                    confidence=0.9,
                ),
            ]

    stage_order = cast(
        list[StageName],
        [StageName.CAPTION, StageName.NORMALIZE, StageName.TRANSLATE],
    )
    job_id = UUID("00000000-0000-0000-0000-000000000201")
    subtitle_path = tmp_path / "source.srt"
    subtitle_path.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\n你好 世界\n\n2\n00:00:02,000 --> 00:00:04,000\nhello team\n",
        encoding="utf-8",
    )
    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"fake-video")

    registry = StageRegistry(stage_order=stage_order)
    registry.register(StageName.CAPTION, build_caption_stage(SubtitleParser()))
    registry.register(StageName.NORMALIZE, build_normalize_stage())
    registry.register(
        StageName.TRANSLATE, build_translate_stage(FakeMediaTranslation())
    )

    orchestrator = InProcessOrchestrator(registry=registry)
    job = orchestrator.run_job(
        JobSpec(
            id=job_id,
            status=cast(JobStatus, JobStatus.pending),
            input=InputConfig(video=str(source_video), subtitle=str(subtitle_path)),
            pipeline=PipelineConfig(stage_order=stage_order),
            runtime=RuntimeConfig(),
            artifact_root=str(tmp_path / "jobs"),
        )
    )

    workspace = JobWorkspace(artifact_root=tmp_path / "jobs", job_id=job_id)
    store = LocalMetadataStore(workspace)
    latest = store.latest_segments()

    assert job.status == JobStatus.completed
    assert latest["seg_0001"].subtitle_text == "Hello, world."
    assert latest["seg_0001"].dubbing_text is not None
    assert (workspace.stage_dir(StageName.TRANSLATE) / "en_subtitle.json").exists()
    assert (workspace.stage_dir(StageName.TRANSLATE) / "en_subtitle.srt").exists()
    assert (workspace.stage_dir(StageName.TRANSLATE) / "en_dub_text.json").exists()
    assert (workspace.stage_dir(StageName.TRANSLATE) / "en_dub_text.txt").exists()


def test_tts_stage_generates_segment_and_merged_audio(tmp_path: Path) -> None:
    class FakeSpeechTTS(LocalTTSAdapter):
        def _synthesize_with_macos_voice(
            self, *, text: str, voice_profile: str, target_duration_ms: int
        ) -> TTSClip | None:
            duration_ms = max(500, target_duration_ms or 500)
            sample_count = max(1, int(self.sample_rate_hz * duration_ms / 1000))
            return TTSClip(
                sample_rate_hz=self.sample_rate_hz,
                duration_ms=duration_ms,
                pcm16_samples=[512] * sample_count,
            )

    stage_order = cast(
        list[StageName],
        [StageName.CAPTION, StageName.NORMALIZE, StageName.TRANSLATE, StageName.TTS],
    )
    job_id = UUID("00000000-0000-0000-0000-000000000202")
    subtitle_path = tmp_path / "source.srt"
    subtitle_path.write_text(
        "1\n00:00:00,000 --> 00:00:03,000\nhello world\n\n2\n00:00:04,000 --> 00:00:07,000\nhello again\n",
        encoding="utf-8",
    )
    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"fake-video")

    registry = StageRegistry(stage_order=stage_order)
    registry.register(StageName.CAPTION, build_caption_stage(SubtitleParser()))
    registry.register(StageName.NORMALIZE, build_normalize_stage())
    registry.register(
        StageName.TRANSLATE, build_translate_stage(LocalTranslationAdapter())
    )
    registry.register(StageName.TTS, build_tts_stage(FakeSpeechTTS()))

    orchestrator = InProcessOrchestrator(registry=registry)
    orchestrator.run_job(
        JobSpec(
            id=job_id,
            status=cast(JobStatus, JobStatus.pending),
            input=InputConfig(video=str(source_video), subtitle=str(subtitle_path)),
            pipeline=PipelineConfig(stage_order=stage_order),
            runtime=RuntimeConfig(),
            artifact_root=str(tmp_path / "jobs"),
        )
    )

    workspace = JobWorkspace(artifact_root=tmp_path / "jobs", job_id=job_id)
    store = LocalMetadataStore(workspace)
    latest = store.latest_segments()

    assert (workspace.stage_dir(StageName.TTS) / "seg_0001.wav").exists()
    assert (workspace.stage_dir(StageName.TTS) / "seg_0002.wav").exists()
    assert (workspace.stage_dir(StageName.TTS) / "dub_en.wav").exists()
    assert latest["seg_0001"].tts_path is not None
    assert latest["seg_0001"].tts_duration_ms is not None


def test_render_stage_outputs_final_subtitle_and_video_artifacts(
    tmp_path: Path,
) -> None:
    stage_order = cast(
        list[StageName],
        [
            StageName.CAPTION,
            StageName.NORMALIZE,
            StageName.TRANSLATE,
            StageName.TTS,
            StageName.RENDER,
        ],
    )
    job_id = UUID("00000000-0000-0000-0000-000000000203")
    subtitle_path = tmp_path / "source.srt"
    subtitle_path.write_text(
        "1\n00:00:00,000 --> 00:00:03,000\nhello render\n",
        encoding="utf-8",
    )
    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"video-bytes")

    registry = StageRegistry(stage_order=stage_order)
    registry.register(StageName.CAPTION, build_caption_stage(SubtitleParser()))
    registry.register(StageName.NORMALIZE, build_normalize_stage())
    registry.register(
        StageName.TRANSLATE, build_translate_stage(LocalTranslationAdapter())
    )
    registry.register(StageName.TTS, build_tts_stage())
    registry.register(
        StageName.RENDER,
        build_render_stage(
            LocalRenderAdapter(prefer_ffmpeg=False, allow_copy_fallback=True)
        ),
    )

    orchestrator = InProcessOrchestrator(registry=registry)
    orchestrator.run_job(
        JobSpec(
            id=job_id,
            status=cast(JobStatus, JobStatus.pending),
            input=InputConfig(video=str(source_video), subtitle=str(subtitle_path)),
            pipeline=PipelineConfig(stage_order=stage_order),
            runtime=RuntimeConfig(),
            artifact_root=str(tmp_path / "jobs"),
        )
    )

    workspace = JobWorkspace(artifact_root=tmp_path / "jobs", job_id=job_id)
    final_video = workspace.stage_dir(StageName.RENDER) / "final_en.mp4"
    output_subtitle = workspace.stage_dir(StageName.RENDER) / "output_en.srt"
    mix_wav = workspace.stage_dir(StageName.RENDER) / "mix.wav"

    assert output_subtitle.exists()
    assert mix_wav.exists()
    assert final_video.exists()
    assert final_video.read_bytes() == source_video.read_bytes()


def test_qa_stage_generates_reports_and_pauses_on_missing_translation(
    tmp_path: Path,
) -> None:
    class EmptyFirstTranslation(LocalTranslationAdapter):
        def translate_segment(
            self, text: str, *, segment_index: int
        ) -> TranslationResult:
            if segment_index == 0:
                return TranslationResult(
                    subtitle_text="",
                    dubbing_text="",
                    risk_flags=["missing_translation"],
                    confidence=0.0,
                )
            return super().translate_segment(text, segment_index=segment_index)

    stage_order = cast(
        list[StageName],
        [StageName.CAPTION, StageName.NORMALIZE, StageName.TRANSLATE, StageName.QA],
    )
    job_id = UUID("00000000-0000-0000-0000-000000000204")
    subtitle_path = tmp_path / "source.srt"
    subtitle_path.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\n你好\n\n2\n00:00:02,000 --> 00:00:04,000\nhello\n",
        encoding="utf-8",
    )
    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"fake-video")

    registry = StageRegistry(stage_order=stage_order)
    registry.register(StageName.CAPTION, build_caption_stage(SubtitleParser()))
    registry.register(StageName.NORMALIZE, build_normalize_stage())
    registry.register(
        StageName.TRANSLATE, build_translate_stage(EmptyFirstTranslation())
    )
    registry.register(StageName.QA, build_qa_stage(QAAdapter()))

    orchestrator = InProcessOrchestrator(registry=registry)
    job = orchestrator.run_job(
        JobSpec(
            id=job_id,
            status=cast(JobStatus, JobStatus.pending),
            input=InputConfig(video=str(source_video), subtitle=str(subtitle_path)),
            pipeline=PipelineConfig(stage_order=stage_order),
            runtime=RuntimeConfig(),
            artifact_root=str(tmp_path / "jobs"),
        )
    )

    workspace = JobWorkspace(artifact_root=tmp_path / "jobs", job_id=job_id)
    store = LocalMetadataStore(workspace)
    report_json = workspace.stage_dir(StageName.QA) / "qa_report.json"
    report_md = workspace.stage_dir(StageName.QA) / "qa_report.md"
    payload = json.loads(report_json.read_text(encoding="utf-8"))

    assert job.status == JobStatus.paused
    assert report_json.exists()
    assert report_md.exists()
    assert payload["blocking"] is True
    assert "missing_translation" in payload["blocking_reasons"]
    assert "render_missing_artifacts" in payload["blocking_reasons"]
    assert "missing_translation" in store.latest_segments()["seg_0001"].qa_flags


def test_full_seven_stage_pipeline_with_default_registry(tmp_path: Path) -> None:
    subtitle_path = tmp_path / "source.srt"
    subtitle_path.write_text(
        "1\n00:00:00,000 --> 00:00:03,000\nhello world\n\n2\n00:00:03,000 --> 00:00:06,000\nhello team\n",
        encoding="utf-8",
    )
    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"video-bytes")

    def _ffprobe_runner(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout='{"streams":[{"codec_type":"video"},{"codec_type":"audio"}],"format":{"duration":"6.0","size":"12000","format_name":"mp4"}}',
            stderr="",
        )

    registry = build_default_stage_registry(
        media_probe_adapter=MediaProbeAdapter(run_command=_ffprobe_runner),
        render_adapter=LocalRenderAdapter(
            prefer_ffmpeg=False, allow_copy_fallback=True
        ),
    )
    orchestrator = InProcessOrchestrator(registry=registry)
    job_id = UUID("00000000-0000-0000-0000-000000000205")
    job = orchestrator.run_job(
        JobSpec(
            id=job_id,
            status=cast(JobStatus, JobStatus.pending),
            input=InputConfig(video=str(source_video), subtitle=str(subtitle_path)),
            pipeline=PipelineConfig(stage_order=list(StageName)),
            runtime=RuntimeConfig(),
            artifact_root=str(tmp_path / "jobs"),
        )
    )

    workspace = JobWorkspace(artifact_root=tmp_path / "jobs", job_id=job_id)
    store = LocalMetadataStore(workspace)
    stage_runs = store.list_stage_runs()

    assert job.status == JobStatus.completed
    assert [run.stage_name for run in stage_runs] == list(StageName)
    assert (workspace.stage_dir(StageName.TRANSLATE) / "en_subtitle.srt").exists()
    assert (workspace.stage_dir(StageName.TTS) / "dub_en.wav").exists()
    assert (workspace.stage_dir(StageName.RENDER) / "final_en.mp4").exists()
    assert (workspace.stage_dir(StageName.QA) / "qa_report.json").exists()
