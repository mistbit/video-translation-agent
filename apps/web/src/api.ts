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
  UploadedInputAsset,
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

export async function selectDirectory(
  initialDirectory?: string
): Promise<string | null> {
  const search = new URLSearchParams();
  if (initialDirectory?.trim()) {
    search.set('initial_directory', initialDirectory.trim());
  }
  const suffix = search.size > 0 ? `?${search.toString()}` : '';
  const response = await fetch(`/api/v1/system/select-directory${suffix}`);
  const envelope = (await response.json()) as ApiEnvelope<{ path: string }>;
  if (response.ok && envelope.code === 0 && envelope.data === null) {
    return null;
  }
  if (!response.ok || envelope.code !== 0 || envelope.data === null) {
    throw new Error(envelope.message || 'Failed to select directory.');
  }
  return envelope.data.path;
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
  if (response.ok && envelope.code === 0 && envelope.data === null) {
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

export function uploadInput(
  file: File,
  params: {
    artifactRoot: string;
    kind: 'video' | 'subtitle';
    onProgress?: (progress: number) => void;
  }
): Promise<UploadedInputAsset> {
  const search = new URLSearchParams({
    artifact_root: params.artifactRoot,
    kind: params.kind,
    filename: file.name,
  });

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `/api/v1/uploads?${search.toString()}`);
    xhr.setRequestHeader('content-type', file.type || 'application/octet-stream');

    xhr.upload.onprogress = (event) => {
      if (!params.onProgress || !event.lengthComputable) {
        return;
      }
      params.onProgress(Math.round((event.loaded / event.total) * 100));
    };

    xhr.onerror = () => {
      reject(new Error('Upload request failed.'));
    };

    xhr.onload = () => {
      try {
        const envelope = JSON.parse(xhr.responseText) as ApiEnvelope<UploadedInputAsset>;
        if (xhr.status < 200 || xhr.status >= 300 || envelope.code !== 0 || envelope.data === null) {
          reject(new Error(envelope.message || 'Upload failed.'));
          return;
        }
        resolve(envelope.data);
      } catch (error) {
        reject(
          error instanceof Error ? error : new Error('Failed to parse upload response.')
        );
      }
    };

    xhr.send(file);
  });
}
