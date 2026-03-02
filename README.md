# Video Translation Agent

一个功能完整的视频翻译agent，支持字幕提取（OCR/ASR）、字幕翻译（GLM云服务）、字幕导出（SRT格式）和带字幕的视频导出。

## 功能特性

- **字幕提取**
  - OCR提取：使用PaddleOCR从视频帧中识别硬编码字幕
  - ASR提取：使用Faster-Whisper从音频转录软字幕
  - 混合模式：结合OCR和ASR提高准确性

- **字幕翻译**
  - 支持中英互译
  - 使用GLM云服务API，翻译质量高
  - 批量翻译优化
  - 自动检测源语言

- **字幕导出**
  - SRT格式导出（默认）
  - 支持VTT、ASS/SSA格式
  - UTF-8编码，兼容性更好

- **视频导出**
  - 将字幕烧录到视频中
  - 支持软字幕（MUX）输出
  - 自定义字幕样式（字体、颜色、位置）

## 系统要求

- Python 3.10+
- FFmpeg（用于视频/音频处理）

## 安装

### 1. 安装 FFmpeg

**macOS (使用 Homebrew):**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
从 [FFmpeg官网](https://ffmpeg.org/download.html) 下载并添加到系统PATH。

### 2. 安装 Python 依赖

```bash
# 克隆项目
git clone https://github.com/yourusername/video-translation-agent.git
cd video-translation-agent

# 安装依赖
pip install -r requirements.txt

# 或使用setup.py安装
pip install -e .
```

### 3. 安装完成后验证

```bash
python -c "import cv2; import paddleocr; import faster_whisper; print('所有依赖安装成功！')"
```

## 配置

### GLM API Key

编辑 `config.yaml` 文件或设置环境变量：

```bash
export GLM_API_KEY="your_glm_api_key"
```

GLM API Key可以从 [智谱AI开放平台](https://open.bigmodel.cn/) 获取。

### 配置文件说明

```yaml
# config.yaml

glm:
  api_key: ""              # GLM API密钥（可使用环境变量）
  model: "glm-4"           # 使用的模型
  temperature: 0.3         # 温度参数

ocr:
  lang: "ch"               # 语言：ch=中英文，en=英文
  use_angle_cls: true      # 是否使用角度分类
  det_db_thresh: 0.3       # 检测阈值
  det_db_box_thresh: 0.5   # 边界框阈值

asr:
  model_size: "base"       # 模型大小：tiny/base/small/medium/large
  compute_type: "int8"     # 计算类型：int8/float16/float32
  language: "auto"         # 语言：auto/zh/en
  beam_size: 5

video:
  frame_interval: 1.0       # OCR提取时的帧间隔（秒）
  output_fps: 30

output:
  subtitle_format: "srt"    # 输出格式
  encoding: "utf-8-sig"
  output_dir: "./output"

subtitle:
  font_size: 24
  font_color: "white"
  position: "bottom"       # 位置：bottom/top/center
  margin: 10
```

## 使用方法

### 提取字幕

```bash
# 使用ASR提取软字幕（推荐，准确度更高）
vta extract video.mp4 --method asr -o subtitles.srt

# 使用OCR提取硬字幕
vta extract video.mp4 --method ocr -o subtitles.srt

# 同时使用OCR和ASR（结合两者优点）
vta extract video.mp4 --method both -o subtitles.srt

# 指定不同的帧间隔（仅对OCR有效）
vta extract video.mp4 --method ocr --interval 0.5 -o subtitles.srt

# 使用更大的Whisper模型（更准确但更慢）
vta extract video.mp4 --method asr --model-size medium -o subtitles.srt
```

### 翻译字幕

```bash
# 中译英
vta translate subtitles.srt --lang en -o subtitles_en.srt

# 英译中
vta translate subtitles_en.srt --lang zh -o subtitles_zh.srt

# 自动检测源语言并翻译
vta translate subtitles.srt --lang en
```

### 导出带字幕视频

```bash
# 导出硬字幕（烧录到视频）
vta export subtitles.srt video.mp4 -o output.mp4

# 导出软字幕（可开关）
vta export subtitles.srt video.mp4 -o output.mp4 --soft
```

### 一键完整流程

```bash
# 提取字幕并翻译
vta full video.mp4 --translate

# 提取、翻译并导出视频
vta full video.mp4 --translate --export

# 完整流程，指定输出目录
vta full video.mp4 --translate --export --output-dir ./my_output

# 使用OCR提取并翻译
vta full video.mp4 --translate --export --method ocr
```

### 直接使用 Python API

```python
from src.video_processor import VideoProcessor
from src.asr_transcriber import ASRTranscriber
from src.translator import Translator
from src.subtitle_export import SubtitleExporter
from src.video_export import VideoExporter

# 提取字幕
transcriber = ASRTranscriber(model_size="base")
subtitles = transcriber.transcribe_video("video.mp4")

# 翻译字幕
translator = Translator(api_key="your_api_key")
translated = translator.translate_subtitles(subtitles, target_lang="en")

# 导出SRT
exporter = SubtitleExporter()
exporter.export_srt(translated, "output.srt")

# 导出带字幕视频
video_exporter = VideoExporter(font_size=24, font_color="white")
video_exporter.export_with_subtitles("video.mp4", translated, "output.mp4")
```

## 常见问题

### Q: OCR提取不到字幕怎么办？
A: 尝试以下方法：
- 减小 `frame_interval` 值（如 0.5 或 0.3）
- 调整 `det_db_thresh` 和 `det_db_box_thresh` 参数
- 检查视频分辨率，过低分辨率可能影响识别

### Q: ASR转录速度太慢？
A: 可以：
- 使用更小的模型（tiny 或 base）
- 设置 `compute_type` 为 `int8`
- 使用 `vad_filter` 过滤静音片段

### Q: 翻译API调用失败？
A: 请检查：
- GLM API Key是否正确设置
- 网络连接是否正常
- API账户是否有余额

### Q: 导出视频失败？
A: 确保已安装FFmpeg，并检查：
- 输出目录是否有写入权限
- 磁盘空间是否充足
- moviepy是否正确安装

## 技术栈

- **OCR**: PaddleOCR - 百度开源的OCR工具库
- **ASR**: Faster-Whisper - OpenAI Whisper的优化版本
- **翻译**: GLM云服务API - 智谱AI的大语言模型
- **视频处理**: OpenCV + FFmpeg + moviepy

## 项目结构

```
video-translation-agent/
├── src/
│   ├── __init__.py
│   ├── main.py              # CLI入口
│   ├── config.py            # 配置管理
│   ├── video_processor.py   # 视频处理（OpenCV）
│   ├── subtitle_extractor.py # OCR字幕提取（PaddleOCR）
│   ├── asr_transcriber.py   # ASR语音转录（Faster-Whisper）
│   ├── translator.py        # GLM翻译服务
│   ├── subtitle_export.py   # 字幕导出（SRT/VTT/ASS）
│   └── video_export.py      # 视频导出（moviepy）
├── tests/
│   ├── __init__.py
│   ├── test_subtitle_extractor.py
│   └── test_translator.py
├── config.yaml              # 配置文件
├── requirements.txt          # Python依赖
├── setup.py                 # 安装脚本
└── README.md
```

## 许可证

MIT License
