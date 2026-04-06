import type { JobStatus } from './types';

export type UiLanguage = 'en' | 'zh';

type Copy = {
  shell: {
    console: string;
    agent: string;
    interfaceLabel: string;
  };
  metrics: {
    jobs: string;
    running: string;
    paused: string;
    total: string;
    completed: string;
    failedPaused: string;
  };
  hero: {
    pathBasedJobsTitle: string;
    pathBasedJobsBody: string;
    asrModesTitle: string;
    asrModesBody: string;
    feedbackTitle: string;
    feedbackBody: string;
  };
  cards: {
    newJobTitle: string;
    newJobSubtitle: string;
    activeRunTitle: string;
    activeRunSubtitle: string;
    historyTitle: string;
    historySubtitle: string;
    stageTimelineTitle: string;
    stageTimelineSubtitle: string;
    artifactsTitle: string;
    artifactsSubtitle: string;
  };
  upload: {
    title: string;
    body: string;
    button: string;
    sameMachine: string;
  };
  fields: {
    inputVideoPath: string;
    subtitlePath: string;
    artifactRoot: string;
    sourceLanguage: string;
    targetLanguage: string;
    asrModel: string;
    voiceProfile: string;
    mixMode: string;
    optional: string;
  };
  placeholders: {
    videoPath: string;
    subtitlePath: string;
    artifactRoot: string;
    searchJobs: string;
  };
  languageNames: {
    zh: string;
    en: string;
    ja: string;
  };
  asrOptions: {
    small: string;
    medium: string;
  };
  voiceProfiles: {
    enFemaleNeutral01: string;
    enMaleNeutral01: string;
  };
  mixModes: {
    duck: string;
    replace: string;
  };
  toggles: {
    preferFfmpegTitle: string;
    preferFfmpegBody: string;
    allowFallbackTitle: string;
    allowFallbackBody: string;
  };
  hints: {
    asrBase: string;
    asrMediumActive: string;
    asrSubtitleOverride: string;
  };
  actions: {
    startProcessing: string;
    startingJob: string;
    refresh: string;
    refreshHistory: string;
  };
  empty: {
    noJobSelectedTitle: string;
    noJobSelectedBody: string;
    noJobDataTitle: string;
    noJobDataBody: string;
    noJobsFoundTitle: string;
    noJobsFoundBody: string;
    noStageRunsTitle: string;
    noStageRunsBody: string;
    noArtifactsTitle: string;
    noArtifactsBody: string;
  };
  loading: {
    jobDetails: string;
    history: string;
  };
  activeRun: {
    artifactRoot: string;
    asrModel: string;
    sourceLanguage: string;
    targetLanguage: string;
    qaSummary: string;
    segmentsChecked: string;
    overrunRatio: string;
    blockingReasons: string;
    qaPending: string;
  };
  history: {
    allStatuses: string;
    completed: string;
    failed: string;
    paused: string;
    pending: string;
    running: string;
    cancelled: string;
  };
  timeline: {
    attempt: string;
    inProgress: string;
  };
  artifacts: {
    recentArtifacts: string;
    logSnapshot: string;
    stageRuns: string;
    logFiles: string;
    segmentReruns: string;
    qaFlagCounts: string;
    qaSummaryPending: string;
    noQaFlags: string;
  };
  common: {
    none: string;
    notAvailable: string;
    unknownStage: string;
    done: string;
    idle: string;
  };
  statusLabels: Record<JobStatus, string>;
  stageLabels: Record<string, string>;
  errors: {
    videoRequired: string;
    loadHistoryFailed: string;
    createJobFailed: string;
    loadJobFailed: string;
  };
};

export const uiCopy: Record<UiLanguage, Copy> = {
  en: {
    shell: {
      console: 'Local Console',
      agent: 'VTL Agent',
      interfaceLabel: 'Interface',
    },
    metrics: {
      jobs: 'Jobs',
      running: 'Running',
      paused: 'Paused',
      total: 'Total',
      completed: 'Completed',
      failedPaused: 'Failed/Paused',
    },
    hero: {
      pathBasedJobsTitle: 'Path-Based Jobs',
      pathBasedJobsBody:
        'This frontend mirrors the real backend contract: jobs are created from local filesystem paths on the same machine.',
      asrModesTitle: 'Chinese ASR Modes',
      asrModesBody:
        'Use `small` for balanced local runs or `medium` for higher-accuracy subtitle extraction with tuned decoding.',
      feedbackTitle: 'Operational Feedback',
      feedbackBody:
        'Track stages, QA blocking reasons, artifacts, and recent runs without dropping back to the terminal.',
    },
    cards: {
      newJobTitle: 'New Job',
      newJobSubtitle:
        'Create a real processing job using local file paths and backend-backed settings.',
      activeRunTitle: 'Active Run',
      activeRunSubtitle: 'Live job summary with polling against the current backend API.',
      historyTitle: 'History',
      historySubtitle: 'Recent jobs under the selected artifact root.',
      stageTimelineTitle: 'Stage Timeline',
      stageTimelineSubtitle: 'Latest known stage runs from the selected job.',
      artifactsTitle: 'Artifacts and QA',
      artifactsSubtitle: 'Key outputs, logs, and QA report paths for the selected run.',
    },
    upload: {
      title: 'Reference a local file',
      body:
        'Browser file pickers do not expose a usable absolute path. Use this as a visual check, then paste the actual local path into the form.',
      button: 'Pick Reference File',
      sameMachine:
        'Run this web app on the same machine as the FastAPI service. The API starts jobs from local paths, not uploaded browser blobs.',
    },
    fields: {
      inputVideoPath: 'Input Video Path',
      subtitlePath: 'Subtitle Path',
      artifactRoot: 'Artifact Root',
      sourceLanguage: 'Source Language',
      targetLanguage: 'Target Language',
      asrModel: 'ASR Model',
      voiceProfile: 'Voice Profile',
      mixMode: 'Mix Mode',
      optional: 'Optional',
    },
    placeholders: {
      videoPath: '/Users/you/Videos/source.mp4',
      subtitlePath: '/Users/you/Videos/source.srt',
      artifactRoot: './.artifacts/web-runs',
      searchJobs: 'Search jobs',
    },
    languageNames: {
      zh: 'Chinese',
      en: 'English',
      ja: 'Japanese',
    },
    asrOptions: {
      small: 'Small - Balanced default',
      medium: 'Medium - Higher accuracy',
    },
    voiceProfiles: {
      enFemaleNeutral01: 'English Female Neutral',
      enMaleNeutral01: 'English Male Neutral',
    },
    mixModes: {
      duck: 'Duck (Lower background audio)',
      replace: 'Replace (Mute original audio)',
    },
    toggles: {
      preferFfmpegTitle: 'Prefer ffmpeg',
      preferFfmpegBody: 'Use ffmpeg when available for final render.',
      allowFallbackTitle: 'Allow render fallback',
      allowFallbackBody: 'Keep jobs moving if ffmpeg render fails.',
    },
    hints: {
      asrBase:
        'Chinese ASR: switch to medium when extraction quality matters more than latency.',
      asrMediumActive: 'Tuned decoding is applied automatically in this mode.',
      asrSubtitleOverride:
        'A sidecar subtitle path is provided, so this run will ingest subtitles instead of exercising ASR extraction.',
    },
    actions: {
      startProcessing: 'Start Processing',
      startingJob: 'Starting job',
      refresh: 'Refresh',
      refreshHistory: 'Refresh history',
    },
    empty: {
      noJobSelectedTitle: 'No job selected',
      noJobSelectedBody:
        'Create a new job or pick one from history to inspect stages, artifacts, and QA.',
      noJobDataTitle: 'No job data',
      noJobDataBody: 'Select a job from history or create a new one to start polling.',
      noJobsFoundTitle: 'No jobs found',
      noJobsFoundBody:
        'Change the artifact root, clear filters, or create a new run from the panel above.',
      noStageRunsTitle: 'No stage runs yet',
      noStageRunsBody: 'Once a job starts, stage attempts and timings will appear here.',
      noArtifactsTitle: 'No artifacts yet',
      noArtifactsBody: 'Artifacts appear as each stage persists outputs.',
    },
    loading: {
      jobDetails: 'Loading job details',
      history: 'Loading history',
    },
    activeRun: {
      artifactRoot: 'Artifact root',
      asrModel: 'ASR model',
      sourceLanguage: 'Source language',
      targetLanguage: 'Target language',
      qaSummary: 'QA Summary',
      segmentsChecked: 'Segments checked',
      overrunRatio: 'Overrun ratio',
      blockingReasons: 'Blocking reasons',
      qaPending: 'QA report not available yet. It will appear after the pipeline reaches the QA stage.',
    },
    history: {
      allStatuses: 'All statuses',
      completed: 'Completed',
      failed: 'Failed',
      paused: 'Paused',
      pending: 'Pending',
      running: 'Running',
      cancelled: 'Cancelled',
    },
    timeline: {
      attempt: 'Attempt',
      inProgress: 'in progress',
    },
    artifacts: {
      recentArtifacts: 'Recent Artifacts',
      logSnapshot: 'Log Snapshot',
      stageRuns: 'Stage runs',
      logFiles: 'Log files',
      segmentReruns: 'Segment reruns',
      qaFlagCounts: 'QA Flag Counts',
      qaSummaryPending: 'QA summary will appear after the pipeline reaches the QA stage.',
      noQaFlags: 'No QA flags recorded.',
    },
    common: {
      none: 'none',
      notAvailable: 'n/a',
      unknownStage: 'unknown stage',
      done: 'done',
      idle: 'idle',
    },
    statusLabels: {
      pending: 'Pending',
      running: 'Running',
      paused: 'Paused',
      completed: 'Completed',
      failed: 'Failed',
      cancelled: 'Cancelled',
    },
    stageLabels: {
      ingest: 'Ingest',
      caption: 'Caption',
      normalize: 'Normalize',
      translate: 'Translate',
      tts: 'TTS',
      render: 'Render',
      qa: 'QA',
    },
    errors: {
      videoRequired: 'Input video path is required.',
      loadHistoryFailed: 'Failed to load job history.',
      createJobFailed: 'Failed to create job.',
      loadJobFailed: 'Failed to load job details.',
    },
  },
  zh: {
    shell: {
      console: '本地控制台',
      agent: 'VTL Agent',
      interfaceLabel: '界面语言',
    },
    metrics: {
      jobs: '任务数',
      running: '运行中',
      paused: '已暂停',
      total: '总数',
      completed: '已完成',
      failedPaused: '失败/暂停',
    },
    hero: {
      pathBasedJobsTitle: '本地路径任务',
      pathBasedJobsBody: '前端已对齐真实后端契约：任务直接基于同机文件系统路径创建。',
      asrModesTitle: '中文 ASR 模式',
      asrModesBody: '日常本地运行用 `small`，更看重字幕识别率时切到 `medium`。',
      feedbackTitle: '运行反馈',
      feedbackBody: '无需回到终端，就能查看阶段状态、QA 阻塞原因、产物和近期任务。',
    },
    cards: {
      newJobTitle: '新建任务',
      newJobSubtitle: '使用本地文件路径和后端真实配置创建处理任务。',
      activeRunTitle: '当前任务',
      activeRunSubtitle: '基于当前后端 API 轮询显示任务实时摘要。',
      historyTitle: '历史记录',
      historySubtitle: '查看当前 artifact root 下的最近任务。',
      stageTimelineTitle: '阶段时间线',
      stageTimelineSubtitle: '展示所选任务最近一次已知阶段运行记录。',
      artifactsTitle: '产物与 QA',
      artifactsSubtitle: '查看所选任务的关键输出、日志和 QA 报告路径。',
    },
    upload: {
      title: '选择本地文件作参考',
      body: '浏览器文件选择器拿不到可用的绝对路径。这里仅作视觉确认，实际运行仍需把真实本地路径粘贴到表单里。',
      button: '选择参考文件',
      sameMachine: '请在与 FastAPI 服务同一台机器上使用本页面。API 接收的是本地路径，不是浏览器上传的文件流。',
    },
    fields: {
      inputVideoPath: '输入视频路径',
      subtitlePath: '字幕路径',
      artifactRoot: '产物根目录',
      sourceLanguage: '源语言',
      targetLanguage: '目标语言',
      asrModel: 'ASR 模型',
      voiceProfile: '音色配置',
      mixMode: '混音模式',
      optional: '可选',
    },
    placeholders: {
      videoPath: '/Users/you/Videos/source.mp4',
      subtitlePath: '/Users/you/Videos/source.srt',
      artifactRoot: './.artifacts/web-runs',
      searchJobs: '搜索任务',
    },
    languageNames: {
      zh: '中文',
      en: '英文',
      ja: '日文',
    },
    asrOptions: {
      small: 'Small - 默认均衡',
      medium: 'Medium - 更高识别率',
    },
    voiceProfiles: {
      enFemaleNeutral01: '英文女声中性',
      enMaleNeutral01: '英文男声中性',
    },
    mixModes: {
      duck: 'Duck（压低背景音）',
      replace: 'Replace（静音原音频）',
    },
    toggles: {
      preferFfmpegTitle: '优先使用 ffmpeg',
      preferFfmpegBody: '可用时使用 ffmpeg 完成最终渲染。',
      allowFallbackTitle: '允许渲染回退',
      allowFallbackBody: 'ffmpeg 渲染失败时允许回退，避免任务中断。',
    },
    hints: {
      asrBase: '中文 ASR：当字幕提取质量比处理速度更重要时，建议切到 medium。',
      asrMediumActive: '当前模式会自动启用调优后的解码参数。',
      asrSubtitleOverride: '当前已提供外挂字幕路径，这次任务会直接导入字幕，不会实际走 ASR 提取。',
    },
    actions: {
      startProcessing: '开始处理',
      startingJob: '正在创建任务',
      refresh: '刷新',
      refreshHistory: '刷新历史',
    },
    empty: {
      noJobSelectedTitle: '还没有选中任务',
      noJobSelectedBody: '先创建新任务，或从历史记录里选择一个任务查看阶段、产物和 QA。',
      noJobDataTitle: '没有任务数据',
      noJobDataBody: '请从历史记录中选择任务，或先创建一个新任务开始轮询。',
      noJobsFoundTitle: '没有找到任务',
      noJobsFoundBody: '可以切换 artifact root、清空筛选条件，或直接从上方创建新任务。',
      noStageRunsTitle: '还没有阶段运行记录',
      noStageRunsBody: '任务开始后，这里会显示各阶段的尝试次数和耗时。',
      noArtifactsTitle: '还没有产物',
      noArtifactsBody: '每个阶段落盘后，对应产物会出现在这里。',
    },
    loading: {
      jobDetails: '正在加载任务详情',
      history: '正在加载历史记录',
    },
    activeRun: {
      artifactRoot: '产物根目录',
      asrModel: 'ASR 模型',
      sourceLanguage: '源语言',
      targetLanguage: '目标语言',
      qaSummary: 'QA 摘要',
      segmentsChecked: '检查片段数',
      overrunRatio: '超时比例',
      blockingReasons: '阻塞原因',
      qaPending: 'QA 报告暂未生成，任务运行到 QA 阶段后会显示在这里。',
    },
    history: {
      allStatuses: '全部状态',
      completed: '已完成',
      failed: '失败',
      paused: '已暂停',
      pending: '等待中',
      running: '运行中',
      cancelled: '已取消',
    },
    timeline: {
      attempt: '尝试',
      inProgress: '进行中',
    },
    artifacts: {
      recentArtifacts: '最近产物',
      logSnapshot: '日志摘要',
      stageRuns: '阶段运行数',
      logFiles: '日志文件数',
      segmentReruns: '片段重跑数',
      qaFlagCounts: 'QA 标记统计',
      qaSummaryPending: '任务运行到 QA 阶段后，这里会显示 QA 摘要。',
      noQaFlags: '没有记录到 QA 标记。',
    },
    common: {
      none: '无',
      notAvailable: '暂无',
      unknownStage: '未知阶段',
      done: '已完成',
      idle: '空闲',
    },
    statusLabels: {
      pending: '等待中',
      running: '运行中',
      paused: '已暂停',
      completed: '已完成',
      failed: '失败',
      cancelled: '已取消',
    },
    stageLabels: {
      ingest: '导入',
      caption: '字幕提取',
      normalize: '标准化',
      translate: '翻译',
      tts: '语音合成',
      render: '渲染',
      qa: '质检',
    },
    errors: {
      videoRequired: '必须填写输入视频路径。',
      loadHistoryFailed: '加载历史任务失败。',
      createJobFailed: '创建任务失败。',
      loadJobFailed: '加载任务详情失败。',
    },
  },
};

export function getInitialUiLanguage(): UiLanguage {
  if (typeof window === 'undefined') {
    return 'en';
  }

  const saved = window.localStorage.getItem('vtl-ui-language');
  if (saved === 'en' || saved === 'zh') {
    return saved;
  }

  return window.navigator.language.toLowerCase().startsWith('zh') ? 'zh' : 'en';
}

export function persistUiLanguage(language: UiLanguage) {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem('vtl-ui-language', language);
  document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
}

export function translateStatus(language: UiLanguage, status: string) {
  return uiCopy[language].statusLabels[status as JobStatus] ?? status;
}

export function translateStage(
  language: UiLanguage,
  stage: string | null,
  status?: string
) {
  if (!stage) {
    if (status === 'completed') {
      return null;
    }
    return uiCopy[language].common.idle;
  }

  return uiCopy[language].stageLabels[stage] ?? stage;
}

export function formatDateTimeForLanguage(value: string, language: UiLanguage) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(language === 'zh' ? 'zh-CN' : 'en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}
