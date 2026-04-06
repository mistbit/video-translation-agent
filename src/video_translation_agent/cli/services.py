import json
import platform
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ValidationError

from video_translation_agent.adapters.render import LocalRenderAdapter
from video_translation_agent.domain.config import (
    InputConfig,
    PipelineConfig,
    RuntimeConfig,
)
from video_translation_agent.domain.enums import JobStatus, StageName
from video_translation_agent.domain.models import JobManifest, JobSpec
from video_translation_agent.orchestrator import InProcessOrchestrator
from video_translation_agent.pipeline.bootstrap import build_default_stage_registry


class CLIExitCode:
    OK = 0
    FAILURE = 1
    ARGUMENT_ERROR = 2
    CONFIG_ERROR = 3
    DEPENDENCY_ERROR = 4
    STAGE_ERROR = 5
    NOT_FOUND = 6
    QA_BLOCKED = 7


class OutputConfig(BaseModel):
    artifact_root: str = "jobs"


class JobFileConfig(BaseModel):
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    input: InputConfig
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


def make_default_job_file_config() -> JobFileConfig:
    return JobFileConfig(
        input=InputConfig(
            video="./sample/source.mp4",
            subtitle="./sample/source.srt",
            source_lang="zh",
            target_lang="en",
        ),
        pipeline=PipelineConfig(caption_strategy="auto"),
    )


def load_job_file_config(path: Path) -> JobFileConfig:
    payload = _read_payload(path)
    return JobFileConfig.model_validate(payload)


def write_job_file_config(config: JobFileConfig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    payload = config.model_dump(mode="json")
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-untyped]
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "YAML output requested but PyYAML is not installed"
            ) from exc
        path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return

    if suffix == ".toml":
        raise RuntimeError("TOML write is not supported; use .json or .yaml")

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_job_spec(
    *,
    config_path: Path | None,
    job_id: UUID | None,
    input_video: str | None,
    input_subtitle: str | None,
    source_lang: str | None,
    target_lang: str | None,
    artifact_root: str | None,
    caption_strategy: str | None,
    asr_model: str | None,
    translation_model: str | None,
    tts_model: str | None,
    voice_profile: str | None,
    mix_mode: str | None,
    burn_subtitles: bool | None,
) -> JobSpec:
    if config_path is not None:
        config = load_job_file_config(config_path)
        runtime = config.runtime.model_copy(deep=True)
        input_config = config.input.model_copy(deep=True)
        pipeline_config = config.pipeline.model_copy(deep=True)
        effective_artifact_root = config.output.artifact_root
    else:
        runtime = RuntimeConfig()
        input_config = InputConfig(video=input_video or "")
        pipeline_config = PipelineConfig()
        effective_artifact_root = "jobs"

    if input_video is not None:
        input_config.video = input_video
    if input_subtitle is not None:
        input_config.subtitle = input_subtitle
    if source_lang is not None:
        input_config.source_lang = source_lang
    if target_lang is not None:
        input_config.target_lang = target_lang

    if caption_strategy is not None:
        pipeline_config.caption_strategy = caption_strategy
    if asr_model is not None:
        pipeline_config.asr_model = asr_model
    if translation_model is not None:
        pipeline_config.translation_model = translation_model
    if tts_model is not None:
        pipeline_config.tts_model = tts_model
    if voice_profile is not None:
        pipeline_config.voice_profile = voice_profile
    if mix_mode is not None:
        pipeline_config.mix_mode = mix_mode
    if burn_subtitles is not None:
        pipeline_config.burn_subtitles = burn_subtitles

    if artifact_root is not None:
        effective_artifact_root = artifact_root

    try:
        return JobSpec(
            id=job_id or uuid4(),
            status=JobStatus.pending,
            current_stage=None,
            runtime=runtime,
            input=input_config,
            pipeline=pipeline_config,
            artifact_root=effective_artifact_root,
        )
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


def run_local_pipeline(
    *,
    job_spec: JobSpec,
    prefer_ffmpeg: bool,
    allow_render_copy_fallback: bool,
) -> JobManifest:
    orchestrator = InProcessOrchestrator(
        build_default_stage_registry(
            render_adapter=LocalRenderAdapter(
                prefer_ffmpeg=prefer_ffmpeg,
                allow_copy_fallback=allow_render_copy_fallback,
            )
        )
    )
    return orchestrator.run_job(job_spec)


def run_stage_rerun(
    *,
    stage: StageName,
    job_id: UUID,
    artifact_root: str,
    prefer_ffmpeg: bool,
    allow_render_copy_fallback: bool,
) -> JobManifest:
    orchestrator = InProcessOrchestrator(
        build_default_stage_registry(
            render_adapter=LocalRenderAdapter(
                prefer_ffmpeg=prefer_ffmpeg,
                allow_copy_fallback=allow_render_copy_fallback,
            )
        )
    )
    return orchestrator.rerun_stage(
        job_id=job_id, artifact_root=artifact_root, stage=stage
    )


def run_segment_rerun(
    *,
    job_id: UUID,
    artifact_root: str,
    segment_key: str,
    stages: list[StageName] | None,
    reason: str | None,
    execute_stages: bool,
    prefer_ffmpeg: bool,
    allow_render_copy_fallback: bool,
) -> JobManifest:
    orchestrator = InProcessOrchestrator(
        build_default_stage_registry(
            render_adapter=LocalRenderAdapter(
                prefer_ffmpeg=prefer_ffmpeg,
                allow_copy_fallback=allow_render_copy_fallback,
            )
        )
    )
    return orchestrator.rerun_segment(
        job_id=job_id,
        artifact_root=artifact_root,
        segment_key=segment_key,
        stages=stages,
        reason=reason,
        execute_stages=execute_stages,
    )


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    ok: bool
    details: str


@dataclass(frozen=True)
class DoctorReport:
    checks: list[DoctorCheck]

    @property
    def ok(self) -> bool:
        return all(item.ok for item in self.checks)


def run_doctor(*, artifact_root: str) -> DoctorReport:
    checks: list[DoctorCheck] = []
    checks.append(
        DoctorCheck(
            name="python",
            ok=sys.version_info >= (3, 11),
            details=f"{platform.python_version()} ({sys.executable})",
        )
    )

    ffprobe_path = shutil.which("ffprobe")
    media_probe_fallback = shutil.which("mdls") or shutil.which("swift")
    checks.append(
        DoctorCheck(
            name="ffprobe",
            ok=ffprobe_path is not None or media_probe_fallback is not None,
            details=ffprobe_path
            or (
                f"fallback via {media_probe_fallback}"
                if media_probe_fallback
                else "missing on PATH"
            ),
        )
    )

    ffmpeg_path = shutil.which("ffmpeg")
    checks.append(
        DoctorCheck(
            name="ffmpeg",
            ok=ffmpeg_path is not None,
            details=ffmpeg_path or "missing on PATH",
        )
    )

    output_dir = Path(artifact_root)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        writable = output_dir.exists() and output_dir.is_dir()
        details = str(output_dir.resolve())
    except OSError as exc:
        writable = False
        details = str(exc)
    checks.append(DoctorCheck(name="artifact_root", ok=writable, details=details))

    return DoctorReport(checks=checks)


def _read_payload(path: Path) -> dict[str, object]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if suffix == ".toml":
        import tomllib

        return tomllib.loads(path.read_text(encoding="utf-8"))
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-untyped]
        except ModuleNotFoundError as exc:
            raise RuntimeError("YAML config requires PyYAML to be installed") from exc
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if payload is None:
            return {}
        if not isinstance(payload, dict):
            raise ValueError("config root must be a mapping object")
        return payload

    raise ValueError("unsupported config format; use .json, .toml, .yaml, or .yml")
