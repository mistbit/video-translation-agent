import hashlib
import json
from pathlib import Path
import re
from typing import TypedDict

from video_translation_agent.adapters.translation import (
    LocalTranslationAdapter,
    MediaTranslationSegment,
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


class TranslationPayloadItem(TypedDict):
    segment_key: str
    segment_index: int
    start_ms: int
    end_ms: int
    source_text: str
    subtitle_text: str
    dubbing_text: str
    risk_flags: list[str]
    translation_confidence: float


def build_translate_stage(adapter: LocalTranslationAdapter | None = None):
    translator = adapter or LocalTranslationAdapter()

    def _run(context: StageExecutionContext) -> StageExecutionResult:
        latest = context.store.latest_segments()
        ordered = sorted(latest.values(), key=lambda item: item.segment_index)
        media_translation_segments: list[MediaTranslationSegment] = []
        if _should_translate_from_media(
            context=context,
            segments=ordered,
            translator=translator,
        ):
            media_translation_segments = translator.translate_media(
                context.job.input.video,
                source_lang=context.job.input.source_lang,
            )

        translated_segments: list[SegmentRecord] = []
        translation_payload: list[TranslationPayloadItem] = []
        for segment in ordered:
            source_text = (segment.source_text or "").strip()
            effective_text = (
                _select_translation_text(
                    segment=segment,
                    media_segments=media_translation_segments,
                )
                or source_text
            )
            translated = translator.translate_segment(
                effective_text,
                segment_index=segment.segment_index,
            )

            updated = segment.model_copy(deep=True)
            updated.status = SegmentStatus.completed
            updated.subtitle_text = translated.subtitle_text
            updated.dubbing_text = translated.dubbing_text
            updated.translation_confidence = translated.confidence
            updated.meta = {
                **updated.meta,
                "translate": {
                    "risk_flags": translated.risk_flags,
                    "source_lang": context.job.input.source_lang,
                    "target_lang": context.job.input.target_lang,
                },
            }
            translated_segments.append(updated)
            translation_payload.append(
                {
                    "segment_key": updated.segment_key,
                    "segment_index": updated.segment_index,
                    "start_ms": updated.start_ms,
                    "end_ms": updated.end_ms,
                    "source_text": source_text,
                    "subtitle_text": translated.subtitle_text,
                    "dubbing_text": translated.dubbing_text,
                    "risk_flags": translated.risk_flags,
                    "translation_confidence": translated.confidence,
                }
            )

        stage_dir = context.workspace.stage_dir(StageName.TRANSLATE)
        subtitle_json = stage_dir / "en_subtitle.json"
        subtitle_srt = stage_dir / "en_subtitle.srt"
        dub_json = stage_dir / "en_dub_text.json"
        dub_txt = stage_dir / "en_dub_text.txt"

        stage_dir.mkdir(parents=True, exist_ok=True)
        subtitle_json.write_text(
            json.dumps({"segments": translation_payload}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        subtitle_srt.write_text(_to_srt(translation_payload), encoding="utf-8")
        dub_json.write_text(
            json.dumps(
                {
                    "segments": [
                        {
                            "segment_key": item["segment_key"],
                            "segment_index": item["segment_index"],
                            "dubbing_text": item["dubbing_text"],
                            "risk_flags": item["risk_flags"],
                        }
                        for item in translation_payload
                    ]
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        dub_txt.write_text(
            "\n".join(
                f"{item['segment_key']}: {item['dubbing_text']}"
                for item in translation_payload
            )
            + "\n",
            encoding="utf-8",
        )

        artifacts = [
            _artifact_for_file(
                context=context,
                path=subtitle_json,
                artifact_type="translated_subtitle_json",
                stage=StageName.TRANSLATE,
                meta={"count": len(translation_payload)},
            ),
            _artifact_for_file(
                context=context,
                path=subtitle_srt,
                artifact_type="translated_subtitle_srt",
                stage=StageName.TRANSLATE,
                meta={"count": len(translation_payload)},
            ),
            _artifact_for_file(
                context=context,
                path=dub_json,
                artifact_type="translated_dubbing_json",
                stage=StageName.TRANSLATE,
                meta={"count": len(translation_payload)},
            ),
            _artifact_for_file(
                context=context,
                path=dub_txt,
                artifact_type="translated_dubbing_text",
                stage=StageName.TRANSLATE,
                meta={"count": len(translation_payload)},
            ),
        ]

        return StageExecutionResult(
            artifacts=artifacts,
            segments=translated_segments,
            meta={"translated_segment_count": len(translated_segments)},
        )

    return _run


def _should_translate_from_media(
    *,
    context: StageExecutionContext,
    segments: list[SegmentRecord],
    translator: LocalTranslationAdapter,
) -> bool:
    if not translator.media_translation_enabled:
        return False
    if context.job.input.target_lang != "en":
        return False
    return any(item.meta.get("caption_source") == "asr" for item in segments)


def _select_translation_text(
    *,
    segment: SegmentRecord,
    media_segments: list[MediaTranslationSegment],
) -> str | None:
    if not media_segments:
        return None

    best: MediaTranslationSegment | None = None
    best_score = float("-inf")
    for candidate in media_segments:
        overlap = min(segment.end_ms, candidate.end_ms) - max(
            segment.start_ms, candidate.start_ms
        )
        if overlap > 0:
            score = float(overlap)
        else:
            segment_mid = (segment.start_ms + segment.end_ms) / 2
            candidate_mid = (candidate.start_ms + candidate.end_ms) / 2
            score = -abs(segment_mid - candidate_mid)
        if score > best_score:
            best = candidate
            best_score = score

    return None if best is None else best.text


def _to_srt(items: list[TranslationPayloadItem]) -> str:
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        lines.extend(
            [
                str(index),
                f"{_ms_to_srt_ts(item['start_ms'])} --> {_ms_to_srt_ts(item['end_ms'])}",
                item["subtitle_text"],
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
