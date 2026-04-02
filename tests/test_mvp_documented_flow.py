import os
import shutil
from pathlib import Path
from uuid import UUID

from typer.testing import CliRunner

from apps.cli.main import app
from video_translation_agent.domain.enums import StageName
from video_translation_agent.store import LocalMetadataStore
from video_translation_agent.workspace import JobWorkspace


def test_documented_mvp_cli_flow_and_reruns(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    fixture_root = repo_root / "examples" / "mvp"
    run_root = tmp_path / "workspace"
    shutil.copytree(fixture_root, run_root / "examples" / "mvp")

    ffprobe_bin = tmp_path / "ffprobe"
    ffprobe_bin.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "print(json.dumps({'streams':[{'codec_type':'video'},{'codec_type':'audio'}],'format':{'duration':'4.0','size':'2048','format_name':'mp4'}}))\n",
        encoding="utf-8",
    )
    ffprobe_bin.chmod(0o755)

    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.chdir(run_root)

    runner = CliRunner()
    job_id = UUID("00000000-0000-0000-0000-000000000260")
    config_path = run_root / "examples" / "mvp" / "vtl.config.json"
    artifact_root = run_root / ".artifacts" / "mvp-jobs"

    run_result = runner.invoke(
        app,
        [
            "run",
            "--config",
            str(config_path),
            "--job-id",
            str(job_id),
            "--no-prefer-ffmpeg",
        ],
    )
    assert run_result.exit_code == 0

    workspace = JobWorkspace(artifact_root=artifact_root, job_id=job_id)
    store = LocalMetadataStore(workspace)

    assert workspace.job_manifest_path.exists()
    assert (workspace.stage_dir(StageName.CAPTION) / "source_zh.raw.json").exists()
    assert (workspace.stage_dir(StageName.NORMALIZE) / "source_zh.srt").exists()
    assert (workspace.stage_dir(StageName.TRANSLATE) / "en_subtitle.srt").exists()
    assert (workspace.stage_dir(StageName.TTS) / "dub_en.wav").exists()
    assert (workspace.stage_dir(StageName.RENDER) / "final_en.mp4").exists()
    assert (workspace.stage_dir(StageName.QA) / "qa_report.json").exists()
    assert (workspace.stage_dir(StageName.QA) / "qa_report.md").exists()

    stage_rerun_result = runner.invoke(
        app,
        [
            "stage",
            "run",
            "translate",
            "--job-id",
            str(job_id),
            "--artifact-root",
            str(artifact_root),
            "--no-prefer-ffmpeg",
        ],
    )
    assert stage_rerun_result.exit_code == 0

    segment_rerun_result = runner.invoke(
        app,
        [
            "segment",
            "rerun",
            "seg_0001",
            "--job-id",
            str(job_id),
            "--artifact-root",
            str(artifact_root),
            "--reason",
            "documented mvp rerun",
            "--execute-stages",
            "--no-prefer-ffmpeg",
        ],
    )
    assert segment_rerun_result.exit_code == 0

    translate_runs = store.list_stage_runs(stage=StageName.TRANSLATE)
    tts_runs = store.list_stage_runs(stage=StageName.TTS)
    assert [item.attempt for item in translate_runs] == [1, 2, 3]
    assert [item.attempt for item in tts_runs] == [1, 2]

    reruns = store.list_segment_reruns()
    assert len(reruns) == 1
    assert reruns[0].segment_key == "seg_0001"
    assert [stage.value for stage in reruns[0].stages] == ["translate", "tts"]

    latest_segments = store.latest_segments()
    assert latest_segments["seg_0001"].rerun_count == 1
    assert (
        latest_segments["seg_0001"].meta["last_rerun_reason"] == "documented mvp rerun"
    )
