/**
 * Central API client for the Lectra AI backend.
 * Base URL comes from VITE_API_BASE_URL (falls back to same-origin / proxy).
 */

const API_BASE = ((import.meta as any).env?.VITE_API_BASE_URL || '').trim();

export function buildUrl(path: string): string {
  if (!path) return path;
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  if (API_BASE) return `${API_BASE.replace(/\/$/, '')}${path}`;
  return path;
}

// ---------- auth token ----------
const TOKEN_KEY = 'lectra_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(buildUrl(path), {
    headers,
    ...options,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body.detail || body.error || detail;
    } catch {
      /* ignore */
    }
    if (res.status === 401) {
      // Session is gone/expired server-side — drop the stale token so the
      // next protected-route check redirects to /login instead of looping.
      clearToken();
    }
    const err = new Error(detail) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  return res.json() as Promise<T>;
}

// Consumes a `data: {...}\n\n`-formatted SSE POST response (native
// EventSource can't be used here — it's GET-only and can't carry an
// Authorization header or a JSON body). Calls onDelta as text arrives and
// resolves with whatever fields the server's final `{done: true, ...}`
// event carried (e.g. `sources` for chat, `cached` for notes).
async function reqStream<TDone extends Record<string, unknown>>(
  path: string,
  options: RequestInit,
  onDelta: (text: string) => void,
): Promise<TDone> {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(buildUrl(path), { headers, ...options });
  if (!res.ok || !res.body) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body.detail || body.error || detail;
    } catch {
      /* ignore — not JSON, keep the generic message */
    }
    if (res.status === 401) clearToken();
    const err = new Error(detail) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary: number;
    while ((boundary = buffer.indexOf('\n\n')) !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const line = rawEvent.split('\n').find((l) => l.startsWith('data: '));
      if (!line) continue;
      const event = JSON.parse(line.slice('data: '.length));
      if (event.error) throw new Error(event.error);
      if (event.delta) onDelta(event.delta);
      if (event.done) return event as TDone;
    }
  }
  throw new Error('Stream ended without a completion event');
}

// ---------- types ----------
export type LectureSummary = {
  id: string;
  title: string;
  created_at: number;
  duration?: number;
  has_notes: boolean;
  has_quiz: boolean;
  has_schedule: boolean;
  has_evaluation: boolean;
  word_count: number;
  quiz_attempts: number;
  best_score: number | null;
};

export type TranscriptSegment = {
  start: number;
  end: number;
  text: string;
  speaker?: string | null;
  // Confidence signals (src/asr_processor.py::combine_with_diarization) —
  // null on segments from before this field existed, not "0% confident".
  asr_confidence?: number | null; // ASR's own certainty in its transcription, 0-1
  speaker_confidence?: number | null; // how cleanly one diarization turn covers this segment, 0-1
};

export type AudioFile = {
  audio_id: string;
  kind: string; // "original" | "cleaned" | "speaker:<label>"
  file_path: string;
  duration: number | null;
};

export type ReferenceNote = {
  id: string;
  text: string;
  created_at: number;
};

export type Lecture = {
  id: string;
  title: string;
  created_at: number;
  transcript_text: string;
  transcript_segments: TranscriptSegment[];
  diarization: any[];
  audio_files: AudioFile[];
  speaker_names: Record<string, string>; // raw diarization label -> chosen display name
  review_state: ReviewState;
  recap_script: string | null;
  recap_audio_url: string | null;
  metadata: Record<string, any>;
  notes: string | null;
  quiz: QuizQuestion[] | null;
  quiz_id: string | null;
  schedule: Schedule | null;
  evaluation: Evaluation | null;
  chat_history: { question: string; answer: string }[];
  // Student-added supplementary text the chatbot's RAG retrieval also draws
  // on, alongside the transcript — see study_api.py::_chat_messages_and_sources.
  reference_notes: ReferenceNote[];
};

export type QuizAnswer = {
  answer_id: string;
  text: string;
  is_correct: boolean;
};

export type QuizQuestion = {
  question_id: string;
  question: string;
  answers: QuizAnswer[];
  explanation: string;
};

export type Schedule = {
  id?: string;
  plan: { day: number; focus: string; tasks: string[]; est_minutes: number }[];
  tips: string[];
  student_id?: string;
  lecture_id?: string;
  available_time?: string | null;
  learning_goals?: string | null;
  created_at?: number;
};

// Real SM-2 spaced-repetition state computed from actual quiz score history
// (src/spaced_repetition.py) — not LLM-generated, always fresh (recomputed
// on every fetch, never stale).
export type ReviewState = {
  attempts_considered: number;
  repetition_count: number;
  ease_factor: number;
  interval_days: number;
  last_graded_at: number | null;
  next_review_at: number | null;
  quality_history: number[];
};

export type Evaluation = {
  main_topics: string[];
  difficulty: string;
  estimated_study_minutes: number;
  prerequisites: string[];
  comprehension_questions: string[];
  summary: string;
};

export type ChatResponse = {
  answer: string;
  sources: { text: string; score: number }[];
};

export type GradeResult = {
  result_id: string;
  score: number;
  correct: number;
  total: number;
  breakdown: {
    question: string;
    your_answer_id: string | null;
    correct_answer_id: string | null;
    is_correct: boolean;
    explanation: string;
  }[];
};

export type Student = {
  id: string;
  username: string;
  name: string;
  email: string | null;
  created_at: number;
};

export type AuthResponse = {
  token: string;
  student: Student;
};

// ---------- endpoints ----------
export const api = {
  llmStatus: () => req<{ configured: boolean; model: string | null }>('/api/llm-status'),

  library: () => req<{ lectures: LectureSummary[] }>('/api/library'),
  getLecture: (id: string) => req<Lecture>(`/api/lecture/${id}`),
  deleteLecture: (id: string) =>
    req<{ deleted: boolean }>(`/api/lecture/${id}`, { method: 'DELETE' }),
  renameSpeakers: (id: string, names: Record<string, string>) =>
    req<{ speaker_names: Record<string, string> }>(`/api/lecture/${id}/speakers`, {
      method: 'PUT',
      body: JSON.stringify({ names }),
    }),

  addReferenceNote: (id: string, text: string) =>
    req<{ reference_notes: ReferenceNote[] }>(`/api/lecture/${id}/reference-notes`, {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),
  deleteReferenceNote: (id: string, noteId: string) =>
    req<{ reference_notes: ReferenceNote[] }>(
      `/api/lecture/${id}/reference-notes/${noteId}`,
      { method: 'DELETE' },
    ),

  notes: (id: string, refresh = false) =>
    req<{ notes: string; cached: boolean }>(
      `/api/lecture/${id}/notes?refresh=${refresh}`,
      { method: 'POST' },
    ),
  notesStream: (id: string, onDelta: (text: string) => void, refresh = false) =>
    reqStream<{ done: true; cached: boolean }>(
      `/api/lecture/${id}/notes/stream?refresh=${refresh}`,
      { method: 'POST' },
      onDelta,
    ),

  quiz: (id: string, num_questions = 5, refresh = false) =>
    req<{ quiz: QuizQuestion[]; quiz_id: string; cached: boolean }>(
      `/api/lecture/${id}/quiz?refresh=${refresh}`,
      { method: 'POST', body: JSON.stringify({ num_questions }) },
    ),

  // quiz_id is optional — omit it to grade against the latest quiz (the
  // common case); pass it to grade against the exact version a student
  // actually attempted, even if a newer one has since been generated.
  gradeQuiz: (id: string, answers: (string | null)[], quiz_id?: string) =>
    req<GradeResult>(`/api/lecture/${id}/quiz/grade`, {
      method: 'POST',
      body: JSON.stringify({ answers, quiz_id }),
    }),

  schedule: (
    id: string,
    days = 7,
    refresh = false,
    available_time?: string,
    learning_goals?: string,
  ) =>
    req<{ schedule: Schedule; review_state: ReviewState; cached: boolean }>(
      `/api/lecture/${id}/schedule?refresh=${refresh}`,
      { method: 'POST', body: JSON.stringify({ days, available_time, learning_goals }) },
    ),
  reviewSchedule: (id: string) =>
    req<ReviewState>(`/api/lecture/${id}/review-schedule`),

  evaluate: (id: string, refresh = false) =>
    req<{ evaluation: Evaluation; cached: boolean }>(
      `/api/lecture/${id}/evaluate?refresh=${refresh}`,
      { method: 'POST' },
    ),

  recap: (id: string, refresh = false) =>
    req<{ script: string; audio_url: string; cached: boolean }>(
      `/api/lecture/${id}/recap?refresh=${refresh}`,
      { method: 'POST' },
    ),

  chat: (id: string, question: string, top_k = 4) =>
    req<ChatResponse>(`/api/lecture/${id}/chat`, {
      method: 'POST',
      body: JSON.stringify({ question, top_k }),
    }),
  chatStream: (
    id: string,
    question: string,
    onDelta: (text: string) => void,
    top_k = 4,
  ) =>
    reqStream<{ done: true; sources: ChatResponse['sources'] }>(
      `/api/lecture/${id}/chat/stream`,
      { method: 'POST', body: JSON.stringify({ question, top_k }) },
      onDelta,
    ),

  // ---------- auth ----------
  signup: async (username: string, password: string, name?: string, email?: string) => {
    const r = await req<AuthResponse>('/api/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ username, password, name, email }),
    });
    setToken(r.token);
    return r;
  },

  login: async (username: string, password: string) => {
    const r = await req<AuthResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    setToken(r.token);
    return r;
  },

  logout: async () => {
    try {
      await req('/api/auth/logout', { method: 'POST' });
    } finally {
      clearToken();
    }
  },

  me: () => req<Student>('/api/auth/me'),
};
