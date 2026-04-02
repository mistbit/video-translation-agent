from uuid import UUID

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from video_translation_agent.api.services import (
    CreateJobRequest,
    JobNotFoundError,
    SegmentRerunRequest,
    StageRerunRequest,
    create_job,
    get_job,
    get_job_artifacts,
    get_job_logs,
    get_job_qa,
    list_jobs,
    rerun_segment,
    rerun_stage,
)
from video_translation_agent.domain.enums import JobStatus, StageName
from video_translation_agent.domain.models import ApiEnvelope
from video_translation_agent.settings import settings

app = FastAPI(title=settings.app_name)


@app.get(f"{settings.api_prefix}/health")
def health() -> ApiEnvelope[dict[str, str]]:
    return ApiEnvelope(data={"status": "ok"})


@app.get(f"{settings.api_prefix}/health/ready")
def ready() -> ApiEnvelope[dict[str, str]]:
    return ApiEnvelope(data={"status": "ready"})


@app.post(f"{settings.api_prefix}/jobs")
def create_job_endpoint(request: CreateJobRequest):
    try:
        job = create_job(request)
    except Exception as exc:
        return _error_envelope(status_code=400, code=4001, message=str(exc))

    return ApiEnvelope(data={"job": job.model_dump(mode="json")})


@app.get(f"{settings.api_prefix}/jobs")
def list_jobs_endpoint(
    artifact_root: str = settings.artifact_root,
    status: JobStatus | None = None,
    offset: int = 0,
    limit: int = 50,
):
    data = list_jobs(
        artifact_root=artifact_root,
        status=status,
        offset=max(offset, 0),
        limit=max(min(limit, 200), 1),
    )
    return ApiEnvelope(data=data)


@app.get(f"{settings.api_prefix}/jobs/{{job_id}}")
def get_job_endpoint(
    job_id: UUID,
    artifact_root: str = settings.artifact_root,
):
    try:
        job = get_job(job_id=job_id, artifact_root=artifact_root)
    except JobNotFoundError as exc:
        return _error_envelope(status_code=404, code=4040, message=str(exc))

    return ApiEnvelope(data={"job": job.model_dump(mode="json")})


@app.get(f"{settings.api_prefix}/jobs/{{job_id}}/artifacts")
def get_job_artifacts_endpoint(
    job_id: UUID,
    artifact_root: str = settings.artifact_root,
):
    try:
        payload = get_job_artifacts(job_id=job_id, artifact_root=artifact_root)
    except JobNotFoundError as exc:
        return _error_envelope(status_code=404, code=4040, message=str(exc))

    return ApiEnvelope(data=payload)


@app.get(f"{settings.api_prefix}/jobs/{{job_id}}/logs")
def get_job_logs_endpoint(
    job_id: UUID,
    artifact_root: str = settings.artifact_root,
):
    try:
        payload = get_job_logs(job_id=job_id, artifact_root=artifact_root)
    except JobNotFoundError as exc:
        return _error_envelope(status_code=404, code=4040, message=str(exc))

    return ApiEnvelope(data=payload)


@app.post(f"{settings.api_prefix}/jobs/{{job_id}}/stages/{{stage}}/rerun")
def rerun_stage_endpoint(
    job_id: UUID,
    stage: StageName,
    request: StageRerunRequest,
):
    try:
        payload = rerun_stage(job_id=job_id, stage=stage, request=request)
    except JobNotFoundError as exc:
        return _error_envelope(status_code=404, code=4040, message=str(exc))
    except Exception as exc:
        return _error_envelope(status_code=400, code=4002, message=str(exc))

    return ApiEnvelope(data=payload)


@app.post(f"{settings.api_prefix}/jobs/{{job_id}}/segments/{{segment_key}}/rerun")
def rerun_segment_endpoint(
    job_id: UUID,
    segment_key: str,
    request: SegmentRerunRequest,
):
    try:
        payload = rerun_segment(
            job_id=job_id,
            segment_key=segment_key,
            request=request,
        )
    except JobNotFoundError as exc:
        return _error_envelope(status_code=404, code=4040, message=str(exc))
    except Exception as exc:
        return _error_envelope(status_code=400, code=4003, message=str(exc))

    return ApiEnvelope(data=payload)


@app.get(f"{settings.api_prefix}/jobs/{{job_id}}/qa")
def get_job_qa_endpoint(
    job_id: UUID,
    artifact_root: str = settings.artifact_root,
):
    try:
        payload = get_job_qa(job_id=job_id, artifact_root=artifact_root)
    except JobNotFoundError as exc:
        return _error_envelope(status_code=404, code=4040, message=str(exc))
    except FileNotFoundError as exc:
        return _error_envelope(status_code=404, code=4041, message=str(exc))

    return ApiEnvelope(data=payload)


def _error_envelope(*, status_code: int, code: int, message: str) -> JSONResponse:
    payload = ApiEnvelope[None](code=code, message=message, data=None).model_dump(
        mode="json"
    )
    return JSONResponse(status_code=status_code, content=payload)
