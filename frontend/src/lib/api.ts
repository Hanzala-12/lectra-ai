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
};

export type AudioFile = {
  audio_id: string;
  kind: string; // "original" | "cleaned" | "speaker:<label>"
  file_path: string;
  duration: number | null;
};

export type Lecture = {
  id: string;
  title: string;
  created_at: number;
  transcript_text: string;
  transcript_segments: TranscriptSegment[];
  diarization: any[];
  audio_files: AudioFile[];
  metadata: Record<string, any>;
  notes: string | null;
  quiz: QuizQuestion[] | null;
  schedule: Schedule | null;
  evaluation: Evaluation | null;
  chat_history: { question: string; answer: string }[];
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
  plan: { day: number; focus: string; tasks: string[]; est_minutes: number }[];
  tips: string[];
  student_id?: string;
  lecture_id?: string;
  available_time?: string | null;
  learning_goals?: string | null;
  created_at?: number;
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

  notes: (id: string, refresh = false) =>
    req<{ notes: string; cached: boolean }>(
      `/api/lecture/${id}/notes?refresh=${refresh}`,
      { method: 'POST' },
    ),

  quiz: (id: string, num_questions = 5, refresh = false) =>
    req<{ quiz: QuizQuestion[]; cached: boolean }>(
      `/api/lecture/${id}/quiz?refresh=${refresh}`,
      { method: 'POST', body: JSON.stringify({ num_questions }) },
    ),

  gradeQuiz: (id: string, answers: (string | null)[]) =>
    req<GradeResult>(`/api/lecture/${id}/quiz/grade`, {
      method: 'POST',
      body: JSON.stringify({ answers }),
    }),

  schedule: (
    id: string,
    days = 7,
    refresh = false,
    available_time?: string,
    learning_goals?: string,
  ) =>
    req<{ schedule: Schedule; cached: boolean }>(
      `/api/lecture/${id}/schedule?refresh=${refresh}`,
      { method: 'POST', body: JSON.stringify({ days, available_time, learning_goals }) },
    ),

  evaluate: (id: string, refresh = false) =>
    req<{ evaluation: Evaluation; cached: boolean }>(
      `/api/lecture/${id}/evaluate?refresh=${refresh}`,
      { method: 'POST' },
    ),

  chat: (id: string, question: string, top_k = 4) =>
    req<ChatResponse>(`/api/lecture/${id}/chat`, {
      method: 'POST',
      body: JSON.stringify({ question, top_k }),
    }),

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
