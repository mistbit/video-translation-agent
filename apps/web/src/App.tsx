import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Clock3,
  FileText,
  FileVideo,
  FolderOpen,
  Globe,
  LoaderCircle,
  Mic2,
  Play,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
  Upload,
  Volume2,
  Waves,
} from 'lucide-react';
import {
  startTransition,
  useDeferredValue,
  useEffect,
  useState,
  type ChangeEvent,
  type DragEvent,
  type ReactNode,
} from 'react';

import { createJob, listJobs } from './api';
import type {
  ActiveJobBundle,
  ArtifactItem,
  CreateJobRequest,
  JobListPayload,
  JobStatus,
} from './types';
import { useJobPolling } from './useJobPolling';

type FormState = {
  videoPath: string;
  subtitlePath: string;
  artifactRoot: string;
  sourceLanguage: string;
  targetLanguage: string;
  asrModel: string;
  voiceProfile: string;
  mixMode: string;
  preferFfmpeg: boolean;
  allowRenderCopyFallback: boolean;
};

type JobTarget = {
  jobId: string;
  artifactRoot: string;
} | null;

const DEFAULT_FORM: FormState = {
  videoPath: '',
  subtitlePath: '',
  artifactRoot: './.artifacts/web-runs',
  sourceLanguage: 'zh',
  targetLanguage: 'en',
  asrModel: 'small',
  voiceProfile: 'en_female_neutral_01',
  mixMode: 'duck',
  preferFfmpeg: false,
  allowRenderCopyFallback: true,
};

function App() {
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [activeTarget, setActiveTarget] = useState<JobTarget>(null);
  const [historyRoot, setHistoryRoot] = useState(DEFAULT_FORM.artifactRoot);
  const [historyStatus, setHistoryStatus] = useState<'all' | JobStatus>('all');
  const [historyQuery, setHistoryQuery] = useState('');
  const deferredHistoryQuery = useDeferredValue(historyQuery);
  const [historyRefreshToken, setHistoryRefreshToken] = useState(0);
  const [history, setHistory] = useState<JobListPayload | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);

  const { data: activeData, isLoading: activeLoading, error: activeError } =
    useJobPolling(activeTarget);

  useEffect(() => {
    let cancelled = false;
    setHistoryLoading(true);
    setHistoryError(null);

    void listJobs({
      artifactRoot: historyRoot.trim() || DEFAULT_FORM.artifactRoot,
      status: historyStatus,
    })
      .then((payload) => {
        if (cancelled) {
          return;
        }
        setHistory(payload);
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        setHistoryError(
          error instanceof Error ? error.message : 'Failed to load job history.'
        );
      })
      .finally(() => {
        if (!cancelled) {
          setHistoryLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [historyRefreshToken, historyRoot, historyStatus]);

  const visibleJobs =
    history?.items.filter((job) => {
      const query = deferredHistoryQuery.trim().toLowerCase();
      if (!query) {
        return true;
      }
      return (
        job.id.toLowerCase().includes(query) ||
        job.input.video.toLowerCase().includes(query) ||
        job.pipeline.asr_model.toLowerCase().includes(query)
      );
    }) ?? [];

  const historyMetrics = summarizeJobs(history?.items ?? []);
  const currentJob = activeData?.job ?? null;
  const currentArtifacts = activeData?.artifacts?.items ?? [];
  const currentStageRuns = activeData?.logs?.stage_runs ?? [];
  const currentQa = activeData?.qa?.report ?? null;
  const showHighAccuracyHint =
    form.sourceLanguage === 'zh' && form.asrModel === 'medium';

  const handleFileReference = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFileName(file.name);
    }
  };

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file) {
      setSelectedFileName(file.name);
    }
  };

  const patchForm = <Key extends keyof FormState>(key: Key, value: FormState[Key]) => {
    setForm((current) => ({
      ...current,
      [key]: value,
    }));
  };

  const refreshHistory = () => {
    setHistoryRefreshToken((value) => value + 1);
  };

  const handleCreateJob = async () => {
    if (!form.videoPath.trim()) {
      setSubmitError('Input video path is required.');
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    const payload: CreateJobRequest = {
      input_video: form.videoPath.trim(),
      input_subtitle: form.subtitlePath.trim() || undefined,
      artifact_root: form.artifactRoot.trim(),
      source_lang: form.sourceLanguage,
      target_lang: form.targetLanguage,
      asr_model: form.asrModel,
      voice_profile: form.voiceProfile,
      mix_mode: form.mixMode,
      prefer_ffmpeg: form.preferFfmpeg,
      allow_render_copy_fallback: form.allowRenderCopyFallback,
    };

    try {
      const response = await createJob(payload);
      startTransition(() => {
        setActiveTarget({
          jobId: response.job.id,
          artifactRoot: response.job.artifact_root,
        });
        setHistoryRoot(response.job.artifact_root);
        setHistoryQuery(response.job.id);
      });
      refreshHistory();
    } catch (error) {
      setSubmitError(
        error instanceof Error ? error.message : 'Failed to create job.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSelectJob = (jobId: string, artifactRoot: string) => {
    startTransition(() => {
      setActiveTarget({ jobId, artifactRoot });
    });
  };

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#ffffff_0%,#f6f6f4_100%)] text-[#171717] selection:bg-gray-100">
      <header className="sticky top-0 z-10 border-b border-black/5 bg-white/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-black shadow-sm">
              <Play className="ml-0.5 h-4 w-4 text-white" />
            </div>
            <div>
              <p className="text-sm uppercase tracking-[0.22em] text-gray-400">
                Local Console
              </p>
              <h1 className="text-lg font-semibold tracking-tight">VTL Agent</h1>
            </div>
          </div>
          <div className="hidden items-center gap-3 md:flex">
            <MetricBadge label="Jobs" value={String(historyMetrics.total)} />
            <MetricBadge label="Running" value={String(historyMetrics.running)} />
            <MetricBadge label="Paused" value={String(historyMetrics.paused)} />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-10">
        <section className="mb-8 grid gap-4 md:grid-cols-3">
          <HeroTile
            icon={<Sparkles className="h-4 w-4" />}
            title="Path-Based Jobs"
            body="This frontend now mirrors the real backend contract: it creates jobs from local filesystem paths on the same machine."
          />
          <HeroTile
            icon={<Waves className="h-4 w-4" />}
            title="Chinese ASR Modes"
            body="Use `small` for balanced local runs or `medium` for higher-accuracy subtitle extraction with tuned decoding."
          />
          <HeroTile
            icon={<ShieldAlert className="h-4 w-4" />}
            title="Operational Feedback"
            body="Track stages, QA blocking reasons, artifacts, and recent runs without dropping back to the terminal."
          />
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <ConsoleCard
            title="New Job"
            subtitle="Create a real processing job using local file paths and backend-backed settings."
            icon={<FileVideo className="h-5 w-5 text-gray-400" />}
          >
            <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
              <div>
                <div
                  className={`flex min-h-[230px] flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 text-center transition-colors ${
                    isDragging
                      ? 'border-black bg-gray-50'
                      : 'border-gray-200 bg-white hover:border-gray-300'
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-gray-100 bg-gray-50">
                    {selectedFileName ? (
                      <CheckCircle2 className="h-6 w-6 text-black" />
                    ) : (
                      <Upload className="h-5 w-5 text-gray-600" />
                    )}
                  </div>
                  <p className="mb-1 font-medium text-gray-900">
                    {selectedFileName ?? 'Reference a local file'}
                  </p>
                  <p className="max-w-sm text-sm leading-6 text-gray-500">
                    Browser file pickers do not expose a usable absolute path. Use this
                    as a visual check, then paste the actual local path into the form.
                  </p>
                  <label className="mt-6 cursor-pointer rounded-full bg-black px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-gray-800">
                    Pick Reference File
                    <input
                      type="file"
                      accept="video/*"
                      className="hidden"
                      onChange={handleFileReference}
                    />
                  </label>
                </div>
                <div className="mt-4 rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">
                  Run this web app on the same machine as the FastAPI service. The API
                  starts jobs from local paths, not uploaded browser blobs.
                </div>
              </div>

              <div className="grid gap-4">
                <Field
                  label="Input Video Path"
                  icon={<FolderOpen className="h-4 w-4 text-gray-400" />}
                >
                  <input
                    data-testid="input-video-path"
                    value={form.videoPath}
                    onChange={(event) => patchForm('videoPath', event.target.value)}
                    placeholder="/Users/you/Videos/source.mp4"
                    className={inputClassName}
                  />
                </Field>
                <Field
                  label="Subtitle Path"
                  note="Optional"
                  icon={<FolderOpen className="h-4 w-4 text-gray-400" />}
                >
                  <input
                    data-testid="input-subtitle-path"
                    value={form.subtitlePath}
                    onChange={(event) => patchForm('subtitlePath', event.target.value)}
                    placeholder="/Users/you/Videos/source.srt"
                    className={inputClassName}
                  />
                </Field>
                <Field
                  label="Artifact Root"
                  icon={<FolderOpen className="h-4 w-4 text-gray-400" />}
                >
                  <input
                    data-testid="input-artifact-root"
                    value={form.artifactRoot}
                    onChange={(event) => patchForm('artifactRoot', event.target.value)}
                    className={inputClassName}
                  />
                </Field>

                <div className="grid gap-4 md:grid-cols-2">
                  <Field
                    label="Source Language"
                    icon={<Globe className="h-4 w-4 text-gray-400" />}
                  >
                    <select
                      data-testid="select-source-language"
                      value={form.sourceLanguage}
                      onChange={(event) =>
                        patchForm('sourceLanguage', event.target.value)
                      }
                      className={inputClassName}
                    >
                      <option value="zh">Chinese</option>
                      <option value="en">English</option>
                      <option value="ja">Japanese</option>
                    </select>
                  </Field>
                  <Field
                    label="Target Language"
                    icon={<Globe className="h-4 w-4 text-gray-400" />}
                  >
                    <select
                      data-testid="select-target-language"
                      value={form.targetLanguage}
                      onChange={(event) =>
                        patchForm('targetLanguage', event.target.value)
                      }
                      className={inputClassName}
                    >
                      <option value="en">English</option>
                      <option value="zh">Chinese</option>
                      <option value="ja">Japanese</option>
                    </select>
                  </Field>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <Field
                    label="ASR Model"
                    icon={<Waves className="h-4 w-4 text-gray-400" />}
                  >
                    <select
                      data-testid="select-asr-model"
                      value={form.asrModel}
                      onChange={(event) => patchForm('asrModel', event.target.value)}
                      className={inputClassName}
                    >
                      <option value="small">Small - Balanced default</option>
                      <option value="medium">Medium - Higher accuracy</option>
                    </select>
                  </Field>
                  <Field
                    label="Voice Profile"
                    icon={<Mic2 className="h-4 w-4 text-gray-400" />}
                  >
                    <select
                      data-testid="select-voice-profile"
                      value={form.voiceProfile}
                      onChange={(event) =>
                        patchForm('voiceProfile', event.target.value)
                      }
                      className={inputClassName}
                    >
                      <option value="en_female_neutral_01">
                        English Female Neutral
                      </option>
                      <option value="en_male_neutral_01">English Male Neutral</option>
                    </select>
                  </Field>
                </div>

                <Field
                  label="Mix Mode"
                  icon={<Volume2 className="h-4 w-4 text-gray-400" />}
                >
                  <select
                    data-testid="select-mix-mode"
                    value={form.mixMode}
                    onChange={(event) => patchForm('mixMode', event.target.value)}
                    className={inputClassName}
                  >
                    <option value="duck">Duck (Lower background audio)</option>
                    <option value="replace">Replace (Mute original audio)</option>
                  </select>
                </Field>

                <div className="grid gap-3 md:grid-cols-2">
                  <ToggleTile
                    title="Prefer ffmpeg"
                    body="Use ffmpeg when available for final render."
                    checked={form.preferFfmpeg}
                    onChange={(checked) => patchForm('preferFfmpeg', checked)}
                  />
                  <ToggleTile
                    title="Allow render fallback"
                    body="Keep jobs moving if ffmpeg render fails."
                    checked={form.allowRenderCopyFallback}
                    onChange={(checked) =>
                      patchForm('allowRenderCopyFallback', checked)
                    }
                  />
                </div>

                <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm leading-6 text-gray-600">
                  <span className="font-medium text-gray-800">Chinese ASR:</span>{' '}
                  switch to <span className="text-black">medium</span> when extraction
                  quality matters more than latency.
                  {showHighAccuracyHint
                    ? ' Tuned decoding is applied automatically in this mode.'
                    : ''}
                </div>

                {submitError ? (
                  <Banner tone="error" message={submitError} />
                ) : null}

                <button
                  data-testid="button-start-processing"
                  type="button"
                  onClick={handleCreateJob}
                  disabled={isSubmitting || !form.videoPath.trim()}
                  className={`flex items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-medium transition-all ${
                    isSubmitting || !form.videoPath.trim()
                      ? 'cursor-not-allowed bg-gray-100 text-gray-400'
                      : 'bg-black text-white shadow-md shadow-black/5 hover:bg-gray-800'
                  }`}
                >
                  {isSubmitting ? (
                    <>
                      <LoaderCircle className="h-4 w-4 animate-spin" />
                      Starting job
                    </>
                  ) : (
                    <>
                      Start Processing
                      <ChevronRight className="h-4 w-4" />
                    </>
                  )}
                </button>
              </div>
            </div>
          </ConsoleCard>

          <ConsoleCard
            title="Active Run"
            subtitle="Live job summary with polling against the current backend API."
            icon={<Clock3 className="h-5 w-5 text-gray-400" />}
          >
            {activeTarget === null ? (
              <EmptyState
                title="No job selected"
                body="Create a new job or pick one from history to inspect stages, artifacts, and QA."
              />
            ) : activeLoading && currentJob === null ? (
              <LoadingState label="Loading job details" />
            ) : activeError ? (
              <Banner tone="error" message={activeError} />
            ) : currentJob ? (
              <div className="space-y-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="mb-2 flex items-center gap-2" data-testid="active-job-status-row">
                      <StatusPill status={currentJob.status} />
                      <span className="text-xs uppercase tracking-[0.18em] text-gray-400">
                        {currentJob.current_stage ?? 'idle'}
                      </span>
                    </div>
                    <h3 className="font-medium text-gray-900" data-testid="active-job-id">{currentJob.id}</h3>
                    <p className="mt-1 text-sm text-gray-500">
                      {currentJob.input.video}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setHistoryRefreshToken((value) => value + 1)}
                    className="rounded-full border border-gray-200 px-3 py-2 text-xs font-medium text-gray-600 transition hover:border-gray-300 hover:text-gray-900"
                  >
                    Refresh history
                  </button>
                </div>

                <dl className="grid gap-3 sm:grid-cols-2">
                  <KeyValue label="Artifact root" value={currentJob.artifact_root} mono />
                  <KeyValue label="ASR model" value={currentJob.pipeline.asr_model} />
                  <KeyValue label="Source language" value={currentJob.input.source_lang} />
                  <KeyValue label="Target language" value={currentJob.input.target_lang} />
                </dl>

                {currentJob.error_message ? (
                  <Banner tone="error" message={currentJob.error_message} />
                ) : null}

                {currentQa ? (
                  <div className="rounded-2xl border border-gray-200 bg-white p-4" data-testid="qa-summary">
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2 text-sm font-medium text-gray-800">
                        <ShieldAlert className="h-4 w-4 text-gray-400" />
                        QA Summary
                      </div>
                      <StatusPill
                        status={currentQa.blocking ? 'paused' : 'completed'}
                      />
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <KeyValue
                        label="Segments checked"
                        value={String(currentQa.segment_count)}
                      />
                      <KeyValue
                        label="Overrun ratio"
                        value={`${Math.round(currentQa.overrun_ratio * 100)}%`}
                      />
                    </div>
                    <div className="mt-3 text-sm text-gray-600">
                      Blocking reasons:{' '}
                      {currentQa.blocking_reasons.length > 0
                        ? currentQa.blocking_reasons.join(', ')
                        : 'none'}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-dashed border-gray-200 px-4 py-5 text-sm text-gray-500">
                    QA report not available yet. It will appear after the pipeline reaches
                    the QA stage.
                  </div>
                )}
              </div>
            ) : (
              <EmptyState
                title="No job data"
                body="Select a job from history or create a new one to start polling."
              />
            )}
          </ConsoleCard>
        </section>

        <section className="mt-6 grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
          <ConsoleCard
            title="History"
            subtitle="Recent jobs under the selected artifact root."
            icon={<RefreshCw className="h-5 w-5 text-gray-400" />}
            action={
              <button
                type="button"
                onClick={refreshHistory}
                className="flex items-center gap-2 rounded-full border border-gray-200 px-3 py-2 text-xs font-medium text-gray-600 transition hover:border-gray-300 hover:text-gray-900"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Refresh
              </button>
            }
          >
            <div className="grid gap-3 md:grid-cols-[1.2fr_0.8fr_auto]">
              <input
                value={historyRoot}
                onChange={(event) => setHistoryRoot(event.target.value)}
                className={inputClassName}
                placeholder="./.artifacts/web-runs"
              />
              <select
                value={historyStatus}
                onChange={(event) =>
                  setHistoryStatus(event.target.value as 'all' | JobStatus)
                }
                className={inputClassName}
              >
                <option value="all">All statuses</option>
                <option value="running">Running</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="paused">Paused</option>
                <option value="pending">Pending</option>
              </select>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  value={historyQuery}
                  onChange={(event) => setHistoryQuery(event.target.value)}
                  className={`${inputClassName} pl-9`}
                  placeholder="Search jobs"
                />
              </div>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <MiniMetric label="Total" value={String(historyMetrics.total)} />
              <MiniMetric label="Completed" value={String(historyMetrics.completed)} />
              <MiniMetric label="Failed/Paused" value={String(historyMetrics.attention)} />
            </div>

            <div className="mt-5 space-y-3">
              {historyLoading ? (
                <LoadingState label="Loading history" compact />
              ) : historyError ? (
                <Banner tone="error" message={historyError} />
              ) : visibleJobs.length === 0 ? (
                <EmptyState
                  title="No jobs found"
                  body="Change the artifact root, clear filters, or create a new run from the panel above."
                  compact
                />
              ) : (
                visibleJobs.slice(0, 10).map((job) => {
                  const isActive = activeTarget?.jobId === job.id;
                  return (
                    <button
                      data-testid={`history-job-${job.id}`}
                      key={job.id}
                      type="button"
                      onClick={() => handleSelectJob(job.id, job.artifact_root)}
                      className={`w-full rounded-2xl border px-4 py-4 text-left transition ${
                        isActive
                          ? 'border-black bg-black text-white'
                          : 'border-gray-200 bg-white hover:border-gray-300'
                      }`}
                    >
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <StatusPill status={job.status} inverted={isActive} />
                        <span
                          className={`text-xs ${
                            isActive ? 'text-white/70' : 'text-gray-400'
                          }`}
                        >
                          {formatDateTime(job.updated_at)}
                        </span>
                      </div>
                      <div className="font-medium">{job.id}</div>
                      <div
                        className={`mt-1 text-sm ${
                          isActive ? 'text-white/80' : 'text-gray-500'
                        }`}
                      >
                        {job.input.video}
                      </div>
                      <div
                        className={`mt-3 flex items-center justify-between text-xs ${
                          isActive ? 'text-white/70' : 'text-gray-400'
                        }`}
                      >
                        <span>{job.pipeline.asr_model}</span>
                        <span>{job.current_stage ?? 'idle'}</span>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </ConsoleCard>

          <div className="grid gap-6">
            <ConsoleCard
              title="Stage Timeline"
              subtitle="Latest known stage runs from the selected job."
              icon={<Clock3 className="h-5 w-5 text-gray-400" />}
            >
              {currentStageRuns.length === 0 ? (
                <EmptyState
                  title="No stage runs yet"
                  body="Once a job starts, stage attempts and timings will appear here."
                  compact
                />
              ) : (
                <div className="space-y-3">
                  {currentStageRuns.map((run) => (
                    <div
                      key={run.id}
                      className="rounded-2xl border border-gray-200 bg-white px-4 py-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <StatusPill status={run.status} />
                            <span className="text-sm font-medium capitalize text-gray-900">
                              {run.stage_name}
                            </span>
                          </div>
                          <div className="mt-2 text-xs text-gray-500">
                            Attempt {run.attempt} · {formatDuration(run.duration_ms)}
                          </div>
                        </div>
                        <span className="text-xs text-gray-400">
                          {run.finished_at ? formatDateTime(run.finished_at) : 'in progress'}
                        </span>
                      </div>
                      {run.error_message ? (
                        <p className="mt-3 text-sm text-red-600">{run.error_message}</p>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </ConsoleCard>

            <ConsoleCard
              title="Artifacts and QA"
              subtitle="Key outputs, logs, and QA report paths for the selected run."
              icon={<FileText className="h-5 w-5 text-gray-400" />}
            >
              <div className="grid gap-6 lg:grid-cols-[1fr_0.9fr]">
                <div>
                  <h3 className="mb-3 text-sm font-medium text-gray-800">
                    Recent Artifacts
                  </h3>
                  {currentArtifacts.length === 0 ? (
                    <EmptyState
                      title="No artifacts yet"
                      body="Artifacts appear as each stage persists outputs."
                      compact
                    />
                  ) : (
                    <div className="space-y-3" data-testid="artifact-list">
                      {currentArtifacts.slice(-8).reverse().map((artifact) => (
                        <ArtifactRow key={artifact.id} artifact={artifact} />
                      ))}
                    </div>
                  )}
                </div>

                <div className="space-y-4">
                  <div className="rounded-2xl border border-gray-200 bg-white p-4">
                    <div className="mb-2 text-sm font-medium text-gray-800">
                      Log Snapshot
                    </div>
                    <div className="space-y-1 text-xs leading-5 text-gray-500">
                      <p>
                        Stage runs: {activeData?.logs?.stage_runs.length ?? 0}
                      </p>
                      <p>
                        Log files: {activeData?.logs?.log_files.length ?? 0}
                      </p>
                      <p>
                        Segment reruns: {activeData?.logs?.segment_reruns.length ?? 0}
                      </p>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-gray-200 bg-white p-4">
                    <div className="mb-2 text-sm font-medium text-gray-800">
                      QA Flag Counts
                    </div>
                    {currentQa ? (
                      Object.keys(currentQa.flag_counts).length > 0 ? (
                        <div className="space-y-1 text-xs leading-5 text-gray-500">
                          {Object.entries(currentQa.flag_counts).map(([key, value]) => (
                            <p key={key}>
                              {key}: {value}
                            </p>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-gray-500">No QA flags recorded.</p>
                      )
                    ) : (
                      <p className="text-xs text-gray-500">
                        QA summary will appear after the pipeline reaches the QA stage.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </ConsoleCard>
          </div>
        </section>
      </main>
    </div>
  );
}

function ConsoleCard({
  title,
  subtitle,
  icon,
  action,
  children,
}: {
  title: string;
  subtitle: string;
  icon: ReactNode;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-[28px] border border-black/5 bg-white p-6 shadow-[0_24px_80px_-48px_rgba(24,24,27,0.35)] md:p-7">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-gray-800">
            {icon}
            {title}
          </div>
          <p className="max-w-2xl text-sm leading-6 text-gray-500">{subtitle}</p>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function HeroTile({
  icon,
  title,
  body,
}: {
  icon: ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-[24px] border border-black/5 bg-white/80 px-5 py-4 shadow-[0_20px_70px_-56px_rgba(24,24,27,0.5)]">
      <div className="mb-3 flex items-center gap-2 text-sm font-medium text-gray-800">
        {icon}
        {title}
      </div>
      <p className="text-sm leading-6 text-gray-500">{body}</p>
    </div>
  );
}

function MetricBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-full border border-black/5 bg-white px-4 py-2 text-right shadow-sm">
      <div className="text-[11px] uppercase tracking-[0.22em] text-gray-400">{label}</div>
      <div className="text-sm font-medium text-gray-900">{value}</div>
    </div>
  );
}

function Field({
  label,
  icon,
  note,
  children,
}: {
  label: string;
  icon: ReactNode;
  note?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-2">
      <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
        {icon}
        {label}
        {note ? <span className="text-xs font-normal text-gray-400">{note}</span> : null}
      </label>
      {children}
    </div>
  );
}

function ToggleTile({
  title,
  body,
  checked,
  onChange,
}: {
  title: string;
  body: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`rounded-2xl border px-4 py-4 text-left transition ${
        checked ? 'border-black bg-black text-white' : 'border-gray-200 bg-white'
      }`}
    >
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="text-sm font-medium">{title}</span>
        <span
          className={`inline-flex h-6 w-11 items-center rounded-full p-1 transition ${
            checked ? 'bg-white/20' : 'bg-gray-100'
          }`}
        >
          <span
            className={`h-4 w-4 rounded-full bg-white transition ${
              checked ? 'translate-x-5' : ''
            }`}
          />
        </span>
      </div>
      <p className={`text-sm leading-6 ${checked ? 'text-white/75' : 'text-gray-500'}`}>
        {body}
      </p>
    </button>
  );
}

function Banner({ tone, message }: { tone: 'error'; message: string }) {
  if (tone === 'error') {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        <div className="flex items-start gap-2">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{message}</span>
        </div>
      </div>
    );
  }
  return null;
}

function LoadingState({ label, compact = false }: { label: string; compact?: boolean }) {
  return (
    <div
      className={`flex items-center gap-3 rounded-2xl border border-dashed border-gray-200 text-gray-500 ${
        compact ? 'px-4 py-4 text-sm' : 'px-5 py-5 text-sm'
      }`}
    >
      <LoaderCircle className="h-4 w-4 animate-spin" />
      {label}
    </div>
  );
}

function EmptyState({
  title,
  body,
  compact = false,
}: {
  title: string;
  body: string;
  compact?: boolean;
}) {
  return (
    <div
      className={`rounded-2xl border border-dashed border-gray-200 text-gray-500 ${
        compact ? 'px-4 py-5' : 'px-5 py-6'
      }`}
    >
      <div className="font-medium text-gray-700">{title}</div>
      <p className="mt-1 text-sm leading-6">{body}</p>
    </div>
  );
}

function StatusPill({
  status,
  inverted = false,
}: {
  status: string;
  inverted?: boolean;
}) {
  const styles = inverted
    ? {
        running: 'bg-white/15 text-white',
        completed: 'bg-white/15 text-white',
        failed: 'bg-white/15 text-white',
        paused: 'bg-white/15 text-white',
        pending: 'bg-white/15 text-white',
      }
    : {
        running: 'bg-amber-50 text-amber-700',
        completed: 'bg-emerald-50 text-emerald-700',
        failed: 'bg-red-50 text-red-700',
        paused: 'bg-yellow-50 text-yellow-700',
        pending: 'bg-gray-100 text-gray-600',
      };
  const className = styles[status as keyof typeof styles] ?? styles.pending;

  return (
    <span className={`rounded-full px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.14em] ${className}`}>
      {status}
    </span>
  );
}

function KeyValue({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3">
      <div className="text-[11px] uppercase tracking-[0.2em] text-gray-400">{label}</div>
      <div className={`mt-1 text-sm text-gray-800 ${mono ? 'break-all font-mono' : ''}`}>
        {value}
      </div>
    </div>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white px-4 py-3">
      <div className="text-[11px] uppercase tracking-[0.18em] text-gray-400">{label}</div>
      <div className="mt-1 text-lg font-semibold tracking-tight text-gray-900">{value}</div>
    </div>
  );
}

function ArtifactRow({ artifact }: { artifact: ArtifactItem }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-medium text-gray-900">{artifact.artifact_type}</div>
          <div className="mt-1 text-xs uppercase tracking-[0.16em] text-gray-400">
            {artifact.stage_name ?? 'unknown stage'}
          </div>
        </div>
        <div className="text-xs text-gray-400">
          {artifact.size_bytes ? formatBytes(artifact.size_bytes) : '-'}
        </div>
      </div>
      <p className="mt-3 break-all font-mono text-xs leading-5 text-gray-500">
        {artifact.path}
      </p>
    </div>
  );
}

function summarizeJobs(items: ActiveJobBundle['job'][]) {
  return {
    total: items.length,
    running: items.filter((item) => item.status === 'running').length,
    paused: items.filter((item) => item.status === 'paused').length,
    completed: items.filter((item) => item.status === 'completed').length,
    attention: items.filter((item) => item.status === 'failed' || item.status === 'paused').length,
  };
}

function formatDuration(value: number | null) {
  if (value === null) {
    return 'n/a';
  }
  if (value < 1000) {
    return `${value} ms`;
  }
  return `${(value / 1000).toFixed(1)} s`;
}

function formatBytes(value: number) {
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

const inputClassName =
  'w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-gray-300 focus:ring-2 focus:ring-black/5';

export default App;
