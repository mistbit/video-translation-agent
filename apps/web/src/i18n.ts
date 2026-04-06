import type { JobStatus } from './types';

export type UiLanguage = 'en' | 'zh';
export type SubmissionMode = 'upload' | 'path';

type Copy = {
  shell: {
    console: string;
    agent: string;
    interfaceLabel: string;
    workspaceLabel: string;
    menuLabel: string;
  };
  navigation: {
    create: string;
    createHint: string;
    pipeline: string;
    pipelineHint: string;
    history: string;
    historyHint: string;
    activity: string;
    activityHint: string;
  };
  pageHeaders: {
    createTitle: string;
    createSubtitle: string;
    pipelineTitle: string;
    pipelineSubtitle: string;
    historyTitle: string;
    historySubtitle: string;
    activityTitle: string;
    activitySubtitle: string;
  };
  sidebar: {
    workspaceBody: string;
    metricsLabel: string;
    menuLabel: string;
    activeJobLabel: string;
    activeJobTitle: string;
    activeJobIdle: string;
    activeJobBody: string;
    noActiveJob: string;
    jobIdLabel: string;
    inputLabel: string;
    artifactRoot: string;
  };
  metrics: {
    jobs: string;
    running: string;
    attention: string;
  };
  composer: {
    title: string;
    subtitle: string;
    uploadMode: string;
    pathMode: string;
    artifactRoot: string;
    sourceLanguage: string;
    targetLanguage: string;
    asrModel: string;
    voiceProfile: string;
    mixMode: string;
    uploadProgress: string;
    selectedAssets: string;
  };
  upload: {
    videoTitle: string;
    subtitleTitle: string;
    optional: string;
    browse: string;
    emptyVideo: string;
    emptySubtitle: string;
    helper: string;
    replace: string;
    clear: string;
    uploaded: string;
  };
  paths: {
    videoPath: string;
    subtitlePath: string;
    helper: string;
    videoPlaceholder: string;
    subtitlePlaceholder: string;
  };
  settings: {
    preferFfmpegTitle: string;
    preferFfmpegBody: string;
    allowFallbackTitle: string;
    allowFallbackBody: string;
    renderWarning: string;
    asrHint: string;
    asrHintMedium: string;
    sidecarHint: string;
  };
  actions: {
    startProcessing: string;
    uploading: string;
    queueing: string;
    refresh: string;
    selectFromHistory: string;
    chooseDirectory: string;
    selectingDirectory: string;
  };
  pipeline: {
    title: string;
    subtitle: string;
    overallProgress: string;
    currentStage: string;
    pipelineHealth: string;
    stageAttempts: string;
    duration: string;
    waiting: string;
    inProgress: string;
    failedMessage: string;
    createdFrom: string;
    artifactRoot: string;
  };
  insights: {
    title: string;
    subtitle: string;
    qaSummary: string;
    segmentsChecked: string;
    overrunRatio: string;
    blockingReasons: string;
    noQa: string;
    artifacts: string;
    logs: string;
    stageRuns: string;
    segmentReruns: string;
    noArtifacts: string;
  };
  activity: {
    title: string;
    subtitle: string;
  };
  history: {
    title: string;
    subtitle: string;
    allStatuses: string;
    searchPlaceholder: string;
    total: string;
    completed: string;
    failedPaused: string;
    noJobsTitle: string;
    noJobsBody: string;
  };
  empty: {
    noActiveTitle: string;
    noActiveBody: string;
    noPipelineTitle: string;
    noPipelineBody: string;
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
  historyStatuses: {
    all: string;
    running: string;
    completed: string;
    failed: string;
    paused: string;
    pending: string;
    cancelled: string;
  };
  common: {
    none: string;
    notAvailable: string;
    unknownStage: string;
    idle: string;
    uploadPending: string;
  };
  statusLabels: Record<JobStatus, string>;
  stageLabels: Record<string, string>;
  errors: {
    videoRequired: string;
    uploadVideoRequired: string;
    loadHistoryFailed: string;
    createJobFailed: string;
    loadJobFailed: string;
    uploadFailed: string;
    directorySelectionFailed: string;
  };
};

export const uiCopy: Record<UiLanguage, Copy> = {
  en: {
    shell: {
      console: 'Operator Console',
      agent: 'VTL Agent',
      interfaceLabel: 'Interface',
      workspaceLabel: 'Workspace',
      menuLabel: 'Navigate',
    },
    navigation: {
      create: 'Create Job',
      createHint: 'Upload inputs, tune settings, and queue a fresh run.',
      pipeline: 'Pipeline',
      pipelineHint: 'Follow the selected job through every stage.',
      history: 'History',
      historyHint: 'Browse prior runs under the active artifact root.',
      activity: 'Activity',
      activityHint: 'Inspect recent stage attempts and downstream output.',
    },
    pageHeaders: {
      createTitle: 'Create and Queue',
      createSubtitle: 'Prepare inputs, choose models, and launch a new background job.',
      pipelineTitle: 'Pipeline Monitor',
      pipelineSubtitle: 'Track the selected job stage by stage and inspect failure context.',
      historyTitle: 'Run History',
      historySubtitle: 'Browse recent jobs under the active artifact root and reopen any run.',
      activityTitle: 'Run Activity',
      activitySubtitle: 'Review recent stage attempts, QA snapshots, and output artifacts.',
    },
    sidebar: {
      workspaceBody:
        'Run local dubbing jobs from one place, with uploads, monitoring, and history stitched into a single operator workflow.',
      metricsLabel: 'Live metrics',
      menuLabel: 'Menu',
      activeJobLabel: 'Pinned run',
      activeJobTitle: 'Active job',
      activeJobIdle: 'No job selected',
      activeJobBody: 'Choose a run from history or queue a new one to keep its status pinned here.',
      noActiveJob: 'Queue a run or reopen one from history to pin it here.',
      jobIdLabel: 'Job ID',
      inputLabel: 'Input video',
      artifactRoot: 'Artifact root',
    },
    metrics: {
      jobs: 'Jobs',
      running: 'Running',
      attention: 'Attention',
    },
    composer: {
      title: 'Job Composer',
      subtitle: 'Choose an input mode, attach media, and queue a job for background execution.',
      uploadMode: 'Upload files',
      pathMode: 'Local paths',
      artifactRoot: 'Artifact Root',
      sourceLanguage: 'Source Language',
      targetLanguage: 'Target Language',
      asrModel: 'ASR Model',
      voiceProfile: 'Voice Profile',
      mixMode: 'Mix Mode',
      uploadProgress: 'Upload Progress',
      selectedAssets: 'Prepared Inputs',
    },
    upload: {
      videoTitle: 'Video file',
      subtitleTitle: 'Subtitle file',
      optional: 'Optional',
      browse: 'Browse',
      emptyVideo: 'Drop a video here or browse from disk.',
      emptySubtitle: 'Drop a sidecar subtitle here if you already have one.',
      helper: 'Uploads are stored under the selected artifact root and then used as server-side job inputs.',
      replace: 'Replace',
      clear: 'Clear',
      uploaded: 'Uploaded',
    },
    paths: {
      videoPath: 'Input Video Path',
      subtitlePath: 'Subtitle Path',
      helper: 'Path mode still works for operators who run the API and frontend on the same machine.',
      videoPlaceholder: '/Users/you/Videos/source.mp4',
      subtitlePlaceholder: '/Users/you/Videos/source.srt',
    },
    settings: {
      preferFfmpegTitle: 'Prefer ffmpeg',
      preferFfmpegBody: 'Use ffmpeg for the final render when it is available.',
      allowFallbackTitle: 'Allow render fallback',
      allowFallbackBody: 'Keep the job moving if ffmpeg render is unavailable or fails.',
      renderWarning: 'This combination disables every render path. Enable ffmpeg or allow fallback before submitting.',
      asrHint: 'Chinese ASR: use medium when recognition quality matters more than latency.',
      asrHintMedium: 'Tuned decoding is applied automatically in this mode.',
      sidecarHint: 'A subtitle sidecar is present, so the caption stage will ingest subtitles instead of exercising ASR.',
    },
    actions: {
      startProcessing: 'Queue Job',
      uploading: 'Uploading files',
      queueing: 'Queueing job',
      refresh: 'Refresh',
      selectFromHistory: 'Select from history',
      chooseDirectory: 'Choose directory',
      selectingDirectory: 'Opening picker',
    },
    pipeline: {
      title: 'Live Pipeline',
      subtitle: 'Background execution updates this rail as each stage finishes.',
      overallProgress: 'Overall progress',
      currentStage: 'Current stage',
      pipelineHealth: 'Pipeline health',
      stageAttempts: 'Attempts',
      duration: 'Duration',
      waiting: 'Waiting',
      inProgress: 'In progress',
      failedMessage: 'Failure reason',
      createdFrom: 'Input source',
      artifactRoot: 'Artifact root',
    },
    insights: {
      title: 'Run Insights',
      subtitle: 'Recent artifacts, QA summary, and log counts for the selected job.',
      qaSummary: 'QA Summary',
      segmentsChecked: 'Segments checked',
      overrunRatio: 'Overrun ratio',
      blockingReasons: 'Blocking reasons',
      noQa: 'QA data will appear after the job reaches the QA stage.',
      artifacts: 'Artifacts',
      logs: 'Logs',
      stageRuns: 'Stage runs',
      segmentReruns: 'Segment reruns',
      noArtifacts: 'Artifacts will appear as stages persist outputs.',
    },
    activity: {
      title: 'Recent Activity',
      subtitle: 'A reverse-chronological feed of stage attempts for the selected job.',
    },
    history: {
      title: 'History',
      subtitle: 'Recent jobs under the current artifact root.',
      allStatuses: 'All statuses',
      searchPlaceholder: 'Search jobs',
      total: 'Total',
      completed: 'Completed',
      failedPaused: 'Failed/Paused',
      noJobsTitle: 'No jobs found',
      noJobsBody: 'Change the artifact root, clear the filters, or queue a new run.',
    },
    empty: {
      noActiveTitle: 'No active job',
      noActiveBody: 'Queue a run or select one from history to inspect its pipeline.',
      noPipelineTitle: 'Pipeline will appear here',
      noPipelineBody: 'As soon as a job is queued, the stage rail, QA summary, and artifacts will begin updating.',
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
      duck: 'Duck (lower background audio)',
      replace: 'Replace (mute original audio)',
    },
    historyStatuses: {
      all: 'All statuses',
      running: 'Running',
      completed: 'Completed',
      failed: 'Failed',
      paused: 'Paused',
      pending: 'Pending',
      cancelled: 'Cancelled',
    },
    common: {
      none: 'none',
      notAvailable: 'n/a',
      unknownStage: 'Unknown stage',
      idle: 'Idle',
      uploadPending: 'Not uploaded yet',
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
      uploadVideoRequired: 'Select a video file before queueing an upload-based job.',
      loadHistoryFailed: 'Failed to load job history.',
      createJobFailed: 'Failed to create job.',
      loadJobFailed: 'Failed to load job details.',
      uploadFailed: 'Failed to upload input file.',
      directorySelectionFailed: 'Failed to open the directory picker.',
    },
  },
  zh: {
    shell: {
      console: '操作控制台',
      agent: 'VTL Agent',
      interfaceLabel: '界面语言',
      workspaceLabel: '工作区',
      menuLabel: '菜单',
    },
    navigation: {
      create: '创建任务',
      createHint: '上传素材、调整参数，然后发起新的后台任务。',
      pipeline: '流水线',
      pipelineHint: '跟踪当前选中任务经过每一个阶段的状态。',
      history: '历史记录',
      historyHint: '浏览当前产物根目录下的历史任务。',
      activity: '运行活动',
      activityHint: '查看最近阶段尝试、QA 结果和下游产物。',
    },
    pageHeaders: {
      createTitle: '创建并提交任务',
      createSubtitle: '准备输入、选择模型参数，并把任务送入后台执行。',
      pipelineTitle: '流水线监控',
      pipelineSubtitle: '按阶段追踪当前任务，并快速定位失败上下文。',
      historyTitle: '任务历史',
      historySubtitle: '查看当前产物根目录下的最近任务，并重新打开任意一次运行。',
      activityTitle: '运行活动',
      activitySubtitle: '检查最近的阶段尝试、QA 摘要和产物输出。',
    },
    sidebar: {
      workspaceBody:
        '把上传、任务创建、监控和历史记录整合到一个本地操作台里，减少来回切换。',
      metricsLabel: '实时指标',
      menuLabel: '菜单',
      activeJobLabel: '固定任务',
      activeJobTitle: '当前任务',
      activeJobIdle: '尚未选择任务',
      activeJobBody: '可以从历史记录里选一个任务，或者直接提交新的运行，让状态固定显示在侧边栏。',
      noActiveJob: '提交一个新任务，或者从历史记录里重新打开一个任务并固定在这里。',
      jobIdLabel: '任务 ID',
      inputLabel: '输入视频',
      artifactRoot: '产物根目录',
    },
    metrics: {
      jobs: '任务数',
      running: '运行中',
      attention: '需关注',
    },
    composer: {
      title: '任务创建器',
      subtitle: '先选择输入方式，再附加媒体文件并把任务提交到后台执行。',
      uploadMode: '上传文件',
      pathMode: '本地路径',
      artifactRoot: '产物根目录',
      sourceLanguage: '源语言',
      targetLanguage: '目标语言',
      asrModel: 'ASR 模型',
      voiceProfile: '音色配置',
      mixMode: '混音模式',
      uploadProgress: '上传进度',
      selectedAssets: '已准备输入',
    },
    upload: {
      videoTitle: '视频文件',
      subtitleTitle: '字幕文件',
      optional: '可选',
      browse: '选择文件',
      emptyVideo: '把视频拖到这里，或者从磁盘中选择。',
      emptySubtitle: '如果已经有人审过字幕，可以把外挂字幕一起上传。',
      helper: '上传后的文件会保存在当前 artifact root 下，再作为服务端任务输入使用。',
      replace: '替换',
      clear: '清除',
      uploaded: '已上传',
    },
    paths: {
      videoPath: '输入视频路径',
      subtitlePath: '字幕路径',
      helper: '如果前端和 API 跑在同一台机器上，也可以继续直接填写本地路径。',
      videoPlaceholder: '/Users/you/Videos/source.mp4',
      subtitlePlaceholder: '/Users/you/Videos/source.srt',
    },
    settings: {
      preferFfmpegTitle: '优先使用 ffmpeg',
      preferFfmpegBody: '如果环境里可用，优先用 ffmpeg 完成最终渲染。',
      allowFallbackTitle: '允许渲染回退',
      allowFallbackBody: 'ffmpeg 不可用或失败时，允许回退到其他本地渲染路径。',
      renderWarning: '这组配置会把所有渲染路径都关掉。提交前请启用 ffmpeg 或允许 fallback。',
      asrHint: '中文 ASR：当识别率比处理速度更重要时，建议切到 medium。',
      asrHintMedium: '当前模式会自动启用调优后的解码参数。',
      sidecarHint: '当前已提供外挂字幕，因此 caption 阶段会直接导入字幕，而不是实际跑 ASR。',
    },
    actions: {
      startProcessing: '提交任务',
      uploading: '正在上传文件',
      queueing: '正在排队创建任务',
      refresh: '刷新',
      selectFromHistory: '从历史中选择',
      chooseDirectory: '选择目录',
      selectingDirectory: '正在打开选择器',
    },
    pipeline: {
      title: '实时流水线',
      subtitle: '后台任务执行时，阶段轨道会随着每个阶段完成而更新。',
      overallProgress: '整体进度',
      currentStage: '当前阶段',
      pipelineHealth: '流水线状态',
      stageAttempts: '尝试次数',
      duration: '耗时',
      waiting: '等待中',
      inProgress: '执行中',
      failedMessage: '失败原因',
      createdFrom: '输入来源',
      artifactRoot: '产物根目录',
    },
    insights: {
      title: '任务观察',
      subtitle: '查看所选任务最近的产物、QA 摘要和日志统计。',
      qaSummary: 'QA 摘要',
      segmentsChecked: '检查片段数',
      overrunRatio: '超时比例',
      blockingReasons: '阻塞原因',
      noQa: '任务运行到 QA 阶段后，这里会显示对应结果。',
      artifacts: '产物数',
      logs: '日志数',
      stageRuns: '阶段运行数',
      segmentReruns: '片段重跑数',
      noArtifacts: '每个阶段落盘后，对应产物会出现在这里。',
    },
    activity: {
      title: '最近活动',
      subtitle: '按时间倒序查看所选任务最近的阶段尝试记录。',
    },
    history: {
      title: '历史记录',
      subtitle: '查看当前 artifact root 下最近的任务。',
      allStatuses: '全部状态',
      searchPlaceholder: '搜索任务',
      total: '总数',
      completed: '已完成',
      failedPaused: '失败/暂停',
      noJobsTitle: '没有找到任务',
      noJobsBody: '可以切换 artifact root、清空筛选条件，或者新建一次运行。',
    },
    empty: {
      noActiveTitle: '还没有活动任务',
      noActiveBody: '提交一个任务，或者从历史记录里选择任务查看流水线。',
      noPipelineTitle: '流水线会显示在这里',
      noPipelineBody: '任务一旦进入后台执行，阶段轨道、QA 摘要和产物列表就会开始更新。',
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
    historyStatuses: {
      all: '全部状态',
      running: '运行中',
      completed: '已完成',
      failed: '失败',
      paused: '已暂停',
      pending: '等待中',
      cancelled: '已取消',
    },
    common: {
      none: '无',
      notAvailable: '暂无',
      unknownStage: '未知阶段',
      idle: '空闲',
      uploadPending: '尚未上传',
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
      uploadVideoRequired: '上传模式下必须先选择视频文件。',
      loadHistoryFailed: '加载历史任务失败。',
      createJobFailed: '创建任务失败。',
      loadJobFailed: '加载任务详情失败。',
      uploadFailed: '上传输入文件失败。',
      directorySelectionFailed: '打开目录选择器失败。',
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
