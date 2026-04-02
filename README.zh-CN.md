[English](./README.md) · **简体中文**

# video-translation-agent

这是一个本地优先的 Phase 1 MVP，用于视频翻译与配音。仓库同时提供 Typer CLI 和 FastAPI API，它们共用同一套进程内编排引擎。

这个项目现在已经可以用于本地实验和个人工作流，尤其适合**已有外挂字幕**的场景。但它依然**不是生产级翻译或配音系统**。

## 当前实现概览

- 流水线阶段：`ingest -> caption -> normalize -> translate -> tts -> render -> qa`
- 每个任务都会写入本地 artifact 工作区，包含 `job.json` 和追加式 JSONL 历史
- CLI 支持：`run`、`stage run`、`segment rerun`、`config init/show/validate`、`doctor`、`completion show/install`
- API 支持：健康检查、创建/列出/读取任务、读取 artifacts/logs/qa、阶段重跑、片段重跑
- `caption_strategy=auto` 时，**如果提供字幕 sidecar，会优先使用字幕**；否则退回到本地 ASR / 媒体翻译路径
- 对于**带中文字幕 sidecar** 的任务，系统优先使用**离线文本翻译**，而不是再从音频翻译；这更适合人工整理过的字幕
- 对于**没有字幕**的任务，系统会退回到**基于源视频的媒体翻译**
- TTS 有本地兜底实现；在 macOS 上可使用 **`say` + `afconvert`** 生成真正的语音音频
- Render 优先使用 `ffmpeg`；如果 `ffmpeg` 不可用或失败且允许 fallback，macOS 上可通过 **`swift` + `AVFoundation`** 生成**带配音音轨但不烧录字幕**的 MP4

## 现实预期 / 质量边界

已经比之前更好的地方：

- 基于中文字幕到英文的工作流明显比之前更实用
- macOS 原生 fallback 现在可以生成可听的英文语音和带配音音轨的 MP4
- 真实本地任务可以端到端跑通并保留完整 artifacts

但它仍然不是：

- 不是成熟的翻译系统
- 不是专业级配音系统
- 不是可放心无人值守跑生产媒体任务的系统

## 运行要求

- Python 3.11+
- 最好在 `PATH` 中提供 `ffprobe`，供 ingest / doctor 使用
- 在 macOS 上，媒体探测可以通过 `mdls` / `swift` 走原生 fallback
- 推荐安装 `ffmpeg`，但在允许 render fallback 时不是硬依赖
- 在 macOS 上，`say` + `afconvert` 可以明显提升 fallback TTS 效果
- 在 macOS 上，`swift` 可启用 AVFoundation 的视频复用 fallback

推荐安装方式：

```bash
python -m pip install -e '.[dev]'
```

验证测试：

```bash
python -m pytest
```

## 示例输入

文档示例文件位于 `examples/mvp/`：

- `examples/mvp/source.srt`
- `examples/mvp/source.mp4`（只是用于确定性测试的占位文件，**不是真实视频**）
- `examples/mvp/vtl.config.json`

说明：

- `tests/test_mvp_documented_flow.py` 用于校验 README 中的示例流程
- 真正本地运行时，请把 `examples/mvp/source.mp4` 换成真实媒体文件
- 运行生成的 job 输出不会提交到 `examples/mvp/`

## 流水线如何选择路径

### 1）字幕 / caption 输入

- 如果传入 `input_subtitle`，则字幕 sidecar 是事实来源
- 否则 `caption_strategy=auto` 会退回到基于音频的视频字幕提取路径

### 2）翻译

- 对于带中文字幕 sidecar 的任务，优先走离线文本翻译，而不是重新从音频翻译
- 对于没有字幕的任务，会退回到基于源视频的媒体翻译
- 当前翻译仍然是尽力而为；本地逻辑包含少量领域词覆盖/清洗，以及可选的离线 MT 行为

### 3）TTS

- 默认仍有确定性本地兜底实现
- 在 macOS 上，`say` + `afconvert` 可生成真正的人声 WAV，通常比早期占位音调明显更好

### 4）Render

- 首选路径：使用 `ffmpeg` 生成 `mix.wav` 和 `final_en.mp4`
- 如果失败且允许 fallback，在 macOS 上可通过 AVFoundation 仍然生成带配音音轨的 `final_en.mp4`
- **fallback 生成的 MP4 不会把字幕烧录进视频**
- 如果 AVFoundation 也不可用，则最后的本地 copy fallback 只能保住 artifacts 流程继续；此时 MP4 只是原视频副本

## CLI 用法

查看帮助：

```bash
python -m apps.cli.main --help
```

运行 doctor：

```bash
python -m apps.cli.main doctor --artifact-root ./.artifacts/mvp-jobs

# 把 ffmpeg 变成硬依赖
python -m apps.cli.main doctor \
  --artifact-root ./.artifacts/mvp-jobs \
  --no-allow-render-copy-fallback
```

使用文档示例 fixture 运行：

```bash
python -m apps.cli.main run \
  --config ./examples/mvp/vtl.config.json \
  --job-id 00000000-0000-0000-0000-000000000260 \
  --no-prefer-ffmpeg
```

使用真实视频 + 字幕 sidecar 运行：

```bash
python -m apps.cli.main run \
  --input-video ./我是不白痴.mp4 \
  --input-subtitle ./我是不白痴.srt \
  --source-lang zh \
  --target-lang en \
  --artifact-root ./.artifacts/wobubaichi-run-v5 \
  --no-prefer-ffmpeg
```

阶段重跑：

```bash
python -m apps.cli.main stage run translate \
  --job-id 00000000-0000-0000-0000-000000000260 \
  --artifact-root ./.artifacts/mvp-jobs \
  --no-prefer-ffmpeg
```

片段重跑：

```bash
python -m apps.cli.main segment rerun seg_0001 \
  --job-id 00000000-0000-0000-0000-000000000260 \
  --artifact-root ./.artifacts/mvp-jobs \
  --reason "manual fix" \
  --execute-stages \
  --no-prefer-ffmpeg
```

配置辅助命令：

```bash
python -m apps.cli.main config init --output ./vtl.config.json
python -m apps.cli.main config validate --config ./vtl.config.json
python -m apps.cli.main config show --config ./vtl.config.json
```

说明：

- 本阶段尚未实现 `run --mode remote`
- `config init` 可写 `.json` 或 `.yaml`；不支持写 TOML

## API 用法

启动 API：

```bash
python -m uvicorn apps.api.main:app --reload
```

健康检查：

```bash
curl -s http://127.0.0.1:8000/api/v1/health
curl -s http://127.0.0.1:8000/api/v1/health/ready
```

创建本地任务：

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/jobs \
  -H 'content-type: application/json' \
  -d '{
    "job_id": "00000000-0000-0000-0000-000000000350",
    "input_video": "./examples/mvp/source.mp4",
    "input_subtitle": "./examples/mvp/source.srt",
    "artifact_root": "./.artifacts/mvp-jobs",
    "prefer_ffmpeg": false,
    "allow_render_copy_fallback": true
  }'
```

查看任务状态与输出：

```bash
curl -s "http://127.0.0.1:8000/api/v1/jobs?artifact_root=./.artifacts/mvp-jobs"
curl -s "http://127.0.0.1:8000/api/v1/jobs/00000000-0000-0000-0000-000000000350?artifact_root=./.artifacts/mvp-jobs"
curl -s "http://127.0.0.1:8000/api/v1/jobs/00000000-0000-0000-0000-000000000350/artifacts?artifact_root=./.artifacts/mvp-jobs"
curl -s "http://127.0.0.1:8000/api/v1/jobs/00000000-0000-0000-0000-000000000350/logs?artifact_root=./.artifacts/mvp-jobs"
curl -s "http://127.0.0.1:8000/api/v1/jobs/00000000-0000-0000-0000-000000000350/qa?artifact_root=./.artifacts/mvp-jobs"
```

通过 API 重跑：

```bash
curl -s -X POST "http://127.0.0.1:8000/api/v1/jobs/00000000-0000-0000-0000-000000000350/stages/translate/rerun" \
  -H 'content-type: application/json' \
  -d '{"artifact_root":"./.artifacts/mvp-jobs","prefer_ffmpeg":false,"allow_render_copy_fallback":true}'

curl -s -X POST "http://127.0.0.1:8000/api/v1/jobs/00000000-0000-0000-0000-000000000350/segments/seg_0001/rerun" \
  -H 'content-type: application/json' \
  -d '{"artifact_root":"./.artifacts/mvp-jobs","reason":"api rerun","execute_stages":true,"prefer_ffmpeg":false,"allow_render_copy_fallback":true}'
```

## Artifact 布局

任务目录 `<artifact_root>/<job_id>/` 当前会生成：

- 顶层文件
  - `job.json`
  - `stage_runs.jsonl`
  - `artifacts.jsonl`
  - `segments.jsonl`
  - `segment_reruns.jsonl`（执行过片段重跑时才会出现）
- 各阶段目录
  - `ingest/media_info.json`
  - `caption/source_zh.raw.json`
  - `normalize/source_zh.cleaned.json`
  - `normalize/source_zh.srt`
  - `translate/en_subtitle.json`
  - `translate/en_subtitle.srt`
  - `translate/en_dub_text.json`
  - `translate/en_dub_text.txt`
  - `tts/seg_*.wav`
  - `tts/dub_en.wav`
  - `render/output_en.srt`
  - `render/mix.wav`
  - `render/final_en.mp4`
  - `qa/qa_report.json`
  - `qa/qa_report.md`
- `input/` 与 `logs/` 目录当前可能存在，但也可能为空

最近一次成功的真实运行 artifact 根目录是：

```text
.artifacts/wobubaichi-run-v5/00000000-0000-0000-0000-000000009105/
```

该运行使用了 `我是不白痴.mp4` 与手工 SRT，并成功产出：

- `translate/` 下的中译英字幕与配音文本
- 分段语音 WAV 与 `tts/dub_en.wav`
- `render/final_en.mp4` 与 `render/output_en.srt`
- `qa/qa_report.json` 与 `qa/qa_report.md`

## 已知限制

- 这仍然只是本地 MVP，不是生产级媒体流水线
- 当前最佳效果仍然来自**已经有人工整理字幕 sidecar** 的任务
- 没有字幕的任务依赖本地 ASR / 媒体翻译 fallback，结果更不稳定
- 字幕文本与配音文本分开存储，因此字幕质量和配音质量可能并不一致
- fallback 生成的 MP4 **不会**把字幕烧录进视频
- 在 macOS 上，AVFoundation fallback 可以生成带配音音轨的 MP4；如果该路径也不可用，最后的 copy fallback 只会保留原视频 MP4，不会把配音混进去
- 默认情况下，`doctor` 会把 `python`、`ffprobe` / macOS 探测 fallback、artifact 根目录可写性视为硬要求；只有在你关闭 render fallback 且坚持优先 ffmpeg 时，`ffmpeg` 才会变成硬要求
- 如果 QA 发现阻塞问题，任务会被标记为 `paused`，CLI 也会以 QA-blocked 退出码结束

## 验证参考

- `tests/test_mvp_documented_flow.py`
- `tests/test_cli_smoke.py`
- `tests/test_api_smoke.py`
