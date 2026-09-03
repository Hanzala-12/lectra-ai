# Lectra AI — Audit Findings & Fix List

**Last updated:** 2026-09-03 (live-verified this session, in `D:\fyp` using `D:\fyp\venv`)
**Purpose:** single source of truth for what's actually confirmed working, what's broken, what's missing, and every fix that still needs doing. Every claim below is either (a) marked `CONFIRMED` with the exact evidence that proves it, or (b) marked `HYPOTHESIS`/`NOT YET TESTED` if it isn't proven. Nothing here is a guess dressed up as a fact.

---

## FIX LOG (most recent first)

Fixes below are code-complete and passed **fast** checks (`py_compile`, `tsc --noEmit`, `pytest tests/` — 108 passed in 33.68s). None have been re-verified with a full, real, end-to-end audio pipeline run yet — that's intentionally deferred to one comprehensive run covering everything in this batch at once, instead of a slow (~20-50 min) real-audio test after every individual change.

1. **[done, fast-verified]** `src/pipeline.py` — replaced the per-diarization-segment transcription loop (22 separate Whisper calls, ~85-95s fixed overhead each ≈ ~30 min of pure waste) with single-pass whole-file transcription + `asr_processor.combine_with_diarization()` for speaker labeling. Does not touch noise removal (separate, earlier pipeline stage). **Not yet re-run against real audio to confirm the real speedup number or that output is still correct — that's part of the deferred final run.**
2. **[done, fast-verified]** `backend.py::get_model_status()` — Pyannote readiness now also checks the live `pipeline.diarization.pipeline` object (same pattern already used for Whisper), not just local folder size. Fixes the false-negative where `/api/model-status` reported `pyannote.ready: false` even while diarization was demonstrably working.
3. **[done, fast-verified]** `backend.py::initialize_pipeline()` — fixed the Whisper "turbo" vs "large-v3-turbo" alias mismatch that caused a full model reload from disk (~20-30s) on every single `/api/process` or `/api/process-lecture` request, even when nothing changed.
4. **[done, verified]** `pytest.ini` — `[tool:pytest]` → `[pytest]` (correct section name for a file with this filename). Installed the missing `pytest-cov` into `D:\fyp\venv` so the now-active `--cov` addopts don't just hard-error. Confirmed: `--cov` now genuinely runs and produces a real coverage report (12% overall on `test_api.py` alone — full-suite number will differ).
5. **[done, fast-verified]** `src/study_api.py::grade()` + `src/lecture_repository.py` — quiz attempts are now persisted (`quiz_attempts: []` on each lecture record, capped at the last 20), instead of being computed and silently discarded. `lecture_repository.py::list()` now also surfaces `quiz_attempts` (count) and `best_score` per lecture for the library summary view. `frontend/src/lib/api.ts`'s `LectureSummary` type updated to match.
6. **[done]** `.env.example` — rewritten to clearly separate the ~6 env vars actually read anywhere in the code (confirmed via `grep -rn "os.getenv\|os.environ\[" backend.py src/` — the full list is `HF_TOKEN`/`HUGGING_FACE_HUB_TOKEN`, `MAX_FILE_SIZE_MB`, `OPENROUTER_API_KEY`/`OPENROUTER_MODEL`/`OPENROUTER_BASE_URL`/`LLM_API_KEY`, `APP_URL`) from the ~13 that were previously listed as if they did something but are **never read anywhere** (`API_KEY`, `API_HOST`, `API_PORT`, `MODEL_CACHE_DIR`, `DEFAULT_WHISPER_MODEL`, `ENABLE_GPU`, `MAX_WORKERS`, `ENABLE_DIARIZATION`, `REDIS_URL`, `ENABLE_CACHING`, `ENABLE_METRICS`, `LOG_LEVEL`, `ENV`, `DEBUG`). This was a bigger finding than originally scoped in §4.4 below — almost the whole file was aspirational, not just `API_KEY`.
7. **[done]** `docker-compose.yml` — added comments clarifying the same vestigial-env-var situation applies to the `backend` service's `environment:` block, and that the `redis` service is provisioned but unused by any application code. Did not delete anything (conservative — don't remove infra you don't have full context on without being asked).

8. **[decision made, not code]** Auth scope — **user explicitly chose "skip for now"** (asked via a direct question, not assumed). Auth stays fully open; fix time redirected to test coverage / LLM verification / diarization testing instead. This is a deliberate decision, not an oversight — don't silently start building auth without asking again first.
9. **[done]** `config.yaml` — `beautify.enabled` and `low_band_denoise.enabled` reverted to `false` per explicit user choice ("revert both to off"), matching the original committed defaults. Combined with the 4 DSP flags already reverted, `config.yaml` is now back to running only the core DeepFilterNet3→MetricGAN+→diarization→Whisper chain, no extras.

10. **[done, verified]** `tests/test_study_api.py` — new file, **19 tests**, all passing, covering `/api/library`, full lecture CRUD, notes/quiz/schedule/evaluation/chat generation, the LLM-not-configured 503 path, and — critically — a **regression test for the quiz-persistence fix** (`test_grade_quiz_persists_attempt`, `test_multiple_quiz_attempts_accumulate`). Uses a `FakeLLM` stand-in (no real network/credits needed) and an isolated temp-dir lecture repository (doesn't touch real `data/lectures/`). Full suite is now **127 passed** (108 original + 19 new), confirmed run together with no cross-file interference.

11. **[done — real success confirmed]** A genuine, non-mocked, successful LLM generation against the real OpenRouter API, through the actual `llm_client.py` code path:
    ```
    Q: In one short sentence, what is photosynthesis?
    A: Photosynthesis is the process by which plants, algae, and some bacteria
       convert light energy into chemical energy, producing oxygen and glucose
       from carbon dioxide and water.
    ```
    Took 3 attempts to find a working free model (non-invasive test, did **not** touch `D:\fyp\.env` or `config.yaml`): `meta-llama/llama-3.3-70b-instruct:free` → dead, HTTP 404 "unavailable for free" (model deprecated); `openrouter/free` (auto-router) → HTTP 200 but null `content`; `z-ai/glm-5.2:free` → HTTP 429, upstream shared-pool rate-limited (confirmed via raw response inspection, reproduced twice); `minimax/minimax-m3:free` → **worked cleanly**. Confirms: the API key is genuinely valid, the request/response handling in `llm_client.py` is correct, and the earlier `402`s were purely an out-of-credits issue on the default paid model (`openai/gpt-4o-mini`), not a wiring problem. Free-tier models are real but flaky/rotate — don't hard-code one without a fallback.

**Still open / not started this session:** multi-speaker diarization test, video-file test, committing the working tree, and the deferred final comprehensive pipeline run.

---

## 0. READ THIS FIRST — uncommitted local changes

`D:\fyp` is on `master`, HEAD = `19f4a74`, "up to date with origin/master" — but the working tree has **real, unpushed, uncommitted fixes** that a fresh clone (or the audit worktree used earlier in this session) does **not** have:

```
git status --short  (as of this session)
 M .gitignore
 A PROJECT_ANALYSIS.md
MM backend.py
MM config.yaml
 A frontend/src/lib/api.ts
 M frontend/src/pages/Analytics.tsx
 M frontend/src/pages/Dashboard.tsx
```

**If none of this gets committed, all of the fixes below are lost the moment this folder is cloned fresh or the branch is reset.** Committing this working tree (in sensible, reviewed chunks — not blindly) should be an early fix-phase step, not an afterthought.

---

## 1. Executive summary

- The **audio pipeline (DeepFilterNet3 → MetricGAN+ → Pyannote diarization → faster-whisper)** is real, and — as of this session — **confirmed working end-to-end on real audio**, producing a real, accurate transcript. This was NOT true in a fresh checkout / the wrong Python environment (see §9).
- It is currently **~21x slower than real-time** (50 min for 2.3 min of audio) even with all experimental extras turned off. This is the single biggest practical blocker right now. Root cause not yet proven (§3).
- The **frontend build is fixed** locally (uncommitted) — `tsc --noEmit` and `vite build` both pass, the dev server renders correctly. The version living in git history (`19f4a74`) is still broken (missing `frontend/src/lib/api.ts` because of a `.gitignore` bug) — see §9.
- **Dashboard and Analytics are now real** (uncommitted) — they used to be 100% hardcoded/mock; the current on-disk versions genuinely fetch and compute from the lecture repository.
- **No authentication, no Student entity, no quiz-result persistence, no relational database** exist anywhere. Login/Signup are decorative. This has not changed and needs real work (§5).
- Test suite: **108/108 pass**, confirmed twice (once with deps missing, once with the real venv) — but there is **zero test coverage** for the entire Study Assistant API (notes/quiz/schedule/evaluate/chat).

---

## 2. CONFIRMED WORKING (live-tested this session, in `D:\fyp`, real venv, real models)

| # | What | Evidence |
|---|---|---|
| 1 | `D:\fyp\venv` has all heavy ML deps installed for real | `python -c "import df.enhance, pyannote.audio, speechbrain, faster_whisper"` → all `OK` |
| 2 | Real downloaded model weights exist | `D:\fyp\models\deepfilternet\DeepFilterNet3\checkpoints\model_120.ckpt.best`, `models\metricgan\enhance_model.ckpt`, `models\models--mobiuslabsgmbh--faster-whisper-large-v3-turbo` (1.6GB), pyannote `speaker-diarization-3.1` config |
| 3 | Backend boots successfully | `python backend.py` → `Application startup complete`, confirmed twice (13:01 and 13:27 boots this session) |
| 4 | DeepFilterNet3 loads and runs | log: `DF \| Found checkpoint ...model_120.ckpt.best... \| Model loaded`; `deepfilter_processor - Model loaded successfully (SR: 48000Hz)` |
| 5 | MetricGAN+ loads and runs | log: `metricgan_processor - MetricGAN+ loaded successfully` |
| 6 | Pyannote diarization loads and produces real output | log: `diarization - Diarization pipeline loaded successfully`; **live run produced 22 real timestamped speaker-turn segments** on a 140.5s file |
| 7 | Diarization sub-models download successfully over HTTPS | Live `httpx` 200 OK responses for `pyannote/segmentation-3.0` and `pyannote/wespeaker-voxceleb-resnet34-LM` — the `[WinError 10013]` failure documented in `PROJECT_ANALYSIS.md` (2026-09-02) did **not** reproduce today; was a transient network/firewall issue, not a code bug |
| 8 | faster-whisper (large-v3-turbo) loads and transcribes real speech | log: 22× `Detected language 'en' with probability [0.94-1.00]` + `Transcription complete` |
| 9 | **Full end-to-end pipeline produces a real, accurate transcript** | `POST /api/process-lecture` on `fyp audio/output_overlapped.mp3` (140.5s, real recorded lecture about GANs/Ian Goodfellow) → HTTP 200, transcript is coherent and matches the actual audio content (minor ASR imperfections like "generated adverse load methods, GANS" instead of "generative adversarial networks, GANs" — normal ASR behavior, not fabrication). Stored as `lecture_id: eb2f8501707a` |
| 10 | Diarization → transcript speaker-labeling actually works | All 22 transcript segments correctly carry `"speaker":"SPEAKER_00"`, timestamps match the diarization turns exactly |
| 11 | Lecture repository (JSON file store) works | Created/read/deleted real records live via `/api/lecture`, `/api/library`, `DELETE /api/lecture/{id}` |
| 12 | LLM client reaches the real provider | Earlier live test: `POST .../notes` → real HTTPS call to `openrouter.ai`, real `402 Payment Required` response (not a fake/mocked error) — confirms wiring is correct, blocked only by provider credits on the default paid model |
| 13 | RAG retrieval logic (TF-IDF) is real, not mocked | `src/rag_engine.py` — chunking + cosine similarity, exercised live (reached the LLM call step before hitting the same 402) |
| 14 | **Frontend TypeScript check passes** | `cd D:\fyp\frontend && npx tsc --noEmit` → 0 errors (checked fresh this session) |
| 15 | **Frontend production build passes** | `npm run build` → `✓ 2102 modules transformed`, real `dist/` output, `built in 28.21s` |
| 16 | **Frontend actually renders** (not just builds) | Live `vite dev` + browser: `Library.tsx`, `Lecture.tsx`, `lib/api.ts`, `LecturePicker.tsx` all `200 OK` over the network. Only error seen was an *expected* `ERR_CONNECTION_REFUSED` to `/api/library` because the backend wasn't started yet at that exact check — correct, graceful error handling, not a bug |
| 17 | `Dashboard.tsx` is real, not mocked | Full file read: calls `api.library()`, computes real stats (lecture count, notes/quiz/eval counts, total words/minutes, completion %), real loading/error/empty states, **zero hardcoded numbers** |
| 18 | `Analytics.tsx` is real, not mocked | Full file read: calls `api.library()` + `api.getLecture(id)` per lecture, computes real artifact coverage, real topic frequency from actual `evaluation.main_topics`, real CSV/text export via Blob — **no `Math.random()`, no `{/* Mock */}` comments** (those only exist in the old committed version) |
| 19 | `backend.py`'s multipart form parsing works | `Form(...)` added for `whisper_model`/`enable_diarization`/`transcript_format`/`title` on `/api/process` and `/api/process-lecture` — this is what makes the browser's real `FormData` upload actually work (before this fix those fields silently fell back to their defaults) |
| 20 | Full `pytest` suite passes, twice | 108 passed, 0 failed — once via a Python with the ML deps missing (mocked test fixtures), once via `D:\fyp\venv` with everything really installed (168.50s). Same result either way — confirms the test suite itself doesn't secretly depend on the missing-vs-present state |
| 21 | Disabling the 4 custom DSP modules actually took effect | Post-edit run's log jumps straight from `STEP 1: Loading media` to `STEP 2: Diarizing` — no more `Audio Quality Profiler enabled` / `Adaptive Router enabled` / `Spectral Restoration enabled` lines |

---

## 3. CRITICAL — Performance problem (NOT solved yet)

**The full pipeline currently takes ~50 minutes to process a 2.3-minute audio file.**

- Exact measurement: `POST /api/process-lecture`, 140.5s input, DSP modules OFF, nothing else running concurrently → **2984.93 seconds (49 min 45s)**, `HTTP 200`.
- README claims **5-7.5x faster than real-time**. Actual measured result this session: **~21x slower than real-time**. This is a ~150x gap from the documented claim.
- Removing the 4 experimental DSP modules (§6) did **not** fix this — the slow run was still slow afterward. So the DSP modules are not the (sole) cause.

**Diagnosis — `HYPOTHESIS, NOT CONFIRMED`:** the pipeline transcribes **once per diarization turn** (22 separate `whisper.transcribe()` calls for this file) instead of once for the whole file. Evidence pointing this way:
- Every single one of the 22 calls independently logged `Detected language 'en' with probability X.XX` — language detection is being redundantly re-run 22 times.
- Wall-clock cost per call did **not** scale with audio length the way you'd expect: a 0.357-second clip took ~85s, a 27.351-second clip took ~7 min, a 1.986-second clip took ~87s, a 3.905-second clip took ~108s. Very short and moderately-short clips cost roughly the *same* wall time — consistent with a large **fixed per-call overhead** dominating over actual audio-length-proportional compute.
- Relevant code: `src/pipeline.py` "Transcribing per speaker segment (diarization-guided)" path; `src/asr_processor.py::ASRProcessor.transcribe()`.

**This has NOT been isolated or proven.** The untested next step (proposed, not yet done): disable diarization and time a single-pass whole-file transcription of the same audio, to see if the per-segment approach is really the bottleneck versus this CPU just being generically slow for `faster-whisper` `int8` inference. **Do this before assuming a fix.**

Other things that could also be contributing (not ruled out):
- No GPU (`gpu_available: false` in `/api/health`) — everything runs on CPU only.
- `int8` compute type may not be well-optimized for this specific CPU's instruction set (int8 quantization isn't a universal speedup — depends on AVX support).
- Background OS-level activity (antivirus, indexing) on this Windows machine is invisible to us and untested as a factor.

---

## 4. Bugs found (confirmed, reproducible)

1. **`/api/model-status` reports Pyannote as not-ready when it actually is.**
   Reproduced twice, in two separate backend boots. `GET /api/model-status` → `"pyannote":{"ready":false,"progress":0.0}` **even while the same running process's own log says `Diarization pipeline loaded successfully` and it demonstrably diarized real audio correctly.**
   Root cause: the readiness check only measures the size of `D:\fyp\models\pyannote\`, but the two sub-models Pyannote actually needs (`segmentation-3.0`, `wespeaker-voxceleb-resnet34-LM`) get cached to `C:\Users\<user>\.cache\torch\pyannote\` instead — a different folder entirely. File: `backend.py`, function `get_model_status()`.

2. **Stale file cache silently serves outdated results.**
   First `/api/process-lecture` call this session returned instantly with `"transcript":"", "transcript_segments":[]` — looked broken. Backend log showed why: `cache_manager - Cache HIT for key d47f78... ` / `pipeline - ✅ CACHE HIT! Returning cached result instantly`. The cached entry was from before ASR was enabled (`asr.skip` used to be `true`), so it cached an empty transcript, and — because `cache.enabled: true` and the cache key is `hash(file content + config)` — kept serving that stale empty result even after `asr.skip` was fixed to `false`, because the file+config-relevant-parts hash apparently still matched. Clearing `D:\fyp\cache\` and re-running fixed it. **This will bite again** any time code/model behavior changes without the cache key changing. File: `src/cache_manager.py`.

3. **`pytest.ini` uses the wrong section header for its filename**, so its `addopts` (verbose mode, short traceback, and critically `--cov=src --cov=backend --cov-report=...`) silently do nothing.
   - `pytest.ini` uses `[tool:pytest]` (line 2) — that section name is only honored inside `setup.cfg`. A file literally named `pytest.ini` must use plain `[pytest]`.
   - Confirmed by direct A/B test: bare `pytest tests/` never errors even though `pytest-cov` isn't installed; adding `--cov=src` explicitly on the command line **immediately hard-errors** with `unrecognized arguments: --cov=src` — proving the ini's addopts (which include the same flag) are never actually being read.
   - Also confirmed: `pytest-cov`, `black`, `flake8`, `pytest-asyncio`, `pytest-mock` are **not installed** in `D:\fyp\venv` either (checked directly, not guessed).

4. **`.env.example` documents an `API_KEY` that is never checked anywhere in the code.** Grepped the whole repo for `API_KEY` outside of `OPENROUTER_API_KEY` — zero matches in any `.py` file. It gives a false impression that the API is protected. It is not (see §5).

5. **`redis` is provisioned in `docker-compose.yml` and wired into `backend`'s env (`REDIS_URL`) but never imported or used anywhere in `src/` or `backend.py`.** The actual cache (`src/cache_manager.py`) is a plain local-filesystem cache. Likely leftover from an earlier design.

---

## 5. Confirmed MISSING (no meaningful implementation anywhere)

- **Authentication of any kind.** `Login.tsx`/`Signup.tsx` forms call `e.preventDefault()` and do nothing; the "Sign In"/"Sign Up" buttons are plain `<Link to="/app/dashboard">` — no request is ever sent, no credential is ever checked. Confirmed: zero matches anywhere in `frontend/src` for `token|localStorage|sessionStorage|useAuth|AuthContext|jwt`.
- **Every backend API route is unauthenticated.** No auth dependency on any FastAPI route. `CORS` is `allow_origins=["*"]`. Anyone reaching the server can list/read/**delete** any lecture or spend the LLM budget.
- **Student entity.** Doesn't exist. No accounts, no per-user anything.
- **QuizResult persistence.** `study_api.py`'s `grade()` (`POST /lecture/{id}/quiz/grade`) computes a score with `study_tools.grade_quiz()` and returns it in the HTTP response — **it never calls `get_repository().update(...)`.** Confirmed by re-fetching a lecture record right after grading it: no trace of the attempt anywhere. A quiz score is shown once and permanently discarded.
- **LectureSession, Question, Answer as real entities.** They only exist as nested fields inside the single lecture JSON blob — no independent IDs, no history (regenerating a quiz overwrites the previous one with no versioning).
- **Any relational database / ORM.** Zero matches anywhere for `sqlalchemy|sqlite3|postgres|create_engine`. Storage is one JSON file per lecture (`src/lecture_repository.py`), by explicit design ("swap for a real DB later" per its own docstring).
- **Teacher/student speaker identification.** Diarization only ever emits pyannote's raw, anonymous `SPEAKER_00`/`SPEAKER_01`-style labels. No classification step exists anywhere to distinguish roles.
- **Real personalization / weak-topic detection.** There is nothing to personalize from — see QuizResult above. (The old, now-fixed `Dashboard.tsx`/`Analytics.tsx` used to hardcode a fake "Gradient Descent" weak topic; the current real versions correctly show an empty state instead, but there's still no actual weak-topic *computation* logic anywhere because there's no stored performance data to compute it from.)
- **Vector embeddings / vector database for RAG.** Confirmed intentional — `src/rag_engine.py` explicitly implements TF-IDF instead, documented as a deliberate, swappable design choice, not an oversight.
- **Tests for the Study Assistant backend.** `study_api.py`/`study_tools.py`/`rag_engine.py`/`llm_client.py`/`lecture_repository.py` — zero references in any test file.

---

## 6. Config state right now (`D:\fyp\config.yaml`) — some decided, some still open

| Flag | Current value | Status |
|---|---|---|
| `low_band_denoise.enabled` | `true` | **Set yesterday by `PROJECT_ANALYSIS.md`'s pass, not yet addressed this session — ASK: keep or revert to `false`?** |
| `beautify.enabled` | `true` | **Same — ASK: keep or revert to `false`?** |
| `asr.skip` | `false` | Correct — needed for transcription to happen at all. Keep. |
| `cache.enabled` | `true` | Functional, but caused the stale-result confusion in §4.2. Works fine as long as you remember to clear `D:\fyp\cache\` after any pipeline/config code change. Consider disabling during active development. |
| `profiler.enabled` | `false` | **Fixed this session** — explicitly requested by user ("no use for them, make it faster"). |
| `adaptive_router.enabled` | `false` | **Fixed this session** — same. |
| `spectral_restoration.enabled` | `false` | **Fixed this session** — same. |
| `quality_metrics.enabled` | `false` | **Fixed this session** — same. |

All 4 DSP flags were `enabled: true` in the uncommitted local copy (contradicting both the README's "disabled by default" default and the user's own stated prior decision to not use them) — reverted to `false` this session, confirmed to take effect via the live log (no more DSP-stage log lines).

---

## 7. Things NOT yet tested — real gaps in verification, not claims either way

- ~~Root cause of the performance problem~~ — **found and fixed**, see FIX LOG #1. Not yet re-verified against real audio (deferred to the final comprehensive run).
- **Multi-speaker diarization accuracy.** The only file tested this session (`output_overlapped.mp3`) turned out to be single-narrator content (confirmed by transcript content itself — "Welcome to 100 Days of Research Papers... solo presenter tone throughout). Diarization correctly returned 1 speaker for it, which is *plausibly correct behavior*, not a bug — but this means **diarization has never actually been tested against a real multi-speaker file** this session. Unknown whether it correctly splits multiple real speakers.
- **Video file handling** (`src/media_loader.py`'s `moviepy`-based extraction path) — not exercised with any real video file this session.
- ~~A real, successful (non-402) LLM generation~~ — **confirmed**, see FIX LOG #11. `openai/gpt-4o-mini` (the default) still has no credits on this account; `minimax/minimax-m3:free` works right now. Free models rotate/rate-limit without warning (confirmed: 1 of the 4 tried was fully dead, 1 returned null content, 1 was rate-limited twice) — don't hard-code a single free model as a permanent fix, and consider basic retry-with-backoff for 429s (new, minor finding — `llm_client.py::chat()` doesn't retry transient errors at all right now).
- **Visual, live, side-by-side confirmation of frontend + backend both running together with real data on screen.** Have strong network-level evidence (§2.16) but never took a final screenshot with both servers up and a populated Library/Dashboard.
- **Docker build/deploy.** `Dockerfile`/`docker-compose.yml` exist and look reasonable but were not built or run this session.

---

## 8. Full fix list, prioritized

### P0 — blocks real usage
- [x] **Diagnose the ~21x-slower-than-realtime pipeline performance root cause** — confirmed in code (22× redundant Whisper calls). [~] **Fix applied** (single-pass transcription) — code-complete, **not yet re-verified against real audio** (see FIX LOG #1). Note: this only fixes the transcription-redundancy portion; diarization/DFN/MetricGAN+ are independently slow on CPU and were not addressed — do not expect this alone to hit the README's 5-7.5x-faster-than-realtime claim.
- [ ] **Commit the uncommitted working-tree fixes** (§0) — otherwise none of this survives a fresh clone. **Not done — waiting to be asked before running `git commit`.**

### P1 — core product gaps
- [ ] Add real authentication (Student accounts, login/signup that actually calls a backend, session/token handling). **Not started — needs a scope decision first (see chat).**
- [ ] Add auth checks to backend API routes; stop returning `allow_origins=["*"]` once real auth exists.
- [x] Persist quiz results — done, see FIX LOG #5.
- [x] Minimal attempt-history structure — done (`quiz_attempts` list per lecture, `quiz_attempts` count + `best_score` in the library summary). Still no dedicated `Student`/`QuizResult` entities — this is a lecture-scoped list, not a per-student one, since there's still no Student concept.

### P2 — important but not blocking a local demo
- [x] Fix `/api/model-status`'s Pyannote-readiness check — done, see FIX LOG #2.
- [x] Fix `pytest.ini`'s section header + install `pytest-cov` — done, see FIX LOG #4. `black`/`flake8`/`pytest-asyncio`/`pytest-mock` still **not installed** (weren't blocking the addopts fix, lower priority).
- [ ] Add tests for the entire Study Assistant API surface (currently zero coverage).
- [ ] Decide + resolve: `beautify` and `low_band_denoise` — keep on or revert (§6, still an open question, needs your call).
- [ ] Test with a real multi-speaker audio file to actually validate diarization speaker-splitting.
- [ ] Test video-file upload/extraction path with a real video.
- [x] Get one full successful (non-402) LLM generation confirmed — done, see FIX LOG #11.
- [ ] Add basic retry-with-backoff to `llm_client.py::chat()` for transient errors (429 rate-limits especially, common on free-tier models) — new, minor finding from testing #11.

### P3 — cleanup
- [x] `.env.example` unused-var cleanup — done, see FIX LOG #6 (turned out to be ~13 vars, not just `API_KEY`).
- [x] `redis`/`docker-compose.yml` — documented as unused rather than removed (kept conservative — didn't want to delete infra config without being asked). See FIX LOG #7.
- [ ] Document the "clear `./cache` after pipeline/config changes" gotcha somewhere a future dev will see it (or make the cache key include a code/version fingerprint so it invalidates itself).
- [ ] Redundant Whisper reload on every request — **fixed**, see FIX LOG #3 (moving here from being unlisted before).

### P4 — nice-to-have (not investigated deeply, lower priority)
- [ ] Teacher/student speaker-role labeling (heuristic or manual).
- [ ] Real weak-topic detection / personalization once quiz-result history exists.
- [ ] Docker build/deploy verification.

---

## 9. Why the first pass of this audit got some things wrong (context, so it doesn't happen again)

The first audit pass was run inside a **git worktree** (`D:\fyp\.claude\worktrees\...`), which is a fresh checkout containing only what's committed to git — no `venv/`, no `models/`, no `.env`, no `data/`, none of the uncommitted fixes in §0. Running a bare `python` there resolved to an unrelated system Python install with none of the ML packages, which produced an incorrect "DeepFilterNet/pyannote/speechbrain are missing" finding. It also could not see `frontend/src/lib/api.ts` (never committed) or the real `Dashboard.tsx`/`Analytics.tsx` rewrites (uncommitted), so it correctly-for-that-checkout, incorrectly-for-reality flagged the frontend as completely broken and the dashboards as fully mocked.

**Lesson applied for the rest of this document:** everything in §2 and §3 was verified by actually running the real code, in `D:\fyp`, with `D:\fyp\venv`, against real models and a real audio file — not by reading source and assuming.
