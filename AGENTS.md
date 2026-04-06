# Repository Guidelines

## Project Structure & Module Organization
Core Python code lives in `src/video_translation_agent/`. Keep domain models in `domain/`, pipeline wiring in `pipeline/`, stage implementations in `stages/`, and external integrations in `adapters/`. Entry points live in `apps/cli/main.py` and `apps/api/main.py`. The React/Vite UI is isolated in `apps/web/`. Tests live in `tests/`, documented fixtures in `examples/mvp/`, and local run outputs belong under `.artifacts/` or other untracked workspace folders, not in commits.

## Build, Test, and Development Commands
Install Python dependencies with `python -m pip install -e '.[dev]'`. Run the backend test suite with `python -m pytest`. Inspect CLI commands with `python -m apps.cli.main --help`, and start the API locally with `python -m uvicorn apps.api.main:app --reload`.

For the web app, work inside `apps/web/`: `npm install`, `npm run dev`, `npm run build`, and `npm run lint`. Use `python -m apps.cli.main run --config ./examples/mvp/vtl.config.json` when validating the documented MVP flow.

## Coding Style & Naming Conventions
Follow existing conventions: Python uses 4-space indentation, type hints, `snake_case` for functions/modules, and `PascalCase` for classes. Keep imports grouped by standard library, third-party, and local modules. Frontend code uses TypeScript + React function components; keep component names in `PascalCase`, hooks/state in `camelCase`, and prefer small, focused UI components under `apps/web/src/`.

There is no repo-wide formatter configured today. For frontend changes, keep code compatible with `apps/web/eslint.config.js`.

## Testing Guidelines
Pytest is configured in `pyproject.toml` and discovers tests from `tests/` with `test_*.py` naming. Add or update focused tests beside the affected area, for example API smoke coverage in `tests/test_api_smoke.py` or stage coverage in `tests/test_stages_translate_tts_render_qa.py`. If you touch `README.md`, CLI flows, or `examples/mvp/`, run `tests/test_mvp_documented_flow.py` as part of verification.

## Commit & Pull Request Guidelines
Recent history follows short, imperative subjects with optional scopes, for example `feat(web): build minimalist white-themed frontend UI` and `docs: clarify phase-1 execution baseline`. Prefer that style and keep commits narrowly focused.

Pull requests should explain the user-visible change, list verification commands run, and link related issues when applicable. Include screenshots for `apps/web` changes and note any required local tools such as `ffmpeg`, `ffprobe`, `say`, or `swift`.
