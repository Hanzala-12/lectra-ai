# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Lectra AI: a speech-audio noise-removal pipeline (DeepFilterNet3 → MetricGAN+, Pyannote diarization, faster-whisper ASR) plus a "Study Assistant" NLP/LLM+RAG layer that turns a lecture transcript into notes, quizzes, a study schedule, an evaluation, and a RAG chatbot. FastAPI backend (`backend.py`), React/Vite frontend (`frontend/`), pure-Python `src/` core.

## Commands

### Setup
```bash
python -m venv venv
venv\Scripts\activate              # Windows; `source venv/bin/activate` elsewhere
pip install -r requirements.txt    # runtime deps (torch, deepfilternet, pyannote, faster-whisper, ...)
pip install -r requirements-dev.txt  # + pytest, black, flake8, mypy, pre-commit
cp .env.example .env                # fill HF_TOKEN (diarization) and OPENROUTER_API_KEY (LLM features)
```

### Run
```bash
python backend.py                            # API on :8000 (docs at /docs); no --reload, restart after code changes
cd frontend && npm install && npm run dev     # Vite dev server on :3000
start_both.bat                                # Windows: launches both in separate windows
python clean_voice.py input.mp3               # CLI, no server: single file
python clean_voice.py audio.wav --transcript --transcript-format srt
python clean_voice.py ./audio_folder/         # batch/directory mode
```

### Tests
```bash
pytest tests/                                              # full suite (coverage on by default, see pytest.ini)
pytest tests/test_pipeline.py -v
pytest tests/test_pipeline.py::test_config_loading -v      # single test
pytest tests/test_custom_modules.py -k profiler -v         # by keyword
pytest tests/test_cleanup_tool.py tests/test_cleanup_tool_properties.py -q
```
Full suite requires the complete runtime dependency set (notably `soundfile`); it's not always installable in constrained environments.

### Lint / format
```bash
black .
flake8 --max-line-length=127 --select=E9,F63,F7,F82
pre-commit run --all-files          # runs both of the above; this is what CI runs
cd frontend && npm run lint         # tsc --noEmit (type-check only; no eslint configured)
```

### Docker
```bash
docker-compose up --build   # backend:8000, frontend:3000, redis:6379, prometheus:9090, grafana:3001
```

## Architecture

### One FastAPI app, two API surfaces
`backend.py` creates a single global `LectraAIPipeline` instance at startup (in `lifespan`, so expensive model loads happen once, not per-request) and mounts `src/study_api.py`'s router via `app.include_router(study_router)`. So port 8000 serves both the audio-processing endpoints (`/api/process`, `/api/process-lecture`) and every study-assistant endpoint (`/api/lecture/...`).

### Audio pipeline (`src/pipeline.py`, class `LectraAIPipeline`)
`config.yaml` is the single source of truth for stage behavior — read it before changing pipeline code. Rough stage order: load media → adaptive-threshold VAD trim → diarize (Pyannote) → DeepFilterNet3 (+ optional band-limited dry-mix / low-band denoise to restore syllables DFN over-suppresses) → MetricGAN+ final polish → optional custom DSP stages → optional Voice Beautify (speech-only, SNR-guarded so it can't add noise back) → per-speaker ASR (faster-whisper).

Every optional stage (`neural_enhancer`, `beautify`, `profiler`, `adaptive_router`, `spectral_restoration`, `quality_metrics`, `low_band_denoise`) is off by default in `config.yaml` and lazily imported through `_load_optional_class()` in `pipeline.py`, gated by its own `enabled` flag — the module doesn't need to import cleanly (or even be installed) unless its flag is on. Follow this pattern for new optional stages rather than importing at module load time. See [docs/NOISE_REMOVAL_AND_DIARIZATION.md](docs/NOISE_REMOVAL_AND_DIARIZATION.md) for the full engineering rationale and [docs/PIPELINE_EXPLAINED.md](docs/PIPELINE_EXPLAINED.md) for a plain-language walkthrough.

### Custom DSP modules (academic layer, disabled by default)
Five modules bolted onto the production DFN→MetricGAN+ chain for research/demonstration purposes: `audio_quality_profiler.py`, `spectral_restoration.py`, `audio_quality_metrics.py`, `adaptive_router.py`, and `optimized_utils.py` (a Numba/SIMD benchmark helper, not a live pipeline stage). Enable via the corresponding `enabled: true` in `config.yaml`. Reference: [docs/CUSTOM_DSP.md](docs/CUSTOM_DSP.md).

### Study Assistant — NLP/LLM + RAG (`docs/STUDY_ASSISTANT.md`)
The half of the system downstream of a finished transcript:
- `src/lecture_repository.py` (+ `student_repository.py`, `session_store.py`, `lecture_session_repository.py`, `quiz_repository.py`, `study_plan_repository.py`, `audio_file_repository.py`) — one JSON file per record, per repository, under `data/` (git-ignored); the intended swap point for a real DB later. All seven share an identical `create()`/`get()`/`list()`/singleton-`get_repository()` shape.
- `src/rag_engine.py` — embedding-based retrieval (sentence-transformers, `all-MiniLM-L6-v2`) over overlapping transcript chunks, cosine similarity; automatic TF-IDF (scikit-learn) fallback if the embedding model can't load. Fully offline either way, no embedding API calls.
- `src/llm_client.py` — provider-agnostic OpenAI-compatible chat client, OpenRouter by default (`OPENROUTER_API_KEY` + optional `_2`/`_3` for automatic rotation on a rejected/exhausted key, `OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`). Every LLM-backed route returns HTTP 503 (not a crash) when no key is configured; check `GET /api/llm-status`. Supports both a blocking `chat()` and a streaming `chat_stream()` (SSE) — see `chat`/`chat/stream` and `notes`/`notes/stream` in `study_api.py`.
- `src/spaced_repetition.py` — a real SM-2 algorithm over a lecture's actual `quiz_attempts` history, feeding the schedule's review-date calculation. Stateless (recomputed on every fetch), not persisted separately.
- `src/tts_engine.py` — Piper (fully offline neural TTS) narrates a spoken-style LLM summary per lecture (the "audio recap" feature). Voice model lives in `models/piper/` (gitignored, same as the other pipeline model caches), download separately — see `_require_tts()`'s error message for the exact command.
- `src/study_tools.py` — notes/quiz/schedule/evaluation/recap-script generation built on `llm_client` + `rag_engine` (+ `spaced_repetition` for schedule).
- `src/study_api.py` — the FastAPI router exposing all of the above, mounted into `backend.py`. All `/lecture*` routes require a logged-in student (`auth_api.py`) and are scoped to that student's own lectures (404, not 403, on a cross-student access attempt — doesn't leak existence).

Flow: `POST /api/process-lecture` (runs the audio pipeline, stores the result as a lecture) → `POST /api/lecture/{id}/{notes|quiz|schedule|evaluate|chat|recap}`. Generated artifacts are cached on the lecture record; pass `?refresh=true` (or body equivalent) to regenerate.

### Frontend (`frontend/`, React 19 + TypeScript + Vite + Tailwind v4)
`frontend/src/App.tsx` defines two independent route trees under one `BrowserRouter`: the marketing site (`Layout` — `/`, `/features`, `/docs`, `/about`, ...) and the actual app (`AppLayout`, under `/app/*` — Dashboard, Upload, Library, `lecture/:id`, Quiz, Analytics, Chat). All API calls target `VITE_API_BASE_URL` (`frontend/.env.example`). The `/app/*` pages are fully wired to `study_api`'s endpoints (auth, notes/quiz/schedule/evaluation/chat/recap all live) — check the current state of a page's fetch calls before assuming otherwise, since this has changed over the project's history.

**Frontend animation/UI toolkit — use these, don't reach for something else:**
- **Motion** (formerly Framer Motion, `"motion"` in `package.json`, imported as `motion/react`) — the only animation library in this project. Already used for page transitions; use it for any new interaction/transition animation rather than hand-rolled CSS animations or a different library. Reference: [motion.dev](https://motion.dev).
- **MagicUI** ([magicui.design](https://magicui.design)) — the source for polished, animated UI components (shimmer effects, bento grids, marquees, scroll reveals) when building new frontend surfaces. It's a shadcn-registry-style component collection, not a plain npm package: pull individual components in on demand with `npx shadcn@latest add "https://magicui.design/r/<component>.json"`, which copies real source into `frontend/src/components/ui/` (per the `ui` alias in `frontend/components.json` — MagicUI registry items are typed `registry:ui`; they do **not** land in a `magicui/` subfolder, despite the name). It depends on Motion under the hood and the `cn()` helper at `frontend/src/lib/utils.ts` (already set up — `clsx` + `tailwind-merge`, standard shadcn convention). The `@` path alias resolves to `frontend/src` (`tsconfig.json` + `vite.config.ts`), matching where MagicUI/shadcn components expect `@/lib/utils` and `@/components/...` to resolve. `frontend/components.json` is hand-authored and committed for this — do **not** run `npx shadcn init`; see the gotcha below.
- Restyle any pulled-in component to match this project's own design tokens (`frontend/src/index.css`'s `@theme` block — teal `--color-primary`, magenta `--color-accent`, Fraunces serif headings, deliberately flat/near-shadowless) rather than using a component's stock look as-is — see the existing app pages for the established visual language before adding something that clashes with it.

### Standalone maintenance CLI
`cleanup_tool.py` is unrelated to the audio/study pipelines: a two-phase repo-cleanup utility (dry-run Markdown report → explicit `--execute` with tar backup, ordered deletion, post-deletion validation, and auto-restore on failure). Independently tested via `tests/test_cleanup_tool.py` and `tests/test_cleanup_tool_properties.py` (property-based).

## Git / commit conventions

- Do **not** add Claude as a co-author or contributor when committing/pushing to GitHub from this repo — omit any `Co-Authored-By: Claude ...` trailer from commit messages.

## Operational gotchas

- Both `backend.py` and `clean_voice.py` call `load_dotenv()` independently — `.env` (`HF_TOKEN` for diarization, `OPENROUTER_API_KEY` for LLM features) is required by either entry point, not just the server.
- `backend.py` runs uvicorn without `reload=True` and loads the pipeline/models once at startup — **restart the process after changing `backend.py` or anything under `src/`**; it will not pick up changes live.
- The file cache (`cache.enabled` in `config.yaml`, implemented in `src/cache_manager.py`, keyed by file hash + config) can silently return stale results after a pipeline code change even though the config looks unchanged. It's off by default in `config.yaml`; if you enable it during development, clear `./cache` after code edits.
- This file (`CLAUDE.md`) previously existed only as an untracked local file in an auto-provisioned worktree — never actually committed to git, invisible from the real working directory and from GitHub. Fixed by committing it for real; if you ever find yourself editing a `CLAUDE.md` that `git log -- CLAUDE.md` shows no history for, that's the same bug recurring — commit it, don't just leave it local.
- `npx shadcn@latest add <registry-url>` hangs forever (no output, no error, no file written) if `frontend/components.json` is missing — with no config present it silently launches an interactive `init` wizard, and there's no TTY in this environment to answer its prompts. `frontend/components.json` is already committed specifically to prevent this; if it's ever missing, hand-author it (style/rsc/tsx/tailwind/aliases — see git history for the exact shape) rather than letting the CLI prompt.
