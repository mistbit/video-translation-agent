import hashlib
import json
from pathlib import Path
from typing import TypedDict

from video_translation_agent.adapters.normalization import (
    normalize_caption_text_for_language,
)
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


class NormalizeHistoryItem(TypedDict):
    segment_key: str
    segment_index: int
    start_ms: int
    end_ms: int
    original_text: str
    normalized_text: str


def build_normalize_stage(normalizer=normalize_caption_text_for_language):
    def _run(context: StageExecutionContext) -> StageExecutionResult:
        latest = context.store.latest_segments()
        ordered = sorted(latest.values(), key=lambda item: item.segment_index)

        normalized_segments: list[SegmentRecord] = []
        history: list[NormalizeHistoryItem] = []
        for segment in ordered:
            original_text = segment.source_text or ""
            normalized_text = normalizer(
                original_text, source_lang=context.job.input.source_lang
            )
            normalized_segment = segment.model_copy(deep=True)
            normalized_segment.status = SegmentStatus.completed
            normalized_segment.source_text = normalized_text
            normalized_segment.subtitle_text = normalized_text
            normalized_segment.meta = {
                **normalized_segment.meta,
                "normalize": {
                    "previous_source_text": original_text,
                    "normalized": original_text != normalized_text,
                },
            }
            normalized_segments.append(normalized_segment)
            history.append(
                {
                    "segment_key": segment.segment_key,
                    "segment_index": segment.segment_index,
                    "start_ms": segment.start_ms,
                    "end_ms": segment.end_ms,
                    "original_text": original_text,
                    "normalized_text": normalized_text,
                }
            )

        stage_dir = context.workspace.stage_dir(StageName.NORMALIZE)
        cleaned_json = stage_dir / "source_zh.cleaned.json"
        cleaned_srt = stage_dir / "source_zh.srt"
        stage_dir.mkdir(parents=True, exist_ok=True)

        cleaned_json.write_text(
            json.dumps({"segments": history}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        cleaned_srt.write_text(_to_srt(history), encoding="utf-8")

        artifacts = [
            _artifact_for_file(
                context=context,
                path=cleaned_json,
                artifact_type="normalized_segments_json",
                meta={"count": len(history)},
            ),
            _artifact_for_file(
                context=context,
                path=cleaned_srt,
                artifact_type="normalized_segments_srt",
                meta={"count": len(history)},
            ),
        ]

        return StageExecutionResult(
            artifacts=artifacts,
            segments=normalized_segments,
            meta={"normalized_segment_count": len(normalized_segments)},
        )

    return _run


def _to_srt(items: list[NormalizeHistoryItem]) -> str:
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        start_ms = item["start_ms"]
        end_ms = item["end_ms"]
        text = item["normalized_text"]
        lines.extend(
            [
                str(index),
                f"{_ms_to_srt_ts(start_ms)} --> {_ms_to_srt_ts(end_ms)}",
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
    meta: dict[str, int],
) -> ArtifactRecord:
    content = path.read_bytes()
    return ArtifactRecord(
        job_id=context.job.id,
        stage_name=StageName.NORMALIZE,
        artifact_type=artifact_type,
        path=str(path),
        checksum=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        meta=meta,
    )
