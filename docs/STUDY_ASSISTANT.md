# Study Assistant — NLP/LLM + RAG Layer

This is the right-hand half of the architecture diagram: everything *after* the
lecture has been cleaned and transcribed. It turns a transcript into **study
notes, quizzes, a personalized schedule, an evaluation/analysis**, and a
**RAG-grounded chatbot** — all stored in a **lecture repository**.

The audio half (noise removal + diarization + Whisper) is documented separately in
[NOISE_REMOVAL_AND_DIARIZATION.md](NOISE_REMOVAL_AND_DIARIZATION.md) and
[PIPELINE_EXPLAINED.md](PIPELINE_EXPLAINED.md).

---

## 1. How it maps to the architecture diagram

| Diagram box | Implemented by |
|---|---|
| Audio Preprocessing | `src/pipeline.py` (DeepFilterNet3 → MetricGAN+) |
| Speech Transcription (Whisper) | `src/asr_processor.py` |
| **Lecture repository / Storage** | `src/lecture_repository.py` (JSON store under `data/lectures/`) |
| **RAG** (query) | `src/rag_engine.py` (TF-IDF retrieval) |
| **NLP & LLM** | `src/llm_client.py` (OpenRouter) + `src/study_tools.py` |
| **Notes** | `study_tools.generate_notes` |
| **Quiz Generation** | `study_tools.generate_quiz` (+ `grade_quiz`) |
| **Personalize Schedule** | `study_tools.generate_schedule` |
| **Evaluation / Analysis** | `study_tools.evaluate_lecture` |
| **Dashboard / Chat / Library / Quiz UI** | `frontend/` (React) → calls the API below |
| API surface | `src/study_api.py` (FastAPI router, included in `backend.py`) |

**Data flow:** `upload → /api/process-lecture (clean + transcribe) → stored as a
lecture → /api/lecture/{id}/{notes|quiz|schedule|evaluate|chat}`.

---

## 2. Enabling the LLM (one env var)

The NLP/LLM features call an **OpenAI-compatible** provider (default: OpenRouter).
Add a key to `.env`:

```bash
OPENROUTER_API_KEY=sk-or-...          # from https://openrouter.ai/keys
# Optional: choose a model. Default openai/gpt-4o-mini needs credits.
# For a no-credit option use a free model:
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct:free
# Optional: point at any other OpenAI-compatible endpoint (e.g. NVIDIA NIM)
OPENROUTER_BASE_URL=
```

- **Without a key:** every LLM route returns HTTP 503 with a clear message; the
  audio pipeline, RAG retrieval, and repository still work.
- **402 Payment Required** from the provider → your account is out of credits;
  add credits or switch `OPENROUTER_MODEL` to a `:free` model.
- Check status anytime: `GET /api/llm-status` → `{"configured": true, "model": "..."}`.

---

## 3. API reference

| Method & path | Purpose | Body |
|---|---|---|
| `POST /api/process-lecture` | Clean + transcribe an upload, store it, return `lecture_id` | multipart file (`whisper_model`, `enable_diarization`, `title`) |
| `POST /api/lecture` | Create a lecture from raw transcript text (no audio) | `{title, transcript}` |
| `GET /api/library` | List stored lectures (summaries) | — |
| `GET /api/lecture/{id}` | Full lecture record | — |
| `DELETE /api/lecture/{id}` | Delete a lecture | — |
| `POST /api/lecture/{id}/notes` | Generate (and cache) Markdown study notes | `?refresh=true` to regenerate |
| `POST /api/lecture/{id}/quiz` | Generate MCQ quiz | `{num_questions}` |
| `POST /api/lecture/{id}/quiz/grade` | Grade submitted answers | `{answers: [int]}` |
| `POST /api/lecture/{id}/schedule` | Personalized study plan | `{days}` |
| `POST /api/lecture/{id}/evaluate` | Topics / difficulty / study-time analysis | `?refresh=true` |
| `POST /api/lecture/{id}/chat` | RAG-grounded Q&A over the lecture | `{question, top_k}` |
| `GET /api/llm-status` | Whether the LLM key is configured | — |

Generated artifacts (notes/quiz/schedule/evaluation) are **cached** in the lecture
record after first generation; pass `refresh=true` to regenerate.

### Example
```bash
# 1) process a lecture (clean + transcribe + store)
curl -F "file=@lecture.mp3" "http://localhost:8000/api/process-lecture"
# → {"lecture_id":"6e226c10b8bc", "transcript":"...", ...}

# 2) generate notes
curl -X POST "http://localhost:8000/api/lecture/6e226c10b8bc/notes"

# 3) ask a question (RAG)
curl -X POST "http://localhost:8000/api/lecture/6e226c10b8bc/chat" \
     -H "Content-Type: application/json" \
     -d '{"question":"What is the Calvin cycle?"}'
```

---

## 4. Design notes
- **RAG without heavy deps:** retrieval uses TF-IDF (scikit-learn) over overlapping
  transcript chunks — fully offline, no embedding model to download. The interface
  (`RagEngine`) can be swapped for vector embeddings later without touching callers.
- **Grounded answers:** the chatbot is instructed to answer *only* from retrieved
  passages and to say so when the answer isn't in the lecture (reduces hallucination).
  Responses include the source passages used.
- **Provider-agnostic:** `llm_client.py` speaks the OpenAI chat-completions format,
  so OpenRouter, a local server, or NVIDIA NIM all work by changing two env vars.
- **Storage:** `lecture_repository.py` uses one JSON file per lecture under
  `data/lectures/` (git-ignored). Swap for SQLite/Postgres later without changing
  the API.

---

## 5. What remains (frontend wiring)
The backend for the entire diagram is complete and tested. The React pages
(`Dashboard`, `Library`, `Quiz`, `Chat`, `Analytics`) currently exist as UI shells;
the remaining task is to point them at the endpoints above (e.g. Library →
`GET /api/library`, Quiz → `POST /api/lecture/{id}/quiz`, Chat →
`POST /api/lecture/{id}/chat`).
