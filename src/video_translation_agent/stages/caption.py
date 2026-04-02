import hashlib
import json
from pathlib import Path

from video_translation_agent.adapters.subtitles import (
    CaptionSourceUnsupportedError,
    SubtitleParser,
)
from video_translation_agent.adapters.asr import ASRAdapter, FasterWhisperASRAdapter
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


def build_caption_stage(
    parser: SubtitleParser | None = None,
    asr_adapter: ASRAdapter | None = None,
):
    subtitle_parser = parser or SubtitleParser()
    speech_transcriber = asr_adapter or FasterWhisperASRAdapter()

    def _run(context: StageExecutionContext) -> StageExecutionResult:
        strategy = context.job.pipeline.caption_strategy.lower()
        subtitle_path = context.job.input.subtitle

        if subtitle_path:
            cues = subtitle_parser.parse(Path(subtitle_path))
            caption_source = "subtitle"
            source_meta = {"subtitle_path": subtitle_path}
            segments: list[SegmentRecord] = []
            for idx, cue in enumerate(cues):
                segment_key = f"seg_{idx + 1:04d}"
                segments.append(
                    SegmentRecord(
                        job_id=context.job.id,
                        segment_key=segment_key,
                        segment_index=idx,
                        status=SegmentStatus.completed,
                        start_ms=cue.start_ms,
                        end_ms=cue.end_ms,
                        source_text=cue.text,
                        subtitle_text=cue.text,
                        meta={
                            "caption_source": "subtitle",
                            "subtitle_cue_index": cue.index,
                        },
                    )
                )
        elif strategy in {"asr", "auto"}:
            cues = speech_transcriber.transcribe(
                context.job.input.video,
                language=context.job.input.source_lang,
                model_size=context.job.pipeline.asr_model,
            )
            caption_source = "asr"
            source_meta = {
                "asr_model": context.job.pipeline.asr_model,
                "source_video": context.job.input.video,
            }
            segments = []
            for idx, cue in enumerate(cues):
                segment_key = f"seg_{idx + 1:04d}"
                segments.append(
                    SegmentRecord(
                        job_id=context.job.id,
                        segment_key=segment_key,
                        segment_index=idx,
                        status=SegmentStatus.completed,
                        start_ms=cue.start_ms,
                        end_ms=cue.end_ms,
                        source_text=cue.text,
                        subtitle_text=cue.text,
                        asr_confidence=cue.confidence,
                        meta={
                            "caption_source": "asr",
                        },
                    )
                )
        elif strategy == "subtitle":
            raise CaptionSourceUnsupportedError(
                "subtitle caption_strategy requires input.subtitle to be set"
            )
        else:
            raise CaptionSourceUnsupportedError(
                f"unsupported caption_strategy '{context.job.pipeline.caption_strategy}'"
            )

        output_path = (
            context.workspace.stage_dir(StageName.CAPTION) / "source_zh.raw.json"
        )
        payload = {
            "source": caption_source,
            **source_meta,
            "segments": [
                {
                    "segment_key": item.segment_key,
                    "segment_index": item.segment_index,
                    "start_ms": item.start_ms,
                    "end_ms": item.end_ms,
                    "text": item.source_text,
                }
                for item in segments
            ],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        content = output_path.read_bytes()

        artifact = ArtifactRecord(
            job_id=context.job.id,
            stage_name=StageName.CAPTION,
            artifact_type="caption_source_segments",
            path=str(output_path),
            checksum=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
            meta={"count": len(segments), "source": caption_source},
        )

        return StageExecutionResult(
            artifacts=[artifact],
            segments=segments,
            meta={"caption_source": caption_source, "segment_count": len(segments)},
        )

    return _run
