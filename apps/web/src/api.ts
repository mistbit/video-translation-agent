import type {
  ActiveJobBundle,
  ApiEnvelope,
  ArtifactPayload,
  CreateJobPayload,
  CreateJobRequest,
  JobListPayload,
  JobSummary,
  LogsPayload,
  QaPayload,
} from './types';

async function request<T>(input: string, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init);
  const envelope = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || envelope.code !== 0 || envelope.data === null) {
    throw new Error(envelope.message || 'Request failed.');
  }
  return envelope.data;
}

export function createJob(payload: CreateJobRequest): Promise<CreateJobPayload> {
  return request<CreateJobPayload>('/api/v1/jobs', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}

export function listJobs(params: {
  artifactRoot: string;
  status?: string;
}): Promise<JobListPayload> {
  const search = new URLSearchParams({
    artifact_root: params.artifactRoot,
  });
  if (params.status && params.status !== 'all') {
    search.set('status', params.status);
  }
  return request<JobListPayload>(`/api/v1/jobs?${search.toString()}`);
}

export function getJob(jobId: string, artifactRoot: string): Promise<{ job: JobSummary }> {
  const search = new URLSearchParams({
    artifact_root: artifactRoot,
  });
  return request<{ job: JobSummary }>(`/api/v1/jobs/${jobId}?${search.toString()}`);
}

export function getArtifacts(jobId: string, artifactRoot: string): Promise<ArtifactPayload> {
  const search = new URLSearchParams({
    artifact_root: artifactRoot,
  });
  return request<ArtifactPayload>(`/api/v1/jobs/${jobId}/artifacts?${search.toString()}`);
}

export function getLogs(jobId: string, artifactRoot: string): Promise<LogsPayload> {
  const search = new URLSearchParams({
    artifact_root: artifactRoot,
  });
  return request<LogsPayload>(`/api/v1/jobs/${jobId}/logs?${search.toString()}`);
}

export async function getQa(
  jobId: string,
  artifactRoot: string
): Promise<QaPayload | null> {
  const search = new URLSearchParams({
    artifact_root: artifactRoot,
  });
  const response = await fetch(`/api/v1/jobs/${jobId}/qa?${search.toString()}`);
  const envelope = (await response.json()) as ApiEnvelope<QaPayload>;
  if (response.status === 404) {
    return null;
  }
  if (!response.ok || envelope.code !== 0 || envelope.data === null) {
    throw new Error(envelope.message || 'Failed to fetch QA report.');
  }
  return envelope.data;
}

export async function getActiveJobBundle(
  jobId: string,
  artifactRoot: string
): Promise<ActiveJobBundle> {
  const [{ job }, artifacts, logs, qa] = await Promise.all([
    getJob(jobId, artifactRoot),
    getArtifacts(jobId, artifactRoot),
    getLogs(jobId, artifactRoot),
    getQa(jobId, artifactRoot),
  ]);

  return {
    job,
    artifacts,
    logs,
    qa,
  };
}
