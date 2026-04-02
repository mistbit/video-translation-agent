import json
from pathlib import Path
from uuid import UUID

import typer
from pydantic import ValidationError

from video_translation_agent.cli import (
    CLIExitCode,
    load_job_file_config,
    make_default_job_file_config,
    resolve_job_spec,
    run_doctor,
    run_local_pipeline,
    run_segment_rerun,
    run_stage_rerun,
    write_job_file_config,
)
from video_translation_agent.domain.enums import JobStatus, StageName
from video_translation_agent.orchestrator import StageExecutionError
from video_translation_agent.workspace import JobWorkspace

app = typer.Typer(name="vtl", no_args_is_help=True)
stage_app = typer.Typer(help="Run single stage operations.")
segment_app = typer.Typer(help="Rerun a segment operation.")
config_app = typer.Typer(help="Manage configuration.")
completion_app = typer.Typer(help="Shell completion utilities.")


@app.command()
def run(
    mode: str = typer.Option("local", help="Execution mode: local or remote."),
    config: Path | None = typer.Option(None, help="Path to job config file."),
    job_id: UUID | None = typer.Option(None, help="Optional fixed job ID."),
    input_video: str | None = typer.Option(None, help="Input video path."),
    input_subtitle: str | None = typer.Option(None, help="Input subtitle path (.srt)."),
    source_lang: str | None = typer.Option(None, help="Source language."),
    target_lang: str | None = typer.Option(None, help="Target language."),
    artifact_root: str | None = typer.Option(None, help="Job artifacts root path."),
    caption_strategy: str | None = typer.Option(None, help="Caption strategy."),
    translation_model: str | None = typer.Option(None, help="Translation model."),
    tts_model: str | None = typer.Option(None, help="TTS model."),
    voice_profile: str | None = typer.Option(None, help="Voice profile."),
    mix_mode: str | None = typer.Option(None, help="Audio mix mode."),
    burn_subtitles: bool | None = typer.Option(
        None,
        "--burn-subtitles/--no-burn-subtitles",
    ),
    prefer_ffmpeg: bool = typer.Option(
        True,
        "--prefer-ffmpeg/--no-prefer-ffmpeg",
        help="Prefer ffmpeg rendering when available.",
    ),
    allow_render_copy_fallback: bool = typer.Option(
        True,
        "--allow-render-copy-fallback/--no-allow-render-copy-fallback",
        help="Allow local copy fallback if ffmpeg render fails.",
    ),
    dry_run: bool = typer.Option(False, help="Validate config/dependencies only."),
) -> None:
    if mode != "local":
        typer.echo("Only local mode is implemented in this phase.", err=True)
        raise typer.Exit(code=CLIExitCode.ARGUMENT_ERROR)

    try:
        job_spec = resolve_job_spec(
            config_path=config,
            job_id=job_id,
            input_video=input_video,
            input_subtitle=input_subtitle,
            source_lang=source_lang,
            target_lang=target_lang,
            artifact_root=artifact_root,
            caption_strategy=caption_strategy,
            translation_model=translation_model,
            tts_model=tts_model,
            voice_profile=voice_profile,
            mix_mode=mix_mode,
            burn_subtitles=burn_subtitles,
        )
    except Exception as exc:
        typer.echo(f"Config validation failed: {exc}", err=True)
        raise typer.Exit(code=CLIExitCode.CONFIG_ERROR) from exc

    doctor_report = run_doctor(artifact_root=job_spec.artifact_root)
    if dry_run:
        _print_doctor_report(doctor_report)
        for name in _blocking_dependency_failures(
            report=doctor_report,
            prefer_ffmpeg=prefer_ffmpeg,
            allow_render_copy_fallback=allow_render_copy_fallback,
        ):
            typer.echo(f"blocking_dependency: {name}", err=True)
        typer.echo("Dry run complete; configuration is valid.")
        raise typer.Exit(code=CLIExitCode.OK)

    blocking_failures = _blocking_dependency_failures(
        report=doctor_report,
        prefer_ffmpeg=prefer_ffmpeg,
        allow_render_copy_fallback=allow_render_copy_fallback,
    )
    if blocking_failures:
        _print_doctor_report(doctor_report)
        for name in blocking_failures:
            typer.echo(f"blocking_dependency: {name}", err=True)
        raise typer.Exit(code=CLIExitCode.DEPENDENCY_ERROR)

    try:
        job = run_local_pipeline(
            job_spec=job_spec,
            prefer_ffmpeg=prefer_ffmpeg,
            allow_render_copy_fallback=allow_render_copy_fallback,
        )
    except StageExecutionError as exc:
        typer.echo(f"Pipeline failed: {exc}", err=True)
        raise typer.Exit(code=CLIExitCode.STAGE_ERROR) from exc
    except Exception as exc:
        typer.echo(f"Run failed: {exc}", err=True)
        raise typer.Exit(code=CLIExitCode.FAILURE) from exc

    workspace = JobWorkspace(artifact_root=Path(job_spec.artifact_root), job_id=job.id)
    typer.echo(f"job_id: {job.id}")
    typer.echo(f"status: {job.status.value}")
    typer.echo(f"workspace: {workspace.root}")
    if job.status == JobStatus.paused:
        raise typer.Exit(code=CLIExitCode.QA_BLOCKED)


@stage_app.command("run")
def stage_run(
    stage: StageName,
    job_id: UUID = typer.Option(..., help="Job ID to rerun."),
    artifact_root: str = typer.Option("jobs", help="Artifacts root path."),
    prefer_ffmpeg: bool = typer.Option(
        True,
        "--prefer-ffmpeg/--no-prefer-ffmpeg",
    ),
    allow_render_copy_fallback: bool = typer.Option(
        True,
        "--allow-render-copy-fallback/--no-allow-render-copy-fallback",
    ),
) -> None:
    try:
        job = run_stage_rerun(
            stage=stage,
            job_id=job_id,
            artifact_root=artifact_root,
            prefer_ffmpeg=prefer_ffmpeg,
            allow_render_copy_fallback=allow_render_copy_fallback,
        )
    except FileNotFoundError as exc:
        typer.echo(f"Job not found: {exc}", err=True)
        raise typer.Exit(code=CLIExitCode.NOT_FOUND) from exc
    except StageExecutionError as exc:
        typer.echo(f"Stage rerun failed: {exc}", err=True)
        raise typer.Exit(code=CLIExitCode.STAGE_ERROR) from exc

    typer.echo(f"job_id: {job.id}")
    typer.echo(f"reran_stage: {stage.value}")
    typer.echo(f"status: {job.status.value}")


@segment_app.command("rerun")
def segment_rerun(
    segment_key: str = typer.Argument(..., help="Business segment key, e.g. seg_0001."),
    job_id: UUID = typer.Option(..., help="Job ID."),
    artifact_root: str = typer.Option("jobs", help="Artifacts root path."),
    stage: list[StageName] | None = typer.Option(
        None,
        "--stage",
        help="Optional stage(s) to execute when --execute-stages is set.",
    ),
    reason: str | None = typer.Option(None, help="Rerun reason."),
    execute_stages: bool = typer.Option(
        False, help="Execute stages after recording rerun."
    ),
    prefer_ffmpeg: bool = typer.Option(
        True,
        "--prefer-ffmpeg/--no-prefer-ffmpeg",
    ),
    allow_render_copy_fallback: bool = typer.Option(
        True,
        "--allow-render-copy-fallback/--no-allow-render-copy-fallback",
    ),
) -> None:
    try:
        job = run_segment_rerun(
            job_id=job_id,
            artifact_root=artifact_root,
            segment_key=segment_key,
            stages=stage,
            reason=reason,
            execute_stages=execute_stages,
            prefer_ffmpeg=prefer_ffmpeg,
            allow_render_copy_fallback=allow_render_copy_fallback,
        )
    except FileNotFoundError as exc:
        typer.echo(f"Job not found: {exc}", err=True)
        raise typer.Exit(code=CLIExitCode.NOT_FOUND) from exc
    except StageExecutionError as exc:
        typer.echo(f"Segment rerun failed: {exc}", err=True)
        raise typer.Exit(code=CLIExitCode.STAGE_ERROR) from exc

    typer.echo(f"job_id: {job.id}")
    typer.echo(f"segment_key: {segment_key}")
    typer.echo(f"execute_stages: {execute_stages}")
    typer.echo(f"status: {job.status.value}")


@config_app.command("init")
def config_init(
    output: Path = typer.Option(
        Path("vtl.config.json"),
        "--output",
        help="Path to write starter config (.json/.yaml/.toml).",
    ),
    force: bool = typer.Option(False, help="Overwrite if output already exists."),
) -> None:
    if output.exists() and not force:
        typer.echo(f"Config already exists: {output}", err=True)
        raise typer.Exit(code=CLIExitCode.ARGUMENT_ERROR)
    try:
        write_job_file_config(make_default_job_file_config(), output)
    except Exception as exc:
        typer.echo(f"Failed to write config: {exc}", err=True)
        raise typer.Exit(code=CLIExitCode.FAILURE) from exc
    typer.echo(f"Wrote starter config: {output}")


@config_app.command("show")
def config_show(
    config: Path = typer.Option(..., help="Path to config file."),
) -> None:
    try:
        parsed = load_job_file_config(config)
    except ValidationError as exc:
        typer.echo(f"Invalid config: {exc}", err=True)
        raise typer.Exit(code=CLIExitCode.CONFIG_ERROR) from exc
    except Exception as exc:
        typer.echo(f"Failed to read config: {exc}", err=True)
        raise typer.Exit(code=CLIExitCode.FAILURE) from exc

    typer.echo(json.dumps(parsed.model_dump(mode="json"), ensure_ascii=False, indent=2))


@config_app.command("validate")
def config_validate(
    config: Path = typer.Option(..., help="Path to config file."),
) -> None:
    try:
        load_job_file_config(config)
    except ValidationError as exc:
        typer.echo(f"Config validation failed: {exc}", err=True)
        raise typer.Exit(code=CLIExitCode.CONFIG_ERROR) from exc
    except Exception as exc:
        typer.echo(f"Failed to validate config: {exc}", err=True)
        raise typer.Exit(code=CLIExitCode.FAILURE) from exc
    typer.echo("Config is valid.")


@app.command()
def doctor(
    artifact_root: str = typer.Option("jobs", help="Artifacts root path."),
    prefer_ffmpeg: bool = typer.Option(
        True,
        "--prefer-ffmpeg/--no-prefer-ffmpeg",
        help="Treat ffmpeg as preferred render backend.",
    ),
    allow_render_copy_fallback: bool = typer.Option(
        True,
        "--allow-render-copy-fallback/--no-allow-render-copy-fallback",
        help="Allow copy fallback when ffmpeg is unavailable.",
    ),
) -> None:
    report = run_doctor(artifact_root=artifact_root)
    _print_doctor_report(report)
    blocking_failures = _blocking_dependency_failures(
        report=report,
        prefer_ffmpeg=prefer_ffmpeg,
        allow_render_copy_fallback=allow_render_copy_fallback,
    )
    if blocking_failures:
        for name in blocking_failures:
            typer.echo(f"blocking_dependency: {name}", err=True)
        raise typer.Exit(code=CLIExitCode.DEPENDENCY_ERROR)


@completion_app.command("show")
def completion_show(shell: str = "zsh", program: str = "vtl") -> None:
    if shell not in {"zsh", "bash", "fish"}:
        typer.echo("shell must be one of: zsh, bash, fish", err=True)
        raise typer.Exit(code=CLIExitCode.ARGUMENT_ERROR)
    typer.echo(f'eval "$(_{program.upper()}_COMPLETE={shell}_source {program})"')


@completion_app.command("install")
def completion_install(shell: str = "zsh", program: str = "vtl") -> None:
    if shell == "zsh":
        rc_path = Path.home() / ".zshrc"
    elif shell == "bash":
        rc_path = Path.home() / ".bashrc"
    elif shell == "fish":
        rc_path = Path.home() / ".config/fish/config.fish"
    else:
        typer.echo("shell must be one of: zsh, bash, fish", err=True)
        raise typer.Exit(code=CLIExitCode.ARGUMENT_ERROR)

    line = f'eval "$(_{program.upper()}_COMPLETE={shell}_source {program})"'
    rc_path.parent.mkdir(parents=True, exist_ok=True)
    existing = rc_path.read_text(encoding="utf-8") if rc_path.exists() else ""
    if line not in existing:
        with rc_path.open("a", encoding="utf-8") as file_obj:
            if existing and not existing.endswith("\n"):
                file_obj.write("\n")
            file_obj.write(line + "\n")
    typer.echo(f"Installed completion hook in {rc_path}")


def _print_doctor_report(report) -> None:
    for check in report.checks:
        icon = "OK" if check.ok else "FAIL"
        typer.echo(f"[{icon}] {check.name}: {check.details}")


def _blocking_dependency_failures(
    *,
    report,
    prefer_ffmpeg: bool,
    allow_render_copy_fallback: bool,
) -> list[str]:
    checks_by_name = {item.name: item.ok for item in report.checks}
    required = {"python", "ffprobe", "artifact_root"}
    if prefer_ffmpeg and not allow_render_copy_fallback:
        required.add("ffmpeg")
    return sorted([name for name in required if not checks_by_name.get(name, False)])


app.add_typer(stage_app, name="stage")
app.add_typer(segment_app, name="segment")
app.add_typer(config_app, name="config")
app.add_typer(completion_app, name="completion")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
