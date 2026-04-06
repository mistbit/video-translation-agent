# Frontend Browser Test Report

## Scope

This report covers a real browser test of the local web console after the recent frontend/API integration work. The goal was to verify that the UI can create a job, render the resulting status, poll details, and surface artifacts and QA data.

The run used local sample files:

- Video: `examples/mvp/source.mp4`
- Subtitle: `examples/mvp/source.srt`
- Artifact root: `output/playwright/artifacts`

To keep the test deterministic, the backend was started with a local `ffprobe` stub at `output/playwright/bin/ffprobe`.

## Commands

Servers and browser automation were orchestrated with the `webapp-testing` helper:

```bash
./.venv/bin/python /Users/masamiyui/OpenSoureProjects/skills/skills/webapp-testing/scripts/with_server.py \
  --server 'cd /Users/masamiyui/OpenSoureProjects/Forks/video-translation-agent && PATH="/Users/masamiyui/OpenSoureProjects/Forks/video-translation-agent/output/playwright/bin:$PATH" ./.venv/bin/python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000' --port 8000 \
  --server 'cd /Users/masamiyui/OpenSoureProjects/Forks/video-translation-agent/apps/web && npm run dev -- --host 127.0.0.1 --port 5173' --port 5173 \
  --timeout 60 \
  -- node /Users/masamiyui/OpenSoureProjects/Forks/video-translation-agent/apps/web/scripts/e2e-local-console.mjs
```

Automation script: `apps/web/scripts/e2e-local-console.mjs`

## Test Flow

1. Open `http://127.0.0.1:5173`.
2. Fill video path, subtitle path, artifact root, source/target languages, and switch `ASR Model` to `medium`.
3. Submit `Start Processing`.
4. Wait for:
   - active job ID
   - active status row
   - artifact list
   - QA summary
5. Click the matching history entry and capture final screenshots.

## Result

- Status: success
- Job ID: `2458fd26-db56-4241-ae61-e9ad8bc8bac1`
- Browser console errors: none
- Page runtime errors: none
- QA summary rendered with `Segments checked = 2`, `Overrun ratio = 0%`, `Blocking reasons = none`
- Artifacts rendered, including final video, dub WAV, output subtitle, and QA reports

Raw structured output is saved in `output/playwright/result.json`.

## Screenshots

- `output/playwright/screenshots/01-home.png`
- `output/playwright/screenshots/02-form-filled.png`
- `output/playwright/screenshots/03-job-complete.png`

## Findings

### 1. Completed jobs display a misleading `idle` stage

Observed result: the captured status row text was `completedidle` for a successful run. The job completed, QA rendered, and artifacts were present, but the UI still showed `idle` as the stage label.

Code path:

- `apps/web/src/App.tsx:520`
- `apps/web/src/App.tsx:523`

Cause: the UI renders `currentJob.current_stage ?? 'idle'`. For completed jobs, `current_stage` is `null`, so the fallback becomes `idle`, which reads like the job never entered a stage or is waiting.

Impact: users can misread a completed run as inactive or not yet started.

### 2. The ASR accuracy hint does not account for provided sidecar subtitles

Observed result: the form allowed `Subtitle Path` and `ASR Model = medium` together, and the screen still showed the Chinese ASR tuning hint. In this test, the run completed from the provided subtitle file, so the ASR path was not exercised.

Code path:

- `apps/web/src/App.tsx:333`
- `apps/web/src/App.tsx:462`

Impact: users can think they validated `medium` ASR quality when they actually validated a sidecar-subtitle ingest flow.

## Notes

This test validates the frontend/API workflow and rendering path. It does not validate raw ASR transcription quality, because the sample run intentionally used a provided subtitle file for speed and determinism.
