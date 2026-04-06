export type ApiEnvelope<T> = {
  code: number;
  message: string;
  data: T | null;
};

export type JobStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'paused'
  | 'cancelled';

export type PipelineConfig = {
  asr_model: string;
  voice_profile: string;
  mix_mode: string;
  caption_strategy: string;
};

export type JobSummary = {
  id: string;
  status: JobStatus;
  current_stage: string | null;
  artifact_root: string;
  error_message: string | null;
  pipeline: PipelineConfig;
  input: {
    video: string;
    subtitle: string | null;
    source_lang: string;
    target_lang: string;
  };
  created_at: string;
  updated_at: string;
};

export type JobListPayload = {
  items: JobSummary[];
  total: number;
  offset: number;
  limit: number;
  artifact_root: string;
};

export type ArtifactItem = {
  id: string;
  stage_name: string | null;
  artifact_type: string;
  path: string;
  size_bytes: number | null;
  created_at: string;
  meta: Record<string, unknown>;
};

export type ArtifactPayload = {
  job_id: string;
  artifact_root: string;
  items: ArtifactItem[];
  count: number;
};

export type UploadedInputAsset = {
  id: string;
  kind: string;
  filename: string;
  path: string;
  size_bytes: number;
  content_type: string | null;
};

export type StageRun = {
  id: string;
  stage_name: string;
  status: string;
  attempt: number;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  error_message: string | null;
};

export type SegmentRerun = {
  id: string;
  segment_key: string;
  reason: string | null;
  requested_at: string;
};

export type LogFile = {
  path: string;
  relative_path: string;
  size_bytes: number;
  updated_at: number;
  content: string | null;
};

export type LogsPayload = {
  job_id: string;
  artifact_root: string;
  log_files: LogFile[];
  stage_runs: StageRun[];
  segment_reruns: SegmentRerun[];
};

export type QaReport = {
  job_id: string;
  segment_count: number;
  blocking: boolean;
  blocking_reasons: string[];
  flag_counts: Record<string, number>;
  overrun_ratio: number;
  [key: string]: unknown;
};

export type QaPayload = {
  job_id: string;
  artifact_root: string;
  report: QaReport;
  report_json_path: string;
  report_markdown_path: string;
  report_markdown: string | null;
};

export type CreateJobRequest = {
  input_video: string;
  input_subtitle?: string;
  artifact_root: string;
  source_lang: string;
  target_lang: string;
  asr_model: string;
  voice_profile: string;
  mix_mode: string;
  prefer_ffmpeg: boolean;
  allow_render_copy_fallback: boolean;
  run_async?: boolean;
};

export type CreateJobPayload = {
  job: JobSummary;
};

export type ActiveJobBundle = {
  job: JobSummary;
  artifacts: ArtifactPayload | null;
  logs: LogsPayload | null;
  qa: QaPayload | null;
};
