import hashlib
import shutil
from pathlib import Path

from video_translation_agent.adapters.render import LocalRenderAdapter
from video_translation_agent.domain.enums import StageName
from video_translation_agent.domain.models import ArtifactRecord
from video_translation_agent.pipeline.context import (
    StageExecutionContext,
    StageExecutionResult,
)


def build_render_stage(adapter: LocalRenderAdapter | None = None):
    renderer = adapter or LocalRenderAdapter()

    def _run(context: StageExecutionContext) -> StageExecutionResult:
        latest = context.store.latest_segments()
        ordered = sorted(latest.values(), key=lambda item: item.segment_index)
        stage_dir = context.workspace.stage_dir(StageName.RENDER)
        stage_dir.mkdir(parents=True, exist_ok=True)

        translate_dir = context.workspace.stage_dir(StageName.TRANSLATE)
        translated_subtitle = translate_dir / "en_subtitle.srt"
        output_subtitle = stage_dir / "output_en.srt"
        if translated_subtitle.exists():
            shutil.copyfile(translated_subtitle, output_subtitle)
        else:
            output_subtitle.write_text(_to_srt_from_segments(ordered), encoding="utf-8")

        tts_dub = context.workspace.stage_dir(StageName.TTS) / "dub_en.wav"
        if not tts_dub.exists():
            raise FileNotFoundError(f"missing TTS merged output: {tts_dub}")

        source_video = Path(context.job.input.video)
        mix_wav = stage_dir / "mix.wav"
        final_video = stage_dir / "final_en.mp4"
        render_result = renderer.render(
            source_video=source_video,
            dub_audio=tts_dub,
            subtitle_srt=output_subtitle,
            mix_output=mix_wav,
            final_video_output=final_video,
            burn_subtitles=context.job.pipeline.burn_subtitles,
        )

        artifacts = [
            _artifact_for_file(
                context=context,
                path=output_subtitle,
                artifact_type="render_subtitle_srt",
                stage=StageName.RENDER,
                meta={"count": len(ordered)},
            ),
            _artifact_for_file(
                context=context,
                path=mix_wav,
                artifact_type="render_mix_wav",
                stage=StageName.RENDER,
                meta={"fallback": int(render_result.used_fallback)},
            ),
            _artifact_for_file(
                context=context,
                path=final_video,
                artifact_type="render_final_video",
                stage=StageName.RENDER,
                meta={"fallback": int(render_result.used_fallback)},
            ),
        ]

        return StageExecutionResult(
            artifacts=artifacts,
            meta={
                "render_used_ffmpeg": render_result.used_ffmpeg,
                "render_used_fallback": render_result.used_fallback,
                "render_warnings": render_result.warnings,
                "final_video": str(final_video),
                "output_subtitle": str(output_subtitle),
            },
        )

    return _run


def _to_srt_from_segments(segments) -> str:
    lines: list[str] = []
    for idx, segment in enumerate(segments, start=1):
        text = segment.subtitle_text or segment.source_text or ""
        lines.extend(
            [
                str(idx),
                f"{_ms_to_srt_ts(segment.start_ms)} --> {_ms_to_srt_ts(segment.end_ms)}",
                text,
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _ms_to_srt_ts(value: int) -> str:
    hours = value // 3_600_000
    minutes = (value % 3_600_000) // 60_000
    seconds = (value % 60_000) // 1000
    millis = value % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _artifact_for_file(
    *,
    context: StageExecutionContext,
    path: Path,
    artifact_type: str,
    stage: StageName,
    meta: dict[str, int],
) -> ArtifactRecord:
    content = path.read_bytes()
    return ArtifactRecord(
        job_id=context.job.id,
        stage_name=stage,
        artifact_type=artifact_type,
        path=str(path),
        checksum=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        meta=meta,
    )
