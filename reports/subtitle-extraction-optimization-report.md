# Subtitle Extraction Optimization Report

Date: 2026-04-03

## Scope
Evaluated Chinese subtitle extraction on:

- `test_video/我是不白痴.mp4` vs `test_video/我是不白痴.srt`
- `test_video/我在迪拜等你.mp4` vs `test_video/我的迪拜等你.srt`

## What Changed
- Switched the default ASR model from `tiny` to `small`, with fallback to `tiny` if `small` cannot initialize offline.
- Added explicit Whisper decode settings for Chinese: `task=transcribe`, stronger beam search, zero temperature, Chinese initial prompt, and tuned VAD padding.
- Mapped `avg_logprob` to a 0-1 confidence-like score instead of storing raw negative log probabilities.
- Made normalization language-aware so Chinese punctuation and spoken repetition are preserved.

## Evaluation Method
- Baseline: old behavior emulation with `faster-whisper tiny` using only `language='zh'` and `vad_filter=True`.
- Optimized: current repository code path via `FasterWhisperASRAdapter()`.
- Metric: character error rate (CER) after light Chinese-safe normalization and punctuation stripping for comparison.

## Results
| Video | Baseline CER | Optimized CER | Relative Improvement |
| --- | ---: | ---: | ---: |
| 我是不白痴.mp4 | 0.4704 | 0.1763 | 62.52% |
| 我在迪拜等你.mp4 | 0.4225 | 0.2698 | 36.14% |
| Weighted overall | 0.4481 | 0.2198 | 50.95% |

## Notable Improvements
- `我是不白痴.mp4`: baseline frequently misheard `龙虾` as `龙家`; optimized output recovered most seafood terms and sentence intent.
- `我在迪拜等你.mp4`: optimized output restored much more of the travel-dialogue structure, though proper nouns such as `哈利法塔` still have residual errors.

## Remaining Gaps
- Domain hotwords are still not configurable from job config or CLI.
- Proper nouns and rare terms remain the main error source.
- We did not change subtitle segmentation logic yet; this pass focused on recognition accuracy first.

## Verification
- `./.venv/bin/python -m pytest tests/test_asr_adapter.py tests/test_normalization_adapter.py tests/test_stages_ingest_caption_normalize.py tests/test_cli_smoke.py`
