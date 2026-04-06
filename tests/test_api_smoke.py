import os
import time
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from fastapi.testclient import TestClient

import apps.api.main as api_main
from apps.api.main import app
from video_translation_agent.domain.models import ApiEnvelope


def test_api_health_smoke() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = ApiEnvelope[dict[str, str]].model_validate(response.json())
    assert payload.code == 0
    assert payload.data is not None
    assert payload.data["status"] == "ok"


def test_api_ready_smoke() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    payload = ApiEnvelope[dict[str, str]].model_validate(response.json())
    assert payload.code == 0
    assert payload.data is not None
    assert payload.data["status"] == "ready"


def test_api_select_directory_endpoint(monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(
        api_main,
        "select_directory_path",
        lambda initial_directory=None: "/tmp/selected-artifacts",
    )

    response = client.get(
        "/api/v1/system/select-directory",
        params={"initial_directory": "/tmp"},
    )
    assert response.status_code == 200
    payload = ApiEnvelope[dict[str, str]].model_validate(response.json())
    assert payload.code == 0
    assert payload.data is not None
    assert payload.data["path"] == "/tmp/selected-artifacts"


def test_api_job_lifecycle_and_rerun_endpoints(tmp_path: Path, monkeypatch) -> None:
    client = TestClient(app)

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
    job_id = UUID("00000000-0000-0000-0000-000000000350")

    create_response = client.post(
        "/api/v1/jobs",
        json={
            "job_id": str(job_id),
            "input_video": str(source_video),
            "input_subtitle": str(subtitle_path),
            "artifact_root": str(artifact_root),
            "asr_model": "medium",
            "prefer_ffmpeg": False,
            "allow_render_copy_fallback": True,
        },
    )
    assert create_response.status_code == 200
    create_payload = ApiEnvelope[dict[str, object]].model_validate(
        create_response.json()
    )
    assert create_payload.code == 0
    assert create_payload.data is not None
    create_data = cast(dict[str, Any], create_payload.data)
    assert create_data["job"]["id"] == str(job_id)
    assert create_data["job"]["pipeline"]["asr_model"] == "medium"

    list_response = client.get(
        "/api/v1/jobs", params={"artifact_root": str(artifact_root)}
    )
    assert list_response.status_code == 200
    list_payload = ApiEnvelope[dict[str, object]].model_validate(list_response.json())
    assert list_payload.data is not None
    list_data = cast(dict[str, Any], list_payload.data)
    items = cast(list[dict[str, Any]], list_data["items"])
    assert any(item["id"] == str(job_id) for item in items)

    detail_response = client.get(
        f"/api/v1/jobs/{job_id}", params={"artifact_root": str(artifact_root)}
    )
    assert detail_response.status_code == 200
    detail_payload = ApiEnvelope[dict[str, object]].model_validate(
        detail_response.json()
    )
    assert detail_payload.data is not None
    detail_data = cast(dict[str, Any], detail_payload.data)
    assert detail_data["job"]["id"] == str(job_id)

    artifact_response = client.get(
        f"/api/v1/jobs/{job_id}/artifacts",
        params={"artifact_root": str(artifact_root)},
    )
    assert artifact_response.status_code == 200
    artifact_payload = ApiEnvelope[dict[str, object]].model_validate(
        artifact_response.json()
    )
    assert artifact_payload.data is not None
    artifact_data = cast(dict[str, Any], artifact_payload.data)
    assert artifact_data["count"] > 0

    logs_response = client.get(
        f"/api/v1/jobs/{job_id}/logs", params={"artifact_root": str(artifact_root)}
    )
    assert logs_response.status_code == 200
    logs_payload = ApiEnvelope[dict[str, object]].model_validate(logs_response.json())
    assert logs_payload.data is not None
    logs_data = cast(dict[str, Any], logs_payload.data)
    assert len(logs_data["stage_runs"]) >= 7

    stage_rerun_response = client.post(
        f"/api/v1/jobs/{job_id}/stages/translate/rerun",
        json={
            "artifact_root": str(artifact_root),
            "prefer_ffmpeg": False,
            "allow_render_copy_fallback": True,
        },
    )
    assert stage_rerun_response.status_code == 200
    stage_rerun_payload = ApiEnvelope[dict[str, object]].model_validate(
        stage_rerun_response.json()
    )
    assert stage_rerun_payload.data is not None
    stage_rerun_data = cast(dict[str, Any], stage_rerun_payload.data)
    assert len(stage_rerun_data["attempts"]) == 2

    segment_rerun_response = client.post(
        f"/api/v1/jobs/{job_id}/segments/seg_0001/rerun",
        json={
            "artifact_root": str(artifact_root),
            "reason": "api rerun",
            "execute_stages": True,
            "prefer_ffmpeg": False,
            "allow_render_copy_fallback": True,
        },
    )
    assert segment_rerun_response.status_code == 200
    segment_rerun_payload = ApiEnvelope[dict[str, object]].model_validate(
        segment_rerun_response.json()
    )
    assert segment_rerun_payload.data is not None
    segment_rerun_data = cast(dict[str, Any], segment_rerun_payload.data)
    assert len(segment_rerun_data["reruns"]) >= 1

    qa_response = client.get(
        f"/api/v1/jobs/{job_id}/qa", params={"artifact_root": str(artifact_root)}
    )
    assert qa_response.status_code == 200
    qa_payload = ApiEnvelope[dict[str, object]].model_validate(qa_response.json())
    assert qa_payload.data is not None
    qa_data = cast(dict[str, Any], qa_payload.data)
    report = cast(dict[str, Any], qa_data["report"])
    assert report["job_id"] == str(job_id)
    assert "segment_count" in report


def test_api_job_not_found_envelope() -> None:
    client = TestClient(app)
    missing = "00000000-0000-0000-0000-000000000999"
    response = client.get(f"/api/v1/jobs/{missing}", params={"artifact_root": "jobs"})
    assert response.status_code == 404
    payload = ApiEnvelope[dict[str, object] | None].model_validate(response.json())
    assert payload.code != 0
    assert payload.data is None


def test_api_qa_pending_returns_ok_envelope(tmp_path: Path) -> None:
    client = TestClient(app)
    artifact_root = tmp_path / "jobs"
    job_id = UUID("00000000-0000-0000-0000-000000000352")
    job_root = artifact_root / str(job_id)
    job_root.mkdir(parents=True)
    (job_root / "job.json").write_text(
        (
            "{\n"
            f'  "id": "{job_id}",\n'
            '  "status": "running",\n'
            '  "current_stage": "render",\n'
            '  "runtime": {"profile":"standalone","metadata_backend":"sqlite","queue_backend":"inline"},\n'
            '  "input": {"video":"video.mp4","subtitle":null,"source_lang":"zh","target_lang":"en"},\n'
            '  "pipeline": {"mode":"auto","caption_strategy":"auto","asr_model":"small","translation_model":"qwen2.5-14b-instruct","tts_model":"melotts","voice_profile":"en_female_neutral_01","mix_mode":"duck","burn_subtitles":true,"stage_order":["ingest","caption","normalize","translate","tts","render","qa"]},\n'
            f'  "artifact_root": "{artifact_root}",\n'
            '  "error_message": null,\n'
            '  "retry_count": 0,\n'
            '  "created_at": "2026-04-06T00:00:00Z",\n'
            '  "updated_at": "2026-04-06T00:00:00Z"\n'
            "}\n"
        ),
        encoding="utf-8",
    )

    response = client.get(
        f"/api/v1/jobs/{job_id}/qa", params={"artifact_root": str(artifact_root)}
    )
    assert response.status_code == 200
    payload = ApiEnvelope[dict[str, object] | None].model_validate(response.json())
    assert payload.code == 0
    assert payload.data is None


def test_api_upload_and_async_job_endpoints(tmp_path: Path, monkeypatch) -> None:
    client = TestClient(app)

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
    upload_video = client.post(
        f"/api/v1/uploads?artifact_root={artifact_root}&kind=video&filename=source.mp4",
        content=b"video-bytes",
        headers={"content-type": "video/mp4"},
    )
    assert upload_video.status_code == 200
    upload_video_payload = ApiEnvelope[dict[str, object]].model_validate(
        upload_video.json()
    )
    assert upload_video_payload.data is not None
    upload_video_data = cast(dict[str, Any], upload_video_payload.data)
    assert Path(cast(str, upload_video_data["path"])).exists()

    upload_subtitle = client.post(
        f"/api/v1/uploads?artifact_root={artifact_root}&kind=subtitle&filename=source.srt",
        content=(
            b"1\n00:00:00,000 --> 00:00:02,000\n\xe4\xbd\xa0\xe5\xa5\xbd \xe4\xb8\x96\xe7\x95\x8c\n"
        ),
        headers={"content-type": "application/x-subrip"},
    )
    assert upload_subtitle.status_code == 200
    upload_subtitle_payload = ApiEnvelope[dict[str, object]].model_validate(
        upload_subtitle.json()
    )
    assert upload_subtitle_payload.data is not None
    upload_subtitle_data = cast(dict[str, Any], upload_subtitle_payload.data)
    assert Path(cast(str, upload_subtitle_data["path"])).exists()

    job_id = UUID("00000000-0000-0000-0000-000000000351")
    create_response = client.post(
        "/api/v1/jobs",
        json={
            "job_id": str(job_id),
            "input_video": upload_video_data["path"],
            "input_subtitle": upload_subtitle_data["path"],
            "artifact_root": str(artifact_root),
            "source_lang": "zh",
            "target_lang": "en",
            "prefer_ffmpeg": False,
            "allow_render_copy_fallback": True,
            "run_async": True,
        },
    )
    assert create_response.status_code == 200
    create_payload = ApiEnvelope[dict[str, object]].model_validate(
        create_response.json()
    )
    assert create_payload.data is not None
    create_data = cast(dict[str, Any], create_payload.data)
    created_job = cast(dict[str, Any], create_data["job"])
    assert created_job["id"] == str(job_id)
    assert created_job["status"] in {"pending", "running"}

    final_status = created_job["status"]
    for _ in range(50):
        detail_response = client.get(
            f"/api/v1/jobs/{job_id}", params={"artifact_root": str(artifact_root)}
        )
        assert detail_response.status_code == 200
        detail_payload = ApiEnvelope[dict[str, object]].model_validate(
            detail_response.json()
        )
        assert detail_payload.data is not None
        detail_data = cast(dict[str, Any], detail_payload.data)
        final_job = cast(dict[str, Any], detail_data["job"])
        final_status = cast(str, final_job["status"])
        if final_status in {"completed", "failed", "paused"}:
            break
        time.sleep(0.05)

    assert final_status == "completed"
