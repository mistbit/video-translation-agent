# Medium Model Comparison Report

Date: 2026-04-03

## Scope
Compared `faster-whisper small` and `faster-whisper medium` on:

- `test_video/我是不白痴.mp4` vs `test_video/我是不白痴.srt`
- `test_video/我在迪拜等你.mp4` vs `test_video/我的迪拜等你.srt`

## Evaluation Setup
- Same decode settings for both models: `task=transcribe`, `beam_size=8`, `best_of=8`, `temperature=0.0`
- Same Chinese prompt and VAD parameters as the current optimized path
- Metric: character error rate (CER) after light Chinese-safe normalization and punctuation stripping
- Hardware path: local CPU, `compute_type=int8`

## Results
| Video | Small CER | Medium CER | Better Model | Small Time (s) | Medium Time (s) |
| --- | ---: | ---: | --- | ---: | ---: |
| 我是不白痴.mp4 | 0.1763 | 0.2562 | Small | 78.37 | 285.41 |
| 我在迪拜等你.mp4 | 0.2698 | 0.2286 | Medium | 69.72 | 259.06 |
| Weighted overall | 0.2198 | 0.2434 | Small | 148.09 | 544.47 |

## Conclusion
`medium` did not improve overall subtitle extraction quality in this repo on these two test videos. Weighted CER worsened from `0.2198` to `0.2434`, while runtime increased by `3.68x`.

## Observations
- `我在迪拜等你.mp4`: `medium` improved proper nouns and dialogue wording, for example `哈里法塔` and `我已经在机场了`.
- `我是不白痴.mp4`: `medium` over-merged content into very long segments, introduced hallucinated continuation, and produced repeated garbage near the end. This dominated the overall score.
- The failure pattern suggests the current decode settings are not robust enough for `medium` on long-form Chinese content under CPU inference.

## Recommendation
- Keep `small` as the default model for now.
- If we want to pursue `medium`, test it behind an opt-in flag and tune decode behavior separately:
  - reduce `condition_on_previous_text`
  - cap chunk length or clip timestamps
  - add hallucination controls for long segments
  - inspect whether lower `beam_size` is more stable for long videos
