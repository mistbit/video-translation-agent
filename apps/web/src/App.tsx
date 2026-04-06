import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Clock3,
  FileText,
  FileUp,
  FileVideo,
  FolderOpen,
  Globe,
  Languages,
  LoaderCircle,
  Mic2,
  Play,
  RefreshCw,
  Search,
  Server,
  ShieldAlert,
  Sparkles,
  Upload,
  Volume2,
  Waves,
  Workflow,
  X,
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

import { createJob, listJobs, selectDirectory, uploadInput } from './api';
import {
  formatDateTimeForLanguage,
  getInitialUiLanguage,
  persistUiLanguage,
  translateStage,
  translateStatus,
  uiCopy,
  type SubmissionMode,
  type UiLanguage,
} from './i18n';
import type {
  ActiveJobBundle,
  ArtifactItem,
  CreateJobRequest,
  JobListPayload,
  JobStatus,
  StageRun,
  UploadedInputAsset,
} from './types';
import { useJobPolling } from './useJobPolling';

const STAGE_SEQUENCE = [
  'ingest',
  'caption',
  'normalize',
  'translate',
  'tts',
  'render',
  'qa',
] as const;

type FormState = {
  artifactRoot: string;
  sourceLanguage: string;
  targetLanguage: string;
  asrModel: string;
  voiceProfile: string;
  mixMode: string;
  preferFfmpeg: boolean;
  allowRenderCopyFallback: boolean;
  videoPath: string;
  subtitlePath: string;
};

type UploadState = {
  video: File | null;
  subtitle: File | null;
};

type UploadedAssets = {
  video: UploadedInputAsset | null;
  subtitle: UploadedInputAsset | null;
};

type UploadProgress = {
  video: number;
  subtitle: number;
};

type JobTarget = {
  jobId: string;
  artifactRoot: string;
} | null;

type SubmissionPhase = 'idle' | 'uploading' | 'queueing';

type StageView = {
  stage: (typeof STAGE_SEQUENCE)[number];
  status: 'pending' | 'running' | 'completed' | 'failed';
  durationMs: number | null;
  attempt: number | null;
  errorMessage: string | null;
};

const DEFAULT_FORM: FormState = {
  artifactRoot: './.artifacts/web-runs',
  sourceLanguage: 'zh',
  targetLanguage: 'en',
  asrModel: 'small',
  voiceProfile: 'en_female_neutral_01',
  mixMode: 'duck',
  preferFfmpeg: true,
  allowRenderCopyFallback: true,
  videoPath: '',
  subtitlePath: '',
};

function App() {
  const [language, setLanguage] = useState<UiLanguage>(getInitialUiLanguage);
  const t = uiCopy[language];
  const [submissionMode, setSubmissionMode] = useState<SubmissionMode>('upload');
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);
  const [uploadFiles, setUploadFiles] = useState<UploadState>({
    video: null,
    subtitle: null,
  });
  const [uploadedAssets, setUploadedAssets] = useState<UploadedAssets>({
    video: null,
    subtitle: null,
  });
  const [uploadProgress, setUploadProgress] = useState<UploadProgress>({
    video: 0,
    subtitle: 0,
  });
  const [uploadDragging, setUploadDragging] = useState<'video' | 'subtitle' | null>(
    null
  );
  const [submissionPhase, setSubmissionPhase] = useState<SubmissionPhase>('idle');
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
  const [pickingComposerDirectory, setPickingComposerDirectory] = useState(false);
  const [pickingHistoryDirectory, setPickingHistoryDirectory] = useState(false);

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
        if (!cancelled) {
          setHistory(payload);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setHistoryError(
            error instanceof Error ? error.message : t.errors.loadHistoryFailed
          );
        }
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
  const stageViews = buildStageViews(currentJob, currentStageRuns);
  const completedStages = stageViews.filter((item) => item.status === 'completed').length;
  const progressPercent =
    currentJob && currentJob.status === 'completed'
      ? 100
      : Math.round((completedStages / STAGE_SEQUENCE.length) * 100);
  const activeStageLabel = currentJob
    ? translateStage(language, currentJob.current_stage, currentJob.status)
    : t.common.idle;
  const showHighAccuracyHint =
    form.sourceLanguage === 'zh' && form.asrModel === 'medium';
  const subtitleOverridesAsr =
    submissionMode === 'upload'
      ? uploadFiles.subtitle !== null
      : form.subtitlePath.trim().length > 0;
  const invalidRenderConfig = !form.preferFfmpeg && !form.allowRenderCopyFallback;
  const readyForSubmit =
    submissionMode === 'upload'
      ? uploadFiles.video !== null
      : form.videoPath.trim().length > 0;
  const isSubmitting = submissionPhase !== 'idle';
  const recentStageRuns = [...currentStageRuns].slice(-7).reverse();

  const patchForm = <Key extends keyof FormState>(key: Key, value: FormState[Key]) => {
    setForm((current) => ({
      ...current,
      [key]: value,
    }));
  };

  const refreshHistory = () => {
    setHistoryRefreshToken((value) => value + 1);
  };

  const handlePickDirectory = async (target: 'composer' | 'history') => {
    const isComposer = target === 'composer';
    const currentValue = isComposer ? form.artifactRoot : historyRoot;
    const setBusy = isComposer
      ? setPickingComposerDirectory
      : setPickingHistoryDirectory;
    setBusy(true);
    try {
      const selected = await selectDirectory(currentValue);
      if (!selected) {
        return;
      }
      if (isComposer) {
        patchForm('artifactRoot', selected);
      } else {
        setHistoryRoot(selected);
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : t.errors.directorySelectionFailed;
      if (isComposer) {
        setSubmitError(message);
      } else {
        setHistoryError(message);
      }
    } finally {
      setBusy(false);
    }
  };

  const handleUploadSelection = (kind: keyof UploadState, file: File | null) => {
    setUploadFiles((current) => ({
      ...current,
      [kind]: file,
    }));
    setUploadedAssets((current) => ({
      ...current,
      [kind]: null,
    }));
    setUploadProgress((current) => ({
      ...current,
      [kind]: 0,
    }));
  };

  const handleDrop =
    (kind: keyof UploadState) => (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setUploadDragging(null);
      const file = event.dataTransfer.files?.[0] ?? null;
      handleUploadSelection(kind, file);
    };

  const handleDragOver =
    (kind: keyof UploadState) => (event: DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setUploadDragging(kind);
    };

  const handleDragLeave = () => {
    setUploadDragging(null);
  };

  const handleCreateJob = async () => {
    if (invalidRenderConfig) {
      setSubmitError(t.settings.renderWarning);
      return;
    }

    if (!readyForSubmit) {
      setSubmitError(
        submissionMode === 'upload' ? t.errors.uploadVideoRequired : t.errors.videoRequired
      );
      return;
    }

    setSubmitError(null);

    try {
      let inputVideoPath = form.videoPath.trim();
      let inputSubtitlePath = form.subtitlePath.trim() || undefined;

      if (submissionMode === 'upload') {
        setSubmissionPhase('uploading');

        const uploadedVideo = await uploadInput(uploadFiles.video as File, {
          artifactRoot: form.artifactRoot.trim(),
          kind: 'video',
          onProgress: (progress) =>
            setUploadProgress((current) => ({ ...current, video: progress })),
        });

        let uploadedSubtitle: UploadedInputAsset | null = null;
        if (uploadFiles.subtitle) {
          uploadedSubtitle = await uploadInput(uploadFiles.subtitle, {
            artifactRoot: form.artifactRoot.trim(),
            kind: 'subtitle',
            onProgress: (progress) =>
              setUploadProgress((current) => ({ ...current, subtitle: progress })),
          });
        }

        setUploadedAssets({
          video: uploadedVideo,
          subtitle: uploadedSubtitle,
        });

        inputVideoPath = uploadedVideo.path;
        inputSubtitlePath = uploadedSubtitle?.path;
      }

      setSubmissionPhase('queueing');

      const payload: CreateJobRequest = {
        input_video: inputVideoPath,
        input_subtitle: inputSubtitlePath,
        artifact_root: form.artifactRoot.trim(),
        source_lang: form.sourceLanguage,
        target_lang: form.targetLanguage,
        asr_model: form.asrModel,
        voice_profile: form.voiceProfile,
        mix_mode: form.mixMode,
        prefer_ffmpeg: form.preferFfmpeg,
        allow_render_copy_fallback: form.allowRenderCopyFallback,
        run_async: true,
      };

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
        error instanceof Error
          ? error.message
          : submissionMode === 'upload'
            ? t.errors.uploadFailed
            : t.errors.createJobFailed
      );
    } finally {
      setSubmissionPhase('idle');
    }
  };

  const handleSelectJob = (jobId: string, artifactRoot: string) => {
    startTransition(() => {
      setActiveTarget({ jobId, artifactRoot });
    });
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,#ffffff_0%,#f5f5f2_55%,#efefe8_100%)] text-[#171717] selection:bg-black/10">
      <header className="sticky top-0 z-20 border-b border-black/5 bg-white/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-black shadow-[0_16px_40px_-18px_rgba(0,0,0,0.55)]">
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
            <div className="hidden items-center gap-3 lg:flex">
              <MetricBadge label={t.metrics.jobs} value={String(historyMetrics.total)} />
              <MetricBadge
                label={t.metrics.running}
                value={String(historyMetrics.running)}
              />
              <MetricBadge
                label={t.metrics.attention}
                value={String(historyMetrics.attention)}
              />
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
            icon={<Upload className="h-4 w-4" />}
            title={t.summary.uploadTitle}
            body={t.summary.uploadBody}
          />
          <HeroTile
            icon={<Workflow className="h-4 w-4" />}
            title={t.summary.pipelineTitle}
            body={t.summary.pipelineBody}
          />
          <HeroTile
            icon={<Languages className="h-4 w-4" />}
            title={t.summary.bilingualTitle}
            body={t.summary.bilingualBody}
          />
        </section>

        <section className="mb-8 rounded-[32px] border border-black/5 bg-white px-6 py-6 shadow-[0_40px_120px_-64px_rgba(0,0,0,0.4)]">
          <div className="mb-3 flex items-center gap-2 text-sm font-medium text-gray-900">
            <Sparkles className="h-4 w-4 text-gray-500" />
            {t.summary.title}
          </div>
          <p className="max-w-4xl text-sm leading-7 text-gray-600">{t.summary.body}</p>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.04fr_0.96fr]">
          <ShellCard
            title={t.composer.title}
            subtitle={t.composer.subtitle}
            icon={<FileUp className="h-5 w-5 text-gray-400" />}
          >
            <div className="mb-5 flex flex-wrap gap-2">
              <ModePill
                active={submissionMode === 'upload'}
                onClick={() => setSubmissionMode('upload')}
                label={t.composer.uploadMode}
                testId="mode-upload"
              />
              <ModePill
                active={submissionMode === 'path'}
                onClick={() => setSubmissionMode('path')}
                label={t.composer.pathMode}
                testId="mode-path"
              />
            </div>

            {submissionMode === 'upload' ? (
              <div className="space-y-4">
                <div className="grid gap-4 lg:grid-cols-2">
                  <UploadDropzone
                    title={t.upload.videoTitle}
                    helper={t.upload.emptyVideo}
                    file={uploadFiles.video}
                    uploadedAsset={uploadedAssets.video}
                    progress={uploadProgress.video}
                    isDragging={uploadDragging === 'video'}
                    onDragOver={handleDragOver('video')}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop('video')}
                    onChange={(file) => handleUploadSelection('video', file)}
                    onClear={() => handleUploadSelection('video', null)}
                    buttonLabel={uploadFiles.video ? t.upload.replace : t.upload.browse}
                    testId="upload-video-input"
                  />
                  <UploadDropzone
                    title={`${t.upload.subtitleTitle} · ${t.upload.optional}`}
                    helper={t.upload.emptySubtitle}
                    file={uploadFiles.subtitle}
                    uploadedAsset={uploadedAssets.subtitle}
                    progress={uploadProgress.subtitle}
                    isDragging={uploadDragging === 'subtitle'}
                    onDragOver={handleDragOver('subtitle')}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop('subtitle')}
                    onChange={(file) => handleUploadSelection('subtitle', file)}
                    onClear={() => handleUploadSelection('subtitle', null)}
                    buttonLabel={uploadFiles.subtitle ? t.upload.replace : t.upload.browse}
                    testId="upload-subtitle-input"
                  />
                </div>
                <p className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm leading-6 text-gray-600">
                  {t.upload.helper}
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <Field
                  label={t.paths.videoPath}
                  icon={<FolderOpen className="h-4 w-4 text-gray-400" />}
                >
                  <input
                    data-testid="input-video-path"
                    value={form.videoPath}
                    onChange={(event) => patchForm('videoPath', event.target.value)}
                    placeholder={t.paths.videoPlaceholder}
                    className={inputClassName}
                  />
                </Field>
                <Field
                  label={`${t.paths.subtitlePath} · ${t.upload.optional}`}
                  icon={<FolderOpen className="h-4 w-4 text-gray-400" />}
                >
                  <input
                    data-testid="input-subtitle-path"
                    value={form.subtitlePath}
                    onChange={(event) => patchForm('subtitlePath', event.target.value)}
                    placeholder={t.paths.subtitlePlaceholder}
                    className={inputClassName}
                  />
                </Field>
                <p className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm leading-6 text-gray-600">
                  {t.paths.helper}
                </p>
              </div>
            )}

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <Field
                label={t.composer.artifactRoot}
                icon={<FolderOpen className="h-4 w-4 text-gray-400" />}
              >
                <DirectoryInput
                  inputTestId="input-artifact-root"
                  buttonTestId="button-select-artifact-root"
                  value={form.artifactRoot}
                  onChange={(value) => patchForm('artifactRoot', value)}
                  onPick={() => void handlePickDirectory('composer')}
                  buttonLabel={
                    pickingComposerDirectory
                      ? t.actions.selectingDirectory
                      : t.actions.chooseDirectory
                  }
                  disabled={pickingComposerDirectory}
                />
              </Field>
              <Field
                label={t.composer.sourceLanguage}
                icon={<Globe className="h-4 w-4 text-gray-400" />}
              >
                <select
                  data-testid="select-source-language"
                  value={form.sourceLanguage}
                  onChange={(event) => patchForm('sourceLanguage', event.target.value)}
                  className={inputClassName}
                >
                  <option value="zh">{t.languageNames.zh}</option>
                  <option value="en">{t.languageNames.en}</option>
                  <option value="ja">{t.languageNames.ja}</option>
                </select>
              </Field>
              <Field
                label={t.composer.targetLanguage}
                icon={<Globe className="h-4 w-4 text-gray-400" />}
              >
                <select
                  data-testid="select-target-language"
                  value={form.targetLanguage}
                  onChange={(event) => patchForm('targetLanguage', event.target.value)}
                  className={inputClassName}
                >
                  <option value="en">{t.languageNames.en}</option>
                  <option value="zh">{t.languageNames.zh}</option>
                  <option value="ja">{t.languageNames.ja}</option>
                </select>
              </Field>
              <Field
                label={t.composer.asrModel}
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
                label={t.composer.voiceProfile}
                icon={<Mic2 className="h-4 w-4 text-gray-400" />}
              >
                <select
                  data-testid="select-voice-profile"
                  value={form.voiceProfile}
                  onChange={(event) => patchForm('voiceProfile', event.target.value)}
                  className={inputClassName}
                >
                  <option value="en_female_neutral_01">
                    {t.voiceProfiles.enFemaleNeutral01}
                  </option>
                  <option value="en_male_neutral_01">
                    {t.voiceProfiles.enMaleNeutral01}
                  </option>
                </select>
              </Field>
              <Field
                label={t.composer.mixMode}
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
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-2">
              <ToggleTile
                title={t.settings.preferFfmpegTitle}
                body={t.settings.preferFfmpegBody}
                checked={form.preferFfmpeg}
                onChange={(checked) => patchForm('preferFfmpeg', checked)}
              />
              <ToggleTile
                title={t.settings.allowFallbackTitle}
                body={t.settings.allowFallbackBody}
                checked={form.allowRenderCopyFallback}
                onChange={(checked) => patchForm('allowRenderCopyFallback', checked)}
              />
            </div>

            <div className="mt-5 space-y-3">
              <InfoStrip>{t.settings.asrHint}</InfoStrip>
              {showHighAccuracyHint ? <InfoStrip>{t.settings.asrHintMedium}</InfoStrip> : null}
              {subtitleOverridesAsr ? <InfoStrip>{t.settings.sidecarHint}</InfoStrip> : null}
              {invalidRenderConfig ? (
                <Banner message={t.settings.renderWarning} />
              ) : null}
              {submitError ? <Banner message={submitError} /> : null}
            </div>

            <div className="mt-6 grid gap-4 lg:grid-cols-[0.92fr_1.08fr]">
              <div className="rounded-[24px] border border-gray-200 bg-gray-50 p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-medium text-gray-800">
                  <Upload className="h-4 w-4 text-gray-400" />
                  {t.composer.uploadProgress}
                </div>
                <div className="space-y-3 text-sm text-gray-600">
                  <ProgressLine
                    label={t.upload.videoTitle}
                    value={uploadProgress.video}
                    fallbackLabel={t.common.uploadPending}
                  />
                  <ProgressLine
                    label={t.upload.subtitleTitle}
                    value={uploadProgress.subtitle}
                    fallbackLabel={t.common.uploadPending}
                  />
                  <p className="pt-2 text-xs text-gray-500">
                    {submissionPhase === 'uploading'
                      ? t.actions.uploading
                      : submissionPhase === 'queueing'
                        ? t.actions.queueing
                        : t.pipeline.waiting}
                  </p>
                </div>
              </div>

              <div className="rounded-[24px] border border-gray-200 bg-white p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-medium text-gray-800">
                  <Server className="h-4 w-4 text-gray-400" />
                  {t.composer.selectedAssets}
                </div>
                <div className="space-y-3">
                  <PreparedInputRow
                    label={t.upload.videoTitle}
                    value={
                      uploadedAssets.video?.path ??
                      (submissionMode === 'path'
                        ? form.videoPath.trim() || t.common.uploadPending
                        : uploadFiles.video?.name || t.common.uploadPending)
                    }
                  />
                  <PreparedInputRow
                    label={t.upload.subtitleTitle}
                    value={
                      uploadedAssets.subtitle?.path ??
                      (submissionMode === 'path'
                        ? form.subtitlePath.trim() || t.common.none
                        : uploadFiles.subtitle?.name || t.common.none)
                    }
                  />
                </div>
              </div>
            </div>

            <button
              data-testid="button-start-processing"
              type="button"
              onClick={handleCreateJob}
              disabled={isSubmitting || !readyForSubmit || invalidRenderConfig}
              className={`mt-6 flex w-full items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-medium transition ${
                isSubmitting || !readyForSubmit || invalidRenderConfig
                  ? 'cursor-not-allowed bg-gray-100 text-gray-400'
                  : 'bg-black text-white shadow-[0_20px_44px_-20px_rgba(0,0,0,0.55)] hover:bg-gray-800'
              }`}
            >
              {submissionPhase === 'uploading' || submissionPhase === 'queueing' ? (
                <>
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                  {submissionPhase === 'uploading'
                    ? t.actions.uploading
                    : t.actions.queueing}
                </>
              ) : (
                <>
                  {t.actions.startProcessing}
                  <ChevronRight className="h-4 w-4" />
                </>
              )}
            </button>
          </ShellCard>

          <div className="grid gap-6">
            <ShellCard
              title={t.pipeline.title}
              subtitle={t.pipeline.subtitle}
              icon={<Workflow className="h-5 w-5 text-gray-400" />}
            >
              {!currentJob && !activeLoading ? (
                <EmptyState
                  title={t.empty.noActiveTitle}
                  body={t.empty.noActiveBody}
                />
              ) : activeLoading && !currentJob ? (
                <LoadingState label={t.errors.loadJobFailed} />
              ) : activeError ? (
                <Banner message={activeError} />
              ) : currentJob ? (
                <div className="space-y-5">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <div
                        className="mb-2 flex items-center gap-2"
                        data-testid="active-job-status-row"
                      >
                        <StatusPill
                          status={currentJob.status}
                          label={translateStatus(language, currentJob.status)}
                        />
                        {activeStageLabel ? (
                          <span className="text-xs uppercase tracking-[0.18em] text-gray-400">
                            {activeStageLabel}
                          </span>
                        ) : null}
                      </div>
                      <h3
                        className="font-medium text-gray-900"
                        data-testid="active-job-id"
                      >
                        {currentJob.id}
                      </h3>
                      <p className="mt-1 text-sm text-gray-500">
                        {currentJob.input.video}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={refreshHistory}
                      className="rounded-full border border-gray-200 px-3 py-2 text-xs font-medium text-gray-600 transition hover:border-gray-300 hover:text-gray-900"
                    >
                      {t.actions.refresh}
                    </button>
                  </div>

                  <div className="rounded-[24px] border border-gray-200 bg-gray-50 p-4">
                    <div className="mb-2 flex items-center justify-between gap-3 text-sm text-gray-600">
                      <span>{t.pipeline.overallProgress}</span>
                      <span className="font-medium text-gray-900">{progressPercent}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-white">
                      <div
                        className="h-2 rounded-full bg-black transition-all"
                        style={{ width: `${progressPercent}%` }}
                      />
                    </div>
                    <div className="mt-3 grid gap-3 sm:grid-cols-3">
                      <KeyValue
                        label={t.pipeline.currentStage}
                        value={activeStageLabel ?? t.common.idle}
                      />
                      <KeyValue
                        label={t.pipeline.createdFrom}
                        value={currentJob.input.subtitle ? 'subtitle' : 'audio/video'}
                      />
                      <KeyValue
                        label={t.pipeline.artifactRoot}
                        value={currentJob.artifact_root}
                        mono
                      />
                    </div>
                  </div>

                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {stageViews.map((stageView) => (
                      <StageTile
                        key={stageView.stage}
                        stageView={stageView}
                        language={language}
                        waitingLabel={t.pipeline.waiting}
                        durationLabel={t.pipeline.duration}
                        attemptsLabel={t.pipeline.stageAttempts}
                        inProgressLabel={t.pipeline.inProgress}
                        notAvailableLabel={t.common.notAvailable}
                      />
                    ))}
                  </div>

                  {currentJob.error_message ? (
                    <Banner message={`${t.pipeline.failedMessage}: ${currentJob.error_message}`} />
                  ) : null}
                </div>
              ) : (
                <EmptyState title={t.empty.noActiveTitle} body={t.empty.noActiveBody} />
              )}
            </ShellCard>

            <ShellCard
              title={t.insights.title}
              subtitle={t.insights.subtitle}
              icon={<FileText className="h-5 w-5 text-gray-400" />}
            >
              {!currentJob ? (
                <EmptyState
                  title={t.empty.noPipelineTitle}
                  body={t.empty.noPipelineBody}
                  compact
                />
              ) : (
                <div className="grid gap-6 lg:grid-cols-[0.92fr_1.08fr]">
                  <div className="space-y-4">
                    <div
                      className="rounded-[24px] border border-gray-200 bg-white p-4"
                      data-testid="qa-summary"
                    >
                      <div className="mb-3 flex items-center gap-2 text-sm font-medium text-gray-800">
                        <ShieldAlert className="h-4 w-4 text-gray-400" />
                        {t.insights.qaSummary}
                      </div>
                      {currentQa ? (
                        <div className="space-y-3">
                          <InsightMetric
                            label={t.insights.segmentsChecked}
                            value={String(currentQa.segment_count)}
                          />
                          <InsightMetric
                            label={t.insights.overrunRatio}
                            value={`${Math.round(currentQa.overrun_ratio * 100)}%`}
                          />
                          <InsightMetric
                            label={t.insights.blockingReasons}
                            value={
                              currentQa.blocking_reasons.length > 0
                                ? currentQa.blocking_reasons.join(', ')
                                : t.common.none
                            }
                          />
                        </div>
                      ) : (
                        <p className="text-sm leading-6 text-gray-500">{t.insights.noQa}</p>
                      )}
                    </div>

                    <div className="rounded-[24px] border border-gray-200 bg-gray-50 p-4">
                      <div className="mb-3 text-sm font-medium text-gray-800">
                        {t.insights.logs}
                      </div>
                      <div className="grid gap-3 sm:grid-cols-3">
                        <MiniMetric
                          label={t.insights.stageRuns}
                          value={String(activeData?.logs?.stage_runs.length ?? 0)}
                        />
                        <MiniMetric
                          label={t.insights.logs}
                          value={String(activeData?.logs?.log_files.length ?? 0)}
                        />
                        <MiniMetric
                          label={t.insights.segmentReruns}
                          value={String(activeData?.logs?.segment_reruns.length ?? 0)}
                        />
                      </div>
                    </div>
                  </div>

                  <div>
                    <div className="mb-3 flex items-center gap-2 text-sm font-medium text-gray-800">
                      <FileVideo className="h-4 w-4 text-gray-400" />
                      {t.insights.artifacts}
                    </div>
                    {currentArtifacts.length === 0 ? (
                      <EmptyState
                        title={t.insights.artifacts}
                        body={t.insights.noArtifacts}
                        compact
                      />
                    ) : (
                      <div className="space-y-3" data-testid="artifact-list">
                        {currentArtifacts.slice(-6).reverse().map((artifact) => (
                          <ArtifactRow
                            key={artifact.id}
                            artifact={artifact}
                            language={language}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </ShellCard>
          </div>
        </section>

        <section className="mt-6 grid gap-6 xl:grid-cols-[0.88fr_1.12fr]">
          <ShellCard
            title={t.history.title}
            subtitle={t.history.subtitle}
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
            <div className="grid gap-3 md:grid-cols-[1.2fr_0.9fr_auto]">
              <DirectoryInput
                inputTestId="input-history-artifact-root"
                buttonTestId="button-select-history-root"
                value={historyRoot}
                onChange={setHistoryRoot}
                onPick={() => void handlePickDirectory('history')}
                buttonLabel={
                  pickingHistoryDirectory
                    ? t.actions.selectingDirectory
                    : t.actions.chooseDirectory
                }
                disabled={pickingHistoryDirectory}
                placeholder={DEFAULT_FORM.artifactRoot}
              />
              <select
                value={historyStatus}
                onChange={(event) =>
                  setHistoryStatus(event.target.value as 'all' | JobStatus)
                }
                className={inputClassName}
              >
                <option value="all">{t.historyStatuses.all}</option>
                <option value="running">{t.historyStatuses.running}</option>
                <option value="completed">{t.historyStatuses.completed}</option>
                <option value="failed">{t.historyStatuses.failed}</option>
                <option value="paused">{t.historyStatuses.paused}</option>
                <option value="pending">{t.historyStatuses.pending}</option>
                <option value="cancelled">{t.historyStatuses.cancelled}</option>
              </select>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  value={historyQuery}
                  onChange={(event) => setHistoryQuery(event.target.value)}
                  className={`${inputClassName} pl-9`}
                  placeholder={t.history.searchPlaceholder}
                />
              </div>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <MiniMetric label={t.history.total} value={String(historyMetrics.total)} />
              <MiniMetric
                label={t.history.completed}
                value={String(historyMetrics.completed)}
              />
              <MiniMetric
                label={t.history.failedPaused}
                value={String(historyMetrics.attention)}
              />
            </div>

            <div className="mt-5 space-y-3">
              {historyLoading ? (
                <LoadingState label={t.actions.refresh} compact />
              ) : historyError ? (
                <Banner message={historyError} />
              ) : visibleJobs.length === 0 ? (
                <EmptyState
                  title={t.history.noJobsTitle}
                  body={t.history.noJobsBody}
                  compact
                />
              ) : (
                visibleJobs.slice(0, 8).map((job) => {
                  const isActive = activeTarget?.jobId === job.id;
                  const historyStageLabel = translateStage(
                    language,
                    job.current_stage,
                    job.status
                  );
                  return (
                    <button
                      key={job.id}
                      data-testid={`history-job-${job.id}`}
                      type="button"
                      onClick={() => handleSelectJob(job.id, job.artifact_root)}
                      className={`w-full rounded-[24px] border px-4 py-4 text-left transition ${
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
                        <span>{historyStageLabel ?? translateStatus(language, job.status)}</span>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </ShellCard>

          <ShellCard
            title={t.pipeline.title}
            subtitle={t.pipeline.subtitle}
            icon={<Clock3 className="h-5 w-5 text-gray-400" />}
          >
            {recentStageRuns.length === 0 ? (
              <EmptyState
                title={t.empty.noPipelineTitle}
                body={t.empty.noPipelineBody}
                compact
              />
            ) : (
              <div className="space-y-3">
                {recentStageRuns.map((run) => (
                  <div
                    key={run.id}
                    className="rounded-[24px] border border-gray-200 bg-white px-4 py-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <StatusPill
                            status={run.status}
                            label={translateStatus(language, run.status)}
                          />
                          <span className="text-sm font-medium text-gray-900">
                            {translateStage(language, run.stage_name) ?? run.stage_name}
                          </span>
                        </div>
                        <div className="mt-2 text-xs text-gray-500">
                          {t.pipeline.stageAttempts} {run.attempt} ·{' '}
                          {formatDuration(run.duration_ms, t.common.notAvailable)}
                        </div>
                      </div>
                      <span className="text-xs text-gray-400">
                        {run.finished_at
                          ? formatDateTimeForLanguage(run.finished_at, language)
                          : t.pipeline.inProgress}
                      </span>
                    </div>
                    {run.error_message ? (
                      <p className="mt-3 text-sm text-red-600">{run.error_message}</p>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </ShellCard>
        </section>
      </main>
    </div>
  );
}

function ShellCard({
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
    <section className="rounded-[30px] border border-black/5 bg-white p-6 shadow-[0_28px_90px_-56px_rgba(0,0,0,0.35)]">
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
    <div className="rounded-[24px] border border-black/5 bg-white/85 px-5 py-4 shadow-[0_18px_70px_-50px_rgba(0,0,0,0.4)]">
      <div className="mb-3 flex items-center gap-2 text-sm font-medium text-gray-800">
        {icon}
        {title}
      </div>
      <p className="text-sm leading-6 text-gray-500">{body}</p>
    </div>
  );
}

function ModePill({
  active,
  onClick,
  label,
  testId,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  testId: string;
}) {
  return (
    <button
      data-testid={testId}
      type="button"
      onClick={onClick}
      className={`rounded-full px-4 py-2.5 text-sm font-medium transition ${
        active
          ? 'bg-black text-white shadow-[0_20px_40px_-20px_rgba(0,0,0,0.55)]'
          : 'border border-gray-200 bg-white text-gray-600 hover:border-gray-300 hover:text-gray-900'
      }`}
    >
      {label}
    </button>
  );
}

function UploadDropzone({
  title,
  helper,
  file,
  uploadedAsset,
  progress,
  isDragging,
  onDragOver,
  onDragLeave,
  onDrop,
  onChange,
  onClear,
  buttonLabel,
  testId,
}: {
  title: string;
  helper: string;
  file: File | null;
  uploadedAsset: UploadedInputAsset | null;
  progress: number;
  isDragging: boolean;
  onDragOver: (event: DragEvent<HTMLDivElement>) => void;
  onDragLeave: () => void;
  onDrop: (event: DragEvent<HTMLDivElement>) => void;
  onChange: (file: File | null) => void;
  onClear: () => void;
  buttonLabel: string;
  testId: string;
}) {
  return (
    <div
      className={`rounded-[28px] border-2 border-dashed p-5 transition ${
        isDragging ? 'border-black bg-gray-50' : 'border-gray-200 bg-white'
      }`}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="text-sm font-medium text-gray-900">{title}</div>
        {file ? (
          <button
            type="button"
            onClick={onClear}
            className="rounded-full border border-gray-200 p-2 text-gray-400 transition hover:border-gray-300 hover:text-gray-700"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        ) : null}
      </div>

      <div className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-gray-100 bg-gray-50">
          {file ? (
            <CheckCircle2 className="h-5 w-5 text-black" />
          ) : (
            <Upload className="h-5 w-5 text-gray-500" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-gray-900">
            {file ? file.name : helper}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            {file ? formatBytes(file.size) : ' '}
          </p>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-3">
        <label className="cursor-pointer rounded-full bg-black px-4 py-2 text-sm font-medium text-white transition hover:bg-gray-800">
          {buttonLabel}
          <input
            data-testid={testId}
            type="file"
            className="hidden"
            onChange={(event: ChangeEvent<HTMLInputElement>) =>
              onChange(event.target.files?.[0] ?? null)
            }
          />
        </label>
        {uploadedAsset ? (
          <span className="truncate text-xs text-gray-500">{uploadedAsset.path}</span>
        ) : null}
      </div>

      {progress > 0 ? (
        <div className="mt-4">
          <div className="mb-2 flex items-center justify-between text-xs text-gray-500">
            <span>{progress < 100 ? `${progress}%` : '100%'}</span>
            <span>{uploadedAsset ? 'ready' : 'uploading'}</span>
          </div>
          <div className="h-2 rounded-full bg-gray-100">
            <div
              className="h-2 rounded-full bg-black transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Field({
  label,
  icon,
  children,
}: {
  label: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="space-y-2">
      <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
        {icon}
        {label}
      </label>
      {children}
    </div>
  );
}

function DirectoryInput({
  value,
  onChange,
  onPick,
  buttonLabel,
  disabled,
  inputTestId,
  buttonTestId,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  onPick: () => void;
  buttonLabel: string;
  disabled: boolean;
  inputTestId: string;
  buttonTestId: string;
  placeholder?: string;
}) {
  return (
    <div className="flex gap-2">
      <input
        data-testid={inputTestId}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={`${inputClassName} min-w-0 flex-1`}
        placeholder={placeholder}
      />
      <button
        data-testid={buttonTestId}
        type="button"
        onClick={onPick}
        disabled={disabled}
        className={`shrink-0 rounded-full px-4 py-3 text-sm font-medium transition ${
          disabled
            ? 'cursor-wait border border-gray-200 bg-gray-100 text-gray-400'
            : 'border border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:text-gray-900'
        }`}
      >
        {disabled ? (
          <span className="flex items-center gap-2">
            <LoaderCircle className="h-4 w-4 animate-spin" />
            {buttonLabel}
          </span>
        ) : (
          buttonLabel
        )}
      </button>
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
      className={`rounded-[24px] border px-4 py-4 text-left transition ${
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

function InfoStrip({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm leading-6 text-gray-600">
      {children}
    </div>
  );
}

function ProgressLine({
  label,
  value,
  fallbackLabel,
}: {
  label: string;
  value: number;
  fallbackLabel: string;
}) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between gap-3 text-xs text-gray-500">
        <span>{label}</span>
        <span>{value > 0 ? `${value}%` : fallbackLabel}</span>
      </div>
      <div className="h-2 rounded-full bg-white">
        <div
          className="h-2 rounded-full bg-black transition-all"
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

function PreparedInputRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3">
      <div className="text-[11px] uppercase tracking-[0.18em] text-gray-400">{label}</div>
      <div className="mt-1 break-all text-sm text-gray-800">{value}</div>
    </div>
  );
}

function StageTile({
  stageView,
  language,
  waitingLabel,
  durationLabel,
  attemptsLabel,
  inProgressLabel,
  notAvailableLabel,
}: {
  stageView: StageView;
  language: UiLanguage;
  waitingLabel: string;
  durationLabel: string;
  attemptsLabel: string;
  inProgressLabel: string;
  notAvailableLabel: string;
}) {
  const styles = {
    pending: 'border-gray-200 bg-white text-gray-600',
    running: 'border-black bg-black text-white',
    completed: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    failed: 'border-red-200 bg-red-50 text-red-700',
  } as const;
  const cardClass = styles[stageView.status];

  return (
    <div
      data-testid={`pipeline-stage-${stageView.stage}`}
      className={`rounded-[24px] border px-4 py-4 ${cardClass}`}
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] opacity-60">
            {translateStage(language, stageView.stage) ?? stageView.stage}
          </div>
          <div className="mt-1 text-sm font-medium">
            {translateStatus(language, stageView.status)}
          </div>
        </div>
        <div className="text-right text-xs opacity-70">
          {stageView.status === 'running' ? inProgressLabel : waitingLabel}
        </div>
      </div>
      <div className="space-y-1 text-xs opacity-80">
        <div>
          {attemptsLabel}: {stageView.attempt ?? 0}
        </div>
        <div>
          {durationLabel}: {formatDuration(stageView.durationMs, notAvailableLabel)}
        </div>
      </div>
      {stageView.errorMessage ? (
        <p className="mt-3 text-xs leading-5">{stageView.errorMessage}</p>
      ) : null}
    </div>
  );
}

function Banner({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      <div className="flex items-start gap-2">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
        <span>{message}</span>
      </div>
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
      className={`rounded-[24px] border border-dashed border-gray-200 text-gray-500 ${
        compact ? 'px-4 py-5' : 'px-5 py-6'
      }`}
    >
      <div className="font-medium text-gray-700">{title}</div>
      <p className="mt-1 text-sm leading-6">{body}</p>
    </div>
  );
}

function LoadingState({ label, compact = false }: { label: string; compact?: boolean }) {
  return (
    <div
      className={`flex items-center gap-3 rounded-[24px] border border-dashed border-gray-200 text-gray-500 ${
        compact ? 'px-4 py-4 text-sm' : 'px-5 py-5 text-sm'
      }`}
    >
      <LoaderCircle className="h-4 w-4 animate-spin" />
      {label}
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
        cancelled: 'bg-white/15 text-white',
      }
    : {
        running: 'bg-amber-50 text-amber-700',
        completed: 'bg-emerald-50 text-emerald-700',
        failed: 'bg-red-50 text-red-700',
        paused: 'bg-yellow-50 text-yellow-700',
        pending: 'bg-gray-100 text-gray-600',
        cancelled: 'bg-gray-100 text-gray-600',
      };

  const className = styles[status as keyof typeof styles] ?? styles.pending;

  return (
    <span
      className={`rounded-full px-2.5 py-1 text-[11px] font-medium tracking-[0.14em] ${className}`}
    >
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
    <div className="rounded-2xl border border-gray-200 bg-white px-4 py-3">
      <div className="text-[11px] uppercase tracking-[0.2em] text-gray-400">{label}</div>
      <div className={`mt-1 text-sm text-gray-800 ${mono ? 'break-all font-mono' : ''}`}>
        {value}
      </div>
    </div>
  );
}

function InsightMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3">
      <div className="text-[11px] uppercase tracking-[0.18em] text-gray-400">{label}</div>
      <div className="mt-1 text-sm text-gray-800">{value}</div>
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
    <div className="rounded-[24px] border border-gray-200 bg-white px-4 py-4">
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
    completed: items.filter((item) => item.status === 'completed').length,
    attention: items.filter((item) =>
      item.status === 'failed' || item.status === 'paused'
    ).length,
  };
}

function buildStageViews(job: ActiveJobBundle['job'] | null, runs: StageRun[]): StageView[] {
  const latestByStage = new Map<string, StageRun>();
  for (const run of runs) {
    latestByStage.set(run.stage_name, run);
  }

  return STAGE_SEQUENCE.map((stage) => {
    const latest = latestByStage.get(stage);
    let status: StageView['status'] = 'pending';

    if (latest?.status === 'completed') {
      status = 'completed';
    }
    if (job?.current_stage === stage && job.status === 'running') {
      status = 'running';
    }
    if (latest?.status === 'failed' || (job?.status === 'failed' && job.current_stage === stage)) {
      status = 'failed';
    }

    return {
      stage,
      status,
      durationMs: latest?.duration_ms ?? null,
      attempt: latest?.attempt ?? null,
      errorMessage: latest?.error_message ?? null,
    };
  });
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
