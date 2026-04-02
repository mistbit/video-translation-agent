import hashlib
import json
from pathlib import Path
from typing import Any, cast

from video_translation_agent.adapters.qa import QAAdapter
from video_translation_agent.domain.enums import JobStatus, StageName
from video_translation_agent.domain.models import (
    ArtifactRecord,
    SegmentRecord,
    SegmentStatus,
)
from video_translation_agent.pipeline.context import (
    StageExecutionContext,
    StageExecutionResult,
)


def build_qa_stage(adapter: QAAdapter | None = None):
    qa = adapter or QAAdapter()

    def _run(context: StageExecutionContext) -> StageExecutionResult:
        latest = context.store.latest_segments()
        ordered = sorted(latest.values(), key=lambda item: item.segment_index)
        artifacts = context.store.list_artifacts()

        render_artifacts = [
            artifact
            for artifact in artifacts
            if artifact.stage_name == StageName.RENDER
            and artifact.artifact_type in {"render_subtitle_srt", "render_final_video"}
        ]
        has_render_subtitle = any(
            item.artifact_type == "render_subtitle_srt" and Path(item.path).exists()
            for item in render_artifacts
        )
        has_render_video = any(
            item.artifact_type == "render_final_video" and Path(item.path).exists()
            for item in render_artifacts
        )

        report_segments: list[dict[str, Any]] = []
        updated_segments: list[SegmentRecord] = []
        flag_counts: dict[str, int] = {}
        overrun_count = 0
        high_overrun_count = 0
        for segment in ordered:
            evaluated_flags = qa.evaluate_segment(segment)
            target_duration_ms = max(0, segment.end_ms - segment.start_ms)
            actual_duration_ms = segment.tts_duration_ms
            overrun_ms = (
                0
                if actual_duration_ms is None
                else max(0, actual_duration_ms - target_duration_ms)
            )
            if overrun_ms > qa.policy.max_tts_overrun_ms:
                overrun_count += 1
                high_overrun_count += 1

            combined_flags = sorted(set(segment.qa_flags + evaluated_flags))
            for flag in combined_flags:
                flag_counts[flag] = flag_counts.get(flag, 0) + 1

            updated = segment.model_copy(deep=True)
            updated.status = SegmentStatus.completed
            updated.qa_flags = combined_flags
            updated_segments.append(updated)

            report_segments.append(
                {
                    "segment_key": segment.segment_key,
                    "segment_index": segment.segment_index,
                    "target_duration_ms": target_duration_ms,
                    "tts_duration_ms": actual_duration_ms,
                    "overrun_ms": overrun_ms,
                    "flags": combined_flags,
                }
            )

        segment_count = len(ordered)
        overrun_ratio = 0.0 if segment_count == 0 else overrun_count / segment_count

        stage_flags: list[str] = []
        if not has_render_subtitle or not has_render_video:
            stage_flags.append("render_missing_artifacts")

        blocking_reasons: list[str] = []
        if (
            qa.policy.pause_on_missing_translation
            and flag_counts.get("missing_translation", 0) > 0
        ):
            blocking_reasons.append("missing_translation")
        if (
            qa.policy.pause_on_audio_clipping_risk
            and flag_counts.get("audio_clipping_risk", 0) > 0
        ):
            blocking_reasons.append("audio_clipping_risk")
        if overrun_ratio > qa.policy.max_tts_overrun_ratio:
            blocking_reasons.append("tts_duration_overrun_ratio")
        if high_overrun_count > 0:
            blocking_reasons.append("tts_duration_overrun")
        if stage_flags:
            blocking_reasons.extend(stage_flags)

        report_payload = {
            "job_id": str(context.job.id),
            "segment_count": segment_count,
            "flag_counts": flag_counts,
            "overrun_ratio": overrun_ratio,
            "render_artifacts_present": {
                "subtitle": has_render_subtitle,
                "final_video": has_render_video,
            },
            "stage_flags": stage_flags,
            "blocking": bool(blocking_reasons),
            "blocking_reasons": sorted(set(blocking_reasons)),
            "segments": report_segments,
        }

        markdown_report = _to_markdown(report_payload)
        stage_dir = context.workspace.stage_dir(StageName.QA)
        stage_dir.mkdir(parents=True, exist_ok=True)
        report_json = stage_dir / "qa_report.json"
        report_md = stage_dir / "qa_report.md"
        report_json.write_text(
            json.dumps(report_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        report_md.write_text(markdown_report, encoding="utf-8")

        if blocking_reasons:
            context.store.update_job_status(
                status=cast(JobStatus, JobStatus.paused),
                current_stage=StageName.QA,
                error_message=f"qa blocked: {', '.join(sorted(set(blocking_reasons)))}",
            )

        qa_artifacts = [
            _artifact_for_file(
                context=context,
                path=report_json,
                artifact_type="qa_report_json",
                stage=StageName.QA,
                meta={"segment_count": segment_count},
            ),
            _artifact_for_file(
                context=context,
                path=report_md,
                artifact_type="qa_report_markdown",
                stage=StageName.QA,
                meta={"segment_count": segment_count},
            ),
        ]

        return StageExecutionResult(
            artifacts=qa_artifacts,
            segments=updated_segments,
            meta={
                "qa_blocking": bool(blocking_reasons),
                "qa_blocking_reasons": sorted(set(blocking_reasons)),
                "qa_report_json": str(report_json),
                "qa_report_md": str(report_md),
            },
        )

    return _run


def _to_markdown(report_payload: dict[str, Any]) -> str:
    lines = [
        "# QA Report",
        "",
        f"- Job ID: `{report_payload['job_id']}`",
        f"- Segment count: {report_payload['segment_count']}",
        f"- Blocking: {report_payload['blocking']}",
        f"- Blocking reasons: {', '.join(report_payload['blocking_reasons']) or 'none'}",
        "",
        "## Flag Counts",
    ]
    flag_counts = report_payload["flag_counts"]
    if flag_counts:
        for key in sorted(flag_counts):
            lines.append(f"- {key}: {flag_counts[key]}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Segment Checks",
            "",
            "| Segment | Overrun(ms) | Flags |",
            "|---|---:|---|",
        ]
    )
    for item in report_payload["segments"]:
        flags = ", ".join(item["flags"]) or "none"
        lines.append(f"| {item['segment_key']} | {item['overrun_ms']} | {flags} |")
    lines.append("")
    return "\n".join(lines)


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
