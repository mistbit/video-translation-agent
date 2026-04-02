import hashlib
from pathlib import Path

from video_translation_agent.adapters.tts import LocalTTSAdapter, TTSClip
from video_translation_agent.domain.enums import StageName
from video_translation_agent.domain.models import (
    ArtifactRecord,
    SegmentRecord,
    SegmentStatus,
)
from video_translation_agent.pipeline.context import (
    StageExecutionContext,
    StageExecutionResult,
)


def build_tts_stage(adapter: LocalTTSAdapter | None = None):
    tts = adapter or LocalTTSAdapter()

    def _run(context: StageExecutionContext) -> StageExecutionResult:
        latest = context.store.latest_segments()
        ordered = sorted(latest.values(), key=lambda item: item.segment_index)
        stage_dir = context.workspace.stage_dir(StageName.TTS)
        stage_dir.mkdir(parents=True, exist_ok=True)

        artifacts: list[ArtifactRecord] = []
        updated_segments: list[SegmentRecord] = []
        timeline_clips: list[tuple[int, list[int]]] = []

        for segment in ordered:
            text = (segment.dubbing_text or segment.subtitle_text or "").strip()
            target_duration_ms = max(0, segment.end_ms - segment.start_ms)
            clip = tts.synthesize(
                text=text,
                voice_profile=context.job.pipeline.voice_profile,
                target_duration_ms=target_duration_ms,
            )

            segment_wav = stage_dir / f"{segment.segment_key}.wav"
            tts.write_wav(segment_wav, clip)
            artifacts.append(
                _artifact_for_file(
                    context=context,
                    path=segment_wav,
                    artifact_type="tts_segment_wav",
                    stage=StageName.TTS,
                    meta={
                        "segment_index": segment.segment_index,
                        "duration_ms": clip.duration_ms,
                    },
                )
            )

            updated = segment.model_copy(deep=True)
            updated.status = SegmentStatus.completed
            updated.tts_duration_ms = clip.duration_ms
            updated.tts_path = str(segment_wav)
            updated.meta = {
                **updated.meta,
                "tts": {
                    "voice_profile": context.job.pipeline.voice_profile,
                    "sample_rate_hz": clip.sample_rate_hz,
                },
            }
            updated_segments.append(updated)
            timeline_clips.append((segment.start_ms, clip.pcm16_samples))

        merged_samples = tts.merge_with_timeline(
            sample_rate_hz=tts.sample_rate_hz,
            timeline_clips=timeline_clips,
        )
        merged_duration_ms = int(len(merged_samples) * 1000 / tts.sample_rate_hz)
        merged_wav = stage_dir / "dub_en.wav"
        tts.write_wav(
            merged_wav,
            TTSClip(
                sample_rate_hz=tts.sample_rate_hz,
                duration_ms=merged_duration_ms,
                pcm16_samples=merged_samples,
            ),
        )
        artifacts.append(
            _artifact_for_file(
                context=context,
                path=merged_wav,
                artifact_type="tts_dub_wav",
                stage=StageName.TTS,
                meta={"duration_ms": merged_duration_ms, "segment_count": len(ordered)},
            )
        )

        return StageExecutionResult(
            artifacts=artifacts,
            segments=updated_segments,
            meta={
                "tts_segment_count": len(updated_segments),
                "dub_wav": str(merged_wav),
            },
        )

    return _run


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
