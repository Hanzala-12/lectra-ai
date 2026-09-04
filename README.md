# Lectra AI

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests](https://img.shields.io/badge/tests-229%20passing-brightgreen.svg)](tests/)

**Turn a noisy lecture recording into a full study kit.** Lectra AI cleans the audio, diarizes and transcribes it, then generates study notes, a self-grading quiz, a spaced-repetition schedule, a lecture evaluation, a chat you can ask questions in, and a short audio recap you can listen to instead of read — all grounded in what was actually said, not hallucinated.

Two halves, one pipeline: a production-grade **speech-audio noise-removal chain** (DeepFilterNet3 → MetricGAN+ → Pyannote diarization → faster-whisper ASR) feeds a **Study Assistant** (NLP/LLM + RAG) that does the rest. Both are real, tested, and wired end to end — not a backend demo with a UI stub in front of it.

---

## What's actually in here

### Audio pipeline
- **Two-stage neural noise removal** — DeepFilterNet3 removes the bulk, MetricGAN+ polishes the residual to a near-silent floor (~39 dB speech-to-noise) without artifacts. See [Noise Removal & Diarization pipeline](docs/NOISE_REMOVAL_AND_DIARIZATION.md).
- **Speaker diarization** — Pyannote 3.1, drives both speech detection and per-speaker transcription.
- **Speech recognition** — faster-whisper (CTranslate2), with per-segment and per-word confidence scores kept and surfaced, not thrown away.
- **CPU-friendly** — the whole chain runs on CPU, no GPU required (see [Performance](#performance) for honest, measured numbers — not marketing ones).
- **Optional Voice Beautify master** — adaptive tone, loudness leveling, high-band "air," SNR-guarded so it can never add noise back. Off by default.
- **Optional custom DSP research layer** — five hand-written signal-processing modules (adaptive routing, spectral restoration, quality metrics, profiling) for academic demonstration, disabled by default. See [Custom DSP Modules](#custom-dsp-modules-academic-layer).

### Study Assistant (NLP/LLM + RAG) — fully wired, frontend and backend
- **Real accounts** — signup/login/sessions; a lecture belongs to exactly one student and is invisible to everyone else.
- **Notes, quiz, schedule, evaluation, chat** — generated per lecture, cached, regenerable on demand. Chat and notes **stream token-by-token** as they're written instead of a blocking wait.
- **Retrieval is real semantic search** — sentence-embedding cosine similarity (`sentence-transformers`), not keyword overlap, with an automatic offline fallback if the model can't load.
- **Real spaced repetition** — the schedule's review date is computed by an actual SM-2 algorithm (the same one Anki uses) over the student's real quiz-score history, not improvised by the LLM.
- **An audio recap, not just a text one** — a short spoken-style summary narrated by a fully offline neural TTS voice (Piper), so there's something to *listen to*, not only read.
- **Click any transcript line to jump the audio there**, rename anonymous `SPEAKER_00`-style labels once and it sticks everywhere (transcript, exports, audio cards), and low-confidence lines are quietly flagged instead of presented as equally certain.
- **Export** everything generated for a lecture as one Markdown file.
- Provider-agnostic LLM client (OpenRouter by default) with retry-with-backoff and multi-key rotation, so one exhausted or rate-limited key doesn't fail the whole request.

See [Study Assistant docs](docs/STUDY_ASSISTANT.md) for the full API reference.

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+ (for the frontend)
- 8GB RAM minimum (16GB recommended)
- ffmpeg (bundled automatically)

### Installation

```bash
git clone https://github.com/Hanzala-12/lectra-ai.git
cd lectra-ai

python -m venv venv
venv\Scripts\activate          # Windows; `source venv/bin/activate` elsewhere

pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:
- `HF_TOKEN` — required for speaker diarization (a gated HuggingFace model; accept the terms for `pyannote/speaker-diarization-3.1` and `pyannote/segmentation-3.0` on huggingface.co first).
- `OPENROUTER_API_KEY` — required for the Study Assistant's LLM features (notes/quiz/schedule/evaluation/chat/recap script). Without it those routes return a clean `503`, not a crash — the audio pipeline itself works fine either way.

### Usage

**Web interface** (the primary way to use this):
```bash
python backend.py                              # API on :8000 (docs at /docs)
cd frontend && npm install && npm run dev       # dev server on :3000
```
Or on Windows, `start_both.bat` launches both in separate windows.

**Command line**, no server:
```bash
python clean_voice.py input.mp3
python clean_voice.py audio.wav --transcript --transcript-format srt
python clean_voice.py ./audio_folder/           # batch mode
```

**Docker**:
```bash
docker-compose up --build      # backend:8000, frontend:3000
```

---

## Project Structure

```
.
├── backend.py                   # FastAPI app: audio-pipeline routes + mounts src/study_api.py
├── clean_voice.py                # Standalone CLI, no server required
├── config.yaml                   # Pipeline stage configuration (single source of truth)
├── src/
│   ├── pipeline.py               # Orchestrates the full audio pipeline
│   ├── deepfilter_processor.py   # DeepFilterNet3
│   ├── metricgan_processor.py    # MetricGAN+ final polish
│   ├── diarization.py            # Pyannote speaker diarization
│   ├── asr_processor.py          # faster-whisper transcription + confidence scoring
│   ├── voice_beautify.py         # Optional post-cleaning master
│   │
│   ├── auth_api.py, student_repository.py, session_store.py       # Real Student auth
│   ├── study_api.py, study_tools.py, llm_client.py, rag_engine.py # Study Assistant + RAG
│   ├── spaced_repetition.py, tts_engine.py                        # SM-2 scheduling, Piper TTS
│   ├── lecture_repository.py, quiz_repository.py,                 # One JSON file per record —
│   │   study_plan_repository.py, audio_file_repository.py,        # the intended swap point for
│   │   lecture_session_repository.py                              # a real DB later
│   │
│   └── audio_quality_profiler.py, spectral_restoration.py,        # [academic] disabled by
│       audio_quality_metrics.py, adaptive_router.py                # default, see below
│
├── frontend/                     # React 19 + TypeScript + Vite + Tailwind v4
├── tests/                        # 229 tests — pipeline, auth, Study API, RAG, TTS, etc.
├── docs/                         # Architecture, pipeline internals, Study Assistant reference
└── cleanup_tool.py                # Standalone repo-maintenance CLI, unrelated to the pipelines
```

---

## Custom DSP Modules (academic layer)

Five hand-written signal-processing modules bolted onto the production DeepFilterNet3 → MetricGAN+ chain for research and demonstration purposes — an **input quality profiler**, **spectral restoration**, **nine-metric quality evaluation**, an **adaptive processing router**, and a **Numba/SIMD-optimized benchmark helper**. All disabled by default (`config.yaml`) to preserve the stable production path; enabling any of them is a config flag, not a code change.

Full API reference, code samples, and benchmark numbers: **[docs/CUSTOM_DSP.md](docs/CUSTOM_DSP.md)**.

---

## Documentation

- **[Noise Removal & Diarization Pipeline](docs/NOISE_REMOVAL_AND_DIARIZATION.md)** — full signal chain, stage-by-stage, and the engineering decisions behind it ⭐
- **[Pipeline Explained (plain language)](docs/PIPELINE_EXPLAINED.md)** — the same pipeline, explained without jargon
- **[Study Assistant (NLP/LLM + RAG)](docs/STUDY_ASSISTANT.md)** — full API reference for notes/quiz/schedule/evaluation/chat/recap ⭐
- **[Architecture](docs/ARCHITECTURE.md)** — system design and component overview
- **[Custom DSP Modules](docs/CUSTOM_DSP.md)** — the academic layer, API reference
- **[Performance Optimization](docs/OPTIMIZATION.md)** — CPU optimization techniques
- **[Integration Guide](docs/INTEGRATION.md)** — how to integrate the custom modules into the pipeline
- **[Dependencies](docs/DEPENDENCIES.md)** — what's installed and why
- **[AUDIT_REPORT.md](AUDIT_REPORT.md)** — this project's own running, evidence-cited self-audit: every claim about what works is backed by a live test, not asserted. The most honest single document in this repo.

---

## Testing

```bash
pytest tests/                                              # full suite — 229 passing
pytest tests/test_study_api.py -v                           # Study Assistant API
pytest tests/test_pipeline.py                                # audio pipeline
pytest tests/test_rag_engine.py tests/test_spaced_repetition.py tests/test_tts_engine.py
```

Coverage spans the audio pipeline, real Student auth, the full Study Assistant API surface, RAG retrieval (both the embedding path and the TF-IDF fallback), spaced repetition, TTS, and ASR confidence scoring. A meaningful share of this was also verified live against real models and a real LLM, not just mocks — see `AUDIT_REPORT.md` for exactly what was checked and how.

---

## Performance

Measured, not estimated — see [AUDIT_REPORT.md](AUDIT_REPORT.md) for the full investigation (per-stage breakdown, what was tried, what was rejected for hurting accuracy).

On a 2-core CPU with no GPU, a 2.3-minute real lecture recording takes **~11 minutes** to process end-to-end (denoise + diarize + transcribe) — roughly **4.7x the audio's own length**, down from an original **~21x** after two verified fixes (single-pass transcription, batched diarization inference). Diarization and speech recognition together are **95%+** of that time, and both are genuine neural-network inference at this quality level, not waste — two further candidate optimizations were tested and rejected because they measurably degraded transcription accuracy. Closing the remaining gap needs a GPU or an accepted quality trade-off, not more configuration tuning.

This is slower than real-time. It is not sold here as anything else.

---

## Technology Stack

| Component | Technology |
|---|---|
| Backend | FastAPI |
| Frontend | React 19 + TypeScript + Vite + Tailwind v4 |
| Noise removal (stage 1) | DeepFilterNet3 |
| Noise removal (stage 2) | MetricGAN+ (SpeechBrain) |
| Speaker diarization | Pyannote 3.1 |
| Speech recognition | faster-whisper (CTranslate2) |
| RAG retrieval | sentence-transformers (`all-MiniLM-L6-v2`), TF-IDF fallback |
| LLM | OpenRouter (provider-agnostic, OpenAI-compatible), multi-key rotation |
| Audio recap narration | Piper TTS (fully offline neural TTS) |
| Auth | Session tokens, PBKDF2 password hashing |
| Storage | One JSON file per record, per repository — deliberate, documented swap point for a real DB |
| DSP | NumPy, SciPy, Numba (optional custom layer) |

---

## Configuration

The key pipeline settings live in `config.yaml` (full reference: [the pipeline doc](docs/NOISE_REMOVAL_AND_DIARIZATION.md#6-configuration-reference)):

```yaml
deepfilternet:
  atten_lim_db: 30          # suppression strength
  post_filter: false        # off → preserves quiet consonants

neural_enhancer:
  enabled: true              # MetricGAN+ final polish; false = DeepFilterNet-only

beautify:
  enabled: false             # optional post-cleaning master, off by default

diarization:
  enabled: true
  min_speakers: 1
  max_speakers: 10

asr:
  model: "turbo"             # turbo, large-v3, large, medium, small, base, tiny
  language: null              # auto-detect
```

Environment variables actually read by the code are documented in [`.env.example`](.env.example) — `HF_TOKEN` (diarization), `OPENROUTER_API_KEY` (+ optional `_2`/`_3` for rotation, `OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`), and `MAX_FILE_SIZE_MB`. That file also explains which commonly-seen env vars are *not* read by anything, to save you debugging one that silently does nothing.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run `black .` and `flake8 --max-line-length=127 --select=E9,F63,F7,F82` before committing (or `pre-commit run --all-files`, which runs both)
4. Open a Pull Request

---

## Roadmap

What's genuinely still open, from this project's own audit — not a wishlist:

- **GPU support** — the single largest remaining performance gap (see [Performance](#performance)); a config-level `device` switch on top of the existing pipeline.
- **Topic-level weak-area detection** — the data now exists (per-question quiz feedback, spaced-repetition history); the computation to turn it into "you're weak on X" doesn't yet.
- **A real database** — the current one-JSON-file-per-record storage is a deliberate, disclosed placeholder, documented as the intended swap point in every repository module's own docstring.
- **`QuizResult` as its own top-level repository** — currently still embedded on the Lecture record, unlike Quiz/StudyPlan/AudioFile.
- **Multi-language transcription** — faster-whisper already supports it; not yet exposed end-to-end through the Study Assistant.

---

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- **DeepFilterNet** (Schröter et al.) and **MetricGAN+/SpeechBrain** (Fu et al.) for the noise-removal and speech-enhancement models
- **faster-whisper** (Systran) and **Whisper** (OpenAI) for speech recognition
- **Pyannote** (Hervé Bredin) for speaker diarization
- **Piper** (OHF Voice) for offline neural text-to-speech

## Citation

```bibtex
@software{lectra_ai,
  title = {Lectra AI},
  year = {2026},
  author = {Hanzala-12 and contributors},
  url = {https://github.com/Hanzala-12/lectra-ai}
}
```

---

**Status**: audio pipeline and Study Assistant both working end-to-end, frontend fully wired to both, 229 automated tests. See [AUDIT_REPORT.md](AUDIT_REPORT.md) for the detailed, evidence-cited breakdown of exactly what's been verified and what's honestly still open.
**Maintainer**: Hanzala-12

If you find this project useful, consider starring it.

[![Star History Chart](https://api.star-history.com/svg?repos=Hanzala-12/lectra-ai&type=Date)](https://star-history.com/#Hanzala-12/lectra-ai&Date)
