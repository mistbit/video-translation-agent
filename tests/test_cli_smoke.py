import json
import os
from pathlib import Path
from uuid import UUID

from typer.testing import CliRunner

import apps.cli.main as cli_main
from apps.cli.main import app
from video_translation_agent.cli import DoctorCheck, DoctorReport
from video_translation_agent.domain.enums import StageName
from video_translation_agent.store import LocalMetadataStore
from video_translation_agent.workspace import JobWorkspace


def test_cli_help_smoke() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "vtl" in result.output
    assert "stage" in result.output
    assert "segment" in result.output
    assert "config" in result.output


def test_cli_config_init_validate_show(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "vtl.config.json"

    init_result = runner.invoke(app, ["config", "init", "--output", str(config_path)])
    assert init_result.exit_code == 0
    assert config_path.exists()

    validate_result = runner.invoke(
        app,
        ["config", "validate", "--config", str(config_path)],
    )
    assert validate_result.exit_code == 0
    assert "Config is valid" in validate_result.output

    show_result = runner.invoke(app, ["config", "show", "--config", str(config_path)])
    assert show_result.exit_code == 0
    payload = json.loads(show_result.output)
    assert payload["pipeline"]["caption_strategy"] == "auto"


def test_cli_run_end_to_end_local_pipeline(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()

    subtitle_path = tmp_path / "source.srt"
    subtitle_path.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\n你好 世界\n\n"
        "2\n00:00:02,000 --> 00:00:04,000\nhello team\n",
        encoding="utf-8",
    )
    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"video-bytes")

    ffprobe_bin = tmp_path / "ffprobe"
    ffprobe_bin.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "print(json.dumps({'streams':[{'codec_type':'video'},{'codec_type':'audio'}],'format':{'duration':'4.0','size':'2048','format_name':'mp4'}}))\n",
        encoding="utf-8",
    )
    ffprobe_bin.chmod(0o755)

    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")

    artifact_root = tmp_path / "jobs"
    job_id = UUID("00000000-0000-0000-0000-000000000250")
    result = runner.invoke(
        app,
        [
            "run",
            "--job-id",
            str(job_id),
            "--input-video",
            str(source_video),
            "--input-subtitle",
            str(subtitle_path),
            "--artifact-root",
            str(artifact_root),
            "--no-prefer-ffmpeg",
        ],
    )

    assert result.exit_code == 0
    workspace = JobWorkspace(artifact_root=artifact_root, job_id=job_id)
    store = LocalMetadataStore(workspace)
    assert workspace.job_manifest_path.exists()
    assert (workspace.stage_dir(StageName.TRANSLATE) / "en_subtitle.srt").exists()
    assert (workspace.stage_dir(StageName.TTS) / "dub_en.wav").exists()
    assert (workspace.stage_dir(StageName.RENDER) / "final_en.mp4").exists()
    assert (workspace.stage_dir(StageName.QA) / "qa_report.json").exists()
    assert len(store.list_stage_runs()) == len(list(StageName))


def test_doctor_ffmpeg_is_optional_by_default(monkeypatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr(
        cli_main,
        "run_doctor",
        lambda artifact_root: DoctorReport(
            checks=[
                DoctorCheck(name="python", ok=True, details="ok"),
                DoctorCheck(name="ffprobe", ok=True, details="ok"),
                DoctorCheck(name="ffmpeg", ok=False, details="missing on PATH"),
                DoctorCheck(name="artifact_root", ok=True, details="ok"),
            ]
        ),
    )

    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "[FAIL] ffmpeg" in result.output


def test_doctor_ffmpeg_blocks_when_fallback_disabled_and_preferred(monkeypatch) -> None:
    runner = CliRunner()

    monkeypatch.setattr(
        cli_main,
        "run_doctor",
        lambda artifact_root: DoctorReport(
            checks=[
                DoctorCheck(name="python", ok=True, details="ok"),
                DoctorCheck(name="ffprobe", ok=True, details="ok"),
                DoctorCheck(name="ffmpeg", ok=False, details="missing on PATH"),
                DoctorCheck(name="artifact_root", ok=True, details="ok"),
            ]
        ),
    )

    result = runner.invoke(app, ["doctor", "--no-allow-render-copy-fallback"])
    assert result.exit_code == 4
