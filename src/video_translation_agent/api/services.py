import json
import subprocess
import sys
import threading
from pathlib import Path
from uuid import UUID, uuid4
from os import PathLike

from pydantic import BaseModel

from video_translation_agent.adapters.render import LocalRenderAdapter
from video_translation_agent.cli.services import resolve_job_spec
from video_translation_agent.domain.enums import JobStatus, StageName
from video_translation_agent.domain.models import JobManifest
from video_translation_agent.orchestrator import InProcessOrchestrator
from video_translation_agent.pipeline.bootstrap import build_default_stage_registry
from video_translation_agent.store import LocalMetadataStore
from video_translation_agent.workspace import JobWorkspace


class JobNotFoundError(FileNotFoundError):
    pass


class DirectorySelectionCancelled(RuntimeError):
    pass


class CreateJobRequest(BaseModel):
    job_id: UUID | None = None
    input_video: str
    input_subtitle: str | None = None
    source_lang: str | None = None
    target_lang: str | None = None
    artifact_root: str = "jobs"
    caption_strategy: str | None = None
    asr_model: str | None = None
    translation_model: str | None = None
    tts_model: str | None = None
    voice_profile: str | None = None
    mix_mode: str | None = None
    burn_subtitles: bool | None = None
    prefer_ffmpeg: bool = True
    allow_render_copy_fallback: bool = True
    run_async: bool = False


class UploadAsset(BaseModel):
    id: UUID
    kind: str
    filename: str
    path: str
    size_bytes: int
    content_type: str | None = None


class StageRerunRequest(BaseModel):
    artifact_root: str = "jobs"
    prefer_ffmpeg: bool = True
    allow_render_copy_fallback: bool = True


class SegmentRerunRequest(BaseModel):
    artifact_root: str = "jobs"
    stages: list[StageName] | None = None
    reason: str | None = None
    execute_stages: bool = True
    prefer_ffmpeg: bool = True
    allow_render_copy_fallback: bool = True


def list_jobs(
    *,
    artifact_root: str,
    status: JobStatus | None,
    offset: int,
    limit: int,
) -> dict[str, object]:
    root = Path(artifact_root)
    if not root.exists():
        return {
            "items": [],
            "total": 0,
            "offset": offset,
            "limit": limit,
            "artifact_root": str(root),
        }

    jobs: list[JobManifest] = []
    for candidate in root.iterdir():
        if not candidate.is_dir():
            continue
        manifest_path = candidate / "job.json"
        if not manifest_path.exists():
            continue
        try:
            manifest = JobManifest.model_validate(
                json.loads(manifest_path.read_text(encoding="utf-8"))
            )
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if status is not None and manifest.status != status:
            continue
        jobs.append(manifest)

    jobs.sort(key=lambda item: item.updated_at, reverse=True)
    paged = jobs[offset : offset + limit]
    return {
        "items": [item.model_dump(mode="json") for item in paged],
        "total": len(jobs),
        "offset": offset,
        "limit": limit,
        "artifact_root": str(root),
    }


def get_job(*, job_id: UUID, artifact_root: str) -> JobManifest:
    store = _load_store(job_id=job_id, artifact_root=artifact_root)
    return store.load_job()


def get_job_artifacts(*, job_id: UUID, artifact_root: str) -> dict[str, object]:
    store = _load_store(job_id=job_id, artifact_root=artifact_root)
    artifacts = store.list_artifacts()
    return {
        "job_id": str(job_id),
        "artifact_root": artifact_root,
        "items": [item.model_dump(mode="json") for item in artifacts],
        "count": len(artifacts),
    }


def get_job_logs(*, job_id: UUID, artifact_root: str) -> dict[str, object]:
    store = _load_store(job_id=job_id, artifact_root=artifact_root)
    workspace = JobWorkspace(artifact_root=Path(artifact_root), job_id=job_id)

    log_files: list[dict[str, object]] = []
    if workspace.logs_dir.exists():
        for file_path in sorted(workspace.logs_dir.rglob("*")):
            if not file_path.is_file():
                continue
            content: str | None
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = None
            stats = file_path.stat()
            log_files.append(
                {
                    "path": str(file_path),
                    "relative_path": str(file_path.relative_to(workspace.root)),
                    "size_bytes": stats.st_size,
                    "updated_at": stats.st_mtime,
                    "content": content,
                }
            )

    stage_runs = store.list_stage_runs()
    segment_reruns = store.list_segment_reruns()
    return {
        "job_id": str(job_id),
        "artifact_root": artifact_root,
        "log_files": log_files,
        "stage_runs": [item.model_dump(mode="json") for item in stage_runs],
        "segment_reruns": [item.model_dump(mode="json") for item in segment_reruns],
    }


def get_job_qa(*, job_id: UUID, artifact_root: str) -> dict[str, object]:
    _load_store(job_id=job_id, artifact_root=artifact_root)
    workspace = JobWorkspace(artifact_root=Path(artifact_root), job_id=job_id)
    report_json_path = workspace.stage_dir(StageName.QA) / "qa_report.json"
    report_md_path = workspace.stage_dir(StageName.QA) / "qa_report.md"
    if not report_json_path.exists():
        raise FileNotFoundError(f"QA report not found: {report_json_path}")

    report_payload = json.loads(report_json_path.read_text(encoding="utf-8"))
    report_markdown = (
        report_md_path.read_text(encoding="utf-8") if report_md_path.exists() else None
    )
    return {
        "job_id": str(job_id),
        "artifact_root": artifact_root,
        "report": report_payload,
        "report_json_path": str(report_json_path),
        "report_markdown_path": str(report_md_path),
        "report_markdown": report_markdown,
    }


def create_job(request: CreateJobRequest) -> JobManifest:
    spec = resolve_job_spec(
        config_path=None,
        job_id=request.job_id,
        input_video=request.input_video,
        input_subtitle=request.input_subtitle,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        artifact_root=request.artifact_root,
        caption_strategy=request.caption_strategy,
        asr_model=request.asr_model,
        translation_model=request.translation_model,
        tts_model=request.tts_model,
        voice_profile=request.voice_profile,
        mix_mode=request.mix_mode,
        burn_subtitles=request.burn_subtitles,
    )
    orchestrator = _build_orchestrator(
        prefer_ffmpeg=request.prefer_ffmpeg,
        allow_render_copy_fallback=request.allow_render_copy_fallback,
    )
    if request.run_async:
        job = orchestrator.create_job_record(spec)
        worker = threading.Thread(
            target=_run_job_in_background,
            kwargs={
                "job_id": job.id,
                "artifact_root": job.artifact_root,
                "prefer_ffmpeg": request.prefer_ffmpeg,
                "allow_render_copy_fallback": request.allow_render_copy_fallback,
            },
            daemon=True,
            name=f"job-{job.id}",
        )
        worker.start()
        return job
    return orchestrator.run_job(spec)


def save_uploaded_input(
    *,
    artifact_root: str,
    filename: str,
    payload: bytes,
    kind: str,
    content_type: str | None,
) -> UploadAsset:
    safe_name = _sanitize_upload_filename(filename=filename, kind=kind)
    upload_id = uuid4()
    upload_dir = Path(artifact_root) / "_uploads" / str(upload_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / safe_name
    target.write_bytes(payload)
    return UploadAsset(
        id=upload_id,
        kind=kind,
        filename=safe_name,
        path=str(target),
        size_bytes=target.stat().st_size,
        content_type=content_type,
    )


def select_directory_path(*, initial_directory: str | None = None) -> str:
    if sys.platform == "darwin":
        return _select_directory_path_macos(initial_directory=initial_directory)
    return _select_directory_path_tk(initial_directory=initial_directory)


def rerun_stage(
    *,
    job_id: UUID,
    stage: StageName,
    request: StageRerunRequest,
) -> dict[str, object]:
    orchestrator = _build_orchestrator(
        prefer_ffmpeg=request.prefer_ffmpeg,
        allow_render_copy_fallback=request.allow_render_copy_fallback,
    )
    job = orchestrator.rerun_stage(
        job_id=job_id,
        artifact_root=request.artifact_root,
        stage=stage,
    )
    store = _load_store(job_id=job_id, artifact_root=request.artifact_root)
    stage_runs = [
        item.model_dump(mode="json") for item in store.list_stage_runs(stage=stage)
    ]
    return {
        "job": job.model_dump(mode="json"),
        "stage": stage.value,
        "attempts": stage_runs,
    }


def rerun_segment(
    *,
    job_id: UUID,
    segment_key: str,
    request: SegmentRerunRequest,
) -> dict[str, object]:
    orchestrator = _build_orchestrator(
        prefer_ffmpeg=request.prefer_ffmpeg,
        allow_render_copy_fallback=request.allow_render_copy_fallback,
    )
    job = orchestrator.rerun_segment(
        job_id=job_id,
        artifact_root=request.artifact_root,
        segment_key=segment_key,
        stages=request.stages,
        reason=request.reason,
        execute_stages=request.execute_stages,
    )
    store = _load_store(job_id=job_id, artifact_root=request.artifact_root)
    segment_records = [
        item.model_dump(mode="json")
        for item in store.list_segment_reruns()
        if item.segment_key == segment_key
    ]
    return {
        "job": job.model_dump(mode="json"),
        "segment_key": segment_key,
        "reruns": segment_records,
    }


def _load_store(*, job_id: UUID, artifact_root: str) -> LocalMetadataStore:
    workspace = JobWorkspace(artifact_root=Path(artifact_root), job_id=job_id)
    if not workspace.job_manifest_path.exists():
        raise JobNotFoundError(
            f"job '{job_id}' not found under artifact root '{artifact_root}'"
        )
    return LocalMetadataStore(workspace)


def _build_orchestrator(*, prefer_ffmpeg: bool, allow_render_copy_fallback: bool):
    registry = build_default_stage_registry(
        render_adapter=LocalRenderAdapter(
            prefer_ffmpeg=prefer_ffmpeg,
            allow_copy_fallback=allow_render_copy_fallback,
        )
    )
    return InProcessOrchestrator(registry=registry)


def _run_job_in_background(
    *,
    job_id: UUID,
    artifact_root: str,
    prefer_ffmpeg: bool,
    allow_render_copy_fallback: bool,
) -> None:
    orchestrator = _build_orchestrator(
        prefer_ffmpeg=prefer_ffmpeg,
        allow_render_copy_fallback=allow_render_copy_fallback,
    )
    orchestrator.run_existing_job(job_id=job_id, artifact_root=artifact_root)


def _sanitize_upload_filename(*, filename: str, kind: str) -> str:
    cleaned = Path(filename).name.strip()
    if cleaned:
        return cleaned
    default_name = "video.bin" if kind == "video" else "subtitle.srt"
    return default_name


def _select_directory_path_macos(*, initial_directory: str | None) -> str:
    script = ['set dialogPrompt to "Select artifact root"']
    default_directory = _resolve_existing_directory(initial_directory)
    if default_directory is None:
        script.append("set chosenFolder to choose folder with prompt dialogPrompt")
    else:
        escaped = _escape_applescript_string(default_directory)
        script.append(
            'set chosenFolder to choose folder with prompt dialogPrompt default location '
            f'POSIX file "{escaped}"'
        )
    script.append("POSIX path of chosenFolder")

    command: list[str] = ["osascript"]
    for line in script:
        command.extend(["-e", line])

    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        if "User canceled" in detail:
            raise DirectorySelectionCancelled("Directory selection cancelled")
        raise RuntimeError(detail or "Directory selection failed")

    selected = result.stdout.strip()
    if not selected:
        raise RuntimeError("Directory selection returned an empty path")
    return str(Path(selected))


def _select_directory_path_tk(*, initial_directory: str | None) -> str:
    from tkinter import Tk, filedialog

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(
            initialdir=_resolve_existing_directory(initial_directory),
            title="Select artifact root",
            mustexist=False,
        )
    finally:
        root.destroy()

    if not selected:
        raise DirectorySelectionCancelled("Directory selection cancelled")
    return str(Path(selected))


def _resolve_existing_directory(initial_directory: str | None) -> str | None:
    if not initial_directory:
        return None
    candidate = Path(initial_directory).expanduser()
    if candidate.is_file():
        candidate = candidate.parent
    if not candidate.exists():
        return None
    return str(candidate)


def _escape_applescript_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
