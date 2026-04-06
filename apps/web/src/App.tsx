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
import {
  formatDateTimeForLanguage,
  getInitialUiLanguage,
  persistUiLanguage,
  translateStage,
  translateStatus,
  uiCopy,
  type UiLanguage,
} from './i18n';
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
  const [language, setLanguage] = useState<UiLanguage>(getInitialUiLanguage);
  const t = uiCopy[language];
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
    useJobPolling(activeTarget, t.errors.loadJobFailed);

  useEffect(() => {
    persistUiLanguage(language);
  }, [language]);

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
          error instanceof Error ? error.message : t.errors.loadHistoryFailed
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
  }, [historyRefreshToken, historyRoot, historyStatus, t.errors.loadHistoryFailed]);

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
  const subtitleOverridesAsr = form.subtitlePath.trim().length > 0;

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
      setSubmitError(t.errors.videoRequired);
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
        error instanceof Error ? error.message : t.errors.createJobFailed
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
                {t.shell.console}
              </p>
              <h1 className="text-lg font-semibold tracking-tight">{t.shell.agent}</h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-3 md:flex">
              <MetricBadge label={t.metrics.jobs} value={String(historyMetrics.total)} />
              <MetricBadge
                label={t.metrics.running}
                value={String(historyMetrics.running)}
              />
              <MetricBadge label={t.metrics.paused} value={String(historyMetrics.paused)} />
            </div>
            <div className="rounded-full border border-black/5 bg-white p-1 shadow-sm">
              <div className="flex items-center gap-1">
                <span className="px-2 text-[11px] uppercase tracking-[0.18em] text-gray-400">
                  {t.shell.interfaceLabel}
                </span>
                {(['en', 'zh'] as const).map((nextLanguage) => (
                  <button
                    key={nextLanguage}
                    data-testid={`ui-language-${nextLanguage}`}
                    type="button"
                    onClick={() => setLanguage(nextLanguage)}
                    className={`rounded-full px-3 py-2 text-xs font-medium transition ${
                      language === nextLanguage
                        ? 'bg-black text-white'
                        : 'text-gray-500 hover:text-gray-900'
                    }`}
                  >
                    {nextLanguage === 'en' ? 'EN' : '中文'}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-10">
        <section className="mb-8 grid gap-4 md:grid-cols-3">
          <HeroTile
            icon={<Sparkles className="h-4 w-4" />}
            title={t.hero.pathBasedJobsTitle}
            body={t.hero.pathBasedJobsBody}
          />
          <HeroTile
            icon={<Waves className="h-4 w-4" />}
            title={t.hero.asrModesTitle}
            body={t.hero.asrModesBody}
          />
          <HeroTile
            icon={<ShieldAlert className="h-4 w-4" />}
            title={t.hero.feedbackTitle}
            body={t.hero.feedbackBody}
          />
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <ConsoleCard
            title={t.cards.newJobTitle}
            subtitle={t.cards.newJobSubtitle}
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
                    {selectedFileName ?? t.upload.title}
                  </p>
                  <p className="max-w-sm text-sm leading-6 text-gray-500">
                    {t.upload.body}
                  </p>
                  <label className="mt-6 cursor-pointer rounded-full bg-black px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-gray-800">
                    {t.upload.button}
                    <input
                      type="file"
                      accept="video/*"
                      className="hidden"
                      onChange={handleFileReference}
                    />
                  </label>
                </div>
                <div className="mt-4 rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">
                  {t.upload.sameMachine}
                </div>
              </div>

              <div className="grid gap-4">
                <Field
                  label={t.fields.inputVideoPath}
                  icon={<FolderOpen className="h-4 w-4 text-gray-400" />}
                >
                  <input
                    data-testid="input-video-path"
                    value={form.videoPath}
                    onChange={(event) => patchForm('videoPath', event.target.value)}
                    placeholder={t.placeholders.videoPath}
                    className={inputClassName}
                  />
                </Field>
                <Field
                  label={t.fields.subtitlePath}
                  note={t.fields.optional}
                  icon={<FolderOpen className="h-4 w-4 text-gray-400" />}
                >
                  <input
                    data-testid="input-subtitle-path"
                    value={form.subtitlePath}
                    onChange={(event) => patchForm('subtitlePath', event.target.value)}
                    placeholder={t.placeholders.subtitlePath}
                    className={inputClassName}
                  />
                </Field>
                <Field
                  label={t.fields.artifactRoot}
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
                    label={t.fields.sourceLanguage}
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
                      <option value="zh">{t.languageNames.zh}</option>
                      <option value="en">{t.languageNames.en}</option>
                      <option value="ja">{t.languageNames.ja}</option>
                    </select>
                  </Field>
                  <Field
                    label={t.fields.targetLanguage}
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
                      <option value="en">{t.languageNames.en}</option>
                      <option value="zh">{t.languageNames.zh}</option>
                      <option value="ja">{t.languageNames.ja}</option>
                    </select>
                  </Field>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <Field
                    label={t.fields.asrModel}
                    icon={<Waves className="h-4 w-4 text-gray-400" />}
                  >
                    <select
                      data-testid="select-asr-model"
                      value={form.asrModel}
                      onChange={(event) => patchForm('asrModel', event.target.value)}
                      className={inputClassName}
                    >
                      <option value="small">{t.asrOptions.small}</option>
                      <option value="medium">{t.asrOptions.medium}</option>
                    </select>
                  </Field>
                  <Field
                    label={t.fields.voiceProfile}
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
                      <option value="en_female_neutral_01">{t.voiceProfiles.enFemaleNeutral01}</option>
                      <option value="en_male_neutral_01">{t.voiceProfiles.enMaleNeutral01}</option>
                    </select>
                  </Field>
                </div>

                <Field
                  label={t.fields.mixMode}
                  icon={<Volume2 className="h-4 w-4 text-gray-400" />}
                >
                  <select
                    data-testid="select-mix-mode"
                    value={form.mixMode}
                    onChange={(event) => patchForm('mixMode', event.target.value)}
                    className={inputClassName}
                  >
                    <option value="duck">{t.mixModes.duck}</option>
                    <option value="replace">{t.mixModes.replace}</option>
                  </select>
                </Field>

                <div className="grid gap-3 md:grid-cols-2">
                  <ToggleTile
                    title={t.toggles.preferFfmpegTitle}
                    body={t.toggles.preferFfmpegBody}
                    checked={form.preferFfmpeg}
                    onChange={(checked) => patchForm('preferFfmpeg', checked)}
                  />
                  <ToggleTile
                    title={t.toggles.allowFallbackTitle}
                    body={t.toggles.allowFallbackBody}
                    checked={form.allowRenderCopyFallback}
                    onChange={(checked) =>
                      patchForm('allowRenderCopyFallback', checked)
                    }
                  />
                </div>

                <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm leading-6 text-gray-600">
                  <span className="font-medium text-gray-800">{t.hints.asrBase}</span>
                  {showHighAccuracyHint ? ` ${t.hints.asrMediumActive}` : ''}
                  {subtitleOverridesAsr ? ` ${t.hints.asrSubtitleOverride}` : ''}
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
                      {t.actions.startingJob}
                    </>
                  ) : (
                    <>
                      {t.actions.startProcessing}
                      <ChevronRight className="h-4 w-4" />
                    </>
                  )}
                </button>
              </div>
            </div>
          </ConsoleCard>

          <ConsoleCard
            title={t.cards.activeRunTitle}
            subtitle={t.cards.activeRunSubtitle}
            icon={<Clock3 className="h-5 w-5 text-gray-400" />}
          >
            {activeTarget === null ? (
              <EmptyState
                title={t.empty.noJobSelectedTitle}
                body={t.empty.noJobSelectedBody}
              />
            ) : activeLoading && currentJob === null ? (
              <LoadingState label={t.loading.jobDetails} />
            ) : activeError ? (
              <Banner tone="error" message={activeError} />
            ) : currentJob ? (
              <div className="space-y-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    {(() => {
                      const currentStageLabel = translateStage(
                        language,
                        currentJob.current_stage,
                        currentJob.status
                      );

                      return (
                    <div className="mb-2 flex items-center gap-2" data-testid="active-job-status-row">
                      <StatusPill
                        status={currentJob.status}
                        label={translateStatus(language, currentJob.status)}
                      />
                      {currentStageLabel ? (
                        <span className="text-xs uppercase tracking-[0.18em] text-gray-400">
                          {currentStageLabel}
                        </span>
                      ) : null}
                    </div>
                      );
                    })()}
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
                    {t.actions.refreshHistory}
                  </button>
                </div>

                <dl className="grid gap-3 sm:grid-cols-2">
                  <KeyValue label={t.activeRun.artifactRoot} value={currentJob.artifact_root} mono />
                  <KeyValue label={t.activeRun.asrModel} value={currentJob.pipeline.asr_model} />
                  <KeyValue label={t.activeRun.sourceLanguage} value={currentJob.input.source_lang} />
                  <KeyValue label={t.activeRun.targetLanguage} value={currentJob.input.target_lang} />
                </dl>

                {currentJob.error_message ? (
                  <Banner tone="error" message={currentJob.error_message} />
                ) : null}

                {currentQa ? (
                  <div className="rounded-2xl border border-gray-200 bg-white p-4" data-testid="qa-summary">
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2 text-sm font-medium text-gray-800">
                        <ShieldAlert className="h-4 w-4 text-gray-400" />
                        {t.activeRun.qaSummary}
                      </div>
                      <StatusPill
                        status={currentQa.blocking ? 'paused' : 'completed'}
                        label={translateStatus(
                          language,
                          currentQa.blocking ? 'paused' : 'completed'
                        )}
                      />
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <KeyValue
                        label={t.activeRun.segmentsChecked}
                        value={String(currentQa.segment_count)}
                      />
                      <KeyValue
                        label={t.activeRun.overrunRatio}
                        value={`${Math.round(currentQa.overrun_ratio * 100)}%`}
                      />
                    </div>
                    <div className="mt-3 text-sm text-gray-600">
                      {t.activeRun.blockingReasons}:{' '}
                      {currentQa.blocking_reasons.length > 0
                        ? currentQa.blocking_reasons.join(', ')
                        : t.common.none}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-2xl border border-dashed border-gray-200 px-4 py-5 text-sm text-gray-500">
                    {t.activeRun.qaPending}
                  </div>
                )}
              </div>
            ) : (
              <EmptyState
                title={t.empty.noJobDataTitle}
                body={t.empty.noJobDataBody}
              />
            )}
          </ConsoleCard>
        </section>

        <section className="mt-6 grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
          <ConsoleCard
            title={t.cards.historyTitle}
            subtitle={t.cards.historySubtitle}
            icon={<RefreshCw className="h-5 w-5 text-gray-400" />}
            action={
              <button
                type="button"
                onClick={refreshHistory}
                className="flex items-center gap-2 rounded-full border border-gray-200 px-3 py-2 text-xs font-medium text-gray-600 transition hover:border-gray-300 hover:text-gray-900"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                {t.actions.refresh}
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
                <option value="all">{t.history.allStatuses}</option>
                <option value="running">{t.history.running}</option>
                <option value="completed">{t.history.completed}</option>
                <option value="failed">{t.history.failed}</option>
                <option value="paused">{t.history.paused}</option>
                <option value="pending">{t.history.pending}</option>
                <option value="cancelled">{t.history.cancelled}</option>
              </select>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  value={historyQuery}
                  onChange={(event) => setHistoryQuery(event.target.value)}
                  className={`${inputClassName} pl-9`}
                  placeholder={t.placeholders.searchJobs}
                />
              </div>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <MiniMetric label={t.metrics.total} value={String(historyMetrics.total)} />
              <MiniMetric label={t.metrics.completed} value={String(historyMetrics.completed)} />
              <MiniMetric
                label={t.metrics.failedPaused}
                value={String(historyMetrics.attention)}
              />
            </div>

            <div className="mt-5 space-y-3">
              {historyLoading ? (
                <LoadingState label={t.loading.history} compact />
              ) : historyError ? (
                <Banner tone="error" message={historyError} />
              ) : visibleJobs.length === 0 ? (
                <EmptyState
                  title={t.empty.noJobsFoundTitle}
                  body={t.empty.noJobsFoundBody}
                  compact
                />
              ) : (
                visibleJobs.slice(0, 10).map((job) => {
                  const isActive = activeTarget?.jobId === job.id;
                  const historyStageLabel = translateStage(
                    language,
                    job.current_stage,
                    job.status
                  );
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
                        <StatusPill
                          status={job.status}
                          label={translateStatus(language, job.status)}
                          inverted={isActive}
                        />
                        <span
                          className={`text-xs ${
                            isActive ? 'text-white/70' : 'text-gray-400'
                          }`}
                        >
                          {formatDateTimeForLanguage(job.updated_at, language)}
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
                        {historyStageLabel ? <span>{historyStageLabel}</span> : null}
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </ConsoleCard>

          <div className="grid gap-6">
            <ConsoleCard
              title={t.cards.stageTimelineTitle}
              subtitle={t.cards.stageTimelineSubtitle}
              icon={<Clock3 className="h-5 w-5 text-gray-400" />}
            >
              {currentStageRuns.length === 0 ? (
                <EmptyState
                  title={t.empty.noStageRunsTitle}
                  body={t.empty.noStageRunsBody}
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
                            <StatusPill
                              status={run.status}
                              label={translateStatus(language, run.status)}
                            />
                            <span className="text-sm font-medium capitalize text-gray-900">
                              {translateStage(language, run.stage_name)}
                            </span>
                          </div>
                          <div className="mt-2 text-xs text-gray-500">
                            {t.timeline.attempt} {run.attempt} ·{' '}
                            {formatDuration(run.duration_ms, t.common.notAvailable)}
                          </div>
                        </div>
                        <span className="text-xs text-gray-400">
                          {run.finished_at
                            ? formatDateTimeForLanguage(run.finished_at, language)
                            : t.timeline.inProgress}
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
              title={t.cards.artifactsTitle}
              subtitle={t.cards.artifactsSubtitle}
              icon={<FileText className="h-5 w-5 text-gray-400" />}
            >
              <div className="grid gap-6 lg:grid-cols-[1fr_0.9fr]">
                <div>
                  <h3 className="mb-3 text-sm font-medium text-gray-800">
                    {t.artifacts.recentArtifacts}
                  </h3>
                  {currentArtifacts.length === 0 ? (
                    <EmptyState
                      title={t.empty.noArtifactsTitle}
                      body={t.empty.noArtifactsBody}
                      compact
                    />
                  ) : (
                    <div className="space-y-3" data-testid="artifact-list">
                      {currentArtifacts.slice(-8).reverse().map((artifact) => (
                        <ArtifactRow key={artifact.id} artifact={artifact} language={language} />
                      ))}
                    </div>
                  )}
                </div>

                <div className="space-y-4">
                  <div className="rounded-2xl border border-gray-200 bg-white p-4">
                    <div className="mb-2 text-sm font-medium text-gray-800">
                      {t.artifacts.logSnapshot}
                    </div>
                    <div className="space-y-1 text-xs leading-5 text-gray-500">
                      <p>
                        {t.artifacts.stageRuns}: {activeData?.logs?.stage_runs.length ?? 0}
                      </p>
                      <p>
                        {t.artifacts.logFiles}: {activeData?.logs?.log_files.length ?? 0}
                      </p>
                      <p>
                        {t.artifacts.segmentReruns}: {activeData?.logs?.segment_reruns.length ?? 0}
                      </p>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-gray-200 bg-white p-4">
                    <div className="mb-2 text-sm font-medium text-gray-800">
                      {t.artifacts.qaFlagCounts}
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
                        <p className="text-xs text-gray-500">{t.artifacts.noQaFlags}</p>
                      )
                    ) : (
                      <p className="text-xs text-gray-500">
                        {t.artifacts.qaSummaryPending}
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
  label,
  inverted = false,
}: {
  status: string;
  label: string;
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
    <span className={`rounded-full px-2.5 py-1 text-[11px] font-medium tracking-[0.14em] ${className}`}>
      {label}
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

function ArtifactRow({
  artifact,
  language,
}: {
  artifact: ArtifactItem;
  language: UiLanguage;
}) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-medium text-gray-900">{artifact.artifact_type}</div>
          <div className="mt-1 text-xs uppercase tracking-[0.16em] text-gray-400">
            {artifact.stage_name
              ? translateStage(language, artifact.stage_name)
              : uiCopy[language].common.unknownStage}
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

function formatDuration(value: number | null, fallback: string) {
  if (value === null) {
    return fallback;
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

const inputClassName =
  'w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-gray-300 focus:ring-2 focus:ring-black/5';

export default App;
