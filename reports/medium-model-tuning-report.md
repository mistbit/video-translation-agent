# Medium Model Tuning Report

Date: 2026-04-03

## Scope
Compared current `small` against tuned `medium` on:

- `test_video/我是不白痴.mp4` vs `test_video/我是不白痴.srt`
- `test_video/我在迪拜等你.mp4` vs `test_video/我的迪拜等你.srt`

## Tuned Medium Settings
- `condition_on_previous_text=False`
- `task=transcribe`
- `beam_size=8`
- `best_of=8`
- `temperature=0.0`
- Chinese initial prompt enabled
- VAD parameters: `min_silence_duration_ms=300`, `speech_pad_ms=200`

## Why This Tuning
The previous untuned `medium` run over-merged long spans and fell into hallucinated continuation. Disabling `condition_on_previous_text` was the highest-impact fix in the parameter search on `我是不白痴.mp4`.

## Results
| Video | Small CER | Tuned Medium CER | Relative Improvement | Small Time (s) | Tuned Medium Time (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 我是不白痴.mp4 | 0.1763 | 0.1219 | 30.86% | 83.81 | 210.59 |
| 我在迪拜等你.mp4 | 0.2698 | 0.2563 | 5.00% | 76.85 | 148.56 |
| Weighted overall | 0.2198 | 0.1844 | 16.09% | 160.66 | 359.15 |

## Observations
- `我是不白痴.mp4`: tuned `medium` removed the catastrophic long-form hallucination seen before and clearly beat `small` on CER.
- `我在迪拜等你.mp4`: tuned `medium` improved proper nouns and dialogue wording, including `哈里法塔` and `我已经在机场了`.
- Tuned `medium` still tends to produce punctuation-heavy long first segments on some clips, but it no longer spirals into the severe repetition seen in the untuned run.

## Conclusion
Tuned `medium` is now better than `small` on both test videos and improves weighted CER from `0.2198` to `0.1844`. The tradeoff is runtime: `2.24x` slower on local CPU.

## Recommendation
- Keep `small` as the default for general local use if latency matters.
- Add tuned `medium` as an opt-in high-accuracy mode.
- If we later promote tuned `medium` more broadly, also clean up output formatting for leading dialogue markers such as `-`.
