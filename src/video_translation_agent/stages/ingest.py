import hashlib
import json
from pathlib import Path

from video_translation_agent.adapters.media import MediaProbeAdapter
from video_translation_agent.domain.enums import StageName
from video_translation_agent.domain.models import ArtifactRecord
from video_translation_agent.pipeline.context import (
    StageExecutionContext,
    StageExecutionResult,
)


def build_ingest_stage(adapter: MediaProbeAdapter | None = None):
    media_probe = adapter or MediaProbeAdapter()

    def _run(context: StageExecutionContext) -> StageExecutionResult:
        source_video = Path(context.job.input.video)
        probe = media_probe.probe(source_video)

        output_path = context.workspace.stage_dir(StageName.INGEST) / "media_info.json"
        output_payload = probe.model_dump(mode="json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(output_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        content = output_path.read_bytes()
        artifact = ArtifactRecord(
            job_id=context.job.id,
            stage_name=StageName.INGEST,
            artifact_type="media_probe",
            path=str(output_path),
            checksum=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
            meta={
                "stream_count": probe.stream_count,
                "has_subtitle_stream": probe.has_subtitle_stream,
                "duration_seconds": probe.duration_seconds,
            },
        )

        return StageExecutionResult(
            artifacts=[artifact],
            meta={
                "media_probe_path": str(output_path),
                "subtitle_streams": probe.subtitle_stream_count,
            },
        )

    return _run
